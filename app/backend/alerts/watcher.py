import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

from sentiment_loader import load_latest_sentiment
from feature_engineer import get_latest_feature_row
from predictor import Predictor
from alerts.telegram_bot import send_message
from alerts.alert_store  import already_sent, mark_sent
from alerts.digest       import (
    fmt_direction_flip, fmt_sentiment_spike, fmt_litigation_spike
)

SUPPORTED_TICKERS = ["KO", "JNJ", "PG", "WMT", "AAPL", "GOOGL"]
DATA_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "stock-analysis" / "data" / "processed"

_predictor = Predictor()
_last_predictions: dict = {}  # in-memory store for direction flip detection


def check_direction_flip(ticker: str):
    """Alert if model flipped direction since last check."""
    try:
        feature_df, _ = get_latest_feature_row(ticker)
        result = _predictor.predict(ticker, feature_df)
        new_pred = result["prediction"]
        confidence = result["confidence"]

        old_pred = _last_predictions.get(ticker)
        _last_predictions[ticker] = new_pred

        if old_pred and old_pred != new_pred:
            key = f"flip_{ticker}_{datetime.now().strftime('%Y%m%d')}"
            if not already_sent(key, cooldown_hours=12):
                msg = fmt_direction_flip(ticker, old_pred, new_pred, confidence)
                send_message(msg)
                mark_sent(key, "direction_flip", ticker)
                print(f"[INFO][watcher] Direction flip alert sent for {ticker}")

    except Exception as e:
        print(f"[ERROR][watcher] check_direction_flip {ticker}: {e}")


def check_sentiment_spike(ticker: str, zscore_threshold: float = 2.0):
    """Alert if latest sentiment is > N std devs from ticker average."""
    try:
        sentiment = load_latest_sentiment(ticker)
        score     = sentiment.get("lm_sentiment_score", 0)
        zscore    = sentiment.get("lm_uncertainty_zscore", 0)

        if abs(zscore) > zscore_threshold:
            key = f"sent_spike_{ticker}_{datetime.now().strftime('%Y%m%d')}"
            if not already_sent(key, cooldown_hours=24):
                msg = fmt_sentiment_spike(ticker, score, zscore)
                send_message(msg)
                mark_sent(key, "sentiment_spike", ticker)
                print(f"[INFO][watcher] Sentiment spike alert sent for {ticker}")

    except Exception as e:
        print(f"[ERROR][watcher] check_sentiment_spike {ticker}: {e}")


def check_litigation_spike(ticker: str):
    """Alert if litigation language spiked in latest filing."""
    try:
        sentiment = load_latest_sentiment(ticker)
        spike     = sentiment.get("lm_litigation_spike", 0)

        if spike:
            key = f"litigation_{ticker}_{datetime.now().strftime('%Y%m%d')}"
            if not already_sent(key, cooldown_hours=48):
                msg = fmt_litigation_spike(ticker)
                send_message(msg)
                mark_sent(key, "litigation_spike", ticker)
                print(f"[INFO][watcher] Litigation spike alert sent for {ticker}")

    except Exception as e:
        print(f"[ERROR][watcher] check_litigation_spike {ticker}: {e}")


def run_all_checks():
    """Run all signal checks for all tickers. Called by scheduler."""
    print(f"[INFO][watcher] Running signal checks at {datetime.now()}")
    for ticker in SUPPORTED_TICKERS:
        check_direction_flip(ticker)
        check_sentiment_spike(ticker)
        check_litigation_spike(ticker)