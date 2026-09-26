"""CLI: fetch / analyze / build-site / watch."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from . import __version__
from .alerts import run_once, watch_loop
from .fetch import fetch_addresses, fetch_holdings, save_json, load_json
from .graph import analyze


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def cmd_fetch(args: argparse.Namespace) -> None:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    print("Pobieram /api/addresses …")
    addresses = fetch_addresses()
    save_json(out / "addresses.json", addresses)
    print(f"  {len(addresses)} adresów → {out / 'addresses.json'}")
    print("Pobieram /api/holdings …")
    holdings = fetch_holdings()
    save_json(out / "holdings.json", holdings)
    print(f"  chains={list(holdings.keys())} → {out / 'holdings.json'}")


def cmd_analyze(args: argparse.Namespace) -> None:
    path = Path(args.input)
    addresses = load_json(path)
    result = analyze(addresses)
    out = Path(args.out)
    save_json(out, result)
    t = result["totals"]
    print(
        f"OK → {out}\n"
        f"  adresy={t['addresses']} nonzero={t['nonzero']} usd=${t['usd']:,.0f}"
    )


def cmd_build_site(args: argparse.Namespace) -> None:
    addresses_path = Path(args.input)
    if addresses_path.exists():
        addresses = load_json(addresses_path)
    else:
        print("Brak lokalnego dumpa — pobieram live…")
        addresses = fetch_addresses()
        raw = _root() / "raw"
        raw.mkdir(exist_ok=True)
        save_json(raw / "addresses.json", addresses)

    result = analyze(addresses)
    # kompaktowy snapshot pod stronę (bez pełnych 100 holderów balances jeśli za ciężkie)
    site = {
        "generated_at": result["generated_at"],
        "totals": result["totals"],
        "concentration": result["concentration"],
        "usd_by_chain": result["usd_by_chain"],
        "usd_by_hop": result["usd_by_hop"],
        "tokens": result["tokens"],
        "seeds": result["seeds"],
        "top_holders": [
            {
                "address": h["address"],
                "usd": h["usd"],
                "hop": h["hop"],
                "role": h["role"],
                "chains": h["chains"],
                "balances": h["balances"],
                "last_t": h.get("last_t"),
            }
            for h in result["top_holders"][:50]
        ],
        "watchlist": result["watchlist"][:30],
        "cex": result["cex"],
        "bridges": result["bridges"][:25],
        "freezable": result["freezable"][:20],
        "graph": result["graph"],
        "links": {
            "bounty": "https://www.bitget.com/support/articles/12560603896108",
            "dashboard": "https://trace.bgblockchain.xyz/v2#explorer",
            "report": "https://trace.bgblockchain.xyz/report",
            "api": "https://trace.bgblockchain.xyz/api/addresses",
        },
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    save_json(out, site)
    # też analiza pełna
    save_json(out.parent / "analysis.json", result)
    print(f"Site data → {out} ({out.stat().st_size // 1024} KB)")


def cmd_watch(args: argparse.Namespace) -> None:
    load_dotenv(_root() / ".env")
    interval = int(args.interval or os.getenv("POLL_INTERVAL") or 60)
    min_usd = float(args.min_usd or os.getenv("WATCH_MIN_USD") or 1_000_000)
    min_delta = float(args.min_delta or os.getenv("MIN_USD_DELTA") or 1000)
    extra_raw = args.extra or os.getenv("WATCH_EXTRA") or ""
    extra = [x.strip() for x in extra_raw.split(",") if x.strip()]
    discord = os.getenv("DISCORD_WEBHOOK_URL") or ""
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN") or ""
    tg_chat = os.getenv("TELEGRAM_CHAT_ID") or ""
    state = Path(args.state)
    if args.once:
        run_once(
            state_path=state,
            min_usd=min_usd,
            min_delta=min_delta,
            extra=extra,
            discord=discord,
            telegram_token=tg_token,
            telegram_chat=tg_chat,
        )
        return
    watch_loop(
        state_path=state,
        interval=interval,
        min_usd=min_usd,
        min_delta=min_delta,
        extra=extra,
        discord=discord,
        telegram_token=tg_token,
        telegram_chat=tg_chat,
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="bitget-trace", description="Bitget hack tracker")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_fetch = sub.add_parser("fetch", help="Pobierz surowy graf z API Bitget")
    p_fetch.add_argument("--out", default=str(_root() / "raw"))
    p_fetch.set_defaults(func=cmd_fetch)

    p_an = sub.add_parser("analyze", help="Zbuduj analizę / siatkę z addresses.json")
    p_an.add_argument("--input", default=str(_root() / "raw" / "addresses.json"))
    p_an.add_argument("--out", default=str(_root() / "raw" / "analysis.json"))
    p_an.set_defaults(func=cmd_analyze)

    p_site = sub.add_parser("build-site", help="Wygeneruj site/data/snapshot.json")
    p_site.add_argument("--input", default=str(_root() / "raw" / "addresses.json"))
    p_site.add_argument("--out", default=str(_root() / "site" / "data" / "snapshot.json"))
    p_site.set_defaults(func=cmd_build_site)

    p_w = sub.add_parser("watch", help="Alerty przy zmianie sald watchlisty")
    p_w.add_argument("--once", action="store_true", help="Jeden cykl zamiast pętli")
    p_w.add_argument("--interval", type=int, default=None)
    p_w.add_argument("--min-usd", type=float, default=None)
    p_w.add_argument("--min-delta", type=float, default=None)
    p_w.add_argument("--extra", default=None, help="Adresy CSV")
    p_w.add_argument("--state", default=str(_root() / "alerts_state.json"))
    p_w.set_defaults(func=cmd_watch)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
