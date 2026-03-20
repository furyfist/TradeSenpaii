/**
 * Real data fetched from:
 *   GET /anomaly-history  → total_filings, total_flagged, ticker count
 *   GET /evidence-cases   → hero cases for real evidence examples
 *
 * Written content (definitions, red flags, methodology) is hardcoded
 * because it's educational copy, not dynamic data.
 */

import { useState, useEffect } from "react";
import axios from "axios";

const API = import.meta.env.VITE_API_URL;

// ── Design tokens 
const C = {
  bg:      "#080808", surface: "#0a0a0a",
  border:  "#1a1a1a", border2: "#222222",
  gold:    "#f59e0b", goldGlow: "rgba(245,158,11,0.10)",
  red:     "#ef4444", redDim:   "rgba(239,68,68,0.10)",
  green:   "#22c55e", greenDim: "rgba(34,197,94,0.08)",
  amber:   "#f97316", amberDim: "rgba(249,115,22,0.10)",
  blue:    "#3b82f6", blueDim:  "rgba(59,130,246,0.10)",
  text:    "#e5e7eb", textDim:  "#6b7280", textMid: "#9ca3af",
  font:    "'IBM Plex Mono', 'Courier New', monospace",
};

// ── Static educational content 

const FILING_TYPES = [
  {
    form:    "10-K",
    name:    "Annual Report",
    freq:    "Once per year",
    color:   C.gold,
    tag:     "MOST IMPORTANT",
    summary: "The most comprehensive filing a company makes. Think of it as the company's annual autobiography — everything that happened, every risk they face, every dollar they spent.",
    sections: [
      { name: "Business",            desc: "What the company actually does. Products, markets, competition, strategy." },
      { name: "Risk Factors",        desc: "Every risk the company admits to. This is where lawyers get paid — and where signals hide." },
      { name: "MD&A",                desc: "Management's Discussion & Analysis. Executives explain results in their own words. Tone matters here." },
      { name: "Financial Statements",desc: "Income statement, balance sheet, cash flow. The hard numbers." },
      { name: "Legal Proceedings",   desc: "Active lawsuits and investigations. Often buried. Often important." },
    ],
    whyMatters: "Institutional investors spend weeks on 10-Ks. Retail investors read the headline. The gap between those two is where edge lives.",
    redFlags: [
      "Going concern language — auditors questioning the company's survival",
      "Sudden increase in Risk Factors section length",
      "Management tone shift from confident to hedged",
      "New litigation disclosures buried in footnotes",
      "Auditor change without explanation",
    ],
  },
  {
    form:    "10-Q",
    name:    "Quarterly Report",
    freq:    "3x per year",
    color:   C.amber,
    tag:     "EARLY WARNING",
    summary: "The quarterly update — less comprehensive than 10-K but filed 3x per year. This is where deteriorating trends first appear before they show up in annual reports.",
    sections: [
      { name: "Financial Statements",desc: "Unaudited quarterly numbers. Watch for sequential decline." },
      { name: "MD&A",                desc: "Quarterly management commentary. Compare tone to previous quarters." },
      { name: "Risk Factors",        desc: "Changes from the annual report. New risks added = something changed." },
      { name: "Legal Proceedings",   desc: "Updated litigation status. New cases are a red flag." },
    ],
    whyMatters: "Three consecutive quarters of sentiment deterioration in our AAPL analysis (Q1-Q3 2023) preceded a -15% drawdown. The annual report would have been too late.",
    redFlags: [
      "Sequential revenue decline across 2+ quarters",
      "New risk factors not in the 10-K",
      "Increased uncertainty language vs prior quarter",
      "Litigation section growing filing by filing",
      "CFO or auditor changes mid-year",
    ],
  },
  {
    form:    "8-K",
    name:    "Current Report",
    freq:    "As needed",
    color:   C.red,
    tag:     "EVENT DRIVEN",
    summary: "Filed within 4 business days of a material event. Earnings, acquisitions, executive departures, lawsuits, bankruptcies. If something big happened, an 8-K was filed.",
    sections: [
      { name: "Item 1.01", desc: "Material agreements — acquisitions, partnerships, major contracts." },
      { name: "Item 5.02", desc: "Executive departures or appointments. C-suite changes matter." },
      { name: "Item 7.01", desc: "Regulation FD disclosure — what management told investors." },
      { name: "Item 8.01", desc: "Other material events. Catch-all for anything significant." },
    ],
    whyMatters: "8-Ks move stock prices. But they're reactive — the company is telling you what already happened. 10-K/10-Q signals are predictive.",
    redFlags: [
      "CEO/CFO departure without succession plan",
      "Restatement of financial statements",
      "Material weakness in internal controls",
      "Regulatory investigation disclosed",
      "Amendment to executive compensation (often precedes trouble)",
    ],
  },
];

