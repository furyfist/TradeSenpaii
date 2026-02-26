import { useState, useEffect } from "react";
import { Routes, Route, NavLink } from "react-router-dom";
import PredictionCard   from "./components/PredictionCard";
import PriceChart       from "./components/PriceChart";
import SentimentGauge   from "./components/SentimentGauge";
import SignalBreakdown  from "./components/SignalBreakdown";
import ExplanationPanel from "./components/ExplanationPanel";
import HypothesisPage   from "./components/HypothesisPage";
import LandingPage from "./components/LandingPage";

import {
  fetchPrediction, fetchPriceHistory,
  fetchSentimentHistory, fetchModelInfo, fetchTickers
} from "./api/client";

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

  useEffect(() => {
    fetchTickers().then(res => setTickers(res.data.tickers)).catch(() => setTickers([]));
  }, []);

  useEffect(() => { loadAll(activeTicker); }, [activeTicker]);

  const loadAll = async (ticker) => {
    setLoading(true); setError(null); setPrediction(null);
    try {
      const [priceRes, sentRes, modelRes] = await Promise.all([
        fetchPriceHistory(ticker), fetchSentimentHistory(ticker), fetchModelInfo(ticker),
      ]);
      setPriceData(priceRes.data.data);
      setSentData(sentRes.data.data);
      setModelInfo(modelRes.data);
      setLoading(false);
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
      {/* Global Header */}
      <header style={styles.header}>
        <div style={styles.logo}>
          <span style={styles.logoText}>TRADE</span>
          <span style={styles.logoAccent}>SENPAI</span>
          <span style={styles.logoBadge}>V3</span>
        </div>
        <nav style={styles.nav}>
          <NavLink to="/" end style={({ isActive }) => ({
            ...styles.navLink, ...(isActive ? styles.navLinkActive : {})
          })}>
            ▸ HOME
          </NavLink>
          <NavLink to="/dashboard" style={({ isActive }) => ({
            ...styles.navLink, ...(isActive ? styles.navLinkActive : {})
          })}>
            ▸ DASHBOARD
          </NavLink>
          <NavLink to="/hypothesis" style={({ isActive }) => ({
            ...styles.navLink, ...(isActive ? styles.navLinkActive : {})
          })}>
            ▸ HYPOTHESIS ENGINE
          </NavLink>
        </nav>
        <div style={styles.headerRight}>
          {lastUpdated && <span style={styles.lastUpdated}>UPDATED {lastUpdated}</span>}
          {modelInfo && (
            <div style={styles.modelBadge}>
              TRANSFORMER · {(modelInfo.cv_accuracy * 100).toFixed(2)}% CV
            </div>
          )}
        </div>
      </header>

      {/* Routes */}
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/dashboard" element={
          <DashboardPage
            activeTicker={activeTicker} setActiveTicker={setActiveTicker}
            tickers={tickers} prediction={prediction} priceData={priceData}
            sentData={sentData} modelInfo={modelInfo} loading={loading}
            error={error} onRefresh={() => loadAll(activeTicker)}
          />
        }/>
        <Route path="/hypothesis" element={<HypothesisPage />} />
      </Routes>
    </div>
  );
}

