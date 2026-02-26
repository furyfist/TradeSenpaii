"""
Agent 1 — Hypothesis Parser
Parses raw natural language hypothesis text into structured data.

Input:  raw text + current_price (float)
Output: ParsedHypothesis dict

Ticker matching covers:
  KO    → Coca-Cola, Coke, $KO
  JNJ   → Johnson & Johnson, J&J, $JNJ
  PG    → Procter & Gamble, P&G, $PG
  WMT   → Walmart, Wal-Mart, $WMT
  AAPL  → Apple, $AAPL
  GOOGL → Google, Alphabet, $GOOGL
"""

import re
import math
import yfinance as yf
from typing import Optional

# ─── Supported Tickers 
TICKER_ALIASES: dict[str, list[str]] = {
    "KO":    ["ko", "coca-cola", "coca cola", "coke"],
    "JNJ":   ["jnj", "johnson & johnson", "johnson and johnson", "j&j"],
    "PG":    ["pg", "procter & gamble", "procter and gamble", "p&g"],
    "WMT":   ["wmt", "walmart", "wal-mart", "wal mart"],
    "AAPL":  ["aapl", "apple"],
    "GOOGL": ["googl", "google", "alphabet"],
}

SUPPORTED_TICKERS = list(TICKER_ALIASES.keys())

# ─── Timeframe Patterns 
TIMEFRAME_PATTERNS: list[tuple[str, int]] = [
    # (regex pattern, days)  — ordered most-specific first
    (r"(\d+)\s*year[s]?",        365),   # n years
    (r"(\d+)\s*month[s]?",       30),    # n months
    (r"(\d+)\s*week[s]?",        7),     # n weeks
    (r"(\d+)\s*day[s]?",         1),     # n days
    (r"(\d+)\s*quarter[s]?",     90),    # n quarters
    (r"end of (the )?year",      None),  # handled separately
    (r"this (quarter|q[1-4])",   90),
    (r"short[ -]term",           30),
    (r"mid[ -]term",             180),
    (r"long[ -]term",            365),
]

UNIT_MULTIPLIERS: dict[str, int] = {
    "year": 365,
    "years": 365,
    "month": 30,
    "months": 30,
    "week": 7,
    "weeks": 7,
    "day": 1,
    "days": 1,
    "quarter": 90,
    "quarters": 90,
}

# ─── Hypothesis Type Classifier 

PRICE_TARGET_PATTERNS = [
    r"\$[\d,]+(\.\d+)?",          # $300, $1,200.50
    r"reach[es]?\s+\$?[\d,]+",
    r"hit[s]?\s+\$?[\d,]+",
    r"go\s+to\s+\$?[\d,]+",
    r"target\s+(?:price\s+)?\$?[\d,]+",
    r"price\s+target\s+\$?[\d,]+",
    r"worth\s+\$?[\d,]+",
    r"at\s+\$[\d,]+",
]

DIRECTIONAL_PATTERNS = [
    r"\b(bullish|bearish|buy|sell|short|long)\b",
    r"\b(go up|go down|rise|fall|drop|rally|surge|crash|climb|decline)\b",
    r"\b(up\s*\d+%|down\s*\d+%)\b",
    r"\b(outperform|underperform)\b",
]

EVENT_DRIVEN_PATTERNS = [
    r"\b(earnings|report|announcement|merger|acquisition|fda|patent|lawsuit|dividend|split)\b",
    r"\b(q[1-4]|fiscal|guidance|upgrade|downgrade|catalyst)\b",
]


# ─── Core Functions

def extract_ticker(text: str) -> Optional[str]:
    """
    Find the first matching ticker from supported list.
    Matches: $AAPL, AAPL, Apple, apple inc., etc.
    Returns ticker symbol or None.
    """
    lower = text.lower()

    # 1. Dollar-sign notation: $KO, $AAPL etc.
    dollar_match = re.search(r"\$([A-Za-z]{1,5})\b", text)
    if dollar_match:
        candidate = dollar_match.group(1).upper()
        if candidate in SUPPORTED_TICKERS:
            return candidate

    # 2. Exact uppercase ticker: "KO will..." (word boundary)
    for ticker in SUPPORTED_TICKERS:
        if re.search(r"\b" + ticker + r"\b", text):
            return ticker

    # 3. Company name / alias match
    for ticker, aliases in TICKER_ALIASES.items():
        for alias in aliases:
            if alias in lower:
                return ticker

    return None


