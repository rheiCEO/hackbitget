"""Budowa siatki połączeń i agregatów z grafu Bitget."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any


def _usd(meta: dict[str, Any]) -> float:
    try:
        return float(meta.get("usd") or 0)
    except (TypeError, ValueError):
        return 0.0


def analyze(addresses: dict[str, Any]) -> dict[str, Any]:
    """Pełna analiza klastra: tokeny, hop, role, top holdery, graf."""
    by_role: Counter[str] = Counter()
    by_chain: Counter[str] = Counter()
    usd_by_role: dict[str, float] = defaultdict(float)
    usd_by_chain: dict[str, float] = defaultdict(float)
    usd_by_hop: dict[str, float] = defaultdict(float)
    tokens: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {"usd": 0.0, "amount": 0.0, "addrs": 0, "freezable_usd": 0.0}
    )

    holders: list[dict[str, Any]] = []
    freezable: list[dict[str, Any]] = []
    cex: list[dict[str, Any]] = []
    bridges: list[dict[str, Any]] = []
    graph_nodes: list[dict[str, Any]] = []

    total_usd = 0.0
    nonzero = 0

    for addr, meta in addresses.items():
        role = meta.get("role") or "unknown"
        hop = meta.get("hop")
        hop_key = str(hop) if hop is not None else "none"
        usd = _usd(meta)
        chains = meta.get("chains") or []
        balances = meta.get("balances") or []

        by_role[role] += 1
        usd_by_role[role] += usd
        usd_by_hop[hop_key] += usd
        total_usd += usd
        if usd > 0:
            nonzero += 1

        for c in chains:
            by_chain[c] += 1
            usd_by_chain[c] += usd

        for b in balances:
            sym = b.get("sym") or "?"
            chain = b.get("chain") or "?"
            key = f"{sym}@{chain}"
            bu = float(b.get("usd") or 0)
            amt = float(b.get("amount") or 0)
            tokens[key]["usd"] = float(tokens[key]["usd"]) + bu
            tokens[key]["amount"] = float(tokens[key]["amount"]) + amt
            tokens[key]["addrs"] = int(tokens[key]["addrs"]) + 1
            if b.get("freezable"):
                tokens[key]["freezable_usd"] = float(tokens[key]["freezable_usd"]) + bu
                freezable.append(
                    {
                        "address": addr,
                        "asset": key,
                        "usd": bu,
                        "amount": amt,
                        "hop": hop,
                        "label": meta.get("label"),
                    }
                )

        if role == "cex":
            cex.append(
                {
                    "address": addr,
                    "label": meta.get("label"),
                    "hop": hop,
                    "chains": chains,
                    "last_t": meta.get("last_t"),
                }
            )
        if role == "bridge":
            bridges.append(
                {
                    "address": addr,
                    "label": meta.get("label"),
                    "chains": chains,
                }
            )

        if usd > 0 or role in {"cex", "bridge", "dex", "bitget"}:
            holders.append(
                {
                    "address": addr,
                    "usd": usd,
                    "hop": hop,
                    "role": role,
                    "label": meta.get("label"),
                    "chains": chains,
                    "balances": balances,
                    "last_t": meta.get("last_t"),
                }
            )

        # węzły grafu: holdery >$50k + infrastruktura
        if usd >= 50_000 or role in {"cex", "bridge", "dex", "bitget"}:
            graph_nodes.append(
                {
                    "id": addr,
                    "usd": usd,
                    "hop": hop if hop is not None else -1,
                    "role": role,
                    "chains": chains,
                    "label": (meta.get("label") or "")[:80],
                }
            )

    holders.sort(key=lambda x: -x["usd"])
    freezable.sort(key=lambda x: -x["usd"])
    graph_nodes.sort(key=lambda x: -x["usd"])

    # krawędzie logiczne: hop N -> hop N+1 w obrębie tej samej dominant chain (przybliżenie siatki)
    edges = _build_hop_edges(graph_nodes)

    attacker = [h for h in holders if h["role"] == "attacker" and h["usd"] > 0]
    top10 = sum(h["usd"] for h in attacker[:10])
    top50 = sum(h["usd"] for h in attacker[:50])
    attacker_sum = sum(h["usd"] for h in attacker) or 1.0

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "https://trace.bgblockchain.xyz/api/addresses",
        "totals": {
            "addresses": len(addresses),
            "nonzero": nonzero,
            "usd": round(total_usd, 2),
            "attacker_usd": round(usd_by_role.get("attacker", 0), 2),
        },
        "concentration": {
            "top10_pct": round(100 * top10 / attacker_sum, 2),
            "top50_pct": round(100 * top50 / attacker_sum, 2),
            "ge_1m": sum(1 for h in attacker if h["usd"] >= 1_000_000),
            "ge_1m_usd": round(sum(h["usd"] for h in attacker if h["usd"] >= 1_000_000), 2),
        },
        "by_role": dict(by_role),
        "usd_by_role": {k: round(v, 2) for k, v in usd_by_role.items()},
        "usd_by_chain": {
            k: round(v, 2) for k, v in sorted(usd_by_chain.items(), key=lambda x: -x[1])
        },
        "usd_by_hop": dict(sorted(usd_by_hop.items(), key=lambda x: _hop_sort(x[0]))),
        "tokens": {
            k: {
                "usd": round(float(v["usd"]), 2),
                "amount": float(v["amount"]),
                "addrs": int(v["addrs"]),
                "freezable_usd": round(float(v["freezable_usd"]), 2),
            }
            for k, v in sorted(tokens.items(), key=lambda x: -float(x[1]["usd"]))
        },
        "top_holders": holders[:100],
        "watchlist": [h for h in attacker if h["usd"] >= 1_000_000][:50],
        "freezable": freezable,
        "cex": cex,
        "bridges": bridges[:40],
        "graph": {
            "nodes": graph_nodes[:250],
            "edges": edges,
        },
        "seeds": _seed_status(addresses),
    }


def _hop_sort(key: str) -> tuple[int, int]:
    if key == "none":
        return (1, 0)
    try:
        return (0, int(key))
    except ValueError:
        return (2, 0)


def _build_hop_edges(nodes: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Łączy węzły o kolejnych hopach w tej samej pierwszej sieci (przybliżona siatka)."""
    by_chain_hop: dict[str, dict[int, list[str]]] = defaultdict(lambda: defaultdict(list))
    for n in nodes:
        if n["role"] != "attacker" or n["usd"] < 100_000:
            continue
        chains = n.get("chains") or ["?"]
        chain = chains[0]
        hop = int(n.get("hop") if n.get("hop") is not None else -1)
        if hop < 0:
            continue
        by_chain_hop[chain][hop].append(n["id"])

    edges: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for chain, hops in by_chain_hop.items():
        for hop, ids in hops.items():
            nxt = hops.get(hop + 1) or []
            # ogranicz fan-out: top 3 z hop -> top 5 z hop+1
            for src in ids[:8]:
                for dst in nxt[:12]:
                    key = (src, dst)
                    if key in seen:
                        continue
                    seen.add(key)
                    edges.append({"source": src, "target": dst, "chain": chain})
                    if len(edges) >= 400:
                        return edges
    return edges


