# TradeSenpai

**AI-Powered Stock Research Platform**

**Version 3.0 — February 2026**

---

## Overview

TradeSenpai is an AI-powered stock research platform designed to give retail investors access to the same quality of signal analysis that institutional research desks use daily. The platform combines quantitative technical analysis, SEC regulatory filing sentiment, transformer-based machine learning models, and a multi-agent AI hypothesis engine to deliver structured, explainable research — not arbitrary price predictions.

The core premise is straightforward: retail investors are at an information disadvantage not because markets are rigged, but because the tools and workflows used by institutional analysts — reading 10-Ks for language shifts, computing technical regimes, synthesizing historical analogies — are simply inaccessible. TradeSenpai automates that workflow and surfaces it through a clean, terminal-aesthetic research interface.

> **This is not a trading system.** TradeSenpai is an educational simulation and research augmentation tool. Model accuracy is 51.9–53.5% on next-day direction classification — honest and statistically meaningful given market noise, not a failure. The academic ceiling for short-term direction prediction is approximately 55–56%. All outputs include explicit uncertainty disclosures.

---

## What's New in Version 3

Version 3 represents the largest architectural leap in the project's history. Two major systems were introduced on top of the V2 prediction and explanation foundation:

### 1. Hypothesis Engine (6-Agent AI Research Pipeline)

A user submits a natural language market hypothesis — for example, *"Apple will drop 10% in the next 60 days"* — and six independent AI agents research, validate, stress-test, and synthesize it into a structured research brief.

| Agent | Role |
|-------|------|
| **Agent 1 — Parser** | Extracts ticker, target price, timeframe, implied return, and hypothesis type from free text. Flags statistically unrealistic moves using a z-score against 5-year rolling return distributions. |
| **Agent 2 — Market Context** | Pulls the current live technical state for the identified ticker: RSI, MA regime, momentum, volatility, Bollinger band position, sentiment score. |
| **Agent 3 — Historical Evidence** | Computes base rates from the full historical dataset: what percentage of comparable windows produced the implied move? Surfaces the top 3 most similar historical setups via cosine similarity. |
| **Agent 4 — Bear Case** | Uses Tavily web search + Llama 3.3-70B to retrieve and format current sourced evidence for the downside scenario. |
| **Agent 5 — Bull Case** | Same architecture as Agent 4, for the upside scenario. |
| **Agent 6 — Synthesizer** | Receives all five agent outputs and produces a structured research brief: feasibility score (0–100), verdict, key risks, key catalysts, and a quantitative summary. |

The feasibility score is interpretable and composable: 40 points from the historical base rate for the implied move, 30 points from technical regime alignment, 30 points from the realism check (penalizing statistically implausible hypotheses).

### 2. Telegram Alert System

A scheduled, multi-subscriber alert delivery system built on APScheduler and the Telegram Bot API:

- **Morning Brief** (9:30 AM ET) — Directional predictions, confidence tiers, and sentiment readings for all six tickers
- **Evening Brief** (4:15 PM ET) — Actual vs. predicted outcomes for the day with accuracy tracking
- **Weekly Digest** (Sunday 6:00 PM ET) — Per-ticker accuracy statistics from the live prediction history database
- **Signal Alerts** (every 2 hours) — Direction flip, sentiment spike, and litigation flag change notifications

Subscriber management is handled through a `/subscribe` endpoint with optional self-registration via Telegram chat ID (immediate approval) or admin-controlled approval for username-only registrations.

---

## Full Feature Set

### Prediction & Analysis
- **Next-Day Directional Prediction** — Binary UP/DOWN classification with probability-based confidence score and tier (Low / Moderate / Strong / High Conviction)
- **56-Feature Engineering Pipeline** — Price features (daily return, lags, MAs, Bollinger band distances, RSI, momentum, volatility, volume regime), calendar features, LM sentiment features (positive, negative, uncertain, litigious, constraining word counts and derived metrics), sentiment lags, return lags, regime flags, and interaction terms
- **Per-Ticker Transformer Models** — One PyTorch Transformer encoder per ticker (d_model=128, 4 attention heads, 3 layers, 60-day lookback window, pre-norm architecture for training stability)
- **LM Sentiment Analysis** — Loughran-McDonald financial dictionary-based sentiment scoring on full SEC filing history (10-K, 10-Q, 8-K from EDGAR, 1993/1994–present)

