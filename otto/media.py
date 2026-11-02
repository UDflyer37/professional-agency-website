"""Photos and logos uploaded from the portal.

Vercel's file system is read-only, so uploads live in Postgres. They are small (logos and
portraits), served with long cache headers, and checked by their first bytes rather than
the browser-supplied content type.
"""

from __future__ import annotations

from dataclasses import dataclass

from werkzeug.datastructures import FileStorage

from otto.db import Connection

MAX_BYTES = 3 * 1024 * 1024

_SIGNATURES = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
)


class UploadRejected(ValueError):
    pass


@dataclass(frozen=True)
class StoredImage:
    content_type: str
    data: bytes


def sniff(data: bytes) -> str | None:
    for signature, content_type in _SIGNATURES:
        if data.startswith(signature):
            return content_type
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def save_upload(connection: Connection, upload: FileStorage | None) -> int | None:
    """Store an uploaded image and return its id, or None when no file was chosen."""
    if upload is None or not upload.filename:
        return None
    data = upload.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise UploadRejected("That image is larger than 3 MB. Please choose a smaller one.")
    content_type = sniff(data)
    if content_type is None:
        raise UploadRejected("Please upload a JPG, PNG or WebP image.")
    row = connection.execute(
        "INSERT INTO media (content_type, filename, data) VALUES (%s, %s, %s) RETURNING id",
        (content_type, upload.filename[:200], data),
    ).fetchone()
    return int(row["id"]) if row else None


def load_image(connection: Connection, media_id: int) -> StoredImage | None:
    row = connection.execute("SELECT content_type, data FROM media WHERE id = %s", (media_id,)).fetchone()
    if row is None:
        return None
    return StoredImage(row["content_type"], bytes(row["data"]))
