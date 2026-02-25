
# TradeSenpai
**AI-Powered Stock Research Tool**

**Version 2.0 – Multi-Ticker + Agentic Explanations**  
February 2026

## Overview

TradeSenpai is an AI-powered stock research tool that combines historical price pattern analysis with sentiment from SEC regulatory filings (8-K, 10-Q, 10-K) to generate next-day directional predictions (UP/DOWN) and **explainable research summaries** for retail investors.

It automates the institutional analyst workflow: downloading SEC filings, extracting financial sentiment using the **Loughran-McDonald** dictionary, engineering technical indicators, and synthesizing insights with historical analogies + LLM explanations.

**Key upgrade in V2**: Expanded from single-ticker (KO) to **six diversified tickers** (KO, JNJ, PG, WMT, AAPL, GOOGL) spanning consumer staples, healthcare, retail, and technology. Added an **agentic explanation layer** using cosine-similarity historical search + Groq/Llama 3.1 synthesis for plain-English narratives, key drivers, risks, and precedents.

This is **not** a trading system or price predictor — it's an educational simulation tool that surfaces rarely-seen signals (sentiment shifts, technical patterns, historical context). Models achieve **51.9–53.5%** cross-validation accuracy on next-day direction — honest and realistic given market noise (academic short-term prediction ceiling ~55–56%).

The real value lies in the **signal aggregation**, **sentiment history**, **historical analogies**, and **AI-generated explanations**.

## Features

- **Next-Day Directional Prediction** — Binary (UP/DOWN) with confidence score & tier (Low/Moderate/Strong/High Conviction)
- **AI Explanation Panel** — Groq LLM synthesizes: headline, explanation, key driver, main risk, historical note
- **Historical Similarity Search** — Top 3 most similar past trading days (cosine similarity on 38 features, ≥365 days old)
- **Signal Breakdown** — Key drivers (RSI, MAs, volatility, LM sentiment, etc.) with color-coded states
- **Real-Time Multi-Ticker Support** — Switch between 6 tickers; fetches live prices via yfinance
- **Dashboard Visualizations**:
  - 90-day price chart (Recharts)
  - Sentiment history line chart
  - Prediction card + confidence tier
  - Expandable AI explanation with analogy cards (outcome, return %, similarity %, top signals)
- **Feature Set** — ~56 features: price (lags, MAs, Bollinger, RSI, momentum), calendar, LM sentiment (pos/neg/uncertain/litigious/constraining + derived), interactions
- **Data Sources**:
  - Historical & live OHLCV from Yahoo Finance
  - SEC EDGAR filings (1993/1994–present) via sec-edgar-downloader

## Prerequisites

- Python 3.10+
- Node.js 18+ and npm (for frontend)
- Libraries: See `requirements.txt` (yfinance, sec-edgar-downloader, pandas, torch, fastapi, etc.) and `frontend/package.json`
- Groq API key (free tier) for explanations — set as `GROQ_API_KEY` env var
- Kaggle account (optional, for GPU training)

## Installation

1. Clone the Repository

   ```bash
   git clone https://github.com/yourusername/TradeSenpai.git
   cd TradeSenpai
   ```

2. Python Environment

   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Frontend Setup

   ```bash
   cd frontend
   npm install
   ```

4. Set Environment Variables

   Create `.env` in root or backend:

   ```
   GROQ_API_KEY=your_groq_key_here
   ```

5. Download & Process Data (per ticker)

   ```bash
   # Example for one ticker
   python stock-analysis/scripts/fetch_stock_data.py --ticker KO
   python stock-analysis/scripts/fetch_sec_filings.py --ticker KO
   python stock-analysis/scripts/preprocess_filings.py --ticker KO
   python stock-analysis/scripts/lm_sentiment.py --ticker KO
   python stock-analysis/scripts/merge_datasets.py --ticker KO
   ```

   Repeat for JNJ, PG, WMT, AAPL, GOOGL (or script all via config).

6. Train Models (optional — pre-trained in `models/`)

   Run the Kaggle notebook (`training.ipynb`) — uses TimeSeriesSplit CV, saves one `.pt` per ticker.

## Usage

1. Run Backend (FastAPI)

   ```bash
   cd backend
   uvicorn main:app --reload --port 8000
   ```

   Key endpoints:
   - `/health`
   - `/predict?ticker=KO`
   - `/price-history?ticker=KO`
   - `/sentiment-history?ticker=KO`
   - `/explain?ticker=KO` (AI explanation)
   - `/model-info?ticker=KO`

2. Run Frontend (React/Vite)

   ```bash
   cd frontend
   npm run dev
   ```

   Open http://localhost:5173  
   Select ticker → view prediction, charts, signals → expand AI Explanation.

## System Architecture

- **Data Pipeline** — Parameterized scripts using `config.py` (CIKs, paths, metadata)
- **Models** — 6 separate Transformers (d_model=128, 4 heads, 3 layers, 60-day lookback)
- **Backend** — FastAPI with per-ticker routing, caching, yfinance + torch inference
- **Frontend** — React/Vite + Recharts; ticker selector, lazy-loaded explanation panel
- **Explanation Layer** — Cosine similarity (numpy) + Groq Llama 3.1 8B (JSON-structured output)

## V2 Training Results

Cross-validation accuracy (no leakage):
- KO: 52.29% ± 0.0067
- JNJ: 51.97% ± 0.0110
- PG: 51.92% ± 0.0131
- WMT: 53.33% ± 0.0147
- AAPL: 52.40% ± 0.0076
- GOOGL: 53.48% ± 0.0122

All beat majority baseline; best in defensive & tech sectors.

## Known Limitations

- ~52% accuracy ceiling — honest for next-day direction
- Forward-filled sentiment between filings
- No earnings calendar / macro features (VIX, SPX, rates)
- yfinance dependency (no SLA, occasional gaps)
- Local-only deployment
- No live prediction logging / real-world tracking
- Desktop-focused UI (not mobile-responsive)

## Technical Debt & Future Ideas

- Inline CSS → migrate to Tailwind / styled-components
- No tests → add pytest + vitest
- Hardcoded paths → use pathlib + env vars fully
- Partial LM dictionary → use full 86k+ version
- Add earnings flag, macro features, 5-day target
- Optional: PostgreSQL logging, cloud deploy

## Lessons from V1 → V2

- One `config.py` prevents hundreds of bugs
- Domain tools (LM) > general neural models for filings
- Explanation layer > raw prediction in value
- Migrate & verify baseline before expanding scope
- Cosine similarity on features gives surprisingly good historical analogies

Contributions welcome — focus on debt reduction, new tickers, or macro features.

**License**  
MIT — see LICENSE

**Version 2.0 — February 2026**  
From single-ticker foundation to multi-ticker explainable research tool.