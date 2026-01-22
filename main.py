import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from database import init_db

# Загружаем переменные окружения
load_dotenv()

# Настраиваем intents (разрешения бота)
intents = discord.Intents.default()
intents.members = True      # Для отслеживания входа/выхода участников
intents.message_content = True  # Для работы с сообщениями (если нужно)

# Создаём бота с префиксом (для совместимости) и slash-командами
bot = commands.Bot(command_prefix="gf!", intents=intents)

@bot.event
async def on_ready():
    """Вызывается при успешном запуске бота"""
    print(f"{bot.user} успешно запущен!")
    print(f"Подключено к {len(bot.guilds)} серверам")
    print(f"Имя проекта: {os.getenv('PROJECT_NAME', 'Greenfild Project')}")

    # Синхронизируем slash-команды со всеми серверами
    try:
        await bot.tree.sync()
        print("бот синхронизировался")
    except Exception as e:
        print(f"Ошибка синхронизации команд: {e}")

    # Инициализируем базу данных
    init_db()
    print("База данных создана")

# Автоматическая загрузка всех Cogs (модулей)
cog_files = [
    "core",          # Приветствие, роль при входе
    "panels",        # Панели управления
    "assignment",    # Назначения, статистика назначений
    "moderation",    # Баны, предупреждения
    "stats"          # Онлайн, статистика
]

for cog in cog_files:
    try:
        bot.load_extension(f"cogs.{cog}")
        print(f"📦 Модуль cogs.{cog} загружен")
    except Exception as e:
        print(f"❌ Ошибка загрузки cogs.{cog}: {e}")

# Запуск бота
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ ОШИБКА: DISCORD_TOKEN не найден в .env!")
        print("   Убедитесь, что файл .env существует и содержит токен.")
        exit(1)

    bot.run(token)
