from __future__ import annotations

import argparse
import csv
import json
import re
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from tactical_oracle.pipeline.data_spike import normalize_team_name
from tactical_oracle.pipeline.fotmob_parse_bot import (
    DEFAULT_RAW_DIR,
    fetch_and_cache_endpoint,
    raw_response_path,
)

WORLD_CUP_LEAGUE_ID = 77
DEFAULT_DETAIL_DIR = Path("data/raw/world-cup-detail")
DEFAULT_MATCH_IDS_PATH = DEFAULT_RAW_DIR / "worldcup_match_ids.json"
DEFAULT_TEAM_STATS_PATH = DEFAULT_RAW_DIR / "worldcup_match_team_stats.csv"


def _read_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_csv(rows: list[dict[str, Any]], path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row})
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return destination


def _json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _iso_date(value: Any) -> str:
    text = str(value)
    if re.fullmatch(r"\d{8}", text):
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    return text


def _team_lookup(detail_dir: str | Path) -> dict[int, str]:
    return {
        int(row["team_id"]): normalize_team_name(row["team_name"])
        for row in _read_csv(Path(detail_dir) / "teams.csv")
    }


def local_worldcup_matches(
    detail_dir: str | Path = DEFAULT_DETAIL_DIR,
    status: str = "Completed",
) -> list[dict[str, Any]]:
    teams = _team_lookup(detail_dir)
    rows: list[dict[str, Any]] = []
    for row in _read_csv(Path(detail_dir) / "matches.csv"):
        if status and row["status"] != status:
            continue
        home_team_id = int(row["home_team_id"])
        away_team_id = int(row["away_team_id"])
        rows.append(
            {
                "match_id": int(row["match_id"]),
                "date": row["date"],
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "home_team": teams[home_team_id],
                "away_team": teams[away_team_id],
                "status": row["status"],
            }
        )
    return rows


def is_worldcup_league(league: dict[str, Any]) -> bool:
    return any(
        league.get(key) == WORLD_CUP_LEAGUE_ID
        for key in ("primaryId", "parentLeagueId", "leagueId", "id")
    )


def extract_worldcup_day_matches(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data", {})
    played_at = _iso_date(data.get("date"))
    rows: list[dict[str, Any]] = []
    for league in data.get("leagues", []):
        if not is_worldcup_league(league):
            continue
        for match in league.get("matches", []):
            home = match.get("home", {})
            away = match.get("away", {})
            status = match.get("status", {})
            rows.append(
                {
                    "date": played_at,
                    "fotmob_match_id": int(match["id"]),
                    "league_id": match.get("leagueId"),
                    "league_name": league.get("name"),
                    "home_team": normalize_team_name(home["longName"]),
                    "away_team": normalize_team_name(away["longName"]),
                    "home_score": home.get("score"),
                    "away_score": away.get("score"),
                    "started": bool(status.get("started")),
                    "finished": bool(status.get("finished")),
                    "utc_time": status.get("utcTime"),
                }
            )
    return rows


def _match_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row["date"]),
        normalize_team_name(row["home_team"]),
        normalize_team_name(row["away_team"]),
    )


def _teams_key(row: dict[str, Any]) -> tuple[str, str]:
    return (
        normalize_team_name(row["home_team"]),
        normalize_team_name(row["away_team"]),
    )


def _date(value: Any) -> date:
    return date.fromisoformat(_iso_date(value))


