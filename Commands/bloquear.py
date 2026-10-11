import disnake
from disnake.ext import commands

import json

with open("Database/emojis.json") as f:
    emojis = json.load(f)

check = emojis["check"]
cancelar = emojis["cancelar"]
carregarAnimado = emojis["carregarAnimado"]
CadUnlock = emojis["CadUnlock"]
user = emojis["user"]

class Bloquear(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _handle_bloquear(self, ctx_or_inter, loading_message=None, cargo: disnake.Role = None):
        is_interaction = isinstance(
            ctx_or_inter, disnake.ApplicationCommandInteraction
        )

        channel = ctx_or_inter.channel
        guild = ctx_or_inter.guild
        author = ctx_or_inter.author
        
        target_role = cargo or guild.default_role

        # ===================== PERMISSÃO CUSTOM ( /perms ) =====================
        if not self.bot.verificar_permissao(
            author.id,
            tipo="command",
            nome_permissao="bloquear"
        ):
            if is_interaction:
                error_container = disnake.ui.Container(disnake.ui.TextDisplay(f"{cancelar} Você não tem permissão."))
                return await ctx_or_inter.edit_original_response(components=[error_container])
            else:
                if loading_message: await loading_message.delete()
                return await ctx_or_inter.send(f"{cancelar} Você não tem permissão.")

        overwrite = channel.overwrites_for(target_role)

        # ===================== JÁ TRANCADO =====================
        if overwrite.send_messages is False:
            error_container = disnake.ui.Container(disnake.ui.TextDisplay(f"{cancelar} Este canal já está trancado para {target_role.mention}."))
            if is_interaction:
                return await ctx_or_inter.edit_original_response(components=[error_container])
            else:
                if loading_message: await loading_message.delete()
                return await ctx_or_inter.send(f"{cancelar} Este canal já está trancado para {target_role.mention}.")

        overwrite.send_messages = False
        overwrite.create_public_threads = False
        overwrite.create_private_threads = False

        # ===================== CONTAINER V2 (MENSAGEM PÚBLICA) =====================
        try:
            with open("Database/Configuracoes.json", "r") as f_config_db:
                config_db = json.load(f_config_db)
                primary_color_str = config_db.get("Cores", {}).get("Color_Primary", "16777215") # Default to white if not found
                primary_color = disnake.Colour(int(primary_color_str))
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            primary_color = disnake.Colour(16777215) # Fallback to white if file not found or invalid

        container_publico = disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"{check} Canal bloqueado para {target_role.mention}! Eles não podem enviar mensagens nem criar tópicos."
            ),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Desbloquear",
                    style=disnake.ButtonStyle.secondary,
                    custom_id=f"unlock_channel_btn:{target_role.id}",
                    emoji=CadUnlock,
                    disabled=False
                )
            ),
            accent_colour=primary_color
        )

        try:
            await channel.set_permissions(
                target_role,
                overwrite=overwrite,
                reason=f"Canal trancado por {author}"
            )

            # ===================== RESPOSTA =====================
            if is_interaction:
                await ctx_or_inter.edit_original_response(
                    components=[container_publico]
                )
            else:
                if loading_message: await loading_message.delete()
                await channel.send(components=[container_publico])

        except disnake.Forbidden:
            error_container = disnake.ui.Container(disnake.ui.TextDisplay(f"{cancelar} O bot não tem permissões para trancar este canal."))
            if is_interaction:
                await ctx_or_inter.edit_original_response(components=[error_container])
            else:
                if loading_message: await loading_message.delete()
                await ctx_or_inter.send(f"{cancelar} O bot não tem permissões para trancar este canal.")

        except Exception as e:
            error_container = disnake.ui.Container(disnake.ui.TextDisplay(f"{cancelar} Ocorreu um erro ao trancar o canal: {e}"))
            if is_interaction:
                await ctx_or_inter.edit_original_response(components=[error_container])
            else:
                if loading_message: await loading_message.delete()
                await ctx_or_inter.send(f"{cancelar} Ocorreu um erro ao trancar o canal: {e}")

    # ===================== SLASH LOCK =====================
    @commands.slash_command(name="bloquear")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def bloquear(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @bloquear.sub_command(name="canal", description="Bloqueia o canal de texto atual.")
    async def canal(self, inter: disnake.ApplicationCommandInteraction, cargo: disnake.Role = None):

        await inter.response.defer()
        await inter.edit_original_response(components=[disnake.ui.TextDisplay(f"{carregarAnimado} Carregando Informações...")])
        await self._handle_bloquear(inter, cargo=cargo)

    # ===================== PREFIX LOCK =====================
    @commands.command(
        name="bloquear",
        description="bloquear o canal de texto atual."
    )
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def prefix_bloquear(self, ctx: commands.Context, cargo: disnake.Role = None):
        loading_message = await ctx.send(f"{carregarAnimado} Carregando Informações...")
        await self._handle_bloquear(ctx, loading_message, cargo=cargo)

    # ===================== ERROS PREFIX =====================
    @prefix_bloquear.error
    async def bloquear_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(
                f"{cancelar} Você não tem a permissão `Gerenciar Canais`."
            )
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(
                f"{cancelar} Eu não tenho a permissão `Gerenciar Canais`."
            )
        else:
            print(f"Erro no comando 'bloquear': {error}")

    # ===================== BOTÃO UNLOCK =====================
    @commands.Cog.listener("on_button_click")
    async def on_unlock_button(self, inter: disnake.MessageInteraction):

        if not inter.component.custom_id.startswith("unlock_channel_btn:"):
            return
        
        await inter.response.defer()
        
        await inter.edit_original_response(components=[disnake.ui.TextDisplay(f"{carregarAnimado} Carregando Informações...")])

        role_id = int(inter.component.custom_id.split(":")[1])

        channel = inter.channel
        guild = inter.guild
        author = inter.author
        
        target_role = guild.get_role(role_id)
        if not target_role:
            error_container = disnake.ui.Container(disnake.ui.TextDisplay(f"{cancelar} O cargo a ser desbloqueado não foi encontrado."))
            return await inter.edit_original_response(components=[error_container])

        # ===== PERMISSÃO CUSTOM NO BOTÃO TAMBÉM =====
        if not self.bot.verificar_permissao(
            author.id,
            tipo="command",
            nome_permissao="bloquear"
        ):
            error_container = disnake.ui.Container(disnake.ui.TextDisplay(f"{cancelar} Você não tem permissão para usar este botão."))
            return await inter.edit_original_response(components=[error_container])

        overwrite = channel.overwrites_for(target_role)

        if overwrite.send_messages is not False:
            error_container = disnake.ui.Container(disnake.ui.TextDisplay(f"{cancelar} Este canal já está desbloqueado para {target_role.mention}."))
            return await inter.edit_original_response(components=[error_container])

        overwrite.send_messages = None
        overwrite.create_public_threads = None
        overwrite.create_private_threads = None

        await channel.set_permissions(
            target_role,
            overwrite=overwrite,
            reason=f"Canal desbloqueado por {author}"
        )

        success_container = disnake.ui.Container(
            disnake.ui.TextDisplay(f"{check} canal desbloqueado para {target_role.mention}!\n{user} autor da ação: {author.mention}")
        )
        await inter.edit_original_response(components=[success_container])


def setup(bot: commands.Bot):
    bot.add_cog(Bloquear(bot))