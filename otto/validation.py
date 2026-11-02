from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from urllib.parse import urlparse

EMAIL_PATTERN = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")
PHONE_DIGITS = re.compile(r"\d")


@dataclass
class FormErrors:
    by_field: dict[str, str] = field(default_factory=dict)

    def add(self, name: str, message: str) -> None:
        self.by_field.setdefault(name, message)

    def __bool__(self) -> bool:
        return bool(self.by_field)


def clean_text(form: Mapping[str, str], name: str, *, max_length: int) -> str:
    return " ".join(form.get(name, "").split())[:max_length]


def clean_block(form: Mapping[str, str], name: str, *, max_length: int) -> str:
    return form.get(name, "").strip().replace("\r\n", "\n")[:max_length]


def require_name(value: str, errors: FormErrors, name: str = "name") -> None:
    if len(value) < 2:
        errors.add(name, "Tell us your name.")


def require_email(value: str, errors: FormErrors, name: str = "email") -> None:
    if not EMAIL_PATTERN.match(value):
        errors.add(name, "Enter an email address like name@example.com.")


def optional_phone(value: str, errors: FormErrors, name: str = "phone") -> None:
    if value and len(PHONE_DIGITS.findall(value)) not in (10, 11):
        errors.add(name, "Enter a 10-digit phone number, or leave it blank.")


def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def parse_slot(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return None
    return moment if moment.tzinfo else None


def safe_link(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme in {"http", "https"}:
        return bool(parsed.netloc)
    return parsed.scheme in {"tel", "mailto"} and bool(parsed.path)


def looks_like_bot(form: Mapping[str, str]) -> bool:
    # Hidden field that people never see; simple form-filling bots fill everything.
    return bool(form.get("website", "").strip())
