
import { useState, useEffect } from "react";
import axios from "axios";

const API = import.meta.env.VITE_API_URL;

// ── Design tokens 
const C = {
  bg:       "#080808",
  surface:  "#0a0a0a",
  border:   "#1a1a1a",
  border2:  "#222222",
  gold:     "#f59e0b",
  goldGlow: "rgba(245,158,11,0.12)",
  red:      "#ef4444",
  redDim:   "rgba(239,68,68,0.12)",
  green:    "#22c55e",
  amber:    "#f97316",
  amberDim: "rgba(249,115,22,0.12)",
  text:     "#e5e7eb",
  textDim:  "#6b7280",
  textMid:  "#9ca3af",
  font:     "'IBM Plex Mono', 'Courier New', monospace",
};

const RISK_COLOR = { HIGH: C.red, ELEVATED: C.amber, WATCH: C.gold, NORMAL: C.textDim };
const RISK_BG    = { HIGH: C.redDim, ELEVATED: C.amberDim, WATCH: C.goldGlow, NORMAL: "transparent" };

const TICKERS     = ["KO", "JNJ", "PG", "WMT", "AAPL", "GOOGL"];
const TICKER_NAME = {
  KO: "Coca-Cola", JNJ: "Johnson & Johnson", PG: "Procter & Gamble",
  WMT: "Walmart",  AAPL: "Apple",            GOOGL: "Alphabet",
};

const fmt = (d) =>
  new Date(d).toLocaleDateString("en-US", { month: "short", year: "numeric" });


// ══════════════════════════════════════════════════════════════════════════
// SVG Sentiment Chart
// ══════════════════════════════════════════════════════════════════════════
function SentimentChart({ filings, heroDate }) {
  const W = 680, H = 200;
  const PAD = { top: 24, right: 16, bottom: 32, left: 48 };
  const cW  = W - PAD.left - PAD.right;
  const cH  = H - PAD.top  - PAD.bottom;

  if (!filings || filings.length < 2) {
    return (
      <div style={{
        height: 200, display: "flex", alignItems: "center",
        justifyContent: "center", color: C.textDim,
        fontFamily: C.font, fontSize: 10,
      }}>
        NO DATA
      </div>
    );
  }

  const vals  = filings.map(f => f.sentiment);
  const minV  = Math.min(...vals) - 0.4;
  const maxV  = Math.max(...vals) + 0.4;
  const xStep = cW / Math.max(filings.length - 1, 1);
  const xOf   = (i) => PAD.left + i * xStep;
  const yOf   = (v) => PAD.top + cH - ((v - minV) / (maxV - minV)) * cH;
  const zero  = yOf(0);

  const pts      = filings.map((f, i) => [xOf(i), yOf(f.sentiment)]);
  const linePath = pts.map((p, i) =>
    i === 0 ? `M${p[0].toFixed(1)},${p[1].toFixed(1)}`
            : `L${p[0].toFixed(1)},${p[1].toFixed(1)}`
  ).join(" ");

  const areaPath = [
    `M${pts[0][0].toFixed(1)},${Math.min(zero, PAD.top + cH).toFixed(1)}`,
    ...pts.map(p => `L${p[0].toFixed(1)},${p[1].toFixed(1)}`),
    `L${pts[pts.length-1][0].toFixed(1)},${Math.min(zero, PAD.top + cH).toFixed(1)}`,
    "Z",
  ].join(" ");

  const labelCount = Math.min(8, filings.length);
  const labelStep  = Math.max(1, Math.floor(filings.length / labelCount));
  const labelIdxs  = new Set(
    Array.from({ length: labelCount }, (_, i) => i * labelStep)
  );

  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ display: "block" }}>
      <defs>
        <linearGradient id="sg_up" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor={C.gold} stopOpacity="0.20" />
          <stop offset="100%" stopColor={C.gold} stopOpacity="0.01" />
        </linearGradient>
      </defs>

      {/* grid lines */}
      {[0.25, 0.5, 0.75].map(t => (
        <line key={t}
          x1={PAD.left} y1={PAD.top + cH * t}
          x2={PAD.left + cW} y2={PAD.top + cH * t}
          stroke={C.border} strokeWidth="1"
        />
      ))}

      {/* zero line */}
      {zero >= PAD.top && zero <= PAD.top + cH && (
        <line
          x1={PAD.left} y1={zero} x2={PAD.left + cW} y2={zero}
          stroke={C.border2} strokeWidth="1" strokeDasharray="4,4"
        />
      )}

      {/* area + line */}
      <path d={areaPath} fill="url(#sg_up)" />
      <path d={linePath} fill="none" stroke={C.gold}
        strokeWidth="1.5" strokeLinejoin="round" />

      {/* anomaly markers */}
      {filings.map((f, i) => {
        if (f.risk_level === "NORMAL") return null;
        const x   = xOf(i);
        const y   = yOf(f.sentiment);
        const col = RISK_COLOR[f.risk_level];
        const isHero = heroDate === f.date;
        return (
          <g key={i}>
            {isHero && (
              <>
                <circle cx={x} cy={y} r={14} fill="none"
                  stroke={col} strokeWidth="1" opacity="0.2" />
                <circle cx={x} cy={y} r={9} fill="none"
                  stroke={col} strokeWidth="1" opacity="0.12" />
              </>
            )}
            <circle cx={x} cy={y} r={isHero ? 5 : 3.5}
              fill={col} stroke={C.bg} strokeWidth="1.5" />
            <line
              x1={x} y1={y + (isHero ? 7 : 5)}
              x2={x} y2={PAD.top + cH}
              stroke={col} strokeWidth="1"
              strokeDasharray="2,3" opacity="0.3"
            />
          </g>
        );
      })}

      {/* y-axis */}
      {[minV, (minV + maxV) / 2, maxV].map((v, i) => (
        <g key={i}>
          <line x1={PAD.left-4} y1={yOf(v)} x2={PAD.left} y2={yOf(v)}
            stroke={C.border2} strokeWidth="1" />
          <text x={PAD.left-8} y={yOf(v)+4}
            textAnchor="end" fill={C.textDim}
            fontSize="9" fontFamily={C.font}>
            {v.toFixed(1)}
          </text>
        </g>
      ))}

      {/* x-axis labels */}
      {filings.map((f, i) => {
        if (!labelIdxs.has(i)) return null;
        return (
          <text key={i} x={xOf(i)} y={H - 4}
            textAnchor="middle" fill={C.textDim}
            fontSize="8" fontFamily={C.font}>
            {fmt(f.date)}
          </text>
        );
      })}

      <text x={10} y={PAD.top + cH / 2}
        textAnchor="middle" fill={C.textDim}
        fontSize="8" fontFamily={C.font}
        transform={`rotate(-90,10,${PAD.top + cH / 2})`}>
        SENTIMENT
      </text>
    </svg>
  );
}


