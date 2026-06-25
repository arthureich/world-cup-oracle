from __future__ import annotations

from dataclasses import dataclass
from datetime import date


def parse_date(value: date | str) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


@dataclass(frozen=True)
class Team:
    team: str
    fifa_rank: int | None = None
    confederation: str | None = None
    is_host: bool = False


@dataclass(frozen=True)
class FifaPoints:
    team: str
    fifa_points: float
    ranking_date: date | str
    fifa_rank: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "ranking_date", parse_date(self.ranking_date))


@dataclass(frozen=True)
class Match:
    match_id: str
    date: date | str
    team_a: str
    team_b: str
    goals_a: int
    goals_b: int
    match_type: str
    competition: str = ""
    stage: str = ""
    home_team: str | None = None
    neutral_site: bool = True
    went_to_penalties: bool = False
    penalty_winner: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "date", parse_date(self.date))
        if self.team_a == self.team_b:
            raise ValueError("team_a and team_b must be different teams")
        if self.goals_a < 0 or self.goals_b < 0:
            raise ValueError("goals cannot be negative")
        if self.home_team is not None and self.home_team not in {self.team_a, self.team_b}:
            raise ValueError("home_team must be one of the match teams")
        if self.penalty_winner is not None and self.penalty_winner not in {
            self.team_a,
            self.team_b,
        }:
            raise ValueError("penalty_winner must be one of the match teams")
        if self.went_to_penalties and self.penalty_winner is None:
            raise ValueError("penalty_winner is required when went_to_penalties is true")


@dataclass(frozen=True)
class GroupAssignment:
    group: str
    team: str
    position: int | None = None
    fifa_rank: int | None = None


@dataclass(frozen=True)
class ScheduleMatch:
    match_id: str
    group: str
    team_a: str
    team_b: str
    match_number: int | None = None
    host_team: str | None = None
    neutral_site: bool = True

    def __post_init__(self) -> None:
        if self.team_a == self.team_b:
            raise ValueError("team_a and team_b must be different teams")
        if self.host_team is not None and self.host_team not in {self.team_a, self.team_b}:
            raise ValueError("host_team must be one of the match teams")
