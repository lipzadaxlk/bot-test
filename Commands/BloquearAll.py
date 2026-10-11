import disnake
from disnake.ext import commands
from Functions.CarregarEmojis import *

class NukeCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _handle_nuke(self, inter: disnake.ApplicationCommandInteraction):
        channel = inter.channel
        guild = inter.guild
        author = inter.author

        # ===================== PERMISSÃO CUSTOM (/perms) =====================
        if not self.bot.verificar_permissao(
            author.id,
            tipo="command",
            nome_permissao="nuke"
        ):
            return await inter.edit_original_response(
                f"{negativo} Você não tem permissão para usar este comando."
            )

        # ===================== PERMISSÕES DISCORD =====================
        if not author.guild_permissions.manage_channels:
            return await inter.edit_original_response(
                f"{negativo} Você não tem permissão para gerenciar canais."
            )

        if not guild.me.guild_permissions.manage_channels:
            return await inter.edit_original_response(
                f"{negativo} O bot não tem permissões suficientes para nukar este canal."
            )

        try:
            # ===================== CLONAR CANAL =====================
            new_channel = await channel.clone(
                reason=f"Nuke realizado por {author}"
            )

            # ===================== CONTAINER V2 (SEM BOTÃO) =====================
            container_publico = disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"{positivo} Canal nukado por `{author.name}`"
                )
            )

            # Enviar no canal novo
            await new_channel.send(components=[container_publico])

            # ===================== DELETAR CANAL ANTIGO =====================
            await channel.delete(
                reason=f"Nuke realizado por {author}"
            )

        except disnake.Forbidden:
            await inter.edit_original_response(
                f"{negativo} O bot não tem permissões suficientes para nukar este canal."
            )

        except Exception as e:
            await inter.edit_original_response(
                f"{negativo} Ocorreu um erro ao tentar nukar o canal: {e}"
            )

    # ===================== SLASH NUKE =====================
    @commands.slash_command(
        name="nuke",
        description="Nuka (reseta) o canal de texto atual."
    )
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def nuke(self, inter: disnake.ApplicationCommandInteraction):

        if not getattr(self.bot, "emojis_ready", False):
            return await inter.response.send_message(
                f"{carregarAnimado} O bot ainda está sendo configurado. Aguarde um momento.",
                ephemeral=True
            )

        await inter.response.defer(ephemeral=True)
        await self._handle_nuke(inter)


def setup(bot):
    bot.add_cog(NukeCommand(bot))