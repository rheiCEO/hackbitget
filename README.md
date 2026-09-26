# HackBitget · bitget-trace

Independent on-chain tracker for the **Bitget Sep 24 2026** exploit (~$387.5M) and the official **5% freeze / 5% recovery** bounty.

Live site: **[hackbitget.pages.dev](https://hackbitget.pages.dev)**

> Unofficial community tool. Data from Bitget public APIs. Not affiliated with Bitget.

## What it does

| Piece | Role |
|---|---|
| `bitget_trace fetch` | Pulls official `/api/addresses` + `/api/holdings` |
| `bitget_trace analyze` | Builds hop/token/role aggregates + approximate peel graph |
| `bitget_trace build-site` | Writes `site/data/snapshot.json` for the Pages UI |
| `bitget_trace watch` | Polls watchlist (≥$1M + seeds) → Discord / Telegram alerts |
| `site/` | Professional Bitget-green dashboard (Cloudflare Pages) |

## Quick start

```bash
cd projects/bitget-trace   # or clone this repo root
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -e .
cp .env.example .env       # optional webhooks

python -m bitget_trace fetch
python -m bitget_trace build-site
python -m bitget_trace watch --once   # baseline
python -m bitget_trace watch          # loop
```

Local site preview:

```bash
npx --yes serve site
# or: python -m http.server -d site 8787
```

## Deploy → hackbitget.pages.dev

### A) Cloudflare dashboard (fastest)

1. Push this repo to GitHub.
2. Cloudflare → **Workers & Pages** → **Create** → **Pages** → connect repo.
3. Project name: `hackbitget` (gives `hackbitget.pages.dev`).
4. Build command: *(empty)* · Output directory: `site`.
5. Add secrets for GitHub Action deploy (optional):
   - `CLOUDFLARE_API_TOKEN`
   - `CLOUDFLARE_ACCOUNT_ID`

### B) Wrangler CLI

```bash
npx wrangler pages project create hackbitget
npx wrangler pages deploy site --project-name=hackbitget
```

Snapshot auto-refresh: `.github/workflows/refresh-snapshot.yml` (every 30 min).

## Alert config (`.env`)

```env
POLL_INTERVAL=60
WATCH_MIN_USD=1000000
MIN_USD_DELTA=1000
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
WATCH_EXTRA=t1WgMdtND8NF7NDUuYmq8MpMj1NTCXkMDVG
```

## Official Bitget links

- [Bounty announcement](https://www.bitget.com/support/articles/12560603896108)
- [Live dashboard](https://trace.bgblockchain.xyz/v2#explorer)
- [Report portal](https://trace.bgblockchain.xyz/report)
- [Addresses API](https://trace.bgblockchain.xyz/api/addresses)

## License

MIT — use at your own risk; always comply with applicable law and Bitget bounty terms.
