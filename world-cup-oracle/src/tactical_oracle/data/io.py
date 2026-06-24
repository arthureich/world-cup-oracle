from __future__ import annotations

from pathlib import Path
from typing import Any


def _polars() -> Any:
    try:
        import polars as pl
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Polars is required for Parquet IO. Install project dependencies with "
            "`pip install -e '.[dev]'`."
        ) from exc
    return pl


def read_parquet(path: str | Path) -> Any:
    """Read a Parquet file with Polars."""

    return _polars().read_parquet(path)


def write_parquet(frame: Any, path: str | Path) -> None:
    """Write a Polars DataFrame to Parquet, creating the parent directory."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(destination)


def write_rows_parquet(rows: list[dict[str, Any]], path: str | Path) -> None:
    """Write row dictionaries to Parquet using Polars."""

    pl = _polars()
    write_parquet(pl.DataFrame(rows), path)

