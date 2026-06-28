from __future__ import annotations

import math
from collections.abc import Iterable, Sequence


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def mean(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("mean requires at least one value")
    return sum(values) / len(values)


def population_std(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("population_std requires at least one value")
    avg = mean(values)
    return math.sqrt(sum((value - avg) ** 2 for value in values) / len(values))


def z_scores_by_key(values: dict[str, float]) -> dict[str, float]:
    vals = list(values.values())
    avg = mean(vals)
    std = population_std(vals)
    if std == 0:
        return {key: 0.0 for key in values}
    return {key: (value - avg) / std for key, value in values.items()}


def standardize_to_reference(
    values: dict[str, float],
    reference: dict[str, float],
) -> dict[str, float]:
    """Standardize values, then map them to the mean/std of a reference mapping."""

    if set(values) != set(reference):
        missing = set(reference).symmetric_difference(values)
        raise ValueError(f"values and reference must have the same keys: {sorted(missing)}")

    value_z = z_scores_by_key(values)
    reference_values = list(reference.values())
    ref_mean = mean(reference_values)
    ref_std = population_std(reference_values)
    return {key: ref_mean + value_z[key] * ref_std for key in values}


def safe_logit(probability: float, epsilon: float = 1e-12) -> float:
    p = clamp(probability, epsilon, 1.0 - epsilon)
    return math.log(p / (1.0 - p))


def require_probability_vector(probabilities: Iterable[float]) -> list[float]:
    vector = [float(probability) for probability in probabilities]
    if not vector:
        raise ValueError("probability vector cannot be empty")
    if any(probability < 0 for probability in vector):
        raise ValueError("probabilities cannot be negative")
    total = sum(vector)
    if total <= 0:
        raise ValueError("probability vector must have positive mass")
    return vector

