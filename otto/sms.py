"""Text messages to the agent's phone.

Twilio's REST API is one HTTPS form post, so no extra package is needed. When the
three Twilio settings are missing the office simply gets no texts: requests and
bookings still reach the portal and the inbox, and the portal says why.
"""

from __future__ import annotations

import base64
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Protocol

from otto.config import SmsSettings

log = logging.getLogger(__name__)


class SmsError(RuntimeError):
    pass


class Texter(Protocol):
    def send(self, to: str, body: str) -> None: ...


@dataclass
class TwilioTexter:
    settings: SmsSettings
    timeout_seconds: float = 12.0

    def send(self, to: str, body: str) -> None:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.settings.account_sid}/Messages.json"
        payload = urllib.parse.urlencode(
            {"To": to, "From": self.settings.sender, "Body": body[:1500]}
        ).encode()
        token = base64.b64encode(
            f"{self.settings.account_sid}:{self.settings.auth_token}".encode()
        ).decode()
        request = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Basic {token}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                if response.status >= 300:
                    raise SmsError(f"Twilio answered {response.status}")
        except (urllib.error.URLError, OSError) as exc:
            raise SmsError(f"Could not text {to}: {exc}") from exc


@dataclass
class LogTexter:
    """Used when Twilio is not configured: the text is written to the log instead."""

    sent: list[tuple[str, str]] = field(default_factory=list)

    def send(self, to: str, body: str) -> None:
        self.sent.append((to, body))
        log.warning("Text messages are not configured; message to %s not sent. %s", to, body)


def send_quietly(texter: Texter, to: str, body: str) -> bool:
    """Send a text, and never let an outage break the visitor's booking."""
    if not to:
        return False
    try:
        texter.send(to, body)
    except SmsError:
        log.exception("Text message delivery failed")
        return False
    return True


def to_e164(value: str) -> str:
    """Twilio wants +19376100088 even when the office types (937) 610-0088."""
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 10:
        return "+1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    return "+" + digits if digits else ""


def reminder_body(client_name: str, when: str, kind: str) -> str:
    return f"Otto & Associates: {client_name} is booked {when} ({kind.lower()}). Reply to this text or call the office to change it."
