from __future__ import annotations

from world_cup_oracle.pipeline.tournament_projection import (
    build_next_match_rows,
    current_group_standing_rows,
    resolve_round_of_32_placeholder,
)


def test_build_next_match_rows_filters_completed_matches() -> None:
    schedule = [
        {
            "match_id": "m1",
            "match_number": 1,
            "group": "A",
            "team_a": "A1",
            "team_b": "A2",
            "host_team": None,
            "neutral_site": True,
        },
        {
            "match_id": "m2",
            "match_number": 2,
            "group": "A",
            "team_a": "A3",
            "team_b": "A4",
            "host_team": None,
            "neutral_site": True,
        },
    ]
    probabilities = [
        {
            "match_id": "m1",
            "match_number": 1,
            "group": "A",
            "team_a": "A1",
            "team_b": "A2",
            "lambda_a": 1.0,
            "lambda_b": 1.0,
            "p_win_a": 0.35,
            "p_draw": 0.30,
            "p_win_b": 0.35,
            "expected_points_a": 1.35,
            "expected_points_b": 1.35,
            "most_likely_goals_a": 1,
            "most_likely_goals_b": 1,
        },
        {
            "match_id": "m2",
            "match_number": 2,
            "group": "A",
            "team_a": "A3",
            "team_b": "A4",
            "lambda_a": 1.5,
            "lambda_b": 0.8,
            "p_win_a": 0.50,
            "p_draw": 0.25,
            "p_win_b": 0.25,
            "expected_points_a": 1.75,
            "expected_points_b": 1.00,
            "most_likely_goals_a": 1,
            "most_likely_goals_b": 0,
        },
    ]
    stats = [
        {
            "match_number": 1,
            "team": "A1",
            "goals": 2,
            "goals_against": 0,
        }
    ]

    rows = build_next_match_rows(schedule, probabilities, stats)

    assert len(rows) == 1
    assert rows[0]["match_number"] == 2
    assert rows[0]["most_likely_score"] == "1-0"


def test_current_group_standing_rows_uses_known_results() -> None:
    groups = [
        {"group": "A", "position": 1, "team": "A1", "fifa_rank": 1},
        {"group": "A", "position": 2, "team": "A2", "fifa_rank": 2},
        {"group": "A", "position": 3, "team": "A3", "fifa_rank": 3},
        {"group": "A", "position": 4, "team": "A4", "fifa_rank": 4},
    ]
    schedule = [
        {
            "match_number": 1,
            "group": "A",
            "team_a": "A1",
            "team_b": "A2",
        }
    ]
    stats = [{"match_number": 1, "team": "A1", "goals": 2, "goals_against": 0}]

    rows = current_group_standing_rows(groups, schedule, stats)

    assert rows[0]["team"] == "A1"
    assert rows[0]["points"] == 3
    assert rows[-1]["team"] == "A2"


def test_resolve_round_of_32_placeholder_uses_annex_c_assignment() -> None:
    slot_map = {"1A": "Winner A", "3E": "Third E"}
    assignments = {"1A": "3E"}

    team = resolve_round_of_32_placeholder("3CEFHI", "1A", slot_map, assignments)

    assert team == "Third E"
