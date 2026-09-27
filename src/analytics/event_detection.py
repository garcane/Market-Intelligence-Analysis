"""Detects AI events (model releases, deals, chips, data-centre build-outs)
from ingested news headlines, so the AI events timeline keeps up with new
releases without anyone editing data/reference/events.csv by hand.

Rules, not a model: a headline becomes a candidate when it names an AI
organisation and matches one event category's pattern. Candidates are grouped
into one event per (category, subject) within a short window. The subject is
the model name for releases (e.g. "claude opus 5"). For deals, investments
and build-outs it is the organisation plus the deal size ("openai:38b"),
which both filters out immaterial items (only billions of dollars or
gigawatts count) and keeps unrelated stories about the same company apart.
An event needs several articles, and any detected event within a few days
of a curated event for the same organisation is dropped, since the curated
entry already covers it.

Output: data/processed/detected_events.csv (same columns as events.csv, plus
n_articles and first_headline). Run as: python -m src.analytics.event_detection
"""
from __future__ import annotations

import logging
import re

import pandas as pd

from src.config import PROCESSED_DIR, RAW_DIR, REFERENCE_DIR

logger = logging.getLogger(__name__)

OUTPUT_PATH = PROCESSED_DIR / "detected_events.csv"
GROUP_WINDOW_DAYS = 7
CURATED_OVERLAP_DAYS = 3
ACTOR_CHARS = 40
MIN_ARTICLES = {"model_release": 2}
DEFAULT_MIN_ARTICLES = 3

# keyword (regex) -> (organisation id, primary market id or None). Model-family
# names map to their lab, so "Gemini 3.5" is attributed to Alphabet.
ORGANISATIONS: list[tuple[str, str, str | None]] = [
    (r"openai|chatgpt|\bgpt-?\d|\bsora\b|\bcodex\b", "openai", "MSFT"),
    (r"anthropic|\bclaude\b|\bmythos\b", "anthropic", "AMZN"),
    (r"deepmind|\bgemini\b|google", "alphabet", "GOOGL"),
    (r"\bxai\b|\bgrok\b", "xai", None),
    (r"deepseek", "deepseek", "NVDA"),
    (r"\bqwen\b|alibaba", "alibaba", "BABA"),
    (r"moonshot|\bkimi\b", "moonshot", "BABA"),
    (r"\bmeta\b|\bllama\b", "meta", "META"),
    (r"mistral", "mistral", None),
    (r"zhipu|\bglm-?\d", "zhipu", None),
    (r"minimax", "minimax", None),
    (r"nvidia|nemotron", "nvidia", "NVDA"),
    (r"microsoft|\bazure\b", "microsoft", "MSFT"),
    (r"amazon|\baws\b", "amazon", "AMZN"),
    (r"oracle", "oracle", "ORCL"),
    (r"\bamd\b", "amd", "AMD"),
    (r"broadcom", "broadcom", "AVGO"),
    (r"\btsmc\b|taiwan semiconductor", "tsmc", "TSM"),
    (r"coreweave", "coreweave", "CRWV"),
    (r"nebius", "nebius", "NBIS"),
    (r"\biren\b", "iren", "IREN"),
    (r"terawulf", "terawulf", "WULF"),
    (r"cipher (digital|mining)", "cipher", "CIFR"),
    (r"\bintel\b", "intel", "INTC"),
]

# Model names: the subject of a model-release event.
MODEL_NAME = re.compile(
    r"\b(gpt-?\d+(?:\.\d+)?(?:-[a-z]+)?|o\d-(?:mini|pro)|"
    r"claude (?:opus|sonnet|haiku) \d+(?:\.\d+)?|(?:opus|sonnet|haiku) \d+(?:\.\d+)?|mythos|"
    r"gemini \d+(?:\.\d+)?(?: (?:pro|flash|ultra))?|grok \d+(?:\.\d+)?|"
    r"deepseek[- ]?[vr]\d+(?:\.\d+)?|qwen ?\d+(?:\.\d+)?|llama \d+(?:\.\d+)?|kimi k\d+(?:\.\d+)?|"
    r"glm-\d+(?:\.\d+)?|minimax m\d+(?:\.\d+)?|nemotron \d+(?:\.\d+)?|sora \d+|veo \d+)\b",
    re.IGNORECASE,
)

