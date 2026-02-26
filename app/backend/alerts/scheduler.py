import sys, os
import yfinance as yf
from alerts.alert_store import get_accuracy_stats

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron         import CronTrigger
from datetime import datetime

from predictor        import Predictor
from feature_engineer import get_latest_feature_row
from alerts.telegram_bot import send_message
from alerts.alert_store  import init_db, already_sent, mark_sent
from alerts.digest       import fmt_morning_brief, fmt_evening_brief, fmt_weekly_digest
from alerts.watcher      import run_all_checks

SUPPORTED_TICKERS = ["KO", "JNJ", "PG", "WMT", "AAPL", "GOOGL"]
_predictor = Predictor()
_accuracy_tracker = {"total": 0, "correct": 0}
_last_predictions: dict = {}


def _get_all_predictions() -> list[dict]:
    results = []
    for ticker in SUPPORTED_TICKERS:
        try:
            feature_df, _ = get_latest_feature_row(ticker)
            result = _predictor.predict(ticker, feature_df)
            results.append({
                "ticker":     ticker,
                "prediction": result["prediction"],
                "confidence": result["confidence"],
            })
            _last_predictions[ticker] = result["prediction"]
        except Exception as e:
            print(f"[ERROR][scheduler] Could not predict {ticker}: {e}")
    return results


def job_morning_brief():
    """9:30 AM ET — send all 6 predictions."""
    print(f"[INFO][scheduler] Running morning brief job")
    key = f"morning_{datetime.now().strftime('%Y%m%d')}"
    if already_sent(key, cooldown_hours=20):
        print(f"[INFO][scheduler] Morning brief already sent today, skipping")
        return
    predictions = _get_all_predictions()
    if predictions:
        msg = fmt_morning_brief(predictions)
        send_message(msg)
        mark_sent(key, "morning_brief")


def job_evening_brief():
    """4:15 PM ET — actual outcomes vs predictions from DB."""
    print(f"[INFO][scheduler] Running evening brief job")
    key = f"evening_{datetime.now().strftime('%Y%m%d')}"
    if already_sent(key, cooldown_hours=20):
        return

    from alerts.alert_store import fill_actual_outcomes, get_accuracy_stats
    outcomes = fill_actual_outcomes()
    stats    = get_accuracy_stats()

    total   = sum(s["total"]   for s in stats.values())
    correct = sum(s["correct"] for s in stats.values())
    accuracy_tracker = {"total": total, "correct": correct}

    if outcomes:
        msg = fmt_evening_brief(outcomes, accuracy_tracker)
        send_message(msg)
        mark_sent(key, "evening_brief")
    else:
        print(f"[INFO][scheduler] No outcomes to report yet")


def job_weekly_digest():
    """Sunday 6 PM ET — weekly accuracy summary."""
    print(f"[INFO][scheduler] Running weekly digest job")
    key = f"weekly_{datetime.now().strftime('%Y%W')}"
    if already_sent(key, cooldown_hours=100):
        return

    # Simple weekly stats from accuracy tracker
    weekly_stats = get_accuracy_stats()

    if not weekly_stats:
        print("[WARN][scheduler] No accuracy data yet, skipping weekly digest")
        return

    msg = fmt_weekly_digest(weekly_stats)
    send_message(msg)
    mark_sent(key, "weekly_digest")


def job_signal_watcher():
    """Every 2 hours — check for direction flips, sentiment spikes, litigation."""
    run_all_checks()


def create_scheduler() -> BackgroundScheduler:
    """Build and return configured scheduler. Call start() separately."""
    init_db()
    scheduler = BackgroundScheduler(timezone="America/New_York")

    # Morning brief — 9:30 AM ET weekdays
    scheduler.add_job(
        job_morning_brief,
        CronTrigger(day_of_week="mon-fri", hour=9, minute=30, timezone="America/New_York"),
        id="morning_brief", replace_existing=True,
    )

    # Evening brief — 4:15 PM ET weekdays
    scheduler.add_job(
        job_evening_brief,
        CronTrigger(day_of_week="mon-fri", hour=16, minute=15, timezone="America/New_York"),
        id="evening_brief", replace_existing=True,
    )

    # Weekly digest — Sunday 6 PM ET
    scheduler.add_job(
        job_weekly_digest,
        CronTrigger(day_of_week="sun", hour=18, minute=0, timezone="America/New_York"),
        id="weekly_digest", replace_existing=True,
    )

    # Signal watcher — every 2 hours
    scheduler.add_job(
        job_signal_watcher,
        CronTrigger(hour="*/2", timezone="America/New_York"),
        id="signal_watcher", replace_existing=True,
    )

    print("[INFO][scheduler] All jobs registered:")
    for job in scheduler.get_jobs():
        print(f"  · {job.id}")

    return scheduler