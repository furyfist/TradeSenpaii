import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ResponsiveContainer
} from "recharts";

export default function SentimentGauge({ data }) {
  if (!data || data.length === 0) return null;

  const formatted = data.map(d => ({
    ...d,
    date:  d.date.slice(0, 7),   // YYYY-MM
    score: parseFloat(d.lm_sentiment_score.toFixed(3)),
  }));

  const latest = formatted[formatted.length - 1];

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    const val = payload[0].value;
    return (
      <div style={tooltipStyle}>
        <div style={{ color: "#94a3b8", marginBottom: 4 }}>{label}</div>
        <div style={{ color: val >= 0 ? "#22c55e" : "#ef4444", fontWeight: 700 }}>
          {val > 0 ? "+" : ""}{val}
        </div>
      </div>
    );
  };

  return (
    <div style={styles.card}>
      <div style={styles.header}>
        <h3 style={styles.title}>SEC Filing Sentiment</h3>
        <div style={styles.latestScore}>
          <span style={{ color: "#64748b", fontSize: 12 }}>Latest Score</span>
          <span style={{
            fontSize: 18, fontWeight: 700,
            color: latest?.score >= 0 ? "#22c55e" : "#ef4444"
          }}>
            {latest?.score > 0 ? "+" : ""}{latest?.score}
          </span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={formatted} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
          <XAxis
            dataKey="date"
            tick={{ fill: "#475569", fontSize: 10 }}
            tickLine={false}
            interval={4}
          />
          <YAxis
            tick={{ fill: "#475569", fontSize: 11 }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine y={0} stroke="rgba(255,255,255,0.1)" strokeDasharray="4 4" />
          <Line
            type="monotone"
            dataKey="score"
            stroke="#6366f1"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: "#6366f1" }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

const tooltipStyle = {
  background:   "#1e1e2e",
  border:       "1px solid rgba(255,255,255,0.1)",
  borderRadius: 8,
  padding:      "8px 12px",
  fontSize:     13,
};

const styles = {
  card: {
    background:   "rgba(255,255,255,0.03)",
    border:       "1px solid rgba(255,255,255,0.08)",
    borderRadius: 16, padding: 28,
  },
  header: {
    display: "flex", justifyContent: "space-between",
    alignItems: "center", marginBottom: 20,
  },
  title: {
    fontSize: 15, fontWeight: 600,
    color: "#94a3b8", textTransform: "uppercase",
    letterSpacing: "0.5px",
  },
  latestScore: {
    display: "flex", flexDirection: "column",
    alignItems: "flex-end", gap: 2,
  },
};