def extract_target_price(text: str) -> Optional[float]:
    """
    Extract the most likely target price from text.
    Handles: "$300", "300 dollars", "reach 280.50", "target of $1,200"
    Returns float or None.
    """
    # Pattern: optional $ + digits + optional comma + optional decimals
    # Prioritize prices after keywords like reach/hit/target/to
    keyword_pattern = (
        r"(?:reach(?:es)?|hit[s]?|go\s+to|target(?:\s+(?:price|of))?|"
        r"worth|at|climb\s+to|rise\s+to|drop\s+to|fall\s+to)\s+"
        r"\$?([\d,]+(?:\.\d+)?)"
    )
    match = re.search(keyword_pattern, text, re.IGNORECASE)
    if match:
        return _parse_price_str(match.group(1))

    # Fallback: any $NNN.NN pattern
    dollar_match = re.search(r"\$([\d,]+(?:\.\d+)?)", text)
    if dollar_match:
        return _parse_price_str(dollar_match.group(1))

    return None


def _parse_price_str(s: str) -> Optional[float]:
    """'1,200.50' → 1200.50"""
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def extract_timeframe_days(text: str) -> Optional[int]:
    """
    Convert timeframe mentions to integer days.
    "3 months" → 90, "2 years" → 730, "next quarter" → 90
    Returns int days or None.
    """
    lower = text.lower()

    # Numeric + unit: "3 months", "2 years", "6 weeks"
    match = re.search(
        r"(\d+)\s*(year[s]?|month[s]?|week[s]?|day[s]?|quarter[s]?)",
        lower
    )
    if match:
        n = int(match.group(1))
        unit = match.group(2).rstrip("s")  # normalize plural
        return n * UNIT_MULTIPLIERS.get(unit, UNIT_MULTIPLIERS.get(unit + "s", 30))

    # Named horizons
    if re.search(r"\bshort[- ]term\b", lower):
        return 30
    if re.search(r"\bmid[- ]term\b", lower):
        return 180
    if re.search(r"\blong[- ]term\b", lower):
        return 365
    if re.search(r"\bthis (quarter|q[1-4])\b", lower):
        return 90
    if re.search(r"\bend of (the )?year\b", lower):
        return 180  # approximate; could be smarter with calendar
    if re.search(r"\bsoon\b|\bshortly\b", lower):
        return 14
    if re.search(r"\bovernight\b|\btoday\b\btomorrow\b", lower):
        return 1

    return None


def classify_hypothesis_type(text: str) -> str:
    """
    Classify into: price_target | directional | event_driven
    Uses keyword matching with priority order.
    """
    lower = text.lower()

    has_price_target = any(
        re.search(p, text, re.IGNORECASE) for p in PRICE_TARGET_PATTERNS
    )
    has_event = any(
        re.search(p, lower) for p in EVENT_DRIVEN_PATTERNS
    )
    has_directional = any(
        re.search(p, lower) for p in DIRECTIONAL_PATTERNS
    )

    if has_price_target:
        return "price_target"
    if has_event:
        return "event_driven"
    if has_directional:
        return "directional"

    # Fallback: if there's a target price somewhere, it's price_target
    return "directional"


def fetch_current_price(ticker: str) -> Optional[float]:
    """Live price fetch via yfinance. Returns None on failure."""
    try:
        data = yf.Ticker(ticker)
        hist = data.history(period="2d")
        if hist.empty:
            return None
        return float(hist["Close"].iloc[-1])
    except Exception as e:
        print(f"[WARN][parser] Failed to fetch price for {ticker}: {e}")
        return None


def get_historical_return_std(ticker: str, timeframe_days: int) -> Optional[float]:
    """
    Compute std deviation of rolling N-day returns for the ticker.
    Used to flag unrealistic hypotheses.
    Returns std as a decimal (e.g., 0.15 = 15%) or None on failure.
    """
    try:
        data = yf.Ticker(ticker)
        # Fetch ~5 years for a solid distribution
        hist = data.history(period="5y")
        if hist.empty or len(hist) < timeframe_days + 10:
            return None

        closes = hist["Close"]
        # Rolling N-day return: (price_t / price_{t-N}) - 1
        rolling_returns = closes.pct_change(periods=timeframe_days).dropna()
        return float(rolling_returns.std())
    except Exception as e:
        print(f"[WARN][parser] Failed to compute std for {ticker}: {e}")
        return None


def is_unrealistic(
    implied_return_pct: float,
    ticker: str,
    timeframe_days: int,
    std_threshold: float = 3.0,
) -> tuple[bool, Optional[float], Optional[float]]:
    """
    Flag if implied return > N std deviations from historical distribution.
    Returns: (is_unrealistic_flag, historical_std, z_score)
    """
    if implied_return_pct is None or timeframe_days is None:
        return False, None, None

    std = get_historical_return_std(ticker, timeframe_days)
    if std is None or std == 0:
        return False, None, None

    # implied_return_pct is 0-100 scale; convert to decimal
    implied_decimal = implied_return_pct / 100.0
    z_score = abs(implied_decimal) / std

    flag = z_score > std_threshold
    return flag, round(std * 100, 2), round(z_score, 2)


