"""Pobieranie danych z oficjalnego API Bitget."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests

from . import API_ADDRESSES, API_HOLDINGS

DEFAULT_TIMEOUT = 120


def fetch_json(url: str, timeout: int = DEFAULT_TIMEOUT) -> Any:
    r = requests.get(url, timeout=timeout, headers={"Accept": "application/json"})
    r.raise_for_status()
    return r.json()


def fetch_addresses() -> dict[str, Any]:
    return fetch_json(API_ADDRESSES)


def fetch_holdings() -> dict[str, Any]:
    return fetch_json(API_HOLDINGS)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
