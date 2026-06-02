import numpy as np
import pandas as pd
from pathlib import Path

_here = Path(__file__).resolve().parent
BASE_PATH = next(
    p / "stock-analysis" / "data" / "processed"
    for p in [_here, _here.parent, _here.parent.parent]
    if (p / "stock-analysis" / "data" / "processed").exists()
)

def fetch_recent_prices(ticker: str = "KO", days: int = 100) -> pd.DataFrame:
    csv_path = BASE_PATH / ticker / "merged_dataset.csv"
    df = pd.read_csv(csv_path, usecols=["date", "open", "high", "low", "close", "volume"])
    df["date"] = pd.to_datetime(df["date"])
    return df.tail(days).reset_index(drop=True)


def engineer_features(df: pd.DataFrame, sentiment: dict) -> pd.DataFrame:
    """
    Replicates the exact same feature engineering as training.
    Must match merged_dataset.csv column order exactly.
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # ── Price features ──
    df["daily_return"]  = df["close"].pct_change() * 100
    df["gap_pct"]       = ((df["open"] - df["close"].shift(1)) / df["close"].shift(1)) * 100
    df["close_lag1"]    = df["close"].shift(1)
    df["close_lag5"]    = df["close"].shift(5)
    df["close_lag10"]   = df["close"].shift(10)

    # ── Moving averages ──
    df["ma_7"]   = df["close"].rolling(7).mean()
    df["ma_20"]  = df["close"].rolling(20).mean()
    df["ma_50"]  = df["close"].rolling(50).mean()
    df["ma_200"] = df["close"].rolling(200).mean()

    # ── Volatility ──
    df["volatility_20"] = df["daily_return"].rolling(20).std()
    df["volatility_30"] = df["daily_return"].rolling(30).std()

    # ── Volume ──
    df["avg_volume_20"]  = df["volume"].rolling(20).mean()
    df["volume_ratio_20"]= df["volume"] / df["avg_volume_20"]

    # ── Momentum ──
    df["momentum_5d"]  = df["close"].pct_change(5)  * 100
    df["momentum_10d"] = df["close"].pct_change(10) * 100

    # ── Bollinger Bands ──
    df["distance_from_ma20"] = ((df["close"] - df["ma_20"]) / df["ma_20"]) * 100
    df["distance_from_ma50"] = ((df["close"] - df["ma_50"]) / df["ma_50"]) * 100
    std_20 = df["close"].rolling(20).std()
    df["upper_band_20"] = df["ma_20"] + (2 * std_20)
    df["lower_band_20"] = df["ma_20"] - (2 * std_20)

    # ── RSI ──
    delta = df["close"].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, np.nan)
    df["rsi_14"] = 100 - (100 / (1 + rs))

    # ── Market regime ──
    df["market_regime_enc"] = (df["close"] > df["ma_200"]).astype(int)

    # ── Calendar ──
    df["day_of_week"] = df["date"].dt.dayofweek
    df["month"]       = df["date"].dt.month
    df["quarter"]     = df["date"].dt.quarter

    # ── Sentiment features (forward filled from latest filing) ──
    for col, val in sentiment.items():
        if col not in ["date", "form_type"]:
            df[col] = val

    # ── Derived sentiment features ──
    df["lm_sentiment_lag1"]  = df["lm_sentiment_score"].shift(1)
    df["lm_sentiment_lag5"]  = df["lm_sentiment_score"].shift(5)
    df["lm_sentiment_lag10"] = df["lm_sentiment_score"].shift(10)
    df["lm_neg_pct_lag1"]    = df["lm_neg_pct"].shift(1)
    df["lm_uncertain_lag1"]  = df["lm_uncertain_pct"].shift(1)

    # ── Return lags ──
    df["return_lag1"] = df["daily_return"].shift(1)
    df["return_lag2"] = df["daily_return"].shift(2)
    df["return_lag3"] = df["daily_return"].shift(3)
    df["return_lag5"] = df["daily_return"].shift(5)

    # ── Regime features ──
    df["vol_regime"]      = (df["volatility_20"] > df["volatility_20"].rolling(60).mean()).astype(int)
    df["rsi_oversold"]    = (df["rsi_14"] < 30).astype(int)
    df["rsi_overbought"]  = (df["rsi_14"] > 70).astype(int)
    df["ma7_above_ma20"]  = (df["ma_7"]  > df["ma_20"]).astype(int)
    df["ma20_above_ma50"] = (df["ma_20"] > df["ma_50"]).astype(int)
    df["volume_surge"]    = (df["volume_ratio_20"] > 1.5).astype(int)

    # ── Interaction features ──
    df["sent_x_vol"] = df["lm_sentiment_score"] * df["volatility_20"]
    df["sent_x_unc"] = df["lm_sentiment_score"] * df["lm_uncertain_pct"]

    df = df.dropna().reset_index(drop=True)
    return df


def get_latest_feature_row(ticker: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    csv_path = BASE_PATH / ticker / "merged_dataset.csv"
    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"])
    price_df = df[["date", "open", "high", "low", "close", "volume"]].copy()
    return df, price_df