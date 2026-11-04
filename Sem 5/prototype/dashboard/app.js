/* SIMGuard operations console.
   Every value rendered here comes from the risk-engine API (model, rules, SQLite, smart contract). */
"use strict";

const API = "/api/v1";
const state = { thresholds: { review: 0.13, block: 0.9 }, scenario: null, logFilter: "", current: null };

const DECISION = {
  AUTO_APPROVE: { cls: "approve", icon: "✓", label: "AUTO APPROVE", sub: "Low risk. The SIM replacement can proceed." },
  MANUAL_REVIEW: { cls: "review", icon: "!", label: "MANUAL REVIEW", sub: "Elevated risk. A fraud analyst must verify the customer first." },
  AUTO_BLOCK: { cls: "block", icon: "✕", label: "AUTO BLOCK", sub: "High risk. The SIM replacement is stopped automatically." },
};
const LAT_PARTS = [
  ["telemetry_ms", "Telemetry verification", "#1baf7a"],
  ["ml_shap_ms", "Model + SHAP", "#2a78d6"],
  ["rules_ms", "Rules + blacklist", "#eda100"],
  ["hashing_ms", "Hashing", "#4a3aa7"],
  ["chain_ms", "Blockchain transaction", "#e34948"],
  ["db_ms", "Database write", "#7b8190"],
];

// ───────────────────────── helpers ─────────────────────────
const $ = (id) => document.getElementById(id);
function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null) continue;
    if (k === "class") el.className = v;
    else if (k === "text") el.textContent = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v);
  }
  for (const kid of kids.flat()) if (kid != null) el.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  return el;
}
const short = (s, n = 10) => (s ? `${s.slice(0, n)}…${s.slice(-6)}` : "—");
const pct = (x) => `${(x * 100).toFixed(1)}%`;
const fmt = (x, d = 2) => Number(x).toFixed(d);
async function api(path, opts) {
  const r = await fetch(API + path, opts);
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw Object.assign(new Error(body.reason || body.detail || r.statusText), { status: r.status, body });
  return body;
}
function toast(msg, err = false) {
  const t = $("toast");
  t.textContent = msg;
  t.className = "toast" + (err ? " err" : "");
  t.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => (t.hidden = true), 4500);
}
function badge(decision) {
  const d = DECISION[decision];
  return h("span", { class: `badge ${d.cls}` }, h("i", { text: d.icon }), d.label.replace("AUTO ", "").replace("MANUAL ", "").toLowerCase().replace(/^./, (c) => c.toUpperCase()));
}
function kv(el, rows) {
  el.replaceChildren();
  for (const [k, v, mono] of rows) {
    el.append(h("dt", { text: k }), h("dd", { class: mono ? "mono" : null }, v));
  }
}

// ───────────────────────── tabs ─────────────────────────
function showTab(name) {
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
  document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("active", p.id === "tab-" + name));
  if (name === "log") loadLog();
  if (name === "ledger") loadLedger();
  if (name === "audit") loadTargets();
  if (name === "model") loadModel();
}
document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => showTab(t.dataset.tab)));

// ───────────────────────── header ─────────────────────────
async function loadHealth() {
  try {
    const hl = await api("/health");
    state.thresholds = hl.thresholds;
    const c = $("chipChain");
    c.className = "chip live";
    c.replaceChildren(h("i", { class: "dot" }), h("span", { text: `Ethereum node · block ${hl.chain.latest_block} · contract ${short(hl.chain.contract, 8)}` }));
    $("chipModel").replaceChildren(h("span", { text: `${hl.model_version} · ${hl.blacklist_size} blacklisted IMEIs` }));
  } catch (e) {
    const c = $("chipChain");
    c.className = "chip down";
    c.replaceChildren(h("i", { class: "dot" }), h("span", { text: "Risk engine unreachable" }));
  }
}

// ───────────────────────── evaluate ─────────────────────────
async function loadScenarios() {
  const list = await api("/scenarios");
  const row = $("scenarioRow");
  row.replaceChildren();
  for (const s of list) {
    row.append(h("button", { class: "scenario", "data-key": s.key, onclick: () => runScenario(s.key) }, h("b", { text: s.label }), h("span", { text: s.description })));
  }
}

