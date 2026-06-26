from __future__ import annotations

import math

import polars as pl
import pytest

from tactical_oracle.data.io import write_rows_parquet
from tactical_oracle.pipeline.match_performance import (
    build_real_match_performance_outputs,
    match_performance_audit_frame,
    match_performance_frame,
    team_performance_adjustment_frame,
)


def _soft_cap(value: float, cap: float = 4.0) -> float:
    return cap * math.tanh(value / cap)


def test_match_performance_frame_builds_tsi_delta_with_red_card_weight(tmp_path) -> None:
    stats = tmp_path / "match_stats.parquet"
    probabilities = tmp_path / "probabilities.parquet"
    write_rows_parquet(
        [
            {
                "match_id": "m1",
                "match_number": 1,
                "date": "2026-06-11",
                "team": "Brazil",
                "opponent": "Argentina",
                "goals": 2,
                "goals_against": 0,
                "xg": 2.0,
                "xg_against": 0.5,
                "clear_chances": None,
                "clear_chances_against": None,
                "shots_on_target": None,
                "shots_on_target_against": None,
                "shots": None,
                "shots_against": None,
                "red_cards": 1,
                "first_red_card_minute": 60,
            },
            {
                "match_id": "m1",
                "match_number": 1,
                "date": "2026-06-11",
                "team": "Argentina",
                "opponent": "Brazil",
                "goals": 0,
                "goals_against": 2,
                "xg": 0.5,
                "xg_against": 2.0,
                "clear_chances": None,
                "clear_chances_against": None,
                "shots_on_target": None,
                "shots_on_target_against": None,
                "shots": None,
                "shots_against": None,
                "red_cards": 0,
                "first_red_card_minute": None,
            },
        ],
        stats,
    )
    write_rows_parquet(
        [
            {
                "match_id": "m1",
                "match_number": 1,
                "team_a": "Brazil",
                "team_b": "Argentina",
                "lambda_a": 1.0,
                "lambda_b": 1.0,
                "expected_points_a": 1.4,
                "expected_points_b": 1.4,
            }
        ],
        probabilities,
    )

    frame = match_performance_frame(
        match_stats=pl.read_parquet(stats),
        match_probabilities=pl.read_parquet(probabilities),
    )
    rows = {row["team"]: row for row in frame.to_dicts()}

    assert rows["Brazil"]["process_for"] == 2.0
    assert rows["Brazil"]["process_against"] == 0.5
    assert rows["Brazil"]["raw_match_tsi_delta"] == pytest.approx(10.8)
    compressed_brazil = _soft_cap(10.8)
    compressed_argentina = _soft_cap(-10.2)
    centered_brazil = compressed_brazil - ((compressed_brazil + compressed_argentina) / 2.0)
    assert rows["Brazil"]["compressed_match_tsi_delta"] == pytest.approx(compressed_brazil)
    assert rows["Brazil"]["match_tsi_delta"] == pytest.approx(centered_brazil)
    delta_sum = rows["Brazil"]["match_tsi_delta"] + rows["Argentina"]["match_tsi_delta"]
    assert delta_sum == pytest.approx(0.0)
    assert rows["Brazil"]["weighted_match_tsi_delta"] + rows["Argentina"][
        "weighted_match_tsi_delta"
    ] == pytest.approx(0.0)
    assert rows["Brazil"]["match_weight"] == pytest.approx(1.0 - 0.5 * (30 / 90))
    assert rows["Argentina"]["match_tsi_delta"] < 0
    assert rows["Argentina"]["match_weight"] == 1.0


