from __future__ import annotations

import polars as pl
import streamlit as st
from oracle_ui import configure_page, load_frame, page_header, sidebar_context, table

configure_page("Audit | World Cup Oracle")
sidebar_context()

performance = load_frame("match_performance_audit.parquet")
knockout_performance = load_frame("knockout_match_performance_audit.parquet")
review = load_frame("calibration_b3_review.parquet")
team_adjustments = load_frame("team_performance_adjustments.parquet")
current_strength = load_frame("team_current_strength.parquet")

if not knockout_performance.is_empty():
    performance = pl.concat([performance, knockout_performance], how="diagonal_relaxed")
if not current_strength.is_empty():
    team_adjustments = (
        team_adjustments.join(
            current_strength.select(["team", "knockout_tsi_delta", "tsi_current"]),
            on="team",
            how="left",
        )
        .with_columns(
            [
                pl.col("knockout_tsi_delta").fill_null(0.0),
                (pl.col("post_groups_tsi_delta") + pl.col("knockout_tsi_delta").fill_null(0.0))
                .alias("post_groups_tsi_delta"),
                pl.coalesce(["tsi_current", "tsi_post_groups"]).alias("tsi_post_groups"),
            ]
        )
        .drop(["knockout_tsi_delta", "tsi_current"])
    )

page_header("Auditoria", "TSI, desempenho por jogo e casos de calibracao B3")

flags = {
    "Favorito perdeu": "favorite_loss",
    "Azarao empatou": "underdog_draw",
    "Goleada": "blowout",
    "Processo contra resultado": "process_against_result",
    "Empate com processo forte": "strong_process_draw",
    "Raw extremo": "extreme_raw",
}

selected_flag = st.selectbox("Filtro B3", ["Todos", *flags])
filtered_review = review
if selected_flag != "Todos":
    filtered_review = review.filter(pl.col(flags[selected_flag]))

top_cols = st.columns(4)
top_cols[0].metric("Jogos auditados", performance["match_number"].n_unique())
top_cols[1].metric("Linhas de performance", performance.height)
top_cols[2].metric("Casos B3", review.height)
top_cols[3].metric("Filtro atual", filtered_review.height)

st.divider()

left, right = st.columns([1.0, 1.0])

with left:
    st.subheader("TSI Pos-Grupos")
    tsi_view = (
        team_adjustments.sort("tsi_post_groups", descending=True)
        .select(
            [
                "team",
                "matches_played",
                "tsi_pre",
                "performance_adjustment",
                "post_groups_tsi_delta",
                "tsi_post_groups",
            ]
        )
        .with_columns(pl.all().exclude("team").round(3))
    )
    table(tsi_view, height=560)

with right:
    st.subheader("Casos B3")
    review_view = (
        filtered_review.select(
            [
                "review_priority",
                "match_number",
                "team",
                "opponent",
                "score",
                "tsi_gap",
                "xg_difference",
                "process_goal_difference",
                "result_surprise",
                "raw",
                "delta_final",
                "favorite_loss",
                "underdog_draw",
                "blowout",
                "process_against_result",
                "extreme_raw",
            ]
        )
        .with_columns(
            pl.all()
            .exclude(
                [
                    "team",
                    "opponent",
                    "score",
                    "favorite_loss",
                    "underdog_draw",
                    "blowout",
                    "process_against_result",
                    "extreme_raw",
                ]
            )
            .round(3)
        )
        .sort(["review_priority", "match_number"], descending=[True, False])
    )
    table(review_view, height=560)

st.divider()

st.subheader("Performance Por Partida")
teams = ["Todos", *sorted(performance["team"].unique().to_list())]
team = st.selectbox("Selecao", teams)
perf = performance if team == "Todos" else performance.filter(pl.col("team") == team)
perf_view = (
    perf.select(
        [
            "match_number",
            "team",
            "opponent",
            "score",
            "raw_xg",
            "raw_xg_against",
            "expected_points",
            "actual_points",
            "result_surprise",
            "process_goal_difference",
            "raw",
            "delta_final",
            "match_weight",
            "data_source",
        ]
    )
    .with_columns(pl.all().exclude(["team", "opponent", "score", "data_source"]).round(3))
    .sort(["match_number", "team"])
)
table(perf_view, height=680)
