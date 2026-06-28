from __future__ import annotations

from html import escape

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
    select_team,
    signed,
    table,
    team_stage_row,
)

from world_cup_oracle.attack_defense import expected_goals
from world_cup_oracle.config import AttackDefenseParameters, SimulationParameters
from world_cup_oracle.pipeline.tournament_projection import load_knockout_template
from world_cup_oracle.simulation import match_probabilities, penalty_win_probability

STAGE_FUNNEL = [
    ("qualify_r32", "R32"),
    ("reach_r16", "Oitavas"),
    ("reach_qf", "Quartas"),
    ("reach_sf", "Semis"),
    ("reach_final", "Final"),
    ("champion", "Titulo"),
]

BRACKET_STAGES = [
    ("Round of 32", "R32"),
    ("Round of 16", "R16"),
    ("Quarter-final", "QF"),
    ("Semi-final", "SF"),
    ("Final", "Final"),
]


def _stage_leaders(
    stage_probabilities: pl.DataFrame,
    stages: tuple[str, ...] = ("reach_r16", "reach_qf", "reach_sf", "reach_final", "champion"),
) -> pl.DataFrame:
    labels = {
        "reach_r16": "Oitavas",
        "reach_qf": "Quartas",
        "reach_sf": "Semis",
        "reach_final": "Final",
        "champion": "Titulo",
    }
    rows = []
    for stage in stages:
        leader = stage_probabilities.sort(stage, descending=True).row(0, named=True)
        rows.append(
            {
                "stage": labels.get(stage, stage),
                "team": leader["team"],
                "probability": leader[stage],
            }
        )
    return pl.DataFrame(rows)


def _knockout_match_favorites(knockout_probabilities: pl.DataFrame) -> pl.DataFrame:
    rows = []
    for partition in knockout_probabilities.partition_by("match_number", maintain_order=True):
        ordered = partition.sort(
            ["win_probability", "conditional_win_probability"],
            descending=[True, True],
        )
        favorite = ordered.row(0, named=True)
        runner_up = ordered.row(1, named=True) if ordered.height > 1 else None
        rows.append(
            {
                "match_number": favorite["match_number"],
                "stage": favorite["stage"],
                "most_likely_to_pass": favorite["team"],
                "pass_probability": favorite["win_probability"],
                "conditional_pass_probability": favorite["conditional_win_probability"],
                "appear_probability": favorite["appear_probability"],
                "next_best_team": runner_up["team"] if runner_up else None,
                "next_best_pass_probability": runner_up["win_probability"] if runner_up else None,
            }
        )
    return pl.DataFrame(rows).sort("match_number")


def _current_status(row: dict[str, object]) -> str:
    if float(row.get("champion", 0.0)) >= 0.999:
        return "Campeao"
    if float(row.get("reach_final", 0.0)) >= 0.999:
        return "Final"
    if float(row.get("reach_sf", 0.0)) >= 0.999:
        return "R4"
    if float(row.get("reach_qf", 0.0)) >= 0.999:
        return "R8"
    if float(row.get("reach_r16", 0.0)) >= 0.999:
        return "R16"
    if float(row.get("qualify_r32", 0.0)) >= 0.999:
        return "R32"
    if float(row.get("prob_eliminated_group", 0.0)) >= 0.999:
        return "Eliminado"
    return "Grupo"


def _record_frame(match_audit: pl.DataFrame) -> pl.DataFrame:
    return (
        match_audit.with_columns(
            [
                (pl.col("goals") > pl.col("goals_against")).cast(pl.Int64).alias("vitorias"),
                (pl.col("goals") == pl.col("goals_against")).cast(pl.Int64).alias("empates"),
                (pl.col("goals") < pl.col("goals_against")).cast(pl.Int64).alias("derrotas"),
            ]
        )
        .group_by("team")
        .agg(
            [
                pl.sum("vitorias").alias("vitorias"),
                pl.sum("empates").alias("empates"),
                pl.sum("derrotas").alias("derrotas"),
            ]
        )
    )


