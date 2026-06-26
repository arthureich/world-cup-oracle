from __future__ import annotations

import math

from tactical_oracle.pipeline.data_quality import odds_coverage_rows, squad_coverage_rows


def test_squad_coverage_rows_summarizes_called_up_squad() -> None:
    squads = [
        {
            "team": "Brazil",
            "called_up": True,
            "sector": "GOL",
            "market_value": 10.0,
            "market_value_trusted": True,
            "market_value_source": "manual",
        },
        {
            "team": "Brazil",
            "called_up": True,
            "sector": "ATA",
            "market_value": 20.0,
            "market_value_trusted": False,
            "market_value_source": "manual",
        },
        {
            "team": "Brazil",
            "called_up": False,
            "sector": "ATA",
            "market_value": 999.0,
            "market_value_trusted": True,
            "market_value_source": "manual",
        },
    ]

    rows = squad_coverage_rows(squads, {"Brazil"})

    assert rows == [
        {
            "team": "Brazil",
            "called_up_count": 2,
            "trusted_player_count": 1,
            "trusted_coverage": 0.5,
            "squad_complete": False,
            "trusted_coverage_ok": False,
            "market_value_total": 30.0,
            "goalkeepers": 1,
            "defenders": 0,
            "midfielders": 0,
            "attackers": 1,
            "missing_sector_count": 0,
            "missing_market_value_count": 0,
            "market_value_source_count": 1,
        }
    ]


def test_odds_coverage_rows_keeps_alias_and_missing_team_status() -> None:
    rows = odds_coverage_rows(
        [
            {
                "team": "United States",
                "source_team": "USA",
                "source": "manual",
                "bookmaker": "market",
                "american_odd": 6000,
                "champion": 61.0,
                "champion_probability_devig": 0.01,
            }
        ],
        {"United States", "Algeria"},
    )

    by_team = {row["team"]: row for row in rows}

    assert by_team["United States"]["covered"] is True
    assert by_team["United States"]["alias_used"] is True
    assert math.isclose(by_team["United States"]["champion"], 61.0)
    assert by_team["Algeria"]["covered"] is False
