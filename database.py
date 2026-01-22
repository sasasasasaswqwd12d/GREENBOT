import sqlite3
import os

def init_db():
    """Инициализирует базу данных и создаёт все таблицы, если их нет"""
    # Убедимся, что папка существует (на случай, если запуск из другой директории)
    db_path = "greenfild.db"

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Таблица: роли проекта (хранит ID ролей по ключам)
    c.execute('''CREATE TABLE IF NOT EXISTS project_roles (
        role_name TEXT PRIMARY KEY,
        role_id INTEGER
    )''')

    # Таблица: логи назначений (админы, лидеры, медиа)
    c.execute('''CREATE TABLE IF NOT EXISTS assignment_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assigner_id INTEGER NOT NULL,      -- кто назначил
        assigned_id INTEGER NOT NULL,      -- кого назначили
        role_type TEXT NOT NULL,           -- 'admin', 'leader', 'movie'
        reason TEXT NOT NULL,              -- причина назначения
        timestamp INTEGER DEFAULT (strftime('%s', 'now'))
    )''')

    # Таблица: глобальные баны (работает на всех серверах проекта)
    c.execute('''CREATE TABLE IF NOT EXISTS global_bans (
        user_id INTEGER PRIMARY KEY,
        reason TEXT NOT NULL,
        banned_by INTEGER NOT NULL,
        expires_at INTEGER                  -- NULL = навсегда, иначе timestamp
    )''')

    # Таблица: предупреждения (warns)
    c.execute('''CREATE TABLE IF NOT EXISTS warns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        guild_id INTEGER NOT NULL,
        moderator_id INTEGER NOT NULL,
        reason TEXT NOT NULL,
        expires_at INTEGER NOT NULL         -- автоматически снимается через N дней
    )''')

    # Таблица: онлайн-статистика (время в голосовых каналах)
    c.execute('''CREATE TABLE IF NOT EXISTS online_time (
        user_id INTEGER,
        guild_id INTEGER,
        last_join INTEGER,                 -- когда зашёл в голосовой канал
        total_seconds INTEGER DEFAULT 0,   -- общее время в секундах
        PRIMARY KEY (user_id, guild_id)
    )''')

    # Таблица: техподдержка (тикеты)
    c.execute('''CREATE TABLE IF NOT EXISTS tech_tickets (
        ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        guild_id INTEGER NOT NULL,
        channel_id INTEGER NOT NULL,
        status TEXT DEFAULT 'open',        -- 'open' или 'closed'
        created_at INTEGER DEFAULT (strftime('%s', 'now'))
    )''')

    conn.commit()
    conn.close()
    print(f"💾 База данных '{db_path}' готова.")
