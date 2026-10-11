# Nome do Arquivo: Definicoes.py
import disnake
from disnake.ext import commands
from disnake import Colour

from datetime import *
import json
import re
import uuid
import requests
import os
import asyncio
from functools import partial

from Functions.CarregarEmojis import *
from Functions.VerificarPerms import *
from Functions.GerenciarCargosCanais import *
from Functions.Config.FormasPagamentos import *

# Importe a cog principal de Condecoração para chamar a função de concessão
from Commands.Admin.Plugins.Condecoracao import ObterDatabaseCondecoracao, CondecoracaoCommand

# --- IMPORTAÇÃO DOS PAINÉIS DE GERENCIAMENTO DE PAGAMENTO ---
from Functions.Config.FormasPagamento.MercadoPago import GerenciarMercadoPago
from Functions.Config.FormasPagamento.PagBank import GerenciarPagBank
from Functions.Config.FormasPagamento.EFIBank import GerenciarEfi
from Functions.Config.FormasPagamento.Asaas import GerenciarAsaas
from Functions.Config.FormasPagamento.Stripe import GerenciarStripe
from Functions.Config.FormasPagamento.PicPay import GerenciarPicPay
from Functions.Config.FormasPagamento.LivePix import GerenciarLivePix
from Functions.Config.FormasPagamento.Inter import GerenciarInter
from Functions.Config.FormasPagamento.C6 import GerenciarC6
from Functions.Config.FormasPagamento.Nubank import GerenciarNubankIMAP
from Functions.Config.FormasPagamento.IMAPBanks import GerenciarIMAPBank
from Functions.Config.FormasPagamento.SemiAuto import GerenciarSemiAuto
# -------------------------------------------------------------

API_URL = "https://ecloudxesteerdaocu.squareweb.app/"

# Metadados para todos os tipos de log. Usado para construir a UI e criar canais.
# A estrutura do canais.json permanece simples: {"key": "id"}
LOG_METADATA = {
    # Geral (do arquivo antigo, mantido para compatibilidade)
    "logs": {"nome": "Logs Gerais", "emoji": "📜", "categoria": "Geral"},
    "vendas": {"nome": "Vendas", "emoji": "🛒", "categoria": "Geral"},
    "boasvindas": {"nome": "Boas-Vindas", "emoji": "👋", "categoria": "Geral"},
    "sistema": {"nome": "Logs do Sistema", "emoji": "🤖", "categoria": "Geral"},
    "antifake": {"nome": "Logs Anti-Fake", "emoji": "🛡️", "categoria": "Geral"},
    "tickets": {"nome": "Logs de Tickets", "emoji": "🎟️", "categoria": "Geral"},
    "logsformulario": {"nome": "Logs de Formulários", "emoji": "📝", "categoria": "Geral"},
    "feedbacks": {"nome": "Feedbacks", "emoji": "⭐", "categoria": "Geral"},
    "verificados": {"nome": "Verificados (eCloud)", "emoji": "☁️", "categoria": "Geral"},
    # Logs de Mensagens
    "mensagem_deletada": {"nome": "Mensagem Deletada", "emoji": "🗑️", "categoria": "Mensagens"},
    "mensagem_editada": {"nome": "Mensagem Editada", "emoji": "✏️", "categoria": "Mensagens"},
    "mensagem_bulk_delete": {"nome": "Bulk Delete", "emoji": "🧹", "categoria": "Mensagens"},
    "reaction_add": {"nome": "Reação Adicionada", "emoji": "➕", "categoria": "Mensagens"},
    "reaction_remove": {"nome": "Reação Removida", "emoji": "➖", "categoria": "Mensagens"},
    # Logs de Membros
    "membro_entrou": {"nome": "Membro Entrou", "emoji": "📥", "categoria": "Membros"},
    "membro_saiu": {"nome": "Membro Saiu", "emoji": "📤", "categoria": "Membros"},
    "membro_update": {"nome": "Membro Atualizado", "emoji": "🔄", "categoria": "Membros"},
    "nick_change": {"nome": "Nick Alterado", "emoji": "🏷️", "categoria": "Membros"},
    "avatar_change": {"nome": "Avatar Alterado", "emoji": "🖼️", "categoria": "Membros"},
    # Logs de Cargos
    "cargo_add": {"nome": "Cargo Adicionado a Membro", "emoji": "🎭", "categoria": "Cargos"},
    "cargo_remove": {"nome": "Cargo Removido de Membro", "emoji": "🚫", "categoria": "Cargos"},
    "cargo_create": {"nome": "Cargo Criado", "emoji": "✨", "categoria": "Cargos"},
    "cargo_delete": {"nome": "Cargo Deletado", "emoji": "🗑️", "categoria": "Cargos"},
    "cargo_update": {"nome": "Cargo Atualizado", "emoji": "🔧", "categoria": "Cargos"},
    # Logs de Canais
    "canal_create": {"nome": "Canal Criado", "emoji": "📋", "categoria": "Canais"},
    "canal_delete": {"nome": "Canal Deletado", "emoji": "🗑️", "categoria": "Canais"},
    "canal_update": {"nome": "Canal Atualizado", "emoji": "⚙️", "categoria": "Canais"},
    # Logs de Voice
    "voice_join": {"nome": "Entrou na Call", "emoji": "🔊", "categoria": "Voz"},
    "voice_leave": {"nome": "Saiu da Call", "emoji": "🔇", "categoria": "Voz"},
    "voice_move": {"nome": "Movido na Call", "emoji": "🔀", "categoria": "Voz"},
    "voice_mute": {"nome": "Mutado na Call", "emoji": "🎤", "categoria": "Voz"},
    "voice_deafen": {"nome": "Ensurdecido na Call", "emoji": "🎧", "categoria": "Voz"},
    # Logs de Servidor
    "server_update": {"nome": "Servidor Atualizado", "emoji": "🏠", "categoria": "Servidor"},
    "emoji_create": {"nome": "Emoji Criado", "emoji": "😀", "categoria": "Servidor"},
    "emoji_delete": {"nome": "Emoji Deletado", "emoji": "❌", "categoria": "Servidor"},
    "emoji_update": {"nome": "Emoji Atualizado", "emoji": "🔄", "categoria": "Servidor"},
    # Logs de Convites
    "invite_create": {"nome": "Convite Criado", "emoji": "📬", "categoria": "Convites"},
    "invite_delete": {"nome": "Convite Deletado", "emoji": "🗑️", "categoria": "Convites"},
    # Logs de Moderação
    "ban": {"nome": "Banimento", "emoji": "🔨", "categoria": "Moderação"},
    "unban": {"nome": "Desbanimento", "emoji": "🔓", "categoria": "Moderação"},
    "kick": {"nome": "Expulsão", "emoji": "👢", "categoria": "Moderação"},
    "timeout": {"nome": "Castigo", "emoji": "⏰", "categoria": "Moderação"},
}

