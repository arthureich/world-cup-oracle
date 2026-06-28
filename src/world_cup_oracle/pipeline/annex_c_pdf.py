from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from world_cup_oracle.data.io import write_rows_parquet
from world_cup_oracle.simulation.annex_c import (
    ANNEX_C_WINNER_SLOTS,
    EXPECTED_ANNEX_C_COMBINATIONS,
    build_annex_c_table,
    validate_annex_c_table,
)

OPTION_ROW_PATTERN = re.compile(
    r"^\s*(\d{1,3})\s+"
    r"(3[A-L])\s+(3[A-L])\s+(3[A-L])\s+(3[A-L])\s+"
    r"(3[A-L])\s+(3[A-L])\s+(3[A-L])\s+(3[A-L])\s*$"
)


def _extract_pdf_text(pdf_path: str | Path) -> str:
    try:
        from pypdf import PdfReader
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "pypdf is required to extract Annex C PDFs. Install it with "
            "`python -m pip install pypdf`."
        ) from exc

    reader = PdfReader(pdf_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def annex_c_rows_from_pdf_text(text: str) -> list[dict[str, Any]]:
    rows_by_option: dict[int, dict[str, Any]] = {}

    for line in text.splitlines():
        match = OPTION_ROW_PATTERN.match(line)
        if match is None:
            continue

        option = int(match.group(1))
        if not 1 <= option <= EXPECTED_ANNEX_C_COMBINATIONS:
            continue
        assignments = dict(zip(ANNEX_C_WINNER_SLOTS, match.groups()[1:], strict=True))
        qualified_thirds = "".join(sorted(target[1] for target in assignments.values()))
        rows_by_option[option] = {
            "option": option,
            "qualified_thirds": qualified_thirds,
            **assignments,
        }

    expected_options = set(range(1, EXPECTED_ANNEX_C_COMBINATIONS + 1))
    missing = sorted(expected_options - set(rows_by_option))
    if missing:
        raise ValueError(f"Annex C PDF extraction missed option rows: {missing[:20]}")

    rows = [rows_by_option[index] for index in sorted(rows_by_option)]
    table = build_annex_c_table(rows)
    validate_annex_c_table(table, expected_combinations=EXPECTED_ANNEX_C_COMBINATIONS)
    return rows


def extract_annex_c_pdf(
    pdf_path: str | Path = "data/raw/annex-c.pdf",
    output_path: str | Path = "data/interim/worldcup_annex_c.parquet",
) -> Path:
    rows = annex_c_rows_from_pdf_text(_extract_pdf_text(pdf_path))
    destination = Path(output_path)
    write_rows_parquet(rows, destination)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract Annex C combinations from FIFA PDF.")
    parser.add_argument("--pdf", default="data/raw/annex-c.pdf")
    parser.add_argument("--output", default="data/interim/worldcup_annex_c.parquet")
    args = parser.parse_args()

    print(extract_annex_c_pdf(args.pdf, args.output))


if __name__ == "__main__":
    main()