async function runScenario(key) {
  document.querySelectorAll(".scenario").forEach((b) => b.classList.toggle("active", b.dataset.key === key));
  let req;
  try {
    req = await api("/scenarios/" + key);
    renderRequest(req);
    const res = await api("/evaluate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(req) });
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
  const b = req.bss, p = req.telemetry.payload;
  kv($("reqKv"), [
    ["Request ID", req.request_id, true],
    ["Subscriber", req.msisdn.slice(0, 3) + "•••••" + req.msisdn.slice(-4)],
    ["Channel", req.channel.replace("_", " ").toLowerCase()],
    ["Account age", `${Math.round(b.account_age_days)} days`],
    ["Current SIM age", `${Math.round(b.sim_age_days)} days`],
    ["Swaps in 180 days", Math.round(b.swaps_last_180d)],
    ["Requested at", `${String(b.hour_of_request).padStart(2, "0")}:00${b.is_weekend ? " (weekend)" : ""}`],
    ["Biometric KYC", b.kyc_biometric_verified ? "completed" : "not completed"],
    ["Auth failures (7 d)", Math.round(b.auth_failures_7d)],
    ["Profile changed (7 d)", b.profile_change_7d ? "yes" : "no"],
    ["Agent swaps (24 h)", Math.round(b.agent_swaps_24h)],
  ]);
  const env = req.telemetry;
  kv($("telKv"), [
    ["Edge device", env.device_id, true],
    ["New handset IMEI", p.imei, true],
    ["Handset changed", p.imei_changed ? "yes" : "no"],
    ["Old SIM last seen", `${p.old_sim_last_seen_min} min ago`],
    ["Distance from home", `${p.distance_from_home_km} km`],
    ["Cell changes (24 h)", p.cell_changes_24h],
    ["Serving cell / RSSI", `${p.cell_id} · ${p.rssi_dbm} dBm`],
    ["Nonce", short(env.nonce, 8), true],
    ["Signature", short(env.signature, 12), true],
  ]);
}

function renderGauge(risk) {
  const g = $("gauge"), t = state.thresholds;
  g.style.setProperty("--t1", t.review * 100 + "%");
  g.style.setProperty("--t2", t.block * 100 + "%");
  g.replaceChildren(
    h("div", { class: "pin", style: `left:${risk * 100}%` }),
    h("div", { class: "tick", style: "left:0", text: "0" }),
    h("div", { class: "tick", style: `left:${t.review * 100}%`, text: `review ≥ ${t.review}` }),
    h("div", { class: "tick", style: `left:${t.block * 100}%`, text: `block ≥ ${t.block}` }),
    h("div", { class: "tick", style: "left:100%", text: "1" })
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
  parts.replaceChildren(h("span", { class: "pill", text: `Model fraud probability ${pct(res.ml_probability)}` }));
  if (!res.rule_detail.length) parts.append(h("span", { class: "pill", text: "No policy rules triggered" }));
  for (const f of res.rule_detail) {
    parts.append(h("span", { class: "pill " + { CRITICAL: "crit", HIGH: "high", MEDIUM: "med" }[f.severity], title: f.detail, text: `${f.rule} · ${f.severity}` }));
  }

  const shap = $("shapBars");
  shap.replaceChildren();
  const max = Math.max(...res.reasons.map((r) => Math.abs(r.shap)), 0.01);
  for (const r of res.reasons) {
    const w = (Math.abs(r.shap) / max) * 50;
    shap.append(
      h("div", { class: "shap-row" },
        h("div", { class: "shap-label", text: r.text }),
        h("div", { class: "shap-track" }, h("div", { class: "shap-bar " + (r.shap > 0 ? "up" : "down"), style: `width:${w}%`, title: `${r.feature}: ${r.shap > 0 ? "+" : ""}${r.shap}` })),
        h("div", { class: "shap-val", text: (r.shap > 0 ? "+" : "") + fmt(r.shap) })
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
    ["Block", res.block_number],
    ["Transaction", short(res.tx_hash, 14), true],
    ["Gas used", Number(res.gas_used).toLocaleString()],
    ["Decision hash", short(res.decision_hash, 14), true],
    ["SHAP hash", short(res.shap_hash, 14), true],
    ["Subscriber ref", short(res.subscriber_ref, 14), true],
  ]);
  const lat = res.latency_ms;
  $("totalMs").textContent = `${fmt(lat.total_ms, 0)} ms total`;
  const total = LAT_PARTS.reduce((s, [k]) => s + (lat[k] || 0), 0);
  $("latBar").replaceChildren(...LAT_PARTS.map(([k, , c]) => h("span", { style: `width:${((lat[k] || 0) / total) * 100}%;background:${c}`, title: `${k}: ${lat[k]} ms` })));
  $("latList").replaceChildren(...LAT_PARTS.map(([k, name, c]) => h("li", {}, h("span", {}, h("i", { style: `background:${c}` }), name), h("b", { text: `${fmt(lat[k] || 0, 1)} ms` }))));
}

// ───────────────────────── decision log ─────────────────────────
async function loadLog() {
  const { total, decisions } = await api("/decisions?limit=60" + (state.logFilter ? "&decision=" + state.logFilter : ""));
  $("logCount").textContent = `${total} stored`;
  const tb = document.querySelector("#logTable tbody");
  tb.replaceChildren();
  if (!decisions.length) tb.append(h("tr", {}, h("td", { colspan: 9, class: "empty", text: "No decisions yet — evaluate a request first." })));
  for (const d of decisions) {
    const action = d.decision === "MANUAL_REVIEW" && !d.resolution
      ? h("button", { class: "btn small primary", onclick: () => openResolve(d), text: "Resolve" })
      : d.resolution ? h("span", { class: "hint", text: `Resolved: ${d.resolution.final_decision.replace("AUTO_", "").toLowerCase()}` }) : null;
    tb.append(h("tr", {},
      h("td", { class: "num", text: `#${d.entry_id}` }),
      h("td", { class: "mono", text: d.timestamp.slice(0, 19).replace("T", " ") }),
      h("td", { class: "mono", text: d.msisdn_masked }),
      h("td", { text: d.channel.replace("_", " ").toLowerCase() }),
      h("td", {}, badge(d.decision)),
      h("td", { class: "num", text: fmt(d.risk_score) }),
      h("td", { text: d.rule_flags.length ? d.rule_flags.join(", ") : "—" }),
      h("td", { class: "mono", text: short(d.tx_hash, 10) }),
      h("td", {}, action)
    ));
  }
}
document.querySelectorAll("#logFilter button").forEach((b) => b.addEventListener("click", () => {
  document.querySelectorAll("#logFilter button").forEach((x) => x.classList.toggle("active", x === b));
  state.logFilter = b.dataset.f;
  loadLog();
}));

function openResolve(d) {
  $("resolveFor").textContent = `${d.request_id} · risk ${fmt(d.risk_score)} · ${d.msisdn_masked}`;
  $("resolveNote").value = "";
  $("resolveDialog").dataset.rid = d.request_id;
  $("resolveDialog").showModal();
}
$("resolveForm").addEventListener("submit", async (ev) => {
  if (ev.submitter && ev.submitter.value !== "ok") return;
  const dlg = $("resolveDialog");
  try {
    const r = await api(`/decisions/${dlg.dataset.rid}/resolve`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ final_decision: $("resolveDecision").value, analyst_id: $("resolveAnalyst").value, note: $("resolveNote").value }),
    });
    toast(`Outcome recorded on-chain (tx ${short(r.tx_hash, 10)})`);
    loadLog();
  } catch (e) { toast(e.message, true); }
});

// ───────────────────────── ledger ─────────────────────────
async function loadLedger() {
  const l = await api("/ledger?limit=20");
  const s = l.stats;
  $("ledgerStats").replaceChildren(...[["Entries on-chain", s.total], ["Auto-approved", s.AUTO_APPROVE], ["Manual review", s.MANUAL_REVIEW], ["Auto-blocked", s.AUTO_BLOCK]]
    .map(([k, v]) => h("div", { class: "stat" }, h("b", { text: v }), h("span", { text: k }))));
  kv($("ledgerInfo"), [
    ["Network", l.info.network], ["Latest block", l.info.latest_block],
    ["Contract", l.info.contract, true], ["Compiler", l.info.compiler.split("+")[0] ? "solc " + l.info.compiler.split("+")[0] : l.info.compiler],
    ["Engine account", l.info.engine_account, true], ["Deployment gas", Number(l.info.deploy_gas_used).toLocaleString()],
  ]);
  const tb = document.querySelector("#ledgerTable tbody");
  tb.replaceChildren();
  if (!l.entries.length) tb.append(h("tr", {}, h("td", { colspan: 8, class: "empty", text: "Ledger is empty." })));
  for (const e of l.entries) {
    tb.append(h("tr", {},
      h("td", { class: "num", text: `#${e.entry_id}` }), h("td", { class: "num", text: e.block_number ?? "—" }),
      h("td", { class: "mono", text: short(e.subscriber_ref, 8) }), h("td", {}, badge(e.decision)),
      h("td", { class: "num", text: fmt(e.risk_score) }), h("td", { class: "mono", text: short(e.decision_hash, 8) }),
      h("td", { class: "mono", text: short(e.shap_hash, 8) }),
      h("td", { text: e.resolution ? `${e.resolution.final_decision.replace("AUTO_", "").toLowerCase()} (analyst ${short(e.resolution.analyst_ref, 4)})` : "—" })
    ));
  }
}

// ───────────────────────── audit ─────────────────────────
async function loadTargets() {
  const { decisions } = await api("/decisions?limit=30");
  const sel = $("tamperTarget");
  const keep = sel.value;
  sel.replaceChildren(...decisions.map((d) => h("option", { value: d.request_id, text: `#${d.entry_id} · ${d.decision.replace("AUTO_", "").toLowerCase()} · ${d.msisdn_masked}` })));
  if (keep) sel.value = keep;
}
function auditBox(a) {
  const ok = a.integrity_ok;
  const box = h("div", { class: "result-box " + (ok ? "ok" : "bad") },
    h("b", { text: ok ? "Integrity verified" : `${a.tampered} integrity violation${a.tampered > 1 ? "s" : ""} detected` }),
    h("div", { text: `${a.verified} of ${a.on_chain_entries} on-chain entries match their off-chain record (${a.audit_seconds}s).` }));
  if (!ok) box.append(h("ul", {}, a.findings.map((f) => h("li", { text: `Entry #${f.entry_id}: ${f.reason}` }))));
  return box;
}
$("btnVerify").addEventListener("click", async () => {
  $("auditResult").replaceChildren(auditBox(await api("/audit/verify")));
});
document.querySelectorAll("[data-tamper]").forEach((b) => b.addEventListener("click", async () => {
  const rid = $("tamperTarget").value;
  if (!rid) return toast("Evaluate a request first.", true);
  const t = await api("/demo/tamper", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ request_id: rid, mode: b.dataset.tamper }) });
  const a = await api("/audit/verify");
  $("tamperResult").replaceChildren(h("p", { class: "muted", text: `Insider action: ${t.change}.` }), auditBox(a));
}));
$("btnRestore").addEventListener("click", async () => {
  await api("/demo/restore", { method: "POST" });
  const a = await api("/audit/verify");
  $("tamperResult").replaceChildren(h("p", { class: "muted", text: "Records restored." }), auditBox(a));
  loadTargets();
});
document.querySelectorAll("[data-edge]").forEach((b) => b.addEventListener("click", async () => {
  const r = await api("/demo/edge-attack/" + b.dataset.edge, { method: "POST" });
  const tb = document.querySelector("#edgeTable tbody");
  tb.prepend(h("tr", {}, h("td", { text: r.what }), h("td", { class: "mono", text: r.reason }),
    h("td", {}, h("span", { class: "tag " + (r.accepted ? "bad" : "ok"), text: r.accepted ? "ACCEPTED" : "REJECTED" }))));
}));

