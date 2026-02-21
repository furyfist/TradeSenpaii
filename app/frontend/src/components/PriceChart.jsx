import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer
} from "recharts";

export default function PriceChart({ data, prediction }) {
  if (!data || data.length === 0) return null;

  const accentColor = prediction?.prediction === "UP" ? "#22c55e" : "#ef4444";

  const formatted = data.map(d => ({
    ...d,
    date:  d.date.slice(5),   // show MM-DD only
    close: parseFloat(d.close.toFixed(2)),
  }));

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    return (
      <div style={tooltipStyle}>
        <div style={{ color: "#94a3b8", marginBottom: 4 }}>{label}</div>
        <div style={{ color: accentColor, fontWeight: 700 }}>
          ${payload[0].value}
        </div>
      </div>
    );
  };

  return (
    <div style={styles.card}>
      <div style={styles.header}>
        <h3 style={styles.title}>Price History — 90 Days</h3>
        <span style={styles.latest}>
          Latest: ${formatted[formatted.length - 1]?.close}
        </span>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={formatted} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor={accentColor} stopOpacity={0.2} />
              <stop offset="95%" stopColor={accentColor} stopOpacity={0}   />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
          <XAxis
            dataKey="date"
            tick={{ fill: "#475569", fontSize: 11 }}
            tickLine={false}
            interval={14}
          />
          <YAxis
            tick={{ fill: "#475569", fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            domain={["auto", "auto"]}
            tickFormatter={v => `$${v}`}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="close"
            stroke={accentColor}
            strokeWidth={2}
            fill="url(#priceGrad)"
            dot={false}
          />
        </AreaChart>
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
  latest: { fontSize: 14, color: "#f1f5f9", fontWeight: 700 },
};