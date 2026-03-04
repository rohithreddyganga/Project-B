"""
Telegram notification bot.
Sends daily reports, alerts, and error notifications.
"""
import httpx
from loguru import logger
from src.config import config


async def send_telegram(message: str, parse_mode: str = "HTML"):
    """Send a message to your Telegram chat."""
    token = config.env.telegram_bot_token
    chat_id = config.env.telegram_chat_id
    if not token or not chat_id:
        logger.debug("Telegram not configured, skipping notification")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message[:4096],  # Telegram limit
        "parse_mode": parse_mode,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                logger.warning(f"Telegram send failed: {resp.text}")
    except Exception as e:
        logger.warning(f"Telegram notification error: {e}")


async def send_daily_report(applied: int, failed: int, total_scraped: int, total_cost: float):
    """Send formatted daily report."""
    msg = f"""<b>📊 AutoApply Daily Report</b>

✅ <b>Applied:</b> {applied}
❌ <b>Failed:</b> {failed}
🔍 <b>Scraped:</b> {total_scraped}
💰 <b>Cost today:</b> ${total_cost:.2f}

<i>Pipeline completed at local time.</i>"""

    await send_telegram(msg)


async def send_alert(title: str, details: str):
    """Send an alert notification."""
    msg = f"⚠️ <b>{title}</b>\n\n{details}"
    await send_telegram(msg)