### Explanation & Research
- **AI Explanation Panel** — Groq Llama 3.3-70B generates: headline, plain-English explanation, key driver, main risk, historical note, and confidence tier context
- **Historical Analogy Cards** — Top 3 most similar historical setups (cosine similarity on 38 features, filtered to ≥365 days ago), each enriched with what actually happened on that date
- **Signal Breakdown** — Color-coded display of key contributing signals with current state

### Hypothesis Engine
- **Natural Language Hypothesis Input** — Free-text submission, automatically parsed for ticker, target, and timeframe
- **Realism Check** — Z-score vs. 5-year rolling return distribution; statistically impossible hypotheses flagged at parse time
- **Sourced Bear & Bull Cases** — Real articles from current sources (Nasdaq, GuruFocus, analyst reports) via Tavily, not hallucinated content
- **Feasibility Score** — Composite 0–100 score from base rate + technical alignment + realism check
- **Streaming Pipeline** — Research brief built and streamed step by step with per-agent status updates in real time

### Alerts & Notifications
- **Telegram Alert Delivery** — Scheduled briefs and real-time signal alerts
- **Subscriber Management** — Self-registration with optional chat ID for immediate activation, or pending admin approval
- **Prediction History Database** — Every prediction logged to SQLite; evening scheduler fills actual outcomes automatically via yfinance price fetch
- **Live Accuracy Tracking** — Per-ticker accuracy computed from real prediction vs. outcome records, displayed in weekly digest

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                             │
│   React / Vite  ·  IBM Plex Mono  ·  Terminal Aesthetic     │
│                                                             │
│   /              → Landing page + animated ticker tape      │
│   /dashboard     → Prediction, charts, signals, explain     │
│   /hypothesis    → 6-agent research pipeline UI             │
│   /admin         → Hidden subscriber management panel       │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP / SSE
┌────────────────────────▼────────────────────────────────────┐
│                        BACKEND                              │
│                   FastAPI · Port 8000                        │
│                                                             │
│   /predict           /price-history    /sentiment-history   │
│   /explain           /model-info       /hypothesis/stream   │
│   /subscribe         /subscribers     /hypothesis           │
│                                                             │
│   ┌─────────────────┐   ┌─────────────────────────────┐    │
│   │  ML Inference   │   │    6-Agent Hypothesis        │    │
│   │  6 Transformer  │   │    Pipeline                  │    │
│   │  .pt checkpoints│   │    (Parser → Market →        │    │
│   │  (per ticker)   │   │    Evidence → Bear → Bull    │    │
│   └────────┬────────┘   │    → Synthesizer)            │    │
│            │            └──────────────┬────────────── ┘    │
│   ┌────────▼────────────────────────── ▼───────────────┐   │
│   │              Feature Engineer                       │   │
│   │   56-feature pipeline · yfinance · LM Sentiment     │   │
│   └──────────────────────────────────────────────────── ┘   │
│                                                             │
│   ┌──────────────────────────────────────────────────────┐  │
│   │   APScheduler  ·  Telegram Bot  ·  SQLite (alerts.db)│  │
│   │   Morning/Evening/Weekly jobs  ·  Signal watchers    │  │
│   └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   DATA PIPELINE                             │
│   stock-analysis/scripts/                                   │
│                                                             │
│   fetch_stock_data.py   →  OHLCV via yfinance              │
│   fetch_sec_filings.py  →  SEC EDGAR (10-K, 10-Q, 8-K)     │
│   preprocess_filings.py →  HTML strip, encoding clean      │
│   lm_sentiment.py       →  LM dictionary scoring           │
│   merge_datasets.py     →  56-feature merged CSV           │
│   training.ipynb        →  TimeSeriesSplit CV, .pt save     │
└─────────────────────────────────────────────────────────────┘
```

**External Integrations:**

| Service | Purpose |
|---------|---------|
| **yfinance** | Live and historical OHLCV price data |
| **SEC EDGAR API** | 10-K, 10-Q, 8-K filings (1993/1994–present) |
| **Groq (Llama 3.3-70B)** | LLM synthesis for explanations and hypothesis briefs |
| **Tavily** | Web search for sourced bear/bull case evidence |
| **Telegram Bot API** | Alert delivery and subscriber management |

---

## Model Performance

All models use TimeSeriesSplit cross-validation (no lookahead leakage). Accuracy reflects real-world directional prediction difficulty.

| Ticker | Company | CV Accuracy | Sector |
|--------|---------|-------------|--------|
| KO | Coca-Cola | **52.29%** ± 0.67% | Consumer Staples |
| JNJ | Johnson & Johnson | **51.97%** ± 1.10% | Healthcare |
| PG | Procter & Gamble | **51.92%** ± 1.31% | Consumer Staples |
| WMT | Walmart | **53.33%** ± 1.47% | Retail |
| AAPL | Apple | **52.40%** ± 0.76% | Technology |
| GOOGL | Alphabet | **53.48%** ± 1.22% | Technology |

All models exceed the majority-class baseline (50%). The range of 51.9–53.5% is consistent with published academic results on short-term equity direction classification. The ceiling for this task is approximately 55–56%.

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **ML Framework** | PyTorch 2.x | Transformer model training and inference |
| **Data Processing** | pandas, numpy, scikit-learn | Feature engineering, scaling, similarity search |
| **Sentiment Analysis** | Loughran-McDonald Dictionary | Domain-specific SEC filing sentiment |
| **Backend** | FastAPI + uvicorn | REST API, SSE streaming, rate limiting (slowapi) |
| **Background Jobs** | APScheduler | Scheduled alert delivery |
| **Database** | SQLite | Alert deduplication, subscriber management, prediction history |
| **Bot Integration** | python-telegram-bot | Telegram alert delivery and subscriber listener |
| **LLM** | Groq API (Llama 3.3-70B) | Explanation synthesis, hypothesis research brief |
| **Web Search** | Tavily API | Sourced evidence for bear/bull case agents |
| **Frontend** | React 18 + Vite | Single-page application with multi-route navigation |
| **Charts** | Recharts | Price history and sentiment history visualizations |
| **Price Data** | yfinance | Live and historical OHLCV |
| **Filing Data** | sec-edgar-downloader | SEC EDGAR filing retrieval |
| **HTTP Client** | axios | Frontend API communication |

---

## Installation

### Prerequisites

- Python 3.10+
- Node.js 18+ and npm
- API keys: Groq, Tavily, Telegram Bot Token

### 1. Clone the Repository

```bash
git clone https://github.com/furyfist/TradeSenpaii.git
cd TradeSenpai
```

### 2. Python Environment

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

### 3. Frontend Setup

```bash
cd app/frontend
npm install
```

### 4. Environment Variables

Create `app/backend/.env`:

```env
GROQ_API_KEY=your_groq_key
TAVILY_API_KEY=your_tavily_key
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_ADMIN_CHAT_ID=your_chat_id
ADMIN_PASSWORD=your_admin_password
```

Create `app/frontend/.env`:

```env
VITE_ADMIN_PASSWORD=your_admin_password
```

### 5. Data Pipeline (per ticker)

```bash
cd stock-analysis

