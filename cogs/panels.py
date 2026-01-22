import discord
from discord.ext import commands
from utils.helpers import get_role_id

class Panels(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @discord.app_command.command(name="панель_главная", description="Главная панель управления (только для Руководства и Команды)")
    async def main_panel(self, interaction: discord.Interaction):
        """Главная панель — полный контроль над проектом"""
        if not self.has_leadership_access(interaction.user):
            await interaction.response.send_message(
                "❌ Доступ запрещён.\n"
                "Эта панель доступна только:\n"
                "• Руководству проекта\n"
                "• Команде проекта",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🛡️ Главная панель Greenfild",
            description="Полный контроль над проектом",
            color=0x9b59b6,
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url="attachment://logo.png")
        embed.add_field(name="🔧 Управление", value="• Настройка ролей\n• Глобальные баны\n• Статистика проекта", inline=False)
        embed.add_field(name="👥 Персонал", value="• Назначение руководителей\n• Аудит назначений", inline=False)

        # Попытка прикрепить логотип (если есть)
        file = None
        try:
            file = discord.File("assets/logo.png", filename="logo.png")
        except FileNotFoundError:
            pass

        view = MainPanelView()
        if file:
            await interaction.response.send_message(embed=embed, view=view, file=file, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    def has_leadership_access(self, user: discord.Member) -> bool:
        """Проверяет, есть ли у пользователя роль Руководства или Команды проекта"""
        leadership_id = get_role_id("leadership")
        team_id = get_role_id("project_team")

        user_role_ids = [r.id for r in user.roles]
        return (leadership_id in user_role_ids) or (team_id in user_role_ids)

class MainPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="⚙️ Настроить роли", style=discord.ButtonStyle.danger, emoji="⚙️")
    async def configure_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.assignment import RoleConfigModal
        await interaction.response.send_modal(RoleConfigModal())

    @discord.ui.button(label="📊 Статистика проекта", style=discord.ButtonStyle.primary, emoji="📊")
    async def project_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Пример статистики
        total_bans = 0
        total_assignments = 0
        active_guilds = len(interaction.client.guilds)

        # Получаем данные из БД
        import sqlite3
        conn = sqlite3.connect("greenfild.db")
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM global_bans")
        total_bans = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM assignment_logs")
        total_assignments = c.fetchone()[0]
        conn.close()

        embed = discord.Embed(
            title="📈 Статистика Greenfild Project",
            color=0x2ecc71,
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="🌍 Серверов", value=active_guilds, inline=True)
        embed.add_field(name="🚫 Глобальных банов", value=total_bans, inline=True)
        embed.add_field(name="✅ Назначений", value=total_assignments, inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🔍 Аудит назначений", style=discord.ButtonStyle.secondary, emoji="🔍")
    async def audit_assignments(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.assignment import Assignment
        cog = interaction.client.get_cog("Assignment")
        if cog:
            await cog.assignment_stats(interaction)
        else:
            await interaction.response.send_message("❌ Модуль назначений недоступен.", ephemeral=True)

class RoleConfigModal(discord.ui.Modal, title="⚙️ Настройка ролей проекта"):
    def __init__(self):
        super().__init__()
        self.role_name = discord.ui.TextInput(
            label="Ключ роли (например: leadership)",
            placeholder="leadership, project_team, chief_admin...",
            required=True,
            max_length=30
        )
        self.role_id = discord.ui.TextInput(
            label="ID роли в Discord",
            placeholder="123456789012345678",
            required=True,
            max_length=20
        )
        self.add_item(self.role_name)
        self.add_item(self.role_id)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            role_id = int(self.role_id.value.strip())
        except ValueError:
            await interaction.response.send_message("❌ Неверный ID роли.", ephemeral=True)
            return

        role = interaction.guild.get_role(role_id)
        if not role:
            await interaction.response.send_message("❌ Роль не найдена на этом сервере.", ephemeral=True)
            return

        # Сохраняем в БД
        import sqlite3
        conn = sqlite3.connect("greenfild.db")
        c = conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO project_roles (role_name, role_id) VALUES (?, ?)",
            (self.role_name.value.strip().lower(), role_id)
        )
        conn.commit()
        conn.close()

        await interaction.response.send_message(
            f"✅ Роль `{role.name}` привязана к ключу `{self.role_name.value.strip().lower()}`.",
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(Panels(bot))