// ══════════════════════════════════════════════════════════════════════════
// Hero Case Card
// ══════════════════════════════════════════════════════════════════════════
function HeroCaseCard({ c, active, onClick }) {
  return (
    <div onClick={onClick} style={{
      background: active ? "rgba(245,158,11,0.05)" : C.surface,
      border:     `1px solid ${active ? C.gold : C.border}`,
      padding:    "14px 16px", cursor: "pointer",
      transition: "all 0.15s", position: "relative",
    }}>
      {active && (
        <div style={{
          position: "absolute", left: 0, top: 0,
          bottom: 0, width: 2, background: C.gold,
        }} />
      )}

      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
        <div>
          <span style={{ color: C.gold, fontFamily: C.font, fontSize: 13, fontWeight: 700, letterSpacing: 1 }}>
            {c.ticker}
          </span>
          <span style={{ color: C.textDim, fontFamily: C.font, fontSize: 9, marginLeft: 8 }}>
            {c.filing_date} · {c.form_type}
          </span>
        </div>
        <span style={{
          background: C.redDim, color: C.red,
          fontFamily: C.font, fontSize: 8,
          padding: "2px 6px", letterSpacing: 1,
        }}>
          BEARISH
        </span>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 10 }}>
        {(c.signals || []).map((s, i) => (
          <span key={i} style={{
            background: C.border, color: C.textMid,
            fontFamily: C.font, fontSize: 8,
            padding: "2px 6px", letterSpacing: 0.5,
          }}>
            {String(s).toUpperCase()}
          </span>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 5 }}>
        {[
          { label: "30D", val: c.return_30d },
          { label: "60D", val: c.return_60d },
          { label: "90D", val: c.return_90d },
        ].map(({ label, val }) => (
          <div key={label} style={{
            background: val !== null && val < 0 ? C.redDim : "rgba(34,197,94,0.07)",
            padding: "6px 8px", textAlign: "center",
          }}>
            <div style={{ color: C.textDim, fontFamily: C.font, fontSize: 8, letterSpacing: 1 }}>
              {label}
            </div>
            <div style={{
              color: val !== null && val < 0 ? C.red : C.green,
              fontFamily: C.font, fontSize: 12, fontWeight: 700,
            }}>
              {val !== null ? `${val > 0 ? "+" : ""}${val.toFixed(1)}%` : "—"}
            </div>
          </div>
        ))}
      </div>

      {c.base_price && (
        <div style={{ color: C.textDim, fontFamily: C.font, fontSize: 8, marginTop: 8 }}>
          Price at filing: ${c.base_price.toFixed(2)}
          {c.return_90d && (
            <span style={{ color: C.red, marginLeft: 8 }}>
              → ${(c.base_price * (1 + c.return_90d / 100)).toFixed(2)} after 90d
            </span>
          )}
        </div>
      )}
    </div>
  );
}


