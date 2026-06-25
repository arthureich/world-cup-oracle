from __future__ import annotations

import math
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

from tactical_oracle.config import EloParameters
from tactical_oracle.data.schemas import FifaPoints, Match, parse_date
from tactical_oracle.utils import clamp, z_scores_by_key

DEFAULT_ELO_PARAMETERS = EloParameters()


@dataclass(frozen=True)
class MatchEloUpdate:
    match_id: str
    team_a: str
    team_b: str
    expected_a: float
    expected_b: float
    actual_a: float
    actual_b: float
    weight: float
    margin_multiplier: float
    delta_a: float
    delta_b: float


@dataclass(frozen=True)
class EloRating:
    team: str
    initial_elo: float
    base_elo: float
    recency_adjustment: float
    adjusted_elo: float


def _normalize_key(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return ascii_value.strip().lower().replace(" ", "_").replace("-", "_").replace("/", "_")


def importance_weight(match_type: str, params: EloParameters | None = None) -> float:
    params = params or DEFAULT_ELO_PARAMETERS
    key = _normalize_key(match_type)
    aliases = {
        "amistoso": "friendly",
        "friendly": "friendly",
        "nations_league": "nations_league",
        "similar": "nations_league",
        "qualifier": "qualifier",
        "qualifiers": "qualifier",
        "eliminatorias": "qualifier",
        "eliminatoria": "qualifier",
        "continental_group": "continental_group",
        "continental_grupos": "continental_group",
        "continental_mata_mata": "continental_knockout",
        "continental_knockout": "continental_knockout",
        "world_cup_group": "world_cup_group",
        "copa_do_mundo_grupos": "world_cup_group",
        "world_cup_knockout": "world_cup_knockout",
        "copa_do_mundo_mata_mata": "world_cup_knockout",
    }
    canonical = aliases.get(key, key)
    try:
        return params.importance_weights[canonical]
    except KeyError as exc:
        raise ValueError(f"unknown match_type: {match_type}") from exc


def _fifa_points_mapping(
    points: Mapping[str, float] | Iterable[FifaPoints | Mapping[str, Any]],
) -> dict[str, float]:
    if isinstance(points, Mapping):
        return {str(team): float(value) for team, value in points.items()}

    mapped: dict[str, float] = {}
    for row in points:
        if isinstance(row, FifaPoints):
            mapped[row.team] = float(row.fifa_points)
        else:
            mapped[str(row["team"])] = float(row["fifa_points"])
    return mapped


def initial_elo_from_fifa_points(
    points: Mapping[str, float] | Iterable[FifaPoints | Mapping[str, Any]],
    params: EloParameters | None = None,
) -> dict[str, float]:
    """Initialize Elo from FIFA points with z-score over the supplied FIFA universe."""

    params = params or DEFAULT_ELO_PARAMETERS
    fifa_points = _fifa_points_mapping(points)
    z_scores = z_scores_by_key(fifa_points)
    return {
        team: clamp(
            params.base_elo + params.fifa_z_factor * z,
            params.elo_min,
            params.elo_max,
        )
        for team, z in z_scores.items()
    }


def expected_result(
    elo_a: float,
    elo_b: float,
    home_advantage_a: float = 0.0,
    home_advantage_b: float = 0.0,
) -> float:
    """Expected result for team A in Elo space."""

    adjusted_a = elo_a + home_advantage_a
    adjusted_b = elo_b + home_advantage_b
    return 1.0 / (1.0 + 10.0 ** ((adjusted_b - adjusted_a) / 400.0))


def actual_result_for_team(
    match: Match,
    team: str,
    params: EloParameters | None = None,
) -> float:
    """Return 1/0.5/0, or 0.55/0.45 for shootouts."""

    params = params or DEFAULT_ELO_PARAMETERS
    if team not in {match.team_a, match.team_b}:
        raise ValueError(f"{team} did not play match {match.match_id}")

    goals_for = match.goals_a if team == match.team_a else match.goals_b
    goals_against = match.goals_b if team == match.team_a else match.goals_a

    if match.went_to_penalties and goals_for == goals_against:
        if match.penalty_winner == team:
            return params.penalty_win_score
        return params.penalty_loss_score
    if goals_for > goals_against:
        return 1.0
    if goals_for < goals_against:
        return 0.0
    return 0.5


def margin_multiplier(goal_difference: int, params: EloParameters | None = None) -> float:
    """Goal margin multiplier documented in B2."""

    params = params or DEFAULT_ELO_PARAMETERS
    if goal_difference <= 1:
        return 1.0
    x = float(goal_difference - 1)
    value = 1.0 + 0.4 * (1.0 - math.exp(-(0.277 * x + 0.006 * x**2.97)))
    return min(1.4, value)


def _home_advantage(match: Match, team: str, params: EloParameters) -> float:
    if match.neutral_site or match.home_team is None:
        return 0.0
    return params.home_elo if match.home_team == team else 0.0


def update_match(
    ratings: dict[str, float],
    match: Match,
    params: EloParameters | None = None,
) -> MatchEloUpdate:
    """Update mutable ratings in place for one match and return the update details."""

    params = params or DEFAULT_ELO_PARAMETERS
    ratings.setdefault(match.team_a, params.base_elo)
    ratings.setdefault(match.team_b, params.base_elo)

    elo_a = ratings[match.team_a]
    elo_b = ratings[match.team_b]
    expected_a = expected_result(
        elo_a,
        elo_b,
        home_advantage_a=_home_advantage(match, match.team_a, params),
        home_advantage_b=_home_advantage(match, match.team_b, params),
    )
    expected_b = 1.0 - expected_a
    actual_a = actual_result_for_team(match, match.team_a, params)
    actual_b = actual_result_for_team(match, match.team_b, params)
    weight = importance_weight(match.match_type, params)
    margin = margin_multiplier(abs(match.goals_a - match.goals_b), params)

    delta_a = params.k_factor * weight * margin * (actual_a - expected_a)
    delta_b = params.k_factor * weight * margin * (actual_b - expected_b)

    ratings[match.team_a] = elo_a + delta_a
    ratings[match.team_b] = elo_b + delta_b

    return MatchEloUpdate(
        match_id=match.match_id,
        team_a=match.team_a,
        team_b=match.team_b,
        expected_a=expected_a,
        expected_b=expected_b,
        actual_a=actual_a,
        actual_b=actual_b,
        weight=weight,
        margin_multiplier=margin,
        delta_a=delta_a,
        delta_b=delta_b,
    )


def months_before(reference: date, played_at: date) -> float:
    days = (reference - played_at).days
    return max(0.0, days / 30.4375)


def recency_weight(months_before_cup: float, params: EloParameters | None = None) -> float:
    params = params or DEFAULT_ELO_PARAMETERS
    return 0.5 ** (months_before_cup / params.recency_half_life_months)


def recency_adjustment(
    deltas: Iterable[tuple[float, date | str]],
    params: EloParameters | None = None,
) -> float:
    params = params or DEFAULT_ELO_PARAMETERS
    weighted_sum = 0.0
    weight_sum = 0.0
    for delta, played_at in deltas:
        months = months_before(params.tournament_start, parse_date(played_at))
        weight = recency_weight(months, params)
        weighted_sum += delta * weight
        weight_sum += weight

    if weight_sum == 0:
        return 0.0

    recent_mean = weighted_sum / weight_sum
    sample_factor = min(1.0, weight_sum / params.recency_sample_reference)
    adjustment = params.recency_multiplier * recent_mean * sample_factor
    return clamp(adjustment, -params.recency_cap, params.recency_cap)


def compute_elo_ratings(
    fifa_points: Mapping[str, float] | Iterable[FifaPoints | Mapping[str, Any]],
    matches: Iterable[Match | Mapping[str, Any]],
    params: EloParameters | None = None,
) -> dict[str, EloRating]:
    """Run the cycle Elo game by game and apply the final recency adjustment."""

    params = params or DEFAULT_ELO_PARAMETERS
    initial = initial_elo_from_fifa_points(fifa_points, params)
    ratings = dict(initial)
    deltas_by_team: dict[str, list[tuple[float, date]]] = {team: [] for team in initial}

    parsed_matches = [match if isinstance(match, Match) else Match(**match) for match in matches]
    for match in sorted(parsed_matches, key=lambda item: item.date):
        ratings.setdefault(match.team_a, params.base_elo)
        ratings.setdefault(match.team_b, params.base_elo)
        initial.setdefault(match.team_a, params.base_elo)
        initial.setdefault(match.team_b, params.base_elo)
        deltas_by_team.setdefault(match.team_a, [])
        deltas_by_team.setdefault(match.team_b, [])

        update = update_match(ratings, match, params)
        deltas_by_team[match.team_a].append((update.delta_a, match.date))
        deltas_by_team[match.team_b].append((update.delta_b, match.date))

    final: dict[str, EloRating] = {}
    for team, base_elo in ratings.items():
        adjustment = recency_adjustment(deltas_by_team.get(team, []), params)
        final[team] = EloRating(
            team=team,
            initial_elo=initial[team],
            base_elo=base_elo,
            recency_adjustment=adjustment,
            adjusted_elo=base_elo + adjustment,
        )
    return final


def elo_rows(ratings: Mapping[str, EloRating]) -> list[dict[str, float | str]]:
    return [
        {
            "team": rating.team,
            "initial_elo": rating.initial_elo,
            "base_elo": rating.base_elo,
            "recency_adjustment": rating.recency_adjustment,
            "adjusted_elo": rating.adjusted_elo,
        }
        for rating in ratings.values()
    ]
