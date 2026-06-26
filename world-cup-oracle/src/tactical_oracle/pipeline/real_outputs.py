from __future__ import annotations

from pathlib import Path
from typing import Any

from tactical_oracle.attack_defense import (
    build_components,
    expected_goals_from_components,
    profile_from_goal_totals,
)
from tactical_oracle.config import TSIParameters
from tactical_oracle.data.io import read_parquet, write_rows_parquet
from tactical_oracle.elo import compute_elo_ratings, elo_rows
from tactical_oracle.odds import champion_market_adjustments_from_rows, odds_adjustment_rows
from tactical_oracle.simulation import match_probabilities
from tactical_oracle.squad import squad_adjustments_from_players
from tactical_oracle.tsi import TSIRating, map_elo_distribution_to_tsi, tsi_pre
from tactical_oracle.utils import clamp, mean

MIN_TRUSTED_SQUAD_PLAYERS = 22
MIN_TRUSTED_SQUAD_COVERAGE = 0.80


def _rows_from_parquet(path: Path) -> list[dict[str, Any]]:
    return read_parquet(path).to_dicts()


def fifa_team_names(fifa_points: list[dict[str, Any]]) -> set[str]:
    return {str(row["team"]) for row in fifa_points}


def filter_matches_to_fifa_teams(
    matches: list[dict[str, Any]],
    fifa_teams: set[str],
) -> list[dict[str, Any]]:
    return [
        match
        for match in matches
        if match["team_a"] in fifa_teams and match["team_b"] in fifa_teams
    ]


def cycle_goal_rates(matches: list[dict[str, Any]]) -> tuple[dict[str, float], dict[str, float]]:
    goals_for: dict[str, float] = {}
    goals_against: dict[str, float] = {}
    games: dict[str, int] = {}

    for match in matches:
        team_a = str(match["team_a"])
        team_b = str(match["team_b"])
        goals_a = float(match["goals_a"])
        goals_b = float(match["goals_b"])

        goals_for[team_a] = goals_for.get(team_a, 0.0) + goals_a
        goals_against[team_a] = goals_against.get(team_a, 0.0) + goals_b
        games[team_a] = games.get(team_a, 0) + 1

        goals_for[team_b] = goals_for.get(team_b, 0.0) + goals_b
        goals_against[team_b] = goals_against.get(team_b, 0.0) + goals_a
        games[team_b] = games.get(team_b, 0) + 1

    return (
        {team: goals_for[team] / games[team] for team in games},
        {team: goals_against[team] / games[team] for team in games},
    )


def tsi_rows(tsi_ratings: dict[str, Any]) -> list[dict[str, float | str]]:
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


def attack_defense_rows(components: dict[str, Any]) -> list[dict[str, float | str]]:
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


def squad_adjustment_rows(
    tsi_ratings: dict[str, Any],
    coverage_by_team: dict[str, dict[str, float | int]],
    eligible_teams: set[str],
) -> list[dict[str, bool | float | int | str]]:
    return [
        {
            "team": team,
            "called_up_count": int(coverage["called_up_count"]),
            "trusted_player_count": int(coverage["trusted_player_count"]),
            "trusted_coverage": float(coverage["trusted_coverage"]),
            "squad_adjustment_applied": team in eligible_teams,
            "squad_adjustment": tsi_ratings[team].squad_adjustment,
        }
        for team, coverage in sorted(coverage_by_team.items())
        if team in tsi_ratings
    ]


def average_opponent_elo(
    matches: list[dict[str, Any]],
    adjusted_elo_by_team: dict[str, float],
) -> dict[str, float]:
    totals: dict[str, float] = {}
    games: dict[str, int] = {}

    for match in matches:
        team_a = str(match["team_a"])
        team_b = str(match["team_b"])
        if team_a not in adjusted_elo_by_team or team_b not in adjusted_elo_by_team:
            continue
        totals[team_a] = totals.get(team_a, 0.0) + adjusted_elo_by_team[team_b]
        totals[team_b] = totals.get(team_b, 0.0) + adjusted_elo_by_team[team_a]
        games[team_a] = games.get(team_a, 0) + 1
        games[team_b] = games.get(team_b, 0) + 1

    return {team: totals[team] / games[team] for team in games}


