"""
CSC-128 Assignment 7: tests for the tools and the dispatch guard
Archit Dubey

Run:  python test_tools.py

No API key is needed. Tool functions and the dispatch guard are ordinary
deterministic Python, which is exactly the part of an agent you can unit test.
"""
import json

import tools
from agent import dispatch
from tools import (
    AVAILABILITY,
    AVAILABLE_TOOLS,
    BOOKINGS,
    book_room,
    check_availability,
    get_hours,
    normalize_day,
)


def fresh_state():
    """Reset the module state so each run starts from the same place."""
    tools.AVAILABILITY["Monday"] = ["214", "216", "220"]
    tools.AVAILABILITY["Tuesday"] = ["214", "301", "305"]
    tools.AVAILABILITY["Wednesday"] = ["216", "220", "301"]
    tools.AVAILABILITY["Thursday"] = ["214", "220", "305"]
    tools.AVAILABILITY["Friday"] = ["216", "301", "305"]
    tools.BOOKINGS.clear()


def build_cases():
    cases = []
    fresh_state()

    # --- normalize_day ---
    cases.append(("lowercase day is accepted", normalize_day("monday"), "Monday"))
    cases.append(("day with spaces is accepted", normalize_day("  friday "), "Friday"))
    cases.append(("weekend is rejected", normalize_day("Saturday"), None))
    cases.append(("nonsense is rejected", normalize_day("blursday"), None))
    cases.append(("a number does not crash", normalize_day(7), None))

    # --- check_availability ---
    cases.append((
        "availability lists the free rooms",
        check_availability("Monday"),
        "Rooms free on Monday: 214, 216, 220.",
    ))
    cases.append((
        "availability is case insensitive",
        check_availability("monday"),
        "Rooms free on Monday: 214, 216, 220.",
    ))
    cases.append((
        "a bad day returns a message, not an exception",
        "Monday through Friday" in check_availability("Caturday"),
        True,
    ))

    # --- get_hours ---
    cases.append((
        "hours for a normal day",
        get_hours("Tuesday"),
        "Tuesday hours are 8:00 AM to 9:00 PM.",
    ))
    cases.append((
        "friday closes earlier",
        get_hours("friday"),
        "Friday hours are 8:00 AM to 5:00 PM.",
    ))
    cases.append((
        "a bad day returns a message for hours too",
        "Monday through Friday" in get_hours("Sunday"),
        True,
    ))

    # --- book_room, the state changing tool ---
    fresh_state()
    cases.append((
        "booking a free room succeeds",
        book_room("Monday", "214", "Archit"),
        "Booked room 214 on Monday for Archit.",
    ))
    cases.append((
        "the booked room is no longer available",
        "214" in tools.AVAILABILITY["Monday"],
        False,
    ))
    cases.append((
        "the booking was recorded",
        tools.BOOKINGS[0],
        {"day": "Monday", "room": "214", "name": "Archit"},
    ))
    cases.append((
        "the same room cannot be booked twice",
        "not free" in book_room("Monday", "214", "Someone Else"),
        True,
    ))
    cases.append((
        "a double booking did not add a second record",
        len(tools.BOOKINGS),
        1,
    ))

    fresh_state()
    cases.append((
        "a room that does not exist is refused",
        "not free" in book_room("Monday", "999", "Archit"),
        True,
    ))
    cases.append((
        "an empty name is refused",
        book_room("Monday", "216", "   "),
        "I need a name to put the booking under.",
    ))
    cases.append((
        "a refused booking changed nothing",
        "216" in tools.AVAILABILITY["Monday"],
        True,
    ))
    cases.append((
        "a weekend booking is refused",
        "Monday through Friday" in book_room("Saturday", "214", "Archit"),
        True,
    ))

    # --- the dispatch guard ---
    # This is the security model of tool calling. The name comes from the
    # model, so it is untrusted input choosing which function runs.
    fresh_state()
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
    cases.append((
        "GUARD: a python builtin name is rejected",
        "no tool called" in dispatch("print", '{"x": 1}'),
        True,
    ))
    cases.append((
        "GUARD: an empty name is rejected",
        "no tool called" in dispatch("", "{}"),
        True,
    ))

    # --- malformed arguments ---
    cases.append((
        "malformed JSON is reported, not raised",
        "not valid JSON" in dispatch("get_hours", "{day: Monday"),
        True,
    ))
    cases.append((
        "a JSON list instead of an object is rejected",
        "must be a JSON object" in dispatch("get_hours", '["Monday"]'),
        True,
    ))
    cases.append((
        "a wrong argument name is reported, not raised",
        "wrong arguments" in dispatch("get_hours", '{"weekday": "Monday"}'),
        True,
    ))
    cases.append((
        "a missing required argument is reported",
        "wrong arguments" in dispatch("book_room", '{"day": "Monday"}'),
        True,
    ))

    # --- dispatch on the happy path ---
    fresh_state()
    cases.append((
        "a valid call runs the real function",
        dispatch("get_hours", '{"day": "Monday"}'),
        "Monday hours are 8:00 AM to 9:00 PM.",
    ))
    cases.append((
        "dispatch can run the write tool",
        dispatch("book_room", '{"day": "Tuesday", "room": "301", "name": "Archit"}'),
        "Booked room 301 on Tuesday for Archit.",
    ))
    cases.append((
        "the write tool changed state through dispatch",
        "301" in tools.AVAILABILITY["Tuesday"],
        False,
    ))

    # --- the tool table and the schemas agree ---
    schema_names = sorted(s["function"]["name"] for s in tools.TOOL_SCHEMAS)
    cases.append((
        "every schema has a matching function",
        schema_names,
        sorted(AVAILABLE_TOOLS),
    ))
    cases.append(("there are three tools", len(AVAILABLE_TOOLS), 3))
    cases.append((
        "no tool is named like a delete",
        [n for n in AVAILABLE_TOOLS if "delete" in n or "cancel" in n or "remove" in n],
        [],
    ))

    return cases


def run_tests():
    cases = build_cases()
    passed = 0
    failed = 0

    for name, actual, expected in cases:
        if actual == expected:
            passed += 1
        else:
            failed += 1
            print("FAILED:", name)
            print("  expected:", expected)
            print("  actual:  ", actual)
            print()

    print("-" * 60)
    print("Passed:", passed)
    print("Failed:", failed)
    print("Total: ", passed + failed)


if __name__ == "__main__":
    run_tests()