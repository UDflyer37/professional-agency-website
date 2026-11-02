"""Entry point. Vercel's Python runtime and `flask --app app` both look for `app` here."""

from otto import create_app

app = create_app()
