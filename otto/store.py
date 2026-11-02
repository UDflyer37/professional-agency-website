from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from otto.db import Connection, Row
from otto.scheduling import BookingRules, DayHours


class SlotTaken(Exception):
    pass


@dataclass(frozen=True)
class NewBooking:
    client_name: str
    client_email: str
    client_phone: str
    reason: str
    starts_at: datetime
    meeting_kind: str = "phone"


@dataclass(frozen=True)
class NewMessage:
    sender_name: str
    sender_email: str
    sender_phone: str
    topic: str
    body: str


def utc_now() -> datetime:
    return datetime.now(UTC)


def week_hours(connection: Connection) -> dict[int, DayHours]:
    rows = connection.execute("SELECT weekday, is_open, opens_at, closes_at FROM office_hours").fetchall()
    return {
        row["weekday"]: DayHours(row["weekday"], row["is_open"], row["opens_at"], row["closes_at"]) for row in rows
    }


def save_week_hours(connection: Connection, week: list[DayHours]) -> None:
    with connection.cursor() as cursor:
        cursor.executemany(
            "UPDATE office_hours SET is_open = %s, opens_at = %s, closes_at = %s WHERE weekday = %s",
            [(day.is_open, day.opens_at, day.closes_at, day.weekday) for day in week],
        )


def booking_rules(connection: Connection) -> BookingRules:
    row = connection.execute("SELECT slot_minutes, days_ahead, per_slot FROM booking_rules WHERE id = 1").fetchone()
    if row is None:
        raise RuntimeError("booking_rules has no row; run `flask --app app init-db` against this database.")
    return BookingRules(row["slot_minutes"], row["days_ahead"], row["per_slot"])


def save_booking_rules(connection: Connection, rules: BookingRules) -> None:
    connection.execute(
        "UPDATE booking_rules SET slot_minutes = %s, days_ahead = %s, per_slot = %s WHERE id = 1",
        (rules.slot_minutes, rules.days_ahead, rules.per_slot),
    )


def taken_slots(connection: Connection, day: date, tz: ZoneInfo) -> Counter[datetime]:
    start = datetime.combine(day, time.min, tzinfo=tz)
    rows = connection.execute(
        "SELECT starts_at FROM bookings WHERE starts_at >= %s AND starts_at < %s",
        (start, start + timedelta(days=1)),
    ).fetchall()
    return Counter(row["starts_at"].astimezone(UTC) for row in rows)


def create_booking(connection: Connection, booking: NewBooking, rules: BookingRules) -> int:
    with connection.transaction():
        # One lock per start time, so two visitors cannot both pass the count check
        # for the same slot. Released automatically at commit or rollback.
        connection.execute("SELECT pg_advisory_xact_lock(%s)", (int(booking.starts_at.timestamp()),))
        row = connection.execute("SELECT count(*) AS n FROM bookings WHERE starts_at = %s", (booking.starts_at,)).fetchone()
        if row is not None and row["n"] >= rules.per_slot:
            raise SlotTaken(booking.starts_at.isoformat())
        created = connection.execute(
            "INSERT INTO bookings (client_name, client_email, client_phone, reason, starts_at, meeting_kind)"
            " VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (
                booking.client_name,
                booking.client_email,
                booking.client_phone,
                booking.reason,
                booking.starts_at,
                booking.meeting_kind,
            ),
        ).fetchone()
    return int(created["id"]) if created else 0


def bookings_between(
    connection: Connection, start: datetime | None, end: datetime | None, *, newest_first: bool = False, limit: int = 500
) -> list[Row]:
    order = "DESC" if newest_first else "ASC"
    return connection.execute(
        "SELECT * FROM bookings"
        " WHERE (%(start)s::timestamptz IS NULL OR starts_at >= %(start)s)"
        " AND (%(end)s::timestamptz IS NULL OR starts_at < %(end)s)"
        f" ORDER BY starts_at {order} LIMIT %(limit)s",
        {"start": start, "end": end, "limit": limit},
    ).fetchall()


def get_booking(connection: Connection, booking_id: int) -> Row | None:
    return connection.execute("SELECT * FROM bookings WHERE id = %s", (booking_id,)).fetchone()


def delete_booking(connection: Connection, booking_id: int) -> None:
    connection.execute("DELETE FROM bookings WHERE id = %s", (booking_id,))


def bookings_due_reminder(connection: Connection, start: datetime, end: datetime) -> list[Row]:
    """Appointments in the window that have not had a reminder text yet."""
    return connection.execute(
        "SELECT * FROM bookings WHERE reminded_at IS NULL AND starts_at >= %s AND starts_at < %s"
        " ORDER BY starts_at",
        (start, end),
    ).fetchall()


def mark_booking_reminded(connection: Connection, booking_id: int) -> None:
    connection.execute("UPDATE bookings SET reminded_at = now() WHERE id = %s", (booking_id,))


def delete_bookings_before(connection: Connection, cutoff: datetime) -> int:
    return connection.execute("DELETE FROM bookings WHERE starts_at < %s", (cutoff,)).rowcount


