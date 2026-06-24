from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class EloParameters:
    """Parameters documented for B2, the custom cycle Elo."""

    base_elo: float = 1500.0
    fifa_z_factor: float = 120.0
    elo_min: float = 1100.0
    elo_max: float = 1900.0
    k_factor: float = 25.0
    home_elo: float = 50.0
    recency_half_life_months: float = 24.0
    recency_sample_reference: float = 8.0
    recency_multiplier: float = 10.0
    recency_cap: float = 80.0
    penalty_win_score: float = 0.55
    penalty_loss_score: float = 0.45
    tournament_start: date = date(2026, 6, 11)
    importance_weights: dict[str, float] = field(
        default_factory=lambda: {
            "friendly": 0.50,
            "nations_league": 0.80,
            "qualifier": 1.00,
            "continental_group": 1.20,
            "continental_knockout": 1.50,
            "world_cup_group": 1.80,
            "world_cup_knockout": 2.20,
        }
    )


@dataclass(frozen=True)
class TSIParameters:
    """Parameters documented for B1, the Team Strength Index."""

    tsi_min: float = 0.0
    tsi_max: float = 20.0
    squad_adjustment_cap: float = 1.0
    odds_adjustment_cap: float = 0.75
    post_groups_weight: float = 0.30
    post_groups_delta_cap: float = 2.0


@dataclass(frozen=True)
class AttackDefenseParameters:
    """Parameters documented for B4."""

    profile_multiplier: float = 0.8
    profile_cap: float = 2.0
    base_goals: float = 1.30
    k: float = 0.09
    host_gamma: float = 0.15
    opponent_delta: float = 0.0


@dataclass(frozen=True)
class SimulationParameters:
    """Parameters documented for B7."""

    score_max_goals: int = 15
    extra_time_factor: float = 1.0 / 3.0
    penalty_strength_factor: float = 0.010
    penalty_min: float = 0.40
    penalty_max: float = 0.60
    quick_simulations: int = 50_000
    stable_simulations: int = 200_000


@dataclass(frozen=True)
class ValidationParameters:
    """Parameters documented for B9."""

    calibration_bins: int = 10
    epsilon: float = 1e-15

