import pandas as pd

from src.sentiment.agreement import compare_models
from src.sentiment.score import label_from_score, score_news, score_textblob, score_vader
from src.sentiment.text_clean import clean_headline


class TestCleanHeadline:
    def test_strips_embedded_crlf_and_whitespace(self):
        raw = "\r\n\r\n   Some headline text here   \r\n"
        assert clean_headline(raw) == "Some headline text here"

    def test_collapses_internal_whitespace(self):
        assert clean_headline("Too    many   spaces") == "Too many spaces"

    def test_unescapes_html_entities(self):
        assert clean_headline("Pump.fun&#8217;s lawsuit") == "Pump.fun’s lawsuit"

    def test_none_input_returns_empty_string(self):
        assert clean_headline(None) == ""


class TestLabelThresholds:
    def test_covers_full_range_without_gaps(self):
        # Regression test: original repo's thresholds left [0.4, 0.5) unclassified
        # (PROJECT_AUDIT.md 3c). Every score in [-1, 1] must get exactly one label.
        import numpy as np
        for score in np.arange(-1.0, 1.0, 0.01):
            label = label_from_score(float(score))
            assert label in {"Bullish", "Slightly Bullish", "Neutral", "Slightly Bearish", "Bearish"}

    def test_boundary_values(self):
        # Each band is left-closed/right-open: [0.5, 1], [0.2, 0.5), [-0.2, 0.2),
        # [-0.5, -0.2), [-1, -0.5) — consistent convention, no gaps or overlaps.
        assert label_from_score(0.5) == "Bullish"
        assert label_from_score(0.49) == "Slightly Bullish"
        assert label_from_score(0.2) == "Slightly Bullish"
        assert label_from_score(0.19) == "Neutral"
        assert label_from_score(0.0) == "Neutral"
        assert label_from_score(-0.19) == "Neutral"
        assert label_from_score(-0.2) == "Neutral"
        assert label_from_score(-0.21) == "Slightly Bearish"
        assert label_from_score(-0.5) == "Slightly Bearish"
        assert label_from_score(-0.51) == "Bearish"

    def test_previously_unclassified_band_now_classified(self):
        # 0.45 fell in the original bug's gap; must now resolve deterministically.
        assert label_from_score(0.45) == "Slightly Bullish"


class TestScoring:
    def test_positive_text_scores_positive(self):
        text = "Company reports record profits and stock surges to all-time high"
        assert score_vader(text) > 0
        assert score_textblob(text) > 0

    def test_negative_text_scores_negative(self):
        text = "Stock plunges after terrible earnings miss and shocking scandal"
        assert score_vader(text) < 0
        assert score_textblob(text) < 0

    def test_models_can_disagree_on_domain_specific_negative_text(self):
        # Documents a real finding, not a bug: TextBlob's fixed lexicon doesn't
        # score "lawsuit"/"crashes"/"fraud" as negative, while VADER does. This
        # is exactly the kind of model disagreement the sentiment pipeline is
        # meant to surface (see PROJECT_AUDIT.md — "do not assume one sentiment
        # model is superior").
        text = "Company faces massive lawsuit as stock crashes amid fraud allegations"
        assert score_vader(text) < -0.5
        assert score_textblob(text) == 0.0

    def test_scores_are_deterministic(self):
        text = "Some neutral headline about markets"
        assert score_vader(text) == score_vader(text)
        assert score_textblob(text) == score_textblob(text)

    def test_score_news_produces_long_format_with_both_models(self):
        news_df = pd.DataFrame({
            "news_id": ["a", "b"],
            "title": ["Stock surges on strong earnings", "Company faces regulatory probe"],
        })
        result = score_news(news_df, dedupe_on_cleaned_title=False)
        assert len(result) == 4  # 2 articles x 2 models
        assert set(result["sentiment_model"]) == {"vader", "textblob"}
        assert result["sentiment_score"].between(-1, 1).all()

    def test_score_news_drops_exact_duplicate_headlines(self):
        news_df = pd.DataFrame({
            "news_id": ["a", "b"],
            "title": ["Same headline", "Same headline"],
        })
        result = score_news(news_df, dedupe_on_cleaned_title=True)
        assert result["news_id"].nunique() == 1

    def test_score_news_handles_empty_title_gracefully(self):
        news_df = pd.DataFrame({"news_id": ["a"], "title": [""]})
        result = score_news(news_df)
        assert len(result) == 0


class TestAgreement:
    def test_identical_scores_have_perfect_agreement(self):
        df = pd.DataFrame({
            "news_id": ["a", "b", "c"] * 2,
            "sentiment_model": ["vader"] * 3 + ["textblob"] * 3,
            "sentiment_score": [0.5, -0.3, 0.0] * 2,
            "sentiment_label": ["Bullish", "Slightly Bearish", "Neutral"] * 2,
        })
        stats = compare_models(df)
        assert stats["exact_label_agreement_rate"] == 1.0
        assert stats["n_compared"] == 3

    def test_disagreeing_scores_reduce_agreement(self):
        df = pd.DataFrame({
            "news_id": ["a", "b"] * 2,
            "sentiment_model": ["vader"] * 2 + ["textblob"] * 2,
            "sentiment_score": [0.8, -0.8, -0.8, 0.8],
            "sentiment_label": ["Bullish", "Bearish", "Bearish", "Bullish"],
        })
        stats = compare_models(df)
        assert stats["exact_label_agreement_rate"] == 0.0
