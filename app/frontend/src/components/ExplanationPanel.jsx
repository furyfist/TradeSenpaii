import { useState, useEffect } from "react";
import { Brain, TrendingUp, TrendingDown, AlertTriangle, Clock, Zap } from "lucide-react";
import { fetchExplanation } from "../api/client";

export default function ExplanationPanel({ ticker, prediction }) {
  const [explanation, setExplanation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(false);

  // Reset state when ticker changes
  useEffect(() => {
    setExplanation(null);
    setError(null);
    setLoading(false);
    setExpanded(false);   // collapse the panel on ticker switch
  }, [ticker]);

  // Load explanation when expanded
  useEffect(() => {
    if (!ticker || !prediction) return;
    if (!expanded) return;
    loadExplanation();
  }, [ticker, expanded]);

  const loadExplanation = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchExplanation(ticker);
      setExplanation(res.data);
    } catch (err) {
      setError("Failed to load explanation.");
    } finally {
      setLoading(false);
    }
  };

  const tierColor = (tier) => {
    if (tier === "High Conviction") return "#22c55e";
    if (tier === "Strong Signal") return "#6366f1";
    if (tier === "Moderate Signal") return "#f59e0b";
    return "#64748b";
  };

  return (
    <div style={styles.card}>
      {/* Header — always visible */}
      <div style={styles.header} onClick={() => setExpanded(!expanded)}>
        <div style={styles.headerLeft}>
          <Brain size={16} color="#6366f1" />
          <span style={styles.title}>AI Explanation</span>
          <span style={styles.badge}>Powered by Groq</span>
        </div>
        <button style={styles.expandBtn}>
          {expanded ? "▲ Hide" : "▼ Show Analysis"}
        </button>
      </div>

      {/* Expanded content */}
      {expanded && (
        <div style={styles.content}>
          {loading && (
            <div style={styles.loadingState}>
              <div style={styles.spinner} />
              <span style={{ color: "#64748b", fontSize: 13 }}>
                Analyzing signals + searching historical analogies...
              </span>
            </div>
          )}

          {error && (
            <div style={styles.errorState}>{error}</div>
          )}

          {explanation && !loading && (
            <>
              {/* Headline */}
              <div style={styles.headline}>
                <span style={{
                  ...styles.tierBadge,
                  background: `${tierColor(explanation.confidence_tier)}15`,
                  color: tierColor(explanation.confidence_tier),
                  border: `1px solid ${tierColor(explanation.confidence_tier)}30`,
                }}>
                  <Zap size={10} />
                  {explanation.confidence_tier}
                </span>
                <p style={styles.headlineText}>{explanation.headline}</p>
              </div>

              {/* Main explanation */}
              <p style={styles.explanationText}>{explanation.explanation}</p>

              {/* Key driver + risk */}
              <div style={styles.twoCol}>
                <div style={styles.infoBox}>
                  <div style={styles.infoBoxHeader}>
                    <Zap size={12} color="#6366f1" />
                    <span style={{ color: "#6366f1", fontSize: 11, fontWeight: 600 }}>
                      KEY DRIVER
                    </span>
                  </div>
                  <p style={styles.infoBoxText}>{explanation.key_driver}</p>
                </div>
                <div style={{ ...styles.infoBox, borderColor: "rgba(239,68,68,0.15)" }}>
                  <div style={styles.infoBoxHeader}>
                    <AlertTriangle size={12} color="#ef4444" />
                    <span style={{ color: "#ef4444", fontSize: 11, fontWeight: 600 }}>
                      MAIN RISK
                    </span>
                  </div>
                  <p style={styles.infoBoxText}>{explanation.main_risk}</p>
                </div>
              </div>

              {/* Historical analogies */}
              <div style={styles.analogiesSection}>
                <div style={styles.analogiesHeader}>
                  <Clock size={13} color="#94a3b8" />
                  <span style={styles.analogiesTitle}>Historical Analogies</span>
                </div>
                <div style={styles.analogiesList}>
                  {explanation.analogies.map((a, i) => {
                    const isUp = a.actual_direction === "UP";
                    const color = isUp ? "#22c55e" : "#ef4444";

                    return (
                      <div key={i} style={styles.analogyCard}>

                        {/* Top row — date, days ago, outcome */}
                        <div style={styles.analogyTop}>
                          <span style={styles.analogyDate}>{a.date}</span>
                          <span style={styles.analogyDaysAgo}>{a.days_ago} days ago</span>
                          <span style={{
                            ...styles.analogyOutcome,
                            color,
                            background: `${color}15`,
                          }}>
                            {isUp
                              ? <TrendingUp size={10} />
                              : <TrendingDown size={10} />
                            }
                            {a.actual_direction} ({a.actual_return > 0 ? "+" : ""}
                            {a.actual_return.toFixed(2)}%)
                          </span>
                        </div>

                        {/* Similarity bar */}
                        <div style={styles.analogySimilarity}>
                          <div style={styles.similarityBarBg}>
                            <div style={{
                              ...styles.similarityBarFill,
                              width: `${a.similarity * 100}%`,
                              background: color,
                            }} />
                          </div>
                          <span style={{ color: "#64748b", fontSize: 11 }}>
                            {(a.similarity * 100).toFixed(1)}% similar
                          </span>
                        </div>

                        {/* Key signals */}
                        <div style={styles.analogySignals}>
                          {Object.entries(a.key_signals).slice(0, 3).map(([k, v]) => (
                            <span key={k} style={styles.signalChip}>
                              {k}: {typeof v === "number" ? v.toFixed(2) : v}
                            </span>
                          ))}
                        </div>

                        {/* Search context — what actually happened */}
                        {a.search_context && (
                          <div style={styles.searchContext}>
                            <span style={styles.searchContextLabel}>📰 What happened:</span>
                            <p style={styles.searchContextText}>{a.search_context}</p>
                          </div>
                        )}

                        {/* Search button */}
                        {a.search_url && (
                          <a
                            href={a.search_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={styles.searchBtn}
                          >
                            🔍 Search This Event
                          </a>
                        )}

                      </div>
                    );
                  })}
                </div>
                <p style={styles.historicalNote}>
                  💡 {explanation.historical_note}
                </p>
              </div>

              {/* Disclaimer */}
              <p style={styles.disclaimer}>
                Educational simulation only — not financial advice.
                Model CV accuracy: ~52%. Past analogies do not guarantee future outcomes.
              </p>
            </>
          )}
        </div>
      )}
    </div>
  );
}

