from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from tactical_oracle.data.io import write_rows_parquet
from tactical_oracle.data.schemas import FifaPoints, Match, parse_date

CYCLE_START = date(2022, 12, 19)
CYCLE_END = date(2026, 6, 11)

TEAM_NAME_ALIASES = {
    "cabo_verde": "Cape Verde",
    "cape_verde_islands": "Cape Verde",
    "china_pr": "China",
    "congo_dr": "DR Congo",
    "cote_d_ivoire": "Ivory Coast",
    "curacao": "Curacao",
    "czechia": "Czech Republic",
    "brunei_darussalam": "Brunei",
    "chinese_taipei": "Taiwan",
    "ir_iran": "Iran",
    "korea_republic": "South Korea",
    "korea_dpr": "North Korea",
    "kyrgyz_republic": "Kyrgyzstan",
    "sao_tome_and_principe": "Sao Tome and Principe",
    "st_kitts_and_nevis": "Saint Kitts and Nevis",
    "st_lucia": "Saint Lucia",
    "st_vincent_and_the_grenadines": "Saint Vincent and the Grenadines",
    "the_gambia": "Gambia",
    "turkiye": "Turkey",
    "us_virgin_islands": "United States Virgin Islands",
    "u_s_virgin_islands": "United States Virgin Islands",
    "usa": "United States",
    "united_states_of_america": "United States",
}

FIFA_TEAM_COLUMNS = ("team", "country", "country_full", "nation", "association", "team_name")
FIFA_POINTS_COLUMNS = ("fifa_points", "points", "total_points", "pts")
FIFA_RANK_COLUMNS = ("fifa_rank", "rank", "rk", "ranking", "position")
FIFA_DATE_COLUMNS = ("ranking_date", "rank_date", "date")


def _ascii_key(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    key = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_value.strip().lower())
    return key.strip("_")


def normalize_team_name(value: Any) -> str:
    cleaned = " ".join(str(value).strip().split())
    if not cleaned:
        raise ValueError("team name cannot be empty")
    return TEAM_NAME_ALIASES.get(_ascii_key(cleaned), cleaned)


def _slug(value: str) -> str:
    return _ascii_key(value).replace("_", "-")


def _read_csv_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows: list[dict[str, str]] = []
        for raw_row in reader:
            rows.append(
                {
                    _ascii_key(str(key)): "" if value is None else str(value).strip()
                    for key, value in raw_row.items()
                    if key is not None
                }
            )
        return rows


def _required(row: dict[str, str], candidates: tuple[str, ...], source: str) -> str:
    for column in candidates:
        value = row.get(column)
        if value not in (None, ""):
            return value
    raise ValueError(f"{source} is missing one of these columns: {', '.join(candidates)}")


def _optional(row: dict[str, str], candidates: tuple[str, ...], default: str = "") -> str:
    for column in candidates:
        value = row.get(column)
        if value not in (None, ""):
            return value
    return default


def _parse_bool(value: Any, default: bool = False) -> bool:
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "t", "yes", "y", "sim"}:
        return True
    if normalized in {"0", "false", "f", "no", "n", "nao", "não"}:
        return False
    raise ValueError(f"cannot parse boolean value: {value}")


def _parse_int(value: Any, field: str) -> int:
    try:
        return int(float(str(value).strip()))
    except ValueError as exc:
        raise ValueError(f"cannot parse integer field {field}: {value}") from exc


def infer_match_type(competition: str, stage: str = "") -> str:
    key = f"{_ascii_key(competition)} {_ascii_key(stage)}"
    if "friendly" in key:
        return "friendly"
    if "qualification" in key or "qualifier" in key or "qualifying" in key:
        return "qualifier"
    if "nations_league" in key:
        return "nations_league"
    if "world_cup" in key and "knockout" in key:
        return "world_cup_knockout"
    if "world_cup" in key and "group" in key:
        return "world_cup_group"
    if any(term in key for term in ("final", "semi", "quarter", "knockout", "playoff")):
        return "continental_knockout"
    if any(
        term in key
        for term in (
            "afcon",
            "africa_cup",
            "asian_cup",
            "copa_america",
            "euro",
            "gold_cup",
            "ofc_nations",
        )
    ):
        return "continental_group"
    return "friendly"


