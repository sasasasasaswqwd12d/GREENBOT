import sqlite3
import discord

def get_role_id(role_name: str) -> int | None:
    """
    Получает ID роли из базы данных по её ключу.

    Примеры role_name:
        'leadership'         → Руководство проекта
        'project_team'       → Команда проекта
        'chief_admin'        → Chief Administrator
        'deputy_chief'       → Deputy Chief Administrator
        'chief_curator'      → Chief Curator
        'admin'              → Administrator
        'leader'             → Leader (роль при назначении)
        'movie'              → Movie (роль медиа)
        'default_member'     → Игрок (при входе)
    """
    try:
        conn = sqlite3.connect("greenfild.db")
        c = conn.cursor()
        c.execute("SELECT role_id FROM project_roles WHERE role_name = ?", (role_name,))
        row = c.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception as e:
        print(f"❌ Ошибка в get_role_id('{role_name}'): {e}")
        return None

def has_management_access(user: discord.Member) -> bool:
    """
    Проверяет, имеет ли пользователь доступ к панелям управления.

    Доступ имеют:
        - Руководство проекта
        - Команда проекта
        - Chief Administrator
        - Deputy Chief Administrator
        - Chief Curator
    """
    allowed_roles = [
        "leadership",
        "project_team",
        "chief_admin",
        "deputy_chief",
        "chief_curator"
    ]

    for role_key in allowed_roles:
        role_id = get_role_id(role_key)
        if role_id and role_id in [r.id for r in user.roles]:
            return True
    return False

def log_to_channel(guild: discord.Guild, message: str):
    """
    Отправляет сообщение в канал логов (если указан в .env или БД).
    Пока заглушка — можно расширить.
    """
    pass
