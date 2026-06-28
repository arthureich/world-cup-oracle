from __future__ import annotations

from world_cup_oracle.data import ApiCache, params_hash


def test_params_hash_is_stable_for_sorted_params() -> None:
    assert params_hash({"b": 2, "a": 1}) == params_hash({"a": 1, "b": 2})


def test_api_cache_get_or_fetch_writes_and_reuses_payload(tmp_path) -> None:
    cache = ApiCache(tmp_path)
    calls = {"count": 0}

    def fetcher(endpoint, params):
        calls["count"] += 1
        return {"endpoint": endpoint, "params": dict(params)}

    first = cache.get_or_fetch("fixtures", {"league": "wc"}, fetcher)
    second = cache.get_or_fetch("fixtures", {"league": "wc"}, fetcher)

    assert first.payload == second.payload
    assert calls["count"] == 1
    assert cache.exists("fixtures", {"league": "wc"})