// ───────────────────────── model ─────────────────────────
async function loadModel() {
  const m = await api("/metrics");
  const tb = document.querySelector("#modelTable tbody");
  tb.replaceChildren();
  for (const [name, v] of Object.entries(m.comparison.models)) {
    tb.append(h("tr", { style: name.includes("proposed") ? "font-weight:600" : null },
      h("td", { text: name }), h("td", { class: "num", text: fmt(v.precision, 3) }), h("td", { class: "num", text: fmt(v.recall, 3) }),
      h("td", { class: "num", text: fmt(v.f1, 3) }), h("td", { class: "num", text: fmt(v.roc_auc, 3) }), h("td", { class: "num", text: fmt(v.pr_auc, 3) })));
  }
  const sp = m.comparison.split;
  $("modelNote").textContent = `Test set: ${sp.test} requests (${sp.test_fraud} fraudulent). Decision thresholds were fixed on the validation split. 5-fold CV ROC-AUC ${fmt(m.comparison.xgboost_cv.roc_auc_mean, 3)} ± ${fmt(m.comparison.xgboost_cv.roc_auc_std, 3)}.`;
  const p = m.meta.policy;
  kv($("policyKv"), [
    ["Model", m.meta.model_version], ["Trees", m.meta.n_trees],
    ["Review threshold", `risk ≥ ${p.t_review}`], ["Block threshold", `risk ≥ ${p.t_block}`],
    ["Review capacity", pct(p.review_capacity)], ["Cost of a missed fraud", p.cost_weights.missed_fraud],
    ["Cost of a false block", p.cost_weights.false_block], ["Cost of one review", p.cost_weights.review],
  ]);
}

// ───────────────────────── boot ─────────────────────────
(async function boot() {
  await loadHealth();
  await loadScenarios();
  const q = new URLSearchParams(location.search);
  if (q.get("tab")) showTab(q.get("tab"));
  if (q.get("scenario")) await runScenario(q.get("scenario"));
})();
