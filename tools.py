"""
CSC-128 Assignment 7: the tools and their schemas
Archit Dubey

No Streamlit and no groq imports here, so test_tools.py runs with no API key.
"""

AVAILABILITY = {
    "Monday": ["214", "216", "220"],
    "Tuesday": ["214", "301", "305"],
    "Wednesday": ["216", "220", "301"],
    "Thursday": ["214", "220", "305"],
    "Friday": ["216", "301", "305"],
}

HOURS = {
    "Monday": "8:00 AM to 9:00 PM",
    "Tuesday": "8:00 AM to 9:00 PM",
    "Wednesday": "8:00 AM to 9:00 PM",
    "Thursday": "8:00 AM to 9:00 PM",
    "Friday": "8:00 AM to 5:00 PM",
}

BOOKINGS = []


def normalize_day(day):
    """Return a capitalized weekday name, or None if it is not a weekday we have."""
    if not isinstance(day, str):
        return None
    cleaned = day.strip().capitalize()
    if cleaned in AVAILABILITY:
        return cleaned
    return None


def check_availability(day):
    """Return which rooms are free. Handle a bad day name."""
    name = normalize_day(day)
    if name is None:
        return (
            "I do not have a schedule for '" + str(day) + "'. "
            "Rooms are only bookable Monday through Friday."
        )

    rooms = AVAILABILITY[name]
    if not rooms:
        return "No rooms are free on " + name + "."
    return "Rooms free on " + name + ": " + ", ".join(rooms) + "."


def get_hours(day):
    """Return the opening hours for a weekday."""
    name = normalize_day(day)
    if name is None:
        return (
            "I do not have hours for '" + str(day) + "'. "
            "The building is only open Monday through Friday."
        )
    return name + " hours are " + HOURS[name] + "."


def book_room(day, room, name):
    """
    Reserve a room and remove it from availability.

    This function can only add a booking. It cannot cancel one, move one,
    look up who booked a room, or change the hours. See the README.
    """
    weekday = normalize_day(day)
    if weekday is None:
        return (
            "I cannot book '" + str(day) + "'. "
            "Rooms are only bookable Monday through Friday."
        )

    room = str(room).strip()
    if room not in AVAILABILITY[weekday]:
        free = AVAILABILITY[weekday]
        if not free:
            return "Room " + room + " is not free on " + weekday + ", and nothing else is either."
        return (
            "Room " + room + " is not free on " + weekday + ". "
            "These are: " + ", ".join(free) + "."
        )

    name = str(name).strip()
    if not name:
        return "I need a name to put the booking under."

    AVAILABILITY[weekday].remove(room)
    BOOKINGS.append({"day": weekday, "room": room, "name": name})
    return "Booked room " + room + " on " + weekday + " for " + name + "."


AVAILABLE_TOOLS = {
    "check_availability": check_availability,
    "get_hours": get_hours,
    "book_room": book_room,
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": (
                "Call this when the user asks which rooms are free, whether a "
                "specific room is open, or what is available on a given weekday. "
                "Call it before booking anything, so you know the room is actually "
                "free. Do not call it for questions about opening and closing times, "
                "which is a different tool."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "day": {
                        "type": "string",
                        "description": "A weekday name, Monday through Friday.",
                    }
                },
                "required": ["day"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_hours",
            "description": (
                "Call this only when the user asks what time the building opens or "
                "closes on a given weekday. This tool knows nothing about rooms or "
                "bookings. If the user asks what is free or available, use "
                "check_availability instead."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "day": {
                        "type": "string",
                        "description": "A weekday name, Monday through Friday.",
                    }
                },
                "required": ["day"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_room",
            "description": (
                "Call this to actually reserve a room. This changes the schedule and "
                "cannot be undone, so only call it once you have the weekday, the room "
                "number, and the name to book under, and the user has confirmed those "
                "details. If any of the three is missing, ask the user for it instead "
                "of guessing. Never invent a name."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "day": {
                        "type": "string",
                        "description": "A weekday name, Monday through Friday.",
                    },
                    "room": {
                        "type": "string",
                        "description": "The room number, for example 214.",
                    },
                    "name": {
                        "type": "string",
                        "description": "The name to put the booking under, given by the user.",
                    },
                },
                "required": ["day", "room", "name"],
            },
        },
    },
]