def schedule_strength_adjustments(
    matches: list[dict[str, Any]],
    adjusted_elo_by_team: dict[str, float],
    tsi_base_by_team: dict[str, float],
    params: TSIParameters | None = None,
) -> dict[str, float]:
    params = params or TSIParameters()
    avg_opponents = average_opponent_elo(matches, adjusted_elo_by_team)
    if not avg_opponents:
        return {team: 0.0 for team in adjusted_elo_by_team}

    contender_opponents = [
        avg_opponents[team]
        for team in avg_opponents
        if tsi_base_by_team.get(team, 0.0) >= params.schedule_contender_tsi_floor
    ]
    baseline = mean(contender_opponents or list(avg_opponents.values()))

    return {
        team: clamp(
            ((avg_opponents.get(team, baseline) - baseline) / 100.0)
            * params.schedule_adjustment_per_100_elo,
            -params.schedule_adjustment_cap,
            params.schedule_adjustment_cap,
        )
        for team in adjusted_elo_by_team
    }


def build_real_tsi_ratings(
    elo_ratings: dict[str, Any],
    matches: list[dict[str, Any]] | None = None,
    squad_rows: list[dict[str, Any]] | None = None,
    odds_rows: list[dict[str, Any]] | None = None,
) -> dict[str, TSIRating]:
    adjusted_elo_by_team = {team: rating.adjusted_elo for team, rating in elo_ratings.items()}
    base_by_team = map_elo_distribution_to_tsi(adjusted_elo_by_team)
    schedule_adjustments = schedule_strength_adjustments(
        matches or [],
        adjusted_elo_by_team,
        base_by_team,
    )
    coverage_by_team = squad_coverage_by_team(squad_rows or [])
    eligible_teams = eligible_squad_teams(coverage_by_team)
    # Eligibility is gated on trusted coverage, but once a team qualifies we value
    # the WHOLE called-up squad: dropping an untrusted player would zero out a real
    # player (e.g. Casemiro, mismatched on Transfermarkt), which understates his
    # sector far worse than using his approximate value.
    eligible_squad_rows = [
        row
        for row in (squad_rows or [])
        if row.get("called_up", True) and row.get("team") in eligible_teams
    ]
    squad_reference = {
        team: base_by_team[team] + schedule_adjustments[team]
        for team in _squad_teams(eligible_squad_rows)
        if team in base_by_team
    }
    squad_adjustments = (
        squad_adjustments_from_players(
            [row for row in eligible_squad_rows if row.get("team") in squad_reference],
            squad_reference,
        )
        if squad_reference
        else {}
    )
    tsi_model_by_team = {
        team: base_by_team[team]
        + schedule_adjustments[team]
        + squad_adjustments.get(team, 0.0)
        for team in elo_ratings
    }
    odds_adjustments = (
        champion_market_adjustments_from_rows(tsi_model_by_team, odds_rows)
        if odds_rows
        else {}
    )

    return {
        team: TSIRating(
            team=team,
            elo_adjusted=rating.adjusted_elo,
            tsi_base=base_by_team[team],
            schedule_adjustment=schedule_adjustments[team],
            squad_adjustment=squad_adjustments.get(team, 0.0),
            tsi_model=tsi_model_by_team[team],
            odds_adjustment=odds_adjustments.get(team, 0.0),
            tsi_pre=tsi_pre(tsi_model_by_team[team], odds_adjustments.get(team, 0.0)),
        )
        for team, rating in elo_ratings.items()
    }


def _squad_teams(squad_rows: list[dict[str, Any]]) -> set[str]:
    return {str(row["team"]) for row in squad_rows if row.get("called_up", True)}


def trusted_squad_value_rows(squad_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in squad_rows
        if row.get("called_up", True) and row.get("market_value_trusted", True)
    ]


def squad_coverage_by_team(squad_rows: list[dict[str, Any]]) -> dict[str, dict[str, float | int]]:
    counts: dict[str, dict[str, int]] = {}
    for row in squad_rows:
        if not row.get("called_up", True):
            continue
        team = str(row["team"])
        counts.setdefault(team, {"called_up_count": 0, "trusted_player_count": 0})
        counts[team]["called_up_count"] += 1
        if row.get("market_value_trusted", True):
            counts[team]["trusted_player_count"] += 1

    return {
        team: {
            "called_up_count": values["called_up_count"],
            "trusted_player_count": values["trusted_player_count"],
            "trusted_coverage": values["trusted_player_count"] / values["called_up_count"]
            if values["called_up_count"]
            else 0.0,
        }
        for team, values in counts.items()
    }


def eligible_squad_teams(
    coverage_by_team: dict[str, dict[str, float | int]],
) -> set[str]:
    eligible: set[str] = set()
    for team, coverage in coverage_by_team.items():
        called_up_count = int(coverage["called_up_count"])
        trusted_player_count = int(coverage["trusted_player_count"])
        trusted_coverage = float(coverage["trusted_coverage"])
        required_players = min(MIN_TRUSTED_SQUAD_PLAYERS, called_up_count)
        if (
            trusted_player_count >= required_players
            and trusted_coverage >= MIN_TRUSTED_SQUAD_COVERAGE
        ):
            eligible.add(team)
    return eligible


