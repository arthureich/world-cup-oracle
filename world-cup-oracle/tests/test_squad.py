from __future__ import annotations

from tactical_oracle.data.mocks import squads_mock
from tactical_oracle.squad import (
    apply_squad_age_uplift,
    player_effective_value,
    player_value_from_row,
    sector_values,
    squad_adjustments_from_players,
    squad_age_multiplier,
    squad_age_multipliers,
    squad_scores,
)


def test_player_effective_value_is_market_value_scaled_by_club_level() -> None:
    assert player_effective_value(market_value=50.0) == 50.0
    assert player_effective_value(market_value=50.0, club_level=1.2) == 60.0


def test_squad_age_multiplier_rewards_older_squads_monotonically() -> None:
    assert squad_age_multiplier(24.0) == 1.0
    assert squad_age_multiplier(26.0) == 1.0
    assert round(squad_age_multiplier(29.4), 2) == 1.88
    assert squad_age_multiplier(33.0) == 2.3


def test_apply_squad_age_uplift_scales_each_team_by_its_multiplier() -> None:
    rows = []
    for team, age in (("Old", 31.0), ("Young", 24.0)):
        for sector in ("GOL", "DEF", "MEI", "ATA"):
            rows.append({"team": team, "sector": sector, "age": age,
                         "player_name": f"{team} {sector}", "market_value": 50.0})

    players = [player_value_from_row(row) for row in rows]
    uplifted = {p.team: p for p in apply_squad_age_uplift(players, squad_age_multipliers(rows))}

    assert uplifted["Old"].effective_value == 50.0 * 2.3
    assert uplifted["Young"].effective_value == 50.0


def test_player_value_from_row_ignores_age_and_minutes() -> None:
    base = {"player_name": "P", "team": "T", "sector": "MEI", "market_value": 50.0}
    veteran = player_value_from_row({**base, "age": 34, "recent_minutes_factor": 0.5})
    youngster = player_value_from_row({**base, "age": 20, "recent_minutes_factor": 1.0})

    assert veteran.effective_value == youngster.effective_value == 50.0


def test_squad_scores_penalize_only_critical_sectors() -> None:
    # Fillers fix the per-sector distribution; "Holed" has a genuinely critical GOL.
    teams = {f"F{i}": {"GOL": 5.0, "DEF": 5.0, "MEI": 5.0, "ATA": 5.0} for i in range(6)}
    teams["Holed"] = {"GOL": 0.0, "DEF": 9.0, "MEI": 9.0, "ATA": 9.0}

    penalized = squad_scores(teams)["Holed"]
    without_penalty = squad_scores(teams, critical_threshold=-10.0)["Holed"]

    assert penalized < without_penalty


def test_squad_scores_do_not_penalize_uneven_squad_above_the_critical_line() -> None:
    # "Spiky" is elite in ATA and merely average (not critical) elsewhere. With no
    # sector under the line, its score is the same whatever the threshold — i.e. the
    # uneven shape costs nothing; only the total talent (mean) counts.
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
