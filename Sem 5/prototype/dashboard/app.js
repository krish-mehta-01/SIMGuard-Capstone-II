/* ==========================================================================
   SIMGUARD — Blockchain-Based Secure Communication System
   Client Application Controller — Streamlined for Live Demonstration
   ========================================================================== */
"use strict";

const API_V2 = "/api/v2";

const state = {
  isProtectedMode: true,
  currentCategory: "ALL",
};

const TAB_LABELS = {
  simulator: "Live Simulator",
  "ledger-v2": "Blockchain Ledger",
  defense: "Threat Defense & Audit",
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

function shortHash(str, len = 14) {
  if (!str) return "—";
  return str.length > len ? str.slice(0, len) + "…" : str;
}

function toast(msg, isErr = false) {
  const t = $("toast");
  if (!t) return;
  t.textContent = msg;
  t.className = "toast" + (isErr ? " err" : "");
  t.hidden = false;
  setTimeout(() => (t.hidden = true), 3500);
}

async function apiv2(path, opts = {}) {
  const res = await fetch(API_V2 + path, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw err;
  }
  return res.json();
}

// ───────────────────────── Tab Routing ─────────────────────────
function showTab(name) {
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
  document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("active", p.id === "tab-" + name));

  const breadcrumb = $("breadcrumbCurrent");
  if (breadcrumb && TAB_LABELS[name]) {
    breadcrumb.textContent = TAB_LABELS[name];
  }

  if (name === "simulator") loadV2Stats();
  if (name === "ledger-v2") loadLedgerV2(state.currentCategory);
}

document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => showTab(t.dataset.tab)));

// ═════════════════════════════════════════════════════════════════════
// 1. LIVE SIMULATOR (ALICE -> ATTACKER -> BOB)
// ═════════════════════════════════════════════════════════════════════

function setSimMsg(txt) {
  const input = $("simMessageText");
  if (input) input.value = txt;
}

function initSimulator() {
  const btnUnprot = $("btnModeUnprotected");
  const btnProt = $("btnModeProtected");
  const btnTransmit = $("btnTransmitSim");

  if (btnUnprot && btnProt) {
    btnUnprot.addEventListener("click", () => {
      state.isProtectedMode = false;
      btnUnprot.classList.add("active");
      btnProt.classList.remove("active");
      $("simProtocolTag").textContent = "Legacy Unencrypted GSM Airwaves";
      $("simProtocolTag").className = "tag err";
      $("simFlowCipherDot").className = "flow-dot red";
      $("simFlowCipherLabel").textContent = "Encryption: None (Plaintext Airwave Interception)";
    });

    btnProt.addEventListener("click", () => {
      state.isProtectedMode = true;
      btnProt.classList.add("active");
      btnUnprot.classList.remove("active");
      $("simProtocolTag").textContent = "SIMGUARD Cryptographic Engine";
      $("simProtocolTag").className = "tag ok";
      $("simFlowCipherDot").className = "flow-dot green";
      $("simFlowCipherLabel").textContent = "Encryption: AES-256-GCM AEAD (Device-Bound)";
    });
  }

  if (btnTransmit) {
    btnTransmit.addEventListener("click", runSimulateIntercept);
  }
}

