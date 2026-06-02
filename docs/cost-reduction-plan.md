# Cost Reduction Plan — Drop Torch, Cut Bot, Use Seeded Data

**Goal:** Reduce Railway memory from ~700 MB to ~150 MB (~75–80% bill reduction).  
**Approach:** Pre-compute all predictions + signals offline → store in Postgres (Supabase) → serve from DB. Remove PyTorch, yfinance, APScheduler, and Telegram bot from the server entirely.

---

## What changes and what stays the same

| Route | Before | After |
|---|---|---|
| `GET /predict` | Calls yfinance → runs torch model | Reads pre-computed row from DB |
| `GET /price-history` | Calls yfinance | Reads from `merged_dataset.csv` |
| `GET /sentiment-history` | Reads CSV ✓ | No change |
| `GET /model-info` | Reads cached model state | Reads pre-computed row from DB |
| `GET /explain` | Calls Groq LLM ✓ | No change — but feature data comes from CSV not yfinance |
| `POST /hypothesis` | Calls Groq LLM ✓ | No change |
| `POST /hypothesis/stream` | Calls Groq LLM ✓ | No change |
| `GET /anomaly-history` | Reads CSV ✓ | No change |
| `GET /evidence-cases` | Reads CSV ✓ | No change |
| `GET /filing-list` | Calls EDGAR API ✓ | No change |
| `GET /filing-viewer` | Calls EDGAR API ✓ | No change |
| `GET /prediction-history` | Reads from DB ✓ | No change |
| Telegram bot + scheduler | Runs in background threads | **Removed entirely** |

---

## Step 1 — Create the `seeded_predictions` table in Supabase

Run this SQL in the Supabase SQL editor once:

```sql
CREATE TABLE seeded_predictions (
    ticker          TEXT PRIMARY KEY,
    name            TEXT,
    prediction      TEXT,         -- "UP" or "DOWN"
    confidence      FLOAT,
    predicted_date  TEXT,         -- "2026-02-21"
    as_of_date      TEXT,         -- "2026-02-20"
    top_signals     JSONB,        -- same shape as PredictionResponse.top_signals
    sentiment_score FLOAT,
    sentiment_label TEXT,
    model_accuracy  FLOAT,
    -- model-info fields (replaces /model-info torch call too)
    sector          TEXT,
    input_features  INT,
    sequence_len    INT,
    model_type      TEXT,
    trained_on      TEXT,
    cv_accuracy     FLOAT
);
```

---

## Step 2 — Write a local seed script

Create `scripts/seed_predictions.py` at the project root. This runs **locally on your machine**, never on the server.

It does:
1. Loads each `.pt` model (torch stays on your machine only)
2. Reads `merged_dataset.csv` for each ticker (last rows as feature input)
3. Runs `predictor.predict()` and `load_latest_sentiment()`
4. Upserts one row per ticker into `seeded_predictions` via psycopg2

Run this once now, and again whenever you retrain models.

**Inputs it needs locally:**
- `app/backend/model/transformer_*.pt`
- `stock-analysis/data/processed/<TICKER>/merged_dataset.csv`
- `stock-analysis/data/processed/<TICKER>/sec_sentiment_features.csv`
- Your Supabase `DATABASE_URL` in `.env`

---

## Step 3 — Rewrite `predictor.py` → `prediction_reader.py`

Replace the `Predictor` class (which imports torch) with a simple DB reader:

```python
# app/backend/prediction_reader.py
import psycopg2, os, json

def get_prediction(ticker: str) -> dict:
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur  = conn.cursor()
    cur.execute("SELECT * FROM seeded_predictions WHERE ticker = %s", (ticker,))
    row = cur.fetchone()
    cur.close(); conn.close()
    if not row:
        raise ValueError(f"No seeded prediction for {ticker}")
    cols = [d[0] for d in cur.description]  # use before close in real code
    return dict(zip(cols, row))
```

No torch import anywhere in this file.

---

## Step 4 — Rewrite `feature_engineer.py` to read from CSV

Replace `fetch_recent_prices()` (yfinance call) with a CSV reader:

```python
def fetch_recent_prices(ticker: str, days: int = 100) -> pd.DataFrame:
    csv_path = BASE_PATH / ticker / "merged_dataset.csv"
    df = pd.read_csv(csv_path, usecols=["date","open","high","low","close","volume"])
    df["date"] = pd.to_datetime(df["date"])
    return df.tail(days).reset_index(drop=True)
```

Replace `get_latest_feature_row()` similarly — read the last `sequence_len` rows from `merged_dataset.csv` directly, since all features are already computed there. No need to call `engineer_features()` at all.

```python
def get_latest_feature_row(ticker: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    csv_path = BASE_PATH / ticker / "merged_dataset.csv"
    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"])
    price_df = df[["date","open","high","low","close","volume"]].copy()
    return df, price_df
```

