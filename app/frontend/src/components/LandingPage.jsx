import { useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";

const TICKERS = [
  { symbol: "KO",    name: "Coca-Cola",          sector: "Consumer Staples", color: "#ef4444" },
  { symbol: "JNJ",   name: "Johnson & Johnson",  sector: "Healthcare",       color: "#6366f1" },
  { symbol: "PG",    name: "Procter & Gamble",   sector: "Consumer Staples", color: "#22c55e" },
  { symbol: "WMT",   name: "Walmart",            sector: "Retail",           color: "#f59e0b" },
  { symbol: "AAPL",  name: "Apple",              sector: "Technology",       color: "#3b82f6" },
  { symbol: "GOOGL", name: "Alphabet",           sector: "Technology",       color: "#8b5cf6" },
];

const FEATURES = [
  {
    icon: "◈",
    title: "Transformer Model",
    desc:  "60-day sequence model trained on 56 features per ticker. ~52% CV accuracy — honest, not inflated.",
  },
  {
    icon: "▲",
    title: "SEC Sentiment Engine",
    desc:  "Loughran-McDonald dictionary applied to real SEC filings. Domain-specific beats general-purpose LLMs.",
  },
  {
    icon: "◉",
    title: "Hypothesis Engine",
    desc:  "Type any market hypothesis. 6 AI agents research, stress-test, and produce a structured research brief.",
  },
  {
    icon: "⬡",
    title: "Telegram Alerts",
    desc:  "Morning briefs, evening outcomes, direction flips, sentiment spikes — delivered to your Telegram.",
  },
];

// Simulated ticker tape data
const TAPE_ITEMS = [
  "KO ▼ DOWN 73.3%", "AAPL ▲ UP 57.3%", "GOOGL ▼ DOWN 50.2%",
  "WMT ▼ DOWN 50.1%", "JNJ ▼ DOWN 55.0%", "PG ▲ UP 53.3%",
  "SEC SENTIMENT · KO 0.637", "LITIGATION FLAG · AAPL",
  "HYPOTHESIS ENGINE · READY", "TRANSFORMER · 56 FEATURES",
];

export default function LandingPage() {
  const navigate = useNavigate();
  const [tapePos, setTapePos] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setTapePos(p => p + 1);
    }, 40);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={s.page}>

      {/* Ticker Tape */}
      <div style={s.tape}>
        <div style={{
          ...s.tapeInner,
          transform: `translateX(-${(tapePos * 0.5) % (TAPE_ITEMS.join("   ·   ").length * 8)}px)`
        }}>
          {[...TAPE_ITEMS, ...TAPE_ITEMS, ...TAPE_ITEMS].map((item, i) => (
            <span key={i} style={s.tapeItem}>
              {item} <span style={s.tapeDot}>·</span>&nbsp;
            </span>
          ))}
        </div>
      </div>

      {/* Hero */}
      <section style={s.hero}>
        <div style={s.heroLeft}>
          <div style={s.heroEyebrow}>AI-POWERED STOCK RESEARCH</div>
          <h1 style={s.heroTitle}>
            <span style={s.heroTitleWhite}>TRADE</span>
            <span style={s.heroTitleGold}>SENPAI</span>
          </h1>
          <div style={s.heroBadge}>V3</div>
          <p style={s.heroDesc}>
            Surfaces SEC filing sentiment and technical signals so retail investors
            see what institutional analysts see. Educational simulation — not financial advice.
          </p>
          <div style={s.heroCta}>
            <button style={s.ctaPrimary} onClick={() => navigate("/dashboard")}>
              OPEN DASHBOARD →
            </button>
            <button style={s.ctaSecondary} onClick={() => navigate("/hypothesis")}>
              TRY HYPOTHESIS ENGINE
            </button>
          </div>
          <div style={s.heroDisclaimer}>
            ⚠ Educational/simulation only · ~52% model accuracy · Not financial advice
          </div>
        </div>

        {/* Live ticker grid */}
        <div style={s.heroRight}>
          <div style={s.tickerGrid}>
            {TICKERS.map(t => (
              <div key={t.symbol} style={{ ...s.tickerCard, borderTop: `2px solid ${t.color}30` }}
                onClick={() => navigate("/dashboard")}>
                <div style={{ ...s.tickerCardSymbol, color: t.color }}>{t.symbol}</div>
                <div style={s.tickerCardName}>{t.name}</div>
                <div style={s.tickerCardSector}>{t.sector}</div>
                <div style={{ ...s.tickerCardDot, background: t.color }} />
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Stats bar */}
      <div style={s.statsBar}>
        {[
          ["6",    "TICKERS COVERED"],
          ["56",   "FEATURES PER DAY"],
          ["~52%", "CV ACCURACY"],
          ["60D",  "LOOKBACK WINDOW"],
          ["3",    "FILINGS ANALYZED"],
        ].map(([val, label]) => (
          <div key={label} style={s.statItem}>
            <div style={s.statValue}>{val}</div>
            <div style={s.statLabel}>{label}</div>
          </div>
        ))}
      </div>

      {/* Features */}
      <section style={s.features}>
        <div style={s.sectionHeader}>
          <div style={s.sectionEyebrow}>CAPABILITIES</div>
          <h2 style={s.sectionTitle}>What TradeSenpai Does</h2>
        </div>
        <div style={s.featuresGrid}>
          {FEATURES.map((f, i) => (
            <div key={i} style={s.featureCard}>
              <div style={s.featureIcon}>{f.icon}</div>
              <div style={s.featureTitle}>{f.title}</div>
              <div style={s.featureDesc}>{f.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section style={s.howItWorks}>
        <div style={s.sectionHeader}>
          <div style={s.sectionEyebrow}>PIPELINE</div>
          <h2 style={s.sectionTitle}>How It Works</h2>
        </div>
        <div style={s.pipeline}>
          {[
            { step: "01", title: "SEC FILING INGESTED",    desc: "EDGAR RSS feed monitored for 6 tickers" },
            { step: "02", title: "LM SENTIMENT SCORED",    desc: "Loughran-McDonald dictionary applied" },
            { step: "03", title: "56 FEATURES ENGINEERED", desc: "Price, volume, technical + sentiment signals" },
            { step: "04", title: "TRANSFORMER PREDICTS",   desc: "60-day sequence → UP/DOWN probability" },
            { step: "05", title: "ALERTS DISPATCHED",      desc: "Telegram brief sent at market open/close" },
          ].map((item, i) => (
            <div key={i} style={s.pipelineStep}>
              <div style={s.pipelineNum}>{item.step}</div>
              <div style={s.pipelineConnector} />
              <div style={s.pipelineContent}>
                <div style={s.pipelineTitle}>{item.title}</div>
                <div style={s.pipelineDesc}>{item.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA bottom */}
      <section style={s.ctaSection}>
        <div style={s.ctaBox}>
          <div style={s.ctaTitle}>READY TO RESEARCH?</div>
          <div style={s.ctaSubtitle}>
            Open the dashboard to see live predictions, or test the hypothesis engine.
          </div>
          <div style={s.ctaButtons}>
            <button style={s.ctaPrimary} onClick={() => navigate("/dashboard")}>
              OPEN DASHBOARD →
            </button>
            <button style={s.ctaSecondary} onClick={() => navigate("/hypothesis")}>
              HYPOTHESIS ENGINE →
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer style={s.footer}>
        <div style={s.footerLeft}>
          <span style={s.footerLogo}>TRADE<span style={{ color: "#f59e0b" }}>SENPAI</span></span>
          <span style={s.footerVersion}>V3</span>
        </div>
        <div style={s.footerRight}>
          Educational simulation only · Not financial advice · Model accuracy ~52%
        </div>
      </footer>
    </div>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────
const s = {
  page: {
    minHeight:  "100vh",
    background: "#080808",
    fontFamily: "'IBM Plex Mono', 'Courier New', monospace",
    color:      "#e2e8f0",
    overflowX:  "hidden",
  },

  // Ticker tape
  tape: {
    background:  "#0a0a0a",
    borderBottom:"1px solid #111",
    overflow:    "hidden",
    height:      32,
    display:     "flex",
    alignItems:  "center",
  },
  tapeInner: {
    display:    "flex",
    whiteSpace: "nowrap",
    transition: "none",
  },
  tapeItem:   { fontSize: 10, color: "#374151", letterSpacing: 1.5, padding: "0 8px" },
  tapeDot:    { color: "#f59e0b" },

  // Hero
  hero: {
    display:       "flex",
    justifyContent:"space-between",
    alignItems:    "center",
    padding:       "80px 64px",
    gap:           64,
    maxWidth:      1400,
    margin:        "0 auto",
  },
  heroLeft:       { flex: 1, maxWidth: 560 },
  heroEyebrow:    { fontSize: 10, color: "#374151", letterSpacing: 3, marginBottom: 16 },
  heroTitle: {
    fontSize:    72,
    fontWeight:  900,
    lineHeight:  1,
    letterSpacing: 6,
    margin:      "0 0 8px",
  },
  heroTitleWhite: { color: "#f1f5f9" },
  heroTitleGold:  { color: "#f59e0b" },
  heroBadge: {
    display:     "inline-block",
    fontSize:    10,
    color:       "#f59e0b",
    background:  "rgba(245,158,11,0.1)",
    border:      "1px solid rgba(245,158,11,0.3)",
    padding:     "2px 10px",
    letterSpacing: 2,
    marginBottom: 24,
  },
  heroDesc: {
    fontSize:   14,
    color:      "#475569",
    lineHeight: 1.8,
    marginBottom: 32,
  },
  heroCta:       { display: "flex", gap: 12, marginBottom: 20 },
  heroDisclaimer:{ fontSize: 10, color: "#1f2937", letterSpacing: 0.5 },

  // CTA Buttons
  ctaPrimary: {
    padding:     "14px 24px",
    background:  "#f59e0b",
    border:      "none",
    color:       "#000",
    fontWeight:  800,
    fontSize:    11,
    letterSpacing: 2,
    cursor:      "pointer",
    fontFamily:  "'IBM Plex Mono', monospace",
  },
  ctaSecondary: {
    padding:     "14px 24px",
    background:  "transparent",
    border:      "1px solid #222",
    color:       "#475569",
    fontWeight:  600,
    fontSize:    11,
    letterSpacing: 2,
    cursor:      "pointer",
    fontFamily:  "'IBM Plex Mono', monospace",
  },

  // Ticker grid
  heroRight: { flex: 1, maxWidth: 480 },
  tickerGrid: {
    display:             "grid",
    gridTemplateColumns: "1fr 1fr 1fr",
    gap:                 1,
    background:          "#111",
    border:              "1px solid #111",
  },
  tickerCard: {
    background: "#0a0a0a",
    padding:    "20px 16px",
    cursor:     "pointer",
    position:   "relative",
    transition: "background 0.15s",
  },
  tickerCardSymbol: { fontSize: 16, fontWeight: 800, letterSpacing: 2, marginBottom: 4 },
  tickerCardName:   { fontSize: 9,  color: "#374151", marginBottom: 4 },
  tickerCardSector: { fontSize: 9,  color: "#1f2937" },
  tickerCardDot: {
    position: "absolute", top: 12, right: 12,
    width: 6, height: 6, borderRadius: "50%",
  },

  // Stats bar
  statsBar: {
    display:       "flex",
    justifyContent:"center",
    gap:           0,
    background:    "#0a0a0a",
    borderTop:     "1px solid #111",
    borderBottom:  "1px solid #111",
    padding:       "0 64px",
  },
  statItem: {
    display:       "flex",
    flexDirection: "column",
    alignItems:    "center",
    padding:       "24px 40px",
    borderRight:   "1px solid #111",
    gap:           6,
  },
  statValue:  { fontSize: 28, fontWeight: 800, color: "#f59e0b", letterSpacing: 2 },
  statLabel:  { fontSize: 9,  color: "#374151", letterSpacing: 2 },

  // Features
  features: {
    padding:  "80px 64px",
    maxWidth: 1400,
    margin:   "0 auto",
  },
  sectionHeader: { marginBottom: 48 },
  sectionEyebrow:{ fontSize: 10, color: "#374151", letterSpacing: 3, marginBottom: 12 },
  sectionTitle:  { fontSize: 28, fontWeight: 800, color: "#f1f5f9", letterSpacing: 2, margin: 0 },
  featuresGrid: {
    display:             "grid",
    gridTemplateColumns: "repeat(4, 1fr)",
    gap:                 1,
    background:          "#111",
    border:              "1px solid #111",
  },
  featureCard: {
    background: "#0a0a0a",
    padding:    "32px 24px",
  },
  featureIcon:  { fontSize: 24, color: "#f59e0b", marginBottom: 16 },
  featureTitle: { fontSize: 12, fontWeight: 700, color: "#f1f5f9", letterSpacing: 1.5, marginBottom: 12 },
  featureDesc:  { fontSize: 11, color: "#374151", lineHeight: 1.7 },

  // Pipeline
  howItWorks: {
    padding:    "0 64px 80px",
    maxWidth:   1400,
    margin:     "0 auto",
  },
  pipeline: {
    display:  "flex",
    gap:      1,
    background:"#111",
    border:   "1px solid #111",
  },
  pipelineStep: {
    flex:       1,
    background: "#0a0a0a",
    padding:    "28px 20px",
    position:   "relative",
  },
  pipelineNum: {
    fontSize:    28,
    fontWeight:  800,
    color:       "#1a1a1a",
    marginBottom: 16,
    letterSpacing: 2,
  },
  pipelineConnector: {
    position:   "absolute",
    right:      -1,
    top:        "50%",
    width:      1,
    height:     40,
    background: "#111",
    transform:  "translateY(-50%)",
  },
  pipelineTitle: { fontSize: 10, color: "#f59e0b", letterSpacing: 2, marginBottom: 8 },
  pipelineDesc:  { fontSize: 11, color: "#374151", lineHeight: 1.6 },

  // Bottom CTA
  ctaSection: {
    padding:  "0 64px 80px",
    maxWidth: 1400,
    margin:   "0 auto",
  },
  ctaBox: {
    background:  "#0a0a0a",
    border:      "1px solid #151515",
    borderLeft:  "3px solid #f59e0b",
    padding:     "48px",
    textAlign:   "center",
  },
  ctaTitle:    { fontSize: 22, fontWeight: 800, color: "#f1f5f9", letterSpacing: 4, marginBottom: 12 },
  ctaSubtitle: { fontSize: 12, color: "#374151", marginBottom: 32 },
  ctaButtons:  { display: "flex", gap: 12, justifyContent: "center" },

  // Footer
  footer: {
    display:        "flex",
    justifyContent: "space-between",
    alignItems:     "center",
    padding:        "20px 64px",
    borderTop:      "1px solid #111",
    background:     "#0a0a0a",
  },
  footerLeft:    { display: "flex", alignItems: "center", gap: 8 },
  footerLogo:    { fontSize: 14, fontWeight: 800, color: "#f1f5f9", letterSpacing: 3 },
  footerVersion: { fontSize: 9, color: "#f59e0b", letterSpacing: 2 },
  footerRight:   { fontSize: 10, color: "#1f2937", letterSpacing: 0.5 },
};