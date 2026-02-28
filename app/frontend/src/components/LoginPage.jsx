import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "../lib/supabase";

export default function LoginPage({ onLogin }) {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const submit = async () => {
        if (!email || !password) return;
        setLoading(true);
        setError(null);

        const { data, error: authError } = await supabase.auth.signInWithPassword({
            email, password
        });

        if (authError) {
            setError(authError.message);
            setLoading(false);
            return;
        }

        // Check admin role
        const role = data.user?.user_metadata?.role;
        if (role !== "admin") {
            setError("Access denied. Admin only.");
            await supabase.auth.signOut();
            setLoading(false);
            return;
        }

        // Pass JWT up to App so AdminPanel can use it
        onLogin(data.session);
        navigate("/ts-ops-7x9k");
    };

    return (
        <div style={s.page}>
            <div style={s.box}>
                <div style={s.title}>⬡ ADMIN LOGIN</div>
                <div style={s.subtitle}>TradeSenpai · Restricted Access</div>

                <div style={s.field}>
                    <span style={s.fieldLabel}>EMAIL</span>
                    <input
                        style={s.input}
                        type="email"
                        value={email}
                        onChange={e => setEmail(e.target.value)}
                        onKeyDown={e => e.key === "Enter" && submit()}
                        placeholder="admin@email.com"
                        autoFocus
                    />
                </div>

                <div style={s.field}>
                    <span style={s.fieldLabel}>PASSWORD</span>
                    <input
                        style={s.input}
                        type="password"
                        value={password}
                        onChange={e => setPassword(e.target.value)}
                        onKeyDown={e => e.key === "Enter" && submit()}
                        placeholder="••••••••"
                    />
                </div>

                {error && <div style={s.error}>⚠ {error}</div>}

                <button
                    style={{ ...s.btn, ...(loading ? s.btnDisabled : {}) }}
                    onClick={submit}
                    disabled={loading}
                >
                    {loading ? "AUTHENTICATING..." : "LOGIN →"}
                </button>

                <div style={s.note}>
                    Supabase JWT · Admin role required · Session expires in 1 hour
                </div>
            </div>
        </div>
    );
}

const s = {
    page: {
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#080808",
        fontFamily: "'IBM Plex Mono', monospace",
    },
    box: {
        background: "#0a0a0a",
        border: "1px solid #151515",
        borderTop: "2px solid #f59e0b",
        padding: "48px",
        width: 420,
        display: "flex",
        flexDirection: "column",
        gap: 20,
    },
    title: { fontSize: 18, fontWeight: 800, color: "#f59e0b", letterSpacing: 4 },
    subtitle: { fontSize: 10, color: "#374151", letterSpacing: 2, marginBottom: 8 },
    field: { display: "flex", flexDirection: "column", gap: 6 },
    fieldLabel: { fontSize: 9, color: "#374151", letterSpacing: 2 },
    input: {
        background: "#080808",
        border: "1px solid #222",
        outline: "none",
        color: "#f1f5f9",
        fontSize: 13,
        padding: "12px 14px",
        fontFamily: "'IBM Plex Mono', monospace",
    },
    error: {
        background: "rgba(239,68,68,0.06)",
        border: "1px solid rgba(239,68,68,0.2)",
        color: "#ef4444",
        padding: "10px 14px",
        fontSize: 11,
    },
    btn: {
        padding: "14px",
        background: "#f59e0b",
        border: "none",
        color: "#000",
        fontWeight: 800,
        fontSize: 11,
        letterSpacing: 2,
        cursor: "pointer",
        fontFamily: "'IBM Plex Mono', monospace",
    },
    btnDisabled: { opacity: 0.5, cursor: "not-allowed" },
    note: { fontSize: 9, color: "#1f2937", letterSpacing: 0.5, textAlign: "center" },
};