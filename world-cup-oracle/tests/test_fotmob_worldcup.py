from __future__ import annotations

from tactical_oracle.pipeline.fotmob_worldcup import (
    extract_match_team_stats,
    extract_worldcup_day_matches,
    map_local_to_fotmob,
)


def test_extract_worldcup_day_matches_filters_world_cup_and_normalizes_names() -> None:
    payload = {
        "data": {
            "date": "2026-06-11",
            "leagues": [
                {
                    "primaryId": 77,
                    "id": 894790,
                    "name": "World Cup Grp. A",
                    "matches": [
                        {
                            "id": 4667751,
                            "leagueId": 894790,
                            "home": {"longName": "USA", "score": 2},
                            "away": {"longName": "Czechia", "score": 1},
                            "status": {
                                "started": True,
                                "finished": True,
                                "utcTime": "2026-06-11T19:00:00.000Z",
                            },
                        }
                    ],
                },
                {
                    "primaryId": 114,
                    "id": 914609,
                    "name": "Friendlies",
                    "matches": [
                        {
                            "id": 1,
                            "home": {"longName": "Bolivia"},
                            "away": {"longName": "Algeria"},
                            "status": {},
                        }
                    ],
                },
            ],
        }
    }

    rows = extract_worldcup_day_matches(payload)

    assert rows == [
        {
            "date": "2026-06-11",
            "fotmob_match_id": 4667751,
            "league_id": 894790,
            "league_name": "World Cup Grp. A",
            "home_team": "United States",
            "away_team": "Czech Republic",
            "home_score": 2,
            "away_score": 1,
            "started": True,
            "finished": True,
            "utc_time": "2026-06-11T19:00:00.000Z",
        }
    ]


def test_map_local_to_fotmob_matches_by_date_and_teams() -> None:
    mapped, missing = map_local_to_fotmob(
        [
            {
                "match_id": 1,
                "date": "20260611",
                "home_team": "United States",
                "away_team": "Czech Republic",
            }
        ],
        [
            {
                "date": "20260611",
                "fotmob_match_id": 4667751,
                "home_team": "USA",
                "away_team": "Czechia",
            }
        ],
    )

    assert missing == []
    assert mapped[0]["match_id"] == 1
    assert mapped[0]["fotmob_match_id"] == 4667751


def test_map_local_to_fotmob_allows_one_day_fotmob_rollover() -> None:
    mapped, missing = map_local_to_fotmob(
        [
            {
                "match_id": 2,
                "date": "2026-06-11",
                "home_team": "South Korea",
                "away_team": "Czech Republic",
            }
        ],
        [
            {
                "date": "2026-06-12",
                "fotmob_match_id": 4667752,
                "home_team": "South Korea",
                "away_team": "Czech Republic",
            }
        ],
    )

    assert missing == []
    assert mapped[0]["fotmob_match_id"] == 4667752


def test_extract_match_team_stats_reads_fotmob_process_metrics() -> None:
    match = {
        "match_id": 1,
        "fotmob_match_id": 4667751,
        "home_team_id": 1,
        "away_team_id": 2,
        "home_team": "Mexico",
        "away_team": "South Africa",
    }
    payload = {
        "data": {
            "content": {
                "stats": {
                    "Periods": {
                        "All": {
                            "stats": [
                                {
                                    "key": "top_stats",
                                    "stats": [
                                        {"key": "expected_goals", "stats": ["1.46", "0.07"]},
                                        {"key": "touches_opp_box", "stats": [20, 2]},
                                        {"key": "big_chance", "stats": [2, 0]},
                                    ],
                                },
                                {
                                    "key": "passes",
                                    "stats": [
                                        {"key": "opposition_half_passes", "stats": [188, 74]}
                                    ],
                                },
                                {
                                    "key": "duels",
                                    "stats": [
                                        {
                                            "key": "ground_duels_won",
                                            "stats": ["32 (55%)", "26 (45%)"],
                                        },
                                        {
                                            "key": "dribbles_succeeded",
                                            "stats": ["9 (60%)", "1 (17%)"],
                                        },
                                    ],
                                },
                            ]
                        }
                    }
                }
            }
        }
    }

    rows = extract_match_team_stats(match, payload)

    assert rows[0]["team"] == "Mexico"
    assert rows[0]["xg"] == 1.46
    assert rows[0]["touches_in_opposition_box"] == 20.0
    assert rows[0]["clear_chances"] == 2.0
    assert rows[0]["opposition_half_passes"] == 188.0
    assert rows[0]["ground_duels_won"] == 32.0
    assert rows[0]["ground_duels_won_pct"] == 55.0
    assert rows[0]["successful_dribbles"] == 9.0
    assert rows[0]["successful_dribbles_pct"] == 60.0
    assert rows[1]["team"] == "South Africa"
    assert rows[1]["successful_dribbles_pct"] == 17.0
