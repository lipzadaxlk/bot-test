import disnake
import json
import asyncio
import time
from disnake.ext import commands
from datetime import datetime, timedelta
from Functions.CarregarEmojis import *
from collections import defaultdict

# Cache para rastrear ações dos usuários
user_actions = defaultdict(lambda: defaultdict(list))
suspicious_activities = defaultdict(list)

def ObterDatabaseProtecao():
    try:
        with open("Database/Server/protecao.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        db = {
            "canais": {
                "logs_channel_id": None,
                "criar": {"sistema": False, "limite": 0, "tempo_segundos": 0, "acao": "ban", "imunes_cargos": [], "imunes_categorias": []},
                "editar": {"sistema": False, "limite": 0, "tempo_segundos": 0, "acao": "ban", "imunes_cargos": [], "imunes_categorias": []},
                "excluir": {"sistema": False, "limite": 0, "tempo_segundos": 0, "acao": "ban", "imunes_cargos": [], "imunes_categorias": []}
            },
            "cargos": {
                "logs_channel_id": None,
                "criar": {"sistema": False, "limite": 0, "tempo_segundos": 0, "acao": "ban", "imunes_cargos": []},
                "editar": {"sistema": False, "limite": 0, "tempo_segundos": 0, "acao": "ban", "imunes_cargos": []},
                "excluir": {"sistema": False, "limite": 0, "tempo_segundos": 0, "acao": "ban", "imunes_cargos": []}
            },
            "banimento": {"sistema": False, "limite": 0, "tempo_segundos": 0, "acao": "reverter", "logs_channel_id": None, "imunes_cargos": []},
            "expulsao": {"sistema": False, "limite": 0, "tempo_segundos": 0, "acao": "reverter", "logs_channel_id": None, "imunes_cargos": []},
            "mencao": {"sistema": False, "limite_mencoes": 0, "tempo_segundos": 0, "acao": "silenciar", "logs_channel_id": None, "imunes_cargos": []},
            "adicionar_bot": {"sistema": False, "logs_channel_id": None, "acao": "ban_adicionador", "imunes_cargos": [], "whitelist_bots": []},
            "comandos_externos": {
                "sistema": False, 
                "logs_channel_id": None, 
                "acao": "ban", 
                "imunes_cargos": [], 
                "verificar_audit_log": True,
                "tempo_verificacao": 5,
                "banir_automatico": True
            },
            "webhook": {
                "sistema": False,
                "logs_channel_id": None,
                "acao": "ban",
                "imunes_cargos": [],
                "verificar_criacao": True,
                "limite": 2,
                "tempo_segundos": 60
            },
            "convites": {
                "sistema": False,
                "logs_channel_id": None,
                "acao": "timeout",
                "imunes_cargos": [],
                "limite": 3,
                "tempo_segundos": 30,
                "deletar_mensagem": True
            }
        }
        with open("Database/Server/protecao.json", "w") as f:
            json.dump(db, f, indent=4)
        return db

def salvar_database(db):
    with open("Database/Server/protecao.json", "w") as f:
        json.dump(db, f, indent=4)

def is_user_immune(guild, user_id, protection_type, sub_type=None):
    """Verifica se um usuário é imune à proteção"""
    try:
        member = guild.get_member(user_id)
        if not member:
            return False
        
        # Owner sempre é imune
        if member.id == guild.owner_id:
            return True
        
        # Admin com permissão de administrador é imune
        if member.guild_permissions.administrator:
            return True
        
        db = ObterDatabaseProtecao()
        config = db.get(protection_type, {})
        
        if sub_type:
            immune_roles = config.get(sub_type, {}).get("imunes_cargos", [])
        else:
            immune_roles = config.get("imunes_cargos", [])
        
        # Verifica se algum cargo do usuário está na lista de imunidade
        user_role_ids = [role.id for role in member.roles]
        return any(role_id in immune_roles for role_id in user_role_ids)
    except:
        return False

async def log_protection_action(guild, protection_type, user, action, reason, logs_channel_id=None):
    """Registra ações de proteção no canal de logs"""
    try:
        if not logs_channel_id:
            return
        
        channel = guild.get_channel(logs_channel_id)
        if not channel:
            return
        
        embed = disnake.Embed(
            title=f"🛡️ Proteção Ativada - {protection_type.title()}",
            color=0xFF0000,
            timestamp=datetime.now()
        )
        
        embed.add_field(name="Usuário", value=f"{user.mention} (`{user.id}`)", inline=True)
        embed.add_field(name="Ação", value=action, inline=True)
        embed.add_field(name="Motivo", value=reason, inline=False)
        
        await channel.send(embed=embed)
    except:
        pass

async def execute_protection_action(guild, user, action, reason="Proteção ativada"):
    """Executa a ação de proteção no usuário"""
    try:
        member = guild.get_member(user.id)
        if not member:
            return False
        
        if action == "ban":
            await member.ban(reason=reason)
        elif action == "kick":
            await member.kick(reason=reason)
        elif action == "timeout":
            await member.timeout(duration=timedelta(hours=1), reason=reason)
        elif action == "silenciar":
            # Remove permissões de falar
            for channel in guild.channels:
                if isinstance(channel, (disnake.TextChannel, disnake.VoiceChannel)):
                    await channel.set_permissions(member, send_messages=False, speak=False, reason=reason)
        
        return True
    except:
        return False

def add_user_action(user_id, action_type, timestamp=None):
    """Adiciona uma ação do usuário ao cache"""
    if timestamp is None:
        timestamp = time.time()
    
    user_actions[user_id][action_type].append(timestamp)

def check_rate_limit(user_id, action_type, limit, time_window):
    """Verifica se o usuário excedeu o limite de ações"""
    now = time.time()
    actions = user_actions[user_id][action_type]
    
    # Remove ações antigas
    user_actions[user_id][action_type] = [
        timestamp for timestamp in actions 
        if now - timestamp <= time_window
    ]
    
    return len(user_actions[user_id][action_type]) >= limit

async def detect_external_commands(guild, user_id):
    """Detecta comandos executados por usuários através de bots vinculados"""
    try:
        db = ObterDatabaseProtecao()
        config = db.get("comandos_externos", {})
        
        if not config.get("sistema", False):
            return False
        
        if is_user_immune(guild, user_id, "comandos_externos"):
            return False
        
        # Verifica audit logs por ações suspeitas
        async for entry in guild.audit_logs(limit=10, oldest_first=False):
            if entry.user and entry.user.id == user_id:
                # Verifica se a ação foi feita através de um bot não presente no servidor
                if entry.user.bot:
                    continue
                
                # Verifica ações suspeitas nos últimos segundos
                time_diff = (datetime.now() - entry.created_at).total_seconds()
                if time_diff <= config.get("tempo_verificacao", 5):
                    # Marca como atividade suspeita
                    suspicious_activities[user_id].append({
                        "action": entry.action,
                        "timestamp": time.time(),
                        "reason": "Comando externo detectado"
                    })
                    
                    if config.get("banir_automatico", True):
                        user = guild.get_member(user_id)
                        if user:
                            await execute_protection_action(
                                guild, user, config.get("acao", "ban"),
                                "Uso de comandos externos detectado"
                            )
                            await log_protection_action(
                                guild, "Comandos Externos", user,
                                config.get("acao", "ban"),
                                "Comando executado através de bot vinculado",
                                config.get("logs_channel_id")
                            )
                    return True
        
        return False
    except:
        return False

