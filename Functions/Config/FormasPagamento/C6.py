import disnake
from disnake import *
from disnake.ext import commands
import json
from datetime import *

from Functions.CarregarEmojis import *
from Functions.Config.FormasPagamentos import ObterFormasPagamento, SalvarFormasPagamento

class ConfigurarC6Modal(disnake.ui.Modal):
    def __init__(self):
        pagamentos = ObterFormasPagamento(); config = pagamentos.get("c6", {})
        components = [
            disnake.ui.TextInput(label="Client ID (C6 Bank)", custom_id="client_id", style=TextInputStyle.short, value=config.get("client_id", "")),
            disnake.ui.TextInput(label="Client Secret (C6 Bank)", custom_id="client_secret", style=TextInputStyle.short, value=config.get("client_secret", "")),
        ]
        super().__init__(title="Credenciais API C6 Bank", components=components)
    async def callback(self, inter: disnake.ModalInteraction):
        container = disnake.ui.Container(disnake.ui.TextDisplay(f"# {carregarAnimado} Salvando credenciais..."))
        await inter.response.edit_message(content="", embed=None, components=[container])
        pagamentos = ObterFormasPagamento()
        if "c6" not in pagamentos: pagamentos["c6"] = {"habilitado": False}
        pagamentos["c6"].update({"configurado": True, "client_id": inter.text_values["client_id"], "client_secret": inter.text_values["client_secret"]})
        SalvarFormasPagamento(pagamentos)
        await GerenciarC6(inter)
        await inter.followup.send(f"{positivo} Credenciais da API do C6 Bank salvas.", ephemeral=True, delete_after=3)

async def GerenciarC6(inter: disnake.MessageInteraction):
    pagamentos = ObterFormasPagamento()
    config = pagamentos.get("c6", {"habilitado": False, "configurado": False})
    
    status_habilitado = f"{positivo} ``Habilitado``" if config.get("habilitado") else f"{negativo} ``Desabilitado``"
    status_configurado = f"{positivo} ``Configurado``" if config.get("configurado") else f"{negativo} ``Não configurado``"

    texto_container = f"""# ⚫ C6 Bank (API) | Formas de Pagamento
Gerencie a integração com a API do C6 Bank.

**Status do Módulo**
{status_habilitado}

**Status da Configuração**
{status_configurado}"""

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(texto_container),
        disnake.ui.Separator(),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Habilitar" if not config.get("habilitado") else "Desabilitar", style=disnake.ButtonStyle.green if not config.get("habilitado") else disnake.ButtonStyle.red, custom_id="HabilitarPagamento_c6"),
            disnake.ui.Button(label="Configurar Credenciais", style=disnake.ButtonStyle.blurple, custom_id="ConfigurarCredenciais_C6"),
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=voltar, custom_id="PainelConfigurar_FormasPagamento")
        )
    )
    
    await inter.edit_original_message(content="", embed=None, components=[container])

class C6PagamentosPlugin(commands.Cog):
    def __init__(self, bot: commands.Bot): self.bot = bot
    @commands.Cog.listener("on_button_click")
    async def C6ButtonListener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        if custom_id == "GerenciarDefinicoesFormasPagamento_C6":
            container = disnake.ui.Container(disnake.ui.TextDisplay(f"# {carregarAnimado} Carregando..."))
            await inter.response.edit_message(content="", embed=None, components=[container])
            await GerenciarC6(inter)
        elif custom_id == "HabilitarPagamento_c6":
            pagamentos = ObterFormasPagamento(); config = pagamentos.get("c6", {})
            if config.get("configurado"): config["habilitado"] = not config.get("habilitado", False); SalvarFormasPagamento(pagamentos)
            await GerenciarC6(inter)
        elif custom_id == "ConfigurarCredenciais_C6": await inter.response.send_modal(ConfigurarC6Modal())
def setup(bot: commands.Bot): bot.add_cog(C6PagamentosPlugin(bot))