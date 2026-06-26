from __future__ import annotations

import pytest

from tactical_oracle.attack_defense import build_components
from tactical_oracle.data.io import read_parquet, write_rows_parquet
from tactical_oracle.pipeline.real_outputs import (
    average_opponent_elo,
    cycle_goal_rates,
    filter_matches_to_fifa_teams,
    real_match_probability_rows,
    schedule_strength_adjustments,
    write_post_group_match_probability_outputs,
    write_real_core_outputs,
    write_real_elo_outputs,
    write_real_match_probability_outputs,
)


def test_filter_matches_to_fifa_teams_drops_non_fifa_opponents() -> None:
    matches = [
        {"team_a": "Brazil", "team_b": "Argentina"},
        {"team_a": "Brazil", "team_b": "Basque Country"},
    ]

    filtered = filter_matches_to_fifa_teams(matches, {"Brazil", "Argentina"})

    assert filtered == [{"team_a": "Brazil", "team_b": "Argentina"}]


def test_cycle_goal_rates_counts_both_match_sides() -> None:
    goals_for, goals_against = cycle_goal_rates(
        [
            {"team_a": "A", "team_b": "B", "goals_a": 2, "goals_b": 1},
            {"team_a": "B", "team_b": "A", "goals_a": 3, "goals_b": 3},
        ]
    )

    assert goals_for == {"A": 2.5, "B": 2.0}
    assert goals_against == {"A": 2.0, "B": 2.5}


def test_schedule_strength_adjustments_reward_stronger_average_opponents() -> None:
    matches = [
        {"team_a": "Contender", "team_b": "Elite"},
        {"team_a": "SoftPath", "team_b": "Weak"},
        {"team_a": "Elite", "team_b": "SoftPath"},
    ]
    adjusted_elo = {
        "Contender": 1750.0,
        "Elite": 1800.0,
        "SoftPath": 1750.0,
        "Weak": 1300.0,
    }
    tsi_base = {
        "Contender": 13.5,
        "Elite": 14.0,
        "SoftPath": 13.5,
        "Weak": 7.0,
    }

    avg_opponents = average_opponent_elo(matches, adjusted_elo)
    adjustments = schedule_strength_adjustments(matches, adjusted_elo, tsi_base)

    assert avg_opponents["Contender"] == 1800.0
    assert avg_opponents["SoftPath"] == 1550.0
    assert adjustments["Contender"] > 0
    assert adjustments["SoftPath"] < 0


def test_write_real_elo_outputs_uses_interim_real_inputs(tmp_path) -> None:
    interim = tmp_path / "interim"
    processed = tmp_path / "processed"
    write_rows_parquet(
        [
            {
                "team": "Brazil",
                "fifa_points": 1840.77,
                "ranking_date": "2022-12-22",
                "fifa_rank": 1,
            },
            {
                "team": "Argentina",
                "fifa_points": 1838.38,
                "ranking_date": "2022-12-22",
                "fifa_rank": 2,
            },
        ],
        interim / "fifa_points.parquet",
    )
    write_rows_parquet(
        [
            {
                "match_id": "m1",
                "date": "2023-01-01",
                "team_a": "Brazil",
                "team_b": "Argentina",
                "goals_a": 1,
                "goals_b": 0,
                "competition": "Friendly",
                "stage": "single",
                "match_type": "friendly",
                "home_team": "Brazil",
                "neutral_site": False,
                "went_to_penalties": False,
                "penalty_winner": None,
            }
        ],
        interim / "matches_cycle.parquet",
    )

    written = write_real_elo_outputs(interim, processed)

    assert [path.name for path in written] == ["ratings_elo.parquet"]
    ratings = read_parquet(processed / "ratings_elo.parquet")
    assert set(ratings["team"].to_list()) == {"Brazil", "Argentina"}