def test_match_performance_frame_rewards_underdog_draw_against_strong_favorite(
    tmp_path,
) -> None:
    stats = tmp_path / "match_stats.parquet"
    probabilities = tmp_path / "probabilities.parquet"
    write_rows_parquet(
        [
            {
                "match_id": "m1",
                "match_number": 1,
                "date": "2026-06-11",
                "team": "Cape Verde",
                "opponent": "Spain",
                "goals": 0,
                "goals_against": 0,
                "xg": 0.36,
                "xg_against": 1.55,
                "clear_chances": None,
                "clear_chances_against": None,
                "shots_on_target": None,
                "shots_on_target_against": None,
                "shots": None,
                "shots_against": None,
                "red_cards": 0,
                "first_red_card_minute": None,
            },
            {
                "match_id": "m1",
                "match_number": 1,
                "date": "2026-06-11",
                "team": "Spain",
                "opponent": "Cape Verde",
                "goals": 0,
                "goals_against": 0,
                "xg": 1.55,
                "xg_against": 0.36,
                "clear_chances": None,
                "clear_chances_against": None,
                "shots_on_target": None,
                "shots_on_target_against": None,
                "shots": None,
                "shots_against": None,
                "red_cards": 0,
                "first_red_card_minute": None,
            },
        ],
        stats,
    )
    write_rows_parquet(
        [
            {
                "match_id": "m1",
                "match_number": 1,
                "team_a": "Cape Verde",
                "team_b": "Spain",
                "lambda_a": 0.95,
                "lambda_b": 1.82,
                "expected_points_a": 0.81,
                "expected_points_b": 1.96,
            }
        ],
        probabilities,
    )

    frame = match_performance_frame(
        match_stats=pl.read_parquet(stats),
        match_probabilities=pl.read_parquet(probabilities),
    )
    rows = {row["team"]: row for row in frame.to_dicts()}

    assert rows["Cape Verde"]["result_surprise"] == pytest.approx(0.19)
    assert rows["Spain"]["result_surprise"] == pytest.approx(-0.96)
    assert rows["Cape Verde"]["match_tsi_delta"] > 0
    assert rows["Spain"]["match_tsi_delta"] < 0
    delta_sum = rows["Cape Verde"]["match_tsi_delta"] + rows["Spain"]["match_tsi_delta"]
    assert delta_sum == pytest.approx(0.0)


def test_match_performance_frame_uses_fotmob_process_metrics_instead_of_shots(
    tmp_path,
) -> None:
    stats = tmp_path / "match_stats.parquet"
    probabilities = tmp_path / "probabilities.parquet"
    write_rows_parquet(
        [
            {
                "match_id": "m1",
                "match_number": 1,
                "date": "2026-06-11",
                "team": "Brazil",
                "opponent": "Argentina",
                "goals": 1,
                "goals_against": 0,
                "xg": None,
                "xg_against": None,
                "clear_chances": None,
                "clear_chances_against": None,
                "shots_on_target": 99,
                "shots_on_target_against": 99,
                "shots": 99,
                "shots_against": 99,
                "touches_in_opposition_box": 20,
                "touches_in_opposition_box_against": 10,
                "opposition_half_passes": 100,
                "opposition_half_passes_against": 50,
                "ground_duels_won": 30,
                "ground_duels_won_against": 20,
                "ground_duels_won_pct": 60,
                "ground_duels_won_pct_against": 50,
                "successful_dribbles": 5,
                "successful_dribbles_against": 2,
                "successful_dribbles_pct": 50,
                "successful_dribbles_pct_against": 50,
                "red_cards": 0,
                "first_red_card_minute": None,
            },
            {
                "match_id": "m1",
                "match_number": 1,
                "date": "2026-06-11",
                "team": "Argentina",
                "opponent": "Brazil",
                "goals": 0,
                "goals_against": 2,
                "xg": 0.5,
                "xg_against": 2.0,
                "clear_chances": None,
                "clear_chances_against": None,
                "shots_on_target": None,
                "shots_on_target_against": None,
                "shots": None,
                "shots_against": None,
                "red_cards": 0,
                "first_red_card_minute": None,
            },
        ],
        stats,
    )
    write_rows_parquet(
        [
            {
                "match_id": "m1",
                "match_number": 1,
                "team_a": "Brazil",
                "team_b": "Argentina",
                "lambda_a": 1.0,
                "lambda_b": 1.0,
                "expected_points_a": 1.4,
                "expected_points_b": 1.4,
            }
        ],
        probabilities,
    )

    frame = match_performance_frame(
        match_stats=pl.read_parquet(stats),
        match_probabilities=pl.read_parquet(probabilities),
    )
    row = frame.filter(pl.col("team") == "Brazil").row(0, named=True)

    assert row["process_for"] == pytest.approx(0.6395833333)
    assert row["process_against"] == pytest.approx(0.3316666667)
    assert row["process_goal_difference"] == pytest.approx(0.3079166666)


