"""
TradeSenpai — Evidence Builder
================================
Correlates SEC filing anomaly dates with subsequent price movements.
Answers: "Did the filing signal predict what happened to the stock?"

For each HIGH/ELEVATED anomaly filing:
    - Price at filing date
    - Price 30/60/90 days after
    - Return over each window
    - Whether the signal direction was correct

Usage:
    python evidence_builder.py                  # all 6 tickers
    python evidence_builder.py --ticker JNJ     # single ticker
    python evidence_builder.py --export         # save to evidence_cases.csv
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path

ROOT      = Path(__file__).resolve().parent
DATA_ROOT = ROOT / "stock-analysis" / "data" / "processed"
TICKERS   = ["KO", "JNJ", "PG", "WMT", "AAPL", "GOOGL"]

# look-forward windows in trading days
WINDOWS = [30, 60, 90]

# only analyze these risk levels
TARGET_RISK = ["HIGH", "ELEVATED"]


#  Load data

def load_price_data(ticker: str) -> pd.DataFrame:
    path = DATA_ROOT / ticker / "merged_dataset.csv"
    df   = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df[["date", "close", "daily_return"]]


def load_anomaly_results() -> pd.DataFrame:
    path = ROOT / "anomaly_results.csv"
    if not path.exists():
        raise FileNotFoundError(
            "[ERROR] anomaly_results.csv not found. "
            "Run anomaly_detector.py --export first."
        )
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    return df


#  Price impact calculator

def get_price_at_or_after(price_df: pd.DataFrame, target_date: pd.Timestamp) -> float | None:
    """Gets closing price on or after target_date (handles weekends/holidays)."""
    future = price_df[price_df["date"] >= target_date]
    if future.empty:
        return None
    return float(future.iloc[0]["close"])


def compute_price_impact(
    filing_date: pd.Timestamp,
    price_df: pd.DataFrame,
    windows: list[int] = WINDOWS
) -> dict:
    """
    Computes forward returns from filing date over each window.
    Uses trading days not calendar days — more accurate.
    """
    # find filing date index in price data
    future_prices = price_df[price_df["date"] >= filing_date].reset_index(drop=True)

    if future_prices.empty:
        return {}

    base_price = float(future_prices.iloc[0]["close"])
    base_date  = future_prices.iloc[0]["date"]

    result = {
        "base_price": round(base_price, 2),
        "base_date":  base_date,
    }

    for w in windows:
        if len(future_prices) > w:
            fwd_price  = float(future_prices.iloc[w]["close"])
            fwd_date   = future_prices.iloc[w]["date"]
            fwd_return = ((fwd_price - base_price) / base_price) * 100
            result[f"price_{w}d"]  = round(fwd_price, 2)
            result[f"return_{w}d"] = round(fwd_return, 2)
            result[f"date_{w}d"]   = fwd_date
        else:
            result[f"price_{w}d"]  = None
            result[f"return_{w}d"] = None
            result[f"date_{w}d"]   = None

    return result


# Signal direction check

def signal_was_bearish(anomalies_str: str) -> bool:
    """
    Returns True if the anomaly signals suggest downside risk.
    Bearish signals: Negative Language spike, Uncertainty spike,
                     Litigation spike, Sentiment Score drop.
    Bullish signals: Positive Language spike (often means growth narrative).
    """
    if pd.isna(anomalies_str):
        return False

    bearish_signals = [
        "Negative Language", "Uncertainty",
        "Litigation Count", "Sentiment Score"
    ]
    return any(s in anomalies_str for s in bearish_signals)


#  Full evidence analysis for one ticker

def analyze_ticker_evidence(
    ticker: str,
    anomaly_df: pd.DataFrame,
    price_df: pd.DataFrame
) -> pd.DataFrame:

    ticker_anomalies = anomaly_df[
        (anomaly_df["ticker"] == ticker) &
        (anomaly_df["risk_level"].isin(TARGET_RISK))
    ].copy()

    if ticker_anomalies.empty:
        print(f"[INFO] {ticker} — no HIGH/ELEVATED filings to analyze")
        return pd.DataFrame()

    print(f"[INFO] {ticker} — analyzing {len(ticker_anomalies)} HIGH/ELEVATED filings...")

    records = []

    for _, row in ticker_anomalies.iterrows():
        filing_date = row["date"]
        impact      = compute_price_impact(filing_date, price_df)

        if not impact:
            continue

        is_bearish = signal_was_bearish(str(row.get("anomalies", "")))

        record = {
            "ticker":        ticker,
            "filing_date":   filing_date.strftime("%Y-%m-%d"),
            "form_type":     row["form_type"],
            "risk_level":    row["risk_level"],
            "anomaly_count": row["anomaly_count"],
            "anomalies":     row.get("anomalies", ""),
            "signal_bearish":is_bearish,
            "base_price":    impact.get("base_price"),
        }

        for w in WINDOWS:
            record[f"return_{w}d"] = impact.get(f"return_{w}d")
            record[f"price_{w}d"]  = impact.get(f"price_{w}d")

        # was the signal correct? bearish signal + negative return = correct
        r30 = impact.get("return_30d")
        if r30 is not None:
            if is_bearish:
                record["signal_correct_30d"] = r30 < 0
            else:
                record["signal_correct_30d"] = r30 > 0
        else:
            record["signal_correct_30d"] = None

        records.append(record)

    return pd.DataFrame(records)


# Print evidence cases

def print_ticker_evidence(df: pd.DataFrame, ticker: str):
    if df.empty:
        return

    print(f"\n{'═'*68}")
    print(f"  EVIDENCE CASES — {ticker}")
    print(f"{'═'*68}")

    # sort by absolute 90d return for most impactful cases
    df_sorted = df.copy()
    df_sorted["abs_return_90d"] = df_sorted["return_90d"].abs()
    df_sorted = df_sorted.sort_values("abs_return_90d", ascending=False)

    for _, row in df_sorted.head(5).iterrows():
        correct_marker = ""
        if row["signal_correct_30d"] is True:
            correct_marker = "✓ SIGNAL CORRECT"
        elif row["signal_correct_30d"] is False:
            correct_marker = "✗ signal wrong"

        direction = "BEARISH" if row["signal_bearish"] else "BULLISH"

        print(f"\n  📋 {row['filing_date']} | {row['form_type']} | "
              f"{row['risk_level']} | {direction} | {correct_marker}")
        print(f"     Signals : {row['anomalies']}")
        print(f"     Price   : ${row['base_price']:.2f} at filing")

        for w in WINDOWS:
            ret = row.get(f"return_{w}d")
            p   = row.get(f"price_{w}d")
            if ret is not None:
                arrow = "↓" if ret < 0 else "↑"
                print(f"     {w:>3}d later: ${p:.2f}  {arrow} {ret:+.2f}%")


def print_signal_accuracy(all_dfs: list[pd.DataFrame]):
    combined = pd.concat(all_dfs, ignore_index=True)
    combined = combined.dropna(subset=["signal_correct_30d"])

    if combined.empty:
        return

    print(f"\n{'═'*68}")
    print(f"  SIGNAL ACCURACY SUMMARY (30-day forward return)")
    print(f"{'═'*68}")
    print(f"  {'Ticker':<8} {'Cases':>6} {'Correct':>8} {'Accuracy':>10} "
          f"{'Avg Return':>12}")
    print(f"  {'─'*60}")

    for ticker in TICKERS:
        t = combined[combined["ticker"] == ticker]
        if t.empty:
            continue
        cases   = len(t)
        correct = t["signal_correct_30d"].sum()
        acc     = correct / cases * 100
        avg_ret = t["return_30d"].mean()
        print(f"  {ticker:<8} {cases:>6} {correct:>8} {acc:>9.1f}% {avg_ret:>+11.2f}%")

    total   = len(combined)
    correct = combined["signal_correct_30d"].sum()
    acc     = correct / total * 100
    avg_ret = combined["return_30d"].mean()
    print(f"  {'─'*60}")
    print(f"  {'OVERALL':<8} {total:>6} {correct:>8} {acc:>9.1f}% {avg_ret:>+11.2f}%")
    print(f"{'═'*68}")


# Top 3 cases for README (the hero story)

def print_hero_cases(all_dfs: list[pd.DataFrame]):
    combined = pd.concat(all_dfs, ignore_index=True)
    combined = combined[combined["signal_bearish"] == True]
    combined = combined.dropna(subset=["return_90d"])
    combined["abs_return_90d"] = combined["return_90d"].abs()
    combined = combined[combined["return_90d"] < -5]   # bearish signal + real drop
    combined = combined.sort_values("abs_return_90d", ascending=False)

    print(f"\n{'═'*68}")
    print(f"  TOP HERO CASES — 'Filing Warned Us Early'")
    print(f"  (Bearish signals that preceded >5% drops within 90 days)")
    print(f"{'═'*68}")

    for _, row in combined.head(3).iterrows():
        print(f"\n  🎯 {row['ticker']} | {row['filing_date']} | {row['form_type']}")
        print(f"     Signal  : {row['anomalies']}")
        print(f"     30d     : {row['return_30d']:+.2f}%")
        print(f"     60d     : {row['return_60d']:+.2f}%")
        print(f"     90d     : {row['return_90d']:+.2f}%")
        print(f"     → Filing warned of this drop. Market took {abs(row['return_90d']):.1f}% to react.")

    print(f"\n{'═'*68}")


# Entry point

def main():
    parser = argparse.ArgumentParser(description="TradeSenpai Evidence Builder")
    parser.add_argument("--ticker", type=str, default=None)
    parser.add_argument("--export", action="store_true",
                        help="Export results to evidence_cases.csv")
    args = parser.parse_args()

    tickers = [args.ticker.upper()] if args.ticker else TICKERS

    print(f"\n[INFO] TradeSenpai Evidence Builder")
    print(f"[INFO] Tickers : {tickers}")
    print(f"[INFO] Windows : {WINDOWS} trading days\n")

    anomaly_df = load_anomaly_results()
    all_dfs    = []

    for ticker in tickers:
        try:
            price_df = load_price_data(ticker)
            df       = analyze_ticker_evidence(ticker, anomaly_df, price_df)
            if not df.empty:
                all_dfs.append(df)
                print_ticker_evidence(df, ticker)
        except FileNotFoundError as e:
            print(e)
            continue

    if all_dfs:
        print_signal_accuracy(all_dfs)
        print_hero_cases(all_dfs)

    if args.export and all_dfs:
        combined = pd.concat(all_dfs, ignore_index=True)
        out_path = ROOT / "evidence_cases.csv"
        combined.to_csv(out_path, index=False)
        print(f"\n[INFO] Exported to {out_path}")
        print(f"[INFO] {len(combined)} evidence cases total")


if __name__ == "__main__":
    main()