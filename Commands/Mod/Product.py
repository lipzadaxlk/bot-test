import disnake
from disnake.ext import commands
import json
from Functions.CarregarEmojis import *
from Functions.VerificarPerms import *
from Functions.VendaInfo import *

def ObterDatabase():
    with open("Database/Vendas/historicos.json") as f:
        return json.load(f)

class InfoProdutoCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command()
    async def order(self, inter):
        pass

    @order.sub_command()
    async def info(self, inter: disnake.MessageCommandInteraction, id: str):
        if not getattr(self.bot, 'emojis_ready', False):
            return await inter.response.send_message(f"{carregarAnimado} O bot ainda está sendo configurado. Por favor, aguarde um momento.", ephemeral=True)

        if not verificar_permissao(inter.author.id):
            return await inter.response.send_message(f"{negativo} Faltam permissões para executar essa ação", ephemeral=True)

        await inter.response.send_message(f"{carregarAnimado} Carregando informações", ephemeral=True)
        embed, components = ObterVendaPainel(inter, id)
        if embed is None:
            return await inter.edit_original_message(f"{negativo} Venda `{id}` não encontrada.")
        await inter.edit_original_message("", embed=embed, components=components, file=disnake.File(f"Database/Vendas/entregas/{id}.txt", filename="itens_comprados.txt"))

def setup(bot: commands.Bot):
    bot.add_cog(InfoProdutoCommand(bot))