// ══════════════════════════════════════════════════════════════════════════
// Filing Row
// ══════════════════════════════════════════════════════════════════════════
function FilingRow({ f, isHero }) {
  const [open, setOpen] = useState(false);
  const col      = RISK_COLOR[f.risk_level] || C.textDim;
  const clickable = f.risk_level !== "NORMAL";

  return (
    <div
      onClick={() => clickable && setOpen(!open)}
      style={{
        borderBottom: `1px solid ${C.border}`,
        background:   isHero ? "rgba(245,158,11,0.03)" : "transparent",
        cursor:       clickable ? "pointer" : "default",
      }}
    >
      <div style={{
        display: "grid",
        gridTemplateColumns: "100px 50px 80px 1fr 60px",
        gap: 6, padding: "8px 12px", alignItems: "center",
      }}>
        <span style={{ color: C.textMid, fontFamily: C.font, fontSize: 10 }}>
          {f.date}
        </span>
        <span style={{ color: C.textDim, fontFamily: C.font, fontSize: 10 }}>
          {f.form_type}
        </span>
        <span style={{
          color: col, fontFamily: C.font, fontSize: 8,
          background: RISK_BG[f.risk_level],
          padding: "2px 6px", letterSpacing: 0.5,
          display: "inline-block",
        }}>
          {f.risk_level}
        </span>
        <span style={{ color: C.textDim, fontFamily: C.font, fontSize: 8 }}>
          {f.signals?.length > 0 ? f.signals.join(" · ") : "—"}
        </span>
        <span style={{ color: C.textDim, fontFamily: C.font, fontSize: 8, textAlign: "right" }}>
          {f.sentiment !== undefined ? Number(f.sentiment).toFixed(3) : ""}
        </span>
      </div>

      {open && f.signals?.length > 0 && (
        <div style={{
          padding: "8px 12px 10px",
          borderTop: `1px solid ${C.border}`,
          background: "rgba(0,0,0,0.25)",
        }}>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {f.signals.map((s, i) => (
              <span key={i} style={{
                color: col, fontFamily: C.font, fontSize: 8,
                border: `1px solid ${col}`,
                padding: "2px 8px", letterSpacing: 0.5, opacity: 0.8,
              }}>
                ⚠ {String(s).toUpperCase()}
              </span>
            ))}
          </div>
          <div style={{
            color: C.textDim, fontFamily: C.font,
            fontSize: 8, marginTop: 6,
          }}>
            {f.anomaly_count} signal{f.anomaly_count !== 1 ? "s" : ""} triggered
            · sentiment: {Number(f.sentiment).toFixed(4)}
            · neg_pct: {Number(f.neg_pct).toFixed(3)}
            · uncertain_pct: {Number(f.uncertain_pct).toFixed(3)}
          </div>
        </div>
      )}
    </div>
  );
}


