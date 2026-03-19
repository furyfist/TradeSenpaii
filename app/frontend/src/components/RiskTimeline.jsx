/**
 * RiskTimeline.jsx
 * ─────────────────
 * SEC Filing Risk Signal Timeline — TradeSenpai
 *
 * Shows sentiment score trend over quarters per ticker,
 * annotates flagged filings, highlights hero evidence cases.
 *
 * Place at: app/frontend/src/components/RiskTimeline.jsx
 *
 * Props:
 *   ticker      — string, e.g. "JNJ"
 *   filingData  — array of filing objects from /api/anomaly-history
 *   priceData   — array of {date, close} from /price-history
 *
 * Standalone usage (no props needed):
 *   Uses hardcoded hero case data for demo/README screenshot mode
 */

import { useState, useEffect, useRef } from "react";

// ── Design tokens (matches TradeSenpai design system) ─────────────────────
const C = {
  bg:       "#080808",
  surface:  "#0a0a0a",
  border:   "#1a1a1a",
  border2:  "#222222",
  gold:     "#f59e0b",
  goldDim:  "#92610a",
  goldGlow: "rgba(245,158,11,0.15)",
  red:      "#ef4444",
  redDim:   "rgba(239,68,68,0.15)",
  green:    "#22c55e",
  greenDim: "rgba(34,197,94,0.12)",
  amber:    "#f97316",
  amberDim: "rgba(249,115,22,0.15)",
  text:     "#e5e7eb",
  textDim:  "#6b7280",
  textMid:  "#9ca3af",
  font:     "'IBM Plex Mono', 'Courier New', monospace",
};

// ── Risk level → color ────────────────────────────────────────────────────
const RISK_COLOR = {
  HIGH:     C.red,
  ELEVATED: C.amber,
  WATCH:    C.gold,
  NORMAL:   C.textDim,
};

const RISK_BG = {
  HIGH:     C.redDim,
  ELEVATED: C.amberDim,
  WATCH:    C.goldGlow,
  NORMAL:   "transparent",
};

// ── Hero evidence cases (hardcoded for standalone/demo mode) ──────────────
const HERO_CASES = [
  {
    ticker:      "GOOGL",
    date:        "2022-02-02",
    form:        "10-K",
    signals:     ["Sentiment Score", "Positive Language"],
    return_30d:  -9.57,
    return_60d:  -22.90,
    return_90d:  -28.11,
    description: "Tech selloff. Filing flagged sentiment anomaly 3 months before -28% drawdown.",
  },
  {
    ticker:      "AAPL",
    date:        "2002-05-14",
    form:        "10-Q",
    signals:     ["Negative Language", "Litigation Count"],
    return_30d:  -35.38,
    return_60d:  -40.26,
    return_90d:  -41.94,
    description: "Dot-com bust tail. Litigation spike preceded -42% collapse over 90 days.",
  },
  {
    ticker:      "JNJ",
    date:        "2008-11-04",
    form:        "10-Q",
    signals:     ["Litigation Count", "Sentiment Score"],
    return_30d:  -4.24,
    return_60d:  -6.01,
    return_90d:  -16.68,
    description: "Talc/Risperdal litigation wave. Negative sentiment confirmed crisis in progress.",
  },
];

