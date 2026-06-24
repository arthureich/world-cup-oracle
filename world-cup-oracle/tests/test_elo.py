from __future__ import annotations

import math

from tactical_oracle.data.schemas import Match
from tactical_oracle.elo import (
    actual_result_for_team,
    compute_elo_ratings,
    expected_result,
    margin_multiplier,
    update_match,
)


def test_expected_result_equal_ratings_is_half() -> None:
    assert math.isclose(expected_result(1500, 1500), 0.5)
    assert expected_result(1500, 1500, home_advantage_a=50) > 0.5


def test_margin_multiplier_is_capped_and_monotonic() -> None:
    assert margin_multiplier(0) == 1.0
    assert margin_multiplier(1) == 1.0
    assert 1.0 < margin_multiplier(2) < margin_multiplier(5) <= 1.4


def test_penalties_are_small_result_bonus_not_goal_margin() -> None:
    match = Match(
        match_id="p1",
        date="2024-07-05",
        team_a="Morocco",
        team_b="Mexico",
        goals_a=1,
        goals_b=1,
        match_type="continental_knockout",
        went_to_penalties=True,
        penalty_winner="Morocco",
    )

    assert actual_result_for_team(match, "Morocco") == 0.55
    assert actual_result_for_team(match, "Mexico") == 0.45
    assert margin_multiplier(abs(match.goals_a - match.goals_b)) == 1.0


def test_update_match_is_zero_sum_for_pair() -> None:
    ratings = {"Brazil": 1600.0, "Argentina": 1600.0}
    match = Match(
        match_id="m1",
        date="2025-01-01",
        team_a="Brazil",
        team_b="Argentina",
        goals_a=2,
        goals_b=0,
        match_type="qualifier",
    )

    update = update_match(ratings, match)

    assert update.delta_a > 0
    assert update.delta_b < 0
    assert math.isclose(update.delta_a, -update.delta_b)


def test_compute_elo_ratings_applies_recency_adjustment() -> None:
    ratings = compute_elo_ratings(
        {"Brazil": 1800.0, "Japan": 1600.0},
        [
            {
                "match_id": "recent",
                "date": "2026-03-01",
                "team_a": "Japan",
                "team_b": "Brazil",
                "goals_a": 2,
                "goals_b": 0,
                "match_type": "qualifier",
            }
        ],
    )

    assert ratings["Japan"].recency_adjustment > 0
    assert ratings["Brazil"].recency_adjustment < 0
