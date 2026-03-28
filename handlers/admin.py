from __future__ import annotations

import secrets
import string

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import settings
from database.repository import repo
from keyboards.admin import admin_main_kb
from states.access import AdminStates

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id == settings.admin_id


def generate_code(length: int = 10) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    await message.answer(
        "👑 <b>Админ-панель</b>\n\nВыбери действие:",
        reply_markup=admin_main_kb(),
    )


@router.callback_query(F.data == "admin_generate_code")
async def cb_admin_generate_code(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    while True:
        code = generate_code()
        exists = await repo.get_access_code(code)
        if not exists:
            break

    await repo.create_access_code(code, callback.from_user.id)
    await callback.message.answer(f"✅ Новый код создан:\n<code>{code}</code>")
    await callback.answer()


@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    stats = await repo.get_codes_stats()
    text = f"""
📊 <b>Статистика</b>

<b>Всего кодов:</b> {stats["total"]}
<b>Активных кодов:</b> {stats["active"]}
<b>Использованных:</b> {stats["used"]}
<b>Неиспользованных:</b> {stats["unused"]}
<b>Активированных пользователей:</b> {stats["users_activated"]}
"""
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == "admin_list_codes")
async def cb_admin_list_codes(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    codes = await repo.list_access_codes(limit=30)

    if not codes:
        await callback.message.answer("Список кодов пуст.")
        await callback.answer()
        return

    lines = ["📋 <b>Последние коды</b>\n"]
    for item in codes:
        status = "✅ used" if item["is_used"] else ("🟢 active" if item["is_active"] else "⛔ inactive")
        used_by = item["used_by_telegram_id"] or "—"
        username = item["used_by_username"] or "—"
        lines.append(
            f"<code>{item['code']}</code> | {status}\n"
            f"👤 tg_id: <code>{used_by}</code> | user: {username}\n"
        )

    text = "\n".join(lines)

    if len(text) > 4000:
        for i in range(0, len(text), 4000):
            await callback.message.answer(text[i:i + 4000])
    else:
        await callback.message.answer(text)

    await callback.answer()


@router.callback_query(F.data == "admin_deactivate_code")
async def cb_admin_deactivate_code(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_for_deactivate_code)
    await callback.message.answer("⛔ Отправь код, который нужно деактивировать.")
    await callback.answer()


@router.callback_query(F.data == "admin_delete_code")
async def cb_admin_delete_code(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_for_delete_code)
    await callback.message.answer("🗑 Отправь неиспользованный код, который нужно удалить.")
    await callback.answer()


@router.message(AdminStates.waiting_for_deactivate_code)
async def process_deactivate_code(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        await message.answer("⛔ Доступ запрещён.")
        return

    code = (message.text or "").strip()
    success = await repo.deactivate_code(code)

    await state.clear()

    if success:
        await message.answer(f"⛔ Код <code>{code}</code> деактивирован.")
    else:
        await message.answer("Не удалось деактивировать код. Возможно, он уже использован или не существует.")


@router.message(AdminStates.waiting_for_delete_code)
async def process_delete_code(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        await message.answer("⛔ Доступ запрещён.")
        return

    code = (message.text or "").strip()
    success = await repo.delete_unused_code(code)

    await state.clear()

    if success:
        await message.answer(f"🗑 Код <code>{code}</code> удалён.")
    else:
        await message.answer("Не удалось удалить код. Он либо использован, либо не найден.")