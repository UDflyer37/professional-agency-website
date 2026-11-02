from __future__ import annotations

import csv
import io
import json
import re
import secrets
from datetime import UTC, date as date_type, datetime, time as clock_time, timedelta
from urllib.parse import urlparse

from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.wrappers.response import Response

from otto import content, notify, store
from otto import site as site_content
from otto.config import Settings
from otto.db import get_db
from otto.mailer import Email, Mailer, send_quietly
from otto.scheduling import WEEKDAY_NAMES, BookingRules, DayHours, format_clock, parse_clock
from otto.security import login_required
from otto.validation import EMAIL_PATTERN, clean_block, clean_text, parse_iso_date, safe_link

bp = Blueprint("portal", __name__, url_prefix="/portal")

LOCK_AFTER_FAILURES = 5
LOCK_DURATION = timedelta(minutes=15)
# Checked against when the email is unknown, so a wrong email and a wrong password take the same time.
_DUMMY_HASH = generate_password_hash(secrets.token_hex(16))


def _settings() -> Settings:
    return current_app.config["OTTO"]


def _mailer() -> Mailer:
    return current_app.extensions["otto_mailer"]


def _texter():
    return current_app.extensions["otto_texter"]


def _same_site_path(target: str | None) -> str:
    if target and target.startswith("/") and not target.startswith("//") and not urlparse(target).netloc:
        return target
    return url_for("portal.dashboard")


def _local(moment: datetime | None) -> str:
    return moment.astimezone(_settings().timezone).strftime("%Y-%m-%d %H:%M") if moment else ""


def _csv_cell(value: object) -> object:
    """Stop a spreadsheet treating a visitor's text as a formula."""
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + value
    return value