def create_message(connection: Connection, message: NewMessage) -> int:
    created = connection.execute(
        "INSERT INTO messages (sender_name, sender_email, sender_phone, topic, body)"
        " VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (message.sender_name, message.sender_email, message.sender_phone, message.topic, message.body),
    ).fetchone()
    return int(created["id"]) if created else 0


def list_messages(connection: Connection, limit: int = 300, *, unread_only: bool = False) -> list[Row]:
    where = " WHERE read_at IS NULL" if unread_only else ""
    return connection.execute(
        f"SELECT * FROM messages{where} ORDER BY created_at DESC LIMIT %s", (limit,)
    ).fetchall()


def get_message(connection: Connection, message_id: int) -> Row | None:
    return connection.execute("SELECT * FROM messages WHERE id = %s", (message_id,)).fetchone()


def mark_message_read(connection: Connection, message_id: int) -> None:
    connection.execute("UPDATE messages SET read_at = COALESCE(read_at, now()) WHERE id = %s", (message_id,))


def mark_message_replied(connection: Connection, message_id: int, body: str) -> None:
    connection.execute(
        "UPDATE messages SET reply_body = %s, replied_at = now(), read_at = COALESCE(read_at, now()) WHERE id = %s",
        (body, message_id),
    )


def delete_message(connection: Connection, message_id: int) -> None:
    connection.execute("DELETE FROM messages WHERE id = %s", (message_id,))


def list_faqs(connection: Connection) -> list[Row]:
    return connection.execute("SELECT * FROM faqs ORDER BY position, id").fetchall()


def upsert_faq(connection: Connection, faq_id: int | None, question: str, answer: str, position: int) -> None:
    if faq_id is None:
        connection.execute(
            "INSERT INTO faqs (question, answer, position) VALUES (%s, %s, %s)", (question, answer, position)
        )
    else:
        connection.execute(
            "UPDATE faqs SET question = %s, answer = %s, position = %s WHERE id = %s",
            (question, answer, position, faq_id),
        )


def delete_faq(connection: Connection, faq_id: int) -> None:
    connection.execute("DELETE FROM faqs WHERE id = %s", (faq_id,))


def next_faq_position(connection: Connection) -> int:
    row = connection.execute("SELECT COALESCE(MAX(position), -1) + 1 AS n FROM faqs").fetchone()
    return int(row["n"]) if row else 0


def faq_position(connection: Connection, faq_id: int) -> int:
    row = connection.execute("SELECT position FROM faqs WHERE id = %s", (faq_id,)).fetchone()
    return int(row["position"]) if row else 0


def move_faq(connection: Connection, faq_id: int, direction: int) -> None:
    """Move a question one place and renumber the whole list, so positions never drift."""
    rows = connection.execute("SELECT id FROM faqs ORDER BY position, id").fetchall()
    ids = [row["id"] for row in rows]
    if faq_id not in ids:
        return
    index = ids.index(faq_id)
    target = index + direction
    if not 0 <= target < len(ids):
        return
    ids[index], ids[target] = ids[target], ids[index]
    with connection.cursor() as cursor:
        cursor.executemany("UPDATE faqs SET position = %s WHERE id = %s", [(n, row_id) for n, row_id in enumerate(ids)])


def renumber_faqs(connection: Connection) -> None:
    rows = connection.execute("SELECT id FROM faqs ORDER BY position, id").fetchall()
    with connection.cursor() as cursor:
        cursor.executemany("UPDATE faqs SET position = %s WHERE id = %s", [(n, row["id"]) for n, row in enumerate(rows)])


def list_links(connection: Connection) -> list[Row]:
    return connection.execute("SELECT * FROM links ORDER BY audience, section, title").fetchall()


def create_link(connection: Connection, audience: str, section: str, title: str, url: str) -> None:
    connection.execute(
        "INSERT INTO links (audience, section, title, url) VALUES (%s, %s, %s, %s)", (audience, section, title, url)
    )


def delete_link(connection: Connection, link_id: int) -> None:
    connection.execute("DELETE FROM links WHERE id = %s", (link_id,))


def get_agent_by_email(connection: Connection, email: str) -> Row | None:
    return connection.execute("SELECT * FROM agents WHERE lower(email) = lower(%s)", (email,)).fetchone()


def get_agent(connection: Connection, agent_id: int) -> Row | None:
    return connection.execute("SELECT id, email, name FROM agents WHERE id = %s", (agent_id,)).fetchone()


def upsert_agent(connection: Connection, email: str, name: str, password_hash: str) -> None:
    connection.execute(
        "INSERT INTO agents (email, name, password_hash) VALUES (%s, %s, %s)"
        " ON CONFLICT (lower(email)) DO UPDATE SET name = excluded.name,"
        " password_hash = excluded.password_hash, failed_logins = 0, locked_until = NULL",
        (email, name, password_hash),
    )