def test_match_performance_frame_neutralizes_process_when_stats_are_missing(
    tmp_path,
) -> None:
    stats = tmp_path / "match_stats.parquet"
    probabilities = tmp_path / "probabilities.parquet"
    write_rows_parquet(
        [
            {
                "match_id": "m1",
                "match_number": 1,
                "date": "2026-06-11",
                "team": "Underdog",
                "opponent": "Favorite",
                "goals": 1,
                "goals_against": 0,
                "xg": None,
                "xg_against": None,
                "red_cards": 0,
                "first_red_card_minute": None,
            },
            {
                "match_id": "m1",
                "match_number": 1,
                "date": "2026-06-11",
                "team": "Favorite",
                "opponent": "Underdog",
                "goals": 0,
                "goals_against": 1,
                "xg": None,
                "xg_against": None,
                "red_cards": 0,
                "first_red_card_minute": None,
            },
        ],
        stats,
    )
    write_rows_parquet(
        [
            {
                "match_id": "m1",
                "match_number": 1,
                "team_a": "Underdog",
                "team_b": "Favorite",
                "lambda_a": 0.6,
                "lambda_b": 1.8,
                "expected_points_a": 0.6,
                "expected_points_b": 2.1,
            }
        ],
        probabilities,
    )

    frame = match_performance_frame(
        match_stats=pl.read_parquet(stats),
        match_probabilities=pl.read_parquet(probabilities),
    )
    rows = {row["team"]: row for row in frame.to_dicts()}

    assert rows["Underdog"]["has_process_stats"] is False
    assert rows["Underdog"]["process_surprise"] == pytest.approx(0.0)
    assert rows["Underdog"]["raw_match_tsi_delta"] == pytest.approx(7.2)
    assert rows["Favorite"]["process_surprise"] == pytest.approx(0.0)
    delta_sum = rows["Underdog"]["weighted_match_tsi_delta"] + rows["Favorite"][
        "weighted_match_tsi_delta"
    ]
    assert delta_sum == pytest.approx(0.0)


def test_team_performance_adjustment_frame_applies_post_group_weight(tmp_path) -> None:
    stats = tmp_path / "match_stats.parquet"
    probabilities = tmp_path / "probabilities.parquet"
    tsi = tmp_path / "tsi.parquet"
    write_rows_parquet(
        [
            {
                "match_id": "m1",
                "match_number": 1,
                "date": "2026-06-11",
                "team": "Brazil",
                "opponent": "Argentina",
                "goals": 2,
                "goals_against": 0,
                "xg": 2.0,
                "xg_against": 0.5,
                "clear_chances": None,
                "clear_chances_against": None,
                "shots_on_target": None,
                "shots_on_target_against": None,
                "shots": None,
                "shots_against": None,
                "red_cards": 0,
                "first_red_card_minute": None,
            },
            {
                "match_id": "m1",
                "match_number": 1,
                "date": "2026-06-11",
                "team": "Argentina",
                "opponent": "Brazil",
                "goals": 0,
                "goals_against": 2,
                "xg": 0.5,
                "xg_against": 2.0,
                "clear_chances": None,
                "clear_chances_against": None,
                "shots_on_target": None,
                "shots_on_target_against": None,
                "shots": None,
                "shots_against": None,
                "red_cards": 0,
                "first_red_card_minute": None,
            },
        ],
        stats,
    )
    write_rows_parquet(
        [
            {
                "match_id": "m1",
                "match_number": 1,
                "team_a": "Brazil",
                "team_b": "Argentina",
                "lambda_a": 1.0,
                "lambda_b": 1.0,
                "expected_points_a": 1.4,
                "expected_points_b": 1.4,
            }
        ],
        probabilities,
    )
    write_rows_parquet(
        [{"team": "Brazil", "tsi_pre": 13.0}, {"team": "Argentina", "tsi_pre": 12.0}],
        tsi,
    )

    match_frame = match_performance_frame(
        match_stats=pl.read_parquet(stats),
        match_probabilities=pl.read_parquet(probabilities),
    )
    team_frame = team_performance_adjustment_frame(
        match_performance=match_frame,
        tsi_pre_cup=pl.read_parquet(tsi),
    )
    row = team_frame.filter(pl.col("team") == "Brazil").row(0, named=True)

    compressed_delta = _soft_cap(10.8)
    opponent_compressed_delta = _soft_cap(-10.2)
    centered_delta = compressed_delta - ((compressed_delta + opponent_compressed_delta) / 2.0)
    assert row["performance_adjustment"] == pytest.approx(centered_delta)
    assert row["post_groups_tsi_delta"] == pytest.approx(centered_delta * 0.30)
    assert row["tsi_post_groups"] == pytest.approx(13.0 + centered_delta * 0.30)