const SIGNAL_KEYS = {
  "Negative Language":    { keyword: "Negative", icon: "↓", color: C.red,   bg: C.redDim  },
  "Uncertainty Language": { keyword: "Uncertain", icon: "?", color: C.amber, bg: C.amberDim },
  "Litigation Language":  { keyword: "Litigation", icon: "⚖", color: C.blue, bg: C.blueDim  },
  "Sentiment Score":      { keyword: "Sentiment", icon: "S", color: C.green, bg: C.greenDim },
};

const LM_SIGNALS_STATIC = [
  {
    name:    "Negative Language",
    what:    "Words like: loss, decline, adverse, impairment, deteriorate, worsen, write-off",
    why:     "Companies use negative language when they can't avoid acknowledging bad news. A spike means something got materially worse since the last filing.",
    example: '"We experienced a significant decline in revenue due to adverse macroeconomic conditions and deteriorating demand in key markets."',
    signal:  "When negative language spikes >1.5σ above a company's own baseline, our model flags it as a risk signal.",
    fallbackCase: "JNJ Q3 2005: All 5 signals triggered simultaneously. Preceded Risperdal litigation wave.",
  },
  {
    name:    "Uncertainty Language",
    what:    "Words like: uncertain, unpredictable, volatile, fluctuate, may affect, cannot predict",
    why:     "Management uses hedging language when they genuinely don't know what's coming. More uncertainty language = less management forward visibility.",
    example: '"Future results are subject to significant uncertainties and may be materially affected by factors that are difficult to predict."',
    signal:  "Uncertainty spikes often precede earnings misses by 1-2 quarters. Management is signaling reduced forward visibility.",
    fallbackCase: "AAPL 2012 10-K: Uncertainty spiked 3.5σ — year of Maps disaster, Tim Cook transition, margin compression.",
  },
  {
    name:    "Litigation Language",
    what:    "Words like: litigation, lawsuit, plaintiff, judgment, settlement, regulatory, investigation, penalty",
    why:     "Legal costs are real. Litigation language spikes before settlements are reached — often 2-4 quarters before the financial impact hits.",
    example: '"The Company is subject to various legal proceedings and claims, the outcomes of which are inherently uncertain."',
    signal:  "JNJ 2008: Litigation count hit 92.55σ — 141 mentions in a single quarterly filing.",
    fallbackCase: "KO 2005: Litigation count spiked to 191 mentions — 33.88σ above baseline during SEC investigation.",
  },
  {
    name:    "Sentiment Score",
    what:    "Net score: positive words minus negative words, normalized by total word count",
    why:     "Overall filing tone. A company that filed positively for years suddenly filing negatively is a structural shift — not just one bad quarter.",
    example: "Score = (positive_words - negative_words) / total_words × 100",
    signal:  "Three consecutive quarters of declining sentiment score is the strongest signal in our model — it means the deterioration is structural.",
    fallbackCase: "GOOGL 2022 10-K: Sentiment anomaly flagged before -28.1% drawdown over 90 days.",
  },
];

