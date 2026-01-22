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
            synced = await self.bot.tree.sync()
            embed = discord.Embed(
                title="✅ Синхронизация завершена",
                description=f"Глобально синхронизировано **{len(synced)}** slash-команд.",
                color=0x2ecc71
            )
            await ctx.send(embed=embed)
            print(f"🔄 Синхронизировано {len(synced)} команд глобально.")
        except Exception as e:
            embed = discord.Embed(
                title="❌ Ошибка синхронизации",
                description=str(e),
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            print(f"❌ Ошибка: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(SyncCommands(bot))
