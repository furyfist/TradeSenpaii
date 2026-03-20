# TRADESENPAI — API REFERENCE
### V5 · March 2026

---

**PRODUCTION**: `https://tradesenpaii-production.up.railway.app`
**LOCAL DEV**: `http://localhost:8000`
**API DOCS**: `/docs` (Swagger UI — interactive)

---

## ENDPOINTS

### CORE

---

**01** `GET /health`
> API status, version, supported tickers
> **Parameters**: None

---

**02** `GET /tickers`
> List all supported tickers with company names
> **Parameters**: None

---

**03** `GET /predict?ticker=KO`
> Transformer model — UP/DOWN prediction + confidence score
> **Parameters**: `ticker` (`KO` | `JNJ` | `PG` | `WMT` | `AAPL` | `GOOGL`)
> **Cache**: 30 minutes per ticker
> **Response fields**: `prediction`, `confidence`, `prob_up`, `prob_down`, `top_signals`, `cv_accuracy`, `sentiment_score`, `sentiment_label`

---

**04** `GET /price-history?ticker=KO`
> 90-day OHLCV price data
> **Parameters**: `ticker`

---

**05** `GET /sentiment-history?ticker=KO`
> LM sentiment scores per SEC filing date
> **Parameters**: `ticker`

---

**06** `GET /model-info?ticker=KO`
> CV accuracy, feature count, sequence length, architecture
> **Parameters**: `ticker`

---

**07** `GET /explain?ticker=KO`
> Groq LLM explanation — headline, key driver, main risk, historical note, analogies (~8s)
> **Parameters**: `ticker`
> **Rate limit**: 10 req/min

---

### RESEARCH INTELLIGENCE

---

**08** `POST /hypothesis/stream`
> 6-agent research pipeline — streams SSE per-agent progress
> **Body**:
```json
{"text": "Coca-Cola will reach $90 in 3 months"}
```
> **Rate limit**: 5 req/min
> **Response**: Server-Sent Events stream
> ```
> data: {"step": 1, "status": "running"}
> data: {"step": 1, "status": "done", "ticker": "KO"}
> data: {"step": 2, "status": "done", "price": 73.4, "rsi": 54.2}
> data: {"step": 3, "status": "done", "base_rate": 0.42}
> data: {"step": 4, "status": "done", "risks_found": 3}
> data: {"step": 5, "status": "done", "catalysts_found": 2}
> data: {"step": 6, "status": "done"}
> data: {"step": 0, "status": "complete", "brief": {...}}
> ```

---

**09** `GET /prediction-history?ticker=AAPL`
> Backtested predictions from Supabase — direction calls with actual outcomes and price
> **Parameters**: `ticker`
> **Response fields per row**: `date`, `prediction`, `confidence`, `actual_direction`, `actual_return`, `correct`, `close`
> **Response also includes**: `stats` (total, correct, accuracy, date_from, date_to)
> **Data range**: Feb 2024 → Mar 2026 · ~500 predictions per ticker

---

**10** `GET /anomaly-history?ticker=JNJ`
> SEC filing anomaly data from anomaly_results.csv
> **Parameters**: `ticker` (optional — omit for all 6 tickers)
> **Response fields per filing**: `date`, `form_type`, `sentiment`, `neg_pct`, `uncertain_pct`, `litigation`, `risk_level`, `anomaly_count`, `signals`
> **Response also includes**: `total_filings`, `total_flagged`
> **Note**: Requires `anomaly_results.csv` at project root (run `anomaly_detector.py --export` first)

---

**11** `GET /evidence-cases`
> Top hero evidence cases — bearish signals that preceded >5% drops within 90 days
> **Parameters**: None
> **Response fields per case**: `ticker`, `filing_date`, `form_type`, `risk_level`, `signals`, `base_price`, `return_30d`, `return_60d`, `return_90d`
> **Note**: Requires `evidence_cases.csv` at project root (run `evidence_builder.py --export` first)

---

**12** `GET /filing-list?ticker=JNJ`
> Recent 10-K and 10-Q filings for a ticker from EDGAR
> **Parameters**: `ticker`
> **Response fields per filing**: `ticker`, `form`, `date`, `accession`, `primaryDocument`
> **Returns**: Last 20 qualifying filings

---

**13** `GET /filing-viewer?ticker=JNJ&accession=0000200406-26-000016`
> Fetches actual SEC filing text from EDGAR, extracts key sections, highlights risk sentences
> **Parameters**: `ticker`, `accession` (format: `0000200406-26-000016`)
> **Response**: Sections array with highlighted sentences + stats
> **Response structure**:
> ```json
> {
>   "ticker": "JNJ",
>   "accession": "0000200406-26-000016",
>   "sections": [
>     {
>       "name": "Risk Factors",
>       "sentences": [
>         {
>           "text": "...",
>           "tags": ["negative", "uncertainty"],
>           "highlighted": true
>         }
>       ]
>     }
>   ],
>   "stats": {
>     "total": 60,
>     "highlighted": 9,
>     "pct": 15.0,
>     "negative": 4,
>     "uncertainty": 3,
>     "litigation": 2
>   }
> }
> ```
> **Note**: EDGAR requests take 5–15 seconds (government server). Retry logic built in (3 attempts).
> **Sections extracted**: Risk Factors, MD&A, Legal Proceedings, Liquidity

