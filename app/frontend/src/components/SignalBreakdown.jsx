export default function SignalBreakdown({ signals }) {
  if (!signals || signals.length === 0) return null;

  const stateColor = (state) => {
    const positive = ["Oversold", "Bullish", "Positive", "Normal", "Low", "Above"];
    const negative = ["Overbought", "Bearish", "Negative", "Elevated",
                      "High", "Below", "Spike", "Surge"];
    if (positive.includes(state)) return "#22c55e";
    if (negative.includes(state)) return "#ef4444";
    return "#94a3b8";
  };

  return (
    <div style={styles.card}>
      <h3 style={styles.title}>Signal Breakdown</h3>
      <div style={styles.grid}>
        {signals.map((signal, i) => (
          <div key={i} style={styles.signalItem}>
            <div style={styles.signalName}>{signal.name}</div>
            <div style={styles.signalBottom}>
              <span style={styles.signalValue}>
                {typeof signal.value === "number"
                  ? signal.value.toFixed(3)
                  : signal.value}
              </span>
              <span style={{
                ...styles.signalState,
                color:      stateColor(signal.state),
                background: `${stateColor(signal.state)}15`,
              }}>
                {signal.state}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const styles = {
  card: {
    background:   "rgba(255,255,255,0.03)",
    border:       "1px solid rgba(255,255,255,0.08)",
    borderRadius: 16, padding: 28,
  },
  title: {
    fontSize: 15, fontWeight: 600,
    color: "#94a3b8", marginBottom: 20,
    textTransform: "uppercase", letterSpacing: "0.5px",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(2, 1fr)",
    gap: 12,
  },
  signalItem: {
    background:   "rgba(255,255,255,0.03)",
    border:       "1px solid rgba(255,255,255,0.06)",
    borderRadius: 10, padding: "12px 14px",
  },
  signalName: {
    fontSize: 12, color: "#475569",
    marginBottom: 8, textTransform: "uppercase",
    letterSpacing: "0.3px",
  },
  signalBottom: {
    display: "flex", justifyContent: "space-between",
    alignItems: "center",
  },
  signalValue: { fontSize: 14, fontWeight: 600, color: "#cbd5e1" },
  signalState: {
    fontSize: 11, fontWeight: 600,
    padding: "2px 8px", borderRadius: 20,
  },
};