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


def squads_mock() -> list[dict[str, Any]]:
    profiles = {
        "Argentina": (82.0, 0.98),
        "France": (86.0, 1.00),
        "England": (78.0, 0.98),
        "Brazil": (80.0, 0.97),
        "Morocco": (46.0, 0.90),
        "Mexico": (39.0, 0.88),
        "Japan": (36.0, 0.89),
        "Canada": (28.0, 0.84),
    }
    sector_multipliers = {"GOL": 0.45, "DEF": 0.85, "MEI": 1.00, "ATA": 1.15}
    rows: list[dict[str, Any]] = []
    for team, (base_value, level) in profiles.items():
        for idx, sector in enumerate(("GOL", "DEF", "MEI", "ATA"), start=1):
            rows.append(
                {
                    "player_id": f"{team[:3].upper()}-{sector}",
                    "player_name": f"{team} {sector}",
                    "team": team,
                    "age": 24 + idx,
                    "sector": sector,
                    "market_value": base_value * sector_multipliers[sector],
                    "recent_minutes_factor": 0.82 + idx * 0.03,
                    "club_level": level,
                    "league_level": level,
                    "status": 0.9,
                    "called_up": True,
                }
            )
    return rows


def odds_long_term_mock() -> list[dict[str, Any]]:
    return [
        {"team": "Argentina", "pass_yes": 1.20, "pass_no": 5.80, "champion": 7.0},
        {"team": "France", "pass_yes": 1.18, "pass_no": 6.20, "champion": 6.5},
        {"team": "England", "pass_yes": 1.25, "pass_no": 5.20, "champion": 8.0},
        {"team": "Brazil", "pass_yes": 1.22, "pass_no": 5.50, "champion": 7.5},
        {"team": "Morocco", "pass_yes": 1.85, "pass_no": 1.95, "champion": 35.0},
        {"team": "Mexico", "pass_yes": 1.75, "pass_no": 2.05, "champion": 42.0},
        {"team": "Japan", "pass_yes": 1.90, "pass_no": 1.90, "champion": 45.0},
        {"team": "Canada", "pass_yes": 2.65, "pass_no": 1.48, "champion": 90.0},
    ]


def worldcup_annex_c_mock() -> list[dict[str, Any]]:
    return [
        {
            "qualified_thirds": "EFGHIJKL",
            "1A": "3E",
            "1B": "3J",
            "1D": "3I",
            "1E": "3F",
            "1G": "3H",
            "1I": "3G",
            "1K": "3L",
            "1L": "3K",
        },
        {
            "qualified_thirds": "DFGHIJKL",
            "1A": "3H",
            "1B": "3G",
            "1D": "3I",
            "1E": "3D",
            "1G": "3J",
            "1I": "3F",
            "1K": "3L",
            "1L": "3K",
        },
    ]


def all_mock_datasets() -> dict[str, list[dict[str, Any]]]:
    return {
        "teams_mock.parquet": teams_mock(),
        "fifa_points_mock.parquet": fifa_points_mock(),
        "matches_cycle_mock.parquet": matches_cycle_mock(),
        "worldcup_groups_mock.parquet": worldcup_groups_mock(),
        "worldcup_schedule_mock.parquet": worldcup_schedule_mock(),
        "squads_mock.parquet": squads_mock(),
        "odds_long_term_mock.parquet": odds_long_term_mock(),
        "worldcup_annex_c_mock.parquet": worldcup_annex_c_mock(),
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
