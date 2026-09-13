"""Text cleaning for headlines. The original repo's scraped headlines had raw
\\r\\n and leading/trailing whitespace baked directly into the stored strings
(see PROJECT_AUDIT.md §3c) — this module exists specifically to not repeat that.
"""
from __future__ import annotations

import html
import re

_WHITESPACE_RE = re.compile(r"\s+")


def clean_headline(text: str | None) -> str:
    if text is None:
        return ""
    text = html.unescape(text)
    text = text.replace("\r", " ").replace("\n", " ")
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()
