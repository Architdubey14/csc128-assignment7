# Room Booking Agent

CSC-128 Assignment 7

Archit Dubey

## Overview

A Streamlit agent that does something rather than just talking about doing something. It has three tools, two for querying (check which rooms are free, check the building hours) and one for updating state (book a room). The model chooses which tool to call and with what arguments; it is my code that decides whether or not the call is allowed to proceed.

## How to run it

1. Open a terminal within the assignment directory.
2. Activate the virtual environment.
3. `pip install -r requirements.txt`
4. Put your Groq key in `.streamlit/secrets.toml` as `GROQ_API_KEY = "..."`.
5. `streamlit run app.py`

To run the tests: `python test_tools.py`. They require no API key, since the tool functions and the dispatch guard are just ordinary deterministic Python.

The model is `openai/gpt-oss-20b`. The assignment suggests `llama-3.3-70b-versatile`, but that model is not available on my Groq account. I listed the models I have and confirmed `openai/gpt-oss-20b` supports tool calling before building anything on it.

## The function I did not write

`cancel_booking`. There is no tool to cancel, move, or look up an existing booking, and that is deliberate.

The model is what decides when a tool gets called, based on its reading of a sentence a user typed. It is wrong sometimes. With a cancel tool in the table, a message the model misread as a cancellation could delete a reservation belonging to someone who is not even in the conversation. There is no undo, nothing in my data records who booked what beyond a name string, and the person who lost their room would find out when they showed up to a room someone else was using.

A system prompt saying "never cancel a booking" would not fix this. A prompt is a request, and I watched the model ignore a prompt rule in this same assignment (see the rewritten description below). A function that was never written cannot be called by any prompt, any phrasing, or any jailbreak, because there is nothing to call.

For the same reason there is no `list_bookings`, which would hand out other people's names, and no tool that edits `HOURS`.

`book_room` is the only tool that changes anything, and all it can do is append. It cannot overwrite an existing booking, because it refuses any room that is not currently free.

## What happens when the model requests a tool that does not exist

`dispatch()` in `agent.py` checks the tool name against the allow list before anything else happens:

```python
if name not in AVAILABLE_TOOLS:
    return (
        "Error: there is no tool called '" + str(name) + "'. "
        "The available tools are: " + ", ".join(sorted(AVAILABLE_TOOLS)) + "."
    )
```

That check is the first statement in the function. It runs before the arguments are parsed and before any dictionary lookup, so an invented name never reaches a function at all. The error string goes back to the model as a tool result, so the conversation keeps going and the model can tell the user what it cannot do.

Three tests in `test_tools.py` prove it, and the third is the one that matters:

```python
cases.append((
    "GUARD: an invented tool name is rejected",
    "no tool called" in dispatch("delete_booking", '{"room": "214"}'),
    True,
))
cases.append((
    "GUARD: the rejection names the tools that do exist",
    "check_availability" in dispatch("delete_booking", '{"room": "214"}'),
    True,
))
cases.append((
    "GUARD: an invented tool executes nothing",
    tools.AVAILABILITY["Monday"],
    ["214", "216", "220"],
))
```

The first two check that an error comes back. The third checks the schedule immediately after dispatching a fake `delete_booking` and confirms nothing changed. An error message alone would not prove the guard worked, only that something was returned.

There are also tests for a Python builtin name (`print`) and an empty string, since both are things a confused model could produce.

All 35 tests pass.

## The description I had to rewrite

This one is about the confirmation step rather than a tool being called at the wrong time, and the rewrite was prompted by watching the model do real damage.

### Version 1

The `book_room` schema description and the system prompt both told the model to confirm first:

```
"Call this to actually reserve a room. This changes the schedule and cannot be
undone, so only call it once you have the weekday, the room number, and the name
to book under, and the user has confirmed those details."
```

```
- Booking changes the schedule and cannot be undone. Read the three details back
  to the user and get a clear yes before you call book_room.
```

What actually happened: I asked it to book room 214 on Monday for Archit. The reply was:

> You want to book room 214 on Monday for Archit, correct?

and in the same turn, the tool log showed `book_room` had already run and the room was gone. It asked for confirmation and booked it simultaneously. My "yes" afterwards did nothing, because there was nothing left to confirm.

This is the point the assignment makes about the delete function, in a different shape. A prompt instruction is a request. The model can ignore it, and it did.

### Version 2

I moved the confirmation into code. `dispatch()` takes an `allow_write` flag that defaults to `False`, and `book_room` is in a `WRITE_TOOLS` set:

```python
if name in WRITE_TOOLS and not allow_write:
    return (
        "Not done yet: " + name + " changes the schedule, so it needs the user to "
        "confirm first. Read these details back to the user and wait: "
        + json.dumps(arguments)
    )
```

The model can request `book_room` as many times as it likes and nothing happens. Only the confirm button in the interface passes `allow_write=True`.

With the gate in code, the prompt no longer needed to ask for confirmation, so it was rewritten to describe what the system does instead:

```
- Once you have all three details, call book_room immediately. Do not ask the user
  to confirm first. The system shows them a confirmation button, so asking in chat
  only delays them.
- Call book_room once per turn, never twice.
- If a tool result starts with "Not done yet", the booking is waiting on the
  confirmation button. Say the details are ready and ask them to use the button.
  Do not say it is booked.
```

One more thing broke after that. Clicking confirm originally sent "Yes, I confirm" back to the model and re-ran the loop with `allow_write=True`, hoping the model would request the tool again. It did not. It replied in prose saying the booking was confirmed, while the schedule showed the room still free. The bot told me I had a room I did not have, which is worse than refusing.

The fix was to stop asking the model at all on confirmation. The blocked arguments are already known, so the button calls `dispatch()` directly with exactly those arguments:

```python
result = dispatch("book_room", json.dumps(details), allow_write=True)
```

No model round trip between the user agreeing and the booking happening, so nothing can change in between.

## What the interface shows

Every tool call appears under the reply that produced it, with the tool name, the arguments the model sent as JSON, and the string my code returned. The sidebar shows the live schedule and the bookings made, so a booking can be seen to actually take effect rather than just being claimed.

## What I would fix with more time

State lives in module level lists in `tools.py`, so everything resets when the app restarts and two people running it would not see each other's bookings. A real version needs a database, which also means `book_room` would need to handle two people booking the same room at the same moment.

The iteration cap is five rounds and the message when it runs out is generic. It would be better to tell the user which tools were tried.

The confirm button only exists for `book_room`. If a second write tool were added, the `pending_write` logic would need to handle more than one blocked call at a time rather than taking the most recent.

A booking is stored under a name string with nothing verifying it. Anyone can book under any name, and there is no way to prove a booking is yours. That is fine for an assignment and would not be fine anywhere else.