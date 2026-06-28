from __future__ import annotations

import math

from world_cup_oracle.pipeline.manual_odds import normalized_outright_rows


def test_normalized_outright_rows_devigs_american_winner_odds() -> None:
    rows = normalized_outright_rows(
        [
            {
                "snapshot_date": "2026-06-25",
                "source": "manual",
                "bookmaker": "market",
                "source_team": "USA",
                "team": "United States",
                "market": "champion",
                "american_odd": 6000,
            },
            {
                "snapshot_date": "2026-06-25",
                "source": "manual",
                "bookmaker": "market",
                "source_team": "Spain",
                "team": "Spain",
                "market": "champion",
                "american_odd": 420,
            },
        ]
    )

    assert rows[0]["team"] == "United States"
    assert rows[0]["source_team"] == "USA"
    assert math.isclose(rows[1]["champion"], 5.2)
    assert math.isclose(sum(row["champion_probability_devig"] for row in rows), 1.0)
    assert rows[1]["champion_probability_devig"] > rows[0]["champion_probability_devig"]
