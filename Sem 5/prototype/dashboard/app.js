/* ==========================================================================
   SIMGuard Telecom Fraud Intelligence Console
   Client Application Controller — SOC / Threat Intelligence Interface
   Maintains all API endpoints, XGBoost inference, TreeSHAP explainability,
   and Ethereum smart contract anchors.
   ========================================================================== */
"use strict";

const API = "/api/v1";
const state = {
  thresholds: { review: 0.13, block: 0.9 },
  scenario: null,
  logFilter: "",
  current: null,
  allDecisions: [],
  searchQuery: "",
};

const DECISION = {
  AUTO_APPROVE: { cls: "approve", icon: "✓", label: "AUTO APPROVE", sub: "Low risk. Verified subscriber telemetry allows automated provisioning." },
  MANUAL_REVIEW: { cls: "review", icon: "!", label: "MANUAL REVIEW", sub: "Elevated risk. Escalated to fraud analyst for out-of-band identity verification." },
  AUTO_BLOCK: { cls: "block", icon: "✕", label: "AUTO BLOCK", sub: "Critical threat detected. Request terminated and flagged on immutable ledger." },
};

const LAT_PARTS = [
  ["telemetry_ms", "Telemetry verification", "#22C55E"],
  ["ml_shap_ms", "Model + TreeSHAP", "#38BDF8"],
  ["rules_ms", "Rules & Blacklist", "#F59E0B"],
  ["hashing_ms", "Cryptographic Hashing", "#6366F1"],
  ["chain_ms", "Blockchain Anchor", "#EF4444"],
  ["db_ms", "Database Persistence", "#64748B"],
];

const SCENARIO_ICONS = {
  legitimate: `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/></svg>`,
  genuine: `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/></svg>`,
  suspicious: `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
  attack: `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="18" y1="8" x2="23" y2="13"/><line x1="23" y1="8" x2="18" y2="13"/></svg>`,
  blacklisted: `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="2" width="14" height="20" rx="2" ry="2"/><line x1="12" y1="18" x2="12.01" y2="18"/><line x1="2" y1="2" x2="22" y2="22"/></svg>`,
};

// ───────────────────────── Helpers ─────────────────────────
const $ = (id) => document.getElementById(id);

function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null) continue;
    if (k === "class") el.className = v;
    else if (k === "text") el.textContent = v;
    else if (k === "html") el.innerHTML = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v);
  }
  for (const kid of kids.flat()) {
    if (kid != null) el.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  }
  return el;
}

const short = (s, n = 10) => (s ? `${s.slice(0, n)}…${s.slice(-6)}` : "—");
const pct = (x) => `${(x * 100).toFixed(1)}%`;
const fmt = (x, d = 2) => Number(x).toFixed(d);

function copyToClipboard(text, label = "Value") {
  if (!text) return;
  navigator.clipboard.writeText(text).then(
    () => toast(`${label} copied to clipboard`),
    () => toast("Failed to copy", true)
  );
}

function makeCopyable(displayVal, fullVal, label = "Hash") {
  return h("span", { style: "display:inline-flex;align-items:center;gap:4px;" },
    h("span", { class: "mono", text: displayVal }),
    h("button", {
      class: "copy-btn",
      title: `Copy full ${label}`,
      onclick: (e) => { e.stopPropagation(); copyToClipboard(fullVal, label); },
      html: `<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>`
    })
  );
}

async function api(path, opts) {
  const r = await fetch(API + path, opts);
  const body = await r.json().catch(() => ({}));
  if (!r.ok) {
    throw Object.assign(new Error(body.reason || body.detail || r.statusText), { status: r.status, body });
  }
  return body;
}

function toast(msg, err = false) {
  const t = $("toast");
  if (!t) return;
  t.textContent = msg;
  t.className = "toast" + (err ? " err" : "");
  t.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => { t.hidden = true; }, 4000);
}

function badge(decision) {
  const d = DECISION[decision] || { cls: "review", icon: "?", label: decision };
  const labelClean = d.label.replace("AUTO ", "").replace("MANUAL ", "").toLowerCase().replace(/^./, (c) => c.toUpperCase());
  return h("span", { class: `badge ${d.cls}` },
    h("i", { text: d.icon }),
    labelClean
  );
}

function kv(el, rows) {
  el.replaceChildren();
  for (const [k, v, mono, fullVal, label] of rows) {
    let ddContent;
    if (fullVal) {
      ddContent = makeCopyable(v, fullVal, label || k);
    } else {
      ddContent = v;
    }
    el.append(
      h("dt", { text: k }),
      h("dd", { class: mono && !fullVal ? "mono" : null }, ddContent)
    );
  }
}

// ───────────────────────── Navigation Tabs ─────────────────────────
const TAB_LABELS = {
  evaluate: "Evaluate Request",
  log: "Decision Log",
  ledger: "Blockchain Ledger",
  audit: "Integrity Audit",
  model: "Model Performance",
};

function showTab(name) {
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
  document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("active", p.id === "tab-" + name));
  
  const breadcrumb = $("breadcrumbCurrent");
  if (breadcrumb && TAB_LABELS[name]) {
    breadcrumb.textContent = TAB_LABELS[name];
  }

  if (name === "log") loadLog();
  if (name === "ledger") loadLedger();
  if (name === "audit") loadTargets();
  if (name === "model") loadModel();
}

document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => showTab(t.dataset.tab)));

// ───────────────────────── Header & System Status ─────────────────────────
async function loadHealth() {
  try {
    const hl = await api("/health");
    state.thresholds = hl.thresholds;
    const c = $("chipChain");
    c.className = "chip live";
    
    const blockText = `Block #${hl.chain.latest_block}`;
    const contractShort = short(hl.chain.contract, 6);
    
    c.replaceChildren(
      h("i", { class: "dot" }),
      h("span", { text: `Ethereum Node · ${blockText} · ` }),
      makeCopyable(contractShort, hl.chain.contract, "Contract Address")
    );

    $("chipModel").replaceChildren(
      h("span", { text: `Model ${hl.model_version} · ${hl.blacklist_size} Blacklisted IMEIs` })
    );
  } catch (e) {
    const c = $("chipChain");
    c.className = "chip down";
    c.replaceChildren(
      h("i", { class: "dot" }),
      h("span", { text: "Risk Engine Offline" })
    );
  }
}

