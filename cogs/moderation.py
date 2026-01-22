import discord
from discord.ext import commands, tasks
import sqlite3
import time
import aiohttp
import os
from utils.helpers import get_role_id


# === Модальное окно для глобального бана (используется из других Cogs) ===
class GlobalBanModal(discord.ui.Modal, title="🌍 Глобальный бан"):
    def __init__(self):
        super().__init__()
        self.user_id = discord.ui.TextInput(
            label="ID пользователя",
            placeholder="123456789012345678",
            required=True,
            max_length=20
        )
        self.duration = discord.ui.TextInput(
            label="Срок (например: 7d, 0=навсегда)",
            default="0",
            required=True,
            max_length=10
        )
        self.reason = discord.ui.TextInput(
            label="Причина",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=300
        )
        self.add_item(self.user_id)
        self.add_item(self.duration)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("Moderation")
        if not cog:
            await interaction.response.send_message("❌ Модуль модерации недоступен.", ephemeral=True)
            return

        try:
            user_id = int(self.user_id.value.strip())
            user = await interaction.client.fetch_user(user_id)
        except (ValueError, discord.NotFound):
            await interaction.response.send_message("❌ Неверный ID пользователя или пользователь не найден.", ephemeral=True)
            return

        try:
            # Вызываем команду напрямую
            await cog.global_ban(interaction, user, self.duration.value, self.reason.value)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка при бане: {e}", ephemeral=True)


