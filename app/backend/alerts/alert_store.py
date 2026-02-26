import sqlite3
import os
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "alerts.db"


def _conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    """Create tables on first run."""
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS sent_alerts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_key   TEXT NOT NULL,
                alert_type  TEXT NOT NULL,
                ticker      TEXT,
                sent_at     TEXT NOT NULL
            )
        """)
        con.execute("""
            CREATE INDEX IF NOT EXISTS idx_alert_key
            ON sent_alerts(alert_key)
        """)
        con.commit()
    print("[INFO][alert_store] DB initialized at", DB_PATH)


def already_sent(alert_key: str, cooldown_hours: int = 24) -> bool:
    """
    Returns True if this alert_key was already sent
    within the cooldown window. Prevents duplicate alerts.
    """
    cutoff = (datetime.now() - timedelta(hours=cooldown_hours)).isoformat()
    with _conn() as con:
        row = con.execute(
            "SELECT id FROM sent_alerts WHERE alert_key = ? AND sent_at > ?",
            (alert_key, cutoff)
        ).fetchone()
    return row is not None


def mark_sent(alert_key: str, alert_type: str, ticker: str = None):
    """Log an alert as sent."""
    with _conn() as con:
        con.execute(
            "INSERT INTO sent_alerts (alert_key, alert_type, ticker, sent_at) VALUES (?,?,?,?)",
            (alert_key, alert_type, ticker, datetime.now().isoformat())
        )
        con.commit()


def get_recent_alerts(hours: int = 24) -> list[dict]:
    """Fetch alerts sent in the last N hours — for debugging."""
    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
    with _conn() as con:
        rows = con.execute(
            "SELECT alert_key, alert_type, ticker, sent_at FROM sent_alerts "
            "WHERE sent_at > ? ORDER BY sent_at DESC",
            (cutoff,)
        ).fetchall()
    return [
        {"alert_key": r[0], "alert_type": r[1], "ticker": r[2], "sent_at": r[3]}
        for r in rows
    ]


if __name__ == "__main__":
    init_db()
    print("already_sent test:", already_sent("test_key"))
    mark_sent("test_key", "test", "KO")
    print("after mark_sent:", already_sent("test_key"))
    print("recent alerts:", get_recent_alerts())