# World Cup Oracle

World Cup Oracle is a local analytical MVP for modeling the 2026 World Cup.

The project builds a small, testable pipeline:

1. FIFA points initialize a custom cycle Elo.
2. Elo is adjusted by match result, importance, goal margin, penalties, home field and recency.
3. Adjusted Elo maps to TSI, the Team Strength Index.
4. TSI receives capped squad and long-term odds adjustments.
5. TSI is split into attack and defense through a style profile.
6. Attack and defense produce expected goals.
7. Poisson and Monte Carlo functions simulate matches, groups and knockouts.
8. Group-stage performance separates process and result surprise.
9. Validation utilities compute Brier Score, Log Loss, calibration bins and score likelihood.

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
data/raw/squads_mock.parquet
data/raw/odds_long_term_mock.parquet
data/raw/worldcup_annex_c_mock.parquet
```

## Smoke pipeline

```bash
tactical-oracle-mock-pipeline
```

## Processed outputs

```bash
tactical-oracle-normalize-mocks
tactical-oracle-validate-annex-c data/interim/worldcup_annex_c.parquet
tactical-oracle-build-mock-outputs
```

That creates:

```text
data/processed/ratings_elo.parquet
data/processed/squad_adjustments.parquet
data/processed/odds_adjustments.parquet
data/processed/tsi_pre_cup.parquet
data/processed/attack_defense_pre_cup.parquet
data/processed/match_probabilities.parquet
```

`tactical-oracle-validate-annex-c --complete` requires the full official Annex C table with
495 combinations. The bundled mock table is intentionally partial and only exercises the loader.

## Tests

```bash
pytest
ruff check .
```

## Dashboard

Install the app dependencies and run the local Streamlit dashboard:

```bash
pip install -e ".[app]"
streamlit run app/streamlit_app.py
```

The dashboard reads the processed Parquet outputs in `data/processed/`, including:

```text
current_group_standings.parquet
next_matches.parquet
group_projection.parquet
team_stage_probabilities.parquet
knockout_match_probabilities.parquet
match_performance_audit.parquet
calibration_b3_review.parquet
```

## Notes

This MVP intentionally does not use Spark, PostgreSQL, FastAPI or React. The first version is
local, analytical and file-based.
