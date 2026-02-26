import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import numpy as np
from pathlib import Path
from similarity_search import find_similar_days

# Path to merged datasets — same pattern as sentiment_loader fix
DATA_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "stock-analysis" / "data" / "processed"

def load_merged(ticker: str) -> pd.DataFrame:
    path = DATA_ROOT / ticker / "merged_dataset.csv"
    if not path.exists():
        raise FileNotFoundError(f"merged_dataset.csv not found at {path}")
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def compute_base_rates(df: pd.DataFrame, implied_return_pct: float, timeframe_days: int) -> dict:
    """
    For each row in df, compute the actual N-day forward return.
    Then calculate what % of periods achieved various thresholds.

    Returns base rates for: 5%, 10%, 20%, and the implied_return_pct target.
    """
    closes = df["close"].values if "close" in df.columns else df["Close"].values
    n = timeframe_days

    forward_returns = []
    for i in range(len(closes) - n):
        fwd = (closes[i + n] - closes[i]) / closes[i] * 100
        forward_returns.append(fwd)

    if not forward_returns:
        return {}

    arr = np.array(forward_returns)
    total = len(arr)

    def base_rate(threshold: float) -> float:
        """% of periods where abs move exceeded threshold (directional: positive)"""
        return round(float(np.sum(arr >= threshold) / total * 100), 2)

    def base_rate_either(threshold: float) -> float:
        """% of periods where move in either direction exceeded threshold"""
        return round(float(np.sum(np.abs(arr) >= threshold) / total * 100), 2)

    result = {
        "total_periods_analyzed": total,
        "timeframe_days": n,
        "base_rate_up_5pct":   base_rate(5),
        "base_rate_up_10pct":  base_rate(10),
        "base_rate_up_20pct":  base_rate(20),
        "base_rate_down_5pct": round(float(np.sum(arr <= -5) / total * 100), 2),
        "base_rate_either_10pct": base_rate_either(10),
        "max_gain_in_timeframe":  round(float(arr.max()), 2),
        "max_loss_in_timeframe":  round(float(arr.min()), 2),
        "median_return":          round(float(np.median(arr)), 2),
        "mean_return":            round(float(arr.mean()), 2),
    }

    # Base rate for the specific implied return
    if implied_return_pct is not None:
        direction = "up" if implied_return_pct > 0 else "down"
        if implied_return_pct > 0:
            rate = base_rate(implied_return_pct)
        else:
            rate = round(float(np.sum(arr <= implied_return_pct) / total * 100), 2)

        result["implied_return_pct"]        = round(implied_return_pct, 2)
        result["base_rate_for_implied"]     = rate
        result[f"base_rate_{direction}_label"] = (
            f"{rate}% of {n}-day periods achieved {implied_return_pct:+.1f}%"
        )

    return result


def get_similar_setups(ticker: str, n: int = 3) -> list[dict]:
    """
    Reuse existing similarity_search.find_similar_days().
    Fetches current feature row and passes it as required.
    """
    try:
        from feature_engineer import get_latest_feature_row
        feature_df, _ = get_latest_feature_row(ticker)
        if feature_df is None or feature_df.empty:
            print(f"[WARN][evidence_agent] Empty feature row for {ticker}")
            return []
        current_features = feature_df.iloc[-1]
        similar = find_similar_days(ticker, current_features=current_features, top_n=n)
        return similar if similar else []
    except Exception as e:
        print(f"[WARN][evidence_agent] Similarity search failed for {ticker}: {e}")
        return []


def collect_historical_evidence(
    ticker: str,
    implied_return_pct: float,
    timeframe_days: int,
) -> dict:
    """
    Agent 3 — Historical Evidence.

    Returns:
    {
        ticker, timeframe_days, implied_return_pct,
        base_rates: { total_periods, base_rate_up_5/10/20, max_gain, ... },
        similar_setups: [ { date, similarity, actual_direction, actual_return, key_signals } ],
        verdict: str,   ← plain English summary
        error: None
    }
    """
    print(f"[INFO][evidence_agent] Analyzing {ticker} | "
          f"implied={implied_return_pct}% | timeframe={timeframe_days}d")

    result = {
        "ticker": ticker,
        "timeframe_days": timeframe_days,
        "implied_return_pct": implied_return_pct,
        "base_rates": {},
        "similar_setups": [],
        "verdict": "",
        "error": None,
    }

    # ── Load merged dataset 
    try:
        df = load_merged(ticker)
        print(f"[INFO][evidence_agent] Loaded {len(df)} rows for {ticker}")
    except Exception as e:
        result["error"] = str(e)
        print(f"[ERROR][evidence_agent] {e}")
        return result

    # ── Base rates 
    if implied_return_pct is not None:
        result["base_rates"] = compute_base_rates(df, implied_return_pct, timeframe_days)
    else:
        # No target price — still compute general base rates
        result["base_rates"] = compute_base_rates(df, None, timeframe_days)

    # ── Similar setups 
    result["similar_setups"] = get_similar_setups(ticker)

    # ── Plain English verdict 
    br = result["base_rates"]
    if br and implied_return_pct is not None:
        rate = br.get("base_rate_for_implied", 0)
        max_gain = br.get("max_gain_in_timeframe", 0)
        total = br.get("total_periods_analyzed", 0)

        if implied_return_pct > max_gain:
            verdict = (
                f"The implied move of {implied_return_pct:+.1f}% exceeds the maximum "
                f"historical {timeframe_days}-day gain of {max_gain:+.1f}% — "
                f"this has never happened in {total} periods analyzed."
            )
        elif rate < 5:
            verdict = (
                f"Only {rate}% of historical {timeframe_days}-day windows produced "
                f"a {implied_return_pct:+.1f}% gain. This is a rare outcome."
            )
        elif rate < 20:
            verdict = (
                f"{rate}% of {timeframe_days}-day periods achieved {implied_return_pct:+.1f}%. "
                f"Possible but unlikely without a major catalyst."
            )
        else:
            verdict = (
                f"{rate}% of {timeframe_days}-day periods achieved {implied_return_pct:+.1f}%. "
                f"This move is within the historical range of normal outcomes."
            )
        result["verdict"] = verdict
        print(f"[INFO][evidence_agent] Verdict: {verdict}")

    return result


# ── Quick Test 
if __name__ == "__main__":
    import json

    tests = [
        ("KO",   272.81, 90),   # unrealistic — $300 target
        ("AAPL", -8.84,  180),  # realistic bearish
        ("GOOGL", None,  90),   # no target price
    ]

    for ticker, implied, days in tests:
        print(f"\n{'='*60}")
        result = collect_historical_evidence(ticker, implied, days)
        print(json.dumps(result, indent=2, default=str))