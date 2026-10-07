# Agent instructions

Project: SBB delay propagation analysis (amplifier / absorber sections and stops).
Full requirements: `docs/requirements.md` (German). Read it before non-trivial work.

## Conventions

- Environment: uv, Python 3.13. Add dependencies with `uv add`, never pip. Run everything via `uv run`.
- Code in English, docs (README, log, report) in German.
- Reusable logic goes in `src/sbb_delays/`; notebooks (marimo, plain `.py`) only explore and present.
- Paths via `sbb_delays.paths`, never hard-coded.
- Raw data in `data/raw/` is read-only. Downloads only through `sbb_delays.download`
  (records URL, date, SHA-256 in `data/raw/manifest.csv`).
- Derived data as Parquet or DuckDB in `data/processed/`.
- Analysis reads the rail-only daily Parquet files in `data/processed/istdaten_rail/`
  (built by `uv run python -m sbb_delays.load`), not the raw CSVs.
- Before finishing: `uv run pytest` and `uv run ruff check . && uv run ruff format --check .` must pass.

## Domain rules (from requirements)

- Only `REAL` in `AN_PROGNOSE_STATUS` / `AB_PROGNOSE_STATUS` counts as measured; treat
  `PROGNOSE` / `GESCHAETZT` separately. `UNBEKANNT` is not a measurement (all cancelled rows have it).
- A trip = (`BETRIEBSTAG`, `FAHRT_BEZEICHNER`). A section = two consecutive stops of the same trip,
  ordered by `ZEILE` (row number in the daily CSV), never by scheduled time (minute resolution, ties).
- Analyse Swiss stops only (`BPUIC` 85xxxxx): foreign stops are ~11 % `REAL` and have no coordinates.
- Drop exact duplicate rows, sections whose scheduled time runs backwards, and delays beyond ±12 h.
- Stop delay is biased: 73 % of stops have scheduled dwell 0, where it equals the actual dwell time.
  Never rank raw stop delays without a reference per scheduled dwell (see `docs/log.md`, 2026-10-06).
- Cancellations (`FAELLT_AUS_TF`) stay in the data; handle explicitly.
- Timetable change in December: a year contains two timetables.
- Section delay = arrival delay at B − departure delay at A.
  Stop delay = departure delay − arrival delay at the same stop.
- No forecasting model, no causal analysis.

## Workflow

- `main` is protected; work on feature branches, merge via PR reviewed by the other team member.
- Small, focused commits.
- Log decisions, assumptions, hypotheses and AI use in `docs/log.md` in the same PR as the code
  (dated entries, no prompt transcripts). Hypotheses are logged *before* the analysis.
- Every key number needs a check (baseline, permutation, placebo, sum check or stability),
  see requirements section 6.
