import disnake
from disnake.ext import commands
from disnake.ui import Container, TextDisplay
import json
import time # Added time import

from Functions.CarregarEmojis import (
    check,
    cancelar,
    carregarAnimado,
    clock, # Added clock emoji import
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

class AddRoleCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(
        name="adicionar",
        description="Comandos para adicionar elementos."
    )
    async def adicionar(self, inter: disnake.ApplicationCommandInteraction):
        pass # This is a group command, it will have subcommands

    @adicionar.sub_command_group(
        name="cargo",
        description="Gerencia cargos."
    )
    async def cargo(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @cargo.sub_command(
        name="usuario",
        description="Adiciona um cargo a um usuário específico."
    )
    async def usuario(
        self,
        inter: disnake.ApplicationCommandInteraction,
        role: disnake.Role = commands.Param(description="O cargo a ser adicionado ao usuário."),
        user: disnake.Member = commands.Param(description="O usuário para adicionar o cargo.")
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

        # Check if the bot's role is higher than the role to be added
        if inter.guild.me.top_role.position <= role.position:
            error_container = Container(TextDisplay(f"{cancelar} Meu cargo não é alto o suficiente para adicionar o cargo '{role.name}'."), accent_colour=primary_color)
            return await inter.edit_original_response(components=[error_container], content="")
        
        # Check if the role is assignable (not @everyone or a managed role that can't be assigned manually)
        if role.managed or role.is_bot_managed() or role.is_integration() or role.is_premium_subscriber():
            error_container = Container(TextDisplay(f"{cancelar} Não posso adicionar o cargo '{role.name}' pois é um cargo gerenciado ou de sistema."), accent_colour=primary_color)
            return await inter.edit_original_response(components=[error_container], content="")


        try:
            # Check if the user already has the role
            if role in user.roles:
                info_container = Container(TextDisplay(f"{check} O usuário {user.mention} já possui o cargo {role.mention}."), accent_colour=primary_color)
                return await inter.edit_original_response(components=[info_container], content="")

            await user.add_roles(role)
            success_container = Container(TextDisplay(f"{check} Cargo {role.mention} adicionado com sucesso ao usuário {user.mention}."), accent_colour=primary_color)
            await inter.edit_original_response(components=[success_container], content="")
        except disnake.Forbidden:
            error_container = Container(TextDisplay(f"{cancelar} Eu não tenho permissão para adicionar o cargo {role.mention} ao usuário {user.mention} (Permissões insuficientes)."), accent_colour=primary_color)
            await inter.edit_original_response(components=[error_container], content="")
        except Exception as e:
            error_container = Container(TextDisplay(f"{cancelar} Ocorreu um erro ao adicionar o cargo: {e}."), accent_colour=primary_color)
            await inter.edit_original_response(components=[error_container], content="")

    @cargo.sub_command(
        name="todos",
        description="Adiciona um cargo a todos os membros do servidor."
    )
    async def todos(
        self,
        inter: disnake.ApplicationCommandInteraction,
        role: disnake.Role = commands.Param(description="O cargo a ser adicionado a todos os membros.")
    ):
        start_time = time.time()
        await inter.response.send_message(content=f"{carregarAnimado} Carregando Informações...", ephemeral=True)

        primary_color = load_primary_color()

        # Permission checks (copied from 'usuario' subcommand)
        if not verificar_permissao(inter.user.id):
            error_container = Container(TextDisplay(f"{cancelar} Você não tem permissão para usar este comando."), accent_colour=primary_color)
            return await inter.edit_original_response(components=[error_container], content="")

        if not inter.guild.me.guild_permissions.manage_roles:
            error_container = Container(TextDisplay(f"{cancelar} Eu não tenho permissão para gerenciar cargos neste servidor."), accent_colour=primary_color)
            return await inter.edit_original_response(components=[error_container], content="")

        if inter.guild.me.top_role.position <= role.position:
            error_container = Container(TextDisplay(f"{cancelar} Meu cargo não é alto o suficiente para adicionar o cargo '{role.name}'. Mova meu cargo acima do cargo '{role.name}'."), accent_colour=primary_color)
            return await inter.edit_original_response(components=[error_container], content="")
        
        if role.managed or role.is_bot_managed() or role.is_integration() or role.is_premium_subscriber():
            error_container = Container(TextDisplay(f"{cancelar} Não posso adicionar o cargo '{role.name}' pois é um cargo gerenciado ou de sistema."), accent_colour=primary_color)
            return await inter.edit_original_response(components=[error_container], content="")

        success_count = 0
        failure_count = 0

        # Iterate through all members and add the role
        for member in inter.guild.members:
            if role not in member.roles: # Only add if member doesn't have the role
                if member == self.bot.user: # Skip the bot itself
                    continue
                try:
                    await member.add_roles(role)
                    success_count += 1
                except disnake.Forbidden:
                    failure_count += 1
                except Exception:
                    failure_count += 1
        
        end_time = time.time()

        final_message_content = (
            f"{check} O cargo {role.mention} foi adicionado com sucesso em `{success_count}` membros!\n"
            f"{cancelar} Falhas: `{failure_count}`\n"
            f"{clock} Tempo de finalização: <t:{int(end_time)}:R>"
        )

        final_container = Container(TextDisplay(final_message_content), accent_colour=primary_color)
        await inter.edit_original_response(components=[final_container], content="")


def setup(bot):
    bot.add_cog(AddRoleCommand(bot))