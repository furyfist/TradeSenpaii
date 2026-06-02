import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
from pathlib import Path
from feature_engineer import get_latest_feature_row

_here = Path(__file__).resolve().parent
BASE_PATH = next(
    p / "stock-analysis" / "data" / "processed"
    for p in [_here, _here.parent, _here.parent.parent, _here.parent.parent.parent]
    if (p / "stock-analysis" / "data" / "processed").exists()
)

SECTOR_MAP = {
    "KO":    "Consumer Staples",
    "JNJ":   "Healthcare",
    "PG":    "Consumer Staples",
    "WMT":   "Retail",
    "AAPL":  "Technology",
    "GOOGL": "Technology",
}

def collect_market_context(ticker: str) -> dict:
    """
    Agent 2 — pulls current market context for a ticker.
    Reuses get_latest_feature_row() from feature_engineer.py.

    Returns:
    {
        ticker, current_price, 52w_high, 52w_low,
        distance_to_52w_high_pct, distance_to_52w_low_pct,
        sector,
        signals: { rsi_14, ma distances, momentum, sentiment, flags... }
        error: str | None
    }
    """
    print(f"[INFO][market_collector] Collecting context for {ticker}")

    result = {
        "ticker": ticker,
        "current_price": None,
        "52w_high": None,
        "52w_low": None,
        "distance_to_52w_high_pct": None,
        "distance_to_52w_low_pct": None,
        "sector": SECTOR_MAP.get(ticker, "Unknown"),
        "signals": {},
        "error": None,
    }

    try:
        # ── Load from CSV
        csv_df = pd.read_csv(BASE_PATH / ticker / "merged_dataset.csv")
        csv_df["date"] = pd.to_datetime(csv_df["date"])
        csv_df = csv_df.sort_values("date").reset_index(drop=True)

        # ── 52-week range from CSV
        last_252 = csv_df["close"].tail(252)
        result["52w_high"] = float(last_252.max())
        result["52w_low"]  = float(last_252.min())

        # ── Latest feature row
        feature_df, _ = get_latest_feature_row(ticker)

        if feature_df is None or feature_df.empty:
            result["error"] = f"get_latest_feature_row returned empty for {ticker}"
            return result

        latest = feature_df.iloc[-1]

        # ── Current price from CSV
        current_price = float(csv_df["close"].iloc[-1])
        result["current_price"] = current_price

        # ── 52w distances 
        if current_price and result["52w_high"]:
            result["distance_to_52w_high_pct"] = round(
                ((result["52w_high"] - current_price) / current_price) * 100, 2
            )
        if current_price and result["52w_low"]:
            result["distance_to_52w_low_pct"] = round(
                ((current_price - result["52w_low"]) / result["52w_low"]) * 100, 2
            )

        # ── Safe getter 
        def g(col, default=None):
            val = latest.get(col, default)
            if val is None or (isinstance(val, float) and pd.isna(val)):
                return default
            return round(float(val), 4)

        # ── Signals dict 
        result["signals"] = {
            # Technical
            "rsi_14":                  g("rsi_14"),
            "ma_7":                    g("ma_7"),
            "ma_20":                   g("ma_20"),
            "ma_50":                   g("ma_50"),
            "ma_200":                  g("ma_200"),
            "distance_from_ma20_pct":  round(g("distance_from_ma20") or 0, 4),
            "distance_from_ma50_pct":  round(g("distance_from_ma50") or 0, 4),
            "momentum_5d_pct":         round(g("momentum_5d") or 0, 4),
            "momentum_10d_pct":        round(g("momentum_10d") or 0, 4),
            "volume_ratio_20":         g("volume_ratio_20"),
            "volatility_20_pct":       round((g("volatility_20") or 0), 4),
            # Sentiment
            "lm_sentiment_score":      g("lm_sentiment_score"),
            "lm_uncertainty_zscore":   g("lm_uncertainty_zscore"),
            "lm_sentiment_delta":      g("lm_sentiment_delta"),
            "lm_neg_dominant":         bool(g("lm_neg_dominant", 0)),
            "lm_litigation_spike":     bool(g("lm_litigation_spike", 0)),
            # Regime
            "market_regime":           int(g("market_regime_enc", 0)),
            # Boolean flags
            "rsi_oversold":            bool(g("rsi_oversold", 0)),
            "rsi_overbought":          bool(g("rsi_overbought", 0)),
            "ma7_above_ma20":          bool(g("ma7_above_ma20", 0)),
            "ma20_above_ma50":         bool(g("ma20_above_ma50", 0)),
            "volume_surge":            bool(g("volume_surge", 0)),
        }

        print(f"[INFO][market_collector] {ticker} done. "
              f"Price={current_price}, RSI={result['signals']['rsi_14']}, "
              f"Regime={result['signals']['market_regime']}")

    except Exception as e:
        result["error"] = str(e)
        print(f"[ERROR][market_collector] {ticker}: {e}")

    return result


# ── Quick Test
if __name__ == "__main__":
    import json
    for ticker in ["KO", "AAPL"]:
        print(f"\n{'='*60}")
        ctx = collect_market_context(ticker)
        print(json.dumps(ctx, indent=2))