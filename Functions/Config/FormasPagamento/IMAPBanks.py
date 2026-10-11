import disnake
from disnake import *
from disnake.ext import commands
import json
from datetime import *

from Functions.CarregarEmojis import *
from Functions.Config.FormasPagamentos import ObterFormasPagamento, SalvarFormasPagamento

BANCOS_IMAP = {
    "itau": {"nome": "Itaú", "cor": 0xEC7000},
    "santander": {"nome": "Santander", "cor": 0xEC0000},
    "bradesco": {"nome": "Bradesco", "cor": 0xFF0000},
}

class IMAPBankModal(disnake.ui.Modal):
    def __init__(self, bank_key: str):
        self.bank_key = bank_key
        banco_info = BANCOS_IMAP[bank_key]
        pagamentos = ObterFormasPagamento()
        config = pagamentos.get(f"{bank_key}_imap", {})
        
        components = [
            disnake.ui.TextInput(label="Email para o IMAP", custom_id="email", placeholder=f"Email que recebe notificações do {banco_info['nome']}", value=config.get("email", "")),
            disnake.ui.TextInput(label="Senha de Aplicativo do Email", custom_id="senha", placeholder="Senha do seu provedor de email", style=TextInputStyle.short),
            disnake.ui.TextInput(label="Sua Chave PIX", custom_id="chave_pix", placeholder="Chave PIX que receberá os pagamentos", value=config.get("chave_pix", "")),
        ]
        super().__init__(title=f"Credenciais {banco_info['nome']} IMAP", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        container = disnake.ui.Container(disnake.ui.TextDisplay(f"# {carregarAnimado} Salvando credenciais..."))
        await inter.response.edit_message(content="", embed=None, components=[container])
        pagamentos = ObterFormasPagamento()
        config_key = f"{self.bank_key}_imap"
        if config_key not in pagamentos: pagamentos[config_key] = {"habilitado": False}
        
        pagamentos[config_key].update({
            "configurado": True,
            "email": inter.text_values["email"],
            "senha": inter.text_values["senha"],
            "chave_pix": inter.text_values["chave_pix"]
        })
        SalvarFormasPagamento(pagamentos)
        await GerenciarIMAPBank(inter, self.bank_key)
        await inter.followup.send(f"{positivo} Credenciais salvas.", ephemeral=True, delete_after=3)

async def GerenciarIMAPBank(inter: disnake.MessageInteraction, bank_key: str):
    banco_info = BANCOS_IMAP[bank_key]
    pagamentos = ObterFormasPagamento()
    config = pagamentos.get(f"{bank_key}_imap", {"habilitado": False, "configurado": False})

    status_habilitado = f"{positivo} ``Habilitado``" if config.get("habilitado") else f"{negativo} ``Desabilitado``"
    status_configurado = f"{positivo} ``Configurado``" if config.get("configurado") else f"{negativo} ``Não configurado``"

    texto_container = f"""# 🏦 {banco_info['nome']} (IMAP) | Formas de Pagamento
Gerencie a integração com o {banco_info['nome']} via IMAP para monitoramento de PIX.

**Status do Módulo**
{status_habilitado}

**Status da Configuração**
{status_configurado}"""

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(texto_container),
        disnake.ui.Separator(),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Habilitar" if not config.get("habilitado") else "Desabilitar", style=disnake.ButtonStyle.green if not config.get("habilitado") else disnake.ButtonStyle.red, custom_id=f"HabilitarPagamento_{bank_key}_imap"),
            disnake.ui.Button(label="Configurar Credenciais", style=disnake.ButtonStyle.blurple, custom_id=f"ConfigurarCredenciais_{bank_key.capitalize()}IMAP"),
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=voltar, custom_id="PainelConfigurar_FormasPagamento")
        )
    )
    
    await inter.edit_original_message(content="", embed=None, components=[container])

class IMAPBanksPlugin(commands.Cog):
    def __init__(self, bot: commands.Bot): self.bot = bot
    @commands.Cog.listener("on_button_click")
    async def IMAPButtonListener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        for key in BANCOS_IMAP.keys():
            if custom_id == f"GerenciarDefinicoesFormasPagamento_{key.capitalize()}IMAP":
                container = disnake.ui.Container(disnake.ui.TextDisplay(f"# {carregarAnimado} Carregando..."))
                await inter.response.edit_message(content="", embed=None, components=[container])
                await GerenciarIMAPBank(inter, key)
                return
            elif custom_id == f"HabilitarPagamento_{key}_imap":
                pagamentos = ObterFormasPagamento(); config = pagamentos.get(f"{key}_imap", {})
                if config.get("configurado"): config["habilitado"] = not config.get("habilitado", False); SalvarFormasPagamento(pagamentos)
                await GerenciarIMAPBank(inter, key)
                return
            elif custom_id == f"ConfigurarCredenciais_{key.capitalize()}IMAP":
                await inter.response.send_modal(IMAPBankModal(key))
                return
def setup(bot: commands.Bot): bot.add_cog(IMAPBanksPlugin(bot))