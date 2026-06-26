from __future__ import annotations

import math

from tactical_oracle.data.mocks import squads_mock
from tactical_oracle.squad import (
    age_factor,
    player_effective_value,
    player_value_from_row,
    sector_values,
    squad_adjustments_from_players,
    squad_scores,
)


def test_age_factor_matches_documented_curve() -> None:
    assert age_factor(24.0) == 1.0
    assert age_factor(27.0) == 1.0
    assert math.isclose(age_factor(39.0), 6.67, rel_tol=1e-3)
    assert age_factor(60.0) == 7.0


def test_player_effective_value_is_market_value_scaled_by_age_factor() -> None:
    assert player_effective_value(market_value=50.0, age=24.0) == 50.0
    assert player_effective_value(market_value=50.0, age=39.0) > 300.0


def test_player_value_from_row_uses_age_and_ignores_minutes() -> None:
    base = {"player_name": "P", "team": "T", "sector": "MEI", "market_value": 50.0}
    veteran = player_value_from_row({**base, "age": 34, "recent_minutes_factor": 0.5})
    youngster = player_value_from_row({**base, "age": 20, "recent_minutes_factor": 1.0})

    assert veteran.effective_value > youngster.effective_value


def test_squad_scores_weight_outfield_lines_more_than_goalkeepers() -> None:
    teams = {
        "GkOnly": {"GOL": 10.0, "DEF": 5.0, "MEI": 5.0, "ATA": 5.0},
        "Outfield": {"GOL": 5.0, "DEF": 10.0, "MEI": 10.0, "ATA": 10.0},
        "Base": {"GOL": 5.0, "DEF": 5.0, "MEI": 5.0, "ATA": 5.0},
    }

    scores = squad_scores(teams)

    assert scores["Outfield"] > scores["GkOnly"]


def test_squad_scores_penalize_only_critical_sectors() -> None:
    teams = {f"F{i}": {"GOL": 5.0, "DEF": 5.0, "MEI": 5.0, "ATA": 5.0} for i in range(6)}
    teams["Holed"] = {"GOL": 0.0, "DEF": 9.0, "MEI": 9.0, "ATA": 9.0}

    penalized = squad_scores(teams)["Holed"]
    without_penalty = squad_scores(teams, critical_threshold=-10.0)["Holed"]

    assert penalized < without_penalty


def test_squad_scores_do_not_penalize_uneven_squad_above_the_critical_line() -> None:
    teams = {f"F{i}": {"GOL": 5.0, "DEF": 5.0, "MEI": 5.0, "ATA": 5.0} for i in range(6)}
    teams["Spiky"] = {"GOL": 5.0, "DEF": 5.0, "MEI": 5.0, "ATA": 20.0}

    assert squad_scores(teams)["Spiky"] == squad_scores(teams, critical_threshold=-10.0)["Spiky"]


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
