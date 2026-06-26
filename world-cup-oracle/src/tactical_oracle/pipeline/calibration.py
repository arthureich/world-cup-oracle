from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from tactical_oracle.attack_defense import build_components, profile_from_goal_totals
from tactical_oracle.calibration import (
    attack_defense_grid,
    calibration_bin_rows,
    evaluate_attack_defense_parameters,
)
from tactical_oracle.calibration.attack_defense import predict_matches, result_row
from tactical_oracle.data.io import read_parquet, write_rows_parquet
from tactical_oracle.elo import compute_elo_ratings
from tactical_oracle.pipeline.real_outputs import (
    build_real_tsi_ratings,
    cycle_goal_rates,
    fifa_team_names,
    filter_matches_to_fifa_teams,
)


def _rows(path: Path) -> list[dict[str, Any]]:
    return read_parquet(path).to_dicts()


def _optional_rows(path: Path) -> list[dict[str, Any]]:
    return _rows(path) if path.exists() else []


def _split_matches(
    matches: list[dict[str, Any]],
    split_date: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    train = [row for row in matches if str(row["date"]) < split_date]
    evaluation = [row for row in matches if str(row["date"]) >= split_date]
    if not train or not evaluation:
        raise ValueError("split_date must leave at least one train and one evaluation match")
    return train, evaluation


def _calibration_base_inputs(interim_dir: str | Path) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
]:
    interim = Path(interim_dir)
    fifa_points = _rows(interim / "fifa_points.parquet")
    matches = _rows(interim / "matches_cycle.parquet")
    squads = _optional_rows(interim / "squads.parquet")
    odds = _optional_rows(interim / "odds_long_term.parquet")
    filtered_matches = filter_matches_to_fifa_teams(matches, fifa_team_names(fifa_points))
    elo = compute_elo_ratings(fifa_points, filtered_matches)
    tsi = build_real_tsi_ratings(
        elo,
        filtered_matches,
        squad_rows=squads,
        odds_rows=odds,
    )
    return fifa_points, filtered_matches, squads, tsi


def calibrate_attack_defense_rows(
    interim_dir: str | Path = "data/interim",
    split_date: str = "2025-01-01",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    _, matches, _, tsi = _calibration_base_inputs(interim_dir)
    train_matches, evaluation_matches = _split_matches(matches, split_date)
    goals_for, goals_against = cycle_goal_rates(matches)

    grid_rows: list[dict[str, Any]] = []
    candidates = attack_defense_grid()
    for candidate_id, params in enumerate(candidates, start=1):
        profiles = profile_from_goal_totals(goals_for, goals_against, params=params)
        # Calibration uses TSI_model, not TSI_pre, to avoid long-term market leakage.
        components = build_components(
            {team: rating.tsi_model for team, rating in tsi.items()},
            profiles,
        )
        train_result = evaluate_attack_defense_parameters(
            train_matches,
            components,
            params,
        )
        evaluation_result = evaluate_attack_defense_parameters(
            evaluation_matches,
            components,
            params,
        )
        for split, result in (("train", train_result), ("evaluation", evaluation_result)):
            grid_rows.append({"candidate_id": candidate_id, **result_row(result, split)})

    evaluation_rows = [row for row in grid_rows if row["split"] == "evaluation"]
    best = min(
        evaluation_rows,
        key=lambda row: (
            float(row["log_loss"]),
            float(row["score_negative_log_likelihood"]),
            float(row["brier"]),
        ),
    )
    best_candidate_id = int(best["candidate_id"])
    summary_rows = [
        {"selection": "best_by_evaluation_log_loss", **row}
        for row in grid_rows
        if int(row["candidate_id"]) == best_candidate_id
    ]

    best_params = candidates[best_candidate_id - 1]
    best_profiles = profile_from_goal_totals(goals_for, goals_against, params=best_params)
    best_components = build_components(
        {team: rating.tsi_model for team, rating in tsi.items()},
        best_profiles,
    )
    best_predictions, _ = predict_matches(evaluation_matches, best_components, best_params)
    bin_rows = [
        {"candidate_id": best_candidate_id, "split": "evaluation", **row}
        for row in calibration_bin_rows(best_predictions)
    ]

    return grid_rows, summary_rows, bin_rows


def write_attack_defense_calibration_outputs(
    interim_dir: str | Path = "data/interim",
    output_dir: str | Path = "data/processed",
    split_date: str = "2025-01-01",
) -> list[Path]:
    grid_rows, summary_rows, bin_rows = calibrate_attack_defense_rows(
        interim_dir,
        split_date,
    )
    output = Path(output_dir)
    outputs = {
        "calibration_attack_defense_grid.parquet": grid_rows,
        "calibration_attack_defense_summary.parquet": summary_rows,
        "calibration_attack_defense_bins.parquet": bin_rows,
    }

    written: list[Path] = []
    for filename, rows in outputs.items():
        path = output / filename
        write_rows_parquet(rows, path)
        written.append(path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calibrate attack/defense expected-goals parameters."
    )
    parser.add_argument("--interim-dir", default="data/interim")
    parser.add_argument("--output-dir", default="data/processed")
    parser.add_argument("--split-date", default="2025-01-01")
    args = parser.parse_args()

    for path in write_attack_defense_calibration_outputs(
        interim_dir=args.interim_dir,
        output_dir=args.output_dir,
        split_date=args.split_date,
    ):
        print(path)


if __name__ == "__main__":
    main()
