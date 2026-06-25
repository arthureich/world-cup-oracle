from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from tactical_oracle.config import PerformanceParameters
from tactical_oracle.utils import clamp

DEFAULT_PERFORMANCE_PARAMETERS = PerformanceParameters()


@dataclass(frozen=True)
class MatchPerformance:
    team: str
    match_id: str
    expected_goal_difference: float
    process_goal_difference: float
    expected_points: float
    actual_points: float
    process_surprise: float
    result_surprise: float
    performance_score: float
    match_weight: float


def actual_points(goals_for: int, goals_against: int) -> float:
    if goals_for > goals_against:
        return 3.0
    if goals_for == goals_against:
        return 1.0
    return 0.0


def weighted_metric_score(
    metrics: Mapping[str, float],
    weights: Mapping[str, float],
) -> float:
    """Composite score for already-normalized process metrics."""

    if not weights:
        raise ValueError("weights cannot be empty")
    total_weight = sum(weights.values())
    if total_weight <= 0:
        raise ValueError("weights must have positive total mass")
    weighted_sum = sum(float(metrics.get(name, 0.0)) * weight for name, weight in weights.items())
    return weighted_sum / total_weight


def process_goal_difference(process_for: float, process_against: float) -> float:
    return process_for - process_against


def match_weight(
    minutes_numerical_imbalance: float = 0.0,
    rotation_weight: float = 1.0,
    necessity_weight: float = 1.0,
    params: PerformanceParameters | None = None,
) -> float:
    params = params or DEFAULT_PERFORMANCE_PARAMETERS
    if minutes_numerical_imbalance < 0:
        raise ValueError("minutes_numerical_imbalance cannot be negative")
    red_card_component = 1.0 - params.red_card_weight_factor * (
        min(minutes_numerical_imbalance, 90.0) / 90.0
    )
    raw = red_card_component * rotation_weight * necessity_weight
    return clamp(raw, params.min_match_weight, 1.0)


def performance_score(
    lambda_for: float,
    lambda_against: float,
    process_for: float,
    process_against: float,
    expected_points: float,
    points: float,
    params: PerformanceParameters | None = None,
) -> tuple[float, float, float]:
    """Return score, process surprise and result surprise for one team-match."""

    params = params or DEFAULT_PERFORMANCE_PARAMETERS
    expected_gd = lambda_for - lambda_against
    process_gd = process_goal_difference(process_for, process_against)
    process_surprise = process_gd - expected_gd
    result_surprise = points - expected_points
    score = params.process_weight * process_surprise + params.result_weight * result_surprise
    return score, process_surprise, result_surprise


def build_match_performance(
    team: str,
    match_id: str,
    lambda_for: float,
    lambda_against: float,
    expected_points: float,
    goals_for: int,
    goals_against: int,
    process_for: float,
    process_against: float,
    minutes_numerical_imbalance: float = 0.0,
    rotation_weight: float = 1.0,
    necessity_weight: float = 1.0,
    params: PerformanceParameters | None = None,
) -> MatchPerformance:
    params = params or DEFAULT_PERFORMANCE_PARAMETERS
    points = actual_points(goals_for, goals_against)
    score, process_surprise, result_surprise = performance_score(
        lambda_for=lambda_for,
        lambda_against=lambda_against,
        process_for=process_for,
        process_against=process_against,
        expected_points=expected_points,
        points=points,
        params=params,
    )
    weight = match_weight(
        minutes_numerical_imbalance=minutes_numerical_imbalance,
        rotation_weight=rotation_weight,
        necessity_weight=necessity_weight,
        params=params,
    )
    return MatchPerformance(
        team=team,
        match_id=match_id,
        expected_goal_difference=lambda_for - lambda_against,
        process_goal_difference=process_goal_difference(process_for, process_against),
        expected_points=expected_points,
        actual_points=points,
        process_surprise=process_surprise,
        result_surprise=result_surprise,
        performance_score=score,
        match_weight=weight,
    )


def build_match_performance_from_metrics(
    team: str,
    match_id: str,
    lambda_for: float,
    lambda_against: float,
    expected_points: float,
    goals_for: int,
    goals_against: int,
    offensive_metrics: Mapping[str, float],
    defensive_metrics: Mapping[str, float],
    minutes_numerical_imbalance: float = 0.0,
    rotation_weight: float = 1.0,
    necessity_weight: float = 1.0,
    params: PerformanceParameters | None = None,
) -> MatchPerformance:
    params = params or DEFAULT_PERFORMANCE_PARAMETERS
    process_for = weighted_metric_score(offensive_metrics, params.offensive_weights)
    process_against = weighted_metric_score(defensive_metrics, params.defensive_weights)
    return build_match_performance(
        team=team,
        match_id=match_id,
        lambda_for=lambda_for,
        lambda_against=lambda_against,
        expected_points=expected_points,
        goals_for=goals_for,
        goals_against=goals_against,
        process_for=process_for,
        process_against=process_against,
        minutes_numerical_imbalance=minutes_numerical_imbalance,
        rotation_weight=rotation_weight,
        necessity_weight=necessity_weight,
        params=params,
    )


def aggregate_performance_adjustment(matches: Iterable[MatchPerformance]) -> float:
    weighted_sum = 0.0
    weight_sum = 0.0
    for match in matches:
        weighted_sum += match.performance_score * match.match_weight
        weight_sum += match.match_weight
    if weight_sum == 0:
        return 0.0
    return weighted_sum / weight_sum


def group_performance_tsi(tsi_pre: float, performance_adjustment: float) -> float:
    return tsi_pre + performance_adjustment