# Deal size: "$38 billion", "$1.5bn", "$1 trillion", "10GW", "1 gigawatt".
AMOUNT = re.compile(r"\$ ?(\d+(?:\.\d+)?) ?(billion|bn|b|trillion|tn)\b|\b(\d+(?:\.\d+)?) ?(gw|gigawatts?)\b",
                    re.IGNORECASE)
SIZED_TYPES = {"acquisition", "investment", "partnership", "infrastructure"}

RELEASE = r"\b(launch(es|ed)?|releas(es|ed)?|unveil(s|ed)?|introduc(es|ed)|debut(s|ed)?|rolls? out|rolling out|drops|now available|generally available)\b"
CATEGORIES: dict[str, str] = {
    "acquisition": r"\b(acquires?|acquired|acquisition of|to acquire|to buy|buys)\b",
    "investment": r"\b(invests?|investment in|takes? .{0,10}stake|funding round|raises \$|valuation of)\b",
    "partnership": r"\b(partnership|partners with|strikes? .{0,15}deal|signs? .{0,20}(deal|agreement|contract)|\$\d+(\.\d+)? ?(billion|bn) (deal|contract))\b",
    "hardware": r"\b(chip|gpu|accelerator|tpu|trainium|maia|rubin|blackwell)s?\b.*" + RELEASE + r"|" + RELEASE + r".*\b(chip|gpu|accelerator|tpu|superchip)s?\b",
    "infrastructure": r"\b(data ?cent(er|re)s?|gigawatts?|\d+ ?gw\b|power purchase|nuclear (plant|reactor|power deal))\b",
}

# Headlines about the stock rather than the event.
NOISE = re.compile(
    r"\?|\b(stocks?|shares|price target|buy|sell|dividend|podcast|futures|etf|analyst|prediction|"
    r"should you|here's why|what to know|motley|top midday|market chatter|week ahead|earnings preview|"
    r"new position|position in|trade tracker|years ago|could be worth|market report|market for)\b|\$[A-Z]{2,5}\b",
    re.IGNORECASE,
)


def match_organisation(title: str) -> tuple[str, str | None] | None:
    """The organisation named earliest in the headline, usually its subject."""
    lower = title.lower()
    best = None
    for pattern, org, market in ORGANISATIONS:
        m = re.search(pattern, lower)
        if m and (best is None or m.start() < best[0]):
            best = (m.start(), org, market)
    return (best[1], best[2]) if best else None


def deal_size(title: str) -> str | None:
    """Normalised deal size, e.g. "38b", "1.5t", "10gw"; None if not material."""
    m = AMOUNT.search(title)
    if not m:
        return None
    if m.group(1):
        unit = "t" if m.group(2).lower() in ("trillion", "tn") else "b"
        return f"{float(m.group(1)):g}{unit}"
    return f"{float(m.group(3)):g}gw"


def classify(title: str) -> tuple[str, str] | None:
    """(event_type, subject) for a headline, or None if it isn't an AI event."""
    if NOISE.search(title):
        return None
    org = match_organisation(title)
    if org is None:
        return None
    model = MODEL_NAME.search(title)
    if model and re.search(RELEASE, title, re.IGNORECASE):
        return "model_release", re.sub(r"\s+", " ", model.group(0).lower().replace("claude ", ""))
    # Beyond model releases, the organisation must lead the headline: "Nvidia
    # invests..." is Nvidia's event, "Cadence unveils ... powered by NVIDIA" isn't.
    if not re.search(next(p for p, o, _ in ORGANISATIONS if o == org[0]), title[:ACTOR_CHARS].lower()):
        return None
    for event_type, pattern in CATEGORIES.items():
        if re.search(pattern, title, re.IGNORECASE):
            if event_type not in SIZED_TYPES:
                return event_type, org[0]
            size = deal_size(title)
            return (event_type, f"{org[0]}:{size}") if size else None
    return None


