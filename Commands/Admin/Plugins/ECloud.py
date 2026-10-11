import disnake
import re
import requests
import json
import os
import asyncio
from disnake import *
from disnake.ext import commands, tasks
from datetime import datetime, timezone

from Functions.CarregarEmojis import *
from Functions.VerificarPerms import *

API_URL = "https://ecloudxesteerdaocu.squareweb.app/"
BACKUP_FILE_PATH = 'Database/Auth/server_backup.json'

def get_local_db_path(filename):
    dir_path = "Database/eCloud"
    os.makedirs(dir_path, exist_ok=True)
    return os.path.join(dir_path, filename)

def ObterAuthLocal():
    caminho = get_local_db_path("auth_config.json")
    if not os.path.exists(caminho):
        with open(caminho, "w") as f:
            json.dump({"authorization": None, "last_backup_timestamp": None}, f, indent=4)
    with open(caminho) as f:
        config = json.load(f)
        if "last_backup_timestamp" not in config:
            config["last_backup_timestamp"] = None
        return config

def SalvarAuthLocal(data):
    caminho = get_local_db_path("auth_config.json")
    with open(caminho, "w") as f:
        json.dump(data, f, indent=4)

def ObterMensagemLocal():
    caminho = get_local_db_path("message_config.json")
    if not os.path.exists(caminho):
        default_msg = {"content": "Verifique-se para ter acesso ao servidor!", "embed": {"title": "Sistema de Verificação", "description": "Clique no botão abaixo para se autenticar.", "color": "#00FFFF"}, "button": {"label": "Verificar", "emoji": "✅"}}
        with open(caminho, "w") as f:
            json.dump(default_msg, f, indent=4)
    with open(caminho) as f:
        return json.load(f)

def SalvarMensagemLocal(data):
    caminho = get_local_db_path("message_config.json")
    with open(caminho, "w") as f:
        json.dump(data, f, indent=4)

def ObterPsicoConfig():
    caminho = get_local_db_path("psico_config.json")
    if not os.path.exists(caminho):
        default_config = {
            "verificado_obrigatorio": True, 
            "sincronizacao_inteligente": True, 
            "cargo_persistente": True,
            "checkVPN": False,
            "checkProxy": False,
            "checkAlt": False
        }
        with open(caminho, "w") as f:
            json.dump(default_config, f, indent=4)
        return default_config
    
    with open(caminho) as f:
        config = json.load(f)
    
    needs_save = False
    default_keys = {"checkVPN": False, "checkProxy": False, "checkAlt": False}
    for key, default_value in default_keys.items():
        if key not in config:
            config[key] = default_value
            needs_save = True
            
    if needs_save:
        SalvarPsicoConfig(config)
        
    return config

def SalvarPsicoConfig(data):
    caminho = get_local_db_path("psico_config.json")
    with open(caminho, "w") as f:
        json.dump(data, f, indent=4)

def sync_psico_to_api():
    auth_data = ObterAuthLocal()
    auth_token = auth_data.get("authorization")
    if not auth_token:
        return

    psico_config = ObterPsicoConfig()
    endpoint_url = f"{API_URL}config/psico-update"
    headers = {
        'Authorization': auth_token,
        'Content-Type': 'application/json'
    }
    try:
        requests.post(endpoint_url, headers=headers, json={"psico_config": psico_config})
    except requests.RequestException:
        pass