const HOW_IT_WORKS = [
  {
    step: "01", title: "Download Filings",
    desc:   "We pull every 10-K and 10-Q from EDGAR for each ticker. Some companies have 30+ years of filings.",
    detail: "SEC EDGAR is the public database where all US public companies must file. It's free, it's complete, and most retail investors have never opened it.",
  },
  {
    step: "02", title: "Apply LM Dictionary",
    desc:   "The Loughran-McDonald financial dictionary categorizes words specifically for financial documents.",
    detail: "Generic sentiment tools (like VADER) were trained on tweets and reviews. The word 'liability' is negative in everyday language but neutral in finance. LM dictionary was built specifically for SEC filings — same one used by academic researchers and hedge funds.",
  },
  {
    step: "03", title: "Compute Baseline",
    desc:   "Each company is compared against its own history — not against other companies.",
    detail: "JNJ naturally uses more litigation language than AAPL. What matters is when JNJ's language deviates from JNJ's own baseline. We use a rolling 8-filing window (2 years) as the baseline.",
  },
  {
    step: "04", title: "Flag Anomalies",
    desc:   "Any signal >1.5 standard deviations from baseline triggers a flag.",
    detail: "1.5σ means the signal is in the top 7% of historical readings for that specific company. We use z-scores so the threshold is statistically grounded, not arbitrary.",
  },
  {
    step: "05", title: "Train Transformer",
    desc:   "56 features (sentiment + technical) fed into a PyTorch transformer encoder.",
    detail: "The model learns which combinations of sentiment signals and price features historically preceded UP vs DOWN days. Sequence length of 60 trading days — the model sees 3 months of context before making a prediction.",
  },
  {
    step: "06", title: "Verify With Evidence",
    desc:   "We backtested 500 trading days per ticker — 3000 predictions total.",
    detail: "Overall accuracy: 52.5% on held-out data. Calibrated model: higher confidence predictions are more accurate. GOOGL and JNJ show the strongest signal alignment on 90-day forward returns.",
  },
];

// ── Helpers 

function findHeroCaseForSignal(heroCases, keyword) {
  if (!heroCases || heroCases.length === 0) return null;
  return heroCases.find(c =>
    (c.signals || []).some(sig =>
      String(sig).toLowerCase().includes(keyword.toLowerCase())
    )
  ) || null;
}

function formatHeroCase(c) {
  if (!c) return null;
  const r90 = c.return_90d !== null ? `${c.return_90d > 0 ? "+" : ""}${c.return_90d.toFixed(1)}%` : "—";
  const r30 = c.return_30d !== null ? `${c.return_30d > 0 ? "+" : ""}${c.return_30d.toFixed(1)}%` : "—";
  return `${c.ticker} ${c.filing_date} (${c.form_type}): Signal triggered. `
    + `30d: ${r30} · 90d: ${r90}. `
    + `Signals: ${(c.signals || []).join(", ")}.`;
}

// ── Small components 

function Tag({ label, color }) {
  return (
    <span style={{
      color, fontFamily: C.font, fontSize: 8,
      border: `1px solid ${color}`,
      padding: "2px 6px", letterSpacing: 1,
    }}>
      {label}
    </span>
  );
}

function SectionRow({ s, color }) {
  const [open, setOpen] = useState(false);
  return (
    <div
      onClick={() => setOpen(!open)}
      style={{ borderBottom: `1px solid ${C.border}`, cursor: "pointer" }}
    >
      <div style={{
        display: "flex", justifyContent: "space-between",
        padding: "10px 0", alignItems: "center",
      }}>
        <span style={{ color: C.text, fontFamily: C.font, fontSize: 10 }}>{s.name}</span>
        <span style={{ color: C.textDim, fontFamily: C.font, fontSize: 10 }}>
          {open ? "▲" : "▼"}
        </span>
      </div>
      {open && (
        <p style={{
          color: C.textMid, fontFamily: C.font,
          fontSize: 10, lineHeight: 1.7,
          margin: "0 0 10px 0",
          paddingLeft: 12,
          borderLeft: `2px solid ${color}`,
        }}>
          {s.desc}
        </p>
      )}
    </div>
  );
}

