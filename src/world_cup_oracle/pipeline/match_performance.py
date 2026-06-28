from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from world_cup_oracle.config import PerformanceParameters, TSIParameters
from world_cup_oracle.data.io import read_parquet, write_parquet

CLEAR_CHANCE_XG_EQUIVALENT = 0.35
TOUCH_OPPOSITION_BOX_XG_EQUIVALENT = 0.04
OPPOSITION_HALF_PASS_XG_EQUIVALENT = 0.004
GROUND_DUEL_XG_EQUIVALENT = 0.025
SUCCESSFUL_DRIBBLE_XG_EQUIVALENT = 0.08
PROCESS_INPUT_COLUMNS = (
    "clear_chances",
    "clear_chances_against",
    "touches_in_opposition_box",
    "touches_in_opposition_box_against",
    "opposition_half_passes",
    "opposition_half_passes_against",
    "ground_duels_won",
    "ground_duels_won_against",
    "ground_duels_won_pct",
    "ground_duels_won_pct_against",
    "successful_dribbles",
    "successful_dribbles_against",
    "successful_dribbles_pct",
    "successful_dribbles_pct_against",
)
PROCESS_AVAILABILITY_COLUMNS = ("xg", "xg_against", *PROCESS_INPUT_COLUMNS)


def _polars() -> Any:
    import polars as pl

    return pl


def _as_float(column: str) -> Any:
    return _polars().col(column).cast(_polars().Float64)


def _metric_expr(column: str, multiplier: float = 1.0) -> Any:
    return _as_float(column) * multiplier


def _count_pct_metric_expr(count_column: str, pct_column: str, multiplier: float) -> Any:
    pct_factor = 0.5 + (_as_float(pct_column) / 100.0).fill_null(0.5)
    return _as_float(count_column) * multiplier * pct_factor


def _ensure_process_columns(frame: Any) -> Any:
    pl = _polars()
    missing = [column for column in PROCESS_INPUT_COLUMNS if column not in frame.columns]
    if not missing:
        return frame
    return frame.with_columns(pl.lit(None).cast(pl.Float64).alias(column) for column in missing)


def _weighted_available_average(specs: list[tuple[str, Any, float]]) -> Any:
    pl = _polars()
    numerator = pl.lit(0.0)
    denominator = pl.lit(0.0)
    for _, value_expr, weight in specs:
        available = value_expr.is_not_null()
        numerator = numerator + pl.when(available).then(value_expr * weight).otherwise(0.0)
        denominator = denominator + pl.when(available).then(weight).otherwise(0.0)
    return pl.when(denominator > 0).then(numerator / denominator).otherwise(0.0)


def _any_available_expr(columns: tuple[str, ...]) -> Any:
    pl = _polars()
    return pl.any_horizontal([pl.col(column).is_not_null() for column in columns])


def _clamp_expr(expr: Any, lower: float, upper: float) -> Any:
    pl = _polars()
    return pl.min_horizontal(pl.max_horizontal(expr, pl.lit(lower)), pl.lit(upper))


def _soft_cap_expr(expr: Any, cap: float) -> Any:
    # Smoothly compresses extreme one-match signals while preserving sign and ordering.
    return cap * ((2.0 / (1.0 + ((-2.0 * expr / cap).exp()))) - 1.0)


def _first_red_card_disadvantage_minutes() -> Any:
    pl = _polars()
    own_red = _as_float("first_red_card_minute")
    opponent_red = _as_float("opponent_first_red_card_minute")
    raw_minutes = opponent_red.fill_null(90.0) - own_red
    return (
        pl.when(own_red.is_null())
        .then(0.0)
        .when(opponent_red.is_null() | (own_red < opponent_red))
        .then(_clamp_expr(raw_minutes, 0.0, 90.0))
        .otherwise(0.0)
    )