def test_write_real_core_outputs_creates_tsi_and_attack_defense(tmp_path) -> None:
    interim = tmp_path / "interim"
    processed = tmp_path / "processed"
    write_rows_parquet(
        [
            {
                "team": "Brazil",
                "fifa_points": 1840.77,
                "ranking_date": "2022-12-22",
                "fifa_rank": 1,
            },
            {
                "team": "Argentina",
                "fifa_points": 1838.38,
                "ranking_date": "2022-12-22",
                "fifa_rank": 2,
            },
            {
                "team": "France",
                "fifa_points": 1823.39,
                "ranking_date": "2022-12-22",
                "fifa_rank": 3,
            },
        ],
        interim / "fifa_points.parquet",
    )
    write_rows_parquet(
        [
            {
                "match_id": "m1",
                "date": "2023-01-01",
                "team_a": "Brazil",
                "team_b": "Argentina",
                "goals_a": 4,
                "goals_b": 3,
                "competition": "Friendly",
                "stage": "single",
                "match_type": "friendly",
                "home_team": "Brazil",
                "neutral_site": False,
                "went_to_penalties": False,
                "penalty_winner": None,
            },
            {
                "match_id": "m2",
                "date": "2023-01-02",
                "team_a": "France",
                "team_b": "Argentina",
                "goals_a": 1,
                "goals_b": 0,
                "competition": "Friendly",
                "stage": "single",
                "match_type": "friendly",
                "home_team": "France",
                "neutral_site": False,
                "went_to_penalties": False,
                "penalty_winner": None,
            },
        ],
        interim / "matches_cycle.parquet",
    )
    squad_rows = []
    for team, base_value in {
        "Brazil": 90_000_000,
        "Argentina": 45_000_000,
        "France": 20_000_000,
    }.items():
        for index, sector in enumerate(("GOL", "DEF", "MEI", "ATA"), start=1):
            squad_rows.append(
                {
                    "player_id": f"{team}-{sector}",
                    "player_name": f"{team} {sector}",
                    "team": team,
                    "age": 25 + index,
                    "sector": sector,
                    "market_value": base_value,
                    "recent_minutes_factor": 1.0,
                    "club_level": 1.0,
                    "league_level": 1.0,
                    "status": 1.0,
                    "called_up": True,
                }
            )
    write_rows_parquet(squad_rows, interim / "squads.parquet")
    write_rows_parquet(
        [
            {"team": "Brazil", "american_odd": 850},
            {"team": "Argentina", "american_odd": 1000},
            {"team": "France", "american_odd": 460},
        ],
        interim / "odds_long_term.parquet",
    )

    written = write_real_core_outputs(interim, processed)

    names = {path.name for path in written}
    assert names == {
        "ratings_elo.parquet",
        "squad_adjustments.parquet",
        "odds_adjustments.parquet",
        "tsi_pre_cup.parquet",
        "attack_defense_pre_cup.parquet",
    }
    tsi = read_parquet(processed / "tsi_pre_cup.parquet")
    assert tsi.height == 3
    assert tsi["tsi_pre"].max() < 20.0
    assert tsi["squad_adjustment"].max() > 0.0
    assert tsi["odds_adjustment"].abs().max() > 0.0
    odds_adjustments = read_parquet(processed / "odds_adjustments.parquet")
    assert odds_adjustments.height == 3
    squad_adjustments = read_parquet(processed / "squad_adjustments.parquet")
    assert squad_adjustments.height == 3
    assert squad_adjustments["squad_adjustment"].max() > 0.0
    assert read_parquet(processed / "attack_defense_pre_cup.parquet").height == 3


def test_write_real_match_probability_outputs_creates_group_fixture_probabilities(
    tmp_path,
) -> None:
    interim = tmp_path / "interim"
    processed = tmp_path / "processed"
    write_rows_parquet(
        [
            {
                "team": "Brazil",
                "fifa_points": 1840.77,
                "ranking_date": "2022-12-22",
                "fifa_rank": 1,
            },
            {
                "team": "Argentina",
                "fifa_points": 1838.38,
                "ranking_date": "2022-12-22",
                "fifa_rank": 2,
            },
            {
                "team": "France",
                "fifa_points": 1823.39,
                "ranking_date": "2022-12-22",
                "fifa_rank": 3,
            },
        ],
        interim / "fifa_points.parquet",
    )
    write_rows_parquet(
        [
            {
                "match_id": "m1",
                "date": "2023-01-01",
                "team_a": "Brazil",
                "team_b": "Argentina",
                "goals_a": 4,
                "goals_b": 3,
                "competition": "Friendly",
                "stage": "single",
                "match_type": "friendly",
                "home_team": "Brazil",
                "neutral_site": False,
                "went_to_penalties": False,
                "penalty_winner": None,
            },
            {
                "match_id": "m2",
                "date": "2023-01-02",
                "team_a": "France",
                "team_b": "Argentina",
                "goals_a": 1,
                "goals_b": 0,
                "competition": "Friendly",
                "stage": "single",
                "match_type": "friendly",
                "home_team": "France",
                "neutral_site": False,
                "went_to_penalties": False,
                "penalty_winner": None,
            },
        ],
        interim / "matches_cycle.parquet",
    )
    write_rows_parquet(
        [
            {
                "match_id": "wc-1",
                "group": "C",
                "team_a": "Brazil",
                "team_b": "Argentina",
                "match_number": 7,
                "host_team": None,
                "neutral_site": True,
            }
        ],
        interim / "worldcup_schedule.parquet",
    )

    written = write_real_match_probability_outputs(interim, processed)

    assert [path.name for path in written] == ["match_probabilities.parquet"]
    probabilities = read_parquet(processed / "match_probabilities.parquet")
    row = probabilities.row(0, named=True)
    assert row["match_number"] == 7
    assert row["team_a"] == "Brazil"
    assert row["team_b"] == "Argentina"
    assert row["p_win_a"] + row["p_draw"] + row["p_win_b"] == pytest.approx(1.0)
    assert row["team_a_guaranteed_first"] is False
    assert row["team_a_rotated"] is False


