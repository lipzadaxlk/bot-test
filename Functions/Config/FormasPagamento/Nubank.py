import disnake
from disnake import *
from disnake.ext import commands
import json
from datetime import *

from Functions.CarregarEmojis import *
from Functions.Config.FormasPagamentos import ObterFormasPagamento, SalvarFormasPagamento

# --- Funções do Painel de Configuração Nubank ---

class NubankIMAPModal(disnake.ui.Modal):
    def __init__(self):
        pagamentos = ObterFormasPagamento()
        nubank_config = pagamentos.get("nubank_imap", {})
        components = [
            disnake.ui.TextInput(
                label="Email do GMAIL para o IMAP",
                custom_id="email",
                placeholder="exemplo@gmail.com",
                value=nubank_config.get("email", "")
            ),
            disnake.ui.TextInput(
                label="Senha de Aplicativo do GMAIL",
                custom_id="senha",
                placeholder="É a senha de 16 dígitos gerada pelo Google",
                style=TextInputStyle.short
            ),
            # Adicionado campo para chave PIX, essencial para gerar o pagamento
            disnake.ui.TextInput(
                label="Sua Chave PIX (Aleatória, CPF, etc.)",
                custom_id="chave_pix",
                placeholder="Chave PIX que receberá os pagamentos",
                value=nubank_config.get("chave_pix", "")
            ),
        ]
        super().__init__(title="Configurar Credenciais Nubank IMAP", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        email = inter.text_values["email"]
        senha = inter.text_values["senha"]
        chave_pix = inter.text_values["chave_pix"]

        if not all([email, senha, chave_pix]):
            await inter.response.send_message(f"{negativo} Todos os campos são obrigatórios.", ephemeral=True)
            return
        
        pagamentos = ObterFormasPagamento()
        if "nubank_imap" not in pagamentos: 
            pagamentos["nubank_imap"] = {}
        
        pagamentos["nubank_imap"].update({
            "habilitado": pagamentos["nubank_imap"].get("habilitado", False),
            "configurado": True,
            "email": email,
            "senha": senha,
            "chave_pix": chave_pix
        })
        
        SalvarFormasPagamento(pagamentos)
        await inter.response.send_message(f"{positivo} Credenciais do Nubank (IMAP) salvas!", ephemeral=True, delete_after=3)
        
        await GerenciarNubankIMAP(inter)

async def GerenciarNubankIMAP(inter: disnake.MessageInteraction):
    pagamentos = ObterFormasPagamento()
    nubank = pagamentos.get("nubank_imap", {"habilitado": False, "configurado": False})

    status_habilitado = f"{positivo} ``Habilitado``" if nubank.get("habilitado") else f"{negativo} ``Desabilitado``"
    status_configurado = f"{positivo} ``Configurado``" if nubank.get("configurado") else f"{negativo} ``Não Configurado``"
    
    email_display = f"`{nubank.get('email')}`" if nubank.get('email') else f"{negativo} `Não definido`"
    senha_display = f"{positivo} `Definida`" if nubank.get('senha') else f"{negativo} `Não definida`"
    chave_display = f"{positivo} `Definida`" if nubank.get('chave_pix') else f"{negativo} `Não definida`"

    texto_container = "# 🟣 Nubank (IMAP) | Formas de Pagamento\n"
    texto_container += "Gerencie a forma de pagamento automática via leitura de e-mails do Nubank.\n\n"
    texto_container += f"**Status do Módulo**\n{status_habilitado}\n\n"
    texto_container += f"**Status da Configuração**\n{status_configurado}\n\n"
    texto_container += f"**Email (IMAP)**\n{email_display}\n\n"
    texto_container += f"**Senha de App (IMAP)**\n{senha_display}\n\n"
    texto_container += f"**Chave PIX**\n{chave_display}"

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(texto_container),
        disnake.ui.Separator(),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Habilitar" if not nubank.get("habilitado") else "Desabilitar",
                style=disnake.ButtonStyle.green if not nubank.get("habilitado") else disnake.ButtonStyle.red,
                custom_id="HabilitarPagamento_nubank_imap",
                emoji=reload
            ),
            disnake.ui.Button(
                label="Configurar Credenciais",
                style=disnake.ButtonStyle.blurple,
                emoji=editar,
                custom_id="ConfigurarCredenciais_NubankIMAP"
            ),
            disnake.ui.Button(
                label="Voltar",
                style=disnake.ButtonStyle.grey,
                emoji=voltar,
                custom_id="PainelConfigurar_FormasPagamento"
            )
        )
    )
    
    await inter.edit_original_message(content="", embed=None, components=[container])


# --- Cog do Plugin ---
class NubankPagamentosPlugin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def NubankExtensionButtonListener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id

        if custom_id == "GerenciarDefinicoesFormasPagamento_NubankIMAP":
            container = disnake.ui.Container(disnake.ui.TextDisplay(f"# {carregarAnimado} Carregando..."))
            await inter.response.edit_message(content="", embed=None, components=[container])
            await GerenciarNubankIMAP(inter)
    
        elif custom_id == "HabilitarPagamento_nubank_imap":
            container = disnake.ui.Container(disnake.ui.TextDisplay(f"# {carregarAnimado} Carregando..."))
            await inter.response.edit_message(content="", embed=None, components=[container])
            pagamentos = ObterFormasPagamento()
            nubank_config = pagamentos.get("nubank_imap", {})

            if nubank_config.get("configurado"):
                nubank_config["habilitado"] = not nubank_config.get("habilitado", False)
                SalvarFormasPagamento(pagamentos)
                if nubank_config["habilitado"]:
                    await inter.followup.send(f"{positivo} O sistema de pagamento Nubank (IMAP) foi habilitado.", ephemeral=True, delete_after=3)
                else:
                    await inter.followup.send(f"{negativo} O sistema de pagamento Nubank (IMAP) foi desabilitado.", ephemeral=True, delete_after=3)
            else:
                await inter.followup.send(f"{negativo} As credenciais não estão configuradas.", ephemeral=True, delete_after=3)
            
            await GerenciarNubankIMAP(inter)

        elif custom_id == "ConfigurarCredenciais_NubankIMAP":
            await inter.response.send_modal(NubankIMAPModal())

def setup(bot: commands.Bot):
    bot.add_cog(NubankPagamentosPlugin(bot))