# ─── Main Entry Point
def parse_hypothesis(text: str, current_price: Optional[float] = None) -> dict:
    """
    Parse a raw hypothesis string into a structured dict.

    Args:
        text:          Raw hypothesis text from user input.
        current_price: Override live price fetch (useful in tests / downstream).

    Returns:
        {
            raw_text:              str,
            ticker:                str | None,
            ticker_found:          bool,
            target_price:          float | None,
            timeframe_days:        int | None,
            current_price:         float | None,
            implied_return_pct:    float | None,  # signed, e.g. 15.3 or -8.2
            hypothesis_type:       str,           # price_target | directional | event_driven
            is_realistic_flag:     bool,          # True = UNREALISTIC
            historical_std_pct:    float | None,  # std of N-day returns as %
            z_score:               float | None,  # how many stds from mean
            parse_warnings:        list[str],     # non-fatal issues
            error:                 str | None,    # fatal parse error
        }
    """
    result: dict = {
        "raw_text": text,
        "ticker": None,
        "ticker_found": False,
        "target_price": None,
        "timeframe_days": None,
        "current_price": None,
        "implied_return_pct": None,
        "hypothesis_type": "directional",
        "is_realistic_flag": False,
        "historical_std_pct": None,
        "z_score": None,
        "parse_warnings": [],
        "error": None,
    }

    if not text or not text.strip():
        result["error"] = "Empty hypothesis text."
        return result

    # ── 1. Ticker 
    ticker = extract_ticker(text)
    if not ticker:
        result["error"] = (
            "Could not identify a supported ticker. "
            f"Supported: {', '.join(SUPPORTED_TICKERS)}"
        )
        return result

    result["ticker"] = ticker
    result["ticker_found"] = True
    print(f"[INFO][parser] Ticker identified: {ticker}")

    # ── 2. Timeframe 
    timeframe_days = extract_timeframe_days(text)
    result["timeframe_days"] = timeframe_days
    if timeframe_days is None:
        result["parse_warnings"].append(
            "No timeframe detected. Historical analysis will use 90-day default."
        )
        result["timeframe_days"] = 90  # default

    print(f"[INFO][parser] Timeframe: {result['timeframe_days']} days")

    # ── 3. Target Price 
    target_price = extract_target_price(text)
    result["target_price"] = target_price

    # ── 4. Current Price 
    if current_price is not None:
        result["current_price"] = current_price
    else:
        price = fetch_current_price(ticker)
        result["current_price"] = price
        if price is None:
            result["parse_warnings"].append(
                f"Could not fetch live price for {ticker}. Implied return unavailable."
            )

    # ── 5. Implied Return 
    if result["current_price"] and target_price:
        implied = ((target_price - result["current_price"]) / result["current_price"]) * 100
        result["implied_return_pct"] = round(implied, 2)
        print(f"[INFO][parser] Implied return: {result['implied_return_pct']}%")
    elif result["current_price"] is None:
        result["implied_return_pct"] = None
    else:
        result["parse_warnings"].append(
            "No target price found — implied return not calculable."
        )

    # ── 6. Hypothesis Type 
    result["hypothesis_type"] = classify_hypothesis_type(text)
    print(f"[INFO][parser] Hypothesis type: {result['hypothesis_type']}")

    # ── 7. Realism Chec
    if result["implied_return_pct"] is not None:
        flag, std_pct, z_score = is_unrealistic(
            result["implied_return_pct"],
            ticker,
            result["timeframe_days"],
        )
        result["is_realistic_flag"] = flag
        result["historical_std_pct"] = std_pct
        result["z_score"] = z_score

        if flag:
            result["parse_warnings"].append(
                f"⚠️  Implied return of {result['implied_return_pct']}% is "
                f"{z_score:.1f} std deviations from the historical {result['timeframe_days']}-day "
                f"return distribution (σ={std_pct}%). This move would be historically extreme."
            )
            print(f"[WARN][parser] Unrealistic flag set. z={z_score}")

    return result


# ─── Quick Test 

if __name__ == "__main__":
    import json

    test_cases = [
        "Coca-Cola will reach $300 in 3 months",
        "I think $AAPL hits $250 by end of year",
        "GOOGL will rally after earnings next quarter",
        "WMT is bearish short-term",
        "Apple is going to drop 50% this week",   # should flag unrealistic
        "Johnson & Johnson will outperform the market in 2 years",
        "Tesla will hit $500",                    # unsupported ticker
    ]

    for hypothesis in test_cases:
        print("\n" + "=" * 60)
        print(f"INPUT: {hypothesis}")
        result = parse_hypothesis(hypothesis)
        print(json.dumps(result, indent=2))