# REPRODUCIBILITY.md — Clean-Environment Reproduction (target spec §28)

The spec's sequence is `git clone → install dependencies → configure environment → run pipeline → generate outputs`. It was run twice:

1. **Fresh-directory test** (earlier): the working tree copied to a new directory with a new venv, because the session's work was not yet committed.
2. **Literal `git clone` test** (final): once everything was committed, the repository was cloned into an empty directory and the README's instructions were followed exactly.

The second run is the one that counts. It also overturned a diagnosis made during the first.

## Final Run: Literal `git clone` (commit `cd7a4f5` + dependency fixes)

| Step | Result |
|---|---|
| `git clone` into an empty directory | Only `data/reference/` present; no `data/raw/`, no `.env` (correct: both are untracked) |
| `python -m venv` + `pip install -r requirements.txt` | Clean install |
| `pytest tests/` **with zero data present** | 148/148 passed |
| `cp .env.example .env` (README step 4) | `.env.example` present in the clone. It was missing from the repository until this stage (see Finding 3) |
| Ingestion, 6 modelling assets | 6/6 via Yahoo Finance, after the yfinance fix below (Finding 1) |
| Every remaining README pipeline command, in order | All 16 ran successfully on freshly ingested live data, with no substitution |
| `pytest tests/` after the full pipeline | 148/148 passed |
| `streamlit run dashboard/app.py` | HTTP 200, `/_stcore/health` → `ok` |

> **2026-09-26:** the Streamlit dashboard has been replaced by the FastAPI + React web app ([`WEB_APP.md`](WEB_APP.md)), so the row above is historical. The web app has been verified in the working environment, and its API dependencies (`requirements-web.txt`) in a fresh virtualenv. A full `git clone` reproduction of the web app has **not** been run yet.

### Results reproduced

| Result | Working environment | Git-clone reproduction |
|---|---|---|
| Stage 9 leaderboard order | XGBoost > RF > HGB > LR | XGBoost > RF > HGB > LR |
| XGBoost PR-AUC across 5 seeds | mean 0.410, std 0.0025 | mean 0.410, std 0.0039 |
| Equity / crypto PR-AUC | 0.411 / 0.420 | 0.414 / 0.419 |
| DeepSeek-shock NVDA T0 return | -16.97% | -16.97% |
| Ablation: market-only vs. market+sentiment | 0.404 vs. 0.397 | 0.400 vs. 0.401 |

The last row is Finding 2.

## Finding 1 (correction): the equity "rate limit" was a stale dependency pin

The fresh-directory run failed to ingest NVDA/MSFT/TSM with `YFRateLimitError`. At the time, this document attributed it to Yahoo rate-limiting this machine's IP after heavy use during the session. **That diagnosis was wrong.**

In the git-clone run the same error appeared again, so both environments were tested side by side, on the same machine, at the same moment:

| Environment | yfinance version | `yf.download("MSFT", ...)` |
|---|---|---|
| Working venv | 1.7.0 (unpinned install) | 13 rows |
| Fresh install from `requirements.txt` | **0.2.52 (pinned)** | `YFRateLimitError`, 0 rows |

Same IP, opposite outcome, so the IP was not the cause. `requirements.txt` was inherited from the original repository's `pip freeze` and pinned `yfinance==0.2.52`, a version Yahoo now rejects. **A clean install from the repository could not ingest any equity data.** Crypto only worked because the fallback chain reached CoinCodex.

Fixed by requiring `yfinance>=1.7.0`. With that, the clone ingested all six assets from Yahoo. A related portability bug was fixed at the same time: `pywin32==308` was an unconditional requirement, but pywin32 exists only on Windows, so `pip install -r requirements.txt` would have failed outright on macOS or Linux. It now carries a `sys_platform == "win32"` marker.

**Lesson recorded:** an error message is not a diagnosis. "Rate limited" was accepted at face value in the first run; comparing two environments side by side found the real cause in one step.

## Finding 2: the reproduction overturned an analytical claim

The ablation result "adding sentiment slightly *lowers* PR-AUC" (0.404 → 0.397) came from one run. In the reproduction the sign flipped (0.400 → 0.401). Both gaps are smaller than XGBoost's seed-to-seed standard deviation, so the effect is noise. `ABLATION_STUDY.md`, `ANALYSIS_REPORT.md` and the README now say "no measurable effect", with the correction noted.

## Finding 3: `.env.example` was missing from the repository

The README tells new users to configure credentials, but no `.env.example` was tracked in git, so a fresh clone had nothing to copy. It had been created earlier in the project and was lost at some point before ever being committed. It has been restored, and it now lists only the variables the code actually reads. Restoring it also exposed a dead variable: `NEWS_API_KEY` was read in `src/config.py` but never used by any provider, while several documents told readers to set it for historical news. It was removed, and the documents were corrected.

## Earlier Run: Fresh Directory (superseded)

For the record: the fresh-directory run passed 137/137 tests before and after the pipeline, and it found one real bug. `src/models/run_explain.py` was the only figure-producing script that didn't create `outputs/figures/`, so it crashed when run before the others. That is now fixed. The run substituted previously ingested data for the equity fetch it could not complete, which was disclosed at the time. Its explanation for that failure is corrected in Finding 1 above.

## Remaining Caveats

- `yfinance>=1.7.0` is a lower bound, not an exact pin: Yahoo breaks old yfinance releases over time, so an exact pin would eventually rot the same way 0.2.52 did. The tradeoff is that a future yfinance release could change behavior.
- `requirements.txt` still carries unused packages from the original repository's `pip freeze` (e.g. `keras`, `keras-tuner`, `h5py`). They install cleanly but add weight; see `FAILURE_LOG.md`.

## Stage Completion Check (§28)

- [x] `git clone` → install → configure → run pipeline → generate outputs, followed exactly as the README describes
- [x] Full test suite passes with zero data, and again after the full pipeline
- [x] Live ingestion and every pipeline stage succeed with no data substitution
- [x] Dashboard boots from the clone
- [x] Headline results reproduce, and the one that didn't was corrected in the analysis documents

**Reproducibility status: COMPLETE.**
