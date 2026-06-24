from __future__ import annotations

from pathlib import Path
from typing import Any

from tactical_oracle.data.io import write_rows_parquet


def teams_mock() -> list[dict[str, Any]]:
    return [
        {"team": "Brazil", "fifa_rank": 5, "confederation": "CONMEBOL", "is_host": False},
        {"team": "Argentina", "fifa_rank": 1, "confederation": "CONMEBOL", "is_host": False},
        {"team": "France", "fifa_rank": 2, "confederation": "UEFA", "is_host": False},
        {"team": "England", "fifa_rank": 4, "confederation": "UEFA", "is_host": False},
        {"team": "Japan", "fifa_rank": 18, "confederation": "AFC", "is_host": False},
        {"team": "Mexico", "fifa_rank": 15, "confederation": "CONCACAF", "is_host": True},
        {"team": "Canada", "fifa_rank": 30, "confederation": "CONCACAF", "is_host": True},
        {"team": "Morocco", "fifa_rank": 12, "confederation": "CAF", "is_host": False},
    ]


def fifa_points_mock() -> list[dict[str, Any]]:
    return [
        {"team": "Argentina", "fifa_points": 1860.0, "ranking_date": "2023-01-01", "fifa_rank": 1},
        {"team": "France", "fifa_points": 1838.0, "ranking_date": "2023-01-01", "fifa_rank": 2},
        {"team": "England", "fifa_points": 1795.0, "ranking_date": "2023-01-01", "fifa_rank": 4},
        {"team": "Brazil", "fifa_points": 1784.0, "ranking_date": "2023-01-01", "fifa_rank": 5},
        {"team": "Morocco", "fifa_points": 1663.0, "ranking_date": "2023-01-01", "fifa_rank": 12},
        {"team": "Mexico", "fifa_points": 1652.0, "ranking_date": "2023-01-01", "fifa_rank": 15},
        {"team": "Japan", "fifa_points": 1614.0, "ranking_date": "2023-01-01", "fifa_rank": 18},
        {"team": "Canada", "fifa_points": 1500.0, "ranking_date": "2023-01-01", "fifa_rank": 30},
    ]


def matches_cycle_mock() -> list[dict[str, Any]]:
    return [
        {
            "match_id": "cycle-001",
            "date": "2023-06-10",
            "team_a": "Brazil",
            "team_b": "Japan",
            "goals_a": 2,
            "goals_b": 0,
            "competition": "Friendly",
            "stage": "single",
            "match_type": "friendly",
            "home_team": "Brazil",
            "neutral_site": False,
            "went_to_penalties": False,
            "penalty_winner": None,
        },
        {
            "match_id": "cycle-002",
            "date": "2023-09-12",
            "team_a": "Argentina",
            "team_b": "Mexico",
            "goals_a": 1,
            "goals_b": 0,
            "competition": "Qualifier",
            "stage": "group",
            "match_type": "qualifier",
            "home_team": "Argentina",
            "neutral_site": False,
            "went_to_penalties": False,
            "penalty_winner": None,
        },
        {
            "match_id": "cycle-003",
            "date": "2024-03-22",
            "team_a": "France",
            "team_b": "England",
            "goals_a": 1,
            "goals_b": 1,
            "competition": "Nations League",
            "stage": "group",
            "match_type": "nations_league",
            "home_team": "France",
            "neutral_site": False,
            "went_to_penalties": False,
            "penalty_winner": None,
        },
        {
            "match_id": "cycle-004",
            "date": "2024-07-05",
            "team_a": "Morocco",
            "team_b": "Mexico",
            "goals_a": 1,
            "goals_b": 1,
            "competition": "Continental Cup",
            "stage": "knockout",
            "match_type": "continental_knockout",
            "home_team": None,
            "neutral_site": True,
            "went_to_penalties": True,
            "penalty_winner": "Morocco",
        },
        {
            "match_id": "cycle-005",
            "date": "2025-10-15",
            "team_a": "Canada",
            "team_b": "Japan",
            "goals_a": 0,
            "goals_b": 2,
            "competition": "Qualifier",
            "stage": "group",
            "match_type": "qualifier",
            "home_team": "Canada",
            "neutral_site": False,
            "went_to_penalties": False,
            "penalty_winner": None,
        },
    ]


def worldcup_groups_mock() -> list[dict[str, Any]]:
    return [
        {"group": "A", "team": "Brazil", "fifa_rank": 5},
        {"group": "A", "team": "Japan", "fifa_rank": 18},
        {"group": "A", "team": "Mexico", "fifa_rank": 15},
        {"group": "A", "team": "Canada", "fifa_rank": 30},
        {"group": "B", "team": "Argentina", "fifa_rank": 1},
        {"group": "B", "team": "France", "fifa_rank": 2},
        {"group": "B", "team": "England", "fifa_rank": 4},
        {"group": "B", "team": "Morocco", "fifa_rank": 12},
    ]


def worldcup_schedule_mock() -> list[dict[str, Any]]:
    return [
        {"match_id": "A-1", "group": "A", "team_a": "Brazil", "team_b": "Japan"},
        {"match_id": "A-2", "group": "A", "team_a": "Mexico", "team_b": "Canada"},
        {"match_id": "A-3", "group": "A", "team_a": "Brazil", "team_b": "Mexico"},
        {"match_id": "A-4", "group": "A", "team_a": "Japan", "team_b": "Canada"},
        {"match_id": "A-5", "group": "A", "team_a": "Brazil", "team_b": "Canada"},
        {"match_id": "A-6", "group": "A", "team_a": "Japan", "team_b": "Mexico"},
        {"match_id": "B-1", "group": "B", "team_a": "Argentina", "team_b": "France"},
        {"match_id": "B-2", "group": "B", "team_a": "England", "team_b": "Morocco"},
        {"match_id": "B-3", "group": "B", "team_a": "Argentina", "team_b": "England"},
        {"match_id": "B-4", "group": "B", "team_a": "France", "team_b": "Morocco"},
        {"match_id": "B-5", "group": "B", "team_a": "Argentina", "team_b": "Morocco"},
        {"match_id": "B-6", "group": "B", "team_a": "France", "team_b": "England"},
    ]


def all_mock_datasets() -> dict[str, list[dict[str, Any]]]:
    return {
        "teams_mock.parquet": teams_mock(),
        "fifa_points_mock.parquet": fifa_points_mock(),
        "matches_cycle_mock.parquet": matches_cycle_mock(),
        "worldcup_groups_mock.parquet": worldcup_groups_mock(),
        "worldcup_schedule_mock.parquet": worldcup_schedule_mock(),
    }


def write_mock_parquets(base_dir: str | Path = "data/raw") -> list[Path]:
    base_path = Path(base_dir)
    written: list[Path] = []
    for filename, rows in all_mock_datasets().items():
        destination = base_path / filename
        write_rows_parquet(rows, destination)
        written.append(destination)
    return written


def main() -> None:
    for path in write_mock_parquets():
        print(path)


if __name__ == "__main__":
    main()
