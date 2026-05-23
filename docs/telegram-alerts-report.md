# Telegram Alerts Feature — TradeSenpai

## Overview

The **Get Telegram Alerts** feature lets users subscribe to receive real-time and scheduled trading signal notifications directly in Telegram. Alerts are broadcast to all approved subscribers using a Python-based Telegram bot running as a background service alongside the FastAPI backend.

---

## Architecture at a Glance

```
User subscribes via website
        │
        ▼
POST /subscribe (main.py)
        │
        ▼
subscribers table (Supabase)
        │                        ┌──────────────────────────┐
        ├───── pending ──────────▶  Admin approves via UI   │
        │                        │  POST /subscribers/{id}/approve
        │                        └──────────┬───────────────┘
        └───── auto-approved ───────────────┤
               (if chat_id provided)        │
                                            ▼
                                   Welcome message sent
                                   via Telegram bot
                                            │
                                            ▼
                              APScheduler runs 4 jobs
                              (morning, evening, weekly, watcher)
                                            │
                                            ▼
                              broadcast() → all approved chat_ids
```

---

## Files Involved

| File | Purpose |
|------|---------|
| `app/backend/alerts/telegram_bot.py` | Core bot: send/broadcast messages |
| `app/backend/alerts/alert_store.py` | DB operations: subscribers, deduplication |
| `app/backend/alerts/scheduler.py` | APScheduler jobs for timed alerts |
| `app/backend/alerts/watcher.py` | Real-time signal change detection |
| `app/backend/alerts/bot_listener.py` | Handles `/start` and `/stop` commands |
| `app/backend/alerts/digest.py` | HTML message formatting |
| `app/backend/main.py` | FastAPI endpoints + startup integration |
| `app/frontend/src/components/SubscribeForm.jsx` | User subscription form |
| `app/frontend/src/components/AdminPanel.jsx` | Admin approval interface |

---

## Subscription Flow

### Option A — User Provides Chat ID (Auto-Approved)

1. User opens the website and fills in their Telegram username + Chat ID.
2. `POST /subscribe` is called.
3. Backend immediately approves the subscriber and sends a welcome message.
4. User starts receiving alerts right away.

### Option B — Username Only (Pending Approval)

1. User submits only their Telegram username.
2. Request is stored with status `pending`.
3. Admin sees the pending request in the Admin Panel.
4. Admin gets the user's Chat ID via `@userinfobot` on Telegram.
5. Admin enters the Chat ID and clicks **Approve** → `POST /subscribers/{id}/approve`.
6. Bot sends a welcome message to the newly approved subscriber.

### Option C — Via Telegram Bot Directly

1. User sends `/start` to the TradeSenpai Telegram bot.
2. Bot listener (`bot_listener.py`) receives the message.
3. If the user has a pending request → auto-approves it.
4. If no pending request → instructs the user to register on the website first.
5. User can send `/stop` to unsubscribe.

---

## Alert Types

### Scheduled Alerts (scheduler.py)

| Alert | Time (ET) | Days | Description |
|-------|-----------|------|-------------|
| **Morning Brief** | 9:30 AM | Mon–Fri | Predicted direction + confidence for all 6 tickers |
| **Evening Brief** | 4:15 PM | Mon–Fri | Actual outcomes vs predictions + running accuracy |
| **Weekly Digest** | 6:00 PM | Sunday | Weekly accuracy stats per ticker |
| **Signal Watcher** | Every 2 hrs | Daily | Checks for real-time signal changes (see below) |

### Real-Time Signal Alerts (watcher.py)

| Alert | Trigger | Cooldown |
|-------|---------|---------|
| **Direction Flip** | Model prediction flips (UP ↔ DOWN) | 12 hours |
| **Sentiment Spike** | SEC filing sentiment Z-score > 2.0σ | 24 hours |
| **Litigation Spike** | Loughran-McDonald litigation language above threshold | 48 hours |

---

## Covered Tickers

All alerts cover these 6 tickers:

- `KO` — Coca-Cola
- `JNJ` — Johnson & Johnson
- `PG` — Procter & Gamble
- `WMT` — Walmart
- `AAPL` — Apple
- `GOOGL` — Alphabet

---

## Message Formats (digest.py)

### Morning Brief
```
🌅 TradeSenpai Morning Brief
<timestamp>
─────────────────────────
🟢 KO ▲ UP  69.6% confidence
   Coca-Cola
🔴 JNJ ▼ DOWN  55.1% confidence
   Johnson & Johnson
─────────────────────────
⚠️ Educational simulation only. Not financial advice.
Model accuracy ~52% across all tickers.
```

