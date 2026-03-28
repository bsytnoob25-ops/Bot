from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Сгенерировать код", callback_data="admin_generate_code")],
        [InlineKeyboardButton(text="📋 Список кодов", callback_data="admin_list_codes")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="⛔ Деактивировать код", callback_data="admin_deactivate_code")],
        [InlineKeyboardButton(text="🗑 Удалить неиспользованный код", callback_data="admin_delete_code")],
    ])