def _teams_overview(
    stage_probabilities: pl.DataFrame,
    group_projection: pl.DataFrame,
    standings: pl.DataFrame,
    tsi_pre: pl.DataFrame,
    elo: pl.DataFrame,
    squad: pl.DataFrame,
    odds: pl.DataFrame,
    performance: pl.DataFrame,
    match_audit: pl.DataFrame,
) -> pl.DataFrame:
    records = _record_frame(match_audit)
    frame = (
        stage_probabilities.join(
            group_projection.select(["team", "group", "prob_eliminated_group"]),
            on="team",
            how="left",
        )
        .join(
            standings.select(["team", "position", "points", "goal_difference"]),
            on="team",
            how="left",
        )
        .join(records, on="team", how="left")
        .join(
            tsi_pre.select(["team", "tsi_pre", "squad_adjustment", "odds_adjustment"]),
            on="team",
            how="left",
        )
        .join(elo.select(["team", "adjusted_elo"]), on="team", how="left")
        .join(squad.select(["team", "squad_adjustment"]), on="team", how="left", suffix="_squad")
        .join(odds.select(["team", "odds_adjustment"]), on="team", how="left", suffix="_odds")
        .join(
            performance.select(["team", "post_groups_tsi_delta", "tsi_post_groups"]),
            on="team",
            how="left",
        )
        .with_columns(
            [
                pl.coalesce(["squad_adjustment_squad", "squad_adjustment"]).alias("elenco"),
                pl.coalesce(["odds_adjustment_odds", "odds_adjustment"]).alias("odds"),
            ]
        )
        .with_columns(
            pl.struct(
                [
                    "champion",
                    "reach_final",
                    "reach_sf",
                    "reach_qf",
                    "reach_r16",
                    "qualify_r32",
                    "prob_eliminated_group",
                ]
            )
            .map_elements(_current_status, return_dtype=pl.String)
            .alias("status")
        )
        .select(
            [
                "team",
                "status",
                "group",
                "position",
                "points",
                "vitorias",
                "empates",
                "derrotas",
                "goal_difference",
                "adjusted_elo",
                "elenco",
                "odds",
                "tsi_pre",
                "post_groups_tsi_delta",
                "tsi_post_groups",
                "qualify_r32",
                "reach_r16",
                "reach_qf",
                "reach_sf",
                "reach_final",
                "champion",
            ]
        )
        .fill_null(0)
        .rename(
            {
                "team": "Selecao",
                "status": "Status",
                "group": "Grupo",
                "position": "Pos",
                "points": "Pts",
                "vitorias": "V",
                "empates": "E",
                "derrotas": "D",
                "goal_difference": "SG",
                "adjusted_elo": "Elo",
                "elenco": "Elenco",
                "odds": "Odds",
                "tsi_pre": "TSI pre",
                "post_groups_tsi_delta": "Delta partidas",
                "tsi_post_groups": "TSI atual",
                "qualify_r32": "Prob R32",
                "reach_r16": "Prob R16",
                "reach_qf": "Prob R8",
                "reach_sf": "Prob R4",
                "reach_final": "Prob Final",
                "champion": "Prob Win",
            }
        )
        .sort(["Prob Win", "TSI atual"], descending=[True, True])
    )
    percent_columns = ["Prob R32", "Prob R16", "Prob R8", "Prob R4", "Prob Final", "Prob Win"]
    return frame.with_columns(
        [
            pl.col("Elo").round(0),
            pl.col("Elenco").round(3),
            pl.col("Odds").round(3),
            pl.col("TSI pre").round(3),
            pl.col("Delta partidas").round(3),
            pl.col("TSI atual").round(3),
            *[(pl.col(column) * 100).round(2) for column in percent_columns],
        ]
    )


