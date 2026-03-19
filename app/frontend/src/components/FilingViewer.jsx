import { useState, useEffect } from "react";
import axios from "axios";

const API = import.meta.env.VITE_API_URL;

const C = {
    bg: "#080808", surface: "#0a0a0a",
    border: "#1a1a1a", border2: "#222222",
    gold: "#f59e0b", goldGlow: "rgba(245,158,11,0.10)",
    red: "#ef4444", redDim: "rgba(239,68,68,0.10)",
    amber: "#f97316", amberDim: "rgba(249,115,22,0.10)",
    blue: "#3b82f6", blueDim: "rgba(59,130,246,0.10)",
    text: "#e5e7eb", textDim: "#6b7280", textMid: "#9ca3af",
    font: "'IBM Plex Mono', 'Courier New', monospace",
};

const TAG_STYLE = {
    negative: { bg: C.redDim, border: C.red, label: "NEGATIVE", col: C.red },
    uncertainty: { bg: C.amberDim, border: C.amber, label: "UNCERTAINTY", col: C.amber },
    litigation: { bg: C.blueDim, border: C.blue, label: "LITIGATION", col: C.blue },
};

const TICKERS = ["KO", "JNJ", "PG", "WMT", "AAPL", "GOOGL"];

// ── Sentence component ────────────────────────────────────────────────────
function Sentence({ s, explain, onExplain }) {
    if (!s.highlighted) {
        return (
            <p style={{
                color: C.textDim, fontFamily: C.font,
                fontSize: 11, lineHeight: 1.8, margin: "0 0 6px 0",
            }}>
                {s.text}
            </p>
        );
    }

    const primaryTag = s.tags[0];
    const style = TAG_STYLE[primaryTag] || TAG_STYLE.negative;

    return (
        <div style={{
            background: style.bg,
            borderLeft: `2px solid ${style.border}`,
            padding: "8px 12px",
            marginBottom: 8,
            position: "relative",
        }}>
            {/* tag badges */}
            <div style={{ display: "flex", gap: 4, marginBottom: 6, flexWrap: "wrap" }}>
                {s.tags.map((tag, i) => {
                    const ts = TAG_STYLE[tag] || TAG_STYLE.negative;
                    return (
                        <span key={i} style={{
                            color: ts.col, fontFamily: C.font,
                            fontSize: 8, letterSpacing: 1,
                            border: `1px solid ${ts.col}`,
                            padding: "1px 5px", opacity: 0.85,
                        }}>
                            ⚠ {ts.label}
                        </span>
                    );
                })}
                <button
                    onClick={() => onExplain(s.text)}
                    style={{
                        marginLeft: "auto",
                        background: "transparent",
                        border: `1px solid ${C.border2}`,
                        color: C.textDim, fontFamily: C.font,
                        fontSize: 8, padding: "1px 8px",
                        cursor: "pointer", letterSpacing: 1,
                    }}
                >
                    EXPLAIN →
                </button>
            </div>

            {/* sentence text */}
            <p style={{
                color: C.text, fontFamily: C.font,
                fontSize: 11, lineHeight: 1.8, margin: 0,
            }}>
                {s.text}
            </p>

            {/* explanation panel */}
            {explain && (
                <div style={{
                    marginTop: 10,
                    padding: "10px 12px",
                    background: "rgba(0,0,0,0.4)",
                    borderTop: `1px solid ${C.border}`,
                }}>
                    {explain === "loading" ? (
                        <span style={{ color: C.textDim, fontFamily: C.font, fontSize: 9 }}>
                            ASKING GROQ...
                        </span>
                    ) : (
                        <p style={{
                            color: C.textMid, fontFamily: C.font,
                            fontSize: 10, lineHeight: 1.7, margin: 0,
                        }}>
                            {explain}
                        </p>
                    )}
                </div>
            )}
        </div>
    );
}

