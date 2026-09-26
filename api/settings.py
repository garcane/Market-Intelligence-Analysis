"""Runtime settings for the web API, read from environment variables.

APP_MODE=local  (default) the developer's machine: pipeline runs allowed from localhost.
APP_MODE=public read-only demo: no pipeline endpoints, and no data whose licence
                forbids redistribution (Tiingo's free plan is personal use only).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

DEV_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

# Price rows from these providers are never served in public mode.
NON_REDISTRIBUTABLE_SOURCES = frozenset({"tiingo"})


@dataclass(frozen=True)
class Settings:
    mode: str = "local"
    allowed_origins: list[str] = field(default_factory=list)

    @property
    def public(self) -> bool:
        return self.mode == "public"

    @property
    def pipeline_enabled(self) -> bool:
        return self.mode == "local"

    @property
    def excluded_sources(self) -> frozenset[str]:
        return NON_REDISTRIBUTABLE_SOURCES if self.public else frozenset()


def load_settings(mode: str | None = None) -> Settings:
    mode = (mode or os.getenv("APP_MODE", "local")).strip().lower()
    if mode not in {"local", "public"}:
        raise ValueError(f"APP_MODE must be 'local' or 'public', got {mode!r}")
    origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
    if mode == "local":
        origins = origins or DEV_ORIGINS
    return Settings(mode=mode, allowed_origins=origins)
