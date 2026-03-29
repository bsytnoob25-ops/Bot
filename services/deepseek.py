import asyncio
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

from config import settings


class DeepSeekError(Exception):
    pass


def _map_role(role: str) -> MessagesRole:
    role = (role or "").strip().lower()

    if role == "system":
        return MessagesRole.SYSTEM
    if role == "assistant":
        return MessagesRole.ASSISTANT
    return MessagesRole.USER


def _build_chat_payload(messages: list[dict]) -> Chat:
    giga_messages = [
        Messages(
            role=_map_role(item.get("role", "user")),
            content=str(item.get("content", "")).strip(),
        )
        for item in messages
        if str(item.get("content", "")).strip()
    ]

    if not giga_messages:
        raise DeepSeekError("В запросе нет сообщений для ChatGPT.")

    return Chat(messages=giga_messages)


def _sync_ask_gigachat(messages: list[dict]) -> str:
    try:
        payload = _build_chat_payload(messages)

        with GigaChat(
            credentials=settings.gigachat_credentials,
            verify_ssl_certs=settings.gigachat_verify_ssl,
            model=settings.gigachat_model,
            timeout=60,
        ) as giga:
            response = giga.chat(payload)

        if not response or not response.choices:
            raise DeepSeekError("ChatGPT вернул пустой ответ.")

        content = (response.choices[0].message.content or "").strip()
        if not content:
            raise DeepSeekError("ChatGPT вернул пустой текст.")

        return content

    except DeepSeekError:
        raise
    except Exception as exc:
        raise DeepSeekError(f"Ошибка ChatGPT: {exc}") from exc


async def ask_deepseek(messages: list[dict]) -> str:
    return await asyncio.to_thread(_sync_ask_gigachat, messages)