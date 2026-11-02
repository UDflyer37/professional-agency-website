from __future__ import annotations

import hmac
import secrets
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from flask import Flask, abort, g, redirect, request, session, url_for
from werkzeug.wrappers.response import Response

from otto import store, throttle
from otto.db import get_db

P = ParamSpec("P")
R = TypeVar("R")

CSRF_SESSION_KEY = "csrf_token"
CSRF_FORM_FIELD = "csrf_token"


def csrf_token() -> str:
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def _check_csrf() -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    expected = session.get(CSRF_SESSION_KEY, "")
    submitted = request.form.get(CSRF_FORM_FIELD, "")
    if not expected or not hmac.compare_digest(expected, submitted):
        abort(400, description="This form expired. Go back, reload the page and try again.")


def _load_agent() -> None:
    agent_id = session.get("agent_id")
    g.agent = store.get_agent(get_db(), agent_id) if isinstance(agent_id, int) else None


def login_required(view: Callable[P, R]) -> Callable[P, R | Response]:
    @wraps(view)
    def guarded(*args: P.args, **kwargs: P.kwargs) -> R | Response:
        if g.get("agent") is None:
            return redirect(url_for("portal.login", next=request.path))
        return view(*args, **kwargs)

    return guarded


def _security_headers(response: Response) -> Response:
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' data:; style-src 'self'; style-src-attr 'unsafe-inline'; script-src 'self'; "
        "font-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'",
    )
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if request.path.startswith(("/portal/", "/tasks/")):
        # Signed-in pages carry a session cookie and the office's own records. Without this
        # Flask marks them cacheable, and a shared cache or the browser's back button could
        # hand one person's page to the next.
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
    return response


def register(app: Flask) -> None:
    app.before_request(_check_csrf)
    app.before_request(throttle.guard)
    app.before_request(_load_agent)
    app.after_request(_security_headers)
    app.jinja_env.globals["csrf_token"] = csrf_token
