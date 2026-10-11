import disnake
from disnake import *
from disnake.ext import commands
import json
from datetime import *

from Functions.CarregarEmojis import *
from Functions.Config.FormasPagamentos import ObterFormasPagamento, SalvarFormasPagamento

class ConfigurarInterModal(disnake.ui.Modal):
    def __init__(self):
        pagamentos = ObterFormasPagamento()
        config = pagamentos.get("inter", {})
        
        components = [
            disnake.ui.TextInput(label="Client ID (Banco Inter)", custom_id="client_id", style=TextInputStyle.short, value=config.get("client_id", "")),
            disnake.ui.TextInput(label="Client Secret (Banco Inter)", custom_id="client_secret", style=TextInputStyle.short, value=config.get("client_secret", "")),
            disnake.ui.TextInput(label="Caminho do Certificado (.crt)", custom_id="cert_path", style=TextInputStyle.short, placeholder="/caminho/para/seu/certificado.crt", value=config.get("cert_path", "")),
            disnake.ui.TextInput(label="Caminho da Chave Privada (.key)", custom_id="key_path", style=TextInputStyle.short, placeholder="/caminho/para/sua/chave.key", value=config.get("key_path", "")),
        ]
        super().__init__(title="Credenciais API Banco Inter", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        container = disnake.ui.Container(disnake.ui.TextDisplay(f"# {carregarAnimado} Salvando credenciais..."))
        await inter.response.edit_message(content="", embed=None, components=[container])
        pagamentos = ObterFormasPagamento()
        if "inter" not in pagamentos: pagamentos["inter"] = {"habilitado": False}
        
        pagamentos["inter"].update({
            "configurado": True,
            "client_id": inter.text_values["client_id"],
            "client_secret": inter.text_values["client_secret"],
            "cert_path": inter.text_values["cert_path"],
            "key_path": inter.text_values["key_path"]
        })
        SalvarFormasPagamento(pagamentos)
        await GerenciarInter(inter)
        await inter.followup.send(f"{positivo} Credenciais da API do Banco Inter salvas.", ephemeral=True, delete_after=3)

async def GerenciarInter(inter: disnake.MessageInteraction):
    pagamentos = ObterFormasPagamento()
    config = pagamentos.get("inter", {"habilitado": False, "configurado": False})
    
    status_habilitado = f"{positivo} ``Habilitado``" if config.get("habilitado") else f"{negativo} ``Desabilitado``"
    status_configurado = f"{positivo} ``Configurado``" if config.get("configurado") else f"{negativo} ``Não configurado``"

    texto_container = f"""# 🟠 Banco Inter (API) | Formas de Pagamento
Gerencie a integração com a API do Banco Inter.

**Status do Módulo**
{status_habilitado}

**Status da Configuração**
{status_configurado}

-# A API do Inter requer um certificado e chave para autenticação."""

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(texto_container),
        disnake.ui.Separator(),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Habilitar" if not config.get("habilitado") else "Desabilitar", style=disnake.ButtonStyle.green if not config.get("habilitado") else disnake.ButtonStyle.red, custom_id="HabilitarPagamento_inter"),
            disnake.ui.Button(label="Configurar Credenciais", style=disnake.ButtonStyle.blurple, custom_id="ConfigurarCredenciais_Inter"),
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=voltar, custom_id="PainelConfigurar_FormasPagamento")
        )
    )
    
    await inter.edit_original_message(content="", embed=None, components=[container])

class InterPagamentosPlugin(commands.Cog):
    def __init__(self, bot: commands.Bot): self.bot = bot
    @commands.Cog.listener("on_button_click")
    async def InterButtonListener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        if custom_id == "GerenciarDefinicoesFormasPagamento_Inter":
            container = disnake.ui.Container(disnake.ui.TextDisplay(f"# {carregarAnimado} Carregando..."))
            await inter.response.edit_message(content="", embed=None, components=[container])
            await GerenciarInter(inter)
        elif custom_id == "HabilitarPagamento_inter":
            pagamentos = ObterFormasPagamento(); config = pagamentos.get("inter", {})
            if config.get("configurado"): config["habilitado"] = not config.get("habilitado", False); SalvarFormasPagamento(pagamentos)
            await GerenciarInter(inter)
        elif custom_id == "ConfigurarCredenciais_Inter": await inter.response.send_modal(ConfigurarInterModal())
def setup(bot: commands.Bot): bot.add_cog(InterPagamentosPlugin(bot))