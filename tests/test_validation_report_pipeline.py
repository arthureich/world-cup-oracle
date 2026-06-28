from __future__ import annotations

from world_cup_oracle.data.io import read_parquet, write_rows_parquet
from world_cup_oracle.pipeline.validation_report import build_worldcup_validation_report


def test_build_worldcup_validation_report_writes_metrics(tmp_path) -> None:
    interim = tmp_path / "interim"
    processed = tmp_path / "processed"
    reports = tmp_path / "reports"
    write_rows_parquet(
        [
            {
                "match_number": 1,
                "match_id": "m1",
                "team": "A",
                "opponent": "B",
                "goals": 2,
                "goals_against": 1,
                "xg": 1.4,
                "xg_against": 0.8,
                "data_source": "test",
            },
            {
                "match_number": 1,
                "match_id": "m1",
                "team": "B",
                "opponent": "A",
                "goals": 1,
                "goals_against": 2,
                "xg": 0.8,
                "xg_against": 1.4,
                "data_source": "test",
            },
        ],
        interim / "worldcup_match_stats.parquet",
    )
    write_rows_parquet(
        [
            {
                "match_id": "m1",
                "match_number": 1,
                "group": "A",
                "team_a": "A",
                "team_b": "B",
                "lambda_a": 1.3,
                "lambda_b": 0.9,
                "p_win_a": 0.55,
                "p_draw": 0.25,
                "p_win_b": 0.20,
            }
        ],
        processed / "match_probabilities.parquet",
    )

    written = build_worldcup_validation_report(interim, processed, reports)

    written_names = {path.name for path in written}
    assert {
        "validation_match_predictions.parquet",
        "validation_summary.parquet",
        "validation_calibration_bins.parquet",
        "validation_odds_comparison.parquet",
    }.issubset(written_names)
    report_path = next(path for path in written if path.name.startswith("validation-"))
    summary = read_parquet(processed / "validation_summary.parquet")
    metrics = {row["metric"]: row["value"] for row in summary.to_dicts()}
    assert metrics["match_count"] == 1.0
    assert metrics["brier_score"] >= 0.0
    odds = read_parquet(processed / "validation_odds_comparison.parquet")
    assert odds.row(0, named=True)["status"] == "missing_odds_file"
    assert "Brier Score" in report_path.read_text(encoding="utf-8")