def _csv_response(rows: list[dict[str, object]], columns: list[tuple[str, str]], filename: str) -> Response:
    """A spreadsheet the owner can open in Excel or Numbers, with a byte-order mark for accents."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([label for _, label in columns])
    for row in rows:
        writer.writerow(["" if row.get(key) is None else _csv_cell(row.get(key)) for key, _ in columns])
    response = Response("\ufeff" + buffer.getvalue(), content_type="text/csv; charset=utf-8")
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@bp.route("/login", methods=["GET", "POST"])
def login() -> str | Response | tuple[str, int]:
    if g.get("agent") is not None:
        return redirect(url_for("portal.dashboard"))

    error = ""
    if request.method == "POST":
        connection = get_db()
        email = clean_text(request.form, "email", max_length=254).lower()
        password = request.form.get("password", "")
        agent = store.get_agent_by_email(connection, email)

        locked_until = agent["locked_until"] if agent else None
        if locked_until and locked_until > store.utc_now():
            error = "Too many attempts. Try again in a few minutes."
        elif agent and check_password_hash(agent["password_hash"], password):
            store.record_login_success(connection, agent["id"])
            next_path = _same_site_path(request.args.get("next"))
            session.clear()
            session["agent_id"] = agent["id"]
            session.permanent = True
            return redirect(next_path)
        else:
            if agent:
                store.record_login_failure(connection, agent["id"], LOCK_AFTER_FAILURES, LOCK_DURATION)
            else:
                check_password_hash(_DUMMY_HASH, password)
            error = "That email and password do not match."

    return render_template("portal/login.html", error=error), (401 if error else 200)


@bp.post("/logout")
def logout() -> Response:
    session.clear()
    return redirect(url_for("public.home"))


@bp.get("/")
@login_required
def dashboard() -> str:
    connection = get_db()
    now = store.utc_now()
    tz = _settings().timezone
    today_end = (now.astimezone(tz).replace(hour=23, minute=59, second=59)).astimezone(UTC)
    upcoming = store.bookings_between(connection, now, None, limit=6)
    return render_template(
        "portal/dashboard.html",
        upcoming=upcoming,
        today_count=sum(1 for booking in upcoming if booking["starts_at"] <= today_end),
        unread=store.count_unread_messages(connection),
        latest_messages=store.list_messages(connection, limit=4),
        meeting_kinds=content.MEETING_KINDS,
        announcement=site_content.get_setting(connection, "announcement"),
        greeting="Good morning" if now.astimezone(tz).hour < 12 else "Good afternoon" if now.astimezone(tz).hour < 17 else "Good evening",
    )


def _calendar(connection, view: str, anchor: str | None) -> dict[str, object]:
    """Month, week or day view of the appointment book, in the office's timezone.

    Everything is worked out on the server so the calendar still reads correctly
    with JavaScript off and no appointment can be hidden by a timezone bug.
    """
    tz = _settings().timezone
    today = store.utc_now().astimezone(tz).date()
    view = view if view in {"month", "week", "day"} else "month"
    try:
        focus = date_type.fromisoformat(anchor) if anchor else today
    except ValueError:
        focus = today

    if view == "month":
        first = focus.replace(day=1)
        last = (first + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        start = first - timedelta(days=first.weekday())
        # Only as many weeks as the month actually needs, never a stray sixth row.
        end = start + timedelta(days=((last - start).days // 7 + 1) * 7)
        previous = first - timedelta(days=1)
        following = (first + timedelta(days=32)).replace(day=1)
        label = first.strftime("%B %Y")
    elif view == "week":
        start = focus - timedelta(days=focus.weekday())
        end = start + timedelta(days=7)
        previous = start - timedelta(days=7)
        following = start + timedelta(days=7)
        label = f"{start.strftime('%b %-d')} – {(end - timedelta(days=1)).strftime('%b %-d, %Y')}"
    else:
        start = focus
        end = focus + timedelta(days=1)
        previous = start - timedelta(days=1)
        following = start + timedelta(days=1)
        label = focus.strftime("%A, %B %-d")

    start_dt = datetime.combine(start, clock_time.min, tzinfo=tz)
    end_dt = datetime.combine(end, clock_time.min, tzinfo=tz)
    booked: dict[date_type, list[dict[str, object]]] = {}
    for booking in store.bookings_between(connection, start_dt, end_dt, limit=1000):
        local = booking["starts_at"].astimezone(tz)
        booked.setdefault(local.date(), []).append(
            {
                "id": booking["id"],
                "time": local.strftime("%-I:%M %p"),
                "name": booking["client_name"],
                "kind": content.MEETING_KINDS.get(booking["meeting_kind"], booking["meeting_kind"]),
            }
        )

    days = [start + timedelta(days=offset) for offset in range((end - start).days)]
    return {
        "view": view,
        "today": today,
        "focus": focus,
        "month": focus.month,
        "label": label,
        "start": start,
        "end": end - timedelta(days=1),
        "previous": previous.isoformat(),
        "following": following.isoformat(),
        "days": days,
        "booked": booked,
        "away": store.closed_dates(connection, start, end),
        "weekday_names": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    }


@bp.get("/appointments")
@login_required
def bookings() -> str:
    connection = get_db()
    now = store.utc_now()
    return render_template(
        "portal/bookings.html",
        upcoming=store.bookings_between(connection, now, None),
        past=store.bookings_between(connection, None, now, newest_first=True)[:50],
        meeting_kinds=content.MEETING_KINDS,
        time_off=store.list_time_off(connection, from_date=now.astimezone(_settings().timezone).date()),
        calendar=_calendar(connection, request.args.get("view", "month"), request.args.get("anchor")),
    )


@bp.post("/bookings/<int:booking_id>/cancel")
@login_required
def cancel_booking(booking_id: int) -> Response:
    connection = get_db()
    booking = store.get_booking(connection, booking_id) or abort(404)
    when = booking["starts_at"].astimezone(_settings().timezone)
    store.delete_booking(connection, booking_id)

    if request.form.get("notify") == "yes":
        note = clean_block(request.form, "note", max_length=2000)
        delivered = send_quietly(
            _mailer(),
            Email(
                to=booking["client_email"],
                subject="Your appointment with Otto & Associates has been cancelled",
                body=(
                    f"Hi {booking['client_name']},\n\nYour appointment on "
                    f"{when.strftime('%A, %B %-d at %-I:%M %p')} has been cancelled.\n\n"
                    f"{note + chr(10) + chr(10) if note else ''}Reply to this email or call us to find a new time."
                ),
                reply_to=_settings().agency_email,
            ),
        )
        flash("Cancelled and the client was emailed." if delivered else "Cancelled, but the email failed. Call the client.")
    else:
        flash("Cancelled. The client was not emailed.")
    return redirect(url_for("portal.bookings"))


@bp.post("/bookings/<int:booking_id>/email")
@login_required
def email_client(booking_id: int) -> Response:
    booking = store.get_booking(get_db(), booking_id) or abort(404)
    subject = clean_text(request.form, "subject", max_length=200) or "A message about your appointment"
    body = clean_block(request.form, "body", max_length=5000)
    if not body:
        flash("Write a message before sending.")
        return redirect(url_for("portal.bookings"))

    delivered = send_quietly(
        _mailer(), Email(to=booking["client_email"], subject=subject, body=body, reply_to=_settings().agency_email)
    )
    flash(f"Sent to {booking['client_email']}." if delivered else "The email could not be sent. Check SMTP settings.")
    return redirect(url_for("portal.bookings"))


@bp.post("/bookings/clear-past")
@login_required
def clear_past_bookings() -> Response:
    removed = store.delete_bookings_before(get_db(), store.utc_now())
    flash(f"Removed {removed} past appointment{'s' if removed != 1 else ''}.")
    return redirect(url_for("portal.bookings"))


@bp.route("/appointments/new", methods=["GET", "POST"])
@login_required
def new_booking() -> str | Response | tuple[str, int]:
    """An appointment the owner took by phone, added to the same calendar."""
    connection = get_db()
    tz = _settings().timezone
    rules = store.booking_rules(connection)
    week = store.week_hours(connection)
    tomorrow = store.utc_now().astimezone(tz).date() + timedelta(days=1)
    values: dict[str, str] = {
        "date": request.form.get("date") or tomorrow.isoformat(),
        "time": request.form.get("time") or "09:30",
        "name": "",
        "email": "",
        "phone": "",
        "reason": "",
        "meeting_kind": "phone",
    }
    errors: dict[str, str] = {}

    if request.method == "POST":
        values = {
            "date": request.form.get("date", ""),
            "time": request.form.get("time", ""),
            "name": clean_text(request.form, "name", max_length=100),
            "email": clean_text(request.form, "email", max_length=254).lower(),
            "phone": clean_text(request.form, "phone", max_length=30),
            "reason": clean_block(request.form, "reason", max_length=1000),
            "meeting_kind": request.form.get("meeting_kind", "phone"),
        }
        day = parse_iso_date(values["date"])
        try:
            requested = clock_time.fromisoformat(values["time"])
        except ValueError:
            requested = None

        if len(values["name"]) < 2:
            errors["name"] = "Add the client's name."
        if values["email"] and not EMAIL_PATTERN.match(values["email"]):
            errors["email"] = "Enter an email address like name@example.com, or leave it blank."
        if values["meeting_kind"] not in content.MEETING_KINDS:
            errors["meeting_kind"] = "Choose how you will meet."
        if day is None:
            errors["date"] = "Choose a date."
        if requested is None:
            errors["time"] = "Choose a time."

        if day is not None and requested is not None and not errors:
            starts = datetime.combine(day, requested, tzinfo=tz)
            hours = week.get(day.weekday())
            if starts <= store.utc_now():
                errors["time"] = "Choose a time in the future."
            elif day in store.closed_dates(connection, day, day):
                errors["date"] = "That day is marked as time off. Remove the time off first, or pick another day."
            elif hours is None or not hours.is_open:
                errors["date"] = "The office is not open for bookings that day. Add it in Hours, or pick another day."
            elif not hours.opens_at <= requested < hours.closes_at:
                errors["time"] = f"That is outside office hours ({format_clock(hours.opens_at)} to {format_clock(hours.closes_at)})."
            else:
                try:
                    store.create_booking(
                        connection,
                        store.NewBooking(
                            values["name"], values["email"], values["phone"], values["reason"], starts, values["meeting_kind"]
                        ),
                        rules,
                    )
                except store.SlotTaken:
                    errors["time"] = "That time is already full. Choose another."
                else:
                    if request.form.get("notify") == "on" and values["email"]:
                        send_quietly(
                            _mailer(),
                            Email(
                                to=values["email"],
                                subject=f"Your appointment with Otto & Associates, {starts.strftime('%A, %B %-d at %-I:%M %p')}",
                                body=(
                                    f"Hi {values['name']},\n\nYou are booked for "
                                    f"{starts.strftime('%A, %B %-d at %-I:%M %p')}: "
                                    f"{content.MEETING_KINDS[values['meeting_kind']].lower()}.\n\n"
                                    "If you need to change it, reply to this email or call the office.\n\n"
                                    "Glenn and Andi Otto\nOtto & Associates"
                                ),
                                reply_to=_settings().agency_email,
                            ),
                        )
                    flash("Appointment added to the calendar.")
                    return redirect(url_for("portal.bookings"))

    return render_template(
        "portal/booking_new.html",
        values=values,
        errors=errors,
        week=week,
        weekday_names=WEEKDAY_NAMES,
        meeting_kinds=content.MEETING_KINDS,
        timezone=tz.key,
        time_off=store.list_time_off(connection, from_date=store.utc_now().astimezone(tz).date()),
    ), (422 if errors else 200)


@bp.get("/appointments.csv")
@login_required
def export_bookings() -> Response:
    rows = [
        {**dict(row), "starts_at": _local(row["starts_at"]), "created_at": _local(row["created_at"])}
        for row in store.bookings_between(get_db(), None, None, newest_first=True, limit=10000)
    ]
    return _csv_response(
        rows,
        [
            ("starts_at", "Appointment"),
            ("client_name", "Client"),
            ("client_email", "Email"),
            ("client_phone", "Phone"),
            ("meeting_kind", "How"),
            ("reason", "Note"),
            ("created_at", "Booked"),
        ],
        "otto-appointments.csv",
    )


@bp.route("/time-off", methods=["GET", "POST"])
@login_required
def time_off() -> str | Response | tuple[str, int]:
    connection = get_db()
    today = store.utc_now().astimezone(_settings().timezone).date()
    errors: dict[str, str] = {}

    if request.method == "POST":
        starts_on = parse_iso_date(request.form.get("starts_on"))
        ends_on = parse_iso_date(request.form.get("ends_on")) or starts_on
        note = clean_text(request.form, "note", max_length=120)
        if starts_on is None:
            errors["starts_on"] = "Choose the first day away."
        elif ends_on < starts_on:
            errors["ends_on"] = "The last day cannot be before the first."
        elif ends_on < today:
            errors["ends_on"] = "Choose a day that has not passed."
        else:
            store.add_time_off(connection, starts_on, ends_on, note)
            flash("Time off saved. Those days no longer offer appointments.")
            return redirect(url_for("portal.time_off"))

    return render_template(
        "portal/time_off.html",
        entries=store.list_time_off(connection, from_date=today),
        errors=errors,
        form=request.form,
        today=today,
        timezone=_settings().timezone.key,
    ), (422 if errors else 200)


@bp.post("/time-off/<int:time_off_id>/delete")
@login_required
def delete_time_off(time_off_id: int) -> Response:
    store.delete_time_off(get_db(), time_off_id)
    flash("Time off removed. Those days are bookable again.")
    return redirect(url_for("portal.time_off"))


@bp.get("/messages")
@login_required
def messages() -> str:
    connection = get_db()
    only_unread = request.args.get("filter") == "unread"
    return render_template(
        "portal/messages.html",
        messages=store.list_messages(connection, unread_only=only_unread),
        unread=store.count_unread_messages(connection),
        only_unread=only_unread,
    )


@bp.post("/messages/<int:message_id>/reply")
@login_required
def reply_message(message_id: int) -> Response:
    connection = get_db()
    message = store.get_message(connection, message_id) or abort(404)
    body = clean_block(request.form, "body", max_length=5000)
    if not body:
        flash("Write a reply before sending.")
        return redirect(url_for("portal.messages"))

    delivered = send_quietly(
        _mailer(),
        Email(
            to=message["sender_email"],
            subject=f"Re: {message['topic']}",
            body=body,
            reply_to=_settings().agency_email,
        ),
    )
    if delivered:
        store.mark_message_replied(connection, message_id, body)
        flash(f"Reply sent to {message['sender_email']}.")
    else:
        flash("The reply could not be sent. Check the mail settings, or email them directly.")
    return redirect(url_for("portal.messages"))


@bp.get("/messages.csv")
@login_required
def export_messages() -> Response:
    rows = [
        {**dict(row), "created_at": _local(row["created_at"]), "replied_at": _local(row["replied_at"])}
        for row in store.list_messages(get_db(), limit=10000)
    ]
    return _csv_response(
        rows,
        [
            ("created_at", "Received"),
            ("sender_name", "Name"),
            ("sender_email", "Email"),
            ("sender_phone", "Phone"),
            ("topic", "About"),
            ("body", "Message"),
            ("reply_body", "Our reply"),
            ("replied_at", "Replied"),
        ],
        "otto-messages.csv",
    )


@bp.post("/messages/<int:message_id>/read")
@login_required
def read_message(message_id: int) -> Response:
    store.mark_message_read(get_db(), message_id)
    return redirect(url_for("portal.messages"))


@bp.post("/messages/<int:message_id>/delete")
@login_required
def delete_message(message_id: int) -> Response:
    store.delete_message(get_db(), message_id)
    flash("Message deleted.")
    return redirect(url_for("portal.messages"))


# --------------------------------------------------------------------------- notes

def _note_color(value: str | None) -> str:
    return value if value in store.NOTE_COLORS else "gold"


def _note_int(value: str | None, default: int = 0) -> int:
    try:
        return int(value or default)
    except (TypeError, ValueError):
        return default


@bp.get("/notes")
@login_required
def notes() -> str:
    view = "list" if request.args.get("view") == "list" else "board"
    return render_template(
        "portal/notes.html",
        notes=store.list_notes(get_db()),
        view=view,
        colors=store.NOTE_COLORS,
    )


@bp.post("/notes")
@login_required
def add_note() -> Response:
    connection = get_db()
    body = clean_block(request.form, "body", max_length=1200)
    if not body:
        flash("Write something on the note first.")
        return redirect(url_for("portal.notes"))
    # Lay new notes out in a loose grid so they do not land on top of each other.
    count = store.count_notes(connection)
    pos_x = 24 + (count % 4) * 258
    pos_y = 24 + ((count // 4) % 3) * 186
    store.create_note(connection, body, _note_color(request.form.get("color")), pos_x, pos_y)
    flash("Note added to the board. Drag it anywhere you like.")
    return redirect(url_for("portal.notes", view=request.form.get("view") or None))


@bp.post("/notes/<int:note_id>")
@login_required
def save_note(note_id: int) -> Response:
    body = clean_block(request.form, "body", max_length=1200)
    if not body:
        flash("A note cannot be empty. Delete it instead if it is finished.")
    else:
        store.update_note(get_db(), note_id, body, _note_color(request.form.get("color")))
        flash("Note saved.")
    return redirect(url_for("portal.notes", view=request.form.get("view") or None))


@bp.post("/notes/<int:note_id>/move")
@login_required
def move_note(note_id: int) -> Response:
    store.move_note(
        get_db(),
        note_id,
        _note_int(request.form.get("pos_x")),
        _note_int(request.form.get("pos_y")),
        _note_int(request.form.get("z_index")),
    )
    return Response(status=204)


@bp.post("/notes/<int:note_id>/pin")
@login_required
def pin_note(note_id: int) -> Response:
    pinned = request.form.get("pinned") == "yes"
    store.set_note_pinned(get_db(), note_id, pinned)
    flash("Note pinned to the top." if pinned else "Note unpinned.")
    return redirect(url_for("portal.notes", view=request.form.get("view") or None))


@bp.post("/notes/<int:note_id>/delete")
@login_required
def delete_note(note_id: int) -> Response:
    store.delete_note(get_db(), note_id)
    flash("Note deleted.")
    return redirect(url_for("portal.notes", view=request.form.get("view") or None))


@bp.route("/settings/texts", methods=["GET", "POST"])
@login_required
def texts() -> str | Response | tuple[str, int]:
    """Text reminders to the owner's own phone."""
    connection = get_db()
    errors: dict[str, str] = {}
    saved = site_content.get_setting(connection, "notify")
    if request.method == "POST":
        phone = clean_text(request.form, "sms_phone", max_length=30)
        try:
            hours = int(request.form.get("sms_reminder_hours", "24"))
        except ValueError:
            hours = 24
        digits = re.sub(r"\D", "", phone)
        if phone and not 10 <= len(digits) <= 15:
            errors["sms_phone"] = "Enter a mobile number with area code, like (937) 610-0088."
        if request.form.get("sms_enabled") == "on" and not phone:
            errors["sms_phone"] = "Add the mobile number that should get the texts."

        templates: dict[str, str] = {}
        for field, label in (
            ("sms_booking_template", "New appointment"),
            ("sms_request_template", "New request"),
            ("sms_reminder_template", "Appointment reminder"),
        ):
            # A form that does not carry the wording at all keeps what is saved.
            if field not in request.form:
                templates[field] = str(saved.get(field, ""))
                continue
            text = clean_block(request.form, field, max_length=480)
            problem = notify.template_problem(text, field)
            if problem:
                errors[field] = f"{label}: {problem}"
            templates[field] = text

        if not errors:
            site_content.save_setting(
                connection,
                "notify",
                {
                    "sms_enabled": request.form.get("sms_enabled") == "on",
                    "sms_phone": phone,
                    "sms_reminder_hours": max(1, min(72, hours)),
                    "sms_on_booking": request.form.get("sms_on_booking") == "on",
                    "sms_on_request": request.form.get("sms_on_request") == "on",
                    **templates,
                },
            )
            flash("Saved. Text settings updated.")
            return redirect(url_for("portal.texts"))

    values = site_content.get_setting(connection, "notify")
    if request.method == "POST" and errors:
        for field in ("sms_phone", "sms_booking_template", "sms_request_template", "sms_reminder_template"):
            if field in request.form:
                values[field] = request.form.get(field, "")
    preview = notify.render(
        str(values.get("sms_reminder_template") or ""),
        "Otto & Associates: {name} is booked {when} ({kind}). Reply to this text or call the office to change it.",
        name="Mary K.",
        when="Tue Nov 4 at 3:00 pm",
        kind="phone call",
    )

    return render_template(
        "portal/texts.html",
        notify=values,
        preview=preview,
        errors=errors,
        configured=_settings().sms is not None,
        form=request.form,
    ), (422 if errors else 200)


