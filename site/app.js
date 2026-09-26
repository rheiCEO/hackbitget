const DATA_URL = "./data/snapshot.json";

const $ = (sel) => document.querySelector(sel);

function fmtUsd(n) {
  if (n == null || Number.isNaN(n)) return "—";
  const abs = Math.abs(n);
  if (abs >= 1e9) return `$${(n / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `$${(n / 1e6).toFixed(2)}M`;
  if (abs >= 1e3) return `$${(n / 1e3).toFixed(1)}K`;
  return `$${n.toFixed(0)}`;
}

function shortAddr(a) {
  if (!a) return "—";
  if (a.length <= 16) return a;
  return `${a.slice(0, 8)}…${a.slice(-6)}`;
}

function explorerUrl(address, chains = []) {
  const c = (chains[0] || "").toUpperCase();
  if (c === "BTC" || address.startsWith("bc1") || address.startsWith("1") || address.startsWith("3")) {
    return `https://mempool.space/address/${address}`;
  }
  if (c === "XRP" || address.startsWith("r")) {
    return `https://xrpscan.com/account/${address}`;
  }
  if (c === "TRON" || address.startsWith("T")) {
    return `https://tronscan.org/#/address/${address}`;
  }
  if (c === "ZEC" || address.startsWith("t1") || address.startsWith("zs")) {
    return `https://explorer.zcha.in/accounts/${address}`;
  }
  if (c === "ALGO") {
    return `https://allo.info/account/${address}`;
  }
  if (c === "BSC") {
    return `https://bscscan.com/address/${address}`;
  }
  if (c === "ARB") {
    return `https://arbiscan.io/address/${address}`;
  }
  return `https://etherscan.io/address/${address}`;
}

async function loadData() {
  const res = await fetch(DATA_URL, { cache: "no-store" });
  if (!res.ok) throw new Error(`snapshot ${res.status}`);
  return res.json();
}

function renderStats(data) {
  const t = data.totals || {};
  const c = data.concentration || {};
  $("#stat-usd").textContent = fmtUsd(t.usd);
  $("#stat-usd-sub").textContent = `of ~$387.5M reported`;
  $("#stat-addrs").textContent = (t.addresses || 0).toLocaleString();
  $("#stat-addrs-sub").textContent = "labeled graph nodes";
  $("#stat-nonzero").textContent = (t.nonzero || 0).toLocaleString();
  $("#stat-whales").textContent = String(c.ge_1m ?? "—");
  $("#stat-whales-sub").textContent = `${fmtUsd(c.ge_1m_usd)} · top10 ${c.top10_pct}%`;
  const ts = data.generated_at ? new Date(data.generated_at) : null;
  $("#snap-time").textContent = ts ? ts.toISOString().replace("T", " ").slice(0, 19) + " UTC" : "—";
  $("#snap-time").dateTime = data.generated_at || "";
}

function renderTokens(data) {
  const tokens = Object.entries(data.tokens || {})
    .filter(([, v]) => v.usd >= 1000)
    .slice(0, 10);
  const max = Math.max(...tokens.map(([, v]) => v.usd), 1);
  const root = $("#token-bars");
  root.innerHTML = "";
  for (const [key, v] of tokens) {
    const row = document.createElement("div");
    row.className = "token-row";
    row.innerHTML = `
      <div class="token-name">${key}</div>
      <div class="bar-track"><div class="bar-fill" style="width:0%"></div></div>
      <div class="token-usd">${fmtUsd(v.usd)}</div>
    `;
    root.appendChild(row);
    requestAnimationFrame(() => {
      row.querySelector(".bar-fill").style.width = `${(100 * v.usd) / max}%`;
    });
  }
}

function renderSeeds(data) {
  const root = $("#seed-list");
  root.innerHTML = "";
  for (const s of data.seeds || []) {
    const el = document.createElement("div");
    el.className = `seed-item${s.usd > 1e6 ? " hot" : ""}`;
    el.innerHTML = `
      <div>
        <div class="name">${s.name}</div>
        <a class="addr" href="${explorerUrl(s.address)}" target="_blank" rel="noopener">${s.address}</a>
      </div>
      <div class="usd">${fmtUsd(s.usd)}</div>
    `;
    root.appendChild(el);
  }
}

function renderInfra(data) {
  const root = $("#infra-tags");
  root.innerHTML = "";
  const seen = new Set();
  for (const c of data.cex || []) {
    const label = (c.label || c.address || "CEX").slice(0, 48);
    if (seen.has(label)) continue;
    seen.add(label);
    const t = document.createElement("span");
    t.className = "tag cex";
    t.textContent = label;
    root.appendChild(t);
  }
  for (const b of data.bridges || []) {
    const label = (b.label || "bridge").slice(0, 40);
    if (seen.has(label)) continue;
    seen.add(label);
    const t = document.createElement("span");
    t.className = "tag bridge";
    t.textContent = label;
    root.appendChild(t);
  }
}

