from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from typing import Any

from tactical_oracle.config import ValidationParameters
from tactical_oracle.data.io import read_parquet, write_rows_parquet
from tactical_oracle.validation import (
    brier_score,
    calibration_bins,
    expected_calibration_error,
    log_loss,
    poisson_score_log_likelihood,
)


OUTCOME_LABELS = ("win_a", "draw", "win_b")


def _outcome(goals_a: int, goals_b: int) -> int:
    if goals_a > goals_b:
        return 0
    if goals_a == goals_b:
        return 1
    return 2


def _completed_result_rows(match_stats: Any, probabilities: Any) -> list[dict[str, Any]]:
    stat_rows = match_stats.select(
        [
            "match_number",
            "match_id",
            "team",
            "opponent",
            "goals",
            "goals_against",
            "xg",
            "xg_against",
            "data_source",
        ]
    ).to_dicts()
    stats_by_match_team = {
        (int(row["match_number"]), str(row["team"])): row for row in stat_rows
    }

    rows: list[dict[str, Any]] = []
    for prediction in probabilities.sort("match_number").to_dicts():
        match_number = int(prediction["match_number"])
        team_a = str(prediction["team_a"])
        team_b = str(prediction["team_b"])
        stat_a = stats_by_match_team.get((match_number, team_a))
        stat_b = stats_by_match_team.get((match_number, team_b))
        if stat_a is None or stat_b is None:
            continue
        goals_a = int(stat_a["goals"])
        goals_b = int(stat_b["goals"])
        outcome = _outcome(goals_a, goals_b)
        probabilities_vector = [
            float(prediction["p_win_a"]),
            float(prediction["p_draw"]),
            float(prediction["p_win_b"]),
        ]
        rows.append(
            {
                "match_number": match_number,
                "match_id": str(prediction["match_id"]),
                "group": prediction["group"],
                "team_a": team_a,
                "team_b": team_b,
                "goals_a": goals_a,
                "goals_b": goals_b,
                "xg_a": stat_a.get("xg"),
                "xg_b": stat_b.get("xg"),
                "lambda_a": float(prediction["lambda_a"]),
                "lambda_b": float(prediction["lambda_b"]),
                "p_win_a": probabilities_vector[0],
                "p_draw": probabilities_vector[1],
                "p_win_b": probabilities_vector[2],
                "outcome": OUTCOME_LABELS[outcome],
                "outcome_index": outcome,
                "actual_outcome_probability": probabilities_vector[outcome],
                "score_log_likelihood": poisson_score_log_likelihood(
                    goals_a,
                    goals_b,
                    float(prediction["lambda_a"]),
                    float(prediction["lambda_b"]),
                ),
                "data_source_a": stat_a.get("data_source"),
                "data_source_b": stat_b.get("data_source"),
            }
        )
    return rows


def _calibration_bin_rows(rows: list[dict[str, Any]], n_bins: int) -> list[dict[str, Any]]:
    bin_rows: list[dict[str, Any]] = []
    for outcome_index, outcome_name in enumerate(OUTCOME_LABELS):
        probabilities = [float(row[f"p_{outcome_name}"]) for row in rows]
        outcomes = [int(row["outcome_index"]) == outcome_index for row in rows]
        for bin_index, bucket in enumerate(calibration_bins(probabilities, outcomes, n_bins)):
            bin_rows.append(
                {
                    "outcome": outcome_name,
                    "bin": bin_index,
                    "lower": bucket.lower,
                    "upper": bucket.upper,
                    "count": bucket.count,
                    "mean_predicted": bucket.mean_predicted,
                    "observed_frequency": bucket.observed_frequency,
                    "absolute_error": abs(bucket.mean_predicted - bucket.observed_frequency),
                }
            )
    return bin_rows