def test_real_match_probability_rows_applies_manual_match_strength_flags() -> None:
    components = build_components(
        {"Brazil": 14.0, "Argentina": 14.0},
        {"Brazil": 0.0, "Argentina": 0.0},
    )
    base_fixture = {
        "match_id": "wc-1",
        "group": "C",
        "team_a": "Brazil",
        "team_b": "Argentina",
        "match_number": 7,
        "host_team": None,
        "neutral_site": True,
    }

    baseline = real_match_probability_rows([base_fixture], components)[0]
    adjusted = real_match_probability_rows(
        [
            {
                **base_fixture,
                "team_a_guaranteed_first": True,
                "team_a_rotated": True,
            }
        ],
        components,
    )[0]

    assert adjusted["team_a_guaranteed_first"] is True
    assert adjusted["team_a_rotated"] is True
    assert adjusted["team_a_match_tsi_penalty"] == pytest.approx(1.60)
    assert adjusted["team_b_match_tsi_penalty"] == pytest.approx(0.0)
    assert adjusted["lambda_a"] < baseline["lambda_a"]
    assert adjusted["lambda_b"] > baseline["lambda_b"]
    assert adjusted["p_win_a"] < baseline["p_win_a"]


def test_write_post_group_match_probability_outputs_uses_tsi_post_groups(tmp_path) -> None:
    interim = tmp_path / "interim"
    processed = tmp_path / "processed"
    write_rows_parquet(
        [
            {
                "match_id": "ko-1",
                "group": "R32",
                "team_a": "Brazil",
                "team_b": "Argentina",
                "match_number": 73,
                "host_team": None,
                "neutral_site": True,
            }
        ],
        interim / "worldcup_knockout_schedule.parquet",
    )
    write_rows_parquet(
        [
            {"team": "Brazil", "tsi": 12.0, "profile": 0.0, "attack": 12.0, "defense": 12.0},
            {
                "team": "Argentina",
                "tsi": 14.0,
                "profile": 0.0,
                "attack": 14.0,
                "defense": 14.0,
            },
        ],
        processed / "attack_defense_pre_cup.parquet",
    )
    write_rows_parquet(
        [
            {
                "team": "Brazil",
                "matches_played": 3,
                "total_match_weight": 3.0,
                "performance_adjustment": 6.0,
                "tsi_pre": 12.0,
                "performance_group_tsi": 18.0,
                "post_groups_tsi_delta": 1.8,
                "tsi_post_groups": 13.8,
            },
            {
                "team": "Argentina",
                "matches_played": 3,
                "total_match_weight": 3.0,
                "performance_adjustment": -6.0,
                "tsi_pre": 14.0,
                "performance_group_tsi": 8.0,
                "post_groups_tsi_delta": -1.8,
                "tsi_post_groups": 12.2,
            },
        ],
        processed / "team_performance_adjustments.parquet",
    )

    written = write_post_group_match_probability_outputs(
        interim,
        processed,
        schedule_file="worldcup_knockout_schedule.parquet",
    )

    assert [path.name for path in written] == [
        "attack_defense_post_groups.parquet",
        "match_probabilities_post_groups.parquet",
    ]
    components = read_parquet(processed / "attack_defense_post_groups.parquet")
    brazil = components.filter(components["team"] == "Brazil").row(0, named=True)
    probabilities = read_parquet(processed / "match_probabilities_post_groups.parquet")
    row = probabilities.row(0, named=True)
    assert brazil["tsi"] == pytest.approx(13.8)
    assert row["match_number"] == 73
    assert row["p_win_a"] > row["p_win_b"]
