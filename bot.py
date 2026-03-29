import asyncio
import logging
import os

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from database.db import init_db
from handlers.admin import router as admin_router
from handlers.user import router as user_router
from utils.logger import setup_logger


async def health(request: web.Request) -> web.Response:
    return web.Response(text="OK")


async def start_healthcheck_server() -> None:
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()

    logging.getLogger(__name__).info(f"Healthcheck server started on port {port}")


async def main() -> None:
    setup_logger()
    logger = logging.getLogger(__name__)

    await init_db()
    logger.info("База данных инициализирована")

    await start_healthcheck_server()

bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

#
await bot.delete_webhook(drop_pending_updates=True)

dp = Dispatcher()
dp.include_router(admin_router)
dp.include_router(user_router)

logger.info("Бот запущен")
await dp.start_polling(bot)