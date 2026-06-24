from __future__ import annotations

import math
from collections.abc import Mapping

from tactical_oracle.config import TSIParameters
from tactical_oracle.utils import clamp, safe_logit, standardize_to_reference


def devig_binary(odd_yes: float, odd_no: float) -> float:
    if odd_yes <= 1.0 or odd_no <= 1.0:
        raise ValueError("decimal odds must be greater than 1")
    raw_yes = 1.0 / odd_yes
    raw_no = 1.0 / odd_no
    return raw_yes / (raw_yes + raw_no)


def devig_three_way(odd_a: float, odd_draw: float, odd_b: float) -> tuple[float, float, float]:
    if min(odd_a, odd_draw, odd_b) <= 1.0:
        raise ValueError("decimal odds must be greater than 1")
    raw = [1.0 / odd_a, 1.0 / odd_draw, 1.0 / odd_b]
    total = sum(raw)
    return raw[0] / total, raw[1] / total, raw[2] / total


def _champion_probabilities(champion_odds: Mapping[str, float]) -> dict[str, float]:
    raw = {team: 1.0 / odd for team, odd in champion_odds.items()}
    total = sum(raw.values())
    if total <= 0:
        raise ValueError("champion odds must have positive implied mass")
    return {team: value / total for team, value in raw.items()}


def long_term_market_adjustments(
    tsi_model_by_team: Mapping[str, float],
    pass_odds_by_team: Mapping[str, tuple[float, float]],
    champion_odds_by_team: Mapping[str, float],
    champion_weight: float = 0.35,
    champion_probability_floor: float = 1e-6,
    params: TSIParameters = TSIParameters(),
) -> dict[str, float]:
    """B6 light market adjustment from long-term markets."""

    teams = set(tsi_model_by_team)
    if not teams <= set(pass_odds_by_team) or not teams <= set(champion_odds_by_team):
        raise ValueError("all TSI teams must have pass and champion odds")

    champion_probs = _champion_probabilities(champion_odds_by_team)
    pass_strength = {
        team: safe_logit(devig_binary(*pass_odds_by_team[team]))
        for team in teams
    }
    champion_strength = {
        team: math.log(max(champion_probs[team], champion_probability_floor))
        for team in teams
    }
    market_strength = {
        team: (1.0 - champion_weight) * pass_strength[team]
        + champion_weight * champion_strength[team]
        for team in teams
    }
    tsi_market = standardize_to_reference(market_strength, dict(tsi_model_by_team))
    return {
        team: clamp(
            tsi_market[team] - tsi_model_by_team[team],
            -params.odds_adjustment_cap,
            params.odds_adjustment_cap,
        )
        for team in teams
    }
