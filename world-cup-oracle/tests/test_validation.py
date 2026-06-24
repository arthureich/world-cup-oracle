from __future__ import annotations

import math

from tactical_oracle.odds import devig_three_way
from tactical_oracle.validation import (
    brier_score,
    calibration_bins,
    expected_calibration_error,
    log_loss,
    poisson_score_log_likelihood,
)


def test_brier_score_for_perfect_prediction_is_zero() -> None:
    assert brier_score([[1.0, 0.0, 0.0]], [0]) == 0.0


def test_log_loss_rewards_confident_correct_prediction() -> None:
    confident = log_loss([[0.9, 0.05, 0.05]], [0])
    weak = log_loss([[0.4, 0.3, 0.3]], [0])

    assert confident < weak


def test_calibration_bins_and_ece() -> None:
    bins = calibration_bins([0.1, 0.2, 0.8, 0.9], [0, 0, 1, 1], n_bins=2)

    assert len(bins) == 2
    assert bins[0].count == 2
    assert bins[1].count == 2
    assert expected_calibration_error(bins) < 0.2


def test_poisson_score_log_likelihood_matches_manual_formula() -> None:
    value = poisson_score_log_likelihood(1, 0, 1.3, 0.7)
    manual = math.log(1.3) - 1.3 - 0.7

    assert math.isclose(value, manual)


def test_devig_three_way_normalizes_market_probabilities() -> None:
    probabilities = devig_three_way(2.0, 3.5, 4.0)

    assert math.isclose(sum(probabilities), 1.0)
    assert probabilities[0] > probabilities[2]
