from __future__ import annotations

from importlib.resources import files
from typing import Any

import psycopg
from flask import Flask, current_app, g
from psycopg.rows import dict_row

Connection = psycopg.Connection[dict[str, Any]]
Row = dict[str, Any]

DEFAULT_HOURS = [(weekday, weekday < 5, "09:30", "17:00") for weekday in range(7)]

# Written from the answers already on the old site so nothing here is invented.
# Agents can edit or replace them from the portal.
DEFAULT_FAQS = [
    (
        "What does an independent agency do differently?",
        "We are not tied to one insurance company. We quote your home, car or business with "
        "the companies we represent and show you the options side by side, so you choose the "
        "coverage and the price, and you understand what you are buying.",
    ),
    (
        "Can I meet with you outside office hours?",
        "Yes. The office is open 9:30 to 5:00 Monday to Friday, and we see clients in the "
        "evening and at weekends by appointment. Book a time online or call us.",
    ),
    (
        "How do I get my proof of insurance card?",
        "Send a request from the contact page and choose Proof of insurance card. The same "
        "form handles declarations pages, certificates of insurance and verification letters.",
    ),
    (
        "Who do I call when I have a claim?",
        "Call your insurance company's claims line first; the numbers for every company we "
        "represent are on our home page. Then call us, and we will help you through it.",
    ),
    (
        "Can you insure a driver who needs an SR22?",
        "Yes. We place preferred, standard and non-standard auto policies, and we file SR22 "
        "bonds for drivers who need one.",
    ),
    (
        "Do you insure small businesses?",
        "Yes. We write business package policies, key person policies, business auto and "
        "contractor packages, for one-person shops and established family firms alike.",
    ),
]


def connect(database_url: str) -> Connection:
    # prepare_threshold=None: Neon's pooled endpoint runs PgBouncer in transaction mode,
    # which breaks server-side prepared statements.
    return psycopg.connect(database_url, row_factory=dict_row, prepare_threshold=None, connect_timeout=10)


def get_db() -> Connection:
    if "db" not in g:
        g.db = connect(current_app.config["OTTO"].database_url)
    return g.db


def close_db(error: BaseException | None = None) -> None:
    connection: Connection | None = g.pop("db", None)
    if connection is None:
        return
    try:
        if error is None:
            connection.commit()
        else:
            connection.rollback()
    finally:
        connection.close()


def initialise(connection: Connection) -> None:
    schema = files("otto").joinpath("schema.sql").read_text(encoding="utf-8")
    with connection.transaction():
        # Serialise concurrent first runs so seed rows are inserted once.
        connection.execute("SELECT pg_advisory_xact_lock(7461)")
        connection.execute(schema)
        with connection.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO office_hours (weekday, is_open, opens_at, closes_at) VALUES (%s, %s, %s, %s)"
                " ON CONFLICT (weekday) DO NOTHING",
                DEFAULT_HOURS,
            )
        connection.execute(
            "INSERT INTO booking_rules (id, slot_minutes, days_ahead, per_slot) VALUES (1, 30, 30, 1)"
            " ON CONFLICT (id) DO NOTHING"
        )
        if connection.execute("SELECT 1 FROM faqs LIMIT 1").fetchone() is None:
            with connection.cursor() as cursor:
                cursor.executemany(
                    "INSERT INTO faqs (question, answer, position) VALUES (%s, %s, %s)",
                    [(question, answer, position) for position, (question, answer) in enumerate(DEFAULT_FAQS)],
                )
        from otto import site  # imported here: site depends on this module's Connection type

        site.seed(connection)


def register(app: Flask) -> None:
    app.teardown_appcontext(close_db)
