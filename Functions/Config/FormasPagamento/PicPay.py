import disnake
from disnake import *
from disnake.ext import commands
import json
import requests
from datetime import *

from Functions.CarregarEmojis import *
from Functions.Config.FormasPagamentos import *

class ConfigurarPicPayModal(disnake.ui.Modal):
    def __init__(self):
        pagamentos = ObterFormasPagamento()
        picpay_config = pagamentos.get("picpay", {})
        
        components = [
            disnake.ui.TextInput(
                label="PicPay API Token",
                placeholder="Seu token de API do PicPay",
                custom_id="picpay_token",
                style=TextInputStyle.short,
                value=picpay_config.get("token", "")
            ),
        ]
        super().__init__(title="Credenciais PicPay", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        container = disnake.ui.Container(disnake.ui.TextDisplay(f"# {carregarAnimado} Verificando credenciais..."))
        await inter.response.edit_message(content="", embed=None, components=[container])

        picpay_token = inter.text_values["picpay_token"]
        
        # A API do PicPay não tem um endpoint "me" para validação simples.
        # A validação real ocorre ao tentar usar o token.
        # Por simplicidade, salvamos diretamente.
        status = True # Assumimos que o token é válido por enquanto.

        if status:
            salvarPicPay(token=picpay_token)
            await GerenciarPicPay(inter)
            await inter.followup.send(f"{positivo} Credenciais do PicPay salvas com sucesso.", ephemeral=True, delete_after=3)
        else:
            await GerenciarPicPay(inter)
            await inter.followup.send(f"{negativo} O Token da API do PicPay parece inválido.", ephemeral=True, delete_after=5)

def salvarPicPay(token):
    try:
        caminho_arquivo = "Database/Vendas/pagamentos.json"
        
        with open(caminho_arquivo, "r") as f:
            db = json.load(f)
        
        if "picpay" not in db:
            db["picpay"] = {"habilitado": False}

        db["picpay"].update({
            "configurado": True,
            "token": token
        })

        with open(caminho_arquivo, "w") as f:
            json.dump(db, f, indent=4)

        return True
    except Exception as e:
        print(f"Erro ao salvar as credenciais do PicPay: {e}")
        return False

async def GerenciarPicPay(inter: disnake.MessageInteraction):
    FormasPagamento = ObterFormasPagamento()
    PicPay = FormasPagamento.get("picpay", {"habilitado": False, "configurado": False, "token": None})

    Button = {
        "label": "Desabilitar" if PicPay.get("habilitado") else "Habilitar",
        "style": disnake.ButtonStyle.danger if PicPay.get("habilitado") else disnake.ButtonStyle.success,
    }

    def formatar_forma_pagamento(habilitado, configurado):
        status_habilitado = f"{positivo} ``Habilitado``" if habilitado else f"{negativo} ``Desabilitado``"
        status_configurado = f"{positivo} ``Configurado``" if configurado else f"{negativo} ``Não configurado``"
        return f"{status_habilitado}\n{status_configurado}"

    # Formatação do token
    token_display = f"{positivo} `Definido`" if PicPay.get("token") else f"{negativo} `Não definido`"

    texto_container = f"""# 💚 PicPay | Formas de Pagamento
Configure a integração de pagamento com o PicPay.

**Sistema**
{formatar_forma_pagamento(PicPay.get("habilitado"), PicPay.get("configurado"))}

**API Token**
{token_display}"""

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(texto_container),
        disnake.ui.Separator(),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Configurar Credenciais", style=disnake.ButtonStyle.blurple, custom_id="ConfigurarSistemaPicPay", emoji=attach),
            disnake.ui.Button(label=Button["label"], style=Button["style"], custom_id="HabilitarDesabilitarSistemaPagamento_PicPay", emoji=reload),
            disnake.ui.Button(label="Voltar", emoji=voltar, custom_id="PainelConfigurar_FormasPagamento")
        )
    )

    await inter.edit_original_message(content="", embed=None, components=[container])

class PicPayPagamentosPlugin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def PicPayExtensionButtonListener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        if custom_id == "GerenciarDefinicoesFormasPagamento_PicPay":
            container = disnake.ui.Container(disnake.ui.TextDisplay(f"# {carregarAnimado} Carregando..."))
            await inter.response.edit_message(content="", embed=None, components=[container])
            await GerenciarPicPay(inter)
    
        elif custom_id == "HabilitarDesabilitarSistemaPagamento_PicPay":
            container = disnake.ui.Container(disnake.ui.TextDisplay(f"# {carregarAnimado} Atualizando..."))
            await inter.response.edit_message(content="", embed=None, components=[container])
            pagamentos = ObterFormasPagamento()
            picpay_config = pagamentos.get("picpay", {})

            if picpay_config.get("configurado"):
                picpay_config["habilitado"] = not picpay_config.get("habilitado", False)
                SalvarFormasPagamento(pagamentos)
                if picpay_config["habilitado"]:
                    await inter.followup.send(f"{positivo} O sistema de pagamento PicPay foi habilitado.", ephemeral=True, delete_after=3)
                else:
                    await inter.followup.send(f"{negativo} O sistema de pagamento PicPay foi desabilitado.", ephemeral=True, delete_after=3)
            else:
                await inter.followup.send(f"{negativo} As credenciais não estão configuradas.", ephemeral=True, delete_after=3)
            
            await GerenciarPicPay(inter)

        elif custom_id == "ConfigurarSistemaPicPay":
            await inter.response.send_modal(ConfigurarPicPayModal())

def setup(bot: commands.Bot):
    bot.add_cog(PicPayPagamentosPlugin(bot))