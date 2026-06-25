from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass

import numpy as np

from tactical_oracle.config import SimulationParameters
from tactical_oracle.utils import clamp

DEFAULT_SIMULATION_PARAMETERS = SimulationParameters()


@dataclass(frozen=True)
class MatchProbabilities:
    win_a: float
    draw: float
    win_b: float
    expected_points_a: float
    expected_points_b: float
    most_likely_score: tuple[int, int]
    most_likely_score_probability: float


@dataclass(frozen=True)
class MatchResult:
    team_a: str
    team_b: str
    goals_a: int
    goals_b: int
    group: str | None = None


@dataclass(frozen=True)
class GroupFixture:
    group: str
    team_a: str
    team_b: str


@dataclass(frozen=True)
class GroupStanding:
    team: str
    group: str
    played: int
    points: int
    goals_for: int
    goals_against: int
    goal_difference: int


@dataclass(frozen=True)
class KnockoutResult:
    team_a: str
    team_b: str
    winner: str
    goals_a_90: int
    goals_b_90: int
    goals_a_extra_time: int = 0
    goals_b_extra_time: int = 0
    decided_by_penalties: bool = False


def poisson_probabilities(lambda_goals: float, max_goals: int) -> list[float]:
    if lambda_goals < 0:
        raise ValueError("lambda_goals cannot be negative")
    if max_goals < 0:
        raise ValueError("max_goals cannot be negative")

    probabilities = [math.exp(-lambda_goals)]
    for goals in range(1, max_goals + 1):
        probabilities.append(probabilities[-1] * lambda_goals / goals)
    return probabilities


def match_probabilities(
    lambda_a: float,
    lambda_b: float,
    max_goals: int | None = None,
    params: SimulationParameters | None = None,
) -> MatchProbabilities:
    params = params or DEFAULT_SIMULATION_PARAMETERS
    max_goals = params.score_max_goals if max_goals is None else max_goals
    probs_a = poisson_probabilities(lambda_a, max_goals)
    probs_b = poisson_probabilities(lambda_b, max_goals)

    win_a = 0.0
    draw = 0.0
    win_b = 0.0
    best_score = (0, 0)
    best_probability = -1.0

    for goals_a, probability_a in enumerate(probs_a):
        for goals_b, probability_b in enumerate(probs_b):
            probability = probability_a * probability_b
            if goals_a > goals_b:
                win_a += probability
            elif goals_a == goals_b:
                draw += probability
            else:
                win_b += probability
            if probability > best_probability:
                best_probability = probability
                best_score = (goals_a, goals_b)

    return MatchProbabilities(
        win_a=win_a,
        draw=draw,
        win_b=win_b,
        expected_points_a=3.0 * win_a + draw,
        expected_points_b=3.0 * win_b + draw,
        most_likely_score=best_score,
        most_likely_score_probability=best_probability,
    )


def penalty_win_probability(
    tsi_a: float,
    tsi_b: float,
    params: SimulationParameters | None = None,
) -> float:
    params = params or DEFAULT_SIMULATION_PARAMETERS
    raw = 0.5 + params.penalty_strength_factor * (tsi_a - tsi_b)
    return clamp(raw, params.penalty_min, params.penalty_max)


def simulate_knockout_match(
    team_a: str,
    team_b: str,
    lambda_a: float,
    lambda_b: float,
    tsi_a: float,
    tsi_b: float,
    rng: np.random.Generator | None = None,
    params: SimulationParameters | None = None,
) -> KnockoutResult:
    params = params or DEFAULT_SIMULATION_PARAMETERS
    rng = rng or np.random.default_rng()
    goals_a_90 = int(rng.poisson(lambda_a))
    goals_b_90 = int(rng.poisson(lambda_b))

    if goals_a_90 > goals_b_90:
        return KnockoutResult(team_a, team_b, team_a, goals_a_90, goals_b_90)
    if goals_b_90 > goals_a_90:
        return KnockoutResult(team_a, team_b, team_b, goals_a_90, goals_b_90)

    extra_a = int(rng.poisson(lambda_a * params.extra_time_factor))
    extra_b = int(rng.poisson(lambda_b * params.extra_time_factor))
    if extra_a > extra_b:
        return KnockoutResult(team_a, team_b, team_a, goals_a_90, goals_b_90, extra_a, extra_b)
    if extra_b > extra_a:
        return KnockoutResult(team_a, team_b, team_b, goals_a_90, goals_b_90, extra_a, extra_b)

    p_a = penalty_win_probability(tsi_a, tsi_b, params)
    winner = team_a if float(rng.random()) < p_a else team_b
    return KnockoutResult(
        team_a,
        team_b,
        winner,
        goals_a_90,
        goals_b_90,
        extra_a,
        extra_b,
        decided_by_penalties=True,
    )


def monte_carlo_match(
    lambda_a: float,
    lambda_b: float,
    simulations: int = 50_000,
    seed: int | None = None,
) -> dict[str, float]:
    if simulations <= 0:
        raise ValueError("simulations must be positive")
    rng = np.random.default_rng(seed)
    goals_a = rng.poisson(lambda_a, simulations)
    goals_b = rng.poisson(lambda_b, simulations)
    return {
        "win_a": float(np.mean(goals_a > goals_b)),
        "draw": float(np.mean(goals_a == goals_b)),
        "win_b": float(np.mean(goals_a < goals_b)),
        "expected_points_a": float(np.mean(np.where(goals_a > goals_b, 3, goals_a == goals_b))),
        "expected_points_b": float(np.mean(np.where(goals_b > goals_a, 3, goals_a == goals_b))),
    }


