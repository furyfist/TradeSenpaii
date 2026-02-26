import { useState } from "react";
import axios from "axios";

const API = import.meta.env.VITE_API_URL;

export default function SubscribeForm() {
    const [username, setUsername] = useState("");
    const [telegramId, setTelegramId] = useState("");
    const [status, setStatus] = useState(null); // null | "approved" | "pending" | "exists" | "error"
    const [message, setMessage] = useState("");
    const [loading, setLoading] = useState(false);

    const submit = async () => {
        if (!username.trim()) return;
        setLoading(true); setStatus(null);
        try {
            const payload = { username: username.trim().replace("@", "") };
            if (telegramId.trim()) payload.telegram_id = telegramId.trim();

            const res = await axios.post(`${API}/subscribe`, payload);
            setStatus(res.data.status === "approved" ? "approved" : res.data.status === "pending" ? "pending" : "exists");
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
                Enter your Telegram username and Chat ID to get instantly subscribed.
                Not sure of your Chat ID? Message{" "}
                <a href="https://t.me/userinfobot" target="_blank" rel="noreferrer" style={s.link}>
                    @userinfobot
                </a>{" "}
                on Telegram — it will reply with your ID.
            </div>

            {status === "approved" && (
                <div style={s.successBox}>
                    ✅ You're subscribed! Check your Telegram for a welcome message.
                </div>
            )}
            {status === "pending" && (
                <div style={s.successBox}>
                    ⏳ Request submitted — pending admin approval.<br />
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
                <>
                    {/* Username row */}
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
                    </div>

                    {/* Chat ID row */}
                    <div style={{ ...s.inputRow, marginBottom: 12 }}>
                        <span style={s.prefix}>#</span>
                        <input
                            style={s.input}
                            value={telegramId}
                            onChange={e => setTelegramId(e.target.value)}
                            onKeyDown={e => e.key === "Enter" && submit()}
                            placeholder="your_telegram_chat_id  (e.g. 123456789)"
                            disabled={loading}
                        />
                    </div>

                    <button
                        style={{ ...s.btn, ...(loading ? s.btnDisabled : {}) }}
                        onClick={submit}
                        disabled={loading}
                    >
                        {loading ? "..." : "SUBSCRIBE →"}
                    </button>
                </>
            )}

            <div style={s.note}>
                Chat ID is used only to deliver alerts. Never shared. Leave blank if you prefer manual approval.
            </div>
        </div>
    );
}

const s = {
    wrap: {
        background: "#0a0a0a",
        border: "1px solid #151515",
        borderLeft: "3px solid #f59e0b",
        padding: "32px 40px",
        fontFamily: "'IBM Plex Mono', monospace",
    },
    title: {
        fontSize: 12, fontWeight: 700,
        color: "#f59e0b", letterSpacing: 2, marginBottom: 10,
    },
    desc: {
        fontSize: 11, color: "#374151",
        lineHeight: 1.7, marginBottom: 20,
    },
    link: { color: "#f59e0b", textDecoration: "none" },
    inputRow: {
        display: "flex", alignItems: "center",
        border: "1px solid #222", background: "#080808", marginBottom: 8,
    },
    at: { padding: "0 12px", color: "#f59e0b", fontSize: 14 },
    prefix: { padding: "0 12px", color: "#6366f1", fontSize: 14 },
    input: {
        flex: 1, background: "transparent", border: "none",
        outline: "none", color: "#f1f5f9", fontSize: 13,
        padding: "12px 0", fontFamily: "'IBM Plex Mono', monospace",
    },
    btn: {
        width: "100%", padding: "12px 20px", background: "#f59e0b",
        border: "none", color: "#000", fontWeight: 800,
        fontSize: 10, letterSpacing: 2, cursor: "pointer",
        fontFamily: "'IBM Plex Mono', monospace", marginBottom: 12,
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