def _direct_match_projection(
    team_a: str,
    team_b: str,
    components_by_team: dict[str, dict[str, object]],
) -> dict[str, object]:
    components_a = components_by_team[team_a]
    components_b = components_by_team[team_b]
    lambda_a, lambda_b = expected_goals(
        float(components_a["attack"]),
        float(components_a["defense"]),
        float(components_b["attack"]),
        float(components_b["defense"]),
        params=AttackDefenseParameters(),
    )
    probabilities = match_probabilities(
        lambda_a,
        lambda_b,
        max_goals=SimulationParameters().score_max_goals,
    )
    extra_time_probabilities = match_probabilities(
        lambda_a * SimulationParameters().extra_time_factor,
        lambda_b * SimulationParameters().extra_time_factor,
        max_goals=SimulationParameters().score_max_goals,
    )
    penalty_a = penalty_win_probability(
        float(components_a["tsi"]),
        float(components_b["tsi"]),
    )
    p_advance_a = probabilities.win_a + probabilities.draw * (
        extra_time_probabilities.win_a + extra_time_probabilities.draw * penalty_a
    )
    p_advance_b = 1.0 - p_advance_a
    return {
        "lambda_a": lambda_a,
        "lambda_b": lambda_b,
        "p_win_a": probabilities.win_a,
        "p_draw": probabilities.draw,
        "p_win_b": probabilities.win_b,
        "p_advance_a": p_advance_a,
        "p_advance_b": p_advance_b,
        "most_likely_score": (
            f"{probabilities.most_likely_score[0]}-{probabilities.most_likely_score[1]}"
        ),
    }


def _likely_bracket(knockout_probabilities: pl.DataFrame, components: pl.DataFrame) -> pl.DataFrame:
    components_by_team = {str(row["team"]): row for row in components.to_dicts()}
    knockout_template = load_knockout_template()
    match_probabilities_by_number = {}
    for frame in knockout_probabilities.partition_by("match_number", maintain_order=True):
        match_number = int(frame.row(0, named=True)["match_number"])
        match_probabilities_by_number[match_number] = frame
    team_match_probability = {
        (int(row["match_number"]), str(row["team"])): row
        for row in knockout_probabilities.to_dicts()
    }
    displayed_winners: dict[int, str] = {}
    displayed_runners_up: dict[int, str] = {}
    displayed_initial_teams: set[str] = set()
    rows = []

    def initial_side(match_number: int, excluded_teams: set[str]) -> str | None:
        ordered = match_probabilities_by_number[match_number].sort(
            ["appear_probability", "win_probability", "conditional_win_probability", "team"],
            descending=[True, True, True, False],
        )
        for row in ordered.to_dicts():
            team = str(row["team"])
            if team not in excluded_teams:
                return team
        return None

    def resolve_placeholder(
        placeholder: str,
        match_number: int,
        excluded_teams: set[str],
    ) -> str | None:
        if placeholder.startswith("W"):
            return displayed_winners.get(int(placeholder[1:]))
        if placeholder.startswith("RU"):
            return displayed_runners_up.get(int(placeholder[2:]))
        return initial_side(match_number, excluded_teams)

    for fixture in knockout_template:
        match_number = int(fixture["match_number"])
        if str(fixture["stage"]) == "Play-off for third place":
            continue
        team_a = resolve_placeholder(
            str(fixture["placeholder_a"]),
            match_number,
            displayed_initial_teams,
        )
        side_b_exclusions = displayed_initial_teams | ({team_a} if team_a else set())
        team_b = resolve_placeholder(
            str(fixture["placeholder_b"]),
            match_number,
            side_b_exclusions,
        )
        if team_a is None or team_b is None:
            continue
        if not str(fixture["placeholder_a"]).startswith(("W", "RU")):
            displayed_initial_teams.add(team_a)
        if not str(fixture["placeholder_b"]).startswith(("W", "RU")):
            displayed_initial_teams.add(team_b)

        projection = _direct_match_projection(team_a, team_b, components_by_team)
        winner = team_a if projection["p_advance_a"] >= projection["p_advance_b"] else team_b
        runner_up = team_b if winner == team_a else team_a
        displayed_winners[match_number] = winner
        displayed_runners_up[match_number] = runner_up

        side_a = team_match_probability.get((match_number, team_a), {})
        side_b = team_match_probability.get((match_number, team_b), {})
        winner_side = side_a if winner == team_a else side_b
        team_a_appear = float(side_a.get("appear_probability", 0.0))
        team_b_appear = float(side_b.get("appear_probability", 0.0))

        rows.append(
            {
                "match_number": match_number,
                "stage": fixture["stage"],
                "team_a": team_a,
                "team_b": team_b,
                "winner": winner,
                "winner_pass_probability": winner_side.get("conditional_win_probability"),
                "team_a_appear_probability": team_a_appear,
                "team_b_appear_probability": team_b_appear,
                "duel_occurrence_probability": min(team_a_appear, team_b_appear),
                "is_confirmed": team_a_appear >= 0.999 and team_b_appear >= 0.999,
                **projection,
            }
        )
    return pl.DataFrame(rows).sort("match_number")


