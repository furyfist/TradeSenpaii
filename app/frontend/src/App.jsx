import { useState, useEffect } from "react";
import PredictionCard  from "./components/PredictionCard";
import PriceChart      from "./components/PriceChart";
import SentimentGauge  from "./components/SentimentGauge";
import SignalBreakdown from "./components/SignalBreakdown";
import ExplanationPanel from "./components/ExplanationPanel";

import {
  fetchPrediction, fetchPriceHistory,
  fetchSentimentHistory, fetchModelInfo, fetchTickers
} from "./api/client";

const SECTOR_COLORS = {
  "Consumer Staples": "#22c55e",
  "Healthcare":       "#6366f1",
  "Retail":           "#f59e0b",
  "Technology":       "#3b82f6",
};

export default function App() {
  const [activeTicker, setActiveTicker] = useState("KO");
  const [tickers,      setTickers]      = useState([]);
  const [prediction,   setPrediction]   = useState(null);
  const [priceData,    setPriceData]    = useState([]);
  const [sentData,     setSentData]     = useState([]);
  const [modelInfo,    setModelInfo]    = useState(null);
  const [loading,      setLoading]      = useState(true);
  const [error,        setError]        = useState(null);
  const [lastUpdated,  setLastUpdated]  = useState(null);

  // Load ticker list once on mount
  useEffect(() => {
    fetchTickers()
      .then(res => setTickers(res.data.tickers))
      .catch(() => setTickers([]));
  }, []);

  // Load data whenever active ticker changes
  useEffect(() => {
    loadAll(activeTicker);
  }, [activeTicker]);

  const loadAll = async (ticker) => {
    setLoading(true);
    setError(null);
    setPrediction(null);

    try {
        // Load fast endpoints first — show chart immediately
        const [priceRes, sentRes, modelRes] = await Promise.all([
            fetchPriceHistory(ticker),
            fetchSentimentHistory(ticker),
            fetchModelInfo(ticker),
        ]);
        setPriceData(priceRes.data.data);
        setSentData(sentRes.data.data);
        setModelInfo(modelRes.data);
        setLoading(false);  // ← unblock UI here

        // Load prediction separately — slower
        const predRes = await fetchPrediction(ticker);
        setPrediction(predRes.data);
        setLastUpdated(new Date().toLocaleTimeString());

    } catch (err) {
        setError("Failed to fetch data. Is the backend running?");
        setLoading(false);
    }
};

  return (
    <div style={styles.root}>

      {/* Header */}
      <header style={styles.header}>
        <div style={styles.logo}>
          <span style={styles.logoText}>TradeSenpai</span>
          <span style={styles.logoBadge}>V2</span>
        </div>
        <div style={styles.headerRight}>
          {lastUpdated && (
            <span style={styles.lastUpdated}>Updated {lastUpdated}</span>
          )}
          {modelInfo && (
            <div style={styles.modelBadge}>
              Transformer · {(modelInfo.cv_accuracy * 100).toFixed(2)}% CV Acc
            </div>
          )}
        </div>
      </header>

      {/* Ticker Selector */}
      <div style={styles.tickerBar}>
        {tickers.map(t => (
          <button
            key={t.ticker}
            onClick={() => setActiveTicker(t.ticker)}
            style={{
              ...styles.tickerBtn,
              ...(activeTicker === t.ticker ? styles.tickerBtnActive : {}),
            }}
          >
            <span style={styles.tickerSymbol}>{t.ticker}</span>
            <span style={styles.tickerName}>{t.name}</span>
          </button>
        ))}
      </div>

      {/* Error */}
      {error && <div style={styles.errorBanner}>{error}</div>}

      {/* Main grid */}
      <main style={styles.grid}>

        {/* Left column */}
        <div style={styles.leftCol}>
          <PredictionCard
            prediction={prediction}
            loading={loading}
            onRefresh={() => loadAll(activeTicker)}
          />
          <SignalBreakdown signals={prediction?.top_signals} />
        </div>

        {/* Right column */}
        <div style={styles.rightCol}>
          <PriceChart
            data={priceData}
            prediction={prediction}
          />
          <SentimentGauge data={sentData} />
          <ExplanationPanel
            ticker={activeTicker}
            prediction={prediction}
          />

          {modelInfo && (
            <div style={styles.infoStrip}>
              <InfoItem label="Model"    value={modelInfo.model_type} />
              <InfoItem label="Sector"   value={modelInfo.sector} />
              <InfoItem label="Features" value={modelInfo.input_features} />
              <InfoItem label="Sequence" value={`${modelInfo.sequence_len} days`} />
              <InfoItem label="Trained"  value={modelInfo.trained_on} />
            </div>
          )}
        </div>

      </main>
    </div>
  );
}