function renderHolders(data) {
  const body = $("#holders-body");
  const search = $("#holder-search");
  const rows = data.top_holders || [];

  const paint = () => {
    const q = (search.value || "").trim().toLowerCase();
    body.innerHTML = "";
    let i = 0;
    for (const h of rows) {
      const hay = `${h.address} ${(h.chains || []).join(" ")}`.toLowerCase();
      if (q && !hay.includes(q)) continue;
      i += 1;
      const bals = (h.balances || [])
        .slice(0, 3)
        .map((b) => `${Number(b.amount).toLocaleString(undefined, { maximumFractionDigits: 4 })} ${b.sym}`)
        .join(" · ");
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${i}</td>
        <td class="mono">
          <a class="copy-addr" href="${explorerUrl(h.address, h.chains)}" target="_blank" rel="noopener" title="${h.address}">${shortAddr(h.address)}</a>
        </td>
        <td class="usd">${fmtUsd(h.usd)}</td>
        <td>${h.hop ?? "—"}</td>
        <td>${(h.chains || []).join(", ")}</td>
        <td class="mono">${bals || "—"}</td>
      `;
      body.appendChild(tr);
    }
  };

  search.addEventListener("input", paint);
  paint();
}

function layoutGraph(nodes) {
  const attackers = nodes.filter((n) => n.role === "attacker" && n.usd > 0);
  const hops = [...new Set(attackers.map((n) => n.hop).filter((h) => h >= 0))].sort((a, b) => a - b);
  const W = 1200;
  const H = 640;
  const cx = W / 2;
  const cy = H / 2;
  const placed = [];

  for (const n of attackers.slice(0, 120)) {
    const hop = n.hop < 0 ? 0 : n.hop;
    const ring = hops.indexOf(hop);
    const r = 60 + (ring < 0 ? 0 : ring) * 42;
    const same = attackers.filter((x) => x.hop === n.hop);
    const idx = same.indexOf(n);
    const angle = (idx / Math.max(same.length, 1)) * Math.PI * 2 - Math.PI / 2;
    const jitter = (Math.sin(idx * 12.9898) * 0.5 + 0.5) * 18;
    placed.push({
      ...n,
      x: cx + Math.cos(angle) * (r + jitter),
      y: cy + Math.sin(angle) * (r + jitter) * 0.92,
      r: Math.max(3, Math.min(22, Math.sqrt(n.usd) / 900)),
    });
  }
  return { placed, W, H, cx, cy, hops };
}

function drawNetwork(data) {
  const canvas = $("#network-canvas");
  const tip = $("#graph-tooltip");
  const legend = $("#graph-legend");
  const ctx = canvas.getContext("2d");
  const graph = data.graph || { nodes: [], edges: [] };
  const { placed, W, H, cx, cy, hops } = layoutGraph(graph.nodes || []);
  const byId = Object.fromEntries(placed.map((n) => [n.id, n]));

  legend.innerHTML = hops
    .slice(0, 8)
    .map((h) => `<span>hop ${h}</span>`)
    .join("");

  const edgeSet = (graph.edges || []).filter((e) => byId[e.source] && byId[e.target]);

  function paint(hoverId) {
    ctx.clearRect(0, 0, W, H);

    // rings
    ctx.strokeStyle = "rgba(0,240,160,0.08)";
    ctx.lineWidth = 1;
    for (let i = 0; i < Math.min(hops.length, 10); i++) {
      ctx.beginPath();
      ctx.ellipse(cx, cy, 60 + i * 42, (60 + i * 42) * 0.92, 0, 0, Math.PI * 2);
      ctx.stroke();
    }

    ctx.strokeStyle = "rgba(0,240,160,0.12)";
    for (const e of edgeSet) {
      const a = byId[e.source];
      const b = byId[e.target];
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
    }

    for (const n of placed) {
      const active = hoverId && n.id === hoverId;
      ctx.beginPath();
      ctx.fillStyle = active ? "#5fffc4" : "#00f0a0";
      ctx.globalAlpha = active ? 1 : 0.75;
      ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
      ctx.fill();
      if (active) {
        ctx.strokeStyle = "#fff";
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
      ctx.globalAlpha = 1;
    }
  }

  paint(null);

  canvas.addEventListener("mousemove", (ev) => {
    const rect = canvas.getBoundingClientRect();
    const x = ((ev.clientX - rect.left) / rect.width) * W;
    const y = ((ev.clientY - rect.top) / rect.height) * H;
    let hit = null;
    for (const n of placed) {
      const d = Math.hypot(n.x - x, n.y - y);
      if (d <= n.r + 4) {
        hit = n;
        break;
      }
    }
    paint(hit?.id || null);
    if (!hit) {
      tip.hidden = true;
      return;
    }
    tip.hidden = false;
    tip.style.left = `${ev.clientX - rect.left + 12}px`;
    tip.style.top = `${ev.clientY - rect.top + 12}px`;
    tip.innerHTML = `${shortAddr(hit.id)}<br/>${fmtUsd(hit.usd)} · hop ${hit.hop}<br/>${(hit.chains || []).join(", ")}`;
  });

  canvas.addEventListener("mouseleave", () => {
    tip.hidden = true;
    paint(null);
  });
}

async function main() {
  try {
    const data = await loadData();
    renderStats(data);
    renderTokens(data);
    renderSeeds(data);
    renderInfra(data);
    renderHolders(data);
    drawNetwork(data);
  } catch (err) {
    console.error(err);
    $("#stat-usd").textContent = "Error";
    $("#stat-usd-sub").textContent = String(err.message || err);
  }
}

main();