python scripts/fetch_stock_data.py --ticker KO
python scripts/fetch_sec_filings.py --ticker KO
python scripts/preprocess_filings.py --ticker KO
python scripts/lm_sentiment.py --ticker KO
python scripts/merge_datasets.py --ticker KO
```

Repeat for: `JNJ`, `PG`, `WMT`, `AAPL`, `GOOGL`

### 6. Model Training (optional — pre-trained checkpoints included)

Open `training.ipynb` on Kaggle or locally with GPU. Checkpoints are saved to `app/backend/model/transformer_{TICKER}.pt`.

---

## Running the Application

### Backend

```bash
cd app/backend
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd app/frontend
npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

### Application Routes

| Route | Description |
|-------|-------------|
| `/` | Landing page with live ticker tape and feature overview |
| `/dashboard` | Main prediction dashboard — select ticker, view charts, signals, AI explanation |
| `/hypothesis` | Hypothesis engine — submit a market thesis and receive a full research brief |
| `/admin` | Hidden admin panel for subscriber management (requires password) |

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service status and version |
| `/predict` | GET | Next-day prediction + confidence for a ticker |
| `/price-history` | GET | 90-day OHLCV price history |
| `/sentiment-history` | GET | LM sentiment score history |
| `/explain` | GET | AI-generated explanation with analogies |
| `/model-info` | GET | Model metadata and CV accuracy |
| `/hypothesis` | POST | Synchronous 6-agent research brief |
| `/hypothesis/stream` | POST | Streaming 6-agent pipeline with per-step status |
| `/subscribe` | POST | Submit subscriber request |
| `/subscribers` | GET | List all subscribers (admin) |
| `/subscribers/{id}/approve` | POST | Approve a subscriber (admin) |
| `/subscribers/{id}/reject` | POST | Reject a subscriber (admin) |

