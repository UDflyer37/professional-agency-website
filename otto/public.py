from __future__ import annotations

import hmac
from datetime import timedelta

from flask import Blueprint, abort, current_app, g, jsonify, make_response, redirect, render_template, request, url_for
from werkzeug.wrappers.response import Response

from otto import content, media, notify, site, store, throttle
from otto.config import Settings
from otto.db import get_db
from otto.mailer import Email, Mailer, send_quietly
from otto.scheduling import WEEKDAY_NAMES, bookable_window, format_clock, office_status, open_slots
from otto.validation import (
    FormErrors,
    clean_block,
    clean_text,
    looks_like_bot,
    optional_phone,
    parse_iso_date,
    parse_slot,
    require_email,
    require_name,
)

bp = Blueprint("public", __name__)


def _settings() -> Settings:
    return current_app.config["OTTO"]


def _mailer() -> Mailer:
    return current_app.extensions["otto_mailer"]


def _texter():
    return current_app.extensions["otto_texter"]


def _hours_lines() -> list[tuple[str, str]]:
    lines = []
    for weekday, day in sorted(store.week_hours(get_db()).items()):
        hours = f"{format_clock(day.opens_at)} to {format_clock(day.closes_at)}" if day.is_open else "by appointment"
        lines.append((WEEKDAY_NAMES[weekday], hours))
    return lines


def _hours_summary(lines: list[tuple[str, str]]) -> list[str]:
    """Merge consecutive days with the same hours: Mon–Fri 9:30 am to 5:00 pm."""
    groups: list[list[str]] = []
    for day, span in lines:
        if groups and groups[-1][2] == span:
            groups[-1][1] = day
        else:
            groups.append([day, day, span])
    return [
        f"{first[:3]}{'–' + last[:3] if last != first else ''} {span}" for first, last, span in groups
    ]


@bp.app_template_filter("dial")
def _dial_filter(display: str) -> str:
    return site.dial(display)


def current_site() -> site.Site:
    if "site" not in g:
        g.site = site.load(get_db())
    return g.site


@bp.app_context_processor
def _shared_context() -> dict[str, object]:
    lines = _hours_lines()
    loaded = current_site()
    return {
        "now_year": store.utc_now().year,
        "hours": lines,
        "hours_summary": _hours_summary(lines),
        "site": loaded,
        "agency": loaded.agency,
    }


@bp.get("/")
def home() -> str:
    connection = get_db()
    settings = _settings()
    week = store.week_hours(connection)
    now_local = store.utc_now().astimezone(settings.timezone)
    away_today = bool(store.closed_dates(connection, now_local.date(), now_local.date()))
    # The badge re-checks these in the browser, so a page left open overnight still
    # knows about vacation days the owner set in the portal.
    away_dates = sorted(store.closed_dates(connection, now_local.date(), now_local.date() + timedelta(days=120)))
    status = office_status(store.utc_now(), week, settings.timezone, away_today=away_today)
    week_for_script = {
        str(weekday): [day.is_open, day.opens_at.strftime("%H:%M"), day.closes_at.strftime("%H:%M")]
        for weekday, day in week.items()
    }
    return render_template(
        "public/home.html",
        paperwork=content.PAPERWORK_ITEMS,
        quote_items=content.QUOTE_ITEMS,
        community=content.COMMUNITY,
        faqs=store.list_faqs(connection),
        status=status,
        away_today=away_today,
        away_dates=[day.isoformat() for day in away_dates],
        week_for_script=week_for_script,
        today_name=WEEKDAY_NAMES[now_local.weekday()],
        years_serving=now_local.year - 1998,
        timezone=settings.timezone.key,
    )


