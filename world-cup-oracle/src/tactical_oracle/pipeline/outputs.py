from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from tactical_oracle.attack_defense import build_components, expected_goals_from_components
from tactical_oracle.data.io import write_rows_parquet
from tactical_oracle.data.mocks import (
    fifa_points_mock,
    matches_cycle_mock,
    odds_long_term_mock,
    squads_mock,
    worldcup_schedule_mock,
)
from tactical_oracle.elo import compute_elo_ratings, elo_rows
from tactical_oracle.odds import long_term_market_adjustments_from_rows, odds_adjustment_rows
from tactical_oracle.simulation import match_probabilities
from tactical_oracle.squad import squad_adjustments_from_players
from tactical_oracle.tsi import build_tsi_ratings, map_elo_to_tsi


def tsi_rows(tsi_ratings: Mapping[str, Any]) -> list[dict[str, float | str]]:
    return [
        {
            "team": rating.team,
            "elo_adjusted": rating.elo_adjusted,
            "tsi_base": rating.tsi_base,
            "schedule_adjustment": rating.schedule_adjustment,
            "squad_adjustment": rating.squad_adjustment,
            "tsi_model": rating.tsi_model,
            "odds_adjustment": rating.odds_adjustment,
            "tsi_pre": rating.tsi_pre,
        }
        for rating in sorted(tsi_ratings.values(), key=lambda row: row.tsi_pre, reverse=True)
    ]


def attack_defense_rows(components: Mapping[str, Any]) -> list[dict[str, float | str]]:
    return [
        {
            "team": component.team,
            "tsi": component.tsi,
            "profile": component.profile,
            "attack": component.attack,
            "defense": component.defense,
        }
        for component in sorted(components.values(), key=lambda row: row.tsi, reverse=True)
    ]


def build_mock_outputs() -> dict[str, list[dict[str, Any]]]:
    elo = compute_elo_ratings(fifa_points_mock(), matches_cycle_mock())
    tsi_base = {team: map_elo_to_tsi(rating.adjusted_elo) for team, rating in elo.items()}
    squad_adjustments = squad_adjustments_from_players(squads_mock(), tsi_base)
    tsi_without_odds = build_tsi_ratings(elo, squad_adjustments=squad_adjustments)
    tsi_model = {team: rating.tsi_model for team, rating in tsi_without_odds.items()}
    odds_adjustments = long_term_market_adjustments_from_rows(tsi_model, odds_long_term_mock())
    tsi = build_tsi_ratings(
        elo,
        squad_adjustments=squad_adjustments,
        odds_adjustments=odds_adjustments,
    )
    components = build_components({team: rating.tsi_pre for team, rating in tsi.items()})

    match_rows: list[dict[str, Any]] = []
    for row in worldcup_schedule_mock():
        team_a = row["team_a"]
        team_b = row["team_b"]
        host_team = row.get("host_team")
        lambda_a, lambda_b = expected_goals_from_components(
            components[team_a],
            components[team_b],
            a_is_host=host_team == team_a,
            b_is_host=host_team == team_b,
        )
        probabilities = match_probabilities(lambda_a, lambda_b)
        most_likely_a, most_likely_b = probabilities.most_likely_score
        match_rows.append(
            {
                "match_id": row["match_id"],
                "group": row["group"],
                "team_a": team_a,
                "team_b": team_b,
                "lambda_a": lambda_a,
                "lambda_b": lambda_b,
                "p_win_a": probabilities.win_a,
                "p_draw": probabilities.draw,
                "p_win_b": probabilities.win_b,
                "expected_points_a": probabilities.expected_points_a,
                "expected_points_b": probabilities.expected_points_b,
                "most_likely_goals_a": most_likely_a,
                "most_likely_goals_b": most_likely_b,
                "most_likely_score_probability": probabilities.most_likely_score_probability,
            }
        )

    return {
        "ratings_elo.parquet": elo_rows(elo),
        "squad_adjustments.parquet": [
            {"team": team, "squad_adjustment": adjustment}
            for team, adjustment in sorted(squad_adjustments.items())
        ],
        "odds_adjustments.parquet": odds_adjustment_rows(odds_adjustments),
        "tsi_pre_cup.parquet": tsi_rows(tsi),
        "attack_defense_pre_cup.parquet": attack_defense_rows(components),
        "match_probabilities.parquet": match_rows,
    }


def write_mock_outputs(base_dir: str | Path = "data/processed") -> list[Path]:
    base_path = Path(base_dir)
    written: list[Path] = []
    for filename, rows in build_mock_outputs().items():
        destination = base_path / filename
        write_rows_parquet(rows, destination)
        written.append(destination)
    return written


def main() -> None:
    for path in write_mock_outputs():
        print(path)


if __name__ == "__main__":
    main()