def infer_stage(competition: str, stage: str = "") -> str:
    if stage:
        return stage
    match_type = infer_match_type(competition, stage)
    if match_type.endswith("knockout"):
        return "knockout"
    if match_type == "qualifier":
        return "qualifier"
    if match_type == "friendly":
        return "single"
    return "group"


def _shootout_key(row: dict[str, str]) -> tuple[date, str, str]:
    played_at = parse_date(_required(row, ("date",), "shootouts.csv"))
    home = normalize_team_name(_required(row, ("home_team", "home"), "shootouts.csv"))
    away = normalize_team_name(_required(row, ("away_team", "away"), "shootouts.csv"))
    return played_at, home, away


def read_kaggle_shootouts(path: str | Path | None) -> dict[tuple[date, str, str], str]:
    if path is None:
        return {}
    shootouts: dict[tuple[date, str, str], str] = {}
    for row in _read_csv_rows(path):
        winner = normalize_team_name(_required(row, ("winner", "penalty_winner"), "shootouts.csv"))
        shootouts[_shootout_key(row)] = winner
    return shootouts


def normalize_kaggle_matches(
    results_csv: str | Path,
    shootouts_csv: str | Path | None = None,
    start_date: date | str = CYCLE_START,
    end_date: date | str = CYCLE_END,
) -> list[dict[str, Any]]:
    start = parse_date(start_date)
    end = parse_date(end_date)
    shootouts = read_kaggle_shootouts(shootouts_csv)
    rows: list[dict[str, Any]] = []
    seen_ids: Counter[str] = Counter()

    for index, row in enumerate(_read_csv_rows(results_csv), start=1):
        played_at = parse_date(_required(row, ("date",), "results.csv"))
        if not (start <= played_at < end):
            continue

        team_a = normalize_team_name(_required(row, ("home_team", "home"), "results.csv"))
        team_b = normalize_team_name(_required(row, ("away_team", "away"), "results.csv"))
        goals_a = _parse_int(_required(row, ("home_score", "goals_a"), "results.csv"), "home_score")
        goals_b = _parse_int(_required(row, ("away_score", "goals_b"), "results.csv"), "away_score")
        competition = _optional(row, ("tournament", "competition"), "Unknown")
        source_stage = _optional(row, ("stage", "round"), "")
        neutral_site = _parse_bool(_optional(row, ("neutral", "neutral_site"), "true"), True)
        shootout_winner = shootouts.get((played_at, team_a, team_b))
        went_to_penalties = goals_a == goals_b and shootout_winner is not None

        base_id = f"kaggle-{played_at.isoformat()}-{_slug(team_a)}-{_slug(team_b)}"
        seen_ids[base_id] += 1
        match_id = base_id if seen_ids[base_id] == 1 else f"{base_id}-{index}"

        parsed = Match(
            match_id=match_id,
            date=played_at,
            team_a=team_a,
            team_b=team_b,
            goals_a=goals_a,
            goals_b=goals_b,
            competition=competition,
            stage=infer_stage(competition, source_stage),
            match_type=infer_match_type(competition, source_stage),
            home_team=None if neutral_site else team_a,
            neutral_site=neutral_site,
            went_to_penalties=went_to_penalties,
            penalty_winner=shootout_winner if went_to_penalties else None,
        )
        item = parsed.__dict__
        item["date"] = parsed.date.isoformat()
        rows.append(item)
    return rows