class ConfigurarProtecaoGeralModal(disnake.ui.Modal):
    def __init__(self, protecao_type: str, sub_type: str = None, current_config: dict = None):
        self.protecao_type = protecao_type
        self.sub_type = sub_type
        self.config = current_config or {}

        title_map = {
            "canais_criar": "Configurar Criação de Canais", "canais_editar": "Configurar Edição de Canais",
            "canais_excluir": "Configurar Exclusão de Canais", "cargos_criar": "Configurar Criação de Cargos",
            "cargos_editar": "Configurar Edição de Cargos", "cargos_excluir": "Configurar Exclusão de Cargos",
            "banimento": "Configurar Proteção de Banimento", "expulsao": "Configurar Proteção de Expulsão",
            "mencao": "Configurar Proteção de Menção", "adicionar_bot": "Configurar Proteção de Adição de Bot",
            "comandos_externos": "Configurar Proteção de Comandos Externos",
            "webhook": "Configurar Proteção de Webhook",
            "convites": "Configurar Proteção de Convites"
        }
        modal_title = title_map.get(f"{protecao_type}_{sub_type}" if sub_type else protecao_type, "Configuração de Proteção")

        components = [
            disnake.ui.TextInput(label="Limite de Ações", placeholder="Ex: 3", custom_id="limite", 
                               style=disnake.TextInputStyle.short, required=True, value=str(self.config.get("limite", 0))),
            disnake.ui.TextInput(label="Tempo (segundos)", placeholder="Ex: 60", custom_id="tempo_segundos",
                               style=disnake.TextInputStyle.short, required=True, value=str(self.config.get("tempo_segundos", 0))),
            disnake.ui.TextInput(label="Ação", placeholder="ban, kick, timeout, reverter", custom_id="acao",
                               style=disnake.TextInputStyle.short, required=True, value=str(self.config.get("acao", "ban"))),
            disnake.ui.TextInput(label="Ativar Sistema", placeholder="true ou false", custom_id="sistema_ativo",
                               style=disnake.TextInputStyle.short, required=True, value=str(self.config.get("sistema", False)).lower())
        ]

        # Componentes específicos para diferentes tipos de proteção
        if protecao_type == "mencao":
            components.insert(1, disnake.ui.TextInput(label="Limite Menções/Msg", placeholder="Ex: 5", custom_id="limite_mencoes",
                                                    style=disnake.TextInputStyle.short, required=True, 
                                                    value=str(self.config.get("limite_mencoes", 0))))
            components = components[:5]
        elif protecao_type == "comandos_externos":
            components.insert(1, disnake.ui.TextInput(label="Tempo Verificação (s)", placeholder="Ex: 5", custom_id="tempo_verificacao",
                                                    style=disnake.TextInputStyle.short, required=True,
                                                    value=str(self.config.get("tempo_verificacao", 5))))
            components = components[:5]

        super().__init__(title=modal_title, components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.edit_message(f"{carregarAnimado} Salvando configurações...", embed=None, components=None)
        
        try:
            limite = int(inter.text_values["limite"])
            tempo_segundos = int(inter.text_values["tempo_segundos"])
            sistema_ativo = inter.text_values["sistema_ativo"].lower() == "true"
            acao = inter.text_values["acao"]
            limite_mencoes = int(inter.text_values["limite_mencoes"]) if "limite_mencoes" in inter.text_values else None
            tempo_verificacao = int(inter.text_values["tempo_verificacao"]) if "tempo_verificacao" in inter.text_values else None
        except ValueError as e:
            await inter.followup.send(f"{negativo} Erro: Valores inválidos ({e})", ephemeral=True, delete_after=5)
            embed, components = Panels.ObterPainelProtecao(inter, self.protecao_type, self.sub_type)
            await inter.edit_original_message(content=None, embed=embed, components=components)
            return

        db = ObterDatabaseProtecao()
        config_path = db[self.protecao_type][self.sub_type] if self.sub_type else db[self.protecao_type]
        
        config_path.update({"limite": limite, "tempo_segundos": tempo_segundos, "sistema": sistema_ativo, "acao": acao})
        
        if self.protecao_type == "mencao" and limite_mencoes is not None:
            config_path["limite_mencoes"] = limite_mencoes
        elif self.protecao_type == "comandos_externos" and tempo_verificacao is not None:
            config_path["tempo_verificacao"] = tempo_verificacao

        salvar_database(db)
        embed, components = Panels.ObterPainelProtecao(inter, self.protecao_type, self.sub_type)
        await inter.edit_original_message(content=None, embed=embed, components=components)
        await inter.followup.send(f"{positivo} Configurações salvas!", ephemeral=True, delete_after=3)

class SelecionarCanaisView(disnake.ui.View):
    def __init__(self, protecao_type: str, action_type: str = "logs"):
        super().__init__(timeout=300)
        self.protecao_type = protecao_type
        self.action_type = action_type

    @disnake.ui.string_select(
        placeholder="Selecione um canal...",
        min_values=1,
        max_values=1,
        custom_id="selecionar_canal"
    )
    async def selecionar_canal(self, select: disnake.ui.StringSelect, inter: disnake.MessageInteraction):
        await inter.response.edit_message(f"{carregarAnimado} Configurando canal...", embed=None, view=None)
        
        channel_id = int(select.values[0])
        db = ObterDatabaseProtecao()
        
        if self.action_type == "logs":
            db[self.protecao_type]["logs_channel_id"] = channel_id
        
        salvar_database(db)
        embed, components = Panels.ObterPainelProtecao(inter, self.protecao_type)
        await inter.edit_original_message(content=None, embed=embed, components=components)
        await inter.followup.send(f"{positivo} Canal configurado com sucesso!", ephemeral=True, delete_after=3)

class SelecionarCargosView(disnake.ui.View):
    def __init__(self, protecao_type: str, action_type: str, sub_type: str = None):
        super().__init__(timeout=300)
        self.protecao_type = protecao_type
        self.action_type = action_type
        self.sub_type = sub_type

    @disnake.ui.string_select(
        placeholder="Selecione cargos para adicionar/remover...",
        min_values=1,
        max_values=25,
        custom_id="selecionar_cargos"
    )
    async def selecionar_cargos(self, select: disnake.ui.StringSelect, inter: disnake.MessageInteraction):
        await inter.response.edit_message(f"{carregarAnimado} Configurando cargos imunes...", embed=None, view=None)
        
        selected_ids = [int(value) for value in select.values]
        db = ObterDatabaseProtecao()
        
        if self.protecao_type in ["canais", "cargos"]:
            if self.sub_type:
                current_imunes = db[self.protecao_type][self.sub_type].get("imunes_cargos", [])
                for cargo_id in selected_ids:
                    if cargo_id not in current_imunes:
                        current_imunes.append(cargo_id)
                    else:
                        current_imunes.remove(cargo_id)
                db[self.protecao_type][self.sub_type]["imunes_cargos"] = current_imunes
            else:
                for sub in ["criar", "editar", "excluir"]:
                    current_imunes = db[self.protecao_type][sub].get("imunes_cargos", [])
                    for cargo_id in selected_ids:
                        if cargo_id not in current_imunes:
                            current_imunes.append(cargo_id)
                        else:
                            current_imunes.remove(cargo_id)
                    db[self.protecao_type][sub]["imunes_cargos"] = current_imunes
        else:
            current_imunes = db[self.protecao_type].get("imunes_cargos", [])
            for cargo_id in selected_ids:
                if cargo_id not in current_imunes:
                    current_imunes.append(cargo_id)
                else:
                    current_imunes.remove(cargo_id)
            db[self.protecao_type]["imunes_cargos"] = current_imunes
        
        salvar_database(db)
        embed, components = Panels.ObterPainelProtecao(inter, self.protecao_type)
        await inter.edit_original_message(content=None, embed=embed, components=components)
        await inter.followup.send(f"{positivo} Cargos imunes atualizados!", ephemeral=True, delete_after=3)

class SelecionarCategoriasView(disnake.ui.View):
    def __init__(self, protecao_type: str):
        super().__init__(timeout=300)
        self.protecao_type = protecao_type

    @disnake.ui.string_select(
        placeholder="Selecione categorias para adicionar/remover...",
        min_values=1,
        max_values=25,
        custom_id="selecionar_categorias"
    )
    async def selecionar_categorias(self, select: disnake.ui.StringSelect, inter: disnake.MessageInteraction):
        await inter.response.edit_message(f"{carregarAnimado} Configurando categorias imunes...", embed=None, view=None)
        
        selected_ids = [int(value) for value in select.values]
        db = ObterDatabaseProtecao()
        
        for sub in ["criar", "editar", "excluir"]:
            current_imunes = db[self.protecao_type][sub].get("imunes_categorias", [])
            for categoria_id in selected_ids:
                if categoria_id not in current_imunes:
                    current_imunes.append(categoria_id)
                else:
                    current_imunes.remove(categoria_id)
            db[self.protecao_type][sub]["imunes_categorias"] = current_imunes
        
        salvar_database(db)
        embed, components = Panels.ObterPainelProtecao(inter, self.protecao_type)
        await inter.edit_original_message(content=None, embed=embed, components=components)
        await inter.followup.send(f"{positivo} Categorias imunes atualizadas!", ephemeral=True, delete_after=3)

class SelecionarBotsView(disnake.ui.View):
    def __init__(self, protecao_type: str):
        super().__init__(timeout=300)
        self.protecao_type = protecao_type

    @disnake.ui.string_select(
        placeholder="Selecione bots para whitelist...",
        min_values=1,
        max_values=25,
        custom_id="selecionar_bots"
    )
    async def selecionar_bots(self, select: disnake.ui.StringSelect, inter: disnake.MessageInteraction):
        await inter.response.edit_message(f"{carregarAnimado} Configurando whitelist de bots...", embed=None, view=None)
        
        selected_ids = [int(value) for value in select.values]
        db = ObterDatabaseProtecao()
        
        current_whitelist = db[self.protecao_type].get("whitelist_bots", [])
        for bot_id in selected_ids:
            if bot_id not in current_whitelist:
                current_whitelist.append(bot_id)
            else:
                current_whitelist.remove(bot_id)
        
        db[self.protecao_type]["whitelist_bots"] = current_whitelist
        salvar_database(db)
        
        embed, components = Panels.ObterPainelProtecao(inter, self.protecao_type)
        await inter.edit_original_message(content=None, embed=embed, components=components)
        await inter.followup.send(f"{positivo} Whitelist de bots atualizada!", ephemeral=True, delete_after=3)

class SelecionarPunicaoView(disnake.ui.View):
    def __init__(self, protecao_type: str, sub_type: str):
        super().__init__(timeout=300)
        self.protecao_type = protecao_type
        self.sub_type = sub_type

    @disnake.ui.string_select(
        placeholder="Selecione a punição...",
        min_values=1,
        max_values=1,
        custom_id="selecionar_punicao",
        options=[
            disnake.SelectOption(label="Banir", value="ban", emoji=hammer, description="Banir o usuário do servidor"),
            disnake.SelectOption(label="Expulsar", value="kick", emoji=kick, description="Expulsar o usuário do servidor"),
            disnake.SelectOption(label="Mutar", value="timeout", emoji=mute, description="Colocar o usuário em timeout"),
            disnake.SelectOption(label="Silenciar", value="silenciar", emoji=mute, description="Remover permissões de falar"),
            disnake.SelectOption(label="Reverter", value="reverter", emoji=reload, description="Reverter a ação realizada")
        ]
    )
    async def selecionar_punicao(self, select: disnake.ui.StringSelect, inter: disnake.MessageInteraction):
        await inter.response.edit_message(f"{carregarAnimado} Configurando punição...", embed=None, view=None)
        
        acao_selecionada = select.values[0]
        db = ObterDatabaseProtecao()
        
        if self.sub_type:
            db[self.protecao_type][self.sub_type]["acao"] = acao_selecionada
        else:
            db[self.protecao_type]["acao"] = acao_selecionada
        
        salvar_database(db)
        embed, components = Panels.ObterPainelProtecao(inter, self.protecao_type)
        await inter.edit_original_message(content=None, embed=embed, components=components)
        await inter.followup.send(f"{positivo} Punição configurada para: **{acao_selecionada}**!", ephemeral=True, delete_after=3)

class Panels:
    @staticmethod
    def ObterPainelProtecaoGeral(inter):
        embed = disnake.Embed(title="🛡️ Proteção do Servidor", 
                            description="Sistema de proteção avançado contra raids e ataques.\nSelecione uma categoria de proteção para configurar.",
                            timestamp=datetime.now(), color=0x00FFFF)
        embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon.url if inter.guild.icon else None)

        options = [
            disnake.SelectOption(label="Proteção de Canais", value="canais", emoji=canalText, description="Criação/edição/exclusão de canais"),
            disnake.SelectOption(label="Proteção de Cargos", value="cargos", emoji=cargo, description="Criação/edição/exclusão de cargos"),
            disnake.SelectOption(label="Proteção de Banimento", value="banimento", emoji=hammer, description="Anti-ban em massa"),
            disnake.SelectOption(label="Proteção de Expulsão", value="expulsao", emoji=hammer, description="Anti-kick em massa"),
            disnake.SelectOption(label="Proteção de Menção", value="mencao", emoji=cargo, description="Anti-spam de menções"),
            disnake.SelectOption(label="Proteção de Bot", value="adicionar_bot", emoji=bot, description="Controle de adição de bots"),
            disnake.SelectOption(label="Comandos Externos", value="comandos_externos", emoji=bot, description="Anti-raid via bots vinculados"),
            disnake.SelectOption(label="Proteção de Webhook", value="webhook", emoji=bot, description="Controle de criação de webhooks"),
            disnake.SelectOption(label="Proteção de Convites", value="convites", emoji=link, description="Anti-spam de convites")
        ]

        return None, [
            disnake.ui.StringSelect(placeholder="🛡️ Selecione um sistema de proteção", custom_id="SelecionarProtecaoGeral", 
                                  options=options, min_values=1, max_values=1),
            disnake.ui.Button(label="Voltar", emoji=voltar, custom_id="PainelInicial")
        ]

    @staticmethod
    def ObterPainelProtecao(inter, protecao_type: str, sub_type: str = None):
        db = ObterDatabaseProtecao()
        config = db.get(protecao_type, {})
        
        title_map = {
            "canais": "Canais", "cargos": "Cargos", "banimento": "Banimento", 
            "expulsao": "Expulsão", "mencao": "Menção", "adicionar_bot": "Adição de Bot",
            "comandos_externos": "Comandos Externos", "webhook": "Webhook", "convites": "Convites"
        }
        
        embed = disnake.Embed(title=f"{safety} Proteção de {title_map.get(protecao_type, 'Desconhecida')}",
                            description=f"Configure as opções de proteção de forma intuitiva.",
                            timestamp=datetime.now(), color=0x00FFFF)
        embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon.url if inter.guild.icon else None)
        
        logs_channel_id = config.get("logs_channel_id")
        logs_text = f"<#{logs_channel_id}>" if logs_channel_id else f"{negativo} Não definido"
        embed.add_field(name="Canal de Logs", value=logs_text, inline=False)
        
        components = []
        
        if protecao_type in ["canais", "cargos"]:
            for subtype in ["criar", "editar", "excluir"]:
                sub_config = config[subtype]
                status = f"{positivo} Ativo" if sub_config.get("sistema") else f"{negativo} Inativo"
                
                acao_emoji = {"ban": f"{hammer}", "kick": f"{kick}", "timeout": f"{mute}", "reverter": f"{reload}", "silenciar": f"{mute}"}.get(sub_config.get("acao", "ban"), f"{config3}")
                
                embed.add_field(name=f"{subtype.capitalize()} {acao_emoji}", 
                              value=f"{status}\nLimite: `{sub_config.get('limite', 0)}` em `{sub_config.get('tempo_segundos', 0)}s`\nAção: `{sub_config.get('acao', 'N/A')}`",
                              inline=True)
            
            imunes_cargos = config.get("criar", {}).get("imunes_cargos", [])
            embed.add_field(name="Cargos Imunes", 
                          value=", ".join([f"<@&{r}>" for r in imunes_cargos[:5]]) + (f" e mais {len(imunes_cargos)-5}..." if len(imunes_cargos) > 5 else "") if imunes_cargos else f"{negativo} Nenhum",
                          inline=False)
            
            if protecao_type == "canais":
                imunes_categorias = config.get("criar", {}).get("imunes_categorias", [])
                embed.add_field(name="Categorias Imunes",
                              value=", ".join([f"<#{c}>" for c in imunes_categorias[:5]]) + (f" e mais {len(imunes_categorias)-5}..." if len(imunes_categorias) > 5 else "") if imunes_categorias else f"{negativo} Nenhuma",
                              inline=False)

            # Botões de configuração
            components.extend([
                disnake.ui.Button(label="Config. Criação", style=disnake.ButtonStyle.blurple, emoji=mais2, custom_id=f"ConfigurarProtecaoGeral_{protecao_type}_criar"),
                disnake.ui.Button(label="Config. Edição", style=disnake.ButtonStyle.blurple, emoji=editar, custom_id=f"ConfigurarProtecaoGeral_{protecao_type}_editar"),
                disnake.ui.Button(label="Config. Exclusão", style=disnake.ButtonStyle.blurple, emoji=apagar, custom_id=f"ConfigurarProtecaoGeral_{protecao_type}_excluir"),
                disnake.ui.Button(label="Canal de Logs", style=disnake.ButtonStyle.gray, emoji=canalText, custom_id=f"SelecionarCanal_{protecao_type}_logs"),
                disnake.ui.Button(label="Cargos Imunes", style=disnake.ButtonStyle.gray, emoji=cargo, custom_id=f"SelecionarCargos_{protecao_type}")
            ])
            
            if protecao_type == "canais":
                components.append(disnake.ui.Button(label="Categorias Imunes", style=disnake.ButtonStyle.gray, emoji=safety, custom_id=f"SelecionarCategorias_{protecao_type}"))
            
            # Select para punições
            punicao_options = [
                disnake.SelectOption(label="Punição: Criação", value=f"punicao_{protecao_type}_criar", emoji=mais2),
                disnake.SelectOption(label="Punição: Edição", value=f"punicao_{protecao_type}_editar", emoji=editar),
                disnake.SelectOption(label="Punição: Exclusão", value=f"punicao_{protecao_type}_excluir", emoji=apagar)
            ]
            components.append(disnake.ui.StringSelect(placeholder="Configurar Punições", custom_id=f"SelecionarPunicaoType_{protecao_type}",
                                                    options=punicao_options, min_values=1, max_values=1))

        else:
            sistema = config.get("sistema", False)
            limite = config.get("limite", "N/A")
            tempo = config.get("tempo_segundos", "N/A")
            acao = config.get("acao", "N/A")
            acao_emoji = {"ban": f"{hammer}", "kick": f"{kick}", "timeout": f"{mute}", "reverter": f"{reload}", "ban_adicionador": f"{hammer}", "silenciar": f"{mute}"}.get(acao, f"{config3}")

            embed.add_field(name="Status", value=f"{positivo} Habilitado" if sistema else f"{negativo} Desabilitado", inline=True)
            embed.add_field(name="Limite", value=f"`{limite}`", inline=True)
            embed.add_field(name="Tempo", value=f"`{tempo}s`", inline=True)
            embed.add_field(name=f"Ação {acao_emoji}", value=f"`{acao}`", inline=True)

            # Campos específicos para cada tipo de proteção
            if protecao_type == "mencao":
                embed.add_field(name="Limite Menções/Msg", value=f"`{config.get('limite_mencoes', 'N/A')}`", inline=True)
            elif protecao_type == "comandos_externos":
                embed.add_field(name="Tempo Verificação", value=f"`{config.get('tempo_verificacao', 5)}s`", inline=True)
                embed.add_field(name="Verificar Audit Log", value=f"{positivo if config.get('verificar_audit_log', True) else negativo}", inline=True)
                embed.add_field(name="Ban Automático", value=f"{positivo if config.get('banir_automatico', True) else negativo}", inline=True)
            elif protecao_type == "webhook":
                embed.add_field(name="Verificar Criação", value=f"{positivo if config.get('verificar_criacao', True) else negativo}", inline=True)
            elif protecao_type == "convites":
                embed.add_field(name="Deletar Mensagem", value=f"{positivo if config.get('deletar_mensagem', True) else negativo}", inline=True)
            
            imunes_cargos = config.get("imunes_cargos", [])
            embed.add_field(name="Cargos Imunes", 
                          value=", ".join([f"<@&{r}>" for r in imunes_cargos[:5]]) + (f" e mais {len(imunes_cargos)-5}..." if len(imunes_cargos) > 5 else "") if imunes_cargos else f"{negativo} Nenhum",
                          inline=False)

            if protecao_type == "adicionar_bot":
                whitelist_bots = config.get("whitelist_bots", [])
                embed.add_field(name="Bots Permitidos", 
                              value=", ".join([f"<@{b}>" for b in whitelist_bots[:5]]) + (f" e mais {len(whitelist_bots)-5}..." if len(whitelist_bots) > 5 else "") if whitelist_bots else f"{negativo} Nenhum",
                              inline=False)
                components.extend([
                    disnake.ui.Button(label="Whitelist Bots", style=disnake.ButtonStyle.blurple, emoji=bot, custom_id=f"SelecionarBots_{protecao_type}"),
                    disnake.ui.Button(label="Configurar", style=disnake.ButtonStyle.blurple, emoji=config3, custom_id=f"ConfigurarProtecaoGeral_{protecao_type}"),
                    disnake.ui.Button(label="Canal de Logs", style=disnake.ButtonStyle.gray, emoji=canalText, custom_id=f"SelecionarCanal_{protecao_type}_logs"),
                    disnake.ui.Button(label="Cargos Imunes", style=disnake.ButtonStyle.gray, emoji=cargo, custom_id=f"SelecionarCargos_{protecao_type}"),
                    disnake.ui.Button(label="Definir Punição", style=disnake.ButtonStyle.gray, emoji=hammer, custom_id=f"SelecionarPunicao_{protecao_type}")
                ])
            else:
                components.extend([
                    disnake.ui.Button(label="Configurar", style=disnake.ButtonStyle.blurple, emoji=config3, custom_id=f"ConfigurarProtecaoGeral_{protecao_type}"),
                    disnake.ui.Button(label="Canal de Logs", style=disnake.ButtonStyle.gray, emoji=canalText, custom_id=f"SelecionarCanal_{protecao_type}_logs"),
                    disnake.ui.Button(label="Cargos Imunes", style=disnake.ButtonStyle.gray, emoji=cargo, custom_id=f"SelecionarCargos_{protecao_type}"),
                    disnake.ui.Button(label="Definir Punição", style=disnake.ButtonStyle.gray, emoji=hammer, custom_id=f"SelecionarPunicao_{protecao_type}")
                ])

        components.append(disnake.ui.Button(label="Voltar", emoji=voltar, style=disnake.ButtonStyle.red, custom_id="GerenciarProtecaoServidor"))
        return embed, components

class ProtecaoServidorCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_guild_channel_create")
    async def on_channel_create(self, channel):
        """Detecta criação de canais"""
        try:
            db = ObterDatabaseProtecao()
            config = db.get("canais", {}).get("criar", {})
            
            if not config.get("sistema", False):
                return
            
            # Busca quem criou o canal no audit log
            async for entry in channel.guild.audit_logs(action=disnake.AuditLogAction.channel_create, limit=1):
                if entry.target.id == channel.id:
                    user_id = entry.user.id
                    
                    if is_user_immune(channel.guild, user_id, "canais", "criar"):
                        return
                    
                    # Verifica se o canal está em categoria imune
                    if channel.category and channel.category.id in config.get("imunes_categorias", []):
                        return
                    
                    add_user_action(user_id, "channel_create")
                    
                    if check_rate_limit(user_id, "channel_create", config.get("limite", 0), config.get("tempo_segundos", 0)):
                        user = channel.guild.get_member(user_id)
                        if user:
                            # Reverte a ação se configurado
                            if config.get("acao") == "reverter":
                                try:
                                    await channel.delete(reason="Proteção: Limite de criação de canais excedido")
                                except:
                                    pass
                            
                            await execute_protection_action(
                                channel.guild, user, config.get("acao", "ban"),
                                f"Criação excessiva de canais ({config.get('limite')} em {config.get('tempo_segundos')}s)"
                            )
                            
                            await log_protection_action(
                                channel.guild, "Criação de Canais", user,
                                config.get("acao", "ban"),
                                f"Limite excedido: {config.get('limite')} canais em {config.get('tempo_segundos')}s",
                                config.get("logs_channel_id")
                            )
                    break
        except Exception as e:
            print(f"Erro na proteção de criação de canais: {e}")

    @commands.Cog.listener("on_guild_channel_update")
    async def on_channel_update(self, before, after):
        """Detecta edição de canais"""
        try:
            db = ObterDatabaseProtecao()
            config = db.get("canais", {}).get("editar", {})
            
            if not config.get("sistema", False):
                return
            
            # Busca quem editou o canal no audit log
            async for entry in after.guild.audit_logs(action=disnake.AuditLogAction.channel_update, limit=1):
                if entry.target.id == after.id:
                    user_id = entry.user.id
                    
                    if is_user_immune(after.guild, user_id, "canais", "editar"):
                        return
                    
                    # Verifica se o canal está em categoria imune
                    if after.category and after.category.id in config.get("imunes_categorias", []):
                        return
                    
                    add_user_action(user_id, "channel_update")
                    
                    if check_rate_limit(user_id, "channel_update", config.get("limite", 0), config.get("tempo_segundos", 0)):
                        user = after.guild.get_member(user_id)
                        if user:
                            await execute_protection_action(
                                after.guild, user, config.get("acao", "ban"),
                                f"Edição excessiva de canais ({config.get('limite')} em {config.get('tempo_segundos')}s)"
                            )
                            
                            await log_protection_action(
                                after.guild, "Edição de Canais", user,
                                config.get("acao", "ban"),
                                f"Limite excedido: {config.get('limite')} edições em {config.get('tempo_segundos')}s",
                                config.get("logs_channel_id")
                            )
                    break
        except Exception as e:
            print(f"Erro na proteção de edição de canais: {e}")

    @commands.Cog.listener("on_guild_channel_delete")
    async def on_channel_delete(self, channel):
        """Detecta exclusão de canais"""
        try:
            db = ObterDatabaseProtecao()
            config = db.get("canais", {}).get("excluir", {})
            
            if not config.get("sistema", False):
                return
            
            # Busca quem deletou o canal no audit log
            async for entry in channel.guild.audit_logs(action=disnake.AuditLogAction.channel_delete, limit=1):
                if entry.target.id == channel.id:
                    user_id = entry.user.id
                    
                    if is_user_immune(channel.guild, user_id, "canais", "excluir"):
                        return
                    
                    # Verifica se o canal estava em categoria imune
                    if channel.category and channel.category.id in config.get("imunes_categorias", []):
                        return
                    
                    add_user_action(user_id, "channel_delete")
                    
                    if check_rate_limit(user_id, "channel_delete", config.get("limite", 0), config.get("tempo_segundos", 0)):
                        user = channel.guild.get_member(user_id)
                        if user:
                            # Reverte a ação se configurado
                            if config.get("acao") == "reverter":
                                try:
                                    # Recria o canal
                                    new_channel = await channel.guild.create_text_channel(
                                        name=channel.name,
                                        category=channel.category,
                                        position=channel.position,
                                        reason="Proteção: Canal restaurado após exclusão suspeita"
                                    )
                                except:
                                    pass
                            
                            await execute_protection_action(
                                channel.guild, user, config.get("acao", "ban"),
                                f"Exclusão excessiva de canais ({config.get('limite')} em {config.get('tempo_segundos')}s)"
                            )
                            
                            await log_protection_action(
                                channel.guild, "Exclusão de Canais", user,
                                config.get("acao", "ban"),
                                f"Limite excedido: {config.get('limite')} exclusões em {config.get('tempo_segundos')}s",
                                config.get("logs_channel_id")
                            )
                    break
        except Exception as e:
            print(f"Erro na proteção de exclusão de canais: {e}")

    @commands.Cog.listener("on_guild_role_create")
    async def on_role_create(self, role):
        """Detecta criação de cargos"""
        try:
            db = ObterDatabaseProtecao()
            config = db.get("cargos", {}).get("criar", {})
            
            if not config.get("sistema", False):
                return
            
            # Busca quem criou o cargo no audit log
            async for entry in role.guild.audit_logs(action=disnake.AuditLogAction.role_create, limit=1):
                if entry.target.id == role.id:
                    user_id = entry.user.id
                    
                    if is_user_immune(role.guild, user_id, "cargos", "criar"):
                        return
                    
                    add_user_action(user_id, "role_create")
                    
                    if check_rate_limit(user_id, "role_create", config.get("limite", 0), config.get("tempo_segundos", 0)):
                        user = role.guild.get_member(user_id)
                        if user:
                            # Reverte a ação se configurado
                            if config.get("acao") == "reverter":
                                try:
                                    await role.delete(reason="Proteção: Limite de criação de cargos excedido")
                                except:
                                    pass
                            
                            await execute_protection_action(
                                role.guild, user, config.get("acao", "ban"),
                                f"Criação excessiva de cargos ({config.get('limite')} em {config.get('tempo_segundos')}s)"
                            )
                            
                            await log_protection_action(
                                role.guild, "Criação de Cargos", user,
                                config.get("acao", "ban"),
                                f"Limite excedido: {config.get('limite')} cargos em {config.get('tempo_segundos')}s",
                                config.get("logs_channel_id")
                            )
                    break
        except Exception as e:
            print(f"Erro na proteção de criação de cargos: {e}")

    @commands.Cog.listener("on_guild_role_update")
    async def on_role_update(self, before, after):
        """Detecta edição de cargos"""
        try:
            db = ObterDatabaseProtecao()
            config = db.get("cargos", {}).get("editar", {})
            
            if not config.get("sistema", False):
                return
            
            # Busca quem editou o cargo no audit log
            async for entry in after.guild.audit_logs(action=disnake.AuditLogAction.role_update, limit=1):
                if entry.target.id == after.id:
                    user_id = entry.user.id
                    
                    if is_user_immune(after.guild, user_id, "cargos", "editar"):
                        return
                    
                    add_user_action(user_id, "role_update")
                    
                    if check_rate_limit(user_id, "role_update", config.get("limite", 0), config.get("tempo_segundos", 0)):
                        user = after.guild.get_member(user_id)
                        if user:
                            await execute_protection_action(
                                after.guild, user, config.get("acao", "ban"),
                                f"Edição excessiva de cargos ({config.get('limite')} em {config.get('tempo_segundos')}s)"
                            )
                            
                            await log_protection_action(
                                after.guild, "Edição de Cargos", user,
                                config.get("acao", "ban"),
                                f"Limite excedido: {config.get('limite')} edições em {config.get('tempo_segundos')}s",
                                config.get("logs_channel_id")
                            )
                    break
        except Exception as e:
            print(f"Erro na proteção de edição de cargos: {e}")

    @commands.Cog.listener("on_guild_role_delete")
    async def on_role_delete(self, role):
        """Detecta exclusão de cargos"""
        try:
            db = ObterDatabaseProtecao()
            config = db.get("cargos", {}).get("excluir", {})
            
            if not config.get("sistema", False):
                return
            
            # Busca quem deletou o cargo no audit log
            async for entry in role.guild.audit_logs(action=disnake.AuditLogAction.role_delete, limit=1):
                if entry.target.id == role.id:
                    user_id = entry.user.id
                    
                    if is_user_immune(role.guild, user_id, "cargos", "excluir"):
                        return
                    
                    add_user_action(user_id, "role_delete")
                    
                    if check_rate_limit(user_id, "role_delete", config.get("limite", 0), config.get("tempo_segundos", 0)):
                        user = role.guild.get_member(user_id)
                        if user:
                            # Reverte a ação se configurado
                            if config.get("acao") == "reverter":
                                try:
                                    # Recria o cargo com as mesmas propriedades
                                    await role.guild.create_role(
                                        name=role.name,
                                        permissions=role.permissions,
                                        colour=role.colour,
                                        hoist=role.hoist,
                                        mentionable=role.mentionable,
                                        reason="Proteção: Cargo restaurado após exclusão suspeita"
                                    )
                                except:
                                    pass
                            
                            await execute_protection_action(
                                role.guild, user, config.get("acao", "ban"),
                                f"Exclusão excessiva de cargos ({config.get('limite')} em {config.get('tempo_segundos')}s)"
                            )
                            
                            await log_protection_action(
                                role.guild, "Exclusão de Cargos", user,
                                config.get("acao", "ban"),
                                f"Limite excedido: {config.get('limite')} exclusões em {config.get('tempo_segundos')}s",
                                config.get("logs_channel_id")
                            )
                    break
        except Exception as e:
            print(f"Erro na proteção de exclusão de cargos: {e}")

    @commands.Cog.listener("on_member_ban")
    async def on_member_ban(self, guild, user):
        """Detecta banimentos"""
        try:
            db = ObterDatabaseProtecao()
            config = db.get("banimento", {})
            
            if not config.get("sistema", False):
                return
            
            # Busca quem baniu o usuário no audit log
            async for entry in guild.audit_logs(action=disnake.AuditLogAction.ban, limit=1):
                if entry.target.id == user.id:
                    user_id = entry.user.id
                    
                    if is_user_immune(guild, user_id, "banimento"):
                        return
                    
                    add_user_action(user_id, "ban")
                    
                    if check_rate_limit(user_id, "ban", config.get("limite", 0), config.get("tempo_segundos", 0)):
                        perpetrator = guild.get_member(user_id)
                        if perpetrator:
                            # Reverte a ação se configurado
                            if config.get("acao") == "reverter":
                                try:
                                    await guild.unban(user, reason="Proteção: Ban revertido automaticamente")
                                except:
                                    pass
                            
                            await execute_protection_action(
                                guild, perpetrator, config.get("acao", "ban"),
                                f"Banimentos excessivos ({config.get('limite')} em {config.get('tempo_segundos')}s)"
                            )
                            
                            await log_protection_action(
                                guild, "Banimentos", perpetrator,
                                config.get("acao", "ban"),
                                f"Limite excedido: {config.get('limite')} bans em {config.get('tempo_segundos')}s",
                                config.get("logs_channel_id")
                            )
                    break
        except Exception as e:
            print(f"Erro na proteção de banimentos: {e}")

    @commands.Cog.listener("on_member_remove")
    async def on_member_remove(self, member):
        """Detecta expulsões (kicks)"""
        try:
            db = ObterDatabaseProtecao()
            config = db.get("expulsao", {})
            
            if not config.get("sistema", False):
                return
            
            # Aguarda um pouco para o audit log ser atualizado
            await asyncio.sleep(1)
            
            # Busca quem expulsou o usuário no audit log
            async for entry in member.guild.audit_logs(action=disnake.AuditLogAction.kick, limit=1):
                if entry.target.id == member.id:
                    user_id = entry.user.id
                    
                    if is_user_immune(member.guild, user_id, "expulsao"):
                        return
                    
                    add_user_action(user_id, "kick")
                    
                    if check_rate_limit(user_id, "kick", config.get("limite", 0), config.get("tempo_segundos", 0)):
                        perpetrator = member.guild.get_member(user_id)
                        if perpetrator:
                            await execute_protection_action(
                                member.guild, perpetrator, config.get("acao", "ban"),
                                f"Expulsões excessivas ({config.get('limite')} em {config.get('tempo_segundos')}s)"
                            )
                            
                            await log_protection_action(
                                member.guild, "Expulsões", perpetrator,
                                config.get("acao", "ban"),
                                f"Limite excedido: {config.get('limite')} kicks em {config.get('tempo_segundos')}s",
                                config.get("logs_channel_id")
                            )
                    break
        except Exception as e:
            print(f"Erro na proteção de expulsões: {e}")

    @commands.Cog.listener("on_message")
    async def on_message_protection(self, message):
        """Proteção contra spam de menções, convites e comandos externos"""
        try:
            if message.author.bot or not message.guild:
                return
            
            db = ObterDatabaseProtecao()
            
            # Proteção de menções
            mencao_config = db.get("mencao", {})
            if mencao_config.get("sistema", False):
                if not is_user_immune(message.guild, message.author.id, "mencao"):
                    mention_count = len(message.mentions) + len(message.role_mentions)
                    
                    if mention_count >= mencao_config.get("limite_mencoes", 0):
                        add_user_action(message.author.id, "mention_spam")
                        
                        if check_rate_limit(message.author.id, "mention_spam", mencao_config.get("limite", 0), mencao_config.get("tempo_segundos", 0)):
                            await execute_protection_action(
                                message.guild, message.author, mencao_config.get("acao", "silenciar"),
                                f"Spam de menções ({mention_count} menções em uma mensagem)"
                            )
                            
                            await log_protection_action(
                                message.guild, "Spam de Menções", message.author,
                                mencao_config.get("acao", "silenciar"),
                                f"Menções excessivas: {mention_count} em uma mensagem",
                                mencao_config.get("logs_channel_id")
                            )
                            
                            try:
                                await message.delete()
                            except:
                                pass
            
            # Proteção de convites
            convites_config = db.get("convites", {})
            if convites_config.get("sistema", False):
                if not is_user_immune(message.guild, message.author.id, "convites"):
                    # Detecta links de convite do Discord
                    invite_patterns = [
                        "discord.gg/", "discord.com/invite/", "discordapp.com/invite/"
                    ]
                    
                    has_invite = any(pattern in message.content.lower() for pattern in invite_patterns)
                    
                    if has_invite:
                        add_user_action(message.author.id, "invite_spam")
                        
                        if check_rate_limit(message.author.id, "invite_spam", convites_config.get("limite", 0), convites_config.get("tempo_segundos", 0)):
                            await execute_protection_action(
                                message.guild, message.author, convites_config.get("acao", "timeout"),
                                f"Spam de convites ({convites_config.get('limite')} em {convites_config.get('tempo_segundos')}s)"
                            )
                            
                            await log_protection_action(
                                message.guild, "Spam de Convites", message.author,
                                convites_config.get("acao", "timeout"),
                                f"Limite excedido: {convites_config.get('limite')} convites em {convites_config.get('tempo_segundos')}s",
                                convites_config.get("logs_channel_id")
                            )
                        
                        if convites_config.get("deletar_mensagem", True):
                            try:
                                await message.delete()
                            except:
                                pass
            
            # Verificação de comandos externos (detecta ações suspeitas)
            await detect_external_commands(message.guild, message.author.id)
            
        except Exception as e:
            print(f"Erro na proteção de mensagens: {e}")

    @commands.Cog.listener("on_member_join")
    async def on_member_join_protection(self, member):
        """Detecta adição de bots"""
        try:
            if not member.bot:
                return
            
            db = ObterDatabaseProtecao()
            config = db.get("adicionar_bot", {})
            
            if not config.get("sistema", False):
                return
            
            # Verifica se o bot está na whitelist
            if member.id in config.get("whitelist_bots", []):
                return
            
            # Busca quem adicionou o bot no audit log
            async for entry in member.guild.audit_logs(action=disnake.AuditLogAction.bot_add, limit=1):
                if entry.target.id == member.id:
                    user_id = entry.user.id
                    
                    if is_user_immune(member.guild, user_id, "adicionar_bot"):
                        return
                    
                    # Executa a ação imediatamente para bots não autorizados
                    perpetrator = member.guild.get_member(user_id)
                    if perpetrator:
                        # Remove o bot primeiro
                        try:
                            await member.kick(reason="Bot não autorizado adicionado")
                        except:
                            pass
                        
                        # Pune o usuário que adicionou
                        await execute_protection_action(
                            member.guild, perpetrator, config.get("acao", "ban_adicionador"),
                            f"Adição de bot não autorizado: {member.name}"
                        )
                        
                        await log_protection_action(
                            member.guild, "Adição de Bot", perpetrator,
                            config.get("acao", "ban_adicionador"),
                            f"Bot não autorizado adicionado: {member.name} ({member.id})",
                            config.get("logs_channel_id")
                        )
                    break
        except Exception as e:
            print(f"Erro na proteção de adição de bots: {e}")

    @commands.Cog.listener("on_webhooks_update")
    async def on_webhooks_update_protection(self, channel):
        """Detecta criação de webhooks"""
        try:
            db = ObterDatabaseProtecao()
            config = db.get("webhook", {})
            
            if not config.get("sistema", False):
                return
            
            if not config.get("verificar_criacao", True):
                return
            
            # Busca quem criou o webhook no audit log
            async for entry in channel.guild.audit_logs(action=disnake.AuditLogAction.webhook_create, limit=1):
                if entry.target and hasattr(entry.target, 'channel') and entry.target.channel.id == channel.id:
                    user_id = entry.user.id
                    
                    if is_user_immune(channel.guild, user_id, "webhook"):
                        return
                    
                    add_user_action(user_id, "webhook_create")
                    
                    if check_rate_limit(user_id, "webhook_create", config.get("limite", 0), config.get("tempo_segundos", 0)):
                        user = channel.guild.get_member(user_id)
                        if user:
                            # Remove o webhook se configurado para reverter
                            if config.get("acao") == "reverter":
                                try:
                                    webhooks = await channel.webhooks()
                                    for webhook in webhooks:
                                        if webhook.user.id == user_id:
                                            await webhook.delete(reason="Proteção: Webhook removido automaticamente")
                                except:
                                    pass
                            
                            await execute_protection_action(
                                channel.guild, user, config.get("acao", "ban"),
                                f"Criação excessiva de webhooks ({config.get('limite')} em {config.get('tempo_segundos')}s)"
                            )
                            
                            await log_protection_action(
                                channel.guild, "Criação de Webhook", user,
                                config.get("acao", "ban"),
                                f"Limite excedido: {config.get('limite')} webhooks em {config.get('tempo_segundos')}s",
                                config.get("logs_channel_id")
                            )
                    break
        except Exception as e:
            print(f"Erro na proteção de webhooks: {e}")

    @commands.Cog.listener("on_button_click")
    async def ProtecaoServidorButtonListener(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "GerenciarProtecaoServidor":
            await inter.response.edit_message(f"{carregarAnimado} Carregando painel de proteção...", embed=None, components=None)
            embed, components = Panels.ObterPainelProtecaoGeral(inter)
            await inter.edit_original_message(content=None, embed=embed, components=components)

        elif inter.component.custom_id.startswith("ConfigurarProtecaoGeral_"):
            parts = inter.component.custom_id.split('_')
            protecao_type, sub_type = parts[1], parts[2] if len(parts) > 2 else None
            
            db = ObterDatabaseProtecao()
            current_config = db.get(protecao_type, {}).get(sub_type, {}) if sub_type else db.get(protecao_type, {})
            await inter.response.send_modal(ConfigurarProtecaoGeralModal(protecao_type, sub_type, current_config))

        elif inter.component.custom_id.startswith("SelecionarCanal_"):
            parts = inter.component.custom_id.split('_')
            protecao_type = parts[1]
            action_type = parts[2] if len(parts) > 2 else "logs"
            
            await inter.response.edit_message(f"{carregarAnimado} Carregando canais...", embed=None, components=None)
            
            # Criar select com canais do servidor
            canais_opcoes = []
            for channel in inter.guild.channels:
                if isinstance(channel, disnake.TextChannel):
                    canais_opcoes.append(disnake.SelectOption(
                        label=f"#{channel.name}",
                        value=str(channel.id),
                        description=f"Categoria: {channel.category.name if channel.category else 'Sem categoria'}"
                    ))
            
            if not canais_opcoes:
                await inter.edit_original_message(content=f"{negativo} Nenhum canal de texto encontrado!", embed=None, components=None)
                return
            
            # Limitar a 25 opções (limite do Discord)
            canais_opcoes = canais_opcoes[:25]
            
            view = SelecionarCanaisView(protecao_type, action_type)
            view.children[0].options = canais_opcoes
            
            embed = disnake.Embed(
                title="📋 Selecionar Canal de Logs",
                description="Escolha o canal onde serão enviados os logs de proteção.\n\n**Dica:** Recomendamos um canal privado apenas para moderadores.",
                color=0x00FFFF
            )
            
            await inter.edit_original_message(embed=embed, view=view)

        elif inter.component.custom_id.startswith("SelecionarCargos_"):
            protecao_type = inter.component.custom_id.replace("SelecionarCargos_", "")
            
            await inter.response.edit_message(f"{carregarAnimado} Carregando cargos...", embed=None, components=None)
            
            # Criar select com cargos do servidor
            cargos_opcoes = []
            db = ObterDatabaseProtecao()
            current_imunes = []
            
            if protecao_type in ["canais", "cargos"]:
                current_imunes = db.get(protecao_type, {}).get("criar", {}).get("imunes_cargos", [])
            else:
                current_imunes = db.get(protecao_type, {}).get("imunes_cargos", [])
            
            for role in inter.guild.roles:
                if role.name != "@everyone" and role.id != inter.guild.default_role.id:
                    is_immune = f"{positivo}" if role.id in current_imunes else f"{negativo}"
                    cargos_opcoes.append(disnake.SelectOption(
                        label=f"{is_immune} {role.name}",
                        value=str(role.id),
                        description=f"Membros: {len(role.members)} | {'Imune' if role.id in current_imunes else 'Não imune'}"
                    ))
            
            if not cargos_opcoes:
                await inter.edit_original_message(content=f"{negativo} Nenhum cargo encontrado!", embed=None, components=None)
                return
            
            # Limitar a 25 opções
            cargos_opcoes = cargos_opcoes[:25]
            
            view = SelecionarCargosView(protecao_type, "imunes")
            view.children[0].options = cargos_opcoes
            
            embed = disnake.Embed(
                title="🛡️ Gerenciar Cargos Imunes",
                description="Selecione os cargos que serão imunes à proteção.\n✅ = Atualmente imune | ❌ = Não imune\n\n**Clique para adicionar/remover da lista de imunes**\n\n⚠️ **Nota:** Administradores e o dono do servidor são sempre imunes.",
                color=0x00FFFF
            )
            
            await inter.edit_original_message(embed=embed, view=view)

        elif inter.component.custom_id.startswith("SelecionarCategorias_"):
            protecao_type = inter.component.custom_id.replace("SelecionarCategorias_", "")
            
            await inter.response.edit_message(f"{carregarAnimado} Carregando categorias...", embed=None, components=None)
            
            # Criar select com categorias do servidor
            categorias_opcoes = []
            db = ObterDatabaseProtecao()
            current_imunes = db.get(protecao_type, {}).get("criar", {}).get("imunes_categorias", [])
            
            for category in inter.guild.categories:
                is_immune = f"{positivo}" if category.id in current_imunes else f"{negativo}"
                categorias_opcoes.append(disnake.SelectOption(
                    label=f"{is_immune} {category.name}",
                    value=str(category.id),
                    description=f"Canais: {len(category.channels)} | {'Imune' if category.id in current_imunes else 'Não imune'}"
                ))
            
            if not categorias_opcoes:
                await inter.edit_original_message(content=f"{negativo} Nenhuma categoria encontrada!", embed=None, components=None)
                return
            
            # Limitar a 25 opções
            categorias_opcoes = categorias_opcoes[:25]
            
            view = SelecionarCategoriasView(protecao_type)
            view.children[0].options = categorias_opcoes
            
            embed = disnake.Embed(
                title="📁 Gerenciar Categorias Imunes",
                description="Selecione as categorias que serão imunes à proteção.\n✅ = Atualmente imune | ❌ = Não imune\n\n**Clique para adicionar/remover da lista de imunes**\n\n**Dica:** Categorias imunes protegem todos os canais dentro delas.",
                color=0x00FFFF
            )
            
            await inter.edit_original_message(embed=embed, view=view)

        elif inter.component.custom_id.startswith("SelecionarBots_"):
            protecao_type = inter.component.custom_id.replace("SelecionarBots_", "")
            
            await inter.response.edit_message(f"{carregarAnimado} Carregando bots...", embed=None, components=None)
            
            # Criar select com bots do servidor
            bots_opcoes = []
            db = ObterDatabaseProtecao()
            current_whitelist = db.get(protecao_type, {}).get("whitelist_bots", [])
            
            for member in inter.guild.members:
                if member.bot and member.id != self.bot.user.id:  # Exclui o próprio bot
                    is_whitelisted = f"{positivo}" if member.id in current_whitelist else f"{negativo}"
                    bots_opcoes.append(disnake.SelectOption(
                        label=f"{is_whitelisted} {member.display_name}",
                        value=str(member.id),
                        description=f"{'Permitido' if member.id in current_whitelist else 'Não permitido'}"
                    ))
            
            if not bots_opcoes:
                await inter.edit_original_message(content=f"{negativo} Nenhum bot encontrado no servidor!", embed=None, components=None)
                return
            
            # Limitar a 25 opções
            bots_opcoes = bots_opcoes[:25]
            
            view = SelecionarBotsView(protecao_type)
            view.children[0].options = bots_opcoes
            
            embed = disnake.Embed(
                title="🤖 Gerenciar Whitelist de Bots",
                description="Selecione os bots que poderão ser adicionados sem restrições.\n✅ = Permitido | ❌ = Não permitido\n\n**Clique para adicionar/remover da whitelist**\n\n⚠️ **Importante:** Bots não listados aqui serão automaticamente removidos se adicionados.",
                color=0x00FFFF
            )
            
            await inter.edit_original_message(embed=embed, view=view)

        elif inter.component.custom_id.startswith("SelecionarPunicao_"):
            protecao_type = inter.component.custom_id.replace("SelecionarPunicao_", "")
            
            await inter.response.edit_message(f"{carregarAnimado} Carregando opções de punição...", embed=None, components=None)
            
            view = SelecionarPunicaoView(protecao_type, None)
            
            embed = disnake.Embed(
                title="⚡ Definir Punição",
                description="Escolha qual ação será tomada quando a proteção for ativada.\n\n**Opções disponíveis:**\n🔨 **Banir** - Remove permanentemente do servidor\n👢 **Expulsar** - Remove mas pode retornar\n🔇 **Mutar** - Timeout temporário\n🤐 **Silenciar** - Remove permissões de falar\n🔄 **Reverter** - Desfaz a ação (quando possível)",
                color=0x00FFFF
            )
            
            await inter.edit_original_message(content=None, embed=embed, view=view)

    @commands.Cog.listener("on_dropdown")
    async def ProtecaoServidorDropdownListener(self, inter: disnake.MessageInteraction):
        try:
            if inter.component.custom_id == "SelecionarProtecaoGeral":
                await inter.response.edit_message(f"{carregarAnimado} Carregando proteção...", embed=None, components=None)
                embed, components = Panels.ObterPainelProtecao(inter, inter.values[0])
                await inter.edit_original_message(content=None, embed=embed, components=components)

            elif inter.component.custom_id.startswith("SelecionarPunicaoType_"):
                protecao_type = inter.component.custom_id.replace("SelecionarPunicaoType_", "")
                selected_value = inter.values[0]
                
                # Extrair o sub_type do valor selecionado (ex: "punicao_canais_criar" -> "criar")
                sub_type = selected_value.split('_')[-1]
                
                await inter.response.edit_message(f"{carregarAnimado} Carregando opções de punição...", embed=None, components=None)
                
                view = SelecionarPunicaoView(protecao_type, sub_type)
                
                embed = disnake.Embed(
                    title=f"⚡ Definir Punição - {sub_type.capitalize()}",
                    description=f"Escolha qual ação será tomada para **{sub_type}** de {protecao_type}.\n\n**Opções disponíveis:**\n🔨 **Banir** - Remove permanentemente do servidor\n👢 **Expulsar** - Remove mas pode retornar\n🔇 **Mutar** - Timeout temporário\n🤐 **Silenciar** - Remove permissões de falar\n🔄 **Reverter** - Desfaz a ação (quando possível)",
                    color=0x00FFFF
                )
                
                await inter.edit_original_message(content=None, embed=embed, view=view)

        except Exception as e:
            try:
                await inter.followup.send(f"{negativo} Erro: {e}", ephemeral=True, delete_after=10)
            except:
                pass

    # Comando para status da proteção
    @commands.slash_command(name="protecao_status", description="Mostra o status atual de todas as proteções")
    async def protecao_status(self, inter: disnake.ApplicationCommandInteraction):
        """Comando para verificar status das proteções"""
        if not inter.user.guild_permissions.administrator:
            await inter.response.send_message(f"{negativo} Você precisa ser administrador para usar este comando!", ephemeral=True)
            return
        
        db = ObterDatabaseProtecao()
        
        embed = disnake.Embed(
            title="📊 Status das Proteções",
            description="Estado atual de todos os sistemas de proteção",
            color=0x00FFFF,
            timestamp=datetime.now()
        )
        
        protecoes = {
            "canais": "📁 Canais",
            "cargos": "🏷️ Cargos", 
            "banimento": "🔨 Banimentos",
            "expulsao": "👢 Expulsões",
            "mencao": "💬 Menções",
            "adicionar_bot": "🤖 Adição de Bots",
            "comandos_externos": "⚠️ Comandos Externos",
            "webhook": "🔗 Webhooks",
            "convites": "📧 Convites"
        }
        
        ativo_count = 0
        
        for key, name in protecoes.items():
            config = db.get(key, {})
            
            if key in ["canais", "cargos"]:
                # Para canais e cargos, verifica subtipos
                sub_status = []
                for sub in ["criar", "editar", "excluir"]:
                    sub_config = config.get(sub, {})
                    status = "✅" if sub_config.get("sistema", False) else "❌"
                    if sub_config.get("sistema", False):
                        ativo_count += 1
                    sub_status.append(f"{status} {sub.capitalize()}")
                
                embed.add_field(
                    name=name,
                    value="\n".join(sub_status),
                    inline=True
                )
            else:
                # Para outros tipos de proteção
                status = "✅ Ativo" if config.get("sistema", False) else "❌ Inativo"
                if config.get("sistema", False):
                    ativo_count += 1
                    
                limite = config.get("limite", "N/A")
                tempo = config.get("tempo_segundos", "N/A")
                
                embed.add_field(
                    name=name,
                    value=f"{status}\nLimite: {limite}\nTempo: {tempo}s",
                    inline=True
                )
        
        embed.set_footer(text=f"Total: {ativo_count} proteções ativas | {inter.guild.name}")
        
        await inter.response.send_message(embed=embed, ephemeral=True)

def setup(bot: commands.Bot):
    bot.add_cog(ProtecaoServidorCommand(bot))