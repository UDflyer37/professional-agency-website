from __future__ import annotations

import logging
import smtplib
import ssl
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Protocol

from otto.config import SmtpSettings

log = logging.getLogger(__name__)


class MailError(RuntimeError):
    pass


@dataclass(frozen=True)
class Email:
    to: str
    subject: str
    body: str
    reply_to: str | None = None


class Mailer(Protocol):
    def send(self, email: Email) -> None: ...


@dataclass
class SmtpMailer:
    settings: SmtpSettings
    sender_name: str = "Otto & Associates"
    timeout_seconds: float = 15.0

    def send(self, email: Email) -> None:
        message = EmailMessage()
        message["From"] = f"{self.sender_name} <{self.settings.sender}>"
        message["To"] = email.to
        message["Subject"] = email.subject
        if email.reply_to:
            message["Reply-To"] = email.reply_to
        message.set_content(email.body)

        context = ssl.create_default_context()
        try:
            if self.settings.use_ssl:
                with smtplib.SMTP_SSL(
                    self.settings.host, self.settings.port, timeout=self.timeout_seconds, context=context
                ) as smtp:
                    smtp.login(self.settings.username, self.settings.password)
                    smtp.send_message(message)
            else:
                with smtplib.SMTP(self.settings.host, self.settings.port, timeout=self.timeout_seconds) as smtp:
                    smtp.starttls(context=context)
                    smtp.login(self.settings.username, self.settings.password)
                    smtp.send_message(message)
        except (smtplib.SMTPException, OSError) as exc:
            raise MailError(f"Could not send '{email.subject}' to {email.to} via {self.settings.host}: {exc}") from exc


@dataclass
class LogMailer:
    """Used when SMTP is not configured: the message is written to the log instead of sent."""

    sent: list[Email] = field(default_factory=list)

    def send(self, email: Email) -> None:
        self.sent.append(email)
        log.warning("SMTP not configured; email to %s not sent. Subject: %s", email.to, email.subject)


def send_quietly(mailer: Mailer, email: Email) -> bool:
    """Send, and on failure log with context instead of failing the visitor's request.

    The booking or message is already saved and visible in the portal, so a mail outage
    must not lose it or show the visitor an error for something that did succeed.
    """
    try:
        mailer.send(email)
    except MailError:
        log.exception("Email delivery failed")
        return False
    return True
