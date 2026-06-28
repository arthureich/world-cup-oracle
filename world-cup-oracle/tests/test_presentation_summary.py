from __future__ import annotations

import polars as pl
import pytest

from tactical_oracle.presentation.summary import (
    available_teams,
    biggest_tsi_moves,
    decisive_next_matches,
    knockout_match_favorites,
    percent,
    signed,
    stage_leaders,
    team_snapshot,
    top_champion,
)


def test_format_helpers() -> None:
    assert percent(0.1234) == "12.3%"
    assert signed(-1.234) == "-1.23"


def test_top_champion_sorts_descending() -> None:
    frame = pl.DataFrame(
        [
            {"team": "A", "champion": 0.10},
            {"team": "B", "champion": 0.30},
            {"team": "C", "champion": 0.20},
        ]
    )

    rows = top_champion(frame, n=2).to_dicts()

    assert [row["team"] for row in rows] == ["B", "C"]


def test_stage_leaders_returns_top_team_for_each_stage() -> None:
    frame = pl.DataFrame(
        [
            {"team": "A", "reach_qf": 0.10, "champion": 0.30},
            {"team": "B", "reach_qf": 0.40, "champion": 0.20},
        ]
    )

    rows = stage_leaders(frame, stages=("reach_qf", "champion")).to_dicts()

    assert rows == [
        {
            "stage": "Quartas",
            "stage_column": "reach_qf",
            "team": "B",
            "probability": 0.40,
        },
        {
            "stage": "Titulo",
            "stage_column": "champion",
            "team": "A",
            "probability": 0.30,
        },
    ]


def test_knockout_match_favorites_uses_unconditional_pass_probability() -> None:
    frame = pl.DataFrame(
        [
            {
                "match_number": 73,
                "stage": "Round of 32",
                "team": "A",
                "appear_probability": 1.0,
                "win_probability": 0.45,
                "conditional_win_probability": 0.45,
            },
            {
                "match_number": 73,
                "stage": "Round of 32",
                "team": "B",
                "appear_probability": 1.0,
                "win_probability": 0.55,
                "conditional_win_probability": 0.55,
            },
            {
                "match_number": 97,
                "stage": "Final",
                "team": "C",
                "appear_probability": 0.2,
                "win_probability": 0.12,
                "conditional_win_probability": 0.60,
            },
        ]
    )

    rows = knockout_match_favorites(frame).to_dicts()

    assert rows[0]["most_likely_to_pass"] == "B"
    assert rows[0]["next_best_team"] == "A"
    assert rows[1]["most_likely_to_pass"] == "C"


def test_biggest_tsi_moves_uses_absolute_delta() -> None:
    frame = pl.DataFrame(
        [
            {"team": "A", "post_groups_tsi_delta": 0.2},
            {"team": "B", "post_groups_tsi_delta": -1.1},
            {"team": "C", "post_groups_tsi_delta": 0.9},
        ]
    )

    rows = biggest_tsi_moves(frame, n=2).to_dicts()

    assert [row["team"] for row in rows] == ["B", "C"]


def test_decisive_next_matches_returns_balanced_matches() -> None:
    frame = pl.DataFrame(
        [
            {"match_number": 1, "p_win_a": 0.70, "p_win_b": 0.10},
            {"match_number": 2, "p_win_a": 0.35, "p_win_b": 0.34},
            {"match_number": 3, "p_win_a": 0.40, "p_win_b": 0.42},
        ]
    )

    rows = decisive_next_matches(frame, n=2).to_dicts()

    assert [row["match_number"] for row in rows] == [2, 3]


def test_team_snapshot_combines_outputs() -> None:
    stage = pl.DataFrame([{"team": "Brazil", "champion": 0.1, "reach_final": 0.2}])
    group = pl.DataFrame([{"team": "Brazil", "group": "C", "prob_qualify": 0.95}])
    performance = pl.DataFrame(
        [
            {
                "team": "Brazil",
                "tsi_pre": 14.0,
                "tsi_post_groups": 15.0,
                "post_groups_tsi_delta": 1.0,
            }
        ]
    )

    snapshot = team_snapshot("Brazil", stage, group, performance)

    assert snapshot["group"] == "C"
    assert snapshot["tsi_post_groups"] == 15.0
    assert available_teams(stage) == ["Brazil"]


def test_team_snapshot_rejects_unknown_team() -> None:
    empty = pl.DataFrame({"team": ["Brazil"]})

    with pytest.raises(ValueError):
        team_snapshot("France", empty, empty, empty)
