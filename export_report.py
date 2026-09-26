# Generuje RAPORT.md + holders.csv ze snapshotu API Bitget
import json
import csv
from pathlib import Path
from datetime import datetime, timezone

d = Path(__file__).resolve().parent
addrs = json.loads((d / "addresses.json").read_text(encoding="utf-8"))
act = json.loads((d / "actionable.json").read_text(encoding="utf-8"))

with (d / "holders.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["address", "usd", "hop", "role", "chains", "balances_json", "last_t"])
    for a, m in sorted(addrs.items(), key=lambda x: -float(x[1].get("usd") or 0)):
        usd = float(m.get("usd") or 0)
        if usd <= 0:
            continue
        w.writerow(
            [
                a,
                usd,
                m.get("hop"),
                m.get("role"),
                "|".join(m.get("chains") or []),
                json.dumps(m.get("balances") or [], ensure_ascii=False),
                m.get("last_t"),
            ]
        )

lines = [
    "# Bitget hack — mapa środków (snapshot)",
    "",
    f"- Zrodlo: oficjalne API Bitget `trace.bgblockchain.xyz`",
    f"- Snapshot: `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}`",
    f"- Adresy w grafie: **1881**",
    f"- Adresy z saldem > 0: **1270**",
    f"- Suma USD w klastrze: **~$385,25 mln** (oficjalnie ~$387,5 mln)",
    "",
    "## Gdzie sa srodki TERAZ (po tokenach)",
    "",
    "| Token | Lancuch | USD | Ilosc | Adresy | Freezable USD |",
    "|---|---|---:|---:|---:|---:|",
]
for k, v in act["tokens"].items():
    if v["usd"] < 100:
        continue
    sym, chain = (k.split("@") + ["?"])[:2]
    lines.append(
        f"| {sym} | {chain} | {v['usd']:,.0f} | {v['amount']:,.4f} | {v['addrs']} | {v['freezable_usd']:,.0f} |"
    )

lines += [
    "",
    "## Koncentracja",
    "",
    "- Top 10 adresow ~ **68%** srodkow",
    "- Top 50 ~ **82%**",
    "- Top 100 ~ **88%**",
    "- 23 adresy >= $1M trzymaja ~$295 mln",
    "- 942 adresy < $1k = szum peel-chain (~$6,7k lacznie)",
    "",
    "## TOP 20 adresow (aktualne saldo)",
    "",
    "| # | USD | Hop | Chain | Adres | Saldo |",
    "|---:|---:|---:|---|---|---|",
]
for i, t in enumerate(act["top20"], 1):
    bals = t.get("balances") or []
    bal = "; ".join(f"{b.get('amount')} {b.get('sym')}" for b in bals[:3])
    chains = ",".join(t.get("chains") or [])
    lines.append(
        f"| {i} | {t['usd']:,.0f} | {t.get('hop')} | {chains} | `{t['address']}` | {bal} |"
    )

lines += [
    "",
    "## Seed wallets (oficjalne Bitget)",
    "",
    "| Adres | Status |",
    "|---|---|",
    "| `0x770b10b273fc44fe9197d6bf20f145c2e98463ee` | prawie pusty (~$2,3k pylu multi-chain) |",
    "| `rwNhefsz1UQEusxhCvHip3RANinWi4CTck` | pusty (~3 XRP) |",
    "| `t1WgMdtND8NF7NDUuYmq8MpMj1NTCXkMDVG` | **NADAL ~18 912 ZEC ~ $29,4 mln** |",
    "| `TBWNguTTgezw9dVorX441C6nDrZpRxYwKD` | pusty |",
    "",
    "## Wzorce przeplywu",
    "",
    "1. ETH chunking: 6 walletow po ~10 000 ETH (~$161 mln).",
    "2. BTC: ~1 237 BTC na 309 adresach (hop 5-11) przez THORChain/Chainflip.",
    "3. XRP: 2 duze hop-2 trzymaja wiekszosc; reszta peel na XRPL.",
    "4. ZEC: nadal na seedzie — monitoring depozytu CEX.",
    "5. ALGO: ~10,1 mln na 1 adresie; sciezki KuCoin w grafie.",
    "6. Stablecoiny: prawie wyczyszczone; freezable ~$2,2k.",
    "",
    "## Infrastruktura w grafie",
    "",
    "- CEX/swap: Binance (ZEC), KuCoin (ALGO), FixedFloat (BSC)",
    "- Bridge: THORChain, Chainflip, Across, Stargate, deBridge, Mayan, Celer, LI.FI, NEAR Intents",
    "- DEX: UniswapX/V3/V4, 1inch Fusion, MetaMask Swaps",
    "",
    "## Pliki",
    "",
    "- `addresses.json` — pelny graf Bitget",
    "- `holdings.json` — listy adresow per chain",
    "- `actionable.json` — top holders + freezable + CEX",
    "- `holders.csv` — wszystkie adresy z saldem",
    "",
]

(d / "RAPORT.md").write_text("\n".join(lines), encoding="utf-8")
print("Wrote RAPORT.md and holders.csv")