// ───────────────────────── Evaluate Request ─────────────────────────
async function loadScenarios() {
  const list = await api("/scenarios");
  const row = $("scenarioRow");
  row.replaceChildren();

  for (const s of list) {
    const iconSvg = SCENARIO_ICONS[s.key] || SCENARIO_ICONS.genuine;
    const btn = h("button", {
      class: "scenario",
      "data-key": s.key,
      onclick: () => runScenario(s.key),
    },
      h("b", {},
        h("span", { style: "display:inline-flex;color:var(--accent-primary);margin-right:6px;", html: iconSvg }),
        s.label
      ),
      h("span", { text: s.description })
    );
    row.append(btn);
  }
}

async function runScenario(key) {
  document.querySelectorAll(".scenario").forEach((b) => b.classList.toggle("active", b.dataset.key === key));
  let req;
  try {
    req = await api("/scenarios/" + key);
    renderRequest(req);
    const res = await api("/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
    state.current = res;
    renderDecision(res);
    renderChain(res);
    loadHealth();
  } catch (e) {
    toast("Evaluation failed: " + e.message, true);
  }
}

function renderRequest(req) {
  $("reqEmpty").hidden = true;
  $("reqBody").hidden = false;
  const b = req.bss;
  const p = req.telemetry.payload;

  kv($("reqKv"), [
    ["Request ID", short(req.request_id, 12), true, req.request_id, "Request ID"],
    ["Subscriber", req.msisdn.slice(0, 3) + "•••••" + req.msisdn.slice(-4), true],
    ["Channel", req.channel.replace("_", " ").toLowerCase()],
    ["Account age", `${Math.round(b.account_age_days)} days`],
    ["Current SIM age", `${Math.round(b.sim_age_days)} days`],
    ["Swaps in 180 days", Math.round(b.swaps_last_180d)],
    ["Requested at", `${String(b.hour_of_request).padStart(2, "0")}:00${b.is_weekend ? " (Weekend)" : ""}`],
    ["Biometric KYC", b.kyc_biometric_verified ? "Verified" : "Unverified"],
    ["Auth failures (7 d)", Math.round(b.auth_failures_7d)],
    ["Profile changed (7 d)", b.profile_change_7d ? "Yes" : "No"],
    ["Agent swaps (24 h)", Math.round(b.agent_swaps_24h)],
  ]);

  const env = req.telemetry;
  kv($("telKv"), [
    ["Edge device", env.device_id, true],
    ["New handset IMEI", short(p.imei, 10), true, p.imei, "IMEI"],
    ["Handset changed", p.imei_changed ? "Yes" : "No"],
    ["Old SIM last seen", `${p.old_sim_last_seen_min} min ago`],
    ["Distance from home", `${p.distance_from_home_km} km`],
    ["Cell changes (24 h)", p.cell_changes_24h],
    ["Serving cell / RSSI", `${p.cell_id} · ${p.rssi_dbm} dBm`],
    ["Nonce", short(env.nonce, 8), true, env.nonce, "Nonce"],
    ["Signature", short(env.signature, 10), true, env.signature, "HMAC Signature"],
  ]);
}

function renderGauge(risk) {
  const g = $("gauge");
  const t = state.thresholds;
  g.style.setProperty("--t1", (t.review * 100) + "%");
  g.style.setProperty("--t2", (t.block * 100) + "%");
  g.replaceChildren(
    h("div", { class: "pin", style: `left:${Math.min(Math.max(risk, 0), 1) * 100}%` }),
    h("div", { class: "tick", style: "left:0", text: "0.0 Safe" }),
    h("div", { class: "tick", style: `left:${t.review * 100}%`, text: `Review ≥ ${t.review}` }),
    h("div", { class: "tick", style: `left:${t.block * 100}%`, text: `Block ≥ ${t.block}` }),
    h("div", { class: "tick", style: "left:100%", text: "1.0 Risk" })
  );
}

function renderDecision(res) {
  $("decEmpty").hidden = true;
  $("decBody").hidden = false;
  const d = DECISION[res.decision];

  $("verdict").className = "verdict " + d.cls;
  $("verdictIcon").textContent = d.icon;
  $("verdictLabel").textContent = d.label;
  $("verdictSub").textContent = d.sub;
  $("verdictScore").textContent = fmt(res.risk_score);
  renderGauge(res.risk_score);

  const parts = $("parts");
  parts.replaceChildren(
    h("span", { class: "pill", text: `Model Probability ${pct(res.ml_probability)}` })
  );

  if (!res.rule_detail || !res.rule_detail.length) {
    parts.append(h("span", { class: "pill", text: "No policy rules triggered" }));
  } else {
    for (const f of res.rule_detail) {
      const cls = { CRITICAL: "crit", HIGH: "high", MEDIUM: "med" }[f.severity] || "med";
      parts.append(
        h("span", { class: "pill " + cls, title: f.detail, text: `${f.rule} · ${f.severity}` })
      );
    }
  }

  const shap = $("shapBars");
  shap.replaceChildren();
  const max = Math.max(...res.reasons.map((r) => Math.abs(r.shap)), 0.01);

  for (const r of res.reasons) {
    const w = (Math.abs(r.shap) / max) * 48;
    shap.append(
      h("div", { class: "shap-row" },
        h("div", { class: "shap-label", text: r.text }),
        h("div", { class: "shap-track" },
          h("div", {
            class: "shap-bar " + (r.shap > 0 ? "up" : "down"),
            style: `width:${w}%`,
            title: `${r.feature}: ${r.shap > 0 ? "+" : ""}${r.shap}`,
          })
        ),
        h("div", {
          class: "shap-val",
          style: r.shap > 0 ? "color:var(--shap-up)" : "color:var(--shap-down)",
          text: (r.shap > 0 ? "+" : "") + fmt(r.shap),
        })
      )
    );
  }

  $("summary").textContent = res.summary;
}

function renderChain(res) {
  $("chainEmpty").hidden = true;
  $("chainBody").hidden = false;

  kv($("chainKv"), [
    ["Ledger entry", `#${res.entry_id}`],
    ["Block number", res.block_number],
    ["Transaction", short(res.tx_hash, 12), true, res.tx_hash, "Transaction Hash"],
    ["Gas consumed", Number(res.gas_used).toLocaleString()],
    ["Decision hash", short(res.decision_hash, 12), true, res.decision_hash, "Decision Hash"],
    ["SHAP hash", short(res.shap_hash, 12), true, res.shap_hash, "SHAP Hash"],
    ["Subscriber ref", short(res.subscriber_ref, 12), true, res.subscriber_ref, "Subscriber Reference"],
    ["Ledger status", "Anchored & Verified On-Chain"],
  ]);

  const lat = res.latency_ms;
  $("totalMs").textContent = `${fmt(lat.total_ms, 1)} ms Latency`;
  const total = LAT_PARTS.reduce((s, [k]) => s + (lat[k] || 0), 0);

  $("latBar").replaceChildren(
    ...LAT_PARTS.map(([k, , c]) =>
      h("span", {
        style: `width:${((lat[k] || 0) / (total || 1)) * 100}%;background:${c}`,
        title: `${k}: ${fmt(lat[k] || 0, 1)} ms`,
      })
    )
  );

  $("latList").replaceChildren(
    ...LAT_PARTS.map(([k, name, c]) =>
      h("li", {},
        h("span", {}, h("i", { style: `background:${c}` }), name),
        h("b", { text: `${fmt(lat[k] || 0, 1)} ms` })
      )
    )
  );
}

// ───────────────────────── Decision Log ─────────────────────────
async function loadLog() {
  const { total, decisions } = await api(
    "/decisions?limit=60" + (state.logFilter ? "&decision=" + state.logFilter : "")
  );
  state.allDecisions = decisions || [];
  renderLogTable();
}

function renderLogTable() {
  const q = state.searchQuery.toLowerCase().trim();
  const filtered = state.allDecisions.filter((d) => {
    if (!q) return true;
    return (
      (d.request_id && d.request_id.toLowerCase().includes(q)) ||
      (d.msisdn_masked && d.msisdn_masked.toLowerCase().includes(q)) ||
      (d.channel && d.channel.toLowerCase().includes(q)) ||
      (d.decision && d.decision.toLowerCase().includes(q)) ||
      (d.tx_hash && d.tx_hash.toLowerCase().includes(q))
    );
  });

  $("logCount").textContent = `${filtered.length} of ${state.allDecisions.length} stored`;
  const tb = document.querySelector("#logTable tbody");
  tb.replaceChildren();

  if (!filtered.length) {
    tb.append(
      h("tr", {},
        h("td", { colspan: 9, class: "empty", text: q ? "No matching decisions found." : "No decisions recorded yet — evaluate a request first." })
      )
    );
    return;
  }

  for (const d of filtered) {
    const action = d.decision === "MANUAL_REVIEW" && !d.resolution
      ? h("button", { class: "btn small primary", onclick: () => openResolve(d), text: "Resolve" })
      : d.resolution
      ? h("span", { class: "tag ok", text: `Resolved: ${d.resolution.final_decision.replace("AUTO_", "").toLowerCase()}` })
      : null;

    tb.append(
      h("tr", {},
        h("td", { class: "num", text: `#${d.entry_id}` }),
        h("td", { class: "mono", text: d.timestamp.slice(0, 19).replace("T", " ") }),
        h("td", { class: "mono", text: d.msisdn_masked }),
        h("td", { text: d.channel.replace("_", " ").toLowerCase() }),
        h("td", {}, badge(d.decision)),
        h("td", { class: "num", text: fmt(d.risk_score) }),
        h("td", { text: d.rule_flags && d.rule_flags.length ? d.rule_flags.join(", ") : "—" }),
        h("td", {}, makeCopyable(short(d.tx_hash, 8), d.tx_hash, "Transaction Hash")),
        h("td", {}, action)
      )
    );
  }
}

// Log Filter & Search bindings
document.querySelectorAll("#logFilter button").forEach((b) => {
  b.addEventListener("click", () => {
    document.querySelectorAll("#logFilter button").forEach((x) => x.classList.toggle("active", x === b));
    state.logFilter = b.dataset.f;
    loadLog();
  });
});

const logSearchInput = $("logSearch");
if (logSearchInput) {
  logSearchInput.addEventListener("input", (e) => {
    state.searchQuery = e.target.value;
    renderLogTable();
  });
}

function openResolve(d) {
  $("resolveFor").textContent = `${d.request_id} · Risk Score ${fmt(d.risk_score)} · ${d.msisdn_masked}`;
  $("resolveNote").value = "";
  $("resolveDialog").dataset.rid = d.request_id;
  $("resolveDialog").showModal();
}

$("resolveForm").addEventListener("submit", async (ev) => {
  if (ev.submitter && ev.submitter.value !== "ok") return;
  const dlg = $("resolveDialog");
  try {
    const r = await api(`/decisions/${dlg.dataset.rid}/resolve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        final_decision: $("resolveDecision").value,
        analyst_id: $("resolveAnalyst").value,
        note: $("resolveNote").value,
      }),
    });
    toast(`Resolution recorded on-chain (Block #${r.block_number || "—"})`);
    dlg.close();
    loadLog();
  } catch (e) {
    toast(e.message, true);
  }
});

// ───────────────────────── Blockchain Ledger ─────────────────────────
async function loadLedger() {
  const l = await api("/ledger?limit=20");
  const s = l.stats;

  $("ledgerStats").replaceChildren(
    ...[
      ["Entries on-chain", s.total],
      ["Auto-approved", s.AUTO_APPROVE],
      ["Manual review", s.MANUAL_REVIEW],
      ["Auto-blocked", s.AUTO_BLOCK],
    ].map(([k, v]) =>
      h("div", { class: "stat" },
        h("b", { text: v }),
        h("span", { text: k })
      )
    )
  );

  kv($("ledgerInfo"), [
    ["Network", l.info.network],
    ["Latest block", l.info.latest_block],
    ["Contract", short(l.info.contract, 10), true, l.info.contract, "Contract Address"],
    ["Compiler", l.info.compiler.split("+")[0] ? "solc " + l.info.compiler.split("+")[0] : l.info.compiler],
    ["Engine account", short(l.info.engine_account, 10), true, l.info.engine_account, "Engine Account"],
    ["Deployment gas", Number(l.info.deploy_gas_used).toLocaleString()],
  ]);

  const tb = document.querySelector("#ledgerTable tbody");
  tb.replaceChildren();

  if (!l.entries || !l.entries.length) {
    tb.append(
      h("tr", {},
        h("td", { colspan: 8, class: "empty", text: "Blockchain ledger is currently empty." })
      )
    );
    return;
  }

  for (const e of l.entries) {
    tb.append(
      h("tr", {},
        h("td", { class: "num", text: `#${e.entry_id}` }),
        h("td", { class: "num", text: e.block_number ?? "—" }),
        h("td", {}, makeCopyable(short(e.subscriber_ref, 8), e.subscriber_ref, "Subscriber Ref")),
        h("td", {}, badge(e.decision)),
        h("td", { class: "num", text: fmt(e.risk_score) }),
        h("td", {}, makeCopyable(short(e.decision_hash, 8), e.decision_hash, "Decision Hash")),
        h("td", {}, makeCopyable(short(e.shap_hash, 8), e.shap_hash, "SHAP Hash")),
        h("td", {
          text: e.resolution
            ? `${e.resolution.final_decision.replace("AUTO_", "").toLowerCase()} (Analyst ${short(e.resolution.analyst_ref, 4)})`
            : "—",
        })
      )
    );
  }
}

// ───────────────────────── Integrity Audit ─────────────────────────
async function loadTargets() {
  const { decisions } = await api("/decisions?limit=30");
  const sel = $("tamperTarget");
  const keep = sel.value;
  sel.replaceChildren(
    ...decisions.map((d) =>
      h("option", {
        value: d.request_id,
        text: `#${d.entry_id} · ${d.decision.replace("AUTO_", "").toLowerCase()} · ${d.msisdn_masked}`,
      })
    )
  );
  if (keep) sel.value = keep;
}

function auditBox(a) {
  const ok = a.integrity_ok;
  const box = h("div", { class: "result-box " + (ok ? "ok" : "bad") },
    h("b", { text: ok ? "✓ Cryptographic Integrity Verified" : `⚠ ${a.tampered} Integrity Violation${a.tampered > 1 ? "s" : ""} Detected!` }),
    h("div", { text: `${a.verified} of ${a.on_chain_entries} on-chain records match their off-chain cryptographic preimage in SQLite (${a.audit_seconds}s).` })
  );

  if (!ok && a.findings) {
    box.append(
      h("ul", {},
        a.findings.map((f) => h("li", { text: `Entry #${f.entry_id}: ${f.reason}` }))
      )
    );
  }
  return box;
}

$("btnVerify").addEventListener("click", async () => {
  const res = await api("/audit/verify");
  $("auditResult").replaceChildren(auditBox(res));
});

document.querySelectorAll("[data-tamper]").forEach((b) => {
  b.addEventListener("click", async () => {
    const rid = $("tamperTarget").value;
    if (!rid) return toast("Evaluate a request first to generate records.", true);
    const t = await api("/demo/tamper", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ request_id: rid, mode: b.dataset.tamper }),
    });
    const a = await api("/audit/verify");
    $("tamperResult").replaceChildren(
      h("p", { class: "muted", style: "color:var(--warning);font-weight:600;", text: `Insider Action Simulated: ${t.change}.` }),
      auditBox(a)
    );
  });
});

