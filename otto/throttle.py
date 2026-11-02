"""Limits on the forms anyone on the internet can post to.

A booking writes a row, sends two emails and, once texts are switched on, a text message
that costs money. Nothing upstream stops a script from filling the inbox, draining the
Twilio balance or booking every free slot for the next month. So each form gets a budget
per visitor, plus a larger shared budget that a single visitor cannot exhaust alone.

Counters live in Postgres. Vercel answers each request from a fresh function instance, so
an in-memory counter would be forgotten between requests. Only a keyed hash of the
visitor's address is stored, never the address, so the table is not a log of who visited.

If the counter cannot be written, the request is allowed through: a broken limit must not
stop a real client from reaching the office.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import random
from datetime import UTC, datetime

import psycopg
from flask import abort, current_app, request

from otto.db import Connection, get_db

log = logging.getLogger(__name__)

WINDOW_SECONDS = 600

# endpoint -> (per visitor, shared across everyone) in one window.
LIMITS: dict[str, tuple[int, int]] = {
    "public.appointments": (5, 25),
    "public.contact": (6, 30),
    "public.quote": (6, 30),
    "portal.login": (10, 60),
}


def _window_start() -> datetime:
    now = int(datetime.now(UTC).timestamp())
    return datetime.fromtimestamp(now // WINDOW_SECONDS * WINDOW_SECONDS, UTC)


def _bucket(scope: str, ident: str) -> str:
    """A stable key per visitor per scope, salted with the app secret."""
    secret = str(current_app.config["SECRET_KEY"]).encode()
    return hmac.new(secret, f"{scope}:{ident}".encode(), hashlib.sha256).hexdigest()[:40]


def _consume(connection: Connection, bucket: str, limit: int, window_start: datetime) -> bool:
    row = connection.execute(
        "INSERT INTO request_throttle (bucket, window_start, hits) VALUES (%s, %s, 1)"
        " ON CONFLICT (bucket, window_start) DO UPDATE SET hits = request_throttle.hits + 1"
        " RETURNING hits",
        (bucket, window_start),
    ).fetchone()
    # Commit straight away: a refused request is rolled back at teardown, and the count
    # it just spent has to survive that or every attempt would look like the first.
    connection.commit()
    return row is not None and int(row["hits"]) <= limit


def _forget_old_windows(connection: Connection) -> None:
    if random.random() >= 0.02:
        return
    connection.execute("DELETE FROM request_throttle WHERE window_start < now() - interval '1 day'")
    connection.commit()


def guard() -> None:
    """Refuse a POST that has used up its budget. Registered as a before_request hook."""
    if request.method != "POST":
        return
    scope = request.endpoint or ""
    limits = LIMITS.get(scope)
    if limits is None:
        return

    per_visitor, shared = limits
    ident = request.remote_addr or "unknown"
    window_start = _window_start()
    try:
        connection = get_db()
        allowed = _consume(connection, _bucket(scope, ident), per_visitor, window_start) and _consume(
            connection, _bucket(scope, "*"), shared, window_start
        )
        _forget_old_windows(connection)
    except psycopg.Error:
        log.exception("Rate limiting is unavailable; letting the request through")
        return

    if not allowed:
        log.warning("Rate limit reached on %s", scope)
        abort(
            429,
            description=(
                "That is a lot of messages from one place in a short time. "
                "Give it a few minutes and try again, or call the office and we will help you now."
            ),
        )