def match_performance_frame(
    match_stats: Any,
    match_probabilities: Any,
    params: PerformanceParameters | None = None,
) -> Any:
    pl = _polars()
    params = params or PerformanceParameters()
    match_stats = _ensure_process_columns(match_stats)
    fixture_weight_columns = (
        "team_a_rotated",
        "team_b_rotated",
        "team_a_guaranteed_first",
        "team_b_guaranteed_first",
    )
    has_fixture_weight_columns = all(
        column in match_probabilities.columns for column in fixture_weight_columns
    )
    match_probabilities = _ensure_columns(
        match_probabilities,
        {column: None for column in fixture_weight_columns},
    )
    opponent_reds = match_stats.select(
        "match_id",
        pl.col("team").alias("opponent"),
        pl.col("red_cards").alias("opponent_red_cards"),
        pl.col("first_red_card_minute").alias("opponent_first_red_card_minute"),
    )

    joined = (
        match_stats.join(opponent_reds, on=["match_id", "opponent"], how="left")
        .join(match_probabilities, on=["match_id", "match_number"], how="inner")
        .filter((pl.col("team") == pl.col("team_a")) | (pl.col("team") == pl.col("team_b")))
    )

    offensive_process = _weighted_available_average(
        [
            ("xg", _metric_expr("xg"), params.offensive_weights["xg"]),
            (
                "clear_chances",
                _metric_expr("clear_chances", CLEAR_CHANCE_XG_EQUIVALENT),
                params.offensive_weights["clear_chances"],
            ),
            (
                "touches_in_opposition_box",
                _metric_expr(
                    "touches_in_opposition_box",
                    TOUCH_OPPOSITION_BOX_XG_EQUIVALENT,
                ),
                params.offensive_weights["touches_in_opposition_box"],
            ),
            (
                "opposition_half_passes",
                _metric_expr("opposition_half_passes", OPPOSITION_HALF_PASS_XG_EQUIVALENT),
                params.offensive_weights["opposition_half_passes"],
            ),
            (
                "ground_duels",
                _count_pct_metric_expr(
                    "ground_duels_won",
                    "ground_duels_won_pct",
                    GROUND_DUEL_XG_EQUIVALENT,
                ),
                params.offensive_weights["ground_duels"],
            ),
            (
                "successful_dribbles",
                _count_pct_metric_expr(
                    "successful_dribbles",
                    "successful_dribbles_pct",
                    SUCCESSFUL_DRIBBLE_XG_EQUIVALENT,
                ),
                params.offensive_weights["successful_dribbles"],
            ),
        ]
    )
    defensive_process = _weighted_available_average(
        [
            ("xg_against", _metric_expr("xg_against"), params.defensive_weights["xg_against"]),
            (
                "clear_chances_against",
                _metric_expr("clear_chances_against", CLEAR_CHANCE_XG_EQUIVALENT),
                params.defensive_weights["clear_chances_against"],
            ),
            (
                "touches_in_opposition_box_against",
                _metric_expr(
                    "touches_in_opposition_box_against",
                    TOUCH_OPPOSITION_BOX_XG_EQUIVALENT,
                ),
                params.defensive_weights["touches_in_opposition_box_against"],
            ),
            (
                "opposition_half_passes_against",
                _metric_expr(
                    "opposition_half_passes_against",
                    OPPOSITION_HALF_PASS_XG_EQUIVALENT,
                ),
                params.defensive_weights["opposition_half_passes_against"],
            ),
            (
                "ground_duels_against",
                _count_pct_metric_expr(
                    "ground_duels_won_against",
                    "ground_duels_won_pct_against",
                    GROUND_DUEL_XG_EQUIVALENT,
                ),
                params.defensive_weights["ground_duels_against"],
            ),
            (
                "successful_dribbles_against",
                _count_pct_metric_expr(
                    "successful_dribbles_against",
                    "successful_dribbles_pct_against",
                    SUCCESSFUL_DRIBBLE_XG_EQUIVALENT,
                ),
                params.defensive_weights["successful_dribbles_against"],
            ),
        ]
    )
    is_team_a = pl.col("team") == pl.col("team_a")
    lambda_for = pl.when(is_team_a).then(pl.col("lambda_a")).otherwise(pl.col("lambda_b"))
    lambda_against = pl.when(is_team_a).then(pl.col("lambda_b")).otherwise(pl.col("lambda_a"))
    expected_points = (
        pl.when(is_team_a).then(pl.col("expected_points_a")).otherwise(pl.col("expected_points_b"))
    )
    actual_points = (
        pl.when(pl.col("goals") > pl.col("goals_against"))
        .then(3.0)
        .when(pl.col("goals") == pl.col("goals_against"))
        .then(1.0)
        .otherwise(0.0)
    )
    disadvantage_minutes = _first_red_card_disadvantage_minutes()
    base_match_weight = _clamp_expr(
        1.0 - params.red_card_weight_factor * (_clamp_expr(disadvantage_minutes, 0.0, 90.0) / 90.0),
        params.min_match_weight,
        1.0,
    )
    game_num = pl.col("match_number").rank("dense").over("team")
    rotated = (
        pl.when(is_team_a)
        .then(pl.col("team_a_rotated"))
        .otherwise(pl.col("team_b_rotated"))
        .fill_null(False)
    )
    guaranteed = (
        pl.when(is_team_a)
        .then(pl.col("team_a_guaranteed_first"))
        .otherwise(pl.col("team_b_guaranteed_first"))
        .fill_null(False)
    )
    has_active_var = pl.lit(not has_fixture_weight_columns) | rotated | guaranteed
    multiplier = (
        pl.when(has_active_var)
        .then(1.0)
        .when(game_num == 1)
        .then(0.8)
        .when((game_num == 2) | (game_num == 3))
        .then(1.2)
        .otherwise(1.0)
    )
    match_weight = base_match_weight * multiplier
    has_process_stats = _any_available_expr(PROCESS_AVAILABILITY_COLUMNS)

    return (
        joined.with_columns(
            lambda_for.alias("lambda_for"),
            lambda_against.alias("lambda_against"),
            expected_points.alias("expected_points"),
            actual_points.alias("actual_points"),
            offensive_process.alias("process_for"),
            defensive_process.alias("process_against"),
            has_process_stats.alias("has_process_stats"),
            disadvantage_minutes.alias("minutes_numerical_imbalance"),
            match_weight.alias("match_weight"),
        )
        .with_columns(
            (pl.col("lambda_for") - pl.col("lambda_against")).alias("expected_goal_difference"),
            (pl.col("process_for") - pl.col("process_against")).alias(
                "raw_process_goal_difference"
            ),
            (pl.col("actual_points") - pl.col("expected_points")).alias("result_surprise"),
        )
        .with_columns(
            (
                pl.when(pl.col("has_process_stats"))
                .then(pl.col("raw_process_goal_difference"))
                .otherwise(pl.col("expected_goal_difference"))
            ).alias("process_goal_difference")
        )
        .with_columns(
            (
                pl.when(pl.col("has_process_stats"))
                .then(
                    pl.col("process_goal_difference")
                    - pl.col("expected_goal_difference")
                    + params.actual_gd_influence * (pl.col("goals") - pl.col("goals_against"))
                )
                .otherwise(0.0)
            ).alias("process_surprise")
        )
        .with_columns(
            (
                params.process_weight * pl.col("process_surprise")
                + params.result_weight * pl.col("result_surprise")
            ).alias("raw_match_tsi_delta")
        )
        .with_columns(
            _soft_cap_expr(
                pl.col("raw_match_tsi_delta"),
                params.match_delta_soft_cap,
            ).alias("compressed_match_tsi_delta")
        )
        .with_columns(
            (
                pl.col("compressed_match_tsi_delta")
                - pl.col("compressed_match_tsi_delta").mean().over(["match_id", "match_number"])
            ).alias("match_tsi_delta")
        )
        .with_columns(
            (pl.col("match_tsi_delta") * pl.col("match_weight")).alias(
                "uncentered_weighted_match_tsi_delta"
            )
        )
        .with_columns(
            (
                pl.col("uncentered_weighted_match_tsi_delta")
                - pl.col("uncentered_weighted_match_tsi_delta").mean().over(
                    ["match_id", "match_number"]
                )
            ).alias(
                "weighted_match_tsi_delta",
            )
        )
        .select(
            "match_id",
            "match_number",
            "date",
            "team",
            "opponent",
            "goals",
            "goals_against",
            "lambda_for",
            "lambda_against",
            "expected_goal_difference",
            "process_for",
            "process_against",
            "has_process_stats",
            "process_goal_difference",
            "expected_points",
            "actual_points",
            "process_surprise",
            "result_surprise",
            "raw_match_tsi_delta",
            "compressed_match_tsi_delta",
            "match_tsi_delta",
            "match_weight",
            "weighted_match_tsi_delta",
            "minutes_numerical_imbalance",
            "red_cards",
            "opponent_red_cards",
        )
        .sort(["match_number", "team"])
    )


