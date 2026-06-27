from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from tactical_oracle.attack_defense import expected_goals_from_components, split_attack_defense
from tactical_oracle.data.io import read_parquet, write_rows_parquet
from tactical_oracle.simulation import (
    MatchResult,
    annex_c_assignments,
    best_third_placed,
    build_annex_c_table,
    rank_group,
    simulate_knockout_match,
)

DEFAULT_KNOCKOUT_SOURCE = Path("data/raw/fifa_worldcup_2026_matches.json")
STAGE_COLUMNS = (
    "qualify_r32",
    "reach_r16",
    "reach_qf",
    "reach_sf",
    "reach_final",
    "champion",
)


def _rows(path: str | Path) -> list[dict[str, Any]]:
    return read_parquet(path).to_dicts()


def _stage_name(value: Any) -> str:
    if isinstance(value, list) and value:
        first = value[0]
        if isinstance(first, dict):
            return str(first.get("Description", ""))
    return str(value or "")


def load_knockout_template(path: str | Path = DEFAULT_KNOCKOUT_SOURCE) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    matches: list[dict[str, Any]] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            if "MatchNumber" in value and int(value["MatchNumber"]) >= 73:
                matches.append(
                    {
                        "match_number": int(value["MatchNumber"]),
                        "stage": _stage_name(value.get("StageName")),
                        "placeholder_a": str(value.get("PlaceHolderA")),
                        "placeholder_b": str(value.get("PlaceHolderB")),
                    }
                )
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(payload)
    if not matches:
        raise ValueError(f"no knockout matches found in {path}")
    return sorted(matches, key=lambda row: int(row["match_number"]))


def completed_match_numbers(match_stats_rows: list[dict[str, Any]]) -> set[int]:
    return {int(row["match_number"]) for row in match_stats_rows}


def known_results(
    schedule_rows: list[dict[str, Any]],
    match_stats_rows: list[dict[str, Any]],
) -> list[MatchResult]:
    stats_by_team = {
        (int(row["match_number"]), str(row["team"])): row for row in match_stats_rows
    }
    results: list[MatchResult] = []
    for fixture in schedule_rows:
        match_number = int(fixture["match_number"])
        team_a = str(fixture["team_a"])
        team_b = str(fixture["team_b"])
        row = stats_by_team.get((match_number, team_a))
        if row is None:
            continue
        results.append(
            MatchResult(
                team_a=team_a,
                team_b=team_b,
                goals_a=int(row["goals"]),
                goals_b=int(row["goals_against"]),
                group=str(fixture["group"]),
            )
        )
    return results


def simulated_group_results(
    schedule_rows: list[dict[str, Any]],
    probability_rows: list[dict[str, Any]],
    completed_matches: set[int],
    rng: np.random.Generator,
) -> list[MatchResult]:
    probabilities = {int(row["match_number"]): row for row in probability_rows}
    results: list[MatchResult] = []
    for fixture in schedule_rows:
        match_number = int(fixture["match_number"])
        if match_number in completed_matches:
            continue
        row = probabilities[match_number]
        results.append(
            MatchResult(
                team_a=str(fixture["team_a"]),
                team_b=str(fixture["team_b"]),
                goals_a=int(rng.poisson(float(row["lambda_a"]))),
                goals_b=int(rng.poisson(float(row["lambda_b"]))),
                group=str(fixture["group"]),
            )
        )
    return results


