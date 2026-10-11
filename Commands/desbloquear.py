import disnake
from disnake.ext import commands

import json

with open("Database/emojis.json") as f:
    emojis = json.load(f)

check = emojis["check"]
cancelar = emojis["cancelar"]
carregarAnimado = emojis["carregarAnimado"]
CadLock = emojis["CadLock"]
user = emojis["user"]
CadUnlock = emojis["CadUnlock"]

class Desbloquear(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _handle_desbloquear(self, ctx_or_inter, loading_message=None, cargo: disnake.Role = None):
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
            nome_permissao="bloquear"  # Assuming 'desbloquear' uses the same perm
        ):
            if is_interaction:
                error_container = disnake.ui.Container(disnake.ui.TextDisplay(f"{cancelar} Você não tem permissão."))
                return await ctx_or_inter.edit_original_response(components=[error_container])
            else:
                if loading_message: await loading_message.delete()
                return await ctx_or_inter.send(f"{cancelar} Você não tem permissão.")

        overwrite = channel.overwrites_for(target_role)

        # ===================== JÁ DESTRANCADO =====================
        if overwrite.send_messages is not False and overwrite.create_public_threads is not False and overwrite.create_private_threads is not False:
            error_container = disnake.ui.Container(disnake.ui.TextDisplay(f"{cancelar} Este canal já está desbloqueado para {target_role.mention}."))
            if is_interaction:
                return await ctx_or_inter.edit_original_response(components=[error_container])
            else:
                if loading_message: await loading_message.delete()
                return await ctx_or_inter.send(f"{cancelar} Este canal já está desbloqueado para {target_role.mention}.")

        overwrite.send_messages = None
        overwrite.create_public_threads = None
        overwrite.create_private_threads = None

        # ===================== CONTAINER V2 (MENSAGEM PÚBLICA) =====================
        try:
            with open("Database/Configuracoes.json", "r") as f_config_db:
                config_db = json.load(f_config_db)
                primary_color_str = config_db.get("Cores", {}).get("Color_Primary", "16777215")
                primary_color = disnake.Colour(int(primary_color_str))
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            primary_color = disnake.Colour(16777215)

        container_publico = disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"{check} Canal desbloqueado para {target_role.mention}! Eles agora podem enviar mensagens e criar tópicos."
            ),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Bloquear",
                    style=disnake.ButtonStyle.secondary,
                    custom_id=f"lock_channel_btn:{target_role.id}",
                    emoji=CadLock,
                    disabled=False
                )
            ),
            accent_colour=primary_color
        )

        try:
            await channel.set_permissions(
                target_role,
                overwrite=overwrite,
                reason=f"Canal destrancado por {author}"
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
            error_container = disnake.ui.Container(disnake.ui.TextDisplay(f"{cancelar} O bot não tem permissões para destrancar este canal."))
            if is_interaction:
                await ctx_or_inter.edit_original_response(components=[error_container])
            else:
                if loading_message: await loading_message.delete()
                await ctx_or_inter.send(f"{cancelar} O bot não tem permissões para destrancar este canal.")

        except Exception as e:
            error_container = disnake.ui.Container(disnake.ui.TextDisplay(f"{cancelar} Ocorreu um erro ao destrancar o canal: {e}"))
            if is_interaction:
                await ctx_or_inter.edit_original_response(components=[error_container])
            else:
                if loading_message: await loading_message.delete()
                await ctx_or_inter.send(f"{cancelar} Ocorreu um erro ao destrancar o canal: {e}")

    # ===================== SLASH LOCK =====================
    @commands.slash_command(name="desbloquear")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def desbloquear(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @desbloquear.sub_command(name="canal", description="Desbloqueia o canal de texto atual.")
    async def canal(self, inter: disnake.ApplicationCommandInteraction, cargo: disnake.Role = None):

        await inter.response.defer()
        await inter.edit_original_response(components=[disnake.ui.TextDisplay(f"{carregarAnimado} Carregando Informações...")])
        await self._handle_desbloquear(inter, cargo=cargo)

    # ===================== PREFIX LOCK =====================
    @commands.command(
        name="desbloquear",
        description="desbloquear o canal de texto atual."
    )
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def prefix_desbloquear(self, ctx: commands.Context, cargo: disnake.Role = None):
        loading_message = await ctx.send(f"{carregarAnimado} Carregando Informações...")
        await self._handle_desbloquear(ctx, loading_message, cargo=cargo)

    # ===================== ERROS PREFIX =====================
    @prefix_desbloquear.error
    async def desbloquear_error(self, ctx: commands.Context, error: commands.CommandError):
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
    async def on_lock_button(self, inter: disnake.MessageInteraction):

        if not inter.component.custom_id.startswith("lock_channel_btn:"):
            return
        
        await inter.response.defer()
        
        await inter.edit_original_response(components=[disnake.ui.TextDisplay(f"{carregarAnimado} Carregando Informações...")])

        role_id = int(inter.component.custom_id.split(":")[1])

        channel = inter.channel
        guild = inter.guild
        author = inter.author
        
        target_role = guild.get_role(role_id)
        if not target_role:
            error_container = disnake.ui.Container(disnake.ui.TextDisplay(f"{cancelar} O cargo a ser bloqueado não foi encontrado."))
            return await inter.edit_original_response(components=[error_container])

        if not self.bot.verificar_permissao(
            author.id,
            tipo="command",
            nome_permissao="bloquear"
        ):
            error_container = disnake.ui.Container(disnake.ui.TextDisplay(f"{cancelar} Você não tem permissão para usar este botão."))
            return await inter.edit_original_response(components=[error_container])

        overwrite = channel.overwrites_for(target_role)

        if overwrite.send_messages is False:
            error_container = disnake.ui.Container(disnake.ui.TextDisplay(f"{cancelar} Este canal já está bloqueado para {target_role.mention}."))
            return await inter.edit_original_response(components=[error_container])

        overwrite.send_messages = False
        overwrite.create_public_threads = False
        overwrite.create_private_threads = False

        await channel.set_permissions(
            target_role,
            overwrite=overwrite,
            reason=f"Canal bloqueado por {author}"
        )

        success_container = disnake.ui.Container(
            disnake.ui.TextDisplay(f"{check} canal bloqueado para {target_role.mention}!\n{user} autor da ação: {author.mention}")
        )
        await inter.edit_original_response(components=[success_container])


def setup(bot: commands.Bot):
    bot.add_cog(Desbloquear(bot))