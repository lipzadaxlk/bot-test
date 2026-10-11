import disnake
from disnake.ext import commands
import json
import os
from Functions.CarregarEmojis import *

ECONOMY_CONFIG_FILE = "Database/Economia/configuracao.json"
USERS_DATA_FILE = "Database/Economia/users.json"
PETS_DATA_FILE = "Database/Economia/petusers.json"
MINER_DATA_FILE = "Database/Economia/mineradoras.json"

COMMANDS_BY_CATEGORY = {
    "Economia": ["daily", "trabalhar", "roubar", "banco", "aposta", "crime", "pagar", "rep", "profile", "contribuição", "minerar", "pescar", "slots"],
    "Roleplay": ["abraçar", "casar", "divórcio", "beijar", "gf", "lua de mel", "afk", "x1", "whatsapp", "ship", "pet", "pet battle", "loja", "prefeitura", "mercador"],
    "Diversão": ["8ball", "akinator", "waifu", "snake", "raul", "manga", "joke", "jokenpo", "ironmen", "hangmen", "guess", "diabo", "buti"],
    "Nsfw": ["anal", "hentai", "neko", "feet", "lesbian", "boobs", "pussy"]
}

def get_default_config():
    config = {"categorias": {}}
    for category, cmds in COMMANDS_BY_CATEGORY.items():
        config["categorias"][category.lower()] = {cmd.lower(): True for cmd in cmds}
    return config

def load_json(file_path, is_econ_config=False):
    dir_path = os.path.dirname(file_path)
    if dir_path and not os.path.exists(dir_path):
        os.makedirs(dir_path)
    if not os.path.exists(file_path):
        default_data = get_default_config() if is_econ_config else {}
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, indent=4)
        return default_data
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not data and is_econ_config:
                return get_default_config()
            return data
    except (json.JSONDecodeError, FileNotFoundError):
        return get_default_config() if is_econ_config else {}

