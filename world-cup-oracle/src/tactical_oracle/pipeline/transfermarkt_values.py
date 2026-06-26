from __future__ import annotations

import argparse
import csv
import gzip
import re
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

from tactical_oracle.data.io import read_parquet, write_rows_parquet

DEFAULT_AS_OF = date(2026, 6, 11)

# Manual name aliases for players whose World Cup source name does not match their
# Transfermarkt name (e.g. Brazilians listed by a given name instead of the nom de
# guerre). Maps (team, source_player_name) -> transfermarkt_name. Add entries as
# mismatches appear; the alias is only tried when the automatic match fails.
NAME_ALIASES: dict[tuple[str, str], str] = {
    ("Brazil", "Henrique"): "Casemiro",
}

PLAYER_ID_COLUMNS = ("player_id", "id")
PLAYER_NAME_COLUMNS = ("name", "player_name", "pretty_name")
PLAYER_DOB_COLUMNS = ("date_of_birth", "birth_date", "dob")
PLAYER_VALUE_COLUMNS = ("market_value_in_eur", "market_value_eur", "market_value")
VALUATION_DATE_COLUMNS = ("date", "valuation_date")
UPPER_CHARS = "A-ZÁÉÍÓÚÀÈÌÒÙÂÊÎÔÛÃÕÇÑ"
LOWER_CHARS = "a-záéíóúàèìòùâêîôûãõçñ"


def _ascii_key(value: str) -> str:
    value = re.sub(rf"([{UPPER_CHARS}]{{2,}})([{UPPER_CHARS}][{LOWER_CHARS}])", r"\1 \2", value)
    value = re.sub(rf"([{LOWER_CHARS}])([{UPPER_CHARS}])", r"\1 \2", value)
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    key = re.sub(r"[^a-zA-Z0-9]+", " ", ascii_value.strip().lower())
    return " ".join(key.split())


def _date_key(value: str) -> str:
    text = value.strip()
    if not text:
        return text
    try:
        return date.fromisoformat(text[:10]).isoformat()
    except ValueError:
        return text.split()[0]


def _read_csv(path: str | Path) -> list[dict[str, str]]:
    source = Path(path)
    opener = gzip.open if source.suffix == ".gz" else open
    with opener(source, "rt", encoding="utf-8-sig", newline="") as handle:
        return [
            {_ascii_key(str(key)).replace(" ", "_"): "" if value is None else str(value).strip()
             for key, value in row.items()
             if key is not None}
            for row in csv.DictReader(handle)
        ]


def _first(row: dict[str, str], columns: tuple[str, ...], source: str) -> str:
    for column in columns:
        value = row.get(column)
        if value not in (None, ""):
            return value
    raise ValueError(f"{source} is missing one of these columns: {', '.join(columns)}")


def _optional(row: dict[str, str], columns: tuple[str, ...]) -> str | None:
    for column in columns:
        value = row.get(column)
        if value not in (None, ""):
            return value
    return None


def player_match_key(name: str, date_of_birth: str) -> tuple[str, str]:
    return _ascii_key(name), _date_key(date_of_birth)


def _name_tokens(name: str) -> set[str]:
    return {token for token in _ascii_key(name).split() if len(token) > 1}


def _fallback_match_by_dob_and_tokens(
    player_name: str,
    date_of_birth: str,
    values_by_dob: dict[str, list[tuple[str, dict[str, Any]]]],
) -> dict[str, Any] | None:
    candidates = values_by_dob.get(_date_key(date_of_birth), [])
    if not candidates:
        return None

    source_tokens = _name_tokens(player_name)
    scored: list[tuple[int, dict[str, Any]]] = []
    for candidate_name_key, candidate in candidates:
        candidate_tokens = set(candidate_name_key.split())
        common = source_tokens & candidate_tokens
        if not common:
            continue
        score = len(common) * 2
        if candidate_tokens <= source_tokens or source_tokens <= candidate_tokens:
            score += 3
        scored.append((score, candidate))

    if not scored:
        return None
    scored.sort(key=lambda item: item[0], reverse=True)
    if len(scored) > 1 and scored[0][0] == scored[1][0]:
        return None
    return scored[0][1]


def latest_transfermarkt_values(
    players_csv: str | Path,
    valuations_csv: str | Path | None = None,
    as_of: date | str = DEFAULT_AS_OF,
) -> dict[tuple[str, str], dict[str, Any]]:
    cutoff = date.fromisoformat(str(as_of))
    player_rows = _read_csv(players_csv)
    players_by_id: dict[str, dict[str, str]] = {
        _first(row, PLAYER_ID_COLUMNS, "Transfermarkt players CSV"): row
        for row in player_rows
    }

    values_by_player_id: dict[str, tuple[date, float]] = {}
    if valuations_csv is not None:
        for row in _read_csv(valuations_csv):
            player_id = _first(row, PLAYER_ID_COLUMNS, "Transfermarkt valuations CSV")
            valuation_date = date.fromisoformat(
                _first(row, VALUATION_DATE_COLUMNS, "Transfermarkt valuations CSV")
            )
            if valuation_date > cutoff:
                continue
            value = float(_first(row, PLAYER_VALUE_COLUMNS, "Transfermarkt valuations CSV"))
            current = values_by_player_id.get(player_id)
            if current is None or valuation_date > current[0]:
                values_by_player_id[player_id] = (valuation_date, value)
    else:
        for player_id, row in players_by_id.items():
            value = _optional(row, PLAYER_VALUE_COLUMNS)
            if value is not None:
                values_by_player_id[player_id] = (cutoff, float(value))

    output: dict[tuple[str, str], dict[str, Any]] = {}
    for player_id, (valuation_date, value) in values_by_player_id.items():
        player = players_by_id.get(player_id)
        if player is None:
            continue
        name = _optional(player, PLAYER_NAME_COLUMNS)
        dob = _optional(player, PLAYER_DOB_COLUMNS)
        if name is None or dob is None:
            continue
        output[player_match_key(name, dob)] = {
            "transfermarkt_player_id": player_id,
            "transfermarkt_name": name,
            "date_of_birth": _date_key(dob),
            "market_value": value,
            "market_value_eur": value,
            "market_value_date": valuation_date.isoformat(),
            "market_value_source": "transfermarkt",
            "market_value_trusted": True,
        }
    return output


