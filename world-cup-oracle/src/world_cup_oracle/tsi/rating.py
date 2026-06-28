from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from world_cup_oracle.config import EloParameters, TSIParameters
from world_cup_oracle.elo import EloRating
from world_cup_oracle.utils import clamp, mean, population_std

DEFAULT_ELO_PARAMETERS = EloParameters()
DEFAULT_TSI_PARAMETERS = TSIParameters()


@dataclass(frozen=True)
class TSIRating:
    team: str
    elo_adjusted: float
    tsi_base: float
    schedule_adjustment: float
    squad_adjustment: float
    tsi_model: float
    odds_adjustment: float
    tsi_pre: float


def map_elo_to_tsi(
    elo_adjusted: float,
    elo_params: EloParameters | None = None,
    tsi_params: TSIParameters | None = None,
) -> float:
    """Linear MVP mapping from adjusted Elo into the 0-20 TSI scale."""

    elo_params = elo_params or DEFAULT_ELO_PARAMETERS
    tsi_params = tsi_params or DEFAULT_TSI_PARAMETERS
    span = elo_params.elo_max - elo_params.elo_min
    if span <= 0:
        raise ValueError("Elo max must be greater than Elo min")
    raw = (elo_adjusted - elo_params.elo_min) / span
    return clamp(
        tsi_params.tsi_min + raw * (tsi_params.tsi_max - tsi_params.tsi_min),
        tsi_params.tsi_min,
        tsi_params.tsi_max,
    )


def map_elo_distribution_to_tsi(
    elo_by_team: Mapping[str, float],
    center: float = 10.0,
    z_scale: float = 2.25,
    tsi_params: TSIParameters | None = None,
) -> dict[str, float]:
    """Map a real Elo cohort to TSI without saturating the top of the scale."""

    tsi_params = tsi_params or DEFAULT_TSI_PARAMETERS
    values = list(elo_by_team.values())
    avg = mean(values)
    std = population_std(values)
    if std == 0:
        return {
            team: clamp(center, tsi_params.tsi_min, tsi_params.tsi_max)
            for team in elo_by_team
        }
    return {
        team: clamp(
            center + z_scale * ((elo - avg) / std),
            tsi_params.tsi_min,
            tsi_params.tsi_max,
        )
        for team, elo in elo_by_team.items()
    }


def tsi_model(
    tsi_base: float,
    squad_adjustment: float = 0.0,
    params: TSIParameters | None = None,
) -> float:
    params = params or DEFAULT_TSI_PARAMETERS
    adjustment = clamp(squad_adjustment, -params.squad_adjustment_cap, params.squad_adjustment_cap)
    return clamp(tsi_base + adjustment, params.tsi_min, params.tsi_max)


def tsi_pre(
    tsi_model_value: float,
    odds_adjustment: float = 0.0,
    params: TSIParameters | None = None,
) -> float:
    params = params or DEFAULT_TSI_PARAMETERS
    adjustment = clamp(odds_adjustment, -params.odds_adjustment_cap, params.odds_adjustment_cap)
    return clamp(tsi_model_value + adjustment, params.tsi_min, params.tsi_max)


def tsi_post_groups(
    tsi_pre_value: float,
    performance_adjustment: float,
    params: TSIParameters | None = None,
) -> float:
    params = params or DEFAULT_TSI_PARAMETERS
    delta = params.post_groups_weight * performance_adjustment
    capped_delta = clamp(delta, -params.post_groups_delta_cap, params.post_groups_delta_cap)
    return clamp(tsi_pre_value + capped_delta, params.tsi_min, params.tsi_max)


def build_tsi_ratings(
    elo_ratings: Mapping[str, EloRating],
    schedule_adjustments: Mapping[str, float] | None = None,
    squad_adjustments: Mapping[str, float] | None = None,
    odds_adjustments: Mapping[str, float] | None = None,
    elo_params: EloParameters | None = None,
    tsi_params: TSIParameters | None = None,
) -> dict[str, TSIRating]:
    elo_params = elo_params or DEFAULT_ELO_PARAMETERS
    tsi_params = tsi_params or DEFAULT_TSI_PARAMETERS
    schedule_adjustments = schedule_adjustments or {}
    squad_adjustments = squad_adjustments or {}
    odds_adjustments = odds_adjustments or {}

    output: dict[str, TSIRating] = {}
    for team, elo in elo_ratings.items():
        base = map_elo_to_tsi(elo.adjusted_elo, elo_params, tsi_params)
        schedule = schedule_adjustments.get(team, 0.0)
        squad = clamp(
            squad_adjustments.get(team, 0.0),
            -tsi_params.squad_adjustment_cap,
            tsi_params.squad_adjustment_cap,
        )
        model = tsi_model(base + schedule, squad, tsi_params)
        odds = clamp(
            odds_adjustments.get(team, 0.0),
            -tsi_params.odds_adjustment_cap,
            tsi_params.odds_adjustment_cap,
        )
        pre = tsi_pre(model, odds, tsi_params)
        output[team] = TSIRating(
            team=team,
            elo_adjusted=elo.adjusted_elo,
            tsi_base=base,
            schedule_adjustment=schedule,
            squad_adjustment=squad,
            tsi_model=model,
            odds_adjustment=odds,
            tsi_pre=pre,
        )
    return output
