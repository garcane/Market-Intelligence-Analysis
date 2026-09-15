import pandas as pd

from src.ingestion.standardize import standardize_market, standardize_news


def test_standardize_market_schema_and_types():
    raw = pd.DataFrame({
        "date": ["2026-01-01"], "close": [100], "volume": [10], "market_cap": [1000]
    })
    out = standardize_market(raw, asset_id="TEST", source="unit")
    assert out.loc[0, "asset_id"] == "TEST"
    assert out.loc[0, "source"] == "unit"
    assert pd.api.types.is_datetime64_any_dtype(out["date"])
    assert "open" in out.columns and "high" in out.columns


def test_standardize_news_schema():
    raw = pd.DataFrame({"news_id": ["1"], "timestamp": ["2026-01-01"], "title": ["Test"], "url": ["https://example.com"]})
    out = standardize_news(raw, source="unit")
    assert out.loc[0, "article_id"] == "1"
    assert out.loc[0, "source"] == "unit"
    assert out.loc[0, "title"] == "Test"