def ObterAuthLocalECloud():
    caminho = "Database/eCloud/auth_config.json"
    if not os.path.exists(caminho): return {}
    try:
        with open(caminho, 'r', encoding='utf-8') as f: return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError): return {}

def ObterSalvarSintaxeLogs(nova_sintaxe=None):
    caminho = "Database/Server/logs_syntax.json"
    default_syntax = "{emoji}┃{nome}"
    if nova_sintaxe is not None:
        with open(caminho, 'w', encoding='utf-8') as f: json.dump({"channel_name_syntax": nova_sintaxe}, f, indent=4)
        return nova_sintaxe
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("channel_name_syntax", default_syntax)
    except (FileNotFoundError, json.JSONDecodeError):
        with open(caminho, 'w', encoding='utf-8') as f: json.dump({"channel_name_syntax": default_syntax}, f, indent=4)
        return default_syntax

async def notificar_api_canal_verificados(bot: commands.Bot, channel_id: str | None, guild_id: str, webhook_url: str | None = None):
    auth_local = ObterAuthLocalECloud()
    authorization = auth_local.get("authorization")
    if not authorization:
        return False, "O token de autorização da API do eCloud não foi encontrado."
    headers = {"authorization": authorization, "Content-Type": "application/json"}
    payload = {"guild_id": str(guild_id), "log_channel_verified": channel_id, "webhook_url": webhook_url}
    try:
        func = partial(requests.post, url=f"{API_URL}config/guild-update", headers=headers, json=payload, timeout=10)
        response = await bot.loop.run_in_executor(None, func)
        if response.status_code == 200: return True, "API atualizada com sucesso."
        else:
            msg = response.json().get('message', response.text)
            return False, f"Falha ao notificar a API: {msg}"
    except requests.exceptions.RequestException as e: return False, "Não foi possível conectar à API para atualizar a configuração do canal."

async def gerenciar_webhook_canal_verificados(bot: commands.Bot, canal_id: str | None, guild_id: str):
    try:
        logs_verificacao_cog = bot.get_cog("LogsVerificacao")
        if not logs_verificacao_cog: return False, "Sistema de logs não encontrado"
        if canal_id is None:
            await logs_verificacao_cog.remover_webhook(None)
            return True, "Webhook removida com sucesso"
        webhook_url = await logs_verificacao_cog.criar_webhook_para_canal(canal_id)
        if webhook_url: return True, "Webhook criada com sucesso"
        else: return False, "Erro ao criar webhook"
    except Exception as e: return False, f"Erro ao gerenciar webhook: {str(e)}"

def ObterComponentsPainelInicial():
    texto_container = f"""# {config2} Definições do Servidor
-# Configure canais, cargos, anti-fake e formas de pagamento."""
    
    container = disnake.ui.Container(
        disnake.ui.TextDisplay(texto_container),
        disnake.ui.Separator(),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Canais", emoji=canal, custom_id="PainelConfigurar_Canais"),
            disnake.ui.Button(label="Cargos", emoji=cargo, custom_id="PainelConfigurar_Cargos")
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Anti Fake", emoji=users, custom_id="PainelConfigurar_AntiFake"),
            disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Formas de Pagamento", emoji=dollar, custom_id="PainelConfigurar_FormasPagamento")
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=voltar, custom_id="PainelInicial")
        )
    )
    
    return [container]

