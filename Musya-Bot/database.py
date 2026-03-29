import aiosqlite
import time
from datetime import datetime, timedelta

DB_PATH = "musya_bot.db"


async def init_db():
    """Инициализация базы данных — создание всех таблиц"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица пользователей (уровни и EXP)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER,
                guild_id INTEGER,
                exp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 0,
                total_messages INTEGER DEFAULT 0,
                total_voice_minutes INTEGER DEFAULT 0,
                last_exp_time REAL DEFAULT 0,
                joined_voice_at REAL DEFAULT 0,
                PRIMARY KEY (user_id, guild_id)
            )
        """)

        # Таблица предупреждений
        await db.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                guild_id INTEGER,
                moderator_id INTEGER,
                reason TEXT,
                timestamp REAL
            )
        """)

        # Таблица модерационных действий (для аналитики)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS mod_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT,
                user_id INTEGER,
                moderator_id INTEGER,
                guild_id INTEGER,
                reason TEXT,
                timestamp REAL
            )
        """)

        # Таблица reaction roles
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reaction_roles (
                message_id INTEGER,
                emoji TEXT,
                role_id INTEGER,
                guild_id INTEGER,
                channel_id INTEGER,
                PRIMARY KEY (message_id, emoji)
            )
        """)

        # Таблица статистики сервера (для аналитики)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS server_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                date TEXT,
                messages_count INTEGER DEFAULT 0,
                members_joined INTEGER DEFAULT 0,
                members_left INTEGER DEFAULT 0,
                voice_minutes INTEGER DEFAULT 0,
                UNIQUE(guild_id, date)
            )
        """)

        # Таблица статистики каналов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS channel_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER,
                guild_id INTEGER,
                date TEXT,
                messages_count INTEGER DEFAULT 0,
                UNIQUE(channel_id, date)
            )
        """)

        await db.commit()


# ===== ФУНКЦИИ ДЛЯ СИСТЕМЫ УРОВНЕЙ =====

async def get_user(user_id: int, guild_id: int) -> dict:
    """Получить данные пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id)
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None


async def create_user(user_id: int, guild_id: int):
    """Создать пользователя если не существует"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, guild_id) VALUES (?, ?)",
            (user_id, guild_id)
        )
        await db.commit()


async def add_exp(user_id: int, guild_id: int, exp: int) -> dict:
    """Добавить EXP пользователю. Возвращает данные пользователя"""
    await create_user(user_id, guild_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE users SET exp = exp + ?, last_exp_time = ?
               WHERE user_id = ? AND guild_id = ?""",
            (exp, time.time(), user_id, guild_id)
        )
        await db.commit()
    return await get_user(user_id, guild_id)


async def set_level(user_id: int, guild_id: int, level: int):
    """Установить уровень"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET level = ? WHERE user_id = ? AND guild_id = ?",
            (level, user_id, guild_id)
        )
        await db.commit()


async def increment_messages(user_id: int, guild_id: int):
    """Увеличить счётчик сообщений"""
    await create_user(user_id, guild_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE users SET total_messages = total_messages + 1
               WHERE user_id = ? AND guild_id = ?""",
            (user_id, guild_id)
        )
        await db.commit()


async def add_voice_minutes(user_id: int, guild_id: int, minutes: int):
    """Добавить минуты в войсе"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE users SET total_voice_minutes = total_voice_minutes + ?
               WHERE user_id = ? AND guild_id = ?""",
            (minutes, user_id, guild_id)
        )
        await db.commit()


async def set_voice_join(user_id: int, guild_id: int):
    """Записать время входа в войс"""
    await create_user(user_id, guild_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET joined_voice_at = ? WHERE user_id = ? AND guild_id = ?",
            (time.time(), user_id, guild_id)
        )
        await db.commit()


async def clear_voice_join(user_id: int, guild_id: int):
    """Очистить время входа в войс"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET joined_voice_at = 0 WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id)
        )
        await db.commit()


async def get_leaderboard(guild_id: int, limit: int = 10) -> list:
    """Получить таблицу лидеров"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT * FROM users WHERE guild_id = ?
               ORDER BY exp DESC LIMIT ?""",
            (guild_id, limit)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def set_exp(user_id: int, guild_id: int, exp: int):
    """Установить точное количество EXP"""
    await create_user(user_id, guild_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET exp = ? WHERE user_id = ? AND guild_id = ?",
            (exp, user_id, guild_id)
        )
        await db.commit()


# ===== ФУНКЦИИ ДЛЯ ПРЕДУПРЕЖДЕНИЙ =====

async def add_warning(user_id: int, guild_id: int, moderator_id: int, reason: str):
    """Добавить предупреждение"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO warnings (user_id, guild_id, moderator_id, reason, timestamp)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, guild_id, moderator_id, reason, time.time())
        )
        await db.commit()


