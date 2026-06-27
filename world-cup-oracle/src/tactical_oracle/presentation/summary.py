from __future__ import annotations

from pathlib import Path
from typing import Any

from tactical_oracle.data.io import read_parquet

PERCENT_COLUMNS = {
    "qualify_r32",
    "reach_r16",
    "reach_qf",
    "reach_sf",
    "reach_final",
    "champion",
    "prob_group_1",
    "prob_group_2",
    "prob_group_3",
    "prob_group_4",
    "prob_top2",
    "prob_best_third",
    "prob_qualify",
    "prob_eliminated_group",
    "p_win_a",
    "p_draw",
    "p_win_b",
    "appear_probability",
    "win_probability",
    "conditional_win_probability",
}


def processed_path(root: str | Path, filename: str) -> Path:
    return Path(root) / "data" / "processed" / filename


def read_processed(root: str | Path, filename: str) -> Any:
    return read_parquet(processed_path(root, filename))


def percent(value: float | int | None, digits: int = 1) -> str:
    if value is None:
        return "-"
    return f"{float(value) * 100:.{digits}f}%"


def signed(value: float | int | None, digits: int = 2) -> str:
    if value is None:
        return "-"
    return f"{float(value):+.{digits}f}"


def top_champion(stage_probabilities: Any, n: int = 15) -> Any:
    return stage_probabilities.sort("champion", descending=True).head(n)


def biggest_tsi_moves(team_performance: Any, n: int = 10) -> Any:
    return (
        team_performance.with_columns(
            team_performance["post_groups_tsi_delta"].abs().alias("abs_delta")
        )
        .sort("abs_delta", descending=True)
        .head(n)
        .drop("abs_delta")
    )


def decisive_next_matches(next_matches: Any, n: int = 8) -> Any:
    return (
        next_matches.with_columns(
            (next_matches["p_win_a"] - next_matches["p_win_b"]).abs().alias("balance_gap")
        )
        .sort(["balance_gap", "match_number"])
        .head(n)
        .drop("balance_gap")
    )


def team_snapshot(
    team: str,
    stage_probabilities: Any,
    group_projection: Any,
    team_performance: Any,
) -> dict[str, Any]:
    stage = stage_probabilities.filter(stage_probabilities["team"] == team)
    group = group_projection.filter(group_projection["team"] == team)
    performance = team_performance.filter(team_performance["team"] == team)
    if stage.is_empty() or group.is_empty() or performance.is_empty():
        raise ValueError(f"team not found in projection outputs: {team}")
    stage_row = stage.row(0, named=True)
    group_row = group.row(0, named=True)
    performance_row = performance.row(0, named=True)
    return {
        "team": team,
        "group": group_row["group"],
        "tsi_pre": performance_row["tsi_pre"],
        "tsi_post_groups": performance_row["tsi_post_groups"],
        "post_groups_tsi_delta": performance_row["post_groups_tsi_delta"],
        "prob_qualify": group_row["prob_qualify"],
        "champion": stage_row["champion"],
        "reach_final": stage_row["reach_final"],
    }


def available_teams(stage_probabilities: Any) -> list[str]:
    return sorted(str(team) for team in stage_probabilities["team"].to_list())
