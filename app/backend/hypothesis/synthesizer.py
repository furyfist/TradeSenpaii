import sys, os, json, re
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from groq import Groq
from dotenv import load_dotenv
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

TICKER_FULL_NAME = {
    "KO":    "Coca-Cola",
    "JNJ":   "Johnson & Johnson",
    "PG":    "Procter & Gamble",
    "WMT":   "Walmart",
    "AAPL":  "Apple",
    "GOOGL": "Alphabet (Google)",
}

def _parse_json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except Exception:
        # Try to find and parse the largest complete JSON object
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                # JSON truncated — try to salvage by closing open brackets
                text = match.group()
                # Count unclosed braces and arrays
                open_braces = text.count("{") - text.count("}")
                open_brackets = text.count("[") - text.count("]")
                text += "]" * open_brackets + "}" * open_braces
                try:
                    return json.loads(text)
                except Exception:
                    pass
    return {}

def compute_feasibility_score(
    parsed: dict,
    market: dict,
    evidence: dict,
) -> int:
    """
    0-100 score based on:
    - Base rate for implied move (40 pts)
    - Technical alignment (30 pts)
    - Realistic flag (30 pts)
    """
    score = 0

    # Base rate component (40 pts)
    br = evidence.get("base_rates", {})
    base_rate = br.get("base_rate_for_implied")
    if base_rate is not None:
        if base_rate >= 40:   score += 40
        elif base_rate >= 20: score += 30
        elif base_rate >= 10: score += 20
        elif base_rate >= 5:  score += 10
        else:                 score += 2

    # Technical alignment (30 pts)
    signals = market.get("signals", {})
    rsi = signals.get("rsi_14", 50)
    regime = signals.get("market_regime", 0)
    ma_aligned = signals.get("ma20_above_ma50", False)
    momentum = signals.get("momentum_5d_pct", 0)

    implied = parsed.get("implied_return_pct")
    if implied is not None:
        bullish_hypothesis = implied > 0
        if bullish_hypothesis:
            if regime == 1:        score += 10
            if ma_aligned:         score += 10
            if momentum > 0:       score += 5
            if 40 < rsi < 70:      score += 5
        else:
            if regime == 0:        score += 10
            if not ma_aligned:     score += 10
            if momentum < 0:       score += 5
            if rsi > 70 or rsi < 30: score += 5

    # Realism component (30 pts)
    if not parsed.get("is_realistic_flag", False):
        score += 30
    else:
        z = parsed.get("z_score", 10)
        if z < 5:   score += 15
        elif z < 10: score += 5

    return min(100, max(0, score))