def _optional_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return _rows_from_parquet(path)


def build_real_elo_outputs(
    interim_dir: str | Path = "data/interim",
) -> dict[str, list[dict[str, Any]]]:
    interim_path = Path(interim_dir)
    fifa_points = _rows_from_parquet(interim_path / "fifa_points.parquet")
    matches = _rows_from_parquet(interim_path / "matches_cycle.parquet")
    filtered_matches = filter_matches_to_fifa_teams(matches, fifa_team_names(fifa_points))
    elo = compute_elo_ratings(fifa_points, filtered_matches)
    return {"ratings_elo.parquet": elo_rows(elo)}


def build_real_core_outputs(
    interim_dir: str | Path = "data/interim",
) -> dict[str, list[dict[str, Any]]]:
    interim_path = Path(interim_dir)
    fifa_points = _rows_from_parquet(interim_path / "fifa_points.parquet")
    matches = _rows_from_parquet(interim_path / "matches_cycle.parquet")
    squad_rows = _optional_rows(interim_path / "squads.parquet")
    odds_rows = _optional_rows(interim_path / "odds_long_term.parquet")
    filtered_matches = filter_matches_to_fifa_teams(matches, fifa_team_names(fifa_points))

    elo = compute_elo_ratings(fifa_points, filtered_matches)
    tsi = build_real_tsi_ratings(
        elo,
        filtered_matches,
        squad_rows=squad_rows,
        odds_rows=odds_rows,
    )
    squad_coverage = squad_coverage_by_team(squad_rows)
    eligible_teams = eligible_squad_teams(squad_coverage)
    goals_for, goals_against = cycle_goal_rates(filtered_matches)
    profiles = profile_from_goal_totals(goals_for, goals_against)
    components = build_components({team: rating.tsi_pre for team, rating in tsi.items()}, profiles)

    return {
        "ratings_elo.parquet": elo_rows(elo),
        "squad_adjustments.parquet": squad_adjustment_rows(tsi, squad_coverage, eligible_teams),
        "odds_adjustments.parquet": odds_adjustment_rows(
            {team: rating.odds_adjustment for team, rating in tsi.items()}
        ),
        "tsi_pre_cup.parquet": tsi_rows(tsi),
        "attack_defense_pre_cup.parquet": attack_defense_rows(components),
    }


def _real_components_from_interim(interim_dir: str | Path) -> dict[str, Any]:
    interim_path = Path(interim_dir)
    fifa_points = _rows_from_parquet(interim_path / "fifa_points.parquet")
    matches = _rows_from_parquet(interim_path / "matches_cycle.parquet")
    squad_rows = _optional_rows(interim_path / "squads.parquet")
    odds_rows = _optional_rows(interim_path / "odds_long_term.parquet")
    filtered_matches = filter_matches_to_fifa_teams(matches, fifa_team_names(fifa_points))

    elo = compute_elo_ratings(fifa_points, filtered_matches)
    tsi = build_real_tsi_ratings(
        elo,
        filtered_matches,
        squad_rows=squad_rows,
        odds_rows=odds_rows,
    )
    goals_for, goals_against = cycle_goal_rates(filtered_matches)
    profiles = profile_from_goal_totals(goals_for, goals_against)
    return build_components({team: rating.tsi_pre for team, rating in tsi.items()}, profiles)


