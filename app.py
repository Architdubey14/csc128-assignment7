"""
CSC-128 Assignment 7: Streamlit interface for the room booking agent
Archit Dubey

Run:  streamlit run app.py
"""
import json

import streamlit as st
from groq import Groq, APIError, RateLimitError

import tools
from agent import MAX_ROUNDS, MODEL, SYSTEM_PROMPT, dispatch, pending_write, run_agent

GREETING = (
    "Hi, I can check which rooms are free, tell you the building hours, and book a "
    "room for you. I cannot cancel or change a booking, so contact the building "
    "office for that."
)


def get_client():
    """Read the key from st.secrets and fail with a clear message."""
    try:
        key = st.secrets["GROQ_API_KEY"]
    except (KeyError, FileNotFoundError):
        st.error(
            "No API key found. Create .streamlit/secrets.toml with GROQ_API_KEY, "
            "and run the app from the folder that contains .streamlit."
        )
        st.stop()
    return Groq(api_key=key)


def show_log(entries):
    """Show every tool call, its arguments, and its result."""
    if not entries:
        return
    with st.expander("Tool calls (" + str(len(entries)) + ")", expanded=True):
        for entry in entries:
            st.markdown("**" + entry["name"] + "**")
            st.code(entry["arguments"], language="json")
            st.text(entry["result"])


def ask_model(client, allow_write=False):
    """Run the agent once and record what happened for display."""
    log = []
    try:
        reply, updated = run_agent(client, st.session_state.messages, log, allow_write)
        st.session_state.messages = updated
    except RateLimitError:
        reply = (
            "I am getting too many requests right now. "
            "Wait about a minute, then ask again."
        )
    except APIError:
        reply = (
            "I could not reach the language model. Check your internet connection "
            "and try again. If it keeps happening, the API key may have been revoked."
        )

    st.session_state.display.append({"role": "assistant", "content": reply, "log": log})
    st.session_state.pending = pending_write(log)


def main():
    st.title("Room Booking Agent")
    st.caption(
        "You are chatting with an automated assistant, not a person. It can run "
        "tools on your behalf, and every tool call is shown under the reply."
    )

    client = get_client()

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if "display" not in st.session_state:
        st.session_state.display = []

    if "pending" not in st.session_state:
        st.session_state.pending = None

    with st.sidebar:
        st.subheader("Agent")
        st.write("Model:", MODEL)
        st.write("Tool call rounds allowed:", MAX_ROUNDS)
        st.write("Tools available:", ", ".join(sorted(tools.AVAILABLE_TOOLS)))
        st.caption(
            "There is deliberately no tool to cancel, move, or look up a booking. "
            "See the README."
        )

        st.subheader("Schedule")
        for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
            free = tools.AVAILABILITY[day]
            if free:
                st.write(day + ":", ", ".join(free))
            else:
                st.write(day + ": nothing free")

        st.subheader("Bookings made")
        if not tools.BOOKINGS:
            st.caption("None yet.")
        for booking in tools.BOOKINGS:
            st.write(booking["day"], "room", booking["room"], "for", booking["name"])

    with st.chat_message("assistant"):
        st.markdown(GREETING)

    for item in st.session_state.display:
        with st.chat_message(item["role"]):
            st.markdown(item["content"])
            if item["role"] == "assistant":
                show_log(item.get("log", []))

    # A write tool was requested and blocked. Nothing has changed yet.
    if st.session_state.pending:
        details = st.session_state.pending
        st.warning(
            "Confirm this booking: room "
            + str(details.get("room"))
            + " on "
            + str(details.get("day"))
            + " for "
            + str(details.get("name"))
            + ". Nothing has been booked yet."
        )
        left, right = st.columns(2)

        if left.button("Confirm booking", type="primary"):
            # Run the exact arguments that were blocked, with no model round
            # trip in between, so nothing can change after the user agreed.
            result = dispatch("book_room", json.dumps(details), allow_write=True)
            st.session_state.messages.append(
                {"role": "user", "content": "I confirmed. Result: " + result}
            )
            st.session_state.display.append({"role": "user", "content": "Confirmed."})
            st.session_state.display.append(
                {
                    "role": "assistant",
                    "content": result,
                    "log": [
                        {
                            "name": "book_room",
                            "arguments": json.dumps(details),
                            "result": result,
                        }
                    ],
                }
            )
            st.session_state.pending = None
            st.rerun()

        if right.button("Cancel"):
            st.session_state.messages.append(
                {"role": "user", "content": "No, do not book that."}
            )
            st.session_state.display.append(
                {"role": "user", "content": "No, do not book that."}
            )
            st.session_state.pending = None
            ask_model(client)
            st.rerun()

    question = st.chat_input("Ask about rooms, hours, or book one")

    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        st.session_state.display.append({"role": "user", "content": question})
        ask_model(client)
        st.rerun()


if __name__ == "__main__":
    main()