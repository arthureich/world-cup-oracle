from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from tactical_oracle.data.io import write_rows_parquet
from tactical_oracle.odds import american_to_decimal


def normalized_outright_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    raw_probability_total = 0.0

    for row in rows:
        american_odd = float(row["american_odd"])
        decimal_odd = american_to_decimal(american_odd)
        raw_probability = 1.0 / decimal_odd
        raw_probability_total += raw_probability
        enriched.append(
            {
                "snapshot_date": str(row["snapshot_date"]),
                "source": str(row["source"]),
                "bookmaker": str(row["bookmaker"]),
                "source_team": str(row.get("source_team", row["team"])),
                "team": str(row["team"]),
                "market": str(row.get("market", "champion")),
                "american_odd": american_odd,
                "champion": decimal_odd,
                "champion_probability_raw": raw_probability,
            }
        )

    if raw_probability_total <= 0:
        raise ValueError("outright snapshot must have positive implied probability mass")

    return [
        {
            **row,
            "champion_probability_devig": row["champion_probability_raw"]
            / raw_probability_total,
        }
        for row in enriched
    ]


def read_manual_outrights_csv(path: str | Path) -> list[dict[str, Any]]:
    try:
        import polars as pl
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Polars is required for CSV normalization. Install project dependencies with "
            "`pip install -e '.[dev]'`."
        ) from exc

    return pl.read_csv(path).to_dicts()


def normalize_manual_outrights(
    input_path: str | Path = "data/raw/manual/odds_worldcup_winner_snapshot.csv",
    output_path: str | Path = "data/interim/odds_long_term.parquet",
) -> Path:
    rows = normalized_outright_rows(read_manual_outrights_csv(input_path))
    destination = Path(output_path)
    write_rows_parquet(rows, destination)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normalize a manual World Cup winner odds snapshot."
    )
    parser.add_argument(
        "--input",
        default="data/raw/manual/odds_worldcup_winner_snapshot.csv",
        help=(
            "CSV with snapshot_date, source, bookmaker, team, market and american_odd. "
            "source_team is optional."
        ),
    )
    parser.add_argument("--output", default="data/interim/odds_long_term.parquet")
    args = parser.parse_args()

    print(normalize_manual_outrights(args.input, args.output))


if __name__ == "__main__":
    main()
