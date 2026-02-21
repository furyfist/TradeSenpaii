from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import pandas as pd
import traceback

from models import (
    PredictionResponse, PriceHistoryResponse,
    SentimentHistoryResponse, ModelInfoResponse,
    PricePoint, SentimentPoint
)
from predictor import Predictor
from feature_engineer import get_latest_feature_row, fetch_recent_prices
from sentiment_loader import load_sentiment_history, load_latest_sentiment

# ── Init ──
app       = FastAPI(title="TradeSenpai API", version="1.0.0")
predictor = Predictor()

# ── CORS — allow React dev server ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ROUTES
@app.get("/health")
def health():
    return {"status": "ok", "timestamp": str(datetime.now())}

# Simple in-memory cache
_cache = {"prediction": None, "timestamp": None}
CACHE_TTL_MINUTES = 30

@app.get("/predict", response_model=PredictionResponse)
def predict():
    try:
        # Return cached result if fresh
        now = datetime.now()
        if (
            _cache["prediction"] is not None and
            _cache["timestamp"] is not/ None and
            (now - _cache["timestamp"]).seconds < CACHE_TTL_MINUTES * 60
        ):
            print("[INFO] Returning cached prediction")
            return _cache["prediction"]

        feature_df, price_df = get_latest_feature_row("KO")
        result    = predictor.predict(feature_df)
        sentiment = load_latest_sentiment()

        last_date = pd.to_datetime(price_df["date"].iloc[-1])
        next_day  = last_date + timedelta(days=1)

        response = PredictionResponse(
            ticker          = "KO",
            prediction      = result["prediction"],
            confidence      = result["confidence"],
            predicted_date  = str(next_day.date()),
            as_of_date      = str(last_date.date()),
            top_signals     = result["top_signals"],
            sentiment_score = sentiment["lm_sentiment_score"],
            sentiment_label = "Positive" if sentiment["lm_sentiment_score"] > 0.5
                              else ("Negative" if sentiment["lm_sentiment_score"] < -0.5
                              else "Neutral"),
            model_accuracy  = predictor.cv_accuracy,
        )

        # Store in cache
        _cache["prediction"] = response
        _cache["timestamp"]  = now

        return response

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/price-history", response_model=PriceHistoryResponse)
def price_history():
    try:
        df = fetch_recent_prices("KO", days=100)
        df = df.tail(90)
        return PriceHistoryResponse(
            ticker="KO",
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
def sentiment_history():
    try:
        data = load_sentiment_history(n=50)
        return SentimentHistoryResponse(
            ticker="KO",
            data=[SentimentPoint(**d) for d in data]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/model-info", response_model=ModelInfoResponse)
def model_info():
    return ModelInfoResponse(
        ticker         = "KO",
        cv_accuracy    = predictor.cv_accuracy,
        trained_on     = predictor.trained_on,
        input_features = len(predictor.feature_cols),
        sequence_len   = predictor.sequence_len,
        model_type     = "Transformer (d_model=128, 3 layers, 4 heads)",
        last_updated   = predictor.trained_on,
    )