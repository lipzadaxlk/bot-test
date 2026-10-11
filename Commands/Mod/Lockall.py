import disnake
from disnake.ext import commands
import asyncio

try:
    from Functions.CarregarEmojis import positivo, negativo, aviso
except ImportError:
    positivo = "✅"
    negativo = "❌"
    aviso = "⚠️"

class LockallCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _handle_lockall(self, ctx_or_inter):
        is_interaction = isinstance(ctx_or_inter, disnake.ApplicationCommandInteraction)
        
        if is_interaction:
            await ctx_or_inter.response.defer(ephemeral=True)
        else:
            await ctx_or_inter.message.add_reaction("⏳")

        send_func = ctx_or_inter.edit_original_response if is_interaction else ctx_or_inter.send
        
        guild = ctx_or_inter.guild
        author = ctx_or_inter.author
        
        locked_channels, failed_channels = [], []
        everyone_role = guild.default_role
        text_channels = [c for c in guild.text_channels if c.overwrites_for(everyone_role).send_messages is not False]

        if not text_channels:
            embed = disnake.Embed(description=f"{aviso} Nenhum canal precisou ser modificado.", color=disnake.Color.yellow())
            return await send_func(embed=embed, ephemeral=is_interaction)

        for channel in text_channels:
            try:
                await channel.set_permissions(everyone_role, send_messages=False, reason=f"Lockall por {author}")
                locked_channels.append(channel.mention)
                await asyncio.sleep(0.3)
            except (disnake.Forbidden, disnake.HTTPException):
                failed_channels.append(channel.mention)
        
        embed = disnake.Embed(title="Resultado do `Lockall`", color=disnake.Color.dark_red())
        if locked_channels:
            embed.add_field(name=f"{positivo} Canais Trancados ({len(locked_channels)})", value=", ".join(locked_channels)[:1024], inline=False)
        if failed_channels:
            embed.add_field(name=f"{negativo} Falha ao Trancar ({len(failed_channels)})", value=", ".join(failed_channels)[:1024], inline=False)
        
        await send_func(embed=embed, ephemeral=is_interaction)
        if not is_interaction:
            await ctx_or_inter.message.remove_reaction("⏳", self.bot.user)

    @commands.slash_command(name="lockall", description="Tranca todos os canais de texto do servidor.")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def slash_lockall(self, inter: disnake.ApplicationCommandInteraction):

        if not self.bot.verificar_permissao(inter.author.id, tipo="command", nome_permissao="lockall"):
            return await inter.response.send_message(f"{negativo} Você não tem permissão para usar este comando.", ephemeral=True)

        await self._handle_lockall(inter)

    @commands.command(name="lockall", description="Tranca todos os canais de texto do servidor.")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def prefix_lockall(self, ctx: commands.Context):

        if not self.bot.verificar_permissao(ctx.author.id, tipo="command", nome_permissao="lockall"):
            return

        await self._handle_lockall(ctx)

    @prefix_lockall.error
    async def lockall_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(f"{negativo} Você não tem a permissão `Gerenciar Canais`.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(f"{negativo} Eu não tenho a permissão `Gerenciar Canais`.")
        else:
            print(f"Erro no comando 'prefix_lockall': {error}")

def setup(bot: commands.Bot):
    bot.add_cog(LockallCommand(bot))