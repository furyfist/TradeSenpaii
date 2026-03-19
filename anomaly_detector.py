"""
TradeSenpai — SEC Filing Anomaly Detector
==========================================
Detects quarter-over-quarter linguistic anomalies in SEC filings.
Compares each filing's sentiment scores against the ticker's own
rolling historical baseline using z-score deviation.

Logic:
    For each 10-K/10-Q filing:
        z_score = (current_value - rolling_mean) / rolling_std
        flag if z_score > SPIKE_THRESHOLD (default 1.5σ)

This is per-ticker baseline — JNJ is compared against JNJ history,
not against AAPL. That's what makes the signal meaningful.

Usage:
    python anomaly_detector.py                  # all 6 tickers
    python anomaly_detector.py --ticker AAPL    # single ticker
    python anomaly_detector.py --ticker JNJ --threshold 2.0
    python anomaly_detector.py --export         # save results to CSV

Place at: TradeSenpai/anomaly_detector.py (project root)
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT      = Path(__file__).resolve().parent
DATA_ROOT = ROOT / "stock-analysis" / "data" / "processed"

TICKERS = ["KO", "JNJ", "PG", "WMT", "AAPL", "GOOGL"]

# ── Config ────────────────────────────────────────────────────────────────────
MIN_WORDS       = 500    # ignore stub filings below this word count
SPIKE_THRESHOLD = 1.5    # z-score threshold to flag as anomaly
ROLLING_WINDOW  = 8      # number of prior filings to compute baseline
                         # 8 quarters = 2 years of history as baseline

# ── Signals to monitor ────────────────────────────────────────────────────────
# Each entry: (column, label, direction)
# direction: "up" = spike upward is bad, "down" = drop is bad
SIGNALS = [
    ("lm_neg_pct",         "Negative Language",  "up"),
    ("lm_uncertain_pct",   "Uncertainty",        "up"),
    ("lm_litigious",       "Litigation Count",   "up"),
    ("lm_sentiment_score", "Sentiment Score",    "down"),
    ("lm_pos_pct",         "Positive Language",  "down"),
]


# ══════════════════════════════════════════════════════════════════════════════
# 1.  Load + clean filing data
# ══════════════════════════════════════════════════════════════════════════════

def load_filings(ticker: str) -> pd.DataFrame:
    """
    Loads sec_sentiment_features.csv for a ticker.
    Filters to 10-K and 10-Q only, minimum word count.
    Returns sorted by date ascending.
    """
    path = DATA_ROOT / ticker / "sec_sentiment_features.csv"
    if not path.exists():
        raise FileNotFoundError(f"[ERROR] No sentiment file at {path}")

    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])

    before = len(df)

    # keep only substantive annual/quarterly reports
    df = df[df["form_type"].isin(["10-K", "10-Q"])]
    df = df[df["total_words"] >= MIN_WORDS]
    df = df.sort_values("date").reset_index(drop=True)

    after = len(df)
    print(f"[INFO] {ticker} — {before} total filings → {after} after filtering "
          f"(10-K/10-Q, ≥{MIN_WORDS} words)")

    return df


# ══════════════════════════════════════════════════════════════════════════════
# 2.  Compute rolling baseline + z-scores
# ══════════════════════════════════════════════════════════════════════════════

def compute_zscores(df: pd.DataFrame, window: int = ROLLING_WINDOW) -> pd.DataFrame:
    """
    For each signal column, computes:
        rolling_mean  — mean of prior `window` filings
        rolling_std   — std of prior `window` filings
        z_score       — how many std devs current filing is from baseline

    Uses shift(1) so current filing is NOT included in its own baseline.
    This mirrors the no-leakage principle from the backtesting engine.
    """
    df = df.copy()

    for col, label, direction in SIGNALS:
        if col not in df.columns:
            continue

        rolling_mean = df[col].shift(1).rolling(window, min_periods=3).mean()
        rolling_std  = df[col].shift(1).rolling(window, min_periods=3).std()

        # avoid division by zero — replace 0 std with NaN
        rolling_std = rolling_std.replace(0, np.nan)

        df[f"{col}_baseline_mean"] = rolling_mean
        df[f"{col}_baseline_std"]  = rolling_std
        df[f"{col}_zscore"]        = (df[col] - rolling_mean) / rolling_std
        df[f"{col}_direction"]     = direction

    return df


# ══════════════════════════════════════════════════════════════════════════════
# 3.  Flag anomalies
# ══════════════════════════════════════════════════════════════════════════════

def flag_anomalies(df: pd.DataFrame, threshold: float = SPIKE_THRESHOLD) -> pd.DataFrame:
    """
    Adds an `anomalies` column — list of signal names that spiked.
    Adds `anomaly_count` and `risk_level` for easy filtering.
    """
    df = df.copy()
    anomaly_lists  = []
    anomaly_counts = []

    for _, row in df.iterrows():
        triggered = []

        for col, label, direction in SIGNALS:
            zscore_col = f"{col}_zscore"
            if zscore_col not in df.columns:
                continue

            z = row.get(zscore_col, np.nan)
            if pd.isna(z):
                continue

            # spike upward for "up" signals, spike downward for "down" signals
            if direction == "up"   and z >  threshold:
                triggered.append(label)
            elif direction == "down" and z < -threshold:
                triggered.append(label)

        anomaly_lists.append(triggered)
        anomaly_counts.append(len(triggered))

    df["anomalies"]     = anomaly_lists
    df["anomaly_count"] = anomaly_counts

    # risk level based on how many signals fired simultaneously
    def risk_level(count):
        if count == 0: return "NORMAL"
        if count == 1: return "WATCH"
        if count == 2: return "ELEVATED"
        return "HIGH"

    df["risk_level"] = df["anomaly_count"].apply(risk_level)

    return df


# ══════════════════════════════════════════════════════════════════════════════
# 4.  Quarter-over-quarter delta (the "what changed" story)
# ══════════════════════════════════════════════════════════════════════════════

def compute_qoq_deltas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes quarter-over-quarter percentage change for key signals.
    This is what makes the "filing warned us early" story concrete:
    "Uncertainty jumped 34% from Q2 to Q3 2023"
    """
    df = df.copy()

    key_cols = ["lm_neg_pct", "lm_uncertain_pct", "lm_sentiment_score", "lm_litigious"]

    for col in key_cols:
        if col in df.columns:
            prev          = df[col].shift(1)
            df[f"{col}_qoq_delta"] = ((df[col] - prev) / prev.abs().replace(0, np.nan)) * 100

    return df


