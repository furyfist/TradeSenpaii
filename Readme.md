
# TradeSenpai

> SEC filing risk intelligence platform — detecting linguistic anomalies in financial documents before the market reacts.

**Version 5.0 — March 2026**

📄 **[API Reference](Api_reference.md)** — Full endpoint documentation (V5 · March 2026)

---



[![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat-square&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-blue?style=flat-square&logo=react)](https://react.dev)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.6-red?style=flat-square&logo=pytorch)](https://pytorch.org)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

---

## What Is This

Retail investors don't read SEC filings. Institutional analysts do — every quarter, cover to cover, looking for language shifts that precede price moves.

TradeSenpai automates that workflow. It parses every 10-K and 10-Q filed by 6 public companies since 1994, detects when a company's language deviates from its own historical baseline, and surfaces those anomalies before the market has fully reacted.

**This is not a trading system.** It is an educational research platform that answers one question: *what are SEC filings actually saying, and when does that language get unusual?*

---

## The Evidence

Three real cases where filing signals preceded significant price moves:

| Ticker | Filing Date | Signal | 30d Return | 60d Return | 90d Return |
|--------|-------------|--------|-----------|-----------|-----------|
| **GOOGL** | 2022-02-02 | Sentiment Score anomaly | -9.6% | -22.9% | **-28.1%** |
| **AAPL** | 2002-05-14 | Negative Language + Litigation spike | -35.4% | -40.3% | **-41.9%** |
| **JNJ** | 2008-11-04 | Litigation Count + Sentiment drop | -4.2% | -6.0% | **-16.7%** |

> Signal accuracy on 30-day forward returns: 44.7% overall. These are structural risk indicators, not short-term trading signals. High-impact cases show stronger directional alignment over 90-day windows.

**Notable anomaly:** JNJ's 2008 Q2 10-Q showed a litigation count spike of **92.55σ** above baseline — 141 litigation mentions in a single filing. This was the Risperdal/talc litigation wave before it became front-page news.

---

## What's New in V5

V5 shifts the project from a prediction platform to a **risk intelligence platform**. Four major systems were added on top of the V4 prediction foundation:

| Feature | Description |
|---------|-------------|
| **Backtesting Engine** | 3,000 verified predictions across 500 trading days per ticker. Real accuracy numbers, no hardcoding. |
| **SEC Anomaly Detector** | Quarter-over-quarter linguistic anomaly detection. 425 filings analyzed, 169 anomalies flagged across 1994–2026. |
| **Risk Timeline** | Interactive chart showing sentiment score history per ticker with flagged filing markers and evidence cases. |
| **Filing Viewer** | Live EDGAR API integration — read actual 10-K/10-Q text with risk sentences highlighted and AI-explained. |
| **Education Hub** | Plain-English guide to SEC filings, LM signals, red flags, and the full methodology. |
| **Prediction Chart** | Direction calls (▲/▼) overlaid on actual price chart with rolling 30-day accuracy and confidence calibration. |

---

## Backtesting Results

3,000 predictions on held-out data (Feb 2024 → Mar 2026):

| Ticker | Predictions | Accuracy | Avg Confidence |
|--------|-------------|----------|----------------|
| KO | 500 | 48.4% | 69.6% |
| JNJ | 500 | **55.5%** | 55.1% |
| PG | 500 | 52.8% | 54.0% |
| WMT | 500 | 47.8% | 52.8% |
| AAPL | 500 | **55.2%** | 55.9% |
| GOOGL | 500 | **55.0%** | 53.1% |
| **Overall** | **3,000** | **52.5%** | — |

**Confidence calibration:** predictions in the 0.55–0.60 confidence bucket achieve **54.9% accuracy** vs 51.1% in the 0.50–0.55 bucket. The model knows when it's more confident — and that confidence is statistically meaningful.

---

## Anomaly Detection Results

425 SEC filings analyzed across 6 tickers (1994–2026):

| Ticker | Filings | Flagged | Flag Rate | HIGH Risk | ELEVATED |
|--------|---------|---------|-----------|-----------|----------|
| KO | 63 | 22 | 34.9% | 2 | 6 |
| JNJ | 100 | 43 | 43.0% | 4 | 12 |
| PG | 64 | 29 | 45.3% | 2 | 14 |
| WMT | 72 | 27 | 37.5% | 3 | 10 |
| AAPL | 115 | 45 | 39.1% | 6 | 15 |
| GOOGL | 11 | 3 | 27.3% | 0 | 2 |

**Methodology:** Loughran-McDonald financial dictionary. Each filing compared against a rolling 8-filing (2-year) baseline for that specific company. Threshold: >1.5σ deviation triggers a flag. Signals monitored: Negative Language, Uncertainty, Litigation Count, Sentiment Score, Positive Language.

---

## Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                          FRONTEND                               │
│   React 18 + Vite  ·  IBM Plex Mono  ·  Terminal Aesthetic      │
│                                                                 │
│   /              Landing page + live stats                      │
│   /dashboard     Predictions, charts, signals, explanation      │
│   /hypothesis    6-agent AI research pipeline                   │
│   /backtest      Direction calls overlaid on price chart        │
│   /timeline      SEC sentiment timeline + anomaly markers       │
│   /filings       Live EDGAR filing viewer + risk highlighting   │
│   /learn         Education hub — filing types, LM signals       │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP / SSE
┌──────────────────────────────▼──────────────────────────────────┐
│                          BACKEND                                │
│                    FastAPI · uvicorn · Railway                   │
│                                                                 │
│  /predict          /price-history     /sentiment-history        │
│  /explain          /model-info        /hypothesis/stream        │
│  /anomaly-history  /evidence-cases    /prediction-history       │
│  /filing-list      /filing-viewer     /explain-sentence         │
│  /subscribe        /subscribers                                 │
│                                                                 │
│  ┌──────────────────┐   ┌────────────────────────────────────┐  │
│  │  ML Inference    │   │   6-Agent Hypothesis Pipeline      │  │
│  │  6 Transformer   │   │   Parser → Market → Evidence →     │  │
│  │  .pt checkpoints │   │   Bear → Bull → Synthesizer        │  │
│  └────────┬─────────┘   └──────────────────┬─────────────────┘  │
│           │                                │                    │
│  ┌────────▼────────────────────────────────▼─────────────────┐  │
│  │   Feature Engineer · 56 features · yfinance · LM Sentiment│  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  APScheduler · Telegram Bot · Supabase PostgreSQL         │  │
│  │  Morning/Evening/Weekly jobs · Signal watchers            │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                        DATA PIPELINE                            │
│                                                                 │
│   fetch_stock_data.py     →  OHLCV via yfinance                 │
│   fetch_sec_filings.py    →  SEC EDGAR (10-K, 10-Q, 8-K)        │
│   lm_sentiment.py         →  LM dictionary scoring              │
│   merge_datasets.py       →  56-feature merged CSV              │
│   training.ipynb          →  TimeSeriesSplit CV · .pt save      │
│   backtest.py             →  3,000 predictions → Supabase       │
│   anomaly_detector.py     →  425 filings → anomaly_results.csv  │
│   evidence_builder.py     →  76 cases → evidence_cases.csv      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Model Architecture
```
Input:   60-day sequence × 56 features per day
         └─ Price (daily return, lags, MAs, Bollinger, RSI, momentum, volatility, volume)
         └─ Calendar (day of week, month, quarter)
         └─ Regime (MA200 binary, vol regime, RSI oversold/overbought)
         └─ LM Sentiment (positive, negative, uncertain, litigious, constraining)
         └─ Sentiment derived (MA5/20, delta, z-score, lags, interaction terms)
         └─ Return lags (1/2/3/5 day)

Model:   Transformer Encoder
         d_model=128 · heads=4 · layers=3
         dropout=0.3 · norm_first=True (pre-norm)
         Classifier: Linear(128→64) → GELU → Dropout → Linear(64→2)

Output:  Binary (UP/DOWN) + softmax confidence score
```

One model per ticker. Six independent checkpoints (~2.45MB each, CPU-only).

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite, react-router-dom, axios |
| Backend | FastAPI, uvicorn, APScheduler |
| ML | PyTorch 2.6 (CPU), TimeSeriesSplit CV |
| Sentiment | Loughran-McDonald Dictionary (NOT FinBERT) |
| Database | Supabase PostgreSQL (psycopg2 direct connection) |
| Auth | Supabase JWT ES256 |
| LLM | Groq llama-3.3-70b-versatile |
| Search | Tavily API |
| Filing Data | SEC EDGAR API (live) |
| Alerts | Telegram Bot API |
| Deployment | Railway (backend) + Vercel (frontend) |
| Styling | Inline CSS, IBM Plex Mono, #080808 bg, #f59e0b gold |

---

## Installation

### Prerequisites

- Python 3.12+
- Node.js 18+
- Supabase project (free tier works)
- API keys: Groq, Tavily, Telegram Bot Token

### 1. Clone
```bash
git clone https://github.com/furyfist/TradeSenpaii.git
cd TradeSenpai
```

### 2. Python Environment
```bash
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate        # macOS/Linux

pip install -r requirements.txt
```

> CPU-only PyTorch. Do not install the CUDA build — Railway's 4GB image limit requires the CPU wheel.

### 3. Frontend
```bash
cd app/frontend
npm install
```

### 4. Environment Variables

`app/backend/.env`:
```env
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile
TAVILY_API_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_JWT_SECRET=
SUPABASE_DB_URL=postgresql://postgres.PROJECTREF:PASSWORD@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres
ADMIN_PASSWORD=
BOT_LISTENER_ENABLED=false
```

`app/frontend/.env`:
```env
VITE_API_URL=http://localhost:8000
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
```

### 5. Supabase Schema
```sql
CREATE TABLE prediction_history (
    id SERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,
    predicted_date DATE NOT NULL,
    prediction TEXT NOT NULL,
    confidence REAL NOT NULL,
    actual_direction TEXT,
    actual_return REAL,
    correct INTEGER,
    logged_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(ticker, predicted_date)
);

CREATE TABLE subscribers (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    telegram_id TEXT,
    status TEXT DEFAULT 'pending',
    requested_at TIMESTAMPTZ DEFAULT NOW(),
    approved_at TIMESTAMPTZ
);
```

### 6. Run Backtest + Anomaly Detection
```bash
# Populate prediction_history in Supabase
python backtest.py --days 500

# Generate anomaly_results.csv and evidence_cases.csv
python anomaly_detector.py --export
python evidence_builder.py --export
```

### 7. Run
```bash
# Backend
cd app/backend
uvicorn main:app --reload --port 8000

# Frontend (separate terminal)
cd app/frontend
npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

---

## Routes

| Route | Description |
|-------|-------------|
| `/` | Landing page |
| `/dashboard` | Live predictions, price chart, signals, AI explanation |
| `/hypothesis` | 6-agent market hypothesis research pipeline |
| `/backtest` | Direction calls overlaid on price, rolling accuracy |
| `/timeline` | SEC sentiment timeline, anomaly markers, evidence cases |
| `/filings` | Live EDGAR filing viewer with risk highlighting |
| `/learn` | Education hub — filing types, LM signals, methodology |
| `/ts-ops-7x9k` | Admin panel (JWT protected) |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Status, version, tickers |
| GET | `/predict` | Next-day UP/DOWN + confidence |
| GET | `/price-history` | 90-day OHLCV |
| GET | `/sentiment-history` | LM scores per filing |
| GET | `/model-info` | CV accuracy, features, architecture |
| GET | `/explain` | Groq LLM explanation |
| POST | `/hypothesis/stream` | SSE 6-agent pipeline |
| GET | `/prediction-history` | Backtested predictions from Supabase |
| GET | `/anomaly-history` | Filing anomaly data |
| GET | `/evidence-cases` | Top hero cases from evidence_cases.csv |
| GET | `/filing-list` | Recent 10-K/10-Q list per ticker |
| GET | `/filing-viewer` | Highlighted filing text from EDGAR |
| POST | `/explain-sentence` | Plain English filing sentence explanation |
| POST | `/subscribe` | Telegram subscription request |
| GET | `/subscribers` | List subscribers (admin) |

---

## Design Principles

**1. Domain-specific beats general-purpose.**
The Loughran-McDonald dictionary outperforms FinBERT on SEC filings. A 2,700-word lexicon built for financial regulatory documents beats a 110M-parameter neural network when the domain is right.

**2. Honest accuracy over inflated accuracy.**
52.5% backtested accuracy is displayed openly. Chasing higher numbers requires overfitting or data leakage — both make the tool less trustworthy.

**3. Anomaly detection over prediction.**
The most defensible claim isn't "we predict direction." It's "we detect when a company's language changes structurally." JNJ's 92.55σ litigation spike in 2008 is not a prediction — it's a fact, verifiable in the public record.

**4. Per-ticker models over shared models.**
A shared model must learn six different volatility regimes simultaneously. Separate models are simpler, more accurate, and independently debuggable.

**5. Silent failures are the hardest bugs.**
Every significant bug in this project produced no error. Logging at key pipeline stages is the primary defense.

---

## Known Limitations

- **52.5% accuracy** — honest ceiling for short-term direction on public data. Academic ceiling is ~55–56%.
- **Forward-filled sentiment** — LM scores are static between filing dates. Intra-quarter sentiment doesn't change.
- **GOOGL has only 11 qualifying filings** — too few for reliable anomaly detection baselines.
- **EDGAR can be slow** — government servers. Filing viewer requests take 5–15 seconds.
- **Desktop-only UI** — not optimized for mobile.
- **No earnings calendar feature** — binary earnings-within-7-days flag not yet added to model.

---

## Project Structure
```
TradeSenpai/
├── app/
│   ├── backend/
│   │   ├── main.py                  FastAPI app, all endpoints
│   │   ├── predictor.py             Model loading + inference
│   │   ├── feature_engineer.py      56-feature live pipeline
│   │   ├── edgar_fetcher.py         EDGAR API + filing text extraction
│   │   ├── anomaly_detector.py      (run from root) Filing anomaly detection
│   │   ├── model/                   6 × .pt checkpoints
│   │   └── alerts/
│   │       ├── alert_store.py       Supabase DB operations
│   │       ├── scheduler.py         APScheduler jobs
│   │       └── telegram_bot.py      Alert delivery
│   └── frontend/
│       └── src/
│           └── components/
│               ├── Dashboard.jsx
│               ├── HypothesisPage.jsx
│               ├── RiskTimeline.jsx
│               ├── FilingViewer.jsx
│               ├── PredictionChart.jsx
│               └── LearnPage.jsx
├── stock-analysis/
│   └── data/processed/              merged_dataset.csv per ticker
├── backtest.py                      Run backtesting engine
├── anomaly_detector.py              Run anomaly detection
├── evidence_builder.py              Run evidence case builder
├── anomaly_results.csv              Generated output
└── evidence_cases.csv               Generated output
```

---

## Version History

| Version | Date | Summary |
|---------|------|---------|
| V1 | 2024 | Single-ticker proof of concept |
| V2 | Late 2024 | Multi-ticker, LM sentiment, feature engineering |
| V3 | Early 2025 | 6-agent hypothesis engine, Telegram alerts |
| V4 | Late 2025 | Supabase migration, JWT auth, rate limiting |
| **V5** | **Mar 2026** | **Backtesting engine, SEC anomaly detection, risk timeline, filing viewer, education hub** |

---

## License

MIT — see [LICENSE](LICENSE)

---

*TradeSenpai V5 — March 2026*
*From prediction platform to SEC filing risk intelligence.*

