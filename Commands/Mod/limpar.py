import disnake
from disnake.ext import commands
import asyncio
import json

# Load Emojis
with open("Database/emojis.json") as f:
    emojis = json.load(f)
check = emojis["check"]
carregarAnimado = emojis["carregarAnimado"]
cancelar = emojis.get("cancelar", "❌") # Fallback

class Limpar(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _handle_limpar(self, ctx_or_inter, quantidade: int):
        is_interaction = isinstance(ctx_or_inter, disnake.ApplicationCommandInteraction)
        channel = ctx_or_inter.channel
        
        # Clear a specific amount of messages
        if quantidade <= 0:
            if is_interaction:
                await ctx_or_inter.edit_original_response("A quantidade deve ser um número positivo.")
            else:
                await ctx_or_inter.channel.send("A quantidade deve ser um número positivo.", delete_after=5)
            return

        try:
            deleted = await channel.purge(limit=quantidade)
            deleted_count = len(deleted)
        except disnake.HTTPException as e:
            print(f"Error purging channel: {e}")
            if is_interaction:
                await ctx_or_inter.edit_original_response(f"Ocorreu um erro ao limpar as mensagens: {e}")
            else:
                await ctx_or_inter.channel.send(f"Ocorreu um erro ao limpar as mensagens: {e}", delete_after=5)
            return


        # Create the success container
        success_container = disnake.ui.Container(
            disnake.ui.TextDisplay(f"{check} `{deleted_count}` Mensagens foram apagadas com sucesso!")
        )

        # Send the final message
        try:
            await channel.send(components=[success_container], delete_after=10)
        except disnake.HTTPException:
            pass # Channel might be gone

        if is_interaction:
            # "Delete" the ephemeral message by editing it to be empty
            await ctx_or_inter.edit_original_response(content="​") # Zero-width space


    @commands.slash_command(name="limpar")
    async def limpar(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @limpar.sub_command(name="canal", description="Limpa uma quantidade de mensagens do canal atual.")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def canal(self, inter: disnake.ApplicationCommandInteraction, quantidade: int = commands.Param(description="a quantidade que deseja limpar")):
        
        if not self.bot.verificar_permissao(inter.author.id, tipo="command", nome_permissao="cls"): # Assuming same perm
            error_container = disnake.ui.Container(disnake.ui.TextDisplay(f"{cancelar} Você não tem permissão."))
            return await inter.response.send_message(components=[error_container], ephemeral=True)

        await inter.response.defer(ephemeral=True)
        await inter.edit_original_response(content=f"{carregarAnimado} Carregando Informações...")
        
        await self._handle_limpar(inter, quantidade)

    @commands.command(name="limparcanal", aliases=["clearchannel"], description="Limpa uma quantidade de mensagens do canal.")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def prefix_limpar(self, ctx: commands.Context, quantidade: int):
        
        if not self.bot.verificar_permissao(ctx.author.id, tipo="command", nome_permissao="cls"): # Assuming same perm
            return

        loading_message = await ctx.send(f"{carregarAnimado} Carregando Informações...")
        
        await self._handle_limpar(ctx, quantidade)
        
        try:
            await loading_message.delete()
        except disnake.NotFound:
            pass # Message might have been deleted already

    @prefix_limpar.error
    async def limpar_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(f"{cancelar} Você não tem a permissão `Gerenciar Mensagens`.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(f"{cancelar} Eu não tenho a permissão `Gerenciar Mensagens`.")
        else:
            print(f"Erro no comando 'prefix_limpar': {error}")


def setup(bot: commands.Bot):
    bot.add_cog(Limpar(bot))
