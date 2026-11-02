from collections import Counter
from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

from otto.scheduling import BookingRules, DayHours, format_clock, office_status, open_slots

EASTERN = ZoneInfo("America/New_York")
MONDAY = date(2026, 11, 2)
WEEKDAY_HOURS = DayHours(0, True, time(9, 30), time(17, 0))
RULES = BookingRules(slot_minutes=30, days_ahead=30, per_slot=1)
WEEK = {d: DayHours(d, d < 5, time(9, 30), time(17, 0)) for d in range(7)}
LONG_AGO = datetime(2026, 1, 1, tzinfo=UTC)


def test_slots_cover_the_day_and_end_by_closing_time() -> None:
    slots = open_slots(MONDAY, WEEKDAY_HOURS, RULES, Counter(), LONG_AGO, EASTERN)
    assert slots[0].time() == time(9, 30)
    assert slots[-1].time() == time(16, 30)
    assert len(slots) == 15


def test_booked_slot_is_removed_once_full() -> None:
    taken_start = datetime.combine(MONDAY, time(10, 0), tzinfo=EASTERN).astimezone(UTC)
    slots = open_slots(MONDAY, WEEKDAY_HOURS, RULES, Counter({taken_start: 1}), LONG_AGO, EASTERN)
    assert time(10, 0) not in [slot.time() for slot in slots]


def test_slot_stays_open_until_per_slot_limit_is_reached() -> None:
    taken_start = datetime.combine(MONDAY, time(10, 0), tzinfo=EASTERN).astimezone(UTC)
    rules = BookingRules(slot_minutes=30, days_ahead=30, per_slot=2)
    slots = open_slots(MONDAY, WEEKDAY_HOURS, rules, Counter({taken_start: 1}), LONG_AGO, EASTERN)
    assert time(10, 0) in [slot.time() for slot in slots]


def test_past_times_are_not_offered() -> None:
    lunchtime = datetime.combine(MONDAY, time(12, 5), tzinfo=EASTERN)
    slots = open_slots(MONDAY, WEEKDAY_HOURS, RULES, Counter(), lunchtime, EASTERN)
    assert slots[0].time() == time(12, 30)


def test_closed_day_has_no_slots() -> None:
    saturday = date(2026, 11, 7)
    assert open_slots(saturday, WEEK[5], RULES, Counter(), LONG_AGO, EASTERN) == []


def test_office_status_during_hours() -> None:
    status = office_status(datetime.combine(MONDAY, time(11, 0), tzinfo=EASTERN), WEEK, EASTERN)
    assert status.is_open
    assert status.summary == "Open now, until 5:00 pm"


def test_office_status_friday_evening_points_to_monday() -> None:
    friday_evening = datetime(2026, 11, 6, 18, 0, tzinfo=EASTERN)
    status = office_status(friday_evening, WEEK, EASTERN)
    assert not status.is_open
    assert status.summary == "Closed now, opens Monday at 9:30 am"


def test_office_status_early_morning() -> None:
    status = office_status(datetime.combine(MONDAY, time(8, 0), tzinfo=EASTERN), WEEK, EASTERN)
    assert status.summary == "Closed now, opens today at 9:30 am"


def test_format_clock() -> None:
    assert format_clock(time(0, 15)) == "12:15 am"
    assert format_clock(time(17, 0)) == "5:00 pm"
