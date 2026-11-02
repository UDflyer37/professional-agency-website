from __future__ import annotations

import csv
import getpass
import logging
from datetime import timedelta
from pathlib import Path

import click
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash

from otto import db, portal, portal_site, public, security, store  # noqa: F401  (portal_site registers routes)
from otto.config import Settings
from otto.mailer import LogMailer, Mailer, SmtpMailer
from otto.sms import LogTexter, Texter, TwilioTexter

__version__ = "3.2.1"

PUBLIC_STATIC = Path(__file__).resolve().parent.parent / "public" / "static"


def create_app(settings: Settings | None = None, mailer: Mailer | None = None, texter: Texter | None = None) -> Flask:
    settings = settings or Settings.from_env()

    # Static files live in /public so Vercel serves them from its CDN at /static/...;
    # Flask serves the same folder when running locally.
    app = Flask(__name__, static_folder=str(PUBLIC_STATIC), static_url_path="/static")
    app.config.update(
        OTTO=settings,
        SECRET_KEY=settings.secret_key,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=settings.secure_cookies,
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
        MAX_CONTENT_LENGTH=4 * 1024 * 1024,
    )
    # Most hosts terminate TLS at a proxy; trust exactly one hop for scheme and client IP.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)  # type: ignore[method-assign]

    app.extensions["otto_mailer"] = mailer or (SmtpMailer(settings.smtp) if settings.smtp else LogMailer())
    app.extensions["otto_texter"] = texter or (TwilioTexter(settings.sms) if settings.sms else LogTexter())
    if settings.smtp is None:
        app.logger.warning("OTTO_SMTP_HOST is not set: emails will be logged, not sent.")
    if settings.sms is None:
        app.logger.info("Twilio is not set: reminder texts will be logged, not sent.")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    @app.context_processor
    def _asset_version() -> dict[str, str]:
        # Stamped on the CSS and JS URLs so a deploy never leaves a visitor with an
        # old stylesheet; the value only changes when a static file changes.
        newest = max((path.stat().st_mtime for path in PUBLIC_STATIC.rglob("*") if path.is_file()), default=0)
        return {"asset_version": str(int(newest))}

    db.register(app)
    security.register(app)
    app.register_blueprint(public.bp)
    app.register_blueprint(portal.bp)
    _register_commands(app)
    return app


def _register_commands(app: Flask) -> None:
    @app.cli.command("init-db")
    def init_db_command() -> None:
        """Create tables and default hours, booking rules and FAQs. Safe to run again."""
        db.initialise(db.get_db())
        click.echo("Database ready.")

    @app.cli.command("create-agent")
    @click.argument("email")
    @click.argument("name")
    def create_agent_command(email: str, name: str) -> None:
        """Create or reset a portal login. Prompts for the password."""
        password = getpass.getpass("Password (12+ characters): ")
        if len(password) < 12:
            raise click.ClickException("Use at least 12 characters.")
        if password != getpass.getpass("Repeat password: "):
            raise click.ClickException("The passwords did not match.")
        store.upsert_agent(db.get_db(), email.strip().lower(), name.strip(), generate_password_hash(password))
        click.echo(f"Portal login ready for {email}.")

    @app.cli.command("import-faqs")
    @click.argument("csv_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
    @click.option("--replace", is_flag=True, help="Delete the existing FAQs first.")
    def import_faqs_command(csv_path: Path, replace: bool) -> None:
        """Load FAQs from an Anvil CSV export with 'question' and 'answer' columns."""
        connection = db.get_db()
        with csv_path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            missing = {"question", "answer"} - set(reader.fieldnames or [])
            if missing:
                raise click.ClickException(f"{csv_path.name} is missing columns: {', '.join(sorted(missing))}")
            rows = [(row["question"].strip(), row["answer"].strip()) for row in reader if row["question"].strip()]

        with connection.transaction():
            if replace:
                connection.execute("DELETE FROM faqs")
            with connection.cursor() as cursor:
                cursor.executemany(
                    "INSERT INTO faqs (question, answer, position) VALUES (%s, %s, %s)",
                    [(question, answer, position) for position, (question, answer) in enumerate(rows)],
                )
        click.echo(f"Imported {len(rows)} FAQs from {csv_path.name}.")
