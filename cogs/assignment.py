import discord
from discord.ext import commands
import sqlite3
from utils.helpers import get_role_id, has_management_access

class Assignment(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @discord.app_command.command(name="панель_управления", description="Панель для назначений и модерации")
    async def management_panel(self, interaction: discord.Interaction):
        """Обычная панель управления для Chief Admin, Deputy Chief и Chief Curator"""
        if not has_management_access(interaction.user):
            await interaction.response.send_message("❌ У вас нет доступа к этой панели.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🛠️ Панель управления",
            description="Выберите действие:",
            color=0x3498db
        )
        view = ManagementPanelView(self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.app_command.command(name="статистика_назначений", description="Показать историю всех назначений")
    async def assignment_stats(self, interaction: discord.Interaction):
        """Показывает последние 20 назначений"""
        if not has_management_access(interaction.user):
            await interaction.response.send_message("❌ У вас нет доступа к этой команде.", ephemeral=True)
            return

        conn = sqlite3.connect("greenfild.db")
        c = conn.cursor()
        c.execute("""
            SELECT assigner_id, assigned_id, role_type, reason, timestamp
            FROM assignment_logs
            ORDER BY timestamp DESC
            LIMIT 20
        """)
        records = c.fetchall()
        conn.close()

        if not records:
            await interaction.response.send_message("📭 Нет записей о назначениях.", ephemeral=True)
            return

        lines = []
        for assigner_id, assigned_id, role_type, reason, ts in records:
            emoji = {"admin": "👤", "leader": "👑", "movie": "🎥"}.get(role_type, "📌")
            line = f"{emoji} <@{assigner_id}> → <@{assigned_id}> | {reason} (<t:{ts}:R>)"
            lines.append(line)

        embed = discord.Embed(
            title="📊 Статистика назначений",
            description="\n".join(lines),
            color=0x2ecc71,
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text="Последние 20 назначений")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ManagementPanelView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="👤 Назначить админа", style=discord.ButtonStyle.primary, emoji="👤")
    async def assign_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AssignModal(self.bot, "admin", "администратора"))

    @discord.ui.button(label="👑 Назначить лидера", style=discord.ButtonStyle.success, emoji="👑")
    async def assign_leader(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AssignModal(self.bot, "leader", "лидера"))

    @discord.ui.button(label="🎥 Назначить медиа", style=discord.ButtonStyle.secondary, emoji="🎥")
    async def assign_movie(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AssignModal(self.bot, "movie", "медиа"))

#    @discord.ui.button(label="🔨 Глобальный бан", style=discord.ButtonStyle.danger, emoji="🔨")
#    async def global_ban_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
#        from cogs.moderation import GlobalBanModal
#        await interaction.response.send_modal(GlobalBanModal())

class AssignModal(discord.ui.Modal):
    def __init__(self, bot, role_type: str, role_name: str):
        super().__init__(title=f"Назначить {role_name}")
        self.bot = bot
        self.role_type = role_type
        self.role_name = role_name

        self.user_id = discord.ui.TextInput(
            label="ID пользователя",
            placeholder="123456789012345678",
            required=True,
            max_length=20
        )
        self.reason = discord.ui.TextInput(
            label="Причина назначения",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=300
        )
        self.add_item(self.user_id)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_id = int(self.user_id.value.strip())
        except ValueError:
            await interaction.response.send_message("❌ Неверный ID пользователя.", ephemeral=True)
            return

        member = interaction.guild.get_member(user_id)
        if not member:
            await interaction.response.send_message("❌ Пользователь не найден на этом сервере.", ephemeral=True)
            return

        # Получаем роль из БД
        role_id = get_role_id(self.role_type)
        if not role_id:
            await interaction.response.send_message(f"❌ Роль '{self.role_name}' не настроена. Обратитесь к владельцу бота.", ephemeral=True)
            return

        role = interaction.guild.get_role(role_id)
        if not role:
            await interaction.response.send_message(f"❌ Роль '{self.role_name}' удалена с сервера.", ephemeral=True)
            return

        # Выдаём роль
        try:
            await member.add_roles(role)
        except discord.Forbidden:
            await interaction.response.send_message("❌ У бота недостаточно прав для выдачи роли.", ephemeral=True)
            return

        # Логируем в БД
        conn = sqlite3.connect("greenfild.db")
        c = conn.cursor()
        c.execute(
            "INSERT INTO assignment_logs (assigner_id, assigned_id, role_type, reason) VALUES (?, ?, ?, ?)",
            (interaction.user.id, user_id, self.role_type, self.reason.value)
        )
        conn.commit()
        conn.close()

        # Отправляем уведомление в ЛС
        try:
            await member.send(
                f"✅ Вы назначены **{self.role_name}** на сервере **{interaction.guild.name}**.\n"
                f"Причина: {self.reason.value}"
            )
        except discord.Forbidden:
            pass  # Не удалось отправить ЛС — игнорируем

        await interaction.response.send_message(
            f"✅ {member.mention} успешно назначен {self.role_name}.",
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(Assignment(bot))
