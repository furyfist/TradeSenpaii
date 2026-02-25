import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
from config import cleaned_prices_path, sentiment_features_path, merged_dataset_path
import pandas as pd
import numpy as np

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--ticker", required=True)
args = parser.parse_args()

PRICE_CSV     = cleaned_prices_path(args.ticker)
SENTIMENT_CSV = sentiment_features_path(args.ticker)
OUTPUT_CSV    = merged_dataset_path(args.ticker)

# LOAD
def load_data():
    price_df = pd.read_csv(PRICE_CSV, parse_dates=["date"])
    sent_df  = pd.read_csv(SENTIMENT_CSV, parse_dates=["date"])

    print(f"[INFO] Price data:     {len(price_df)} rows | {price_df['date'].min().date()} → {price_df['date'].max().date()}")
    print(f"[INFO] Sentiment data: {len(sent_df)} rows  | {sent_df['date'].min().date()} → {sent_df['date'].max().date()}")

    return price_df, sent_df


# BUILD DAILY SENTIMENT SIGNAL
#
# SEC filings drop on specific dates but price
# data is daily. Strategy:
#   - Place each filing's sentiment on its filing date
#   - Forward fill to every subsequent trading day
#   - Until the next filing of any type appears
#
# This reflects how the market actually absorbs
# filing information — it persists until new info arrives

def build_daily_sentiment(sent_df: pd.DataFrame, price_df: pd.DataFrame) -> pd.DataFrame:
    sentiment_cols = [
        "lm_positive", "lm_negative", "lm_uncertain",
        "lm_litigious", "lm_constraining",
        "lm_pos_pct", "lm_neg_pct", "lm_uncertain_pct",
        "lm_sentiment_score"
    ]

    # If multiple filings fall on the same date, average their scores
    daily_sent = (
        sent_df.groupby("date")[sentiment_cols]
        .mean()
        .reset_index()
    )

    # Create a full daily date spine from price data
    date_spine = price_df[["date"]].copy()

    # Merge sentiment onto date spine — only filing dates get values
    daily_sent = date_spine.merge(daily_sent, on="date", how="left")

    # Forward fill — each filing's sentiment persists until next filing
    daily_sent[sentiment_cols] = daily_sent[sentiment_cols].ffill()

    # Back fill only the leading NaNs (before first filing in 1994)
    # These will be dropped later since overlap starts at 1994
    daily_sent[sentiment_cols] = daily_sent[sentiment_cols].bfill()

    return daily_sent


# ENGINEER ADDITIONAL SENTIMENT FEATURES
# Raw scores are useful but derived features
# add more predictive power
def engineer_sentiment_features(df: pd.DataFrame) -> pd.DataFrame:
    # Rolling average sentiment — smooths noise
    df["lm_sentiment_ma5"]  = df["lm_sentiment_score"].rolling(5,  min_periods=1).mean()
    df["lm_sentiment_ma20"] = df["lm_sentiment_score"].rolling(20, min_periods=1).mean()

    # Sentiment delta — how much did sentiment shift from recent average?
    # Sudden drops are more predictive than absolute levels
    df["lm_sentiment_delta"] = df["lm_sentiment_score"] - df["lm_sentiment_ma20"]

    # Uncertainty spike — rolling z-score of uncertainty
    unc_mean = df["lm_uncertain_pct"].rolling(20, min_periods=1).mean()
    unc_std  = df["lm_uncertain_pct"].rolling(20, min_periods=1).std().replace(0, np.nan)
    df["lm_uncertainty_zscore"] = (df["lm_uncertain_pct"] - unc_mean) / unc_std
    df["lm_uncertainty_zscore"] = df["lm_uncertainty_zscore"].fillna(0)

    # Litigation spike — binary flag, litigious language above rolling mean
    lit_mean = df["lm_litigious"].rolling(20, min_periods=1).mean()
    df["lm_litigation_spike"] = (df["lm_litigious"] > lit_mean * 1.5).astype(int)

    # Negative dominance — is negative pct outweighing positive pct?
    df["lm_neg_dominant"] = (df["lm_neg_pct"] > df["lm_pos_pct"]).astype(int)

    return df


# MERGE
def merge_datasets(price_df: pd.DataFrame, daily_sent: pd.DataFrame) -> pd.DataFrame:
    merged = price_df.merge(daily_sent, on="date", how="left")

    # Only keep the overlapping window — 1994 onwards
    # Before 1994 there are no SEC filings so sentiment is meaningless
    merged = merged[merged["date"] >= "1994-01-01"].reset_index(drop=True)

    print(f"[INFO] Merged dataset: {len(merged)} rows | {merged['date'].min().date()} → {merged['date'].max().date()}")

    return merged


# QUALITY CHECK
def quality_check(df: pd.DataFrame):
    print(f"\n[QUALITY CHECK]")
    print(f"  Total rows          : {len(df)}")
    print(f"  Total features      : {df.shape[1]}")

    null_counts = df.isnull().sum()
    null_cols   = null_counts[null_counts > 0]
    if null_cols.empty:
        print(f"  Null values         : None ✓")
    else:
        print(f"  Columns with nulls  :")
        print(null_cols.to_string())

    print(f"\n[SENTIMENT FEATURE STATS]")
    sentiment_cols = [
        "lm_sentiment_score", "lm_sentiment_delta",
        "lm_uncertainty_zscore", "lm_neg_pct", "lm_pos_pct"
    ]
    print(df[sentiment_cols].describe().round(4).to_string())

    print(f"\n[CORRELATION: sentiment vs next_day_return]")
    corr_cols = [
        "lm_sentiment_score", "lm_sentiment_delta",
        "lm_uncertainty_zscore", "lm_neg_pct",
        "lm_neg_dominant", "lm_litigation_spike"
    ]
    corr = df[corr_cols + ["next_day_return"]].corr()["next_day_return"].drop("next_day_return")
    print(corr.round(4).to_string())


# MAIN
def run_merge():
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    price_df, sent_df = load_data()

    print("\n[INFO] Building daily sentiment signal...")
    daily_sent = build_daily_sentiment(sent_df, price_df)

    print("[INFO] Engineering sentiment features...")
    daily_sent = engineer_sentiment_features(daily_sent)

    print("[INFO] Merging datasets...")
    merged = merge_datasets(price_df, daily_sent)

    merged.to_csv(OUTPUT_CSV, index=False)
    print(f"[DONE] Saved to {OUTPUT_CSV}")

    quality_check(merged)

    print(f"\n[FEATURE LIST]")
    print(list(merged.columns))


if __name__ == "__main__":
    run_merge()