@bp.post("/settings/texts/test")
@login_required
def test_text() -> Response:
    if _settings().sms is None:
        flash("No text was sent: the site is not connected to Twilio yet. Add the three OTTO_TWILIO settings on the host and redeploy.")
        return redirect(url_for("portal.texts"))
    ok, detail = notify.test_message(get_db(), _texter())
    if ok:
        flash(f"Test text sent to {detail}. It usually arrives within a few seconds.")
    else:
        flash(f"No text was sent. {detail} Check the Twilio settings on the host.")
    return redirect(url_for("portal.texts"))


@bp.post("/settings/texts/run")
@login_required
def run_reminders() -> Response:
    connection = get_db()
    values = site_content.get_setting(connection, "notify")
    if _settings().sms is None:
        flash("No reminders were sent: the site is not connected to Twilio yet. Add the three OTTO_TWILIO settings on the host and redeploy.")
        return redirect(url_for("portal.texts"))
    sent, failed = notify.send_due_reminders(
        connection,
        _texter(),
        _settings().timezone,
        hours=int(values.get("sms_reminder_hours", 24)),
        kinds=content.MEETING_KINDS,
    )
    if not values.get("sms_enabled") or not values.get("sms_phone"):
        flash("Switch texts on and add a mobile number first.")
    elif sent:
        flash(f"Sent {sent} reminder{'s' if sent != 1 else ''}." + (f" {failed} failed." if failed else ""))
    elif failed:
        flash("The reminders could not be sent. Check the Twilio settings on the host.")
    else:
        flash("No appointments are waiting for a reminder in that window.")
    return redirect(url_for("portal.texts"))


