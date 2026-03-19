"""
TradeSenpai — Backtesting Engine
=================================
Runs trained transformer models on historical merged_dataset.csv data.
Logs predictions + actual outcomes to Supabase prediction_history table.

Usage:
    python backtest.py                    # all 6 tickers, last 60 trading days
    python backtest.py --ticker AAPL      # single ticker
    python backtest.py --days 120         # extend backtest window
    python backtest.py --dry-run          # print results, skip Supabase logging

Place this file at: TradeSenpai/backtest.py (project root)
"""

import os
import sys
import argparse
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import psycopg2
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

# ── Load env ──────────────────────────────────────────────────────────────────
load_dotenv("app/backend/.env")

# ── Paths (all relative to project root) ──────────────────────────────────────
ROOT        = Path(__file__).resolve().parent
DATA_ROOT   = ROOT / "stock-analysis" / "data" / "processed"
MODEL_DIR   = ROOT / "app" / "backend" / "model"

TICKERS = ["KO", "JNJ", "PG", "WMT", "AAPL", "GOOGL"]


# Model definition (must match predictor.py exactly)

class PositionalEncoding(nn.Module):
    def __init__(self, d_model, max_len=200, dropout=0.1):
        super().__init__()
        self.dropout = nn.Dropout(dropout)
        pe           = torch.zeros(max_len, d_model)
        position     = torch.arange(0, max_len).unsqueeze(1).float()
        div_term     = torch.exp(
            torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model)
        )
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0))

    def forward(self, x):
        return self.dropout(x + self.pe[:, :x.size(1)])


class StockTransformer(nn.Module):
    def __init__(self, input_size, d_model=128, nhead=4,
                 num_layers=3, num_classes=2, dropout=0.3):
        super().__init__()
        self.input_proj  = nn.Linear(input_size, d_model)
        self.pos_enc     = PositionalEncoding(d_model, dropout=dropout)
        encoder_layer    = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead,
            dim_feedforward=d_model * 4,
            dropout=dropout, batch_first=True, norm_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.norm        = nn.LayerNorm(d_model)
        self.classifier  = nn.Sequential(
            nn.Linear(d_model, 64), nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(64, num_classes)
        )

    def forward(self, x):
        x = self.input_proj(x)
        x = self.pos_enc(x)
        x = self.transformer(x)
        x = self.norm(x)
        x = x[:, -1, :]
        return self.classifier(x)


# Feature preparation
# CSV has 48 cols. Model needs 56. We compute the 8 missing derived cols.

def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Takes merged_dataset.csv dataframe, adds the 8 derived feature columns
    that were computed dynamically in feature_engineer.py but not stored in CSV.

    Missing cols:
        lm_sentiment_lag1, lm_sentiment_lag5, lm_sentiment_lag10
        lm_neg_pct_lag1, lm_uncertain_lag1
        return_lag1, return_lag2, return_lag3, return_lag5
        vol_regime
        rsi_oversold, rsi_overbought
        ma7_above_ma20, ma20_above_ma50
        volume_surge
        sent_x_vol, sent_x_unc
        market_regime_enc  (CSV has string "bullish"/"bearish", model needs 0/1)
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # market_regime string → int
    df["market_regime_enc"] = (df["market_regime"] == "bullish").astype(int)

    # sentiment lags
    df["lm_sentiment_lag1"]  = df["lm_sentiment_score"].shift(1)
    df["lm_sentiment_lag5"]  = df["lm_sentiment_score"].shift(5)
    df["lm_sentiment_lag10"] = df["lm_sentiment_score"].shift(10)
    df["lm_neg_pct_lag1"]    = df["lm_neg_pct"].shift(1)
    df["lm_uncertain_lag1"]  = df["lm_uncertain_pct"].shift(1)

    # return lags
    df["return_lag1"] = df["daily_return"].shift(1)
    df["return_lag2"] = df["daily_return"].shift(2)
    df["return_lag3"] = df["daily_return"].shift(3)
    df["return_lag5"] = df["daily_return"].shift(5)

    # regime flags
    df["vol_regime"]      = (df["volatility_20"] > df["volatility_20"].rolling(60).mean()).astype(int)
    df["rsi_oversold"]    = (df["rsi_14"] < 30).astype(int)
    df["rsi_overbought"]  = (df["rsi_14"] > 70).astype(int)
    df["ma7_above_ma20"]  = (df["ma_7"]  > df["ma_20"]).astype(int)
    df["ma20_above_ma50"] = (df["ma_20"] > df["ma_50"]).astype(int)
    df["volume_surge"]    = (df["volume_ratio_20"] > 1.5).astype(int)

    # interaction features
    df["sent_x_vol"] = df["lm_sentiment_score"] * df["volatility_20"]
    df["sent_x_unc"] = df["lm_sentiment_score"] * df["lm_uncertain_pct"]

    # drop rows with NaN introduced by lags/rolling (need ~60 rows of warmup)
    df = df.dropna().reset_index(drop=True)

    return df


# Model loader (mirrors predictor.py _load_model logic)