// ── Section panel ─────────────────────────────────────────────────────────
function Section({ sec, explanations, onExplain }) {
    const [open, setOpen] = useState(true);
    const highlighted = sec.sentences.filter(s => s.highlighted).length;

    return (
        <div style={{ marginBottom: 16 }}>
            <div
                onClick={() => setOpen(!open)}
                style={{
                    display: "flex", justifyContent: "space-between",
                    alignItems: "center",
                    padding: "8px 14px",
                    background: C.surface,
                    border: `1px solid ${C.border}`,
                    cursor: "pointer",
                }}
            >
                <span style={{ color: C.gold, fontFamily: C.font, fontSize: 11, letterSpacing: 1 }}>
                    {sec.name.toUpperCase()}
                </span>
                <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                    {highlighted > 0 && (
                        <span style={{
                            color: C.red, fontFamily: C.font, fontSize: 9,
                            background: C.redDim, padding: "2px 6px",
                        }}>
                            {highlighted} FLAGGED
                        </span>
                    )}
                    <span style={{ color: C.textDim, fontFamily: C.font, fontSize: 10 }}>
                        {open ? "▲" : "▼"}
                    </span>
                </div>
            </div>

            {open && (
                <div style={{
                    padding: "14px 16px",
                    border: `1px solid ${C.border}`,
                    borderTop: "none",
                    background: "#090909",
                }}>
                    {sec.sentences.map((s, i) => (
                        <Sentence
                            key={i}
                            s={s}
                            explain={explanations[s.text]}
                            onExplain={onExplain}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}

// ── Main component ─────────────────────────────────────────────────────────
export default function FilingViewer() {
    const [ticker, setTicker] = useState("JNJ");
    const [filingList, setFilingList] = useState([]);
    const [accession, setAccession] = useState("");
    const [filingData, setFilingData] = useState(null);
    const [explanations, setExplanations] = useState({});
    const [loading, setLoading] = useState(false);
    const [listLoading, setListLoading] = useState(false);
    const [error, setError] = useState(null);

    // load filing list when ticker changes
    useEffect(() => {
        const load = async () => {
            setListLoading(true);
            setFilingData(null);
            setAccession("");
            setError(null);
            try {
                const r = await axios.get(`${API}/filing-list?ticker=${ticker}`);
                setFilingList(r.data.filings || []);
            } catch {
                setError("Could not load filing list.");
            } finally {
                setListLoading(false);
            }
        };
        load();
    }, [ticker]);

    // fetch highlighted filing
    const loadFiling = async (acc) => {
        setLoading(true);
        setFilingData(null);
        setExplanations({});
        setError(null);
        try {
            const r = await axios.get(
                `${API}/filing-viewer?ticker=${ticker}&accession=${acc}`
            );
            setFilingData(r.data);
        } catch (e) {
            setError("Could not load filing. EDGAR may be slow — try again.");
        } finally {
            setLoading(false);
        }
    };

    // explain a sentence via Groq
    const explainSentence = async (text) => {
        setExplanations(prev => ({ ...prev, [text]: "loading" }));
        try {
            const r = await axios.post(`${API}/explain-sentence`, { text, ticker });
            setExplanations(prev => ({ ...prev, [text]: r.data.explanation }));
        } catch {
            setExplanations(prev => ({
                ...prev,
                [text]: "Could not generate explanation.",
            }));
        }
    };

    return (
        <div style={{
            background: C.bg, color: C.text,
            fontFamily: C.font, minHeight: "100vh",
            padding: "32px 24px", boxSizing: "border-box",
        }}>

            {/* Header */}
            <div style={{ marginBottom: 24 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
                    <div style={{ width: 3, height: 18, background: C.gold }} />
                    <span style={{ color: C.gold, fontFamily: C.font, fontSize: 9, letterSpacing: 3 }}>
                        SEC FILING INTELLIGENCE
                    </span>
                </div>
                <h1 style={{
                    color: C.text, fontFamily: C.font,
                    fontSize: 22, fontWeight: 700, margin: 0, letterSpacing: 1,
                }}>
                    FILING VIEWER
                </h1>
                <p style={{
                    color: C.textDim, fontFamily: C.font,
                    fontSize: 10, margin: "6px 0 0 0", lineHeight: 1.7,
                }}>
                    Read actual 10-K/10-Q filings. Risk sentences highlighted automatically.
                    Click EXPLAIN to get plain-English interpretation via AI.
                </p>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "260px 1fr", gap: 16 }}>

                {/* LEFT — controls */}
                <div>

                    {/* ticker select */}
                    <div style={{ marginBottom: 12 }}>
                        <div style={{
                            color: C.textDim, fontFamily: C.font,
                            fontSize: 8, letterSpacing: 2, marginBottom: 6,
                        }}>
                            SELECT TICKER
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                            {TICKERS.map(t => (
                                <button key={t} onClick={() => setTicker(t)} style={{
                                    background: ticker === t ? C.gold : C.surface,
                                    color: ticker === t ? C.bg : C.textDim,
                                    border: `1px solid ${ticker === t ? C.gold : C.border}`,
                                    fontFamily: C.font, fontSize: 10,
                                    padding: "6px 12px", cursor: "pointer",
                                    letterSpacing: 1, textAlign: "left",
                                    fontWeight: ticker === t ? 700 : 400,
                                    transition: "all 0.1s",
                                }}>
                                    {t}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* filing list */}
                    <div style={{ marginBottom: 12 }}>
                        <div style={{
                            color: C.textDim, fontFamily: C.font,
                            fontSize: 8, letterSpacing: 2, marginBottom: 6,
                        }}>
                            SELECT FILING
                        </div>

                        {listLoading ? (
                            <div style={{ color: C.textDim, fontFamily: C.font, fontSize: 9 }}>
                                LOADING...
                            </div>
                        ) : (
                            <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                                {filingList.map((f, i) => (
                                    <button key={i} onClick={() => {
                                        setAccession(f.accession);
                                        loadFiling(f.accession);
                                    }} style={{
                                        background: accession === f.accession ? "rgba(245,158,11,0.08)" : C.surface,
                                        color: accession === f.accession ? C.gold : C.textMid,
                                        border: `1px solid ${accession === f.accession ? C.gold : C.border}`,
                                        fontFamily: C.font, fontSize: 9,
                                        padding: "7px 10px", cursor: "pointer",
                                        textAlign: "left", letterSpacing: 0.5,
                                        transition: "all 0.1s",
                                    }}>
                                        <div style={{ fontWeight: 700 }}>{f.form} · {f.date}</div>
                                        <div style={{ color: C.textDim, fontSize: 8, marginTop: 2 }}>
                                            {f.accession}
                                        </div>
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* legend */}
                    <div style={{
                        padding: "12px", border: `1px solid ${C.border}`,
                        background: C.surface,
                    }}>
                        <div style={{
                            color: C.textDim, fontFamily: C.font,
                            fontSize: 8, letterSpacing: 2, marginBottom: 8,
                        }}>
                            HIGHLIGHT LEGEND
                        </div>
                        {Object.entries(TAG_STYLE).map(([tag, s]) => (
                            <div key={tag} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                                <div style={{
                                    width: 10, height: 10,
                                    background: s.bg, border: `1px solid ${s.border}`,
                                }} />
                                <span style={{ color: C.textMid, fontFamily: C.font, fontSize: 9 }}>
                                    {s.label}
                                </span>
                            </div>
                        ))}
                        <p style={{
                            color: C.textDim, fontFamily: C.font,
                            fontSize: 8, lineHeight: 1.6, margin: "8px 0 0 0",
                        }}>
                            Click any highlighted sentence → EXPLAIN for plain English interpretation.
                        </p>
                    </div>
                </div>

                {/* RIGHT — filing content */}
                <div>
                    {!accession && !loading && (
                        <div style={{
                            height: 400, display: "flex", alignItems: "center",
                            justifyContent: "center", border: `1px solid ${C.border}`,
                            color: C.textDim, fontFamily: C.font, fontSize: 11,
                            letterSpacing: 2,
                        }}>
                            SELECT A FILING TO BEGIN
                        </div>
                    )}

                    {loading && (
                        <div style={{
                            height: 400, display: "flex", flexDirection: "column",
                            alignItems: "center", justifyContent: "center",
                            border: `1px solid ${C.border}`,
                            color: C.textDim, fontFamily: C.font,
                            fontSize: 11, letterSpacing: 2, gap: 12,
                        }}>
                            <div>FETCHING FROM EDGAR...</div>
                            <div style={{ fontSize: 9 }}>This takes 5-10 seconds</div>
                        </div>
                    )}

                    {error && !loading && (
                        <div style={{
                            padding: "20px", border: `1px solid ${C.red}`,
                            color: C.red, fontFamily: C.font, fontSize: 11,
                        }}>
                            {error}
                        </div>
                    )}

                    {filingData && !loading && (
                        <>
                            {/* stats bar */}
                            <div style={{
                                display: "grid", gridTemplateColumns: "repeat(4,1fr)",
                                border: `1px solid ${C.border}`,
                                marginBottom: 16,
                            }}>
                                {[
                                    { label: "SENTENCES", val: filingData.stats.total, col: C.textMid },
                                    { label: "FLAGGED", val: filingData.stats.highlighted, col: C.gold },
                                    { label: "FLAG %", val: `${filingData.stats.pct}%`, col: C.amber },
                                    { label: "LITIGATION", val: filingData.stats.litigation, col: C.red },
                                ].map(({ label, val, col }, i, arr) => (
                                    <div key={label} style={{
                                        padding: "10px 14px",
                                        borderRight: i < arr.length - 1 ? `1px solid ${C.border}` : "none",
                                        background: C.surface,
                                    }}>
                                        <div style={{ color: C.textDim, fontFamily: C.font, fontSize: 8, letterSpacing: 1 }}>
                                            {label}
                                        </div>
                                        <div style={{ color: col, fontFamily: C.font, fontSize: 20, fontWeight: 700 }}>
                                            {val}
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {/* sections */}
                            {filingData.sections.map((sec, i) => (
                                <Section
                                    key={i}
                                    sec={sec}
                                    explanations={explanations}
                                    onExplain={explainSentence}
                                />
                            ))}
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}