@bp.post("/settings/test-email")
@login_required
def test_email() -> Response:
    address = _settings().agency_email
    delivered = send_quietly(
        _mailer(),
        Email(
            to=address,
            subject="Test message from your website",
            body=(
                "If you can read this, the website can send email.\n\n"
                "Bookings, quote requests and replies from the portal all arrive through the same account."
            ),
        ),
    )
    if delivered:
        flash(f"Test message sent to {address}. Check that inbox, including the spam folder.")
    else:
        flash("The test message could not be sent. Check the mail settings.")
    return redirect(url_for("portal.settings"))


@bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings() -> str | Response | tuple[str, int]:
    connection = get_db()
    errors: list[str] = []

    if request.method == "POST":
        week: list[DayHours] = []
        for weekday, day_name in enumerate(WEEKDAY_NAMES):
            try:
                opens = parse_clock(request.form.get(f"opens_{weekday}", ""))
                closes = parse_clock(request.form.get(f"closes_{weekday}", ""))
            except ValueError:
                errors.append(f"{day_name}: enter opening and closing times.")
                continue
            if opens >= closes:
                errors.append(f"{day_name}: closing time must be after opening time.")
                continue
            week.append(DayHours(weekday, request.form.get(f"open_{weekday}") == "on", opens, closes))

        try:
            rules = BookingRules(
                slot_minutes=int(request.form.get("slot_minutes", "")),
                days_ahead=int(request.form.get("days_ahead", "")),
                per_slot=int(request.form.get("per_slot", "")),
            )
        except ValueError:
            errors.append("Booking rules must be whole numbers.")
        else:
            if not 10 <= rules.slot_minutes <= 240:
                errors.append("Appointment length must be between 10 and 240 minutes.")
            if not 1 <= rules.days_ahead <= 180:
                errors.append("Booking window must be between 1 and 180 days.")
            if not 1 <= rules.per_slot <= 10:
                errors.append("Clients per time must be between 1 and 10.")

        if not errors:
            store.save_week_hours(connection, week)
            store.save_booking_rules(connection, rules)
            flash("Hours and booking rules saved.")
            return redirect(url_for("portal.settings"))

    return render_template(
        "portal/settings.html",
        week=store.week_hours(connection),
        rules=store.booking_rules(connection),
        weekday_names=WEEKDAY_NAMES,
        errors=errors,
        timezone=_settings().timezone.key,
        mail_configured=_settings().smtp is not None,
        agency_email=_settings().agency_email,
    ), (422 if errors else 200)