def real_match_probability_rows(
    schedule: list[dict[str, Any]],
    components: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    missing_teams: set[str] = set()

    for fixture in sorted(schedule, key=lambda row: int(row["match_number"])):
        team_a = str(fixture["team_a"])
        team_b = str(fixture["team_b"])
        if team_a not in components or team_b not in components:
            missing_teams.update(team for team in (team_a, team_b) if team not in components)
            continue

        host_team = fixture.get("host_team")
        lambda_a, lambda_b = expected_goals_from_components(
            components[team_a],
            components[team_b],
            a_is_host=host_team == team_a,
            b_is_host=host_team == team_b,
        )
        probabilities = match_probabilities(lambda_a, lambda_b)
        most_likely_a, most_likely_b = probabilities.most_likely_score
        rows.append(
            {
                "match_id": fixture["match_id"],
                "match_number": int(fixture["match_number"]),
                "group": fixture["group"],
                "team_a": team_a,
                "team_b": team_b,
                "host_team": host_team,
                "neutral_site": bool(fixture["neutral_site"]),
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

    if missing_teams:
        teams = ", ".join(sorted(missing_teams))
        raise ValueError(f"schedule contains teams without model components: {teams}")
    return rows


def post_group_components_from_rows(
    attack_defense_pre_rows: list[dict[str, Any]],
    team_performance_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    post_tsi_by_team = {
        str(row["team"]): float(row["tsi_post_groups"]) for row in team_performance_rows
    }
    profile_by_team = {
        str(row["team"]): float(row["profile"]) for row in attack_defense_pre_rows
    }
    tsi_by_team = {
        str(row["team"]): post_tsi_by_team.get(str(row["team"]), float(row["tsi"]))
        for row in attack_defense_pre_rows
    }
    return build_components(tsi_by_team, profile_by_team)


def build_post_group_match_probability_outputs(
    interim_dir: str | Path = "data/interim",
    processed_dir: str | Path = "data/processed",
    schedule_file: str | Path = "worldcup_schedule.parquet",
) -> dict[str, list[dict[str, Any]]]:
    interim_path = Path(interim_dir)
    processed_path = Path(processed_dir)
    schedule_path = Path(schedule_file)
    if not schedule_path.is_absolute():
        schedule_path = interim_path / schedule_path
    components = post_group_components_from_rows(
        _rows_from_parquet(processed_path / "attack_defense_pre_cup.parquet"),
        _rows_from_parquet(processed_path / "team_performance_adjustments.parquet"),
    )
    return {
        "attack_defense_post_groups.parquet": attack_defense_rows(components),
        "match_probabilities_post_groups.parquet": real_match_probability_rows(
            _rows_from_parquet(schedule_path),
            components,
        ),
    }


def build_real_match_probability_outputs(
    interim_dir: str | Path = "data/interim",
) -> dict[str, list[dict[str, Any]]]:
    interim_path = Path(interim_dir)
    schedule = _rows_from_parquet(interim_path / "worldcup_schedule.parquet")
    components = _real_components_from_interim(interim_path)
    return {"match_probabilities.parquet": real_match_probability_rows(schedule, components)}


def write_real_elo_outputs(
    interim_dir: str | Path = "data/interim",
    output_dir: str | Path = "data/processed",
) -> list[Path]:
    output_path = Path(output_dir)
    written: list[Path] = []
    for filename, rows in build_real_elo_outputs(interim_dir).items():
        destination = output_path / filename
        write_rows_parquet(rows, destination)
        written.append(destination)
    return written


def write_real_core_outputs(
    interim_dir: str | Path = "data/interim",
    output_dir: str | Path = "data/processed",
) -> list[Path]:
    output_path = Path(output_dir)
    written: list[Path] = []
    for filename, rows in build_real_core_outputs(interim_dir).items():
        destination = output_path / filename
        write_rows_parquet(rows, destination)
        written.append(destination)
    return written


def write_real_match_probability_outputs(
    interim_dir: str | Path = "data/interim",
    output_dir: str | Path = "data/processed",
) -> list[Path]:
    output_path = Path(output_dir)
    written: list[Path] = []
    for filename, rows in build_real_match_probability_outputs(interim_dir).items():
        destination = output_path / filename
        write_rows_parquet(rows, destination)
        written.append(destination)
    return written


def write_post_group_match_probability_outputs(
    interim_dir: str | Path = "data/interim",
    processed_dir: str | Path = "data/processed",
    schedule_file: str | Path = "worldcup_schedule.parquet",
) -> list[Path]:
    output_path = Path(processed_dir)
    written: list[Path] = []
    for filename, rows in build_post_group_match_probability_outputs(
        interim_dir,
        processed_dir,
        schedule_file,
    ).items():
        destination = output_path / filename
        write_rows_parquet(rows, destination)
        written.append(destination)
    return written


def main() -> None:
    for path in write_real_elo_outputs():
        print(path)


def core_main() -> None:
    for path in write_real_core_outputs():
        print(path)


def match_probabilities_main() -> None:
    for path in write_real_match_probability_outputs():
        print(path)


def post_group_match_probabilities_main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Build post-group attack/defense and match probabilities."
    )
    parser.add_argument("--interim-dir", default="data/interim")
    parser.add_argument("--processed-dir", default="data/processed")
    parser.add_argument(
        "--schedule-file",
        default="worldcup_schedule.parquet",
        help="Schedule parquet path or filename under --interim-dir.",
    )
    args = parser.parse_args()

    for path in write_post_group_match_probability_outputs(
        interim_dir=args.interim_dir,
        processed_dir=args.processed_dir,
        schedule_file=args.schedule_file,
    ):
        print(path)


if __name__ == "__main__":
    main()
