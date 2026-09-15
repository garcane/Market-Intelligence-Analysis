# SPLIT.md — Temporal Train/Validation/Test Split (Stage 8)

## Methodology

Chronological split by calendar date, applied identically across every asset — **never** a random split. This directly replaces the original repo's `train_test_split(X, y, test_size=0.2, random_state=42)` on time-series-featured data, the leakage bug documented in `PROJECT_AUDIT.md` §3a.

```text
TRAIN        : ingestion start (2023-06-01) -> 2025-05-31
VALIDATION   : 2026-01-31 -> 2026-01-31 boundary, i.e. 2025-06-01 -> 2026-01-31
TEST         : 2026-02-01 -> present (2026-09-12 as of the last ingestion run)
```

These boundaries split the actual ingested history (2023-06-01 → 2026-09-12, ~1,199 days) roughly 60/20/20 by calendar time — computed directly from the real data range, not copied from the target spec's illustrative example (which assumed 2022–2026 calendar-year boundaries that don't match what's actually been ingested).

## Embargo: the leakage vector a naive date-boundary split misses

A target `target_h(t)` resolves at date `t + h` (see `TARGET.md`). A row dated at the very end of the train window can have `t + h` fall inside the validation window — meaning that row's label was computed using a price the model isn't supposed to have "seen" until validation. This is real, not hypothetical: verified directly in the live data (MSFT, 5-day horizon) —

| date | target_date_5d | split_5d |
|---|---|---|
| 2025-05-22 | 2025-05-30 | train |
| 2025-05-23 | **2025-06-02** | **excluded_embargo** |
| 2025-05-27 | 2025-06-03 | excluded_embargo |
| 2025-05-28 | 2025-06-04 | excluded_embargo |
| 2025-05-29 | 2025-06-05 | excluded_embargo |
| 2025-05-30 | 2025-06-06 | excluded_embargo |
| 2025-06-02 | 2025-06-09 | validation |

`src/models/split.py::assign_split` implements this by comparing each row's own `date` against `target_date_{h}d` (the exact calendar date the label resolves on, added in `src/features/target.py`) — not a calendar-day approximation. A row is only labeled `train` if **both** its date and its target's resolution date fall on or before `train_end`; same logic at the validation/test boundary. Rows that fail this are labeled `excluded_embargo`, not silently kept.

The embargo window is horizon-specific: a 10-day-ahead target needs roughly twice the embargo zone of a 5-day-ahead one. Confirmed in the live run — `excluded_embargo` count scales linearly with horizon (12 rows at 1-day, 60 at 5-day, 120 at 10-day — exactly `2 boundaries × h days × 6 assets`).

## Live Split Counts (`data/processed/split_report.json`)

| Horizon | Train | Validation | Test | Excluded (embargo) | Excluded (no target — tail of data) |
|---|---|---|---|---|---|
| 1-day | 3,690 (61.0%) | 1,233 (20.4%) | 1,128 (18.6%) | 12 | 6 |
| 5-day | 3,666 (60.6%) | 1,209 (20.0%) | 1,104 (18.3%) | 60 | 30 |
| 10-day | 3,636 (60.1%) | 1,179 (19.5%) | 1,074 (17.8%) | 120 | 60 |

Each horizon has its own `split_{h}d` column in `data/processed/ml_dataset/ml_dataset.parquet` — a row can be `train` for `split_1d` and `excluded_embargo` for `split_10d` at the same date, since the safe boundary differs by horizon. Stage 9's model training must select exactly one horizon's split column per experiment run, never mix them.

## Verification

- `tests/test_split.py::TestAssignSplit::test_embargo_excludes_rows_whose_target_crosses_boundary` — constructs a synthetic series, manually identifies which rows *should* be embargoed given a known boundary, and asserts the function agrees.
- `tests/test_split.py::TestAssignSplit::test_no_embargo_needed_check_train_target_dates_never_exceed_train_end` — the actual leakage guarantee, stated directly: every row labeled `train` has `target_date_h <= train_end`, for every horizon, by construction.
- `tests/test_split.py::TestAddSplitLabels::test_never_shuffles_rows` — regression guard: row order in equals row order out, nothing in this module reorders or samples rows.
- `src/models/run_split.py`'s own validation independently re-checks, on the real merged dataset, that `max(train dates) < min(validation dates) < ... < min(test dates)` per asset per horizon — not just on synthetic test data.
- Manually spot-checked against real data above (MSFT, 5-day horizon boundary) — the embargoed rows are exactly the ones whose `target_date_5d` crosses `train_end`.

## Stage 8 Completion Check

- [x] Chronological (not random) split
- [x] Boundaries justified against the actual ingested date range, not copied from the spec's illustrative example
- [x] Embargo implemented and verified against real subtle leakage (target resolving past a split boundary) — not just the obvious "don't shuffle" case
- [x] Horizon-specific split columns, never mixed
- [x] Round-trip stored (`data/processed/ml_dataset/ml_dataset.parquet`)
- [x] `walk_forward_folds()` utility added for Stage 19's robustness testing, not used by the primary single-split experiment

**Stage 8 status: COMPLETE.**