def save_json(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

class MoedaModal(disnake.ui.Modal):
    def __init__(self, view):
        self.parent_view = view
        config = load_json("config.json")
        components = [
            disnake.ui.TextInput(
                label="Nome da Moeda", 
                custom_id="moeda_nome", 
                value=config.get("moeda_nome", "Moedas"), 
                max_length=20
            ),
            disnake.ui.TextInput(
                label="Emoji da Moeda", 
                custom_id="moeda_emoji", 
                value=config.get("moeda_emoji", "🪙"), 
                max_length=50, 
                required=False
            ),
        ]
        super().__init__(title="Configurar Moeda", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        config = load_json("config.json")
        config["moeda_nome"] = inter.text_values["moeda_nome"]
        config["moeda_emoji"] = inter.text_values["moeda_emoji"]
        save_json(config, "config.json")
        self.parent_view.config = config
        await inter.response.edit_message(embed=self.parent_view.get_embed(), view=self.parent_view)

class UserLookupModal(disnake.ui.Modal):
    def __init__(self, view):
        self.parent_view = view
        components = [
            disnake.ui.TextInput(
                label="ID do Usuário", 
                custom_id="user_id", 
                placeholder="Cole o ID do usuário para gerenciar", 
                style=disnake.TextInputStyle.short
            )
        ]
        super().__init__(title="Buscar Usuário", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        user_id_str = inter.text_values["user_id"]
        if not user_id_str.isdigit():
            await inter.response.send_message(f"{negativo} ID inválido.", ephemeral=True)
            return
        user = inter.guild.get_member(int(user_id_str))
        if not user:
            await inter.response.send_message(f"{negativo} Usuário não encontrado neste servidor.", ephemeral=True)
            return
        self.parent_view.target_user = user
        self.parent_view.rebuild_components()
        await inter.response.edit_message(embed=self.parent_view.get_embed(), view=self.parent_view)

class EditUserBalanceModal(disnake.ui.Modal):
    def __init__(self, view):
        self.parent_view = view
        components = [
            disnake.ui.TextInput(
                label="Valor a Adicionar/Remover", 
                custom_id="balance_change", 
                placeholder="Use valores negativos para remover (ex: -1000)"
            )
        ]
        super().__init__(title=f"Editar Saldo - {view.target_user.display_name}", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        try:
            amount = int(inter.text_values["balance_change"])
        except ValueError:
            await inter.response.send_message(f"{negativo} Valor inválido.", ephemeral=True)
            return
        users_data = load_json(USERS_DATA_FILE)
        user_id_str = str(self.parent_view.target_user.id)
        if user_id_str not in users_data:
            users_data[user_id_str] = {"wallet": 0, "bank": 0, "cooldowns": {}}
        users_data[user_id_str]["wallet"] += amount
        save_json(users_data, USERS_DATA_FILE)
        self.parent_view.rebuild_components()
        await inter.response.edit_message(content=f"{positivo} Saldo de {self.parent_view.target_user.mention} atualizado em **{amount:,}**.", embed=self.parent_view.get_embed(), view=self.parent_view)

class EconomiaPanelView(disnake.ui.View):
    def __init__(self, author_id: int):
        super().__init__(timeout=600)
        self.author_id = author_id
        self.current_screen = "main"
        self.current_category = None
        self.target_user = None
        self.config = load_json("config.json")
        self.econ_config = load_json(ECONOMY_CONFIG_FILE, is_econ_config=True)
        self.rebuild_components()

    async def interaction_check(self, inter: disnake.MessageInteraction) -> bool:
        if inter.author.id != self.author_id:
            await inter.response.send_message(f"{negativo} Você não pode interagir com este painel.", ephemeral=True)
            return False
        return True

    def get_embed(self):
        if self.current_screen == "main":
            embed = disnake.Embed(
                title="Painel de Economia",
                description="**Central de Gerenciamento Administrativo**",
                color=0x2F3136
            )
            
            moeda_nome = self.config.get("moeda_nome", "N/A")
            moeda_emoji = self.config.get("moeda_emoji", "")
            embed.add_field(
                name="**Configuração Atual**", 
                value=f"┌ **Moeda:** {moeda_emoji} `{moeda_nome}`\n└ **Sistema:** `Ativo`",
                inline=False
            )
            
            status_text = ""
            for cat, cmds in COMMANDS_BY_CATEGORY.items():
                cat_lower = cat.lower()
                cat_config = self.econ_config.get("categorias", {}).get(cat_lower, {})
                enabled_count = sum(1 for cmd in cmds if cat_config.get(cmd, True))
                
                # Emojis por categoria
                category_emojis = {
                    "Economia": "💰",
                    "Roleplay": "🎭", 
                    "Diversão": "🎮",
                    "Nsfw": "🔞"
                }
                
                status_text += f"{category_emojis.get(cat, '🔒')} **{cat}** `{enabled_count}/{len(cmds)}` ativos\n"
            
            embed.add_field(
                name="**Status dos Comandos**", 
                value=status_text,
                inline=False
            )
            
            embed.set_footer(text="Selecione uma opção abaixo para gerenciar o sistema")
            return embed
            
        elif self.current_screen == "manage_commands":
            if self.current_category is None:
                embed = disnake.Embed(
                    title="Gerenciar Comandos",
                    description="**Selecione uma categoria para configurar**",
                    color=0x5865F2
                )
                embed.set_footer(text="Use o menu dropdown para selecionar uma categoria")
                return embed
            else:
                embed = disnake.Embed(
                    title=f"{self.current_category.capitalize()}",
                    description=f"**Configurando comandos da categoria**",
                    color=0x57F287
                )
                
                category_config = self.econ_config.get("categorias", {}).get(self.current_category, {})
                commands = COMMANDS_BY_CATEGORY[self.current_category.capitalize()]
                
                enabled = [cmd for cmd in commands if category_config.get(cmd, True)]
                disabled = [cmd for cmd in commands if not category_config.get(cmd, True)]
                
                if enabled:
                    embed.add_field(
                        name=f"{positivo} **Comandos Ativos**",
                        value=f"```{', '.join(enabled)}```",
                        inline=False
                    )
                
                if disabled:
                    embed.add_field(
                        name=f"{negativo} **Comandos Desativados**",
                        value=f"```{', '.join(disabled)}```",
                        inline=False
                    )
                
                embed.set_footer(text="Use o menu abaixo para ativar/desativar comandos")
                return embed
                
        elif self.current_screen == "manage_user":
            if self.target_user is None:
                embed = disnake.Embed(
                    title="Gerenciar Usuário",
                    description="**Sistema de Gerenciamento de Usuários**",
                    color=0xEB459E
                )
                embed.add_field(
                    name="**Instruções**",
                    value="• Clique em **Buscar Usuário** para começar\n• Digite o ID do usuário no modal\n• Gerencie saldo e dados do usuário",
                    inline=False
                )
                embed.set_footer(text="Clique no botão abaixo para buscar um usuário")
                return embed
            else:
                users_data = load_json(USERS_DATA_FILE)
                user_data = users_data.get(str(self.target_user.id), {"wallet": 0, "bank": 0})
                
                embed = disnake.Embed(
                    title=f"{self.target_user.display_name}",
                    description=f"**ID:** `{self.target_user.id}`",
                    color=0xEB459E
                )
                
                embed.set_thumbnail(url=self.target_user.display_avatar.url)
                
                wallet = user_data.get('wallet', 0)
                bank = user_data.get('bank', 0)
                total = wallet + bank
                
                embed.add_field(
                    name="**Saldo Atual**",
                    value=f"┌ **Carteira:** `{wallet:,}`\n├ **Banco:** `{bank:,}`\n└ **Total:** `{total:,}`",
                    inline=True
                )
                
                embed.add_field(
                    name="**Ações Disponíveis**",
                    value="• Adicionar/Remover saldo\n• Reset completo dos dados\n• Visualizar informações",
                    inline=True
                )
                
                embed.set_footer(text="Use os botões abaixo para gerenciar este usuário")
                return embed
                
        elif self.current_screen == "reset_economy":
            embed = disnake.Embed(
                title="Reset da Economia",
                description="**ZONA DE PERIGO**",
                color=0xED4245
            )
            
            embed.add_field(
                name="**ATENÇÃO CRÍTICA**",
                value="Esta ação irá **APAGAR PERMANENTEMENTE**:\n\n• Todos os saldos dos usuários\n• Todos os dados de pets\n• Todas as mineradoras\n• Todas as configurações\n\n**NÃO HÁ COMO DESFAZER!**",
                inline=False
            )
            
            embed.add_field(
                name="**Checklist de Segurança**",
                value="▢ Fiz backup dos dados importantes\n▢ Avisei todos os usuários\n▢ Tenho certeza absoluta da decisão\n▢ Li todos os avisos acima",
                inline=False
            )
            
            embed.set_footer(text="⚠️ Só clique em confirmar se tiver 100% de certeza!")
            return embed

    def rebuild_components(self):
        self.clear_items()
        
        if self.current_screen == "main":
            # Botões principais com estética clean
            self.add_item(disnake.ui.Button(
                label="Configurar Moeda", 
                style=disnake.ButtonStyle.secondary, 
                custom_id="config_moeda_button", 
                emoji=dollar
            ))
            
            self.add_item(disnake.ui.Button(
                label="Gerenciar Comandos", 
                style=disnake.ButtonStyle.primary, 
                custom_id="go_to_manage_commands", 
                emoji=tools
            ))
            
            self.add_item(disnake.ui.Button(
                label="Gerenciar Usuários", 
                style=disnake.ButtonStyle.primary, 
                custom_id="go_to_manage_user", 
                emoji=user
            ))
            
            self.add_item(disnake.ui.Button(
                label="Reset Sistema", 
                style=disnake.ButtonStyle.danger, 
                custom_id="go_to_reset_economy", 
                emoji=apagar
            ))
            
            # REMOVIDO: Botão "Voltar" que causava conflito
            # Adicionado novo botão específico para voltar ao painel inicial
            self.add_item(disnake.ui.Button(
                label="Painel Inicial", 
                emoji=voltar, 
                custom_id="voltar_painel_inicial_economia",
                style=disnake.ButtonStyle.secondary
            ))
            
        else:
            # Botão de voltar (sempre presente exceto na tela principal)
            self.add_item(disnake.ui.Button(
                label="Voltar ao Painel", 
                style=disnake.ButtonStyle.grey, 
                custom_id="back_to_main_panel", 
                emoji=voltar
            ))

            if self.current_screen == "manage_commands":
                if self.current_category is None:
                    # Menu de categorias com emojis
                    category_options = [
                        disnake.SelectOption(label="Economia", value="economia", description="Comandos de sistema econômico"),
                        disnake.SelectOption(label="Roleplay", value="roleplay", description="Comandos de interpretação"),
                        disnake.SelectOption(label="Diversão", value="diversão", description="Comandos de entretenimento"),
                        disnake.SelectOption(label="NSFW", value="nsfw", description="Conteúdo adulto")
                    ]
                    
                    self.add_item(disnake.ui.Select(
                        custom_id="category_select",
                        placeholder="Selecione uma categoria...",
                        options=category_options
                    ))
                else:
                    # Menu de comandos da categoria
                    category_config = self.econ_config.get("categorias", {}).get(self.current_category, {})
                    commands = COMMANDS_BY_CATEGORY[self.current_category.capitalize()]
                    
                    options = []
                    for cmd in commands:
                        is_enabled = category_config.get(cmd, True)
                        options.append(disnake.SelectOption(
                            label=f"{cmd.capitalize()}",
                            value=cmd,
                            emoji=ligado if is_enabled else desligado,
                            description=f"{'Ativo' if is_enabled else 'Desativado'}"
                        ))
                    
                    self.add_item(disnake.ui.Select(
                        custom_id="command_toggle_select",
                        placeholder="Ativar/Desativar comandos...",
                        options=options,
                        min_values=1,
                        max_values=len(options)
                    ))
                    
            elif self.current_screen == "manage_user":
                self.add_item(disnake.ui.Button(
                    label="Buscar Usuário", 
                    style=disnake.ButtonStyle.green, 
                    custom_id="lookup_user_button",
                    emoji=lupa
                ))
                
                if self.target_user:
                    self.add_item(disnake.ui.Button(
                        label="Editar Saldo", 
                        style=disnake.ButtonStyle.secondary, 
                        custom_id="edit_user_balance_button",
                        emoji=editar
                    ))
                    
                    self.add_item(disnake.ui.Button(
                        label="Reset Usuário", 
                        style=disnake.ButtonStyle.danger, 
                        custom_id="reset_user_data_button",
                        emoji=apagar
                    ))
                    
            elif self.current_screen == "reset_economy":
                self.add_item(disnake.ui.Button(
                    label="CONFIRMAR RESET TOTAL",
                    style=disnake.ButtonStyle.danger,
                    custom_id="confirm_total_reset_button",
                    emoji=apagar
                ))

    async def handle_interaction(self, inter: disnake.MessageInteraction):
        # Verificar se a interação já foi respondida
        if inter.response.is_done():
            return
            
        custom_id = inter.component.custom_id
        
        screen_map = {
            "back_to_main_panel": "main",
            "go_to_manage_commands": "manage_commands",
            "go_to_manage_user": "manage_user",
            "go_to_reset_economy": "reset_economy"
        }

        if custom_id in screen_map:
            self.current_screen = screen_map[custom_id]
            self.current_category = None
            self.target_user = None
            self.rebuild_components()
            await inter.response.edit_message(embed=self.get_embed(), view=self)
            
        elif custom_id == "config_moeda_button":
            await inter.response.send_modal(MoedaModal(self))
            return
            
        elif custom_id == "lookup_user_button":
            await inter.response.send_modal(UserLookupModal(self))
            return
            
        elif custom_id == "edit_user_balance_button":
            await inter.response.send_modal(EditUserBalanceModal(self))
            return
            
        elif custom_id == "reset_user_data_button":
            for file_path in [USERS_DATA_FILE, PETS_DATA_FILE, MINER_DATA_FILE]:
                data = load_json(file_path)
                if str(self.target_user.id) in data:
                    del data[str(self.target_user.id)]
                    save_json(data, file_path)
            await inter.response.send_message(f"{positivo} Dados de **{self.target_user.display_name}** resetados com sucesso.", ephemeral=True)
            self.target_user = None
            self.rebuild_components()
            # Usar followup se a response já foi usada
            await inter.edit_original_message(embed=self.get_embed(), view=self)
            
        elif custom_id == "confirm_total_reset_button":
            for file_path in [USERS_DATA_FILE, PETS_DATA_FILE, MINER_DATA_FILE]:
                if os.path.exists(file_path):
                    os.remove(file_path)
            self.econ_config = get_default_config()
            save_json(self.econ_config, ECONOMY_CONFIG_FILE)
            
            # Embed de confirmação estilizado
            success_embed = disnake.Embed(
                title="💀 Reset Completo Executado",
                description="**O sistema foi completamente resetado**",
                color=0xED4245
            )
            success_embed.add_field(
                name=f"{positivo} **Ações Executadas**",
                value="• Todos os saldos foram zerados\n• Dados de pets removidos\n• Mineradoras resetadas\n• Configurações restauradas",
                inline=False
            )
            success_embed.set_footer(text="O sistema está pronto para ser usado novamente")
            
            await inter.response.edit_message(content=None, embed=success_embed, view=None)
            return
            
        elif custom_id == "category_select":
            self.current_category = inter.values[0]
            self.rebuild_components()
            await inter.response.edit_message(embed=self.get_embed(), view=self)
            
        elif custom_id == "command_toggle_select":
            if "categorias" not in self.econ_config:
                self.econ_config["categorias"] = {}
            if self.current_category not in self.econ_config["categorias"]:
                self.econ_config["categorias"][self.current_category] = {}
            
            for command_name in inter.values:
                current_status = self.econ_config["categorias"][self.current_category].get(command_name, True)
                self.econ_config["categorias"][self.current_category][command_name] = not current_status
            save_json(self.econ_config, ECONOMY_CONFIG_FILE)
            self.rebuild_components()
            await inter.response.edit_message(embed=self.get_embed(), view=self)

class EconomiaCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_views = {}

    @commands.Cog.listener("on_button_click")
    async def on_panel_button(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        # Abrir painel de economia
        if custom_id == "GerenciarPainelEconomia":
            # Limpar view anterior se existir
            if inter.message.id in self.active_views:
                old_view = self.active_views[inter.message.id]
                old_view.stop()
                
            view = EconomiaPanelView(author_id=inter.author.id)
            self.active_views[inter.message.id] = view
            await inter.response.edit_message(embed=view.get_embed(), view=view, content=None, attachments=[])
            
        # Voltar ao painel inicial (específico da economia)
        elif custom_id == "voltar_painel_inicial_economia":
            # Limpar a view atual
            if inter.message.id in self.active_views:
                view = self.active_views[inter.message.id]
                view.stop()
                del self.active_views[inter.message.id]
            
            # Importar e chamar a função do painel principal
            try:
                # Importar as funções do painel principal
                import sys
                import importlib
                
                # Assumindo que as funções estão no arquivo Painel.py
                painel_module = importlib.import_module('Commands.Admin.Painel')
                components = painel_module.ObterPainelInicialBotoes()
                
                await inter.response.edit_message(content="", components=components, embed=None, attachments=[])
            except Exception as e:
                print(f"Erro ao voltar ao painel inicial: {e}")
                await inter.response.send_message(f"{negativo} Erro ao voltar ao painel inicial.", ephemeral=True)
            
        # Gerenciar interações das views ativas
        elif inter.message.id in self.active_views:
            view = self.active_views[inter.message.id]
            if not view.is_finished():
                await view.handle_interaction(inter)

    @commands.Cog.listener("on_dropdown")
    async def on_panel_select(self, inter: disnake.MessageInteraction):
        if inter.message.id in self.active_views:
            view = self.active_views[inter.message.id]
            if not view.is_finished():
                await view.handle_interaction(inter)

def setup(bot):
    bot.add_cog(EconomiaCog(bot))