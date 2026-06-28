from __future__ import annotations

import json

from world_cup_oracle.data.io import read_parquet, write_rows_parquet
from world_cup_oracle.pipeline.worldcup_structure import (
    normalize_worldcup_groups,
    normalize_worldcup_schedule,
    write_worldcup_structure_outputs,
)


def _team(description: str, country: str) -> dict:
    return {
        "TeamName": [{"Locale": "en-GB", "Description": description}],
        "IdCountry": country,
    }


def _match(
    match_id: str,
    match_number: int,
    group: str,
    home: tuple[str, str],
    away: tuple[str, str],
    stadium_country: str,
) -> dict:
    return {
        "IdMatch": match_id,
        "MatchNumber": match_number,
        "StageName": [{"Locale": "en-GB", "Description": "First Stage"}],
        "GroupName": [{"Locale": "en-GB", "Description": f"Group {group}"}],
        "PlaceHolderA": f"{group}1",
        "PlaceHolderB": f"{group}2",
        "Home": _team(*home),
        "Away": _team(*away),
        "Stadium": {"IdCountry": stadium_country},
    }


def test_normalize_worldcup_groups_uses_draw_positions_and_fifa_ranks(tmp_path) -> None:
    points = tmp_path / "fifa_points.parquet"
    write_rows_parquet(
        [
            {
                "team": "Mexico",
                "fifa_points": 1600.0,
                "ranking_date": "2022-12-22",
                "fifa_rank": 15,
            },
            {
                "team": "South Korea",
                "fifa_points": 1500.0,
                "ranking_date": "2022-12-22",
                "fifa_rank": 25,
            },
        ],
        points,
    )
    payload = {
        "Results": [
            _match("1", 1, "A", ("Mexico", "MEX"), ("Korea Republic", "KOR"), "MEX")
        ]
    }

    rows = normalize_worldcup_groups(payload, points)

    assert rows == [
        {"group": "A", "team": "Mexico", "position": 1, "fifa_rank": 15},
        {"group": "A", "team": "South Korea", "position": 2, "fifa_rank": 25},
    ]


def test_normalize_worldcup_schedule_sets_host_team_only_for_real_host_country() -> None:
    payload = {
        "Results": [
            _match("1", 2, "E", ("Germany", "GER"), ("Côte d'Ivoire", "CIV"), "USA"),
            _match("2", 1, "A", ("Mexico", "MEX"), ("South Africa", "RSA"), "MEX"),
        ]
    }

    rows = normalize_worldcup_schedule(payload)

    assert rows == [
        {
            "match_id": "2",
            "group": "A",
            "team_a": "Mexico",
            "team_b": "South Africa",
            "match_number": 1,
            "host_team": "Mexico",
            "neutral_site": False,
        },
        {
            "match_id": "1",
            "group": "E",
            "team_a": "Germany",
            "team_b": "Ivory Coast",
            "match_number": 2,
            "host_team": None,
            "neutral_site": True,
        },
    ]


def test_write_worldcup_structure_outputs_creates_interim_tables(tmp_path) -> None:
    matches = tmp_path / "matches.json"
    points = tmp_path / "fifa_points.parquet"
    output = tmp_path / "interim"
    matches.write_text(
        json.dumps(
            {
                "Results": [
                    _match("1", 1, "A", ("Mexico", "MEX"), ("South Africa", "RSA"), "MEX")
                ]
            }
        ),
        encoding="utf-8",
    )
    write_rows_parquet(
        [
            {
                "team": "Mexico",
                "fifa_points": 1600.0,
                "ranking_date": "2022-12-22",
                "fifa_rank": 15,
            },
            {
                "team": "South Africa",
                "fifa_points": 1400.0,
                "ranking_date": "2022-12-22",
                "fifa_rank": 66,
            },
        ],
        points,
    )

    written = write_worldcup_structure_outputs(matches, points, output)

    assert {path.name for path in written} == {
        "worldcup_groups.parquet",
        "worldcup_schedule.parquet",
    }
    assert read_parquet(output / "worldcup_groups.parquet").height == 2
    assert read_parquet(output / "worldcup_schedule.parquet").height == 1