def map_local_to_fotmob(
    local_matches: list[dict[str, Any]],
    day_matches: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    fotmob_by_key = {_match_key(row): row for row in day_matches}
    fotmob_by_teams: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in day_matches:
        fotmob_by_teams.setdefault(_teams_key(row), []).append(row)

    mapped: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for local in local_matches:
        fotmob = fotmob_by_key.get(_match_key(local))
        if fotmob is None:
            local_date = _date(local["date"])
            candidates = [
                candidate
                for candidate in fotmob_by_teams.get(_teams_key(local), [])
                if abs((_date(candidate["date"]) - local_date).days) <= 1
            ]
            candidates.sort(key=lambda candidate: abs((_date(candidate["date"]) - local_date).days))
            fotmob = candidates[0] if candidates else None
        if fotmob is None:
            missing.append(local)
            continue
        mapped.append({**local, **fotmob})
    return mapped, missing


def _fetch_cached(
    endpoint: str,
    params: dict[str, str],
    raw_dir: str | Path,
    api_key: str,
    force: bool,
    sleep_seconds: float,
) -> Path:
    destination = raw_response_path(endpoint, params, raw_dir)
    cached = destination.exists() and not force
    path = fetch_and_cache_endpoint(
        endpoint=endpoint,
        params=params,
        raw_dir=raw_dir,
        api_key=api_key,
        force=force,
    )
    if not cached and sleep_seconds > 0:
        time.sleep(sleep_seconds)
    return path


def fetch_worldcup_match_details(
    detail_dir: str | Path = DEFAULT_DETAIL_DIR,
    raw_dir: str | Path = DEFAULT_RAW_DIR,
    api_key: str | None = None,
    status: str = "Completed",
    force: bool = False,
    sleep_seconds: float = 12.5,
    max_matches: int | None = None,
    verbose: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not api_key:
        raise RuntimeError("api_key is required for uncached FotMob World Cup fetches.")

    local_matches = local_worldcup_matches(detail_dir, status=status)
    if max_matches is not None:
        local_matches = local_matches[:max_matches]

    day_matches: list[dict[str, Any]] = []
    match_dates = {_date(row["date"]) for row in local_matches}
    lookup_dates = sorted(
        match_dates | {played_at + timedelta(days=1) for played_at in match_dates}
    )
    for match_date in lookup_dates:
        match_date_text = match_date.isoformat()
        if verbose:
            print(f"fetch date {match_date_text}")
        path = _fetch_cached(
            endpoint="get_matches_by_date",
            params={"date": match_date_text.replace("-", "")},
            raw_dir=raw_dir,
            api_key=api_key,
            force=force,
            sleep_seconds=sleep_seconds,
        )
        extracted = extract_worldcup_day_matches(_json(path))
        day_matches.extend(extracted)
        if verbose:
            print(f"  world cup matches found: {len(extracted)}")

    mapped, missing = map_local_to_fotmob(local_matches, day_matches)
    for index, match in enumerate(mapped, start=1):
        if verbose:
            print(
                f"fetch detail {index}/{len(mapped)} "
                f"{match['home_team']} x {match['away_team']} "
                f"({match['fotmob_match_id']})"
            )
        _fetch_cached(
            endpoint="get_match_details",
            params={"match_id": str(match["fotmob_match_id"])},
            raw_dir=raw_dir,
            api_key=api_key,
            force=force,
            sleep_seconds=sleep_seconds,
        )
    return mapped, missing


def _flatten_all_period_stats(payload: dict[str, Any]) -> dict[str, Any]:
    periods = (
        payload.get("data", {})
        .get("content", {})
        .get("stats", {})
        .get("Periods", {})
        .get("All", {})
    )
    stats_by_key: dict[str, Any] = {}
    for section in periods.get("stats", []):
        for stat in section.get("stats", []):
            values = stat.get("stats")
            if not isinstance(values, list) or len(values) != 2:
                continue
            if values == [None, None]:
                continue
            stats_by_key.setdefault(stat.get("key"), stat)
    return stats_by_key


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, int | float):
        return float(value)
    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    if match is None:
        return None
    return float(match.group(0))


def _pct(value: Any) -> float | None:
    if value in (None, ""):
        return None
    match = re.search(r"\((-?\d+(?:\.\d+)?)%\)", str(value))
    if match is None:
        return None
    return float(match.group(1))


def _stat_pair(stats_by_key: dict[str, Any], key: str) -> list[Any]:
    stat = stats_by_key.get(key)
    if stat is None:
        return [None, None]
    values = stat.get("stats")
    if not isinstance(values, list) or len(values) != 2:
        return [None, None]
    return values


def extract_match_team_stats(
    match: dict[str, Any],
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    stats = _flatten_all_period_stats(payload)
    stat_values = {
        "possession_pct": _stat_pair(stats, "BallPossesion"),
        "xg": _stat_pair(stats, "expected_goals"),
        "total_shots": _stat_pair(stats, "total_shots"),
        "shots_on_target": _stat_pair(stats, "ShotsOnTarget"),
        "touches_in_opposition_box": _stat_pair(stats, "touches_opp_box"),
        "clear_chances": _stat_pair(stats, "big_chance"),
        "opposition_half_passes": _stat_pair(stats, "opposition_half_passes"),
        "corners": _stat_pair(stats, "corners"),
        "fouls": _stat_pair(stats, "fouls"),
        "red_cards": _stat_pair(stats, "red_cards"),
        "ground_duels_won": _stat_pair(stats, "ground_duels_won"),
        "successful_dribbles": _stat_pair(stats, "dribbles_succeeded"),
    }
    teams = [
        (match["home_team_id"], match["home_team"], 0),
        (match["away_team_id"], match["away_team"], 1),
    ]
    rows: list[dict[str, Any]] = []
    for team_id, team, index in teams:
        row = {
            "match_id": match["match_id"],
            "team_id": team_id,
            "team": team,
            "date": match.get("date"),
            "status": match.get("status"),
            "home_score": match.get("home_score"),
            "away_score": match.get("away_score"),
            "utc_time": match.get("utc_time"),
            "fotmob_match_id": match["fotmob_match_id"],
            "data_source": "fotmob-parse-bot",
            "last_updated": date.today().isoformat(),
        }
        for column, values in stat_values.items():
            value = values[index]
            row[column] = _number(value)
            if column == "ground_duels_won":
                row["ground_duels_won_pct"] = _pct(value)
            if column == "successful_dribbles":
                row["successful_dribbles_pct"] = _pct(value)
        rows.append(row)
    return rows


def write_fotmob_worldcup_outputs(
    mapped_matches: list[dict[str, Any]],
    raw_dir: str | Path = DEFAULT_RAW_DIR,
    match_ids_path: str | Path = DEFAULT_MATCH_IDS_PATH,
    team_stats_path: str | Path = DEFAULT_TEAM_STATS_PATH,
) -> dict[str, Path]:
    raw_path = Path(raw_dir)
    match_ids_destination = Path(match_ids_path)
    match_ids_destination.parent.mkdir(parents=True, exist_ok=True)
    match_ids_destination.write_text(
        json.dumps(mapped_matches, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    stat_rows: list[dict[str, Any]] = []
    for match in mapped_matches:
        detail_path = raw_response_path(
            "get_match_details",
            {"match_id": str(match["fotmob_match_id"])},
            raw_path,
        )
        stat_rows.extend(extract_match_team_stats(match, _json(detail_path)))
    stats_destination = _write_csv(stat_rows, team_stats_path)
    return {
        "worldcup_match_ids.json": match_ids_destination,
        "worldcup_match_team_stats.csv": stats_destination,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch and extract World Cup match stats from FotMob through Parse.bot."
    )
    parser.add_argument("--detail-dir", default=str(DEFAULT_DETAIL_DIR))
    parser.add_argument("--raw-dir", default=str(DEFAULT_RAW_DIR))
    parser.add_argument("--match-ids-output", default=str(DEFAULT_MATCH_IDS_PATH))
    parser.add_argument("--team-stats-output", default=str(DEFAULT_TEAM_STATS_PATH))
    parser.add_argument("--status", default="Completed")
    parser.add_argument("--api-key-env", default="PARSE_BOT_API_KEY")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--sleep-seconds", type=float, default=12.5)
    parser.add_argument("--max-matches", type=int, default=None)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    import os

    mapped, missing = fetch_worldcup_match_details(
        detail_dir=args.detail_dir,
        raw_dir=args.raw_dir,
        api_key=os.environ.get(args.api_key_env),
        status=args.status,
        force=args.force,
        sleep_seconds=args.sleep_seconds,
        max_matches=args.max_matches,
        verbose=True,
    )
    outputs = write_fotmob_worldcup_outputs(
        mapped_matches=mapped,
        raw_dir=args.raw_dir,
        match_ids_path=args.match_ids_output,
        team_stats_path=args.team_stats_output,
    )
    for path in outputs.values():
        print(path)
    print(f"mapped_matches={len(mapped)} missing_matches={len(missing)}")
    for row in missing[:10]:
        print(f"missing: {row['date']} {row['home_team']} x {row['away_team']}")


if __name__ == "__main__":
    main()