def detect_events(news: pd.DataFrame, curated: pd.DataFrame | None = None) -> pd.DataFrame:
    news = news.dropna(subset=["title", "timestamp"]).sort_values("timestamp")
    rows = []
    for ts, title in zip(news["timestamp"], news["title"]):
        hit = classify(title)
        if hit:
            org, market = match_organisation(title)
            rows.append({"timestamp": ts, "title": title, "event_type": hit[0], "subject": hit[1],
                         "organisation": org, "primary_market_id": market})
    if not rows:
        return pd.DataFrame(columns=EVENT_COLUMNS)
    hits = pd.DataFrame(rows)

    events = []
    for (event_type, subject), group in hits.groupby(["event_type", "subject"], sort=False):
        # split a subject's articles into bursts separated by > GROUP_WINDOW_DAYS
        gap = group["timestamp"].diff() > pd.Timedelta(days=GROUP_WINDOW_DAYS)
        for _, burst in group.groupby(gap.cumsum()):
            if len(burst) < MIN_ARTICLES.get(event_type, DEFAULT_MIN_ARTICLES):
                continue
            first = burst.iloc[0]
            day = first["timestamp"].normalize()
            events.append({
                "event_id": f"news_{event_type}_{re.sub(r'[^a-z0-9]+', '_', subject)}_{day:%Y%m%d}",
                "event_date": day.strftime("%Y-%m-%d"),
                "event_type": event_type,
                "organisation": first["organisation"],
                "primary_market_id": first["primary_market_id"],
                "title": _title(event_type, subject, first["title"]),
                "description": f"Detected from {len(burst)} headlines between {day:%Y-%m-%d} and "
                               f"{burst['timestamp'].iloc[-1]:%Y-%m-%d}. First: \"{first['title']}\"",
                "n_articles": len(burst),
                "first_headline": first["title"],
            })
    detected = pd.DataFrame(events, columns=EVENT_COLUMNS)
    # One story often matches two categories ("invests $10B in a data centre");
    # keep the better-covered one per organisation and day.
    detected = (detected.sort_values("n_articles", ascending=False)
                .drop_duplicates(["organisation", "event_date"]))
    if curated is not None and not curated.empty and not detected.empty:
        detected = detected[~detected.apply(lambda e: _covered(e, curated), axis=1)]
    return detected.sort_values("event_date").reset_index(drop=True)


EVENT_COLUMNS = ["event_id", "event_date", "event_type", "organisation", "primary_market_id",
                 "title", "description", "n_articles", "first_headline"]


def _title(event_type: str, subject: str, headline: str) -> str:
    if event_type == "model_release":
        return f"{subject.title().replace('Gpt', 'GPT')} release"
    return headline


def _covered(event: pd.Series, curated: pd.DataFrame) -> bool:
    """True if a curated event for the same organisation is within a few days,
    or (for a model release) the curated catalogue already names the model."""
    if event["event_type"] == "model_release":
        model = event["title"].lower().removesuffix(" release")
        if curated["title"].str.lower().str.contains(model, regex=False).any():
            return True
    same_org = curated[curated["organisation"] == event["organisation"]]
    if same_org.empty:
        return False
    gap = (pd.to_datetime(same_org["event_date"]) - pd.Timestamp(event["event_date"])).abs()
    return bool((gap <= pd.Timedelta(days=CURATED_OVERLAP_DAYS)).any())


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    news = pd.read_parquet(RAW_DIR / "news" / "news.parquet", columns=["timestamp", "title"])
    curated = pd.read_csv(REFERENCE_DIR / "events.csv")
    detected = detect_events(news, curated)
    detected.to_csv(OUTPUT_PATH, index=False)
    logger.info("detected %d events from %d headlines:\n%s", len(detected), len(news),
                detected.groupby("event_type").size().to_string())


if __name__ == "__main__":
    main()