const styles = {
  card: {
    background: "rgba(255,255,255,0.03)",
    border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: 16,
    overflow: "hidden",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "16px 20px",
    cursor: "pointer",
    userSelect: "none",
  },
  headerLeft: {
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  title: {
    fontSize: 14,
    fontWeight: 600,
    color: "#e2e8f0",
  },
  badge: {
    fontSize: 10,
    color: "#6366f1",
    background: "rgba(99,102,241,0.1)",
    padding: "2px 6px",
    borderRadius: 4,
  },
  expandBtn: {
    background: "none",
    border: "none",
    color: "#475569",
    fontSize: 12,
    cursor: "pointer",
  },
  content: {
    padding: "0 20px 20px",
    borderTop: "1px solid rgba(255,255,255,0.06)",
    paddingTop: 16,
  },
  loadingState: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    padding: "20px 0",
    justifyContent: "center",
  },
  spinner: {
    width: 20,
    height: 20,
    border: "2px solid rgba(99,102,241,0.2)",
    borderTop: "2px solid #6366f1",
    borderRadius: "50%",
    animation: "spin 1s linear infinite",
  },
  errorState: {
    color: "#ef4444",
    fontSize: 13,
    padding: "12px 0",
  },
  headline: {
    marginBottom: 12,
  },
  tierBadge: {
    display: "inline-flex",
    alignItems: "center",
    gap: 4,
    fontSize: 10,
    fontWeight: 700,
    padding: "3px 8px",
    borderRadius: 20,
    marginBottom: 8,
    textTransform: "uppercase",
    letterSpacing: "0.3px",
  },
  headlineText: {
    fontSize: 15,
    fontWeight: 600,
    color: "#f1f5f9",
    lineHeight: 1.4,
    margin: 0,
  },
  explanationText: {
    fontSize: 13,
    color: "#94a3b8",
    lineHeight: 1.7,
    margin: "12px 0 16px",
  },
  twoCol: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: 12,
    marginBottom: 20,
  },
  infoBox: {
    background: "rgba(255,255,255,0.02)",
    border: "1px solid rgba(99,102,241,0.15)",
    borderRadius: 10,
    padding: "12px 14px",
  },
  infoBoxHeader: {
    display: "flex",
    alignItems: "center",
    gap: 5,
    marginBottom: 6,
  },
  infoBoxText: {
    fontSize: 12,
    color: "#cbd5e1",
    lineHeight: 1.5,
    margin: 0,
  },
  analogiesSection: { marginBottom: 16 },
  analogiesHeader: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    marginBottom: 12,
  },
  analogiesTitle: {
    fontSize: 12,
    fontWeight: 600,
    color: "#94a3b8",
    textTransform: "uppercase",
    letterSpacing: "0.5px",
  },
  analogiesList: {
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  analogyCard: {
    background: "rgba(255,255,255,0.02)",
    border: "1px solid rgba(255,255,255,0.06)",
    borderRadius: 10,
    padding: "10px 12px",
  },
  analogyTop: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    marginBottom: 8,
  },
  analogyDate: {
    fontSize: 13,
    fontWeight: 600,
    color: "#e2e8f0",
  },
  analogyDaysAgo: {
    fontSize: 11,
    color: "#475569",
    flex: 1,
  },
  analogyOutcome: {
    display: "inline-flex",
    alignItems: "center",
    gap: 4,
    fontSize: 11,
    fontWeight: 700,
    padding: "2px 8px",
    borderRadius: 20,
  },
  analogySimilarity: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    marginBottom: 8,
  },
  similarityBarBg: {
    flex: 1,
    height: 4,
    background: "rgba(255,255,255,0.06)",
    borderRadius: 99,
    overflow: "hidden",
  },
  similarityBarFill: {
    height: "100%",
    borderRadius: 99,
    transition: "width 0.6s ease",
  },
  analogySignals: {
    display: "flex",
    flexWrap: "wrap",
    gap: 4,
  },
  signalChip: {
    fontSize: 10,
    color: "#64748b",
    background: "rgba(255,255,255,0.04)",
    padding: "2px 6px",
    borderRadius: 4,
  },
  searchContext: {
    marginTop: 10,
    background: "rgba(99,102,241,0.06)",
    border: "1px solid rgba(99,102,241,0.15)",
    borderRadius: 8,
    padding: "8px 10px",
  },
  searchContextLabel: {
    fontSize: 10,
    fontWeight: 700,
    color: "#818cf8",
    textTransform: "uppercase",
    letterSpacing: "0.4px",
  },
  searchContextText: {
    fontSize: 12,
    color: "#94a3b8",
    lineHeight: 1.6,
    margin: "4px 0 0",
  },
  searchBtn: {
    display: "inline-flex",
    alignItems: "center",
    gap: 4,
    marginTop: 8,
    fontSize: 11,
    fontWeight: 600,
    color: "#818cf8",
    background: "rgba(99,102,241,0.1)",
    border: "1px solid rgba(99,102,241,0.25)",
    borderRadius: 6,
    padding: "4px 10px",
    textDecoration: "none",
    cursor: "pointer",
    transition: "background 0.2s",
  },
  historicalNote: {
    fontSize: 12,
    color: "#6366f1",
    marginTop: 12,
    lineHeight: 1.5,
    margin: "12px 0 0",
  },
  disclaimer: {
    fontSize: 10,
    color: "#334155",
    marginTop: 16,
    lineHeight: 1.5,
    margin: "16px 0 0",
  },
};