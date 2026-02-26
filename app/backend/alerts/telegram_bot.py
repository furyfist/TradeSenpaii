import os
import asyncio
from telegram import Bot
from dotenv import load_dotenv
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


# ── Quick Test 
if __name__ == "__main__":
    send_message(
        "🤖 <b>TradeSenpai V3</b> — Telegram alerts online.\n"
        "Backend connected successfully."
    )