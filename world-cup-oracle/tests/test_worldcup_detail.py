from __future__ import annotations

from tactical_oracle.data.io import read_parquet, write_rows_parquet
from tactical_oracle.pipeline.worldcup_detail import (
    normalize_worldcup_match_stats,
    normalize_worldcup_squads,
    write_worldcup_detail_outputs,
)


def _write_detail_csvs(base) -> None:
    base.mkdir(parents=True)
    (base / "teams.csv").write_text(
        "\n".join(
            [
                "team_id,team_name,fifa_code,group_letter,confederation,"
                "fifa_ranking_pre_tournament,elo_rating,manager_name",
                "1,Mexico,MEX,A,CONCACAF,14,1810,Javier Aguirre",
                "2,Czechia,CZE,A,UEFA,40,1740,Miroslav Koubek",
            ]
        ),
        encoding="utf-8",
    )
    (base / "matches.csv").write_text(
        "\n".join(
            [
                "match_id,date,kickoff_time_utc,stage_id,venue_id,home_team_id,"
                "away_team_id,home_score,away_score,status,home_xg,away_xg,"
                "referee_id,player_of_the_match_id",
                "1,2026-06-11,19:00,1,1,1,2,2,1,Completed,1.8,0.7,1,10",
            ]
        ),
        encoding="utf-8",
    )
    (base / "matches_detailed.csv").write_text(
        "match_id,date,kickoff_time_utc,stage_name,stadium_name,city,country,"
        "home_team_name,home_fifa_code,away_team_name,away_fifa_code,home_score,"
        "away_score,status,home_xg,away_xg,home_goalkeeper,away_goalkeeper,"
        "player_of_the_match_name,referee_name\n",
        encoding="utf-8",
    )
    (base / "match_team_stats.csv").write_text(
        "\n".join(
            [
                "match_id,team_id,possession_pct,total_shots,shots_on_target,corners,"
                "fouls,offsides,saves,player_of_the_match,data_source,last_updated",
                "1,1,57,16,4,6,11,2,1,Player A,fifa.com,2026-06-24",
                "1,2,43,3,2,3,15,1,4,,fifa.com,2026-06-24",
            ]
        ),
        encoding="utf-8",
    )
    (base / "match_events.csv").write_text(
        "\n".join(
            [
                "event_id,match_id,minute,event_type,team_id,player_id",
                "1,1,55,Red Card,2,20",
            ]
        ),
        encoding="utf-8",
    )
    (base / "match_lineups.csv").write_text(
        "\n".join(
            [
                "lineup_id,match_id,player_id,team_id,is_starting_xi,"
                "tactical_position,minutes_played",
                "1,1,10,1,1,FWD,90",
                "2,1,20,2,1,DEF,90",
            ]
        ),
        encoding="utf-8",
    )
    (base / "squads_and_players.csv").write_text(
        "\n".join(
            [
                "player_id,team_id,player_name,position,club_team,market_value_eur,"
                "caps,date_of_birth,height_cm,goals",
                "10,1,Player A,FWD,Club A,10000000,20,2000-01-01,180,5",
                "11,1,Player B,GK,Club B,5000000,10,1998-01-01,190,0",
                "20,2,Player C,DEF,Club C,8000000,12,1999-01-01,185,1",
                "21,2,Player D,MID,Club D,7000000,14,1997-01-01,178,2",
            ]
        ),
        encoding="utf-8",
    )
    (base / "tournament_stages.csv").write_text(
        "stage_id,stage_name,is_knockout\n1,Group Stage,False\n",
        encoding="utf-8",
    )


def test_normalize_worldcup_match_stats_uses_match_number_and_opponent_stats(tmp_path) -> None:
    detail = tmp_path / "detail"
    schedule = tmp_path / "worldcup_schedule.parquet"
    _write_detail_csvs(detail)
    write_rows_parquet(
        [
            {
                "match_id": "400021443",
                "group": "A",
                "team_a": "Mexico",
                "team_b": "Czech Republic",
                "match_number": 1,
                "host_team": "Mexico",
                "neutral_site": False,
            }
        ],
        schedule,
    )

    rows = normalize_worldcup_match_stats(detail, schedule)

    assert rows[0]["match_id"] == "400021443"
    assert rows[0]["match_number"] == 1
    assert rows[0]["team"] == "Mexico"
    assert rows[0]["opponent"] == "Czech Republic"
    assert rows[0]["shots"] == 16
    assert rows[0]["shots_against"] == 3
    assert rows[1]["red_cards"] == 1
    assert rows[1]["first_red_card_minute"] == 55


def test_normalize_worldcup_squads_matches_squad_adjustment_contract(tmp_path) -> None:
    detail = tmp_path / "detail"
    _write_detail_csvs(detail)

    rows = normalize_worldcup_squads(detail)

    assert rows[0]["team"] == "Mexico"
    assert rows[0]["sector"] == "ATA"
    assert rows[0]["market_value"] == 10_000_000.0
    assert rows[0]["market_value_source"] == "world-cup-detail"
    assert rows[0]["market_value_trusted"] is False
    assert rows[0]["called_up"] is True


def test_write_worldcup_detail_outputs_creates_interim_tables(tmp_path) -> None:
    detail = tmp_path / "detail"
    output = tmp_path / "interim"
    _write_detail_csvs(detail)

    written = write_worldcup_detail_outputs(detail, schedule_path=None, output_dir=output)

    assert {path.name for path in written} == {
        "worldcup_teams_detail.parquet",
        "squads.parquet",
        "worldcup_match_stats.parquet",
        "worldcup_match_events.parquet",
        "worldcup_lineups.parquet",
    }
    assert read_parquet(output / "worldcup_match_stats.parquet").height == 2
    assert read_parquet(output / "squads.parquet").height == 4
