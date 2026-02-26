import { useState, useEffect } from "react";
import axios from "axios";

const API = import.meta.env.VITE_API_URL;

export default function AdminPanel() {
    const [unlocked, setUnlocked] = useState(false);
    const [password, setPassword] = useState("");  // stored only in memory
    const [passwordInput, setPasswordInput] = useState("");
    const [passwordError, setPasswordError] = useState(false);
    const [subscribers, setSubscribers] = useState([]);
    const [loading, setLoading] = useState(false);
    const [approveInputs, setApproveInputs] = useState({}); // { id: chatId }
    const [feedback, setFeedback] = useState({}); // { id: message }

    // Restore session password if we reloaded mid-session
    useEffect(() => {
        const saved = sessionStorage.getItem("admin_pwd");
        if (saved) {
            setPassword(saved);
            setUnlocked(true);
        }
    }, []);

    useEffect(() => {
        if (unlocked) fetchSubscribers();
    }, [unlocked]);

    const authHeader = (pwd) => ({
        headers: { Authorization: "Basic " + btoa("admin:" + pwd) },
    });

    const checkPassword = async () => {
        try {
            await axios.get(`${API}/subscribers`, authHeader(passwordInput));
            // 200 → correct password
            sessionStorage.setItem("admin_pwd", passwordInput);
            setPassword(passwordInput);
            setUnlocked(true);
            setPasswordError(false);
        } catch (e) {
            if (e.response?.status === 401) {
                setPasswordError(true);
                setPasswordInput("");
            }
        }
    };

    const fetchSubscribers = async () => {
        setLoading(true);
        try {
            const res = await axios.get(`${API}/subscribers`, authHeader(password));
            setSubscribers(res.data.subscribers);
        } catch (e) {
            console.error("Failed to fetch subscribers", e);
        } finally {
            setLoading(false);
        }
    };

    const approve = async (id) => {
        const chatId = approveInputs[id]?.trim();
        if (!chatId) {
            setFeedback(f => ({ ...f, [id]: "⚠ Enter chat ID first" }));
            return;
        }
        try {
            await axios.post(
                `${API}/subscribers/${id}/approve`,
                { telegram_id: chatId },
                authHeader(password)
            );
            setFeedback(f => ({ ...f, [id]: "✅ Approved — welcome message sent" }));
            fetchSubscribers();
        } catch (e) {
            setFeedback(f => ({ ...f, [id]: `❌ ${e.response?.data?.detail || "Error"}` }));
        }
    };

    const reject = async (id) => {
        try {
            await axios.post(`${API}/subscribers/${id}/reject`, {}, authHeader(password));
            setFeedback(f => ({ ...f, [id]: "🚫 Rejected" }));
            fetchSubscribers();
        } catch (e) {
            setFeedback(f => ({ ...f, [id]: "❌ Error" }));
        }
    };

    const logout = () => {
        sessionStorage.removeItem("admin_pwd");
        setPassword("");
        setUnlocked(false);
    };

    const pending = subscribers.filter(s => s.status === "pending");
    const approved = subscribers.filter(s => s.status === "approved");
    const rejected = subscribers.filter(s => s.status === "rejected");

    // ── Password Gate ───────────────────────────────────────────────────────────
    if (!unlocked) {
        return (
            <div style={s.gate}>
                <div style={s.gateBox}>
                    <div style={s.gateTitle}>⬡ ADMIN ACCESS</div>
                    <div style={s.gateSubtitle}>TradeSenpai · Restricted Area</div>
                    <div style={s.gateInputRow}>
                        <span style={s.gateIcon}>🔑</span>
                        <input
                            style={s.gateInput}
                            type="password"
                            value={passwordInput}
                            onChange={e => { setPasswordInput(e.target.value); setPasswordError(false); }}
                            onKeyDown={e => e.key === "Enter" && checkPassword()}
                            placeholder="admin password"
                            autoFocus
                        />
                        <button style={s.gateBtn} onClick={checkPassword}>
                            ENTER →
                        </button>
                    </div>
                    {passwordError && (
                        <div style={s.gateError}>⚠ Incorrect password</div>
                    )}
                    <div style={s.gateNote}>
                        Direct URL access only · Not linked in navigation
                    </div>
                </div>
            </div>
        );
    }

    // ── Admin Panel ─────────────────────────────────────────────────────────────
    return (
        <div style={s.page}>

            {/* Header */}
            <div style={s.header}>
                <div>
                    <div style={s.pageTitle}>⬡ ADMIN PANEL</div>
                    <div style={s.pageSubtitle}>Telegram Subscriber Management</div>
                </div>
                <div style={s.headerRight}>
                    <button style={s.refreshBtn} onClick={fetchSubscribers}>↻ REFRESH</button>
                    <button style={s.logoutBtn} onClick={logout}>LOCK ⬡</button>
                </div>
            </div>

            {/* Stats */}
            <div style={s.statsRow}>
                {[
                    ["PENDING", pending.length, "#f59e0b"],
                    ["APPROVED", approved.length, "#22c55e"],
                    ["REJECTED", rejected.length, "#ef4444"],
                    ["TOTAL", subscribers.length, "#6366f1"],
                ].map(([label, val, color]) => (
                    <div key={label} style={s.statBox}>
                        <div style={{ ...s.statVal, color }}>{val}</div>
                        <div style={s.statLabel}>{label}</div>
                    </div>
                ))}
            </div>

            {/* How to get chat ID */}
            <div style={s.helpBox}>
                <div style={s.helpTitle}>HOW TO GET A USER'S CHAT ID</div>
                <div style={s.helpSteps}>
                    <span>1. Ask user to message your bot</span>
                    <span style={s.helpArrow}>→</span>
                    <span>2. Open: api.telegram.org/bot<span style={{ color: "#f59e0b" }}>TOKEN</span>/getUpdates</span>
                    <span style={s.helpArrow}>→</span>
                    <span>3. Find <span style={{ color: "#f59e0b" }}>"chat":{"{"}
                        "id": XXXXXX{"}"}</span></span>
                    <span style={s.helpArrow}>→</span>
                    <span>4. Paste below and approve</span>
                </div>
            </div>

            {/* Pending */}
            <div style={s.section}>
                <div style={s.sectionTitle}>
                    PENDING REQUESTS
                    <span style={s.sectionCount}>{pending.length}</span>
                </div>

                {loading && <div style={s.loading}>Loading...</div>}

                {!loading && pending.length === 0 && (
                    <div style={s.empty}>No pending requests</div>
                )}

                {pending.map(sub => (
                    <div key={sub.id} style={s.subCard}>
                        <div style={s.subInfo}>
                            <span style={s.subUsername}>@{sub.username}</span>
                            <span style={s.subMeta}>
                                Requested: {new Date(sub.requested_at).toLocaleString()}
                            </span>
                            <span style={s.subId}>ID: {sub.id}</span>
                        </div>
                        <div style={s.subActions}>
                            <input
                                style={s.chatIdInput}
                                placeholder="Paste chat ID (e.g. 123456789)"
                                value={approveInputs[sub.id] || ""}
                                onChange={e => setApproveInputs(a => ({ ...a, [sub.id]: e.target.value }))}
                                onKeyDown={e => e.key === "Enter" && approve(sub.id)}
                            />
                            <button style={s.approveBtn} onClick={() => approve(sub.id)}>
                                APPROVE →
                            </button>
                            <button style={s.rejectBtn} onClick={() => reject(sub.id)}>
                                REJECT
                            </button>
                        </div>
                        {feedback[sub.id] && (
                            <div style={s.feedback}>{feedback[sub.id]}</div>
                        )}
                    </div>
                ))}
            </div>

            {/* Approved */}
            <div style={s.section}>
                <div style={s.sectionTitle}>
                    APPROVED SUBSCRIBERS
                    <span style={{ ...s.sectionCount, color: "#22c55e" }}>{approved.length}</span>
                </div>
                {approved.length === 0
                    ? <div style={s.empty}>No approved subscribers</div>
                    : approved.map(sub => (
                        <div key={sub.id} style={{ ...s.subCard, borderLeft: "2px solid #22c55e20" }}>
                            <div style={s.subInfo}>
                                <span style={s.subUsername}>@{sub.username}</span>
                                <span style={s.subMeta}>Chat ID: {sub.telegram_id}</span>
                                <span style={s.subMeta}>
                                    Approved: {sub.approved_at
                                        ? new Date(sub.approved_at).toLocaleString()
                                        : "—"}
                                </span>
                            </div>
                            <div style={{ color: "#22c55e", fontSize: 11, letterSpacing: 1 }}>
                                ✓ ACTIVE
                            </div>
                        </div>
                    ))
                }
            </div>

            {/* Rejected */}
            {rejected.length > 0 && (
                <div style={s.section}>
                    <div style={s.sectionTitle}>
                        REJECTED
                        <span style={{ ...s.sectionCount, color: "#ef4444" }}>{rejected.length}</span>
                    </div>
                    {rejected.map(sub => (
                        <div key={sub.id} style={{ ...s.subCard, opacity: 0.4 }}>
                            <div style={s.subInfo}>
                                <span style={s.subUsername}>@{sub.username}</span>
                                <span style={s.subMeta}>
                                    Requested: {new Date(sub.requested_at).toLocaleString()}
                                </span>
                            </div>
                            <div style={{ color: "#ef4444", fontSize: 11 }}>✗ REJECTED</div>
                        </div>
                    ))}
                </div>
            )}

        </div>
    );
}

