from __future__ import annotations

import math

import numpy as np

from tactical_oracle.simulation import (
    GroupFixture,
    MatchResult,
    best_third_placed,
    match_probabilities,
    monte_carlo_match,
    penalty_win_probability,
    rank_group,
    simulate_group,
    simulate_knockout_match,
)


def test_match_probabilities_sum_close_to_one() -> None:
    probabilities = match_probabilities(1.30, 1.30, max_goals=18)

    assert math.isclose(
        probabilities.win_a + probabilities.draw + probabilities.win_b,
        1.0,
        rel_tol=0.0,
        abs_tol=1e-8,
    )
    assert math.isclose(probabilities.win_a, probabilities.win_b)
    assert math.isclose(probabilities.expected_points_a, probabilities.expected_points_b)


def test_penalty_probability_is_clamped() -> None:
    assert penalty_win_probability(40.0, 0.0) == 0.60
    assert penalty_win_probability(0.0, 40.0) == 0.40
    assert penalty_win_probability(12.0, 12.0) == 0.50


def test_knockout_match_always_has_winner() -> None:
    result = simulate_knockout_match(
        "A",
        "B",
        0.1,
        0.1,
        10.0,
        10.0,
        rng=np.random.default_rng(4),
    )

    assert result.winner in {"A", "B"}


def test_rank_group_uses_points_then_goal_difference() -> None:
    standings = rank_group(
        "A",
        ["A", "B", "C", "D"],
        [
            MatchResult("A", "B", 2, 0, "A"),
            MatchResult("C", "D", 1, 0, "A"),
            MatchResult("A", "C", 1, 1, "A"),
            MatchResult("B", "D", 2, 0, "A"),
        ],
        fifa_ranks={"A": 1, "B": 2, "C": 3, "D": 4},
    )

    assert standings[0].team == "A"
    assert standings[-1].team == "D"


def test_best_third_placed_selects_highest_thirds() -> None:
    rankings = {
        "A": rank_group(
            "A",
            ["A1", "A2", "A3", "A4"],
            [
                MatchResult("A1", "A2", 1, 0, "A"),
                MatchResult("A3", "A4", 3, 0, "A"),
                MatchResult("A1", "A3", 1, 1, "A"),
            ],
        ),
        "B": rank_group(
            "B",
            ["B1", "B2", "B3", "B4"],
            [
                MatchResult("B1", "B2", 1, 0, "B"),
                MatchResult("B3", "B4", 0, 0, "B"),
                MatchResult("B1", "B3", 1, 0, "B"),
            ],
        ),
    }

    thirds = best_third_placed(rankings, count=1)

    assert len(thirds) == 1
    assert thirds[0].team in {"A1", "A2", "A3", "A4", "B1", "B2", "B3", "B4"}


def test_monte_carlo_match_returns_probability_distribution() -> None:
    probabilities = monte_carlo_match(1.3, 1.3, simulations=1000, seed=1)

    assert math.isclose(probabilities["win_a"] + probabilities["draw"] + probabilities["win_b"], 1.0)


def test_simulate_group_accepts_expected_goals_provider() -> None:
    standings = simulate_group(
        "A",
        [
            GroupFixture("A", "A", "B"),
            GroupFixture("A", "A", "C"),
            GroupFixture("A", "B", "C"),
        ],
        lambda _a, _b: (1.0, 1.0),
        seed=2,
    )

    assert len(standings) == 3