class AlterarAntiFakeModal(disnake.ui.Modal):
    def __init__(self):
        try:
            with open("Database/Server/antifake.json") as f: antifake = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError): antifake = {"quantidadeMinima": "", "nomesBloqueados": []}
        components = [
            disnake.ui.TextInput(label="Quantidade mínima de dias para entrar", placeholder="Deixe em branco para desativar.", custom_id="quantidademinima", style=disnake.TextInputStyle.short, required=False, value=str(antifake.get("quantidadeMinima", ""))),
            disnake.ui.TextInput(label="Lista de nomes que deseja bloquear", placeholder="Separe por linhas cada nome", custom_id="nomesbloqueados", style=disnake.TextInputStyle.paragraph, required=False, value="\n".join(antifake.get("nomesBloqueados", []))),
        ]
        super().__init__(title="Configurar Anti Fake", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        quantidademinima_str = inter.text_values["quantidademinima"]
        nomesbloqueados = inter.text_values["nomesbloqueados"].splitlines()
        quantidademinima = None
        if quantidademinima_str.strip():
            try: quantidademinima = int(quantidademinima_str)
            except ValueError: return await inter.response.send_message(f"{negativo} Você informou um número inválido para os dias. Tente novamente!", ephemeral=True)
        antifake = {"quantidadeMinima": quantidademinima, "nomesBloqueados": [nome for nome in nomesbloqueados if nome.strip()]}
        with open("Database/Server/antifake.json", "w", encoding="utf-8") as f: json.dump(antifake, f, indent=4, ensure_ascii=False)
        await inter.response.send_message(f"{positivo} As configurações foram salvas com sucesso.", ephemeral=True, delete_after=3)

class LogsSyntaxModal(disnake.ui.Modal):
    def __init__(self):
        sintaxe_atual = ObterSalvarSintaxeLogs()
        components = [
            disnake.ui.TextInput(label="Sintaxe do Nome do Canal de Log", placeholder="Ex: {emoji}┃{nome}", custom_id="syntax", style=disnake.TextInputStyle.short, value=sintaxe_atual, required=True),
            disnake.ui.TextInput(label="Variáveis Disponíveis", custom_id="variables", style=disnake.TextInputStyle.paragraph, value="- {emoji}: O emoji do tipo de log (ex: 🗑️)\n- {nome}: O nome do tipo de log (ex: mensagem-deletada)", required=False)
        ]
        super().__init__(title="Configurar Sintaxe dos Canais", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        nova_sintaxe = inter.text_values["syntax"]
        if "{nome}" not in nova_sintaxe:
            await inter.response.send_message(f"{negativo} A sintaxe deve conter `{{nome}}` para funcionar corretamente.", ephemeral=True)
            return
        ObterSalvarSintaxeLogs(nova_sintaxe=nova_sintaxe)
        await inter.response.send_message(f"{positivo} Sintaxe salva com sucesso!", ephemeral=True, delete_after=5)

class Canais():
    def ObterMensagemCanais(inter: disnake.MessageInteraction):
        canais = ObterCanais()
        
        # Construir texto das categorias
        categorias = {}
        for key, meta in LOG_METADATA.items():
            categoria = meta["categoria"]
            if categoria not in categorias:
                categorias[categoria] = []
            
            canal_formatado = f"<#{canais[key]}>" if key in canais and canais.get(key) else "Não definido"
            categorias[categoria].append(f"**{meta['nome']}:** {canal_formatado}")

        texto_categorias = ""
        for nome_categoria, lista_canais in sorted(categorias.items()):
            texto_categorias += f"\n**{nome_categoria}**\n" + "\n".join(lista_canais) + "\n"
        
        texto_container = f"""# {canal} Configurar Canais
Selecione um tipo de log nos menus abaixo para definir, alterar ou remover o canal correspondente.

{texto_categorias}"""

        log_items = list(LOG_METADATA.items())
        split_point = (len(log_items) + 1) // 2
        
        options1 = [disnake.SelectOption(label=meta["nome"], value=key) for key, meta in log_items[:split_point]]
        options2 = [disnake.SelectOption(label=meta["nome"], value=key) for key, meta in log_items[split_point:]]

        container = disnake.ui.Container(
            disnake.ui.TextDisplay(texto_container),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(placeholder="Selecione um log para configurar (Parte 1)", custom_id="ConfigurarDropdown_Canais_1", options=options1)
            ),
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(placeholder="Selecione um log para configurar (Parte 2)", custom_id="ConfigurarDropdown_Canais_2", options=options2)
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Syntax", emoji="✏️", style=disnake.ButtonStyle.secondary, custom_id="ConfigurarSintaxeLogs"),
                disnake.ui.Button(label="Criar Logs", emoji="🪄", style=disnake.ButtonStyle.success, custom_id="CriarTodosOsLogs"),
                disnake.ui.Button(label="Voltar", emoji=voltar, custom_id="GerenciarPainelConfigurar")
            )
        )

        return [container]

    async def GerenciarCanal(inter: disnake.MessageInteraction, canal_selecionado: str):
        canais = ObterCanais()
        canal_atual_id = canais.get(canal_selecionado.lower())
        metadata = LOG_METADATA.get(canal_selecionado, {})
        nome_canal = metadata.get("nome", canal_selecionado.capitalize())
        
        canal_atual = f"<#{canal_atual_id}>" if canal_atual_id else "Não definido"
        
        texto_container = f"""# {canal} Gerenciar Canal
**Tipo:** {nome_canal}
**Canal Atual:** {canal_atual}
-# Selecione um novo canal ou use as opções abaixo."""
        
        container = disnake.ui.Container(
            disnake.ui.TextDisplay(texto_container),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(placeholder="Selecione o novo canal desejado", custom_id=f"AlterarCanal_{canal_selecionado}", channel_types=[disnake.ChannelType.text])
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Remover", style=disnake.ButtonStyle.danger, emoji=apagar, custom_id=f"RemoverCanal_{canal_selecionado}", disabled=not canal_atual_id),
                disnake.ui.Button(label="Crie pra mim", emoji=wand, style=disnake.ButtonStyle.primary, custom_id=f"CriarCanal_{canal_selecionado}"),
                disnake.ui.Button(label="Voltar", emoji=voltar, style=disnake.ButtonStyle.secondary, custom_id="PainelConfigurar_Canais")
            )
        )
        
        await inter.response.edit_message(content="", embed=None, components=[container])

