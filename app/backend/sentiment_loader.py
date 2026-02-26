import pandas as pd
import numpy as np
from pathlib import Path

# Base path 
BASE_PATH = Path(__file__).resolve().parent.parent.parent / "stock-analysis" / "data" / "processed"


def _get_sentiment_csv(ticker: str) -> Path:
    return BASE_PATH / ticker / "sec_sentiment_features.csv"


def _compute_derived(df: pd.DataFrame) -> pd.DataFrame:
    df["lm_sentiment_ma5"]      = df["lm_sentiment_score"].rolling(5,  min_periods=1).mean()
    df["lm_sentiment_ma20"]     = df["lm_sentiment_score"].rolling(20, min_periods=1).mean()
    df["lm_sentiment_delta"]    = df["lm_sentiment_score"] - df["lm_sentiment_ma20"]
    unc_mean = df["lm_uncertain_pct"].rolling(20, min_periods=1).mean()
    unc_std  = df["lm_uncertain_pct"].rolling(20, min_periods=1).std().replace(0, np.nan)
    df["lm_uncertainty_zscore"] = ((df["lm_uncertain_pct"] - unc_mean) / unc_std).fillna(0)
    lit_mean = df["lm_litigious"].rolling(20, min_periods=1).mean()
    df["lm_litigation_spike"]   = (df["lm_litigious"] > lit_mean * 1.5).astype(int)
    df["lm_neg_dominant"]       = (df["lm_neg_pct"] > df["lm_pos_pct"]).astype(int)
    return df


def load_latest_sentiment(ticker: str) -> dict:
    df = pd.read_csv(_get_sentiment_csv(ticker), parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df = _compute_derived(df)
    latest = df.iloc[-1]

    return {
        "date":                  str(latest["date"].date()),
        "lm_sentiment_score":    float(latest["lm_sentiment_score"]),
        "lm_pos_pct":            float(latest["lm_pos_pct"]),
        "lm_neg_pct":            float(latest["lm_neg_pct"]),
        "lm_uncertain_pct":      float(latest["lm_uncertain_pct"]),
        "lm_litigious":          float(latest["lm_litigious"]),
        "lm_constraining":       float(latest["lm_constraining"]),
        "lm_positive":           float(latest["lm_positive"]),
        "lm_negative":           float(latest["lm_negative"]),
        "lm_uncertain":          float(latest["lm_uncertain"]),
        "lm_sentiment_ma5":      float(latest["lm_sentiment_ma5"]),
        "lm_sentiment_ma20":     float(latest["lm_sentiment_ma20"]),
        "lm_sentiment_delta":    float(latest["lm_sentiment_delta"]),
        "lm_uncertainty_zscore": float(latest["lm_uncertainty_zscore"]),
        "lm_litigation_spike":   float(latest["lm_litigation_spike"]),
        "lm_neg_dominant":       float(latest["lm_neg_dominant"]),
        "form_type":             str(latest["form_type"]),
    }


def load_sentiment_history(ticker: str, n: int = 50) -> list[dict]:
    df = pd.read_csv(_get_sentiment_csv(ticker), parse_dates=["date"])
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