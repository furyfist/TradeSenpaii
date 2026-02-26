
import sys, os, json, re
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from groq import Groq
from tavily import TavilyClient
from dotenv import load_dotenv
load_dotenv()

GROQ_API_KEY   = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

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
        # Step 1 — Tavily search
        tavily = TavilyClient(api_key=TAVILY_API_KEY)
        search = tavily.search(
            query=f"{company_name} {ticker} stock risks headwinds 2026",
            search_depth="basic",
            max_results=3,
        )

        # Extract snippets + urls
        sources = []
        for r in search.get("results", []):
            sources.append({
                "content": r.get("content", ""),
                "url": r.get("url", ""),
                "title": r.get("title", ""),
            })

        search_text = "\n\n".join([
            f"Source: {s['url']}\n{s['content'][:300]}" for s in sources
        ])
        print(f"[INFO][bear_agent] Tavily returned {len(sources)} results for {ticker}")

        # Step 2 — llama formats into structured JSON
        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a financial analyst. Based on the search results, "
                        "identify exactly 3 key risks for this stock. "
                        "Return ONLY a JSON array, no markdown. "
                        "Each item must have: title (5 words max), description (2 sentences), source_url."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Search results for {company_name} risks:\n\n{search_text}"
                },
            ],
            max_tokens=500,
            temperature=0.1,
        )
        raw = response.choices[0].message.content.strip()
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