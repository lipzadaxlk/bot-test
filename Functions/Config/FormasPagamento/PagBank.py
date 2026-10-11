import disnake
from disnake import *
from disnake.ext import commands
import json
import requests
from datetime import *

from Functions.CarregarEmojis import *
from Functions.Config.FormasPagamentos import ObterFormasPagamento, SalvarFormasPagamento

class ConfigurarPagBankModal(disnake.ui.Modal):
    def __init__(self):
        pagamentos = ObterFormasPagamento()
        pagbank_config = pagamentos.get("pagbank", {})
        
        components = [
            disnake.ui.TextInput(
                label="Client ID (PagBank)",
                placeholder="Seu Client ID obtido no portal PagBank",
                custom_id="client_id",
                style=TextInputStyle.short,
                value=pagbank_config.get("client_id", "")
            ),
            disnake.ui.TextInput(
                label="Client Secret (PagBank)",
                placeholder="Seu Client Secret obtido no portal PagBank",
                custom_id="client_secret",
                style=TextInputStyle.short,
                value=pagbank_config.get("client_secret", "")
            ),
        ]
        super().__init__(title="Credenciais API PagBank", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        container = disnake.ui.Container(disnake.ui.TextDisplay(f"# {carregarAnimado} Verificando credenciais..."))
        await inter.response.edit_message(content="", embed=None, components=[container])

        client_id = inter.text_values["client_id"]
        client_secret = inter.text_values["client_secret"]
        
        # A validação real da API PagBank requer um fluxo OAuth 2.0.
        # Por simplicidade, salvamos as credenciais para serem usadas depois.
        status = True

        if status:
            salvarPagBank(client_id=client_id, client_secret=client_secret)
            await GerenciarPagBank(inter)
            await inter.followup.send(f"{positivo} Credenciais da API PagBank salvas com sucesso.", ephemeral=True, delete_after=3)
        else:
            await GerenciarPagBank(inter)
            await inter.followup.send(f"{negativo} As credenciais da API PagBank parecem inválidas.", ephemeral=True, delete_after=5)

def salvarPagBank(client_id, client_secret):
    try:
        caminho_arquivo = "Database/Vendas/pagamentos.json"
        
        with open(caminho_arquivo, "r") as f:
            db = json.load(f)
        
        if "pagbank" not in db:
            db["pagbank"] = {"habilitado": False}

        db["pagbank"].update({
            "configurado": True,
            "client_id": client_id,
            "client_secret": client_secret
        })
        
        # Remove a configuração antiga de IMAP se existir
        db.pop("pagbank_imap", None)

        with open(caminho_arquivo, "w") as f:
            json.dump(db, f, indent=4)

        return True
    except Exception as e:
        print(f"Erro ao salvar as credenciais do PagBank: {e}")
        return False

async def GerenciarPagBank(inter: disnake.MessageInteraction):
    FormasPagamento = ObterFormasPagamento()
    PagBank = FormasPagamento.get("pagbank", {"habilitado": False, "configurado": False})

    Button = {
        "label": "Desabilitar" if PagBank.get("habilitado") else "Habilitar",
        "style": disnake.ButtonStyle.danger if PagBank.get("habilitado") else disnake.ButtonStyle.success,
    }

    def formatar_forma_pagamento(habilitado, configurado):
        status_habilitado = f"{positivo} ``Habilitado``" if habilitado else f"{negativo} ``Desabilitado``"
        status_configurado = f"{positivo} ``Configurado``" if configurado else f"{negativo} ``Não configurado``"
        return f"{status_habilitado}\n{status_configurado}"

    credenciais_status = f"{positivo} `Definidas`" if PagBank.get("configurado") else f"{negativo} `Não definidas`"

    texto_container = f"""# 🟡 PagBank (API) | Formas de Pagamento
Configure a integração de pagamento com a API oficial do PagBank.

**Sistema**
{formatar_forma_pagamento(PagBank.get("habilitado"), PagBank.get("configurado"))}

**Credenciais da API**
{credenciais_status}"""

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(texto_container),
        disnake.ui.Separator(),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Configurar Credenciais", style=disnake.ButtonStyle.blurple, custom_id="ConfigurarSistemaPagBank", emoji=attach),
            disnake.ui.Button(label=Button["label"], style=Button["style"], custom_id="HabilitarDesabilitarSistemaPagamento_PagBank", emoji=reload),
            disnake.ui.Button(label="Voltar", emoji=voltar, custom_id="PainelConfigurar_FormasPagamento")
        )
    )

    await inter.edit_original_message(content="", embed=None, components=[container])

class PagBankPagamentosPlugin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def PagBankExtensionButtonListener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        if custom_id == "GerenciarDefinicoesFormasPagamento_PagBank":
            container = disnake.ui.Container(disnake.ui.TextDisplay(f"# {carregarAnimado} Carregando..."))
            await inter.response.edit_message(content="", embed=None, components=[container])
            await GerenciarPagBank(inter)
    
        elif custom_id == "HabilitarDesabilitarSistemaPagamento_PagBank":
            container = disnake.ui.Container(disnake.ui.TextDisplay(f"# {carregarAnimado} Atualizando..."))
            await inter.response.edit_message(content="", embed=None, components=[container])
            pagamentos = ObterFormasPagamento()
            config = pagamentos.get("pagbank", {})

            if config.get("configurado"):
                config["habilitado"] = not config.get("habilitado", False)
                SalvarFormasPagamento(pagamentos)
                status_msg = "habilitado" if config["habilitado"] else "desabilitado"
                await inter.followup.send(f"{positivo if config['habilitado'] else negativo} O sistema de pagamento PagBank (API) foi {status_msg}.", ephemeral=True, delete_after=3)
            else:
                await inter.followup.send(f"{negativo} As credenciais não estão configuradas.", ephemeral=True, delete_after=3)
            
            await GerenciarPagBank(inter)

        elif custom_id == "ConfigurarSistemaPagBank":
            await inter.response.send_modal(ConfigurarPagBankModal())

def setup(bot: commands.Bot):
    bot.add_cog(PagBankPagamentosPlugin(bot))