function InfoItem({ label, value }) {
  return (
    <div style={infoItemStyle}>
      <span style={{ color: "#475569", fontSize: 11, textTransform: "uppercase" }}>
        {label}
      </span>
      <span style={{ color: "#94a3b8", fontSize: 12, fontWeight: 600 }}>
        {value}
      </span>
    </div>
  );
}

const infoItemStyle = {
  display: "flex", flexDirection: "column", gap: 4,
  padding: "10px 16px",
  borderRight: "1px solid rgba(255,255,255,0.06)",
};

const styles = {
  root: {
    minHeight:  "100vh",
    background: "#0a0a0f",
    padding:    "0 0 40px",
  },
  header: {
    display:        "flex",
    justifyContent: "space-between",
    alignItems:     "center",
    padding:        "20px 32px",
    borderBottom:   "1px solid rgba(255,255,255,0.06)",
    background:     "rgba(255,255,255,0.02)",
  },
  logo: { display: "flex", alignItems: "center", gap: 10 },
  logoText: {
    fontSize: 22, fontWeight: 800,
    background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
    WebkitBackgroundClip: "text",
    WebkitTextFillColor:  "transparent",
  },
  logoBadge: {
    fontSize: 10, fontWeight: 700,
    background: "rgba(99,102,241,0.15)",
    color: "#6366f1", padding: "2px 6px",
    borderRadius: 4, letterSpacing: "0.5px",
  },
  headerRight: {
    display: "flex", alignItems: "center", gap: 16,
  },
  lastUpdated: { fontSize: 12, color: "#475569" },
  modelBadge: {
    fontSize: 12, color: "#6366f1",
    background: "rgba(99,102,241,0.08)",
    padding: "4px 12px", borderRadius: 20,
    border: "1px solid rgba(99,102,241,0.2)",
  },
  tickerBar: {
    display:    "flex",
    gap:        8,
    padding:    "16px 32px",
    borderBottom: "1px solid rgba(255,255,255,0.06)",
    overflowX:  "auto",
  },
  tickerBtn: {
    display:       "flex",
    flexDirection: "column",
    alignItems:    "center",
    gap:           2,
    padding:       "8px 16px",
    background:    "rgba(255,255,255,0.03)",
    border:        "1px solid rgba(255,255,255,0.08)",
    borderRadius:  10,
    cursor:        "pointer",
    transition:    "all 0.2s",
    minWidth:      80,
  },
  tickerBtnActive: {
    background:  "rgba(99,102,241,0.12)",
    border:      "1px solid rgba(99,102,241,0.4)",
  },
  tickerSymbol: {
    fontSize:   14,
    fontWeight: 700,
    color:      "#f1f5f9",
  },
  tickerName: {
    fontSize: 10,
    color:    "#475569",
  },
  errorBanner: {
    background:   "rgba(239,68,68,0.1)",
    border:       "1px solid rgba(239,68,68,0.2)",
    color:        "#ef4444",
    padding:      "12px 32px",
    fontSize:     13,
  },
  grid: {
    display:             "grid",
    gridTemplateColumns: "380px 1fr",
    gap:                 24,
    padding:             "24px 32px 0",
    maxWidth:            1400,
    margin:              "0 auto",
  },
  leftCol:  { display: "flex", flexDirection: "column", gap: 24 },
  rightCol: { display: "flex", flexDirection: "column", gap: 24 },
  infoStrip: {
    display:      "flex",
    background:   "rgba(255,255,255,0.02)",
    border:       "1px solid rgba(255,255,255,0.06)",
    borderRadius: 12,
    overflow:     "hidden",
  },
};