from datetime import datetime

from flask import request


def normalize_field(value):
    if value is None:
        return ""
    value = " ".join(value.strip().upper().split())
    replaces = {
        'm': 'м',
        'e': 'е',
        'sk': 'ск',
        'c': 'с'
    }
    for k, v in replaces.items():
        value = value.replace(k.upper(), v)
    return value.upper()


def normalize_note(value):
    if value is None:
        return None

    note = " ".join(value.strip().split())
    return note or None


def parse_ride_datetime(value):
    value = (value or "").strip()
    if not value:
        raise ValueError("empty datetime")

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError("invalid datetime") from error

    return parsed.replace(microsecond=0).isoformat()


def wants_json_response():
    return (
        request.headers.get("X-Requested-With") == "fetch"
        or request.accept_mimetypes.best == "application/json"
    )


def serialize_ride(ride):
    return {
        "id": ride["id"],
        "route_number": ride["route_number"],
        "bus_number": ride["bus_number"],
        "note": ride["note"],
        "ridden_at": ride["ridden_at"],
    }


def format_profile_day(value):
    try:
        day = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return value

    if day.year == datetime.now().year:
        return day.strftime("%d.%m")
    return day.strftime("%d.%m.%Y")


def format_datetime_local(value):
    try:
        return datetime.fromisoformat(value).strftime("%Y-%m-%dT%H:%M")
    except (TypeError, ValueError):
        return ""


def pluralize(value, one, few, many):
    return f"{value} {plural_word(value, one, few, many)}"


def plural_word(value, one, few, many):
    try:
        number = abs(int(value))
    except (TypeError, ValueError):
        number = 0

    last_two = number % 100
    last = number % 10

    if 11 <= last_two <= 14:
        word = many
    elif last == 1:
        word = one
    elif 2 <= last <= 4:
        word = few
    else:
        word = many

    return word