@bp.route("/appointments", methods=["GET", "POST"])
def appointments() -> tuple[str, int] | Response:
    connection = get_db()
    settings = _settings()
    tz = settings.timezone
    rules = store.booking_rules(connection)
    now = store.utc_now()
    first_day, last_day = bookable_window(now.astimezone(tz).date(), rules)
    closed = store.closed_dates(connection, first_day, last_day)

    chosen = parse_iso_date(request.values.get("date")) or first_day
    chosen = min(max(chosen, first_day), last_day)

    errors = FormErrors()
    form = request.form if request.method == "POST" else {}

    if request.method == "POST":
        if looks_like_bot(request.form):
            return redirect(url_for("public.appointment_booked"))

        name = clean_text(request.form, "name", max_length=100)
        email = clean_text(request.form, "email", max_length=254).lower()
        phone = clean_text(request.form, "phone", max_length=30)
        reason = clean_block(request.form, "reason", max_length=1000)
        slot = parse_slot(request.form.get("slot"))
        meeting_kind = request.form.get("meeting_kind", "")

        require_name(name, errors)
        require_email(email, errors)
        optional_phone(phone, errors)
        if meeting_kind not in content.MEETING_KINDS:
            errors.add("meeting_kind", "Choose how you would like to meet.")
        elif meeting_kind == "phone" and not phone:
            errors.add("phone", "Add the number we should call.")

        week = store.week_hours(connection)
        valid_slots = []
        if slot is not None:
            slot_day = slot.astimezone(tz).date()
            valid_slots = open_slots(
                slot_day, week[slot_day.weekday()], rules, store.taken_slots(connection, slot_day, tz), now, tz, closed
            )
            chosen = slot_day
        if slot is None or slot.astimezone(tz) not in valid_slots:
            errors.add("slot", "Choose one of the open times.")

        if not errors and slot is not None:
            try:
                store.create_booking(
                    connection, store.NewBooking(name, email, phone, reason, slot, meeting_kind), rules
                )
            except store.SlotTaken:
                errors.add("slot", "Someone took that time a moment ago. Please choose another.")
            else:
                _send_booking_emails(
                    name, email, phone, reason, content.MEETING_KINDS[meeting_kind],
                    slot.astimezone(tz).strftime("%A, %B %-d at %-I:%M %p"),
                )
                notify.new_booking(
                    connection, _texter(), name,
                    slot.astimezone(tz).strftime("%a %b %-d at %-I:%M %p"),
                    content.MEETING_KINDS[meeting_kind],
                )
                return redirect(
                    url_for("public.appointment_booked", when=slot.astimezone(tz).isoformat(), kind=meeting_kind)
                )

    week = store.week_hours(connection)
    slots = open_slots(chosen, week[chosen.weekday()], rules, store.taken_slots(connection, chosen, tz), now, tz, closed)

    # With no date asked for, start on the first day that still has a free time,
    # so a visitor arriving after hours does not land on an empty day.
    if not slots and request.method == "GET" and not request.args.get("date"):
        day = chosen
        while day < last_day and not slots:
            day += timedelta(days=1)
            slots = open_slots(day, week[day.weekday()], rules, store.taken_slots(connection, day, tz), now, tz, closed)
        if slots:
            chosen = day

    closed_note = ""
    if chosen in closed:
        closed_note = "We are away on that day. Pick another day, or call us and we will find a time that works."

    return render_template(
        "public/appointments.html",
        chosen=chosen,
        previous_day=chosen - timedelta(days=1) if chosen > first_day else None,
        next_day=chosen + timedelta(days=1) if chosen < last_day else None,
        first_day=first_day,
        last_day=last_day,
        slots=slots,
        selected_slot=request.form.get("slot", ""),
        meeting_kinds=content.MEETING_KINDS,
        selected_kind=request.form.get("meeting_kind", "phone"),
        format_clock=format_clock,
        form=form,
        errors=errors.by_field,
        closed_note=closed_note,
    ), (422 if errors else 200)


def _send_booking_emails(name: str, email: str, phone: str, reason: str, kind: str, when: str) -> None:
    settings = _settings()
    agency = current_site().agency
    how = {
        "Phone call": f"Glenn or Andi will call you on {phone}." if phone else "We will call you.",
        "Video call": "We will email you a video link before the call.",
    }.get(kind, "We will be in touch to confirm where we meet.")
    send_quietly(
        _mailer(),
        Email(
            to=email,
            subject=f"Your appointment with Otto & Associates, {when}",
            body=(
                f"Hi {name},\n\nYou are booked for {when}: {kind.lower()}. {how}\n\n"
                f"If you need to change it, reply to this email or call {agency.phone}.\n\n"
                "Glenn and Andi Otto\nOtto & Associates"
            ),
            reply_to=settings.agency_email,
        ),
    )
    send_quietly(
        _mailer(),
        Email(
            to=settings.agency_email,
            subject=f"New appointment: {name}, {when} ({kind})",
            body=(
                f"{name} booked {when}.\nHow: {kind}\nEmail: {email}\nPhone: {phone or 'not given'}\n\n"
                f"{reason or 'No note.'}"
            ),
            reply_to=email,
        ),
    )


@bp.get("/appointments/booked")
def appointment_booked() -> str:
    when = parse_slot(request.args.get("when"))
    kind = content.MEETING_KINDS.get(request.args.get("kind", ""), "")
    return render_template("public/booked.html", when=when, kind=kind)


@bp.route("/contact", methods=["GET", "POST"])
def contact() -> tuple[str, int] | Response:
    topic = request.values.get("topic", "")
    if topic not in content.REQUEST_TOPICS:
        topic = ""
    errors = FormErrors()

    # Arriving from the home page quote builder: ?topic=quote&items=home,car
    raw_items = [part for value in request.args.getlist("items") for part in value.split(",")]
    picked = list(dict.fromkeys(slug for slug in raw_items if slug in content.QUOTE_ITEMS))
    prefill_body = ""
    if picked:
        topic = "quote"
        prefill_body = "Please quote: " + ", ".join(content.QUOTE_ITEMS[slug][1] for slug in picked) + "."

    if request.method == "POST":
        if looks_like_bot(request.form):
            return redirect(url_for("public.contact_sent"))

        name = clean_text(request.form, "name", max_length=100)
        email = clean_text(request.form, "email", max_length=254).lower()
        phone = clean_text(request.form, "phone", max_length=30)
        body = clean_block(request.form, "body", max_length=4000)

        require_name(name, errors)
        require_email(email, errors)
        optional_phone(phone, errors)
        if not topic:
            errors.add("topic", "Choose what this is about.")
        if topic not in content.PAPERWORK and len(body) < 5:
            errors.add("body", "Tell us a little more so we can help.")

        if not errors:
            label = content.REQUEST_TOPICS[topic]
            store.create_message(get_db(), store.NewMessage(name, email, phone, label, body))
            send_quietly(
                _mailer(),
                Email(
                    to=_settings().agency_email,
                    subject=f"Website request from {name}: {label}",
                    body=f"{name} asked about: {label}\nEmail: {email}\nPhone: {phone or 'not given'}\n\n{body}",
                    reply_to=email,
                ),
            )
            notify.new_request(get_db(), _texter(), name, label)
            return redirect(url_for("public.contact_sent"))

    return render_template(
        "public/contact.html",
        topics=content.REQUEST_TOPICS,
        paperwork=content.PAPERWORK,
        topic=topic,
        form=request.form,
        prefill_body=prefill_body,
        errors=errors.by_field,
    ), (422 if errors else 200)


