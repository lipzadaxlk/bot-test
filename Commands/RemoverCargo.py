import disnake
from disnake.ext import commands
from disnake.ui import Container, TextDisplay
import json

from Functions.CarregarEmojis import (
    check,
    cancelar,
    carregarAnimado,
)

# Placeholder for permission checking function
# In a real scenario, you'd likely import this from Functions.VerificarPerms
def verificar_permissao(user_id):
    # For now, let's just allow everyone for testing
    return True

def load_primary_color():
    try:
        with open("Database/Configuracoes.json", "r") as f:
            config_db = json.load(f)
            primary_color_str = config_db.get("Cores", {}).get("Color_Primary", "16777215") # Default to white if not found
            return disnake.Colour(int(primary_color_str))
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        return disnake.Colour(16777215) # Fallback to white if file not found or invalid

class RemoveRoleCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(
        name="remover",
        description="Comandos para remover elementos."
    )
    async def remover(self, inter: disnake.ApplicationCommandInteraction):
        pass # This is a group command, it will have subcommands

    @remover.sub_command_group(
        name="cargo",
        description="Gerencia a remoção de cargos."
    )
    async def cargo(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @cargo.sub_command(
        name="usuario",
        description="Remove um cargo de um usuário específico."
    )
    async def usuario(
        self,
        inter: disnake.ApplicationCommandInteraction,
        role: disnake.Role = commands.Param(description="O cargo a ser removido do usuário."),
        user: disnake.Member = commands.Param(description="O usuário para remover o cargo.")
    ):
        await inter.response.send_message(content=f"{carregarAnimado} Carregando Informações...", ephemeral=True)

        primary_color = load_primary_color()

        if not verificar_permissao(inter.user.id):
            error_container = Container(TextDisplay(f"{cancelar} Você não tem permissão para usar este comando."), accent_colour=primary_color)
            return await inter.edit_original_response(components=[error_container], content="")

        # Check if the bot has permissions to manage roles
        if not inter.guild.me.guild_permissions.manage_roles:
            error_container = Container(TextDisplay(f"{cancelar} Eu não tenho permissão para gerenciar cargos neste servidor."), accent_colour=primary_color)
            return await inter.edit_original_response(components=[error_container], content="")

        # Check if the bot's role is higher than the role to be removed
        if inter.guild.me.top_role.position <= role.position:
            error_container = Container(TextDisplay(f"{cancelar} Meu cargo não é alto o suficiente para remover o cargo '{role.name}'."), accent_colour=primary_color)
            return await inter.edit_original_response(components=[error_container], content="")
        
        try:
            # Check if the user has the role
            if role not in user.roles:
                info_container = Container(TextDisplay(f"{cancelar} O usuário {user.mention} não possui o cargo {role.mention}."), accent_colour=primary_color)
                return await inter.edit_original_response(components=[info_container], content="")

            await user.remove_roles(role)
            success_container = Container(TextDisplay(f"{check} Cargo {role.mention} removido do usuário {user.mention}!"), accent_colour=primary_color)
            await inter.edit_original_response(components=[success_container], content="")
        except disnake.Forbidden:
            error_container = Container(TextDisplay(f"{cancelar} Eu não tenho permissão para remover o cargo {role.mention} do usuário {user.mention} (Permissões insuficientes)."), accent_colour=primary_color)
            await inter.edit_original_response(components=[error_container], content="")
        except Exception as e:
            error_container = Container(TextDisplay(f"{cancelar} Ocorreu um erro ao remover o cargo: {e}."), accent_colour=primary_color)
            await inter.edit_original_response(components=[error_container], content="")

def setup(bot):
    bot.add_cog(RemoveRoleCommand(bot))
