from __future__ import annotations

import argparse
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from tactical_oracle.data.io import read_parquet, write_rows_parquet
from tactical_oracle.pipeline.data_spike import CYCLE_END, CYCLE_START

GROUP_STAGE_MATCHES_2026 = 72
WORLD_CUP_TEAMS_2026 = 48
WORLD_CUP_GROUPS_2026 = 12
PLAYERS_PER_SQUAD = 26
TRUSTED_SQUAD_COVERAGE_TARGET = 0.80
FULL_ANNEX_C_COMBINATIONS = 495


def _status(condition: bool, failure: str = "FAIL") -> str:
    return "PASS" if condition else failure


def _audit_row(
    area: str,
    check: str,
    status: str,
    observed: Any,
    expected: Any,
    detail: str = "",
) -> dict[str, Any]:
    return {
        "area": area,
        "check": check,
        "status": status,
        "observed": str(observed),
        "expected": str(expected),
        "detail": detail,
    }


def _rows(path: Path) -> list[dict[str, Any]]:
    return read_parquet(path).to_dicts()


def _teams_from_matches(matches: list[dict[str, Any]]) -> set[str]:
    teams: set[str] = set()
    for row in matches:
        teams.add(str(row["team_a"]))
        teams.add(str(row["team_b"]))
    return teams


def _teams_from_schedule(schedule: list[dict[str, Any]]) -> set[str]:
    teams: set[str] = set()
    for row in schedule:
        teams.add(str(row["team_a"]))
        teams.add(str(row["team_b"]))
    return teams


def _null_count(rows: list[dict[str, Any]], column: str) -> int:
    return sum(1 for row in rows if row.get(column) is None)


def _invalid_penalty_winners(matches: list[dict[str, Any]]) -> list[str]:
    invalid: list[str] = []
    for row in matches:
        winner = row.get("penalty_winner")
        if winner is not None and winner not in {row["team_a"], row["team_b"]}:
            invalid.append(str(row["match_id"]))
    return invalid


def squad_coverage_rows(
    squads: list[dict[str, Any]],
    expected_teams: set[str] | None = None,
) -> list[dict[str, Any]]:
    by_team: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in squads:
        if row.get("called_up", True):
            by_team[str(row["team"])].append(row)

    output: list[dict[str, Any]] = []
    for team in sorted(expected_teams or set(by_team)):
        rows = by_team.get(team, [])
        sector_counts = Counter(str(row.get("sector", "")) for row in rows)
        trusted = sum(1 for row in rows if bool(row.get("market_value_trusted", True)))
        market_total = sum(float(row.get("market_value") or 0.0) for row in rows)
        players = len(rows)
        coverage = trusted / players if players else 0.0
        output.append(
            {
                "team": team,
                "called_up_count": players,
                "trusted_player_count": trusted,
                "trusted_coverage": coverage,
                "squad_complete": players == PLAYERS_PER_SQUAD,
                "trusted_coverage_ok": coverage >= TRUSTED_SQUAD_COVERAGE_TARGET,
                "market_value_total": market_total,
                "goalkeepers": sector_counts["GOL"],
                "defenders": sector_counts["DEF"],
                "midfielders": sector_counts["MEI"],
                "attackers": sector_counts["ATA"],
                "missing_sector_count": sector_counts[""],
                "missing_market_value_count": sum(
                    1 for row in rows if row.get("market_value") is None
                ),
                "market_value_source_count": len(
                    {str(row.get("market_value_source", "")) for row in rows}
                ),
            }
        )
    return output


def odds_coverage_rows(
    odds: list[dict[str, Any]],
    expected_teams: set[str] | None = None,
) -> list[dict[str, Any]]:
    by_team = {str(row["team"]): row for row in odds}
    output: list[dict[str, Any]] = []
    for team in sorted(expected_teams or set(by_team)):
        row = by_team.get(team)
        output.append(
            {
                "team": team,
                "covered": row is not None,
                "source_team": None if row is None else row.get("source_team"),
                "source": None if row is None else row.get("source"),
                "bookmaker": None if row is None else row.get("bookmaker"),
                "american_odd": None if row is None else row.get("american_odd"),
                "champion": None if row is None else row.get("champion"),
                "champion_probability_devig": None
                if row is None
                else row.get("champion_probability_devig"),
                "alias_used": False if row is None else row.get("source_team") != row.get("team"),
            }
        )
    return output