async def perform_backup(guild: disnake.Guild):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Iniciando backup para o servidor: {guild.name}...")
    backup_data = {'guild_id': str(guild.id), 'name': guild.name, 'icon_url': str(guild.icon.url) if guild.icon else None, 'roles': [], 'channels': []}
    for role in sorted(guild.roles, key=lambda r: r.position, reverse=True):
        if role.is_default(): continue
        backup_data['roles'].append({'name': role.name, 'color': role.color.value, 'permissions': role.permissions.value, 'hoist': role.hoist, 'mentionable': role.mentionable, 'position': role.position})
    for category, channels in guild.by_category():
        if category is not None:
            category_data = {'name': category.name, 'type': 'category', 'position': category.position, 'overwrites': []}
            for target, overwrite in category.overwrites.items():
                target_type = 'role' if isinstance(target, disnake.Role) else 'member'
                allow_perms, deny_perms = overwrite.pair()
                category_data['overwrites'].append({'id': str(target.id), 'type': target_type, 'allow': allow_perms.value, 'deny': deny_perms.value})
            backup_data['channels'].append(category_data)
        for channel in channels:
            channel_data = {'name': channel.name, 'type': str(channel.type), 'category_name': category.name if category else None, 'position': channel.position, 'overwrites': []}
            if isinstance(channel, disnake.TextChannel):
                channel_data.update({'topic': channel.topic, 'slowmode_delay': channel.slowmode_delay})
            for target, overwrite in channel.overwrites.items():
                target_type = 'role' if isinstance(target, disnake.Role) else 'member'
                allow_perms, deny_perms = overwrite.pair()
                channel_data['overwrites'].append({'id': str(target.id), 'type': target_type, 'allow': allow_perms.value, 'deny': deny_perms.value})
            backup_data['channels'].append(channel_data)
    os.makedirs(os.path.dirname(BACKUP_FILE_PATH), exist_ok=True)
    with open(BACKUP_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, ensure_ascii=False, indent=4)
    auth_local = ObterAuthLocal()
    auth_local["last_backup_timestamp"] = int(datetime.now(timezone.utc).timestamp())
    SalvarAuthLocal(auth_local)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Backup concluído para o servidor: {guild.name}")

async def restore_from_backup(inter: disnake.MessageInteraction):
    loading_container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"{carregarAnimado} Iniciando restauração... Isso pode levar um tempo.")
    )
    await inter.response.edit_message(embed=None, components=[loading_container])
    try:
        with open(BACKUP_FILE_PATH, 'r', encoding='utf-8') as f:
            backup = json.load(f)
    except FileNotFoundError:
        return await inter.followup.send(f"{negativo} Arquivo de backup não encontrado.", ephemeral=True)
    guild = inter.guild
    log = [f"{positivo} **Iniciando restauração para o servidor {guild.name}...**"]
    existing_roles = {r.name: r for r in guild.roles}
    for role_data in reversed(backup['roles']):
        if role_data['name'] not in existing_roles:
            try:
                new_role = await guild.create_role(name=role_data['name'], permissions=disnake.Permissions(role_data['permissions']), color=disnake.Color(role_data['color']), hoist=role_data['hoist'], mentionable=role_data['mentionable'])
                existing_roles[new_role.name] = new_role
                log.append(f"{positivo} Cargo criado: `{new_role.name}`")
                await asyncio.sleep(1)
            except Exception as e:
                log.append(f"{negativo} Falha ao criar cargo `{role_data['name']}`: {e}")
    existing_categories = {c.name: c for c in guild.categories}
    for channel_data in backup['channels']:
        if channel_data['type'] == 'category' and channel_data['name'] not in existing_categories:
            try:
                new_cat = await guild.create_category(name=channel_data['name'])
                existing_categories[new_cat.name] = new_cat
                log.append(f"{positivo} Categoria criada: `{new_cat.name}`")
                await asyncio.sleep(1)
            except Exception as e:
                log.append(f"{negativo} Falha ao criar categoria `{channel_data['name']}`: {e}")
    existing_channels = {c.name: c for c in guild.channels}
    for channel_data in backup['channels']:
        if channel_data['type'] != 'category' and channel_data['name'] not in existing_channels:
            try:
                category = existing_categories.get(channel_data['category_name'])
                overwrites = {}
                for ow_data in channel_data.get('overwrites', []):
                    target = guild.get_role(int(ow_data['id'])) or guild.get_member(int(ow_data['id']))
                    if target:
                        overwrites[target] = disnake.PermissionOverwrite.from_pair(disnake.Permissions(ow_data['allow']), disnake.Permissions(ow_data['deny']))
                if channel_data['type'] == 'text':
                    await guild.create_text_channel(name=channel_data['name'], category=category, topic=channel_data.get('topic'), slowmode_delay=channel_data.get('slowmode_delay', 0), overwrites=overwrites)
                elif channel_data['type'] == 'voice':
                    await guild.create_voice_channel(name=channel_data['name'], category=category, overwrites=overwrites)
                log.append(f"{positivo} Canal criado: `{channel_data['name']}`")
                await asyncio.sleep(1)
            except Exception as e:
                log.append(f"{negativo} Falha ao criar canal `{channel_data['name']}`: {e}")
    log_message = "\n".join(log)
    if len(log_message) > 4000: log_message = log_message[:4000] + "\n..."
    success_container = disnake.ui.Container(
        disnake.ui.TextDisplay("# ✅ Restauração Concluída"),
        disnake.ui.Separator(),
        disnake.ui.TextDisplay(log_message)
    )
    await inter.edit_original_message(embed=None, components=[success_container])

