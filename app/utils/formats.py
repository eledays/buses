from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from flask import request

LOCAL_TZ = ZoneInfo("Europe/Moscow")
MAX_ROUTE_LENGTH = 16
MAX_BUS_LENGTH = 32
MAX_NOTE_LENGTH = 240


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


def validate_ride_fields(route_number, bus_number, note):
    if not route_number or not bus_number:
        return "Заполни маршрут и серийный номер автобуса."
    if len(route_number) > MAX_ROUTE_LENGTH:
        return f"Маршрут не должен быть длиннее {MAX_ROUTE_LENGTH} символов."
    if len(bus_number) > MAX_BUS_LENGTH:
        return f"Серийный номер не должен быть длиннее {MAX_BUS_LENGTH} символов."
    if note and len(note) > MAX_NOTE_LENGTH:
        return f"Заметка не должна быть длиннее {MAX_NOTE_LENGTH} символов."
    return None


def parse_ride_datetime(value):
    value = (value or "").strip()
    if not value:
        raise ValueError("empty datetime")

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError("invalid datetime") from error

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=LOCAL_TZ)

    return parsed.astimezone(UTC).replace(microsecond=0).isoformat()


def parse_stored_datetime(value):
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


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
        "ridden_at_display": format_datetime_local(ride["ridden_at"]),
        "ridden_at_input": format_datetime_input(ride["ridden_at"]),
    }


def format_profile_day(value):
    try:
        day = parse_stored_datetime(value).astimezone(LOCAL_TZ)
    except (TypeError, ValueError):
        return value

    if day.year == datetime.now(LOCAL_TZ).year:
        return day.strftime("%d.%m")
    return day.strftime("%d.%m.%Y")


def format_datetime_local(value):
    try:
        dt = parse_stored_datetime(value).astimezone(LOCAL_TZ)
        return dt.strftime("%d.%m.%Y %H:%M")
    except (TypeError, ValueError):
        return ""


def format_datetime_input(value):
    try:
        dt = parse_stored_datetime(value).astimezone(LOCAL_TZ)
        return dt.strftime("%Y-%m-%dT%H:%M")
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