---

## Known Limitations

- **~52% accuracy ceiling** — Inherent to short-term direction prediction on public data. This is the honest bound, not a failure of the implementation.
- **Forward-filled sentiment** — LM scores are forward-filled between SEC filing dates. Intra-quarter sentiment is static.
- **No earnings calendar integration** — Earnings event flags are not yet included in the feature set.
- **No macro features** — VIX, SPX regime, interest rate data are not currently used.
- **yfinance dependency** — No SLA guarantees; occasional data gaps require handling.
- **Local deployment only** — V3 runs on localhost. Cloud deployment (Railway, Render) is architecturally straightforward but not yet implemented.
- **Desktop-focused UI** — Not optimized for mobile viewports.

---

## Technical Debt

| Item | Priority | Notes |
|------|----------|-------|
| Zero test coverage | High | No unit or integration tests exist |
| Inline CSS in all React components | Medium | Works but verbose; migration to CSS modules planned |
| No earnings calendar feature | High | Known gap since V2; significant signal value |
| No input sanitization on hypothesis text | Medium | Currently trusts user input |
| Inline CSS → CSS modules | Low | Cosmetic; no functional impact |
| `bot_listener.py` daemon thread | Low | Not gracefully stoppable on server shutdown |

---

## Design Principles

These principles emerged empirically across three versions and are now explicit constraints on the project:

1. **Domain-specific beats general-purpose.** The Loughran-McDonald dictionary outperformed FinBERT on SEC filings. A curated 2,700-word lexicon built for financial regulatory documents outperformed a 110M-parameter neural network. Fit to domain matters more than parameter count.

2. **Honest accuracy is more valuable than inflated accuracy.** 52% CV accuracy is reported and displayed openly. Chasing a higher number would require either overfitting or data leakage — both of which would make the tool less trustworthy, not more useful.

3. **Explanation value exceeds prediction value.** Users benefit more from understanding *why* a signal exists than from a bare UP/DOWN. The explanation layer, historical analogies, and hypothesis engine all serve this principle.

4. **Silent failures are the hardest bugs.** Every significant bug in this project produced no error — the hardcoded ticker, the naming collision, the wrong broadcast function. Logging and assertions at key pipeline stages are the primary defense.

5. **Per-ticker models over shared models.** A single model trained across all tickers must learn six different volatility regimes simultaneously. Separate models are simpler, more accurate, and independently debuggable.

---

## Roadmap (V4)

- Cloud deployment (Railway / Render)
- Earnings calendar feature integration
- Prediction history visualization in the dashboard
- Backtesting view for hypothesis feasibility scores
- Additional tickers (expansion beyond current six)
- Test suite (pytest for backend, vitest for frontend)

---

## License

MIT — see [LICENSE](LICENSE)

---

**Version 3.0 — February 2026**
*From single-ticker proof of concept to a multi-agent, multi-component stock research platform.*