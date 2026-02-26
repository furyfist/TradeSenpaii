import sys, os, json, re
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from groq import Groq
from dotenv import load_dotenv
load_dotenv()

GROQ_API_KEY      = os.getenv("GROQ_API_KEY")
GROQ_SEARCH_MODEL = os.getenv("GROQ_SEARCH_MODEL")

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

def collect_bull_case(ticker: str, company_name: str) -> dict:
    print(f"[INFO][bull_agent] Fetching bull case for {ticker}")
    result = {"ticker": ticker, "catalysts": [], "error": None}

    query = f"What are the biggest catalysts and growth drivers for {company_name} ({ticker}) stock in 2026?"

    try:
        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model=GROQ_SEARCH_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Return ONLY a JSON array of 3 risks. Each: {title, description, source_url}. No markdown.",
                },
                {"role": "user", "content": query},
            ],
            temperature=0.2,
            max_tokens=400,
        )
        raw = response.choices[0].message.content.strip()
        catalysts = _parse_json_list(raw)
        result["catalysts"] = catalysts
        print(f"[INFO][bull_agent] {ticker} — {len(catalysts)} catalysts found")

    except Exception as e:
        result["error"] = str(e)
        print(f"[ERROR][bull_agent] {ticker}: {e}")

    return result

if __name__ == "__main__":
    result = collect_bull_case("KO", "Coca-Cola")
    print(json.dumps(result, indent=2))