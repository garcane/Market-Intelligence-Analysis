# WEB_APP.md: the web app (replaces the Stage 14 Streamlit dashboard)

The dashboard is a React single-page app backed by a FastAPI service. It
replaced the Streamlit app, which reran every page on each interaction and
could not be styled or laid out beyond Streamlit's defaults.

Like the Streamlit version, it is a presentation layer only. It reads the
pipeline's saved outputs and never fetches market data or trains a model on
page load.

## Running it

**Development** uses two processes:

```bash
uvicorn api.main:app --reload             # API on http://127.0.0.1:8000
cd web && npm install && npm run dev      # UI on http://localhost:5173, proxies /api to :8000
```

If port 8000 is taken, run the API on another port and point Vite at it:
`uvicorn api.main:app --port 8001` and `API_URL=http://127.0.0.1:8001 npm run dev`.

**Single process** (how it is deployed):

```bash
cd web && npm run build && cd ..          # writes web/dist
uvicorn api.main:app                      # serves the API and the built app on :8000
```

**Docker** (read-only public demo). Build after running the pipeline, because
the image snapshots its outputs:

```bash
docker build -t ai-market-intelligence .
docker run -p 8000:8000 ai-market-intelligence
```

## Modes

`APP_MODE` controls what the server exposes.

| | `local` (default) | `public` (Docker default) |
|---|---|---|
| Read-only endpoints | yes | yes |
| Pipeline page and `/api/pipeline/*` | yes, and only from localhost | not registered |
| API docs at `/api/docs` | yes | no |
| Price rows from Tiingo | served | filtered out: Tiingo's free plan forbids redistribution |
| CORS | Vite dev origins | `ALLOWED_ORIGINS` (comma-separated), none by default |

In both modes, the news feed returns only the headline, link, publisher, time
and sentiment. It never returns article text.

## Architecture

```
web/  React 19 + Vite + TypeScript
      TanStack Query (caching), TanStack Table, ECharts (tree-shaken), Tailwind v4
        │  fetch /api/*
api/  FastAPI
      data.py      readers for data/ and outputs/, cached on file mtime
      routers/     markets · reference · sentiment · models · pipeline
        │  imports
src/  the pipeline's own functions (market_stats, indices, event_study,
      sentiment_stats, models.predict)
```

Each file read is cached until the file's modification time changes. A
pipeline run therefore shows up on the next request without a server restart.
Stats come from the pipeline's own functions, not reimplementations. For
example, the indices page calls `src.analytics.indices`, and per-event windows
call `src.analytics.event_study.abnormal_return_window`.

At startup the server warms the predictions cache in a background thread. The
first cold call loads the joblib models and XGBoost, which takes about 20
seconds.

## Pages and endpoints

| Page | Endpoint(s) | Notes |
|---|---|---|
| Overview | `/api/markets`, `/api/meta` | Sortable asset table (name, ticker, type) with 6-month sparklines, filtered by category: Stocks, AI Supply Chain, Energy, Benchmarks, Crypto |
| AI market | `/api/indices` | Index returns and the 30-day correlation with SPX, computed live |
| Stock performance | `/api/markets/{id}/prices?start&end` | Range presets, zoom, drawdown |
| Risk analytics | `/api/markets`, `/api/markets/correlation` | Risk-return scatter and correlation heatmap, filtered by category |
| Company explorer | `/api/companies` | Filters are kept in the URL |
| AI supply chain | `/api/companies`, `/api/markets` | Semiconductors, hyperscalers, neoclouds, data centres, power and networking, each member with live price stats |
| Energy | `/api/companies`, `/api/markets` | Nuclear and uranium, clean energy, storage, power generation, oil and gas, including thematic ETFs |
| AI events | `/api/events` | Curated and news-detected AI events with type/source filters and search; CAAR chart and per-event abnormal returns |
| Sentiment | `/api/sentiment/summary?model&labels` | The label filter applies to every chart. It was never applied in the Streamlit app. Also shows news coverage by split. |
| News feed | `/api/news?q&entity&source&label&from&to&page` | New page |
| Model performance | `/api/models/report`, `/api/models/validation-predictions` | Validation split only. Interactive PR and ROC curves and threshold-driven confusion matrices, computed in the browser from per-row validation predictions (`python -m src.models.validation_predictions`, also written by training). `?curve=roc&t=0.4` opens a tab at a threshold |
| Explainability | `/api/models/explainability` | Permutation, SHAP and built-in importance |
| Predictions | `/api/predictions/latest` | New page, described below |
| Pipeline | `/api/pipeline/*` | New page. Local mode only. |

**Predictions** come from `src.models.predict.predict_latest`. It scores each
modelling asset's newest feature row, which has no realised target yet, with
every saved model. It computes no metrics, so the held-out test set stays
unscored. The page shows each probability against the validation base rate,
with a not-investment-advice notice.

**Pipeline runs** use a fixed whitelist of `python -m` modules. One job runs
at a time as a subprocess, and its log is polled by the page. The only
argument a caller can set is the news backfill's `max_requests` (1 to 5000).
Callers must be on localhost.

## Verification

- `tests/test_api.py` (19 tests, synthetic data because `data/` is gitignored)
  covers:
  - every endpoint's shape;
  - NaN serialised as null;
  - news filters, and that article text is never returned;
  - Tiingo rows filtered in public mode;
  - the figure whitelist and path-traversal attempts;
  - the SPA fallback not serving files outside `web/dist`;
  - pipeline endpoints rejected for non-local callers and absent in public mode;
  - `predict_latest` choosing the newest complete row per asset.
- `npm run build` runs the TypeScript type-check, and `npm run lint` is clean.
- Every page was loaded in headless Edge (Playwright) at 1440 px and 375 px:
  no console errors, no failed requests, no horizontal overflow. The mobile
  navigation drawer was exercised: it opens, navigates, closes on Escape, and
  hides Pipeline in public mode.
- A `features` job was run end to end through `POST /api/pipeline/run/features`.
  It exited 0, its log streamed, and the rebuilt `features.parquet` was
  byte-identical.
- `requirements-web.txt` was installed into a fresh virtualenv, and every
  endpoint was served from it.
- The Dockerfile is **not** verified: Docker is not installed on the
  development machine.

The rebuild surfaced two pipeline bugs, logged in `FAILURE_LOG.md`:

- The rolling correlation versus SPX had been empty since Stage 12. Weekend
  crypto rows left no complete 30-day window.
- `requirements.txt` pins versions older than those that trained the saved
  models.

## Theme

A light/dark toggle sits at the bottom of the sidebar (in the header on mobile). Light is the default; the choice is saved in the browser, and `?theme=dark` or `?theme=light` sets it from a link. Dark mode redefines the colour tokens in `web/src/theme/index.css` (`:root[data-theme="dark"]`), so components need no per-class dark variants. Charts swap their neutral colours through `darken()` in `web/src/lib/chartTheme.ts`.
