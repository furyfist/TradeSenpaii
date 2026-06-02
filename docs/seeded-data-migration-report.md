# Seeded Data Migration — TradeSenpai

## Overview

Migrated the backend from live inference (PyTorch + yfinance) to pre-computed seeded predictions served from Supabase. This reduced Railway memory from ~700 MB to ~150 MB, cutting the monthly hosting bill by ~75–80%.

---

## Problem

Railway was billing ~$5.64/month for memory because the server was:
- Loading 6 PyTorch Transformer models (~400 MB RAM just for torch)
- Calling yfinance on every `/predict` and `/price-history` request
- Running APScheduler + Telegram bot as background threads 24/7

---

## What Changed

### Prediction flow (before → after)

```
BEFORE:
Request → yfinance (live prices) → engineer_features() → torch model → response

AFTER:
Request → Supabase seeded_predictions table → response (50ms)
```

### Files added
- `scripts/create_seeded_table.sql` — run once in Supabase SQL editor to create the table
- `scripts/seed_predictions.py` — run locally after retraining to upsert predictions into DB
- `app/backend/prediction_reader.py` — reads pre-computed predictions from Supabase, no torch

### Files changed
- `app/backend/main.py` — removed torch preload, scheduler, bot thread from startup; updated `/predict`, `/model-info`, `/explain` to use `prediction_reader`; simplified lifespan to single print
- `app/backend/feature_engineer.py` — replaced yfinance calls with `merged_dataset.csv` reads; `BASE_PATH` resolves dynamically to work both locally and on Railway
- `app/backend/sentiment_loader.py` — same dynamic `BASE_PATH` fix
- `app/backend/hypothesis/hypothesis_parser.py` — replaced yfinance price fetch and return std with CSV reads
- `app/backend/hypothesis/market_collector.py` — replaced yfinance 52w range + current price with CSV reads
- `app/backend/alerts/alert_store.py` — fixed `get_db_connection` to use `SUPABASE_POOLER_URL` fallback
- `app/backend/edgar_fetcher.py` — fixed filing viewer to use EDGAR index API to resolve primary document name instead of guessing filenames
- `app/backend/requirements.txt` — removed: `torch`, `yfinance`, `APScheduler`, `python-telegram-bot`, `multitasking`, `curl_cffi`

### Files decommissioned (kept, not deleted)
Each has a `# DECOMMISSIONED:` comment at the top explaining why.
- `app/backend/predictor.py` — torch inference, replaced by `prediction_reader.py`
- `app/backend/alerts/scheduler.py` — APScheduler jobs, removed from server
- `app/backend/alerts/bot_listener.py` — Telegram bot polling thread
- `app/backend/alerts/telegram_bot.py` — Telegram message sender
- `app/backend/alerts/watcher.py` — direction flip / sentiment spike checker
- `app/backend/alerts/digest.py` — Telegram message formatter

### Files still active and unchanged
- `app/backend/alerts/alert_store.py` — used by `/prediction-history` and `/subscribe`
- `app/backend/model/*.pt` — kept in repo, used locally by seed script only

---

## Supabase Table

```sql
CREATE TABLE IF NOT EXISTS seeded_predictions (
    ticker          TEXT PRIMARY KEY,
    name            TEXT,
    prediction      TEXT,
    confidence      FLOAT,
    predicted_date  TEXT,
    as_of_date      TEXT,
    top_signals     JSONB,
    sentiment_score FLOAT,
    sentiment_label TEXT,
    model_accuracy  FLOAT,
    sector          TEXT,
    input_features  INT,
    sequence_len    INT,
    model_type      TEXT,
    trained_on      TEXT,
    cv_accuracy     FLOAT
);
```

Seeded with predictions as of **Feb 20, 2026** (last training cutoff).

---

## Railway Deployment Config

| Setting | Value |
|---|---|
| Source repo | furyfist/TradeSenpaii |
| Branch | main |
| Root Directory | *(blank — full repo deployed)* |
| Start Command | `cd app/backend && uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Build Command | *(blank — Railpack auto-detects Python)* |

### Required env vars in Railway
```
SUPABASE_DB_URL
SUPABASE_POOLER_URL
GROQ_API_KEY
GROQ_MODEL
GROQ_SEARCH_MODEL
TAVILY_API_KEY
ADMIN_PASSWORD
```

---

## Results

| Metric | Before | After |
|---|---|---|
| Process RAM | ~700 MB | ~150 MB |
| Monthly cost | ~$5.64 | ~$1.00–1.20 |
| Startup time | ~15s (model preload) | ~1s |
| `/predict` latency | ~2–4s | ~50ms |
| Predictions freshness | Live | Frozen at Feb 20, 2026 |
| Telegram alerts | Yes | Removed from server |

---

## Routes Status (post-migration)

| Route | Status | Source |
|---|---|---|
| `GET /predict` | Working | Supabase `seeded_predictions` |
| `GET /price-history` | Working | `merged_dataset.csv` |
| `GET /sentiment-history` | Working | `sec_sentiment_features.csv` |
| `GET /model-info` | Working | Supabase `seeded_predictions` |
| `GET /explain` | Working | Groq LLM + CSV features |
| `POST /hypothesis` | Working | Groq LLM + CSV data |
| `POST /hypothesis/stream` | Working | Groq LLM + CSV data |
| `GET /anomaly-history` | Working | `anomaly_results.csv` |
| `GET /evidence-cases` | Working | `evidence_cases.csv` |
| `GET /filing-list` | Working | EDGAR API |
| `GET /filing-viewer` | Working | EDGAR API (index-first lookup) |
| `GET /prediction-history` | Working | Supabase `prediction_history` |
| `GET /tickers` | Working | Hardcoded |
| Telegram alerts | Removed | — |

---

## How to Re-seed Predictions (when you retrain)

1. Run locally from project root:
   ```
   python scripts/seed_predictions.py
   ```
2. Verify all 6 tickers show as upserted in the output
3. No redeploy needed — server reads from DB on every request

---

## Next Time You Continue

- Predictions are frozen at Feb 20, 2026 — if you retrain models, run the seed script again
- Telegram alerts are fully removed from the server — the code is kept in `alerts/` for reference if you want to revive them as a standalone service later
- The `feat/deploy-seeded-data` branch was merged into `main` after this work
