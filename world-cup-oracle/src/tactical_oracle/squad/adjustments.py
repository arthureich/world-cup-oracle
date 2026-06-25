from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
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

# Sector-balance penalty: only a *critical* sector (one well below the field, i.e.
# z below CRITICAL_SECTOR_Z) is punished, proportionally to its depth below the line.
# Ordinary unevenness above the line costs nothing, so total talent drives the score.
CRITICAL_SECTOR_Z = -1.0  # a sector this far below the 48-team average is "critical"
CRITICAL_SECTOR_PENALTY = 0.5  # score lost per std a critical sector sits below the line

# Collective (squad-level) experience uplift: the squad's total value is scaled by a
# multiplier that grows with the squad's mean age, compensating the Transfermarkt
# resale discount on veteran-heavy squads. Applied uniformly within a team, so it
# does not change the sector-balance comparison.
SQUAD_AGE_NEUTRAL_AGE = 26.0  # mean squad age at/below which there is no uplift
SQUAD_AGE_FULL_AGE = 31.0  # mean squad age at/above which the uplift maxes out
SQUAD_AGE_MAX_MULTIPLIER = 2.3  # cap of the uplift


def squad_age_multiplier(mean_age: float) -> float:
    """Collective valuation uplift as a function of the squad's mean age."""

    if mean_age <= SQUAD_AGE_NEUTRAL_AGE:
        return 1.0
    progress = (mean_age - SQUAD_AGE_NEUTRAL_AGE) / (SQUAD_AGE_FULL_AGE - SQUAD_AGE_NEUTRAL_AGE)
    return 1.0 + clamp(progress, 0.0, 1.0) * (SQUAD_AGE_MAX_MULTIPLIER - 1.0)


def player_effective_value(market_value: float, club_level: float = 1.0) -> float:
    """Player value = market value scaled by club level. No age/minutes/league factor."""

    if market_value < 0:
        raise ValueError("market_value cannot be negative")
    if club_level < 0:
        raise ValueError("club_level cannot be negative")
    return market_value * club_level


def squad_age_multipliers(rows: Iterable[Mapping[str, Any]]) -> dict[str, float]:
    """Map each team to its collective age uplift, from the squad's mean age."""

    ages: dict[str, list[float]] = {}
    for row in rows:
        if not row.get("called_up", True):
            continue
        ages.setdefault(str(row["team"]), []).append(float(row["age"]))
    return {
        team: squad_age_multiplier(sum(team_ages) / len(team_ages))
        for team, team_ages in ages.items()
    }


def apply_squad_age_uplift(
    players: Iterable[PlayerValue],
    multiplier_by_team: Mapping[str, float],
) -> list[PlayerValue]:
    """Scale each team's player values by its collective squad-age multiplier."""

    uplifted: list[PlayerValue] = []
    for player in players:
        multiplier = multiplier_by_team.get(player.team, 1.0)
        scaled = player.effective_value * multiplier
        uplifted.append(
            replace(player, effective_value=scaled, aggregated_value=math.log1p(scaled))
        )
    return uplifted


def player_value_from_row(row: Mapping[str, Any]) -> PlayerValue:
    effective = player_effective_value(
        market_value=float(row["market_value"]),
        club_level=float(row.get("club_level", 1.0)),
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
    """Rank squads by total talent (mean sector z), docking only critical holes.

    A team is scored by its mean sector strength; a penalty applies only to sectors
    that fall below ``critical_threshold`` (a genuinely weak sector relative to the
    field), proportional to how far below the line they sit. Mere unevenness above
    the line is not penalised, so strong-but-spiky squads are not dragged down.
    """

    teams = list(sector_value_by_team)
    sector_z: dict[str, dict[str, float]] = {team: {} for team in teams}
    for sector in SECTORS:
        raw = {team: float(sector_value_by_team[team].get(sector, 0.0)) for team in teams}
        standardized = z_scores_by_key(raw)
        for team, value in standardized.items():
            sector_z[team][sector] = value

    scores: dict[str, float] = {}
    for team, values in sector_z.items():
        z_values = list(values.values())
        mean_z = sum(z_values) / len(z_values)
        deficit = sum(max(0.0, critical_threshold - z) for z in z_values)
        scores[team] = mean_z - critical_penalty * deficit
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
    players = apply_squad_age_uplift(players, squad_age_multipliers(rows))
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
