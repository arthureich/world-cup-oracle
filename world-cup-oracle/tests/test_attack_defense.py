from __future__ import annotations

import math

from tactical_oracle.attack_defense import (
    expected_goals,
    expected_goals_from_components,
    profile_from_goal_totals,
    reverse_components,
    split_attack_defense,
)


def test_attack_defense_is_reversible() -> None:
    components = split_attack_defense("Brazil", tsi=14.0, profile=1.2)

    tsi, profile = reverse_components(components.attack, components.defense)

    assert math.isclose(tsi, 14.0)
    assert math.isclose(profile, 1.2)


def test_expected_goals_equal_strengths_are_base_goals() -> None:
    lambda_a, lambda_b = expected_goals(
        attack_a=12.0,
        defense_a=12.0,
        attack_b=12.0,
        defense_b=12.0,
    )

    assert math.isclose(lambda_a, 1.30)
    assert math.isclose(lambda_b, 1.30)


def test_host_adjustment_increases_host_lambda() -> None:
    neutral_a, neutral_b = expected_goals(12.0, 12.0, 12.0, 12.0)
    host_a, host_b = expected_goals(12.0, 12.0, 12.0, 12.0, a_is_host=True)

    assert host_a > neutral_a
    assert math.isclose(host_b, neutral_b)


def test_profile_from_goal_totals_is_capped() -> None:
    profiles = profile_from_goal_totals(
        {"A": 3.0, "B": 1.0, "C": 0.5},
        {"A": 3.0, "B": 1.0, "C": 0.5},
    )

    assert set(profiles) == {"A", "B", "C"}
    assert all(-2.0 <= value <= 2.0 for value in profiles.values())


def test_expected_goals_from_components_accepts_split_objects() -> None:
    a = split_attack_defense("A", 13.0, 0.5)
    b = split_attack_defense("B", 11.0, -0.5)

    lambda_a, lambda_b = expected_goals_from_components(a, b)

    assert lambda_a > lambda_b