# === Основной Cog модерации ===
class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_expired_warns.start()

    def has_moderator_role(self, user: discord.Member) -> bool:
        """Проверяет, есть ли у пользователя роль модератора"""
        mod_roles = ["chief_admin", "deputy_chief", "chief_curator", "senior_admin", "admin"]
        for role_key in mod_roles:
            role_id = get_role_id(role_key)
            if role_id and role_id in [r.id for r in user.roles]:
                return True
        return False

    def parse_duration(self, s: str) -> int:
        """Преобразует '7d', '2h' в секунды. '0' = навсегда."""
        if s == "0":
            return 0
        unit = s[-1].lower()
        try:
            amount = int(s[:-1])
        except ValueError:
            return 0
        mult = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
        return amount * mult.get(unit, 0)

    async def send_ban_webhook(self, url: str, user: discord.User, moderator: discord.User, reason: str, expires: str):
        """Отправляет уведомление о бане в webhook"""
        async with aiohttp.ClientSession() as session:
            embed = {
                "title": "🌍 Глобальный бан",
                "description": f"**Пользователь:** {user.mention}\n**Модератор:** {moderator.mention}\n**Причина:** {reason}\n**Срок:** {expires}",
                "color": 0xe74c3c,
                "timestamp": discord.utils.utcnow().isoformat()
            }
            payload = {
                "username": "Greenfild Ban Sync",
                "avatar_url": "https://i.imgur.com/5GkzFQl.png",
                "embeds": [embed]
            }
            try:
                await session.post(url, json=payload)
            except Exception as e:
                print(f"Ошибка отправки webhook: {e}")

    @discord.app_command.command(name="глобалбан", description="Забанить пользователя на всех серверах проекта")
    async def global_ban(self, interaction: discord.Interaction, пользователь: discord.User, срок: str = "0", причина: str = "Не указана"):
        if not self.has_moderator_role(interaction.user):
            await interaction.response.send_message("❌ У вас нет прав на выдачу банов.", ephemeral=True)
            return

        seconds = self.parse_duration(срок)
        expires_at = int(time.time()) + seconds if seconds > 0 else None
        expires_str = "навсегда" if expires_at is None else срок

        conn = sqlite3.connect("greenfild.db")
        c = conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO global_bans (user_id, reason, banned_by, expires_at) VALUES (?, ?, ?, ?)",
            (пользователь.id, причина, interaction.user.id, expires_at)
        )
        conn.commit()
        conn.close()

        ban_count = 0
        for guild in self.bot.guilds:
            try:
                await guild.ban(пользователь, reason=f"Глобальный бан: {причина}")
                ban_count += 1
            except discord.Forbidden:
                pass

        webhook_url = os.getenv("BAN_SYNC_WEBHOOK_URL")
        if webhook_url:
            await self.send_ban_webhook(webhook_url, пользователь, interaction.user, причина, expires_str)

        await interaction.response.send_message(
            f"🌍 Пользователь {пользователь.mention} забанен глобально {'навсегда' if expires_at is None else f'на {срок}'}. "
            f"Забанен на {ban_count} серверах.",
            ephemeral=True
        )

    @discord.app_command.command(name="глобалразбан", description="Снять глобальный бан")
    async def global_unban(self, interaction: discord.Interegration, пользователь: discord.User):
        if not self.has_moderator_role(interaction.user):
            await interaction.response.send_message("❌ У вас нет прав на снятие банов.", ephemeral=True)
            return

        conn = sqlite3.connect("greenfild.db")
        c = conn.cursor()
        c.execute("DELETE FROM global_bans WHERE user_id = ?", (пользователь.id,))
        deleted = c.rowcount
        conn.commit()
        conn.close()

        if deleted:
            unban_count = 0
            for guild in self.bot.guilds:
                try:
                    await guild.unban(пользователь)
                    unban_count += 1
                except:
                    pass
            await interaction.response.send_message(
                f"✅ Глобальный бан с {пользователь.mention} снят. Разбанен на {unban_count} серверах.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message("❌ Пользователь не в глобальном бане.", ephemeral=True)

    @discord.app_command.command(name="варн", description="Выдать предупреждение участнику")
    async def warn(self, interaction: discord.Interaction, участник: discord.Member, причина: str = "Не указана"):
        if not self.has_moderator_role(interaction.user):
            await interaction.response.send_message("❌ У вас нет прав на выдачу предупреждений.", ephemeral=True)
            return

        expires_at = int(time.time()) + 7 * 86400  # 7 дней

        conn = sqlite3.connect("greenfild.db")
        c = conn.cursor()
        c.execute(
            "INSERT INTO warns (user_id, guild_id, moderator_id, reason, expires_at) VALUES (?, ?, ?, ?, ?)",
            (участник.id, interaction.guild.id, interaction.user.id, причина, expires_at)
        )
        c.execute(
            "SELECT COUNT(*) FROM warns WHERE user_id = ? AND guild_id = ? AND expires_at > ?",
            (участник.id, interaction.guild.id, int(time.time()))
        )
        active_warns = c.fetchone()[0]
        conn.commit()
        conn.close()

        max_warns = 3
        if active_warns >= max_warns:
            try:
                await interaction.guild.ban(участник, reason=f"Превышено количество предупреждений ({active_warns})")
                await interaction.response.send_message(
                    f"🚫 {участник.mention} забанен за превышение лимита предупреждений ({active_warns}/{max_warns})."
                )
            except discord.Forbidden:
                await interaction.response.send_message(
                    f"⚠️ {участник.mention} получил {active_warns}-й варн, но у бота нет прав на бан."
                )
        else:
            await interaction.response.send_message(
                f"⚠️ {участник.mention} получил предупреждение ({active_warns}/{max_warns}).\nПричина: {причина}"
            )

    @discord.app_command.command(name="варны", description="Посмотреть активные предупреждения участника")
    async def warns(self, interaction: discord.Interaction, участник: discord.Member):
        if not self.has_moderator_role(interaction.user):
            await interaction.response.send_message("❌ У вас нет доступа к этой команде.", ephemeral=True)
            return

        conn = sqlite3.connect("greenfild.db")
        c = conn.cursor()
        c.execute(
            "SELECT reason, expires_at FROM warns WHERE user_id = ? AND guild_id = ? AND expires_at > ?",
            (участник.id, interaction.guild.id, int(time.time()))
        )
        records = c.fetchall()
        conn.close()

        if not records:
            await interaction.response.send_message(f"✅ У {участник.mention} нет активных предупреждений.", ephemeral=True)
            return

        desc = "\n".join(
            f"🔹 `{reason}` (до <t:{exp}:R>)"
            for reason, exp in records
        )
        embed = discord.Embed(
            title=f"⚠️ Предупреждения {участник.display_name}",
            description=desc,
            color=0xe74c3c
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @tasks.loop(hours=1)
    async def check_expired_warns(self):
        """Удаляет просроченные предупреждения (старше 7 дней)"""
        conn = sqlite3.connect("greenfild.db")
        c = conn.cursor()
        now = int(time.time())
        c.execute("DELETE FROM warns WHERE expires_at <= ?", (now,))
        conn.commit()
        conn.close()

    @check_expired_warns.before_loop
    async def before_check_warns(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
