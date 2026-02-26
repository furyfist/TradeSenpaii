from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import pandas as pd
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from explainer import explain_prediction
from alerts.scheduler import create_scheduler
from alerts.bot_listener import create_bot_app
import threading
from fastapi.responses import StreamingResponse
import json
import os
import secrets
load_dotenv()

from models import (
    PredictionResponse, PriceHistoryResponse,
    SentimentHistoryResponse, ModelInfoResponse,
    PricePoint, SentimentPoint, SUPPORTED_TICKERS,
    ExplanationResponse,HypothesisRequest, HypothesisResponse
)
from alerts.alert_store import (
    init_db, add_subscriber, get_all_subscribers,
    approve_subscriber, reject_subscriber
)

from predictor import Predictor
from feature_engineer import get_latest_feature_row, fetch_recent_prices
from sentiment_loader import load_sentiment_history, load_latest_sentiment
from hypothesis.hypothesis_parser import parse_hypothesis
from hypothesis.market_collector  import collect_market_context
from hypothesis.evidence_agent    import collect_historical_evidence
from hypothesis.bear_agent        import collect_bear_case
from hypothesis.bull_agent        import collect_bull_case
from hypothesis.synthesizer       import synthesize, TICKER_FULL_NAME

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Preload models
    print("[STARTUP] Preloading all ticker models...")
    for ticker in SUPPORTED_TICKERS:
        try:
            predictor._load_model(ticker)
            print(f"[STARTUP] {ticker} model ready")
        except Exception as e:
            print(f"[STARTUP] Could not load {ticker}: {e}")

    # Start alert scheduler
    scheduler = create_scheduler()
    scheduler.start()
    print("[STARTUP] Alert scheduler started")

    # Start bot listener in background thread
    def run_bot():
        import asyncio
        bot_app = create_bot_app()
        asyncio.run(bot_app.run_polling())

    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    print("[STARTUP] Bot listener started")

    yield

    scheduler.shutdown(wait=False)
    print("[SHUTDOWN] Scheduler stopped")

app = FastAPI(title="TradeSenpai API v2", version="2.0.0", lifespan=lifespan)

predictor = Predictor()

security = HTTPBasic()

def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    correct_password = os.getenv("ADMIN_PASSWORD", "")
    if not correct_password:
        raise HTTPException(status_code=500, detail="Admin password not configured.")
    is_correct = secrets.compare_digest(
        credentials.password.encode("utf8"),
        correct_password.encode("utf8"),
    )
    if not is_correct:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# Cache per ticker
_cache: dict = {}
CACHE_TTL_MINUTES = 30

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
    allow_credentials=True,
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

        # Log prediction to history (skip if cached — already logged)
        try:
            from alerts.alert_store import log_prediction
            log_prediction(
                ticker         = ticker,
                predicted_date = str(next_day.date()),
                prediction     = result["prediction"],
                confidence     = result["confidence"],
            )
        except Exception as e:
            print(f"[WARN] Could not log prediction for {ticker}: {e}")

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


@app.get("/explain", response_model=ExplanationResponse)
def explain(ticker: str = Query(default="KO")):
    ticker = validate_ticker(ticker)
    try:
        feature_df, price_df  = get_latest_feature_row(ticker)
        result                = predictor.predict(ticker, feature_df)
        sentiment             = load_latest_sentiment(ticker)
        current_features      = feature_df.iloc[-1]

        explanation = explain_prediction(
            ticker           = ticker,
            prediction       = result["prediction"],
            confidence       = result["confidence"],
            top_signals      = result["top_signals"],
            sentiment_score  = sentiment["lm_sentiment_score"],
            sentiment_label  = "Positive" if sentiment["lm_sentiment_score"] > 0.5
                               else ("Negative" if sentiment["lm_sentiment_score"] < -0.5
                               else "Neutral"),
            current_features = current_features,
        )

        return ExplanationResponse(
            ticker          = ticker,
            headline        = explanation["headline"],
            explanation     = explanation["explanation"],
            key_driver      = explanation["key_driver"],
            main_risk       = explanation["main_risk"],
            historical_note = explanation["historical_note"],
            confidence_tier = explanation["confidence_tier"],
            analogies       = explanation["analogies"],
        )
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/hypothesis")
def hypothesis(request: HypothesisRequest):
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Hypothesis text cannot be empty.")

    try:
        # Agent 1 — Parse
        parsed = parse_hypothesis(text)
        if parsed.get("error"):
            raise HTTPException(status_code=400, detail=parsed["error"])

        ticker = parsed["ticker"]
        company_name = TICKER_FULL_NAME.get(ticker, ticker)

        # Agents 2-5 run in sequence
        market   = collect_market_context(ticker)
        evidence = collect_historical_evidence(
            ticker,
            parsed.get("implied_return_pct"),
            parsed.get("timeframe_days", 90),
        )
        bear = collect_bear_case(ticker, company_name)
        bull = collect_bull_case(ticker, company_name)

        # Agent 6 — Synthesize
        brief = synthesize(parsed, market, evidence, bear, bull)

        if "error" in brief and not brief.get("hypothesis_clean"):
            raise HTTPException(status_code=500, detail=brief["error"])

        return brief

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# ── Subscriber Endpoints 

