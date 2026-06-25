from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tactical_oracle.data.io import read_parquet, write_rows_parquet
from tactical_oracle.data.schemas import GroupAssignment, ScheduleMatch
from tactical_oracle.pipeline.data_spike import normalize_team_name


def _description(values: list[dict[str, Any]]) -> str:
    for item in values:
        if item.get("Description"):
            return str(item["Description"])
    return ""


def _load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _group_letter(match: dict[str, Any]) -> str:
    group_name = _description(match.get("GroupName", []))
    if not group_name.startswith("Group "):
        raise ValueError(f"cannot parse group name: {group_name}")
    return group_name.removeprefix("Group ").strip().upper()


def _team_name(side: dict[str, Any]) -> str:
    return normalize_team_name(_description(side.get("TeamName", [])))


def _placeholder_position(placeholder: str) -> tuple[str, int]:
    if len(placeholder) < 2:
        raise ValueError(f"invalid draw placeholder: {placeholder}")
    return placeholder[0].upper(), int(placeholder[1:])


def _fifa_rank_lookup(fifa_points_path: str | Path | None) -> dict[str, int]:
    if fifa_points_path is None:
        return {}
    return {
        str(row["team"]): int(row["fifa_rank"])
        for row in read_parquet(fifa_points_path).to_dicts()
        if row.get("fifa_rank") is not None
    }


def group_stage_matches(matches_payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        match
        for match in matches_payload.get("Results", [])
        if _description(match.get("StageName", [])) == "First Stage"
    ]


def normalize_worldcup_groups(
    matches_payload: dict[str, Any],
    fifa_points_path: str | Path | None = "data/interim/fifa_points.parquet",
) -> list[dict[str, Any]]:
    fifa_ranks = _fifa_rank_lookup(fifa_points_path)
    assignments: dict[tuple[str, int], str] = {}

    for match in group_stage_matches(matches_payload):
        home_group, home_position = _placeholder_position(str(match["PlaceHolderA"]))
        away_group, away_position = _placeholder_position(str(match["PlaceHolderB"]))
        group = _group_letter(match)
        if home_group != group or away_group != group:
            raise ValueError(f"placeholder/group mismatch in match {match.get('IdMatch')}")
        assignments[(group, home_position)] = _team_name(match["Home"])
        assignments[(group, away_position)] = _team_name(match["Away"])

    rows: list[dict[str, Any]] = []
    for group, position in sorted(assignments):
        team = assignments[(group, position)]
        parsed = GroupAssignment(
            group=group,
            team=team,
            position=position,
            fifa_rank=fifa_ranks.get(team),
        )
        rows.append(parsed.__dict__)
    return rows


def _host_team(match: dict[str, Any]) -> str | None:
    stadium_country = (match.get("Stadium") or {}).get("IdCountry")
    if not stadium_country:
        return None
    for side_name in ("Home", "Away"):
        side = match.get(side_name) or {}
        if side.get("IdCountry") == stadium_country:
            return _team_name(side)
    return None


def normalize_worldcup_schedule(matches_payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for match in sorted(
        group_stage_matches(matches_payload),
        key=lambda item: int(item["MatchNumber"]),
    ):
        host_team = _host_team(match)
        parsed = ScheduleMatch(
            match_id=str(match["IdMatch"]),
            group=_group_letter(match),
            team_a=_team_name(match["Home"]),
            team_b=_team_name(match["Away"]),
            match_number=int(match["MatchNumber"]),
            host_team=host_team,
            neutral_site=host_team is None,
        )
        rows.append(parsed.__dict__)
    return rows


def write_worldcup_structure_outputs(
    matches_json: str | Path = "data/raw/fifa_worldcup_2026_matches.json",
    fifa_points_path: str | Path | None = "data/interim/fifa_points.parquet",
    output_dir: str | Path = "data/interim",
) -> list[Path]:
    payload = _load_json(matches_json)
    output_path = Path(output_dir)
    outputs = {
        "worldcup_groups.parquet": normalize_worldcup_groups(payload, fifa_points_path),
        "worldcup_schedule.parquet": normalize_worldcup_schedule(payload),
    }
    written: list[Path] = []
    for filename, rows in outputs.items():
        destination = output_path / filename
        write_rows_parquet(rows, destination)
        written.append(destination)
    return written


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize FIFA World Cup structure JSON.")
    parser.add_argument("--matches-json", default="data/raw/fifa_worldcup_2026_matches.json")
    parser.add_argument("--fifa-points", default="data/interim/fifa_points.parquet")
    parser.add_argument("--output-dir", default="data/interim")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    for path in write_worldcup_structure_outputs(
        matches_json=args.matches_json,
        fifa_points_path=args.fifa_points,
        output_dir=args.output_dir,
    ):
        print(path)


if __name__ == "__main__":
    main()