class Cargos():
    def ObterMensagemCargos(inter: disnake.MessageInteraction):
        cargos = ObterCargos()
        cargos_formatados = {key: f"<@&{valor}>" if valor else "Não definido" for key, valor in cargos.items()}
        
        texto_container = f"""# {cargo} Configurar Cargos
**Cargo de administrador:** {cargos_formatados['administrador']}
**Cargo de suporte:** {cargos_formatados['suporte']}
**Cargo de cliente:** {cargos_formatados['cliente']}
**Cargo de membro:** {cargos_formatados['membro']}
**Cargo verificado:** {cargos_formatados['verificado']}"""
        
        options = [
            disnake.SelectOption(label="Cargo de administrador", value="administrador", emoji=editar),
            disnake.SelectOption(label="Cargo de suporte", value="suporte", emoji=editar),
            disnake.SelectOption(label="Cargo de cliente", value="cliente", emoji=editar),
            disnake.SelectOption(label="Cargo de membro", value="membro", emoji=editar),
            disnake.SelectOption(label="Cargo de verificado", value="verificado", emoji=editar)
        ]
        
        container = disnake.ui.Container(
            disnake.ui.TextDisplay(texto_container),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(placeholder="Selecione um cargo para configurar", custom_id="ConfigurarDropdown_Cargos", options=options)
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=voltar, custom_id="GerenciarPainelConfigurar")
            )
        )
        
        return [container]

    async def GerenciarCargo(inter: disnake.MessageInteraction, cargo_selecionado: str):
        cargos = ObterCargos()
        cargo_atual_id = cargos.get(cargo_selecionado.lower(), None)
        cargo_atual = f"<@&{cargo_atual_id}>" if cargo_atual_id else "Não definido"
        
        texto_container = f"""# {cargo} Gerenciar Cargo
**Tipo:** Cargo de {cargo_selecionado}
**Cargo Atual:** {cargo_atual}
-# Selecione um novo cargo ou use as opções abaixo."""
        
        container = disnake.ui.Container(
            disnake.ui.TextDisplay(texto_container),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(
                disnake.ui.RoleSelect(placeholder="Selecione o novo cargo desejado", custom_id=f"AlterarCargo_{cargo_selecionado}")
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Remover", style=disnake.ButtonStyle.danger, emoji=apagar, custom_id=f"RemoverCargo_{cargo_selecionado}", disabled=not cargo_atual_id),
                disnake.ui.Button(label="Crie pra mim", emoji=wand, style=disnake.ButtonStyle.primary, custom_id=f"CriarCargo_{cargo_selecionado}"),
                disnake.ui.Button(label="Voltar", emoji=voltar, style=disnake.ButtonStyle.secondary, custom_id="PainelConfigurar_Cargos")
            )
        )
        
        await inter.response.edit_message(content="", embed=None, components=[container])