def _ensure_columns(frame: Any, columns: dict[str, Any]) -> Any:
    pl = _polars()
    missing = [
        pl.lit(default).alias(column)
        for column, default in columns.items()
        if column not in frame.columns
    ]
    if not missing:
        return frame
    return frame.with_columns(missing)


def match_performance_audit_frame(match_performance: Any, match_stats: Any) -> Any:
    pl = _polars()
    match_stats = _ensure_columns(
        match_stats,
        {
            "xg": None,
            "xg_against": None,
            "data_source": None,
            "last_updated": None,
            "status": None,
            "is_home": None,
            "red_cards": None,
            "first_red_card_minute": None,
        },
    )
    stats_columns = [
        "match_id",
        "match_number",
        "team",
        "opponent",
        "xg",
        "xg_against",
        "data_source",
        "last_updated",
        "status",
        "is_home",
        "red_cards",
        "first_red_card_minute",
    ]
    stats = match_stats.select(stats_columns).rename(
        {
            "xg": "raw_xg",
            "xg_against": "raw_xg_against",
            "red_cards": "raw_red_cards",
            "first_red_card_minute": "raw_first_red_card_minute",
        }
    )
    score = (
        pl.col("goals").cast(pl.Utf8)
        + pl.lit("-")
        + pl.col("goals_against").cast(pl.Utf8)
    )
    return (
        match_performance.join(
            stats,
            on=["match_id", "match_number", "team", "opponent"],
            how="left",
        )
        .with_columns(
            score.alias("score"),
            (pl.col("goals") - pl.col("goals_against")).alias("goal_difference"),
            (pl.col("raw_xg") - pl.col("raw_xg_against")).alias("xg_difference"),
            pl.col("raw_match_tsi_delta").alias("raw"),
            pl.col("weighted_match_tsi_delta").alias("delta_final"),
        )
        .select(
            "match_id",
            "match_number",
            "date",
            "team",
            "opponent",
            "score",
            "goals",
            "goals_against",
            "goal_difference",
            "raw_xg",
            "raw_xg_against",
            "xg_difference",
            "lambda_for",
            "lambda_against",
            "expected_goal_difference",
            "process_for",
            "process_against",
            "process_goal_difference",
            "expected_points",
            "actual_points",
            "process_surprise",
            "result_surprise",
            "raw",
            "raw_match_tsi_delta",
            "compressed_match_tsi_delta",
            "match_tsi_delta",
            "match_weight",
            "delta_final",
            "weighted_match_tsi_delta",
            "has_process_stats",
            "minutes_numerical_imbalance",
            "red_cards",
            "opponent_red_cards",
            "raw_red_cards",
            "raw_first_red_card_minute",
            "is_home",
            "status",
            "data_source",
            "last_updated",
        )
        .sort(["match_number", "team"])
    )


