import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from database.db import init_db
from handlers.admin import router as admin_router
from handlers.user import router as user_router
from utils.logger import setup_logger


async def main() -> None:
    setup_logger()
    logger = logging.getLogger(__name__)

    await init_db()
    logger.info("База данных инициализирована")

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()
    dp.include_router(admin_router)
    dp.include_router(user_router)

    logger.info("Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())