def test_match_performance_audit_frame_adds_raw_context(tmp_path) -> None:
    stats = tmp_path / "match_stats.parquet"
    probabilities = tmp_path / "probabilities.parquet"
    write_rows_parquet(
        [
            {
                "match_id": "m1",
                "match_number": 1,
                "date": "2026-06-11",
                "team": "Brazil",
                "opponent": "Argentina",
                "goals": 2,
                "goals_against": 1,
                "xg": 1.7,
                "xg_against": 0.9,
                "data_source": "fotmob-manual",
                "last_updated": "2026-06-26",
                "status": "finished",
                "is_home": True,
                "red_cards": 0,
                "first_red_card_minute": None,
            },
            {
                "match_id": "m1",
                "match_number": 1,
                "date": "2026-06-11",
                "team": "Argentina",
                "opponent": "Brazil",
                "goals": 1,
                "goals_against": 2,
                "xg": 0.9,
                "xg_against": 1.7,
                "data_source": "fotmob-manual",
                "last_updated": "2026-06-26",
                "status": "finished",
                "is_home": False,
                "red_cards": 0,
                "first_red_card_minute": None,
            },
        ],
        stats,
    )
    write_rows_parquet(
        [
            {
                "match_id": "m1",
                "match_number": 1,
                "team_a": "Brazil",
                "team_b": "Argentina",
                "lambda_a": 1.2,
                "lambda_b": 1.0,
                "expected_points_a": 1.5,
                "expected_points_b": 1.2,
            }
        ],
        probabilities,
    )
    match_frame = match_performance_frame(
        match_stats=pl.read_parquet(stats),
        match_probabilities=pl.read_parquet(probabilities),
    )

    audit = match_performance_audit_frame(match_frame, pl.read_parquet(stats))
    row = audit.filter(pl.col("team") == "Brazil").row(0, named=True)

    assert audit.height == 2
    assert row["score"] == "2-1"
    assert row["raw_xg"] == pytest.approx(1.7)
    assert row["xg_difference"] == pytest.approx(0.8)
    assert row["data_source"] == "fotmob-manual"
    assert row["has_process_stats"] is True
    assert row["weighted_match_tsi_delta"] > 0


def test_build_real_match_performance_outputs_reads_standard_paths(tmp_path) -> None:
    interim = tmp_path / "interim"
    processed = tmp_path / "processed"
    write_rows_parquet(
        [
            {
                "match_id": "m1",
                "match_number": 1,
                "date": "2026-06-11",
                "team": "Brazil",
                "opponent": "Argentina",
                "goals": 1,
                "goals_against": 1,
                "xg": 1.2,
                "xg_against": 0.8,
                "clear_chances": None,
                "clear_chances_against": None,
                "shots_on_target": None,
                "shots_on_target_against": None,
                "shots": None,
                "shots_against": None,
                "red_cards": 0,
                "first_red_card_minute": None,
            },
            {
                "match_id": "m1",
                "match_number": 1,
                "date": "2026-06-11",
                "team": "Argentina",
                "opponent": "Brazil",
                "goals": 1,
                "goals_against": 1,
                "xg": 0.8,
                "xg_against": 1.2,
                "clear_chances": None,
                "clear_chances_against": None,
                "shots_on_target": None,
                "shots_on_target_against": None,
                "shots": None,
                "shots_against": None,
                "red_cards": 0,
                "first_red_card_minute": None,
            },
        ],
        interim / "worldcup_match_stats.parquet",
    )
    write_rows_parquet(
        [
            {
                "match_id": "m1",
                "match_number": 1,
                "team_a": "Brazil",
                "team_b": "Argentina",
                "lambda_a": 1.0,
                "lambda_b": 1.0,
                "expected_points_a": 1.2,
                "expected_points_b": 1.6,
            }
        ],
        processed / "match_probabilities.parquet",
    )
    write_rows_parquet(
        [{"team": "Brazil", "tsi_pre": 13.0}, {"team": "Argentina", "tsi_pre": 12.0}],
        processed / "tsi_pre_cup.parquet",
    )

    outputs = build_real_match_performance_outputs(interim, processed)

    assert set(outputs) == {
        "match_performance.parquet",
        "match_performance_audit.parquet",
        "team_performance_adjustments.parquet",
    }
    assert outputs["match_performance.parquet"].height == 2
    assert outputs["match_performance_audit.parquet"].height == 2
    assert outputs["team_performance_adjustments.parquet"].height == 2
