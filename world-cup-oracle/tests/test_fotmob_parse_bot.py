from __future__ import annotations

import json

import pytest

from tactical_oracle.pipeline import fotmob_parse_bot
from tactical_oracle.pipeline.fotmob_parse_bot import (
    FotMobApiError,
    canonical_endpoint_params,
    endpoint_url,
    fetch_and_cache_endpoint,
    parse_cli_params,
)


class _FakeResponse:
    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return b'{"status": "success", "data": {"ok": true}}'


def test_parse_cli_params_and_endpoint_aliases() -> None:
    assert parse_cli_params(["date=20260611", "season=2026"]) == {
        "date": "20260611",
        "season": "2026",
    }
    assert canonical_endpoint_params("get_match_details", {"id": "4813374"}) == {
        "match_id": "4813374"
    }
    assert canonical_endpoint_params("get_league_details", {"id": "77"}) == {"league_id": "77"}


def test_endpoint_url_sorts_and_encodes_params() -> None:
    url = endpoint_url(
        "get_league_details",
        {"season": "2026/2027", "league_id": "77"},
        base_url="https://example.test/scraper",
    )

    assert url == "https://example.test/scraper/get_league_details?league_id=77&season=2026%2F2027"


def test_fetch_and_cache_endpoint_writes_raw_json(monkeypatch, tmp_path) -> None:
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = {key.lower(): value for key, value in request.header_items()}
        captured["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setattr(fotmob_parse_bot, "urlopen", fake_urlopen)

    path = fetch_and_cache_endpoint(
        endpoint="get_matches_by_date",
        params={"date": "20260611"},
        raw_dir=tmp_path,
        api_key="test-key",
        base_url="https://example.test/scraper",
        timeout=7.0,
    )

    assert captured["url"] == "https://example.test/scraper/get_matches_by_date?date=20260611"
    assert captured["headers"]["x-api-key"] == "test-key"
    assert captured["timeout"] == 7.0
    assert path.parent.name == "get_matches_by_date"
    assert path.name.startswith("get_matches_by_date_date-20260611_")
    assert json.loads(path.read_text(encoding="utf-8"))["status"] == "success"


def test_fetch_and_cache_endpoint_reuses_cache_without_api_key(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(fotmob_parse_bot, "urlopen", lambda request, timeout: _FakeResponse())

    path = fetch_and_cache_endpoint(
        endpoint="get_match_details",
        params={"id": "4813374"},
        raw_dir=tmp_path,
        api_key="test-key",
        base_url="https://example.test/scraper",
    )

    def fail_urlopen(request, timeout):
        raise AssertionError("cached request should not call the network")

    monkeypatch.setattr(fotmob_parse_bot, "urlopen", fail_urlopen)
    monkeypatch.delenv("PARSE_BOT_API_KEY", raising=False)

    assert fetch_and_cache_endpoint("get_match_details", {"match_id": "4813374"}, tmp_path) == path


def test_fetch_and_cache_endpoint_requires_api_key_for_uncached_request(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.delenv("PARSE_BOT_API_KEY", raising=False)

    with pytest.raises(FotMobApiError, match="PARSE_BOT_API_KEY"):
        fetch_and_cache_endpoint("get_leagues", raw_dir=tmp_path)
