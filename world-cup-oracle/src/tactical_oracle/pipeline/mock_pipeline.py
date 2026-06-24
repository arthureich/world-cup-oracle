from __future__ import annotations

import json
from typing import Any

from tactical_oracle.attack_defense import build_components, expected_goals_from_components
from tactical_oracle.data.mocks import fifa_points_mock, matches_cycle_mock, worldcup_schedule_mock
from tactical_oracle.elo import compute_elo_ratings
from tactical_oracle.simulation import match_probabilities
from tactical_oracle.tsi import build_tsi_ratings


def run_mock_pipeline() -> dict[str, Any]:
    elo = compute_elo_ratings(fifa_points_mock(), matches_cycle_mock())
    tsi = build_tsi_ratings(elo)
    components = build_components({team: rating.tsi_pre for team, rating in tsi.items()})

    match_rows: list[dict[str, Any]] = []
    for row in worldcup_schedule_mock():
        team_a = row["team_a"]
        team_b = row["team_b"]
        lambda_a, lambda_b = expected_goals_from_components(components[team_a], components[team_b])
        probabilities = match_probabilities(lambda_a, lambda_b)
        match_rows.append(
            {
                "match_id": row["match_id"],
                "team_a": team_a,
                "team_b": team_b,
                "lambda_a": lambda_a,
                "lambda_b": lambda_b,
                "p_win_a": probabilities.win_a,
                "p_draw": probabilities.draw,
                "p_win_b": probabilities.win_b,
                "most_likely_score": probabilities.most_likely_score,
            }
        )

    return {
        "elo": {team: rating.adjusted_elo for team, rating in elo.items()},
        "tsi_pre": {team: rating.tsi_pre for team, rating in tsi.items()},
        "matches": match_rows,
    }


def main() -> None:
    print(json.dumps(run_mock_pipeline(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