// ── Mock filing timeline data (replace with real API data in production) ──
const MOCK_FILINGS = {
  JNJ: [
    { date: "2004-11-03", sentiment: 0.83,  risk: "HIGH",     signals: ["Uncertainty","Litigation Count","Sentiment Score","Positive Language"] },
    { date: "2005-05-09", sentiment: 1.12,  risk: "NORMAL",   signals: [] },
    { date: "2005-08-08", sentiment: 0.95,  risk: "NORMAL",   signals: [] },
    { date: "2005-11-07", sentiment: 0.20,  risk: "HIGH",     signals: ["Negative Language","Uncertainty","Litigation Count","Sentiment Score"] },
    { date: "2006-02-27", sentiment: 1.45,  risk: "NORMAL",   signals: [] },
    { date: "2006-05-08", sentiment: 1.38,  risk: "NORMAL",   signals: [] },
    { date: "2006-08-07", sentiment: 1.52,  risk: "NORMAL",   signals: [] },
    { date: "2006-11-06", sentiment: 1.44,  risk: "NORMAL",   signals: [] },
    { date: "2007-02-26", sentiment: 1.67,  risk: "NORMAL",   signals: [] },
    { date: "2007-05-07", sentiment: 1.71,  risk: "NORMAL",   signals: [] },
    { date: "2007-08-06", sentiment: 1.59,  risk: "NORMAL",   signals: [] },
    { date: "2007-11-05", sentiment: 1.63,  risk: "NORMAL",   signals: [] },
    { date: "2008-02-25", sentiment: 1.44,  risk: "NORMAL",   signals: [] },
    { date: "2008-05-07", sentiment: -0.79, risk: "ELEVATED", signals: ["Litigation Count","Sentiment Score"] },
    { date: "2008-08-04", sentiment: 0.31,  risk: "ELEVATED", signals: ["Litigation Count","Sentiment Score"] },
    { date: "2008-11-04", sentiment: 0.18,  risk: "ELEVATED", signals: ["Litigation Count","Sentiment Score"] },
    { date: "2009-02-23", sentiment: 0.92,  risk: "NORMAL",   signals: [] },
    { date: "2009-05-04", sentiment: 1.15,  risk: "NORMAL",   signals: [] },
  ],
  GOOGL: [
    { date: "2018-02-06", sentiment: 1.82,  risk: "NORMAL",   signals: [] },
    { date: "2019-02-05", sentiment: 1.74,  risk: "NORMAL",   signals: [] },
    { date: "2020-02-04", sentiment: 1.66,  risk: "NORMAL",   signals: [] },
    { date: "2021-02-03", sentiment: 0.86,  risk: "ELEVATED", signals: ["Sentiment Score","Positive Language"] },
    { date: "2022-02-02", sentiment: 0.93,  risk: "ELEVATED", signals: ["Sentiment Score","Positive Language"] },
    { date: "2023-02-02", sentiment: 1.55,  risk: "NORMAL",   signals: [] },
    { date: "2024-02-01", sentiment: 1.71,  risk: "NORMAL",   signals: [] },
    { date: "2025-02-05", sentiment: 1.63,  risk: "NORMAL",   signals: [] },
    { date: "2026-02-05", sentiment: 1.22,  risk: "WATCH",    signals: ["Negative Language"] },
  ],
  AAPL: [
    { date: "2001-10-24", sentiment: 0.55,  risk: "NORMAL",   signals: [] },
    { date: "2002-01-23", sentiment: 0.42,  risk: "NORMAL",   signals: [] },
    { date: "2002-05-14", sentiment: -0.29, risk: "ELEVATED", signals: ["Negative Language","Litigation Count"] },
    { date: "2002-08-09", sentiment: -0.30, risk: "HIGH",     signals: ["Negative Language","Litigation Count","Sentiment Score"] },
    { date: "2002-10-23", sentiment: 0.38,  risk: "NORMAL",   signals: [] },
    { date: "2003-01-22", sentiment: 0.89,  risk: "NORMAL",   signals: [] },
    { date: "2003-04-23", sentiment: 1.12,  risk: "NORMAL",   signals: [] },
    { date: "2003-07-16", sentiment: 1.44,  risk: "NORMAL",   signals: [] },
    { date: "2003-10-22", sentiment: 1.38,  risk: "NORMAL",   signals: [] },
  ],
};

// ── Utility: format date ─────────────────────────────────────────────────
const fmt = (dateStr) => {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", { month: "short", year: "numeric" });
};