async def get_warnings(user_id: int, guild_id: int) -> list:
    """Получить предупреждения пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM warnings WHERE user_id = ? AND guild_id = ? ORDER BY timestamp DESC",
            (user_id, guild_id)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def remove_warning(warning_id: int, guild_id: int) -> bool:
    """Удалить предупреждение по ID"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM warnings WHERE id = ? AND guild_id = ?",
            (warning_id, guild_id)
        )
        await db.commit()
        return cursor.rowcount > 0


async def clear_warnings(user_id: int, guild_id: int):
    """Очистить все предупреждения пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM warnings WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id)
        )
        await db.commit()


# ===== ФУНКЦИИ ДЛЯ МОДЕРАЦИОННЫХ ДЕЙСТВИЙ =====

async def log_mod_action(action_type: str, user_id: int, moderator_id: int,
                         guild_id: int, reason: str = None):
    """Логировать модерационное действие"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO mod_actions (action_type, user_id, moderator_id, guild_id, reason, timestamp)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (action_type, user_id, moderator_id, guild_id, reason, time.time())
        )
        await db.commit()


async def get_mod_actions(guild_id: int, limit: int = 20) -> list:
    """Получить последние модерационные действия"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT * FROM mod_actions WHERE guild_id = ?
               ORDER BY timestamp DESC LIMIT ?""",
            (guild_id, limit)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_mod_stats(guild_id: int, days: int = 30) -> dict:
    """Получить статистику модерации за N дней"""
    since = time.time() - (days * 86400)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT action_type, COUNT(*) as count FROM mod_actions
               WHERE guild_id = ? AND timestamp > ?
               GROUP BY action_type""",
            (guild_id, since)
        )
        rows = await cursor.fetchall()
        return {row['action_type']: row['count'] for row in rows}


# ===== ФУНКЦИИ ДЛЯ REACTION ROLES =====

async def add_reaction_role(message_id: int, emoji: str, role_id: int,
                            guild_id: int, channel_id: int):
    """Добавить reaction role"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR REPLACE INTO reaction_roles
               (message_id, emoji, role_id, guild_id, channel_id)
               VALUES (?, ?, ?, ?, ?)""",
            (message_id, emoji, role_id, guild_id, channel_id)
        )
        await db.commit()


async def get_reaction_role(message_id: int, emoji: str) -> dict:
    """Получить reaction role"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM reaction_roles WHERE message_id = ? AND emoji = ?",
            (message_id, emoji)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_reaction_roles_for_message(message_id: int) -> list:
    """Получить все reaction roles для сообщения"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM reaction_roles WHERE message_id = ?",
            (message_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def remove_reaction_role(message_id: int, emoji: str):
    """Удалить reaction role"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM reaction_roles WHERE message_id = ? AND emoji = ?",
            (message_id, emoji)
        )
        await db.commit()


# ===== ФУНКЦИИ ДЛЯ СТАТИСТИКИ СЕРВЕРА =====

async def increment_daily_messages(guild_id: int, channel_id: int = None):
    """Увеличить счётчик сообщений за день"""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO server_stats (guild_id, date, messages_count)
               VALUES (?, ?, 1)
               ON CONFLICT(guild_id, date)
               DO UPDATE SET messages_count = messages_count + 1""",
            (guild_id, today)
        )
        if channel_id:
            await db.execute(
                """INSERT INTO channel_stats (channel_id, guild_id, date, messages_count)
                   VALUES (?, ?, ?, 1)
                   ON CONFLICT(channel_id, date)
                   DO UPDATE SET messages_count = messages_count + 1""",
                (channel_id, guild_id, today)
            )
        await db.commit()


async def increment_daily_join(guild_id: int):
    """Увеличить счётчик присоединившихся за день"""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO server_stats (guild_id, date, members_joined)
               VALUES (?, ?, 1)
               ON CONFLICT(guild_id, date)
               DO UPDATE SET members_joined = members_joined + 1""",
            (guild_id, today)
        )
        await db.commit()


async def increment_daily_leave(guild_id: int):
    """Увеличить счётчик ушедших за день"""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO server_stats (guild_id, date, members_left)
               VALUES (?, ?, 1)
               ON CONFLICT(guild_id, date)
               DO UPDATE SET members_left = members_left + 1""",
            (guild_id, today)
        )
        await db.commit()


async def get_server_stats(guild_id: int, days: int = 7) -> list:
    """Получить статистику сервера за N дней"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT * FROM server_stats
               WHERE guild_id = ? AND date >= date('now', ?)
               ORDER BY date ASC""",
            (guild_id, f'-{days} days')
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_top_channels(guild_id: int, days: int = 7, limit: int = 10) -> list:
    """Получить топ каналов по сообщениям"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT channel_id, SUM(messages_count) as total
               FROM channel_stats
               WHERE guild_id = ? AND date >= date('now', ?)
               GROUP BY channel_id
               ORDER BY total DESC LIMIT ?""",
            (guild_id, f'-{days} days', limit)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_total_users_count(guild_id: int) -> int:
    """Получить количество пользователей в БД"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM users WHERE guild_id = ?",
            (guild_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0