def teams_by_group(group_rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    groups: dict[str, list[tuple[int, str]]] = {}
    for row in group_rows:
        groups.setdefault(str(row["group"]), []).append((int(row["position"]), str(row["team"])))
    return {
        group: [team for _, team in sorted(values)]
        for group, values in sorted(groups.items())
    }


def fifa_ranks(group_rows: list[dict[str, Any]]) -> dict[str, int]:
    return {str(row["team"]): int(row["fifa_rank"]) for row in group_rows}


def rank_all_groups(
    group_rows: list[dict[str, Any]],
    results: list[MatchResult],
) -> dict[str, Any]:
    groups = teams_by_group(group_rows)
    ranks = fifa_ranks(group_rows)
    return {
        group: rank_group(group, teams, results, fifa_ranks=ranks)
        for group, teams in groups.items()
    }


def group_slot_map(group_rankings: dict[str, Any], qualified_thirds: list[Any]) -> dict[str, str]:
    slots: dict[str, str] = {}
    for group, standings in group_rankings.items():
        for index, standing in enumerate(standings[:3], start=1):
            slots[f"{index}{group}"] = standing.team
    qualified_third_groups = {standing.group for standing in qualified_thirds}
    return {
        slot: team
        for slot, team in slots.items()
        if not slot.startswith("3") or slot[1] in qualified_third_groups
    }


def resolve_round_of_32_placeholder(
    placeholder: str,
    opposite_placeholder: str,
    slot_map: dict[str, str],
    third_assignments: dict[str, str],
) -> str:
    if placeholder.startswith("3") and len(placeholder) > 2:
        assigned = third_assignments[opposite_placeholder]
        if assigned[1] not in placeholder[1:]:
            raise ValueError(f"Annex C assignment {assigned} not valid for {placeholder}")
        placeholder = assigned
    return slot_map[placeholder]


def _resolve_knockout_placeholder(
    placeholder: str,
    opposite_placeholder: str,
    slot_map: dict[str, str],
    third_assignments: dict[str, str],
    winners: dict[int, str],
    runners_up: dict[int, str],
) -> str:
    if placeholder.startswith("W"):
        return winners[int(placeholder[1:])]
    if placeholder.startswith("RU"):
        return runners_up[int(placeholder[2:])]
    return resolve_round_of_32_placeholder(
        placeholder,
        opposite_placeholder,
        slot_map,
        third_assignments,
    )


def components_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        str(row["team"]): split_attack_defense(
            str(row["team"]),
            float(row["tsi"]),
            float(row["profile"]),
        )
        for row in rows
    }