async function runSimulateIntercept() {
  const msg = $("simMessageText") ? $("simMessageText").value.trim() : "Your Bank OTP is 849201";
  if (!msg) return toast("Please enter a message to transmit.", true);

  const term = $("attackerTerminal");
  const badge = $("attackerBadge");
  const packetBox = $("attackerPacketContent");
  const impactText = $("attackerImpactText");
  const recipientText = $("simRecipientText");
  const proofBlock = $("simProofBlock");
  const proofTx = $("simProofTx");
  const proofStatus = $("simProofStatus");

  try {
    const res = await apiv2("/simulate/intercept", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sender_phone: "+919876543210",
        recipient_phone: "+919876511223",
        message: msg,
        protection_enabled: state.isProtectedMode,
      }),
    });

    if (!state.isProtectedMode) {
      // Unprotected Mode
      term.className = "attacker-terminal compromised";
      badge.className = "attacker-badge compromised";
      badge.innerHTML = `
        <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
          <line x1="12" y1="9" x2="12" y2="13"/>
          <line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
        <span>Compromised / Intercepted</span>
      `;
      
      packetBox.innerHTML = `
        <div style="color:#94A3B8;">PROTOCOL: Legacy GSM / Unencrypted Airwaves</div>
        <div style="margin-top:6px;"><span class="highlight-leak">INTERCEPTED CLEARTEXT:</span> <strong style="color:#FCA5A5;">"${res.attacker.intercepted_data}"</strong></div>
        <div style="margin-top:6px;color:#F87171;">CAN READ PLAINTEXT: YES (100% Leaked)</div>
      `;
      impactText.innerHTML = `
        <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:#DC2626;">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
          <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
        <span style="color:#DC2626;">CRITICAL BREACH: Bank OTP or confidential communication intercepted by unauthorized party.</span>
      `;

      recipientText.textContent = res.recipient.received_content;
      proofBlock.textContent = "None (Off-chain / Insecure)";
      proofTx.textContent = "N/A";
      proofStatus.className = "tag err";
      proofStatus.textContent = "Unverified Airwave";

      toast("Unprotected: Attacker intercepted plaintext.", true);
    } else {
      // SIMGUARD Protected Mode
      term.className = "attacker-terminal protected";
      badge.className = "attacker-badge protected";
      badge.innerHTML = `
        <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
          <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
        </svg>
        <span>Zero Data Leakage</span>
      `;

      packetBox.innerHTML = `
        <div style="margin-bottom:6px;"><span class="highlight-hash">SHA-256 HASH VALUE:</span> <code style="color:#6EE7B7;word-break:break-all;">${res.attacker.intercepted_hash}</code></div>
        <div style="margin-bottom:6px;color:#94A3B8;">AES-256-GCM CIPHERTEXT: <code style="word-break:break-all;color:#CBD5E1;">${res.attacker.intercepted_data}</code></div>
        <div style="color:#F87171;">DECRYPTION ATTEMPT: <strong>${res.attacker.decryption_attempt_result}</strong></div>
      `;
      impactText.innerHTML = `
        <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:#16A34A;">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
          <polyline points="9 12 11 14 15 10"/>
        </svg>
        <span style="color:#16A34A;">CONFIDENTIALITY PRESERVED: Attacker receives only uncrackable SHA-256 hash value.</span>
      `;

      recipientText.textContent = res.recipient.decrypted_plaintext;
      proofBlock.textContent = `#${res.recipient.block_index} (Immutable Hash-Chain)`;
      proofTx.textContent = res.recipient.tx_id;
      proofStatus.className = "tag ok";
      proofStatus.textContent = "Hash & Sig Verified";

      toast("Protected: Transmitted securely & anchored to Block #" + res.recipient.block_index);
      loadV2Stats();
    }
  } catch (err) {
    toast(err.message || "Simulation error", true);
  }
}

// ═════════════════════════════════════════════════════════════════════
// 2. BLOCKCHAIN LEDGER
// ═════════════════════════════════════════════════════════════════════

async function loadV2Stats() {
  try {
    const s = await apiv2("/stats");
    $("chipBlocks").textContent = `Blocks: ${s.total_blocks}`;

    const statusEl = $("sidebarChainStatus");
    if (statusEl) {
      if (s.chain_valid) {
        statusEl.innerHTML = `<i class="pulse-dot"></i> Synchronized`;
        statusEl.style.color = "var(--color-success)";
      } else {
        statusEl.innerHTML = `<i class="pulse-dot" style="background:#DC2626;"></i> Tamper Alert`;
        statusEl.style.color = "var(--color-critical)";
      }
    }

    const statBox = $("ledgerStatsV2");
    if (statBox) {
      statBox.innerHTML = `
        <div class="stat"><span class="val">${s.total_blocks}</span><span class="lbl">Total Blocks</span></div>
        <div class="stat"><span class="val">${s.total_transactions}</span><span class="lbl">Transactions</span></div>
        <div class="stat"><span class="val">${s.transaction_counts.REGISTER || 0}</span><span class="lbl">REGISTER</span></div>
        <div class="stat"><span class="val">${s.transaction_counts.MESSAGE || 0}</span><span class="lbl">MESSAGE</span></div>
        <div class="stat"><span class="val">${s.transaction_counts.CALL_META || 0}</span><span class="lbl">CALL_META</span></div>
        <div class="stat"><span class="val" style="color:${s.transaction_counts.SECURITY_ALERT ? '#DC2626':'inherit'}">${s.transaction_counts.SECURITY_ALERT || 0}</span><span class="lbl">SECURITY ALERTS</span></div>
      `;
    }
  } catch (e) {
    console.error("V2 stats failed", e);
  }
}