# ══════════════════════════════════════════════════════════════════════════════
# 5.  Full pipeline for one ticker
# ══════════════════════════════════════════════════════════════════════════════

def analyze_ticker(ticker: str, threshold: float = SPIKE_THRESHOLD) -> pd.DataFrame:
    print(f"\n[INFO] ── Analyzing {ticker} ──")

    df = load_filings(ticker)
    df = compute_zscores(df)
    df = compute_qoq_deltas(df)
    df = flag_anomalies(df, threshold)
    df["ticker"] = ticker

    # summary
    total     = len(df)
    anomalous = len(df[df["anomaly_count"] > 0])
    high_risk = len(df[df["risk_level"] == "HIGH"])
    elevated  = len(df[df["risk_level"] == "ELEVATED"])

    print(f"[INFO] {ticker} — {total} filings analyzed")
    print(f"[INFO] {ticker} — {anomalous} flagged ({anomalous/total*100:.1f}%) | "
          f"HIGH: {high_risk} | ELEVATED: {elevated}")

    return df


# ══════════════════════════════════════════════════════════════════════════════
# 6.  Print results
# ══════════════════════════════════════════════════════════════════════════════

def print_anomalies(df: pd.DataFrame, ticker: str, recent_only: bool = True):
    """
    Prints flagged filings. By default shows last 10 years only
    for relevance — full history available in exported CSV.
    """
    flagged = df[df["anomaly_count"] > 0].copy()

    if recent_only:
        cutoff = pd.Timestamp("2010-01-01")
        flagged = flagged[flagged["date"] >= cutoff]

    if flagged.empty:
        print(f"  No anomalies detected for {ticker} (post-2010)")
        return

    print(f"\n  {'Date':<12} {'Form':<6} {'Risk':<10} {'Count':<7} {'Signals Triggered'}")
    print(f"  {'─'*12} {'─'*6} {'─'*10} {'─'*7} {'─'*40}")

    for _, row in flagged.iterrows():
        date      = row["date"].strftime("%Y-%m-%d")
        form      = row["form_type"]
        risk      = row["risk_level"]
        count     = int(row["anomaly_count"])
        signals   = ", ".join(row["anomalies"]) if row["anomalies"] else "—"
        print(f"  {date:<12} {form:<6} {risk:<10} {count:<7} {signals}")


def print_summary(all_dfs: list[pd.DataFrame]):
    print("\n" + "═" * 65)
    print("  ANOMALY DETECTION SUMMARY")
    print("═" * 65)
    print(f"  {'Ticker':<8} {'Filings':>8} {'Flagged':>8} {'Flag%':>7} "
          f"{'HIGH':>6} {'ELEVATED':>9}")
    print("─" * 65)

    for df in all_dfs:
        ticker    = df["ticker"].iloc[0]
        total     = len(df)
        flagged   = len(df[df["anomaly_count"] > 0])
        high      = len(df[df["risk_level"] == "HIGH"])
        elevated  = len(df[df["risk_level"] == "ELEVATED"])
        pct       = flagged / total * 100
        print(f"  {ticker:<8} {total:>8} {flagged:>8} {pct:>6.1f}% "
              f"{high:>6} {elevated:>9}")

    print("═" * 65)