def _summary_rows(rows: list[dict[str, Any]], bin_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return [
            {
                "metric": "match_count",
                "value": 0.0,
                "match_count": 0,
                "notes": "No completed matches with predictions were available.",
            }
        ]
    probability_vectors = [
        [float(row["p_win_a"]), float(row["p_draw"]), float(row["p_win_b"])] for row in rows
    ]
    outcomes = [int(row["outcome_index"]) for row in rows]
    score_ll = sum(float(row["score_log_likelihood"]) for row in rows) / len(rows)
    ece_bins = [
        bucket
        for outcome in OUTCOME_LABELS
        for bucket in calibration_bins(
            [float(row[f"p_{outcome}"]) for row in rows],
            [str(row["outcome"]) == outcome for row in rows],
            ValidationParameters().calibration_bins,
        )
    ]
    return [
        {
            "metric": "match_count",
            "value": float(len(rows)),
            "match_count": len(rows),
            "notes": "Completed matches with model predictions.",
        },
        {
            "metric": "brier_score",
            "value": brier_score(probability_vectors, outcomes),
            "match_count": len(rows),
            "notes": "Lower is better.",
        },
        {
            "metric": "log_loss",
            "value": log_loss(probability_vectors, outcomes),
            "match_count": len(rows),
            "notes": "Lower is better.",
        },
        {
            "metric": "score_log_likelihood",
            "value": score_ll,
            "match_count": len(rows),
            "notes": "Average Poisson log-likelihood of the exact score. Higher is better.",
        },
        {
            "metric": "score_negative_log_likelihood",
            "value": -score_ll,
            "match_count": len(rows),
            "notes": "Negative average score log-likelihood. Lower is better.",
        },
        {
            "metric": "expected_calibration_error",
            "value": expected_calibration_error(ece_bins),
            "match_count": len(rows),
            "notes": "One-vs-rest calibration over win/draw/loss bins. Lower is better.",
        },
    ]


def _american_or_decimal_to_probability(value: Any) -> float | None:
    if value is None:
        return None
    odd = float(value)
    if odd <= 0 and odd > -100:
        return None
    if odd >= 100:
        return 100.0 / (odd + 100.0)
    if odd <= -100:
        return abs(odd) / (abs(odd) + 100.0)
    if odd > 1.0:
        return 1.0 / odd
    return None


def _odds_comparison_rows(
    validation_rows: list[dict[str, Any]],
    odds_path: Path,
) -> list[dict[str, Any]]:
    if not odds_path.exists():
        return [
            {
                "status": "missing_odds_file",
                "match_count": 0,
                "model_log_loss": None,
                "odds_log_loss": None,
                "model_brier": None,
                "odds_brier": None,
                "notes": f"{odds_path} was not found.",
            }
        ]

    odds = read_parquet(odds_path)
    required = {"match_id", "odd_a", "odd_draw", "odd_b"}
    if not required.issubset(set(odds.columns)):
        return [
            {
                "status": "unsupported_odds_schema",
                "match_count": 0,
                "model_log_loss": None,
                "odds_log_loss": None,
                "model_brier": None,
                "odds_brier": None,
                "notes": f"Expected columns: {', '.join(sorted(required))}.",
            }
        ]

    odds_by_match = {str(row["match_id"]): row for row in odds.to_dicts()}
    model_vectors: list[list[float]] = []
    odds_vectors: list[list[float]] = []
    outcomes: list[int] = []
    for row in validation_rows:
        odds_row = odds_by_match.get(str(row["match_id"]))
        if odds_row is None:
            continue
        implied = [
            _american_or_decimal_to_probability(odds_row["odd_a"]),
            _american_or_decimal_to_probability(odds_row["odd_draw"]),
            _american_or_decimal_to_probability(odds_row["odd_b"]),
        ]
        if any(value is None for value in implied):
            continue
        total = sum(float(value) for value in implied)
        if total <= 0:
            continue
        odds_vectors.append([float(value) / total for value in implied])
        model_vectors.append([float(row["p_win_a"]), float(row["p_draw"]), float(row["p_win_b"])])
        outcomes.append(int(row["outcome_index"]))

    if not outcomes:
        return [
            {
                "status": "no_overlapping_odds",
                "match_count": 0,
                "model_log_loss": None,
                "odds_log_loss": None,
                "model_brier": None,
                "odds_brier": None,
                "notes": "No completed model matches overlapped with odds rows.",
            }
        ]
    return [
        {
            "status": "ok",
            "match_count": len(outcomes),
            "model_log_loss": log_loss(model_vectors, outcomes),
            "odds_log_loss": log_loss(odds_vectors, outcomes),
            "model_brier": brier_score(model_vectors, outcomes),
            "odds_brier": brier_score(odds_vectors, outcomes),
            "notes": "Odds probabilities are normalized to remove overround.",
        }
    ]


def _markdown_report(
    summary_rows: list[dict[str, Any]],
    odds_rows: list[dict[str, Any]],
    output_paths: list[Path],
) -> str:
    summary = {row["metric"]: row for row in summary_rows}
    odds = odds_rows[0] if odds_rows else {"status": "not_run"}

    def metric(name: str, digits: int = 4) -> str:
        value = summary.get(name, {}).get("value")
        if value is None:
            return "-"
        return f"{float(value):.{digits}f}"

    lines = [
        "# Validation Report",
        "",
        f"Generated on: {date.today().isoformat()}",
        "",
        "## Summary",
        "",
        f"- Completed matches: {int(float(summary.get('match_count', {}).get('value', 0.0)))}",
        f"- Brier Score: {metric('brier_score')}",
        f"- Log Loss: {metric('log_loss')}",
        f"- Score log-likelihood: {metric('score_log_likelihood')}",
        f"- Score negative log-likelihood: {metric('score_negative_log_likelihood')}",
        f"- Expected calibration error: {metric('expected_calibration_error')}",
        "",
        "## Odds Comparison",
        "",
        f"- Status: {odds.get('status')}",
        f"- Matched odds rows: {odds.get('match_count', 0)}",
    ]
    if odds.get("status") == "ok":
        lines.extend(
            [
                f"- Model Log Loss: {float(odds['model_log_loss']):.4f}",
                f"- Odds Log Loss: {float(odds['odds_log_loss']):.4f}",
                f"- Model Brier: {float(odds['model_brier']):.4f}",
                f"- Odds Brier: {float(odds['odds_brier']):.4f}",
            ]
        )
    else:
        lines.append(f"- Notes: {odds.get('notes')}")
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            *[f"- `{path.as_posix()}`" for path in output_paths],
            "",
        ]
    )
    return "\n".join(lines)