// ── Styles ────────────────────────────────────────────────────────────────────
const s = {
    // Gate
    gate: {
        minHeight: "100vh", display: "flex",
        alignItems: "center", justifyContent: "center",
        background: "#080808", fontFamily: "'IBM Plex Mono', monospace",
    },
    gateBox: {
        background: "#0a0a0a", border: "1px solid #151515",
        borderTop: "2px solid #f59e0b", padding: "48px",
        width: 420, display: "flex", flexDirection: "column", gap: 16,
    },
    gateTitle: { fontSize: 16, fontWeight: 800, color: "#f59e0b", letterSpacing: 4 },
    gateSubtitle: { fontSize: 10, color: "#374151", letterSpacing: 2, marginBottom: 8 },
    gateInputRow: {
        display: "flex", alignItems: "center",
        border: "1px solid #222", background: "#080808",
    },
    gateIcon: { padding: "0 14px", fontSize: 14 },
    gateInput: {
        flex: 1, background: "transparent", border: "none",
        outline: "none", color: "#f1f5f9", fontSize: 13,
        padding: "14px 0", fontFamily: "'IBM Plex Mono', monospace",
    },
    gateBtn: {
        padding: "14px 20px", background: "#f59e0b", border: "none",
        color: "#000", fontWeight: 800, fontSize: 10, letterSpacing: 2,
        cursor: "pointer", fontFamily: "'IBM Plex Mono', monospace",
    },
    gateError: {
        fontSize: 11, color: "#ef4444",
        background: "rgba(239,68,68,0.06)", padding: "8px 12px",
        border: "1px solid rgba(239,68,68,0.2)",
    },
    gateNote: { fontSize: 9, color: "#1f2937", letterSpacing: 0.5 },

    // Panel
    page: {
        maxWidth: 900, margin: "0 auto",
        padding: "32px 32px 80px",
        fontFamily: "'IBM Plex Mono', monospace",
    },
    header: {
        display: "flex", justifyContent: "space-between",
        alignItems: "flex-start", marginBottom: 32,
        paddingBottom: 24, borderBottom: "1px solid #111",
    },
    pageTitle: { fontSize: 20, fontWeight: 800, color: "#f59e0b", letterSpacing: 4 },
    pageSubtitle: { fontSize: 11, color: "#374151", marginTop: 6 },
    headerRight: { display: "flex", gap: 8 },
    refreshBtn: {
        padding: "8px 16px", background: "transparent",
        border: "1px solid #222", color: "#475569",
        fontSize: 10, letterSpacing: 1.5, cursor: "pointer",
        fontFamily: "'IBM Plex Mono', monospace",
    },
    logoutBtn: {
        padding: "8px 16px", background: "transparent",
        border: "1px solid rgba(239,68,68,0.2)", color: "#ef4444",
        fontSize: 10, letterSpacing: 1.5, cursor: "pointer",
        fontFamily: "'IBM Plex Mono', monospace",
    },

    // Stats
    statsRow: {
        display: "flex", gap: 1, background: "#111",
        border: "1px solid #111", marginBottom: 24,
    },
    statBox: {
        flex: 1, background: "#0a0a0a", padding: "20px",
        display: "flex", flexDirection: "column", gap: 4,
    },
    statVal: { fontSize: 28, fontWeight: 800, letterSpacing: 2 },
    statLabel: { fontSize: 9, color: "#374151", letterSpacing: 2 },

    // Help box
    helpBox: {
        background: "#0a0a0a", border: "1px solid #111",
        borderLeft: "2px solid #f59e0b", padding: "16px 20px",
        marginBottom: 24,
    },
    helpTitle: { fontSize: 9, color: "#f59e0b", letterSpacing: 2, marginBottom: 10 },
    helpSteps: {
        display: "flex", gap: 12, alignItems: "center",
        flexWrap: "wrap", fontSize: 10, color: "#374151",
    },
    helpArrow: { color: "#f59e0b" },

    // Sections
    section: { marginBottom: 32 },
    sectionTitle: {
        fontSize: 10, color: "#475569", letterSpacing: 2,
        marginBottom: 12, display: "flex", alignItems: "center", gap: 8,
    },
    sectionCount: {
        background: "rgba(245,158,11,0.1)", color: "#f59e0b",
        padding: "1px 8px", fontSize: 10, border: "1px solid rgba(245,158,11,0.2)",
    },
    loading: { fontSize: 11, color: "#374151", padding: "16px 0" },
    empty: { fontSize: 11, color: "#1f2937", padding: "16px 0" },

    // Subscriber card
    subCard: {
        background: "#0a0a0a", border: "1px solid #111",
        borderLeft: "2px solid #f59e0b20",
        padding: "16px 20px", marginBottom: 4,
        display: "flex", justifyContent: "space-between",
        alignItems: "center", gap: 16, flexWrap: "wrap",
    },
    subInfo: {
        display: "flex", flexDirection: "column", gap: 4,
    },
    subUsername: { fontSize: 14, fontWeight: 700, color: "#f1f5f9", letterSpacing: 1 },
    subMeta: { fontSize: 10, color: "#374151" },
    subId: { fontSize: 9, color: "#1f2937" },
    subActions: { display: "flex", gap: 8, alignItems: "center" },
    chatIdInput: {
        background: "#080808", border: "1px solid #222",
        color: "#f1f5f9", padding: "8px 12px", fontSize: 11,
        fontFamily: "'IBM Plex Mono', monospace", outline: "none", width: 200,
    },
    approveBtn: {
        padding: "8px 16px", background: "#22c55e", border: "none",
        color: "#000", fontWeight: 800, fontSize: 10, letterSpacing: 1.5,
        cursor: "pointer", fontFamily: "'IBM Plex Mono', monospace",
    },
    rejectBtn: {
        padding: "8px 16px", background: "transparent",
        border: "1px solid rgba(239,68,68,0.3)", color: "#ef4444",
        fontSize: 10, letterSpacing: 1.5, cursor: "pointer",
        fontFamily: "'IBM Plex Mono', monospace",
    },
    feedback: {
        width: "100%", fontSize: 11, color: "#94a3b8",
        paddingTop: 8, borderTop: "1px solid #0f0f0f",
    },
};

