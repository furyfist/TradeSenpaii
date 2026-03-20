/**
 * PredictionChart.jsx
 * Direction calls overlaid on actual price chart.
 * ▲ green = model called UP correctly
 * ▼ red   = model called DOWN correctly  
 * ▲ dim   = model called UP incorrectly
 * ▼ dim   = model called DOWN incorrectly
 *
 * Place at: app/frontend/src/components/PredictionChart.jsx
 */

import { useState, useEffect, useRef } from "react";
import axios from "axios";

const API  = import.meta.env.VITE_API_URL;
const FONT = "'IBM Plex Mono', 'Courier New', monospace";

const C = {
  bg:      "#080808", surface: "#0a0a0a",
  border:  "#1a1a1a", border2: "#222222",
  gold:    "#f59e0b", goldGlow: "rgba(245,158,11,0.10)",
  red:     "#ef4444", redDim:   "rgba(239,68,68,0.12)",
  green:   "#22c55e", greenDim: "rgba(34,197,94,0.10)",
  amber:   "#f97316",
  text:    "#e5e7eb", textDim:  "#6b7280", textMid: "#9ca3af",
};

const TICKERS = ["KO", "JNJ", "PG", "WMT", "AAPL", "GOOGL"];

const TICKER_NAME = {
  KO: "Coca-Cola", JNJ: "Johnson & Johnson", PG: "Procter & Gamble",
  WMT: "Walmart",  AAPL: "Apple",            GOOGL: "Alphabet",
};

