import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv
from database import init_db

# Загрузка настроек
load_dotenv()

# Настройка бота
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# === Встроенная команда синхронизации ===
@bot.command(name="sync")
@commands.is_owner()
async def sync_commands(ctx):
    """
    !sync — глобальная синхронизация slash-команд.
    Доступна только владельцу бота (OWNER_ID в .env).
    """
    try:
        synced = await bot.tree.sync()
        embed = discord.Embed(
            title="✅ Синхронизация завершена",
            description=f"Глобально зарегистрировано **{len(synced)}** slash-команд.",
            color=0x2ecc71
        )
        await ctx.send(embed=embed)
        print(f"🔄 Успешно синхронизировано {len(synced)} команд.")
    except Exception as e:
        embed = discord.Embed(
            title="❌ Ошибка синхронизации",
            description=str(e),
            color=0xe74c3c
        )
        await ctx.send(embed=embed)
        print(f"❌ Ошибка: {e}")

# === Загрузка Cogs ===
async def load_cogs():
    cog_files = ["core", "panels", "assignment", "moderation", "stats"]
    for cog in cog_files:
        try:
            await bot.load_extension(f"cogs.{cog}")
            print(f"✅ УСПЕХ: cogs.{cog} загружен")
        except Exception as e:
            print(f"❌ ОШИБКА загрузки cogs.{cog}: {type(e).__name__}: {e}")

# === События ===
@bot.event
async def on_ready():
    print(f"🟢 {bot.user} успешно запущен!")
    print(f"✅ Подключено к {len(bot.guilds)} серверам")
    init_db()
    print("💾 База данных инициализирована!")

# === Запуск ===
async def main():
    await load_cogs()
    await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ DISCORD_TOKEN не найден в .env!")
        exit(1)
    asyncio.run(main())
