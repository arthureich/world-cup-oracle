from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def params_hash(params: Mapping[str, Any]) -> str:
    payload = json.dumps(params, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def endpoint_key(endpoint: str) -> str:
    return endpoint.strip("/").replace("/", "_") or "root"


@dataclass(frozen=True)
class CacheEntry:
    endpoint: str
    params: dict[str, Any]
    fetched_at: str
    payload: Any


class ApiCache:
    def __init__(self, base_dir: str | Path = "data/raw/api_cache") -> None:
        self.base_dir = Path(base_dir)

    def path_for(self, endpoint: str, params: Mapping[str, Any]) -> Path:
        key = endpoint_key(endpoint)
        digest = params_hash(params)
        return self.base_dir / key / digest / "response.json"

    def exists(self, endpoint: str, params: Mapping[str, Any]) -> bool:
        return self.path_for(endpoint, params).exists()

    def read(self, endpoint: str, params: Mapping[str, Any]) -> CacheEntry:
        path = self.path_for(endpoint, params)
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return CacheEntry(
            endpoint=str(data["endpoint"]),
            params=dict(data["params"]),
            fetched_at=str(data["fetched_at"]),
            payload=data["payload"],
        )

    def write(self, endpoint: str, params: Mapping[str, Any], payload: Any) -> CacheEntry:
        entry = CacheEntry(
            endpoint=endpoint,
            params=dict(params),
            fetched_at=datetime.now(UTC).isoformat(),
            payload=payload,
        )
        path = self.path_for(endpoint, params)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(
                {
                    "endpoint": entry.endpoint,
                    "params": entry.params,
                    "fetched_at": entry.fetched_at,
                    "payload": entry.payload,
                },
                handle,
                ensure_ascii=True,
                indent=2,
                sort_keys=True,
            )
        return entry

    def get_or_fetch(
        self,
        endpoint: str,
        params: Mapping[str, Any],
        fetcher: Callable[[str, Mapping[str, Any]], Any],
    ) -> CacheEntry:
        if self.exists(endpoint, params):
            return self.read(endpoint, params)
        return self.write(endpoint, params, fetcher(endpoint, params))


def fetch_json(base_url: str, endpoint: str, params: Mapping[str, Any]) -> Any:
    url = f"{base_url.rstrip('/')}/{endpoint.strip('/')}"
    if params:
        url = f"{url}?{urlencode(params)}"
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))

