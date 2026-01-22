import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv
from database import init_db

load_dotenv()

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="gf!", intents=intents)

async def load_cogs():
    cog_files = ["core", "panels", "assignment", "moderation", "stats"]
    for cog in cog_files:
        try:
            await bot.load_extension(f"cogs.{cog}")
            print(f"📦 Модуль cogs.{cog} загружен")
        except Exception as e:
            print(f"❌ Ошибка загрузки cogs.{cog}: {e}")

@bot.event
async def on_ready():
    print(f"🟢 {bot.user} успешно запущен!")
    print(f"✅ Подключено к {len(bot.guilds)} серверам")
    print(f"🔗 Имя проекта: {os.getenv('PROJECT_NAME', 'Greenfild Project')}")

    try:
        await bot.tree.sync()
        print("🔄 Slash-команды зарегистрированы!")
    except Exception as e:
        print(f"❌ Ошибка синхронизации команд: {e}")

    init_db()
    print("💾 База данных инициализирована!")

async def main():
    await load_cogs()
    await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ ОШИБКА: DISCORD_TOKEN не найден в .env!")
        exit(1)
    asyncio.run(main())
