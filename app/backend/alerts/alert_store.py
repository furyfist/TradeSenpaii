import sqlite3
import os
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "alerts.db"


def _conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    """Create all tables on first run."""
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
    init_subscribers_table()
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

def init_subscribers_table():
    """Create subscribers table if not exists."""
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS subscribers (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                username       TEXT NOT NULL,
                telegram_id    TEXT,
                status         TEXT DEFAULT 'pending',
                requested_at   TEXT NOT NULL,
                approved_at    TEXT
            )
        """)
        con.commit()
    print("[INFO][alert_store] Subscribers table ready")


def add_subscriber(username: str) -> dict:
    """Add a new subscriber request. Status = pending."""
    # Check if already exists
    with _conn() as con:
        existing = con.execute(
            "SELECT id, status FROM subscribers WHERE username = ?",
            (username,)
        ).fetchone()

        if existing:
            return {
                "id":       existing[0],
                "username": username,
                "status":   existing[1],
                "message":  f"Already registered with status: {existing[1]}",
            }

        cur = con.execute(
            "INSERT INTO subscribers (username, status, requested_at) VALUES (?,?,?)",
            (username, "pending", datetime.now().isoformat())
        )
        con.commit()
        return {
            "id":       cur.lastrowid,
            "username": username,
            "status":   "pending",
            "message":  "Request submitted. Pending admin approval.",
        }


def get_all_subscribers() -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT id, username, telegram_id, status, requested_at, approved_at "
            "FROM subscribers ORDER BY requested_at DESC"
        ).fetchall()
    return [
        {
            "id": r[0], "username": r[1], "telegram_id": r[2],
            "status": r[3], "requested_at": r[4], "approved_at": r[5],
        }
        for r in rows
    ]


def approve_subscriber(sub_id: int, telegram_id: str) -> dict:
    """
    Admin approves a subscriber — sets their telegram_id and status=approved.
    telegram_id is entered by admin after verifying with the user.
    """
    with _conn() as con:
        con.execute(
            "UPDATE subscribers SET status=?, telegram_id=?, approved_at=? WHERE id=?",
            ("approved", telegram_id, datetime.now().isoformat(), sub_id)
        )
        con.commit()
        row = con.execute(
            "SELECT id, username, telegram_id, status FROM subscribers WHERE id=?",
            (sub_id,)
        ).fetchone()

    if not row:
        return {"error": "Subscriber not found"}

    return {"id": row[0], "username": row[1], "telegram_id": row[2], "status": row[3]}


def reject_subscriber(sub_id: int) -> dict:
    with _conn() as con:
        con.execute(
            "UPDATE subscribers SET status=? WHERE id=?",
            ("rejected", sub_id)
        )
        con.commit()
    return {"id": sub_id, "status": "rejected"}


def get_approved_chat_ids() -> list[str]:
    """Returns all approved telegram_ids for broadcast."""
    with _conn() as con:
        rows = con.execute(
            "SELECT telegram_id FROM subscribers WHERE status=? AND telegram_id IS NOT NULL",
            ("approved",)
        ).fetchall()
    return [r[0] for r in rows]

if __name__ == "__main__":
    init_db()
    print("already_sent test:", already_sent("test_key"))
    mark_sent("test_key", "test", "KO")
    print("after mark_sent:", already_sent("test_key"))
    print("recent alerts:", get_recent_alerts())