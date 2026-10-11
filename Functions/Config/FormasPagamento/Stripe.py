import disnake
from disnake import *
from disnake.ext import commands
import json
from datetime import *

from Functions.CarregarEmojis import *
from Functions.Config.FormasPagamentos import ObterFormasPagamento, SalvarFormasPagamento

class ConfigurarStripeModal(disnake.ui.Modal):
    def __init__(self):
        pagamentos = ObterFormasPagamento()
        stripe_config = pagamentos.get("stripe", {})
        
        components = [
            disnake.ui.TextInput(
                label="Stripe Secret Key",
                placeholder="sk_live_...",
                custom_id="secret_key",
                style=TextInputStyle.short,
                value=stripe_config.get("secret_key", "")
            ),
            disnake.ui.TextInput(
                label="Stripe Webhook Secret",
                placeholder="whsec_...",
                custom_id="webhook_secret",
                style=TextInputStyle.short,
                value=stripe_config.get("webhook_secret", "")
            ),
        ]
        super().__init__(title="Credenciais API Stripe", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        container = disnake.ui.Container(disnake.ui.TextDisplay(f"# {carregarAnimado} Salvando credenciais..."))
        await inter.response.edit_message(content="", embed=None, components=[container])
        secret_key = inter.text_values["secret_key"]
        webhook_secret = inter.text_values["webhook_secret"]

        salvarStripe(secret_key=secret_key, webhook_secret=webhook_secret)
        await GerenciarStripe(inter)
        await inter.followup.send(f"{positivo} Credenciais da API Stripe salvas.", ephemeral=True, delete_after=3)

def salvarStripe(secret_key, webhook_secret):
    pagamentos = ObterFormasPagamento()
    if "stripe" not in pagamentos:
        pagamentos["stripe"] = {"habilitado": False}
    pagamentos["stripe"].update({
        "configurado": bool(secret_key and webhook_secret),
        "secret_key": secret_key,
        "webhook_secret": webhook_secret
    })
    SalvarFormasPagamento(pagamentos)

async def GerenciarStripe(inter: disnake.MessageInteraction):
    pagamentos = ObterFormasPagamento()
    config = pagamentos.get("stripe", {"habilitado": False, "configurado": False})
    
    status_habilitado = f"{positivo} ``Habilitado``" if config.get("habilitado") else f"{negativo} ``Desabilitado``"
    status_configurado = f"{positivo} ``Configurado``" if config.get("configurado") else f"{negativo} ``Não configurado``"
    
    texto_container = f"""# 💳 Stripe (API) | Formas de Pagamento
Gerencie a integração com a Stripe, uma plataforma global de pagamentos.

**Status do Módulo**
{status_habilitado}

**Status da Configuração**
{status_configurado}"""

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(texto_container),
        disnake.ui.Separator(),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Habilitar" if not config.get("habilitado") else "Desabilitar", style=disnake.ButtonStyle.green if not config.get("habilitado") else disnake.ButtonStyle.red, custom_id="HabilitarPagamento_stripe"),
            disnake.ui.Button(label="Configurar Credenciais", style=disnake.ButtonStyle.blurple, custom_id="ConfigurarCredenciais_Stripe"),
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=voltar, custom_id="PainelConfigurar_FormasPagamento")
        )
    )
    
    await inter.edit_original_message(content="", embed=None, components=[container])

class StripePagamentosPlugin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def StripeButtonListener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        if custom_id == "GerenciarDefinicoesFormasPagamento_Stripe":
            container = disnake.ui.Container(disnake.ui.TextDisplay(f"# {carregarAnimado} Carregando..."))
            await inter.response.edit_message(content="", embed=None, components=[container])
            await GerenciarStripe(inter)
        elif custom_id == "HabilitarPagamento_stripe":
            pagamentos = ObterFormasPagamento()
            config = pagamentos.get("stripe", {})
            if config.get("configurado"):
                config["habilitado"] = not config.get("habilitado", False)
                SalvarFormasPagamento(pagamentos)
            await GerenciarStripe(inter)
        elif custom_id == "ConfigurarCredenciais_Stripe":
            await inter.response.send_modal(ConfigurarStripeModal())

def setup(bot: commands.Bot):
    bot.add_cog(StripePagamentosPlugin(bot))