# ══════════════════════════════════════════════════════════════════════════════
# 7.  Most interesting cases — for the "filing warned us early" story
# ══════════════════════════════════════════════════════════════════════════════

def find_evidence_cases(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """
    Finds the strongest anomaly cases — HIGH risk filings with large z-scores.
    These are your candidates for the "filing warned us early" story.
    Returns top 5 sorted by anomaly_count desc, then by max z-score.
    """
    high_risk = df[df["risk_level"].isin(["HIGH", "ELEVATED"])].copy()

    if high_risk.empty:
        return pd.DataFrame()

    # compute max z-score across all signals for ranking
    zscore_cols = [f"{col}_zscore" for col, _, _ in SIGNALS
                   if f"{col}_zscore" in df.columns]

    high_risk["max_zscore"] = high_risk[zscore_cols].abs().max(axis=1)
    high_risk = high_risk.sort_values(
        ["anomaly_count", "max_zscore"], ascending=False
    ).head(5)

    return high_risk[["date", "form_type", "risk_level", "anomaly_count",
                       "max_zscore", "anomalies",
                       "lm_neg_pct", "lm_uncertain_pct",
                       "lm_sentiment_score", "lm_litigious"]]


def print_evidence_cases(df: pd.DataFrame, ticker: str):
    cases = find_evidence_cases(df, ticker)
    if cases.empty:
        return

    print(f"\n  TOP EVIDENCE CASES — {ticker}")
    print(f"  {'─'*60}")

    for _, row in cases.iterrows():
        print(f"\n  📋 {row['date'].strftime('%Y-%m-%d')} | {row['form_type']} "
              f"| Risk: {row['risk_level']} | Signals: {row['anomaly_count']} "
              f"| Max z-score: {row['max_zscore']:.2f}σ")
        print(f"     Triggered: {', '.join(row['anomalies'])}")
        print(f"     neg_pct={row['lm_neg_pct']:.3f}  "
              f"uncertain_pct={row['lm_uncertain_pct']:.3f}  "
              f"sentiment={row['lm_sentiment_score']:.3f}  "
              f"litigation={row['lm_litigious']:.0f}")


# ══════════════════════════════════════════════════════════════════════════════
# 8.  Export
# ══════════════════════════════════════════════════════════════════════════════

def export_results(all_dfs: list[pd.DataFrame]):
    combined = pd.concat(all_dfs, ignore_index=True)

    # clean up — drop intermediate zscore/baseline cols for readability
    export_cols = [
        "ticker", "date", "form_type", "total_words",
        "lm_pos_pct", "lm_neg_pct", "lm_uncertain_pct",
        "lm_litigious", "lm_sentiment_score",
        "lm_neg_pct_qoq_delta", "lm_uncertain_pct_qoq_delta",
        "lm_sentiment_score_qoq_delta",
        "anomalies", "anomaly_count", "risk_level",
    ]
    export_cols = [c for c in export_cols if c in combined.columns]
    export_df   = combined[export_cols]

    out_path = ROOT / "anomaly_results.csv"
    export_df.to_csv(out_path, index=False)
    print(f"\n[INFO] Results exported to {out_path}")
    print(f"[INFO] {len(export_df)} total filings | "
          f"{len(export_df[export_df['anomaly_count']>0])} flagged")


# ══════════════════════════════════════════════════════════════════════════════
# 9.  Entry point
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="TradeSenpai SEC Anomaly Detector")
    parser.add_argument("--ticker",    type=str,   default=None,
                        help="Single ticker (default: all 6)")
    parser.add_argument("--threshold", type=float, default=SPIKE_THRESHOLD,
                        help=f"Z-score threshold (default: {SPIKE_THRESHOLD})")
    parser.add_argument("--window",    type=int,   default=ROLLING_WINDOW,
                        help=f"Rolling window in filings (default: {ROLLING_WINDOW})")
    parser.add_argument("--export",    action="store_true",
                        help="Export full results to anomaly_results.csv")
    parser.add_argument("--evidence",  action="store_true",
                        help="Show top evidence cases per ticker")
    args = parser.parse_args()

    tickers = [args.ticker.upper()] if args.ticker else TICKERS

    print(f"\n[INFO] TradeSenpai SEC Anomaly Detector")
    print(f"[INFO] Tickers   : {tickers}")
    print(f"[INFO] Threshold : {args.threshold}σ")
    print(f"[INFO] Window    : {args.window} filings")

    all_dfs = []

    for ticker in tickers:
        try:
            df = analyze_ticker(ticker, threshold=args.threshold)
            all_dfs.append(df)
            print_anomalies(df, ticker)

            if args.evidence:
                print_evidence_cases(df, ticker)

        except FileNotFoundError as e:
            print(e)
            continue

    if all_dfs:
        print_summary(all_dfs)

    if args.export and all_dfs:
        export_results(all_dfs)


if __name__ == "__main__":
    main()