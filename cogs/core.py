import discord
from discord.ext import commands
import os
import json
from utils.helpers import get_role_id

class Core(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Вызывается при входе участника на сервер"""

        # === 1. Выдача стартовой роли ===
        default_role_id = None

        # Сначала пробуем из .env
        env_role_id = os.getenv("ROLE_DEFAULT_MEMBER")
        if env_role_id and env_role_id.isdigit():
            default_role_id = int(env_role_id)
        else:
            # Если не указано в .env — берём из БД
            default_role_id = get_role_id("default_member")

        if default_role_id:
            role = member.guild.get_role(default_role_id)
            if role:
                try:
                    await member.add_roles(role)
                except discord.Forbidden:
                    print(f"❌ Не удалось выдать роль '{role.name}' пользователю {member} (недостаточно прав)")
                except Exception as e:
                    print(f"❌ Ошибка выдачи роли: {e}")

        # === 2. Отправка приветствия в ЛС ===
        try:
            # Загружаем текст из settings.json
            with open("settings.json", "r", encoding="utf-8") as f:
                settings = json.load(f)

            welcome_msg = settings["welcome_message"]
            social_links = os.getenv("SOCIAL_LINKS", "Соцсети не указаны")
            final_message = welcome_msg.replace("{social_links}", social_links)

            await member.send(final_message)
        except discord.Forbidden:
            # Пользователь закрыл ЛС — игнорируем
            pass
        except FileNotFoundError:
            print("❌ Файл settings.json не найден!")
        except KeyError:
            print("❌ В settings.json отсутствует поле 'welcome_message'")
        except Exception as e:
            print(f"❌ Ошибка отправки приветствия: {e}")

    @discord.app_command.command(name="перезагрузить_приветствие", description="Тестовая команда для владельца")
    @commands.is_owner()
    async def reload_welcome(self, interaction: discord.Interaction):
        """Тестовая команда — отправляет приветствие самому себе"""
        try:
            with open("settings.json", "r", encoding="utf-8") as f:
                settings = json.load(f)
            msg = settings["welcome_message"].replace("{social_links}", os.getenv("SOCIAL_LINKS", ""))
            await interaction.user.send(msg)
            await interaction.response.send_message("✅ Приветствие отправлено в ЛС.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Core(bot))