class ConfigurarAuthModal(disnake.ui.Modal):
    def __init__(self):
        auth_local = ObterAuthLocal()
        components = [
            disnake.ui.TextInput(label="Client Secret", custom_id="secret", placeholder="Cole o Client Secret do seu bot", style=TextInputStyle.short),
            disnake.ui.TextInput(label="Código de Autorização da API", custom_id="authorization", value=auth_local.get("authorization") or "", placeholder="Use o botão 'Gerar Código'", style=TextInputStyle.paragraph),
        ]
        super().__init__(title="Configurar OAuth2 para seu Bot", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)
        secret, authorization = inter.text_values.values()

        auth_local = ObterAuthLocal()
        auth_local["authorization"] = authorization
        SalvarAuthLocal(auth_local)

        try:
            with open("Database/Server/cargos.json") as f:
                cargos = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            cargos = {}

        try:
            with open("Database/Server/canais.json") as f:
                canais = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            canais = {}

        verificado_role_id = cargos.get("verificado")
        log_verificados_id = canais.get("verificados")

        headers = {"authorization": authorization}
        payload = {
            "clientid": str(inter.bot.user.id),
            "secret": secret,
            "url": API_URL,
            "guild_id": str(inter.guild.id),
            "role": str(verificado_role_id) if verificado_role_id else None,
            "log_channel_verified": str(log_verificados_id) if log_verificados_id else None
        }
        
        try:
            response = requests.post(url=f"{API_URL}config", headers=headers, json=payload)
            if response.status_code == 200:
                await inter.followup.send(f"{positivo} Configurações salvas! O primeiro backup será feito agora...", ephemeral=True)
                await perform_backup(inter.guild)
            else:
                error_message = response.json().get('message', 'Erro desconhecido.')
                await inter.followup.send(f"{negativo} Falha ao salvar na API: {error_message}", ephemeral=True)
        except requests.exceptions.RequestException:
            await inter.followup.send(f"{negativo} Não foi possível conectar à API.", ephemeral=True)

class PuxarMembrosModal(disnake.ui.Modal):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(title="Recuperar Membros", components=[disnake.ui.TextInput(label="ID do Servidor de Destino", custom_id="guild_id", placeholder="Cole o ID do servidor aqui")])
    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)
        guild_id = inter.text_values["guild_id"]
        try:
            if not self.bot.get_guild(int(guild_id)):
                return await inter.followup.send(f"{negativo} O bot não está no servidor com o ID fornecido.", ephemeral=True)
        except (ValueError, TypeError):
            return await inter.followup.send(f"{negativo} ID do servidor inválido.", ephemeral=True)
        auth_local = ObterAuthLocal()
        if not auth_local.get("authorization"):
            return await inter.followup.send(f"{negativo} A API não está configurada.", ephemeral=True)
        headers = {"authorization": auth_local["authorization"]}
        payload = {"guildID": guild_id}
        try:
            response = requests.post(url=f"{API_URL}pullmembers/1", headers=headers, json=payload, timeout=5)
            if response.status_code == 202:
                await inter.followup.send(f"{positivo} Processo iniciado em segundo plano.", ephemeral=True)
            else:
                await inter.followup.send(f"{negativo} Falha ao iniciar o processo: {response.json().get('message')}", ephemeral=True)
        except requests.exceptions.Timeout:
             await inter.followup.send(f"{positivo} Processo iniciado (API demorou, mas o comando foi enviado).", ephemeral=True)
        except requests.exceptions.RequestException:
            await inter.followup.send(f"{negativo} Não foi possível conectar à API.", ephemeral=True)

class PersonalizarMensagemModal(disnake.ui.Modal):
    def __init__(self):
        msg_config = ObterMensagemLocal()
        components = [disnake.ui.TextInput(label="Conteúdo da mensagem", custom_id="content", value=msg_config.get("content", ""), style=TextInputStyle.long, required=False)]
        super().__init__(title="Personalizar Mensagem de Texto", components=components)
    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)
        msg_config = ObterMensagemLocal()
        msg_config["content"] = inter.text_values["content"]
        SalvarMensagemLocal(msg_config)
        components = obter_painel_personalizar()
        await inter.edit_original_message(embed=None, components=components)
        await inter.followup.send(f"{positivo} Conteúdo salvo!", ephemeral=True)