def b3_calibration_review_frame(
    match_audit: Any,
    tsi_pre_cup: Any,
    favorite_gap: float = 2.0,
    process_threshold: float = 0.50,
    blowout_goals: int = 3,
    extreme_raw_threshold: float = 6.0,
) -> Any:
    pl = _polars()
    team_tsi = tsi_pre_cup.select("team", "tsi_pre")
    opponent_tsi = team_tsi.rename({"team": "opponent", "tsi_pre": "opponent_tsi_pre"})
    goal_diff = pl.col("goal_difference")
    process_diff = pl.col("process_goal_difference")
    tsi_gap = pl.col("tsi_pre") - pl.col("opponent_tsi_pre")
    favorite_loss = (tsi_gap >= favorite_gap) & (goal_diff < 0)
    underdog_draw = (tsi_gap <= -favorite_gap) & (goal_diff == 0)
    blowout = goal_diff.abs() >= blowout_goals
    process_against_result = ((goal_diff > 0) & (process_diff <= -process_threshold)) | (
        (goal_diff < 0) & (process_diff >= process_threshold)
    )
    strong_process_draw = (goal_diff == 0) & (process_diff.abs() >= process_threshold)
    extreme_raw = pl.col("raw").abs() >= extreme_raw_threshold
    review_priority = (
        pl.when(favorite_loss).then(5).otherwise(0)
        + pl.when(process_against_result).then(4).otherwise(0)
        + pl.when(underdog_draw).then(3).otherwise(0)
        + pl.when(blowout).then(2).otherwise(0)
        + pl.when(strong_process_draw).then(1).otherwise(0)
        + pl.when(extreme_raw).then(1).otherwise(0)
    )
    return (
        match_audit.join(team_tsi, on="team", how="left")
        .join(opponent_tsi, on="opponent", how="left")
        .with_columns(
            tsi_gap.alias("tsi_gap"),
            favorite_loss.alias("favorite_loss"),
            underdog_draw.alias("underdog_draw"),
            blowout.alias("blowout"),
            process_against_result.alias("process_against_result"),
            strong_process_draw.alias("strong_process_draw"),
            extreme_raw.alias("extreme_raw"),
            review_priority.alias("review_priority"),
        )
        .filter(pl.col("review_priority") > 0)
        .select(
            "review_priority",
            "match_number",
            "team",
            "opponent",
            "score",
            "tsi_pre",
            "opponent_tsi_pre",
            "tsi_gap",
            "raw_xg",
            "raw_xg_against",
            "xg_difference",
            "process_for",
            "process_against",
            "process_goal_difference",
            "expected_points",
            "actual_points",
            "result_surprise",
            "process_surprise",
            "raw",
            "delta_final",
            "favorite_loss",
            "underdog_draw",
            "blowout",
            "process_against_result",
            "strong_process_draw",
            "extreme_raw",
            "has_process_stats",
            "data_source",
        )
        .sort(["review_priority", "match_number", "team"], descending=[True, False, False])
    )