@app.post("/subscribe")
def subscribe(body: dict):
    """
    User submits Telegram username + optionally their chat ID.
    If chat ID provided → auto-approved immediately + welcome message sent.
    Otherwise → pending admin approval.
    """
    username = body.get("username", "").strip().lstrip("@")
    if not username:
        raise HTTPException(status_code=400, detail="Username cannot be empty.")
    if len(username) > 50:
        raise HTTPException(status_code=400, detail="Username too long.")

    telegram_id = body.get("telegram_id", "").strip() or None

    result = add_subscriber(username, telegram_id)

    # Send welcome message immediately on auto-approve
    if result.get("status") == "approved" and telegram_id:
        try:
            import asyncio
            from telegram import Bot
            token = os.getenv("TELEGRAM_BOT_TOKEN")
            async def _welcome():
                bot = Bot(token=token)
                await bot.send_message(
                    chat_id    = telegram_id,
                    text       = (
                        "🤖 <b>TradeSenpai Alerts — You're in!</b>\n\n"
                        "You'll now receive:\n"
                        "• 🌅 Morning brief (9:30 AM ET)\n"
                        "• 🌆 Evening outcomes (4:15 PM ET)\n"
                        "• 🔄 Direction flip alerts\n"
                        "• 📄 Sentiment spike alerts\n\n"
                        "⚠️ <i>Educational simulation only. Not financial advice.</i>"
                    ),
                    parse_mode = "HTML",
                )
            asyncio.run(_welcome())
        except Exception as e:
            print(f"[WARN] Welcome message failed: {e}")

    return result


@app.get("/subscribers")
def list_subscribers(admin: str = Depends(verify_admin)):
    """Admin — list all subscriber requests."""
    return {"subscribers": get_all_subscribers()}


@app.post("/subscribers/{sub_id}/approve")
def approve(sub_id: int, body: dict, admin: str = Depends(verify_admin)):
    """
    Admin approves a subscriber by providing their Telegram chat ID.
    Admin gets chat ID by asking the user to message the bot
    and checking /getUpdates.
    """
    telegram_id = str(body.get("telegram_id", "")).strip()
    if not telegram_id:
        raise HTTPException(status_code=400, detail="telegram_id required.")
    result = approve_subscriber(sub_id, telegram_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    # Send welcome message to the newly approved subscriber
    from alerts.telegram_bot import send_message as _send
    try:
        import asyncio
        from telegram import Bot
        from dotenv import load_dotenv
        load_dotenv()
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        async def _welcome():
            bot = Bot(token=token)
            await bot.send_message(
                chat_id    = telegram_id,
                text       = (
                    "🤖 <b>TradeSenpai Alerts — Approved!</b>\n\n"
                    "You'll now receive:\n"
                    "• 🌅 Morning brief (9:30 AM ET)\n"
                    "• 🌆 Evening outcomes (4:15 PM ET)\n"
                    "• 🔄 Direction flip alerts\n"
                    "• 📄 Sentiment spike alerts\n\n"
                    "⚠️ <i>Educational simulation only. Not financial advice.</i>"
                ),
                parse_mode = "HTML",
            )
        asyncio.run(_welcome())
    except Exception as e:
        print(f"[WARN] Welcome message failed: {e}")

    return result


@app.post("/subscribers/{sub_id}/reject")
def reject(sub_id: int, admin: str = Depends(verify_admin)):
    """Admin rejects a subscriber request."""
    return reject_subscriber(sub_id)



@app.post("/hypothesis/stream")
def hypothesis_stream(request: HypothesisRequest):
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty hypothesis.")

    def event_stream():
        def emit(step: int, status: str, data: dict = {}):
            payload = json.dumps({"step": step, "status": status, **data})
            yield f"data: {payload}\n\n"

        try:
            # Agent 1
            yield from emit(1, "running")
            parsed = parse_hypothesis(text)
            if parsed.get("error"):
                yield from emit(1, "error", {"message": parsed["error"]})
                return
            yield from emit(1, "done", {"ticker": parsed["ticker"]})

            ticker       = parsed["ticker"]
            company_name = TICKER_FULL_NAME.get(ticker, ticker)

            # Agent 2
            yield from emit(2, "running")
            market = collect_market_context(ticker)
            yield from emit(2, "done", {
                "price": market.get("current_price"),
                "rsi":   market.get("signals", {}).get("rsi_14"),
            })

            # Agent 3
            yield from emit(3, "running")
            evidence = collect_historical_evidence(
                ticker,
                parsed.get("implied_return_pct"),
                parsed.get("timeframe_days", 90),
            )
            yield from emit(3, "done", {
                "base_rate": evidence.get("base_rates", {}).get("base_rate_for_implied")
            })

            # Agent 4
            yield from emit(4, "running")
            bear = collect_bear_case(ticker, company_name)
            yield from emit(4, "done", {
                "risks_found": len(bear.get("risks", []))
            })

            # Agent 5
            yield from emit(5, "running")
            bull = collect_bull_case(ticker, company_name)
            yield from emit(5, "done", {
                "catalysts_found": len(bull.get("catalysts", []))
            })

            # Agent 6
            yield from emit(6, "running")
            brief = synthesize(parsed, market, evidence, bear, bull)
            yield from emit(6, "done")

            # Final result
            yield f"data: {json.dumps({'step': 0, 'status': 'complete', 'brief': brief})}\n\n"

        except Exception as e:
            import traceback
            print(traceback.format_exc())
            yield f"data: {json.dumps({'step': 0, 'status': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


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
    