"""End-to-end tests against a real PostgreSQL database.

Set OTTO_TEST_DATABASE_URL to an empty, throwaway database; every table is dropped first.
"""

import io
import os
import re
from collections.abc import Iterator
from datetime import timedelta
from zoneinfo import ZoneInfo

import pytest
from flask import Flask
from flask.testing import FlaskClient
from werkzeug.security import generate_password_hash

from otto import content, create_app, db, notify, site, store
from otto.config import Settings
from otto.mailer import LogMailer
from otto.sms import LogTexter

DATABASE_URL = os.environ.get("OTTO_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="OTTO_TEST_DATABASE_URL is not set")

TABLES = (
    "agents", "office_hours", "booking_rules", "bookings", "messages", "faqs", "links",
    "site_settings", "carriers", "coverage", "team", "testimonials", "media", "time_off", "notes",
    "request_throttle",
)


@pytest.fixture()
def mailer() -> LogMailer:
    return LogMailer()


@pytest.fixture()
def app(mailer: LogMailer) -> Iterator[Flask]:
    settings = Settings.from_env(
        {
            "OTTO_SECRET_KEY": "test-" + "x" * 40,
            "DATABASE_URL": DATABASE_URL or "",
            "OTTO_AGENCY_EMAIL": "office@example.com",
            "OTTO_SECURE_COOKIES": "false",
        }
    )
    flask_app = create_app(settings, mailer=mailer)
    with flask_app.app_context():
        connection = db.get_db()
        connection.execute(f"DROP TABLE IF EXISTS {', '.join(TABLES)} CASCADE")
        db.initialise(connection)
        connection.commit()
    yield flask_app


@pytest.fixture()
def client(app: Flask) -> FlaskClient:
    return app.test_client()


def csrf_from(client: FlaskClient, path: str) -> str:
    page = client.get(path).get_data(as_text=True)
    match = re.search(r'name="csrf_token" value="([^"]+)"', page)
    assert match, f"No CSRF token on {path}"
    return match.group(1)


def first_open_slot(client: FlaskClient) -> str:
    for offset in range(1, 10):
        with client.application.app_context():
            day = (store.utc_now() + timedelta(days=offset)).date()
        page = client.get(f"/appointments?date={day.isoformat()}").get_data(as_text=True)
        match = re.search(r'name="slot" value="([^"]+)"', page)
        if match:
            return match.group(1)
    raise AssertionError("No open slot found in the next ten days")


def test_public_pages_render(client: FlaskClient) -> None:
    for path in ("/", "/appointments", "/contact", "/contact?topic=proof-card", "/privacy"):
        assert client.get(path).status_code == 200, path
    assert client.get("/missing").status_code == 404


def test_post_without_csrf_is_rejected(client: FlaskClient) -> None:
    assert client.post("/contact", data={"name": "Pat"}).status_code == 400


def test_booking_flow_and_double_booking(client: FlaskClient, mailer: LogMailer) -> None:
    slot = first_open_slot(client)
    form = {
        "csrf_token": csrf_from(client, "/appointments"),
        "slot": slot,
        "name": "Pat Doe",
        "email": "pat@example.com",
        "meeting_kind": "video",
    }

    booked = client.post("/appointments", data=form)
    assert booked.status_code == 302
    assert [email.to for email in mailer.sent] == ["pat@example.com", "office@example.com"]

    second = client.post("/appointments", data={**form, "name": "Sam Roe", "email": "sam@example.com"})
    assert second.status_code == 422
    assert "Choose one of the open times" in second.get_data(as_text=True)


def test_contact_request_is_saved(client: FlaskClient, app: Flask) -> None:
    form = {"csrf_token": csrf_from(client, "/contact"), "topic": "proof-card", "name": "Pat Doe", "email": "pat@example.com"}
    assert client.post("/contact", data=form).status_code == 302
    with app.app_context():
        messages = store.list_messages(db.get_db())
    assert messages[0]["topic"] == "Proof of insurance card"


def test_contact_form_shows_errors(client: FlaskClient) -> None:
    response = client.post("/contact", data={"csrf_token": csrf_from(client, "/contact"), "email": "nope"})
    assert response.status_code == 422
    assert "Tell us your name." in response.get_data(as_text=True)


def test_portal_requires_login_and_locks_after_failures(client: FlaskClient, app: Flask) -> None:
    assert client.get("/portal/").status_code == 302
    with app.app_context():
        store.upsert_agent(db.get_db(), "andi@example.com", "Andi", generate_password_hash("a long test password"))

    token = csrf_from(client, "/portal/login")
    for _ in range(5):
        client.post("/portal/login", data={"csrf_token": token, "email": "andi@example.com", "password": "wrong"})
    locked = client.post("/portal/login", data={"csrf_token": token, "email": "andi@example.com", "password": "a long test password"})
    assert "Too many attempts" in locked.get_data(as_text=True)


def test_portal_pages_after_login(client: FlaskClient, app: Flask) -> None:
    with app.app_context():
        store.upsert_agent(db.get_db(), "andi@example.com", "Andi", generate_password_hash("a long test password"))
    token = csrf_from(client, "/portal/login")
    response = client.post("/portal/login", data={"csrf_token": token, "email": "ANDI@example.com", "password": "a long test password"})
    assert response.status_code == 302
    for path in (
        "/portal/", "/portal/appointments", "/portal/appointments/new", "/portal/messages", "/portal/settings",
        "/portal/faqs", "/portal/links", "/portal/time-off", "/portal/backup", "/portal/account",
        "/portal/settings/texts",
        "/portal/website", "/portal/website/basics", "/portal/website/look", "/portal/users",
        "/portal/website/companies", "/portal/website/coverage", "/portal/website/people", "/portal/website/reviews",
        "/portal/website/companies/new",
    ):
        assert client.get(path).status_code == 200, path


def test_redirect_after_login_stays_on_site(client: FlaskClient, app: Flask) -> None:
    with app.app_context():
        store.upsert_agent(db.get_db(), "andi@example.com", "Andi", generate_password_hash("a long test password"))
    token = csrf_from(client, "/portal/login")
    response = client.post(
        "/portal/login?next=//evil.example.com",
        data={"csrf_token": token, "email": "andi@example.com", "password": "a long test password"},
    )
    assert response.headers["Location"] == "/portal/"


def test_redirect_after_login_ignores_backslash_tricks(client: FlaskClient, app: Flask) -> None:
    with app.app_context():
        store.upsert_agent(db.get_db(), "andi@example.com", "Andi", generate_password_hash("a long test password"))
    token = csrf_from(client, "/portal/login")
    response = client.post(
        "/portal/login?next=/%5Cevil.example.com",
        data={"csrf_token": token, "email": "andi@example.com", "password": "a long test password"},
    )
    assert response.headers["Location"] == "/portal/"


def test_public_forms_are_rate_limited(client: FlaskClient) -> None:
    form = {"csrf_token": csrf_from(client, "/contact"), "topic": "proof-card", "name": "Pat Doe", "email": "pat@example.com"}
    for _ in range(6):
        assert client.post("/contact", data=form).status_code == 302
    blocked = client.post("/contact", data=form)
    assert blocked.status_code == 429
    assert blocked.headers["Retry-After"] == "600"
    assert "few minutes" in blocked.get_data(as_text=True)


def test_login_is_rate_limited_per_visitor(client: FlaskClient, app: Flask) -> None:
    with app.app_context():
        store.upsert_agent(db.get_db(), "andi@example.com", "Andi", generate_password_hash("a long test password"))
    token = csrf_from(client, "/portal/login")
    attempts = [
        client.post("/portal/login", data={"csrf_token": token, "email": "andi@example.com", "password": "wrong"}).status_code
        for _ in range(10)
    ]
    assert 429 not in attempts
    assert client.post("/portal/login", data={"csrf_token": token, "email": "andi@example.com", "password": "wrong"}).status_code == 429


def test_portal_pages_are_never_cached(client: FlaskClient, app: Flask) -> None:
    with app.app_context():
        store.upsert_agent(db.get_db(), "andi@example.com", "Andi", generate_password_hash("a long test password"))
    client.post(
        "/portal/login",
        data={"csrf_token": csrf_from(client, "/portal/login"), "email": "andi@example.com", "password": "a long test password"},
    )
    for path in ("/portal/", "/portal/messages", "/portal/notes"):
        response = client.get(path)
        assert response.headers["Cache-Control"] == "no-store", path
        assert response.headers["X-Frame-Options"] == "DENY", path
    assert client.get("/").headers.get("Cache-Control") != "no-store"


def test_phone_call_needs_a_number(client: FlaskClient) -> None:
    slot = first_open_slot(client)
    form = {
        "csrf_token": csrf_from(client, "/appointments"),
        "slot": slot,
        "name": "Pat Doe",
        "email": "pat@example.com",
        "meeting_kind": "phone",
    }
    response = client.post("/appointments", data=form)
    assert response.status_code == 422
    assert "Add the number we should call." in response.get_data(as_text=True)


def test_quote_builder_prefills_the_request(client: FlaskClient) -> None:
    page = client.get("/contact?topic=quote&items=home&items=car&items=not-a-thing").get_data(as_text=True)
    assert "Please quote: Homeowners, Auto." in page
    assert 'value="quote" checked' in page


def sign_in(client: FlaskClient, app: Flask) -> None:
    with app.app_context():
        store.upsert_agent(db.get_db(), "andi@example.com", "Andi Otto", generate_password_hash("a long test password"))
        db.get_db().commit()
    token = csrf_from(client, "/portal/login")
    client.post("/portal/login", data={"csrf_token": token, "email": "andi@example.com", "password": "a long test password"})


def test_website_editor_requires_login(client: FlaskClient) -> None:
    for path in ("/portal/website", "/portal/website/basics", "/portal/website/companies", "/portal/users"):
        assert client.get(path).status_code == 302, path


def test_home_page_shows_seeded_content(client: FlaskClient) -> None:
    page = client.get("/").get_data(as_text=True)
    assert "Appreciated, not tolerated." in page
    assert "1-800-422-0550" in page
    assert "Home and property" in page
    assert "What clients say" not in page  # no reviews until the agents add real ones


def test_basics_change_the_live_site(client: FlaskClient, app: Flask) -> None:
    sign_in(client, app)
    token = csrf_from(client, "/portal/website/basics")
    response = client.post(
        "/portal/website/basics",
        data={
            "csrf_token": token, "name": "Otto & Associates", "email": "andi@example.com", "phone": "(937) 610-0088",
            "city": "Sunbury", "hero_quotes": "Insurance with a handshake\nSecond line", "hero_intro": "Hello.",
            "announce_enabled": "on", "announce_text": "Closed Thursday for Thanksgiving.",
        },
    )
    assert response.status_code == 302
    page = client.get("/").get_data(as_text=True)
    assert "Insurance with a handshake" in page
    assert "Closed Thursday for Thanksgiving." in page
    assert "6650 Kilbourne" not in page  # street hidden because the switch was left off


def test_basics_reject_missing_headline(client: FlaskClient, app: Flask) -> None:
    sign_in(client, app)
    token = csrf_from(client, "/portal/website/basics")
    response = client.post("/portal/website/basics", data={"csrf_token": token, "name": "X", "email": "a@b.co", "phone": "1", "city": "Y"})
    assert response.status_code == 422
    assert "Add at least one headline." in response.get_data(as_text=True)


def test_review_lifecycle(client: FlaskClient, app: Flask) -> None:
    sign_in(client, app)
    token = csrf_from(client, "/portal/website/reviews/new")
    client.post("/portal/website/reviews/new", data={"csrf_token": token, "quote": "Painless switch.", "name": "Mary K."})
    assert "Painless switch." in client.get("/").get_data(as_text=True)

    with app.app_context():
        review_id = db.get_db().execute("SELECT id FROM testimonials").fetchone()["id"]
    token = csrf_from(client, "/portal/website/reviews")
    client.post(f"/portal/website/reviews/{review_id}/toggle", data={"csrf_token": token})
    assert "Painless switch." not in client.get("/").get_data(as_text=True)


def test_sections_can_be_hidden_and_reordered(client: FlaskClient, app: Flask) -> None:
    sign_in(client, app)
    token = csrf_from(client, "/portal/website/look")
    everything_but_faq = [key for key in site.SECTIONS if key != "faq"]
    client.post("/portal/website/look", data={"csrf_token": token, "preset": "forest-sun", "corners": "square", "show": everything_but_faq})
    page = client.get("/").get_data(as_text=True)
    assert "Questions we hear most" not in page
    assert "--primary:#25483b" in page

    token = csrf_from(client, "/portal/website/look")
    client.post("/portal/website/look", data={"csrf_token": token, "move": "contact:-1", "show": everything_but_faq})
    with app.app_context():
        order, _ = site.section_order(db.get_db())
    assert order.index("contact") < order.index("faq")


def test_logo_upload_is_validated_and_served(client: FlaskClient, app: Flask) -> None:
    sign_in(client, app)
    with app.app_context():
        carrier_id = db.get_db().execute("SELECT id FROM carriers ORDER BY position LIMIT 1").fetchone()["id"]
    path = f"/portal/website/companies/{carrier_id}"

    token = csrf_from(client, path)
    bad = client.post(path, data={"csrf_token": token, "name": "Grange", "logo_media_id": (io.BytesIO(b"<svg>"), "logo.svg")}, content_type="multipart/form-data")
    assert bad.status_code == 422

    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    token = csrf_from(client, path)
    good = client.post(path, data={"csrf_token": token, "name": "Grange", "logo_height": "40", "logo_media_id": (io.BytesIO(png), "logo.png")}, content_type="multipart/form-data")
    assert good.status_code == 302
    with app.app_context():
        media_id = db.get_db().execute("SELECT logo_media_id FROM carriers WHERE id = %s", (carrier_id,)).fetchone()["logo_media_id"]
    served = client.get(f"/media/{media_id}")
    assert served.status_code == 200
    assert served.headers["Content-Type"] == "image/png"


def test_quote_form_creates_a_message(client: FlaskClient, app: Flask, mailer: LogMailer) -> None:
    token = csrf_from(client, "/")
    response = client.post("/quote", data={"csrf_token": token, "items": ["home", "car"], "name": "Pat Doe", "email": "pat@example.com"})
    assert response.status_code == 302
    with app.app_context():
        message = store.list_messages(db.get_db())[0]
    assert message["topic"] == "Quote request"
    assert "Homeowners, Auto" in message["body"]
    assert mailer.sent[-1].to == "office@example.com"


def test_quote_form_needs_a_choice(client: FlaskClient) -> None:
    token = csrf_from(client, "/")
    response = client.post("/quote", data={"csrf_token": token, "name": "Pat Doe", "email": "pat@example.com"})
    assert response.status_code == 422
    assert "Choose at least one thing to quote." in response.get_data(as_text=True)


def test_logins_can_be_added_but_not_self_removed(client: FlaskClient, app: Flask) -> None:
    sign_in(client, app)
    token = csrf_from(client, "/portal/users")
    client.post("/portal/users", data={"csrf_token": token, "name": "Glenn Otto", "email": "glenn@example.com", "password": "another long password"})
    with app.app_context():
        agents = {row["email"]: row["id"] for row in store.list_agents(db.get_db())}
    assert "glenn@example.com" in agents
    token = csrf_from(client, "/portal/users")
    client.post(f"/portal/users/{agents['andi@example.com']}/delete", data={"csrf_token": token})
    with app.app_context():
        assert any(row["email"] == "andi@example.com" for row in store.list_agents(db.get_db()))


def test_rotating_headlines_render_and_office_number_leads(client: FlaskClient) -> None:
    page = client.get("/").get_data(as_text=True)
    assert "data-rotator" in page
    assert "Your best insurance policy is a good agent." in page
    assert page.index("(937) 545-6148") < page.index("(937) 610-0088")


def test_old_layouts_gain_new_sections_in_place(app: Flask) -> None:
    with app.app_context():
        connection = db.get_db()
        old_order = [key for key in site.SECTIONS if key != "ribbon"]
        site.save_setting(connection, "sections", {"order": old_order, "hidden": []})
        order, _ = site.section_order(connection)
    assert order.index("ribbon") == order.index("tasks") + 1


def test_time_off_stops_the_calendar_offering_a_day(client: FlaskClient, app: Flask) -> None:
    slot = first_open_slot(client)
    day = slot[:10]
    sign_in(client, app)
    token = csrf_from(client, "/portal/time-off")
    added = client.post("/portal/time-off", data={"csrf_token": token, "starts_on": day, "ends_on": day, "note": "Holiday"})
    assert added.status_code == 302
    page = client.get(f"/appointments?date={day}").get_data(as_text=True)
    assert 'name="slot"' not in page
    assert "We are away on that day" in page


def test_message_reply_is_emailed_and_kept(client: FlaskClient, app: Flask, mailer: LogMailer) -> None:
    with app.app_context():
        message_id = store.create_message(
            db.get_db(), store.NewMessage("Pat Doe", "pat@example.com", "", "A quote", "Please call me.")
        )
        db.get_db().commit()
    sign_in(client, app)
    token = csrf_from(client, "/portal/messages")
    response = client.post(f"/portal/messages/{message_id}/reply", data={"csrf_token": token, "body": "Thanks Pat, we will call."})
    assert response.status_code == 302
    assert mailer.sent[-1].to == "pat@example.com"
    with app.app_context():
        row = store.get_message(db.get_db(), message_id)
    assert row["replied_at"] is not None
    assert row["reply_body"] == "Thanks Pat, we will call."


def test_backup_and_exports_are_downloadable(client: FlaskClient, app: Flask) -> None:
    sign_in(client, app)
    assert client.get("/portal/backup").status_code == 200
    content = client.get("/portal/backup/content.json")
    assert content.status_code == 200
    assert "application/json" in content.headers["Content-Type"]
    assert b'"website"' in content.data
    for path in ("/portal/backup/faqs.csv", "/portal/messages.csv", "/portal/appointments.csv"):
        response = client.get(path)
        assert response.status_code == 200, path
        assert "attachment" in response.headers["Content-Disposition"]


def test_agent_can_change_their_own_password(client: FlaskClient, app: Flask) -> None:
    sign_in(client, app)
    token = csrf_from(client, "/portal/account")
    response = client.post(
        "/portal/account",
        data={
            "csrf_token": token,
            "current_password": "a long test password",
            "new_password": "a longer test password",
            "confirm_password": "a longer test password",
        },
    )
    assert response.status_code == 302
    with app.app_context():
        agent = store.get_agent_by_email(db.get_db(), "andi@example.com")
    from werkzeug.security import check_password_hash as check

    assert check(agent["password_hash"], "a longer test password")


def test_manual_booking_outside_office_hours_is_refused(client: FlaskClient, app: Flask) -> None:
    sign_in(client, app)
    token = csrf_from(client, "/portal/appointments/new")
    with client.application.app_context():
        day = (store.utc_now() + timedelta(days=3)).date().isoformat()
    response = client.post(
        "/portal/appointments/new",
        data={"csrf_token": token, "date": day, "time": "23:30", "name": "Pat Doe", "meeting_kind": "phone"},
    )
    assert response.status_code == 422
    assert "outside office hours" in response.get_data(as_text=True)


def test_init_db_puts_the_office_number_first(app: Flask) -> None:
    with app.app_context():
        connection = db.get_db()
        site.save_setting(connection, "agency", {"phone": "(937) 610-0088", "phone2": "(937) 545-6148"})
        db.initialise(connection)
        agency = site.get_setting(connection, "agency")
    assert agency["phone"] == "(937) 545-6148"
    assert agency["phone2"] == "(937) 610-0088"


def test_faq_arrows_reorder_and_renumber(client: FlaskClient, app: Flask) -> None:
    with app.app_context():
        connection = db.get_db()
        connection.execute("DELETE FROM faqs")
        for question in ("First?", "Second?", "Third?"):
            store.upsert_faq(connection, None, question, "An answer.", store.next_faq_position(connection))
        connection.commit()
    sign_in(client, app)
    with app.app_context():
        faqs = store.list_faqs(db.get_db())
    third = faqs[-1]
    assert client.post(f"/portal/faqs/{third['id']}/up", data={"csrf_token": csrf_from(client, "/portal/faqs")}).status_code == 302
    with app.app_context():
        reordered = store.list_faqs(db.get_db())
    assert [row["question"] for row in reordered] == ["First?", "Third?", "Second?"]
    assert [row["position"] for row in reordered] == [0, 1, 2]


def test_text_settings_save_and_only_send_once(client: FlaskClient, app: Flask) -> None:
    sign_in(client, app)
    token = csrf_from(client, "/portal/settings/texts")
    saved = client.post(
        "/portal/settings/texts",
        data={
            "csrf_token": token,
            "sms_enabled": "on",
            "sms_phone": "(937) 610-0088",
            "sms_reminder_hours": "24",
            "sms_on_booking": "on",
        },
    )
    assert saved.status_code == 302

    with app.app_context():
        connection = db.get_db()
        values = site.get_setting(connection, "notify")
        assert values["sms_enabled"] is True
        assert values["sms_phone"] == "(937) 610-0088"
        assert values["sms_on_request"] is False

        starts = store.utc_now() + timedelta(hours=3)
        store.create_booking(
            connection, store.NewBooking("Pat Doe", "pat@example.com", "", "", starts, "phone"), store.booking_rules(connection)
        )
        connection.commit()

        texter = LogTexter()
        sent, failed = notify.send_due_reminders(
            connection, texter, ZoneInfo("America/New_York"), hours=24, kinds=content.MEETING_KINDS
        )
        assert (sent, failed) == (1, 0)
        assert "Pat Doe" in texter.sent[0][1]
        again, _ = notify.send_due_reminders(
            connection, texter, ZoneInfo("America/New_York"), hours=24, kinds=content.MEETING_KINDS
        )
        assert again == 0


def test_reminder_cron_needs_the_secret(client: FlaskClient) -> None:
    assert client.get("/tasks/reminders").status_code == 403
    assert client.get("/tasks/reminders?token=guess").status_code == 403


def test_holiday_and_custom_palette_change_the_site(client: FlaskClient, app: Flask) -> None:
    sign_in(client, app)
    token = csrf_from(client, "/portal/website/look")
    assert client.post("/portal/website/look", data={"csrf_token": token, "preset": "halloween", "corners": "square"}).status_code == 302
    assert "#3a2a4d" in client.get("/").get_data(as_text=True)

    token = csrf_from(client, "/portal/website/look")
    assert (
        client.post(
            "/portal/website/look",
            data={
                "csrf_token": token,
                "preset": "custom",
                "corners": "soft",
                "custom_primary": "#123456",
                "custom_deep": "#0a0b0c",
                "custom_accent": "#fedcba",
                "custom_on_accent": "#101010",
            },
        ).status_code
        == 302
    )
    page = client.get("/").get_data(as_text=True)
    assert "#123456" in page and "--radius:12px" in page


def test_family_photo_upload_replaces_the_about_photo(client: FlaskClient, app: Flask) -> None:
    sign_in(client, app)
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    token = csrf_from(client, "/portal/website/basics")
    response = client.post(
        "/portal/website/basics",
        data={
            "csrf_token": token,
            "name": "Otto & Associates",
            "city": "Sunbury",
            "region": "OH",
            "phone": "(937) 545-6148",
            "email": "office@example.com",
            "hero_quotes": "A headline worth reading.",
            "hero_intro": "Family-run insurance.",
            "hero_photo": (io.BytesIO(png), "family.png"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 302
    with app.app_context():
        hero = site.get_setting(db.get_db(), "hero")
    assert hero["photo_media_id"]
    page = client.get("/").get_data(as_text=True)
    assert f"/media/{hero['photo_media_id']}" in page
    assert "otto-family.webp" not in page


def test_notes_board_move_and_list(client: FlaskClient, app: Flask) -> None:
    sign_in(client, app)
    token = csrf_from(client, "/portal/notes")
    created = client.post(
        "/portal/notes",
        data={"csrf_token": token, "body": "Call the Hendersons about the boat renewal.", "color": "rose"},
    )
    assert created.status_code == 302

    with app.app_context():
        notes = store.list_notes(db.get_db())
    assert len(notes) == 1
    note = notes[0]
    assert note["color"] == "rose"
    assert "Call the Hendersons" in client.get("/portal/notes").get_data(as_text=True)

    token = csrf_from(client, "/portal/notes")
    moved = client.post(
        f"/portal/notes/{note['id']}/move",
        data={"csrf_token": token, "pos_x": "300", "pos_y": "120", "z_index": "4"},
    )
    assert moved.status_code == 204
    with app.app_context():
        row = db.get_db().execute("SELECT pos_x, pos_y, z_index FROM notes WHERE id = %s", (note["id"],)).fetchone()
    assert (row["pos_x"], row["pos_y"], row["z_index"]) == (300, 120, 4)

    listed = client.get("/portal/notes?view=list").get_data(as_text=True)
    assert "Call the Hendersons" in listed and "note-line" in listed

    # Saving and deleting from the template must carry a token, or the owner gets a 400.
    token = csrf_from(client, "/portal/notes")
    saved = client.post(
        f"/portal/notes/{note['id']}", data={"csrf_token": token, "body": "Call the Hendersons again.", "color": "mint"}
    )
    assert saved.status_code == 302
    with app.app_context():
        assert store.list_notes(db.get_db())[0]["color"] == "mint"

    token = csrf_from(client, "/portal/notes")
    assert client.post(
        f"/portal/notes/{note['id']}/pin", data={"csrf_token": token, "pinned": "yes"}
    ).status_code == 302
    pinned_page = client.get("/portal/notes?view=list").get_data(as_text=True)
    assert "is-pinned" in pinned_page and "Unpin" in pinned_page

    token = csrf_from(client, "/portal/notes")
    assert client.post(f"/portal/notes/{note['id']}/delete", data={"csrf_token": token}).status_code == 302
    with app.app_context():
        assert store.list_notes(db.get_db()) == []


def test_reminder_wording_is_validated_and_saved(client: FlaskClient, app: Flask) -> None:
    sign_in(client, app)
    base = {
        "sms_enabled": "on",
        "sms_phone": "(937) 610-0088",
        "sms_reminder_hours": "24",
        "sms_on_booking": "on",
        "sms_on_request": "on",
        "sms_booking_template": "Booked: {name} on {when}.",
        "sms_request_template": "Request from {name}: {topic}.",
    }
    token = csrf_from(client, "/portal/settings/texts")
    refused = client.post(
        "/portal/settings/texts",
        data={**base, "csrf_token": token, "sms_reminder_template": "Hi {customer}, see you soon."},
    )
    assert refused.status_code == 422
    assert "{customer}" in refused.get_data(as_text=True)

    token = csrf_from(client, "/portal/settings/texts")
    saved = client.post(
        "/portal/settings/texts",
        data={**base, "csrf_token": token, "sms_reminder_template": "Reminder: {name} at {when}."},
    )
    assert saved.status_code == 302
    with app.app_context():
        values = site.get_setting(db.get_db(), "notify")
        assert values["sms_booking_template"] == "Booked: {name} on {when}."
        assert values["sms_reminder_template"] == "Reminder: {name} at {when}."
        # The saved words are the words that go out, with the real details filled in.
        texter = LogTexter()
        assert notify.new_booking(
            db.get_db(), texter, "Mary K.", "Tue Nov 4 at 3:00 pm", "Phone call"
        )
        assert texter.sent[-1][1] == "Booked: Mary K. on Tue Nov 4 at 3:00 pm."