def _empty_stats(team: str, group: str) -> GroupStanding:
    return GroupStanding(
        team=team,
        group=group,
        played=0,
        points=0,
        goals_for=0,
        goals_against=0,
        goal_difference=0,
    )


def _add_result(standing: GroupStanding, goals_for: int, goals_against: int) -> GroupStanding:
    if goals_for > goals_against:
        points = 3
    elif goals_for == goals_against:
        points = 1
    else:
        points = 0
    return GroupStanding(
        team=standing.team,
        group=standing.group,
        played=standing.played + 1,
        points=standing.points + points,
        goals_for=standing.goals_for + goals_for,
        goals_against=standing.goals_against + goals_against,
        goal_difference=standing.goal_difference + goals_for - goals_against,
    )


def _head_to_head_stats(
    teams: set[str],
    results: Iterable[MatchResult],
) -> dict[str, GroupStanding]:
    result_list = list(results)
    group = result_list[0].group if result_list else ""
    stats = {team: _empty_stats(team, group or "") for team in teams}
    for result in result_list:
        if result.team_a in teams and result.team_b in teams:
            stats[result.team_a] = _add_result(stats[result.team_a], result.goals_a, result.goals_b)
            stats[result.team_b] = _add_result(stats[result.team_b], result.goals_b, result.goals_a)
    return stats


def _standing_sort_key(
    standing: GroupStanding,
    h2h: Mapping[str, GroupStanding],
    fair_play_scores: Mapping[str, float],
    fifa_ranks: Mapping[str, int],
) -> tuple[int, int, int, int, int, float, int]:
    h2h_standing = h2h[standing.team]
    fifa_rank = fifa_ranks.get(standing.team, 999)
    return (
        h2h_standing.points,
        h2h_standing.goal_difference,
        h2h_standing.goals_for,
        standing.goal_difference,
        standing.goals_for,
        fair_play_scores.get(standing.team, 0.0),
        -fifa_rank,
    )


def rank_group(
    group: str,
    teams: Iterable[str],
    results: Iterable[MatchResult],
    fifa_ranks: Mapping[str, int] | None = None,
    fair_play_scores: Mapping[str, float] | None = None,
) -> list[GroupStanding]:
    """Rank a group with B7 criteria.

    fair_play_scores are expected as a positive score where higher is better. In the pre-Cup
    simulation this can be omitted, making FIFA ranking the residual tie-breaker.
    """

    fifa_ranks = fifa_ranks or {}
    fair_play_scores = fair_play_scores or {}
    team_list = list(teams)
    stats = {team: _empty_stats(team, group) for team in team_list}
    group_results = [result for result in results if result.group in {None, group}]

    for result in group_results:
        if result.team_a not in stats or result.team_b not in stats:
            continue
        stats[result.team_a] = _add_result(stats[result.team_a], result.goals_a, result.goals_b)
        stats[result.team_b] = _add_result(stats[result.team_b], result.goals_b, result.goals_a)

    point_groups: dict[int, list[GroupStanding]] = {}
    for standing in stats.values():
        point_groups.setdefault(standing.points, []).append(standing)

    ordered: list[GroupStanding] = []
    for points in sorted(point_groups, reverse=True):
        tied = point_groups[points]
        if len(tied) == 1:
            ordered.extend(tied)
            continue
        tied_teams = {standing.team for standing in tied}
        h2h = _head_to_head_stats(tied_teams, group_results)
        ordered.extend(
            sorted(
                tied,
                key=lambda standing: _standing_sort_key(
                    standing,
                    h2h,
                    fair_play_scores,
                    fifa_ranks,
                ),
                reverse=True,
            )
        )
    return ordered


def best_third_placed(
    group_rankings: Mapping[str, list[GroupStanding]],
    count: int = 8,
    fifa_ranks: Mapping[str, int] | None = None,
    fair_play_scores: Mapping[str, float] | None = None,
) -> list[GroupStanding]:
    fifa_ranks = fifa_ranks or {}
    fair_play_scores = fair_play_scores or {}
    thirds = [ranking[2] for ranking in group_rankings.values() if len(ranking) >= 3]
    return sorted(
        thirds,
        key=lambda standing: (
            standing.points,
            standing.goal_difference,
            standing.goals_for,
            fair_play_scores.get(standing.team, 0.0),
            -fifa_ranks.get(standing.team, 999),
        ),
        reverse=True,
    )[:count]


def simulate_group(
    group: str,
    fixtures: Iterable[GroupFixture],
    expected_goals_provider: Callable[[str, str], tuple[float, float]],
    seed: int | None = None,
    fifa_ranks: Mapping[str, int] | None = None,
) -> list[GroupStanding]:
    rng = np.random.default_rng(seed)
    results: list[MatchResult] = []
    teams: set[str] = set()
    for fixture in fixtures:
        if fixture.group != group:
            continue
        teams.update([fixture.team_a, fixture.team_b])
        lambda_a, lambda_b = expected_goals_provider(fixture.team_a, fixture.team_b)
        results.append(
            MatchResult(
                team_a=fixture.team_a,
                team_b=fixture.team_b,
                goals_a=int(rng.poisson(lambda_a)),
                goals_b=int(rng.poisson(lambda_b)),
                group=group,
            )
        )
    return rank_group(group, teams, results, fifa_ranks=fifa_ranks)
