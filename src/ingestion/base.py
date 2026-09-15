"""Common interfaces and resilience helpers for external data providers."""
from __future__ import annotations

import hashlib
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_SECONDS = 2


class ProviderError(RuntimeError):
    """Raised when a provider cannot return usable data."""


class MarketDataProvider(ABC):
    """Provider contract: implementations return the project's canonical market schema."""

    name: str

    @abstractmethod
    def fetch_prices(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        raise NotImplementedError


class NewsDataProvider(ABC):
    """Provider contract: implementations return the project's canonical news schema."""

    name: str

    @abstractmethod
    def fetch_news(self, query: str, max_results: int = 30) -> pd.DataFrame:
        raise NotImplementedError


def with_retries(
    operation: Callable[[], Any],
    *,
    provider: str,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_seconds: float = DEFAULT_BACKOFF_SECONDS,
) -> Any:
    """Run a provider operation with bounded retry/backoff handling."""
    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            return operation()
        except Exception as exc:  # noqa: BLE001 - provider/network libraries vary
            last_error = exc
            logger.warning("%s attempt %d/%d failed: %s", provider, attempt, max_retries, exc)
            if attempt < max_retries:
                time.sleep(backoff_seconds * attempt)
    raise ProviderError(f"{provider}: all {max_retries} attempts failed: {last_error}") from last_error


def add_provenance(df: pd.DataFrame, *, source: str, asset_id: str | None = None) -> pd.DataFrame:
    """Attach source/provenance fields without changing analytical values."""
    out = df.copy()
    out["source"] = source
    out["ingested_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
    if asset_id is not None and "asset_id" not in out.columns:
        out["asset_id"] = asset_id
    return out


def stable_record_id(*parts: object) -> str:
    """Create a deterministic short identifier for a provider record."""
    return hashlib.sha1("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:16]
