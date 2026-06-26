from __future__ import annotations

import itertools
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from tactical_oracle.attack_defense import (
    StrengthComponents,
    expected_goals_from_components,
)
from tactical_oracle.config import AttackDefenseParameters
from tactical_oracle.simulation import match_probabilities
from tactical_oracle.validation import (
    brier_score,
    calibration_bins,
    expected_calibration_error,
    log_loss,
    poisson_score_log_likelihood,
)


@dataclass(frozen=True)
class MatchPrediction:
    match_id: str
    date: str
    team_a: str
    team_b: str
    goals_a: int
    goals_b: int
    outcome: int
    lambda_a: float
    lambda_b: float
    p_win_a: float
    p_draw: float
    p_win_b: float
    score_log_likelihood: float


@dataclass(frozen=True)
class CalibrationResult:
    base_goals: float
    k: float
    host_gamma: float
    opponent_delta: float
    profile_multiplier: float
    profile_cap: float
    match_count: int
    skipped_count: int
    brier: float
    log_loss: float
    score_log_likelihood: float
    score_negative_log_likelihood: float
    expected_calibration_error: float


def _outcome(goals_a: int, goals_b: int) -> int:
    if goals_a > goals_b:
        return 0
    if goals_a == goals_b:
        return 1
    return 2


def _is_host(row: Mapping[str, Any], team: str) -> bool:
    return not bool(row.get("neutral_site", True)) and row.get("home_team") == team


def predict_matches(
    matches: Iterable[Mapping[str, Any]],
    components: Mapping[str, StrengthComponents],
    params: AttackDefenseParameters,
) -> tuple[list[MatchPrediction], int]:
    predictions: list[MatchPrediction] = []
    skipped_count = 0
    for row in matches:
        team_a = str(row["team_a"])
        team_b = str(row["team_b"])
        if team_a not in components or team_b not in components:
            skipped_count += 1
            continue

        lambda_a, lambda_b = expected_goals_from_components(
            components[team_a],
            components[team_b],
            a_is_host=_is_host(row, team_a),
            b_is_host=_is_host(row, team_b),
            params=params,
        )
        probabilities = match_probabilities(lambda_a, lambda_b)
        goals_a = int(row["goals_a"])
        goals_b = int(row["goals_b"])
        predictions.append(
            MatchPrediction(
                match_id=str(row["match_id"]),
                date=str(row["date"]),
                team_a=team_a,
                team_b=team_b,
                goals_a=goals_a,
                goals_b=goals_b,
                outcome=_outcome(goals_a, goals_b),
                lambda_a=lambda_a,
                lambda_b=lambda_b,
                p_win_a=probabilities.win_a,
                p_draw=probabilities.draw,
                p_win_b=probabilities.win_b,
                score_log_likelihood=poisson_score_log_likelihood(
                    goals_a,
                    goals_b,
                    lambda_a,
                    lambda_b,
                ),
            )
        )
    return predictions, skipped_count


def evaluate_attack_defense_parameters(
    matches: Iterable[Mapping[str, Any]],
    components: Mapping[str, StrengthComponents],
    params: AttackDefenseParameters,
) -> CalibrationResult:
    predictions, skipped_count = predict_matches(matches, components, params)
    if not predictions:
        raise ValueError("at least one match with model components is required")

    probability_vectors = [
        [prediction.p_win_a, prediction.p_draw, prediction.p_win_b]
        for prediction in predictions
    ]
    outcomes = [prediction.outcome for prediction in predictions]
    score_ll = sum(prediction.score_log_likelihood for prediction in predictions) / len(
        predictions
    )
    calibration_probabilities: list[float] = []
    calibration_outcomes: list[bool] = []
    for vector, outcome in zip(probability_vectors, outcomes, strict=True):
        for index, probability in enumerate(vector):
            calibration_probabilities.append(probability)
            calibration_outcomes.append(index == outcome)
    bins = calibration_bins(calibration_probabilities, calibration_outcomes, n_bins=10)

    return CalibrationResult(
        base_goals=params.base_goals,
        k=params.k,
        host_gamma=params.host_gamma,
        opponent_delta=params.opponent_delta,
        profile_multiplier=params.profile_multiplier,
        profile_cap=params.profile_cap,
        match_count=len(predictions),
        skipped_count=skipped_count,
        brier=brier_score(probability_vectors, outcomes),
        log_loss=log_loss(probability_vectors, outcomes),
        score_log_likelihood=score_ll,
        score_negative_log_likelihood=-score_ll,
        expected_calibration_error=expected_calibration_error(bins),
    )


