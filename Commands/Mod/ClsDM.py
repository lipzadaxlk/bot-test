import disnake
from disnake.ext import commands
from Functions.CarregarEmojis import *
from Functions.VerificarPerms import *

class ClsDMCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command()
    async def clsdm(self, inter: disnake.ApplicationCommandInteraction, user: disnake.User):
        if not getattr(self.bot, 'emojis_ready', False):
            return await inter.response.send_message(f"{carregarAnimado} O bot ainda está sendo configurado. Por favor, aguarde um momento.", ephemeral=True)
        
        if not verificar_permissao(inter.author.id):
            return await inter.response.send_message(f"{negativo} Faltam permissões para executar essa ação", ephemeral=True)

        await inter.response.send_message(f"{carregarAnimado} Aguarde um momento", ephemeral=True)
        try:
            dm_channel = await user.create_dm()
            async for message in dm_channel.history(limit=100):
                if message.author == self.bot.user:
                    await message.delete()
            await inter.edit_original_message(f"{positivo} Todas as minhas mensagens na DM de {user.name} foram apagadas.")
        except Exception:
            await inter.edit_original_message(f"{negativo} Não foi possível apagar as mensagens.")

def setup(bot: commands.Bot):
    bot.add_cog(ClsDMCommand(bot))
