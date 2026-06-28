from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

PARSE_BOT_SCRAPER_ID = "645b8e03-271d-4c85-97e7-35d5733a2d78"
DEFAULT_BASE_URL = f"https://kpmh37x1.up.railway.app/scraper/{PARSE_BOT_SCRAPER_ID}"
DEFAULT_RAW_DIR = Path("data/raw/fotmob")

SUPPORTED_ENDPOINTS = (
    "get_leagues",
    "get_matches_by_date",
    "get_league_details",
    "get_league_stats",
    "get_match_details",
)

ENDPOINT_PARAM_ALIASES = {
    "get_match_details": {"id": "match_id"},
    "get_league_details": {"id": "league_id"},
    "get_league_stats": {"id": "league_id"},
}


class FotMobApiError(RuntimeError):
    """Raised when Parse.bot's FotMob API cannot be called or parsed."""


def parse_cli_params(items: list[str]) -> dict[str, str]:
    params: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"Parameter must use KEY=VALUE syntax: {item}")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Parameter key cannot be empty: {item}")
        params[key] = value.strip()
    return params


def canonical_endpoint_params(
    endpoint: str,
    params: dict[str, str] | None = None,
) -> dict[str, str]:
    if endpoint not in SUPPORTED_ENDPOINTS:
        raise ValueError(f"Unsupported FotMob endpoint: {endpoint}")

    canonical = dict(params or {})
    for alias, target in ENDPOINT_PARAM_ALIASES.get(endpoint, {}).items():
        if alias in canonical and target not in canonical:
            canonical[target] = canonical.pop(alias)
    return canonical


def endpoint_url(
    endpoint: str,
    params: dict[str, str] | None = None,
    base_url: str = DEFAULT_BASE_URL,
) -> str:
    canonical = canonical_endpoint_params(endpoint, params)
    url = f"{base_url.rstrip('/')}/{endpoint}"
    if canonical:
        url = f"{url}?{urlencode(sorted(canonical.items()))}"
    return url


def _safe_filename_part(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-") or "empty"


def raw_response_path(
    endpoint: str,
    params: dict[str, str] | None = None,
    raw_dir: str | Path = DEFAULT_RAW_DIR,
) -> Path:
    canonical = canonical_endpoint_params(endpoint, params)
    parts = [endpoint]
    for key in ("date", "match_id", "league_id", "season"):
        if key in canonical:
            parts.append(f"{key}-{_safe_filename_part(canonical[key])}")

    if canonical:
        digest = hashlib.sha1(urlencode(sorted(canonical.items())).encode("utf-8")).hexdigest()[:12]
        parts.append(digest)

    return Path(raw_dir) / endpoint / f"{'_'.join(parts)}.json"


def fetch_endpoint(
    endpoint: str,
    params: dict[str, str] | None,
    api_key: str,
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = 30.0,
) -> dict[str, Any]:
    request = Request(
        endpoint_url(endpoint, params, base_url=base_url),
        headers={
            "Accept": "application/json",
            "X-API-Key": api_key,
            "Host": "api.parse.bot",
        },
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read()
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise FotMobApiError(
            f"Parse.bot FotMob API returned HTTP {exc.code}: {body[:500]}"
        ) from exc
    except URLError as exc:
        raise FotMobApiError(f"Could not reach Parse.bot FotMob API: {exc.reason}") from exc

    try:
        decoded = json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise FotMobApiError("Parse.bot FotMob API returned invalid JSON.") from exc

    if not isinstance(decoded, dict):
        raise FotMobApiError("Parse.bot FotMob API returned a non-object JSON payload.")
    return decoded


def fetch_and_cache_endpoint(
    endpoint: str,
    params: dict[str, str] | None = None,
    raw_dir: str | Path = DEFAULT_RAW_DIR,
    api_key: str | None = None,
    base_url: str = DEFAULT_BASE_URL,
    force: bool = False,
    timeout: float = 30.0,
) -> Path:
    canonical = canonical_endpoint_params(endpoint, params)
    destination = raw_response_path(endpoint, canonical, raw_dir)
    if destination.exists() and not force:
        return destination

    resolved_api_key = api_key or os.environ.get("PARSE_BOT_API_KEY")
    if not resolved_api_key:
        raise FotMobApiError("Set PARSE_BOT_API_KEY before fetching FotMob data.")

    payload = fetch_endpoint(
        endpoint=endpoint,
        params=canonical,
        api_key=resolved_api_key,
        base_url=base_url,
        timeout=timeout,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return destination


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch FotMob data through Parse.bot and cache the raw JSON response."
    )
    parser.add_argument("endpoint", choices=SUPPORTED_ENDPOINTS)
    parser.add_argument(
        "--param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Endpoint parameter. Repeat for multiple params, e.g. --param date=20260611.",
    )
    parser.add_argument("--raw-dir", default=str(DEFAULT_RAW_DIR))
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--api-key-env", default="PARSE_BOT_API_KEY")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--timeout", type=float, default=30.0)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    api_key = os.environ.get(args.api_key_env)
    path = fetch_and_cache_endpoint(
        endpoint=args.endpoint,
        params=parse_cli_params(args.param),
        raw_dir=args.raw_dir,
        api_key=api_key,
        base_url=args.base_url,
        force=args.force,
        timeout=args.timeout,
    )
    print(path)


if __name__ == "__main__":
    main()
