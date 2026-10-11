import disnake
from disnake.ext import commands
from typing import Literal

try:
    from Functions.CarregarEmojis import positivo, negativo
except ImportError:
    positivo = "✅"
    negativo = "❌"

class BanCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _handle_ban(self, ctx_or_inter, member: disnake.Member, reason: str, delete_days: int):
        is_interaction = isinstance(ctx_or_inter, disnake.ApplicationCommandInteraction)
        guild = ctx_or_inter.guild
        author = ctx_or_inter.author
        
        # A resposta defer/reply é tratada dentro do comando agora
        send_func = ctx_or_inter.edit_original_response if is_interaction else ctx_or_inter.reply

        if member.id == author.id:
            return await send_func(f"{negativo} Você não pode se banir!")
        if member.id == self.bot.user.id:
            return await send_func(f"{negativo} Você não pode banir o bot!")
        if member.top_role >= author.top_role and guild.owner_id != author.id:
            return await send_func(f"{negativo} Você não pode banir um membro com cargo igual ou superior ao seu.")
        if member.top_role >= guild.me.top_role:
            return await send_func(f"{negativo} Não posso banir este membro, pois o cargo dele é mais alto que o meu.")

        try:
            await member.ban(reason=f"Banido por {author} | Motivo: {reason}", delete_message_days=delete_days)
            await send_func(f"{positivo} `{member}` foi banido com sucesso! Motivo: `{reason}`.")
        except disnake.Forbidden:
            await send_func(f"{negativo} Erro de permissão. Não consegui banir este membro.")
        except Exception as e:
            await send_func(f"{negativo} Ocorreu um erro inesperado: {e}")

    @commands.slash_command(name="ban", description="Bane um membro do servidor.")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def slash_ban(self, inter: disnake.ApplicationCommandInteraction, 
                      member: disnake.Member, 
                      reason: str = "Motivo não especificado.",
                      delete_days: Literal[0, 1, 2, 3, 4, 5, 6, 7] = 0):
        
        if not self.bot.verificar_permissao(inter.author.id, tipo="command", nome_permissao="ban"):
            return await inter.response.send_message(f"{negativo} Você não tem permissão para usar este comando.", ephemeral=True)
        
        await inter.response.defer(ephemeral=True)
        await self._handle_ban(inter, member, reason, delete_days)

    @commands.command(name="ban", description="Bane um membro do servidor.")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def prefix_ban(self, ctx: commands.Context, 
                       member: disnake.Member, 
                       delete_days: int = 0, *, 
                       reason: str = "Motivo não especificado."):

        if not self.bot.verificar_permissao(ctx.author.id, tipo="command", nome_permissao="ban"):
            return # Falha silenciosamente
            
        if not 0 <= delete_days <= 7:
            return await ctx.reply(f"{negativo} O número de dias para apagar mensagens deve estar entre 0 e 7.")
        
        await self._handle_ban(ctx, member, reason, delete_days)
    
    @prefix_ban.error
    async def ban_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(f"{negativo} Você não tem a permissão `Banir Membros` do Discord.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(f"{negativo} Eu não tenho a permissão `Banir Membros` para executar isto.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"{negativo} Uso incorreto! Exemplo: `{ctx.prefix}ban <@membro> [dias] [motivo]`")
        else:
            print(f"Erro no comando 'prefix_ban': {error}")

def setup(bot: commands.Bot):
    bot.add_cog(BanCommand(bot))