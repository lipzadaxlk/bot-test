import disnake
from disnake.ext import commands

try:
    from Functions.CarregarEmojis import positivo, negativo
except ImportError:
    positivo = "✅"
    negativo = "❌"

class KickCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _handle_kick(self, ctx_or_inter, member: disnake.Member, reason: str):
        is_interaction = isinstance(ctx_or_inter, disnake.ApplicationCommandInteraction)
        guild = ctx_or_inter.guild
        author = ctx_or_inter.author
        
        send_func = ctx_or_inter.edit_original_response if is_interaction else ctx_or_inter.reply

        if member.id == author.id:
            return await send_func(f"{negativo} Você não pode se expulsar!")
        if member.id == self.bot.user.id:
            return await send_func(f"{negativo} Você não pode expulsar o bot!")
        if member.top_role >= author.top_role and guild.owner_id != author.id:
            return await send_func(f"{negativo} Você não pode expulsar um membro com cargo igual ou superior ao seu.")
        if member.top_role >= guild.me.top_role:
             return await send_func(f"{negativo} Não posso expulsar este membro, pois o cargo dele é mais alto que o meu.")
        
        try:
            await member.kick(reason=f"Expulso por {author} | Motivo: {reason}")
            await send_func(f"{positivo} `{member}` foi expulso com sucesso! Motivo: `{reason}`.")
        except disnake.Forbidden:
            await send_func(f"{negativo} Erro de permissão. Não consegui expulsar este membro.")
        except Exception as e:
            await send_func(f"{negativo} Ocorreu um erro inesperado: {e}")

    @commands.slash_command(name="kick", description="Expulsa um membro do servidor.")
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def slash_kick(self, inter: disnake.ApplicationCommandInteraction,
                       member: disnake.Member, 
                       reason: str = "Motivo não especificado."):
        
        if not self.bot.verificar_permissao(inter.author.id, tipo="command", nome_permissao="kick"):
            return await inter.response.send_message(f"{negativo} Você não tem permissão para usar este comando.", ephemeral=True)
            
        await inter.response.defer(ephemeral=True)
        await self._handle_kick(inter, member, reason)

    @commands.command(name="kick", description="Expulsa um membro do servidor.")
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def prefix_kick(self, ctx: commands.Context,
                        member: disnake.Member, *,
                        reason: str = "Motivo não especificado."):

        if not self.bot.verificar_permissao(ctx.author.id, tipo="command", nome_permissao="kick"):
            return

        await self._handle_kick(ctx, member, reason)

    @prefix_kick.error
    async def kick_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(f"{negativo} Você não tem a permissão `Expulsar Membros` do Discord.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(f"{negativo} Eu não tenho a permissão `Expulsar Membros` para executar isto.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"{negativo} Uso incorreto! Exemplo: `{ctx.prefix}kick <@membro> [motivo]`")
        else:
            print(f"Erro no comando 'prefix_kick': {error}")

def setup(bot: commands.Bot):
    bot.add_cog(KickCommand(bot))