def normalize_fifa_ranking(
    ranking_csv: str | Path,
    ranking_date: date | str | None = None,
) -> list[dict[str, Any]]:
    if Path(ranking_csv).suffix.lower() == ".json":
        return normalize_fifa_api_ranking(ranking_csv, ranking_date=ranking_date)

    rows: list[dict[str, Any]] = []
    for row in _read_csv_rows(ranking_csv):
        row_ranking_date = ranking_date or _optional(row, FIFA_DATE_COLUMNS)
        if not row_ranking_date:
            raise ValueError(
                "FIFA ranking CSV needs a ranking_date/date column or --ranking-date"
            )
        parsed = FifaPoints(
            team=normalize_team_name(_required(row, FIFA_TEAM_COLUMNS, "fifa ranking CSV")),
            fifa_points=float(_required(row, FIFA_POINTS_COLUMNS, "fifa ranking CSV")),
            ranking_date=row_ranking_date,
            fifa_rank=_parse_int(_required(row, FIFA_RANK_COLUMNS, "fifa ranking CSV"), "rank"),
        )
        item = parsed.__dict__
        item["ranking_date"] = parsed.ranking_date.isoformat()
        rows.append(item)
    return rows


def _fifa_api_team_name(row: dict[str, Any]) -> str:
    names = row.get("TeamName") or []
    for item in names:
        if item.get("Locale") == "en-GB" and item.get("Description"):
            return str(item["Description"])
    for item in names:
        if item.get("Description"):
            return str(item["Description"])
    raise ValueError(f"FIFA ranking row has no TeamName description: {row}")


def normalize_fifa_api_ranking(
    ranking_json: str | Path,
    ranking_date: date | str | None = None,
) -> list[dict[str, Any]]:
    with Path(ranking_json).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    output: list[dict[str, Any]] = []
    for row in payload.get("Results", []):
        row_ranking_date = ranking_date or str(row["PubDate"])[:10]
        parsed = FifaPoints(
            team=normalize_team_name(_fifa_api_team_name(row)),
            fifa_points=float(row.get("DecimalTotalPoints", row["TotalPoints"])),
            ranking_date=row_ranking_date,
            fifa_rank=_parse_int(row["Rank"], "Rank"),
        )
        item = parsed.__dict__
        item["ranking_date"] = parsed.ranking_date.isoformat()
        output.append(item)
    return output


def write_data_spike_outputs(
    kaggle_results: str | Path | None = None,
    kaggle_shootouts: str | Path | None = None,
    fifa_ranking: str | Path | None = None,
    output_dir: str | Path = "data/interim",
    ranking_date: date | str | None = None,
    start_date: date | str = CYCLE_START,
    end_date: date | str = CYCLE_END,
) -> list[Path]:
    output_path = Path(output_dir)
    written: list[Path] = []

    if kaggle_results is not None:
        matches = normalize_kaggle_matches(
            kaggle_results,
            shootouts_csv=kaggle_shootouts,
            start_date=start_date,
            end_date=end_date,
        )
        destination = output_path / "matches_cycle.parquet"
        write_rows_parquet(matches, destination)
        written.append(destination)

    if fifa_ranking is not None:
        points = normalize_fifa_ranking(fifa_ranking, ranking_date=ranking_date)
        destination = output_path / "fifa_points.parquet"
        write_rows_parquet(points, destination)
        written.append(destination)

    if not written:
        raise ValueError("provide --kaggle-results and/or --fifa-ranking")
    return written


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Normalize local data-spike CSV files into World Cup Oracle Parquet inputs."
    )
    parser.add_argument("--kaggle-results", help="Path to Kaggle/martj42 results.csv")
    parser.add_argument("--kaggle-shootouts", help="Optional path to Kaggle/martj42 shootouts.csv")
    parser.add_argument("--fifa-ranking", help="Path to a FIFA ranking CSV")
    parser.add_argument("--ranking-date", help="Ranking date when the FIFA CSV has no date column")
    parser.add_argument("--output-dir", default="data/interim")
    parser.add_argument("--start-date", default=CYCLE_START.isoformat())
    parser.add_argument("--end-date", default=CYCLE_END.isoformat())
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    written = write_data_spike_outputs(
        kaggle_results=args.kaggle_results,
        kaggle_shootouts=args.kaggle_shootouts,
        fifa_ranking=args.fifa_ranking,
        output_dir=args.output_dir,
        ranking_date=args.ranking_date,
        start_date=args.start_date,
        end_date=args.end_date,
    )
    for path in written:
        print(path)


if __name__ == "__main__":
    main()