@bp.get("/contact/sent")
def contact_sent() -> str:
    return render_template("public/sent.html", is_quote=request.args.get("kind") == "quote")


@bp.get("/privacy")
def privacy() -> str:
    return render_template("public/privacy.html")


@bp.app_errorhandler(400)
@bp.app_errorhandler(404)
@bp.app_errorhandler(429)
def client_error(error: Exception) -> Response:
    code = getattr(error, "code", 400)
    description = getattr(error, "description", "")
    if code == 404:
        description = "That page is not here. It may have moved when the site was rebuilt."
    response = make_response(render_template("public/error.html", code=code, description=description), code)
    if code == 429:
        response.headers["Retry-After"] = str(throttle.WINDOW_SECONDS)
    return response



@bp.post("/quote")
def quote() -> tuple[str, int] | Response:
    """The home page quote form: what to insure plus contact details, in one step."""
    if looks_like_bot(request.form):
        return redirect(url_for("public.contact_sent"))

    errors = FormErrors()
    picked = [slug for slug in dict.fromkeys(request.form.getlist("items")) if slug in content.QUOTE_ITEMS]
    name = clean_text(request.form, "name", max_length=100)
    email = clean_text(request.form, "email", max_length=254).lower()
    phone = clean_text(request.form, "phone", max_length=30)
    best_time = clean_text(request.form, "best_time", max_length=60)
    notes = clean_block(request.form, "notes", max_length=2000)

    if not picked:
        errors.add("items", "Choose at least one thing to quote.")
    require_name(name, errors)
    require_email(email, errors)
    optional_phone(phone, errors)

    if errors:
        return render_template(
            "public/quote_error.html", errors=errors.by_field, form=request.form, quote_items=content.QUOTE_ITEMS, picked=picked
        ), 422

    labels = ", ".join(content.QUOTE_ITEMS[slug][1] for slug in picked)
    body = f"Please quote: {labels}.\nBest time to reach me: {best_time or 'any time'}\n\n{notes}".strip()
    store.create_message(get_db(), store.NewMessage(name, email, phone, "Quote request", body))
    send_quietly(
        _mailer(),
        Email(
            to=_settings().agency_email,
            subject=f"Quote request from {name}: {labels}",
            body=f"{name} would like quotes for: {labels}\nEmail: {email}\nPhone: {phone or 'not given'}\n"
            f"Best time: {best_time or 'any time'}\n\n{notes or 'No notes.'}",
            reply_to=email,
        ),
    )
    notify.new_request(get_db(), _texter(), name, "a quote")
    return redirect(url_for("public.contact_sent", kind="quote"))


@bp.get("/tasks/reminders")
def reminder_task() -> Response | tuple[Response, int]:
    """Called by Vercel Cron once a day; texts the owner about tomorrow's appointments.

    Vercel sends `Authorization: Bearer $CRON_SECRET`. With no secret configured the
    endpoint stays closed rather than running unauthenticated.
    """
    settings = _settings()
    if not settings.cron_secret:
        abort(403)
    # Compared in constant time, and only from the header: a secret in a query string ends
    # up in Referer values, logs and browser history. Vercel always sends the header.
    if not hmac.compare_digest(request.headers.get("Authorization", ""), f"Bearer {settings.cron_secret}"):
        abort(403)

    values = site.get_setting(get_db(), "notify")
    sent, failed = notify.send_due_reminders(
        get_db(),
        _texter(),
        settings.timezone,
        hours=int(values.get("sms_reminder_hours", 24)),
        kinds=content.MEETING_KINDS,
    )
    return jsonify({"sent": sent, "failed": failed, "enabled": bool(values.get("sms_enabled"))})


@bp.get("/media/<int:media_id>")
def media_file(media_id: int) -> Response:
    image = media.load_image(get_db(), media_id)
    if image is None:
        abort(404)
    response = make_response(image.data)
    response.headers["Content-Type"] = image.content_type
    # Uploads are never edited in place (a new upload gets a new id), so they can be cached for a long time.
    response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return response
