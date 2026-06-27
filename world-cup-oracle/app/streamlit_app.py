from __future__ import annotations

import polars as pl
import streamlit as st
from oracle_ui import (
    as_pandas,
    compact_probability_frame,
    configure_page,
    load_frame,
    number,
    page_header,
    pct,
    sidebar_context,
    signed,
    table,
)

configure_page()
sidebar_context()

stage = load_frame("team_stage_probabilities.parquet")
next_matches = load_frame("next_matches.parquet")
group_projection = load_frame("group_projection.parquet")
team_performance = load_frame("team_performance_adjustments.parquet")
b3_review = load_frame("calibration_b3_review.parquet")

page_header("World Cup Oracle", "Painel estatistico da Copa 2026")

favorite = stage.sort("champion", descending=True).row(0, named=True)
most_balanced = (
    next_matches.with_columns((pl.col("p_win_a") - pl.col("p_win_b")).abs().alias("gap"))
    .sort(["gap", "match_number"])
    .row(0, named=True)
)
biggest_riser = team_performance.sort("post_groups_tsi_delta", descending=True).row(0, named=True)
highest_review = b3_review.sort(["review_priority", "match_number"], descending=[True, False]).row(
    0,
    named=True,
)

metric_cols = st.columns(4)
metric_cols[0].metric("Favorito", favorite["team"], pct(favorite["champion"]))
metric_cols[1].metric(
    "Jogo mais equilibrado",
    f"{most_balanced['team_a']} x {most_balanced['team_b']}",
    f"{pct(most_balanced['p_win_a'])} / {pct(most_balanced['p_win_b'])}",
)
metric_cols[2].metric(
    "Maior alta TSI",
    biggest_riser["team"],
    signed(biggest_riser["post_groups_tsi_delta"]),
)
metric_cols[3].metric(
    "Revisao B3",
    f"{highest_review['team']} x {highest_review['opponent']}",
    f"prioridade {highest_review['review_priority']}",
)

st.divider()

left, right = st.columns([1.05, 0.95])
with left:
    st.subheader("Titulo")
    top_champion = compact_probability_frame(
        stage.sort("champion", descending=True).head(12),
        ["team", "reach_qf", "reach_sf", "reach_final", "champion"],
    )
    st.bar_chart(as_pandas(top_champion), x="team", y="champion", height=300)
    table(top_champion, height=310)

with right:
    st.subheader("Proximas Partidas")
    next_view = compact_probability_frame(
        next_matches.sort("match_number"),
        [
            "match_number",
            "group",
            "team_a",
            "team_b",
            "p_win_a",
            "p_draw",
            "p_win_b",
            "expected_points_a",
            "expected_points_b",
            "most_likely_score",
        ],
    )
    table(next_view, height=650)

st.divider()

group_left, group_right = st.columns([1.0, 1.0])
with group_left:
    st.subheader("Risco de Grupo")
    risk = compact_probability_frame(
        group_projection.sort("prob_eliminated_group", descending=True).head(12),
        ["team", "group", "prob_qualify", "prob_eliminated_group", "avg_points"],
    )
    table(risk, height=390)

with group_right:
    st.subheader("Movimento TSI")
    movers = (
        team_performance.with_columns(pl.col("post_groups_tsi_delta").abs().alias("abs_delta"))
        .sort("abs_delta", descending=True)
        .drop("abs_delta")
        .head(12)
        .select(
            [
                "team",
                "tsi_pre",
                "performance_adjustment",
                "post_groups_tsi_delta",
                "tsi_post_groups",
            ]
        )
        .with_columns(pl.all().exclude("team").round(3))
    )
    table(movers, height=390)

st.divider()
st.subheader("Casos Marcados Pela Calibracao B3")
review = (
    b3_review.select(
        [
            "review_priority",
            "match_number",
            "team",
            "opponent",
            "score",
            "process_goal_difference",
            "result_surprise",
            "raw",
            "delta_final",
            "favorite_loss",
            "underdog_draw",
            "blowout",
            "process_against_result",
        ]
    )
    .with_columns(pl.all().exclude(["team", "opponent", "score"]).round(3))
    .head(20)
)
table(review, height=520)

st.caption(
    f"{stage.height} selecoes | {next_matches.height} proximos jogos | "
    f"{number(stage['champion'].sum(), 2)} campeao esperado total"
)