def team_performance_adjustment_frame(
    match_performance: Any,
    tsi_pre_cup: Any,
    tsi_params: TSIParameters | None = None,
) -> Any:
    pl = _polars()
    tsi_params = tsi_params or TSIParameters()
    aggregated = (
        match_performance.group_by("team")
        .agg(
            pl.len().alias("matches_played"),
            pl.col("match_weight").sum().alias("total_match_weight"),
            pl.col("weighted_match_tsi_delta").sum().alias("weighted_tsi_delta_sum"),
        )
        .with_columns(
            (
                pl.col("weighted_tsi_delta_sum") / pl.col("total_match_weight")
            ).alias("performance_adjustment")
        )
    )
    post_delta = _clamp_expr(
        pl.col("performance_adjustment") * tsi_params.post_groups_weight,
        -tsi_params.post_groups_delta_cap,
        tsi_params.post_groups_delta_cap,
    )
    return (
        aggregated.join(tsi_pre_cup.select("team", "tsi_pre"), on="team", how="left")
        .with_columns(
            (pl.col("tsi_pre") + pl.col("performance_adjustment")).alias("performance_group_tsi"),
            post_delta.alias("post_groups_tsi_delta"),
        )
        .with_columns(
            _clamp_expr(
                pl.col("tsi_pre") + pl.col("post_groups_tsi_delta"),
                tsi_params.tsi_min,
                tsi_params.tsi_max,
            ).alias("tsi_post_groups")
        )
        .select(
            "team",
            "matches_played",
            "total_match_weight",
            "performance_adjustment",
            "tsi_pre",
            "performance_group_tsi",
            "post_groups_tsi_delta",
            "tsi_post_groups",
        )
        .sort("performance_adjustment", descending=True)
    )


def build_real_match_performance_outputs(
    interim_dir: str | Path = "data/interim",
    processed_dir: str | Path = "data/processed",
) -> dict[str, Any]:
    interim_path = Path(interim_dir)
    processed_path = Path(processed_dir)
    match_performance = match_performance_frame(
        read_parquet(interim_path / "worldcup_match_stats.parquet"),
        read_parquet(processed_path / "match_probabilities.parquet"),
    )
    team_adjustments = team_performance_adjustment_frame(
        match_performance,
        read_parquet(processed_path / "tsi_pre_cup.parquet"),
    )
    match_audit = match_performance_audit_frame(
        match_performance,
        read_parquet(interim_path / "worldcup_match_stats.parquet"),
    )
    b3_review = b3_calibration_review_frame(
        match_audit,
        read_parquet(processed_path / "tsi_pre_cup.parquet"),
    )
    return {
        "match_performance.parquet": match_performance,
        "match_performance_audit.parquet": match_audit,
        "calibration_b3_review.parquet": b3_review,
        "team_performance_adjustments.parquet": team_adjustments,
    }


def write_real_match_performance_outputs(
    interim_dir: str | Path = "data/interim",
    processed_dir: str | Path = "data/processed",
) -> list[Path]:
    output_path = Path(processed_dir)
    written: list[Path] = []
    for filename, frame in build_real_match_performance_outputs(interim_dir, processed_dir).items():
        destination = output_path / filename
        write_parquet(frame, destination)
        written.append(destination)
    return written


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build match-level TSI performance deltas.")
    parser.add_argument("--interim-dir", default="data/interim")
    parser.add_argument("--processed-dir", default="data/processed")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    for path in write_real_match_performance_outputs(args.interim_dir, args.processed_dir):
        print(path)


if __name__ == "__main__":
    main()
