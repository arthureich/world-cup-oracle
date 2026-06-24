# Tactical Oracle

Tactical Oracle is a local analytical MVP for modeling the 2026 World Cup.

The project builds a small, testable pipeline:

1. FIFA points initialize a custom cycle Elo.
2. Elo is adjusted by match result, importance, goal margin, penalties, home field and recency.
3. Adjusted Elo maps to TSI, the Team Strength Index.
4. TSI receives capped squad and long-term odds adjustments.
5. TSI is split into attack and defense through a style profile.
6. Attack and defense produce expected goals.
7. Poisson and Monte Carlo functions simulate matches, groups and knockouts.
8. Validation utilities compute Brier Score, Log Loss, calibration bins and score likelihood.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Mock data

The code ships with in-memory mock datasets and a writer for Parquet fixtures.

```bash
tactical-oracle-mocks
```

That creates:

```text
data/raw/teams_mock.parquet
data/raw/fifa_points_mock.parquet
data/raw/matches_cycle_mock.parquet
data/raw/worldcup_groups_mock.parquet
data/raw/worldcup_schedule_mock.parquet
```

## Smoke pipeline

```bash
tactical-oracle-mock-pipeline
```

## Tests

```bash
pytest
```

## Notes

This MVP intentionally does not use Spark, PostgreSQL, FastAPI or React. The first version is
local, analytical and file-based.