class Pagamentos():
    def ObterPainelFormasPagamento(inter: disnake.MessageInteraction):
        pagamentos = ObterFormasPagamento()
        gateways = {
            "mercadopago": pagamentos.get("mercadopago", {}), "efi": pagamentos.get("efi", {}), "asaas": pagamentos.get("asaas", {}), "pagbank": pagamentos.get("pagbank", {}),
            "stripe": pagamentos.get("stripe", {}), "picpay": pagamentos.get("picpay", {}), "livepix": pagamentos.get("livepix", {}), "inter": pagamentos.get("inter", {}),
            "c6": pagamentos.get("c6", {}), "nubank_imap": pagamentos.get("nubank_imap", {}), "itau_imap": pagamentos.get("itau_imap", {}),
            "santander_imap": pagamentos.get("santander_imap", {}), "bradesco_imap": pagamentos.get("bradesco_imap", {}), "semiauto": pagamentos.get("semiauto", {})
        }
        
        def formatar(habilitado, configurado): 
            hab_status = "✅ Habilitado" if habilitado else "❌ Desabilitado"
            conf_status = "✅ Configurado" if configurado else "❌ Não configurado"
            return f"{hab_status} | {conf_status}"
        
        texto_container = f"""# {dollar} Configurar Formas de Pagamento
Selecione um gateway de pagamento no menu abaixo para configurar.

**Mercado Pago:** {formatar(gateways["mercadopago"].get("habilitado"), gateways["mercadopago"].get("configurado"))}
**PagBank:** {formatar(gateways["pagbank"].get("habilitado"), gateways["pagbank"].get("configurado"))}
**Efí Bank:** {formatar(gateways["efi"].get("habilitado"), gateways["efi"].get("configurado"))}
**Asaas:** {formatar(gateways["asaas"].get("habilitado"), gateways["asaas"].get("configurado"))}
**Stripe:** {formatar(gateways["stripe"].get("habilitado"), gateways["stripe"].get("configurado"))}
**PicPay:** {formatar(gateways["picpay"].get("habilitado"), gateways["picpay"].get("configurado"))}
**LivePix:** {formatar(gateways["livepix"].get("habilitado"), gateways["livepix"].get("configurado"))}
**Banco Inter:** {formatar(gateways["inter"].get("habilitado"), gateways["inter"].get("configurado"))}
**Nubank:** {formatar(gateways["nubank_imap"].get("habilitado"), gateways["nubank_imap"].get("configurado"))}
**Semi Automático:** {formatar(gateways["semiauto"].get("habilitado"), gateways["semiauto"].get("configurado"))}"""
        
        select_options = [
            disnake.SelectOption(label="Mercado Pago", value="mercadopago"), disnake.SelectOption(label="PagBank", value="pagbank"),
            disnake.SelectOption(label="Efí Bank", value="efi"), disnake.SelectOption(label="Asaas", value="asaas"),
            disnake.SelectOption(label="Stripe", value="stripe"), disnake.SelectOption(label="PicPay", value="picpay"),
            disnake.SelectOption(label="LivePix", value="livepix"), disnake.SelectOption(label="Banco Inter", value="inter"),
            disnake.SelectOption(label="Nubank", value="nubank_imap"), disnake.SelectOption(label="Semi Automático", value="semiauto")
        ]
        
        container = disnake.ui.Container(
            disnake.ui.TextDisplay(texto_container),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(placeholder="Selecione uma forma de pagamento", custom_id="select_gateway_to_manage", options=select_options)
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Bloquear Bancos", custom_id="GerenciarPainelBancosBloqueados", emoji=banco),
                disnake.ui.Button(label="Documentação", custom_id="VerDocumentacaoFormasPagamento", emoji=fields),
                disnake.ui.Button(label="Voltar", emoji=voltar, custom_id="GerenciarPainelConfigurar")
            )
        )
        
        return [container]

class BloquearBancos():
    def ObterPainelBloquearBancos(inter: disnake.MessageInteraction):
        with open("Database/Vendas/bancosbloqueados.json", encoding="utf-8") as f: vendasdb = json.load(f)
        bancos, bancos_bloqueados = vendasdb.get("bancosdisponiveis", []), vendasdb.get("bancosbloqueados", [])
        desc = "\n".join(f"- {banco}" for banco in bancos_bloqueados) if bancos_bloqueados else "Nenhum banco bloqueado."
        
        texto_container = f"""# {banco} Bloquear Bancos
Selecione os bancos dos quais você **não** deseja receber pagamentos.

**Bancos Bloqueados Atualmente:**
{desc}"""
        
        if not bancos:
            options = [disnake.SelectOption(label="Nenhum banco disponível para bloquear.", value="disabled")]
            select_disabled = True
        else:
            options = [disnake.SelectOption(label=banco, value=banco, default=banco in bancos_bloqueados) for banco in bancos]
            select_disabled = False
        
        container = disnake.ui.Container(
            disnake.ui.TextDisplay(texto_container),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(custom_id="select_bancos_bloqueados", placeholder="🔒 Selecione os bancos para bloquear", options=options, disabled=select_disabled, max_values=len(options) if options else 1, min_values=0)
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=voltar, custom_id="PainelConfigurar_FormasPagamento")
            )
        )
        
        return [container]
    def registrar_remover_bancos(inter):
        with open("Database/Vendas/bancosbloqueados.json", "r+", encoding="utf-8") as f:
            vendasdb = json.load(f)
            vendasdb["bancosbloqueados"] = inter.values if inter.values else []
            f.seek(0)
            json.dump(vendasdb, f, indent=4)
            f.truncate()

class DefiniçõesCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.condecoracao_cog = None
        self.bot.loop.create_task(self._load_condecoracao_cog())

    async def _load_condecoracao_cog(self):
        await self.bot.wait_until_ready()
        self.condecoracao_cog = self.bot.get_cog("CondecoracaoCommand")
        if not self.condecoracao_cog: print("AVISO: A cog 'CondecoracaoCommand' não foi carregada.")

    async def get_or_create_logs_category(self, guild: disnake.Guild):
        category_name = "⚙️ Logs do Servidor"
        for category in guild.categories:
            if category.name.lower() == category_name.lower(): return category
        try:
            overwrites = {guild.default_role: disnake.PermissionOverwrite(view_channel=False)}
            return await guild.create_category(name=category_name, overwrites=overwrites)
        except disnake.Forbidden: return None

    @commands.Cog.listener("on_message")
    async def monitorar_canal_feedbacks_para_condecoracao(self, message: disnake.Message):
        if message.author.bot or not message.guild: return
        canais = ObterCanais()
        canal_feedbacks_id = canais.get("feedbacks")
        if canal_feedbacks_id and message.channel.id == int(canal_feedbacks_id):
            if self.condecoracao_cog: await self.condecoracao_cog.conceder_condecoracao(message.author.id, "criticoConstrutivo", message)

    @commands.Cog.listener("on_button_click")
    async def ConfigurarButtonListener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        if custom_id == "GerenciarPainelConfigurar":
            components = ObterComponentsPainelInicial()
            await inter.response.edit_message(content="", embed=None, components=components)
            return

        elif custom_id.startswith("PainelConfigurar_"):
            tipo = custom_id.replace("PainelConfigurar_", "")
            if tipo == "AntiFake":
                await inter.response.send_modal(AlterarAntiFakeModal())
                return
            if not inter.response.is_done(): await inter.response.defer()
            components = []
            if tipo == "Canais": components = Canais.ObterMensagemCanais(inter)
            elif tipo == "Cargos": components = Cargos.ObterMensagemCargos(inter)
            elif tipo == "FormasPagamento": components = Pagamentos.ObterPainelFormasPagamento(inter)
            await inter.edit_original_response(content="", embed=None, components=components)
            return

        elif custom_id == "ConfigurarSintaxeLogs":
            await inter.response.send_modal(LogsSyntaxModal())
            return

        elif custom_id == "CriarTodosOsLogs":
            await inter.response.defer()
            container = disnake.ui.Container(disnake.ui.TextDisplay(f"# {carregarAnimado} Criando todos os canais de log necessários... Isso pode demorar um pouco."))
            await inter.edit_original_response(content="", embed=None, components=[container])
            
            log_category = await self.get_or_create_logs_category(inter.guild)
            if not log_category:
                container = disnake.ui.Container(disnake.ui.TextDisplay(f"# {negativo} Não tenho permissão para criar categorias de canais. A operação foi cancelada."))
                await inter.edit_original_response(content="", embed=None, components=[container])
                return

            canais = ObterCanais()
            sintaxe = ObterSalvarSintaxeLogs()
            canais_criados = 0
            
            for key, metadata in LOG_METADATA.items():
                if key not in canais or not canais.get(key):
                    nome_base = metadata.get("nome", key).lower().replace(" ", "-").replace("ç", "c")
                    nome_canal = sintaxe.format(emoji=metadata.get("emoji", "⚙️"), nome=nome_base)
                    try:
                        novo_canal = await inter.guild.create_text_channel(name=nome_canal, category=log_category)
                        canais[key] = novo_canal.id
                        canais_criados += 1
                        await asyncio.sleep(1) # Evita rate limit
                    except disnake.Forbidden:
                        await inter.followup.send(f"{negativo} Sem permissão para criar o canal `{nome_canal}`. Pulando...", ephemeral=True)
                    except Exception as e:
                        await inter.followup.send(f"{negativo} Erro ao criar o canal `{nome_canal}`: {e}", ephemeral=True)

            salvarCanaisDatabase(canais)
            
            components = Canais.ObterMensagemCanais(inter)
            await inter.edit_original_response(content="", embed=None, components=components)
            await inter.followup.send(f"{positivo} Operação concluída! {canais_criados} novos canais de log foram criados.", ephemeral=True)
            return

        elif custom_id.startswith("RemoverCanal_"):
            canal = custom_id.replace("RemoverCanal_", "")
            await removerCanal(canal)
            components = Canais.ObterMensagemCanais(inter)
            await inter.response.edit_message(content="", embed=None, components=components)
            if canal == "verificados":
                success, msg = await gerenciar_webhook_canal_verificados(self.bot, None, inter.guild.id)
                success_api, msg_api = await notificar_api_canal_verificados(self.bot, None, inter.guild.id, None)
                if not success_api: await inter.followup.send(f"{negativo} Canal removido, mas API não atualizada: `{msg_api}`", ephemeral=True)
                else: await inter.followup.send(f"{positivo} Canal removido, webhook e API sincronizadas.", ephemeral=True, delete_after=5)
            return

        elif custom_id.startswith("CriarCanal_"):
            canal_type = custom_id.replace("CriarCanal_", "")
            if not inter.response.is_done(): await inter.response.defer()
            else: 
                container = disnake.ui.Container(disnake.ui.TextDisplay(f"# {carregarAnimado} Criando canal..."))
                await inter.edit_original_response(content="", embed=None, components=[container])
            log_category = await self.get_or_create_logs_category(inter.guild)
            if not log_category:
                container = disnake.ui.Container(disnake.ui.TextDisplay(f"# {negativo} Não tenho permissão para criar categorias."))
                await inter.edit_original_response(content="", embed=None, components=[container])
                return
            metadata = LOG_METADATA.get(canal_type, {})
            sintaxe = ObterSalvarSintaxeLogs()
            nome_base = metadata.get("nome", canal_type).lower().replace(" ", "-").replace("ç", "c")
            nome_canal = sintaxe.format(emoji=metadata.get("emoji", "⚙️"), nome=nome_base)
            try: novo_canal = await inter.guild.create_text_channel(name=nome_canal, category=log_category)
            except disnake.Forbidden:
                 container = disnake.ui.Container(disnake.ui.TextDisplay(f"# {negativo} Não tenho permissão para criar canais."))
                 await inter.edit_original_response(content="", embed=None, components=[container])
                 return
            await novo_canal.send(f"||{inter.user.mention}|| Este canal foi configurado para logs de `{metadata.get('nome', canal_type)}`.")
            canais = ObterCanais()
            canais[canal_type] = novo_canal.id
            salvarCanaisDatabase(canais)
            components = Canais.ObterMensagemCanais(inter)
            await inter.edit_original_response(content="", embed=None, components=components)
            if canal_type == "verificados":
                success, msg = await gerenciar_webhook_canal_verificados(self.bot, str(novo_canal.id), inter.guild.id)
                logs_cog = self.bot.get_cog("LogsVerificacao")
                webhook_url = await logs_cog.obter_webhook_url(novo_canal.id) if logs_cog else None
                success_api, msg_api = await notificar_api_canal_verificados(self.bot, str(novo_canal.id), inter.guild.id, webhook_url)
                if not success_api: await inter.followup.send(f"{negativo} Canal criado, mas API não atualizada: `{msg_api}`", ephemeral=True)
                else: await inter.followup.send(f"{positivo} Canal criado, webhook e API sincronizadas.", ephemeral=True, delete_after=5)
            return

        elif custom_id.startswith("RemoverCargo_"):
            cargo = custom_id.replace("RemoverCargo_", "")
            await removerCargo(cargo)
            components = Cargos.ObterMensagemCargos(inter)
            await inter.response.edit_message(content="", embed=None, components=components)
            return

        elif custom_id.startswith("CriarCargo_"):
            cargo_type = custom_id.replace("CriarCargo_", "")
            if not inter.response.is_done(): await inter.response.defer()
            else: 
                container = disnake.ui.Container(disnake.ui.TextDisplay(f"# {carregarAnimado} Criando cargo..."))
                await inter.edit_original_response(content="", embed=None, components=[container])
            cargo_map = {"administrador": ("Administrador", 0x010101), "suporte": ("Suporte", 0x00FFFF), "cliente": ("Cliente", 0xFFFF00), "membro": ("Membro", 0x00FF00), "verificado": ("Verificado", 0x006400)}
            if cargo_type in cargo_map:
                nome, cor = cargo_map[cargo_type]
                novo_cargo = await inter.guild.create_role(reason=f"Configuração automática de cargo: {nome}", name=nome, hoist=True, colour=disnake.Colour(cor))
                cargos = ObterCargos()
                cargos[cargo_type] = novo_cargo.id
                salvarCargosDatabase(cargos)
            components = Cargos.ObterMensagemCargos(inter)
            await inter.edit_original_response(content="", embed=None, components=components)
            return

        elif custom_id == "VerDocumentacaoFormasPagamento":
            await inter.response.defer(ephemeral=True, with_message=True)
            await inter.followup.send(content="# Documentação | Formas de Pagamento\nVisão geral das formas de pagamento...\n...")
            return

        elif custom_id == "GerenciarPainelBancosBloqueados":
            await inter.response.defer()
            components = BloquearBancos.ObterPainelBloquearBancos(inter)
            await inter.edit_original_response(content="", embed=None, components=components)
            return

    @commands.Cog.listener("on_dropdown")
    async def ConfigurarDropdownListener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        if custom_id == "select_gateway_to_manage":
            gateway = inter.values[0]
            container = disnake.ui.Container(disnake.ui.TextDisplay(f"# {carregarAnimado} Carregando painel de **{gateway.replace('_', ' ').capitalize()}**..."))
            await inter.response.edit_message(content="", embed=None, components=[container])
            
            # Mapear cada gateway para sua respectiva classe de gerenciamento
            gateway_classes = {
                "mercadopago": GerenciarMercadoPago,
                "pagbank": GerenciarPagBank,
                "efi": GerenciarEfi,
                "asaas": GerenciarAsaas,
                "stripe": GerenciarStripe,
                "picpay": GerenciarPicPay,
                "livepix": GerenciarLivePix,
                "inter": GerenciarInter,
                "c6": GerenciarC6,
                "nubank_imap": GerenciarNubankIMAP,
                "itau_imap": GerenciarIMAPBank,
                "santander_imap": GerenciarIMAPBank,
                "bradesco_imap": GerenciarIMAPBank,
                "semiauto": GerenciarSemiAuto  # Adicionamos o Semi Automático
            }
            
            try:
                gateway_function = gateway_classes.get(gateway)
                
                if gateway_function is None:
                    container = disnake.ui.Container(disnake.ui.TextDisplay(f"# {negativo} Gateway `{gateway}` não implementado ainda."))
                    await inter.edit_original_response(content="", embed=None, components=[container])
                    return
                
                # Chamar como função async para a maioria dos gateways
                if gateway in ["itau_imap", "santander_imap", "bradesco_imap"]:
                    banco_nome = {
                        "itau_imap": "Itaú",
                        "santander_imap": "Santander", 
                        "bradesco_imap": "Bradesco"
                    }[gateway]
                    await gateway_function(inter, banco_nome)
                elif gateway == "semiauto":
                    # SemiAuto é uma classe
                    gerenciador = gateway_function(self.bot)
                    embed, components = gerenciador.obter_painel_principal(inter)
                    await inter.edit_original_response(content="", embed=embed, components=components)
                else:
                    # Outros gateways são funções async
                    await gateway_function(inter)
                
            except Exception as e:
                print(f"Erro ao carregar painel do gateway {gateway}: {e}")
                error_container = disnake.ui.Container(
                    disnake.ui.TextDisplay(f"# {negativo} Erro ao carregar o painel\n**Gateway:** {gateway.replace('_', ' ').capitalize()}\n**Erro:** {str(e)}"),
                    disnake.ui.Separator(),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Voltar", 
                            emoji=voltar, 
                            custom_id="PainelConfigurar_FormasPagamento"
                        )
                    )
                )
                await inter.edit_original_response(content="", embed=None, components=[error_container])
            return

        if custom_id.startswith("ConfigurarDropdown_Canais_"):
            await Canais.GerenciarCanal(inter, inter.values[0]); return
            
        elif custom_id.startswith("AlterarCanal_"):
            canal_selecionado = custom_id.replace("AlterarCanal_", "")
            novo_canal_id = inter.values[0]
            if not inter.response.is_done(): await inter.response.defer()
            else: 
                container = disnake.ui.Container(disnake.ui.TextDisplay(f"# {carregarAnimado} Alterando canal..."))
                await inter.edit_original_response(content="", embed=None, components=[container])
            canais = ObterCanais()
            canais[canal_selecionado] = novo_canal_id
            salvarCanaisDatabase(canais)
            components = Canais.ObterMensagemCanais(inter)
            await inter.edit_original_response(content="", embed=None, components=components)
            if canal_selecionado == "verificados":
                success, msg = await gerenciar_webhook_canal_verificados(self.bot, novo_canal_id, inter.guild.id)
                logs_cog = self.bot.get_cog("LogsVerificacao")
                webhook_url = await logs_cog.obter_webhook_url(novo_canal_id) if logs_cog else None
                success_api, msg_api = await notificar_api_canal_verificados(self.bot, novo_canal_id, inter.guild.id, webhook_url)
                if not success_api: await inter.followup.send(f"{negativo} Canal salvo, mas API não atualizada: `{msg_api}`", ephemeral=True)
                else: await inter.followup.send(f"{positivo} Canal salvo, webhook e API sincronizadas.", ephemeral=True, delete_after=5)
            return
        
        elif custom_id == "ConfigurarDropdown_Cargos":
            await Cargos.GerenciarCargo(inter, inter.values[0]); return
            
        elif custom_id.startswith("AlterarCargo_"):
            cargo_selecionado = custom_id.replace("AlterarCargo_", "")
            if not inter.response.is_done(): await inter.response.defer()
            else: 
                container = disnake.ui.Container(disnake.ui.TextDisplay(f"# {carregarAnimado} Alterando cargo..."))
                await inter.edit_original_response(content="", embed=None, components=[container])
            cargos = ObterCargos()
            cargos[cargo_selecionado] = inter.values[0]
            salvarCargosDatabase(cargos)
            components = Cargos.ObterMensagemCargos(inter)
            await inter.edit_original_response(content="", embed=None, components=components)
            return
            
        elif custom_id == "select_bancos_bloqueados":
            await inter.response.defer()
            BloquearBancos.registrar_remover_bancos(inter)
            components = BloquearBancos.ObterPainelBloquearBancos(inter)
            await inter.edit_original_response(content="", embed=None, components=components)
            return

def setup(bot: commands.Bot):
    bot.add_cog(DefiniçõesCommand(bot))