def record_login_failure(connection: Connection, agent_id: int, lock_after: int, lock_for: timedelta) -> None:
    connection.execute(
        "UPDATE agents SET"
        " locked_until = CASE WHEN failed_logins + 1 >= %(after)s THEN now() + %(for)s ELSE locked_until END,"
        " failed_logins = CASE WHEN failed_logins + 1 >= %(after)s THEN 0 ELSE failed_logins + 1 END"
        " WHERE id = %(id)s",
        {"after": lock_after, "for": lock_for, "id": agent_id},
    )
    # Commit now: the login view returns an error page, and the lockout must persist regardless.
    connection.commit()


def record_login_success(connection: Connection, agent_id: int) -> None:
    connection.execute("UPDATE agents SET failed_logins = 0, locked_until = NULL WHERE id = %s", (agent_id,))


def count_unread_messages(connection: Connection) -> int:
    row = connection.execute("SELECT count(*) AS n FROM messages WHERE read_at IS NULL").fetchone()
    return int(row["n"]) if row else 0


def list_agents(connection: Connection) -> list[Row]:
    return connection.execute("SELECT id, email, name, created_at FROM agents ORDER BY name").fetchall()


def delete_agent(connection: Connection, agent_id: int) -> None:
    connection.execute("DELETE FROM agents WHERE id = %s", (agent_id,))


def set_agent_password(connection: Connection, agent_id: int, password_hash: str) -> None:
    connection.execute(
        "UPDATE agents SET password_hash = %s, failed_logins = 0, locked_until = NULL WHERE id = %s",
        (password_hash, agent_id),
    )


def list_time_off(connection: Connection, *, from_date: date | None = None) -> list[Row]:
    if from_date is None:
        return connection.execute("SELECT * FROM time_off ORDER BY starts_on").fetchall()
    return connection.execute(
        "SELECT * FROM time_off WHERE ends_on >= %s ORDER BY starts_on", (from_date,)
    ).fetchall()


def time_off_between(connection: Connection, start: date, end: date) -> list[Row]:
    return connection.execute(
        "SELECT * FROM time_off WHERE starts_on <= %s AND ends_on >= %s ORDER BY starts_on", (end, start)
    ).fetchall()


def add_time_off(connection: Connection, starts_on: date, ends_on: date, note: str) -> int:
    row = connection.execute(
        "INSERT INTO time_off (starts_on, ends_on, note) VALUES (%s, %s, %s) RETURNING id",
        (starts_on, ends_on, note),
    ).fetchone()
    return int(row["id"]) if row else 0


def delete_time_off(connection: Connection, time_off_id: int) -> None:
    connection.execute("DELETE FROM time_off WHERE id = %s", (time_off_id,))


def closed_dates(connection: Connection, start: date, end: date) -> set[date]:
    """Every calendar date between start and end that the office is away."""
    days: set[date] = set()
    for row in time_off_between(connection, start, end):
        day = max(row["starts_on"], start)
        last = min(row["ends_on"], end)
        while day <= last:
            days.add(day)
            day += timedelta(days=1)
    return days


# --------------------------------------------------------------------------- notes
NOTE_COLORS = ("gold", "rose", "sky", "mint", "lilac")


def list_notes(connection: Connection) -> list[Row]:
    # Pinned notes come first in both views; within each group, newest edit wins.
    return connection.execute(
        "SELECT * FROM notes ORDER BY pinned DESC, updated_at DESC, id DESC"
    ).fetchall()


def count_notes(connection: Connection) -> int:
    row = connection.execute("SELECT count(*) AS n FROM notes").fetchone()
    return int(row["n"]) if row else 0


def create_note(connection: Connection, body: str, color: str, pos_x: int, pos_y: int) -> int:
    row = connection.execute(
        "INSERT INTO notes (body, color, pos_x, pos_y, z_index)"
        " VALUES (%s, %s, %s, %s, (SELECT coalesce(max(z_index), 0) + 1 FROM notes)) RETURNING id",
        (body, color, max(0, pos_x), max(0, pos_y)),
    ).fetchone()
    return int(row["id"]) if row else 0


def update_note(connection: Connection, note_id: int, body: str, color: str) -> None:
    connection.execute("UPDATE notes SET body = %s, color = %s, updated_at = now() WHERE id = %s", (body, color, note_id))


def move_note(connection: Connection, note_id: int, pos_x: int, pos_y: int, z_index: int) -> None:
    # Moving a note is not an edit, so updated_at (the list order) stays put.
    connection.execute(
        "UPDATE notes SET pos_x = %s, pos_y = %s, z_index = %s WHERE id = %s",
        (max(0, pos_x), max(0, pos_y), z_index, note_id),
    )


def set_note_pinned(connection: Connection, note_id: int, pinned: bool) -> None:
    connection.execute("UPDATE notes SET pinned = %s WHERE id = %s", (pinned, note_id))


def delete_note(connection: Connection, note_id: int) -> None:
    connection.execute("DELETE FROM notes WHERE id = %s", (note_id,))