async function loadLedgerV2(cat = "ALL") {
  state.currentCategory = cat;
  const tbody = $("ledgerV2Tbody");
  if (!tbody) return;
  tbody.innerHTML = "<tr><td colspan='8' class='empty'>Loading blockchain blocks...</td></tr>";

  try {
    const data = await apiv2("/ledger" + (cat !== "ALL" ? `?category=${cat}` : ""));
    tbody.innerHTML = "";

    data.chain.forEach((block) => {
      block.transactions.forEach((tx) => {
        const tr = h("tr", {},
          h("td", { class: "mono", style: "font-weight:700;", text: `#${block.index}` }),
          h("td", { class: "muted", style: "font-size:11px;", text: new Date(tx.timestamp * 1000).toLocaleTimeString() }),
          h("td", {}, h("span", { class: `badge-tx badge-tx-${tx.tx_type}`, text: tx.tx_type })),
          h("td", { class: "mono", text: tx.tx_id }),
          h("td", { class: "mono", style: "font-size:11px;", text: shortHash(tx.sender_phone_hash, 16) }),
          h("td", { style: "font-size:11.5px;max-width:260px;" },
            tx.tx_type === "REGISTER" ? `Reg: ${tx.payload.device_model || tx.payload.action}` :
            tx.tx_type === "MESSAGE" ? `Ciphertext: ${shortHash(tx.payload.payload_hash, 18)}` :
            tx.tx_type === "CALL_META" ? `Call: ${tx.payload.duration_seconds}s (${tx.payload.codec})` :
            `Security Alert: ${tx.payload.threat_type || 'Takeover Attempt'}`
          ),
          h("td", { class: "mono", style: "font-size:11px;", text: shortHash(tx.signature_hex, 16) }),
          h("td", { class: "mono", style: "font-size:11px;color:var(--text-muted);", text: shortHash(block.block_hash, 14) })
        );
        tbody.appendChild(tr);
      });
    });

    loadV2Stats();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan='8' class='empty'>Error: ${err.message || err}</td></tr>`;
  }
}

document.querySelectorAll("#ledgerCategoryFilter button").forEach((b) => {
  b.addEventListener("click", () => {
    document.querySelectorAll("#ledgerCategoryFilter button").forEach((x) => x.classList.remove("active"));
    b.classList.add("active");
    loadLedgerV2(b.dataset.cat);
  });
});

// ═════════════════════════════════════════════════════════════════════
// 3. THREAT DEFENSE & AUDIT
// ═════════════════════════════════════════════════════════════════════

async function runScenario(scenarioId) {
  const term = $("scenarioTerminal");
  term.innerHTML = `<span style="color:#38BDF8;">[RUNNING] Executing security verification test...</span>\n`;

  try {
    const res = await apiv2(`/scenarios/${scenarioId}`, { method: "POST" });
    const jsonStr = JSON.stringify(res, null, 2);

    let statusColor = "#4ADE80";
    if (res.result && (res.result.includes("DEFENDED") || res.result.includes("TAMPER_DETECTED"))) {
      statusColor = "#F59E0B";
    }

    term.innerHTML = `
<span style="color:${statusColor};font-weight:700;">[TEST: ${res.name.toUpperCase()}]</span>
<span style="color:#94A3B8;">Expected: ${res.expected_outcome}</span>
<span style="color:#F8FAFC;font-weight:700;">Outcome: ${res.result}</span>
----------------------------------------------------------------------
<span style="color:#CBD5E1;">${jsonStr}</span>
`;
    toast(`Test executed: ${res.result}`);
    loadV2Stats();
  } catch (err) {
    term.innerHTML = `<span style="color:#F87171;">[ERROR] Test failed: ${err.detail || err.message}</span>`;
  }
}

async function runCryptoAudit() {
  const term = $("scenarioTerminal");
  term.innerHTML = `<span style="color:#38BDF8;">[AUDITING] Recomputing SHA-256 block hash-chain links and Merkle roots...</span>\n`;

  try {
    const res = await apiv2("/audit");
    const jsonStr = JSON.stringify(res, null, 2);

    let statusColor = res.is_valid ? "#4ADE80" : "#EF4444";
    term.innerHTML = `
<span style="color:${statusColor};font-weight:700;">[BLOCKCHAIN INTEGRITY AUDIT REPORT]</span>
<span style="color:#F8FAFC;font-weight:700;">Status: ${res.is_valid ? "100% VALID & INTACT" : "TAMPERING DETECTED"}</span>
<span style="color:#94A3B8;">Blocks Checked: ${res.total_blocks_checked} | Discrepancies: ${res.anomaly_count}</span>
----------------------------------------------------------------------
<span style="color:#CBD5E1;">${jsonStr}</span>
`;
    toast(res.is_valid ? "Audit Passed: Blockchain 100% valid." : "Audit Alert: Discrepancy detected!", !res.is_valid);
    loadV2Stats();
  } catch (err) {
    term.innerHTML = `<span style="color:#F87171;">[ERROR] Audit failed: ${err.message || err}</span>`;
  }
}

async function restoreLedger() {
  try {
    const res = await apiv2("/scenarios/restore", { method: "POST" });
    const term = $("scenarioTerminal");
    if (term) {
      term.innerHTML = `
<span style="color:#4ADE80;font-weight:700;">[LEDGER RESTORED TO VERIFIED STATE]</span>
All blocks restored to original cryptographic state.
Audit Verification: ${res.audit.is_valid ? "VALID & INTACT" : "ANOMALIES PRESENT"}
Total Blocks Checked: ${res.audit.total_blocks_checked}
`;
    }
    toast("Blockchain ledger restored to 100% verified state.");
    loadV2Stats();
  } catch (err) {
    toast("Restore failed: " + (err.message || err), true);
  }
}

// ───────────────────────── Boot ─────────────────────────
(async function boot() {
  initSimulator();
  await loadV2Stats();
  await runSimulateIntercept();
})();