// ── SVG Chart ─────────────────────────────────────────────────────────────
function SentimentChart({ filings, heroDate }) {
  const W = 680, H = 180;
  const PAD = { top: 20, right: 20, bottom: 30, left: 48 };
  const chartW = W - PAD.left - PAD.right;
  const chartH = H - PAD.top - PAD.bottom;

  if (!filings || filings.length < 2) return null;

  const sentiments  = filings.map(f => f.sentiment);
  const minS        = Math.min(...sentiments) - 0.3;
  const maxS        = Math.max(...sentiments) + 0.3;
  const xStep       = chartW / (filings.length - 1);

  const xOf  = (i)   => PAD.left + i * xStep;
  const yOf  = (val) => PAD.top + chartH - ((val - minS) / (maxS - minS)) * chartH;
  const zero = yOf(0);

  // build smooth path
  const pts = filings.map((f, i) => [xOf(i), yOf(f.sentiment)]);

  const linePath = pts.map((p, i) =>
    i === 0 ? `M ${p[0]},${p[1]}` : `L ${p[0]},${p[1]}`
  ).join(" ");

  const areaPath = [
    `M ${pts[0][0]},${zero}`,
    ...pts.map(p => `L ${p[0]},${p[1]}`),
    `L ${pts[pts.length - 1][0]},${zero}`,
    "Z",
  ].join(" ");

  // y-axis labels
  const yTicks = [minS, 0, maxS].map(v => ({
    val: v,
    y:   yOf(v),
    label: v.toFixed(1),
  }));

  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ display: "block" }}>
      <defs>
        <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor={C.gold} stopOpacity="0.18" />
          <stop offset="100%" stopColor={C.gold} stopOpacity="0.01" />
        </linearGradient>
        <linearGradient id="negGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor={C.red}  stopOpacity="0.01" />
          <stop offset="100%" stopColor={C.red}  stopOpacity="0.18" />
        </linearGradient>
      </defs>

      {/* zero line */}
      {zero > PAD.top && zero < PAD.top + chartH && (
        <line
          x1={PAD.left} y1={zero}
          x2={PAD.left + chartW} y2={zero}
          stroke={C.border2} strokeWidth="1" strokeDasharray="3,4"
        />
      )}

      {/* area fill */}
      <path d={areaPath} fill="url(#areaGrad)" />

      {/* line */}
      <path
        d={linePath}
        fill="none"
        stroke={C.gold}
        strokeWidth="1.5"
        strokeLinejoin="round"
      />

      {/* anomaly markers */}
      {filings.map((f, i) => {
        if (f.risk === "NORMAL") return null;
        const x = xOf(i), y = yOf(f.sentiment);
        const col = RISK_COLOR[f.risk] || C.gold;
        const isHero = heroDate && f.date === heroDate;
        return (
          <g key={i}>
            {isHero && (
              <circle cx={x} cy={y} r="12"
                fill="none" stroke={col} strokeWidth="1"
                opacity="0.3"
              />
            )}
            <circle cx={x} cy={y} r={isHero ? 5 : 3.5}
              fill={col} stroke={C.bg} strokeWidth="1.5"
            />
            {/* vertical drop line to x-axis */}
            <line
              x1={x} y1={y + (isHero ? 6 : 5)}
              x2={x} y2={PAD.top + chartH}
              stroke={col} strokeWidth="1"
              strokeDasharray="2,3" opacity="0.4"
            />
          </g>
        );
      })}

      {/* y-axis ticks */}
      {yTicks.map((t, i) => (
        <g key={i}>
          <line
            x1={PAD.left - 4} y1={t.y}
            x2={PAD.left}      y2={t.y}
            stroke={C.border2} strokeWidth="1"
          />
          <text
            x={PAD.left - 8} y={t.y + 4}
            textAnchor="end"
            fill={C.textDim}
            fontSize="9"
            fontFamily={C.font}
          >
            {t.label}
          </text>
        </g>
      ))}

      {/* x-axis date labels — every 3rd filing */}
      {filings.map((f, i) => {
        if (i % 3 !== 0) return null;
        return (
          <text
            key={i}
            x={xOf(i)} y={H - 4}
            textAnchor="middle"
            fill={C.textDim}
            fontSize="8"
            fontFamily={C.font}
          >
            {fmt(f.date)}
          </text>
        );
      })}

      {/* y-axis label */}
      <text
        x={10} y={PAD.top + chartH / 2}
        textAnchor="middle"
        fill={C.textDim}
        fontSize="8"
        fontFamily={C.font}
        transform={`rotate(-90, 10, ${PAD.top + chartH / 2})`}
      >
        SENTIMENT
      </text>
    </svg>
  );
}

