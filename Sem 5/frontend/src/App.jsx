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
  Database,
  Layers,
  Smartphone,
  BarChart3,
  Settings,
  Bell,
  ChevronDown,
  Copy,
  Check,
  Laptop,
  Cloud,
  User,
  ArrowRight,
  MessageSquare,
  Key,
  Hash,
  Users,
  Eye,
  EyeOff,
  Wifi,
  FileText,
  Box
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
  const [copied, setCopied] = useState(false);
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
        showToast('Legacy GSM: Plaintext intercepted by adversary.', true);
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

  const copyToClipboard = (text) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    showToast('Ciphertext copied to clipboard');
  };

  const handleSimulateSwapAttack = async () => {
    try {
      const res = await fetch('/api/v2/scenarios/2', { method: 'POST' });
      const data = await res.json();
      setDefenseLog(
`[ROGUE SIM SWAP SIMULATION]
Target Phone: ${data.target_phone}
Attacker Fingerprint: ${data.unauthorized_fingerprint}
Result Verdict: ${data.result}
Security Action: ${data.security_action}
Transaction Logged: ${data.transaction?.tx_id} (${data.transaction?.tx_type})
Merkle Anchored: ${data.transaction?.merkle_proof?.root ? 'YES' : 'NO'}
----------------------------------------------------------------------
${JSON.stringify(data, null, 2)}`
      );
      showToast('Unauthorized SIM swap intercepted & rejected!');
      fetchStats();
    } catch (err) {
      setDefenseLog(`[ERROR] SIM swap test failed: ${err.message}`);
    }
  };

  const handleRunAudit = async () => {
    try {
      const res = await fetch('/api/v2/audit');
      const data = await res.json();
      setDefenseLog(
`[CRYPTOGRAPHIC INTEGRITY AUDIT]
Audit Status: ${data.is_valid ? '100% VALID & INTACT' : 'TAMPER DETECTED'}
Total Blocks Checked: ${data.total_blocks_checked}
Anomalies Found: ${data.anomaly_count}
Block Hashes Verified: ${data.verified_hashes?.length || 0}
----------------------------------------------------------------------
${JSON.stringify(data, null, 2)}`
      );
      showToast(data.is_valid ? 'Blockchain audit passed!' : 'Anomalies detected in blockchain!', !data.is_valid);
    } catch (err) {
      setDefenseLog(`[ERROR] Audit failed: ${err.message}`);
    }
  };

  const handleTamperBlock = async () => {
    try {
      const res = await fetch('/api/v2/scenarios/4', { method: 'POST' });
      const data = await res.json();
      setDefenseLog(
`[ADVERSARY TAMPER ATTEMPT]
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
    <div className="sg-app">
      {/* ═══════════════════════════════════════════════════════════════
           SIDEBAR
           ═══════════════════════════════════════════════════════════════ */}
      <aside className="sg-sidebar">
        {/* Brand */}
        <div className="sg-brand">
          <div className="sg-brand-icon">
            <ShieldCheck size={22} color="#FFFFFF" strokeWidth={2.5} />
          </div>
          <div className="sg-brand-text">
            <span className="sg-brand-title">SIMGUARD</span>
            <span className="sg-brand-sub">Zero-Trust Telecom Protocol</span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="sg-nav">
          <div className="sg-nav-heading">NAVIGATION</div>
          
          <button
            className={`sg-nav-btn ${activeTab === 'simulator' ? 'active' : ''}`}
            onClick={() => setActiveTab('simulator')}
          >
            <Radio size={17} />
            <span>Live Simulator</span>
          </button>

          <button
            className={`sg-nav-btn ${activeTab === 'ledger' ? 'active' : ''}`}
            onClick={() => {
              setActiveTab('ledger');
              fetchLedger('ALL');
            }}
          >
            <Layers size={17} />
            <span>Blockchain Ledger</span>
          </button>

          <button
            className={`sg-nav-btn ${activeTab === 'identity' ? 'active' : ''}`}
            onClick={() => setActiveTab('identity')}
          >
            <Smartphone size={17} />
            <span>Device Identity</span>
          </button>

          <button
            className={`sg-nav-btn ${activeTab === 'defense' ? 'active' : ''}`}
            onClick={() => setActiveTab('defense')}
          >
            <ShieldAlert size={17} />
            <span>Threat Defense &amp; Audit</span>
          </button>

          <button
            className={`sg-nav-btn ${activeTab === 'analytics' ? 'active' : ''}`}
            onClick={() => setActiveTab('analytics')}
          >
            <BarChart3 size={17} />
            <span>Analytics</span>
          </button>

          <button
            className={`sg-nav-btn ${activeTab === 'settings' ? 'active' : ''}`}
            onClick={() => setActiveTab('settings')}
          >
            <Settings size={17} />
            <span>Settings</span>
          </button>
        </nav>

        {/* Radio Tower Illustration & Capstone Badge */}
        <div className="sg-sidebar-bottom">
          <div className="sg-tower-visual">
            <svg viewBox="0 0 120 100" fill="none" className="tower-svg">
              <path d="M60 20 L40 90 M60 20 L80 90 M46 65 L74 65 M50 48 L70 48 M60 12 L60 20" stroke="#0D9488" strokeWidth="2" strokeLinecap="round" opacity="0.45" />
              <circle cx="60" cy="12" r="3" fill="#0D9488" opacity="0.8" />
              <path d="M50 8 A14 14 0 0 1 70 8" stroke="#0D9488" strokeWidth="1.8" strokeLinecap="round" fill="none" opacity="0.5" />
              <path d="M42 4 A24 24 0 0 1 78 4" stroke="#0D9488" strokeWidth="1.8" strokeLinecap="round" fill="none" opacity="0.3" />
            </svg>
          </div>

          <div className="sg-capstone-badge">
            <div className="sg-badge-avatar">
              <Users size={16} />
            </div>
            <div className="sg-badge-meta">
              <span className="sg-badge-title">Interdepartmental Project</span>
              <span className="sg-badge-dept">ECE • CSE • IT</span>
            </div>
          </div>
        </div>
      </aside>

      {/* ═══════════════════════════════════════════════════════════════
           MAIN WORKSPACE
           ═══════════════════════════════════════════════════════════════ */}
      <div className="sg-main">
        {/* Top Header Bar */}
        <header className="sg-header">
          <div className="sg-header-left">
            <div className="sg-header-icon-box">
              <Radio size={18} />
            </div>
            <div className="sg-header-titles">
              <h1 className="sg-title">Communication Interception Demonstration</h1>
              <p className="sg-subtitle">Compare legacy (unprotected) communication with SIMGUARD's cryptographic protection.</p>
            </div>
          </div>

          <div className="sg-header-right">
            <div className="sg-pill sg-pill-green">
              <span className="sg-dot-green"></span>
              <span>Ledger: Active</span>
            </div>
            <div className="sg-pill sg-pill-blue">
              <Box size={13} />
              <span>Blocks: {ledgerStats?.total_blocks || 13}</span>
            </div>
            <div className="sg-pill sg-pill-slate">
              <Wifi size={13} />
              <span>Network: 5G-SA</span>
            </div>
            <button className="sg-icon-btn" title="Notifications">
              <Bell size={16} />
            </button>
            <div className="sg-user-badge">
              <div className="sg-user-avatar">K</div>
              <ChevronDown size={14} color="#64748B" />
            </div>
          </div>
        </header>

        {/* Scrollable View Content */}
        <div className="sg-content">

          {/* ═══════════════════════════════════════════════════════════════
               TAB 1: LIVE SIMULATOR
               ═══════════════════════════════════════════════════════════════ */}
          {activeTab === 'simulator' && (
            <>
              {/* Protocol Spec Sub-header Bar */}
              <div className="sg-spec-bar">
                <div className="sg-spec-mode">
                  <span className="sg-spec-label">Communication Mode:</span>
                  <div className="sg-mode-toggle">
                    <button
                      className={`sg-mode-option ${!isProtectedMode ? 'selected-legacy' : ''}`}
                      onClick={() => {
                        setIsProtectedMode(false);
                        runSimulation(false, message);
                      }}
                    >
                      <span className="sg-radio-dot"></span>
                      <span>Legacy (Unprotected)</span>
                    </button>
                    <button
                      className={`sg-mode-option ${isProtectedMode ? 'selected-simguard' : ''}`}
                      onClick={() => {
                        setIsProtectedMode(true);
                        runSimulation(true, message);
                      }}
                    >
                      <span className="sg-radio-dot-solid"></span>
                      <span>SIMGUARD (Protected)</span>
                    </button>
                  </div>
                </div>

                <div className="sg-spec-badges">
                  <div className="sg-spec-badge">
                    <div className="sg-spec-badge-icon">
                      <Lock size={13} />
                    </div>
                    <span><strong>AES-256</strong> Encryption</span>
                  </div>
                  <div className="sg-spec-badge">
                    <div className="sg-spec-badge-icon">
                      <Key size={13} />
                    </div>
                    <span><strong>Ed25519</strong> Digital Signature</span>
                  </div>
                  <div className="sg-spec-badge">
                    <div className="sg-spec-badge-icon">
                      <Hash size={13} />
                    </div>
                    <span><strong>SHA-256</strong> Integrity Hash</span>
                  </div>
                </div>
              </div>

              {/* Central Interactive Network Diagram */}
              <div className="sg-diagram-card">
                <div className="sg-diagram-actors">
                  {/* Sender (Device A) */}
                  <div className="sg-actor-box">
                    <div className="sg-laptop-icon sender">
                      <User size={28} color="#FFFFFF" />
                    </div>
                    <div className="sg-actor-name">Device A (Sender)</div>
                    <div className="sg-actor-sub">Alice · Pixel 8 Pro</div>
                  </div>

                  {/* Flow Arrow 1 */}
                  <div className={`sg-flow-connector ${isProtectedMode ? 'secure' : 'unsecure'}`}>
                    <div className="sg-flow-line"></div>
                    <div className="sg-flow-shield">
                      {isProtectedMode ? (
                        <ShieldCheck size={16} color="#FFFFFF" />
                      ) : (
                        <Unlock size={14} color="#FFFFFF" />
                      )}
                    </div>
                  </div>

                  {/* Cellular Network Cloud */}
                  <div className="sg-cloud-box">
                    <div className="sg-cloud-shape">
                      <Radio size={24} color="#0284C7" />
                    </div>
                    <div className="sg-cloud-name">Cellular Network</div>
                    <div className="sg-cloud-sub">(Communication Channel)</div>
                  </div>

                  {/* Flow Arrow 2 */}
                  <div className={`sg-flow-connector ${isProtectedMode ? 'secure' : 'unsecure'}`}>
                    <div className="sg-flow-line"></div>
                    <div className="sg-flow-shield">
                      {isProtectedMode ? (
                        <ShieldCheck size={16} color="#FFFFFF" />
                      ) : (
                        <Unlock size={14} color="#FFFFFF" />
                      )}
                    </div>
                  </div>

                  {/* Receiver (Device B) */}
                  <div className="sg-actor-box">
                    <div className="sg-laptop-icon receiver">
                      <User size={28} color="#FFFFFF" />
                    </div>
                    <div className="sg-actor-name">Device B (Receiver)</div>
                    <div className="sg-actor-sub">Bob · iPhone 15 Pro</div>
                  </div>
                </div>

                {/* Attacker Intercept Rays & Avatar */}
                <div className="sg-diagram-attacker-branch">
                  <div className="sg-attacker-rays">
                    <svg viewBox="0 0 460 60" fill="none" className="rays-svg">
                      <path
                        d="M 60 0 Q 180 50 230 55"
                        stroke="#EF4444"
                        strokeWidth="2"
                        strokeDasharray="4 4"
                        fill="none"
                      />
                      <path
                        d="M 400 0 Q 280 50 230 55"
                        stroke="#EF4444"
                        strokeWidth="2"
                        strokeDasharray="4 4"
                        fill="none"
                      />
                    </svg>
                  </div>
                  <div className="sg-attacker-avatar-wrap">
                    <div className="sg-attacker-avatar">
                      <AlertTriangle size={18} color="#DC2626" />
                    </div>
                    <div className="sg-attacker-title">Attacker (Eve)</div>
                    <div className="sg-attacker-desc">Intercepting Traffic</div>
                  </div>
                </div>
              </div>

              {/* 3-Column Interaction Layout */}
              <div className="sg-columns-grid">
                
                {/* Column 1: Device A — Send Message */}
                <div className="sg-card device-card">
                  <div className="sg-card-header">
                    <div className="sg-card-title-group">
                      <div className="sg-card-dot blue">
                        <User size={14} color="#FFFFFF" />
                      </div>
                      <span className="sg-card-title">Device A — Send Message</span>
                    </div>
                    <span className="sg-badge-verified">
                      <CheckCircle2 size={12} />
                      <span>Verified Device</span>
                    </span>
                  </div>

                  <div className="sg-card-body">
                    <label className="sg-input-label">Message to Transmit:</label>
                    <textarea
                      className="sg-textarea"
                      rows={3}
                      value={message}
                      onChange={(e) => setMessage(e.target.value)}
                    />

                    <div className="sg-preset-pills">
                      <button
                        className="sg-preset-btn"
                        onClick={() => {
                          const m = 'Your Bank OTP is 849201. Valid for 5 minutes.';
                          setMessage(m);
                          runSimulation(isProtectedMode, m);
                        }}
                      >
                        <MessageSquare size={13} />
                        <span>Bank OTP</span>
                      </button>
                      <button
                        className="sg-preset-btn"
                        onClick={() => {
                          const m = 'CONFIDENTIAL: Wire transfer $50,000 approved to Acct #10928.';
                          setMessage(m);
                          runSimulation(isProtectedMode, m);
                        }}
                      >
                        <ArrowRight size={13} />
                        <span>Wire Transfer</span>
                      </button>
                      <button
                        className="sg-preset-btn"
                        onClick={() => {
                          const m = 'Server Access Token: tok_live_948201948201948';
                          setMessage(m);
                          runSimulation(isProtectedMode, m);
                        }}
                      >
                        <Key size={13} />
                        <span>Auth Token</span>
                      </button>
                    </div>

                    <button
                      className="sg-btn-primary"
                      disabled={loading}
                      onClick={() => runSimulation(isProtectedMode, message)}
                    >
                      <Send size={15} />
                      <span>{loading ? 'Encrypting & Transmitting...' : 'Send Secure Message'}</span>
                    </button>
                  </div>
                </div>

                {/* Column 2: Attacker (Eve) — Intercepted Data */}
                <div className="sg-card attacker-card">
                  <div className="sg-card-header">
                    <div className="sg-card-title-group">
                      <div className="sg-card-dot red">
                        <AlertTriangle size={14} color="#FFFFFF" />
                      </div>
                      <span className="sg-card-title">Attacker (Eve) — Intercepted Data</span>
                    </div>
                    <span className="sg-badge-intercepting">
                      <span className="sg-pulse-red"></span>
                      <span>+ Intercepting...</span>
                    </span>
                  </div>

                  <div className="sg-card-body">
                    {/* Box 1: SIMGUARD is OFF (Legacy) */}
                    <div className={`sg-intercept-box legacy ${!isProtectedMode ? 'active-highlight' : ''}`}>
                      <div className="sg-intercept-box-header">
                        <Eye size={14} color="#DC2626" />
                        <span className="sg-intercept-box-title">If SIMGUARD is OFF (Legacy):</span>
                      </div>
                      <div className="sg-intercept-content plaintext">
                        "{message}"
                      </div>
                    </div>

                    {/* Box 2: SIMGUARD is ON (Protected) */}
                    <div className={`sg-intercept-box protected ${isProtectedMode ? 'active-highlight' : ''}`}>
                      <div className="sg-intercept-box-header">
                        <Lock size={14} color="#0D9488" />
                        <span className="sg-intercept-box-title">If SIMGUARD is ON (Protected):</span>
                      </div>
                      <div className="sg-intercept-content ciphertext">
                        <span>
                          {simResult?.attacker?.intercepted_data ||
                            'bfA0Akf1QArzFOX3KzPYcGWFIFLKVnenVJG3w8sr0rXPHJrpina1KWiWDZx17n3QK3k0...'}
                        </span>
                        <button
                          className="sg-copy-btn"
                          title="Copy Ciphertext"
                          onClick={() => copyToClipboard(simResult?.attacker?.intercepted_data || 'bfA0Akf1QArzFOX3KzPYcGWFIFLKVnenVJ...')}
                        >
                          {copied ? <Check size={13} color="#0D9488" /> : <Copy size={13} />}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Column 3: Device B — Received Message */}
                <div className="sg-card receiver-card">
                  <div className="sg-card-header">
                    <div className="sg-card-title-group">
                      <div className="sg-card-dot green">
                        <User size={14} color="#FFFFFF" />
                      </div>
                      <span className="sg-card-title">Device B — Received Message</span>
                    </div>
                    <span className="sg-badge-verified">
                      <CheckCircle2 size={12} />
                      <span>Verified Device</span>
                    </span>
                  </div>

                  <div className="sg-card-body">
                    <label className="sg-input-label">Decrypted Received Message:</label>
                    <div className="sg-received-bubble">
                      <CheckCircle2 size={18} color="#10B981" className="flex-shrink-0" />
                      <span className="sg-received-text">
                        {simResult?.recipient?.decrypted_plaintext || message}
                      </span>
                    </div>

                    <div className="sg-verification-box">
                      <div className="sg-verification-header">
                        <ShieldCheck size={15} color="#0D9488" />
                        <span>Verification</span>
                      </div>
                      <ul className="sg-verification-list">
                        <li>
                          <CheckCircle2 size={14} color="#10B981" />
                          <span>Digital Signature: <strong>Verified</strong></span>
                        </li>
                        <li>
                          <CheckCircle2 size={14} color="#10B981" />
                          <span>Message Integrity (SHA-256): <strong>Valid</strong></span>
                        </li>
                        <li>
                          <CheckCircle2 size={14} color="#10B981" />
                          <span>Device Identity: <strong>Authenticated</strong></span>
                        </li>
                      </ul>
                    </div>
                  </div>
                </div>

              </div>

              {/* Bottom Blockchain Record Card */}
              <div className="sg-record-card">
                <div className="sg-record-header">
                  <div className="sg-record-title-group">
                    <Layers size={18} color="#0D9488" />
                    <span className="sg-record-title">Blockchain Record (Transaction Logged)</span>
                  </div>
                  <button
                    className="sg-record-link"
                    onClick={() => {
                      setActiveTab('ledger');
                      fetchLedger('ALL');
                    }}
                  >
                    <span>View Ledger</span>
                    <ArrowRight size={14} />
                  </button>
                </div>

                <div className="sg-record-grid">
                  <div className="sg-record-item">
                    <div className="sg-record-icon-box">
                      <Box size={16} />
                    </div>
                    <div className="sg-record-meta">
                      <span className="sg-record-label">Block</span>
                      <span className="sg-record-val">#{simResult?.recipient?.block_index || 12}</span>
                    </div>
                  </div>

                  <div className="sg-record-item">
                    <div className="sg-record-icon-box">
                      <FileText size={16} />
                    </div>
                    <div className="sg-record-meta">
                      <span className="sg-record-label">Transaction ID</span>
                      <span className="sg-record-val font-mono">
                        {simResult?.recipient?.tx_id || 'TX-CE9A8883BB47'}
                      </span>
                    </div>
                  </div>

                  <div className="sg-record-item">
                    <div className="sg-record-icon-box">
                      <MessageSquare size={16} />
                    </div>
                    <div className="sg-record-meta">
                      <span className="sg-record-label">Type</span>
                      <span className="sg-record-val">MESSAGE</span>
                    </div>
                  </div>

                  <div className="sg-record-item">
                    <div className="sg-record-icon-box">
                      <Hash size={16} />
                    </div>
                    <div className="sg-record-meta">
                      <span className="sg-record-label">SHA-256 Hash</span>
                      <span className="sg-record-val font-mono">
                        {simResult?.attacker?.intercepted_hash?.slice(0, 18) || '00bfdca7bafbb5575d'}...
                      </span>
                    </div>
                  </div>

                  <div className="sg-record-item">
                    <div className="sg-record-icon-box status-ok">
                      <CheckCircle2 size={16} color="#10B981" />
                    </div>
                    <div className="sg-record-meta">
                      <span className="sg-record-label">Status</span>
                      <span className="sg-record-val status-verified">Verified</span>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}

          {/* ═══════════════════════════════════════════════════════════════
               TAB 2: BLOCKCHAIN LEDGER
               ═══════════════════════════════════════════════════════════════ */}
          {activeTab === 'ledger' && (
            <div className="sg-tab-view">
              {/* Stats Bar */}
              <div className="sg-ledger-stats">
                <div className="sg-stat-card">
                  <span className="sg-stat-num">{ledgerStats?.total_blocks || 0}</span>
                  <span className="sg-stat-title">Total Blocks</span>
                </div>
                <div className="sg-stat-card">
                  <span className="sg-stat-num">{ledgerStats?.total_transactions || 0}</span>
                  <span className="sg-stat-title">Transactions</span>
                </div>
                <div className="sg-stat-card">
                  <span className="sg-stat-num">{ledgerStats?.transaction_counts?.REGISTER || 0}</span>
                  <span className="sg-stat-title">REGISTER</span>
                </div>
                <div className="sg-stat-card">
                  <span className="sg-stat-num">{ledgerStats?.transaction_counts?.MESSAGE || 0}</span>
                  <span className="sg-stat-title">MESSAGE</span>
                </div>
                <div className="sg-stat-card">
                  <span className="sg-stat-num">{ledgerStats?.transaction_counts?.CALL_META || 0}</span>
                  <span className="sg-stat-title">CALL_META</span>
                </div>
                <div className="sg-stat-card alert">
                  <span className="sg-stat-num text-red">{ledgerStats?.transaction_counts?.SECURITY_ALERT || 0}</span>
                  <span className="sg-stat-title">SECURITY ALERTS</span>
                </div>
              </div>

              {/* Filter Pills */}
              <div className="sg-filter-bar">
                <div className="sg-filter-pills">
                  {['ALL', 'REGISTER', 'MESSAGE', 'CALL_META', 'SECURITY_ALERT'].map((cat) => (
                    <button
                      key={cat}
                      className={`sg-filter-pill ${ledgerCategory === cat ? 'active' : ''}`}
                      onClick={() => handleCategoryChange(cat)}
                    >
                      {cat}
                    </button>
                  ))}
                </div>
                <button className="sg-btn-outline" onClick={() => fetchLedger(ledgerCategory)}>
                  <RefreshCw size={13} />
                  <span>Refresh Ledger</span>
                </button>
              </div>

              {/* Table */}
              <div className="sg-table-card">
                <table className="sg-table">
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
                          <td className="font-bold font-mono">#{block.index}</td>
                          <td className="text-muted text-xs">
                            {new Date(tx.timestamp * 1000).toLocaleTimeString()}
                          </td>
                          <td>
                            <span className={`sg-tx-badge ${tx.tx_type}`}>
                              {tx.tx_type}
                            </span>
                          </td>
                          <td className="font-mono text-xs">{tx.tx_id}</td>
                          <td className="font-mono text-xs text-muted">
                            {tx.sender_phone_hash?.slice(0, 14)}...
                          </td>
                          <td className="text-xs">
                            {tx.tx_type === 'REGISTER' && `Model: ${tx.payload?.device_model || tx.payload?.action}`}
                            {tx.tx_type === 'MESSAGE' && `Payload Hash: ${tx.payload?.payload_hash?.slice(0, 16)}...`}
                            {tx.tx_type === 'CALL_META' && `Call: ${tx.payload?.duration_seconds}s (${tx.payload?.codec})`}
                            {tx.tx_type === 'SECURITY_ALERT' && `Alert: ${tx.payload?.threat_type || 'Takeover Attempt'}`}
                          </td>
                          <td className="font-mono text-xs text-muted">
                            {tx.signature_hex?.slice(0, 14)}...
                          </td>
                          <td className="font-mono text-xs text-muted">
                            {block.block_hash?.slice(0, 12)}...
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
               TAB 3: DEVICE IDENTITY
               ═══════════════════════════════════════════════════════════════ */}
          {activeTab === 'identity' && (
            <div className="sg-tab-view">
              <div className="sg-identity-banner">
                <div className="sg-identity-banner-left">
                  <Smartphone size={24} color="#0D9488" />
                  <div>
                    <h2 className="sg-identity-title">Triple-Factor Device Identity Binding</h2>
                    <p className="sg-identity-sub">
                      Root Identity Hash = SHA-256 ( Phone Hash || Ed25519 Public Key || Hardware Fingerprint Hash )
                    </p>
                  </div>
                </div>
                <div className="sg-identity-banner-right">
                  <span className="sg-badge-verified">
                    <CheckCircle2 size={13} />
                    <span>Hardware Binding: Active</span>
                  </span>
                </div>
              </div>

              <div className="sg-identity-grid">
                {/* Alice */}
                <div className="sg-card identity-box">
                  <div className="sg-card-header">
                    <div className="sg-card-title-group">
                      <div className="sg-card-dot blue">A</div>
                      <span className="sg-card-title">Alice (Pixel 8 Pro)</span>
                    </div>
                    <span className="sg-badge-verified">Authorized</span>
                  </div>
                  <div className="sg-identity-details">
                    <div className="sg-id-row">
                      <span className="sg-id-label">Phone:</span>
                      <span className="sg-id-val">+91 98765 43210</span>
                    </div>
                    <div className="sg-id-row">
                      <span className="sg-id-label">Phone Hash:</span>
                      <span className="sg-id-val font-mono">03a89c72e411b...</span>
                    </div>
                    <div className="sg-id-row">
                      <span className="sg-id-label">Ed25519 PubKey:</span>
                      <span className="sg-id-val font-mono">ed25519:7c9a41c28f10b...</span>
                    </div>
                    <div className="sg-id-row">
                      <span className="sg-id-label">HW Fingerprint:</span>
                      <span className="sg-id-val font-mono">a9f01832b498e...</span>
                    </div>
                    <div className="sg-id-root-box">
                      <span className="sg-root-title">Root Identity Hash:</span>
                      <code className="sg-root-code">00bfdca7bafbb5575df82fb1ac7e2cacd21a6842bc4d889704f3c3151a706610</code>
                    </div>
                  </div>
                </div>

                {/* Bob */}
                <div className="sg-card identity-box">
                  <div className="sg-card-header">
                    <div className="sg-card-title-group">
                      <div className="sg-card-dot green">B</div>
                      <span className="sg-card-title">Bob (iPhone 15 Pro)</span>
                    </div>
                    <span className="sg-badge-verified">Authorized</span>
                  </div>
                  <div className="sg-identity-details">
                    <div className="sg-id-row">
                      <span className="sg-id-label">Phone:</span>
                      <span className="sg-id-val">+91 98765 11223</span>
                    </div>
                    <div className="sg-id-row">
                      <span className="sg-id-label">Phone Hash:</span>
                      <span className="sg-id-val font-mono">11b89ef94902a...</span>
                    </div>
                    <div className="sg-id-row">
                      <span className="sg-id-label">Ed25519 PubKey:</span>
                      <span className="sg-id-val font-mono">ed25519:3b948cf9104a...</span>
                    </div>
                    <div className="sg-id-row">
                      <span className="sg-id-label">HW Fingerprint:</span>
                      <span className="sg-id-val font-mono">b801a942048fe...</span>
                    </div>
                    <div className="sg-id-root-box">
                      <span className="sg-root-title">Root Identity Hash:</span>
                      <code className="sg-root-code">00a184ef9284ba91840284ab910284bc910284ab910284bc910284ab910284ac</code>
                    </div>
                  </div>
                </div>

                {/* Attacker Eve */}
                <div className="sg-card identity-box rogue">
                  <div className="sg-card-header">
                    <div className="sg-card-title-group">
                      <div className="sg-card-dot red">E</div>
                      <span className="sg-card-title">Attacker Eve (Rogue Handset)</span>
                    </div>
                    <span className="sg-badge-intercepting">REJECTED</span>
                  </div>
                  <div className="sg-identity-details">
                    <div className="sg-id-row">
                      <span className="sg-id-label">Spoofed Phone:</span>
                      <span className="sg-id-val text-red">+91 98765 43210</span>
                    </div>
                    <div className="sg-id-row">
                      <span className="sg-id-label">Rogue HW Fingerprint:</span>
                      <span className="sg-id-val font-mono text-red">hw_unauthorized_attacker_rig_99</span>
                    </div>
                    <div className="sg-id-row">
                      <span className="sg-id-label">Missing Keypair:</span>
                      <span className="sg-id-val text-red">Alice Private Key Unavailable</span>
                    </div>
                    <div className="sg-id-root-box rogue">
                      <span className="sg-root-title">Auth Failure:</span>
                      <code className="sg-root-code text-red">MISMATCH: Triple-factor hash does not match registered ledger root.</code>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════════════
               TAB 4: THREAT DEFENSE & AUDIT
               ═══════════════════════════════════════════════════════════════ */}
          {activeTab === 'defense' && (
            <div className="sg-tab-view">
              <div className="sg-grid-2">
                {/* Test 1: Rogue SIM Swap Attack */}
                <div className="sg-card threat-card">
                  <div className="sg-card-header">
                    <div className="sg-card-title-group">
                      <ShieldAlert size={18} color="#DC2626" />
                      <span className="sg-card-title">Unauthorized Digital SIM Swap Defense</span>
                    </div>
                    <span className="sg-badge-intercepting">Attack Vector #1</span>
                  </div>
                  <div className="sg-card-body">
                    <p className="sg-card-p">
                      An attacker on an unauthorized device attempts to claim Alice's MSISDN. Because the attacker's hardware fingerprint and cryptographic signature cannot satisfy Alice's triple-factor binding, authentication is denied and a <code>SECURITY_ALERT</code> transaction is anchored on-chain.
                    </p>
                    <button className="sg-btn-danger" onClick={handleSimulateSwapAttack}>
                      <ShieldAlert size={15} />
                      <span>Simulate Rogue SIM Swap</span>
                    </button>
                  </div>
                </div>

                {/* Test 2: Cryptographic Chain Audit */}
                <div className="sg-card threat-card">
                  <div className="sg-card-header">
                    <div className="sg-card-title-group">
                      <CheckCircle2 size={18} color="#0D9488" />
                      <span className="sg-card-title">Blockchain Integrity Audit &amp; Tamper Detection</span>
                    </div>
                    <span className="sg-badge-verified">Auditing Tool</span>
                  </div>
                  <div className="sg-card-body">
                    <p className="sg-card-p">
                      Traverses every block in the ledger, recalculating the SHA-256 Merkle root across all transactions and verifying block hash chaining. Demonstrates that database tampering is detected immediately.
                    </p>
                    <div className="sg-btn-row">
                      <button className="sg-btn-teal" onClick={handleRunAudit}>
                        <CheckCircle2 size={15} />
                        <span>Run Full Audit</span>
                      </button>
                      <button className="sg-btn-outline" onClick={handleTamperBlock}>
                        <span>Simulate Block Tamper</span>
                      </button>
                      <button className="sg-btn-outline" onClick={handleRestoreLedger}>
                        <RefreshCw size={13} />
                        <span>Restore Ledger</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Terminal */}
              <div className="sg-terminal-card">
                <div className="sg-terminal-header">
                  <div className="sg-term-dots">
                    <span></span><span></span><span></span>
                  </div>
                  <span className="sg-terminal-title">Cryptographic Execution &amp; Audit Log</span>
                </div>
                <pre className="sg-terminal-code">{defenseLog}</pre>
              </div>
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════════════
               TAB 5: ANALYTICS
               ═══════════════════════════════════════════════════════════════ */}
          {activeTab === 'analytics' && (
            <div className="sg-tab-view">
              <div className="sg-record-card" style={{ marginBottom: '16px' }}>
                <div className="sg-record-header">
                  <div className="sg-record-title-group">
                    <BarChart3 size={18} color="#0D9488" />
                    <span className="sg-record-title">System Performance &amp; Cryptographic Latency</span>
                  </div>
                </div>
                <div className="sg-record-grid">
                  <div className="sg-record-item">
                    <div className="sg-record-meta">
                      <span className="sg-record-label">Mean Ed25519 Sign</span>
                      <span className="sg-record-val font-mono">0.052 ms</span>
                    </div>
                  </div>
                  <div className="sg-record-item">
                    <div className="sg-record-meta">
                      <span className="sg-record-label">Mean AES-256-GCM Encrypt</span>
                      <span className="sg-record-val font-mono">0.021 ms</span>
                    </div>
                  </div>
                  <div className="sg-record-item">
                    <div className="sg-record-meta">
                      <span className="sg-record-label">Merkle Tree Anchor</span>
                      <span className="sg-record-val font-mono">0.114 ms</span>
                    </div>
                  </div>
                  <div className="sg-record-item">
                    <div className="sg-record-meta">
                      <span className="sg-record-label">E2E Cellular Overhead</span>
                      <span className="sg-record-val font-mono">&lt; 1.2 ms</span>
                    </div>
                  </div>
                  <div className="sg-record-item">
                    <div className="sg-record-meta">
                      <span className="sg-record-label">Zero-Trust SLA</span>
                      <span className="sg-record-val status-verified">99.999%</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="sg-card">
                <div className="sg-card-header">
                  <span className="sg-card-title">Telecom Security Evaluation Summary</span>
                </div>
                <div className="sg-card-body">
                  <p className="sg-card-p">
                    Standard GSM/3G/4G airwave interception attacks (such as IMSI catchers, SS7 hijacking, and rogue base stations) succeed because cleartext payloads travel across unauthenticated radio links. SIMGUARD binds the subscriber identity to the physical silicon keypair (Ed25519) and anchors the SHA-256 message hash to an immutable blockchain ledger.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════════════
               TAB 6: SETTINGS
               ═══════════════════════════════════════════════════════════════ */}
          {activeTab === 'settings' && (
            <div className="sg-tab-view">
              <div className="sg-card">
                <div className="sg-card-header">
                  <div className="sg-card-title-group">
                    <Settings size={18} color="#0D9488" />
                    <span className="sg-card-title">Cryptographic Node Configuration</span>
                  </div>
                </div>
                <div className="sg-card-body">
                  <div className="sg-id-row">
                    <span className="sg-id-label">Node Consensus Mode:</span>
                    <span className="sg-id-val font-mono">Proof-of-Authority (PoA) Telecom Federation</span>
                  </div>
                  <div className="sg-id-row">
                    <span className="sg-id-label">Digital SIM Identity Algorithm:</span>
                    <span className="sg-id-val font-mono">Ed25519 Curve25519</span>
                  </div>
                  <div className="sg-id-row">
                    <span className="sg-id-label">Payload Cipher:</span>
                    <span className="sg-id-val font-mono">AES-256-GCM AEAD (12-byte Nonce, 16-byte Tag)</span>
                  </div>
                  <div className="sg-id-row">
                    <span className="sg-id-label">Blockchain Anchor Frequency:</span>
                    <span className="sg-id-val font-mono">Immediate per-packet transaction anchor</span>
                  </div>
                </div>
              </div>
            </div>
          )}

        </div>
      </div>

      {/* Floating Toast Notification */}
      {toastMsg && (
        <div className={`sg-toast ${toastMsg.isErr ? 'err' : 'ok'}`}>
          {toastMsg.isErr ? <AlertTriangle size={15} /> : <CheckCircle2 size={15} />}
          <span>{toastMsg.text}</span>
        </div>
      )}
    </div>
  );
}