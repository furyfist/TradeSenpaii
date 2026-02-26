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
    init_predictions_table()
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
    init_subscribers_table()
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

def init_predictions_table():
    """Create prediction_history table if not exists."""
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS prediction_history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker          TEXT NOT NULL,
                predicted_date  TEXT NOT NULL,
                prediction      TEXT NOT NULL,
                confidence      REAL NOT NULL,
                actual_direction TEXT,
                actual_return    REAL,
                correct          INTEGER,
                logged_at        TEXT NOT NULL
            )
        """)
        con.commit()


def log_prediction(ticker: str, predicted_date: str, prediction: str, confidence: float):
    """Log a new prediction. Outcome filled in next day by scheduler."""
    init_predictions_table()
    with _conn() as con:
        # Avoid duplicate for same ticker + date
        existing = con.execute(
            "SELECT id FROM prediction_history WHERE ticker=? AND predicted_date=?",
            (ticker, predicted_date)
        ).fetchone()
        if existing:
            return
        con.execute(
            """INSERT INTO prediction_history
               (ticker, predicted_date, prediction, confidence, logged_at)
               VALUES (?,?,?,?,?)""",
            (ticker, predicted_date, prediction, confidence, datetime.now().isoformat())
        )
        con.commit()
    print(f"[INFO][alert_store] Logged prediction: {ticker} {prediction} for {predicted_date}")


def fill_actual_outcomes():
    """
    Called by evening scheduler job.
    Finds predictions with no actual_direction yet,
    fetches real price movement, marks correct/incorrect.
    Returns list of outcome dicts for the evening brief.
    """
    import yfinance as yf
    init_predictions_table()

    with _conn() as con:
        rows = con.execute(
            """SELECT id, ticker, predicted_date, prediction
               FROM prediction_history
               WHERE actual_direction IS NULL
               AND predicted_date <= date('now')""",
        ).fetchall()

    outcomes = []
    for row in rows:
        pred_id, ticker, predicted_date, prediction = row
        try:
            hist = yf.Ticker(ticker).history(period="5d")
            if len(hist) < 2:
                continue

            actual_return    = float(
                (hist["Close"].iloc[-1] - hist["Close"].iloc[-2])
                / hist["Close"].iloc[-2] * 100
            )
            actual_direction = "UP" if actual_return > 0 else "DOWN"
            correct          = 1 if prediction == actual_direction else 0

            with _conn() as con:
                con.execute(
                    """UPDATE prediction_history
                       SET actual_direction=?, actual_return=?, correct=?
                       WHERE id=?""",
                    (actual_direction, round(actual_return, 4), correct, pred_id)
                )
                con.commit()

            outcomes.append({
                "ticker":           ticker,
                "prediction":       prediction,
                "actual_direction": actual_direction,
                "actual_return":    round(actual_return, 2),
                "correct":          bool(correct),
            })
            print(f"[INFO][alert_store] Outcome filled: {ticker} predicted={prediction} actual={actual_direction} correct={bool(correct)}")

        except Exception as e:
            print(f"[ERROR][alert_store] fill_actual_outcomes {ticker}: {e}")

    return outcomes


def get_accuracy_stats() -> dict:
    """
    Returns real accuracy stats from prediction_history.
    Used by evening brief and weekly digest.
    """
    init_predictions_table()
    with _conn() as con:
        rows = con.execute(
            """SELECT ticker,
                      COUNT(*) as total,
                      SUM(correct) as correct
               FROM prediction_history
               WHERE correct IS NOT NULL
               GROUP BY ticker"""
        ).fetchall()

    stats = {}
    for row in rows:
        ticker, total, correct = row
        stats[ticker] = {
            "total":    total,
            "correct":  correct,
            "accuracy": round((correct / total * 100) if total > 0 else 0, 1),
        }
    return stats

if __name__ == "__main__":
    init_db()
    print("already_sent test:", already_sent("test_key"))
    mark_sent("test_key", "test", "KO")
    print("after mark_sent:", already_sent("test_key"))
    print("recent alerts:", get_recent_alerts())