def apply_transfermarkt_values_to_squads(
    squads_path: str | Path,
    players_csv: str | Path,
    valuations_csv: str | Path | None = None,
    as_of: date | str = DEFAULT_AS_OF,
) -> list[dict[str, Any]]:
    values = latest_transfermarkt_values(players_csv, valuations_csv, as_of)
    values_by_dob: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for (name_key, dob), value in values.items():
        values_by_dob.setdefault(dob, []).append((name_key, value))

    def _match(name: str, dob: str) -> dict[str, Any] | None:
        return values.get(player_match_key(name, dob)) or _fallback_match_by_dob_and_tokens(
            name, dob, values_by_dob
        )

    rows: list[dict[str, Any]] = []
    for row in read_parquet(squads_path).to_dicts():
        updated = dict(row)
        name = str(row["player_name"])
        dob = str(row["date_of_birth"])
        match = _match(name, dob)
        if match is None:
            alias = NAME_ALIASES.get((str(row.get("team", "")), name))
            if alias is not None:
                match = _match(alias, dob)
        if match is not None:
            updated.update(match)
        else:
            updated["market_value_trusted"] = False
        rows.append(updated)
    return rows


def impute_team_mean_market_values(
    rows: list[dict[str, Any]],
    as_of: date | str = DEFAULT_AS_OF,
) -> list[dict[str, Any]]:
    trusted_values: dict[str, list[float]] = {}
    for row in rows:
        if not row.get("called_up", True):
            continue
        if not row.get("market_value_trusted", True):
            continue
        value = row.get("market_value")
        if value is None:
            continue
        trusted_values.setdefault(str(row["team"]), []).append(float(value))

    means = {
        team: sum(values) / len(values)
        for team, values in trusted_values.items()
        if values
    }

    output: list[dict[str, Any]] = []
    for row in rows:
        updated = {
            **row,
            "market_value_imputed": bool(row.get("market_value_imputed", False)),
            "imputed_team_mean_market_value": row.get("imputed_team_mean_market_value"),
            "imputed_from_trusted_player_count": row.get("imputed_from_trusted_player_count"),
        }
        team = str(row["team"])
        if (
            row.get("called_up", True)
            and not row.get("market_value_trusted", True)
            and team in means
        ):
            mean_value = means[team]
            updated["market_value"] = mean_value
            updated["market_value_eur"] = mean_value
            updated["market_value_source"] = "team_mean_imputed"
            updated["market_value_trusted"] = True
            updated["market_value_imputed"] = True
            updated["market_value_date"] = str(as_of)
            updated["imputed_team_mean_market_value"] = mean_value
            updated["imputed_from_trusted_player_count"] = len(trusted_values[team])
        output.append(updated)
    return output


def write_imputed_squads(
    squads_path: str | Path = "data/interim/squads.parquet",
    output_path: str | Path = "data/interim/squads.parquet",
    as_of: date | str = DEFAULT_AS_OF,
) -> Path:
    rows = impute_team_mean_market_values(
        read_parquet(squads_path).to_dicts(),
        as_of=as_of,
    )
    destination = Path(output_path)
    write_rows_parquet(rows, destination)
    return destination


def write_transfermarkt_squads(
    squads_path: str | Path = "data/interim/squads.parquet",
    players_csv: str | Path = "data/raw/transfermarkt/players.csv",
    valuations_csv: str | Path | None = "data/raw/transfermarkt/player_valuations.csv",
    output_path: str | Path = "data/interim/squads.parquet",
    as_of: date | str = DEFAULT_AS_OF,
) -> Path:
    valuations = Path(valuations_csv) if valuations_csv is not None else None
    rows = apply_transfermarkt_values_to_squads(
        squads_path=squads_path,
        players_csv=players_csv,
        valuations_csv=valuations if valuations and valuations.exists() else None,
        as_of=as_of,
    )
    destination = Path(output_path)
    write_rows_parquet(rows, destination)
    return destination


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Apply Transfermarkt values to World Cup squads.")
    parser.add_argument("--squads", default="data/interim/squads.parquet")
    parser.add_argument("--players-csv", default="data/raw/transfermarkt/players.csv")
    parser.add_argument(
        "--valuations-csv",
        default="data/raw/transfermarkt/player_valuations.csv",
    )
    parser.add_argument("--output", default="data/interim/squads.parquet")
    parser.add_argument("--as-of", default=DEFAULT_AS_OF.isoformat())
    return parser


def _build_impute_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Impute missing squad market values with each team's trusted mean."
    )
    parser.add_argument("--squads", default="data/interim/squads.parquet")
    parser.add_argument("--output", default="data/interim/squads.parquet")
    parser.add_argument("--as-of", default=DEFAULT_AS_OF.isoformat())
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    path = write_transfermarkt_squads(
        squads_path=args.squads,
        players_csv=args.players_csv,
        valuations_csv=args.valuations_csv,
        output_path=args.output,
        as_of=args.as_of,
    )
    print(path)


def impute_main() -> None:
    args = _build_impute_parser().parse_args()
    path = write_imputed_squads(
        squads_path=args.squads,
        output_path=args.output,
        as_of=args.as_of,
    )
    print(path)


if __name__ == "__main__":
    main()
