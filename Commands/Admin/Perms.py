# Perms.py (Versão Corrigida)
import disnake
from disnake.ext import commands, tasks
import json
from datetime import datetime, time

# =====================================================================================
# INÍCIO DA LÓGICA DE VERIFICAÇÃO
# =====================================================================================

def carregar_config_para_verificacao():
    try:
        with open("config.json", 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def carregar_perms_para_verificacao():
    try:
        with open("Database/perms.json", 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def verificar_permissao_unificado(user_id: int, tipo: str = None, nome_permissao: str = None) -> bool:
    config = carregar_config_para_verificacao()
    owner_id = config.get("owner")

    if str(user_id) == str(owner_id):
        return True

    perms_data = carregar_perms_para_verificacao()
    user_perms = perms_data.get(str(user_id))

    if not user_perms or not isinstance(user_perms, dict):
        return False

    if user_perms.get("geral", False):
        return True

    if not tipo or not nome_permissao:
        return False

    tipo_perms = user_perms.get(tipo, {})
    
    if tipo_perms.get("geral", False):
        return True

    return tipo_perms.get(nome_permissao, False)

# =====================================================================================
# FIM DA LÓGICA DE VERIFICAÇÃO
# =====================================================================================


from Functions.CarregarEmojis import *

# --- Constantes de Permissões ---
COMANDOS_DISPONIVEIS = {
    "ban": "Comando /ban", "kick": "Comando /kick", "cls": "Comando /cls",
    "lock": "Comando /lock", "unlock": "Comando /unlock", "lockall": "Comando /lockall",
    "addemoji": "Comando /addemoji", "connect": "Comando /connect"
}

PAINEL_DISPONIVEL = {
    "GerenciarPainelVendas": "Painel - Loja", "GerenciarPainelTicket": "Painel - Ticket",
    "GerenciarPainelBoasVindas": "Painel - Boas Vindas", "GerenciarPainelComunidade": "Painel - Comunidade",
    "GerenciarAcoesAutomaticas": "Painel - Ações Automáticas", "GerenciarPainelPersonalizar": "Painel - Personalização",
    "GerenciarPainelECloud": "Painel - Meu EtxCloud", "GerenciarPainelRendimento": "Painel - Rendimento",
    "GerenciarPainelConfigurar": "Painel - Definições", "GerenciarPainelGiveaways": "Painel - Giveaways",
    "GerenciarProtecaoServidor": "Painel - Proteção", "RenovarPlano": "Painel - Renovar",
    "GerenciarPainelAjuda": "Painel - Ajuda", "GerenciarReconfiguracao": "Painel - Reconfiguração",
    "AbrirPainelIA": "Painel - Assistente IA", "GerenciarPermsUsers": "Painel - Permissões"
}

# --- Funções Auxiliares de UI ---

def carregar_dados_perms_ui():
    try:
        with open("Database/perms.json", 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def salvar_dados_perms_ui(data):
    with open("Database/perms.json", 'w') as f:
        json.dump(data, f, indent=4)

def obter_embed_principal():
    perms_data = carregar_dados_perms_ui()
    usuarios_com_perm = [f"- <@{user_id}>" for user_id in perms_data.keys()]
    lista_usuarios = "\n".join(usuarios_com_perm) if usuarios_com_perm else f"{aviso} Nenhum usuário com permissões personalizadas."

    embed = disnake.Embed(
        title="🛡️ Gerenciador de Permissões",
        description="Adicione, remova ou configure permissões detalhadas para os usuários do bot.",
        color=disnake.Color.blurple()
    )
    embed.add_field(name="Usuários com Permissão", value=lista_usuarios, inline=False)
    
    components = [
        disnake.ui.Button(label="Adicionar Membro", emoji=mais2, custom_id="perms_add_user", style=disnake.ButtonStyle.green),
        disnake.ui.Button(label="Remover Membro", emoji=menos2, custom_id="perms_remove_user", style=disnake.ButtonStyle.red),
        disnake.ui.Button(label="Configurar Permissões", emoji=config2, custom_id="perms_configure_user", style=disnake.ButtonStyle.blurple)
    ]
    return embed, [components]

def obter_embed_config_tipo():
    embed = disnake.Embed(
        title="⚙️ Configurar Permissões",
        description="Selecione o tipo de permissão que você deseja configurar para um usuário.",
        color=disnake.Color.blurple()
    )
    options = [
        disnake.SelectOption(label="Permissões de Comando", value="command", emoji="⌨️"),
        disnake.SelectOption(label="Permissões do Painel", value="panel", emoji="📋"),
        disnake.SelectOption(label="Permissão com Tempo", value="timed", emoji="⏳")
    ]
    select = disnake.ui.Select(placeholder="Escolha uma categoria...", custom_id="perms_config_type_select", options=options)
    botao_voltar = disnake.ui.Button(label="Voltar", custom_id="GerenciarPermsUsers", style=disnake.ButtonStyle.grey)
    return embed, [[select], [botao_voltar]]


class PermsCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.owner_id = carregar_config_para_verificacao().get("owner")
        self.timed_perms_loop.start()

    def cog_unload(self):
        self.timed_perms_loop.cancel()

    @tasks.loop(minutes=1)
    async def timed_perms_loop(self):
        await self.bot.wait_until_ready()
        perms_data = carregar_dados_perms_ui()
        now = datetime.now().time()
        
        needs_save = False
        for user_id, data in perms_data.items():
            if not isinstance(data, dict): continue

            timed_info = data.get("timed")
            if not timed_info or not timed_info.get("enabled"):
                continue

            try:
                start_time = time.fromisoformat(timed_info["start"])
                end_time = time.fromisoformat(timed_info["end"])
            except (ValueError, KeyError):
                continue

            if now.hour == start_time.hour and now.minute == start_time.minute and not data.get("geral", False):
                data["geral"] = True; needs_save = True
                print(f"[TimedPerms] Permissão GERAL ativada para o usuário {user_id}.")

            elif now.hour == end_time.hour and now.minute == end_time.minute and data.get("geral", True):
                data["geral"] = False; needs_save = True
                print(f"[TimedPerms] Permissão GERAL desativada para o usuário {user_id}.")
        
        if needs_save:
            salvar_dados_perms_ui(perms_data)

    @commands.slash_command(name="perms")
    async def perms(self, inter: disnake.ApplicationCommandInteraction):
        if str(inter.author.id) != self.owner_id:
            return await inter.response.send_message(f"{negativo} Apenas o dono do bot pode usar este comando.", ephemeral=True)
        
        embed, components = obter_embed_principal()
        await inter.response.send_message(embed=embed, components=components, ephemeral=True)

    @commands.Cog.listener("on_button_click")
    async def perms_button_listener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        if not custom_id.startswith("perms_") and custom_id != "GerenciarPermsUsers":
            return
        
        if not self.bot.verificar_permissao(inter.author.id):
             return await inter.response.send_message(f"{negativo} Você não tem permissão para interagir aqui.", ephemeral=True)

        await inter.response.defer()

        if custom_id == "GerenciarPermsUsers":
            embed, components = obter_embed_principal()
            await inter.edit_original_message(embed=embed, components=components)
        elif custom_id == "perms_configure_user":
            embed, components = obter_embed_config_tipo()
            await inter.edit_original_message(embed=embed, components=components)
        elif custom_id in ["perms_add_user", "perms_remove_user"]:
            action = "add" if custom_id == "perms_add_user" else "remove"
            select = disnake.ui.UserSelect(custom_id=f"perms_user_select_basic:{action}", placeholder=f"Selecione um usuário para {action.lower()}r")
            await inter.edit_original_message(components=[select])
        elif custom_id.startswith("perms_timed_"):
            parts = custom_id.split(":")
            action, user_id = parts[0], parts[1]
            if action == "perms_timed_set_modal":
                await inter.response.send_modal(
                    title="Definir Horário de Permissão",
                    custom_id=f"perms_timed_modal_submit:{user_id}",
                    components=[
                        disnake.ui.TextInput(label="Horário de Entrada (HH:MM)", custom_id="start_time", placeholder="Ex: 09:00"),
                        disnake.ui.TextInput(label="Horário de Saída (HH:MM)", custom_id="end_time", placeholder="Ex: 18:00")
                    ]
                )
                return
            elif action == "perms_timed_toggle":
                perms_data = carregar_dados_perms_ui()
                user_data = perms_data.setdefault(user_id, {})
                timed_data = user_data.setdefault("timed", {})
                timed_data["enabled"] = not timed_data.get("enabled", False)
                salvar_dados_perms_ui(perms_data)
                embed, comps = self.obter_embed_perm_timed(inter.guild.get_member(int(user_id)))
                await inter.edit_original_message(embed=embed, components=comps)
    
    @commands.Cog.listener("on_modal_submit")
    async def perms_modal_listener(self, inter: disnake.ModalInteraction):
        custom_id = inter.custom_id
        if not custom_id.startswith("perms_timed_modal_submit"): return
        await inter.response.defer(ephemeral=True)
        user_id = custom_id.split(":")[1]
        start_str, end_str = inter.text_values["start_time"], inter.text_values["end_time"]
        try:
            time.fromisoformat(start_str); time.fromisoformat(end_str)
        except ValueError:
            return await inter.followup.send(f"{negativo} Formato de hora inválido. Use HH:MM.", ephemeral=True)
        perms_data = carregar_dados_perms_ui()
        user_data = perms_data.setdefault(user_id, {})
        timed_data = user_data.setdefault("timed", {})
        timed_data["start"], timed_data["end"] = start_str, end_str
        salvar_dados_perms_ui(perms_data)
        embed, comps = self.obter_embed_perm_timed(inter.guild.get_member(int(user_id)))
        await inter.edit_original_message(embed=embed, components=comps)

    @commands.Cog.listener("on_dropdown")
    async def perms_dropdown_listener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        if not custom_id.startswith("perms_"): return
        if not self.bot.verificar_permissao(inter.author.id):
             return await inter.response.send_message(f"{negativo} Você não tem permissão para interagir aqui.", ephemeral=True)
        
        await inter.response.defer()
        
        if custom_id == "perms_config_type_select":
            perm_type = inter.values[0]
            embed = disnake.Embed(title="Selecione um Usuário", description=f"Escolha um usuário para gerenciar as **permissões de {perm_type}**.", color=disnake.Color.blurple())
            user_select = disnake.ui.UserSelect(custom_id=f"perms_select_user_for:{perm_type}", placeholder="Selecione um usuário...")
            botao_voltar = disnake.ui.Button(label="Voltar", custom_id="perms_configure_user", style=disnake.ButtonStyle.grey)
            await inter.edit_original_message(embed=embed, components=[[user_select], [botao_voltar]])

        elif custom_id.startswith("perms_select_user_for:"):
            perm_type = custom_id.split(":")[1]
            user_id = inter.values[0]
            member = inter.guild.get_member(int(user_id))
            
            perms_data = carregar_dados_perms_ui()
            user_entry = perms_data.get(user_id)
            if not isinstance(user_entry, dict):
                print(f"[Perms] Convertendo usuário {user_id} do formato antigo para o novo.")
                perms_data[user_id] = {"geral": False, "command": {}, "panel": {}, "timed": {}}
                salvar_dados_perms_ui(perms_data)
            
            if perm_type == "command": embed, comps = self.obter_embed_perm_comando(member)
            elif perm_type == "panel": embed, comps = self.obter_embed_perm_painel(member)
            elif perm_type == "timed": embed, comps = self.obter_embed_perm_timed(member)
            await inter.edit_original_message(embed=embed, components=comps)

        elif custom_id.startswith("perms_cmd_toggle_select:") or custom_id.startswith("perms_panel_toggle_select:"):
            is_command = "cmd" in custom_id
            perm_type, user_id = ("command", custom_id.split(":")[1]) if is_command else ("panel", custom_id.split(":")[1])
            perms_data = carregar_dados_perms_ui()
            user_data = perms_data.setdefault(user_id, {})
            type_perms = user_data.setdefault(perm_type, {})
            all_perms = COMANDOS_DISPONIVEIS.keys() if is_command else PAINEL_DISPONIVEL.keys()
            for perm_name in all_perms: type_perms[perm_name] = perm_name in inter.values
            type_perms["geral"] = "geral" in inter.values
            salvar_dados_perms_ui(perms_data)
            member = inter.guild.get_member(int(user_id))
            if is_command: embed, comps = self.obter_embed_perm_comando(member)
            else: embed, comps = self.obter_embed_perm_painel(member)
            await inter.edit_original_message(embed=embed, components=comps)
            
        elif custom_id.startswith("perms_user_select_basic:"):
            action, user_id = custom_id.split(":")[1], inter.values[0]
            perms_data = carregar_dados_perms_ui()
            if action == "add" and user_id not in perms_data: perms_data[user_id] = {"geral": False, "command": {}, "panel": {}, "timed": {}}
            elif action == "remove": perms_data.pop(user_id, None)
            salvar_dados_perms_ui(perms_data)
            embed, comps = obter_embed_principal()
            await inter.edit_original_message(embed=embed, components=comps)

    # --- FUNÇÕES GERADORAS DE EMBEDS DE CONFIGURAÇÃO (COM CORREÇÃO) ---
    
    def obter_embed_perm_comando(self, member: disnake.Member):
        perms_data = carregar_dados_perms_ui()
        user_perms = perms_data.get(str(member.id), {}).get("command", {})
        embed = disnake.Embed(title=f"⌨️ Permissões de Comando para {member.display_name}", color=disnake.Color.blue())
        options = [disnake.SelectOption(label="Permissão Geral (Todos os Comandos)", value="geral", emoji="👑", default=user_perms.get("geral", False))]
        options.extend([disnake.SelectOption(label=label, value=key, default=user_perms.get(key, False)) for key, label in COMANDOS_DISPONIVEIS.items()])
        
        # --- CORREÇÃO APLICADA AQUI ---
        select = disnake.ui.Select(
            placeholder="Alterne as permissões...", 
            custom_id=f"perms_cmd_toggle_select:{member.id}", 
            options=options, 
            min_values=0, 
            max_values=len(options) # Em vez de 'multiple=True'
        )
        botoes = [disnake.ui.Button(label="Gerenciar Outro Usuário", custom_id="perms_configure_user", style=disnake.ButtonStyle.grey), disnake.ui.Button(label="Voltar ao Menu Principal", custom_id="GerenciarPermsUsers", style=disnake.ButtonStyle.grey)]
        return embed, [[select], botoes]
        
    def obter_embed_perm_painel(self, member: disnake.Member):
        perms_data = carregar_dados_perms_ui()
        user_perms = perms_data.get(str(member.id), {}).get("panel", {})
        embed = disnake.Embed(title=f"📋 Permissões de Painel para {member.display_name}", color=disnake.Color.purple())
        options = [disnake.SelectOption(label="Permissão Geral (Todos os Botões)", value="geral", emoji="👑", default=user_perms.get("geral", False))]
        options.extend([disnake.SelectOption(label=label, value=key, default=user_perms.get(key, False)) for key, label in PAINEL_DISPONIVEL.items()])

        # --- CORREÇÃO APLICADA AQUI ---
        select = disnake.ui.Select(
            placeholder="Alterne as permissões...", 
            custom_id=f"perms_panel_toggle_select:{member.id}", 
            options=options, 
            min_values=0, 
            max_values=len(options) # Em vez de 'multiple=True'
        )
        botoes = [disnake.ui.Button(label="Gerenciar Outro Usuário", custom_id="perms_configure_user", style=disnake.ButtonStyle.grey), disnake.ui.Button(label="Voltar ao Menu Principal", custom_id="GerenciarPermsUsers", style=disnake.ButtonStyle.grey)]
        return embed, [[select], botoes]

    def obter_embed_perm_timed(self, member: disnake.Member):
        perms_data = carregar_dados_perms_ui()
        timed_data = perms_data.get(str(member.id), {}).get("timed", {})
        status = "Ativado" if timed_data.get("enabled") else "Desativado"
        embed = disnake.Embed(title=f"⏳ Permissão com Tempo para {member.display_name}", color=disnake.Color.gold())
        embed.add_field(name="Status", value=status); embed.add_field(name="Horário de Entrada", value=timed_data.get("start", "N/A")); embed.add_field(name="Horário de Saída", value=timed_data.get("end", "N/A"))
        embed.set_footer(text="Quando ativado, o usuário receberá permissão geral apenas entre os horários definidos.")
        botoes = [
            disnake.ui.Button(label="Definir Horário", emoji="⏰", custom_id=f"perms_timed_set_modal:{member.id}"),
            disnake.ui.Button(label=f"Desativar" if status == "Ativado" else "Ativar", custom_id=f"perms_timed_toggle:{member.id}", style=disnake.ButtonStyle.red if status == "Ativado" else disnake.ButtonStyle.green),
            disnake.ui.Button(label="Gerenciar Outro Usuário", custom_id="perms_configure_user", style=disnake.ButtonStyle.grey),
            disnake.ui.Button(label="Voltar ao Menu Principal", custom_id="GerenciarPermsUsers", style=disnake.ButtonStyle.grey)
        ]
        return embed, [botoes]

def setup(bot: commands.Bot):
    bot.verificar_permissao = verificar_permissao_unificado
    bot.add_cog(PermsCommand(bot))