def _render_match_card(row: dict[str, object], target: object) -> None:
    lambda_a = number(float(row["lambda_a"]), 2)
    lambda_b = number(float(row["lambda_b"]), 2)
    winner = str(row["winner"])
    team_a = str(row["team_a"])
    team_b = str(row["team_b"])
    is_confirmed = bool(row["is_confirmed"])
    border_color = "#2e7d32" if is_confirmed else "#d6a100"
    background = "#f7fbf7" if is_confirmed else "#fffaf0"
    status = "Confirmado"
    if not is_confirmed:
        status = (
            f"Duelo ~{pct(float(row['duel_occurrence_probability']), 0)} | "
            f"{team_a} {pct(float(row['team_a_appear_probability']), 0)} · "
            f"{team_b} {pct(float(row['team_b_appear_probability']), 0)}"
        )
    team_a_weight = "800" if team_a == winner else "500"
    team_b_weight = "800" if team_b == winner else "500"
    target.markdown(
        f"""
        <div style="
            border: 1.5px solid {border_color};
            border-radius: 6px;
            background: {background};
            padding: 6px 7px;
            margin: 0 0 7px 0;
            font-size: 12px;
            line-height: 1.18;
        ">
          <div style="color:#697586;font-size:10px;margin-bottom:3px;">
            Jogo {row["match_number"]} · {escape(status)}
          </div>
          <div style="display:flex;justify-content:space-between;gap:6px;
                      font-weight:{team_a_weight};">
            <span>{escape(team_a)}</span><span>{pct(float(row["p_advance_a"]), 0)}</span>
          </div>
          <div style="display:flex;justify-content:space-between;gap:6px;
                      font-weight:{team_b_weight};">
            <span>{escape(team_b)}</span><span>{pct(float(row["p_advance_b"]), 0)}</span>
          </div>
          <div style="color:#697586;font-size:10px;margin-top:4px;">
            xG {lambda_a} - {lambda_b}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_bracket(bracket: pl.DataFrame) -> None:
    columns = st.columns(len(BRACKET_STAGES))
    for column, (stage, label) in zip(columns, BRACKET_STAGES, strict=True):
        stage_rows = bracket.filter(pl.col("stage") == stage).to_dicts()
        column.markdown(f"**{label}**")
        for row in stage_rows:
            _render_match_card(row, column)


def _next_knockout_matches(bracket: pl.DataFrame) -> pl.DataFrame:
    first_stage = bracket.sort("match_number").row(0, named=True)["stage"]
    return (
        bracket.filter(pl.col("stage") == first_stage)
        .with_columns(
            [
                (pl.col("team_a") + " x " + pl.col("team_b")).alias("Duelo"),
                pl.when(pl.col("is_confirmed")).then(pl.lit("Confirmado")).otherwise(pl.lit("Projetado")).alias("Status"),
                pl.when(pl.col("p_advance_a") >= pl.col("p_advance_b"))
                .then(pl.col("team_a"))
                .otherwise(pl.col("team_b"))
                .alias("Mais provavel"),
            ]
        )
        .select(
            [
                "match_number",
                "Status",
                "Duelo",
                "duel_occurrence_probability",
                "lambda_a",
                "lambda_b",
                "p_win_a",
                "p_draw",
                "p_win_b",
                "p_advance_a",
                "p_advance_b",
                "Mais provavel",
            ]
        )
        .rename(
            {
                "match_number": "Jogo",
                "duel_occurrence_probability": "Prob duelo",
                "lambda_a": "xG A",
                "lambda_b": "xG B",
                "p_win_a": "Vit A 90",
                "p_draw": "Empate 90",
                "p_win_b": "Vit B 90",
                "p_advance_a": "Avanca A",
                "p_advance_b": "Avanca B",
            }
        )
        .with_columns(
            [
                pl.col("xG A").round(2),
                pl.col("xG B").round(2),
                *[
                    (pl.col(column) * 100).round(1)
                    for column in [
                        "Prob duelo",
                        "Vit A 90",
                        "Empate 90",
                        "Vit B 90",
                        "Avanca A",
                        "Avanca B",
                    ]
                ],
            ]
        )
        .sort("Jogo")
    )


def _stage_probability_rows(row: dict[str, object]) -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "stage": label,
                "probability": float(row[column]),
            }
            for column, label in STAGE_FUNNEL
        ]
    )


def _selected_team_context(
    team: str,
    group_projection: pl.DataFrame,
    performance: pl.DataFrame,
    attack_defense: pl.DataFrame,
) -> dict[str, object]:
    context: dict[str, object] = {}
    group = group_projection.filter(pl.col("team") == team)
    perf = performance.filter(pl.col("team") == team)
    components = attack_defense.filter(pl.col("team") == team)
    if not group.is_empty():
        context.update(group.row(0, named=True))
    if not perf.is_empty():
        context.update(perf.row(0, named=True))
    if not components.is_empty():
        context.update(components.row(0, named=True))
    return context


configure_page("World Cup Oracle | Simulacao")

stage = load_frame("team_stage_probabilities.parquet")
next_matches = load_frame("next_matches.parquet")
group_projection = load_frame("group_projection.parquet")
team_performance = load_frame("team_performance_adjustments.parquet")
attack_defense = load_frame("attack_defense_post_groups.parquet")
knockout = load_frame("knockout_match_probabilities.parquet")
standings = load_frame("current_group_standings.parquet")
tsi_pre = load_frame("tsi_pre_cup.parquet")
elo = load_frame("ratings_elo.parquet")
squad = load_frame("squad_adjustments.parquet")
odds = load_frame("odds_adjustments.parquet")
match_audit = load_frame("match_performance_audit.parquet")

page_header("Simulacao da Copa", "Probabilidades atuais com TSI pos-grupos, Poisson e Monte Carlo")

leaders = _stage_leaders(
    stage,
    stages=("reach_r16", "reach_qf", "reach_sf", "reach_final", "champion"),
)
favorite = stage.sort("champion", descending=True).row(0, named=True)
finalist = stage.sort("reach_final", descending=True).row(0, named=True)
semi = stage.sort("reach_sf", descending=True).row(0, named=True)

top = st.columns(4)
top[0].metric("Maior chance de titulo", favorite["team"], pct(favorite["champion"]))
top[1].metric("Maior chance de final", finalist["team"], pct(finalist["reach_final"]))
top[2].metric("Maior chance de semi", semi["team"], pct(semi["reach_sf"]))
top[3].metric(
    "Simulacoes",
    f"{stage.height} selecoes",
    f"{number(stage['champion'].sum(), 2)} titulo",
)

st.divider()

leader_cols = st.columns(len(leaders))
for column, row in zip(leader_cols, leaders.to_dicts(), strict=True):
    column.metric(str(row["stage"]), str(row["team"]), pct(row["probability"]))

st.divider()

st.subheader("Simulação - Knockout Stage")
likely_bracket = _likely_bracket(knockout, attack_defense)
_render_bracket(likely_bracket)

st.divider()

st.subheader("Proximas partidas")
if next_matches.is_empty():
    st.caption("Fase de grupos encerrada. Mostrando os confrontos atuais do mata-mata.")
    table(_next_knockout_matches(likely_bracket), height=430)
else:
    next_view = (
        next_matches.sort("match_number")
        .with_columns(
            [
                (pl.col("team_a") + " x " + pl.col("team_b")).alias("Duelo"),
                pl.when(pl.col("expected_points_a") >= pl.col("expected_points_b"))
                .then(pl.col("team_a"))
                .otherwise(pl.col("team_b"))
                .alias("Favorito"),
            ]
        )
        .select(
            [
                "match_number",
                "group",
                "Duelo",
                "lambda_a",
                "lambda_b",
                "p_win_a",
                "p_draw",
                "p_win_b",
                "expected_points_a",
                "expected_points_b",
                "most_likely_score",
                "Favorito",
            ]
        )
        .rename(
            {
                "match_number": "Jogo",
                "group": "Grupo",
                "lambda_a": "xG A",
                "lambda_b": "xG B",
                "p_win_a": "Vit A",
                "p_draw": "Empate",
                "p_win_b": "Vit B",
                "expected_points_a": "Pts esp A",
                "expected_points_b": "Pts esp B",
                "most_likely_score": "Placar provavel",
            }
        )
        .with_columns(
            [
                pl.col("xG A").round(2),
                pl.col("xG B").round(2),
                pl.col("Pts esp A").round(2),
                pl.col("Pts esp B").round(2),
                *[(pl.col(column) * 100).round(1) for column in ["Vit A", "Empate", "Vit B"]],
            ]
        )
    )
    table(next_view, height=430)

st.subheader("Tabela geral das selecoes")
team_overview = _teams_overview(
    stage,
    group_projection,
    standings,
    tsi_pre,
    elo,
    squad,
    odds,
    team_performance,
    match_audit,
)
table(team_overview, height=520)

st.divider()

chart_left, chart_right = st.columns([1.0, 1.0])

with chart_left:
    st.subheader("Top titulo")
    top_title = compact_probability_frame(
        stage.sort("champion", descending=True).head(14),
        ["team", "reach_qf", "reach_sf", "reach_final", "champion"],
    )
    st.bar_chart(as_pandas(top_title), x="team", y="champion", height=320)

with chart_right:
    st.subheader("Times mais provaveis por etapa")
    leader_table = compact_probability_frame(leaders, ["stage", "team", "probability"])
    table(leader_table, height=320)

st.divider()

st.subheader("Busca por selecao")
selected_team = select_team(stage, "Selecao")
selected_stage = team_stage_row(stage, selected_team)
selected_context = _selected_team_context(
    selected_team,
    group_projection,
    team_performance,
    attack_defense,
)
team_funnel = _stage_probability_rows(selected_stage)

team_cols = st.columns(5)
team_cols[0].metric("Grupo", str(selected_context.get("group", "-")))
team_cols[1].metric("TSI pos-grupos", number(selected_context.get("tsi_post_groups"), 2))
team_cols[2].metric("Ataque", number(selected_context.get("attack"), 2))
team_cols[3].metric("Defesa", number(selected_context.get("defense"), 2))
team_cols[4].metric("Delta TSI", signed(selected_context.get("post_groups_tsi_delta"), 2))

funnel_left, funnel_right = st.columns([1.0, 1.0])
with funnel_left:
    team_funnel_view = compact_probability_frame(team_funnel, ["stage", "probability"])
    st.bar_chart(as_pandas(team_funnel_view), x="stage", y="probability", height=320)

with funnel_right:
    details = compact_probability_frame(team_funnel, ["stage", "probability"])
    table(details, height=320)

st.caption(
    "As tabelas usam os arquivos em data/processed. "
    "Recalcule os outputs apos mudar parametros."
)
