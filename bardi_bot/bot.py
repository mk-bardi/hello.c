"""
bot.py — Entry point for BardiOS Telegram bot.
run_polling() manages its own event loop — do NOT wrap in asyncio.run().
Async setup (DB init, scheduler) is done via the post_init hook.
"""

import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application

from bardi_bot.handlers import accountability, breakdown, commands, focus, tasks
from bardi_bot.scheduler import scheduler, start_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """Runs inside the bot's event loop after the app is initialised."""
    from bardi_bot.database import init_db
    await init_db()
    logger.info("Database initialized.")
    start_scheduler(application)


def main() -> None:
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("BOT_TOKEN environment variable is not set.")

    application = (
        Application.builder()
        .token(bot_token)
        .post_init(post_init)
        .post_stop(lambda app: scheduler.shutdown(wait=False))
        .build()
    )

    # Register handlers (ConversationHandlers first)
    breakdown.register(application)
    accountability.register(application)
    tasks.register(application)
    focus.register(application)
    commands.register(application)

    logger.info("BardiOS starting...")
    # run_polling() manages the asyncio event loop itself — no asyncio.run()
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
