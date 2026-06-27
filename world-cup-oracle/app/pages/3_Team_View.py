from __future__ import annotations

import polars as pl
import streamlit as st
from oracle_ui import (
    compact_probability_frame,
    configure_page,
    load_frame,
    page_header,
    pct,
    select_team,
    sidebar_context,
    signed,
    table,
    team_stage_row,
)

configure_page("Team | World Cup Oracle")
sidebar_context()

stage = load_frame("team_stage_probabilities.parquet")
group_projection = load_frame("group_projection.parquet")
team_performance = load_frame("team_performance_adjustments.parquet")
next_matches = load_frame("next_matches.parquet")
knockout = load_frame("knockout_match_probabilities.parquet")
performance_audit = load_frame("match_performance_audit.parquet")

page_header("Selecao", "Forca atual, caminho projetado e desempenho recente")

team = select_team(stage)
stage_row = team_stage_row(stage, team)
group_row = group_projection.filter(pl.col("team") == team).row(0, named=True)
tsi_row = team_performance.filter(pl.col("team") == team).row(0, named=True)

cols = st.columns(5)
cols[0].metric("Grupo", group_row["group"])
cols[1].metric(
    "TSI Agora",
    f"{tsi_row['tsi_post_groups']:.2f}",
    signed(tsi_row["post_groups_tsi_delta"]),
)
cols[2].metric("Classificar", pct(group_row["prob_qualify"]))
cols[3].metric("Final", pct(stage_row["reach_final"]))
cols[4].metric("Titulo", pct(stage_row["champion"]))

st.divider()

left, right = st.columns([1.0, 1.0])

with left:
    st.subheader("Grupo")
    group_peers = compact_probability_frame(
        group_projection.filter(pl.col("group") == group_row["group"]).sort(
            "prob_group_1",
            descending=True,
        ),
        [
            "team",
            "avg_points",
            "prob_group_1",
            "prob_group_2",
            "prob_top2",
            "prob_best_third",
            "prob_qualify",
        ],
    )
    table(group_peers, height=360)

    st.subheader("Partidas Restantes")
    remaining = next_matches.filter(
        (pl.col("team_a") == team) | (pl.col("team_b") == team)
    ).sort("match_number")
    if remaining.is_empty():
        st.info("Sem partidas restantes.")
    else:
        table(
            compact_probability_frame(
                remaining,
                [
                    "match_number",
                    "team_a",
                    "team_b",
                    "p_win_a",
                    "p_draw",
                    "p_win_b",
                    "most_likely_score",
                ],
            ),
            height=230,
        )

with right:
    st.subheader("Caminho")
    path = compact_probability_frame(
        knockout.filter(pl.col("team") == team).sort("match_number"),
        [
            "match_number",
            "stage",
            "appear_probability",
            "win_probability",
            "conditional_win_probability",
        ],
    )
    table(path, height=360)

    st.subheader("Desempenho Nos Jogos")
    perf = (
        performance_audit.filter(pl.col("team") == team)
        .sort("match_number")
        .select(
            [
                "match_number",
                "opponent",
                "score",
                "raw_xg",
                "raw_xg_against",
                "result_surprise",
                "process_goal_difference",
                "delta_final",
            ]
        )
        .with_columns(pl.all().exclude(["opponent", "score"]).round(3))
    )
    table(perf, height=230)