def load_model(ticker: str) -> dict:
    model_path = MODEL_DIR / f"transformer_{ticker}.pt"
    if not model_path.exists():
        raise FileNotFoundError(f"[ERROR] No model checkpoint at {model_path}")

    print(f"[INFO] Loading model for {ticker}...")
    checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)

    cfg   = checkpoint["model_config"]
    model = StockTransformer(
        input_size=cfg["input_size"],
        d_model=cfg["d_model"],
        nhead=cfg["nhead"],
        num_layers=cfg["num_layers"],
        num_classes=cfg["num_classes"],
        dropout=cfg["dropout"],
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    return {
        "model":        model,
        "feature_cols": checkpoint["feature_cols"],
        "sequence_len": checkpoint["sequence_len"],
        "scaler_mean":  np.array(checkpoint["scaler_mean"]),
        "scaler_scale": np.array(checkpoint["scaler_scale"]),
        "cv_accuracy":  checkpoint["cv_accuracy"],
    }


# Single prediction from a feature window

def predict_window(state: dict, window_df: pd.DataFrame) -> tuple[str, float]:
    """
    Given a 60-row feature window, returns (prediction, confidence).
    prediction: "UP" or "DOWN"
    confidence: float 0.5–1.0
    """
    feature_cols  = state["feature_cols"]
    scaler_mean   = state["scaler_mean"]
    scaler_scale  = state["scaler_scale"]
    sequence_len  = state["sequence_len"]

    # verify all features present
    missing = [c for c in feature_cols if c not in window_df.columns]
    if missing:
        raise ValueError(f"[ERROR] Missing features: {missing}")

    X        = window_df[feature_cols].values          # shape: (60, 56)
    X_scaled = (X - scaler_mean) / scaler_scale

    if len(X_scaled) < sequence_len:
        raise ValueError(f"Window too small: {len(X_scaled)} < {sequence_len}")

    sequence = X_scaled[-sequence_len:]                # last 60 rows
    tensor   = torch.FloatTensor(sequence).unsqueeze(0)  # (1, 60, 56)

    with torch.no_grad():
        logits = state["model"](tensor)
        probs  = torch.softmax(logits, dim=1).squeeze().numpy()

    pred_class = int(probs.argmax())
    confidence = float(probs.max())
    prediction = "UP" if pred_class == 1 else "DOWN"

    return prediction, round(confidence, 4)


# Core backtest loop for one ticker

def backtest_ticker(ticker: str, days: int = 60) -> list[dict]:
    """
    Runs backtest for one ticker over the last `days` trading days in the CSV.

    Returns list of result dicts:
    {
        ticker, predicted_date, prediction, confidence,
        actual_direction, actual_return, correct
    }
    """
    print(f"\n[INFO] ── Starting backtest for {ticker} ──")

    # load + prepare data
    csv_path = DATA_ROOT / ticker / "merged_dataset.csv"
    if not csv_path.exists():
        print(f"[ERROR] CSV not found: {csv_path}")
        return []

    raw_df = pd.read_csv(csv_path)
    df     = prepare_features(raw_df)

    print(f"[INFO] {ticker} — {len(df)} rows after feature prep")

    state        = load_model(ticker)
    sequence_len = state["sequence_len"]   # 60

    # we need at least sequence_len rows as lookback + 1 row as target
    # backtest over the last `days` rows (those are our prediction targets)
    total_rows   = len(df)
    start_idx    = max(sequence_len, total_rows - days)   # first target index
    target_range = range(start_idx, total_rows)

    print(f"[INFO] {ticker} — backtesting {len(target_range)} dates "
          f"({df.iloc[start_idx]['date'].date()} → {df.iloc[-1]['date'].date()})")

    results = []

    for i in target_range:
        target_row = df.iloc[i]

        # ── NO LEAKAGE: window is rows [i-60 : i], target date is i ──
        window_df  = df.iloc[i - sequence_len : i].copy()

        predicted_date     = pd.to_datetime(target_row["date"]).date()
        actual_direction   = "UP" if target_row["target_direction"] == 1 else "DOWN"
        actual_return      = round(float(target_row["daily_return"]), 6)

        try:
            prediction, confidence = predict_window(state, window_df)
        except Exception as e:
            print(f"[WARN] {ticker} {predicted_date} — skipped: {e}")
            continue

        correct = 1 if prediction == actual_direction else 0

        results.append({
            "ticker":           ticker,
            "predicted_date":   predicted_date,
            "prediction":       prediction,
            "confidence":       confidence,
            "actual_direction": actual_direction,
            "actual_return":    actual_return,
            "correct":          correct,
        })

    # summary
    if results:
        accuracy = sum(r["correct"] for r in results) / len(results) * 100
        print(f"[INFO] {ticker} — {len(results)} predictions | "
              f"Accuracy: {accuracy:.2f}% | CV was: {state['cv_accuracy']*100:.2f}%")

    return results


# Supabase logging

def get_db_connection():
    import time
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        raise ValueError("[ERROR] SUPABASE_DB_URL not set in .env")
    for attempt in range(5):
        try:
            return psycopg2.connect(db_url, connect_timeout=30)
        except Exception as e:
            print(f"[WARN] DB connection attempt {attempt+1}/5 failed: {e}")
            time.sleep(3 * (attempt + 1))
    raise ConnectionError("[ERROR] Could not connect to Supabase after 5 attempts")


def log_results_to_supabase(results: list[dict]) -> tuple[int, int]:
    """
    Inserts results into prediction_history.
    Uses ON CONFLICT DO NOTHING — safe to rerun.
    Returns (inserted, skipped) counts.
    """
    if not results:
        return 0, 0

    inserted = 0
    skipped  = 0

    conn = get_db_connection()
    cur  = conn.cursor()

    sql = """
        INSERT INTO prediction_history
            (ticker, predicted_date, prediction, confidence,
             actual_direction, actual_return, correct, logged_at)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (ticker, predicted_date) DO NOTHING
    """

    for r in results:
        try:
            cur.execute(sql, (
                r["ticker"],
                r["predicted_date"],
                r["prediction"],
                r["confidence"],
                r["actual_direction"],
                r["actual_return"],
                r["correct"],
                datetime.now(timezone.utc),
            ))
            if cur.rowcount == 1:
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"[ERROR] DB insert failed for {r['ticker']} {r['predicted_date']}: {e}")
            conn.rollback()
            continue

    conn.commit()
    cur.close()
    conn.close()

    return inserted, skipped


