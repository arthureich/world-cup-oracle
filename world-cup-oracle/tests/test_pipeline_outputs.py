from __future__ import annotations

from world_cup_oracle.data.io import read_parquet
from world_cup_oracle.pipeline.outputs import build_mock_outputs, write_mock_outputs


def test_build_mock_outputs_contains_core_tables() -> None:
    outputs = build_mock_outputs()

    assert "ratings_elo.parquet" in outputs
    assert "tsi_pre_cup.parquet" in outputs
    assert "attack_defense_pre_cup.parquet" in outputs
    assert "match_probabilities.parquet" in outputs
    assert len(outputs["match_probabilities.parquet"]) == 12


def test_write_mock_outputs_creates_processed_parquets(tmp_path) -> None:
    written = write_mock_outputs(tmp_path)

    names = {path.name for path in written}
    assert "ratings_elo.parquet" in names
    assert "match_probabilities.parquet" in names
    assert read_parquet(tmp_path / "match_probabilities.parquet").height == 12

