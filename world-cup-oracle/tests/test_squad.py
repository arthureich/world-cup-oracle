from __future__ import annotations

from tactical_oracle.data.mocks import squads_mock
from tactical_oracle.squad import (
    player_effective_value,
    sector_values,
    squad_adjustments_from_players,
    squad_scores,
)


def test_player_effective_value_is_positive_and_age_adjusted() -> None:
    prime = player_effective_value(market_value=50.0, age=28)
    veteran = player_effective_value(market_value=50.0, age=35)

    assert prime > 0
    assert veteran > 0
    assert prime != veteran


def test_squad_scores_penalize_missing_sector_balance() -> None:
    balanced = {
        "A": {"GOL": 2.0, "DEF": 2.0, "MEI": 2.0, "ATA": 2.0},
        "B": {"GOL": 1.0, "DEF": 1.0, "MEI": 1.0, "ATA": 1.0},
    }
    unbalanced = {
        "A": {"GOL": 0.0, "DEF": 3.0, "MEI": 3.0, "ATA": 3.0},
        "B": {"GOL": 1.0, "DEF": 1.0, "MEI": 1.0, "ATA": 1.0},
    }

    assert squad_scores(balanced)["A"] > squad_scores(unbalanced)["A"]


def test_squad_adjustments_from_players_are_capped_for_mock_data() -> None:
    adjustments = squad_adjustments_from_players(
        squads_mock(),
        {
            "Argentina": 14.0,
            "France": 13.0,
            "England": 12.0,
            "Brazil": 12.0,
            "Morocco": 9.0,
            "Mexico": 8.0,
            "Japan": 8.0,
            "Canada": 4.0,
        },
    )

    assert set(adjustments) == {
        "Argentina",
        "France",
        "England",
        "Brazil",
        "Morocco",
        "Mexico",
        "Japan",
        "Canada",
    }
    assert all(-1.0 <= value <= 1.0 for value in adjustments.values())


def test_sector_values_accepts_empty_input() -> None:
    player = next(iter(sector_values([]).values()), None)

    assert player is None
