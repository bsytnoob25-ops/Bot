from __future__ import annotations

import html
import logging

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import settings
from database.repository import repo
from keyboards.user import user_main_kb
from services.deepseek import DeepSeekError, ask_deepseek
from states.access import AccessStates

router = Router()
logger = logging.getLogger(__name__)


WELCOME_TEXT = """
👋 <b>Добро пожаловать в ChatGPT</b>

Здесь ты можешь общаться с нейросетью прямо в Telegram.
Доступ открывается только после активации специального кода.

Что доступно:
• умные ответы на твои запросы
• сохранение простого контекста диалога
• очистка истории в один клик
• профиль и статус доступа
"""

HELP_TEXT = """
<b>Помощь</b>

Команды:
• /start — открыть главное меню
• /help — показать помощь
• /admin — админ-панель

Как пользоваться:
1. Нажми <b>Активировать доступ</b>
2. Введи выданный код
3. После активации просто отправляй сообщения боту

Дополнительно:
• <b>Профиль</b> — информация о твоём аккаунте
• <b>Очистить диалог</b> — удалить историю общения с ИИ
"""


def build_profile_text(user: dict) -> str:
    access_status = "✅ Активирован" if user["is_activated"] else "🔒 Не активирован"
    username = f"@{user['username']}" if user["username"] else "—"
    code = user["activated_code"] or "—"

    return f"""
<b>Твой профиль</b>

<b>Telegram ID:</b> <code>{user["telegram_id"]}</code>
<b>Username:</b> {html.escape(username)}
<b>Статус доступа:</b> {access_status}
<b>Активированный код:</b> <code>{html.escape(code)}</code>
"""


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await repo.create_or_update_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )

    user = await repo.get_user(message.from_user.id)
    await message.answer(
        WELCOME_TEXT,
        reply_markup=user_main_kb(bool(user["is_activated"])),
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)


@router.callback_query(F.data == "help_info")
async def cb_help(callback: CallbackQuery) -> None:
    await callback.message.edit_text(HELP_TEXT, reply_markup=user_main_kb(
        is_activated=bool((await repo.get_user(callback.from_user.id))["is_activated"])
    ))
    await callback.answer()


@router.callback_query(F.data == "profile")
async def cb_profile(callback: CallbackQuery) -> None:
    user = await repo.get_user(callback.from_user.id)
    if not user:
        await repo.create_or_update_user(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            full_name=callback.from_user.full_name,
        )
        user = await repo.get_user(callback.from_user.id)

    await callback.message.edit_text(
        build_profile_text(user),
        reply_markup=user_main_kb(bool(user["is_activated"])),
    )
    await callback.answer()


@router.callback_query(F.data == "activate_access")
async def cb_activate_access(callback: CallbackQuery, state: FSMContext) -> None:
    user = await repo.get_user(callback.from_user.id)
    if user and user["is_activated"]:
        await callback.answer("У тебя уже есть доступ ✅", show_alert=True)
        return

    await state.set_state(AccessStates.waiting_for_access_code)
    await callback.message.answer("🔑 Введи код доступа одним сообщением.")
    await callback.answer()


@router.message(AccessStates.waiting_for_access_code)
async def process_access_code(message: Message, state: FSMContext) -> None:
    code = (message.text or "").strip()

    if not code or len(code) < 4:
        await message.answer("❌ Некорректный код. Попробуй ещё раз.")
        return

    user = await repo.get_user(message.from_user.id)
    if user and user["is_activated"]:
        await state.clear()
        await message.answer("✅ У тебя уже активирован доступ.")
        return

    code_data = await repo.get_access_code(code)

    if not code_data:
        await message.answer("❌ Код не найден или недействителен.")
        return

    if not code_data["is_active"]:
        await message.answer("⚠️ Этот код деактивирован администратором.")
        return

    if code_data["is_used"]:
        if code_data["used_by_telegram_id"] == message.from_user.id:
            await repo.activate_user(message.from_user.id, code)
            await state.clear()
            await message.answer("✅ Этот код уже привязан к твоему аккаунту. Доступ подтверждён.")
            return

        await message.answer("⚠️ Этот код уже активирован на другом аккаунте.")
        return

    await repo.activate_user(message.from_user.id, code)
    await repo.mark_code_used(code, message.from_user.id, message.from_user.username)
    await state.clear()

    await message.answer(
        "🎉 <b>Доступ успешно активирован!</b>\n\nТеперь можешь просто отправлять сообщения ChatGPT.",
        reply_markup=user_main_kb(True),
    )


@router.callback_query(F.data == "clear_dialog")
async def cb_clear_dialog(callback: CallbackQuery) -> None:
    await repo.clear_dialog_messages(callback.from_user.id)
    user = await repo.get_user(callback.from_user.id)
    await callback.message.answer("🧹 История диалога очищена.")
    await callback.answer()

    if user:
        await callback.message.answer(
            "Главное меню:",
            reply_markup=user_main_kb(bool(user["is_activated"])),
        )


@router.message(F.text)
async def handle_chat(message: Message) -> None:
    text = (message.text or "").strip()
    if not text:
        return

    if text.startswith("/"):
        return

    await repo.create_or_update_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )

    user = await repo.get_user(message.from_user.id)
    if not user or not user["is_activated"]:
        await message.answer(
            "🔒 У тебя пока нет доступа к нейросети.\n\nНажми /start и активируй код."
        )
        return

    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    system_prompt = {
        "role": "system",
        "content": (
            "Ты полезный, вежливый и точный AI-ассистент. "
            "Отвечай структурированно и понятно на русском языке, если пользователь пишет по-русски."
        )
    }

    history = await repo.get_dialog_messages(
        telegram_id=message.from_user.id,
        limit=settings.dialog_context_limit,
    )

    messages = [system_prompt] + history + [{"role": "user", "content": text}]

    try:
        answer = await ask_deepseek(messages)
    except DeepSeekError as exc:
        await message.answer("⚠️ {html.escape(str(exc))}")
        return
    except Exception:
        logger.exception("Неожиданная ошибка при общении с ChatGPT")
        await message.answer("⚠️ Произошла непредвиденная ошибка. Попробуй позже.")
        return

    await repo.add_dialog_message(message.from_user.id, "user", text)
    await repo.add_dialog_message(message.from_user.id, "assistant", answer)

    safe_answer = answer.strip()
    if len(safe_answer) > 4000:
        for i in range(0, len(safe_answer), 4000):
            await message.answer(safe_answer[i:i + 4000])
    else:
        await message.answer(safe_answer)