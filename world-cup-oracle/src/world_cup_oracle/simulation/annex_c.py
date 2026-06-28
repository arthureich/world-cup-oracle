from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from world_cup_oracle.data.io import read_parquet

ANNEX_C_WINNER_SLOTS = ("1A", "1B", "1D", "1E", "1G", "1I", "1K", "1L")
EXPECTED_ANNEX_C_COMBINATIONS = 495


@dataclass(frozen=True)
class AnnexCRow:
    qualified_thirds: str
    assignments: dict[str, str]


def normalize_qualified_thirds(groups: str) -> str:
    normalized = "".join(sorted(groups.replace(",", "").replace(" ", "").upper()))
    if len(normalized) != 8 or len(set(normalized)) != 8:
        raise ValueError("qualified third-place groups must contain exactly 8 unique groups")
    return normalized


def annex_c_row_from_mapping(row: Mapping[str, Any]) -> AnnexCRow:
    qualified = normalize_qualified_thirds(str(row["qualified_thirds"]))
    assignments = {slot: str(row[slot]).upper() for slot in ANNEX_C_WINNER_SLOTS}
    for target in assignments.values():
        if len(target) != 2 or target[0] != "3":
            raise ValueError(f"invalid Annex C target: {target}")
        if target[1] not in qualified:
            raise ValueError(f"Annex C target {target} is not in qualified thirds {qualified}")
    return AnnexCRow(qualified_thirds=qualified, assignments=assignments)


def build_annex_c_table(rows: list[Mapping[str, Any]]) -> dict[str, AnnexCRow]:
    table: dict[str, AnnexCRow] = {}
    for row in rows:
        parsed = annex_c_row_from_mapping(row)
        if parsed.qualified_thirds in table:
            raise ValueError(f"duplicate Annex C combination: {parsed.qualified_thirds}")
        table[parsed.qualified_thirds] = parsed
    return table


def validate_annex_c_table(
    table: Mapping[str, AnnexCRow],
    expected_combinations: int | None = None,
) -> None:
    if not table:
        raise ValueError("Annex C table cannot be empty")
    if expected_combinations is not None and len(table) != expected_combinations:
        raise ValueError(
            f"Annex C table has {len(table)} combinations, expected {expected_combinations}"
        )
    for key, row in table.items():
        if key != row.qualified_thirds:
            raise ValueError(f"Annex C key mismatch: {key} != {row.qualified_thirds}")
        if set(row.assignments) != set(ANNEX_C_WINNER_SLOTS):
            raise ValueError(f"Annex C row {key} does not define every winner slot")


def load_annex_c_table(
    path: str | Path,
    require_complete: bool = False,
) -> dict[str, AnnexCRow]:
    rows = read_parquet(path).to_dicts()
    table = build_annex_c_table(rows)
    validate_annex_c_table(
        table,
        expected_combinations=EXPECTED_ANNEX_C_COMBINATIONS if require_complete else None,
    )
    return table


def annex_c_assignments(
    qualified_third_groups: str,
    table: Mapping[str, AnnexCRow],
) -> dict[str, str]:
    key = normalize_qualified_thirds(qualified_third_groups)
    try:
        return dict(table[key].assignments)
    except KeyError as exc:
        raise ValueError(f"Annex C combination not loaded: {key}") from exc


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Validate an Annex C Parquet table.")
    parser.add_argument("path", nargs="?", default="data/interim/worldcup_annex_c.parquet")
    parser.add_argument("--complete", action="store_true", help="require all 495 combinations")
    args = parser.parse_args()

    table = load_annex_c_table(args.path, require_complete=args.complete)
    print(f"loaded {len(table)} Annex C combinations from {args.path}")


if __name__ == "__main__":
    main()