class PersonalizarEmbedModal(disnake.ui.Modal):
    def __init__(self):
        embed_config = ObterMensagemLocal().get("embed", {})
        components = [
            disnake.ui.TextInput(label="Título da Embed", custom_id="title", value=embed_config.get("title", ""), required=False),
            disnake.ui.TextInput(label="Descrição", custom_id="description", value=embed_config.get("description", ""), style=TextInputStyle.paragraph, required=False),
            disnake.ui.TextInput(label="Cor (HEX, ex: #FFFFFF)", custom_id="color", value=embed_config.get("color", ""), max_length=7, required=False),
        ]
        super().__init__(title="Personalizar Embed", components=components)
    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)
        title, description, color = inter.text_values.values()
        if color and not re.fullmatch(r"^#(?:[0-9a-fA-F]{6})$", color):
            return await inter.followup.send(f"{negativo} Cor HEX inválida. Use o formato `#RRGGBB`.", ephemeral=True)
        msg_config = ObterMensagemLocal()
        msg_config["embed"] = {"title": title, "description": description, "color": color}
        SalvarMensagemLocal(msg_config)
        components = obter_painel_personalizar()
        await inter.edit_original_message(embed=None, components=components)
        await inter.followup.send(f"{positivo} Embed salva!", ephemeral=True)

class PersonalizarBotaoModal(disnake.ui.Modal):
    def __init__(self):
        btn_config = ObterMensagemLocal().get("button", {})
        components = [
            disnake.ui.TextInput(label="Texto do Botão (Label)", custom_id="label", value=btn_config.get("label", "Verificar"), required=True),
            disnake.ui.TextInput(label="Emoji do Botão", custom_id="emoji", value=btn_config.get("emoji", ""), required=False),
        ]
        super().__init__(title="Personalizar Botão de Verificação", components=components)
    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)
        msg_config = ObterMensagemLocal()
        msg_config["button"] = {"label": inter.text_values["label"], "emoji": inter.text_values["emoji"]}
        SalvarMensagemLocal(msg_config)
        components = obter_painel_personalizar()
        await inter.edit_original_message(embed=None, components=components)
        await inter.followup.send(f"{positivo} Botão salvo!", ephemeral=True)

class AlternativoRoleModal(disnake.ui.Modal):
    def __init__(self):
        super().__init__(title="Configurar Cargo Alternativo",components=[disnake.ui.TextInput(label="ID do Servidor Alternativo", custom_id="guild_id", placeholder="ID do outro servidor onde o bot está", required=True), disnake.ui.TextInput(label="ID do Cargo a ser Entregue", custom_id="role_id", placeholder="ID do cargo a ser dado nesse outro servidor", required=True)])
    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)
        guild_id, role_id = inter.text_values["guild_id"], inter.text_values["role_id"]
        try:
            int(guild_id); int(role_id)
        except ValueError:
            return await inter.followup.send(f"{negativo} Os IDs do servidor e do cargo devem ser números.", ephemeral=True)
        auth_local = ObterAuthLocal()
        if not auth_local.get("authorization"):
            return await inter.followup.send(f"{negativo} A API principal precisa ser configurada primeiro.", ephemeral=True)
        headers = {"authorization": auth_local["authorization"]}
        payload = {"target_guild_id": guild_id, "target_role_id": role_id}
        try:
            response = requests.post(url=f"{API_URL}config/alternative-role", headers=headers, json=payload)
            if response.status_code == 200:
                await inter.followup.send(f"{positivo} Cargo alternativo salvo com sucesso!", ephemeral=True)
            else:
                await inter.followup.send(f"{negativo} Falha ao salvar na API: {response.json().get('message', 'Erro.')}", ephemeral=True)
        except requests.exceptions.RequestException:
            await inter.followup.send(f"{negativo} Não foi possível conectar à API.", ephemeral=True)

def gerar_componentes_verificacao(preview_mode=False):
    msg_config = ObterMensagemLocal()
    content, embed_data, button_data = msg_config.get('content'), msg_config.get('embed'), msg_config.get('button', {})
    embed = None
    if embed_data and (embed_data.get('title') or embed_data.get('description')):
        try:
            color_hex = embed_data.get("color", "#00FFFF").lstrip('#')
            embed_data_copy = embed_data.copy()
            embed_data_copy["color"] = int(color_hex, 16)
            embed = disnake.Embed.from_dict(embed_data_copy)
        except:
            embed = disnake.Embed.from_dict({k: v for k, v in embed_data.items() if k != 'color'})
    components = [disnake.ui.Button(label=button_data.get("label", "Verificar"), emoji=button_data.get("emoji"), style=ButtonStyle.blurple, custom_id="VerificarOAuth2", disabled=preview_mode)]
    return content, embed, components

