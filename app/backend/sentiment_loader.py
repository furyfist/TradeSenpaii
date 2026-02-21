import pandas as pd
from pathlib import Path

# Path to your existing processed sentiment CSV
SENTIMENT_CSV = Path("../../stock-analysis/data/processed/sec_sentiment_features.csv")


def load_latest_sentiment() -> dict:
    """
    Returns the most recent sentiment scores from the LM pipeline.
    """
    df = pd.read_csv(SENTIMENT_CSV, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    latest = df.iloc[-1]

    return {
        "date":               str(latest["date"].date()),
        "lm_sentiment_score": float(latest["lm_sentiment_score"]),
        "lm_pos_pct":         float(latest["lm_pos_pct"]),
        "lm_neg_pct":         float(latest["lm_neg_pct"]),
        "lm_uncertain_pct":   float(latest["lm_uncertain_pct"]),
        "lm_litigious":       float(latest["lm_litigious"]),
        "lm_constraining":    float(latest["lm_constraining"]),
        "lm_positive":        float(latest["lm_positive"]),
        "lm_negative":        float(latest["lm_negative"]),
        "lm_uncertain":       float(latest["lm_uncertain"]),
        "lm_sentiment_ma5":   float(latest["lm_sentiment_ma5"]),
        "lm_sentiment_ma20":  float(latest["lm_sentiment_ma20"]),
        "lm_sentiment_delta": float(latest["lm_sentiment_delta"]),
        "lm_uncertainty_zscore": float(latest["lm_uncertainty_zscore"]),
        "lm_litigation_spike":   float(latest["lm_litigation_spike"]),
        "lm_neg_dominant":       float(latest["lm_neg_dominant"]),
        "form_type":             str(latest["form_type"]),
    }


def load_sentiment_history(n: int = 50) -> list[dict]:
    """
    Returns last n sentiment data points for the chart.
    """
    df = pd.read_csv(SENTIMENT_CSV, parse_dates=["date"])
    df = df.sort_values("date").tail(n).reset_index(drop=True)

    return [
        {
            "date":               str(row["date"].date()),
            "lm_sentiment_score": float(row["lm_sentiment_score"]),
            "lm_neg_pct":         float(row["lm_neg_pct"]),
            "lm_uncertain_pct":   float(row["lm_uncertain_pct"]),
            "form_type":          str(row["form_type"]),
        }
        for _, row in df.iterrows()
    ]