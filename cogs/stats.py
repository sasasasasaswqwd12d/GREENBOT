import discord
from discord.ext import commands, tasks
import sqlite3
import time
from utils.helpers import get_role_id


# === Вспомогательный View для техподдержки ===
class TechTicketView(discord.ui.View):
    def __init__(self, channel_id: int):
        super().__init__(timeout=None)
        self.channel_id = channel_id

    @discord.ui.button(label="✅ Принять заявку", style=discord.ButtonStyle.green, emoji="✅")
    async def accept_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        if not channel:
            return

        # Получаем ID автора заявки
        author_id = None
        conn = sqlite3.connect("greenfild.db")
        c = conn.cursor()
        c.execute("SELECT user_id FROM tech_tickets WHERE channel_id = ?", (self.channel_id,))
        row = c.fetchone()
        conn.close()

        if row:
            author_id = row[0]

        # Новые права канала
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        # Добавляем автора и принимающего
        if author_id:
            author = interaction.guild.get_member(author_id)
            if author:
                overwrites[author] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        overwrites[interaction.user] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        await channel.edit(overwrites=overwrites)
        await interaction.response.send_message("✅ Заявка принята. Другие техники удалены из канала.")

    @discord.ui.button(label="🔒 Закрыть", style=discord.ButtonStyle.red, emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.delete(reason="Заявка закрыта")


# === Основной Cog ===
class Stats(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before, after):
        """Отслеживает онлайн в голосовых каналах"""
        if member.bot:
            return

        conn = sqlite3.connect("greenfild.db")
        c = conn.cursor()

        # Покинул голосовой канал
        if before.channel is not None and after.channel is None:
            c.execute(
                "SELECT last_join FROM online_time WHERE user_id = ? AND guild_id = ?",
                (member.id, member.guild.id)
            )
            row = c.fetchone()
            if row and row[0]:
                total_time = int(time.time()) - row[0]
                c.execute(
                    "UPDATE online_time SET total_seconds = total_seconds + ? WHERE user_id = ? AND guild_id = ?",
                    (total_time, member.id, member.guild.id)
                )

        # Вошёл в голосовой канал
        elif before.channel is None and after.channel is not None:
            c.execute(
                "INSERT OR REPLACE INTO online_time (user_id, guild_id, last_join, total_seconds) VALUES (?, ?, ?, COALESCE((SELECT total_seconds FROM online_time WHERE user_id = ? AND guild_id = ?), 0))",
                (member.id, member.guild.id, int(time.time()), member.id, member.guild.id)
            )

        conn.commit()
        conn.close()

    @discord.app_command.command(name="статистика", description="Показать статистику сервера")
    async def stats(self, interaction: discord.Interaction):
        conn = sqlite3.connect("greenfild.db")
        c = conn.cursor()

        # Глобальные баны
        c.execute("SELECT COUNT(*) FROM global_bans")
        ban_count = c.fetchone()[0] or 0

        # Активные варны
        c.execute("SELECT COUNT(*) FROM warns WHERE expires_at > ?", (int(time.time()),))
        warn_count = c.fetchone()[0] or 0

        # Назначения
        c.execute("SELECT COUNT(*) FROM assignment_logs")
        assign_count = c.fetchone()[0] or 0

        # Онлайн в голосовых
        voice_members = set()
        for vc in interaction.guild.voice_channels:
            voice_members.update(vc.members)
        online_count = len([m for m in voice_members if not m.bot])

        # Общий онлайн (часы)
        c.execute("SELECT SUM(total_seconds) FROM online_time WHERE guild_id = ?", (interaction.guild.id,))
        total_seconds = c.fetchone()[0] or 0
        hours = total_seconds // 3600

        conn.close()

        embed = discord.Embed(
            title="📊 Статистика Greenfild Project",
            color=0x3498db,
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="🌍 Серверов", value=len(self.bot.guilds), inline=True)
        embed.add_field(name="🚫 Глобальных банов", value=ban_count, inline=True)
        embed.add_field(name="⚠️ Активных варнов", value=warn_count, inline=True)
        embed.add_field(name="✅ Назначений", value=assign_count, inline=True)
        embed.add_field(name="🔊 Онлайн (голос)", value=online_count, inline=True)
        embed.add_field(name="⏳ Общий онлайн", value=f"{hours} ч", inline=True)
        embed.set_footer(text="Обновлено сейчас")

        await interaction.response.send_message(embed=embed)

    @discord.app_command.command(name="техзаявка", description="Создать заявку в техподдержку")
    async def tech_ticket(self, interaction: discord.Interaction):
        tech_role_id = get_role_id("tech_support")
        if not tech_role_id:
            await interaction.response.send_message(
                "❌ Роль техподдержки не настроена. Используйте `/панель_главная` → «Настроить роли».",
                ephemeral=True
            )
            return

        tech_role = interaction.guild.get_role(tech_role_id)
        if not tech_role:
            await interaction.response.send_message(
                "❌ Роль техподдержки удалена с сервера.",
                ephemeral=True
            )
            return

        # Создаём категорию, если нет
        category = discord.utils.get(interaction.guild.categories, name="🔧 Техподдержка")
        if not category:
            category = await interaction.guild.create_category("🔧 Техподдержка")

        # Права канала
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            tech_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        # Создаём канал
        channel = await interaction.guild.create_text_channel(
            name=f"тех-{interaction.user.name}",
            category=category,
            overwrites=overwrites
        )

        # Сохраняем в БД
        conn = sqlite3.connect("greenfild.db")
        c = conn.cursor()
        c.execute(
            "INSERT INTO tech_tickets (user_id, guild_id, channel_id) VALUES (?, ?, ?)",
            (interaction.user.id, interaction.guild.id, channel.id)
        )
        conn.commit()
        conn.close()

        # Отправляем сообщение
        embed = discord.Embed(
            title="📩 Новая заявка в техподдержку",
            description=f"Пользователь: {interaction.user.mention}\nОпишите вашу проблему.",
            color=0x3498db
        )
        view = TechTicketView(channel.id)
        await channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"✅ Канал создан: {channel.mention}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Stats(bot))
