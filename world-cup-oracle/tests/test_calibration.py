from __future__ import annotations

from world_cup_oracle.attack_defense import split_attack_defense
from world_cup_oracle.calibration import evaluate_attack_defense_parameters
from world_cup_oracle.config import AttackDefenseParameters
from world_cup_oracle.data.io import read_parquet, write_rows_parquet
from world_cup_oracle.pipeline.calibration import write_attack_defense_calibration_outputs


def test_evaluate_attack_defense_parameters_scores_predictions() -> None:
    components = {
        "A": split_attack_defense("A", tsi=12.0, profile=0.0),
        "B": split_attack_defense("B", tsi=10.0, profile=0.0),
    }
    result = evaluate_attack_defense_parameters(
        [
            {
                "match_id": "m1",
                "date": "2024-01-01",
                "team_a": "A",
                "team_b": "B",
                "goals_a": 2,
                "goals_b": 0,
                "home_team": "A",
                "neutral_site": False,
            }
        ],
        components,
        AttackDefenseParameters(base_goals=1.25, k=0.08, host_gamma=0.1),
    )

    assert result.match_count == 1
    assert result.skipped_count == 0
    assert result.brier >= 0.0
    assert result.log_loss >= 0.0
    assert result.score_negative_log_likelihood >= 0.0


def test_write_attack_defense_calibration_outputs_writes_three_artifacts(
    tmp_path,
    monkeypatch,
) -> None:
    interim = tmp_path / "interim"
    processed = tmp_path / "processed"
    write_rows_parquet(
        [
            {"team": "A", "fifa_points": 1600.0, "ranking_date": "2022-12-22", "fifa_rank": 1},
            {"team": "B", "fifa_points": 1500.0, "ranking_date": "2022-12-22", "fifa_rank": 2},
        ],
        interim / "fifa_points.parquet",
    )
    write_rows_parquet(
        [
            {
                "match_id": "m1",
                "date": "2024-01-01",
                "team_a": "A",
                "team_b": "B",
                "goals_a": 2,
                "goals_b": 1,
                "competition": "Friendly",
                "stage": "single",
                "match_type": "friendly",
                "home_team": "A",
                "neutral_site": False,
                "went_to_penalties": False,
                "penalty_winner": None,
            },
            {
                "match_id": "m2",
                "date": "2025-01-01",
                "team_a": "B",
                "team_b": "A",
                "goals_a": 0,
                "goals_b": 1,
                "competition": "Friendly",
                "stage": "single",
                "match_type": "friendly",
                "home_team": "B",
                "neutral_site": False,
                "went_to_penalties": False,
                "penalty_winner": None,
            },
        ],
        interim / "matches_cycle.parquet",
    )
    monkeypatch.setattr(
        "world_cup_oracle.pipeline.calibration.attack_defense_grid",
        lambda: [
            AttackDefenseParameters(base_goals=1.2, k=0.05, host_gamma=0.0),
            AttackDefenseParameters(base_goals=1.3, k=0.09, host_gamma=0.1),
        ],
    )

    written = write_attack_defense_calibration_outputs(
        interim,
        processed,
        split_date="2025-01-01",
    )

    assert {path.name for path in written} == {
        "calibration_attack_defense_grid.parquet",
        "calibration_attack_defense_summary.parquet",
        "calibration_attack_defense_bins.parquet",
    }
    grid = read_parquet(processed / "calibration_attack_defense_grid.parquet")
    summary = read_parquet(processed / "calibration_attack_defense_summary.parquet")
    assert grid.height == 4
    assert summary.height == 2
