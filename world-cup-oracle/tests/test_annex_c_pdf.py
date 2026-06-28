from __future__ import annotations

from world_cup_oracle.pipeline.annex_c_pdf import annex_c_rows_from_pdf_text


def test_annex_c_rows_from_pdf_text_parses_option_assignments(monkeypatch) -> None:
    monkeypatch.setattr(
        "world_cup_oracle.pipeline.annex_c_pdf.EXPECTED_ANNEX_C_COMBINATIONS",
        2,
    )
    rows = annex_c_rows_from_pdf_text(
        "\n".join(
            [
                "Option 1A 1B 1D 1E 1G 1I 1K 1L",
                "1 3E 3J 3I 3F 3H 3G 3L 3K",
                "2 3H 3G 3I 3D 3J 3F 3L 3K",
            ]
        )
    )

    assert rows[0]["qualified_thirds"] == "EFGHIJKL"
    assert rows[0]["1A"] == "3E"
    assert rows[1]["qualified_thirds"] == "DFGHIJKL"
    assert rows[1]["1E"] == "3D"
