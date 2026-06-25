from __future__ import annotations

import math

from tactical_oracle.performance import (
    actual_points,
    aggregate_performance_adjustment,
    build_match_performance,
    build_match_performance_from_metrics,
    group_performance_tsi,
    match_weight,
    performance_score,
    weighted_metric_score,
)
from tactical_oracle.tsi import tsi_post_groups


def test_actual_points_uses_match_result() -> None:
    assert actual_points(2, 0) == 3.0
    assert actual_points(1, 1) == 1.0
    assert actual_points(0, 2) == 0.0


def test_weighted_metric_score_uses_documented_weights() -> None:
    score = weighted_metric_score(
        {"xg": 1.5, "clear_chances": 1.0, "shots_on_target": 0.5, "shots": 0.2},
        {"xg": 0.45, "clear_chances": 0.25, "shots_on_target": 0.20, "shots": 0.10},
    )

    assert math.isclose(score, 1.045)


def test_match_weight_respects_red_card_and_floor() -> None:
    assert math.isclose(match_weight(minutes_numerical_imbalance=90), 0.5)
    assert match_weight(minutes_numerical_imbalance=90, rotation_weight=0.1) == 0.15


def test_performance_score_separates_process_and_result_surprise() -> None:
    score, process_surprise, result_surprise = performance_score(
        lambda_for=1.4,
        lambda_against=0.9,
        process_for=2.0,
        process_against=0.8,
        expected_points=1.8,
        points=3.0,
    )

    assert math.isclose(process_surprise, 0.7)
    assert math.isclose(result_surprise, 1.2)
    assert math.isclose(score, 4.0)


def test_build_match_performance_from_metrics_builds_process_composite() -> None:
    performance = build_match_performance_from_metrics(
        team="Brazil",
        match_id="g1",
        lambda_for=1.3,
        lambda_against=1.0,
        expected_points=1.6,
        goals_for=2,
        goals_against=1,
        offensive_metrics={"xg": 1.4, "clear_chances": 1.2, "shots_on_target": 0.9, "shots": 0.5},
        defensive_metrics={
            "xg_against": 0.7,
            "clear_chances_against": 0.4,
            "shots_on_target_against": 0.3,
            "shots_against": 0.2,
        },
    )

    assert performance.team == "Brazil"
    assert performance.performance_score > 0
    assert performance.match_weight == 1.0


def test_aggregate_performance_adjustment_is_weighted_average() -> None:
    strong = build_match_performance(
        team="A",
        match_id="m1",
        lambda_for=1.0,
        lambda_against=1.0,
        expected_points=1.0,
        goals_for=2,
        goals_against=0,
        process_for=2.0,
        process_against=0.5,
    )
    noisy = build_match_performance(
        team="A",
        match_id="m2",
        lambda_for=1.0,
        lambda_against=1.0,
        expected_points=1.0,
        goals_for=0,
        goals_against=1,
        process_for=0.5,
        process_against=1.0,
        rotation_weight=0.3,
    )

    adjustment = aggregate_performance_adjustment([strong, noisy])

    assert adjustment > 0
    assert adjustment < strong.performance_score


def test_group_performance_feeds_tsi_post_groups() -> None:
    performance_group = group_performance_tsi(10.0, performance_adjustment=3.0)

    assert performance_group == 13.0
    assert math.isclose(tsi_post_groups(10.0, performance_group - 10.0), 10.9)

