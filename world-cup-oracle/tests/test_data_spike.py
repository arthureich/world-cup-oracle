from __future__ import annotations

from world_cup_oracle.data.io import read_parquet
from world_cup_oracle.pipeline.data_spike import (
    normalize_fifa_api_ranking,
    normalize_fifa_ranking,
    normalize_kaggle_matches,
    write_data_spike_outputs,
)


def test_normalize_kaggle_matches_filters_cycle_and_separates_penalties(tmp_path) -> None:
    results = tmp_path / "results.csv"
    shootouts = tmp_path / "shootouts.csv"
    results.write_text(
        "\n".join(
            [
                "date,home_team,away_team,home_score,away_score,tournament,neutral",
                "2022-12-18,Argentina,France,3,3,FIFA World Cup,TRUE",
                "2023-03-24,Brazil,Morocco,2,1,Friendly,FALSE",
                "2024-07-05,Morocco,Mexico,1,1,Copa America,TRUE",
                "2026-06-11,Mexico,South Africa,1,0,Friendly,FALSE",
            ]
        ),
        encoding="utf-8",
    )
    shootouts.write_text(
        "\n".join(
            [
                "date,home_team,away_team,winner",
                "2024-07-05,Morocco,Mexico,Mexico",
            ]
        ),
        encoding="utf-8",
    )

    rows = normalize_kaggle_matches(results, shootouts)

    assert [row["match_id"] for row in rows] == [
        "kaggle-2023-03-24-brazil-morocco",
        "kaggle-2024-07-05-morocco-mexico",
    ]
    assert rows[0]["match_type"] == "friendly"
    assert rows[0]["home_team"] == "Brazil"
    assert rows[0]["neutral_site"] is False
    assert rows[1]["match_type"] == "continental_group"
    assert rows[1]["went_to_penalties"] is True
    assert rows[1]["penalty_winner"] == "Mexico"


def test_normalize_fifa_ranking_accepts_common_column_names_and_aliases(tmp_path) -> None:
    ranking = tmp_path / "fifa.csv"
    ranking.write_text(
        "\n".join(
            [
                "Country,Points,Rank,Ranking Date",
                "USA,1648.2,12,2023-01-01",
                "Korea Republic,1530.3,28,2023-01-01",
            ]
        ),
        encoding="utf-8",
    )

    rows = normalize_fifa_ranking(ranking)

    assert rows == [
        {
            "team": "United States",
            "fifa_points": 1648.2,
            "ranking_date": "2023-01-01",
            "fifa_rank": 12,
        },
        {
            "team": "South Korea",
            "fifa_points": 1530.3,
            "ranking_date": "2023-01-01",
            "fifa_rank": 28,
        },
    ]


def test_normalize_fifa_api_ranking_uses_decimal_points_and_pub_date(tmp_path) -> None:
    ranking = tmp_path / "fifa.json"
    ranking.write_text(
        """
        {
          "Results": [
            {
              "TeamName": [{"Locale": "en-GB", "Description": "Brazil"}],
              "Rank": 1,
              "TotalPoints": 1841,
              "DecimalTotalPoints": 1840.77,
              "PubDate": "2022-12-22T08:50:00+00:00"
            },
            {
              "TeamName": [{"Locale": "en-GB", "Description": "USA"}],
              "Rank": 13,
              "TotalPoints": 1653,
              "DecimalTotalPoints": 1652.74,
              "PubDate": "2022-12-22T08:50:00+00:00"
            },
            {
              "TeamName": [{"Locale": "en-GB", "Description": "The Gambia"}],
              "Rank": 126,
              "TotalPoints": 1139,
              "DecimalTotalPoints": 1138.9,
              "PubDate": "2022-12-22T08:50:00+00:00"
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    rows = normalize_fifa_api_ranking(ranking)

    assert rows == [
        {
            "team": "Brazil",
            "fifa_points": 1840.77,
            "ranking_date": "2022-12-22",
            "fifa_rank": 1,
        },
        {
            "team": "United States",
            "fifa_points": 1652.74,
            "ranking_date": "2022-12-22",
            "fifa_rank": 13,
        },
        {
            "team": "Gambia",
            "fifa_points": 1138.9,
            "ranking_date": "2022-12-22",
            "fifa_rank": 126,
        },
    ]


def test_write_data_spike_outputs_writes_requested_parquets(tmp_path) -> None:
    results = tmp_path / "results.csv"
    ranking = tmp_path / "fifa.csv"
    output = tmp_path / "interim"
    results.write_text(
        "\n".join(
            [
                "date,home_team,away_team,home_score,away_score,tournament,neutral",
                "2023-03-24,Brazil,Morocco,2,1,Friendly,FALSE",
            ]
        ),
        encoding="utf-8",
    )
    ranking.write_text(
        "\n".join(
            [
                "team,fifa_points,fifa_rank",
                "Brazil,1784.0,5",
                "Morocco,1663.0,12",
            ]
        ),
        encoding="utf-8",
    )

    written = write_data_spike_outputs(
        kaggle_results=results,
        fifa_ranking=ranking,
        output_dir=output,
        ranking_date="2023-01-01",
    )

    assert {path.name for path in written} == {"matches_cycle.parquet", "fifa_points.parquet"}
    assert read_parquet(output / "matches_cycle.parquet").height == 1
    assert read_parquet(output / "fifa_points.parquet").height == 2


def test_write_data_spike_outputs_handles_late_penalty_winner_strings(tmp_path) -> None:
    results = tmp_path / "results.csv"
    shootouts = tmp_path / "shootouts.csv"
    output = tmp_path / "interim"
    rows = ["date,home_team,away_team,home_score,away_score,tournament,neutral"]
    for index in range(101):
        rows.append(f"2023-01-01,Team {index} A,Team {index} B,1,0,Friendly,TRUE")
    rows.append("2024-07-05,Morocco,Mexico,1,1,Copa America,TRUE")
    results.write_text("\n".join(rows), encoding="utf-8")
    shootouts.write_text(
        "\n".join(
            [
                "date,home_team,away_team,winner",
                "2024-07-05,Morocco,Mexico,Mexico",
            ]
        ),
        encoding="utf-8",
    )

    write_data_spike_outputs(
        kaggle_results=results,
        kaggle_shootouts=shootouts,
        output_dir=output,
    )

    matches = read_parquet(output / "matches_cycle.parquet")
    assert matches.height == 102
    assert matches.filter(matches["penalty_winner"] == "Mexico").height == 1
