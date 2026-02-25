import { TrendingUp, TrendingDown, RefreshCw } from "lucide-react";

export default function PredictionCard({ prediction, loading, onRefresh }) {
  if (loading) {
    return (
      <div style={styles.card}>
        <div style={styles.loadingPulse}>
          <div style={styles.loadingBar} />
          <div style={{ ...styles.loadingBar, width: "60%", marginTop: 12 }} />
          <div style={{ ...styles.loadingBar, width: "40%", marginTop: 12 }} />
        </div>
      </div>
    );
  }

  if (!prediction) return null;

  const isUp         = prediction.prediction === "UP";
  const accentColor  = isUp ? "#22c55e" : "#ef4444";
  const bgAccent     = isUp ? "rgba(34,197,94,0.08)" : "rgba(239,68,68,0.08)";
  const confidence   = (prediction.confidence * 100).toFixed(1);
  const accuracy     = (prediction.model_accuracy * 100).toFixed(2);

  return (
    <div style={{ ...styles.card, borderColor: accentColor, background: bgAccent }}>

      {/* Header */}
      <div style={styles.header}>
        <div>
          <span style={styles.ticker}>{prediction.ticker}</span>
          <span style={styles.company}>{prediction.name}</span>
        </div>
        <button style={styles.refreshBtn} onClick={onRefresh}>
          <RefreshCw size={16} />
        </button>
      </div>

      {/* Main prediction */}
      <div style={styles.predictionRow}>
        {isUp
          ? <TrendingUp  size={56} color={accentColor} />
          : <TrendingDown size={56} color={accentColor} />
        }
        <div style={styles.predictionText}>
          <span style={{ ...styles.direction, color: accentColor }}>
            {prediction.prediction}
          </span>
          <span style={styles.subtext}>Next Day Direction</span>
        </div>
      </div>

      {/* Confidence bar */}
      <div style={styles.confidenceSection}>
        <div style={styles.confidenceLabel}>
          <span>Confidence</span>
          <span style={{ color: accentColor }}>{confidence}%</span>
        </div>
        <div style={styles.barBg}>
          <div style={{
            ...styles.barFill,
            width: `${confidence}%`,
            background: accentColor,
          }} />
        </div>
      </div>

      {/* Metadata */}
      <div style={styles.metaRow}>
        <MetaItem label="Predicting"  value={prediction.predicted_date} />
        <MetaItem label="As of"       value={prediction.as_of_date} />
        <MetaItem label="Model Acc."  value={`${accuracy}%`} />
      </div>

      {/* Sentiment */}
      <div style={styles.sentimentRow}>
        <span style={styles.sentLabel}>SEC Sentiment</span>
        <span style={{
          ...styles.sentBadge,
          background: prediction.sentiment_label === "Positive"
            ? "rgba(34,197,94,0.15)"
            : prediction.sentiment_label === "Negative"
            ? "rgba(239,68,68,0.15)"
            : "rgba(148,163,184,0.15)",
          color: prediction.sentiment_label === "Positive"
            ? "#22c55e"
            : prediction.sentiment_label === "Negative"
            ? "#ef4444"
            : "#94a3b8",
        }}>
          {prediction.sentiment_label} ({prediction.sentiment_score.toFixed(3)})
        </span>
      </div>

    </div>
  );
}

function MetaItem({ label, value }) {
  return (
    <div style={styles.metaItem}>
      <span style={styles.metaLabel}>{label}</span>
      <span style={styles.metaValue}>{value}</span>
    </div>
  );
}

const styles = {
  card: {
    background:   "rgba(255,255,255,0.03)",
    border:       "1px solid rgba(255,255,255,0.08)",
    borderRadius: 16,
    padding:      28,
    transition:   "border-color 0.3s",
  },
  loadingPulse: { animation: "pulse 1.5s infinite" },
  loadingBar: {
    height: 18, borderRadius: 8,
    background: "rgba(255,255,255,0.06)", width: "80%",
  },
  header: {
    display: "flex", justifyContent: "space-between",
    alignItems: "center", marginBottom: 24,
  },
  ticker: {
    fontSize: 22, fontWeight: 700,
    color: "#f1f5f9", marginRight: 8,
  },
  company: { fontSize: 13, color: "#64748b" },
  refreshBtn: {
    background: "rgba(255,255,255,0.05)",
    border:     "1px solid rgba(255,255,255,0.1)",
    borderRadius: 8, padding: "6px 10px",
    color: "#94a3b8", cursor: "pointer",
  },
  predictionRow: {
    display: "flex", alignItems: "center",
    gap: 20, marginBottom: 28,
  },
  predictionText: {
    display: "flex", flexDirection: "column", gap: 4,
  },
  direction: {
    fontSize: 48, fontWeight: 800,
    letterSpacing: "-1px", lineHeight: 1,
  },
  subtext: { fontSize: 13, color: "#64748b" },
  confidenceSection: { marginBottom: 24 },
  confidenceLabel: {
    display: "flex", justifyContent: "space-between",
    fontSize: 13, color: "#94a3b8", marginBottom: 8,
  },
  barBg: {
    height: 6, background: "rgba(255,255,255,0.06)",
    borderRadius: 99, overflow: "hidden",
  },
  barFill: {
    height: "100%", borderRadius: 99,
    transition: "width 0.6s ease",
  },
  metaRow: {
    display: "flex", gap: 12,
    marginBottom: 20,
  },
  metaItem: {
    flex: 1,
    background: "rgba(255,255,255,0.03)",
    borderRadius: 10, padding: "10px 12px",
    display: "flex", flexDirection: "column", gap: 4,
  },
  metaLabel: { fontSize: 11, color: "#475569", textTransform: "uppercase" },
  metaValue: { fontSize: 13, color: "#cbd5e1", fontWeight: 600 },
  sentimentRow: {
    display: "flex", justifyContent: "space-between",
    alignItems: "center",
  },
  sentLabel: { fontSize: 13, color: "#64748b" },
  sentBadge: {
    fontSize: 12, fontWeight: 600,
    padding: "4px 10px", borderRadius: 20,
  },
};