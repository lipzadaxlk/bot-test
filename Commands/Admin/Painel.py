# Commands/Admin/Painel.py
# Painel com Componentes V2 usando ContainerBuilder

import disnake
from disnake.ext import commands
from disnake import Colour
from disnake.ui import Container, TextDisplay, Separator, ActionRow
import json
from datetime import datetime
import pytz


from Functions.CarregarEmojis import *
from Functions.VerificarPerms import *
from Commands.Admin.Plugins.Personalizacao import obterPainel

def get_saudacao_com_emoji():
    try:
        brasilia_tz = pytz.timezone('America/Sao_Paulo')
        now = datetime.now(brasilia_tz)
    except pytz.exceptions.UnknownTimeZoneError:
        now = datetime.now()
    except AttributeError:
        now = datetime.now()
    
    hour = now.hour
    
    if 5 <= hour < 12:
        return f"Bom dia 🌞"
    elif 12 <= hour < 18:
        return f"Boa tarde 🌞"
    else:
        return f"Boa noite 🌙"

def ObterPainelInicialBotoes(user=None):
    """Cria os elementos do painel principal e retorna uma lista de containers."""
    
    # Load primary color from Configuracoes.json
    try:
        with open("Database/Configuracoes.json", "r") as f_config_db:
            config_db = json.load(f_config_db)
            primary_color_str = config_db.get("Cores", {}).get("Color_Primary", "16777215") # Default to white if not found
            primary_color = disnake.Colour(int(primary_color_str))
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        primary_color = disnake.Colour(16777215) # Fallback to white if file not found or invalid
    
    username = f"**{user.name}**" if user else ""
    saudacao = f"Seja bem-vindo(a) {username}, {get_saudacao_com_emoji()}" if user else f"Seja bem-vindo(a), {get_saudacao_com_emoji()}"
    
    container1_elements = [
        disnake.ui.TextDisplay(f"# {Never}"),
        disnake.ui.Separator(),
        disnake.ui.TextDisplay(f"{saudacao}\n-# Aqui é o painel de controle do seu bot: **gerencie**, **configure** e **personalize** as funcionalidades do seu **Never Pro**."),
        disnake.ui.Separator(),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Central de Loja", custom_id="GerenciarPainelVendas", style=disnake.ButtonStyle.secondary, emoji=carrinho),
            disnake.ui.Button(label="Atendimento ", custom_id="GerenciarPainelTicket", style=disnake.ButtonStyle.secondary, emoji=ticket),
            disnake.ui.Button(label="NeverCloud", custom_id="GerenciarPainelECloud", style=disnake.ButtonStyle.secondary, emoji=cloud),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Ver Rendimentos", custom_id="GerenciarEstatisticas", style=disnake.ButtonStyle.secondary, emoji=dollar),
            disnake.ui.Button(label="Customização", custom_id="GerenciarPainelPersonalizar", style=disnake.ButtonStyle.secondary, emoji=wand),
            disnake.ui.Button(label="Automações", custom_id="GerenciarAcoesAutomaticas", style=disnake.ButtonStyle.secondary, emoji=reload),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Sorteios", custom_id="GerenciarPainelGiveaways", style=disnake.ButtonStyle.secondary, emoji=sorteio),
            disnake.ui.Button(label="Proteção do Servidor", custom_id="GerenciarProtecaoServidor", style=disnake.ButtonStyle.secondary, emoji=protect),
            disnake.ui.Button(label="Definições", custom_id="GerenciarPainelConfigurar", style=disnake.ButtonStyle.secondary, emoji=config2),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Boas Vindas", custom_id="GerenciarPainelBoasVindas", style=disnake.ButtonStyle.secondary, emoji=sino),
            disnake.ui.Button(label="Comunidade", custom_id="GerenciarPainelComunidade", style=disnake.ButtonStyle.secondary, emoji=cmmnty),
        ),
    ]
    
    container2_elements = [
        disnake.ui.TextDisplay("-# Em caso de **dúvidas** ou **problemas**, acesse o servidor de suporte da **Never Applications** utilizando o botão abaixo."),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Dashboard", url="https://neverapps.com.br/dashboard"),
            disnake.ui.Button(label="Suporte", url="https://neveapps.com.br/suporte")
        )
    ]
    
    container1 = disnake.ui.Container(*container1_elements, accent_colour=primary_color)
    container2 = disnake.ui.Container(*container2_elements, accent_colour=primary_color)
    
    return [container1, container2], primary_color


class ConfigurarCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(description="Abre o painel de controle do bot.")
    async def painel(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer(ephemeral=True)

        if not verificar_permissao(inter.user.id):
            error_container = disnake.ui.Container(disnake.ui.TextDisplay(f"{cancelar} Você não tem permissão."))
            return await inter.followup.send(components=[error_container], ephemeral=True)

        if not getattr(self.bot, 'emojis_ready', False):
            return await inter.followup.send(f"{carregarAnimado} O bot ainda está sendo configurado. Por favor, aguarde um momento e tente novamente.", ephemeral=True)
                
        components_list, _ = ObterPainelInicialBotoes(inter.user)
        await inter.followup.send(content="", components=components_list, ephemeral=True)

    @commands.Cog.listener("on_button_click")
    async def PainelListener(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "PainelInicial":
            if not verificar_permissao(inter.user.id):
                error_container = disnake.ui.Container(disnake.ui.TextDisplay(f"{cancelar} Você não tem permissão."))
                return await inter.response.send_message(components=[error_container], ephemeral=True)
            
            loading_container = Container(
                TextDisplay(f"{carregarAnimado} Carregando painel principal...")
            )
            await inter.response.edit_message(embed=None, components=[loading_container])
            
            components_list, _ = ObterPainelInicialBotoes(inter.user)
            await inter.edit_original_message(embed=None, components=components_list)
        elif inter.component.custom_id == "GerenciarPainelPersonalizar":
            if not verificar_permissao(inter.user.id):
                error_container = disnake.ui.Container(disnake.ui.TextDisplay(f"{cancelar} Você não tem permissão."))
                return await inter.response.send_message(components=[error_container], ephemeral=True)
            
            loading_container = Container(
                TextDisplay(f"{carregarAnimado} Carregando painel de customização...")
            )
            await inter.response.edit_message(embed=None, components=[loading_container])
            
            # Here we assume obterPainel might need the primary_color, or gets it internally.
            # For now, let's just call it. We will adjust obterPainel later.
            personalizacao_components = obterPainel(inter) 
            await inter.edit_original_message(embed=None, components=personalizacao_components)


def setup(bot):
    bot.add_cog(ConfigurarCommand(bot))