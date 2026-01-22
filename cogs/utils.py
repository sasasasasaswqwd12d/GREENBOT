import discord
from discord.ext import commands

class SyncCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="sync")
    @commands.is_owner()
    async def sync_prefix_command(self, ctx: commands.Context):
        """
        !sync — глобальная синхронизация slash-команд.
        Доступна только владельцу бота.
        """
        try:
            synced = await self.bot.tree.sync()  # Глобальная синхронизация
            await ctx.send(f"Успешно синхронизировано **{len(synced)}** slash-команд глобально.")
            print(f"🔄 Синхронизировано {len(synced)} команд глобально.")
        except Exception as e:
            await ctx.send(f"Ошибка синхронизации: {e}")
            print(f"❌ Ошибка: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(SyncCommands(bot))