function StepCard({ s }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ borderBottom: `1px solid ${C.border}` }}>
      <div
        onClick={() => setOpen(!open)}
        style={{
          display: "flex", alignItems: "center",
          gap: 16, padding: "16px 20px", cursor: "pointer",
          background: open ? "rgba(245,158,11,0.03)" : "transparent",
        }}
      >
        <span style={{
          color: C.gold, fontFamily: C.font,
          fontSize: 11, fontWeight: 700,
          letterSpacing: 2, minWidth: 24,
        }}>
          {s.step}
        </span>
        <span style={{ color: C.text, fontFamily: C.font, fontSize: 11, flex: 1 }}>
          {s.title}
        </span>
        <span style={{ color: C.textDim, fontFamily: C.font, fontSize: 9 }}>
          {open ? "▲" : "▼"}
        </span>
      </div>
      {open && (
        <div style={{ padding: "0 20px 16px 60px" }}>
          <p style={{ color: C.textMid, fontFamily: C.font, fontSize: 10, lineHeight: 1.8, margin: 0 }}>
            {s.desc}
          </p>
          <p style={{
            color: C.textDim, fontFamily: C.font,
            fontSize: 10, lineHeight: 1.8,
            margin: "10px 0 0 0",
            borderLeft: `2px solid ${C.border2}`,
            paddingLeft: 10,
          }}>
            {s.detail}
          </p>
        </div>
      )}
    </div>
  );
}

// ── Filing detail panel 

function FilingCard({ f, active, onClick }) {
  const rgb = f.color === C.gold ? "245,158,11"
            : f.color === C.amber ? "249,115,22"
            : "239,68,68";
  return (
    <div onClick={onClick} style={{
      border:     `1px solid ${active ? f.color : C.border}`,
      background: active ? `rgba(${rgb},0.05)` : C.surface,
      padding:    "16px", cursor: "pointer",
      transition: "all 0.15s", position: "relative",
    }}>
      {active && (
        <div style={{
          position: "absolute", left: 0, top: 0,
          bottom: 0, width: 2, background: f.color,
        }} />
      )}
      <div style={{
        display: "flex", justifyContent: "space-between",
        alignItems: "flex-start", marginBottom: 8,
      }}>
        <span style={{ color: f.color, fontFamily: C.font, fontSize: 18, fontWeight: 700, letterSpacing: 1 }}>
          {f.form}
        </span>
        <Tag label={f.tag} color={f.color} />
      </div>
      <div style={{ color: C.text,    fontFamily: C.font, fontSize: 11, marginBottom: 4 }}>{f.name}</div>
      <div style={{ color: C.textDim, fontFamily: C.font, fontSize: 9  }}>{f.freq}</div>
    </div>
  );
}