// ══════════════════════════════════════════════════════════════════════════
// Main Component
// ══════════════════════════════════════════════════════════════════════════
export default function RiskTimeline() {
  const [allData,      setAllData]      = useState(null);
  const [heroCases,    setHeroCases]    = useState([]);
  const [activeTicker, setActiveTicker] = useState("JNJ");
  const [activeHero,   setActiveHero]   = useState(null);
  const [showAll,      setShowAll]      = useState(false);
  const [loading,      setLoading]      = useState(true);
  const [error,        setError]        = useState(null);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const [aRes, eRes] = await Promise.all([
          axios.get(`${API}/anomaly-history`),
          axios.get(`${API}/evidence-cases`),
        ]);
        setAllData(aRes.data);
        const heroes = eRes.data.hero_cases || [];
        setHeroCases(heroes);
        if (heroes.length > 0) setActiveHero(0);
      } catch (err) {
        setError("Failed to load. Is the backend running?");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const filings    = allData?.data?.[activeTicker] || [];
  const activeCase = activeHero !== null ? heroCases[activeHero] : null;
  const heroDate   = activeCase?.ticker === activeTicker ? activeCase.filing_date : null;
  const flagged    = filings.filter(f => f.risk_level !== "NORMAL");
  const highRisk   = filings.filter(f => f.risk_level === "HIGH");
  const flagRate   = filings.length
    ? ((flagged.length / filings.length) * 100).toFixed(0) : 0;

  const visibleFilings = showAll ? filings : flagged;

  if (loading) return (
    <div style={{
      background: C.bg, minHeight: "100vh",
      display: "flex", alignItems: "center", justifyContent: "center",
      fontFamily: C.font, color: C.textDim,
      fontSize: 11, letterSpacing: 2,
    }}>
      LOADING SEC FILING DATA...
    </div>
  );

  if (error) return (
    <div style={{
      background: C.bg, minHeight: "100vh",
      display: "flex", alignItems: "center", justifyContent: "center",
      fontFamily: C.font, color: C.red, fontSize: 11,
    }}>
      {error}
    </div>
  );

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
          <span style={{
            color: C.gold, fontFamily: C.font,
            fontSize: 9, letterSpacing: 3,
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
          lineHeight: 1.7, maxWidth: 560,
        }}>
          Linguistic anomaly detection on 10-K/10-Q filings using Loughran-McDonald
          financial dictionary. Flags when language deviates &gt;1.5σ from ticker's
          own historical baseline. {allData?.total_filings} filings
          analyzed · {allData?.total_flagged} flagged.
        </p>
      </div>

      <div style={{
        display: "grid",
        gridTemplateColumns: "1fr 310px",
        gap: 16, alignItems: "start",
      }}>

        {/* LEFT */}
        <div>

          {/* Ticker tabs */}
          <div style={{ display: "flex", gap: 4, marginBottom: 12, flexWrap: "wrap" }}>
            {TICKERS.map(t => (
              <button key={t} onClick={() => { setActiveTicker(t); setShowAll(false); }}
                style={{
                  background:    activeTicker === t ? C.gold : "transparent",
                  color:         activeTicker === t ? C.bg   : C.textDim,
                  border:        `1px solid ${activeTicker === t ? C.gold : C.border}`,
                  fontFamily:    C.font, fontSize: 10,
                  padding:       "5px 14px", cursor: "pointer",
                  letterSpacing: 1,
                  fontWeight:    activeTicker === t ? 700 : 400,
                  transition:    "all 0.1s",
                }}>
                {t}
              </button>
            ))}
          </div>

          {/* Chart */}
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
                <span style={{ color: C.gold, fontFamily: C.font, fontSize: 11, letterSpacing: 2 }}>
                  {activeTicker}
                </span>
                <span style={{ color: C.textDim, fontFamily: C.font, fontSize: 9, marginLeft: 8 }}>
                  {TICKER_NAME[activeTicker]} · LM SENTIMENT · {filings.length} FILINGS
                </span>
              </div>
              <div style={{ display: "flex", gap: 10 }}>
                {[
                  { l: "HIGH",     c: C.red   },
                  { l: "ELEVATED", c: C.amber  },
                  { l: "WATCH",    c: C.gold   },
                ].map(({ l, c }) => (
                  <div key={l} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                    <div style={{ width: 6, height: 6, borderRadius: "50%", background: c }} />
                    <span style={{ color: C.textDim, fontFamily: C.font, fontSize: 8 }}>{l}</span>
                  </div>
                ))}
              </div>
            </div>
            <SentimentChart filings={filings} heroDate={heroDate} />
          </div>

          {/* Stats bar */}
          <div style={{
            display: "grid", gridTemplateColumns: "repeat(4,1fr)",
            border: `1px solid ${C.border}`, borderTop: "none",
            marginBottom: 16,
          }}>
            {[
              { label: "FILINGS",   val: filings.length,  col: C.textMid },
              { label: "FLAGGED",   val: flagged.length,  col: C.gold    },
              { label: "HIGH RISK", val: highRisk.length, col: C.red     },
              { label: "FLAG RATE", val: `${flagRate}%`,  col: C.amber   },
            ].map(({ label, val, col }, i, arr) => (
              <div key={label} style={{
                padding: "10px 14px",
                borderRight: i < arr.length - 1 ? `1px solid ${C.border}` : "none",
                background: C.surface,
              }}>
                <div style={{ color: C.textDim, fontFamily: C.font, fontSize: 8, letterSpacing: 1 }}>
                  {label}
                </div>
                <div style={{ color: col, fontFamily: C.font, fontSize: 20, fontWeight: 700, lineHeight: 1.2 }}>
                  {val}
                </div>
              </div>
            ))}
          </div>

          {/* Filing list */}
          <div style={{ border: `1px solid ${C.border}` }}>
            <div style={{
              display: "grid",
              gridTemplateColumns: "100px 50px 80px 1fr 60px",
              gap: 6, padding: "6px 12px",
              background: C.surface,
              borderBottom: `1px solid ${C.border}`,
            }}>
              {["DATE","FORM","RISK","SIGNALS TRIGGERED","SCORE"].map(h => (
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
                {showAll
                  ? `No filings found for ${activeTicker}.`
                  : `No flagged filings for ${activeTicker}. Toggle below to show all.`}
              </div>
            ) : (
              visibleFilings.map((f, i) => (
                <FilingRow key={i} f={f} isHero={heroDate === f.date} />
              ))
            )}

            <div
              onClick={() => setShowAll(!showAll)}
              style={{
                padding: "8px 12px",
                background: C.surface,
                borderTop: `1px solid ${C.border}`,
                cursor: "pointer", textAlign: "center",
                color: C.textDim, fontFamily: C.font,
                fontSize: 9, letterSpacing: 1,
              }}
            >
              {showAll
                ? `▲ SHOW FLAGGED ONLY (${flagged.length})`
                : `▼ SHOW ALL ${filings.length} FILINGS`}
            </div>
          </div>
        </div>

        {/* RIGHT */}
        <div>
          <div style={{
            color: C.textDim, fontFamily: C.font,
            fontSize: 8, letterSpacing: 2,
            marginBottom: 10, paddingBottom: 8,
            borderBottom: `1px solid ${C.border}`,
          }}>
            FILING WARNED US EARLY — TOP EVIDENCE CASES
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {heroCases.map((c, i) => (
              <HeroCaseCard
                key={i} c={c} active={activeHero === i}
                onClick={() => { setActiveHero(i); setActiveTicker(c.ticker); }}
              />
            ))}
          </div>

          {/* Methodology */}
          <div style={{
            marginTop: 16, padding: "12px 14px",
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
              ["Dictionary",  "Loughran-McDonald Financial"],
              ["Threshold",   ">1.5σ from ticker's own history"],
              ["Window",      "8 prior filings as baseline"],
              ["Scope",       "10-K + 10-Q, ≥500 words"],
              ["Total",       `${allData?.total_filings || "—"} filings analyzed`],
              ["Flagged",     `${allData?.total_flagged || "—"} anomalies detected`],
            ].map(([k, v]) => (
              <div key={k} style={{
                display: "flex", justifyContent: "space-between", marginBottom: 5,
              }}>
                <span style={{ color: C.textDim, fontFamily: C.font, fontSize: 9 }}>{k}</span>
                <span style={{ color: C.textMid, fontFamily: C.font, fontSize: 9, textAlign: "right", maxWidth: 150 }}>{v}</span>
              </div>
            ))}
          </div>

          <p style={{
            color: C.textDim, fontFamily: C.font,
            fontSize: 8, lineHeight: 1.8, marginTop: 12,
            borderLeft: `2px solid ${C.border2}`, paddingLeft: 8,
          }}>
            Signal accuracy on 30-day forward returns: 44.7% overall.
            Structural risk indicators, not short-term trading signals.
            High-impact cases show stronger alignment over 90-day windows.
          </p>
        </div>
      </div>
    </div>
  );
}