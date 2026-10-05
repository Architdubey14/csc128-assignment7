"""
CSC-128 Assignment 7: the tool calling loop and the dispatch guard
Archit Dubey

The dispatch function below imports nothing from Streamlit or groq, so
test_tools.py can exercise it with no API key.
"""
import json

from tools import AVAILABLE_TOOLS, TOOL_SCHEMAS

MODEL = "openai/gpt-oss-20b"
MAX_ROUNDS = 5

# Tools that change state. These never run from a model request alone.
WRITE_TOOLS = {"book_room"}

SYSTEM_PROMPT = """You are the room booking assistant for a campus building.

You have three tools. Use them instead of guessing. You have no knowledge of room availability or building hours except what a tool returns to you.

Rules:
- Never state a room number, a time, or a booking as fact unless a tool told you.
- Before booking, you need the weekday, the room number, and the name to book under. If any is missing, ask the user. Never invent a name.
- Once you have all three details, call book_room immediately. Do not ask the user to confirm first. The system shows them a confirmation button, so asking in chat only delays them.
- Call book_room once per turn, never twice.
- If a tool result starts with "Not done yet", the booking is waiting on the confirmation button. Say the details are ready and ask them to use the button. Do not say it is booked.
- You cannot cancel, move, or look up existing bookings. There is no tool for that. Say so plainly and tell the user to contact the building office.
- If a tool returns an error, tell the user what it said. Do not retry the same call with the same arguments.

Keep answers short and plain."""


def dispatch(name, raw_arguments, allow_write=False):
    """
    Run one tool call and return a string for the model.

    Validates the tool name against the allow list BEFORE any lookup happens,
    so a name the model invented never reaches a function. A tool that changes
    state runs only when allow_write is True, which the interface sets after
    the user clicks confirm. The model cannot set it by asking.
    """
    # The name came from the model, so it is untrusted. Check membership first.
    if name not in AVAILABLE_TOOLS:
        return (
            "Error: there is no tool called '" + str(name) + "'. "
            "The available tools are: " + ", ".join(sorted(AVAILABLE_TOOLS)) + "."
        )

    try:
        arguments = json.loads(raw_arguments)
    except (json.JSONDecodeError, TypeError):
        return "Error: the arguments for " + name + " were not valid JSON. Send them again."

    if not isinstance(arguments, dict):
        return "Error: the arguments for " + name + " must be a JSON object."

    # A prompt rule asking the model to confirm is a request it can ignore.
    # This is the same check in code, where it cannot be talked around.
    if name in WRITE_TOOLS and not allow_write:
        return (
            "Not done yet: " + name + " changes the schedule, so it needs the user to "
            "confirm first. Read these details back to the user and wait: "
            + json.dumps(arguments)
        )

    function = AVAILABLE_TOOLS[name]

    try:
        return function(**arguments)
    except TypeError as error:
        return (
            "Error: " + name + " was called with the wrong arguments (" + str(error) + "). "
            "Check the required fields in the tool schema and try again."
        )
    except Exception as error:
        return "Error: " + name + " failed with " + type(error).__name__ + ": " + str(error) + "."


def pending_write(log):
    """
    Return the arguments of a write tool that was blocked, or None.

    The interface uses this to show a confirm button for exactly the call the
    model asked for, rather than trusting the model to describe it.
    """
    for entry in reversed(log):
        if entry["name"] in WRITE_TOOLS and entry["result"].startswith("Not done yet:"):
            try:
                return json.loads(entry["arguments"])
            except (json.JSONDecodeError, TypeError):
                return None
    return None


def run_agent(client, messages, log, allow_write=False):
    """
    Run the tool calling loop until the model gives a final answer or the cap.

    messages is the running conversation. log is a list this appends a record
    to for every tool call, so the interface can display them. allow_write is
    passed straight through to dispatch and is only True right after the user
    clicked confirm.
    """
    rounds = 0

    while rounds < MAX_ROUNDS:
        rounds += 1

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
        )
        reply = response.choices[0].message

        # No tool calls means the model is answering, so the loop is done.
        if not reply.tool_calls:
            return reply.content or "", messages

        messages.append(
            {
                "role": "assistant",
                "content": reply.content or "",
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in reply.tool_calls
                ],
            }
        )

        for call in reply.tool_calls:
            name = call.function.name
            raw_arguments = call.function.arguments
            result = dispatch(name, raw_arguments, allow_write)

            log.append({"name": name, "arguments": raw_arguments, "result": result})

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": name,
                    "content": result,
                }
            )

    return (
        "I made several attempts and could not finish that. "
        "Try asking for one thing at a time.",
        messages,
    )