"""Text-message helpers: new bookings, new requests and appointment reminders.

Everything here is additive. If the owner has not switched texts on, or the Twilio
settings are missing, these functions do nothing and the site behaves exactly as
before. A failed text never blocks a booking or a request.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from otto import site, sms, store
from otto.db import Connection

# The words an owner can use inside a text template. Anything else is a typo, so the
# portal refuses to save it rather than sending a half-empty message.
PLACEHOLDERS = {
    "sms_booking_template": {"name", "when", "kind"},
    "sms_request_template": {"name", "topic"},
    "sms_reminder_template": {"name", "when", "kind"},
}
_PLACEHOLDER = re.compile(r"\{([a-z_]+)\}")


def settings(connection: Connection) -> dict[str, object]:
    return site.get_setting(connection, "notify")


def template_problem(text: str, field: str) -> str:
    """Explain the first thing wrong with a template, or return an empty string."""
    if not text.strip():
        return "Write the message, or use the default."
    allowed = PLACEHOLDERS.get(field, set())
    unknown = sorted({name for name in _PLACEHOLDER.findall(text)} - allowed)
    if unknown:
        return f"These are not words this message understands: {', '.join('{' + name + '}' for name in unknown)}."
    # A stray brace would break the send, so check that it formats cleanly.
    try:
        text.format_map({"name": "Mary K.", "when": "Tue Nov 4 at 3:00 pm", "kind": "phone call", "topic": "a quote"})
    except (KeyError, IndexError, ValueError):
        return "Check the curly brackets: every one needs a word from the list and a matching closing bracket."
    return ""


def render(text: str, fallback: str, **values: str) -> str:
    try:
        body = text.format(**values)
    except (KeyError, IndexError, ValueError):
        body = fallback.format(**values)
    return " ".join(body.split())[:480]


def _target(connection: Connection) -> tuple[str, dict[str, object]]:
    values = settings(connection)
    if not values.get("sms_enabled"):
        return "", values
    return sms.to_e164(str(values.get("sms_phone") or "")), values


def new_booking(connection: Connection, texter: sms.Texter, name: str, when: str, kind: str) -> bool:
    phone, values = _target(connection)
    if not phone or not values.get("sms_on_booking"):
        return False
    body = render(
        str(values.get("sms_booking_template") or ""),
        "New appointment: {name}, {when} ({kind}).",
        name=name,
        when=when,
        kind=kind.lower(),
    )
    return sms.send_quietly(texter, phone, body)


def new_request(connection: Connection, texter: sms.Texter, name: str, topic: str) -> bool:
    phone, values = _target(connection)
    if not phone or not values.get("sms_on_request"):
        return False
    body = render(
        str(values.get("sms_request_template") or ""),
        "New website request: {name} asked about {topic}.",
        name=name,
        topic=topic.lower(),
    )
    return sms.send_quietly(texter, phone, body)


def test_message(connection: Connection, texter: sms.Texter) -> tuple[bool, str]:
    phone, _ = _target(connection)
    if not phone:
        return False, "Add the mobile number and switch texts on first."
    ok = sms.send_quietly(texter, phone, "Otto & Associates: texts are working. This is a test.")
    return ok, phone


def reminder_window(hours: int) -> tuple[datetime, datetime]:
    now = store.utc_now()
    return now, now + timedelta(hours=max(1, min(72, hours)))


def send_due_reminders(
    connection: Connection,
    texter: sms.Texter,
    tz: ZoneInfo,
    *,
    hours: int,
    kinds: dict[str, str],
) -> tuple[int, int]:
    """Text the owner about appointments in the next `hours`. Returns (sent, failed)."""
    phone, values = _target(connection)
    if not phone:
        return 0, 0
    start, end = reminder_window(hours)
    sent = failed = 0
    template = str(values.get("sms_reminder_template") or "")
    for booking in store.bookings_due_reminder(connection, start, end):
        when = booking["starts_at"].astimezone(tz).strftime("%a %b %-d at %-I:%M %p")
        body = render(
            template,
            "Otto & Associates: {name} is booked {when} ({kind}). Reply to this text or call the office to change it.",
            name=booking["client_name"],
            when=when,
            kind=kinds.get(booking["meeting_kind"], "call"),
        )
        if sms.send_quietly(texter, phone, body):
            store.mark_booking_reminded(connection, booking["id"])
            sent += 1
        else:
            failed += 1
    return sent, failed
