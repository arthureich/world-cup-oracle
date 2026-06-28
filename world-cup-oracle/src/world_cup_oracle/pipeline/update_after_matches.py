from __future__ import annotations

import argparse
import os
from pathlib import Path

from world_cup_oracle.pipeline.fotmob_worldcup import (
    DEFAULT_MATCH_IDS_PATH,
    DEFAULT_RAW_DIR,
    DEFAULT_TEAM_STATS_PATH,
    fetch_worldcup_match_details,
    write_fotmob_worldcup_outputs,
)
from world_cup_oracle.pipeline.match_performance import write_real_match_performance_outputs
from world_cup_oracle.pipeline.real_outputs import write_post_group_match_probability_outputs
from world_cup_oracle.pipeline.tournament_projection import write_tournament_projection_outputs
from world_cup_oracle.pipeline.validation_report import build_worldcup_validation_report
from world_cup_oracle.pipeline.worldcup_detail import write_worldcup_detail_outputs


def _schedule_file_for_post_group_step(
    schedule_path: str | Path,
    interim_dir: str | Path,
) -> str | Path:
    schedule = Path(schedule_path)
    interim = Path(interim_dir)
    if schedule.is_absolute():
        return schedule
    try:
        if schedule.parent == interim:
            return schedule.name
    except ValueError:
        pass
    return schedule


def fetch_fotmob_worldcup_updates(
    detail_dir: str | Path = "data/raw/world-cup-detail",
    raw_dir: str | Path = DEFAULT_RAW_DIR,
    match_ids_path: str | Path = DEFAULT_MATCH_IDS_PATH,
    team_stats_path: str | Path = DEFAULT_TEAM_STATS_PATH,
    api_key_env: str = "PARSE_BOT_API_KEY",
    force: bool = False,
    sleep_seconds: float = 12.5,
    max_matches: int | None = None,
) -> list[Path]:
    api_key = os.environ.get(api_key_env)
    mapped, missing = fetch_worldcup_match_details(
        detail_dir=detail_dir,
        raw_dir=raw_dir,
        api_key=api_key,
        force=force,
        sleep_seconds=sleep_seconds,
        max_matches=max_matches,
        verbose=True,
    )
    outputs = write_fotmob_worldcup_outputs(
        mapped_matches=mapped,
        raw_dir=raw_dir,
        match_ids_path=match_ids_path,
        team_stats_path=team_stats_path,
    )
    if missing:
        print(f"fotmob_missing_matches={len(missing)}")
        for row in missing[:10]:
            print(f"missing: {row['date']} {row['home_team']} x {row['away_team']}")
    return [Path(path) for path in outputs.values()]


def run_after_match_update(
    interim_dir: str | Path = "data/interim",
    processed_dir: str | Path = "data/processed",
    detail_dir: str | Path = "data/raw/world-cup-detail",
    schedule_path: str | Path = "data/interim/worldcup_schedule.parquet",
    fotmob_stats_path: str | Path = "data/raw/fotmob/worldcup_match_team_stats.csv",
    report_dir: str | Path = "docs/reports",
    odds_path: str | Path = "data/interim/odds_match_by_match.parquet",
    fetch_fotmob: bool = False,
    api_key_env: str = "PARSE_BOT_API_KEY",
    force_fetch: bool = False,
    sleep_seconds: float = 12.5,
    max_matches: int | None = None,
    normalize_details: bool = True,
    validate: bool = True,
) -> list[Path]:
    written: list[Path] = []
    if fetch_fotmob:
        written.extend(
            fetch_fotmob_worldcup_updates(
                detail_dir=detail_dir,
                api_key_env=api_key_env,
                force=force_fetch,
                sleep_seconds=sleep_seconds,
                max_matches=max_matches,
            )
        )
    if normalize_details:
        written.extend(
            write_worldcup_detail_outputs(
                detail_dir=detail_dir,
                schedule_path=schedule_path,
                output_dir=interim_dir,
                fotmob_stats_path=fotmob_stats_path,
            )
        )
    written.extend(write_real_match_performance_outputs(interim_dir, processed_dir))
    written.extend(
        write_post_group_match_probability_outputs(
            interim_dir=interim_dir,
            processed_dir=processed_dir,
            schedule_file=_schedule_file_for_post_group_step(schedule_path, interim_dir),
        )
    )
    written.extend(write_tournament_projection_outputs(processed_dir=processed_dir))
    if validate:
        written.extend(
            build_worldcup_validation_report(
                interim_dir=interim_dir,
                processed_dir=processed_dir,
                report_dir=report_dir,
                odds_path=odds_path,
            )
        )
    return written


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run the local after-match update pipeline without spending API calls by default."
        )
    )
    parser.add_argument("--interim-dir", default="data/interim")
    parser.add_argument("--processed-dir", default="data/processed")
    parser.add_argument("--detail-dir", default="data/raw/world-cup-detail")
    parser.add_argument("--schedule", default="data/interim/worldcup_schedule.parquet")
    parser.add_argument("--fotmob-stats", default="data/raw/fotmob/worldcup_match_team_stats.csv")
    parser.add_argument("--report-dir", default="docs/reports")
    parser.add_argument("--odds-path", default="data/interim/odds_match_by_match.parquet")
    parser.add_argument("--fetch-fotmob", action="store_true")
    parser.add_argument("--api-key-env", default="PARSE_BOT_API_KEY")
    parser.add_argument("--force-fetch", action="store_true")
    parser.add_argument("--sleep-seconds", type=float, default=12.5)
    parser.add_argument("--max-matches", type=int, default=None)
    parser.add_argument("--skip-detail-normalization", action="store_true")
    parser.add_argument("--skip-validation", action="store_true")
    args = parser.parse_args()

    for path in run_after_match_update(
        interim_dir=args.interim_dir,
        processed_dir=args.processed_dir,
        detail_dir=args.detail_dir,
        schedule_path=args.schedule,
        fotmob_stats_path=args.fotmob_stats,
        report_dir=args.report_dir,
        odds_path=args.odds_path,
        fetch_fotmob=args.fetch_fotmob,
        api_key_env=args.api_key_env,
        force_fetch=args.force_fetch,
        sleep_seconds=args.sleep_seconds,
        max_matches=args.max_matches,
        normalize_details=not args.skip_detail_normalization,
        validate=not args.skip_validation,
    ):
        print(path)


if __name__ == "__main__":
    main()
