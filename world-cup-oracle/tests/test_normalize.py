from __future__ import annotations

from tactical_oracle.data.io import read_parquet
from tactical_oracle.data.mocks import write_mock_parquets
from tactical_oracle.pipeline.normalize import normalize_mock_raw


def test_normalize_mock_raw_writes_canonical_interim_tables(tmp_path) -> None:
    raw_dir = tmp_path / "raw"
    interim_dir = tmp_path / "interim"
    write_mock_parquets(raw_dir)

    written = normalize_mock_raw(raw_dir, interim_dir)
    names = {path.name for path in written}

    assert "teams.parquet" in names
    assert "matches_cycle.parquet" in names
    assert "worldcup_annex_c.parquet" in names
    assert read_parquet(interim_dir / "matches_cycle.parquet").height == 5

