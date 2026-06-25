from __future__ import annotations

from pathlib import Path
from typing import Any

from tactical_oracle.data.io import read_parquet, write_rows_parquet
from tactical_oracle.data.schemas import FifaPoints, GroupAssignment, Match, ScheduleMatch, Team
from tactical_oracle.simulation import build_annex_c_table

MOCK_RAW_TO_INTERIM = {
    "teams_mock.parquet": "teams.parquet",
    "fifa_points_mock.parquet": "fifa_points.parquet",
    "matches_cycle_mock.parquet": "matches_cycle.parquet",
    "worldcup_groups_mock.parquet": "worldcup_groups.parquet",
    "worldcup_schedule_mock.parquet": "worldcup_schedule.parquet",
    "squads_mock.parquet": "squads.parquet",
    "odds_long_term_mock.parquet": "odds_long_term.parquet",
    "worldcup_annex_c_mock.parquet": "worldcup_annex_c.parquet",
}


def _rows_from_parquet(path: Path) -> list[dict[str, Any]]:
    return read_parquet(path).to_dicts()


def _date_to_iso(row: dict[str, Any], field: str) -> dict[str, Any]:
    value = row.get(field)
    if hasattr(value, "isoformat"):
        row[field] = value.isoformat()
    return row


def normalize_teams(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [Team(**row).__dict__ for row in rows]


def normalize_fifa_points(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in rows:
        parsed = FifaPoints(**row).__dict__
        output.append(_date_to_iso(parsed, "ranking_date"))
    return output


def normalize_matches(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in rows:
        parsed = Match(**row).__dict__
        output.append(_date_to_iso(parsed, "date"))
    return output


def normalize_groups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [GroupAssignment(**row).__dict__ for row in rows]


def normalize_schedule(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [ScheduleMatch(**row).__dict__ for row in rows]


def normalize_annex_c(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    build_annex_c_table(rows)
    return rows


def normalize_passthrough(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return rows


NORMALIZERS = {
    "teams_mock.parquet": normalize_teams,
    "fifa_points_mock.parquet": normalize_fifa_points,
    "matches_cycle_mock.parquet": normalize_matches,
    "worldcup_groups_mock.parquet": normalize_groups,
    "worldcup_schedule_mock.parquet": normalize_schedule,
    "squads_mock.parquet": normalize_passthrough,
    "odds_long_term_mock.parquet": normalize_passthrough,
    "worldcup_annex_c_mock.parquet": normalize_annex_c,
}


def normalize_mock_raw(
    raw_dir: str | Path = "data/raw",
    output_dir: str | Path = "data/interim",
) -> list[Path]:
    raw_path = Path(raw_dir)
    output_path = Path(output_dir)
    written: list[Path] = []
    for source_name, destination_name in MOCK_RAW_TO_INTERIM.items():
        source = raw_path / source_name
        if not source.exists():
            raise FileNotFoundError(f"missing raw mock dataset: {source}")
        rows = _rows_from_parquet(source)
        normalized = NORMALIZERS[source_name](rows)
        destination = output_path / destination_name
        write_rows_parquet(normalized, destination)
        written.append(destination)
    return written


def main() -> None:
    for path in normalize_mock_raw():
        print(path)


if __name__ == "__main__":
    main()