// ── SVG Chart ──────────────────────────────────────────────────────────────
function Chart({ predictions, showWrong, confidenceFilter }) {
  const W = 900, H = 300;
  const PAD = { top: 20, right: 20, bottom: 36, left: 64 };
  const cW  = W - PAD.left - PAD.right;
  const cH  = H - PAD.top  - PAD.bottom;

  // filter by confidence
  const filtered = predictions.filter(p =>
    p.close !== null &&
    p.close !== undefined &&
    p.confidence >= confidenceFilter
  );

  if (filtered.length < 2) {
    return (
      <div style={{
        height: H, display: "flex", alignItems: "center",
        justifyContent: "center", color: C.textDim,
        fontFamily: FONT, fontSize: 10,
      }}>
        NOT ENOUGH DATA FOR SELECTED FILTER
      </div>
    );
  }

  const prices  = filtered.map(p => p.close);
  const minP    = Math.min(...prices) * 0.98;
  const maxP    = Math.max(...prices) * 1.02;
  const xStep   = cW / (filtered.length - 1);

  const xOf = (i) => PAD.left + i * xStep;
  const yOf = (v) => PAD.top + cH - ((v - minP) / (maxP - minP)) * cH;

  // price line path
  const linePath = filtered.map((p, i) =>
    i === 0
      ? `M${xOf(i).toFixed(1)},${yOf(p.close).toFixed(1)}`
      : `L${xOf(i).toFixed(1)},${yOf(p.close).toFixed(1)}`
  ).join(" ");

  // area path
  const areaPath = [
    `M${PAD.left},${PAD.top + cH}`,
    ...filtered.map((p, i) => `L${xOf(i).toFixed(1)},${yOf(p.close).toFixed(1)}`),
    `L${xOf(filtered.length-1).toFixed(1)},${PAD.top + cH}`,
    "Z",
  ].join(" ");

  // y-axis ticks
  const yTicks = 5;
  const yTickVals = Array.from({ length: yTicks }, (_, i) =>
    minP + (maxP - minP) * (i / (yTicks - 1))
  );

  // x-axis labels — evenly spaced dates
  const xLabelCount = 8;
  const xLabelStep  = Math.floor(filtered.length / xLabelCount);
  const xLabelIdxs  = new Set(
    Array.from({ length: xLabelCount }, (_, i) => i * xLabelStep)
  );

  const fmtDate = (d) => {
    const dt = new Date(d);
    return `${dt.toLocaleString("en-US", { month: "short" })} '${String(dt.getFullYear()).slice(2)}`;
  };

  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ display: "block" }}>
      <defs>
        <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor={C.gold} stopOpacity="0.12" />
          <stop offset="100%" stopColor={C.gold} stopOpacity="0.01" />
        </linearGradient>
      </defs>

      {/* grid */}
      {yTickVals.map((v, i) => (
        <line key={i}
          x1={PAD.left} y1={yOf(v)}
          x2={PAD.left + cW} y2={yOf(v)}
          stroke={C.border} strokeWidth="1"
        />
      ))}

      {/* area + price line */}
      <path d={areaPath} fill="url(#priceGrad)" />
      <path d={linePath} fill="none"
        stroke={C.gold} strokeWidth="1.5" strokeLinejoin="round" />

      {/* prediction markers */}
      {filtered.map((p, i) => {
        const x       = xOf(i);
        const y       = yOf(p.close);
        const isUp    = p.prediction === "UP";
        const correct = p.correct === 1;

        if (!showWrong && !correct) return null;

        const col     = correct
          ? (isUp ? C.green : C.red)
          : "rgba(100,100,100,0.4)";
        const symbol  = isUp ? "▲" : "▼";
        const size    = correct ? 7 : 5;
        const yOffset = isUp ? -(size + 4) : (size + 4);

        return (
          <text
            key={i}
            x={x} y={y + yOffset}
            textAnchor="middle"
            fill={col}
            fontSize={size * 1.8}
            fontFamily={FONT}
            opacity={correct ? 1 : 0.35}
          >
            {symbol}
          </text>
        );
      })}

      {/* y-axis labels */}
      {yTickVals.map((v, i) => (
        <text key={i}
          x={PAD.left - 8} y={yOf(v) + 4}
          textAnchor="end" fill={C.textDim}
          fontSize="9" fontFamily={FONT}>
          ${v.toFixed(0)}
        </text>
      ))}

      {/* x-axis labels */}
      {filtered.map((p, i) => {
        if (!xLabelIdxs.has(i)) return null;
        return (
          <text key={i}
            x={xOf(i)} y={H - 4}
            textAnchor="middle" fill={C.textDim}
            fontSize="8" fontFamily={FONT}>
            {fmtDate(p.date)}
          </text>
        );
      })}

      {/* y-axis label */}
      <text
        x={14} y={PAD.top + cH / 2}
        textAnchor="middle" fill={C.textDim}
        fontSize="8" fontFamily={FONT}
        transform={`rotate(-90,14,${PAD.top + cH / 2})`}>
        PRICE (USD)
      </text>
    </svg>
  );
}

// ── Rolling accuracy chart ─────────────────────────────────────────────────
function RollingAccuracyChart({ predictions, window = 30 }) {
  const W = 900, H = 100;
  const PAD = { top: 10, right: 20, bottom: 24, left: 64 };
  const cW  = W - PAD.left - PAD.right;
  const cH  = H - PAD.top  - PAD.bottom;

  const valid = predictions.filter(p => p.correct !== null);
  if (valid.length < window + 1) return null;

  // compute rolling accuracy
  const rolling = valid.map((p, i) => {
    if (i < window) return null;
    const slice = valid.slice(i - window, i);
    const acc   = slice.reduce((s, x) => s + x.correct, 0) / window * 100;
    return { date: p.date, acc };
  }).filter(Boolean);

  if (rolling.length < 2) return null;

  const xStep = cW / (rolling.length - 1);
  const xOf   = (i) => PAD.left + i * xStep;
  const yOf   = (v) => PAD.top + cH - ((v - 40) / 30) * cH; // 40-70% range

  const linePath = rolling.map((p, i) =>
    i === 0
      ? `M${xOf(i).toFixed(1)},${yOf(p.acc).toFixed(1)}`
      : `L${xOf(i).toFixed(1)},${yOf(p.acc).toFixed(1)}`
  ).join(" ");

  // 50% baseline
  const baseline = yOf(50);

  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ display: "block" }}>
      {/* 50% line */}
      <line
        x1={PAD.left} y1={baseline}
        x2={PAD.left + cW} y2={baseline}
        stroke={C.border2} strokeWidth="1" strokeDasharray="4,4"
      />
      <text x={PAD.left - 8} y={baseline + 4}
        textAnchor="end" fill={C.textDim}
        fontSize="8" fontFamily={FONT}>
        50%
      </text>

      {/* rolling line */}
      <path d={linePath} fill="none"
        stroke={C.amber} strokeWidth="1.5" strokeLinejoin="round" />

      {/* label */}
      <text x={14} y={PAD.top + cH / 2}
        textAnchor="middle" fill={C.textDim}
        fontSize="7" fontFamily={FONT}
        transform={`rotate(-90,14,${PAD.top + cH / 2})`}>
        {window}D ACC
      </text>
    </svg>
  );
}

