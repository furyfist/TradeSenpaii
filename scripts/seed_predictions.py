"""
Run locally after retraining. Loads each .pt model, runs inference on the last
rows of merged_dataset.csv, then upserts one row per ticker into seeded_predictions.
Never runs on the server — torch stays local only.
"""

import sys, os, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app" / "backend"))

from dotenv import load_dotenv
load_dotenv(ROOT / "app" / "backend" / ".env")

import psycopg2
from predictor import Predictor
from feature_engineer import get_latest_feature_row
from sentiment_loader import load_latest_sentiment

TICKERS = ["KO", "JNJ", "PG", "WMT", "AAPL", "GOOGL"]

TICKER_META = {
    "KO":    {"name": "Coca-Cola",          "sector": "Consumer Staples"},
    "JNJ":   {"name": "Johnson & Johnson",  "sector": "Healthcare"},
    "PG":    {"name": "Procter & Gamble",   "sector": "Consumer Staples"},
    "WMT":   {"name": "Walmart",            "sector": "Retail"},
    "AAPL":  {"name": "Apple",              "sector": "Technology"},
    "GOOGL": {"name": "Alphabet",           "sector": "Technology"},
}

os.chdir(ROOT / "app" / "backend")

def run():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("[ERROR] DATABASE_URL not set in .env")
        sys.exit(1)

    predictor = Predictor()
    conn = psycopg2.connect(db_url)
    cur  = conn.cursor()

    for ticker in TICKERS:
        print(f"\n[{ticker}] Running inference...")
        try:
            feature_df, price_df = get_latest_feature_row(ticker)
            result    = predictor.predict(ticker, feature_df)
            sentiment = load_latest_sentiment(ticker)
            state     = predictor._load_model(ticker)
            meta      = TICKER_META[ticker]

            import pandas as pd
            from datetime import timedelta
            last_date  = pd.to_datetime(price_df["date"].iloc[-1])
            next_day   = last_date + timedelta(days=1)

            sent_score = sentiment["lm_sentiment_score"]
            sent_label = "Positive" if sent_score > 0.5 else ("Negative" if sent_score < -0.5 else "Neutral")

            cur.execute("""
                INSERT INTO seeded_predictions (
                    ticker, name, prediction, confidence,
                    predicted_date, as_of_date,
                    top_signals, sentiment_score, sentiment_label,
                    model_accuracy, sector, input_features,
                    sequence_len, model_type, trained_on, cv_accuracy
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (ticker) DO UPDATE SET
                    prediction      = EXCLUDED.prediction,
                    confidence      = EXCLUDED.confidence,
                    predicted_date  = EXCLUDED.predicted_date,
                    as_of_date      = EXCLUDED.as_of_date,
                    top_signals     = EXCLUDED.top_signals,
                    sentiment_score = EXCLUDED.sentiment_score,
                    sentiment_label = EXCLUDED.sentiment_label,
                    model_accuracy  = EXCLUDED.model_accuracy,
                    cv_accuracy     = EXCLUDED.cv_accuracy
            """, (
                ticker,
                meta["name"],
                result["prediction"],
                result["confidence"],
                str(next_day.date()),
                str(last_date.date()),
                json.dumps(result["top_signals"]),
                sent_score,
                sent_label,
                result["cv_accuracy"],
                meta["sector"],
                len(state["feature_cols"]),
                state["sequence_len"],
                "Transformer (d_model=128, 3 layers, 4 heads)",
                state["trained_on"],
                state["cv_accuracy"],
            ))

            print(f"[{ticker}] {result['prediction']} ({result['confidence']:.2%}) — upserted")

        except Exception as e:
            print(f"[{ticker}] FAILED: {e}")
            import traceback; traceback.print_exc()

    conn.commit()
    cur.close()
    conn.close()
    print("\nAll tickers seeded.")

if __name__ == "__main__":
    run()
