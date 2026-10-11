import disnake
from disnake.ext import commands
import json
import os
from datetime import datetime

# Presume-se que este arquivo exista e contenha as variáveis de emoji
from Functions.CarregarEmojis import *

class EstatisticasCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def safe_load_json(self, path: str, default_return={}):
        """Carrega um arquivo JSON de forma segura, retornando um valor padrão em caso de erro."""
        if not os.path.exists(path):
            return default_return
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return default_return

    def get_painel_inicial(self, inter: disnake.MessageInteraction):
        """Gera a embed e os componentes para o painel inicial de estatísticas."""
        embed = disnake.Embed(
            title=f"{lupa} Painel de Estatísticas",
            description="Selecione abaixo qual sistema você deseja visualizar as estatísticas.",
            color=disnake.Color.blue(),
            timestamp=datetime.now()
        )
        embed.set_footer(text=f"Servidor: {inter.guild.name}", icon_url=inter.guild.icon)

        components = [
            disnake.ui.Button(label="Vendas", custom_id="Estatisticas_Vendas", emoji=caixa, style=disnake.ButtonStyle.primary),
            disnake.ui.Button(label="Ticket", custom_id="Estatisticas_Ticket", emoji=ticket, style=disnake.ButtonStyle.secondary),
        ]
        return embed, components

    def get_stats_vendas(self, inter: disnake.MessageInteraction):
        """Calcula e gera a embed de estatísticas para o sistema de vendas."""
        produtos_db = self.safe_load_json("Database/Vendas/produtos.json")
        
        total_produtos = len(produtos_db)
        total_campos = 0
        total_cupons = 0
        total_usos_cupons = 0
        total_economizado_cupons = 0.0

        for produto_id, produto_data in produtos_db.items():
            total_campos += len(produto_data.get("campos", {}))
            total_cupons += len(produto_data.get("cupons", {}))
            for cupom_id, cupom_data in produto_data.get("cupons", {}).items():
                total_usos_cupons += cupom_data.get("estatistics", {}).get("uses", 0)
                total_economizado_cupons += float(cupom_data.get("estatistics", {}).get("economizado", 0.0))

        embed = disnake.Embed(
            title="📊 Estatísticas de Vendas",
            description="Visão geral dos dados do sistema de vendas.",
            color=disnake.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(name=f"{caixa} Produtos Criados", value=f"```{total_produtos}```", inline=True)
        embed.add_field(name=f"{config3} Itens à Venda (Campos)", value=f"```{total_campos}```", inline=True)
        embed.add_field(name=f"{cupom} Cupons Criados", value=f"```{total_cupons}```", inline=True)
        embed.add_field(name=f"{reload} Usos Totais de Cupons", value=f"```{total_usos_cupons}```", inline=True)
        embed.add_field(name=f"{dollar} Valor Economizado (Cupons)", value=f"```R$ {total_economizado_cupons:.2f}```", inline=True)
        
        embed.set_footer(text="Nota: As estatísticas de vendas (total arrecadado, etc) não são exibidas pois não há um histórico de compras.", icon_url=inter.guild.icon)

        components = [
            disnake.ui.Button(label="Vendas", custom_id="Estatisticas_Vendas", emoji=caixa, style=disnake.ButtonStyle.green, disabled=True),
            disnake.ui.Button(label="Ticket", custom_id="Estatisticas_Ticket", emoji=ticket, style=disnake.ButtonStyle.secondary),
            disnake.ui.Button(label="Voltar", custom_id="GerenciarEstatisticas", emoji=voltar, style=disnake.ButtonStyle.grey)
        ]
        return embed, components

    def get_stats_ticket(self, inter: disnake.MessageInteraction):
        """Calcula e gera a embed de estatísticas para o sistema de tickets."""
        ticket_db = self.safe_load_json("Database/Tickets/ticket.json")
        tickets_abertos_db = self.safe_load_json("Database/Tickets/ticketsAbertos.json")

        total_paineis = len(ticket_db)
        total_categorias = 0
        for painel_id, painel_data in ticket_db.items():
            total_categorias += len(painel_data.get("categorias", {}))
        
        tickets_abertos = len(tickets_abertos_db)

        embed = disnake.Embed(
            title="📊 Estatísticas de Ticket",
            description="Visão geral dos dados do sistema de tickets.",
            color=disnake.Color.orange(),
            timestamp=datetime.now()
        )
        embed.add_field(name=f"{ticket} Painéis de Ticket Criados", value=f"```{total_paineis}```", inline=True)
        embed.add_field(name=f"{diretorio} Categorias Totais", value=f"```{total_categorias}```", inline=True)
        embed.add_field(name=f"{users} Tickets Atualmente Abertos", value=f"```{tickets_abertos}```", inline=True)

        embed.set_footer(text="Nota: Não há um histórico de tickets fechados para exibir estatísticas completas.", icon_url=inter.guild.icon)

        components = [
            disnake.ui.Button(label="Vendas", custom_id="Estatisticas_Vendas", emoji=caixa, style=disnake.ButtonStyle.primary),
            disnake.ui.Button(label="Ticket", custom_id="Estatisticas_Ticket", emoji=ticket, style=disnake.ButtonStyle.secondary, disabled=True),
            disnake.ui.Button(label="Voltar", custom_id="GerenciarEstatisticas", emoji=voltar, style=disnake.ButtonStyle.secondary)
        ]
        return embed, components

    @commands.Cog.listener("on_button_click")
    async def EstatisticasButtonListener(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id

        if cid == "GerenciarEstatisticas":
            embed, components = self.get_painel_inicial(inter)
            # Se a interação já foi respondida (ex: clicando em "Voltar"), edita. Senão, envia uma nova.
            if inter.response.is_done():
                await inter.edit_original_message(embed=embed, components=components)
            else:
                await inter.response.send_message(embed=embed, components=components, ephemeral=True)

        elif cid == "Estatisticas_Vendas":
            await inter.response.defer()
            embed, components = self.get_stats_vendas(inter)
            await inter.edit_original_message(embed=embed, components=components)

        elif cid == "Estatisticas_Ticket":
            await inter.response.defer()
            embed, components = self.get_stats_ticket(inter)
            await inter.edit_original_message(embed=embed, components=components)


def setup(bot: commands.Bot):
    bot.add_cog(EstatisticasCommand(bot))