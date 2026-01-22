import discord
from discord.ext import commands
import sqlite3
from utils.helpers import get_role_id

def has_leadership_access(user: discord.Member) -> bool:
    """Проверяет доступ к главной панели"""
    leadership_id = get_role_id("leadership")
    team_id = get_role_id("project_team")
    user_roles = [r.id for r in user.roles]
    return (leadership_id in user_roles) or (team_id in user_roles)

class Panels(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @discord.app_command.command(name="панель_главная", description="Главная панель управления (только для Руководства и Команды)")
    async def main_panel(self, interaction: discord.Interaction):
        if not has_leadership_access(interaction.user):
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
        embed.add_field(name="🔧 Управление", value="• Настройка ролей\n• Глобальные баны\n• Статистика проекта", inline=False)
        embed.add_field(name="👥 Персонал", value="• Назначение руководителей\n• Аудит назначений", inline=False)

        view = MainPanelView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Panels(bot))


class MainPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="⚙️ Настроить роли", style=discord.ButtonStyle.danger, emoji="⚙️")
    async def configure_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = discord.ui.Modal(title="⚙️ Настройка ролей проекта")

        role_name = discord.ui.TextInput(
            label="Ключ роли (например: leadership)",
            placeholder="leadership, project_team, chief_admin...",
            required=True,
            max_length=30
        )
        role_id = discord.ui.TextInput(
            label="ID роли в Discord",
            placeholder="123456789012345678",
            required=True,
            max_length=20
        )

        modal.add_item(role_name)
        modal.add_item(role_id)

        async def on_submit(interaction: discord.Interaction):
            try:
                r_id = int(role_id.value.strip())
            except ValueError:
                await interaction.response.send_message("❌ Неверный ID роли.", ephemeral=True)
                return

            role = interaction.guild.get_role(r_id)
            if not role:
                await interaction.response.send_message("❌ Роль не найдена на этом сервере.", ephemeral=True)
                return

            conn = sqlite3.connect("greenfild.db")
            c = conn.cursor()
            c.execute(
                "INSERT OR REPLACE INTO project_roles (role_name, role_id) VALUES (?, ?)",
                (role_name.value.strip().lower(), r_id)
            )
            conn.commit()
            conn.close()

            await interaction.response.send_message(
                f"✅ Роль `{role.name}` привязана к ключу `{role_name.value.strip().lower()}`.",
                ephemeral=True
            )

        modal.on_submit = on_submit
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="📊 Статистика проекта", style=discord.ButtonStyle.primary, emoji="📊")
    async def project_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
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
        embed.add_field(name="🌍 Серверов", value=len(interaction.client.guilds), inline=True)
        embed.add_field(name="🚫 Глобальных банов", value=total_bans, inline=True)
        embed.add_field(name="✅ Назначений", value=total_assignments, inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🔍 Аудит назначений", style=discord.ButtonStyle.secondary, emoji="🔍")
    async def audit_assignments(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("Assignment")
        if cog and hasattr(cog, 'assignment_stats'):
            await cog.assignment_stats(interaction)
        else:
            await interaction.response.send_message("❌ Модуль назначений недоступен.", ephemeral=True)
