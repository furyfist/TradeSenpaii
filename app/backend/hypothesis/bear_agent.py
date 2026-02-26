import sys, os, json, re
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from groq import Groq
from dotenv import load_dotenv
load_dotenv()

GROQ_API_KEY      = os.getenv("GROQ_API_KEY")
GROQ_SEARCH_MODEL = os.getenv("GROQ_SEARCH_MODEL")  # groq/compound

def _parse_json_list(raw: str) -> list:
    try:
        return json.loads(raw)
    except Exception:
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
    return []

def collect_bear_case(ticker: str, company_name: str) -> dict:
    print(f"[INFO][bear_agent] Fetching bear case for {ticker}")
    result = {"ticker": ticker, "risks": [], "error": None}

    try:
        client = Groq(api_key=GROQ_API_KEY)

        # Step 1 — compound search with minimal prompt
        search_response = client.chat.completions.create(
            model=GROQ_SEARCH_MODEL,
            messages=[
                {"role": "user", "content": f"What are the main risks facing {company_name} stock in 2026?"}
            ],
            max_tokens=300,
            temperature=0.2,
        )
        search_text = search_response.choices[0].message.content.strip()
        print(f"[INFO][bear_agent] Search complete for {ticker}")

        # Step 2 — llama formats into JSON
        format_response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "Extract exactly 3 risks from the text. Return ONLY a JSON array. Each item: {title, description, source_url}. No markdown.",
                },
                {"role": "user", "content": search_text},
            ],
            max_tokens=500,
            temperature=0.1,
        )
        raw = format_response.choices[0].message.content.strip()
        risks = _parse_json_list(raw)
        result["risks"] = risks
        print(f"[INFO][bear_agent] {ticker} — {len(risks)} risks found")

    except Exception as e:
        result["error"] = str(e)
        print(f"[ERROR][bear_agent] {ticker}: {e}")

    return result

if __name__ == "__main__":
    result = collect_bear_case("KO", "Coca-Cola")
    print(json.dumps(result, indent=2))