def build_worldcup_validation_report(
    interim_dir: str | Path = "data/interim",
    processed_dir: str | Path = "data/processed",
    report_dir: str | Path = "docs/reports",
    odds_path: str | Path = "data/interim/odds_match_by_match.parquet",
) -> list[Path]:
    interim = Path(interim_dir)
    processed = Path(processed_dir)
    reports = Path(report_dir)
    reports.mkdir(parents=True, exist_ok=True)

    validation_rows = _completed_result_rows(
        read_parquet(interim / "worldcup_match_stats.parquet"),
        read_parquet(processed / "match_probabilities.parquet"),
    )
    bin_rows = _calibration_bin_rows(validation_rows, ValidationParameters().calibration_bins)
    summary_rows = _summary_rows(validation_rows, bin_rows)
    odds_rows = _odds_comparison_rows(validation_rows, Path(odds_path))

    output_paths = [
        processed / "validation_match_predictions.parquet",
        processed / "validation_summary.parquet",
        processed / "validation_calibration_bins.parquet",
        processed / "validation_odds_comparison.parquet",
    ]
    write_rows_parquet(validation_rows, output_paths[0])
    write_rows_parquet(summary_rows, output_paths[1])
    write_rows_parquet(bin_rows, output_paths[2])
    write_rows_parquet(odds_rows, output_paths[3])

    report_path = reports / f"validation-{date.today().isoformat()}.md"
    report_path.write_text(
        _markdown_report(summary_rows, odds_rows, output_paths),
        encoding="utf-8",
    )
    return [*output_paths, report_path]


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate World Cup Oracle predictions.")
    parser.add_argument("--interim-dir", default="data/interim")
    parser.add_argument("--processed-dir", default="data/processed")
    parser.add_argument("--report-dir", default="docs/reports")
    parser.add_argument("--odds-path", default="data/interim/odds_match_by_match.parquet")
    args = parser.parse_args()

    for path in build_worldcup_validation_report(
        interim_dir=args.interim_dir,
        processed_dir=args.processed_dir,
        report_dir=args.report_dir,
        odds_path=args.odds_path,
    ):
        print(path)


if __name__ == "__main__":
    main()
