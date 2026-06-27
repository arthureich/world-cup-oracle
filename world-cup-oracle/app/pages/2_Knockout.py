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
    table,
    team_stage_row,
)

configure_page("Knockout | World Cup Oracle")
sidebar_context()

stage = load_frame("team_stage_probabilities.parquet")
knockout = load_frame("knockout_match_probabilities.parquet")

page_header("Mata-Mata", "Probabilidades por fase e por jogo possivel")

team = select_team(stage)
row = team_stage_row(stage, team)

cols = st.columns(6)
cols[0].metric("R32", pct(row["qualify_r32"]))
cols[1].metric("R16", pct(row["reach_r16"]))
cols[2].metric("Quartas", pct(row["reach_qf"]))
cols[3].metric("Semis", pct(row["reach_sf"]))
cols[4].metric("Final", pct(row["reach_final"]))
cols[5].metric("Titulo", pct(row["champion"]))

st.divider()

left, right = st.columns([1.0, 1.0])

with left:
    st.subheader("Ranking Por Titulo")
    title_view = compact_probability_frame(
        stage.sort("champion", descending=True).head(20),
        ["team", "reach_r16", "reach_qf", "reach_sf", "reach_final", "champion"],
    )
    table(title_view, height=650)

with right:
    st.subheader("Caminho da Selecao")
    team_path = compact_probability_frame(
        knockout.filter(pl.col("team") == team).sort("match_number"),
        [
            "match_number",
            "stage",
            "team",
            "appear_probability",
            "win_probability",
            "conditional_win_probability",
        ],
    )
    table(team_path, height=650)

st.divider()

st.subheader("Janelas de Mata-Mata")
stage_filter = st.segmented_control(
    "Fase",
    ["Round of 32", "Round of 16", "Quarter-final", "Semi-final", "Final"],
    default="Round of 32",
)
match_view = compact_probability_frame(
    knockout.filter(pl.col("stage") == stage_filter).sort(
        ["match_number", "appear_probability"],
        descending=[False, True],
    ),
    [
        "match_number",
        "stage",
        "team",
        "appear_probability",
        "win_probability",
        "conditional_win_probability",
    ],
)
table(match_view, height=720)
