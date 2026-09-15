"""AI Market Intelligence & Financial Analytics — Streamlit dashboard (Stage 14).

Every section reads from already-materialized artifacts via data_loader.py.
No live data fetching, no live model training on page load — the dashboard is
a presentation layer over the pipeline's outputs, per the target spec.
Run as: streamlit run dashboard/app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from dashboard.data_loader import (
    figure_path,
    load_all_market_prices,
    load_companies,
    load_company_ai_categories,
    load_crypto_assets,
    load_event_study_report,
    load_events,
    load_explainability_report,
    load_feature_agreement,
    load_indices_report,
    load_model_report,
    load_news,
    load_sentiment,
    list_ingested_market_ids,
)
from src.analytics.market_stats import compute_market_stats, summary_stats
from src.analytics.sentiment_stats import daily_sentiment, label_distribution, sentiment_by_entity

st.set_page_config(page_title="AI Market Intelligence", layout="wide")

SECTIONS = [
    "Overview", "AI Market Overview", "Company Explorer", "Stock Performance",
    "Sentiment Intelligence", "AI Events", "Model Performance",
    "Prediction Analysis", "Risk Analytics", "AI Supply Chain",
]


def show_figure(name: str, caption: str | None = None) -> None:
    path = figure_path(name)
    if path.exists():
        st.image(str(path), caption=caption, width='stretch')
    else:
        st.info(f"Figure not yet generated: {name}")


def section_overview(market_ids: list[str]) -> None:
    st.header("Overview")
    st.caption("AI Market Intelligence & Financial Analytics — pipeline outputs snapshot")
    prices = load_all_market_prices()
    col1, col2, col3 = st.columns(3)
    col1.metric("Tracked assets (ingested)", len(market_ids))
    if prices:
        any_df = next(iter(prices.values()))
        col2.metric("History start", str(pd.to_datetime(any_df["date"]).min().date()))
        col3.metric("History end", str(pd.to_datetime(any_df["date"]).max().date()))

    st.subheader("Asset performance snapshot")
    rows = []
    for mid, df in prices.items():
        stats = summary_stats(compute_market_stats(df))
        rows.append({"market_id": mid, **stats})
    if rows:
        st.dataframe(pd.DataFrame(rows).sort_values("total_return", ascending=False), width='stretch')

    st.markdown("Use the sidebar to explore AI market indices, company universe, sentiment, model results, event studies, risk, and supply-chain structure.")


def section_ai_market_overview() -> None:
    st.header("AI Market Overview")
    report = load_indices_report()
    if not report:
        st.warning("Run `python -m src.analytics.run_indices` first.")
        return
    st.subheader("Thematic index membership")
    for name, members in report["index_members"].items():
        st.markdown(f"**{name}**: {', '.join(members)}")
    st.subheader("Index & benchmark statistics")
    st.dataframe(pd.DataFrame(report["indices"]).T, width='stretch')
    show_figure("12_indices_cumulative_return.png")
    show_figure("12_index_correlation_matrix.png")
    show_figure("12_rolling_correlation_vs_spx.png")


def section_company_explorer() -> None:
    st.header("Company Explorer")
    companies = load_companies()
    categories = load_company_ai_categories()
    ingested = set(list_ingested_market_ids())

    col1, col2 = st.columns(2)
    with col1:
        category_filter = st.multiselect("Filter by AI category", sorted(categories["ai_category"].unique()))
    with col2:
        region_filter = st.multiselect("Filter by region", sorted(companies["region"].dropna().unique()))

    df = companies.copy()
    if region_filter:
        df = df[df["region"].isin(region_filter)]
    if category_filter:
        matching_ids = categories[categories["ai_category"].isin(category_filter)]["company_id"].unique()
        df = df[df["company_id"].isin(matching_ids)]

    df = df.copy()
    df["ingested"] = df["ticker"].isin(ingested)
    st.dataframe(df, width='stretch')
    st.caption(f"{len(df)} companies shown; {int(df['ingested'].sum())} have ingested price data.")


def section_stock_performance(market_ids: list[str]) -> None:
    st.header("Stock Performance")
    if not market_ids:
        st.warning("No ingested market data found.")
        return
    asset = st.selectbox("Asset", market_ids)
    prices = load_all_market_prices()
    df = prices.get(asset)
    if df is None or df.empty:
        st.warning("No data for this asset.")
        return

    dates = pd.to_datetime(df["date"])
    date_range = st.slider("Date range", min_value=dates.min().date(), max_value=dates.max().date(),
                            value=(dates.min().date(), dates.max().date()))
    mask = (dates.dt.date >= date_range[0]) & (dates.dt.date <= date_range[1])
    filtered = df[mask]

    stats_df = compute_market_stats(filtered)
    summary = summary_stats(stats_df)
    cols = st.columns(4)
    cols[0].metric("Total return", f"{summary['total_return']:.1%}")
    cols[1].metric("Ann. volatility", f"{summary['annualized_volatility']:.1%}")
    cols[2].metric("Max drawdown", f"{summary['max_drawdown']:.1%}")
    cols[3].metric("Trading days", summary["n_days"])

    st.line_chart(stats_df.set_index("date")["close"], width='stretch')
    st.line_chart(stats_df.set_index("date")["cumulative_return"], width='stretch')
    st.line_chart(stats_df.set_index("date")["drawdown"], width='stretch')


def section_sentiment_intelligence() -> None:
    st.header("Sentiment Intelligence")
    sentiment_df = load_sentiment()
    news_df = load_news()
    if sentiment_df is None or news_df is None:
        st.warning("Run `python -m src.sentiment.run_sentiment` first.")
        return

    model = st.selectbox("Sentiment model", sorted(sentiment_df["sentiment_model"].unique()))
    label_filter = st.multiselect("Filter by label", sorted(sentiment_df["sentiment_label"].dropna().unique()))

    scored = sentiment_df[sentiment_df["sentiment_model"] == model]
    if label_filter:
        scored = scored[scored["sentiment_label"].isin(label_filter)]

    st.subheader("Label distribution")
    st.bar_chart(label_distribution(sentiment_df, model))

    st.subheader("Sentiment by company")
    by_company = sentiment_by_entity(sentiment_df, news_df, "matched_company_id", model)
    st.dataframe(by_company, width='stretch')

    st.subheader("Sentiment over time")
    daily = daily_sentiment(sentiment_df, news_df, model)
    if not daily.empty:
        st.line_chart(daily.set_index("date")["mean_sentiment"])
    show_figure("13_sentiment_by_sector.png")


def section_ai_events() -> None:
    st.header("AI Events")
    events = load_events()
    report = load_event_study_report()
    if events.empty or not report:
        st.warning("Run `python -m src.analytics.run_event_study` first.")
        return
    st.dataframe(events, width='stretch')
    st.subheader("Event outcomes")
    st.dataframe(pd.DataFrame(report["events"]), width='stretch')
    show_figure("11_caar_all_events.png")
    event_id = st.selectbox("Inspect one event", [e["event_id"] for e in report["events"] if e["status"] == "OK"])
    if event_id:
        show_figure(f"11_event_{event_id}.png")


def section_model_performance() -> None:
    st.header("Model Performance")
    report = load_model_report()
    if not report:
        st.warning("Run `python -m src.models.train_baselines` first.")
        return
    st.subheader(f"Leaderboard (horizon={report['horizon']}d, ranked by {report['leaderboard_criteria']})")
    st.write(report["leaderboard"])
    if report["any_suspiciously_high_auc"]:
        st.error("At least one model exceeded the suspicious-AUC threshold — investigate leakage.")
    else:
        st.success("No model exceeded the suspicious-AUC threshold.")

    rows = []
    for name, m in report["models"].items():
        vm = m.get("validation_metrics", {})
        rows.append({"model": name, **{k: v for k, v in vm.items() if k != "confusion_matrix"}})
    st.dataframe(pd.DataFrame(rows), width='stretch')

    show_figure("13_roc_curves.png")
    show_figure("13_pr_curves.png")
    show_figure("13_confusion_matrices.png")


def section_prediction_analysis() -> None:
    st.header("Prediction Analysis")
    report = load_explainability_report()
    if not report:
        st.warning("Run `python -m src.models.run_explain` first.")
        return
    st.subheader("Cross-model feature agreement")
    agreement = load_feature_agreement()
    if agreement is not None:
        st.dataframe(agreement, width='stretch')
    col1, col2 = st.columns(2)
    with col1:
        show_figure("10_importance_xgboost.png")
        show_figure("10_shap_xgboost.png")
    with col2:
        show_figure("10_importance_logistic_regression.png")
        show_figure("10_shap_logistic_regression.png")


def section_risk_analytics() -> None:
    st.header("Risk Analytics")
    report = load_indices_report()
    if not report:
        st.warning("Run `python -m src.analytics.run_indices` first.")
        return
    rows = []
    for name, stats in report["indices"].items():
        row = {"name": name, "annualized_volatility": stats["annualized_volatility"],
               "max_drawdown": stats["max_drawdown"], "sharpe_ratio": stats["sharpe_ratio"]}
        rows.append(row)
    st.dataframe(pd.DataFrame(rows).sort_values("annualized_volatility", ascending=False), width='stretch')
    show_figure("05_return_correlation_matrix.png")
    show_figure("03_drawdown.png")


def section_ai_supply_chain() -> None:
    st.header("AI Supply Chain")
    categories = load_company_ai_categories()
    companies = load_companies()
    counts = categories.groupby("ai_category")["company_id"].nunique().sort_values(ascending=False)
    st.bar_chart(counts)
    category = st.selectbox("Inspect category", counts.index.tolist())
    members = categories[categories["ai_category"] == category].merge(
        companies[["company_id", "company_name", "ticker", "country"]], on="company_id")
    st.dataframe(members[["company_name", "ticker", "country", "subsector", "role_notes"]], width='stretch')


def main() -> None:
    st.sidebar.title("AI Market Intelligence")
    section = st.sidebar.radio("Section", SECTIONS)
    market_ids = list_ingested_market_ids()

    if section == "Overview":
        section_overview(market_ids)
    elif section == "AI Market Overview":
        section_ai_market_overview()
    elif section == "Company Explorer":
        section_company_explorer()
    elif section == "Stock Performance":
        section_stock_performance(market_ids)
    elif section == "Sentiment Intelligence":
        section_sentiment_intelligence()
    elif section == "AI Events":
        section_ai_events()
    elif section == "Model Performance":
        section_model_performance()
    elif section == "Prediction Analysis":
        section_prediction_analysis()
    elif section == "Risk Analytics":
        section_risk_analytics()
    elif section == "AI Supply Chain":
        section_ai_supply_chain()


main()
