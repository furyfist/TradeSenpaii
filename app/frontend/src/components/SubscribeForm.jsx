import { useState } from "react";
import axios from "axios";

const API = "http://localhost:8000";

export default function SubscribeForm() {
  const [username, setUsername] = useState("");
  const [status,   setStatus]   = useState(null); // null | "pending" | "exists" | "error"
  const [message,  setMessage]  = useState("");
  const [loading,  setLoading]  = useState(false);

  const submit = async () => {
    if (!username.trim()) return;
    setLoading(true); setStatus(null);
    try {
      const res = await axios.post(`${API}/subscribe`, {
        username: username.trim().replace("@", "")
      });
      setStatus(res.data.status === "pending" ? "pending" : "exists");
      setMessage(res.data.message);
    } catch (e) {
      setStatus("error");
      setMessage(e.response?.data?.detail || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={s.wrap}>
      <div style={s.title}>📬 GET TELEGRAM ALERTS</div>
      <div style={s.desc}>
        Enter your Telegram username to request morning briefs,
        evening outcomes, and real-time signal alerts.
      </div>

      {status === "pending" && (
        <div style={s.successBox}>
          ✅ Request submitted — pending admin approval.<br />
          You'll receive a welcome message once approved.
        </div>
      )}
      {status === "exists" && (
        <div style={s.infoBox}>ℹ️ {message}</div>
      )}
      {status === "error" && (
        <div style={s.errorBox}>⚠ {message}</div>
      )}

      {!status && (
        <div style={s.inputRow}>
          <span style={s.at}>@</span>
          <input
            style={s.input}
            value={username}
            onChange={e => setUsername(e.target.value)}
            onKeyDown={e => e.key === "Enter" && submit()}
            placeholder="your_telegram_username"
            disabled={loading}
          />
          <button
            style={{ ...s.btn, ...(loading ? s.btnDisabled : {}) }}
            onClick={submit}
            disabled={loading}
          >
            {loading ? "..." : "REQUEST →"}
          </button>
        </div>
      )}

      <div style={s.note}>
        Admin will verify your username and send your chat ID approval.
        Your Telegram username is never shared.
      </div>
    </div>
  );
}

const s = {
  wrap: {
    background:  "#0a0a0a",
    border:      "1px solid #151515",
    borderLeft:  "3px solid #f59e0b",
    padding:     "32px 40px",
    fontFamily:  "'IBM Plex Mono', monospace",
  },
  title: {
    fontSize: 12, fontWeight: 700,
    color: "#f59e0b", letterSpacing: 2, marginBottom: 10,
  },
  desc: {
    fontSize: 11, color: "#374151",
    lineHeight: 1.7, marginBottom: 20,
  },
  inputRow: {
    display: "flex", alignItems: "center",
    border: "1px solid #222", background: "#080808", marginBottom: 12,
  },
  at: { padding: "0 12px", color: "#f59e0b", fontSize: 14 },
  input: {
    flex: 1, background: "transparent", border: "none",
    outline: "none", color: "#f1f5f9", fontSize: 13,
    padding: "12px 0", fontFamily: "'IBM Plex Mono', monospace",
  },
  btn: {
    padding: "12px 20px", background: "#f59e0b",
    border: "none", color: "#000", fontWeight: 800,
    fontSize: 10, letterSpacing: 2, cursor: "pointer",
    fontFamily: "'IBM Plex Mono', monospace",
  },
  btnDisabled: { opacity: 0.5, cursor: "not-allowed" },
  successBox: {
    background: "rgba(34,197,94,0.06)", border: "1px solid rgba(34,197,94,0.2)",
    color: "#22c55e", padding: "14px 16px", fontSize: 11,
    lineHeight: 1.7, marginBottom: 12,
  },
  infoBox: {
    background: "rgba(99,102,241,0.06)", border: "1px solid rgba(99,102,241,0.2)",
    color: "#6366f1", padding: "14px 16px", fontSize: 11, marginBottom: 12,
  },
  errorBox: {
    background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.2)",
    color: "#ef4444", padding: "14px 16px", fontSize: 11, marginBottom: 12,
  },
  note: { fontSize: 9, color: "#1f2937", letterSpacing: 0.5 },
};