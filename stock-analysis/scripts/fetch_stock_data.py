import sys
import numpy as np
import pandas as pd
import yfinance as yf
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent))
from config import TICKERS, cleaned_prices_path

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--ticker", required=True, choices=list(TICKERS.keys()))
args   = parser.parse_args()

TICKER = args.ticker

# ─────────────────────────────────────────────
def fetch_and_engineer(ticker: str) -> pd.DataFrame:
    print(f"[INFO] Downloading {ticker} price data...")
    df = yf.download(ticker, start="1994-01-01", end=datetime.today().strftime("%Y-%m-%d"), progress=False)

    df = df.reset_index()
    df.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in df.columns]
    df = df.rename(columns={"price": "close"}) if "price" in df.columns else df
    df = df[["date", "open", "high", "low", "close", "volume"]].copy()
    df = df.dropna().reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"]).dt.date.astype(str)

    print(f"[INFO] Engineering features for {ticker}...")

    # ── Returns ──
    df["daily_return"] = df["close"].pct_change() * 100
    df["gap_pct"]      = ((df["open"] - df["close"].shift(1)) / df["close"].shift(1)) * 100

    # ── Lags ──
    df["close_lag1"]  = df["close"].shift(1)
    df["close_lag5"]  = df["close"].shift(5)
    df["close_lag10"] = df["close"].shift(10)

    # ── Moving averages ──
    df["ma_7"]   = df["close"].rolling(7).mean()
    df["ma_20"]  = df["close"].rolling(20).mean()
    df["ma_50"]  = df["close"].rolling(50).mean()
    df["ma_200"] = df["close"].rolling(200).mean()

    # ── Volatility ──
    df["volatility_20"] = df["daily_return"].rolling(20).std()
    df["volatility_30"] = df["daily_return"].rolling(30).std()

    # ── Volume ──
    df["avg_volume_20"]   = df["volume"].rolling(20).mean()
    df["volume_ratio_20"] = df["volume"] / df["avg_volume_20"]

    # ── Momentum ──
    df["momentum_5d"]  = df["close"].pct_change(5)  * 100
    df["momentum_10d"] = df["close"].pct_change(10) * 100

    # ── Bollinger Bands ──
    std_20 = df["close"].rolling(20).std()
    df["distance_from_ma20"] = ((df["close"] - df["ma_20"]) / df["ma_20"]) * 100
    df["distance_from_ma50"] = ((df["close"] - df["ma_50"]) / df["ma_50"]) * 100
    df["upper_band_20"]      = df["ma_20"] + (2 * std_20)
    df["lower_band_20"]      = df["ma_20"] - (2 * std_20)

    # ── RSI ──
    delta = df["close"].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, np.nan)
    df["rsi_14"] = 100 - (100 / (1 + rs))

    # ── Calendar ──
    df["date"]        = pd.to_datetime(df["date"])
    df["day_of_week"] = df["date"].dt.dayofweek
    df["month"]       = df["date"].dt.month
    df["quarter"]     = df["date"].dt.quarter

    # ── Market regime ──
    df["market_regime"] = df["close"].apply(
        lambda x: "bullish" if x > df["ma_200"].mean() else "bearish"
    )
    df["market_regime"] = (df["close"] > df["ma_200"]).map({True: "bullish", False: "bearish"})

    # ── Target ──
    df["next_day_close"]  = df["close"].shift(-1)
    df["next_day_return"] = (df["next_day_close"] - df["close"]) / df["close"] * 100
    df["target_direction"]= (df["next_day_return"] > 0).astype(int)

    df = df.dropna().reset_index(drop=True)

    print(f"[INFO] Final shape: {df.shape}")
    print(f"[INFO] Date range: {df['date'].min()} → {df['date'].max()}")

    return df


df  = fetch_and_engineer(TICKER)
out = cleaned_prices_path(TICKER)
df.to_csv(out, index=False)
print(f"[SAVED] {out}")