// ── Hero Case Card ─────────────────────────────────────────────────────────
function HeroCaseCard({ c, active, onClick }) {
  const isPos = (v) => v > 0;
  return (
    <div
      onClick={onClick}
      style={{
        background:   active ? "rgba(245,158,11,0.06)" : C.surface,
        border:       `1px solid ${active ? C.gold : C.border}`,
        padding:      "14px 16px",
        cursor:       "pointer",
        transition:   "all 0.15s ease",
        position:     "relative",
        overflow:     "hidden",
      }}
    >
      {active && (
        <div style={{
          position: "absolute", left: 0, top: 0, bottom: 0,
          width: "2px", background: C.gold,
        }} />
      )}

      {/* header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
        <div>
          <span style={{ color: C.gold, fontFamily: C.font, fontSize: 13, fontWeight: 700, letterSpacing: 1 }}>
            {c.ticker}
          </span>
          <span style={{ color: C.textDim, fontFamily: C.font, fontSize: 10, marginLeft: 8 }}>
            {c.date} · {c.form}
          </span>
        </div>
        <span style={{
          background: C.redDim, color: C.red,
          fontFamily: C.font, fontSize: 9,
          padding: "2px 6px", letterSpacing: 1,
          textTransform: "uppercase",
        }}>
          BEARISH
        </span>
      </div>

      {/* signals */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 10 }}>
        {c.signals.map((s, i) => (
          <span key={i} style={{
            background: C.border, color: C.textMid,
            fontFamily: C.font, fontSize: 9,
            padding: "2px 6px", letterSpacing: 0.5,
          }}>
            {s.toUpperCase()}
          </span>
        ))}
      </div>

      {/* description */}
      <p style={{
        color: C.textMid, fontFamily: C.font,
        fontSize: 10, lineHeight: 1.6,
        margin: "0 0 12px 0",
      }}>
        {c.description}
      </p>

      {/* forward returns */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 6 }}>
        {[
          { label: "30D", val: c.return_30d },
          { label: "60D", val: c.return_60d },
          { label: "90D", val: c.return_90d },
        ].map(({ label, val }) => (
          <div key={label} style={{
            background: val < 0 ? C.redDim : "rgba(34,197,94,0.08)",
            padding: "6px 8px",
            textAlign: "center",
          }}>
            <div style={{ color: C.textDim, fontFamily: C.font, fontSize: 8, letterSpacing: 1 }}>
              {label}
            </div>
            <div style={{
              color: val < 0 ? C.red : C.green,
              fontFamily: C.font, fontSize: 12, fontWeight: 700,
            }}>
              {val > 0 ? "+" : ""}{val.toFixed(1)}%
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Filing Row ─────────────────────────────────────────────────────────────
function FilingRow({ f, isHero }) {
  const [open, setOpen] = useState(false);
  const col = RISK_COLOR[f.risk] || C.textDim;

  return (
    <div
      onClick={() => f.risk !== "NORMAL" && setOpen(!open)}
      style={{
        borderBottom: `1px solid ${C.border}`,
        background: isHero ? "rgba(245,158,11,0.04)" : "transparent",
        cursor: f.risk !== "NORMAL" ? "pointer" : "default",
        transition: "background 0.1s",
      }}
    >
      <div style={{
        display: "grid",
        gridTemplateColumns: "100px 50px 80px 1fr",
        gap: 8,
        padding: "8px 12px",
        alignItems: "center",
      }}>
        <span style={{ color: C.textMid, fontFamily: C.font, fontSize: 10 }}>
          {f.date}
        </span>
        <span style={{ color: C.textDim, fontFamily: C.font, fontSize: 10 }}>
          {f.form_type || f.form}
        </span>
        <span style={{
          color: col,
          fontFamily: C.font, fontSize: 9,
          background: RISK_BG[f.risk],
          padding: "2px 6px",
          display: "inline-block",
          letterSpacing: 0.5,
        }}>
          {f.risk}
        </span>
        <span style={{ color: C.textDim, fontFamily: C.font, fontSize: 9 }}>
          {f.signals && f.signals.length > 0
            ? f.signals.join(" · ")
            : "—"}
        </span>
      </div>

      {open && f.signals && f.signals.length > 0 && (
        <div style={{
          padding: "8px 12px 10px 12px",
          borderTop: `1px solid ${C.border}`,
          background: "rgba(0,0,0,0.3)",
        }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {f.signals.map((s, i) => (
              <span key={i} style={{
                color: col, fontFamily: C.font, fontSize: 9,
                border: `1px solid ${col}`,
                padding: "2px 8px", letterSpacing: 0.5, opacity: 0.8,
              }}>
                ⚠ {s.toUpperCase()}
              </span>
            ))}
          </div>
          <p style={{
            color: C.textDim, fontFamily: C.font,
            fontSize: 9, marginTop: 6, lineHeight: 1.6,
          }}>
            Click signal markers on the chart above to see price impact windows.
          </p>
        </div>
      )}
    </div>
  );
}

// ── Ticker Selector ────────────────────────────────────────────────────────
function TickerTab({ label, active, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        background:   active ? C.gold : "transparent",
        color:        active ? C.bg   : C.textDim,
        border:       `1px solid ${active ? C.gold : C.border}`,
        fontFamily:   C.font,
        fontSize:     11,
        padding:      "5px 14px",
        cursor:       "pointer",
        letterSpacing: 1,
        transition:   "all 0.1s",
        fontWeight:   active ? 700 : 400,
      }}
    >
      {label}
    </button>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────
export default function RiskTimeline({ filingData, ticker: propTicker }) {
  const TICKERS = ["JNJ", "GOOGL", "AAPL"];
  const [activeTicker, setActiveTicker]   = useState(propTicker || "JNJ");
  const [activeHero,   setActiveHero]     = useState(0);
  const [showAll,      setShowAll]        = useState(false);

  const filings   = filingData?.[activeTicker] || MOCK_FILINGS[activeTicker] || [];
  const heroCase  = HERO_CASES[activeHero];
  const heroDate  = heroCase?.ticker === activeTicker ? heroCase.date : null;

  const visibleFilings = showAll
    ? filings
    : filings.filter(f => f.risk !== "NORMAL").slice(-12);

  return (
    <div style={{
      background:  C.bg,
      color:       C.text,
      fontFamily:  C.font,
      minHeight:   "100vh",
      padding:     "32px 24px",
      boxSizing:   "border-box",
    }}>

      {/* ── Header ── */}
      <div style={{ marginBottom: 28 }}>
        <div style={{
          display: "flex", alignItems: "center",
          gap: 10, marginBottom: 6,
        }}>
          <div style={{
            width: 3, height: 18,
            background: C.gold,
          }} />
          <span style={{
            color: C.gold, fontFamily: C.font,
            fontSize: 10, letterSpacing: 3,
            textTransform: "uppercase",
          }}>
            SEC FILING RISK INTELLIGENCE
          </span>
        </div>
        <h1 style={{
          color: C.text, fontFamily: C.font,
          fontSize: 22, fontWeight: 700,
          margin: 0, letterSpacing: 1,
        }}>
          RISK SIGNAL TIMELINE
        </h1>
        <p style={{
          color: C.textDim, fontFamily: C.font,
          fontSize: 10, margin: "6px 0 0 0",
          lineHeight: 1.7, maxWidth: 520,
        }}>
          Linguistic anomaly detection on 10-K/10-Q filings.
          Flags when a company's language deviates {">"}1.5σ from its own historical baseline.
          Not a trading signal — a structural risk early warning system.
        </p>
      </div>

      <div style={{
        display: "grid",
        gridTemplateColumns: "1fr 320px",
        gap: 16,
        alignItems: "start",
      }}>

        {/* ── Left: Chart Panel ── */}
        <div>

          {/* Ticker tabs */}
          <div style={{ display: "flex", gap: 4, marginBottom: 12 }}>
            {TICKERS.map(t => (
              <TickerTab
                key={t}
                label={t}
                active={activeTicker === t}
                onClick={() => setActiveTicker(t)}
              />
            ))}
          </div>

          {/* Chart container */}
          <div style={{
            border: `1px solid ${C.border}`,
            background: C.surface,
            padding: "16px 12px 8px",
            marginBottom: 1,
          }}>
            {/* chart header */}
            <div style={{
              display: "flex", justifyContent: "space-between",
              alignItems: "center", marginBottom: 10,
            }}>
              <div>
                <span style={{
                  color: C.gold, fontFamily: C.font,
                  fontSize: 11, letterSpacing: 2,
                }}>
                  {activeTicker}
                </span>
                <span style={{
                  color: C.textDim, fontFamily: C.font,
                  fontSize: 9, marginLeft: 8,
                }}>
                  LM SENTIMENT SCORE · {filings.length} FILINGS
                </span>
              </div>
              {/* legend */}
              <div style={{ display: "flex", gap: 12 }}>
                {[
                  { label: "HIGH",     col: C.red   },
                  { label: "ELEVATED", col: C.amber  },
                  { label: "WATCH",    col: C.gold   },
                ].map(({ label, col }) => (
                  <div key={label} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                    <div style={{
                      width: 6, height: 6,
                      borderRadius: "50%", background: col,
                    }} />
                    <span style={{ color: C.textDim, fontFamily: C.font, fontSize: 8 }}>
                      {label}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <SentimentChart filings={filings} heroDate={heroDate} />
          </div>

          {/* stats bar */}
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            border: `1px solid ${C.border}`,
            borderTop: "none",
            marginBottom: 16,
          }}>
            {[
              {
                label: "FILINGS",
                val:   filings.length,
                col:   C.textMid,
              },
              {
                label: "FLAGGED",
                val:   filings.filter(f => f.risk !== "NORMAL").length,
                col:   C.gold,
              },
              {
                label: "HIGH RISK",
                val:   filings.filter(f => f.risk === "HIGH").length,
                col:   C.red,
              },
              {
                label: "FLAG RATE",
                val:   filings.length
                  ? (filings.filter(f => f.risk !== "NORMAL").length / filings.length * 100).toFixed(0) + "%"
                  : "—",
                col:   C.amber,
              },
            ].map(({ label, val, col }) => (
              <div key={label} style={{
                padding: "10px 12px",
                borderRight: `1px solid ${C.border}`,
                background: C.surface,
              }}>
                <div style={{ color: C.textDim, fontFamily: C.font, fontSize: 8, letterSpacing: 1 }}>
                  {label}
                </div>
                <div style={{ color: col, fontFamily: C.font, fontSize: 18, fontWeight: 700 }}>
                  {val}
                </div>
              </div>
            ))}
          </div>

          {/* Filing list */}
          <div style={{ border: `1px solid ${C.border}` }}>
            {/* list header */}
            <div style={{
              display: "grid",
              gridTemplateColumns: "100px 50px 80px 1fr",
              gap: 8,
              padding: "6px 12px",
              background: C.surface,
              borderBottom: `1px solid ${C.border}`,
            }}>
              {["DATE", "FORM", "RISK", "SIGNALS TRIGGERED"].map(h => (
                <span key={h} style={{
                  color: C.textDim, fontFamily: C.font,
                  fontSize: 8, letterSpacing: 1,
                }}>
                  {h}
                </span>
              ))}
            </div>

            {visibleFilings.length === 0 ? (
              <div style={{ padding: "20px 12px", color: C.textDim, fontFamily: C.font, fontSize: 10 }}>
                No flagged filings found for {activeTicker}.
              </div>
            ) : (
              visibleFilings.map((f, i) => (
                <FilingRow
                  key={i}
                  f={f}
                  isHero={heroDate && f.date === heroDate}
                />
              ))
            )}

            {/* toggle */}
            <div
              onClick={() => setShowAll(!showAll)}
              style={{
                padding: "8px 12px",
                background: C.surface,
                borderTop: `1px solid ${C.border}`,
                cursor: "pointer",
                color: C.textDim,
                fontFamily: C.font,
                fontSize: 9,
                letterSpacing: 1,
                textAlign: "center",
              }}
            >
              {showAll
                ? "▲ SHOW FLAGGED ONLY"
                : `▼ SHOW ALL ${filings.length} FILINGS`}
            </div>
          </div>
        </div>

        {/* ── Right: Hero Cases ── */}
        <div>
          <div style={{
            color: C.textDim, fontFamily: C.font,
            fontSize: 8, letterSpacing: 2,
            marginBottom: 10,
            paddingBottom: 8,
            borderBottom: `1px solid ${C.border}`,
          }}>
            FILING WARNED US EARLY — TOP EVIDENCE CASES
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {HERO_CASES.map((c, i) => (
              <HeroCaseCard
                key={i}
                c={c}
                active={activeHero === i}
                onClick={() => {
                  setActiveHero(i);
                  setActiveTicker(c.ticker);
                }}
              />
            ))}
          </div>

          {/* methodology note */}
          <div style={{
            marginTop: 16,
            padding: "12px 14px",
            border: `1px solid ${C.border}`,
            background: C.surface,
          }}>
            <div style={{
              color: C.gold, fontFamily: C.font,
              fontSize: 8, letterSpacing: 2, marginBottom: 8,
            }}>
              METHODOLOGY
            </div>
            {[
              ["Dictionary", "Loughran-McDonald Financial"],
              ["Threshold", ">1.5σ from ticker's own history"],
              ["Window",    "8 prior filings as baseline"],
              ["Scope",     "10-K + 10-Q only, ≥500 words"],
              ["Filings",   "425 analyzed across 6 tickers"],
            ].map(([k, v]) => (
              <div key={k} style={{
                display: "flex", justifyContent: "space-between",
                marginBottom: 5,
              }}>
                <span style={{ color: C.textDim, fontFamily: C.font, fontSize: 9 }}>
                  {k}
                </span>
                <span style={{ color: C.textMid, fontFamily: C.font, fontSize: 9, textAlign: "right", maxWidth: 140 }}>
                  {v}
                </span>
              </div>
            ))}
          </div>

          {/* disclaimer */}
          <p style={{
            color: C.textDim, fontFamily: C.font,
            fontSize: 8, lineHeight: 1.7,
            marginTop: 12,
            borderLeft: `2px solid ${C.border2}`,
            paddingLeft: 8,
          }}>
            Signal accuracy on 30-day forward returns: 44.7% overall.
            These are structural risk indicators, not short-term trading signals.
            High-impact cases (90d window) show stronger directional alignment.
          </p>
        </div>
      </div>
    </div>
  );
}