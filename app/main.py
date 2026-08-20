import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiohttp import web
from app.bot.handlers import main_router
from app.bot.middlewares import (
    AuthMiddleware,
    DatabaseMiddleware,
    ErrorMiddleware,
    RequiredChannelMiddleware,
    ThrottlingMiddleware,
)
from app.bot.storage.persistent_storage import PersistentFSMStorage
from app.config import settings
from app.database.models import Base
from app.database.session import engine
from app.services.scheduler_service import SchedulerService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("app")


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized successfully.")


async def health_check(request):
    return web.Response(text="Telegram Test Platform Bot is RUNNING 24/7 OK!")


async def start_health_server():
    port = int(os.environ.get("PORT", 8080))
    app_web = web.Application()
    app_web.router.add_get("/", health_check)
    app_web.router.add_get("/health", health_check)
    runner = web.AppRunner(app_web)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Health check web server running on port {port}")
    return runner


async def main():
    logger.info("Starting Telegram Test Platform Bot with Turbo Optimization...")

    # Persistent Storage
    storage = PersistentFSMStorage()

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher(storage=storage)

    # Initialize Database Schema
    await create_tables()

    # Register Middlewares
    dp.update.middleware(ErrorMiddleware())
    dp.update.middleware(ThrottlingMiddleware(rate_limit=0.35))
    dp.update.middleware(DatabaseMiddleware())
    dp.update.middleware(AuthMiddleware(cache_ttl=120))
    dp.update.middleware(RequiredChannelMiddleware(cache_ttl_seconds=600))

    # Include Main Routers
    dp.include_router(main_router)

    # Launch Background Scheduler
    scheduler_task = asyncio.create_task(SchedulerService.start_scheduler_loop(bot, interval_seconds=30))

    # Start HTTP Health Server for Render / Cloud (if PORT or web requested)
    web_runner = None
    try:
        web_runner = await start_health_server()
    except Exception as e:
        logger.warning(f"Could not start local web server on port (not critical): {e}")

    # Start Polling
    logger.info("Bot is polling with instant update resolution...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            polling_timeout=15
        )
    finally:
        scheduler_task.cancel()
        if web_runner:
            await web_runner.cleanup()
        await storage.close()
        await bot.session.close()
        await engine.dispose()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot process exited.")