def attack_defense_grid(
    base_goals_values: Sequence[float] = (1.15, 1.25, 1.35, 1.45),
    k_values: Sequence[float] = (0.05, 0.08, 0.11, 0.14),
    host_gamma_values: Sequence[float] = (0.00, 0.12, 0.22),
    opponent_delta_values: Sequence[float] = (0.00,),
    profile_multiplier_values: Sequence[float] = (0.5, 0.8, 1.1),
    profile_cap_values: Sequence[float] = (2.0,),
) -> list[AttackDefenseParameters]:
    return [
        AttackDefenseParameters(
            base_goals=base_goals,
            k=k,
            host_gamma=host_gamma,
            opponent_delta=opponent_delta,
            profile_multiplier=profile_multiplier,
            profile_cap=profile_cap,
        )
        for (
            base_goals,
            k,
            host_gamma,
            opponent_delta,
            profile_multiplier,
            profile_cap,
        ) in itertools.product(
            base_goals_values,
            k_values,
            host_gamma_values,
            opponent_delta_values,
            profile_multiplier_values,
            profile_cap_values,
        )
    ]


def result_row(result: CalibrationResult, split: str) -> dict[str, Any]:
    return {
        "split": split,
        "base_goals": result.base_goals,
        "k": result.k,
        "host_gamma": result.host_gamma,
        "opponent_delta": result.opponent_delta,
        "profile_multiplier": result.profile_multiplier,
        "profile_cap": result.profile_cap,
        "match_count": result.match_count,
        "skipped_count": result.skipped_count,
        "brier": result.brier,
        "log_loss": result.log_loss,
        "score_log_likelihood": result.score_log_likelihood,
        "score_negative_log_likelihood": result.score_negative_log_likelihood,
        "expected_calibration_error": result.expected_calibration_error,
    }


def calibration_bin_rows(
    predictions: Iterable[MatchPrediction],
    n_bins: int = 10,
) -> list[dict[str, Any]]:
    prediction_list = list(predictions)
    probability_by_class = {
        "win_a": [prediction.p_win_a for prediction in prediction_list],
        "draw": [prediction.p_draw for prediction in prediction_list],
        "win_b": [prediction.p_win_b for prediction in prediction_list],
    }
    outcome_by_class = {
        "win_a": [prediction.outcome == 0 for prediction in prediction_list],
        "draw": [prediction.outcome == 1 for prediction in prediction_list],
        "win_b": [prediction.outcome == 2 for prediction in prediction_list],
    }

    rows: list[dict[str, Any]] = []
    for outcome_name, probabilities in probability_by_class.items():
        bins = calibration_bins(
            probabilities,
            outcome_by_class[outcome_name],
            n_bins=n_bins,
        )
        for index, bucket in enumerate(bins):
            rows.append(
                {
                    "outcome": outcome_name,
                    "bin": index,
                    "lower": bucket.lower,
                    "upper": bucket.upper,
                    "count": bucket.count,
                    "mean_predicted": bucket.mean_predicted,
                    "observed_frequency": bucket.observed_frequency,
                    "absolute_error": abs(
                        bucket.mean_predicted - bucket.observed_frequency
                    ),
                }
            )
    return rows
