from __future__ import annotations

import pytest

from tactical_oracle.data.mocks import worldcup_annex_c_mock
from tactical_oracle.simulation import (
    annex_c_assignments,
    build_annex_c_table,
    validate_annex_c_table,
)


def test_annex_c_assignments_are_loaded_from_table() -> None:
    table = build_annex_c_table(worldcup_annex_c_mock())
    assignments = annex_c_assignments("LKJIHGFE", table)

    assert assignments["1A"] == "3E"
    assert assignments["1L"] == "3K"


def test_annex_c_missing_combination_raises() -> None:
    table = build_annex_c_table(worldcup_annex_c_mock())

    with pytest.raises(ValueError):
        annex_c_assignments("ABCDEFGH", table)


def test_annex_c_complete_validation_can_require_495_combinations() -> None:
    table = build_annex_c_table(worldcup_annex_c_mock())

    validate_annex_c_table(table)
    with pytest.raises(ValueError):
        validate_annex_c_table(table, expected_combinations=495)