@bp.route("/faqs", methods=["GET", "POST"])
@login_required
def faqs() -> str | Response:
    connection = get_db()
    if request.method == "POST":
        question = clean_text(request.form, "question", max_length=300)
        answer = clean_block(request.form, "answer", max_length=3000)
        raw_id = request.form.get("faq_id", "")
        raw_position = request.form.get("position", "")
        try:
            position = int(raw_position) if raw_position.strip() else None
        except ValueError:
            position = None
        faq_id = int(raw_id) if raw_id.isdigit() else None
        if position is None:
            position = store.next_faq_position(connection) if faq_id is None else store.faq_position(connection, faq_id)
        if not question or not answer:
            flash("A question and an answer are both needed.")
        else:
            store.upsert_faq(connection, faq_id, question, answer, position)
            flash("Saved.")
        return redirect(url_for("portal.faqs"))

    return render_template("portal/faqs.html", faqs=store.list_faqs(connection))


@bp.post("/faqs/<int:faq_id>/delete")
@login_required
def delete_faq(faq_id: int) -> Response:
    connection = get_db()
    store.delete_faq(connection, faq_id)
    store.renumber_faqs(connection)
    flash("Question removed.")
    return redirect(url_for("portal.faqs"))


@bp.post("/faqs/<int:faq_id>/<action>")
@login_required
def move_faq(faq_id: int, action: str) -> Response:
    if action not in {"up", "down"}:
        abort(404)
    store.move_faq(get_db(), faq_id, -1 if action == "up" else 1)
    return redirect(url_for("portal.faqs"))


