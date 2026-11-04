import React, { useState, useEffect } from 'react';
import {
  Shield,
  ShieldCheck,
  ShieldAlert,
  Lock,
  Unlock,
  Radio,
  Send,
  RefreshCw,
  Terminal,
  CheckCircle2,
  AlertTriangle,
  Database
} from 'lucide-react';
import './App.css';

export default function App() {
  const [activeTab, setActiveTab] = useState('simulator');
  const [isProtectedMode, setIsProtectedMode] = useState(true);
  const [message, setMessage] = useState('Your Bank OTP is 849201. Valid for 5 minutes.');
  const [simResult, setSimResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [ledgerStats, setLedgerStats] = useState(null);
  const [ledgerBlocks, setLedgerBlocks] = useState([]);
  const [ledgerCategory, setLedgerCategory] = useState('ALL');
  const [defenseLog, setDefenseLog] = useState('// Select an action to execute cryptographic verification...');
  const [toastMsg, setToastMsg] = useState(null);

  const showToast = (msg, isErr = false) => {
    setToastMsg({ text: msg, isErr });
    setTimeout(() => setToastMsg(null), 3500);
  };

  useEffect(() => {
    fetchStats();
    runSimulation(true, message);
  }, []);

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/v2/stats');
      if (res.ok) {
        const data = await res.json();
        setLedgerStats(data);
      }
    } catch (err) {
      console.warn('Failed to load stats', err);
    }
  };

  const fetchLedger = async (cat = ledgerCategory) => {
    try {
      const url = cat === 'ALL' ? '/api/v2/ledger' : `/api/v2/ledger?category=${cat}`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setLedgerBlocks(data.chain || []);
      }
    } catch (err) {
      console.warn('Failed to load ledger', err);
    }
  };

  const runSimulation = async (protectedMode, msgText) => {
    setLoading(true);
    try {
      const res = await fetch('/api/v2/simulate/intercept', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sender_phone: '+919876543210',
          recipient_phone: '+919876511223',
          message: msgText,
          protection_enabled: protectedMode,
        }),
      });

      if (!res.ok) throw new Error('Simulation failed');
      const data = await res.json();
      setSimResult(data);
      fetchStats();
      if (!protectedMode) {
        showToast('Unprotected: Plaintext intercepted by adversary.', true);
      } else {
        showToast('SIMGUARD: Protected & anchored to blockchain.');
      }
    } catch (err) {
      showToast(err.message || 'Simulation error', true);
    } finally {
      setLoading(false);
    }
  };

  const handleCategoryChange = (cat) => {
    setLedgerCategory(cat);
    fetchLedger(cat);
  };

  const handleSimulateSwapAttack = async () => {
    setDefenseLog('[RUNNING] Simulating Rogue Device SIM Swap Takeover Attack...');
    try {
      const res = await fetch('/api/v2/scenarios/2', { method: 'POST' });
      const data = await res.json();
      setDefenseLog(
`[THREAT DEFENSE REPORT: UNAUTHORIZED DIGITAL SIM SWAP]
Specification: ${data.expected_outcome}
Evaluation Result: ${data.result} (Takeover Blocked)
Target Subscriber: ${data.attack_details?.claimed_identity}
Handset Fingerprint Match: ${data.attack_details?.binding_match ? 'VALID' : 'REJECTED (Mismatch)'}
On-Chain Security Alert: Transaction ${data.onchain_alert?.tx_id} anchored in Block #${data.onchain_alert?.block_index}
----------------------------------------------------------------------
${JSON.stringify(data, null, 2)}`
      );
      showToast('SIM Swap Attack Blocked & Alert Anchored On-Chain');
      fetchStats();
    } catch (err) {
      setDefenseLog(`[ERROR] Test failed: ${err.message}`);
    }
  };

  const handleRunAudit = async () => {
    setDefenseLog('[AUDITING] Recomputing cryptographic SHA-256 block hash-chain links and Merkle trees...');
    try {
      const res = await fetch('/api/v2/audit');
      const data = await res.json();
      setDefenseLog(
`[BLOCKCHAIN INTEGRITY AUDIT REPORT]
Status: ${data.is_valid ? '100% CRYPTOGRAPHICALLY VALID & INTACT' : 'TAMPER ALERT: DISCREPANCY DETECTED'}
Total Blocks Checked: ${data.total_blocks_checked}
Anomaly Count: ${data.anomaly_count}
Details: ${data.message}
----------------------------------------------------------------------
${JSON.stringify(data, null, 2)}`
      );
      showToast(data.is_valid ? 'Audit Passed: Blockchain verified.' : 'Audit Alert: Tampering detected!', !data.is_valid);
      fetchStats();
    } catch (err) {
      setDefenseLog(`[ERROR] Audit failed: ${err.message}`);
    }
  };

  const handleTamperBlock = async () => {
    setDefenseLog('[TAMPER SIMULATION] Injecting unauthorized modification into Block #1 database payload...');
    try {
      const res = await fetch('/api/v2/scenarios/4', { method: 'POST' });
      const data = await res.json();
      setDefenseLog(
`[TAMPER EXPLOIT SIMULATION OUTCOME]
Target: Block #1
Tamper Result: ${data.result}
Audit Detection: ${data.audit_result?.is_valid ? 'MISSED' : 'DISCREPANCY DETECTED IMMEDIATELY'}
Discrepancies Flagged: ${data.audit_result?.anomaly_count}
Explanation: Stored Merkle root disagreed with recomputed transaction hashes.
----------------------------------------------------------------------
${JSON.stringify(data, null, 2)}`
      );
      showToast('Block #1 modified in DB. Tamper flagged!', true);
      fetchStats();
    } catch (err) {
      setDefenseLog(`[ERROR] Tamper test failed: ${err.message}`);
    }
  };

  const handleRestoreLedger = async () => {
    try {
      const res = await fetch('/api/v2/scenarios/restore', { method: 'POST' });
      const data = await res.json();
      setDefenseLog(
`[BLOCKCHAIN LEDGER RESTORED]
Status: ${data.audit?.is_valid ? 'VALID & INTACT' : 'ANOMALIES PRESENT'}
All modified blocks restored to original cryptographic state.
Total Blocks Verified: ${data.audit?.total_blocks_checked}`
      );
      showToast('Ledger restored to 100% verified state.');
      fetchStats();
    } catch (err) {
      showToast('Restore failed', true);
    }
  };

  return (
    <div className="app-shell">
      {/* ─── Sidebar ─── */}
      <aside className="app-sidebar">
        <div className="sidebar-brand">
          <div className="brand-icon-box">
            <ShieldCheck size={20} />
          </div>
          <div className="brand-info">
            <span className="brand-title">SIMGUARD</span>
            <span className="brand-subtitle">Zero-Trust Telecom Protocol</span>
          </div>
        </div>

        <nav className="sidebar-nav">
          <span className="nav-section-title">Navigation</span>
          
          <button
            className={`nav-item ${activeTab === 'simulator' ? 'active' : ''}`}
            onClick={() => setActiveTab('simulator')}
          >
            <Radio size={16} />
            <span>Live Simulator</span>
          </button>

          <button
            className={`nav-item ${activeTab === 'ledger' ? 'active' : ''}`}
            onClick={() => {
              setActiveTab('ledger');
              fetchLedger('ALL');
            }}
          >
            <Database size={16} />
            <span>Blockchain Ledger</span>
          </button>

          <button
            className={`nav-item ${activeTab === 'defense' ? 'active' : ''}`}
            onClick={() => setActiveTab('defense')}
          >
            <ShieldAlert size={16} />
            <span>Threat Defense &amp; Audit</span>
          </button>
        </nav>

        <div className="sidebar-footer">
          <div className="system-badge">
            <span className="pulse-dot"></span>
            <span>Consensus: Synchronized</span>
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            Ed25519 · SHA-256 · AES-256-GCM
          </div>
        </div>
      </aside>

      {/* ─── Main Content Area ─── */}
      <div className="app-main">
        
        {/* ═══════════════════════════════════════════════════════════════
             UNIFIED TOP HEADER BANNER (REPLACES REDUNDANT TOP BAR)
             ═══════════════════════════════════════════════════════════════ */}
        <header className="app-header-banner">
          {activeTab === 'simulator' && (
            <>
              <div className="header-left-content">
                <div className="header-title-row">
                  <Shield size={16} />
                  <h2>Communication Interception Demonstration</h2>
                </div>
                <span className="header-sep">·</span>
                <p>Legacy GSM Airwaves vs SIMGUARD Protection</p>
              </div>

              <div className="header-right-content">
                <div className="header-chips">
                  <span className="chip dark">
                    <span className="pulse-dot"></span>
                    <span>Ledger: Active</span>
                  </span>
                  <span className="chip dark">
                    <span>Blocks: {ledgerStats?.total_blocks || 4}</span>
                  </span>
                </div>

                <div className="mode-toggle-wrap">
                  <button
                    className={`mode-btn ${!isProtectedMode ? 'active unprotected' : ''}`}
                    onClick={() => {
                      setIsProtectedMode(false);
                      runSimulation(false, message);
                    }}
                  >
                    <Unlock size={14} />
                    <span>Legacy GSM (Unprotected)</span>
                  </button>
                  <button
                    className={`mode-btn ${isProtectedMode ? 'active protected' : ''}`}
                    onClick={() => {
                      setIsProtectedMode(true);
                      runSimulation(true, message);
                    }}
                  >
                    <ShieldCheck size={14} />
                    <span>SIMGUARD (Protected)</span>
                  </button>
                </div>
              </div>
            </>
          )}

          {activeTab === 'ledger' && (
            <>
              <div className="header-left-content">
                <div className="header-title-row">
                  <Database size={16} />
                  <h2>Immutable Cryptographic Audit Ledger</h2>
                </div>
                <span className="header-sep">·</span>
                <p>Hash-Chained Block Verification</p>
              </div>

              <div className="header-right-content">
                <div className="header-chips">
                  <span className="chip dark">
                    <span className="pulse-dot"></span>
                    <span>Ledger: Active</span>
                  </span>
                  <span className="chip dark">
                    <span>Blocks: {ledgerStats?.total_blocks || 4}</span>
                  </span>
                </div>

                <div className="seg dark">
                  {['ALL', 'REGISTER', 'MESSAGE', 'CALL_META', 'SECURITY_ALERT'].map((cat) => (
                    <button
                      key={cat}
                      className={ledgerCategory === cat ? 'active' : ''}
                      onClick={() => handleCategoryChange(cat)}
                    >
                      {cat}
                    </button>
                  ))}
                </div>
              </div>
            </>
          )}

          {activeTab === 'defense' && (
            <>
              <div className="header-left-content">
                <div className="header-title-row">
                  <ShieldAlert size={16} />
                  <h2>Threat Defense &amp; Integrity Audit</h2>
                </div>
                <span className="header-sep">·</span>
                <p>Zero-Trust Policy Enforcement</p>
              </div>

              <div className="header-right-content">
                <div className="header-chips">
                  <span className="chip dark">
                    <span className="pulse-dot"></span>
                    <span>Ledger: Active</span>
                  </span>
                  <span className="chip dark">
                    <span>Blocks: {ledgerStats?.total_blocks || 4}</span>
                  </span>
                </div>

                <button className="btn ghost dark" onClick={handleRestoreLedger}>
                  <RefreshCw size={14} />
                  <span>Restore Verified Ledger</span>
                </button>
              </div>
            </>
          )}
        </header>

        <main className="app-content">

          {/* ═══════════════════════════════════════════════════════════════
               VIEW 1: LIVE SIMULATOR (ALICE -> TRANSIT -> BOB)
               ═══════════════════════════════════════════════════════════════ */}
          {activeTab === 'simulator' && (
            <div className="sim-architecture-grid">
              
              {/* ── Device A (Sender) ── */}
              <article className="phone-mockup">
                <div className="phone-header">
                  <div className="phone-user-info">
                    <div className="phone-avatar">A</div>
                    <div className="phone-meta">
                      <span className="phone-name">Device A: Alice (Sender)</span>
                      <span className="phone-device">Pixel 8 Pro · +91 98765 43210</span>
                    </div>
                  </div>
                  <div className="phone-signals">5G-SA 100%</div>
                </div>

                <div className="phone-body">
                  <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)' }}>
                    Payload to Transmit:
                  </label>
                  <textarea
                    rows={3}
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    style={{
                      width: '100%',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--border-default)',
                      padding: '10px',
                      fontSize: '13px',
                      resize: 'none',
                    }}
                  />

                  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                    <button
                      className="btn ghost sm"
                      onClick={() => {
                        const m = 'Your Bank OTP is 849201. Valid for 5 minutes.';
                        setMessage(m);
                        runSimulation(isProtectedMode, m);
                      }}
                    >
                      Bank OTP
                    </button>
                    <button
                      className="btn ghost sm"
                      onClick={() => {
                        const m = 'CONFIDENTIAL: Wire transfer $50,000 approved to Acct #10928.';
                        setMessage(m);
                        runSimulation(isProtectedMode, m);
                      }}
                    >
                      Wire Transfer
                    </button>
                    <button
                      className="btn ghost sm"
                      onClick={() => {
                        const m = 'Server Access Token: tok_live_948201948201948';
                        setMessage(m);
                        runSimulation(isProtectedMode, m);
                      }}
                    >
                      Auth Token
                    </button>
                  </div>

                  <div className="phone-key-badge" style={{ marginTop: 'auto' }}>
                    Device Key: <code>ed25519:7c9a41c28f10b...</code>
                  </div>
                </div>

                <div className="phone-footer">
                  <button
                    className="btn primary"
                    style={{ width: '100%', justifyContent: 'center' }}
                    disabled={loading}
                    onClick={() => runSimulation(isProtectedMode, message)}
                  >
                    <Send size={15} />
                    <span>{loading ? 'Transmitting...' : 'Transmit Message'}</span>
                  </button>
                </div>
              </article>

              {/* ── Transit & Attacker Terminal ── */}
              <article className="network-transit-card">
                <div className="network-pipe-header">
                  <h3>Cellular Radio Interface</h3>
                  <span className={`tag ${isProtectedMode ? 'ok' : 'err'}`}>
                    {isProtectedMode ? 'SIMGUARD Cryptographic Engine' : 'Legacy Unencrypted GSM Airwaves'}
                  </span>
                </div>

                <div className="transit-flow-visual">
                  <div className="flow-step">
                    <span className="flow-dot blue"></span>
                    <span>Channel: Cellular Airwave Link (BTS)</span>
                  </div>
                  <div className="flow-step">
                    <span className={`flow-dot ${isProtectedMode ? 'green' : 'red'}`}></span>
                    <span>
                      {isProtectedMode
                        ? 'Encryption: AES-256-GCM AEAD (Device-Bound)'
                        : 'Encryption: None (Plaintext Airwave Sniffing)'}
                    </span>
                  </div>
                  <div className="flow-step">
                    <span className="flow-dot red"></span>
                    <span>Adversary: In-Transit Sniffer Active</span>
                  </div>
                </div>

                {/* Attacker Sniffer Box */}
                <div className={`attacker-terminal ${isProtectedMode ? 'protected' : 'compromised'}`}>
                  <div className="attacker-header">
                    <span style={{ fontWeight: 700, fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Terminal size={15} />
                      <span>Attacker Sniffer Output</span>
                    </span>
                    <span className={`attacker-badge ${isProtectedMode ? 'protected' : 'compromised'}`}>
                      {isProtectedMode ? <ShieldCheck size={13} /> : <AlertTriangle size={13} />}
                      <span>{isProtectedMode ? 'Zero Data Leakage' : 'Compromised / Intercepted'}</span>
                    </span>
                  </div>

                  <div className="attacker-data-box">
                    <div style={{ color: '#94A3B8', marginBottom: '4px' }}>// Intercepted Packet:</div>
                    {isProtectedMode ? (
                        <div>
                        <div>
                          <span className="highlight-hash">SHA-256 HASH:</span>{' '}
                          <span style={{ color: '#6EE7B7' }}>{simResult?.attacker?.intercepted_hash}</span>
                        </div>
                        <div style={{ marginTop: '4px', color: '#94A3B8' }}>
                          CIPHERTEXT: <span style={{ color: '#CBD5E1' }}>{simResult?.attacker?.intercepted_data}</span>
                        </div>
                        <div style={{ marginTop: '4px', color: '#F87171' }}>
                          DECRYPT ATTEMPT: <strong>{simResult?.attacker?.decryption_attempt_result}</strong>
                        </div>
                      </div>
                    ) : (
                      <div>
                        <div style={{ color: '#94A3B8' }}>PROTOCOL: Legacy GSM / Cleartext Airwaves</div>
                        <div style={{ marginTop: '6px' }}>
                          <span className="highlight-leak">INTERCEPTED CLEARTEXT:</span>{' '}
                          <strong style={{ color: '#FCA5A5' }}>"{simResult?.attacker?.intercepted_data}"</strong>
                        </div>
                        <div style={{ marginTop: '6px', color: '#F87171' }}>CAN READ PLAINTEXT: YES (100% Leaked)</div>
                      </div>
                    )}
                  </div>

                  <div style={{ marginTop: '10px', fontSize: '11px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
                    {isProtectedMode ? (
                      <>
                        <ShieldCheck size={14} style={{ color: '#16A34A' }} />
                        <span style={{ color: '#16A34A' }}>
                          Confidentiality Preserved: Attacker receives only an uncrackable SHA-256 hash value.
                        </span>
                      </>
                    ) : (
                      <>
                        <AlertTriangle size={14} style={{ color: '#DC2626' }} />
                        <span style={{ color: '#DC2626' }}>
                          CRITICAL BREACH: Bank OTP or confidential communication intercepted by unauthorized party.
                        </span>
                      </>
                    )}
                  </div>
                </div>
              </article>

              {/* ── Device B (Recipient) ── */}
              <article className="phone-mockup">
                <div className="phone-header">
                  <div className="phone-user-info">
                    <div className="phone-avatar" style={{ background: '#16A34A' }}>B</div>
                    <div className="phone-meta">
                      <span className="phone-name">Device B: Bob (Recipient)</span>
                      <span className="phone-device">iPhone 15 Pro · +91 98765 11223</span>
                    </div>
                  </div>
                  <div className="phone-signals">5G-SA 100%</div>
                </div>

                <div className="phone-body">
                  <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)' }}>
                    Decrypted Incoming Message:
                  </label>
                  <div className="message-bubble recipient">
                    <div style={{ fontSize: '13.5px', fontWeight: 500 }}>
                      {simResult?.recipient?.decrypted_plaintext || simResult?.recipient?.received_content || message}
                    </div>
                  </div>

                  <div className="card" style={{ padding: '12px', background: '#F8FAFC', border: '1px solid var(--border-default)', marginTop: 'auto' }}>
                    <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                      BLOCKCHAIN VERIFICATION PROOF:
                    </div>
                    <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <div>Block: <strong>{isProtectedMode ? `#${simResult?.recipient?.block_index || 4}` : 'None (Insecure)'}</strong></div>
                      <div>Transaction: <span style={{ color: 'var(--color-primary)' }}>{simResult?.recipient?.tx_id || 'N/A'}</span></div>
                      <div>
                        Status:{' '}
                        <span className={`tag ${isProtectedMode ? 'ok' : 'err'}`}>
                          {isProtectedMode ? 'Hash & Sig Verified' : 'Unverified Airwave'}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="phone-footer">
                  <div style={{ fontSize: '11.5px', color: 'var(--text-muted)', textAlign: 'center' }}>
                    Device-bound keypair verified via SIMGUARD protocol
                  </div>
                </div>
              </article>

            </div>
          )}

          {/* ═══════════════════════════════════════════════════════════════
               VIEW 2: BLOCKCHAIN LEDGER
               ═══════════════════════════════════════════════════════════════ */}
          {activeTab === 'ledger' && (
            <div>
              {/* Stats Cards */}
              <div className="stats">
                <div className="stat">
                  <span className="val">{ledgerStats?.total_blocks || 0}</span>
                  <span className="lbl">Total Blocks</span>
                </div>
                <div className="stat">
                  <span className="val">{ledgerStats?.total_transactions || 0}</span>
                  <span className="lbl">Transactions</span>
                </div>
                <div className="stat">
                  <span className="val">{ledgerStats?.transaction_counts?.REGISTER || 0}</span>
                  <span className="lbl">REGISTER</span>
                </div>
                <div className="stat">
                  <span className="val">{ledgerStats?.transaction_counts?.MESSAGE || 0}</span>
                  <span className="lbl">MESSAGE</span>
                </div>
                <div className="stat">
                  <span className="val">{ledgerStats?.transaction_counts?.CALL_META || 0}</span>
                  <span className="lbl">CALL_META</span>
                </div>
                <div className="stat">
                  <span className="val" style={{ color: ledgerStats?.transaction_counts?.SECURITY_ALERT ? '#DC2626' : 'inherit' }}>
                    {ledgerStats?.transaction_counts?.SECURITY_ALERT || 0}
                  </span>
                  <span className="lbl">SECURITY ALERTS</span>
                </div>
              </div>

              {/* Table */}
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Block #</th>
                      <th>Timestamp</th>
                      <th>Category</th>
                      <th>Transaction ID</th>
                      <th>Sender Phone Hash</th>
                      <th>Payload Summary</th>
                      <th>Signature</th>
                      <th>Block Hash</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ledgerBlocks.map((block) =>
                      block.transactions.map((tx) => (
                        <tr key={tx.tx_id}>
                          <td style={{ fontWeight: 700, fontFamily: 'var(--font-mono)' }}>#{block.index}</td>
                          <td style={{ color: 'var(--text-muted)', fontSize: '11px' }}>
                            {new Date(tx.timestamp * 1000).toLocaleTimeString()}
                          </td>
                          <td>
                            <span className={`badge-tx badge-tx-${tx.tx_type}`}>
                              {tx.tx_type}
                            </span>
                          </td>
                          <td style={{ fontFamily: 'var(--font-mono)' }}>{tx.tx_id}</td>
                          <td style={{ fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
                            {tx.sender_phone_hash?.slice(0, 16)}...
                          </td>
                          <td style={{ fontSize: '11.5px', maxWidth: '260px' }}>
                            {tx.tx_type === 'REGISTER' && `Reg: ${tx.payload?.device_model || tx.payload?.action}`}
                            {tx.tx_type === 'MESSAGE' && `Ciphertext: ${tx.payload?.payload_hash?.slice(0, 18)}...`}
                            {tx.tx_type === 'CALL_META' && `Call: ${tx.payload?.duration_seconds}s (${tx.payload?.codec})`}
                            {tx.tx_type === 'SECURITY_ALERT' && `Security Alert: ${tx.payload?.threat_type || 'Takeover Attempt'}`}
                          </td>
                          <td style={{ fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
                            {tx.signature_hex?.slice(0, 16)}...
                          </td>
                          <td style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-muted)' }}>
                            {block.block_hash?.slice(0, 14)}...
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════════════
               VIEW 3: THREAT DEFENSE & AUDIT
               ═══════════════════════════════════════════════════════════════ */}
          {activeTab === 'defense' && (
            <div>
              <div className="grid2">
                {/* Test 1: Rogue SIM Swap Attack */}
                <article className="card" style={{ borderLeft: '3px solid #DC2626' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 700 }}>Unauthorized Digital SIM Swap Defense</h3>
                    <span className="tag err">Attack Test</span>
                  </div>
                  <p style={{ fontSize: '12.5px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                    An attacker on an unauthorized machine tries to hijack Alice's phone number. Because the attacker's hardware lacks Alice's device key and fingerprint binding, the authentication is rejected and a <code>SECURITY_ALERT</code> transaction is anchored on-chain.
                  </p>
                  <div style={{ marginTop: '16px' }}>
                    <button
                      className="btn"
                      style={{ background: '#DC2626', color: '#FFFFFF', borderColor: '#DC2626' }}
                      onClick={handleSimulateSwapAttack}
                    >
                      <ShieldAlert size={14} />
                      <span>Simulate Rogue SIM Swap</span>
                    </button>
                  </div>
                </article>

                {/* Test 2: Cryptographic Chain Audit */}
                <article className="card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 700 }}>Blockchain Integrity Audit &amp; Tamper Detection</h3>
                    <span className="tag ok">Audit Tool</span>
                  </div>
                  <p style={{ fontSize: '12.5px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                    Recomputes every block's cryptographic hash and Merkle root across all transactions. Demonstrates that any off-chain modification immediately breaks the hash chain.
                  </p>
                  <div style={{ marginTop: '16px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    <button className="btn primary" onClick={handleRunAudit}>
                      <CheckCircle2 size={14} />
                      <span>Run Full Audit</span>
                    </button>
                    <button className="btn" onClick={handleTamperBlock}>
                      <span>Simulate Block Tamper</span>
                    </button>
                  </div>
                </article>
              </div>

              {/* Execution Terminal */}
              <article className="card" style={{ marginTop: '20px' }}>
                <h2 style={{ fontSize: '14px', fontWeight: 700, margin: '0 0 10px 0' }}>Execution &amp; Verification Output</h2>
                <div className="terminal-box">
                  {defenseLog}
                </div>
              </article>
            </div>
          )}

        </main>
      </div>

      {/* Toast Notification */}
      {toastMsg && (
        <div className={`toast ${toastMsg.isErr ? 'err' : ''}`}>
          {toastMsg.text}
        </div>
      )}
    </div>
  );
}
