from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def user_main_kb(is_activated: bool) -> InlineKeyboardMarkup:
    rows = []

    if not is_activated:
        rows.append([
            InlineKeyboardButton(text="🔐 Активировать доступ", callback_data="activate_access")
        ])

    rows.extend([
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="🧹 Очистить диалог", callback_data="clear_dialog")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help_info")],
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)