@bp.route("/links", methods=["GET", "POST"])
@login_required
def links() -> str | Response:
    connection = get_db()
    if request.method == "POST":
        audience = request.form.get("audience", "")
        section = clean_text(request.form, "section", max_length=80)
        title = clean_text(request.form, "title", max_length=120)
        url = clean_text(request.form, "url", max_length=500)
        if audience not in {"agent", "client"} or not section or not title:
            flash("Choose who the link is for and give it a section and title.")
        elif not safe_link(url):
            flash("Links must start with https://, http://, tel: or mailto:.")
        else:
            store.create_link(connection, audience, section, title, url)
            flash("Link added.")
        return redirect(url_for("portal.links"))

    return render_template("portal/links.html", links=store.list_links(connection))


@bp.post("/links/<int:link_id>/delete")
@login_required
def delete_link(link_id: int) -> Response:
    store.delete_link(get_db(), link_id)
    flash("Link removed.")
    return redirect(url_for("portal.links"))


@bp.route("/account", methods=["GET", "POST"])
@login_required
def account() -> str | Response | tuple[str, int]:
    connection = get_db()
    errors: dict[str, str] = {}

    if request.method == "POST":
        current = request.form.get("current_password", "")
        new = request.form.get("new_password", "")
        repeated = request.form.get("confirm_password", "")
        signed_in = store.get_agent_by_email(connection, g.agent["email"])

        if signed_in is None or not check_password_hash(signed_in["password_hash"], current):
            errors["current_password"] = "That is not your current password."
        if len(new) < 12:
            errors["new_password"] = "Use at least 12 characters. A short sentence works well."
        if new != repeated:
            errors["confirm_password"] = "The new passwords did not match."
        if not errors and signed_in is not None:
            store.set_agent_password(connection, signed_in["id"], generate_password_hash(new))
            flash("Your password is changed. Use the new one the next time you sign in.")
            return redirect(url_for("portal.account"))

    return render_template("portal/account.html", agent=g.agent, errors=errors), (422 if errors else 200)


