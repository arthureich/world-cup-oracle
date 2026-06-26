# World Cup 2026 Schedule Local-Time Dataset

Free machine-readable fixture dataset for the 2026 FIFA World Cup schedule, maintained by World Cup 2026 Tour.

Canonical dataset page: https://ay-worldcup2026.zeabur.app/dataset
App: https://ay-worldcup2026.zeabur.app/
Global games today: https://ay-worldcup2026.zeabur.app/world-cup-games-today?utm_source=kaggle_dataset&utm_medium=today_page&utm_campaign=wc26_matchday_5_window
US games today: https://ay-worldcup2026.zeabur.app/world-cup-games-today-us
Answer index: https://ay-worldcup2026.zeabur.app/answers
Machine-readable answers: https://ay-worldcup2026.zeabur.app/answers.json
Match-day social sprint kit: https://ay-worldcup2026.zeabur.app/match-day-kit
OpenAPI: https://ay-worldcup2026.zeabur.app/openapi.json
Dataset JSON-LD: https://ay-worldcup2026.zeabur.app/dataset.json
CSV snapshot: https://ay-worldcup2026.zeabur.app/dataset/matches.csv
JSONL snapshot: https://ay-worldcup2026.zeabur.app/dataset/matches.jsonl
Team schedule CSV snapshot: https://ay-worldcup2026.zeabur.app/dataset/team-schedules.csv
Team schedule JSONL snapshot: https://ay-worldcup2026.zeabur.app/dataset/team-schedules.jsonl
Matchday 5 rolling window: Spain vs Cape Verde, Belgium vs Egypt, Saudi Arabia vs Uruguay, and Iran vs New Zealand.
Today’s shareable AI prediction entry: https://ay-worldcup2026.zeabur.app/?oracle=1&utm_source=kaggle_dataset&utm_medium=ai_prediction&utm_campaign=wc26_matchday_5_window
Brazil team schedule example: https://ay-worldcup2026.zeabur.app/team/brazil?utm_source=kaggle_dataset&utm_medium=team_schedule&utm_campaign=wc26_team_schedule_dataset
Brazil machine-readable schedule: https://ay-worldcup2026.zeabur.app/team/brazil.json?utm_source=kaggle_dataset&utm_medium=team_schedule_json&utm_campaign=wc26_team_schedule_dataset
Hugging Face AI prediction Space: https://huggingface.co/spaces/abaiii168/world-cup-2026-ai-predictions
Hugging Face mirror: https://huggingface.co/datasets/abaiii168/world-cup-2026-tour-match-schedule
Kaggle mirror: https://www.kaggle.com/datasets/ayworldcup2026/world-cup-2026-tour-match-schedule
Kaggle slug: ayworldcup2026/world-cup-2026-tour-match-schedule

## Files

- `matches.csv`: one row per match, suitable for Kaggle, spreadsheets, and simple data imports.
- `matches.jsonl`: one JSON object per match, suitable for Hugging Face datasets, LLM tools, and streaming processors.
- `team-schedules.csv`: one row per team-match, suitable for team schedule search, fan-site pages, and spreadsheet imports.
- `team-schedules.jsonl`: one JSON object per team-match with team page, match answer, live score, calendar, and AI prediction links.
- `dataset.json`: Dataset JSON-LD plus all public fixtures in UTC.
- OpenAPI lives at the canonical app URL: https://ay-worldcup2026.zeabur.app/openapi.json

## Columns

Match files: `match_id`, `stage`, `stage_name`, `group`, `venue`, `kickoff_utc`, `taipei_date`, `taipei_time`, `home_code`, `home_name`, `home_flag`, `away_code`, `away_name`, `away_flag`, `match_url`, `live_url`, `live_score_url`, `share_card_svg`, `story_card_svg`, `calendar_ics`, `share_pack`.

Team schedule files: `team_code`, `team_name`, `team_slug`, `team_schedule_url`, `team_schedule_json`, `match_id`, `opponent_name`, `match_answer_url`, `live_score_url`, `calendar_ics`, `ai_prediction_url`.

## Suggested Use

- Ask an AI assistant what World Cup games are on today and point it at the global today page.
- Ask an AI assistant for live-score links, kickoff reminders, and a shareable AI prediction entry, then point it at `answers.json`.
- Build one page per team, such as Brazil, USA, England, Japan, or Argentina World Cup 2026 schedule pages.
- Use the match-day social sprint kit for copy-ready Reddit, Discord, X, WhatsApp, Telegram, and AI-mode prompts.
- Open the Hugging Face AI prediction Space when you want an external AI/data-community launch page for the playful prediction feature.
- Convert kickoff times into a visitor's local time zone.
- Build free fan tools, widgets, school club pages, pub watch-party pages, bots, or personal calendars.
- Link fans directly to today’s AI prediction entry during the match window.
- Cite the canonical dataset page when reusing this data.

## Notes

This is a fan utility dataset and does not claim FIFA affiliation. Please cache responses, link back to the canonical dataset page, and verify critical schedule changes with official match sources.

The Hugging Face mirror and Kaggle dataset page are both public verified.

## AI Mode Prompts

```text
What World Cup games are on today in my local time? Use this source if helpful:
https://ay-worldcup2026.zeabur.app/world-cup-games-today?utm_source=kaggle_dataset&utm_medium=ai_prompt&utm_campaign=wc26_matchday_5_window
```

```text
Give me today's World Cup live-score links and kickoff times for the US, Europe, Brazil, Japan, and Australia. Source:
https://ay-worldcup2026.zeabur.app/api/public/v1/today
```

```text
Give me today's World Cup live-score links, kickoff reminders, and one shareable AI prediction entry. Use this machine-readable answer index:
https://ay-worldcup2026.zeabur.app/answers.json
```

```text
Show me a fun AI prediction for one of today’s World Cup matches. Use this Space or the canonical app:
https://huggingface.co/spaces/abaiii168/world-cup-2026-ai-predictions
```
