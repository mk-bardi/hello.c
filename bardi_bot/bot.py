"""
bot.py — Entry point for Bardi Assistant Telegram bot.
Wires all handlers, initializes DB, starts scheduler, and runs polling.
"""

import asyncio
import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application

from bardi_bot.database import init_db
from bardi_bot.handlers import accountability, breakdown, commands, focus, tasks
from bardi_bot.scheduler import scheduler, start_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("BOT_TOKEN environment variable is not set.")

    # Initialize database
    await init_db()
    logger.info("Database initialized.")

    # Build application — shut down scheduler cleanly on stop
    application = (
        Application.builder()
        .token(bot_token)
        .post_stop(lambda app: scheduler.shutdown(wait=False))
        .build()
    )

    # Register handlers (ConversationHandlers first)
    breakdown.register(application)
    accountability.register(application)
    tasks.register(application)
    focus.register(application)
    commands.register(application)  # plain CommandHandlers last

    # Start scheduler
    start_scheduler(application)

    logger.info("Bardi Assistant starting...")
    await application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    asyncio.run(main())
