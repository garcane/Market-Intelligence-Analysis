"""Runs the actual dashboard app (not a mock) headlessly via Streamlit's
AppTest framework for every one of the 9 required sections, and asserts no
uncaught exception surfaced — the real "does the golden path work" check for
a Streamlit app, since a plain HTTP request to the server only proves it
boots, not that each page renders without error.
"""
from pathlib import Path

from streamlit.testing.v1 import AppTest

from dashboard.app import SECTIONS

APP_PATH = str(Path(__file__).resolve().parent.parent / "dashboard" / "app.py")


def _run_section(section_label: str):
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    at.sidebar.radio[0].set_value(section_label).run()
    return at


class TestDashboardSections:
    def test_all_sections_are_declared(self):
        # "Overview" (root) + the spec's 9 named children = 10, matching the
        # target spec's dashboard tree exactly.
        assert len(SECTIONS) == 10
        assert SECTIONS[0] == "Overview"

    def test_overview_renders_without_exception(self):
        at = _run_section("Overview")
        assert not at.exception

    def test_ai_market_overview_renders_without_exception(self):
        at = _run_section("AI Market Overview")
        assert not at.exception

    def test_company_explorer_renders_without_exception(self):
        at = _run_section("Company Explorer")
        assert not at.exception

    def test_stock_performance_renders_without_exception(self):
        at = _run_section("Stock Performance")
        assert not at.exception

    def test_sentiment_intelligence_renders_without_exception(self):
        at = _run_section("Sentiment Intelligence")
        assert not at.exception

    def test_ai_events_renders_without_exception(self):
        at = _run_section("AI Events")
        assert not at.exception

    def test_model_performance_renders_without_exception(self):
        at = _run_section("Model Performance")
        assert not at.exception

    def test_prediction_analysis_renders_without_exception(self):
        at = _run_section("Prediction Analysis")
        assert not at.exception

    def test_risk_analytics_renders_without_exception(self):
        at = _run_section("Risk Analytics")
        assert not at.exception

    def test_ai_supply_chain_renders_without_exception(self):
        at = _run_section("AI Supply Chain")
        assert not at.exception