// ── Stats row ──────────────────────────────────────────────────────────────
function StatsRow({ stats, predictions, confidenceFilter }) {
  if (!stats) return null;

  // accuracy by confidence bucket
  const buckets = [
    { lo: 0.50, hi: 0.55, label: "0.50-0.55" },
    { lo: 0.55, hi: 0.60, label: "0.55-0.60" },
    { lo: 0.60, hi: 0.65, label: "0.60-0.65" },
    { lo: 0.65, hi: 1.01, label: "0.65+"     },
  ];

  const bucketStats = buckets.map(b => {
    const subset  = predictions.filter(
      p => p.confidence >= b.lo && p.confidence < b.hi && p.correct !== null
    );
    const acc     = subset.length
      ? (subset.reduce((s, p) => s + p.correct, 0) / subset.length * 100).toFixed(1)
      : null;
    return { ...b, count: subset.length, acc };
  }).filter(b => b.count > 0);

  return (
    <div style={{ display: "flex", gap: 0, marginBottom: 16 }}>
      {/* main stats */}
      {[
        { label: "PREDICTIONS", val: stats.total,           col: C.textMid },
        { label: "CORRECT",     val: stats.correct,         col: C.green   },
        { label: "ACCURACY",    val: `${stats.accuracy}%`,  col: C.gold    },
        { label: "DATE FROM",   val: stats.date_from,       col: C.textDim },
        { label: "DATE TO",     val: stats.date_to,         col: C.textDim },
      ].map(({ label, val, col }, i, arr) => (
        <div key={label} style={{
          padding: "10px 16px",
          borderRight: `1px solid ${C.border}`,
          border: `1px solid ${C.border}`,
          borderLeft: i === 0 ? `1px solid ${C.border}` : "none",
          background: C.surface, flex: 1,
        }}>
          <div style={{ color: C.textDim, fontFamily: FONT, fontSize: 8, letterSpacing: 1 }}>
            {label}
          </div>
          <div style={{ color: col, fontFamily: FONT, fontSize: 16, fontWeight: 700, lineHeight: 1.3 }}>
            {val}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────
export default function PredictionChart() {
  const [ticker,            setTicker]            = useState("AAPL");
  const [data,              setData]              = useState(null);
  const [loading,           setLoading]           = useState(true);
  const [error,             setError]             = useState(null);
  const [showWrong,         setShowWrong]         = useState(true);
  const [confidenceFilter,  setConfidenceFilter]  = useState(0.50);
  const [hoveredPoint,      setHoveredPoint]      = useState(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      setData(null);
      try {
        const r = await axios.get(`${API}/prediction-history?ticker=${ticker}`);
        setData(r.data);
      } catch {
        setError("Failed to load prediction history. Is the backend running?");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [ticker]);

  const predictions = data?.predictions || [];

  // compute UP/DOWN call counts
  const upCalls   = predictions.filter(p => p.prediction === "UP").length;
  const downCalls = predictions.filter(p => p.prediction === "DOWN").length;
  const upAcc     = predictions.filter(p => p.prediction === "UP" && p.correct === 1).length;
  const downAcc   = predictions.filter(p => p.prediction === "DOWN" && p.correct === 1).length;

  return (
    <div style={{
      background: C.bg, color: C.text,
      fontFamily: FONT, minHeight: "100vh",
      padding: "32px 24px", boxSizing: "border-box",
    }}>

      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
          <div style={{ width: 3, height: 18, background: C.gold }} />
          <span style={{ color: C.gold, fontFamily: FONT, fontSize: 9, letterSpacing: 3 }}>
            BACKTEST RESULTS
          </span>
        </div>
        <h1 style={{
          color: C.text, fontFamily: FONT,
          fontSize: 22, fontWeight: 700, margin: 0, letterSpacing: 1,
        }}>
          PREDICTION vs REALITY
        </h1>
        <p style={{
          color: C.textDim, fontFamily: FONT,
          fontSize: 10, margin: "6px 0 0 0", lineHeight: 1.7, maxWidth: 600,
        }}>
          Transformer direction calls overlaid on actual price.
          ▲ = model predicted UP · ▼ = model predicted DOWN ·
          Bright = correct · Dim = wrong.
          500 trading days per ticker, Feb 2024 → Mar 2026.
        </p>
      </div>

      {/* Ticker tabs */}
      <div style={{ display: "flex", gap: 4, marginBottom: 20, flexWrap: "wrap" }}>
        {TICKERS.map(t => (
          <button key={t} onClick={() => setTicker(t)} style={{
            background:    ticker === t ? C.gold : "transparent",
            color:         ticker === t ? C.bg   : C.textDim,
            border:        `1px solid ${ticker === t ? C.gold : C.border}`,
            fontFamily:    FONT, fontSize: 10,
            padding:       "5px 16px", cursor: "pointer",
            letterSpacing: 1, fontWeight: ticker === t ? 700 : 400,
            transition:    "all 0.1s",
          }}>
            {t}
          </button>
        ))}
      </div>

      {loading && (
        <div style={{
          height: 400, display: "flex", alignItems: "center",
          justifyContent: "center", border: `1px solid ${C.border}`,
          color: C.textDim, fontFamily: FONT, fontSize: 11, letterSpacing: 2,
        }}>
          LOADING {ticker} PREDICTIONS...
        </div>
      )}

      {error && !loading && (
        <div style={{
          padding: "20px", border: `1px solid ${C.red}`,
          color: C.red, fontFamily: FONT, fontSize: 11,
        }}>
          {error}
        </div>
      )}

      {data && !loading && (
        <>
          {/* Stats row */}
          <StatsRow
            stats={data.stats}
            predictions={predictions}
            confidenceFilter={confidenceFilter}
          />

          {/* Controls */}
          <div style={{
            display: "flex", gap: 12, alignItems: "center",
            marginBottom: 8, padding: "8px 12px",
            border: `1px solid ${C.border}`,
            background: C.surface,
          }}>
            <span style={{ color: C.textDim, fontFamily: FONT, fontSize: 9, letterSpacing: 1 }}>
              FILTERS
            </span>

            {/* confidence filter */}
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ color: C.textDim, fontFamily: FONT, fontSize: 9 }}>
                MIN CONFIDENCE
              </span>
              {[0.50, 0.55, 0.60, 0.65].map(v => (
                <button key={v} onClick={() => setConfidenceFilter(v)} style={{
                  background:  confidenceFilter === v ? C.gold : "transparent",
                  color:       confidenceFilter === v ? C.bg   : C.textDim,
                  border:      `1px solid ${confidenceFilter === v ? C.gold : C.border}`,
                  fontFamily:  FONT, fontSize: 8,
                  padding:     "2px 8px", cursor: "pointer",
                  letterSpacing: 0.5,
                }}>
                  {v.toFixed(2)}+
                </button>
              ))}
            </div>

            <div style={{ width: 1, height: 16, background: C.border }} />

            {/* show wrong toggle */}
            <button onClick={() => setShowWrong(!showWrong)} style={{
              background:  showWrong ? "rgba(239,68,68,0.1)" : "transparent",
              color:       showWrong ? C.red : C.textDim,
              border:      `1px solid ${showWrong ? C.red : C.border}`,
              fontFamily:  FONT, fontSize: 8,
              padding:     "2px 10px", cursor: "pointer",
              letterSpacing: 0.5,
            }}>
              {showWrong ? "SHOWING WRONG" : "HIDING WRONG"}
            </button>

            {/* legend */}
            <div style={{ marginLeft: "auto", display: "flex", gap: 12, alignItems: "center" }}>
              {[
                { col: C.green, label: "UP correct"   },
                { col: C.red,   label: "DOWN correct"  },
                { col: "rgba(100,100,100,0.5)", label: "wrong call" },
              ].map(({ col, label }) => (
                <div key={label} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <div style={{ width: 8, height: 8, background: col, borderRadius: "50%" }} />
                  <span style={{ color: C.textDim, fontFamily: FONT, fontSize: 8 }}>{label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Main price chart */}
          <div style={{
            border: `1px solid ${C.border}`,
            background: C.surface,
            padding: "16px 12px 8px",
            marginBottom: 1,
          }}>
            <div style={{
              display: "flex", justifyContent: "space-between",
              alignItems: "center", marginBottom: 10,
            }}>
              <div>
                <span style={{ color: C.gold, fontFamily: FONT, fontSize: 11, letterSpacing: 2 }}>
                  {ticker}
                </span>
                <span style={{ color: C.textDim, fontFamily: FONT, fontSize: 9, marginLeft: 8 }}>
                  {TICKER_NAME[ticker]} · ACTUAL PRICE + DIRECTION CALLS
                </span>
              </div>
              <span style={{ color: C.textDim, fontFamily: FONT, fontSize: 9 }}>
                {predictions.filter(p => p.confidence >= confidenceFilter).length} predictions shown
              </span>
            </div>
            <Chart
              predictions={predictions}
              showWrong={showWrong}
              confidenceFilter={confidenceFilter}
            />
          </div>

          {/* Rolling accuracy chart */}
          <div style={{
            border: `1px solid ${C.border}`,
            borderTop: "none",
            background: C.surface,
            padding: "8px 12px",
            marginBottom: 16,
          }}>
            <div style={{ color: C.textDim, fontFamily: FONT, fontSize: 8, letterSpacing: 1, marginBottom: 4 }}>
              30-DAY ROLLING ACCURACY
            </div>
            <RollingAccuracyChart predictions={predictions} window={30} />
          </div>

          {/* UP vs DOWN breakdown */}
          <div style={{
            display: "grid", gridTemplateColumns: "1fr 1fr",
            gap: 8, marginBottom: 16,
          }}>
            {[
              {
                label: "UP CALLS",
                total: upCalls,
                correct: upAcc,
                col: C.green,
                bg: C.greenDim,
              },
              {
                label: "DOWN CALLS",
                total: downCalls,
                correct: downAcc,
                col: C.red,
                bg: C.redDim,
              },
            ].map(({ label, total, correct, col, bg }) => {
              const acc = total ? (correct / total * 100).toFixed(1) : 0;
              const pct = total ? (correct / total * 100) : 0;
              return (
                <div key={label} style={{
                  padding: "14px 16px",
                  border: `1px solid ${C.border}`,
                  background: C.surface,
                }}>
                  <div style={{ color: C.textDim, fontFamily: FONT, fontSize: 8, letterSpacing: 1, marginBottom: 8 }}>
                    {label}
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                    <span style={{ color: col, fontFamily: FONT, fontSize: 22, fontWeight: 700 }}>
                      {acc}%
                    </span>
                    <span style={{ color: C.textDim, fontFamily: FONT, fontSize: 9, alignSelf: "flex-end" }}>
                      {correct}/{total} correct
                    </span>
                  </div>
                  {/* progress bar */}
                  <div style={{ background: C.border, height: 3 }}>
                    <div style={{
                      background: col, height: 3,
                      width: `${pct}%`, transition: "width 0.5s",
                    }} />
                  </div>
                </div>
              );
            })}
          </div>

          {/* Raw predictions table — last 20 */}
          <div style={{ border: `1px solid ${C.border}` }}>
            <div style={{
              padding: "8px 14px",
              background: C.surface,
              borderBottom: `1px solid ${C.border}`,
              display: "flex", justifyContent: "space-between",
            }}>
              <span style={{ color: C.textDim, fontFamily: FONT, fontSize: 8, letterSpacing: 2 }}>
                RECENT PREDICTIONS (LAST 20)
              </span>
              <span style={{ color: C.textDim, fontFamily: FONT, fontSize: 8 }}>
                {ticker} · {data.stats.total} total
              </span>
            </div>

            {/* table header */}
            <div style={{
              display: "grid",
              gridTemplateColumns: "110px 80px 80px 80px 80px 80px 60px",
              gap: 6, padding: "6px 14px",
              background: "#090909",
              borderBottom: `1px solid ${C.border}`,
            }}>
              {["DATE","PREDICTED","ACTUAL","RETURN","CONFIDENCE","PRICE","CORRECT"].map(h => (
                <span key={h} style={{ color: C.textDim, fontFamily: FONT, fontSize: 8, letterSpacing: 1 }}>
                  {h}
                </span>
              ))}
            </div>

            {[...predictions].reverse().slice(0, 20).map((p, i) => {
              const correct = p.correct === 1;
              const retCol  = p.actual_return > 0 ? C.green : C.red;
              return (
                <div key={i} style={{
                  display: "grid",
                  gridTemplateColumns: "110px 80px 80px 80px 80px 80px 60px",
                  gap: 6, padding: "7px 14px",
                  borderBottom: `1px solid ${C.border}`,
                  background: correct ? "rgba(34,197,94,0.02)" : "rgba(239,68,68,0.02)",
                }}>
                  <span style={{ color: C.textMid,  fontFamily: FONT, fontSize: 9 }}>{p.date}</span>
                  <span style={{
                    color: p.prediction === "UP" ? C.green : C.red,
                    fontFamily: FONT, fontSize: 9, fontWeight: 700,
                  }}>
                    {p.prediction === "UP" ? "▲ UP" : "▼ DOWN"}
                  </span>
                  <span style={{
                    color: p.actual_direction === "UP" ? C.green : C.red,
                    fontFamily: FONT, fontSize: 9,
                  }}>
                    {p.actual_direction === "UP" ? "▲ UP" : "▼ DOWN"}
                  </span>
                  <span style={{ color: retCol, fontFamily: FONT, fontSize: 9 }}>
                    {p.actual_return !== null
                      ? `${p.actual_return > 0 ? "+" : ""}${p.actual_return.toFixed(2)}%`
                      : "—"}
                  </span>
                  <span style={{ color: C.textDim, fontFamily: FONT, fontSize: 9 }}>
                    {(p.confidence * 100).toFixed(1)}%
                  </span>
                  <span style={{ color: C.textDim, fontFamily: FONT, fontSize: 9 }}>
                    {p.close ? `$${p.close.toFixed(2)}` : "—"}
                  </span>
                  <span style={{
                    color: correct ? C.green : C.red,
                    fontFamily: FONT, fontSize: 9, fontWeight: 700,
                  }}>
                    {correct ? "✓" : "✗"}
                  </span>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}