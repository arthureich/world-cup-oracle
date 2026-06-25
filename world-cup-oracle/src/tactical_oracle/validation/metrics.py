from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from tactical_oracle.config import ValidationParameters
from tactical_oracle.utils import clamp, require_probability_vector

DEFAULT_VALIDATION_PARAMETERS = ValidationParameters()


@dataclass(frozen=True)
class CalibrationBin:
    lower: float
    upper: float
    count: int
    mean_predicted: float
    observed_frequency: float


def brier_score(probabilities: Sequence[Sequence[float]], outcomes: Sequence[int]) -> float:
    if len(probabilities) != len(outcomes):
        raise ValueError("probabilities and outcomes must have the same length")
    if not probabilities:
        raise ValueError("at least one prediction is required")

    total = 0.0
    for vector, outcome in zip(probabilities, outcomes, strict=True):
        probs = require_probability_vector(vector)
        if not 0 <= outcome < len(probs):
            raise ValueError("outcome index is outside the probability vector")
        total += sum(
            (probability - (1.0 if idx == outcome else 0.0)) ** 2
            for idx, probability in enumerate(probs)
        )
    return total / len(probabilities)


def log_loss(
    probabilities: Sequence[Sequence[float]],
    outcomes: Sequence[int],
    params: ValidationParameters | None = None,
) -> float:
    params = params or DEFAULT_VALIDATION_PARAMETERS
    if len(probabilities) != len(outcomes):
        raise ValueError("probabilities and outcomes must have the same length")
    if not probabilities:
        raise ValueError("at least one prediction is required")

    total = 0.0
    for vector, outcome in zip(probabilities, outcomes, strict=True):
        probs = require_probability_vector(vector)
        if not 0 <= outcome < len(probs):
            raise ValueError("outcome index is outside the probability vector")
        total -= math.log(clamp(probs[outcome], params.epsilon, 1.0))
    return total / len(probabilities)


def calibration_bins(
    predicted_probabilities: Sequence[float],
    outcomes: Sequence[bool | int],
    n_bins: int = 10,
) -> list[CalibrationBin]:
    if len(predicted_probabilities) != len(outcomes):
        raise ValueError("predicted_probabilities and outcomes must have the same length")
    if n_bins <= 0:
        raise ValueError("n_bins must be positive")

    buckets: list[list[tuple[float, float]]] = [[] for _ in range(n_bins)]
    for probability, outcome in zip(predicted_probabilities, outcomes, strict=True):
        p = clamp(float(probability), 0.0, 1.0)
        bucket = min(n_bins - 1, int(p * n_bins))
        buckets[bucket].append((p, 1.0 if bool(outcome) else 0.0))

    output: list[CalibrationBin] = []
    width = 1.0 / n_bins
    for idx, bucket in enumerate(buckets):
        lower = idx * width
        upper = 1.0 if idx == n_bins - 1 else (idx + 1) * width
        if bucket:
            output.append(
                CalibrationBin(
                    lower=lower,
                    upper=upper,
                    count=len(bucket),
                    mean_predicted=sum(item[0] for item in bucket) / len(bucket),
                    observed_frequency=sum(item[1] for item in bucket) / len(bucket),
                )
            )
        else:
            output.append(
                CalibrationBin(
                    lower=lower,
                    upper=upper,
                    count=0,
                    mean_predicted=0.0,
                    observed_frequency=0.0,
                )
            )
    return output


def expected_calibration_error(bins: Sequence[CalibrationBin]) -> float:
    total_count = sum(bucket.count for bucket in bins)
    if total_count == 0:
        return 0.0
    return sum(
        (bucket.count / total_count) * abs(bucket.mean_predicted - bucket.observed_frequency)
        for bucket in bins
    )


def poisson_score_log_likelihood(
    goals_a: int,
    goals_b: int,
    lambda_a: float,
    lambda_b: float,
) -> float:
    if min(goals_a, goals_b) < 0:
        raise ValueError("goals cannot be negative")
    if min(lambda_a, lambda_b) < 0:
        raise ValueError("lambdas cannot be negative")

    def poisson_log_probability(goals: int, lambda_goals: float) -> float:
        if lambda_goals == 0:
            return 0.0 if goals == 0 else -math.inf
        return goals * math.log(lambda_goals) - lambda_goals - math.lgamma(goals + 1)

    return poisson_log_probability(goals_a, lambda_a) + poisson_log_probability(goals_b, lambda_b)
