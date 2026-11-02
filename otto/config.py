from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from zoneinfo import ZoneInfo


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class SmtpSettings:
    host: str
    port: int
    username: str
    password: str
    sender: str
    use_ssl: bool


@dataclass(frozen=True)
class SmsSettings:
    account_sid: str
    auth_token: str
    sender: str


@dataclass(frozen=True)
class Settings:
    secret_key: str
    database_url: str
    agency_email: str
    timezone: ZoneInfo
    smtp: SmtpSettings | None
    secure_cookies: bool
    sms: SmsSettings | None = None
    cron_secret: str = ""

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        env = os.environ if environ is None else environ

        secret_key = env.get("OTTO_SECRET_KEY", "")
        if len(secret_key) < 32:
            raise ConfigError(
                "OTTO_SECRET_KEY must be set to at least 32 random characters. "
                "Generate one with: python -c 'import secrets; print(secrets.token_hex(32))'"
            )

        agency_email = env.get("OTTO_AGENCY_EMAIL", "")
        if "@" not in agency_email:
            raise ConfigError("OTTO_AGENCY_EMAIL must be the inbox that receives bookings and messages.")

        # Vercel's Neon integration sets DATABASE_URL; OTTO_DATABASE_URL wins if both exist.
        database_url = env.get("OTTO_DATABASE_URL") or env.get("DATABASE_URL", "")
        if not database_url.startswith(("postgres://", "postgresql://")):
            raise ConfigError("Set DATABASE_URL (or OTTO_DATABASE_URL) to a PostgreSQL connection string.")

        return cls(
            secret_key=secret_key,
            database_url=database_url,
            agency_email=agency_email,
            timezone=ZoneInfo(env.get("OTTO_TIMEZONE", "America/New_York")),
            smtp=_smtp_from_env(env),
            secure_cookies=env.get("OTTO_SECURE_COOKIES", "true").lower() != "false",
            sms=_sms_from_env(env),
            cron_secret=env.get("CRON_SECRET", ""),
        )


def _smtp_from_env(env: Mapping[str, str]) -> SmtpSettings | None:
    host = env.get("OTTO_SMTP_HOST")
    if not host:
        return None

    missing = [key for key in ("OTTO_SMTP_USERNAME", "OTTO_SMTP_PASSWORD", "OTTO_SMTP_SENDER") if not env.get(key)]
    if missing:
        raise ConfigError(f"OTTO_SMTP_HOST is set but these are missing: {', '.join(missing)}")

    try:
        port = int(env.get("OTTO_SMTP_PORT", "587"))
    except ValueError as exc:
        raise ConfigError("OTTO_SMTP_PORT must be a number.") from exc

    return SmtpSettings(
        host=host,
        port=port,
        username=env["OTTO_SMTP_USERNAME"],
        password=env["OTTO_SMTP_PASSWORD"],
        sender=env["OTTO_SMTP_SENDER"],
        use_ssl=port == 465,
    )


def _sms_from_env(env: Mapping[str, str]) -> SmsSettings | None:
    """Twilio credentials. With any of the three missing, texts are logged instead."""
    sid = env.get("OTTO_TWILIO_ACCOUNT_SID")
    token = env.get("OTTO_TWILIO_AUTH_TOKEN")
    sender = env.get("OTTO_TWILIO_FROM")
    if not (sid and token and sender):
        return None
    return SmsSettings(account_sid=sid, auth_token=token, sender=sender)
