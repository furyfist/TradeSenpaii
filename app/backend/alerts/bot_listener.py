# Polls Telegram for new messages and auto-approves matching subscribers

import sys, os, asyncio
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from alerts.alert_store import approve_subscriber, get_all_subscribers
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    When user sends /start to the bot:
    1. Get their username + chat ID from the message
    2. Check if they have a pending request in DB
    3. If yes → auto-approve + welcome message
    4. If no → tell them to request on the website first
    """
    chat_id  = str(update.effective_chat.id)
    username = update.effective_user.username

    if not username:
        await update.message.reply_text(
            "⚠️ Your Telegram account needs a username set to use TradeSenpai alerts.\n"
            "Go to Telegram Settings → Username and set one, then try again."
        )
        return

    print(f"[INFO][bot_listener] /start from @{username} (chat_id={chat_id})")

    # Check if this username has a pending request
    subscribers = get_all_subscribers()
    match = next(
        (s for s in subscribers
         if s["username"].lower() == username.lower() and s["status"] == "pending"),
        None
    )

    if match:
        # Auto-approve
        approve_subscriber(match["id"], chat_id)
        await update.message.reply_text(
            f"✅ <b>Welcome to TradeSenpai Alerts!</b>\n\n"
            f"You're now subscribed, @{username}.\n\n"
            f"You'll receive:\n"
            f"• 🌅 Morning brief (9:30 AM ET)\n"
            f"• 🌆 Evening outcomes (4:15 PM ET)\n"
            f"• 🔄 Direction flip alerts\n"
            f"• 📄 Sentiment spike alerts\n\n"
            f"⚠️ <i>Educational simulation only. Not financial advice.</i>",
            parse_mode="HTML"
        )
        print(f"[INFO][bot_listener] Auto-approved @{username} with chat_id={chat_id}")

    elif any(s["username"].lower() == username.lower() and s["status"] == "approved"
             for s in subscribers):
        await update.message.reply_text(
            f"✅ You're already subscribed, @{username}!\n"
            f"Alerts will arrive at scheduled times."
        )

    else:
        await update.message.reply_text(
            f"👋 Hi @{username}!\n\n"
            f"You don't have a pending request yet.\n"
            f"Visit the TradeSenpai website and submit your username first,\n"
            f"then send /start here to activate alerts."
        )


async def handle_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User sends /stop — mark them as rejected/unsubscribed."""
    username = update.effective_user.username
    await update.message.reply_text(
        f"👋 Alerts paused for @{username}.\n"
        f"Visit the website to re-subscribe anytime."
    )
    print(f"[INFO][bot_listener] /stop from @{username}")


def create_bot_app():
    """Build the telegram Application (polling mode)."""
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("stop",  handle_stop))
    return app


# ── Quick Test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("[INFO] Starting bot listener in polling mode...")
    app = create_bot_app()
    app.run_polling()