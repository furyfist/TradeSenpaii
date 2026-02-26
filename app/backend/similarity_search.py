import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.preprocessing import StandardScaler

# Path to processed data
BASE_PATH = Path(__file__).resolve().parent.parent.parent / "stock-analysis" / "data" / "processed"

# Features used for similarity — same as model training
# Excludes leaky cols, date, target, and string cols
SIMILARITY_FEATURES = [
    "daily_return", "gap_pct", "close_lag1", "close_lag5", "close_lag10",
    "ma_7", "ma_20", "ma_50", "ma_200",
    "volatility_20", "volatility_30",
    "avg_volume_20", "volume_ratio_20",
    "momentum_5d", "momentum_10d",
    "distance_from_ma20", "distance_from_ma50",
    "upper_band_20", "lower_band_20",
    "rsi_14", "day_of_week", "month", "quarter",
    "lm_positive", "lm_negative", "lm_uncertain",
    "lm_litigious", "lm_constraining",
    "lm_pos_pct", "lm_neg_pct", "lm_uncertain_pct",
    "lm_sentiment_score", "lm_sentiment_ma5", "lm_sentiment_ma20",
    "lm_sentiment_delta", "lm_uncertainty_zscore",
    "lm_litigation_spike", "lm_neg_dominant",
]

# Key signals to include in each analogy result
# These are the most interpretable for the LLM explanation
SIGNAL_LABELS = {
    "rsi_14":             "RSI",
    "lm_sentiment_score": "SEC Sentiment Score",
    "distance_from_ma20": "Distance from MA20 (%)",
    "volatility_20":      "20-Day Volatility",
    "momentum_5d":        "5-Day Momentum (%)",
    "lm_uncertain_pct":   "Uncertainty Language (%)",
    "lm_neg_pct":         "Negative Language (%)",
    "ma20_above_ma50":    "Trend (MA20 > MA50)",
    "volume_ratio_20":    "Volume Ratio",
    "lm_litigation_spike":"Litigation Spike",
}


def _cosine_similarity_matrix(query: np.ndarray,
                               matrix: np.ndarray) -> np.ndarray:
    """
    Computes cosine similarity between a single query vector
    and every row in a matrix.

    query:  shape (n_features,)
    matrix: shape (n_samples, n_features)
    returns: shape (n_samples,)
    """
    # Normalize query
    query_norm  = query / (np.linalg.norm(query) + 1e-10)

    # Normalize each row of matrix
    row_norms   = np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-10
    matrix_norm = matrix / row_norms

    # Dot product → cosine similarity
    similarities = matrix_norm @ query_norm
    return similarities


def find_similar_days(
    ticker: str,
    current_features: pd.Series,
    top_n: int = 3,
    min_days_ago: int = 365,
) -> list[dict]:
    """
    Finds the top_n most similar historical trading days
    to the current feature snapshot using cosine similarity.

    Args:
        ticker:           stock ticker e.g. "KO"
        current_features: pd.Series of current day features
                          (last row from feature_engineer.py output)
        top_n:            number of analogies to return
        min_days_ago:     minimum age of analogies in days
                          (avoids returning recent days as "historical")

    Returns:
        List of dicts, each containing:
        - date
        - similarity score
        - actual direction (UP/DOWN)
        - actual next day return
        - key signals
    """
    # ── Load historical dataset 
    csv_path = BASE_PATH / ticker / "merged_dataset.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"No merged dataset found for {ticker}")

    df = pd.read_csv(csv_path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df = df.dropna(subset=["next_day_return", "target_direction"])

    # ── Filter out recent days 
    cutoff_date = pd.Timestamp.today() - pd.Timedelta(days=min_days_ago)
    df_historical = df[df["date"] < cutoff_date].reset_index(drop=True)

    if len(df_historical) < top_n:
        raise ValueError(
            f"Not enough historical data for {ticker} "
            f"(need {top_n}, got {len(df_historical)})"
        )

    # ── Select features 
    available_features = [
        f for f in SIMILARITY_FEATURES
        if f in df_historical.columns and f in current_features.index
    ]

    X_historical = df_historical[available_features].values.astype(float)
    x_current    = current_features[available_features].values.astype(float)

    # ── Handle NaN in historical data 
    # Replace NaN with column mean to avoid similarity collapse
    col_means    = np.nanmean(X_historical, axis=0)
    nan_mask     = np.isnan(X_historical)
    X_historical[nan_mask] = np.take(col_means, np.where(nan_mask)[1])

    # Replace NaN in current vector with 0
    x_current = np.nan_to_num(x_current, nan=0.0)

    # ── Normalize (StandardScaler) 
    scaler       = StandardScaler()
    X_scaled     = scaler.fit_transform(X_historical)
    x_curr_scaled = scaler.transform(x_current.reshape(1, -1)).squeeze()

    # ── Compute cosine similarity 
    similarities = _cosine_similarity_matrix(x_curr_scaled, X_scaled)

    # ── Get top N indices 
    top_indices  = np.argsort(similarities)[::-1][:top_n]

    # ── Build result 
    results = []
    for idx in top_indices:
        row        = df_historical.iloc[idx]
        sim_score  = float(similarities[idx])

        # Key signals for this historical day
        key_signals = {}
        for col, label in SIGNAL_LABELS.items():
            if col in df_historical.columns:
                val = row.get(col, None)
                if val is not None and not pd.isna(val):
                    key_signals[label] = round(float(val), 4)

        results.append({
            "date":             str(row["date"].date()),
            "similarity":       round(sim_score, 4),
            "actual_direction": "UP" if int(row["target_direction"]) == 1 else "DOWN",
            "actual_return":    round(float(row["next_day_return"]), 4),
            "key_signals":      key_signals,
            "days_ago":         (pd.Timestamp.today() - row["date"]).days,
        })

    return results


def format_analogies_for_llm(analogies: list[dict], ticker: str) -> str:
    """
    Formats the similarity results into a clean text block
    for injection into the LLM prompt.
    """
    if not analogies:
        return "No historical analogies found."

    lines = [f"Historical analogies for {ticker}:\n"]

    for i, a in enumerate(analogies, 1):
        lines.append(
            f"Analogy {i} — {a['date']} "
            f"({a['days_ago']} days ago, "
            f"similarity: {a['similarity']:.2%})"
        )
        lines.append(
            f"  Outcome: {a['actual_direction']} "
            f"({a['actual_return']:+.2f}% next day)"
        )
        lines.append("  Conditions that day:")
        for label, value in a["key_signals"].items():
            lines.append(f"    - {label}: {value}")
        lines.append("")

    return "\n".join(lines)