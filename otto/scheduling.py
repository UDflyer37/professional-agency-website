from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

WEEKDAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


@dataclass(frozen=True)
class DayHours:
    weekday: int
    is_open: bool
    opens_at: time
    closes_at: time


@dataclass(frozen=True)
class BookingRules:
    slot_minutes: int
    days_ahead: int
    per_slot: int


@dataclass(frozen=True)
class OfficeStatus:
    is_open: bool
    summary: str


def parse_clock(value: str) -> time:
    try:
        return time.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Expected a time like 09:30, got {value!r}") from exc


def format_clock(moment: time | datetime) -> str:
    hour = moment.hour % 12 or 12
    suffix = "am" if moment.hour < 12 else "pm"
    return f"{hour}:{moment.minute:02d} {suffix}"


def bookable_window(today: date, rules: BookingRules) -> tuple[date, date]:
    return today, today + timedelta(days=rules.days_ahead)


def open_slots(
    day: date,
    hours: DayHours,
    rules: BookingRules,
    taken: Counter[datetime],
    now: datetime,
    tz: ZoneInfo,
    closed: frozenset[date] | set[date] = frozenset(),
) -> list[datetime]:
    """Return the free appointment start times on `day`, as aware datetimes in `tz`.

    `taken` counts existing bookings by their UTC start time. `closed` holds days the
    agents marked as time off in the portal, which never offer a slot.
    """
    if day in closed:
        return []
    if not hours.is_open or day.weekday() != hours.weekday:
        return []

    opens = datetime.combine(day, hours.opens_at, tzinfo=tz)
    closes = datetime.combine(day, hours.closes_at, tzinfo=tz)
    step = timedelta(minutes=rules.slot_minutes)
    earliest = now.astimezone(tz)

    slots: list[datetime] = []
    start = opens
    # The last slot must finish by closing time, not merely start before it.
    while start + step <= closes:
        if start > earliest and taken[start.astimezone(UTC)] < rules.per_slot:
            slots.append(start)
        start += step
    return slots


def office_status(
    now: datetime, week: dict[int, DayHours], tz: ZoneInfo, *, away_today: bool = False
) -> OfficeStatus:
    local = now.astimezone(tz)
    if away_today:
        return OfficeStatus(False, "Away today, call and we will get back to you")
    today = week.get(local.weekday())

    if today and today.is_open and today.opens_at <= local.time() < today.closes_at:
        return OfficeStatus(True, f"Open now, until {format_clock(today.closes_at)}")

    if today and today.is_open and local.time() < today.opens_at:
        return OfficeStatus(False, f"Closed now, opens today at {format_clock(today.opens_at)}")

    for offset in range(1, 8):
        candidate = week.get((local.weekday() + offset) % 7)
        if candidate and candidate.is_open:
            day_name = "tomorrow" if offset == 1 else WEEKDAY_NAMES[candidate.weekday]
            return OfficeStatus(False, f"Closed now, opens {day_name} at {format_clock(candidate.opens_at)}")

    return OfficeStatus(False, "Closed now, call to arrange a time")