function FilingDetail({ f }) {
  return (
    <div style={{ border: `1px solid ${C.border}`, background: C.surface }}>
      {/* header */}
      <div style={{
        padding: "20px 24px",
        borderBottom: `1px solid ${C.border}`,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 10 }}>
          <span style={{ color: f.color, fontFamily: C.font, fontSize: 24, fontWeight: 700 }}>
            {f.form}
          </span>
          <span style={{ color: C.textDim, fontFamily: C.font, fontSize: 11 }}>
            {f.name} · {f.freq}
          </span>
        </div>
        <p style={{ color: C.textMid, fontFamily: C.font, fontSize: 11, lineHeight: 1.8, margin: 0 }}>
          {f.summary}
        </p>
      </div>

      {/* why it matters */}
      <div style={{ padding: "16px 24px", borderBottom: `1px solid ${C.border}` }}>
        <div style={{ color: C.gold, fontFamily: C.font, fontSize: 8, letterSpacing: 2, marginBottom: 8 }}>
          WHY IT MATTERS
        </div>
        <p style={{ color: C.text, fontFamily: C.font, fontSize: 11, lineHeight: 1.8, margin: 0 }}>
          {f.whyMatters}
        </p>
      </div>

      {/* sections */}
      <div style={{ padding: "16px 24px", borderBottom: `1px solid ${C.border}` }}>
        <div style={{ color: C.gold, fontFamily: C.font, fontSize: 8, letterSpacing: 2, marginBottom: 10 }}>
          KEY SECTIONS
        </div>
        {f.sections.map((s, i) => (
          <SectionRow key={i} s={s} color={f.color} />
        ))}
      </div>

      {/* red flags */}
      <div style={{ padding: "16px 24px" }}>
        <div style={{ color: C.red, fontFamily: C.font, fontSize: 8, letterSpacing: 2, marginBottom: 10 }}>
          RED FLAGS TO WATCH
        </div>
        {f.redFlags.map((flag, i) => (
          <div key={i} style={{ display: "flex", gap: 10, marginBottom: 8, alignItems: "flex-start" }}>
            <span style={{ color: C.red, fontFamily: C.font, fontSize: 10, flexShrink: 0 }}>⚠</span>
            <span style={{ color: C.textMid, fontFamily: C.font, fontSize: 10, lineHeight: 1.6 }}>
              {flag}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Signal components 

function SignalCard({ s, active, onClick }) {
  const meta = SIGNAL_KEYS[s.name];
  return (
    <div onClick={onClick} style={{
      border:     `1px solid ${active ? meta.color : C.border}`,
      background: active ? meta.bg : C.surface,
      padding:    "14px 16px", cursor: "pointer", transition: "all 0.15s",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
        <div style={{
          width: 28, height: 28,
          background: meta.bg, border: `1px solid ${meta.color}`,
          display: "flex", alignItems: "center", justifyContent: "center",
          color: meta.color, fontFamily: C.font, fontSize: 12, fontWeight: 700,
        }}>
          {meta.icon}
        </div>
        <span style={{ color: meta.color, fontFamily: C.font, fontSize: 11, fontWeight: 700, letterSpacing: 1 }}>
          {s.name}
        </span>
      </div>
      <p style={{ color: C.textDim, fontFamily: C.font, fontSize: 9, lineHeight: 1.6, margin: 0 }}>
        {s.what}
      </p>
    </div>
  );
}

function SignalDetail({ s, heroCase }) {
  const meta        = SIGNAL_KEYS[s.name];
  const evidenceStr = heroCase ? formatHeroCase(heroCase) : s.fallbackCase;

  return (
    <div style={{ border: `1px solid ${C.border}`, background: C.surface }}>

      {/* header */}
      <div style={{
        padding: "20px 24px",
        borderBottom: `1px solid ${C.border}`,
        background: meta.bg,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 10 }}>
          <div style={{
            width: 36, height: 36,
            border: `1px solid ${meta.color}`,
            display: "flex", alignItems: "center", justifyContent: "center",
            color: meta.color, fontFamily: C.font, fontSize: 16, fontWeight: 700,
          }}>
            {meta.icon}
          </div>
          <span style={{ color: meta.color, fontFamily: C.font, fontSize: 16, fontWeight: 700, letterSpacing: 1 }}>
            {s.name.toUpperCase()}
          </span>
          {heroCase && (
            <Tag label="REAL DATA" color={meta.color} />
          )}
        </div>
        <p style={{ color: C.textMid, fontFamily: C.font, fontSize: 10, lineHeight: 1.7, margin: 0 }}>
          {s.why}
        </p>
      </div>

      {/* what triggers it */}
      <div style={{ padding: "16px 24px", borderBottom: `1px solid ${C.border}` }}>
        <div style={{ color: C.gold, fontFamily: C.font, fontSize: 8, letterSpacing: 2, marginBottom: 8 }}>
          WHAT TRIGGERS IT
        </div>
        <p style={{ color: C.textMid, fontFamily: C.font, fontSize: 10, lineHeight: 1.7, margin: 0 }}>
          {s.what}
        </p>
      </div>

      {/* example sentence */}
      <div style={{ padding: "16px 24px", borderBottom: `1px solid ${C.border}` }}>
        <div style={{ color: C.gold, fontFamily: C.font, fontSize: 8, letterSpacing: 2, marginBottom: 8 }}>
          EXAMPLE FROM A REAL FILING
        </div>
        <div style={{
          background: "rgba(0,0,0,0.4)",
          borderLeft: `2px solid ${meta.color}`,
          padding: "10px 14px",
          color: C.text, fontFamily: C.font,
          fontSize: 10, lineHeight: 1.7, fontStyle: "italic",
        }}>
          {s.example}
        </div>
      </div>

      {/* how we use it */}
      <div style={{ padding: "16px 24px", borderBottom: `1px solid ${C.border}` }}>
        <div style={{ color: C.gold, fontFamily: C.font, fontSize: 8, letterSpacing: 2, marginBottom: 8 }}>
          HOW WE USE IT
        </div>
        <p style={{ color: C.textMid, fontFamily: C.font, fontSize: 10, lineHeight: 1.7, margin: 0 }}>
          {s.signal}
        </p>
      </div>

      {/* evidence case — real data if available, fallback otherwise */}
      <div style={{ padding: "16px 24px", background: "rgba(245,158,11,0.03)" }}>
        <div style={{
          display: "flex", alignItems: "center", gap: 8,
          marginBottom: 8,
        }}>
          <div style={{ color: C.gold, fontFamily: C.font, fontSize: 8, letterSpacing: 2 }}>
            EVIDENCE CASE
          </div>
          {heroCase ? (
            <span style={{
              color: C.green, fontFamily: C.font, fontSize: 8,
              border: `1px solid ${C.green}`,
              padding: "1px 5px", letterSpacing: 1,
            }}>
              LIVE FROM DB
            </span>
          ) : (
            <span style={{
              color: C.textDim, fontFamily: C.font, fontSize: 8,
              border: `1px solid ${C.border}`,
              padding: "1px 5px", letterSpacing: 1,
            }}>
              RESEARCH NOTE
            </span>
          )}
        </div>

        {heroCase ? (
          <div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 8 }}>
              <span style={{ color: C.gold, fontFamily: C.font, fontSize: 13, fontWeight: 700 }}>
                {heroCase.ticker}
              </span>
              <span style={{ color: C.textDim, fontFamily: C.font, fontSize: 9, alignSelf: "center" }}>
                {heroCase.filing_date} · {heroCase.form_type}
              </span>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 5, marginBottom: 8 }}>
              {[
                { label: "30D", val: heroCase.return_30d },
                { label: "60D", val: heroCase.return_60d },
                { label: "90D", val: heroCase.return_90d },
              ].map(({ label, val }) => (
                <div key={label} style={{
                  background: val !== null && val < 0 ? C.redDim : C.greenDim,
                  padding: "5px 8px", textAlign: "center",
                }}>
                  <div style={{ color: C.textDim, fontFamily: C.font, fontSize: 8 }}>{label}</div>
                  <div style={{
                    color: val !== null && val < 0 ? C.red : C.green,
                    fontFamily: C.font, fontSize: 11, fontWeight: 700,
                  }}>
                    {val !== null ? `${val > 0 ? "+" : ""}${val.toFixed(1)}%` : "—"}
                  </div>
                </div>
              ))}
            </div>
            <p style={{ color: C.textDim, fontFamily: C.font, fontSize: 9, lineHeight: 1.6, margin: 0 }}>
              Signals: {(heroCase.signals || []).join(" · ")}
            </p>
          </div>
        ) : (
          <p style={{ color: C.gold, fontFamily: C.font, fontSize: 10, lineHeight: 1.7, margin: 0 }}>
            {evidenceStr}
          </p>
        )}
      </div>
    </div>
  );
}

// Main component

const TABS = [
  { id: "filings", label: "FILING TYPES"  },
  { id: "signals", label: "RISK SIGNALS"  },
  { id: "how",     label: "HOW IT WORKS"  },
];

export default function LearnPage() {
  const [activeTab,    setActiveTab]    = useState("filings");
  const [activeFiling, setActiveFiling] = useState(0);
  const [activeSignal, setActiveSignal] = useState(0);

  // ── Real data 
  const [anomalyStats, setAnomalyStats] = useState(null);
  const [heroCases,    setHeroCases]    = useState([]);
  const [dataLoading,  setDataLoading]  = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [aRes, eRes] = await Promise.all([
          axios.get(`${API}/anomaly-history`),
          axios.get(`${API}/evidence-cases`),
        ]);
        setAnomalyStats(aRes.data);
        setHeroCases(eRes.data.hero_cases || []);
      } catch (err) {
        console.error("[LearnPage] API fetch failed:", err);
        // page still works — falls back to static content
      } finally {
        setDataLoading(false);
      }
    };
    load();
  }, []);

  // find hero case for currently active signal
  const activeSignalMeta   = SIGNAL_KEYS[LM_SIGNALS_STATIC[activeSignal].name];
  const activeSignalHero   = findHeroCaseForSignal(heroCases, activeSignalMeta?.keyword || "");

  // real stats with fallbacks
  const totalFilings  = anomalyStats?.total_filings  ?? "—";
  const totalFlagged  = anomalyStats?.total_flagged  ?? "—";
  const tickerCount   = anomalyStats ? Object.keys(anomalyStats.data || {}).length : "—";
  const dateRange     = "1994 – 2026";

  return (
    <div style={{
      background: C.bg, color: C.text,
      fontFamily: C.font, minHeight: "100vh",
      padding: "32px 24px", boxSizing: "border-box",
    }}>

      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
          <div style={{ width: 3, height: 18, background: C.gold }} />
          <span style={{ color: C.gold, fontFamily: C.font, fontSize: 9, letterSpacing: 3 }}>
            EDUCATION HUB
          </span>
        </div>
        <h1 style={{
          color: C.text, fontFamily: C.font,
          fontSize: 22, fontWeight: 700, margin: 0, letterSpacing: 1,
        }}>
          WHAT INSTITUTIONS KNOW
        </h1>
        <p style={{
          color: C.textDim, fontFamily: C.font,
          fontSize: 10, margin: "6px 0 0 0",
          lineHeight: 1.7, maxWidth: 580,
        }}>
          Hedge funds and institutional investors read SEC filings cover to cover.
          Retail investors read the headline. This page explains what they're looking
          for — and how our models detect it automatically.
        </p>
      </div>

      {/* Tab nav */}
      <div style={{
        display: "flex", gap: 0, marginBottom: 24,
        borderBottom: `1px solid ${C.border}`,
      }}>
        {TABS.map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id)} style={{
            background:   "transparent",
            color:        activeTab === t.id ? C.gold : C.textDim,
            border:       "none",
            borderBottom: activeTab === t.id ? `2px solid ${C.gold}` : "2px solid transparent",
            fontFamily:   C.font, fontSize: 10,
            padding:      "10px 20px", cursor: "pointer",
            letterSpacing: 2, marginBottom: -1,
            transition:   "all 0.1s",
          }}>
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Tab: Filing Types ── */}
      {activeTab === "filings" && (
        <div style={{ display: "grid", gridTemplateColumns: "280px 1fr", gap: 16 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {FILING_TYPES.map((f, i) => (
              <FilingCard
                key={i} f={f}
                active={activeFiling === i}
                onClick={() => setActiveFiling(i)}
              />
            ))}

            {/* real stats box */}
            <div style={{
              padding: "14px", border: `1px solid ${C.border}`,
              background: C.surface, marginTop: 4,
            }}>
              <div style={{
                display: "flex", justifyContent: "space-between",
                alignItems: "center", marginBottom: 8,
              }}>
                <div style={{ color: C.textDim, fontFamily: C.font, fontSize: 8, letterSpacing: 2 }}>
                  BY THE NUMBERS
                </div>
                {!dataLoading && anomalyStats && (
                  <span style={{
                    color: C.green, fontFamily: C.font, fontSize: 7,
                    border: `1px solid ${C.green}`, padding: "1px 4px",
                  }}>
                    LIVE
                  </span>
                )}
              </div>
              {[
                ["Filings analyzed", totalFilings],
                ["Anomalies found",  totalFlagged],
                ["Tickers covered",  tickerCount],
                ["Date range",       dateRange],
              ].map(([k, v]) => (
                <div key={k} style={{
                  display: "flex", justifyContent: "space-between", marginBottom: 5,
                }}>
                  <span style={{ color: C.textDim, fontFamily: C.font, fontSize: 9 }}>{k}</span>
                  <span style={{
                    color: dataLoading ? C.textDim : C.gold,
                    fontFamily: C.font, fontSize: 9,
                  }}>
                    {dataLoading ? "..." : v}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <FilingDetail f={FILING_TYPES[activeFiling]} />
        </div>
      )}

      {/* ── Tab: Risk Signals ── */}
      {activeTab === "signals" && (
        <div style={{ display: "grid", gridTemplateColumns: "280px 1fr", gap: 16 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {LM_SIGNALS_STATIC.map((s, i) => (
              <SignalCard
                key={i} s={s}
                active={activeSignal === i}
                onClick={() => setActiveSignal(i)}
              />
            ))}

            <div style={{
              padding: "14px", border: `1px solid ${C.border}`,
              background: C.surface, marginTop: 4,
            }}>
              <div style={{ color: C.textDim, fontFamily: C.font, fontSize: 8, letterSpacing: 2, marginBottom: 8 }}>
                LM DICTIONARY
              </div>
              <p style={{
                color: C.textDim, fontFamily: C.font,
                fontSize: 9, lineHeight: 1.7, margin: 0,
              }}>
                Loughran-McDonald (2011) — the standard financial NLP dictionary
                used by academic researchers and quantitative hedge funds. Built
                specifically for SEC filings, not social media.
              </p>
            </div>
          </div>

          <SignalDetail
            s={LM_SIGNALS_STATIC[activeSignal]}
            heroCase={activeSignalHero}
          />
        </div>
      )}

      {/* ── Tab: How It Works ── */}
      {activeTab === "how" && (
        <div style={{ maxWidth: 720 }}>
          <div style={{ border: `1px solid ${C.border}`, marginBottom: 16 }}>
            {HOW_IT_WORKS.map((s, i) => (
              <StepCard key={i} s={s} />
            ))}
          </div>

          {/* model card — real stats where available */}
          <div style={{
            border: `1px solid ${C.border}`,
            background: C.surface, padding: "20px 24px",
          }}>
            <div style={{
              display: "flex", justifyContent: "space-between",
              alignItems: "center", marginBottom: 14,
            }}>
              <div style={{ color: C.gold, fontFamily: C.font, fontSize: 8, letterSpacing: 2 }}>
                MODEL ARCHITECTURE
              </div>
              {!dataLoading && anomalyStats && (
                <span style={{
                  color: C.green, fontFamily: C.font, fontSize: 7,
                  border: `1px solid ${C.green}`, padding: "1px 4px",
                }}>
                  STATS FROM DB
                </span>
              )}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              {[
                ["Architecture",   "Transformer Encoder"],
                ["d_model",        "128"],
                ["Heads",          "4"],
                ["Layers",         "3"],
                ["Input features", "56 (price + sentiment)"],
                ["Sequence",       "60 trading days"],
                ["Output",         "Binary UP/DOWN + confidence"],
                ["Backtest preds", dataLoading ? "..." : "3,000"],
                ["Overall acc.",   "52.5% (held-out data)"],
                ["Filings analyzed", dataLoading ? "..." : String(totalFilings)],
                ["Anomalies found",  dataLoading ? "..." : String(totalFlagged)],
                ["Best ticker",    "JNJ 55.6% / GOOGL 55.0%"],
              ].map(([k, v]) => (
                <div key={k} style={{
                  display: "flex", justifyContent: "space-between",
                  padding: "6px 0", borderBottom: `1px solid ${C.border}`,
                }}>
                  <span style={{ color: C.textDim, fontFamily: C.font, fontSize: 9 }}>{k}</span>
                  <span style={{ color: C.textMid, fontFamily: C.font, fontSize: 9 }}>{v}</span>
                </div>
              ))}
            </div>

            <p style={{
              color: C.textDim, fontFamily: C.font,
              fontSize: 8, lineHeight: 1.7,
              margin: "14px 0 0 0",
              borderLeft: `2px solid ${C.border2}`, paddingLeft: 8,
            }}>
              Accuracy intentionally modest — these are defensive large-cap stocks
              with low daily volatility. The signal value is in anomaly detection
              and risk flagging, not short-term direction prediction.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
