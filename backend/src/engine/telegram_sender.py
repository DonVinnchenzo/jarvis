import logging

from src.config import Settings

logger = logging.getLogger(__name__)


async def send_to_all_users(message: str, settings: Settings) -> dict[str, int]:
    """Send message to all whitelisted Telegram users.

    Returns a dict mapping user_id (str) to message_id (int).
    """
    from telegram import Bot

    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not configured, skipping send")
        return {}

    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    message_ids: dict[str, int] = {}

    for user_id in settings.allowed_user_ids_list:
        try:
            result = await bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="Markdown",
            )
            message_ids[str(user_id)] = result.message_id
            logger.info("Sent reminder to user %s (message_id=%s)", user_id, result.message_id)
        except Exception:
            logger.exception("Failed to send to user %s", user_id)
            # Don't fail the whole run if one user's send fails

    return message_ids