def obter_painel_personalizar():
    msg_config, embed_config, btn_config = ObterMensagemLocal(), ObterMensagemLocal().get("embed", {}), ObterMensagemLocal().get("button", {})
    
    container_elems = [
        disnake.ui.TextDisplay("# 🎨 Personalizar Mensagem OAuth2"),
        disnake.ui.Separator(),
        disnake.ui.TextDisplay("Configure a aparência da mensagem de verificação que será enviada aos usuários."),
        disnake.ui.Separator(),
        disnake.ui.ActionRow(
            disnake.ui.Button(style=ButtonStyle.primary, label="Configurar Texto", custom_id="CfgContent_eCloud", emoji=mensagem), 
            disnake.ui.Button(custom_id="LimparContent_eCloud", emoji=apagar, style=ButtonStyle.danger, disabled=not msg_config.get('content'))
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(style=ButtonStyle.primary, label="Configurar Embed", custom_id="CfgEmbed_eCloud", emoji=embedE), 
            disnake.ui.Button(custom_id="LimparEmbed_eCloud", emoji=apagar, style=ButtonStyle.danger, disabled=not embed_config.get('title'))
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(style=ButtonStyle.primary, label="Configurar Botão", custom_id="CfgBotao_eCloud", emoji=editar), 
            disnake.ui.Button(label="Preview", custom_id="Preview_eCloud", emoji=preview, style=ButtonStyle.secondary),
            disnake.ui.Button(style=ButtonStyle.primary, label="Enviar Painel", custom_id="EnviarPainel_eCloud", emoji=arrow)
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar",emoji=voltar, custom_id="VoltarPrincipal_eCloud", style=ButtonStyle.grey)
        )
    ]
    
    container = disnake.ui.Container(*container_elems)
    return [container]
  
def obter_painel_psico_config():
    config = ObterPsicoConfig()
    
    vo_ativo = config.get("verificado_obrigatorio", True)
    si_ativo = config.get("sincronizacao_inteligente", True)
    cp_ativo = config.get("cargo_persistente", True)
    vpn_ativo = config.get("checkVPN", False)
    proxy_ativo = config.get("checkProxy", False)
    alt_ativo = config.get("checkAlt", False)
    
    container_elems = [
        disnake.ui.TextDisplay("# ⚙️ Psico Config"),
        disnake.ui.Separator(),
        disnake.ui.TextDisplay("Configurações avançadas e comportamentos automáticos do sistema eCloud."),
        disnake.ui.Separator(),
        disnake.ui.TextDisplay(f"**Verificado Obrigatório:** {positivo if vo_ativo else negativo} {'Ativado' if vo_ativo else 'Desativado'}\n*Exige verificação para usar certas funções.*"),
        disnake.ui.TextDisplay(f"**Sincronização Inteligente (Backup):** {positivo if si_ativo else negativo} {'Ativado' if si_ativo else 'Desativado'}\n*Ativa o backup automático do servidor a cada hora.*"),
        disnake.ui.TextDisplay(f"**Cargo Persistente:** {positivo if cp_ativo else negativo} {'Ativado' if cp_ativo else 'Desativado'}\n*Devolve o cargo de verificado se um membro sair e voltar.*"),
        disnake.ui.Separator(),
        disnake.ui.TextDisplay(f"**Verificação de VPN:** {positivo if vpn_ativo else negativo} {'Ativado' if vpn_ativo else 'Desativado'} *Bloqueia usuários usando VPN.*"),
        disnake.ui.TextDisplay(f"**Verificação de Proxy:** {positivo if proxy_ativo else negativo} {'Ativado' if proxy_ativo else 'Desativado'} *Bloqueia usuários usando Proxy.*"),
        disnake.ui.TextDisplay(f"**Verificação de Contas Novas (Alt):** {positivo if alt_ativo else negativo} {'Ativado' if alt_ativo else 'Desativado'} *Bloqueia contas do Discord muito recentes.*"),
        disnake.ui.Separator(),
        disnake.ui.TextDisplay("**Cargos Alternativos:** *Entrega um cargo específico em outro servidor quando um membro se verifica neste. Use o botão abaixo para configurar.*"),
        disnake.ui.Separator(),
        disnake.ui.ActionRow(
            disnake.ui.Button(label=f"VPN{'Off' if not vpn_ativo else 'On'}", style=ButtonStyle.green if vpn_ativo else ButtonStyle.red, custom_id="TogglePsico_checkVPN"),
            disnake.ui.Button(label=f"Proxy{'Off' if not proxy_ativo else 'On'}", style=ButtonStyle.green if proxy_ativo else ButtonStyle.red, custom_id="TogglePsico_checkProxy"),
            disnake.ui.Button(label=f"Alt {'Off' if not alt_ativo else 'On'}", style=ButtonStyle.green if alt_ativo else ButtonStyle.red, custom_id="TogglePsico_checkAlt")
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Desabilitar Verificado Obrigatório" if vo_ativo else "Ativar Verificado Obrigatório", style=ButtonStyle.red if vo_ativo else ButtonStyle.green, custom_id="TogglePsico_verificado_obrigatorio"),
            disnake.ui.Button(label="Desabilitar Sincronização" if si_ativo else "Ativar Sincronização", style=ButtonStyle.red if si_ativo else ButtonStyle.green, custom_id="TogglePsico_sincronizacao_inteligente")
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Desabilitar Cargo Persistente" if cp_ativo else "Ativar Cargo Persistente", style=ButtonStyle.red if cp_ativo else ButtonStyle.green, custom_id="TogglePsico_cargo_persistente"),
            disnake.ui.Button(label="Configurar Cargos Alternativos", style=ButtonStyle.blurple, custom_id="ConfigAlternativo_eCloud")
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=voltar, style=ButtonStyle.grey, custom_id="VoltarPrincipal_eCloud")
        )
    ]
    
    container = disnake.ui.Container(*container_elems)
    return [container]

class ECloudCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.backup_loop.start()
    def cog_unload(self):
        self.backup_loop.cancel()
    
    @tasks.loop(hours=1.0)
    async def backup_loop(self):
        psico_config = ObterPsicoConfig()
        if not psico_config.get("sincronizacao_inteligente", True):
            print("[Backup Loop] Sincronização inteligente desativada. Pulando backup.")
            return

        auth_local = ObterAuthLocal()
        if not auth_local or not auth_local.get("authorization"):
            print("[Backup Loop] Autorização da API não configurada. Pulando backup.")
            return

        try:
            with open("config.json", "r") as f:
                main_config = json.load(f)
            main_server_id_str = main_config.get("server")
        except (FileNotFoundError, KeyError):
            print("[Backup Loop] 'config.json' ou a chave 'server' não encontrada. Pulando backup.")
            return

        if not main_server_id_str:
            print("[Backup Loop] Servidor principal não definido em config.json. Pulando backup.")
            return
            
        try:
            main_server_id = int(main_server_id_str)
        except ValueError:
            print(f"[Backup Loop] ID do servidor em config.json ('{main_server_id_str}') não é válido. Pulando backup.")
            return

        main_guild = self.bot.get_guild(main_server_id)

        if main_guild:
            await perform_backup(main_guild)
        else:
            print(f"[Backup Loop] Bot não está no servidor principal configurado (ID: {main_server_id}). Pulando backup.")

    @backup_loop.before_loop
    async def before_backup_loop(self):
        await self.bot.wait_until_ready()
    async def obter_painel_principal(self, inter: disnake.MessageInteraction):
        auth_local = ObterAuthLocal()
        verificada, members = False, 0
        if auth_local.get("authorization"):
            try:
                headers = {"authorization": auth_local["authorization"]}
                if requests.get(f"{API_URL}verifyKey", headers=headers, timeout=3).status_code == 200:
                    verificada = True
                members_response = requests.get(f"{API_URL}members", headers=headers, timeout=3)
                if members_response.status_code == 200: members = int(members_response.json().get("message", 0))
            except: members = 0
        
        try:
            with open("Database/Server/cargos.json") as f:
                cargos = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            cargos = {}

        is_configured, disable_actions, disable_recover = verificada, not verificada, (members == 0 or not verificada)
        
        # Criar container com informações do ECloud
        container_elems = [
            disnake.ui.TextDisplay(f"# {cloud} Meu EtxCloud Drive"),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(f"Seu ¿Cloud? está **{'Ativado' if is_configured else 'Desativado'}**."),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(f"**{cloud} Status da API:** {positivo if is_configured else negativo} `{'Configurado' if is_configured else 'Não configurado'}`"),
            disnake.ui.TextDisplay(f"**{users} Membros Verificados:** `{members}`"),
        ]
        
        cargo_verificado_value = f"<@&{cargos.get('verificado')}>" if cargos.get('verificado') else f"{negativo} `Não configurado`"
        container_elems.append(disnake.ui.TextDisplay(f"**{cargo} Cargo de Verificado:** {cargo_verificado_value}"))
        
        last_sync = auth_local.get("last_backup_timestamp")
        sync_text = f"<t:{int(last_sync)}:R>" if last_sync else f"{negativo} `Nunca`"
        container_elems.append(disnake.ui.TextDisplay(f"**{reload} Última Sincronização em Nuvem:** {sync_text}"))
        container_elems.append(disnake.ui.TextDisplay(f"**{rotas} URL da API:** {positivo} `{API_URL}`"))
        
        container_elems.extend([
            disnake.ui.Separator(),
            disnake.ui.ActionRow(
                disnake.ui.Button(style=ButtonStyle.primary, label="Mensagem OAuth2", custom_id="CustomizarMsg_eCloud", emoji=mensagem, disabled=disable_actions), 
                disnake.ui.Button(style=ButtonStyle.green, label="Restaurar Servidor", custom_id="RestaurarServidor_eCloud", emoji=reload, disabled=disable_actions), 
                disnake.ui.Button(style=ButtonStyle.green,label="Recuperar Membros", custom_id="RecuperarMembros_eCloud", emoji=reload, disabled=disable_recover)
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(style=ButtonStyle.secondary, label="Vincular Bot OAuth2", custom_id="ConfigOAuth2_eCloud", emoji=config3), 
                disnake.ui.Button(style=ButtonStyle.secondary, label="Psyche siCloud Actions", custom_id="PsicoConfig_eCloud", emoji=cloud, disabled=disable_actions)
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(style=ButtonStyle.green, label="Criar EtxCloud Authorization ", custom_id="GerarCodigo_eCloud", emoji=tools), 
                disnake.ui.Button(label="WebSite Desing",emoji="<:website:1396063016776106014>", style=ButtonStyle.grey, custom_id="WebSiteDesign_eCloud", disabled=disable_actions),
                disnake.ui.Button(label="Voltar", emoji=voltar, custom_id="PainelInicial")
            )
        ])
        
        container = disnake.ui.Container(*container_elems)
        return [container]

    @commands.Cog.listener("on_button_click")
    async def ECloudButtonListener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        if custom_id == "GerenciarPainelECloud" or custom_id == "VoltarPrincipal_eCloud":
            loading_container = disnake.ui.Container(
                disnake.ui.TextDisplay(f"{carregarAnimado} Carregando...")
            )
            await inter.response.edit_message(embed=None, components=[loading_container])
            components = await self.obter_painel_principal(inter)
            await inter.edit_original_message(embed=None, components=components)
        elif custom_id == "VerificarOAuth2":
            await inter.response.defer(ephemeral=True)
            url = f'{API_URL}login?guild_id={inter.guild.id}&client_id={self.bot.user.id}'
            try:
                response = requests.get(url=url)
                if response.status_code == 200 and response.json().get("authUrl"):
                    await inter.followup.send(components=[disnake.ui.Button(label="Clique aqui para verificar", url=response.json()["authUrl"])], ephemeral=True)
                else:
                    await inter.followup.send(f"{negativo} Falha ao obter URL da API: `{response.json().get('message', 'Erro desconhecido')}`", ephemeral=True)
            except requests.exceptions.RequestException as e:
                await inter.followup.send(f"{negativo} Erro de conexão com a API: {e}", ephemeral=True)
        elif custom_id == "RestaurarServidor_eCloud":
            confirm_container = disnake.ui.Container(
                disnake.ui.TextDisplay("# ⚠️ Confirmação"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("Você tem certeza que deseja restaurar o servidor a partir do último backup?"),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Confirmar Restauração", style=ButtonStyle.danger, custom_id="ConfirmarRestauracao_eCloud"),
                    disnake.ui.Button(label="Cancelar", style=ButtonStyle.grey, custom_id="VoltarPrincipal_eCloud")
                )
            )
            await inter.response.edit_message(embed=None, components=[confirm_container])
        elif custom_id == "ConfirmarRestauracao_eCloud":
            await restore_from_backup(inter)
        elif custom_id == "GerarCodigo_eCloud":
            await inter.response.defer(ephemeral=True)
            with open("config.json") as f:
                bot_principal_config = json.load(f)
            try:
                response = requests.post(f"{API_URL}generate-auth", json={"token": bot_principal_config["token"]})
                if response.status_code == 200:
                    auth_key = response.json()['authorization']
                    SalvarAuthLocal({"authorization": auth_key, "last_backup_timestamp": ObterAuthLocal().get("last_backup_timestamp")})
                    await inter.followup.send(f"{positivo} Seu código de autorização foi gerado e salvo!\n```{auth_key}```", ephemeral=True)
                else:
                    await inter.followup.send(f"{negativo} Falha ao gerar código: {response.json().get('message')}", ephemeral=True)
            except requests.exceptions.RequestException:
                await inter.followup.send(f"{negativo} Não foi possível conectar à API.", ephemeral=True)
        elif custom_id == "ConfigOAuth2_eCloud":
            await inter.response.send_modal(ConfigurarAuthModal())
        elif custom_id == "CustomizarMsg_eCloud":
            components = obter_painel_personalizar()
            await inter.response.edit_message(embed=None, components=components)
        elif custom_id == "CfgContent_eCloud":
            await inter.response.send_modal(PersonalizarMensagemModal())
        elif custom_id == "LimparContent_eCloud":
            await inter.response.defer()
            msg_config = ObterMensagemLocal(); msg_config['content'] = ""; SalvarMensagemLocal(msg_config)
            components = obter_painel_personalizar()
            await inter.edit_original_message(embed=None, components=components)
        elif custom_id == "CfgEmbed_eCloud":
            await inter.response.send_modal(PersonalizarEmbedModal())
        elif custom_id == "LimparEmbed_eCloud":
            await inter.response.defer()
            msg_config = ObterMensagemLocal(); msg_config['embed'] = {}; SalvarMensagemLocal(msg_config)
            components = obter_painel_personalizar()
            await inter.edit_original_message(embed=None, components=components)
        elif custom_id == "CfgBotao_eCloud":
            await inter.response.send_modal(PersonalizarBotaoModal())
        elif custom_id == "Preview_eCloud":
            content, embed, components = gerar_componentes_verificacao(preview_mode=True)
            kwargs = {"content": content, "components": components, "ephemeral": True}
            if embed: kwargs["embed"] = embed
            await inter.response.send_message(**kwargs)
        elif custom_id == "EnviarPainel_eCloud":
            await inter.response.send_message(components=[disnake.ui.ChannelSelect(placeholder="Selecione o canal", custom_id="EnviarDropdown_eCloud")], ephemeral=True)
        elif custom_id == "RecuperarMembros_eCloud":
            await inter.response.send_modal(PuxarMembrosModal(self.bot))
        elif custom_id == "PsicoConfig_eCloud":
            components = obter_painel_psico_config()
            await inter.response.edit_message(embed=None, components=components)
        elif custom_id.startswith("TogglePsico_"):
            await inter.response.defer()
            config_key = custom_id.split("_", 1)[1]
            psico_config = ObterPsicoConfig()
            psico_config[config_key] = not psico_config.get(config_key, False)
            SalvarPsicoConfig(psico_config)
            sync_psico_to_api()
            components = obter_painel_psico_config()
            await inter.edit_original_message(embed=None, components=components)
        elif custom_id == "ConfigAlternativo_eCloud":
            await inter.response.send_modal(AlternativoRoleModal())

    @commands.Cog.listener("on_dropdown")
    async def ECloudDropdownListener(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "EnviarDropdown_eCloud":
            await inter.response.defer(ephemeral=True)
            channel = inter.guild.get_channel(int(inter.values[0]))
            content, embed, components = gerar_componentes_verificacao(preview_mode=False)
            try:
                msg = await channel.send(content=content, embed=embed, components=components)
                await inter.followup.send(f"{positivo} Mensagem enviada com sucesso em {msg.jump_url}", ephemeral=True)
            except Exception as e:
                await inter.followup.send(f"{negativo} Falha ao enviar a mensagem: {e}", ephemeral=True)

def setup(bot: commands.Bot):
    bot.add_cog(ECloudCommand(bot))