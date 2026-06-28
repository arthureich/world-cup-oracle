from __future__ import annotations

import argparse
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from world_cup_oracle.data.cache import ApiCache, fetch_json
from world_cup_oracle.data.io import write_rows_parquet

THE_ODDS_API_BASE_URL = "https://api.the-odds-api.com"
THE_ODDS_API_SOURCE = "the_odds_api"


def _decimal_price(value: Any) -> float:
    price = float(value)
    if price <= 1.0:
        raise ValueError("The Odds API response must use decimal odds greater than 1")
    return price


def _h2h_prices(
    outcomes: list[Mapping[str, Any]],
    home_team: str,
    away_team: str,
) -> tuple[float | None, float | None, float | None]:
    prices = {
        str(outcome["name"]).casefold(): _decimal_price(outcome["price"])
        for outcome in outcomes
    }
    odd_home = prices.get(home_team.casefold())
    odd_away = prices.get(away_team.casefold())
    odd_draw = prices.get("draw")
    return odd_home, odd_draw, odd_away


def odds_match_rows_from_events(events: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in events:
        event_id = str(event["id"])
        sport_key = str(event.get("sport_key", ""))
        commence_time = str(event.get("commence_time", ""))
        home_team = str(event["home_team"])
        away_team = str(event["away_team"])
        for bookmaker in event.get("bookmakers", []):
            bookmaker_key = str(bookmaker["key"])
            bookmaker_title = str(bookmaker.get("title", bookmaker_key))
            timestamp = str(bookmaker.get("last_update", ""))
            for market in bookmaker.get("markets", []):
                if market.get("key") != "h2h":
                    continue
                odd_home, odd_draw, odd_away = _h2h_prices(
                    list(market.get("outcomes", [])),
                    home_team,
                    away_team,
                )
                if odd_home is None or odd_away is None:
                    continue
                rows.append(
                    {
                        "match_id": event_id,
                        "source": THE_ODDS_API_SOURCE,
                        "sport_key": sport_key,
                        "commence_time": commence_time,
                        "team_a": home_team,
                        "team_b": away_team,
                        "odd_a": odd_home,
                        "odd_draw": odd_draw,
                        "odd_b": odd_away,
                        "bookmaker": bookmaker_key,
                        "bookmaker_title": bookmaker_title,
                        "timestamp": timestamp,
                    }
                )
    return rows


def fetch_the_odds_api(
    endpoint: str,
    params_without_key: Mapping[str, Any],
    api_key: str,
) -> Any:
    return fetch_json(
        THE_ODDS_API_BASE_URL,
        endpoint,
        {**dict(params_without_key), "apiKey": api_key},
    )


def collect_upcoming_h2h_odds(
    api_key: str,
    sport: str = "upcoming",
    regions: str = "eu",
    bookmakers: str | None = None,
    commence_time_from: str | None = None,
    commence_time_to: str | None = None,
    cache_dir: str | Path = "data/raw/api_cache/the_odds_api",
    output_path: str | Path = "data/interim/odds_match_by_match.parquet",
    force_refresh: bool = False,
) -> list[Path]:
    endpoint = f"/v4/sports/{sport}/odds"
    params: dict[str, Any] = {
        "regions": regions,
        "markets": "h2h",
        "oddsFormat": "decimal",
        "dateFormat": "iso",
    }
    if bookmakers:
        params["bookmakers"] = bookmakers
    if commence_time_from:
        params["commenceTimeFrom"] = commence_time_from
    if commence_time_to:
        params["commenceTimeTo"] = commence_time_to

    cache = ApiCache(cache_dir)
    if force_refresh:
        entry = cache.write(
            endpoint,
            params,
            fetch_the_odds_api(endpoint, params, api_key),
        )
    else:
        entry = cache.get_or_fetch(
            endpoint,
            params,
            lambda ep, cached_params: fetch_the_odds_api(ep, cached_params, api_key),
        )

    rows = odds_match_rows_from_events(list(entry.payload))
    destination = Path(output_path)
    write_rows_parquet(rows, destination)
    return [cache.path_for(endpoint, params), destination]


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect future h2h odds from The Odds API.")
    parser.add_argument("--sport", default="upcoming")
    parser.add_argument("--regions", default="eu")
    parser.add_argument("--bookmakers")
    parser.add_argument("--commence-time-from")
    parser.add_argument("--commence-time-to")
    parser.add_argument("--cache-dir", default="data/raw/api_cache/the_odds_api")
    parser.add_argument("--output", default="data/interim/odds_match_by_match.parquet")
    parser.add_argument("--force-refresh", action="store_true")
    args = parser.parse_args()

    api_key = os.environ.get("THE_ODDS_API_KEY")
    if not api_key:
        raise RuntimeError("Set THE_ODDS_API_KEY before collecting odds.")

    for path in collect_upcoming_h2h_odds(
        api_key=api_key,
        sport=args.sport,
        regions=args.regions,
        bookmakers=args.bookmakers,
        commence_time_from=args.commence_time_from,
        commence_time_to=args.commence_time_to,
        cache_dir=args.cache_dir,
        output_path=args.output,
        force_refresh=args.force_refresh,
    ):
        print(path)


if __name__ == "__main__":
    main()
