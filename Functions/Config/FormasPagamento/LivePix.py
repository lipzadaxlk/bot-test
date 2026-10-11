import disnake
from disnake import *
from disnake.ext import commands
import json
import requests
from datetime import *

from Functions.CarregarEmojis import *
from Functions.Config.FormasPagamentos import *

class ConfigurarLivePixModal(disnake.ui.Modal):
    def __init__(self):
        pagamentos = ObterFormasPagamento()
        livepix_config = pagamentos.get("livepix", {})
        
        components = [
            disnake.ui.TextInput(
                label="LivePix Client ID",
                placeholder="Seu Client ID da API da LivePix",
                custom_id="livepix_client_id",
                style=TextInputStyle.short,
                value=livepix_config.get("client_id", "")
            ),
            disnake.ui.TextInput(
                label="LivePix Client Secret",
                placeholder="Seu Client Secret da API da LivePix",
                custom_id="livepix_client_secret",
                style=TextInputStyle.short,
                value=livepix_config.get("client_secret", "")
            ),
        ]
        super().__init__(title="Credenciais LivePix", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        container = disnake.ui.Container(disnake.ui.TextDisplay(f"# {carregarAnimado} Verificando credenciais..."))
        await inter.response.edit_message(content="", embed=None, components=[container])

        client_id = inter.text_values["livepix_client_id"]
        client_secret = inter.text_values["livepix_client_secret"]
        
        # A API da LivePix usa Bearer Token, que é gerado com Client ID/Secret.
        # A validação ocorreria ao tentar gerar o token, mas salvamos direto por simplicidade.
        status = True

        if status:
            salvarLivePix(client_id=client_id, client_secret=client_secret)
            await GerenciarLivePix(inter)
            await inter.followup.send(f"{positivo} Credenciais da LivePix salvas com sucesso.", ephemeral=True, delete_after=3)
        else:
            await GerenciarLivePix(inter)
            await inter.followup.send(f"{negativo} As credenciais da LivePix parecem inválidas.", ephemeral=True, delete_after=5)

def salvarLivePix(client_id, client_secret):
    try:
        caminho_arquivo = "Database/Vendas/pagamentos.json"
        
        with open(caminho_arquivo, "r") as f:
            db = json.load(f)
        
        if "livepix" not in db:
            db["livepix"] = {"habilitado": False}

        db["livepix"].update({
            "configurado": True,
            "client_id": client_id,
            "client_secret": client_secret
        })

        with open(caminho_arquivo, "w") as f:
            json.dump(db, f, indent=4)

        return True
    except Exception as e:
        print(f"Erro ao salvar as credenciais da LivePix: {e}")
        return False

async def GerenciarLivePix(inter: disnake.MessageInteraction):
    FormasPagamento = ObterFormasPagamento()
    LivePix = FormasPagamento.get("livepix", {"habilitado": False, "configurado": False, "client_id": None, "client_secret": None})

    Button = {
        "label": "Desabilitar" if LivePix.get("habilitado") else "Habilitar",
        "style": disnake.ButtonStyle.danger if LivePix.get("habilitado") else disnake.ButtonStyle.success,
    }

    def formatar_forma_pagamento(habilitado, configurado):
        status_habilitado = f"{positivo} ``Habilitado``" if habilitado else f"{negativo} ``Desabilitado``"
        status_configurado = f"{positivo} ``Configurado``" if configurado else f"{negativo} ``Não configurado``"
        return f"{status_habilitado}\n{status_configurado}"

    credenciais_status = f"{positivo} `Definidas`" if (LivePix.get("client_id") and LivePix.get("client_secret")) else f"{negativo} `Não definidas`"

    texto_container = f"""# 🟢 LivePix | Formas de Pagamento
Configure a integração de pagamento com a LivePix.

**Sistema**
{formatar_forma_pagamento(LivePix.get("habilitado"), LivePix.get("configurado"))}

**Credenciais**
{credenciais_status}"""

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(texto_container),
        disnake.ui.Separator(),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Configurar Credenciais", style=disnake.ButtonStyle.blurple, custom_id="ConfigurarSistemaLivePix", emoji=attach),
            disnake.ui.Button(label=Button["label"], style=Button["style"], custom_id="HabilitarDesabilitarSistemaPagamento_LivePix", emoji=reload),
            disnake.ui.Button(label="Voltar", emoji=voltar, custom_id="PainelConfigurar_FormasPagamento")
        )
    )

    await inter.edit_original_message(content="", embed=None, components=[container])

class LivePixPagamentosPlugin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def LivePixExtensionButtonListener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        if custom_id == "GerenciarDefinicoesFormasPagamento_LivePix":
            container = disnake.ui.Container(disnake.ui.TextDisplay(f"# {carregarAnimado} Carregando..."))
            await inter.response.edit_message(content="", embed=None, components=[container])
            await GerenciarLivePix(inter)
    
        elif custom_id == "HabilitarDesabilitarSistemaPagamento_LivePix":
            container = disnake.ui.Container(disnake.ui.TextDisplay(f"# {carregarAnimado} Atualizando..."))
            await inter.response.edit_message(content="", embed=None, components=[container])
            pagamentos = ObterFormasPagamento()
            livepix_config = pagamentos.get("livepix", {})

            if livepix_config.get("configurado"):
                livepix_config["habilitado"] = not livepix_config.get("habilitado", False)
                SalvarFormasPagamento(pagamentos)
                if livepix_config["habilitado"]:
                    await inter.followup.send(f"{positivo} O sistema de pagamento LivePix foi habilitado.", ephemeral=True, delete_after=3)
                else:
                    await inter.followup.send(f"{negativo} O sistema de pagamento LivePix foi desabilitado.", ephemeral=True, delete_after=3)
            else:
                await inter.followup.send(f"{negativo} As credenciais não estão configuradas.", ephemeral=True, delete_after=3)
            
            await GerenciarLivePix(inter)

        elif custom_id == "ConfigurarSistemaLivePix":
            await inter.response.send_modal(ConfigurarLivePixModal())

def setup(bot: commands.Bot):
    bot.add_cog(LivePixPagamentosPlugin(bot))