function DashboardPage({
  activeTicker, setActiveTicker, tickers, prediction,
  priceData, sentData, modelInfo, loading, error, onRefresh
}) {
  return (
    <>
      {/* Ticker Bar */}
      <div style={styles.tickerBar}>
        <span style={styles.tickerLabel}>COVERAGE</span>
        {tickers.map(t => (
          <button key={t.ticker} onClick={() => setActiveTicker(t.ticker)}
            style={{ ...styles.tickerBtn, ...(activeTicker === t.ticker ? styles.tickerBtnActive : {}) }}>
            <span style={styles.tickerSymbol}>{t.ticker}</span>
            <span style={styles.tickerName}>{t.name}</span>
          </button>
        ))}
      </div>

      {error && <div style={styles.errorBanner}>⚠ {error}</div>}

      <main style={styles.grid}>
        <div style={styles.leftCol}>
          <PredictionCard prediction={prediction} loading={loading} onRefresh={onRefresh} />
          <SignalBreakdown signals={prediction?.top_signals} />
        </div>
        <div style={styles.rightCol}>
          <PriceChart data={priceData} prediction={prediction} />
          <SentimentGauge data={sentData} />
          <ExplanationPanel ticker={activeTicker} prediction={prediction} />
          {modelInfo && (
            <div style={styles.infoStrip}>
              {[
                ["MODEL",    modelInfo.model_type],
                ["SECTOR",   modelInfo.sector],
                ["FEATURES", modelInfo.input_features],
                ["SEQUENCE", `${modelInfo.sequence_len}D`],
                ["TRAINED",  modelInfo.trained_on],
              ].map(([label, value]) => (
                <div key={label} style={styles.infoItem}>
                  <span style={styles.infoLabel}>{label}</span>
                  <span style={styles.infoValue}>{value}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </>
  );
}

const styles = {
  root: {
    minHeight:  "100vh",
    background: "#080808",
    fontFamily: "'IBM Plex Mono', 'Courier New', monospace",
    color:      "#e2e8f0",
  },
  header: {
    display:        "flex",
    justifyContent: "space-between",
    alignItems:     "center",
    padding:        "0 32px",
    height:         56,
    borderBottom:   "1px solid #1a1a1a",
    background:     "#0a0a0a",
  },
  logo:       { display: "flex", alignItems: "center", gap: 6 },
  logoText:   { fontSize: 18, fontWeight: 800, color: "#f1f5f9", letterSpacing: 3 },
  logoAccent: { fontSize: 18, fontWeight: 800, color: "#f59e0b", letterSpacing: 3 },
  logoBadge:  {
    fontSize: 9, fontWeight: 700, color: "#f59e0b",
    background: "rgba(245,158,11,0.1)", padding: "2px 6px",
    border: "1px solid rgba(245,158,11,0.3)", letterSpacing: 1,
  },
  nav: { display: "flex", gap: 4 },
  navLink: {
    padding:        "6px 16px",
    fontSize:       11,
    fontWeight:     600,
    letterSpacing:  1.5,
    color:          "#475569",
    textDecoration: "none",
    border:         "1px solid transparent",
    transition:     "all 0.15s",
  },
  navLinkActive: {
    color:      "#f59e0b",
    border:     "1px solid rgba(245,158,11,0.3)",
    background: "rgba(245,158,11,0.06)",
  },
  headerRight: { display: "flex", alignItems: "center", gap: 16 },
  lastUpdated: { fontSize: 10, color: "#374151", letterSpacing: 1 },
  modelBadge:  {
    fontSize: 10, color: "#6366f1", letterSpacing: 1,
    background: "rgba(99,102,241,0.08)", padding: "3px 10px",
    border: "1px solid rgba(99,102,241,0.2)",
  },
  tickerBar: {
    display:    "flex",
    alignItems: "center",
    gap:        6,
    padding:    "12px 32px",
    borderBottom: "1px solid #111",
    background: "#090909",
  },
  tickerLabel: { fontSize: 9, color: "#374151", letterSpacing: 2, marginRight: 8 },
  tickerBtn: {
    display: "flex", flexDirection: "column", alignItems: "flex-start",
    gap: 2, padding: "6px 14px",
    background: "transparent",
    border: "1px solid #1a1a1a",
    cursor: "pointer", transition: "all 0.15s", minWidth: 80,
  },
  tickerBtnActive: {
    background: "rgba(245,158,11,0.06)",
    border:     "1px solid rgba(245,158,11,0.35)",
  },
  tickerSymbol: { fontSize: 12, fontWeight: 700, color: "#f1f5f9", letterSpacing: 1 },
  tickerName:   { fontSize: 9,  color: "#374151" },
  errorBanner: {
    background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.2)",
    color: "#ef4444", padding: "10px 32px", fontSize: 11, letterSpacing: 1,
  },
  grid: {
    display: "grid", gridTemplateColumns: "380px 1fr",
    gap: 20, padding: "20px 32px", maxWidth: 1400, margin: "0 auto",
  },
  leftCol:  { display: "flex", flexDirection: "column", gap: 16 },
  rightCol: { display: "flex", flexDirection: "column", gap: 16 },
  infoStrip: {
    display: "flex", background: "#0a0a0a",
    border: "1px solid #111", overflow: "hidden",
  },
  infoItem: {
    display: "flex", flexDirection: "column", gap: 4,
    padding: "10px 16px", borderRight: "1px solid #111", flex: 1,
  },
  infoLabel: { fontSize: 9,  color: "#374151", letterSpacing: 1.5 },
  infoValue: { fontSize: 11, color: "#94a3b8", fontWeight: 600 },
};