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


def market_age_curve(age: float) -> float:
    """Approximate resale-value curve, peaking before the current-ability curve."""

    return clamp(math.exp(-((age - 24.0) ** 2) / 72.0), 0.35, 1.0)


def ability_age_curve(age: float) -> float:
    """Approximate current-ability curve used for MVP squad valuation."""

    return clamp(math.exp(-((age - 28.0) ** 2) / 98.0), 0.45, 1.0)


def player_effective_value(
    market_value: float,
    age: float,
    recent_minutes_factor: float = 1.0,
    club_level: float = 1.0,
    league_level: float = 1.0,
    status: float = 1.0,
) -> float:
    if market_value < 0:
        raise ValueError("market_value cannot be negative")
    if age <= 0:
        raise ValueError("age must be positive")

    peak_value = market_value / market_age_curve(age)
    current_value = peak_value * ability_age_curve(age)
    if age <= 22:
        current_value *= 0.6 + 0.4 * clamp(status, 0.0, 1.0)
    return max(0.0, current_value * recent_minutes_factor * club_level * league_level)


def player_value_from_row(row: Mapping[str, Any]) -> PlayerValue:
    effective = player_effective_value(
        market_value=float(row["market_value"]),
        age=float(row["age"]),
        recent_minutes_factor=float(
            row.get("recent_minutes_factor", row.get("recent_minutes", 1.0))
        ),
        club_level=float(row.get("club_level", 1.0)),
        league_level=float(row.get("league_level", 1.0)),
        status=float(row.get("status", 1.0)),
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
    balance_penalty: float = 0.30,
) -> dict[str, float]:
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
        min_z = min(z_values)
        scores[team] = mean_z - balance_penalty * (mean_z - min_z)
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
