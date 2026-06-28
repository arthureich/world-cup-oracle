from __future__ import annotations

import json

from world_cup_oracle.data.cache import ApiCache
from world_cup_oracle.pipeline.the_odds_api import odds_match_rows_from_events


def test_odds_match_rows_from_events_normalizes_h2h_market() -> None:
    events = [
        {
            "id": "evt-1",
            "sport_key": "soccer_test",
            "commence_time": "2026-06-11T20:00:00Z",
            "home_team": "Brazil",
            "away_team": "France",
            "bookmakers": [
                {
                    "key": "bet365",
                    "title": "Bet365",
                    "last_update": "2026-06-01T12:00:00Z",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "Brazil", "price": 2.1},
                                {"name": "Draw", "price": 3.2},
                                {"name": "France", "price": 3.5},
                            ],
                        }
                    ],
                }
            ],
        }
    ]

    rows = odds_match_rows_from_events(events)

    assert rows == [
        {
            "match_id": "evt-1",
            "source": "the_odds_api",
            "sport_key": "soccer_test",
            "commence_time": "2026-06-11T20:00:00Z",
            "team_a": "Brazil",
            "team_b": "France",
            "odd_a": 2.1,
            "odd_draw": 3.2,
            "odd_b": 3.5,
            "bookmaker": "bet365",
            "bookmaker_title": "Bet365",
            "timestamp": "2026-06-01T12:00:00Z",
        }
    ]


def test_odds_cache_params_do_not_need_api_key(tmp_path) -> None:
    cache = ApiCache(tmp_path)
    endpoint = "/v4/sports/upcoming/odds"
    params = {"regions": "eu", "markets": "h2h", "oddsFormat": "decimal"}

    cache.write(endpoint, params, [{"id": "evt-1"}])
    path = cache.path_for(endpoint, params)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert "apiKey" not in payload["params"]

