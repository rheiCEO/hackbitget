"""Alerty Discord / Telegram przy zmianie sald watchlisty."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from . import REPORT_URL
from .fetch import fetch_addresses, save_json, load_json
from .graph import analyze, watchlist_from_analysis


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def load_state(path: Path) -> dict[str, Any]:
    if path.exists():
        return load_json(path)
    return {"balances": {}, "updated_at": None}


def snapshot_balances(addresses: dict[str, Any], watch: set[str]) -> dict[str, float]:
    out: dict[str, float] = {}
    lower = {a.lower(): a for a in addresses}
    for w in watch:
        key = lower.get(w.lower(), w)
        meta = addresses.get(key) or addresses.get(w)
        if not meta:
            # case-sensitive miss — spróbuj dokładnego
            continue
        try:
            out[key] = float(meta.get("usd") or 0)
        except (TypeError, ValueError):
            out[key] = 0.0
    return out


def diff_balances(
    prev: dict[str, float],
    curr: dict[str, float],
    min_delta: float,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    keys = set(prev) | set(curr)
    for k in keys:
        a = prev.get(k, 0.0)
        b = curr.get(k, 0.0)
        delta = b - a
        if abs(delta) < min_delta:
            continue
        events.append(
            {
                "address": k,
                "before": round(a, 2),
                "after": round(b, 2),
                "delta": round(delta, 2),
                "direction": "out" if delta < 0 else "in",
            }
        )
    events.sort(key=lambda e: -abs(e["delta"]))
    return events


def format_event(e: dict[str, Any]) -> str:
    arrow = "↓ OUT" if e["direction"] == "out" else "↑ IN"
    return (
        f"**{arrow}** `{e['address']}`\n"
        f"Δ **${e['delta']:,.0f}**  ({e['before']:,.0f} → {e['after']:,.0f})\n"
        f"Report: {REPORT_URL}"
    )


def notify_discord(webhook: str, content: str) -> None:
    if not webhook:
        return
    requests.post(
        webhook,
        json={"content": content[:1900]},
        timeout=30,
    ).raise_for_status()


def notify_telegram(token: str, chat_id: str, content: str) -> None:
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(
        url,
        json={
            "chat_id": chat_id,
            "text": content.replace("**", "")[:4000],
            "disable_web_page_preview": True,
        },
        timeout=30,
    ).raise_for_status()


def run_once(
    state_path: Path,
    min_usd: float,
    min_delta: float,
    extra: list[str],
    discord: str,
    telegram_token: str,
    telegram_chat: str,
    dump_path: Path | None = None,
) -> list[dict[str, Any]]:
    addresses = fetch_addresses()
    if dump_path:
        save_json(dump_path, addresses)

    analysis = analyze(addresses)
    watch = watchlist_from_analysis(analysis, min_usd=min_usd, extra=extra)
    curr = snapshot_balances(addresses, watch)
    state = load_state(state_path)
    prev = state.get("balances") or {}

    events: list[dict[str, Any]] = []
    if prev:
        events = diff_balances(prev, curr, min_delta=min_delta)
        for e in events:
            msg = f"[{_now()}] Bitget trace alert\n{format_event(e)}"
            print(msg)
            try:
                notify_discord(discord, msg)
            except Exception as exc:  # noqa: BLE001
                print("Discord error:", exc)
            try:
                notify_telegram(telegram_token, telegram_chat, msg)
            except Exception as exc:  # noqa: BLE001
                print("Telegram error:", exc)
    else:
        print(f"[{_now()}] baseline zapisany — {len(curr)} adresów watchlisty")

    state = {
        "balances": curr,
        "updated_at": _now(),
        "watch_count": len(curr),
        "totals": analysis["totals"],
    }
    save_json(state_path, state)
    return events


def watch_loop(
    state_path: Path,
    interval: int,
    min_usd: float,
    min_delta: float,
    extra: list[str],
    discord: str,
    telegram_token: str,
    telegram_chat: str,
) -> None:
    print(f"Start watch — co {interval}s, min_usd={min_usd:,.0f}, min_delta={min_delta:,.0f}")
    while True:
        try:
            run_once(
                state_path=state_path,
                min_usd=min_usd,
                min_delta=min_delta,
                extra=extra,
                discord=discord,
                telegram_token=telegram_token,
                telegram_chat=telegram_chat,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[{_now()}] błąd poll: {exc}")
        time.sleep(interval)
