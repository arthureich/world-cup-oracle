from __future__ import annotations

from collections.abc import Mapping

from tactical_oracle.config import TSIParameters
from tactical_oracle.utils import clamp


def squad_adjustment(
    tsi_base: float,
    squad_implied_tsi: float,
    shrinkage: float = 0.35,
    params: TSIParameters = TSIParameters(),
) -> float:
    """B5 capped structural squad adjustment."""

    raw = shrinkage * (squad_implied_tsi - tsi_base)
    return clamp(raw, -params.squad_adjustment_cap, params.squad_adjustment_cap)


def squad_adjustments(
    tsi_base_by_team: Mapping[str, float],
    squad_implied_tsi_by_team: Mapping[str, float],
    shrinkage: float = 0.35,
    params: TSIParameters = TSIParameters(),
) -> dict[str, float]:
    return {
        team: squad_adjustment(tsi_base, squad_implied_tsi_by_team[team], shrinkage, params)
        for team, tsi_base in tsi_base_by_team.items()
        if team in squad_implied_tsi_by_team
    }
