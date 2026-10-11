import disnake
from disnake import *
from disnake.ext import commands
import json
import requests
from datetime import *

from Functions.CarregarEmojis import *
from Functions.Config.FormasPagamentos import *

# URL da API da Asaas
ASAAS_API_URL = "https://api.asaas.com/v3/"

class ConfigurarAsaasModal(disnake.ui.Modal):
    def __init__(self):
        pagamentos = ObterFormasPagamento()
        asaas_config = pagamentos.get("asaas", {})
        
        components = [
            disnake.ui.TextInput(
                label="Asaas API Key",
                placeholder="Sua chave de API da Asaas",
                custom_id="asaas_api_key",
                style=TextInputStyle.short,
                value=asaas_config.get("api_key", "")
            ),
        ]
        super().__init__(title="Credenciais Asaas", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        container = disnake.ui.Container(disnake.ui.TextDisplay(f"# {carregarAnimado} Verificando credenciais..."))
        await inter.response.edit_message(content="", embed=None, components=[container])

        api_key = inter.text_values["asaas_api_key"]
        
        # Tenta verificar a chave da API fazendo uma requisição simples
        headers = {"access_token": api_key}
        response = requests.get(f"{ASAAS_API_URL}/my-account", headers=headers)

        if response.status_code == 200:
            salvarAsaas(api_key=api_key)
            await GerenciarAsaas(inter)
            await inter.followup.send(f"{positivo} Credenciais da Asaas salvas e validadas com sucesso.", ephemeral=True, delete_after=3)
        else:
            await GerenciarAsaas(inter)
            await inter.followup.send(f"{negativo} A Chave da API da Asaas parece inválida. Verifique e tente novamente.", ephemeral=True, delete_after=5)

def salvarAsaas(api_key):
    try:
        caminho_arquivo = "Database/Vendas/pagamentos.json"
        
        with open(caminho_arquivo, "r") as f:
            db = json.load(f)
        
        if "asaas" not in db:
            db["asaas"] = {"habilitado": False}

        db["asaas"].update({
            "configurado": True,
            "api_key": api_key
        })

        with open(caminho_arquivo, "w") as f:
            json.dump(db, f, indent=4)

        return True
    except Exception as e:
        print(f"Erro ao salvar as credenciais da Asaas: {e}")
        return False

async def GerenciarAsaas(inter: disnake.MessageInteraction):
    FormasPagamento = ObterFormasPagamento()
    Asaas = FormasPagamento.get("asaas", {"habilitado": False, "configurado": False, "api_key": None})

    Button = {
        "label": "Desabilitar" if Asaas.get("habilitado") else "Habilitar",
        "style": disnake.ButtonStyle.danger if Asaas.get("habilitado") else disnake.ButtonStyle.success,
    }

    def formatar_forma_pagamento(habilitado, configurado):
        status_habilitado = f"{positivo} ``Habilitado``" if habilitado else f"{negativo} ``Desabilitado``"
        status_configurado = f"{positivo} ``Configurado``" if configurado else f"{negativo} ``Não configurado``"
        return f"{status_habilitado}\n{status_configurado}"

    api_key_status = f"{positivo} `Definida`" if Asaas.get("api_key") else f"{negativo} `Não definida`"

    texto_container = f"""# 🔵 Asaas | Formas de Pagamento
Configure a integração de pagamento com a Asaas.

**Sistema**
{formatar_forma_pagamento(Asaas.get("habilitado"), Asaas.get("configurado"))}

**API Key**
{api_key_status}"""

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(texto_container),
        disnake.ui.Separator(),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Configurar Credenciais", style=disnake.ButtonStyle.blurple, custom_id="ConfigurarSistemaAsaas", emoji=attach),
            disnake.ui.Button(label=Button["label"], style=Button["style"], custom_id="HabilitarDesabilitarSistemaPagamento_Asaas", emoji=reload),
            disnake.ui.Button(label="Voltar", emoji=voltar, custom_id="PainelConfigurar_FormasPagamento")
        )
    )

    await inter.edit_original_message(content="", embed=None, components=[container])

class AsaasPagamentosPlugin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def AsaasExtensionButtonListener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        if custom_id == "GerenciarDefinicoesFormasPagamento_Asaas":
            container = disnake.ui.Container(disnake.ui.TextDisplay(f"# {carregarAnimado} Carregando..."))
            await inter.response.edit_message(content="", embed=None, components=[container])
            await GerenciarAsaas(inter)
    
        elif custom_id == "HabilitarDesabilitarSistemaPagamento_Asaas":
            container = disnake.ui.Container(disnake.ui.TextDisplay(f"# {carregarAnimado} Atualizando..."))
            await inter.response.edit_message(content="", embed=None, components=[container])
            pagamentos = ObterFormasPagamento()
            asaas_config = pagamentos.get("asaas", {})

            if asaas_config.get("configurado"):
                asaas_config["habilitado"] = not asaas_config.get("habilitado", False)
                SalvarFormasPagamento(pagamentos)
                if asaas_config["habilitado"]:
                    await inter.followup.send(f"{positivo} O sistema de pagamento Asaas foi habilitado.", ephemeral=True, delete_after=3)
                else:
                    await inter.followup.send(f"{negativo} O sistema de pagamento Asaas foi desabilitado.", ephemeral=True, delete_after=3)
            else:
                await inter.followup.send(f"{negativo} As credenciais não estão configuradas.", ephemeral=True, delete_after=3)
            
            await GerenciarAsaas(inter)

        elif custom_id == "ConfigurarSistemaAsaas":
            await inter.response.send_modal(ConfigurarAsaasModal())

def setup(bot: commands.Bot):
    bot.add_cog(AsaasPagamentosPlugin(bot))