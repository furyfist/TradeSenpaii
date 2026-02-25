import os
import json
import time
import pandas as pd
from groq import Groq
from similarity_search import find_similar_days, format_analogies_for_llm

# Config
GROQ_API_KEY    = os.getenv("GROQ_API_KEY")
GROQ_MODEL      = os.getenv("GROQ_MODEL")
GROQ_SEARCH_MODEL = os.getenv("GROQ_SEARCH_MODEL")

TICKER_CONTEXT = {
    "KO":    "Coca-Cola Company, a global beverage giant known for defensive, non-cyclical revenue and consistent dividends.",
    "JNJ":   "Johnson & Johnson, a diversified healthcare company with pharmaceuticals, medical devices, and consumer health segments.",
    "PG":    "Procter & Gamble, a consumer staples leader with iconic household brands like Tide, Pampers, and Gillette.",
    "WMT":   "Walmart Inc., the world's largest retailer known for recession-resistant revenue and dominant supply chain.",
    "AAPL":  "Apple Inc., a technology giant with high-margin hardware, software, and services ecosystem.",
    "GOOGL": "Alphabet Inc., Google's parent company with dominant search advertising and growing cloud business.",
}

TICKER_FULL_NAME = {
    "KO":    "Coca-Cola",
    "JNJ":   "Johnson & Johnson",
    "PG":    "Procter & Gamble",
    "WMT":   "Walmart",
    "AAPL":  "Apple",
    "GOOGL": "Alphabet",
}


# Step 1 — Enrich each analogy with web search
def enrich_analogy_with_search(
    ticker: str,
    date: str,
    actual_direction: str,
    actual_return: float,
) -> dict:
    """
    Uses Groq compound-beta (built-in web search) to find
    what actually happened with this stock on this historical date.

    Returns:
        search_context: plain English explanation of what happened
        search_url:     pre-built Google search URL for the user to explore further
    """
    company = TICKER_FULL_NAME.get(ticker, ticker)

    # Parse date for human-readable format
    try:
        dt         = pd.to_datetime(date)
        month_year = dt.strftime("%B %Y")
        full_date  = dt.strftime("%B %d, %Y")
    except Exception:
        month_year = date
        full_date  = date

    direction_word = "rose" if actual_direction == "UP" else "fell"
    return_str     = f"{actual_return:+.2f}%"

    search_prompt = f"""Search the web and find out what happened with {company} ({ticker}) stock around {full_date}.

The stock {direction_word} {return_str} the next trading day after this date.

Find the most likely business reason — earnings results, analyst upgrades/downgrades, product announcements, regulatory news, macroeconomic events, or SEC filings — that explains this price movement.

Respond in 2-3 sentences only. Be specific: mention actual events, earnings figures, or news if you find them. If you cannot find specific news for this exact date, describe the general market context for {company} during {month_year}.

Do not mention that you searched the web. Write as a factual research note."""

    try:
        client   = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model    = GROQ_SEARCH_MODEL,
            messages = [{"role": "user", "content": search_prompt}],
            max_tokens  = 200,
            temperature = 0.2,
        )
        search_context = response.choices[0].message.content.strip()

    except Exception as e:
        print(f"[WARN] Search enrichment failed for {ticker} {date}: {e}")
        search_context = f"No additional context found for {company} around {full_date}."

    # Build Google search URL for the user to explore further
    query      = f"{company} {ticker} stock {month_year} news earnings"
    query_enc  = query.replace(" ", "+")
    search_url = f"https://www.google.com/search?q={query_enc}"

    return {
        "search_context": search_context,
        "search_url":     search_url,
    }


def enrich_all_analogies(
    ticker: str,
    analogies: list[dict],
) -> list[dict]:
    """
    Enriches all analogies with search context.
    Adds a small delay between calls to avoid rate limiting.
    """
    enriched = []
    for analogy in analogies:
        print(f"[INFO] Searching context for {ticker} {analogy['date']}...")
        search_result = enrich_analogy_with_search(
            ticker           = ticker,
            date             = analogy["date"],
            actual_direction = analogy["actual_direction"],
            actual_return    = analogy["actual_return"],
        )
        enriched_analogy = {**analogy, **search_result}
        enriched.append(enriched_analogy)
        time.sleep(0.5)   # small delay between search calls

    return enriched