This is safe because `merged_dataset.csv` already has every engineered feature column — it's the exact same file the model was trained on.

---

## Step 5 — Update `main.py`

**Remove these imports entirely:**
```python
# DELETE these lines:
from predictor import Predictor
from feature_engineer import get_latest_feature_row, fetch_recent_prices
from alerts.scheduler import create_scheduler
from alerts.bot_listener import create_bot_app
import threading
```

**Replace with:**
```python
from prediction_reader import get_prediction
from feature_engineer import fetch_recent_prices, get_latest_feature_row  # now CSV-only
```

**Simplify the lifespan function** — remove model preloading, scheduler start, and bot thread:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[STARTUP] TradeSenpai API ready (seeded mode)")
    yield
```

**Update `/predict` route** to read from DB instead of running inference:
```python
@app.get("/predict", response_model=PredictionResponse)
def predict(ticker: str = Query(default="KO")):
    ticker = validate_ticker(ticker)
    data = get_prediction(ticker)
    return PredictionResponse(
        ticker          = ticker,
        name            = data["name"],
        prediction      = data["prediction"],
        confidence      = data["confidence"],
        predicted_date  = data["predicted_date"],
        as_of_date      = data["as_of_date"],
        top_signals     = data["top_signals"],
        sentiment_score = data["sentiment_score"],
        sentiment_label = data["sentiment_label"],
        model_accuracy  = data["model_accuracy"],
    )
```

**Update `/model-info` route** to read from DB:
```python
@app.get("/model-info", response_model=ModelInfoResponse)
def model_info(ticker: str = Query(default="KO")):
    ticker = validate_ticker(ticker)
    data = get_prediction(ticker)
    return ModelInfoResponse(
        ticker         = ticker,
        name           = data["name"],
        sector         = data["sector"],
        cv_accuracy    = data["cv_accuracy"],
        trained_on     = data["trained_on"],
        input_features = data["input_features"],
        sequence_len   = data["sequence_len"],
        model_type     = data["model_type"],
        last_updated   = data["trained_on"],
    )
```

**Update `/price-history`** — already calls `fetch_recent_prices` which will now read from CSV. No route change needed.

**Update `/explain`** — calls `get_latest_feature_row` which will now read from CSV. No route change needed.

---

## Step 6 — Remove packages from `requirements.txt`

Remove these lines:
```
torch==2.6.0+cpu
yfinance==1.2.0
APScheduler==3.11.2
python-telegram-bot==22.6
multitasking==0.0.12
curl_cffi==0.13.0
```

Also remove the entire `app/backend/alerts/` folder — it's only used by the scheduler and bot, neither of which run on the server anymore.

> **Note:** Keep `scikit-learn`, `scipy`, `numpy`, `pandas` — they're still used by `feature_engineer.py` and `explainer.py`.

---

## Step 7 — Annotate decommissioned files

Do **not** delete any files. Instead, add a short comment block at the top of each file that no longer runs on the server, explaining what it did and why it was retired.

Files to annotate:
- `app/backend/predictor.py` — ran torch inference, replaced by `prediction_reader.py` to cut ~400 MB RAM
- `app/backend/alerts/scheduler.py` — ran APScheduler for morning/evening Telegram briefs, removed to cut background threads
- `app/backend/alerts/bot_listener.py` — ran Telegram bot polling loop in a background thread, removed with scheduler
- `app/backend/alerts/telegram_bot.py` — sent Telegram messages, only used by scheduler
- `app/backend/alerts/watcher.py` — checked for direction flips and sentiment spikes every 2 hours, only used by scheduler
- `app/backend/alerts/digest.py` — formatted Telegram message bodies, only used by scheduler

Files that are **unchanged and still active:**
- `app/backend/alerts/alert_store.py` — still used by `/prediction-history` and `/subscribe`
- `app/backend/model/*.pt` — kept in repo, only used locally by the seed script

---

## Expected result

| Metric | Before | After |
|---|---|---|
| Process RAM | ~700 MB | ~120–150 MB |
| Monthly cost (at your rate) | ~$5.64 | ~$1.00–1.20 |
| Startup time | ~15s (model preload) | ~1s |
| `/predict` latency | ~2–4s (yfinance + inference) | ~50ms (DB read) |
| Predictions freshness | Live (as of today) | Frozen at Feb 20, 2026 |
| Telegram alerts | Yes | No (removed) |

---

## Order of operations

1. Run seed script locally → verify all 6 tickers have rows in DB
2. Rewrite `feature_engineer.py` (CSV reads)
3. Write `prediction_reader.py`
4. Update `main.py` (remove imports, update routes, simplify lifespan)
5. Remove packages from `requirements.txt`
6. Deploy and verify all routes respond correctly
7. Delete dead code 
