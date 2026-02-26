import { useState } from "react";
import axios from "axios";

const API = import.meta.env.VITE_API_URL;

const STEPS = [
  { id: 1, label: "PARSING HYPOTHESIS",        detail: "" },
  { id: 2, label: "COLLECTING MARKET CONTEXT", detail: "" },
  { id: 3, label: "SCANNING HISTORICAL EVIDENCE", detail: "" },
  { id: 4, label: "RESEARCHING BEAR CASE",     detail: "" },
  { id: 5, label: "RESEARCHING BULL CASE",     detail: "" },
  { id: 6, label: "SYNTHESIZING RESEARCH BRIEF", detail: "" },
];

export default function HypothesisPage() {
  const [text,    setText]    = useState("");
  const [brief,   setBrief]   = useState(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState(null);
  const [steps,     setSteps]     = useState(
    STEPS.map(s => ({ ...s, status: "idle", detail: "" }))
    // status: idle | running | done | error
  );

  const submit = async () => {
  if (!text.trim()) return;
  setLoading(true);
  setError(null);
  setBrief(null);
  setSteps(STEPS.map(s => ({ ...s, status: "idle", detail: "" })));

  try {
    const response = await fetch(`${API}/hypothesis/stream`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ text }),
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const reader  = response.body.getReader();
    const decoder = new TextDecoder();
    let   buffer  = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n\n");
      buffer = lines.pop(); // keep incomplete chunk

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        try {
          const msg = JSON.parse(line.slice(6));

          if (msg.status === "running") {
            updateStep(msg.step, "running");
          }
          else if (msg.status === "done") {
            // Build detail string from metadata
            let detail = "";
            if (msg.ticker)          detail = `→ ${msg.ticker}`;
            if (msg.price)           detail = `→ $${msg.price?.toFixed(2)} · RSI ${msg.rsi?.toFixed(1)}`;
            if (msg.base_rate != null) detail = `→ base rate ${msg.base_rate}%`;
            if (msg.risks_found)     detail = `→ ${msg.risks_found} risks identified`;
            if (msg.catalysts_found) detail = `→ ${msg.catalysts_found} catalysts identified`;
            updateStep(msg.step, "done", detail);
          }
          else if (msg.status === "complete") {
            setBrief(msg.brief);
            setLoading(false);
          }
          else if (msg.status === "error") {
            if (msg.step > 0) updateStep(msg.step, "error", msg.message);
            else setError(msg.message || "Analysis failed.");
            setLoading(false);
          }
        } catch (parseErr) {
          console.warn("SSE parse error:", parseErr);
        }
      }
    }
  } catch (e) {
    setError(e.message || "Backend error.");
    setLoading(false);
  }
};

  return (
    <div style={s.page}>
      {/* Page header */}
      <div style={s.pageHeader}>
        <div>
          <div style={s.pageTitle}>HYPOTHESIS ENGINE</div>
          <div style={s.pageSubtitle}>
            Enter a market hypothesis. 6 agents will research, validate, and stress-test it.
          </div>
        </div>
        <div style={s.supportedTickers}>
          {["KO","JNJ","PG","WMT","AAPL","GOOGL"].map(t => (
            <span key={t} style={s.supportedBadge}>{t}</span>
          ))}
        </div>
      </div>

      {/* Input */}
      <div style={s.inputSection}>
        <div style={s.inputWrapper}>
          <span style={s.inputPrompt}>▸</span>
          <input
            style={s.input}
            value={text}
            onChange={e => setText(e.target.value)}
            onKeyDown={e => e.key === "Enter" && submit()}
            placeholder="e.g. Coca-Cola will reach $90 in 3 months"
            disabled={loading}
          />
          <button style={{ ...s.submitBtn, ...(loading ? s.submitBtnDisabled : {}) }}
            onClick={submit} disabled={loading}>
            {loading ? "ANALYZING..." : "RUN ANALYSIS →"}
          </button>
        </div>
        <div style={s.examples}>
          TRY:&nbsp;
          {[
            "Apple will drop 15% this quarter",
            "WMT will outperform in 2 months",
            "GOOGL hits $350 in 6 months",
          ].map(ex => (
            <span key={ex} style={s.exampleChip} onClick={() => setText(ex)}>
              {ex}
            </span>
          ))}
        </div>
      </div>

      {/* Dynamic Steps Panel */}
      {(loading || (steps[0].status !== "idle")) && !brief && (
        <div style={s.stepsPanel}>
          {steps.map((step) => (
            <div key={step.id} style={{
              ...s.stepRow,
              ...(step.status === "running" ? s.stepRunning : {}),
              ...(step.status === "done"    ? s.stepDone    : {}),
              ...(step.status === "error"   ? s.stepError   : {}),
            }}>
              <span style={s.stepNum}>0{step.id}</span>
              <span style={s.stepIcon}>
                {step.status === "idle"    && "○"}
                {step.status === "running" && <span style={s.spinner}>◈</span>}
                {step.status === "done"    && "✓"}
                {step.status === "error"   && "✗"}
              </span>
              <span style={s.stepLabel}>{step.label}</span>
              {step.detail && (
                <span style={s.stepDetail}>{step.detail}</span>
              )}
              {step.status === "running" && (
                <span style={s.stepPulse}>PROCESSING</span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Error */}
      {error && <div style={s.errorBox}>⚠ {error}</div>}

      {/* Research Brief */}
      {brief && <ResearchBrief brief={brief} />}
    </div>
  );
}

function ResearchBrief({ brief }) {
  const bullish = (brief.implied_return_pct ?? 0) >= 0;
  const scoreColor = brief.feasibility_score >= 70 ? "#22c55e"
                   : brief.feasibility_score >= 40 ? "#f59e0b" : "#ef4444";

  return (
    <div style={s.brief}>

      {/* Brief Header */}
      <div style={s.briefHeader}>
        <div style={s.briefMeta}>
          <span style={s.briefTicker}>{brief.ticker}</span>
          <span style={s.briefHypothesis}>"{brief.hypothesis_clean}"</span>
        </div>
        <div style={s.briefScores}>
          <div style={s.scoreBox}>
            <div style={{ ...s.scoreValue, color: scoreColor }}>
              {brief.feasibility_score}
            </div>
            <div style={s.scoreLabel}>FEASIBILITY</div>
          </div>
          {brief.implied_return_pct != null && (
            <div style={s.scoreBox}>
              <div style={{ ...s.scoreValue, color: bullish ? "#22c55e" : "#ef4444" }}>
                {brief.implied_return_pct > 0 ? "+" : ""}{brief.implied_return_pct}%
              </div>
              <div style={s.scoreLabel}>IMPLIED RETURN</div>
            </div>
          )}
          {brief.current_price && (
            <div style={s.scoreBox}>
              <div style={{ ...s.scoreValue, color: "#f1f5f9" }}>
                ${brief.current_price.toFixed(2)}
              </div>
              <div style={s.scoreLabel}>CURRENT PRICE</div>
            </div>
          )}
          {brief.target_price && (
            <div style={s.scoreBox}>
              <div style={{ ...s.scoreValue, color: "#f59e0b" }}>
                ${brief.target_price}
              </div>
              <div style={s.scoreLabel}>TARGET</div>
            </div>
          )}
        </div>
      </div>

      {/* Feasibility Bar */}
      <div style={s.feasBar}>
        <div style={s.feasBarLabel}>
          <span>FEASIBILITY SCORE</span>
          <span style={{ color: scoreColor }}>{brief.feasibility_score}/100</span>
        </div>
        <div style={s.feasBarTrack}>
          <div style={{ ...s.feasBarFill, width: `${brief.feasibility_score}%`, background: scoreColor }} />
        </div>
      </div>

      {/* Reality Check */}
      <div style={s.section}>
        <div style={s.sectionTitle}>◈ REALITY CHECK</div>
        <div style={s.sectionBody}>{brief.reality_check}</div>
      </div>

      {/* 3-column grid */}
      <div style={s.triGrid}>

        {/* Technical Picture */}
        <div style={s.card}>
          <div style={s.cardTitle}>TECHNICAL PICTURE</div>
          <div style={s.cardBody}>
            <DataRow label="RSI (14)"  value={brief.technical_picture?.rsi} />
            <DataRow label="TREND"     value={brief.technical_picture?.trend?.toUpperCase()} />
            <DataRow label="MOMENTUM"  value={brief.technical_picture?.momentum?.toUpperCase()} />
          </div>
          <div style={s.cardText}>{brief.technical_picture?.summary}</div>
        </div>

        {/* Historical Evidence */}
        <div style={s.card}>
          <div style={s.cardTitle}>HISTORICAL EVIDENCE</div>
          <div style={s.cardBody}>
            <DataRow
              label="BASE RATE"
              value={brief.historical_evidence?.base_rate_for_implied != null
                ? `${brief.historical_evidence.base_rate_for_implied}%` : "N/A"}
            />
            <DataRow
              label="MAX HIST. MOVE"
              value={brief.historical_evidence?.max_historical_move != null
                ? `+${brief.historical_evidence.max_historical_move}%` : "N/A"}
            />
          </div>
          <div style={s.cardText}>{brief.historical_evidence?.summary}</div>
        </div>

        {/* Parameters to Monitor */}
        <div style={s.card}>
          <div style={s.cardTitle}>MONITOR</div>
          {(brief.parameters_to_monitor || []).map((p, i) => (
            <div key={i} style={s.monitorRow}>
              <div style={s.monitorParam}>
                <span style={s.monitorName}>{p.param}</span>
                <span style={s.monitorCurrent}>{p.current}</span>
              </div>
              <div style={s.monitorWatch}>{p.watch_for}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Bull / Bear */}
      <div style={s.dualGrid}>
        <CasePanel title="▲ BULL CASE" items={brief.bull_case} color="#22c55e" />
        <CasePanel title="▼ BEAR CASE" items={brief.bear_case} color="#ef4444" />
      </div>

      {/* Summary */}
      <div style={s.summaryBox}>
        <div style={s.sectionTitle}>◈ ANALYST SUMMARY</div>
        <div style={s.summaryText}>{brief.summary}</div>
      </div>

      {/* Disclaimer */}
      <div style={s.disclaimer}>{brief.disclaimer}</div>
    </div>
  );
}

function CasePanel({ title, items, color }) {
  return (
    <div style={{ ...s.card, borderTop: `2px solid ${color}20` }}>
      <div style={{ ...s.cardTitle, color }}>{title}</div>
      {(items || []).map((item, i) => (
        <div key={i} style={s.caseItem}>
          <div style={{ ...s.caseTitle, color }}>{item.title}</div>
          <div style={s.caseDesc}>{item.description}</div>
          {item.source_url && (
            <a href={item.source_url} target="_blank" rel="noreferrer" style={s.caseLink}>
              SOURCE →
            </a>
          )}
        </div>
      ))}
    </div>
  );
}

function DataRow({ label, value }) {
  return (
    <div style={s.dataRow}>
      <span style={s.dataLabel}>{label}</span>
      <span style={s.dataValue}>{value ?? "—"}</span>
    </div>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────
const s = {
  page: {
    maxWidth: 1200, margin: "0 auto", padding: "32px 32px 80px",
    fontFamily: "'IBM Plex Mono', 'Courier New', monospace",
  },
  pageHeader: {
    display: "flex", justifyContent: "space-between", alignItems: "flex-start",
    marginBottom: 32, paddingBottom: 24, borderBottom: "1px solid #111",
  },
  pageTitle:    { fontSize: 22, fontWeight: 800, color: "#f1f5f9", letterSpacing: 3 },
  pageSubtitle: { fontSize: 12, color: "#374151", marginTop: 6, letterSpacing: 0.5 },
  supportedTickers: { display: "flex", gap: 6, flexWrap: "wrap", justifyContent: "flex-end" },
  supportedBadge: {
    fontSize: 10, padding: "3px 8px", color: "#475569",
    border: "1px solid #1a1a1a", letterSpacing: 1,
  },
  inputSection: { marginBottom: 32 },
  inputWrapper: {
    display: "flex", alignItems: "center", gap: 0,
    border: "1px solid #222", background: "#0a0a0a",
  },
  inputPrompt: { padding: "0 16px", color: "#f59e0b", fontSize: 16 },
  input: {
    flex: 1, background: "transparent", border: "none", outline: "none",
    color: "#f1f5f9", fontSize: 14, padding: "16px 0",
    fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 0.3,
  },
  submitBtn: {
    padding: "16px 24px", background: "#f59e0b", border: "none",
    color: "#000", fontWeight: 800, fontSize: 11, letterSpacing: 2,
    cursor: "pointer", fontFamily: "'IBM Plex Mono', monospace",
    transition: "opacity 0.15s",
  },
  submitBtnDisabled: { opacity: 0.5, cursor: "not-allowed" },
  examples: {
    fontSize: 10, color: "#374151", marginTop: 10,
    display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap",
  },
  exampleChip: {
    color: "#475569", cursor: "pointer", padding: "2px 8px",
    border: "1px solid #1a1a1a", fontSize: 10,
    transition: "color 0.15s",
  },
  loadingPanel: {
    background: "#0a0a0a", border: "1px solid #1a1a1a",
    padding: "32px", marginBottom: 24,
  },
  loadingStep: {
    fontSize: 11, color: "#374151", padding: "6px 0",
    borderBottom: "1px solid #0f0f0f", letterSpacing: 1,
    animation: "fadeIn 0.4s ease forwards", opacity: 0,
  },
  loadingDot: { color: "#f59e0b" },
  errorBox: {
    background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.2)",
    color: "#ef4444", padding: "16px 24px", fontSize: 12, marginBottom: 24,
  },
  brief: { display: "flex", flexDirection: "column", gap: 16 },
  briefHeader: {
    display: "flex", justifyContent: "space-between", alignItems: "flex-start",
    padding: "24px", background: "#0a0a0a", border: "1px solid #151515",
  },
  briefMeta:      { display: "flex", flexDirection: "column", gap: 8 },
  briefTicker:    { fontSize: 28, fontWeight: 800, color: "#f59e0b", letterSpacing: 4 },
  briefHypothesis:{ fontSize: 13, color: "#64748b", maxWidth: 500 },
  briefScores:    { display: "flex", gap: 1 },
  scoreBox: {
    display: "flex", flexDirection: "column", alignItems: "center", gap: 4,
    padding: "12px 20px", background: "#080808", border: "1px solid #111",
    minWidth: 90,
  },
  scoreValue: { fontSize: 22, fontWeight: 800 },
  scoreLabel: { fontSize: 9,  color: "#374151", letterSpacing: 1.5 },
  feasBar:     { padding: "16px 24px", background: "#0a0a0a", border: "1px solid #111" },
  feasBarLabel:{
    display: "flex", justifyContent: "space-between",
    fontSize: 10, letterSpacing: 1.5, color: "#374151", marginBottom: 8,
  },
  feasBarTrack:{ height: 3, background: "#111" },
  feasBarFill: { height: "100%", transition: "width 0.8s ease" },
  section:     { padding: "20px 24px", background: "#0a0a0a", border: "1px solid #111" },
  sectionTitle:{ fontSize: 10, color: "#f59e0b", letterSpacing: 2, marginBottom: 12 },
  sectionBody: { fontSize: 13, color: "#94a3b8", lineHeight: 1.7 },
  triGrid:     { display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 1 },
  dualGrid:    { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1 },
  card:        { padding: "20px", background: "#0a0a0a", border: "1px solid #111" },
  cardTitle:   { fontSize: 10, color: "#475569", letterSpacing: 2, marginBottom: 16 },
  cardBody:    { marginBottom: 12 },
  cardText:    { fontSize: 11, color: "#475569", lineHeight: 1.6 },
  dataRow: {
    display: "flex", justifyContent: "space-between", alignItems: "center",
    padding: "6px 0", borderBottom: "1px solid #0f0f0f",
  },
  dataLabel: { fontSize: 10, color: "#374151", letterSpacing: 1 },
  dataValue: { fontSize: 12, color: "#f1f5f9", fontWeight: 600 },
  monitorRow: {
    padding: "10px 0", borderBottom: "1px solid #0f0f0f",
  },
  monitorParam:   { display: "flex", justifyContent: "space-between", marginBottom: 4 },
  monitorName:    { fontSize: 10, color: "#f59e0b", letterSpacing: 1 },
  monitorCurrent: { fontSize: 10, color: "#f1f5f9", fontWeight: 600 },
  monitorWatch:   { fontSize: 10, color: "#374151", lineHeight: 1.5 },
  caseItem: {
    padding: "12px 0", borderBottom: "1px solid #0f0f0f",
  },
  caseTitle: { fontSize: 11, fontWeight: 700, letterSpacing: 1, marginBottom: 6 },
  caseDesc:  { fontSize: 11, color: "#475569", lineHeight: 1.6, marginBottom: 6 },
  caseLink:  {
    fontSize: 9, color: "#374151", letterSpacing: 1.5,
    textDecoration: "none",
  },
  summaryBox: {
    padding: "24px", background: "#0a0a0a",
    border: "1px solid #151515", borderLeft: "3px solid #f59e0b",
  },
  summaryText: { fontSize: 13, color: "#94a3b8", lineHeight: 1.8 },
  disclaimer:  {
    fontSize: 10, color: "#1f2937", letterSpacing: 0.5,
    textAlign: "center", padding: "12px",
  },
    stepsPanel: {
    background:   "#0a0a0a",
    border:       "1px solid #1a1a1a",
    marginBottom: 24,
    overflow:     "hidden",
  },
  stepRow: {
    display:     "flex",
    alignItems:  "center",
    gap:         12,
    padding:     "14px 24px",
    borderBottom:"1px solid #0f0f0f",
    fontSize:    11,
    color:       "#1f2937",
    letterSpacing: 1,
    transition:  "all 0.3s ease",
  },
  stepRunning: {
    color:      "#f59e0b",
    background: "rgba(245,158,11,0.03)",
    borderLeft: "2px solid #f59e0b",
  },
  stepDone: {
    color:      "#22c55e",
    borderLeft: "2px solid rgba(34,197,94,0.3)",
  },
  stepError: {
    color:      "#ef4444",
    borderLeft: "2px solid rgba(239,68,68,0.3)",
  },
  stepNum:    { color: "#1f2937", fontSize: 10, minWidth: 20 },
  stepIcon:   { fontSize: 12, minWidth: 16 },
  stepLabel:  { flex: 1 },
  stepDetail: { fontSize: 10, color: "#475569", marginLeft: "auto" },
  stepPulse:  {
    fontSize: 9, color: "#f59e0b",
    letterSpacing: 2, animation: "pulse 1s ease-in-out infinite",
  },
  spinner: {
    display:   "inline-block",
    animation: "spin 1s linear infinite",
  },
};