$("btnRestore").addEventListener("click", async () => {
  await api("/demo/restore", { method: "POST" });
  const a = await api("/audit/verify");
  $("tamperResult").replaceChildren(
    h("p", { class: "muted", style: "color:var(--success);font-weight:600;", text: "All database records restored to match blockchain state." }),
    auditBox(a)
  );
  loadTargets();
});

document.querySelectorAll("[data-edge]").forEach((b) => {
  b.addEventListener("click", async () => {
    const r = await api("/demo/edge-attack/" + b.dataset.edge, { method: "POST" });
    const tb = document.querySelector("#edgeTable tbody");
    tb.prepend(
      h("tr", {},
        h("td", { style: "font-weight:600;", text: r.what }),
        h("td", { class: "mono", text: r.reason }),
        h("td", {},
          h("span", {
            class: "tag " + (r.accepted ? "bad" : "ok"),
            text: r.accepted ? "ACCEPTED (VULNERABLE)" : "REJECTED (DEFENDED)",
          })
        )
      )
    );
  });
});

// ───────────────────────── Model Performance ─────────────────────────
async function loadModel() {
  const m = await api("/metrics");
  const tb = document.querySelector("#modelTable tbody");
  tb.replaceChildren();

  for (const [name, v] of Object.entries(m.comparison.models)) {
    const isProposed = name.includes("proposed");
    tb.append(
      h("tr", { style: isProposed ? "background:rgba(56,189,248,0.08);font-weight:700;" : null },
        h("td", { text: (isProposed ? "★ " : "") + name }),
        h("td", { class: "num", text: fmt(v.precision, 3) }),
        h("td", { class: "num", text: fmt(v.recall, 3) }),
        h("td", { class: "num", text: fmt(v.f1, 3) }),
        h("td", { class: "num", text: fmt(v.roc_auc, 3) }),
        h("td", { class: "num", text: fmt(v.pr_auc, 3) })
      )
    );
  }

  const sp = m.comparison.split;
  $("modelNote").textContent = `Evaluation conducted on held-out test split of ${sp.test} requests (${sp.test_fraud} confirmed fraud cases). Policy thresholds fixed on validation set. 5-Fold Cross-Validation ROC-AUC: ${fmt(m.comparison.xgboost_cv.roc_auc_mean, 3)} ± ${fmt(m.comparison.xgboost_cv.roc_auc_std, 3)}.`;

  const p = m.meta.policy;
  kv($("policyKv"), [
    ["Algorithm Version", m.meta.model_version],
    ["Ensemble Estimators", `${m.meta.n_trees} Trees`],
    ["Review Threshold (t_review)", `Risk Score ≥ ${p.t_review}`],
    ["Block Threshold (t_block)", `Risk Score ≥ ${p.t_block}`],
    ["Max Review Capacity", pct(p.review_capacity)],
    ["Penalty: Missed Fraud", p.cost_weights.missed_fraud],
    ["Penalty: False Block", p.cost_weights.false_block],
    ["Cost: Manual Review", p.cost_weights.review],
  ]);
}

// ───────────────────────── Boot ─────────────────────────
(async function boot() {
  await loadHealth();
  await loadScenarios();
  const q = new URLSearchParams(location.search);
  if (q.get("tab")) showTab(q.get("tab"));
  if (q.get("scenario")) await runScenario(q.get("scenario"));
})();