# Step 2 — Build LLM synthesis prompt
def build_prompt(
    ticker:          str,
    prediction:      str,
    confidence:      float,
    top_signals:     list[dict],
    analogies:       list[dict],
    sentiment_score: float,
    sentiment_label: str,
) -> str:
    company_context = TICKER_CONTEXT.get(ticker, ticker)
    confidence_pct  = f"{confidence * 100:.1f}%"
    analogy_text    = format_analogies_for_llm(analogies, ticker)

    signals_text = "\n".join([
        f"  - {s['name']}: {s['value']} ({s['state']})"
        for s in top_signals
    ])

    # Include search context in the prompt if available
    search_context_block = ""
    for a in analogies:
        if a.get("search_context"):
            search_context_block += f"\nContext for {a['date']}: {a['search_context']}"

    prompt = f"""You are a financial research analyst explaining a quantitative stock signal to a retail investor.

COMPANY: {ticker} — {company_context}

MODEL PREDICTION: {prediction} with {confidence_pct} confidence
SEC FILING SENTIMENT: {sentiment_label} (score: {sentiment_score:.3f})

CURRENT TECHNICAL SIGNALS:
{signals_text}

{analogy_text}

HISTORICAL CONTEXT FROM NEWS SEARCH:
{search_context_block if search_context_block else "No additional historical context available."}

TASK:
Write a concise, factual explanation (4-6 sentences) of why the model is predicting {prediction} for {ticker} tomorrow.

Your explanation must:
1. Reference specific signals driving the prediction (RSI, sentiment, momentum etc.)
2. Mention the most relevant historical analogy AND the real-world event that drove it (if available)
3. Identify the single biggest risk factor that could invalidate this prediction
4. End with a plain-English summary a retail investor can understand

IMPORTANT RULES:
- Never recommend buying or selling. This is educational/simulation only.
- Be specific — reference actual numbers from the signals
- Be honest about uncertainty — 52% accuracy means this is probabilistic, not certain
- Do not use phrases like "as an AI" or "I cannot provide financial advice"
- Write as: "The model sees..." or "Current conditions show..."

Respond ONLY with valid JSON in this exact format:
{{
  "headline": "one sentence summary (max 15 words)",
  "explanation": "4-6 sentence detailed explanation referencing real events where available",
  "key_driver": "the single most important signal driving this prediction",
  "main_risk": "the single biggest risk factor that could invalidate this prediction",
  "historical_note": "one sentence about the most relevant historical analogy including the real-world event",
  "confidence_tier": "Low Signal | Moderate Signal | Strong Signal | High Conviction"
}}"""

    return prompt


# Step 3 — Confidence tier helper
def get_confidence_tier(confidence: float) -> str:
    if confidence < 0.55:
        return "Low Signal"
    elif confidence < 0.65:
        return "Moderate Signal"
    elif confidence < 0.75:
        return "Strong Signal"
    else:
        return "High Conviction"


# Main entry point
def explain_prediction(
    ticker:           str,
    prediction:       str,
    confidence:       float,
    top_signals:      list[dict],
    sentiment_score:  float,
    sentiment_label:  str,
    current_features: pd.Series,
) -> dict:
    """
    Full explanation pipeline:
    1. Find similar historical days (cosine similarity)
    2. Enrich each analogy with web search context (Groq compound-beta)
    3. Build synthesis prompt with all context
    4. Call Groq for plain-English explanation (llama-3.1-8b-instant)
    5. Return structured result
    """

    # Step 1 — Historical similarity
    try:
        analogies = find_similar_days(ticker, current_features, top_n=3)
    except Exception as e:
        print(f"[WARN] Similarity search failed: {e}")
        analogies = []

    # Step 2 — Web search enrichment per analogy
    if analogies:
        analogies = enrich_all_analogies(ticker, analogies)

    # Step 3 — Build prompt with all context
    prompt = build_prompt(
        ticker          = ticker,
        prediction      = prediction,
        confidence      = confidence,
        top_signals     = top_signals,
        analogies       = analogies,
        sentiment_score = sentiment_score,
        sentiment_label = sentiment_label,
    )

    # Step 4 — LLM synthesis
    try:
        client   = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model       = GROQ_MODEL,
            messages    = [{"role": "user", "content": prompt}],
            max_tokens  = 600,
            temperature = 0.3,
        )

        raw_text = response.choices[0].message.content.strip()

        # Strip markdown fences if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]

        result = json.loads(raw_text)

    except json.JSONDecodeError as e:
        print(f"[WARN] LLM returned invalid JSON: {e}")
        result = {
            "headline":        f"{ticker} model predicts {prediction}",
            "explanation":     raw_text if 'raw_text' in dir() else "Explanation unavailable.",
            "key_driver":      top_signals[0]["name"] if top_signals else "Unknown",
            "main_risk":       "Model uncertainty — 52% accuracy means prediction is probabilistic",
            "historical_note": analogies[0]["date"] if analogies else "No analogies found",
            "confidence_tier": get_confidence_tier(confidence),
        }
    except Exception as e:
        print(f"[ERROR] Groq synthesis failed: {e}")
        result = {
            "headline":        f"{ticker} model predicts {prediction}",
            "explanation":     "Explanation unavailable — LLM service error.",
            "key_driver":      top_signals[0]["name"] if top_signals else "Unknown",
            "main_risk":       "Unable to generate risk analysis",
            "historical_note": "Unable to retrieve historical context",
            "confidence_tier": get_confidence_tier(confidence),
        }

    # Step 5 — Attach enriched analogies and confidence tier
    result["analogies"]       = analogies
    result["confidence_tier"] = get_confidence_tier(confidence)
    return result