### Direction Flip
```
🔄 DIRECTION FLIP — KO
Coca-Cola

Previous: DOWN
New: ▲ UP (69.6% confidence)

Model changed its prediction since last run.
⚠️ Educational only. Not financial advice.
```

### Sentiment Spike
```
📄 SEC SENTIMENT SPIKE — JNJ
Johnson & Johnson

New sentiment score: 0.523 (positive ↑)
Z-score: 2.45σ from ticker average

A new SEC filing has shifted the sentiment signal significantly.
⚠️ Educational only. Not financial advice.
```

### Litigation Spike
```
⚖️ LITIGATION FLAG — JNJ
Johnson & Johnson

Loughran-McDonald litigation language spiked in latest SEC filing.
Elevated legal/regulatory language detected — monitor for developments.
⚠️ Educational only. Not financial advice.
```

---

## Alert Dispatch (telegram_bot.py)

### Single Message (admin/system use)
```python
async def _send(text: str):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    await bot.send_message(
        chat_id    = TELEGRAM_CHAT_ID,
        text       = text,
        parse_mode = "HTML",
    )
```

### Broadcast (all subscribers)
```python
def broadcast(text: str):
    chat_ids = set([TELEGRAM_CHAT_ID])      # Admin always included
    chat_ids.update(get_approved_chat_ids()) # All approved subscribers
    for chat_id in chat_ids:
        asyncio.run(_send_to(text, chat_id)) # Gracefully skips failures
```

All messages use `parse_mode="HTML"` for bold, italic, and strikethrough formatting.

---

## Deduplication (alert_store.py)

A `sent_alerts` table prevents duplicate alerts within cooldown windows.

| Column | Purpose |
|--------|---------|
| `alert_key` | Unique identifier (e.g., `morning_20260523`) |
| `alert_type` | `morning_brief`, `evening_brief`, `direction_flip`, etc. |
| `ticker` | NULL for briefs; ticker symbol for signal alerts |
| `sent_at` | Timestamp for cooldown calculation |

`already_sent(alert_key, cooldown_hours=24)` is checked before every dispatch.

---

## Database Schema (alert_store.py)

### `subscribers` table

| Column | Type | Notes |
|--------|------|-------|
| `id` | INT | Primary key |
| `username` | VARCHAR | Telegram username |
| `telegram_id` | VARCHAR | Chat ID (NULL until approved) |
| `status` | ENUM | `pending` / `approved` / `rejected` |
| `requested_at` | TIMESTAMP | Submission time |
| `approved_at` | TIMESTAMP | Approval time |

---

## API Endpoints (main.py)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/subscribe` | Public | Submit subscription request |
| `GET` | `/subscribers` | Admin JWT | List all subscribers |
| `POST` | `/subscribers/{id}/approve` | Admin JWT | Approve + set Chat ID |
| `POST` | `/subscribers/{id}/reject` | Admin JWT | Reject a request |

Rate limit on `/subscribe`: **3 requests/minute**.

---

## Startup Sequence (main.py, lines 44–78)

1. Preload all 6 ticker ML models into memory.
2. Create APScheduler (timezone: `America/New_York`).
3. Register 4 jobs: morning brief, evening brief, weekly digest, signal watcher.
4. Start APScheduler.
5. Build Telegram bot application.
6. Start bot listener in a **background thread** (polling mode).

---

## Environment Variables Required

| Variable | Purpose |
|----------|---------|
| `TELEGRAM_BOT_TOKEN` | Bot API token from BotFather |
| `TELEGRAM_CHAT_ID` | Admin/default chat ID (always receives alerts) |
| `SUPABASE_POOLER_URL` | Database connection string |

---

## Dependencies

```
python-telegram-bot==22.6
APScheduler
```

---

## Summary

The Telegram Alerts system is a fully automated, multi-channel notification pipeline:

- **Subscription** happens via website form or directly through the Telegram bot's `/start` command.
- **Approval** can be instant (if Chat ID is provided) or manual via the Admin Panel.
- **Alerts** fire on a schedule (morning/evening/weekly) and in real-time whenever the model detects a direction flip, sentiment spike, or litigation spike.
- **Broadcast** iterates over all approved subscribers and delivers HTML-formatted messages, gracefully skipping any failed deliveries.
- **Deduplication** ensures no subscriber receives the same alert twice within the defined cooldown window.
