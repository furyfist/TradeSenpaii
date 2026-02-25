from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import pandas as pd
from contextlib import asynccontextmanager

from models import (
    PredictionResponse, PriceHistoryResponse,
    SentimentHistoryResponse, ModelInfoResponse,
    PricePoint, SentimentPoint, SUPPORTED_TICKERS
)
from predictor import Predictor
from feature_engineer import get_latest_feature_row, fetch_recent_prices
from sentiment_loader import load_sentiment_history, load_latest_sentiment


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Preload all models on startup so first request is fast
    print("[STARTUP] Preloading all ticker models...")
    for ticker in SUPPORTED_TICKERS:
        try:
            predictor._load_model(ticker)
            print(f"[STARTUP] {ticker} model ready")
        except Exception as e:
            print(f"[STARTUP] Could not load {ticker}: {e}")
    yield

app = FastAPI(title="TradeSenpai API v2", version="2.0.0", lifespan=lifespan)

predictor = Predictor()

# Cache per ticker
_cache: dict = {}
CACHE_TTL_MINUTES = 30

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TICKER_NAMES = {
    "KO":    "Coca-Cola",
    "JNJ":   "Johnson & Johnson",
    "PG":    "Procter & Gamble",
    "WMT":   "Walmart",
    "AAPL":  "Apple",
    "GOOGL": "Alphabet",
}


def validate_ticker(ticker: str) -> str:
    ticker = ticker.upper()
    if ticker not in SUPPORTED_TICKERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported ticker '{ticker}'. Supported: {SUPPORTED_TICKERS}"
        )
    return ticker


@app.get("/health")
def health():
    return {
        "status":   "ok",
        "version":  "2.0.0",
        "tickers":  SUPPORTED_TICKERS,
        "timestamp": str(datetime.now())
    }


@app.get("/predict", response_model=PredictionResponse)
def predict(ticker: str = Query(default="KO")):
    ticker = validate_ticker(ticker)
    try:
        now = datetime.now()
        if (
            ticker in _cache and
            _cache[ticker].get("timestamp") and
            (now - _cache[ticker]["timestamp"]).seconds < CACHE_TTL_MINUTES * 60
        ):
            print(f"[INFO] Returning cached prediction for {ticker}")
            return _cache[ticker]["prediction"]

        feature_df, price_df = get_latest_feature_row(ticker)
        print(f"[DEBUG] feature_df shape in main: {feature_df.shape}")
        result    = predictor.predict(ticker, feature_df)
        sentiment = load_latest_sentiment(ticker)

        last_date = pd.to_datetime(price_df["date"].iloc[-1])
        next_day  = last_date + timedelta(days=1)

        response = PredictionResponse(
            ticker          = ticker,
            name            = TICKER_NAMES.get(ticker, ticker),
            prediction      = result["prediction"],
            confidence      = result["confidence"],
            predicted_date  = str(next_day.date()),
            as_of_date      = str(last_date.date()),
            top_signals     = result["top_signals"],
            sentiment_score = sentiment["lm_sentiment_score"],
            sentiment_label = "Positive" if sentiment["lm_sentiment_score"] > 0.5
                              else ("Negative" if sentiment["lm_sentiment_score"] < -0.5
                              else "Neutral"),
            model_accuracy  = result["cv_accuracy"],
        )

        _cache[ticker] = {"prediction": response, "timestamp": now}
        return response

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/price-history", response_model=PriceHistoryResponse)
def price_history(ticker: str = Query(default="KO")):
    ticker = validate_ticker(ticker)
    try:
        df = fetch_recent_prices(ticker, days=100)
        df = df.tail(90)
        return PriceHistoryResponse(
            ticker=ticker,
            data=[
                PricePoint(
                    date   = str(row["date"].date()),
                    open   = round(float(row["open"]),   2),
                    high   = round(float(row["high"]),   2),
                    low    = round(float(row["low"]),    2),
                    close  = round(float(row["close"]),  2),
                    volume = round(float(row["volume"]), 0),
                )
                for _, row in df.iterrows()
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sentiment-history", response_model=SentimentHistoryResponse)
def sentiment_history(ticker: str = Query(default="KO")):
    ticker = validate_ticker(ticker)
    try:
        data = load_sentiment_history(ticker, n=50)
        return SentimentHistoryResponse(
            ticker=ticker,
            data=[SentimentPoint(**d) for d in data]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/model-info", response_model=ModelInfoResponse)
def model_info(ticker: str = Query(default="KO")):
    ticker = validate_ticker(ticker)
    try:
        info = predictor.get_model_info(ticker)
        return ModelInfoResponse(**info)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tickers")
def get_tickers():
    return {
        "tickers": [
            {
                "ticker": t,
                "name":   TICKER_NAMES[t],
            }
            for t in SUPPORTED_TICKERS
        ]
    }