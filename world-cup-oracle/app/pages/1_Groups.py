from __future__ import annotations

import polars as pl
import streamlit as st
from oracle_ui import (
    compact_probability_frame,
    configure_page,
    load_frame,
    page_header,
    sidebar_context,
    table,
)

configure_page("Groups | World Cup Oracle")
sidebar_context()

standings = load_frame("current_group_standings.parquet")
projection = load_frame("group_projection.parquet")
next_matches = load_frame("next_matches.parquet")

page_header("Grupos", "Classificacao atual e projecao do fechamento da fase de grupos")

groups = sorted(standings["group"].unique().to_list())
selected_group = st.segmented_control("Grupo", groups, default=groups[0])

group_standings = standings.filter(pl.col("group") == selected_group).sort("position")
group_projection = projection.filter(pl.col("group") == selected_group).sort(
    "prob_group_1",
    descending=True,
)
if next_matches.is_empty() or "group" not in next_matches.columns:
    group_next = pl.DataFrame()
else:
    group_next = next_matches.filter(pl.col("group") == selected_group).sort("match_number")

left, right = st.columns([0.9, 1.1])
with left:
    st.subheader(f"Grupo {selected_group}")
    table(group_standings, height=250)

    st.subheader("Partidas Restantes")
    if group_next.is_empty():
        st.info("Sem partidas restantes.")
    else:
        next_view = compact_probability_frame(
            group_next,
            [
                "match_number",
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
        table(next_view, height=250)

with right:
    st.subheader("Projecao")
    projection_view = compact_probability_frame(
        group_projection,
        [
            "team",
            "avg_points",
            "avg_goal_difference",
            "prob_group_1",
            "prob_group_2",
            "prob_group_3",
            "prob_top2",
            "prob_best_third",
            "prob_qualify",
        ],
    )
    table(projection_view, height=540)

st.divider()

st.subheader("Mapa de Classificacao")
all_projection = compact_probability_frame(
    projection.sort(["group", "prob_qualify"], descending=[False, True]),
    [
        "group",
        "team",
        "prob_group_1",
        "prob_group_2",
        "prob_group_3",
        "prob_top2",
        "prob_best_third",
        "prob_qualify",
        "prob_eliminated_group",
    ],
)
table(all_projection, height=620)
