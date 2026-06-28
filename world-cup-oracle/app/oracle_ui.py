from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import polars as pl
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from world_cup_oracle.presentation.summary import processed_path, read_processed  # noqa: E402

APP_TITLE = "World Cup Oracle"


def configure_page(title: str = APP_TITLE) -> None:
    st.set_page_config(
        page_title=title,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.4rem;
            padding-bottom: 2.5rem;
            max-width: 1480px;
        }
        h1, h2, h3 {
            letter-spacing: 0;
        }
        div[data-testid="stMetric"] {
            border: 1px solid #d8dee9;
            border-radius: 6px;
            padding: 0.7rem 0.8rem;
            background: #fbfcfe;
        }
        div[data-testid="stMetricLabel"] {
            color: #46515f;
        }
        section[data-testid="stSidebar"] {
            border-right: 1px solid #e3e8ef;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def _load_frame_cached(filename: str, modified_at_ns: int) -> pl.DataFrame:
    return read_processed(ROOT, filename)


def load_frame(filename: str) -> pl.DataFrame:
    modified_at_ns = processed_path(ROOT, filename).stat().st_mtime_ns
    return _load_frame_cached(filename, modified_at_ns)


def sidebar_context() -> None:
    st.sidebar.title(APP_TITLE)
    st.sidebar.caption("Modelo local | Poisson + Monte Carlo | TSI pos-grupos")
    st.sidebar.divider()
    st.sidebar.write("Outputs")
    st.sidebar.code("data/processed", language=None)


def pct(value: float | int | None, digits: int = 1) -> str:
    if value is None:
        return "-"
    return f"{float(value) * 100:.{digits}f}%"


def number(value: float | int | None, digits: int = 2) -> str:
    if value is None:
        return "-"
    return f"{float(value):.{digits}f}"


def signed(value: float | int | None, digits: int = 2) -> str:
    if value is None:
        return "-"
    return f"{float(value):+.{digits}f}"


def table(frame: pl.DataFrame, height: int = 440, hide_index: bool = True) -> None:
    st.dataframe(
        frame,
        width="stretch",
        height=height,
        hide_index=hide_index,
    )


def as_pandas(frame: pl.DataFrame) -> Any:
    try:
        return frame.to_pandas()
    except Exception:
        return frame


def select_team(stage_probabilities: pl.DataFrame, label: str = "Selecao") -> str:
    teams = sorted(stage_probabilities["team"].to_list())
    default = teams.index("Brazil") if "Brazil" in teams else 0
    return st.selectbox(label, teams, index=default)


def team_stage_row(stage_probabilities: pl.DataFrame, team: str) -> dict[str, Any]:
    return stage_probabilities.filter(pl.col("team") == team).row(0, named=True)


def compact_probability_frame(frame: pl.DataFrame, columns: list[str]) -> pl.DataFrame:
    output = frame.select(columns)
    percent_columns = [
        column
        for column in output.columns
        if column.startswith("prob_")
        or column.startswith("p_")
        or column in {
            "qualify_r32",
            "reach_r16",
            "reach_qf",
            "reach_sf",
            "reach_final",
            "champion",
            "probability",
            "pass_probability",
            "conditional_pass_probability",
            "appear_probability",
            "next_best_pass_probability",
            "win_probability",
            "conditional_win_probability",
        }
    ]
    return output.with_columns((pl.col(column) * 100).round(2) for column in percent_columns)


def stage_short_name(column: str) -> str:
    return {
        "qualify_r32": "R32",
        "reach_r16": "R16",
        "reach_qf": "QF",
        "reach_sf": "SF",
        "reach_final": "Final",
        "champion": "Campeao",
    }.get(column, column)


def page_header(title: str, subtitle: str | None = None) -> None:
    st.title(title)
    if subtitle:
        st.caption(subtitle)