def _seed_status(addresses: dict[str, Any]) -> list[dict[str, Any]]:
    seeds = [
        ("0x770b10b273fc44fe9197d6bf20f145c2e98463ee", "EVM primary"),
        ("rwNhefsz1UQEusxhCvHip3RANinWi4CTck", "XRP primary"),
        ("t1WgMdtND8NF7NDUuYmq8MpMj1NTCXkMDVG", "ZEC primary"),
        ("TBWNguTTgezw9dVorX441C6nDrZpRxYwKD", "TRON primary"),
    ]
    out = []
    lower_map = {k.lower(): k for k in addresses}
    for addr, name in seeds:
        key = lower_map.get(addr.lower(), addr)
        meta = addresses.get(key) or addresses.get(addr) or {}
        out.append(
            {
                "address": key if meta else addr,
                "name": name,
                "usd": _usd(meta),
                "balances": meta.get("balances") or [],
                "hop": meta.get("hop"),
            }
        )
    return out


def watchlist_from_analysis(
    analysis: dict[str, Any],
    min_usd: float = 1_000_000,
    extra: list[str] | None = None,
) -> set[str]:
    addrs = {h["address"] for h in analysis.get("watchlist") or [] if h["usd"] >= min_usd}
    for h in analysis.get("top_holders") or []:
        if h.get("role") == "attacker" and h.get("usd", 0) >= min_usd:
            addrs.add(h["address"])
    for a in extra or []:
        a = a.strip()
        if a:
            addrs.add(a)
    for s in analysis.get("seeds") or []:
        if s.get("usd", 0) > 0:
            addrs.add(s["address"])
    return addrs
