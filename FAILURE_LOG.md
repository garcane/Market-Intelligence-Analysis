# FAILURE_LOG.md — Failure-Recovery Record (target spec §33)

The spec's protocol: identify the failure, find the root cause, classify it (Data, Code, Dependency, Logic, Statistical, ML, Leakage, Documentation), correct it, run a targeted test, run the full stage test, check for regressions. And one hard rule: **if the same failure occurs three times, stop implementing new functionality and investigate the architecture.**

This log records every failure found in the project, including the ones in my own process. Details and evidence for each are in the `CHECKPOINT.md` entry for the stage named.

## Failures by Class

| # | Stage | Class | Failure | Root cause | Correction |
|---|---|---|---|---|---|
| 1 | 0 | Dependency | `requirements.txt` unreadable by pip | Saved as UTF-16 | Re-encoded as UTF-8 |
| 2 | 3 | Dependency | Every HTTPS call failed | Antivirus TLS interception; its root CA was trusted by Windows but not by `certifi` | `truststore` plus an OS-certificate bundle for `curl_cffi` (`src/config.py`) |
| 3 | 3 | Code *(missing-value)* | Parquet round-trip falsely reported corruption | `datetime64[s]` read back as `[ms]` | Unit normalization before comparison |
| 4 | 3 | Code *(missing-value)* | Round-trip false failure, again | `pd.NA` read back as `None` | NaN normalization |
| 5 | 3 | Code *(missing-value)* | Round-trip false failure, a third time | `object` dtype read back as pandas `str` dtype | **Third occurrence: replaced the hand-rolled comparison with `assert_frame_equal(check_dtype=False)`** |
| 6 | 4 | Logic | Test asserted the wrong threshold boundary | Test bug, not code bug | Test corrected to match the documented left-closed bands |
| 7 | 5 | Code | Em-dashes corrupted in reports | `open(..., "w")` defaulted to cp1252 on Windows | `encoding="utf-8"` on every report write |
| 8 | 5 | Statistical | A correlation of -0.997 on n=4 shown without qualification | No minimum-sample guard | Report flags any n<10 result as not interpretable |
| 9 | 6 | Code *(missing-value)* | `rolling().mean()` crashed on an asset with no news | Column filled with `pd.NA`, giving `object` dtype | Float NaN instead of `pd.NA` |
| 10 | Interim | Code | 3 tests failed after a merge | Merged `validate.py` expected a schema `run_ingestion` never produced | Rename step at the provider/storage boundary |
| 11 | Interim | Code | CoinCodex failed for every crypto asset, silently | Passed `BTC-USD`; the API wants `BTC` | Strip the suffix inside the provider |
| 12 | Interim | Data | CoinCodex dropped ~11% of days, silently | Provider data gaps; the validator has no completeness check | Yahoo first, CoinCodex as fallback only |
| 13 | Interim | Data *(my process)* | A smoke test overwrote two assets' full history with a one-month slice | Test run wrote to the real data directory | Full re-ingestion and downstream regeneration |
| 14 | 9 | ML | Tree models overfit (train PR-AUC 0.88–0.98 vs. validation 0.40) | Trees too deep for ~2,800 rows | One regularization pass; the gap more than halved |
| 15 | 10 | Code | `HistGradientBoostingClassifier` has no `feature_importances_` | sklearn limitation | Covered by permutation importance |
| 16 | 11 | Data | `events.csv` failed to parse | Unquoted comma in a description | Quoted the text fields |
| 17 | 14 | Logic | Test expected 9 dashboard sections | Miscounted: Overview plus 9 = 10 | Test corrected |
| 18 | 14 | Dependency | `use_container_width` already past its removal date | Deprecated Streamlit API | Switched to `width="stretch"` |
| 19 | 15 | Code *(missing-value)* | Notebook reported a leak that didn't exist | `NaN != NaN` in the demo's `==` comparison | NaN-aware `Series.equals()` |
| 20 | §27 | Code *(missing-value)* | Sentiment columns absent (not NaN) for assets with no news, crashing the imputer | The pipeline skipped the sentiment join entirely | Always call the join; the callee already handled "no match" |
| 21 | §27 | Code *(missing-value)* | Sector columns absent when no asset had a sector match | Same pattern as #20 | Consumer created missing columns; see the architecture note below |
| 22 | §27 | Logic | 17 assets flowed into the 6-asset modelling pipeline | `run_features` globbed the whole directory | Explicit `MODELING_MARKET_IDS` |
| 23 | §28 | Code | `run_explain` crashed in a fresh directory | Only script that didn't create `outputs/figures/` | Added the `mkdir` |
| 24 | §28 | Dependency | Equity ingestion failed from a clean install; **first misdiagnosed as an IP rate limit** | `yfinance==0.2.52` pin, which Yahoo now rejects | `yfinance>=1.7.0`; `REPRODUCIBILITY.md` corrected |
| 25 | §28 | Dependency | `pip install` would fail on macOS/Linux | Unconditional `pywin32` | Platform marker |
| 26 | §29 | Code | `run_explain` took 51–70s | `n_jobs=-1` re-spawned process pools on every inner call | Removed; 36.5s, identical results |
| 27 | §19/20 | Documentation *(my process)* | Robustness testing and the ablation study were skipped without being flagged | I deferred them in Stages 9–13 and didn't say so | Built both; caught via the Definition of Done |
| 28 | §20 | Statistical | "Sentiment slightly hurts" claimed from a single run | One run treated as a result | The reproduction flipped the sign; corrected to "no measurable effect" |
| 29 | §30 | Documentation | README listed Finnhub/GDELT as current providers, plus wrong dashboard sections and SUI status | Written ahead of or apart from the code | Corrected against the code |
| 30 | §36 | Documentation | Docs told readers to set `NEWS_API_KEY`; `.env.example` missing | The variable was never wired to any provider | Variable removed, `.env.example` restored, docs corrected |
| 31 | Providers | Data *(latent)* | Routine news ingestion overwrote `news.parquet`, which would have wiped any backfilled history | `ingest_news` wrote only the current batch | Shared `merge_news_frames`; verified live, 282 → 302 rows |
| 32 | Providers | Code *(security)* | API tokens could appear in error messages and health reports | `requests` errors embed the full URL; Marketaux and Alpha Vantage only take the token as a URL parameter | `get_json` redacts tokens from every error; header auth where the provider supports it |
| 33 | Providers | Code | yfinance failures reported only as "empty response" | yfinance logs the real cause and returns an empty frame | The cause is captured and included in `FetchError` (the gap behind #24's misdiagnosis) |
| 34 | Providers | Code *(security)* | Alpha Vantage's daily-quota message included the API key, and it was copied into `news_backfill_report.json` and the backfill log | #32's redaction covered request URLs, not provider message bodies | Messages are redacted (the known key plus any "API key as ..." echo); local reports and logs scrubbed. Rotating the key is recommended as a precaution |
| 35 | Providers | Code | That quota message was classified as `AccessDenied` rather than `QuotaExhausted` | It also mentions "premium plans", and the premium check ran first | Quota phrases are checked first; regression test uses the real message |
| 36 | §12 Indices | Code | 30-day rolling correlation vs SPX was entirely NaN (0 of 1,202 points); `12_rolling_correlation_vs_spx.png` had been empty since Stage 12 | The returns frame has weekend rows (crypto trades daily) where equities are NaN, so no 30-row window was ever complete | Series aligned on shared days first (794 points); regression test. Found when the web app drew it as a live chart. Reported index metrics unchanged |
| 37 | Web app | Environment | `requirements.txt` pins older versions (e.g. scikit-learn 1.6.1) than the environment that trained the saved models (1.9.1) | The original `pip freeze` was never refreshed | `requirements-web.txt` pins the real versions and was verified in a fresh virtualenv; `requirements.txt` still needs the same refresh |

No **Leakage**-class failure reached a result. The one real leakage vector found (labels crossing a split boundary) was designed out by the Stage 8 embargo before any model was trained (`SPLIT.md`).

## The Three-Occurrence Rule

**Missing-value representation** (rows 3, 4, 5, 9, 19, 20, 21) recurred seven times: `pd.NA` vs. `None` vs. `NaN` vs. a column that isn't there at all. The rule was applied twice:

- **At the third occurrence (row 5):** the round-trip checks stopped patching individual cases and switched to a comparison designed for this problem (`assert_frame_equal(check_dtype=False)` plus NaN normalization).
- **Late, at rows 20–21:** each consumer had been patched separately. The fix moved to the producer: `src/features/pipeline.py` now guarantees every sentiment and sector column as a float NaN column even with no data behind it, and a regression test (`tests/test_pipeline.py::test_feature_schema_is_stable_without_any_sentiment_data`) enforces it.

The honest assessment is that the architectural fix came later than the rule asks. There were four more occurrences after row 5 before the producer took ownership of the schema. The convention now in place: **numeric missing values are float NaN, and feature columns are always present.**

**Implicit-context assumptions** (rows 22 and 23: a script relying on directory contents or run order) occurred twice, below the threshold, but they share a cause worth watching: behavior that depends on state accumulated in the working directory. The git-clone test in `REPRODUCIBILITY.md` is the guard against that class.

## Open Items

- No date-completeness check for 24/7 assets in `validate_market_prices` (row 12 was caught by manual inspection, not automation).
- **Historical news backfill (live since 2026-09-26):** day 1 brought news to 69,583 articles. Coverage of trading days is 0% for train, 20% for validation and 56% for test. The ablation gate (25% of training days) depends on Alpha Vantage's 25 requests per day, about 10 daily runs. Tiingo's equity fallback is verified live (closes within 0.0036% of Yahoo across NVDA's 2024 split).
- **Backfilled news needs cleaning before sentiment is rebuilt from it.**
  - Finnhub `company-news` and Yahoo Finance's ticker news both return general market stories under a ticker ("Should You Buy Nike Stock", a Costco story, both tagged NVDA). Articles are attributed to the queried symbol. Yahoo's response carries no per-article ticker list to filter on.
  - The same story from two providers survives deduplication because the URLs differ.
  - Scoring sentiment on this as-is would add noise to exactly the features the ablation tests.
- `requirements.txt` still carries unused legacy packages from the original `pip freeze` (e.g. `keras`, `keras-tuner`, `h5py`), and pins older versions than the models were trained with (#37).
