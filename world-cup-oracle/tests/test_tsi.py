from __future__ import annotations

import math

from tactical_oracle.elo import EloRating
from tactical_oracle.tsi import build_tsi_ratings, map_elo_to_tsi, tsi_model, tsi_post_groups, tsi_pre


def test_map_elo_to_tsi_uses_zero_to_twenty_scale() -> None:
    assert map_elo_to_tsi(1100) == 0.0
    assert map_elo_to_tsi(1900) == 20.0
    assert math.isclose(map_elo_to_tsi(1500), 10.0)


def test_tsi_adjustments_are_capped() -> None:
    assert tsi_model(10.0, 5.0) == 11.0
    assert tsi_pre(10.0, -5.0) == 9.25


def test_tsi_post_groups_caps_delta_after_weighting() -> None:
    assert tsi_post_groups(10.0, 100.0) == 12.0
    assert tsi_post_groups(10.0, -100.0) == 8.0
    assert math.isclose(tsi_post_groups(10.0, 3.0), 10.9)


def test_build_tsi_ratings_keeps_components() -> None:
    ratings = {
        "Brazil": EloRating(
            team="Brazil",
            initial_elo=1500.0,
            base_elo=1600.0,
            recency_adjustment=10.0,
            adjusted_elo=1610.0,
        )
    }

    tsi = build_tsi_ratings(ratings, squad_adjustments={"Brazil": 0.5}, odds_adjustments={"Brazil": 0.2})

    assert tsi["Brazil"].tsi_model == tsi["Brazil"].tsi_base + 0.5
    assert tsi["Brazil"].tsi_pre == tsi["Brazil"].tsi_model + 0.2
