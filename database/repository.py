from __future__ import annotations

import aiosqlite
from typing import Any

from config import settings


class Repository:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def _connect(self) -> aiosqlite.Connection:
        conn = await aiosqlite.connect(self.db_path)
        conn.row_factory = aiosqlite.Row
        return conn

    async def create_or_update_user(
        self,
        telegram_id: int,
        username: str | None,
        full_name: str,
    ) -> None:
        db = await self._connect()
        try:
            await db.execute("""
            INSERT INTO users (telegram_id, username, full_name)
            VALUES (?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username,
                full_name = excluded.full_name
            """, (telegram_id, username, full_name))
            await db.commit()
        finally:
            await db.close()

    async def get_user(self, telegram_id: int) -> dict[str, Any] | None:
        db = await self._connect()
        try:
            cur = await db.execute(
                "SELECT * FROM users WHERE telegram_id = ?",
                (telegram_id,),
            )
            row = await cur.fetchone()
            return dict(row) if row else None
        finally:
            await db.close()

    async def activate_user(self, telegram_id: int, code: str) -> None:
        db = await self._connect()
        try:
            await db.execute("""
            UPDATE users
            SET is_activated = 1, activated_code = ?
            WHERE telegram_id = ?
            """, (code, telegram_id))
            await db.commit()
        finally:
            await db.close()

    async def create_access_code(self, code: str, admin_id: int) -> None:
        db = await self._connect()
        try:
            await db.execute("""
            INSERT INTO access_codes (code, created_by_admin)
            VALUES (?, ?)
            """, (code, admin_id))
            await db.commit()
        finally:
            await db.close()

    async def get_access_code(self, code: str) -> dict[str, Any] | None:
        db = await self._connect()
        try:
            cur = await db.execute(
                "SELECT * FROM access_codes WHERE code = ?",
                (code,),
            )
            row = await cur.fetchone()
            return dict(row) if row else None
        finally:
            await db.close()

    async def mark_code_used(
        self,
        code: str,
        telegram_id: int,
        username: str | None,
    ) -> None:
        db = await self._connect()
        try:
            await db.execute("""
            UPDATE access_codes
            SET is_used = 1,
                used_by_telegram_id = ?,
                used_by_username = ?,
                used_at = CURRENT_TIMESTAMP
            WHERE code = ?
            """, (telegram_id, username, code))
            await db.commit()
        finally:
            await db.close()

    async def deactivate_code(self, code: str) -> bool:
        db = await self._connect()
        try:
            cur = await db.execute("""
            UPDATE access_codes
            SET is_active = 0
            WHERE code = ? AND is_used = 0
            """, (code,))
            await db.commit()
            return cur.rowcount > 0
        finally:
            await db.close()

    async def delete_unused_code(self, code: str) -> bool:
        db = await self._connect()
        try:
            cur = await db.execute("""
            DELETE FROM access_codes
            WHERE code = ? AND is_used = 0
            """, (code,))
            await db.commit()
            return cur.rowcount > 0
        finally:
            await db.close()

    async def list_access_codes(self, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        db = await self._connect()
        try:
            cur = await db.execute("""
            SELECT *
            FROM access_codes
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """, (limit, offset))
            rows = await cur.fetchall()
            return [dict(row) for row in rows]
        finally:
            await db.close()

    async def get_codes_stats(self) -> dict[str, int]:
        db = await self._connect()
        try:
            result = {}
            for key, query in {
                "total": "SELECT COUNT(*) FROM access_codes",
                "active": "SELECT COUNT(*) FROM access_codes WHERE is_active = 1",
                "used": "SELECT COUNT(*) FROM access_codes WHERE is_used = 1",
                "unused": "SELECT COUNT(*) FROM access_codes WHERE is_used = 0",
                "users_activated": "SELECT COUNT(*) FROM users WHERE is_activated = 1",
            }.items():
                cur = await db.execute(query)
                row = await cur.fetchone()
                result[key] = row[0]
            return result
        finally:
            await db.close()

    async def add_dialog_message(self, telegram_id: int, role: str, content: str) -> None:
        db = await self._connect()
        try:
            await db.execute("""
            INSERT INTO dialog_messages (telegram_id, role, content)
            VALUES (?, ?, ?)
            """, (telegram_id, role, content))
            await db.commit()
        finally:
            await db.close()

    async def get_dialog_messages(self, telegram_id: int, limit: int) -> list[dict[str, str]]:
        db = await self._connect()
        try:
            cur = await db.execute("""
            SELECT role, content
            FROM dialog_messages
            WHERE telegram_id = ?
            ORDER BY id DESC
            LIMIT ?
            """, (telegram_id, limit))
            rows = await cur.fetchall()
            return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]
        finally:
            await db.close()

    async def clear_dialog_messages(self, telegram_id: int) -> None:
        db = await self._connect()
        try:
            await db.execute(
                "DELETE FROM dialog_messages WHERE telegram_id = ?",
                (telegram_id,),
            )
            await db.commit()
        finally:
            await db.close()


repo = Repository(settings.db_path)