from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from tactical_oracle.config import TSIParameters
from tactical_oracle.utils import clamp, standardize_to_reference, z_scores_by_key

DEFAULT_TSI_PARAMETERS = TSIParameters()


@dataclass(frozen=True)
class PlayerValue:
    player_id: str
    player_name: str
    team: str
    sector: str
    effective_value: float
    aggregated_value: float


SECTORS = ("GOL", "DEF", "MEI", "ATA")
SECTOR_POSITION_COUNTS = {"GOL": 1.0, "DEF": 4.0, "MEI": 3.0, "ATA": 3.0}

# Sector-balance penalty: only a *critical* sector (one well below the field, i.e.
# z below CRITICAL_SECTOR_Z) is punished, proportionally to its depth below the line.
# Ordinary unevenness above the line costs nothing, so total talent drives the score.
CRITICAL_SECTOR_Z = -0.75  # a sector this far below the 48-team average is "critical"
CRITICAL_SECTOR_PENALTY = 0.5  # score lost per std a critical sector sits below the line
AGE_FACTOR_START = 27.0
AGE_FACTOR_SPAN = 12.0
AGE_FACTOR_TARGET = 6.67
AGE_FACTOR_EXPONENT = 0.9
AGE_FACTOR_CAP = 7.0


def age_factor(age: float) -> float:
    if age <= 0:
        raise ValueError("age must be positive")
    if age <= AGE_FACTOR_START:
        return 1.0
    progress = ((age - AGE_FACTOR_START) / AGE_FACTOR_SPAN) ** AGE_FACTOR_EXPONENT
    return min(AGE_FACTOR_CAP, math.exp(math.log(AGE_FACTOR_TARGET) * progress))


def player_effective_value(market_value: float, age: float) -> float:
    """Player value = market value scaled by the documented age factor."""

    if market_value < 0:
        raise ValueError("market_value cannot be negative")
    return market_value * age_factor(age)


def player_value_from_row(row: Mapping[str, Any]) -> PlayerValue:
    effective = player_effective_value(
        market_value=float(row["market_value"]),
        age=float(row["age"]),
    )
    return PlayerValue(
        player_id=str(row.get("player_id", row["player_name"])),
        player_name=str(row["player_name"]),
        team=str(row["team"]),
        sector=str(row["sector"]),
        effective_value=effective,
        aggregated_value=math.log1p(effective),
    )


def sector_values(players: Iterable[PlayerValue]) -> dict[str, dict[str, float]]:
    values: dict[str, dict[str, float]] = {}
    for player in players:
        if player.sector not in SECTORS:
            raise ValueError(f"unknown sector: {player.sector}")
        values.setdefault(player.team, {sector: 0.0 for sector in SECTORS})
        values[player.team][player.sector] += player.aggregated_value
    return values


def squad_scores(
    sector_value_by_team: Mapping[str, Mapping[str, float]],
    critical_threshold: float = CRITICAL_SECTOR_Z,
    critical_penalty: float = CRITICAL_SECTOR_PENALTY,
) -> dict[str, float]:
    """Rank squads by position-weighted sector strength, docking critical holes.

    Sector z-scores are averaged with starting-shape weights:
    GOL=1, DEF=4, MEI=3, ATA=3. This keeps goalkeepers from carrying the same
    structural impact as multi-player outfield lines while still allowing a
    genuinely elite or weak goalkeeper group to matter.
    """

    teams = list(sector_value_by_team)
    sector_z: dict[str, dict[str, float]] = {team: {} for team in teams}
    for sector in SECTORS:
        raw = {team: float(sector_value_by_team[team].get(sector, 0.0)) for team in teams}
        standardized = z_scores_by_key(raw)
        for team, value in standardized.items():
            sector_z[team][sector] = value

    total_weight = sum(SECTOR_POSITION_COUNTS.values())
    scores: dict[str, float] = {}
    for team, values in sector_z.items():
        weighted_z = sum(values[sector] * SECTOR_POSITION_COUNTS[sector] for sector in SECTORS)
        weighted_mean = weighted_z / total_weight
        deficit = sum(
            max(0.0, -1.0 - values[sector])
            for sector in SECTORS
            if values[sector] < critical_threshold
        )
        scores[team] = weighted_mean - critical_penalty * deficit
    return scores


def squad_implied_tsi(
    squad_score_by_team: Mapping[str, float],
    tsi_base_by_team: Mapping[str, float],
) -> dict[str, float]:
    return standardize_to_reference(dict(squad_score_by_team), dict(tsi_base_by_team))


def squad_adjustments_from_players(
    rows: Iterable[Mapping[str, Any]],
    tsi_base_by_team: Mapping[str, float],
    shrinkage: float = 0.35,
    params: TSIParameters | None = None,
) -> dict[str, float]:
    rows = list(rows)
    players = [player_value_from_row(row) for row in rows if row.get("called_up", True)]
    sectors = sector_values(players)
    scores = squad_scores(sectors)
    implied = squad_implied_tsi(scores, tsi_base_by_team)
    return squad_adjustments(tsi_base_by_team, implied, shrinkage=shrinkage, params=params)


def squad_adjustment(
    tsi_base: float,
    squad_implied_tsi: float,
    shrinkage: float = 0.35,
    params: TSIParameters | None = None,
) -> float:
    """B5 capped structural squad adjustment."""

    params = params or DEFAULT_TSI_PARAMETERS
    raw = shrinkage * (squad_implied_tsi - tsi_base)
    return clamp(raw, -params.squad_adjustment_cap, params.squad_adjustment_cap)


def squad_adjustments(
    tsi_base_by_team: Mapping[str, float],
    squad_implied_tsi_by_team: Mapping[str, float],
    shrinkage: float = 0.35,
    params: TSIParameters | None = None,
) -> dict[str, float]:
    params = params or DEFAULT_TSI_PARAMETERS
    return {
        team: squad_adjustment(tsi_base, squad_implied_tsi_by_team[team], shrinkage, params)
        for team, tsi_base in tsi_base_by_team.items()
        if team in squad_implied_tsi_by_team
    }
