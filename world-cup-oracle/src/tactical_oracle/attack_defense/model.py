from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

from tactical_oracle.config import AttackDefenseParameters
from tactical_oracle.utils import clamp, mean, population_std


@dataclass(frozen=True)
class StrengthComponents:
    team: str
    tsi: float
    profile: float
    attack: float
    defense: float


def split_attack_defense(team: str, tsi: float, profile: float) -> StrengthComponents:
    attack = tsi + profile
    defense = tsi - profile
    return StrengthComponents(team=team, tsi=tsi, profile=profile, attack=attack, defense=defense)


def reverse_components(attack: float, defense: float) -> tuple[float, float]:
    tsi = (attack + defense) / 2.0
    profile = (attack - defense) / 2.0
    return tsi, profile


def profile_from_goal_totals(
    goals_for_per_game: Mapping[str, float],
    goals_against_per_game: Mapping[str, float],
    params: AttackDefenseParameters = AttackDefenseParameters(),
) -> dict[str, float]:
    if set(goals_for_per_game) != set(goals_against_per_game):
        raise ValueError("goals_for_per_game and goals_against_per_game must have the same teams")

    totals = {
        team: goals_for_per_game[team] + goals_against_per_game[team]
        for team in goals_for_per_game
    }
    values = list(totals.values())
    avg = mean(values)
    std = population_std(values)
    if std == 0:
        return {team: 0.0 for team in totals}
    return {
        team: clamp(params.profile_multiplier * ((total - avg) / std), -params.profile_cap, params.profile_cap)
        for team, total in totals.items()
    }


def build_components(
    tsi_by_team: Mapping[str, float],
    profile_by_team: Mapping[str, float] | None = None,
) -> dict[str, StrengthComponents]:
    profile_by_team = profile_by_team or {}
    return {
        team: split_attack_defense(team, tsi, profile_by_team.get(team, 0.0))
        for team, tsi in tsi_by_team.items()
    }


def expected_goals(
    attack_a: float,
    defense_a: float,
    attack_b: float,
    defense_b: float,
    a_is_host: bool = False,
    b_is_host: bool = False,
    params: AttackDefenseParameters = AttackDefenseParameters(),
) -> tuple[float, float]:
    if a_is_host and b_is_host:
        raise ValueError("only one team can receive host adjustment")

    host_a = params.host_gamma if a_is_host else 0.0
    host_b = params.host_gamma if b_is_host else 0.0
    opp_a = params.opponent_delta if b_is_host else 0.0
    opp_b = params.opponent_delta if a_is_host else 0.0

    lambda_a = params.base_goals * math.exp(params.k * (attack_a - defense_b) + host_a - opp_a)
    lambda_b = params.base_goals * math.exp(params.k * (attack_b - defense_a) + host_b - opp_b)
    return lambda_a, lambda_b


def expected_goals_from_components(
    team_a: StrengthComponents,
    team_b: StrengthComponents,
    a_is_host: bool = False,
    b_is_host: bool = False,
    params: AttackDefenseParameters = AttackDefenseParameters(),
) -> tuple[float, float]:
    return expected_goals(
        team_a.attack,
        team_a.defense,
        team_b.attack,
        team_b.defense,
        a_is_host=a_is_host,
        b_is_host=b_is_host,
        params=params,
    )
