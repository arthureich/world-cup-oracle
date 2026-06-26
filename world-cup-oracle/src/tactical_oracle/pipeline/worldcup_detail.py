from __future__ import annotations

import argparse
import csv
import re
from datetime import date
from pathlib import Path
from typing import Any

from tactical_oracle.data.io import read_parquet, write_rows_parquet
from tactical_oracle.pipeline.data_spike import normalize_team_name

TOURNAMENT_START = date(2026, 6, 11)

POSITION_TO_SECTOR = {
    "GK": "GOL",
    "DEF": "DEF",
    "MID": "MEI",
    "FWD": "ATA",
}


def _read_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(float(str(value)))


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _first_optional(converter: Any, *values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return converter(value)
    return None


def _first_text(*values: Any) -> str | None:
    for value in values:
        if value not in (None, ""):
            return str(value)
    return None


def _stat_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _optional_stat_float(row: dict[str, Any], *columns: str) -> float | None:
    keyed = {_stat_key(str(key)): value for key, value in row.items()}
    for column in columns:
        value = keyed.get(_stat_key(column))
        if value not in (None, ""):
            return float(str(value).replace("%", ""))
    return None


def _bool_from_int(value: Any) -> bool:
    return bool(_optional_int(value))


def _age_on_tournament_start(date_of_birth: str) -> float:
    born = date.fromisoformat(date_of_birth)
    return (TOURNAMENT_START - born).days / 365.2425


def _detail_path(base_dir: str | Path, filename: str) -> Path:
    return Path(base_dir) / filename


def _team_rows(detail_dir: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in _read_csv(_detail_path(detail_dir, "teams.csv")):
        rows.append(
            {
                "team_id": int(row["team_id"]),
                "team": normalize_team_name(row["team_name"]),
                "fifa_code": row["fifa_code"],
                "group": row["group_letter"],
                "confederation": row["confederation"],
                "fifa_rank": _optional_int(row["fifa_ranking_pre_tournament"]),
                "source_elo": _optional_float(row["elo_rating"]),
                "manager": row["manager_name"],
            }
        )
    return rows


def _team_lookup(detail_dir: str | Path) -> dict[int, str]:
    return {row["team_id"]: row["team"] for row in _team_rows(detail_dir)}


def _player_lookup(detail_dir: str | Path) -> dict[int, str]:
    return {
        int(row["player_id"]): row["player_name"]
        for row in _read_csv(_detail_path(detail_dir, "squads_and_players.csv"))
    }


def _official_match_lookup(schedule_path: str | Path | None) -> dict[int, str]:
    if schedule_path is None or not Path(schedule_path).exists():
        return {}
    return {
        int(row["match_number"]): str(row["match_id"])
        for row in read_parquet(schedule_path).to_dicts()
    }


def _official_match_info_by_raw_match(
    detail_dir: str | Path,
    schedule_path: str | Path | None,
) -> dict[int, dict[str, Any]]:
    if schedule_path is None or not Path(schedule_path).exists():
        return {}

    schedule_by_teams: dict[tuple[str, str], dict[str, Any]] = {}
    for row in read_parquet(schedule_path).to_dicts():
        key = (normalize_team_name(row["team_a"]), normalize_team_name(row["team_b"]))
        schedule_by_teams[key] = {
            "match_id": str(row["match_id"]),
            "match_number": int(row["match_number"]),
        }

    teams = _team_lookup(detail_dir)
    raw_match_info: dict[int, dict[str, Any]] = {}
    for row in _read_csv(_detail_path(detail_dir, "matches.csv")):
        raw_match_id = int(row["match_id"])
        key = (
            teams[int(row["home_team_id"])],
            teams[int(row["away_team_id"])],
        )
        if key in schedule_by_teams:
            raw_match_info[raw_match_id] = schedule_by_teams[key]
    return raw_match_info


def normalize_worldcup_teams_detail(
    detail_dir: str | Path = "data/raw/world-cup-detail",
) -> list[dict[str, Any]]:
    return _team_rows(detail_dir)


def normalize_worldcup_squads(
    detail_dir: str | Path = "data/raw/world-cup-detail",
) -> list[dict[str, Any]]:
    teams = _team_lookup(detail_dir)
    rows: list[dict[str, Any]] = []
    for row in _read_csv(_detail_path(detail_dir, "squads_and_players.csv")):
        position = row["position"]
        rows.append(
            {
                "player_id": str(row["player_id"]),
                "player_name": row["player_name"],
                "team": teams[int(row["team_id"])],
                "age": _age_on_tournament_start(row["date_of_birth"]),
                "sector": POSITION_TO_SECTOR[position],
                "position": position,
                "club": row["club_team"],
                "market_value": float(row["market_value_eur"]),
                "market_value_eur": float(row["market_value_eur"]),
                "market_value_source": "world-cup-detail",
                "market_value_trusted": False,
                "recent_minutes_factor": 1.0,
                "club_level": 1.0,
                "league_level": 1.0,
                "status": 1.0,
                "called_up": True,
                "caps": _optional_int(row["caps"]),
                "date_of_birth": row["date_of_birth"],
                "height_cm": _optional_int(row["height_cm"]),
                "international_goals": _optional_int(row["goals"]),
            }
        )
    return rows


def _red_card_index(detail_dir: str | Path) -> dict[tuple[int, int], tuple[int, int | None]]:
    red_cards: dict[tuple[int, int], list[int]] = {}
    for row in _read_csv(_detail_path(detail_dir, "match_events.csv")):
        if row["event_type"] != "Red Card":
            continue
        key = (int(row["match_id"]), int(row["team_id"]))
        red_cards.setdefault(key, []).append(int(row["minute"]))
    return {
        key: (len(minutes), min(minutes) if minutes else None)
        for key, minutes in red_cards.items()
    }


def _match_rows_by_number(detail_dir: str | Path) -> dict[int, dict[str, Any]]:
    return {int(row["match_id"]): row for row in _read_csv(_detail_path(detail_dir, "matches.csv"))}


def _stats_by_match_team(
    detail_dir: str | Path,
    supplemental_stats_path: str | Path | None = None,
) -> dict[tuple[int, int], dict[str, str]]:
    stats = {
        (int(row["match_id"]), int(row["team_id"])): row
        for row in _read_csv(_detail_path(detail_dir, "match_team_stats.csv"))
    }
    if supplemental_stats_path is None or not Path(supplemental_stats_path).exists():
        return stats
    for row in _read_csv(supplemental_stats_path):
        key = (int(row["match_id"]), int(row["team_id"]))
        merged = dict(stats.get(key, {}))
        merged.update({column: value for column, value in row.items() if value not in (None, "")})
        stats[key] = merged
    return stats


def normalize_worldcup_match_stats(
    detail_dir: str | Path = "data/raw/world-cup-detail",
    schedule_path: str | Path | None = "data/interim/worldcup_schedule.parquet",
    fotmob_stats_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    teams = _team_lookup(detail_dir)
    matches = _match_rows_by_number(detail_dir)
    stats = _stats_by_match_team(detail_dir, fotmob_stats_path)
    red_cards = _red_card_index(detail_dir)
    official_ids = _official_match_lookup(schedule_path)
    official_matches = _official_match_info_by_raw_match(detail_dir, schedule_path)

    rows: list[dict[str, Any]] = []
    for (raw_match_number, team_id), team_stats in sorted(stats.items()):
        match = matches[raw_match_number]
        official_match = official_matches.get(
            raw_match_number,
            {
                "match_id": official_ids.get(raw_match_number, str(raw_match_number)),
                "match_number": raw_match_number,
            },
        )
        home_team_id = int(match["home_team_id"])
        away_team_id = int(match["away_team_id"])
        opponent_id = away_team_id if team_id == home_team_id else home_team_id
        opponent_stats = stats.get((raw_match_number, opponent_id), {})
        is_home = team_id == home_team_id
        event_red_card_count, first_red_card_minute = red_cards.get(
            (raw_match_number, team_id),
            (0, None),
        )
        stat_red_card_count = _optional_int(team_stats.get("red_cards"))
        red_card_count = event_red_card_count or stat_red_card_count or 0

        rows.append(
            {
                "match_id": official_match["match_id"],
                "match_number": official_match["match_number"],
                "date": _first_text(team_stats.get("date"), match["date"]),
                "team": teams[team_id],
                "opponent": teams[opponent_id],
                "is_home": is_home,
                "status": _first_text(team_stats.get("status"), match["status"]),
                "goals": _first_optional(
                    _optional_int,
                    team_stats.get("home_score" if is_home else "away_score"),
                    match["home_score" if is_home else "away_score"],
                ),
                "goals_against": _first_optional(
                    _optional_int,
                    opponent_stats.get("home_score" if not is_home else "away_score"),
                    match["away_score" if is_home else "home_score"]
                ),
                "xg": _first_optional(
                    _optional_float,
                    team_stats.get("xg"),
                    match["home_xg" if is_home else "away_xg"],
                ),
                "xg_against": _first_optional(
                    _optional_float,
                    opponent_stats.get("xg"),
                    match["away_xg" if is_home else "home_xg"],
                ),
                "shots": _optional_int(team_stats.get("total_shots")),
                "shots_against": _optional_int(opponent_stats.get("total_shots")),
                "shots_on_target": _optional_int(team_stats.get("shots_on_target")),
                "shots_on_target_against": _optional_int(
                    opponent_stats.get("shots_on_target")
                ),
                "clear_chances": _optional_stat_float(
                    team_stats,
                    "clear_chances",
                    "big_chance",
                    "big chances",
                ),
                "clear_chances_against": _optional_stat_float(
                    opponent_stats,
                    "clear_chances",
                    "big_chance",
                    "big chances",
                ),
                "touches_in_opposition_box": _optional_stat_float(
                    team_stats,
                    "touches_in_opposition_box",
                    "touches in opposition box",
                ),
                "touches_in_opposition_box_against": _optional_stat_float(
                    opponent_stats,
                    "touches_in_opposition_box",
                    "touches in opposition box",
                ),
                "opposition_half_passes": _optional_stat_float(
                    team_stats,
                    "opposition_half_passes",
                    "opposition half passes",
                ),
                "opposition_half_passes_against": _optional_stat_float(
                    opponent_stats,
                    "opposition_half_passes",
                    "opposition half passes",
                ),
                "ground_duels_won": _optional_stat_float(
                    team_stats,
                    "ground_duels_won",
                    "ground duels won",
                ),
                "ground_duels_won_against": _optional_stat_float(
                    opponent_stats,
                    "ground_duels_won",
                    "ground duels won",
                ),
                "ground_duels_won_pct": _optional_stat_float(
                    team_stats,
                    "ground_duels_won_pct",
                    "ground duels won %",
                    "ground duels won percent",
                ),
                "ground_duels_won_pct_against": _optional_stat_float(
                    opponent_stats,
                    "ground_duels_won_pct",
                    "ground duels won %",
                    "ground duels won percent",
                ),
                "successful_dribbles": _optional_stat_float(
                    team_stats,
                    "successful_dribbles",
                    "successful dribbles",
                ),
                "successful_dribbles_against": _optional_stat_float(
                    opponent_stats,
                    "successful_dribbles",
                    "successful dribbles",
                ),
                "successful_dribbles_pct": _optional_stat_float(
                    team_stats,
                    "successful_dribbles_pct",
                    "successful dribbles %",
                    "successful dribbles percent",
                ),
                "successful_dribbles_pct_against": _optional_stat_float(
                    opponent_stats,
                    "successful_dribbles_pct",
                    "successful dribbles %",
                    "successful dribbles percent",
                ),
                "possession_pct": _optional_float(team_stats.get("possession_pct")),
                "corners": _optional_int(team_stats.get("corners")),
                "corners_against": _optional_int(opponent_stats.get("corners")),
                "fouls": _optional_int(team_stats.get("fouls")),
                "fouls_against": _optional_int(opponent_stats.get("fouls")),
                "offsides": _optional_int(team_stats.get("offsides")),
                "saves": _optional_int(team_stats.get("saves")),
                "red_cards": red_card_count,
                "first_red_card_minute": first_red_card_minute,
                "player_of_the_match": team_stats.get("player_of_the_match") or None,
                "data_source": team_stats.get("data_source") or None,
                "last_updated": team_stats.get("last_updated") or None,
            }
        )
    return rows


def normalize_worldcup_match_events(
    detail_dir: str | Path = "data/raw/world-cup-detail",
    schedule_path: str | Path | None = "data/interim/worldcup_schedule.parquet",
) -> list[dict[str, Any]]:
    teams = _team_lookup(detail_dir)
    players = _player_lookup(detail_dir)
    official_ids = _official_match_lookup(schedule_path)
    official_matches = _official_match_info_by_raw_match(detail_dir, schedule_path)
    rows: list[dict[str, Any]] = []
    for row in _read_csv(_detail_path(detail_dir, "match_events.csv")):
        raw_match_number = int(row["match_id"])
        official_match = official_matches.get(
            raw_match_number,
            {
                "match_id": official_ids.get(raw_match_number, str(raw_match_number)),
                "match_number": raw_match_number,
            },
        )
        player_id = int(row["player_id"])
        rows.append(
            {
                "event_id": str(row["event_id"]),
                "match_id": official_match["match_id"],
                "match_number": official_match["match_number"],
                "minute": int(row["minute"]),
                "event_type": row["event_type"],
                "team": teams[int(row["team_id"])],
                "player_id": str(player_id),
                "player_name": players.get(player_id),
            }
        )
    return rows


def normalize_worldcup_lineups(
    detail_dir: str | Path = "data/raw/world-cup-detail",
    schedule_path: str | Path | None = "data/interim/worldcup_schedule.parquet",
) -> list[dict[str, Any]]:
    teams = _team_lookup(detail_dir)
    players = _player_lookup(detail_dir)
    official_ids = _official_match_lookup(schedule_path)
    official_matches = _official_match_info_by_raw_match(detail_dir, schedule_path)
    rows: list[dict[str, Any]] = []
    for row in _read_csv(_detail_path(detail_dir, "match_lineups.csv")):
        raw_match_number = int(row["match_id"])
        official_match = official_matches.get(
            raw_match_number,
            {
                "match_id": official_ids.get(raw_match_number, str(raw_match_number)),
                "match_number": raw_match_number,
            },
        )
        player_id = int(row["player_id"])
        rows.append(
            {
                "lineup_id": str(row["lineup_id"]),
                "match_id": official_match["match_id"],
                "match_number": official_match["match_number"],
                "team": teams[int(row["team_id"])],
                "player_id": str(player_id),
                "player_name": players.get(player_id),
                "is_starting_xi": _bool_from_int(row["is_starting_xi"]),
                "position": row["tactical_position"],
                "sector": POSITION_TO_SECTOR[row["tactical_position"]],
                "minutes_played": _optional_int(row["minutes_played"]),
            }
        )
    return rows


def write_worldcup_detail_outputs(
    detail_dir: str | Path = "data/raw/world-cup-detail",
    schedule_path: str | Path | None = "data/interim/worldcup_schedule.parquet",
    output_dir: str | Path = "data/interim",
    fotmob_stats_path: str | Path | None = None,
) -> list[Path]:
    output_path = Path(output_dir)
    outputs = {
        "worldcup_teams_detail.parquet": normalize_worldcup_teams_detail(detail_dir),
        "squads.parquet": normalize_worldcup_squads(detail_dir),
        "worldcup_match_stats.parquet": normalize_worldcup_match_stats(
            detail_dir,
            schedule_path,
            fotmob_stats_path,
        ),
        "worldcup_match_events.parquet": normalize_worldcup_match_events(
            detail_dir,
            schedule_path,
        ),
        "worldcup_lineups.parquet": normalize_worldcup_lineups(detail_dir, schedule_path),
    }
    written: list[Path] = []
    for filename, rows in outputs.items():
        destination = output_path / filename
        write_rows_parquet(rows, destination)
        written.append(destination)
    return written


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize World Cup detail CSVs.")
    parser.add_argument("--detail-dir", default="data/raw/world-cup-detail")
    parser.add_argument("--schedule", default="data/interim/worldcup_schedule.parquet")
    parser.add_argument("--output-dir", default="data/interim")
    parser.add_argument("--fotmob-stats", default="data/raw/fotmob/worldcup_match_team_stats.csv")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    for path in write_worldcup_detail_outputs(
        detail_dir=args.detail_dir,
        schedule_path=args.schedule,
        output_dir=args.output_dir,
        fotmob_stats_path=args.fotmob_stats,
    ):
        print(path)


if __name__ == "__main__":
    main()
