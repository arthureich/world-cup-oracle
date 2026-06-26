from __future__ import annotations

import gzip

from tactical_oracle.data.io import read_parquet, write_rows_parquet
from tactical_oracle.pipeline.transfermarkt_values import (
    apply_transfermarkt_values_to_squads,
    impute_team_mean_market_values,
    write_transfermarkt_squads,
)


def test_apply_transfermarkt_values_matches_name_and_birth_date(tmp_path) -> None:
    squads = tmp_path / "squads.parquet"
    players = tmp_path / "players.csv"
    valuations = tmp_path / "player_valuations.csv"
    write_rows_parquet(
        [
            {
                "player_id": "wc-1",
                "player_name": "Lionel Andrés Messi",
                "team": "Argentina",
                "date_of_birth": "1987-06-24",
                "age": 38.0,
                "sector": "ATA",
                "market_value": 999.0,
                "called_up": True,
            },
            {
                "player_id": "wc-2",
                "player_name": "Unmatched Player",
                "team": "Argentina",
                "date_of_birth": "1999-01-01",
                "age": 27.0,
                "sector": "MEI",
                "market_value": 999.0,
                "called_up": True,
            },
        ],
        squads,
    )
    players.write_text(
        "\n".join(
            [
                "player_id,name,date_of_birth",
                "tm-1,Lionel Andres Messi,1987-06-24 00:00:00",
                "tm-missing,Missing Birth Date,",
            ]
        ),
        encoding="utf-8",
    )
    valuations.write_text(
        "\n".join(
            [
                "player_id,date,market_value_in_eur",
                "tm-1,2026-01-01,25000000",
                "tm-1,2026-06-12,30000000",
                "tm-missing,2026-01-01,1000000",
            ]
        ),
        encoding="utf-8",
    )

    rows = apply_transfermarkt_values_to_squads(
        squads,
        players,
        valuations,
        as_of="2026-06-11",
    )

    assert rows[0]["market_value"] == 25_000_000.0
    assert rows[0]["market_value_source"] == "transfermarkt"
    assert rows[0]["market_value_trusted"] is True
    assert rows[0]["market_value_date"] == "2026-01-01"
    assert rows[1]["market_value"] == 999.0
    assert rows[1]["market_value_trusted"] is False


def test_apply_transfermarkt_values_uses_name_alias_when_match_fails(tmp_path) -> None:
    squads = tmp_path / "squads.parquet"
    players = tmp_path / "players.csv"
    write_rows_parquet(
        [
            {
                "player_id": "wc-1",
                "player_name": "Henrique",
                "team": "Brazil",
                "date_of_birth": "1992-02-23",
                "age": 34.0,
                "sector": "MEI",
                "market_value": 999.0,
                "called_up": True,
            }
        ],
        squads,
    )
    players.write_text(
        "\n".join(
            [
                "player_id,name,date_of_birth,market_value_in_eur",
                "tm-9,Casemiro,1992-02-23,20000000",
            ]
        ),
        encoding="utf-8",
    )

    rows = apply_transfermarkt_values_to_squads(squads, players, None, as_of="2026-06-11")

    assert rows[0]["market_value"] == 20_000_000.0
    assert rows[0]["market_value_trusted"] is True
    assert rows[0]["transfermarkt_name"] == "Casemiro"


def test_write_transfermarkt_squads_writes_updated_parquet(tmp_path) -> None:
    squads = tmp_path / "squads.parquet"
    players = tmp_path / "players.csv"
    output = tmp_path / "updated.parquet"
    write_rows_parquet(
        [
            {
                "player_id": "wc-1",
                "player_name": "Kylian Mbappe",
                "team": "France",
                "date_of_birth": "1998-12-20",
                "age": 27.0,
                "sector": "ATA",
                "market_value": 1.0,
                "called_up": True,
            }
        ],
        squads,
    )
    players.write_text(
        "\n".join(
            [
                "player_id,name,date_of_birth,market_value_in_eur",
                "tm-2,Kylian Mbappe,1998-12-20,180000000",
            ]
        ),
        encoding="utf-8",
    )

    written = write_transfermarkt_squads(
        squads_path=squads,
        players_csv=players,
        valuations_csv=None,
        output_path=output,
    )

    assert written == output
    row = read_parquet(output).row(0, named=True)
    assert row["market_value"] == 180_000_000.0
    assert row["transfermarkt_player_id"] == "tm-2"


def test_apply_transfermarkt_values_reads_gzipped_exports(tmp_path) -> None:
    squads = tmp_path / "squads.parquet"
    players = tmp_path / "players.csv.gz"
    valuations = tmp_path / "player_valuations.csv.gz"
    write_rows_parquet(
        [
            {
                "player_id": "wc-1",
                "player_name": "Ronaldo Cristiano Ronaldo",
                "team": "Portugal",
                "date_of_birth": "1985-02-05",
                "age": 41.0,
                "sector": "ATA",
                "market_value": 1.0,
                "called_up": True,
            }
        ],
        squads,
    )
    with gzip.open(players, "wt", encoding="utf-8") as handle:
        handle.write("player_id,name,date_of_birth\n")
        handle.write("tm-7,Cristiano Ronaldo,1985-02-05\n")
    with gzip.open(valuations, "wt", encoding="utf-8") as handle:
        handle.write("player_id,date,market_value_in_eur\n")
        handle.write("tm-7,2026-06-01,12000000\n")

    rows = apply_transfermarkt_values_to_squads(
        squads,
        players,
        valuations,
        as_of="2026-06-11",
    )

    assert rows[0]["market_value"] == 12_000_000.0
    assert rows[0]["market_value_source"] == "transfermarkt"
    assert rows[0]["market_value_trusted"] is True


def test_impute_team_mean_market_values_uses_trusted_team_average() -> None:
    rows = impute_team_mean_market_values(
        [
            {
                "team": "Tunisia",
                "player_name": "Trusted A",
                "called_up": True,
                "market_value": 10.0,
                "market_value_eur": 10.0,
                "market_value_source": "transfermarkt",
                "market_value_trusted": True,
            },
            {
                "team": "Tunisia",
                "player_name": "Trusted B",
                "called_up": True,
                "market_value": 30.0,
                "market_value_eur": 30.0,
                "market_value_source": "transfermarkt",
                "market_value_trusted": True,
            },
            {
                "team": "Tunisia",
                "player_name": "Missing",
                "called_up": True,
                "market_value": 999.0,
                "market_value_eur": 999.0,
                "market_value_source": "world-cup-detail",
                "market_value_trusted": False,
            },
        ],
        as_of="2026-06-11",
    )

    assert rows[2]["market_value"] == 20.0
    assert rows[2]["market_value_eur"] == 20.0
    assert rows[2]["market_value_source"] == "team_mean_imputed"
    assert rows[2]["market_value_trusted"] is True
    assert rows[2]["market_value_imputed"] is True
    assert rows[2]["imputed_from_trusted_player_count"] == 2
