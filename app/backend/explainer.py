import os
from groq import Groq
from similarity_search import find_similar_days, format_analogies_for_llm
import pandas as pd
import json

# Set your Groq API key here
# Note: It will expire on 27 March 2026
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL   = "llama-3.1-8b-instant"   # free, fast, good enough

TICKER_CONTEXT = {
    "KO":    "Coca-Cola Company, a global beverage giant known for defensive, non-cyclical revenue and consistent dividends.",
    "JNJ":   "Johnson & Johnson, a diversified healthcare company with pharmaceuticals, medical devices, and consumer health segments.",
    "PG":    "Procter & Gamble, a consumer staples leader with iconic household brands like Tide, Pampers, and Gillette.",
    "WMT":   "Walmart Inc., the world's largest retailer known for recession-resistant revenue and dominant supply chain.",
    "AAPL":  "Apple Inc., a technology giant with high-margin hardware, software, and services ecosystem.",
    "GOOGL": "Alphabet Inc., Google's parent company with dominant search advertising and growing cloud business.",
}


def build_prompt(
    ticker:          str,
    prediction:      str,
    confidence:      float,
    top_signals:     list[dict],
    analogies:       list[dict],
    sentiment_score: float,
    sentiment_label: str,
) -> str:
    """
    Builds the full LLM prompt combining:
    - Current market signals
    - Model prediction
    - Historical analogies
    """
    company_context = TICKER_CONTEXT.get(ticker, ticker)
    confidence_pct  = f"{confidence * 100:.1f}%"
    analogy_text    = format_analogies_for_llm(analogies, ticker)

    # Format top signals
    signals_text = "\n".join([
        f"  - {s['name']}: {s['value']} ({s['state']})"
        for s in top_signals
    ])

    prompt = f"""You are a financial research analyst explaining a quantitative stock signal to a retail investor.

COMPANY: {ticker} — {company_context}

MODEL PREDICTION: {prediction} with {confidence_pct} confidence
SEC FILING SENTIMENT: {sentiment_label} (score: {sentiment_score:.3f})

CURRENT TECHNICAL SIGNALS:
{signals_text}

{analogy_text}

TASK:
Write a concise, factual explanation (4-6 sentences) of why the model is predicting {prediction} for {ticker} tomorrow.

Your explanation must:
1. Reference the specific signals driving the prediction (RSI, sentiment, momentum etc.)
2. Mention the most relevant historical analogy and what actually happened
3. Identify the single biggest risk factor that could invalidate this prediction
4. End with a one-sentence plain-English summary a retail investor can understand

IMPORTANT RULES:
- Never recommend buying or selling. This is educational/simulation only.
- Be specific — reference actual numbers from the signals
- Be honest about uncertainty — 52% accuracy means this is probabilistic, not certain
- Do not use phrases like "as an AI" or "I cannot provide financial advice"
- Write in second person: "The model sees..." or "Current conditions show..."

Respond ONLY with a valid JSON object in this exact format:
{{
  "headline": "one sentence summary (max 15 words)",
  "explanation": "4-6 sentence detailed explanation",
  "key_driver": "the single most important signal driving this prediction",
  "main_risk": "the single biggest risk factor that could invalidate this prediction",
  "historical_note": "one sentence about the most relevant historical analogy",
  "confidence_tier": "Low Signal | Moderate Signal | Strong Signal | High Conviction"
}}"""

    return prompt


def get_confidence_tier(confidence: float) -> str:
    if confidence < 0.55:
        return "Low Signal"
    elif confidence < 0.65:
        return "Moderate Signal"
    elif confidence < 0.75:
        return "Strong Signal"
    else:
        return "High Conviction"


def explain_prediction(
    ticker:          str,
    prediction:      str,
    confidence:      float,
    top_signals:     list[dict],
    sentiment_score: float,
    sentiment_label: str,
    current_features: pd.Series,
) -> dict:
    """
    Full explanation pipeline:
    1. Find similar historical days
    2. Build LLM prompt
    3. Call Groq API
    4. Return structured explanation
    """
    # Step 1 — Find historical analogies
    try:
        analogies = find_similar_days(ticker, current_features, top_n=3)
    except Exception as e:
        print(f"[WARN] Similarity search failed: {e}")
        analogies = []

    # Step 2 — Build prompt
    prompt = build_prompt(
        ticker          = ticker,
        prediction      = prediction,
        confidence      = confidence,
        top_signals     = top_signals,
        analogies       = analogies,
        sentiment_score = sentiment_score,
        sentiment_label = sentiment_label,
    )

    # Step 3 — Call Groq
    try:
        client   = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model    = GROQ_MODEL,
            messages = [{"role": "user", "content": prompt}],
            max_tokens      = 600,
            temperature     = 0.3,    # low temp = more factual, less creative
        )

        raw_text = response.choices[0].message.content.strip()

        # Strip markdown code fences if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]

        result = json.loads(raw_text)

    except json.JSONDecodeError as e:
        print(f"[WARN] LLM returned invalid JSON: {e}")
        result = {
            "headline":        f"{ticker} model predicts {prediction}",
            "explanation":     raw_text,
            "key_driver":      top_signals[0]["name"] if top_signals else "Unknown",
            "main_risk":       "Model uncertainty — 52% accuracy means prediction is probabilistic",
            "historical_note": analogies[0]["date"] if analogies else "No analogies found",
            "confidence_tier": get_confidence_tier(confidence),
        }
    except Exception as e:
        print(f"[ERROR] Groq API call failed: {e}")
        result = {
            "headline":        f"{ticker} model predicts {prediction}",
            "explanation":     "Explanation unavailable — LLM service error.",
            "key_driver":      top_signals[0]["name"] if top_signals else "Unknown",
            "main_risk":       "Unable to generate risk analysis",
            "historical_note": "Unable to retrieve historical context",
            "confidence_tier": get_confidence_tier(confidence),
        }

    # Always attach analogies to result
    result["analogies"]        = analogies
    result["confidence_tier"]  = get_confidence_tier(confidence)
    return result