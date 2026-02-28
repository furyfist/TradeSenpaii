import os
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

# ── Connection 

def _conn():
    """
    Always use service_role key for backend DB access.
    This bypasses RLS — backend has full access.
    """
    url = os.getenv("SUPABASE_POOLER_URL") or os.getenv("SUPABASE_DB_URL")
    if url and "sslmode" not in url:
        url += ("&" if "?" in url else "?") + "sslmode=require"
    # Transaction pooler (port 6543) works when session pooler (5432) is blocked
    if url:
        url = url.replace(":5432/", ":6543/")
    return psycopg2.connect(url)


# ── Alert Deduplication 

def already_sent(alert_key: str, cooldown_hours: int = 24) -> bool:
    cutoff = datetime.now() - timedelta(hours=cooldown_hours)
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(
                "SELECT id FROM sent_alerts WHERE alert_key = %s AND sent_at > %s",
                (alert_key, cutoff)
            )
            return cur.fetchone() is not None


def mark_sent(alert_key: str, alert_type: str, ticker: str = None):
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(
                "INSERT INTO sent_alerts (alert_key, alert_type, ticker) VALUES (%s, %s, %s)",
                (alert_key, alert_type, ticker)
            )
        con.commit()


def get_recent_alerts(hours: int = 24) -> list[dict]:
    cutoff = datetime.now() - timedelta(hours=hours)
    with _conn() as con:
        with con.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT alert_key, alert_type, ticker, sent_at
                   FROM sent_alerts WHERE sent_at > %s
                   ORDER BY sent_at DESC""",
                (cutoff,)
            )
            return [dict(r) for r in cur.fetchall()]


# ── Subscribers 

def add_subscriber(username: str, telegram_id: str = None) -> dict:
    with _conn() as con:
        with con.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

            # Check if already exists
            cur.execute(
                "SELECT id, status FROM subscribers WHERE username = %s",
                (username,)
            )
            existing = cur.fetchone()
            if existing:
                return {
                    "id":       existing["id"],
                    "username": username,
                    "status":   existing["status"],
                    "message":  f"Already registered with status: {existing['status']}",
                }

            if telegram_id:
                # Auto-approve
                cur.execute(
                    """INSERT INTO subscribers
                       (username, telegram_id, status, approved_at)
                       VALUES (%s, %s, 'approved', NOW())
                       RETURNING id""",
                    (username, telegram_id)
                )
                new_id = cur.fetchone()["id"]
                con.commit()
                return {
                    "id":       new_id,
                    "username": username,
                    "status":   "approved",
                    "message":  "Auto-approved successfully.",
                }
            else:
                # Pending — needs admin approval
                cur.execute(
                    """INSERT INTO subscribers (username, status)
                       VALUES (%s, 'pending')
                       RETURNING id""",
                    (username,)
                )
                new_id = cur.fetchone()["id"]
                con.commit()
                return {
                    "id":       new_id,
                    "username": username,
                    "status":   "pending",
                    "message":  "Request submitted. Pending admin approval.",
                }


def get_all_subscribers() -> list[dict]:
    with _conn() as con:
        with con.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT id, username, telegram_id, status, requested_at, approved_at
                   FROM subscribers ORDER BY requested_at DESC"""
            )
            rows = cur.fetchall()
    return [dict(r) for r in rows]


def approve_subscriber(sub_id: int, telegram_id: str) -> dict:
    with _conn() as con:
        with con.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """UPDATE subscribers
                   SET status='approved', telegram_id=%s, approved_at=NOW()
                   WHERE id=%s
                   RETURNING id, username, telegram_id, status""",
                (telegram_id, sub_id)
            )
            row = cur.fetchone()
            con.commit()
    if not row:
        return {"error": "Subscriber not found"}
    return dict(row)


def reject_subscriber(sub_id: int) -> dict:
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(
                "UPDATE subscribers SET status='rejected' WHERE id=%s",
                (sub_id,)
            )
        con.commit()
    return {"id": sub_id, "status": "rejected"}


def get_approved_chat_ids() -> list[str]:
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(
                """SELECT telegram_id FROM subscribers
                   WHERE status='approved' AND telegram_id IS NOT NULL"""
            )
            return [r[0] for r in cur.fetchall()]


# ── Prediction History 

def log_prediction(ticker: str, predicted_date: str,
                   prediction: str, confidence: float):
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(
                """INSERT INTO prediction_history
                   (ticker, predicted_date, prediction, confidence)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (ticker, predicted_date) DO NOTHING""",
                (ticker, predicted_date, prediction, confidence)
            )
        con.commit()
    print(f"[INFO][alert_store] Logged prediction: {ticker} {prediction} for {predicted_date}")


def fill_actual_outcomes() -> list[dict]:
    import yfinance as yf
    with _conn() as con:
        with con.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT id, ticker, predicted_date, prediction
                   FROM prediction_history
                   WHERE actual_direction IS NULL
                   AND predicted_date <= CURRENT_DATE"""
            )
            rows = cur.fetchall()

    outcomes = []
    for row in rows:
        try:
            hist = yf.Ticker(row["ticker"]).history(period="5d")
            if len(hist) < 2:
                continue

            actual_return    = float(
                (hist["Close"].iloc[-1] - hist["Close"].iloc[-2])
                / hist["Close"].iloc[-2] * 100
            )
            actual_direction = "UP" if actual_return > 0 else "DOWN"
            correct          = 1 if row["prediction"] == actual_direction else 0

            with _conn() as con:
                with con.cursor() as cur:
                    cur.execute(
                        """UPDATE prediction_history
                           SET actual_direction=%s, actual_return=%s, correct=%s
                           WHERE id=%s""",
                        (actual_direction, round(actual_return, 4), correct, row["id"])
                    )
                con.commit()

            outcomes.append({
                "ticker":           row["ticker"],
                "prediction":       row["prediction"],
                "actual_direction": actual_direction,
                "actual_return":    round(actual_return, 2),
                "correct":          bool(correct),
            })
            print(f"[INFO][alert_store] Outcome: {row['ticker']} "
                  f"predicted={row['prediction']} actual={actual_direction} "
                  f"correct={bool(correct)}")

        except Exception as e:
            print(f"[ERROR][alert_store] fill_actual_outcomes {row['ticker']}: {e}")

    return outcomes


def get_accuracy_stats() -> dict:
    with _conn() as con:
        with con.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT ticker,
                          COUNT(*)    AS total,
                          SUM(correct) AS correct
                   FROM prediction_history
                   WHERE correct IS NOT NULL
                   GROUP BY ticker"""
            )
            rows = cur.fetchall()

    return {
        r["ticker"]: {
            "total":    r["total"],
            "correct":  r["correct"],
            "accuracy": round((r["correct"] / r["total"] * 100)
                              if r["total"] > 0 else 0, 1),
        }
        for r in rows
    }