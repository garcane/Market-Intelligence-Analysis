"""Vercel entrypoint. Vercel's FastAPI preset looks for an `app` in ./app.py.

The deployment is the read-only public demo (see api/settings.py): no
pipeline endpoints, no API docs, and no price rows from providers whose
licence forbids redistribution. Locally, keep using `uvicorn api.main:app`.
"""
import os

os.environ.setdefault("APP_MODE", "public")

from api.main import app  # noqa: E402,F401 - APP_MODE must be set before the app is built
