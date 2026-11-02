"""Portal screens for changing the public website and managing agent logins.

Each kind of repeating content (companies, coverage, people, reviews) is described once in
KINDS, and one generic list screen and one generic edit form serve all of them, so adding a
field means adding a line here rather than a new template.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flask import abort, flash, g, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash
from werkzeug.wrappers.response import Response

from otto import media, site, store
from otto.db import get_db
from otto.portal import bp
from otto.security import login_required
from otto.validation import EMAIL_PATTERN, clean_block, clean_text, safe_link


@dataclass(frozen=True)
class Field:
    name: str
    label: str
    kind: str = "text"  # text, textarea, lines, number, url, image, select
    help: str = ""
    required: bool = False
    max_length: int = 300


@dataclass(frozen=True)
class Kind:
    table: str
    title: str
    singular: str
    plural: str
    intro: str
    fields: tuple[Field, ...]
    summary_field: str
    detail_field: str


KINDS: dict[str, Kind] = {
    "companies": Kind(
        table="carriers",
        title="Insurance companies",
        singular="company",
        plural="companies",
        intro="The logos strip and the claims numbers on the home page come from this list.",
        fields=(
            Field("name", "Company name", required=True, max_length=80),
            Field("claims_phone", "Claims phone", help="Shown large on the claims card. Example: 1-800-422-0550", max_length=40),
            Field("billing_phone", "Billing phone", max_length=40),
            Field("website", "Website", "url", help="Starts with https://"),
            Field("logo_media_id", "Logo", "image", help="PNG with a transparent background looks best. Up to 3 MB."),
            Field("logo_height", "Logo size", "number", help="Height in pixels, 16 to 80. Wide logos look best smaller (about 24), tall ones larger (about 50)."),
        ),
        summary_field="name",
        detail_field="claims_phone",
    ),
    "coverage": Kind(
        table="coverage",
        title="What we cover",
        singular="coverage type",
        plural="coverage types",
        intro="Each type becomes a tab in the What we cover section, with its picture and checklist.",
        fields=(
            Field("name", "Tab name", required=True, max_length=40, help="Short, like Auto or Home and property."),
            Field("headline", "Headline", required=True, max_length=90),
            Field("summary", "Description", "textarea", required=True, max_length=500),
            Field("items", "Checklist", "lines", help="One item per line. Two to six items look best."),
            Field("illustration", "Picture", "select"),
        ),
        summary_field="name",
        detail_field="headline",
    ),
    "people": Kind(
        table="team",
        title="People",
        singular="person",
        plural="people",
        intro="The bios in the About section. The first two photos also appear on the top banner.",
        fields=(
            Field("name", "Name", required=True, max_length=80),
            Field("role", "Role", max_length=60, help="Like Founder or Licensed agent."),
            Field("bio", "Short bio", "textarea", max_length=500, help="Two or three sentences reads best."),
            Field("photo_media_id", "Photo", "image", help="A square, friendly headshot. Up to 3 MB."),
        ),
        summary_field="name",
        detail_field="role",
    ),
    "reviews": Kind(
        table="testimonials",
        title="Client reviews",
        singular="review",
        plural="reviews",
        intro="Real words from real clients, with their permission. The section stays hidden until you add one.",
        fields=(
            Field("quote", "What they said", "textarea", required=True, max_length=600),
            Field("name", "Their name", required=True, max_length=80, help="First name and last initial is fine, like Mary K."),
            Field("detail", "Detail", max_length=80, help="Optional, like Sunbury homeowner or Client since 2012."),
        ),
        summary_field="name",
        detail_field="quote",
    ),
}


def _kind(slug: str) -> Kind:
    kind = KINDS.get(slug)
    if kind is None:
        abort(404)
    return kind


@bp.get("/website")
@login_required
def website() -> str:
    connection = get_db()
    loaded = site.load(connection, include_hidden=True)
    order, hidden = site.section_order(connection)
    counts = {slug: len(getattr(loaded, attr)) for slug, attr in (("companies", "carriers"), ("coverage", "coverage"), ("people", "team"), ("reviews", "testimonials"))}
    return render_template(
        "portal/website.html",
        loaded=loaded,
        counts=counts,
        hidden_count=len(hidden),
        faq_count=len(store.list_faqs(connection)),
        kinds=KINDS,
    )


@bp.route("/website/basics", methods=["GET", "POST"])
@login_required
def website_basics() -> str | Response | tuple[str, int]:
    connection = get_db()
    errors: dict[str, str] = {}
    if request.method == "POST":
        agency = {
            "name": clean_text(request.form, "name", max_length=80),
            "street": clean_text(request.form, "street", max_length=120),
            "city": clean_text(request.form, "city", max_length=60),
            "region": clean_text(request.form, "region", max_length=20),
            "postcode": clean_text(request.form, "postcode", max_length=12),
            "phone": clean_text(request.form, "phone", max_length=30),
            "phone2": clean_text(request.form, "phone2", max_length=30),
            "email": clean_text(request.form, "email", max_length=254).lower(),
            "show_street": request.form.get("show_street") == "on",
        }
        quotes = [
            " ".join(line.split())[:80]
            for line in clean_block(request.form, "hero_quotes", max_length=600).splitlines()
            if line.strip()
        ][:6]
        hero = {
            "title": quotes[0] if quotes else "",
            "quotes": quotes,
            "intro": clean_block(request.form, "hero_intro", max_length=400),
        }
        announcement = {
            "enabled": request.form.get("announce_enabled") == "on",
            "text": clean_text(request.form, "announce_text", max_length=200),
            "link_label": clean_text(request.form, "announce_label", max_length=40),
            "link_url": clean_text(request.form, "announce_url", max_length=300),
        }
        for key, label in (("name", "agency name"), ("city", "city"), ("phone", "office phone")):
            if not agency[key]:
                errors[key] = f"The {label} is needed."
        if not EMAIL_PATTERN.match(agency["email"]):
            errors["email"] = "Enter an email address like name@example.com."
        if not hero["title"]:
            errors["hero_quotes"] = "Add at least one headline."
        if announcement["link_url"] and not (announcement["link_url"].startswith("/") or safe_link(announcement["link_url"])):
            errors["announce_url"] = "Links start with https:// or / for a page on this site."
        if announcement["enabled"] and not announcement["text"]:
            errors["announce_text"] = "Write the message, or switch the banner off."

        try:
            photo_id = media.save_upload(connection, request.files.get("hero_photo"))
        except media.UploadRejected as exc:
            errors["hero_photo"] = str(exc)
            photo_id = None

        if not errors:
            if photo_id is not None:
                hero["photo_media_id"] = photo_id
            elif request.form.get("hero_photo_reset") == "on":
                hero["photo_media_id"] = None
            site.save_setting(connection, "agency", agency)
            site.save_setting(connection, "hero", hero)
            site.save_setting(connection, "announcement", announcement)
            flash("Saved. Your changes are live on the website.")
            return redirect(url_for("portal.website_basics"))

    return render_template(
        "portal/basics.html",
        agency=site.get_setting(connection, "agency"),
        hero=site.get_setting(connection, "hero"),
        announcement=site.get_setting(connection, "announcement"),
        form=request.form,
        errors=errors,
    ), (422 if errors else 200)


@bp.route("/website/look", methods=["GET", "POST"])
@login_required
def website_look() -> str | Response:
    connection = get_db()
    order, hidden = site.section_order(connection)
    if request.method == "POST":
        move = request.form.get("move", "")
        if move:
            key, _, direction = move.partition(":")
            if key in order and direction in {"-1", "1"}:
                index = order.index(key)
                target = index + int(direction)
                if 0 <= target < len(order):
                    order[index], order[target] = order[target], order[index]
            # Keep any ticks the agent changed before pressing an arrow.
            shown = set(request.form.getlist("show"))
            site.save_setting(connection, "sections", {"order": order, "hidden": sorted(set(site.SECTIONS) - shown)})
            return redirect(url_for("portal.website_look") + "#sections")

        preset = request.form.get("preset", "")
        corners = request.form.get("corners", "")
        shown = set(request.form.getlist("show"))
        custom = {}
        for key in site.CUSTOM_THEME_DEFAULT:
            value = request.form.get(f"custom_{key}", "").strip().lower()
            custom[key] = value if site.HEX.match(value) else site.CUSTOM_THEME_DEFAULT[key]
        site.save_setting(
            connection,
            "theme",
            {
                "preset": preset if preset in site.THEMES or preset == "custom" else "navy-gold",
                "corners": corners if corners in site.CORNERS else "rounded",
                "custom": custom,
            },
        )
        site.save_setting(connection, "sections", {"order": order, "hidden": sorted(set(site.SECTIONS) - shown)})
        flash("Saved. Your changes are live on the website.")
        return redirect(url_for("portal.website_look"))

    return render_template(
        "portal/look.html",
        theme=site.get_setting(connection, "theme"),
        themes=site.THEMES,
        corners=site.CORNERS,
        order=order,
        hidden=hidden,
        sections=site.SECTIONS,
        hints=site.SECTION_HINTS,
    )


@bp.get("/website/<slug>")
@login_required
def website_list(slug: str) -> str:
    kind = _kind(slug)
    rows = get_db().execute(f"SELECT * FROM {kind.table} ORDER BY position, id").fetchall()
    return render_template("portal/content_list.html", slug=slug, kind=kind, rows=rows)


@bp.route("/website/<slug>/new", methods=["GET", "POST"])
@bp.route("/website/<slug>/<int:row_id>", methods=["GET", "POST"])
@login_required
def website_edit(slug: str, row_id: int | None = None) -> str | Response | tuple[str, int]:
    kind = _kind(slug)
    connection = get_db()
    existing = site.get_row(connection, kind.table, row_id) if row_id is not None else None
    if row_id is not None and existing is None:
        abort(404)

    errors: dict[str, str] = {}
    values: dict[str, Any] = dict(existing or {})
    if request.method == "POST":
        values, errors = _read_fields(kind, existing)
        if not errors:
            for field in kind.fields:
                if field.kind != "image":
                    continue
                try:
                    uploaded = media.save_upload(connection, request.files.get(field.name))
                except media.UploadRejected as exc:
                    errors[field.name] = str(exc)
                    continue
                if uploaded is not None:
                    values[field.name] = uploaded
                elif request.form.get(f"{field.name}_reset") == "on":
                    values[field.name] = None
        if not errors:
            site.save_row(connection, kind.table, row_id, values)
            flash(f"Saved. The {kind.singular} is live on the website.")
            return redirect(url_for("portal.website_list", slug=slug))

    return render_template(
        "portal/content_edit.html",
        slug=slug,
        kind=kind,
        row=existing,
        values=values,
        errors=errors,
        illustrations=site.ILLUSTRATIONS,
    ), (422 if errors else 200)


def _read_fields(kind: Kind, existing: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, str]]:
    values: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for field in kind.fields:
        if field.kind == "image":
            values[field.name] = existing.get(field.name) if existing else None
            continue
        if field.kind == "lines":
            raw = clean_block(request.form, field.name, max_length=2000)
            values[field.name] = [" ".join(line.split())[:120] for line in raw.splitlines() if line.strip()][:12]
        elif field.kind == "textarea":
            values[field.name] = clean_block(request.form, field.name, max_length=field.max_length)
        elif field.kind == "number":
            try:
                values[field.name] = max(16, min(80, int(request.form.get(field.name, "40"))))
            except ValueError:
                errors[field.name] = "Enter a whole number."
        elif field.kind == "select":
            choice = request.form.get(field.name, "")
            values[field.name] = choice if choice in site.ILLUSTRATIONS else "shield"
        else:
            values[field.name] = clean_text(request.form, field.name, max_length=field.max_length)
            if field.kind == "url" and values[field.name] and not safe_link(values[field.name]):
                errors[field.name] = "Website addresses start with https://"
        if field.required and not values.get(field.name):
            errors[field.name] = f"{field.label} is needed."
    return values, errors


@bp.post("/website/<slug>/<int:row_id>/<action>")
@login_required
def website_action(slug: str, row_id: int, action: str) -> Response:
    kind = _kind(slug)
    connection = get_db()
    if action == "up":
        site.move(connection, kind.table, row_id, -1)
    elif action == "down":
        site.move(connection, kind.table, row_id, 1)
    elif action == "toggle":
        site.toggle(connection, kind.table, row_id)
        flash("Updated. Hidden items stay saved but do not show on the website.")
    elif action == "delete":
        site.delete(connection, kind.table, row_id)
        flash(f"The {kind.singular} was deleted.")
    else:
        abort(404)
    return redirect(url_for("portal.website_list", slug=slug))


@bp.route("/users", methods=["GET", "POST"])
@login_required
def users() -> str | Response | tuple[str, int]:
    connection = get_db()
    errors: dict[str, str] = {}
    if request.method == "POST":
        email = clean_text(request.form, "email", max_length=254).lower()
        name = clean_text(request.form, "name", max_length=80)
        password = request.form.get("password", "")
        if not EMAIL_PATTERN.match(email):
            errors["email"] = "Enter an email address like name@example.com."
        if len(name) < 2:
            errors["name"] = "Enter their name."
        if len(password) < 12:
            errors["password"] = "Use at least 12 characters. A short sentence works well."
        if not errors:
            store.upsert_agent(connection, email, name, generate_password_hash(password))
            flash(f"{name} can now sign in with {email}. If that login already existed, its password was reset.")
            return redirect(url_for("portal.users"))
    return render_template("portal/users.html", agents=store.list_agents(connection), errors=errors, form=request.form), (
        422 if errors else 200
    )


@bp.post("/users/<int:agent_id>/delete")
@login_required
def delete_user(agent_id: int) -> Response:
    if g.agent and g.agent["id"] == agent_id:
        flash("You cannot remove your own login while signed in.")
    else:
        store.delete_agent(get_db(), agent_id)
        flash("Login removed.")
    return redirect(url_for("portal.users"))