@bp.get("/backup")
@login_required
def backup() -> str:
    connection = get_db()
    return render_template(
        "portal/backup.html",
        message_count=len(store.list_messages(connection, limit=10000)),
        booking_count=len(store.bookings_between(connection, None, None, limit=10000)),
        faq_count=len(store.list_faqs(connection)),
        carrier_count=len(connection.execute("SELECT id FROM carriers").fetchall()),
        time_off_count=len(store.list_time_off(connection)),
    )


@bp.get("/backup/content.json")
@login_required
def backup_content() -> Response:
    connection = get_db()
    payload = {
        "exported_at": store.utc_now().isoformat(),
        "note": "Photos and logos uploaded in the portal live in the database and are not included in this file.",
        "website": {key: site_content.get_setting(connection, key) for key in site_content.DEFAULT_SETTINGS},
        "carriers": [dict(row) for row in connection.execute("SELECT * FROM carriers ORDER BY position, id").fetchall()],
        "coverage": [dict(row) for row in connection.execute("SELECT * FROM coverage ORDER BY position, id").fetchall()],
        "people": [dict(row) for row in connection.execute("SELECT * FROM team ORDER BY position, id").fetchall()],
        "reviews": [dict(row) for row in connection.execute("SELECT * FROM testimonials ORDER BY position, id").fetchall()],
        "faqs": [dict(row) for row in store.list_faqs(connection)],
        "resources": [dict(row) for row in store.list_links(connection)],
    }
    response = Response(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        content_type="application/json; charset=utf-8",
    )
    response.headers["Content-Disposition"] = 'attachment; filename="otto-website-backup.json"'
    return response


@bp.get("/backup/faqs.csv")
@login_required
def export_faqs() -> Response:
    rows = [dict(row) for row in store.list_faqs(get_db())]
    return _csv_response(rows, [("question", "Question"), ("answer", "Answer"), ("position", "Position")], "otto-faqs.csv")


@bp.context_processor
def _portal_context() -> dict[str, object]:
    if g.get("agent") is None:
        return {}
    return {"unread_total": store.count_unread_messages(get_db())}


@bp.app_template_filter("local_time")
def local_time(value: datetime, fmt: str = "%a %b %-d, %-I:%M %p") -> str:
    tz = _settings().timezone
    return value.astimezone(tz).strftime(fmt) if value.tzinfo else value.replace(tzinfo=UTC).astimezone(tz).strftime(fmt)
