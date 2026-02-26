import os
import asyncio
from telegram import Bot
from dotenv import load_dotenv
from alerts.alert_store import get_approved_chat_ids

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")


async def _send(text: str):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    await bot.send_message(
        chat_id    = TELEGRAM_CHAT_ID,
        text       = text,
        parse_mode = "HTML",
    )


def send_message(text: str):
    """
    Sync wrapper — safe to call from APScheduler jobs
    and anywhere outside async context.
    """
    try:
        asyncio.run(_send(text))
        print(f"[INFO][telegram] Message sent ({len(text)} chars)")
    except Exception as e:
        print(f"[ERROR][telegram] Failed to send message: {e}")

def broadcast(text: str):
    """
    Send message to ALL approved subscribers + the default admin chat.
    Falls back gracefully if a chat_id is invalid.
    """
    # Always include admin
    chat_ids = set([TELEGRAM_CHAT_ID])

    # Add all approved subscribers
    try:
        chat_ids.update(get_approved_chat_ids())
    except Exception as e:
        print(f"[WARN][telegram] Could not fetch subscribers: {e}")

    for chat_id in chat_ids:
        try:
            asyncio.run(_send_to(text, chat_id))
            print(f"[INFO][telegram] Sent to {chat_id}")
        except Exception as e:
            print(f"[WARN][telegram] Failed to send to {chat_id}: {e}")


async def _send_to(text: str, chat_id: str):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
    
# ── Quick Test 
if __name__ == "__main__":
    send_message(
        "🤖 <b>TradeSenpai V3</b> — Telegram alerts online.\n"
        "Backend connected successfully."
    )