def data_quality_rows(interim_dir: str | Path = "data/interim") -> list[dict[str, Any]]:
    interim = Path(interim_dir)
    fifa = _rows(interim / "fifa_points.parquet")
    matches = _rows(interim / "matches_cycle.parquet")
    groups = _rows(interim / "worldcup_groups.parquet")
    schedule = _rows(interim / "worldcup_schedule.parquet")
    squads = _rows(interim / "squads.parquet")
    odds = _rows(interim / "odds_long_term.parquet")
    annex_c = _rows(interim / "worldcup_annex_c.parquet")

    fifa_teams = {str(row["team"]) for row in fifa}
    group_teams = {str(row["team"]) for row in groups}
    schedule_teams = _teams_from_schedule(schedule)
    match_ids = [str(row["match_id"]) for row in matches]
    match_dates = [str(row["date"]) for row in matches]
    group_sizes = Counter(str(row["group"]) for row in groups)
    squad_rows = squad_coverage_rows(squads, group_teams)
    odds_rows = odds_coverage_rows(odds, group_teams)
    non_fifa_match_teams = sorted(_teams_from_matches(matches) - fifa_teams)
    invalid_penalty_winners = _invalid_penalty_winners(matches)
    duplicate_match_ids = len(match_ids) - len(set(match_ids))
    cycle_dates_ok = (
        min(match_dates) >= CYCLE_START.isoformat()
        and max(match_dates) < CYCLE_END.isoformat()
    )
    negative_goal_count = sum(
        1
        for row in matches
        if int(row["goals_a"]) < 0 or int(row["goals_b"]) < 0
    )
    missing_penalty_winner_count = sum(
        1
        for row in matches
        if row.get("went_to_penalties") and not row.get("penalty_winner")
    )
    groups_are_complete = (
        len(group_sizes) == WORLD_CUP_GROUPS_2026
        and all(size == 4 for size in group_sizes.values())
    )
    schedule_group_gap = len(schedule_teams.symmetric_difference(group_teams))
    invalid_host_count = sum(
        1
        for row in schedule
        if row.get("host_team") not in (None, row["team_a"], row["team_b"])
    )
    squad_teams = {row["team"] for row in squad_rows}
    squad_count_range = (
        f"{min(row['called_up_count'] for row in squad_rows)}.."
        f"{max(row['called_up_count'] for row in squad_rows)}"
    )
    missing_market_value_count = sum(
        row["missing_market_value_count"] for row in squad_rows
    )
    missing_sector_count = sum(row["missing_sector_count"] for row in squad_rows)
    missing_odds_count = sum(1 for row in odds_rows if not row["covered"])
    champion_probability_sum = sum(
        float(row.get("champion_probability_devig") or 0.0) for row in odds
    )

    rows = [
        _audit_row(
            "fifa",
            "ranking teams",
            _status(len(fifa_teams) >= 200),
            len(fifa_teams),
            ">= 200",
        ),
        _audit_row(
            "matches",
            "cycle match ids unique",
            _status(duplicate_match_ids == 0),
            duplicate_match_ids,
            0,
        ),
        _audit_row(
            "matches",
            "cycle date range",
            _status(cycle_dates_ok),
            f"{min(match_dates)}..{max(match_dates)}",
            f"{CYCLE_START.isoformat()}..{CYCLE_END.isoformat()}",
        ),
        _audit_row(
            "matches",
            "negative goals",
            _status(negative_goal_count == 0),
            negative_goal_count,
            0,
        ),
        _audit_row(
            "matches",
            "penalty winner required when penalty flag is true",
            _status(missing_penalty_winner_count == 0),
            missing_penalty_winner_count,
            0,
        ),
        _audit_row(
            "matches",
            "penalty winner is one of match teams",
            _status(not invalid_penalty_winners),
            len(invalid_penalty_winners),
            0,
            ", ".join(invalid_penalty_winners[:10]),
        ),
        _audit_row(
            "matches",
            "non-FIFA teams kept only in raw cycle source",
            _status(not non_fifa_match_teams, failure="WARN"),
            len(non_fifa_match_teams),
            0,
            ", ".join(non_fifa_match_teams[:20]),
        ),
        _audit_row(
            "groups",
            "World Cup teams",
            _status(len(group_teams) == WORLD_CUP_TEAMS_2026),
            len(group_teams),
            WORLD_CUP_TEAMS_2026,
        ),
        _audit_row(
            "groups",
            "12 groups with 4 teams",
            _status(groups_are_complete),
            dict(sorted(group_sizes.items())),
            "12 groups x 4",
        ),
        _audit_row(
            "groups",
            "all group teams in FIFA ranking",
            _status(group_teams <= fifa_teams),
            len(group_teams - fifa_teams),
            0,
        ),
        _audit_row(
            "schedule",
            "group stage matches",
            _status(len(schedule) == GROUP_STAGE_MATCHES_2026),
            len(schedule),
            GROUP_STAGE_MATCHES_2026,
        ),
        _audit_row(
            "schedule",
            "schedule teams match groups",
            _status(schedule_teams == group_teams),
            schedule_group_gap,
            0,
        ),
        _audit_row(
            "schedule",
            "host team valid",
            _status(invalid_host_count == 0),
            invalid_host_count,
            0,
        ),
        _audit_row(
            "squads",
            "squad teams cover groups",
            _status(squad_teams == group_teams),
            len(group_teams - squad_teams),
            0,
        ),
        _audit_row(
            "squads",
            "26 called-up players per team",
            _status(all(row["called_up_count"] == PLAYERS_PER_SQUAD for row in squad_rows)),
            squad_count_range,
            PLAYERS_PER_SQUAD,
        ),
        _audit_row(
            "squads",
            "trusted market value coverage",
            _status(
                all(row["trusted_coverage_ok"] for row in squad_rows),
                failure="WARN",
            ),
            f"{min(row['trusted_coverage'] for row in squad_rows):.3f}",
            f">= {TRUSTED_SQUAD_COVERAGE_TARGET:.2f}",
            ", ".join(
                row["team"]
                for row in squad_rows
                if not row["trusted_coverage_ok"]
            ),
        ),
        _audit_row(
            "squads",
            "market values not null",
            _status(missing_market_value_count == 0),
            missing_market_value_count,
            0,
        ),
        _audit_row(
            "squads",
            "sectors not null",
            _status(missing_sector_count == 0),
            missing_sector_count,
            0,
        ),
        _audit_row(
            "odds",
            "long-term odds cover groups",
            _status(missing_odds_count == 0),
            missing_odds_count,
            0,
        ),
        _audit_row(
            "odds",
            "devig champion probabilities sum to one",
            _status(math.isclose(champion_probability_sum, 1.0, abs_tol=1e-9)),
            f"{champion_probability_sum:.12f}",
            "1.0",
        ),
        _audit_row(
            "annex_c",
            "complete official Annex C",
            _status(len(annex_c) == FULL_ANNEX_C_COMBINATIONS, failure="WARN"),
            len(annex_c),
            FULL_ANNEX_C_COMBINATIONS,
            "MVP can run group stage; full best-thirds bracket still needs official table.",
        ),
    ]
    return rows


def write_data_quality_outputs(
    interim_dir: str | Path = "data/interim",
    output_dir: str | Path = "data/processed",
) -> list[Path]:
    interim = Path(interim_dir)
    output = Path(output_dir)
    groups = _rows(interim / "worldcup_groups.parquet")
    group_teams = {str(row["team"]) for row in groups}

    outputs = {
        "data_quality_report.parquet": data_quality_rows(interim),
        "squad_coverage.parquet": squad_coverage_rows(
            _rows(interim / "squads.parquet"),
            group_teams,
        ),
        "odds_long_term_coverage.parquet": odds_coverage_rows(
            _rows(interim / "odds_long_term.parquet"),
            group_teams,
        ),
    }

    written: list[Path] = []
    for filename, rows in outputs.items():
        path = output / filename
        write_rows_parquet(rows, path)
        written.append(path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit real World Cup Oracle input data.")
    parser.add_argument("--interim-dir", default="data/interim")
    parser.add_argument("--output-dir", default="data/processed")
    args = parser.parse_args()

    for path in write_data_quality_outputs(args.interim_dir, args.output_dir):
        print(path)


if __name__ == "__main__":
    main()
