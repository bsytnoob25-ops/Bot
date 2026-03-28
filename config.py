from dataclasses import dataclass
import os

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    bot_token: str
    admin_id: int
    gigachat_credentials: str
    gigachat_model: str
    gigachat_verify_ssl: bool
    db_path: str
    dialog_context_limit: int


def _to_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def load_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    admin_id_raw = os.getenv("ADMIN_ID", "0").strip()
    gigachat_credentials = os.getenv("GIGACHAT_CREDENTIALS", "").strip()

    if not bot_token:
        raise ValueError("BOT_TOKEN не найден в .env")
    if not admin_id_raw.isdigit():
        raise ValueError("ADMIN_ID должен быть числом")
    if not gigachat_credentials:
        raise ValueError("GIGACHAT_CREDENTIALS не найден в .env")

    return Settings(
        bot_token=bot_token,
        admin_id=int(admin_id_raw),
        gigachat_credentials=gigachat_credentials,
        gigachat_model=os.getenv("GIGACHAT_MODEL", "GigaChat").strip(),
        gigachat_verify_ssl=_to_bool(os.getenv("GIGACHAT_VERIFY_SSL", "false")),
        db_path=os.getenv("DB_PATH", "bot.db").strip(),
        dialog_context_limit=int(os.getenv("DIALOG_CONTEXT_LIMIT", "12")),
    )


settings = load_settings()