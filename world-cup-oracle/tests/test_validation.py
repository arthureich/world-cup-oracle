from __future__ import annotations

import math

from tactical_oracle.odds import (
    american_to_decimal,
    champion_market_adjustments_from_rows,
    devig_three_way,
    long_term_market_adjustments_from_rows,
)
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


def test_american_to_decimal_converts_positive_and_negative_odds() -> None:
    assert math.isclose(american_to_decimal(420), 5.2)
    assert math.isclose(american_to_decimal(-125), 1.8)


def test_long_term_market_adjustments_from_rows_are_capped() -> None:
    adjustments = long_term_market_adjustments_from_rows(
        {"A": 12.0, "B": 8.0},
        [
            {"team": "A", "pass_yes": 1.2, "pass_no": 5.5, "champion": 5.0},
            {"team": "B", "pass_yes": 2.8, "pass_no": 1.4, "champion": 80.0},
        ],
    )

    assert set(adjustments) == {"A", "B"}
    assert all(-0.75 <= value <= 0.75 for value in adjustments.values())


def test_champion_market_adjustments_from_rows_can_use_champion_only_snapshot() -> None:
    adjustments = champion_market_adjustments_from_rows(
        {"Spain": 9.0, "Brazil": 10.0, "Long Shot": 11.0},
        [
            {"team": "Spain", "american_odd": 420},
            {"team": "Brazil", "american_odd": 850},
            {"team": "Long Shot", "american_odd": 250000},
        ],
    )

    assert set(adjustments) == {"Spain", "Brazil", "Long Shot"}
    assert adjustments["Spain"] > adjustments["Long Shot"]
    assert all(-0.75 <= value <= 0.75 for value in adjustments.values())
