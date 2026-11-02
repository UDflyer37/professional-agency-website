"""Website content the agents edit in the portal.

Settings are small JSON documents keyed by name; repeating things (companies, coverage,
people, reviews) are rows. Every value has a default here so a fresh database shows a
complete site, and a missing or partial setting never breaks a page.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from psycopg.types.json import Jsonb

from otto import content
from otto.db import Connection

THEMES: dict[str, dict[str, str]] = {
    "navy-gold": {"label": "Navy and gold", "primary": "#353d61", "deep": "#232946", "accent": "#f2c14e", "on_accent": "#1d2240"},
    "navy-sky": {"label": "Navy and sky", "primary": "#2e3f6e", "deep": "#1d2a4d", "accent": "#8cc8f0", "on_accent": "#10223d"},
    "forest-sun": {"label": "Forest and sun", "primary": "#25483b", "deep": "#183128", "accent": "#efb84a", "on_accent": "#1a2a22"},
    "slate-mint": {"label": "Slate and mint", "primary": "#2f3742", "deep": "#1e242c", "accent": "#8fd8b9", "on_accent": "#14251e"},
    # Seasonal sets the owner can switch on for a few weeks and switch back.
    "christmas": {"label": "Christmas", "primary": "#1d4433", "deep": "#12301f", "accent": "#c6322c", "on_accent": "#fff7ef"},
    "halloween": {"label": "Halloween", "primary": "#3a2a4d", "deep": "#241a33", "accent": "#f08a24", "on_accent": "#241505"},
    "july4": {"label": "Fourth of July", "primary": "#1f3468", "deep": "#14224a", "accent": "#cf3a34", "on_accent": "#fff6f2"},
    "thanksgiving": {"label": "Thanksgiving", "primary": "#5a3620", "deep": "#3a2113", "accent": "#e09a4a", "on_accent": "#2a1608"},
}

CUSTOM_THEME_DEFAULT = {"primary": "#353d61", "deep": "#232946", "accent": "#f2c14e", "on_accent": "#1d2240"}
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

CORNERS = {"rounded": ("Rounded", "22px", "14px"), "soft": ("Soft", "12px", "8px"), "square": ("Square", "2px", "2px")}

# Home page sections in their default order. Keys are referenced by templates and the portal.
SECTIONS: dict[str, str] = {
    "tasks": "Quick tasks under the top banner",
    "ribbon": "Scrolling ribbon of what we insure",
    "companies": "Company logos strip",
    "coverage": "What we cover",
    "quote": "Quote request",
    "claims": "Claims numbers",
    "documents": "Document requests",
    "about": "About Glenn and Andi",
    "reviews": "Client reviews",
    "faq": "Questions and answers",
    "contact": "Contact and hours",
}

# One plain sentence per section, shown beside the small picture in the reorder list.
SECTION_HINTS: dict[str, str] = {
    "tasks": "Four numbered shortcuts on a dark band.",
    "ribbon": "A slanted strip of what you insure, moving slowly.",
    "companies": "The carrier logos, scrolling sideways.",
    "coverage": "An openable row for each kind of cover.",
    "quote": "The quote request form.",
    "claims": "The claims steps and the company rolodex.",
    "documents": "A shelf of documents clients can request.",
    "about": "Your story, the family photo and your portraits.",
    "reviews": "One client quote at a time.",
    "faq": "Openable questions and answers.",
    "contact": "Phones, hours and the map link.",
}

ILLUSTRATIONS = {
    "home": "House",
    "car": "Car",
    "boat": "Boat",
    "umbrella": "Umbrella",
    "business": "Storefront",
    "shield": "Shield",
}

DEFAULT_SETTINGS: dict[str, dict[str, Any]] = {
    "agency": {
        "name": content.AGENCY.name,
        "street": content.AGENCY.street,
        "city": content.AGENCY.city,
        "region": content.AGENCY.region,
        "postcode": content.AGENCY.postcode,
        "phone": content.AGENCY.phone_display,
        "phone2": content.AGENCY.second_phone_display,
        "email": content.AGENCY.email,
        "show_street": True,
    },
    "hero": {
        "title": "Appreciated, not tolerated.",
        "quotes": [
            "Appreciated, not tolerated.",
            "Your best insurance policy is a good agent.",
            "It’s about trust, service and you.",
            "Eight companies. Two people who pick up.",
        ],
        "intro": (
            "Otto & Associates is a family-run independent insurance agency in Sunbury, Ohio. "
            "We compare eight companies for your home, car and business, and we stay with you when you have a claim."
        ),
        "photo_media_id": None,
    },
    "announcement": {"enabled": False, "text": "", "link_label": "", "link_url": ""},
    "theme": {"preset": "navy-gold", "corners": "rounded", "custom": dict(CUSTOM_THEME_DEFAULT)},
    "sections": {"order": list(SECTIONS), "hidden": []},
    "notify": {
        "sms_enabled": False,
        "sms_phone": "",
        "sms_reminder_hours": 24,
        "sms_on_booking": True,
        "sms_on_request": True,
        "sms_booking_template": "New appointment: {name}, {when} ({kind}).",
        "sms_request_template": "New website request: {name} asked about {topic}.",
        "sms_reminder_template": (
            "Otto & Associates: {name} is booked {when} ({kind}). "
            "Reply to this text or call the office to change it."
        ),
    },
}


@dataclass(frozen=True)
class AgencyInfo:
    name: str
    street: str
    city: str
    region: str
    postcode: str
    phone: str
    phone2: str
    email: str
    show_street: bool

    @property
    def phone_dial(self) -> str:
        return dial(self.phone)

    @property
    def phone2_dial(self) -> str:
        return dial(self.phone2)

    @property
    def map_url(self) -> str:
        query = f"{self.street} {self.city} {self.region} {self.postcode}" if self.show_street else f"{self.city} {self.region}"
        return "https://www.google.com/maps/search/?api=1&query=" + re.sub(r"\s+", "+", query.strip())

    @property
    def place(self) -> str:
        return f"{self.city}, {self.region}"


@dataclass(frozen=True)
class Site:
    agency: AgencyInfo
    hero: dict[str, Any]
    announcement: dict[str, Any]
    theme: dict[str, str]
    corners: tuple[str, str, str]
    sections: list[str]
    carriers: list[dict[str, Any]] = field(default_factory=list)
    coverage: list[dict[str, Any]] = field(default_factory=list)
    team: list[dict[str, Any]] = field(default_factory=list)
    testimonials: list[dict[str, Any]] = field(default_factory=list)

    @property
    def theme_style(self) -> str:
        """CSS custom properties for the chosen look, applied on the <html> element."""
        return (
            f"--primary:{self.theme['primary']};--primary-deep:{self.theme['deep']};"
            f"--accent:{self.theme['accent']};--on-accent:{self.theme['on_accent']};"
            f"--radius:{self.corners[1]};--radius-sm:{self.corners[2]}"
        )


def dial(display: str) -> str:
    digits = re.sub(r"\D", "", display)
    if len(digits) == 10:
        return "+1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    return digits


def get_setting(connection: Connection, key: str) -> dict[str, Any]:
    row = connection.execute("SELECT value FROM site_settings WHERE key = %s", (key,)).fetchone()
    merged = dict(DEFAULT_SETTINGS[key])
    if row and isinstance(row["value"], dict):
        merged.update({k: v for k, v in row["value"].items() if k in merged})
    return merged


def save_setting(connection: Connection, key: str, value: dict[str, Any]) -> None:
    if key not in DEFAULT_SETTINGS:
        raise KeyError(f"Unknown setting {key!r}")
    allowed = {k: v for k, v in value.items() if k in DEFAULT_SETTINGS[key]}
    connection.execute(
        "INSERT INTO site_settings (key, value) VALUES (%s, %s)"
        " ON CONFLICT (key) DO UPDATE SET value = excluded.value, updated_at = now()",
        (key, Jsonb({**get_setting(connection, key), **allowed})),
    )


def section_order(connection: Connection) -> tuple[list[str], set[str]]:
    stored = get_setting(connection, "sections")
    order = [key for key in stored.get("order", []) if key in SECTIONS]
    # Sections added in a later release slot in after their default neighbour,
    # so a saved layout keeps its order and still gains the new section.
    defaults = list(SECTIONS)
    for key in defaults:
        if key in order:
            continue
        before = defaults[: defaults.index(key)]
        anchor = next((k for k in reversed(before) if k in order), None)
        order.insert(order.index(anchor) + 1 if anchor else 0, key)
    hidden = {key for key in stored.get("hidden", []) if key in SECTIONS}
    return order, hidden


def _custom_theme(stored: object) -> dict[str, str]:
    """A hand-picked palette, with any missing or malformed colour falling back safely."""
    custom = stored if isinstance(stored, dict) else {}
    theme = {key: CUSTOM_THEME_DEFAULT[key] for key in CUSTOM_THEME_DEFAULT}
    for key in theme:
        value = custom.get(key)
        if isinstance(value, str) and HEX.match(value):
            theme[key] = value.lower()
    theme["label"] = "Your own colours"
    return theme


def load(connection: Connection, *, include_hidden: bool = False) -> Site:
    agency = get_setting(connection, "agency")
    theme_setting = get_setting(connection, "theme")
    order, hidden = section_order(connection)
    visible_only = "" if include_hidden else " WHERE visible"
    return Site(
        agency=AgencyInfo(**{k: agency[k] for k in AgencyInfo.__dataclass_fields__}),
        hero=get_setting(connection, "hero"),
        announcement=get_setting(connection, "announcement"),
        theme=(
            _custom_theme(theme_setting.get("custom"))
            if theme_setting["preset"] == "custom"
            else THEMES.get(theme_setting["preset"], THEMES["navy-gold"])
        ),
        corners=CORNERS.get(theme_setting["corners"], CORNERS["rounded"]),
        sections=[key for key in order if include_hidden or key not in hidden],
        carriers=connection.execute(f"SELECT * FROM carriers{visible_only} ORDER BY position, id").fetchall(),
        coverage=connection.execute(f"SELECT * FROM coverage{visible_only} ORDER BY position, id").fetchall(),
        team=connection.execute(f"SELECT * FROM team{visible_only} ORDER BY position, id").fetchall(),
        testimonials=connection.execute(f"SELECT * FROM testimonials{visible_only} ORDER BY position, id").fetchall(),
    )


def seed(connection: Connection) -> None:
    """Fill empty content tables from the defaults in content.py. Safe to run repeatedly."""
    _fix_swapped_phones(connection)
    # 2.2 replaced the round headshot cut-outs with rectangular portraits.
    connection.execute(
        "UPDATE team SET photo_static = replace(photo_static, '-otto.webp', '-otto-portrait.webp')"
        " WHERE photo_static IN ('img/andi-otto.webp', 'img/glenn-otto.webp')"
    )
    if connection.execute("SELECT 1 FROM carriers LIMIT 1").fetchone() is None:
        with connection.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO carriers (name, website, claims_phone, billing_phone, logo_static, logo_height, position)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s)",
                [
                    (c.name, c.website, c.claims_display, c.billing_display, f"img/carriers/{c.slug}.png", c.logo_height, i)
                    for i, c in enumerate(content.CARRIERS)
                ],
            )
    if connection.execute("SELECT 1 FROM coverage LIMIT 1").fetchone() is None:
        art = {"home": "home", "auto": "car", "toys": "boat", "umbrella": "umbrella", "business": "business"}
        with connection.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO coverage (name, headline, summary, items, illustration, position)"
                " VALUES (%s, %s, %s, %s, %s, %s)",
                [
                    (c.name, c.headline, c.summary, Jsonb(list(c.lines)), art.get(c.slug, "shield"), i)
                    for i, c in enumerate(content.COVERAGE)
                ],
            )
    if connection.execute("SELECT 1 FROM team LIMIT 1").fetchone() is None:
        with connection.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO team (name, role, bio, photo_static, position) VALUES (%s, %s, %s, %s, %s)",
                [
                    (
                        "Andi Otto",
                        "Founder",
                        "Grew up in Tucson, Arizona, and served in the U.S. Air Force. Before insurance she ran "
                        "offices and managed materials, which is why your paperwork gets done.",
                        "img/andi-otto-portrait.webp",
                        0,
                    ),
                    (
                        "Glenn Otto",
                        "Co-founder",
                        "Grew up in Beavercreek, Ohio, and served in the U.S. Army. Years in construction, auto "
                        "repair and roofing mean he knows a claim from your side of it.",
                        "img/glenn-otto-portrait.webp",
                        1,
                    ),
                ],
            )


def _next_position(connection: Connection, table: str) -> int:
    row = connection.execute(f"SELECT COALESCE(MAX(position), -1) + 1 AS n FROM {table}").fetchone()
    return int(row["n"]) if row else 0


EDITABLE_TABLES = ("carriers", "coverage", "team", "testimonials")


def move(connection: Connection, table: str, row_id: int, direction: int) -> None:
    """Swap a row with its neighbour in display order. direction is -1 (up) or 1 (down)."""
    if table not in EDITABLE_TABLES:
        raise ValueError(f"Cannot reorder {table!r}")
    rows = connection.execute(f"SELECT id FROM {table} ORDER BY position, id").fetchall()
    ids = [row["id"] for row in rows]
    if row_id not in ids:
        return
    index = ids.index(row_id)
    target = index + direction
    if not 0 <= target < len(ids):
        return
    ids[index], ids[target] = ids[target], ids[index]
    with connection.cursor() as cursor:
        cursor.executemany(f"UPDATE {table} SET position = %s WHERE id = %s", [(i, rid) for i, rid in enumerate(ids)])


def toggle(connection: Connection, table: str, row_id: int) -> None:
    if table not in EDITABLE_TABLES:
        raise ValueError(f"Cannot toggle {table!r}")
    connection.execute(f"UPDATE {table} SET visible = NOT visible WHERE id = %s", (row_id,))


def delete(connection: Connection, table: str, row_id: int) -> None:
    if table not in EDITABLE_TABLES:
        raise ValueError(f"Cannot delete from {table!r}")
    connection.execute(f"DELETE FROM {table} WHERE id = %s", (row_id,))


def save_row(connection: Connection, table: str, row_id: int | None, values: dict[str, Any]) -> int:
    columns = {
        "carriers": ("name", "website", "claims_phone", "billing_phone", "logo_height", "logo_media_id"),
        "coverage": ("name", "headline", "summary", "items", "illustration"),
        "team": ("name", "role", "bio", "photo_media_id"),
        "testimonials": ("quote", "name", "detail"),
    }[table]
    data = {k: (Jsonb(v) if k == "items" else v) for k, v in values.items() if k in columns}
    if row_id is None:
        data["position"] = _next_position(connection, table)
        names = ", ".join(data)
        placeholders = ", ".join(["%s"] * len(data))
        row = connection.execute(
            f"INSERT INTO {table} ({names}) VALUES ({placeholders}) RETURNING id", list(data.values())
        ).fetchone()
        return int(row["id"]) if row else 0
    if data:
        assignments = ", ".join(f"{name} = %s" for name in data)
        connection.execute(f"UPDATE {table} SET {assignments} WHERE id = %s", [*data.values(), row_id])
    return row_id


def get_row(connection: Connection, table: str, row_id: int) -> dict[str, Any] | None:
    if table not in EDITABLE_TABLES:
        raise ValueError(f"Unknown table {table!r}")
    return connection.execute(f"SELECT * FROM {table} WHERE id = %s", (row_id,)).fetchone()


def _fix_swapped_phones(connection: Connection) -> None:
    """Earlier versions saved the cell as the main number. Put (937) 610-0088 first, once."""
    row = connection.execute("SELECT value FROM site_settings WHERE key = 'agency'").fetchone()
    if not row:
        return
    value = dict(row["value"])
    if value.get("phone") == "(937) 545-6148" and value.get("phone2") == "(937) 610-0088":
        value["phone"], value["phone2"] = value["phone2"], value["phone"]
        connection.execute("UPDATE site_settings SET value = %s WHERE key = 'agency'", (Jsonb(value),))
