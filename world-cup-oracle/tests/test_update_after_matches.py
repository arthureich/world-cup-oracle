from __future__ import annotations

from pathlib import Path

from tactical_oracle.pipeline import update_after_matches


def test_schedule_file_for_post_group_step_accepts_interim_prefixed_path() -> None:
    assert (
        update_after_matches._schedule_file_for_post_group_step(
            "data/interim/worldcup_schedule.parquet",
            "data/interim",
        )
        == "worldcup_schedule.parquet"
    )


def test_run_after_match_update_chains_local_steps(monkeypatch, tmp_path) -> None:
    calls: list[str] = []

    def step(name: str):
        def _inner(*args, **kwargs):
            calls.append(name)
            return [tmp_path / f"{name}.parquet"]

        return _inner

    monkeypatch.setattr(update_after_matches, "write_worldcup_detail_outputs", step("detail"))
    monkeypatch.setattr(
        update_after_matches,
        "write_real_match_performance_outputs",
        step("performance"),
    )
    monkeypatch.setattr(
        update_after_matches,
        "write_post_group_match_probability_outputs",
        step("post_groups"),
    )
    monkeypatch.setattr(
        update_after_matches,
        "write_tournament_projection_outputs",
        step("tournament"),
    )
    monkeypatch.setattr(
        update_after_matches,
        "build_worldcup_validation_report",
        step("validation"),
    )

    written = update_after_matches.run_after_match_update(
        interim_dir=tmp_path / "interim",
        processed_dir=tmp_path / "processed",
        detail_dir=tmp_path / "detail",
        schedule_path=tmp_path / "schedule.parquet",
        fotmob_stats_path=tmp_path / "stats.csv",
        report_dir=tmp_path / "reports",
    )

    assert calls == ["detail", "performance", "post_groups", "tournament", "validation"]
    assert all(isinstance(path, Path) for path in written)


def test_run_after_match_update_can_skip_fetch_detail_and_validation(monkeypatch, tmp_path) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        update_after_matches,
        "write_real_match_performance_outputs",
        lambda *args, **kwargs: calls.append("performance") or [],
    )
    monkeypatch.setattr(
        update_after_matches,
        "write_post_group_match_probability_outputs",
        lambda *args, **kwargs: calls.append("post_groups") or [],
    )
    monkeypatch.setattr(
        update_after_matches,
        "write_tournament_projection_outputs",
        lambda *args, **kwargs: calls.append("tournament") or [],
    )

    update_after_matches.run_after_match_update(
        interim_dir=tmp_path / "interim",
        processed_dir=tmp_path / "processed",
        normalize_details=False,
        validate=False,
    )

    assert calls == ["performance", "post_groups", "tournament"]