# Summary printer

def print_summary(all_results: list[dict]):
    if not all_results:
        print("\n[INFO] No results to summarize.")
        return

    df = pd.DataFrame(all_results)
    print("\n" + "═" * 55)
    print("  BACKTEST SUMMARY")
    print("═" * 55)

    overall_acc = df["correct"].mean() * 100
    print(f"  Overall accuracy : {overall_acc:.2f}%")
    print(f"  Total predictions: {len(df)}")
    print(f"  Date range       : {df['predicted_date'].min()} → {df['predicted_date'].max()}")
    print("─" * 55)
    print(f"  {'Ticker':<8} {'Preds':>6} {'Correct':>8} {'Accuracy':>10} {'Avg Conf':>10}")
    print("─" * 55)

    for ticker in sorted(df["ticker"].unique()):
        t       = df[df["ticker"] == ticker]
        preds   = len(t)
        correct = t["correct"].sum()
        acc     = t["correct"].mean() * 100
        conf    = t["confidence"].mean() * 100
        print(f"  {ticker:<8} {preds:>6} {correct:>8} {acc:>9.2f}% {conf:>9.2f}%")

    print("═" * 55)

    # confidence calibration
    print("\n  CONFIDENCE CALIBRATION")
    print("─" * 55)
    print(f"  {'Bucket':<18} {'Preds':>6} {'Accuracy':>10}")
    print("─" * 55)
    buckets = [(0.50, 0.55), (0.55, 0.60), (0.60, 0.65), (0.65, 1.01)]
    for lo, hi in buckets:
        mask   = (df["confidence"] >= lo) & (df["confidence"] < hi)
        subset = df[mask]
        if len(subset) == 0:
            continue
        label  = f"{lo:.2f}–{min(hi, 1.0):.2f}"
        acc    = subset["correct"].mean() * 100
        print(f"  {label:<18} {len(subset):>6} {acc:>9.2f}%")
    print("═" * 55)


# Entry point

def main():
    parser = argparse.ArgumentParser(description="TradeSenpai Backtesting Engine")
    parser.add_argument("--ticker",  type=str, default=None,
                        help="Single ticker (default: all 6)")
    parser.add_argument("--days",    type=int, default=60,
                        help="How many trading days to backtest (default: 60)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print results only, skip Supabase logging")
    args = parser.parse_args()

    tickers = [args.ticker.upper()] if args.ticker else TICKERS

    # validate ticker
    for t in tickers:
        if t not in TICKERS:
            print(f"[ERROR] Unknown ticker: {t}. Valid: {TICKERS}")
            sys.exit(1)

    print(f"\n[INFO] TradeSenpai Backtest Engine")
    print(f"[INFO] Tickers  : {tickers}")
    print(f"[INFO] Days     : {args.days}")
    print(f"[INFO] Dry run  : {args.dry_run}")
    print(f"[INFO] Data root: {DATA_ROOT}")
    print(f"[INFO] Model dir: {MODEL_DIR}\n")

    all_results = []

    for ticker in tickers:
        results = backtest_ticker(ticker, days=args.days)
        all_results.extend(results)

        if results and not args.dry_run:
            inserted, skipped = log_results_to_supabase(results)
            print(f"[INFO] {ticker} — Supabase: {inserted} inserted, {skipped} skipped (duplicates)")

    print_summary(all_results)

    if args.dry_run:
        print("\n[INFO] Dry run complete — nothing logged to Supabase.")
    else:
        print(f"\n[INFO] Done. {len(all_results)} total results logged to prediction_history.")


if __name__ == "__main__":
    main()