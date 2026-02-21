import { useState, useEffect } from "react";
import PredictionCard   from "./components/PredictionCard";
import PriceChart       from "./components/PriceChart";
import SentimentGauge   from "./components/SentimentGauge";
import SignalBreakdown  from "./components/SignalBreakdown";
import {
  fetchPrediction, fetchPriceHistory,
  fetchSentimentHistory, fetchModelInfo
} from "./api/client";

export default function App() {
  const [prediction,  setPrediction]  = useState(null);
  const [priceData,   setPriceData]   = useState([]);
  const [sentData,    setSentData]    = useState([]);
  const [modelInfo,   setModelInfo]   = useState(null);
  const [loading,     setLoading]     = useState(true);
  const [error,       setError]       = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  const loadAll = async () => {
    setLoading(true);
    setError(null);
    try {
      const [predRes, priceRes, sentRes, modelRes] = await Promise.all([
        fetchPrediction(),
        fetchPriceHistory(),
        fetchSentimentHistory(),
        fetchModelInfo(),
      ]);
      setPrediction(predRes.data);
      setPriceData(priceRes.data.data);
      setSentData(sentRes.data.data);
      setModelInfo(modelRes.data);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      setError("Failed to fetch data. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadAll(); }, []);

  return (
    <div style={styles.root}>

      {/* Header */}
      <header style={styles.header}>
        <div style={styles.logo}>
          <span style={styles.logoText}>TradeSenpai</span>
          <span style={styles.logoBadge}>BETA</span>
        </div>
        <div style={styles.headerRight}>
          {lastUpdated && (
            <span style={styles.lastUpdated}>Updated {lastUpdated}</span>
          )}
          <div style={styles.modelBadge}>
            {modelInfo && `Transformer · ${(modelInfo.cv_accuracy * 100).toFixed(2)}% CV Acc`}
          </div>
        </div>
      </header>

      {/* Error */}
      {error && (
        <div style={styles.errorBanner}>{error}</div>
      )}

      {/* Main grid */}
      <main style={styles.grid}>

        {/* Left column */}
        <div style={styles.leftCol}>
          <PredictionCard
            prediction={prediction}
            loading={loading}
            onRefresh={loadAll}
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

          {/* Model info strip */}
          {modelInfo && (
            <div style={styles.infoStrip}>
              <InfoItem label="Model"    value={modelInfo.model_type} />
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
    marginBottom:   32,
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
  errorBanner: {
    background: "rgba(239,68,68,0.1)",
    border:     "1px solid rgba(239,68,68,0.2)",
    color:      "#ef4444",
    padding:    "12px 32px",
    marginBottom: 24,
    fontSize: 13,
  },
  grid: {
    display:             "grid",
    gridTemplateColumns: "380px 1fr",
    gap:                 24,
    padding:             "0 32px",
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