def build_next_match_rows(
    schedule_rows: list[dict[str, Any]],
    probability_rows: list[dict[str, Any]],
    match_stats_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    done = completed_match_numbers(match_stats_rows)
    schedule_by_match = {int(row["match_number"]): row for row in schedule_rows}
    output: list[dict[str, Any]] = []
    for row in sorted(probability_rows, key=lambda item: int(item["match_number"])):
        match_number = int(row["match_number"])
        if match_number in done:
            continue
        fixture = schedule_by_match[match_number]
        output.append(
            {
                "match_id": row["match_id"],
                "match_number": match_number,
                "group": row["group"],
                "team_a": row["team_a"],
                "team_b": row["team_b"],
                "team_a_match_tsi_penalty": row.get("team_a_match_tsi_penalty", 0.0),
                "team_b_match_tsi_penalty": row.get("team_b_match_tsi_penalty", 0.0),
                "lambda_a": row["lambda_a"],
                "lambda_b": row["lambda_b"],
                "p_win_a": row["p_win_a"],
                "p_draw": row["p_draw"],
                "p_win_b": row["p_win_b"],
                "expected_points_a": row["expected_points_a"],
                "expected_points_b": row["expected_points_b"],
                "most_likely_score": (
                    f"{row['most_likely_goals_a']}-{row['most_likely_goals_b']}"
                ),
                "host_team": fixture.get("host_team"),
                "neutral_site": fixture.get("neutral_site", True),
            }
        )
    return output


def current_group_standing_rows(
    group_rows: list[dict[str, Any]],
    schedule_rows: list[dict[str, Any]],
    match_stats_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rankings = rank_all_groups(group_rows, known_results(schedule_rows, match_stats_rows))
    rows: list[dict[str, Any]] = []
    for group, standings in rankings.items():
        for position, standing in enumerate(standings, start=1):
            rows.append(
                {
                    "group": group,
                    "position": position,
                    "team": standing.team,
                    "played": standing.played,
                    "points": standing.points,
                    "goals_for": standing.goals_for,
                    "goals_against": standing.goals_against,
                    "goal_difference": standing.goal_difference,
                }
            )
    return rows


def _empty_team_state(team: str, group: str) -> dict[str, Any]:
    return {
        "team": team,
        "group": group,
        "points_sum": 0.0,
        "goal_difference_sum": 0.0,
        "goals_for_sum": 0.0,
        "goals_against_sum": 0.0,
        "top2_count": 0,
        "best_third_count": 0,
        "qualify_r32_count": 0,
        "position_counts": {1: 0, 2: 0, 3: 0, 4: 0},
        "stage_counts": dict.fromkeys(STAGE_COLUMNS, 0),
    }


def _increment_stage(team_states: dict[str, dict[str, Any]], team: str, stage: str) -> None:
    team_states[team]["stage_counts"][stage] += 1


def _simulate_knockout(
    group_rankings: dict[str, Any],
    qualified_thirds: list[Any],
    annex_table: dict[str, Any],
    components: dict[str, Any],
    knockout_template: list[dict[str, Any]],
    rng: np.random.Generator,
    team_states: dict[str, dict[str, Any]],
    match_team_counts: dict[tuple[int, str], dict[str, int]],
) -> None:
    third_groups = "".join(sorted(standing.group for standing in qualified_thirds))
    third_assignments = annex_c_assignments(third_groups, annex_table)
    slot_map = group_slot_map(group_rankings, qualified_thirds)
    winners: dict[int, str] = {}
    runners_up: dict[int, str] = {}

    for fixture in knockout_template:
        match_number = int(fixture["match_number"])
        placeholder_a = str(fixture["placeholder_a"])
        placeholder_b = str(fixture["placeholder_b"])
        team_a = _resolve_knockout_placeholder(
            placeholder_a,
            placeholder_b,
            slot_map,
            third_assignments,
            winners,
            runners_up,
        )
        team_b = _resolve_knockout_placeholder(
            placeholder_b,
            placeholder_a,
            slot_map,
            third_assignments,
            winners,
            runners_up,
        )
        component_a = components[team_a]
        component_b = components[team_b]
        lambda_a, lambda_b = expected_goals_from_components(component_a, component_b)
        result = simulate_knockout_match(
            team_a,
            team_b,
            lambda_a,
            lambda_b,
            component_a.tsi,
            component_b.tsi,
            rng=rng,
        )
        winner = result.winner
        loser = team_b if winner == team_a else team_a
        winners[match_number] = winner
        runners_up[match_number] = loser
        for team in (team_a, team_b):
            key = (match_number, team)
            match_team_counts.setdefault(key, {"appearances": 0, "wins": 0})
            match_team_counts[key]["appearances"] += 1
        match_team_counts[(match_number, winner)]["wins"] += 1

        stage = str(fixture["stage"])
        if stage == "Round of 32":
            _increment_stage(team_states, winner, "reach_r16")
        elif stage == "Round of 16":
            _increment_stage(team_states, winner, "reach_qf")
        elif stage == "Quarter-final":
            _increment_stage(team_states, winner, "reach_sf")
        elif stage == "Semi-final":
            _increment_stage(team_states, winner, "reach_final")
        elif stage == "Final":
            _increment_stage(team_states, winner, "champion")


def tournament_projection_outputs(
    group_rows: list[dict[str, Any]],
    schedule_rows: list[dict[str, Any]],
    match_stats_rows: list[dict[str, Any]],
    probability_rows: list[dict[str, Any]],
    annex_rows: list[dict[str, Any]],
    component_rows: list[dict[str, Any]],
    knockout_template: list[dict[str, Any]],
    simulations: int = 20_000,
    seed: int = 2026,
) -> dict[str, list[dict[str, Any]]]:
    if simulations <= 0:
        raise ValueError("simulations must be positive")

    rng = np.random.default_rng(seed)
    known = known_results(schedule_rows, match_stats_rows)
    completed = completed_match_numbers(match_stats_rows)
    annex_table = build_annex_c_table(annex_rows)
    components = components_from_rows(component_rows)
    team_states = {
        str(row["team"]): _empty_team_state(str(row["team"]), str(row["group"]))
        for row in group_rows
    }
    match_team_counts: dict[tuple[int, str], dict[str, int]] = {}

    for _ in range(simulations):
        simulated = simulated_group_results(schedule_rows, probability_rows, completed, rng)
        results = [*known, *simulated]
        rankings = rank_all_groups(group_rows, results)
        thirds = best_third_placed(rankings, count=8, fifa_ranks=fifa_ranks(group_rows))
        qualified = {standing.team for standing in thirds}

        for standings in rankings.values():
            for position, standing in enumerate(standings, start=1):
                state = team_states[standing.team]
                state["points_sum"] += standing.points
                state["goal_difference_sum"] += standing.goal_difference
                state["goals_for_sum"] += standing.goals_for
                state["goals_against_sum"] += standing.goals_against
                state["position_counts"][position] += 1
                if position <= 2:
                    state["top2_count"] += 1
                    qualified.add(standing.team)
                if position == 3 and standing.team in qualified:
                    state["best_third_count"] += 1

        for team in qualified:
            state = team_states[team]
            state["qualify_r32_count"] += 1
            state["stage_counts"]["qualify_r32"] += 1

        _simulate_knockout(
            rankings,
            thirds,
            annex_table,
            components,
            knockout_template,
            rng,
            team_states,
            match_team_counts,
        )

    group_projection = []
    stage_probabilities = []
    for team, state in sorted(team_states.items(), key=lambda item: (item[1]["group"], item[0])):
        row = {
            "team": team,
            "group": state["group"],
            "avg_points": state["points_sum"] / simulations,
            "avg_goal_difference": state["goal_difference_sum"] / simulations,
            "avg_goals_for": state["goals_for_sum"] / simulations,
            "avg_goals_against": state["goals_against_sum"] / simulations,
            "prob_group_1": state["position_counts"][1] / simulations,
            "prob_group_2": state["position_counts"][2] / simulations,
            "prob_group_3": state["position_counts"][3] / simulations,
            "prob_group_4": state["position_counts"][4] / simulations,
            "prob_top2": state["top2_count"] / simulations,
            "prob_best_third": state["best_third_count"] / simulations,
            "prob_qualify": state["qualify_r32_count"] / simulations,
            "prob_eliminated_group": 1.0 - (state["qualify_r32_count"] / simulations),
        }
        group_projection.append(row)
        stage_probabilities.append(
            {
                "team": team,
                **{
                    column: state["stage_counts"][column] / simulations
                    for column in STAGE_COLUMNS
                },
            }
        )

    knockout_stage_by_match = {
        int(row["match_number"]): str(row["stage"]) for row in knockout_template
    }
    knockout_match_probabilities = []
    for (match_number, team), counts in sorted(match_team_counts.items()):
        knockout_match_probabilities.append(
            {
                "match_number": match_number,
                "stage": knockout_stage_by_match[match_number],
                "team": team,
                "appear_probability": counts["appearances"] / simulations,
                "win_probability": counts["wins"] / simulations,
                "conditional_win_probability": counts["wins"] / counts["appearances"]
                if counts["appearances"]
                else 0.0,
            }
        )

    return {
        "current_group_standings.parquet": current_group_standing_rows(
            group_rows,
            schedule_rows,
            match_stats_rows,
        ),
        "next_matches.parquet": build_next_match_rows(
            schedule_rows,
            probability_rows,
            match_stats_rows,
        ),
        "group_projection.parquet": group_projection,
        "team_stage_probabilities.parquet": sorted(
            stage_probabilities,
            key=lambda row: row["champion"],
            reverse=True,
        ),
        "knockout_match_probabilities.parquet": knockout_match_probabilities,
    }


def write_tournament_projection_outputs(
    interim_dir: str | Path = "data/interim",
    processed_dir: str | Path = "data/processed",
    simulations: int = 20_000,
    seed: int = 2026,
    knockout_source: str | Path = DEFAULT_KNOCKOUT_SOURCE,
) -> list[Path]:
    interim = Path(interim_dir)
    processed = Path(processed_dir)
    outputs = tournament_projection_outputs(
        group_rows=_rows(interim / "worldcup_groups.parquet"),
        schedule_rows=_rows(interim / "worldcup_schedule.parquet"),
        match_stats_rows=_rows(interim / "worldcup_match_stats.parquet"),
        probability_rows=_rows(processed / "match_probabilities_post_groups.parquet"),
        annex_rows=_rows(interim / "worldcup_annex_c.parquet"),
        component_rows=_rows(processed / "attack_defense_post_groups.parquet"),
        knockout_template=load_knockout_template(knockout_source),
        simulations=simulations,
        seed=seed,
    )
    written: list[Path] = []
    for filename, rows in outputs.items():
        destination = processed / filename
        write_rows_parquet(rows, destination)
        written.append(destination)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Project remaining World Cup paths.")
    parser.add_argument("--interim-dir", default="data/interim")
    parser.add_argument("--processed-dir", default="data/processed")
    parser.add_argument("--simulations", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--knockout-source", default=str(DEFAULT_KNOCKOUT_SOURCE))
    args = parser.parse_args()

    for path in write_tournament_projection_outputs(
        interim_dir=args.interim_dir,
        processed_dir=args.processed_dir,
        simulations=args.simulations,
        seed=args.seed,
        knockout_source=args.knockout_source,
    ):
        print(path)


if __name__ == "__main__":
    main()
