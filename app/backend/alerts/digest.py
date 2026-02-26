from datetime import datetime

TICKER_NAMES = {
    "KO":    "Coca-Cola",
    "JNJ":   "Johnson & Johnson",
    "PG":    "Procter & Gamble",
    "WMT":   "Walmart",
    "AAPL":  "Apple",
    "GOOGL": "Alphabet",
}


def fmt_morning_brief(predictions: list[dict]) -> str:
    now = datetime.now().strftime("%A %b %d, %Y · %I:%M %p ET")
    lines = [
        f"🌅 <b>TradeSenpai Morning Brief</b>",
        f"<i>{now}</i>",
        "─────────────────────────",
    ]

    for p in predictions:
        ticker  = p.get("ticker", "?")
        name    = TICKER_NAMES.get(ticker, ticker)
        pred    = p.get("prediction", "?")
        conf    = p.get("confidence", 0) * 100
        arrow   = "▲" if pred == "UP" else "▼"
        emoji   = "🟢" if pred == "UP" else "🔴"

        lines.append(
            f"{emoji} <b>{ticker}</b> {arrow} {pred}  "
            f"<code>{conf:.1f}%</code> confidence\n"
            f"   <i>{name}</i>"
        )

    lines += [
        "─────────────────────────",
        "⚠️ <i>Educational simulation only. Not financial advice.</i>",
        f"Model accuracy ~52% across all tickers.",
    ]
    return "\n".join(lines)


def fmt_direction_flip(ticker: str, old_pred: str, new_pred: str, confidence: float) -> str:
    arrow = "▲" if new_pred == "UP" else "▼"
    emoji = "🔄"
    name  = TICKER_NAMES.get(ticker, ticker)
    return (
        f"{emoji} <b>DIRECTION FLIP — {ticker}</b>\n"
        f"{name}\n\n"
        f"Previous: <s>{old_pred}</s>\n"
        f"New: <b>{arrow} {new_pred}</b> "
        f"(<code>{confidence*100:.1f}%</code> confidence)\n\n"
        f"<i>Model changed its prediction since last run.</i>\n"
        f"⚠️ Educational only. Not financial advice."
    )


def fmt_sentiment_spike(ticker: str, score: float, zscore: float) -> str:
    name      = TICKER_NAMES.get(ticker, ticker)
    direction = "positive ↑" if score > 0 else "negative ↓"
    return (
        f"📄 <b>SEC SENTIMENT SPIKE — {ticker}</b>\n"
        f"{name}\n\n"
        f"New sentiment score: <code>{score:.3f}</code> ({direction})\n"
        f"Z-score: <code>{zscore:.2f}σ</code> from ticker average\n\n"
        f"<i>A new SEC filing has shifted the sentiment signal significantly.</i>\n"
        f"⚠️ Educational only. Not financial advice."
    )


def fmt_litigation_spike(ticker: str) -> str:
    name = TICKER_NAMES.get(ticker, ticker)
    return (
        f"⚖️ <b>LITIGATION FLAG — {ticker}</b>\n"
        f"{name}\n\n"
        f"Loughran-McDonald litigation language spiked in latest SEC filing.\n"
        f"<i>Elevated legal/regulatory language detected — monitor for developments.</i>\n"
        f"⚠️ Educational only. Not financial advice."
    )


def fmt_evening_brief(outcomes: list[dict], accuracy_tracker: dict) -> str:
    now = datetime.now().strftime("%A %b %d, %Y · %I:%M %p ET")
    lines = [
        f"🌆 <b>TradeSenpai Evening Brief</b>",
        f"<i>{now}</i>",
        "─────────────────────────",
    ]

    for o in outcomes:
        ticker   = o.get("ticker", "?")
        pred     = o.get("prediction", "?")
        actual   = o.get("actual_direction", "?")
        correct  = pred == actual
        emoji    = "✅" if correct else "❌"
        ret      = o.get("actual_return", 0)

        lines.append(
            f"{emoji} <b>{ticker}</b>  "
            f"Predicted: {pred} | Actual: {actual}  "
            f"<code>{ret:+.2f}%</code>"
        )

    # Running accuracy
    total   = accuracy_tracker.get("total", 0)
    correct = accuracy_tracker.get("correct", 0)
    acc     = (correct / total * 100) if total > 0 else 0

    lines += [
        "─────────────────────────",
        f"📊 Running accuracy: <code>{acc:.1f}%</code> "
        f"({correct}/{total} correct this week)",
        "⚠️ <i>Educational simulation only. Not financial advice.</i>",
    ]
    return "\n".join(lines)


def fmt_weekly_digest(weekly_stats: dict) -> str:
    now = datetime.now().strftime("Week ending %b %d, %Y")
    lines = [
        f"📈 <b>TradeSenpai Weekly Digest</b>",
        f"<i>{now}</i>",
        "─────────────────────────",
    ]

    for ticker, stats in weekly_stats.items():
        acc   = stats.get("accuracy", 0)
        total = stats.get("total", 0)
        bar   = "█" * int(acc / 10) + "░" * (10 - int(acc / 10))
        lines.append(
            f"<b>{ticker}</b>  {bar}  <code>{acc:.0f}%</code>  ({total} signals)"
        )

    lines += [
        "─────────────────────────",
        "⚠️ <i>Educational simulation only. Not financial advice.</i>",
    ]
    return "\n".join(lines)