def build_synthesis_prompt(
    parsed: dict,
    market: dict,
    evidence: dict,
    bear: dict,
    bull: dict,
    feasibility_score: int,
) -> str:
    ticker       = parsed["ticker"]
    company_name = TICKER_FULL_NAME.get(ticker, ticker)
    signals      = market.get("signals", {})
    br           = evidence.get("base_rates", {})

    # Compact signal summary
    tech_summary = (
        f"RSI={signals.get('rsi_14')}, "
        f"MA20_dist={signals.get('distance_from_ma20_pct')}%, "
        f"momentum_5d={signals.get('momentum_5d_pct')}%, "
        f"regime={'Bull' if signals.get('market_regime') == 1 else 'Bear'}, "
        f"sentiment={signals.get('lm_sentiment_score')}, "
        f"litigation_spike={signals.get('lm_litigation_spike')}"
    )

    base_rate_summary = (
        f"Base rate for implied move: {br.get('base_rate_for_implied', 'N/A')}% | "
        f"Max historical {evidence.get('timeframe_days')}d gain: {br.get('max_gain_in_timeframe')}% | "
        f"Median {evidence.get('timeframe_days')}d return: {br.get('median_return')}%"
    )

    risks_text = "\n".join([
        f"- {r['title']}: {r['description']}"
        for r in bear.get("risks", [])
    ])

    catalysts_text = "\n".join([
        f"- {c['title']}: {c['description']}"
        for c in bull.get("catalysts", [])
    ])

    similar_text = ""
    for s in evidence.get("similar_setups", []):
        similar_text += (
            f"  {s['date']} ({s['days_ago']}d ago): "
            f"{s['actual_direction']} {s['actual_return']:+.2f}% "
            f"similarity={s['similarity']:.2%}\n"
        )

    prompt = f"""You are a senior financial research analyst writing a structured research brief.

HYPOTHESIS: "{parsed.get('raw_text')}"
TICKER: {ticker} ({company_name})
CURRENT PRICE: ${market.get('current_price')}
TARGET PRICE: ${parsed.get('target_price')}
IMPLIED RETURN: {parsed.get('implied_return_pct')}% over {parsed.get('timeframe_days')} days
FEASIBILITY SCORE: {feasibility_score}/100
UNREALISTIC FLAG: {parsed.get('is_realistic_flag')} (z-score: {parsed.get('z_score')})

TECHNICAL PICTURE:
{tech_summary}
52w High: ${market.get('52w_high')} ({market.get('distance_to_52w_high_pct')}% away)
52w Low: ${market.get('52w_low')} ({market.get('distance_to_52w_low_pct')}% above)

HISTORICAL EVIDENCE:
{base_rate_summary}
Similar past setups:
{similar_text if similar_text else "None found"}

BEAR CASE (current risks):
{risks_text}

BULL CASE (current catalysts):
{catalysts_text}

Write a research brief. Return ONLY valid JSON, no markdown:
{{
  "hypothesis_clean": "clean restatement of the hypothesis",
  "ticker": "{ticker}",
  "current_price": {market.get('current_price')},
  "target_price": {parsed.get('target_price')},
  "implied_return_pct": {parsed.get('implied_return_pct')},
  "feasibility_score": {feasibility_score},
  "reality_check": "2-3 sentences: is this hypothesis realistic? reference base rates and z-score",
  "technical_picture": {{
    "summary": "2 sentences on current technical setup",
    "rsi": {signals.get('rsi_14')},
    "trend": "bullish/bearish/neutral based on MA alignment and regime",
    "momentum": "positive/negative/neutral"
  }},
  "historical_evidence": {{
    "summary": "2 sentences on what history says about this move",
    "base_rate_for_implied": {br.get('base_rate_for_implied')},
    "max_historical_move": {br.get('max_gain_in_timeframe')}
  }},
  "bull_case": {json.dumps(bull.get('catalysts', []))},
  "bear_case": {json.dumps(bear.get('risks', []))},
  "parameters_to_monitor": [
    {{"param": "RSI", "current": {signals.get('rsi_14')}, "watch_for": "crosses above 70 (overbought) or below 30 (oversold)"}},
    {{"param": "MA20", "current": {signals.get('ma_20')}, "watch_for": "price breaks below MA20 invalidates bullish setup"}},
    {{"param": "Sentiment", "current": {signals.get('lm_sentiment_score')}, "watch_for": "new SEC filing that shifts sentiment score"}}
  ],
  "summary": "3-4 sentence plain English conclusion a retail investor can understand",
  "disclaimer": "This is an educational simulation only. Not financial advice. Model accuracy is ~52%."
}}"""

    return prompt


def synthesize(
    parsed: dict,
    market: dict,
    evidence: dict,
    bear: dict,
    bull: dict,
) -> dict:
    """
    Agent 6 — Final synthesis into complete research brief.
    """
    ticker = parsed.get("ticker", "UNKNOWN")
    print(f"[INFO][synthesizer] Synthesizing research brief for {ticker}")

    feasibility_score = compute_feasibility_score(parsed, market, evidence)
    print(f"[INFO][synthesizer] Feasibility score: {feasibility_score}/100")

    prompt = build_synthesis_prompt(parsed, market, evidence, bear, bull, feasibility_score)

    try:
        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.2,
        )
        raw = response.choices[0].message.content.strip()
        brief = _parse_json(raw)

        if not brief:
            print(f"[WARN][synthesizer] JSON parse failed, returning raw text")
            brief = {"raw_response": raw, "error": "JSON parse failed"}

        print(f"[INFO][synthesizer] Brief generated for {ticker}")
        return brief

    except Exception as e:
        print(f"[ERROR][synthesizer] {ticker}: {e}")
        return {"error": str(e), "ticker": ticker}


# ── Full Pipeline Test ────────────────────────────────────────────────────────
if __name__ == "__main__":
    from hypothesis_parser import parse_hypothesis
    from market_collector import collect_market_context
    from evidence_agent import collect_historical_evidence
    from bear_agent import collect_bear_case
    from bull_agent import collect_bull_case

    hypothesis_text = "Coca-Cola will reach $90 in 3 months"
    print(f"\nRunning full pipeline for: '{hypothesis_text}'\n{'='*60}")

    # Run all 5 agents
    parsed   = parse_hypothesis(hypothesis_text)
    market   = collect_market_context(parsed["ticker"])
    evidence = collect_historical_evidence(
        parsed["ticker"],
        parsed["implied_return_pct"],
        parsed["timeframe_days"],
    )
    bear = collect_bear_case(parsed["ticker"], TICKER_FULL_NAME[parsed["ticker"]])
    bull = collect_bull_case(parsed["ticker"], TICKER_FULL_NAME[parsed["ticker"]])

    # Synthesize
    brief = synthesize(parsed, market, evidence, bear, bull)
    print(json.dumps(brief, indent=2))