---

**14** `POST /explain-sentence`
> Plain English explanation of a raw SEC filing sentence via Groq
> **Body**:
> ```json
> {"text": "We may be unable to maintain compliance with debt covenants...", "ticker": "JNJ"}
> ```
> **Rate limit**: 20 req/min
> **Response**: `{"explanation": "..."}`
> **Model**: llama-3.3-70b-versatile · max_tokens=200

---

### ALERTS & SUBSCRIPTIONS

---

**15** `POST /subscribe`
> Submit Telegram alert subscription request
> **Body**:
> ```json
> {"username": "john", "telegram_id": "123456789"}
> ```
> **Rate limit**: 3 req/min
> **Note**: If `telegram_id` provided → auto-approved immediately. Otherwise → pending admin approval.

---

**16** `GET /subscribers` 🔐 *JWT ADMIN*
> List all subscribers with status, username, chat ID
> **Header**: `Authorization: Bearer <token>`

---

**17** `POST /subscribers/{id}/approve` 🔐 *JWT ADMIN*
> Approve subscriber + send Telegram welcome message
> **Body**:
> ```json
> {"telegram_id": "123456789"}
> ```
> **Header**: `Authorization: Bearer <token>`

---

**18** `POST /subscribers/{id}/reject` 🔐 *JWT ADMIN*
> Reject a pending subscriber request
> **Header**: `Authorization: Bearer <token>`

---

## SUPPORTED TICKERS

| Ticker | Company | Sector | CV Accuracy | Backtest Accuracy |
|--------|---------|--------|-------------|-------------------|
| `KO` | Coca-Cola | Consumer Staples | 52.29% | 48.4% |
| `JNJ` | Johnson & Johnson | Healthcare | 51.97% | 55.5% |
| `PG` | Procter & Gamble | Consumer Staples | 51.92% | 52.8% |
| `WMT` | Walmart | Retail | 53.33% | 47.8% |
| `AAPL` | Apple | Technology | 52.40% | 55.2% |
| `GOOGL` | Alphabet | Technology | 53.48% | 55.0% |

---

## AUTHENTICATION

Admin endpoints require a **Supabase JWT** with `role=admin`

- **Header format**: `Authorization: Bearer <access_token>`
- **Token endpoint**: `POST {supabase_url}/auth/v1/token`
- **Algorithm**: `ES256` (Supabase default, HS256 fallback)
- **Expiry**: 1 hour
- **Admin setup**: Set `raw_user_meta_data = {"role": "admin"}` via Supabase SQL editor

---

## RATE LIMITS

| Endpoint | Limit |
|----------|-------|
| `/explain` | 10 req/min |
| `/hypothesis/stream` | 5 req/min |
| `/subscribe` | 3 req/min |
| `/explain-sentence` | 20 req/min |
| All others | No limit |

---

## ERROR CODES

| Code | Meaning |
|------|---------|
| `400` | Bad request — invalid ticker, missing body field, or unknown accession |
| `401` | Unauthorized — missing or invalid JWT token |
| `403` | Forbidden — valid JWT but insufficient role |
| `404` | Not found — subscriber ID or CSV file does not exist |
| `429` | Too many requests — rate limit exceeded |
| `500` | Internal server error — check Railway logs |

---

## OFFLINE DATA REQUIREMENTS

Some endpoints require pre-generated CSV files at the project root:

| Endpoint | Required File | How to Generate |
|----------|--------------|-----------------|
| `/anomaly-history` | `anomaly_results.csv` | `python anomaly_detector.py --export` |
| `/evidence-cases` | `evidence_cases.csv` | `python evidence_builder.py --export` |
| `/prediction-history` | Supabase `prediction_history` table | `python backtest.py --days 500` |

---

## NOTES

- All responses are `JSON` except `/hypothesis/stream` (SSE)
- `/hypothesis/stream` uses **Server-Sent Events** — connect with `EventSource` or `fetch` + `ReadableStream`
- Predictions cached **30 min** per ticker — same ticker returns cached result within window
- EDGAR filing requests take **5–15 seconds** — build loading states accordingly
- Interactive docs at `/docs` (Swagger UI)
- All sentiment data uses **Loughran-McDonald financial dictionary** — not FinBERT or general sentiment models

---

> ⚠️ EDUCATIONAL SIMULATION ONLY — NOT FINANCIAL ADVICE
