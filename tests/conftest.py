import pytest

API_KEY_VARS = [
    "MARKETAUX_API_TOKEN", "TIINGO_API_TOKEN", "FINNHUB_API_KEY", "ALPHA_VANTAGE_API_KEY",
    "FINNHUB_API_TOKEN", "ALPHA_VANTAGE_TOKEN",
]


@pytest.fixture(autouse=True)
def _no_real_api_keys(monkeypatch):
    """src.config loads the developer's .env at import. Remove every key for
    each test so none can make a live call or spend a real quota; tests that
    need a key set one explicitly."""
    for var in API_KEY_VARS:
        monkeypatch.delenv(var, raising=False)
