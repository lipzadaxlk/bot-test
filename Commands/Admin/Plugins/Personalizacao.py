import disnake
import disnake
from disnake.ext import commands
from datetime import *
import json # Added this import
import requests
import base64

from Functions.CarregarEmojis import *
# from Functions.VerificarPerms import * <- Removido, usando self.bot.verificar_permissao
from Events.OnBotStart import *
from Functions.CarregarEmojis import *

def obterPainel(inter):
    # Load primary color
    try:
        with open("Database/Configuracoes.json", "r") as f_config_db:
            config_db = json.load(f_config_db)
            primary_color_str = config_db.get("Cores", {}).get("Color_Primary", "16777215")
            primary_color = disnake.Colour(int(primary_color_str))
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        primary_color = disnake.Colour(16777215) # Fallback to white

    # Load Never emoji
    try:
        with open("Database/emojis.json", "r") as f_emojis_db:
            emojis_db = json.load(f_emojis_db)
            never_emoji = emojis_db.get("Never", "") # Default to empty string if not found
    except (FileNotFoundError, json.JSONDecodeError):
        never_emoji = "" # Fallback to empty string if file not found or invalid


    main_container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {never_emoji}\n-# Painel > **Customização**"), 
        disnake.ui.Separator(),
        disnake.ui.TextDisplay("Aqui e o painel de customização do seu Bot, use as opções abaixo para personalizar cada parte do seu bot."),
        disnake.ui.Separator(),
        disnake.ui.ActionRow(
            disnake.ui.StringSelect(
                custom_id="PersonalizacaoSelect", # Semantic custom_id
                placeholder="Selecione uma opção abaixo",
                options=[
                    disnake.SelectOption(label="Configurar Status", value="configurar_status", emoji=Config),
                    disnake.SelectOption(label="Configurar Informações", value="configurar_informacoes", emoji=mensagem),
                    disnake.SelectOption(label="Modo de Exibição", value="modo_exibicao", emoji=personalizarE),
                    disnake.SelectOption(label="Configurar Cores", value="configurar_cores", emoji=wand)
                ],
                min_values=1,
                max_values=1
            )
        ),
        accent_colour=primary_color
    )

    back_button_row = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", custom_id="PainelInicial", style=disnake.ButtonStyle.secondary, emoji=voltar)
    )
    
    return [main_container, back_button_row]

def obterPainelConfigurarStatus(inter):
    # Load primary color
    try:
        with open("Database/Configuracoes.json", "r") as f_config_db:
            config_db = json.load(f_config_db)
            primary_color_str = config_db.get("Cores", {}).get("Color_Primary", "16777215")
            primary_color = disnake.Colour(int(primary_color_str))
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        primary_color = disnake.Colour(16777215) # Fallback to white

    # Load Never emoji
    try:
        with open("Database/emojis.json", "r") as f_emojis_db:
            emojis_db = json.load(f_emojis_db)
            never_emoji = emojis_db.get("Never", "") # Default to empty string if not found
    except (FileNotFoundError, json.JSONDecodeError):
        never_emoji = "" # Fallback to empty string if file not found or invalid

    # Load current status configuration
    try:
        with open("config.json", "r") as f_config:
            config = json.load(f_config)
            current_presence = config.get("status", {}).get("presence", "online")
            current_names = [config.get("status", {}).get(f"name{i}", "") for i in range(1, 6)]
    except (FileNotFoundError, json.JSONDecodeError):
        current_presence = "online"
        current_names = ["", "", "", "", ""]

    status_description = (
        f"Configure os status, presença e os nomes do seu Bot.\n"
        f"**Presença:** `{current_presence.capitalize()}`\n"
        f"**Nomes:** `{current_names[0]}` | `{current_names[1]}` | `{current_names[2]}` | `{current_names[3]}` | `{current_names[4]}`"
    )

    main_container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {never_emoji}\n-# Painel > Customização > **Configurar Status**"),
        disnake.ui.Separator(),
        disnake.ui.TextDisplay(status_description),
        disnake.ui.Separator(),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                style=disnake.ButtonStyle.secondary,
                label="Configurar nomes",
                custom_id="ConfigurarNomesStatus",
                emoji=editar
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.StringSelect(
                custom_id="SelectPresenceStatus",
                placeholder="Selecione uma opção abaixo",
                options=[
                    disnake.SelectOption(label="Online", value="online", default=(current_presence == "online"), emoji=online),
                    disnake.SelectOption(label="Não Perturbe", value="dnd", default=(current_presence == "dnd"), emoji=npertubar),
                    disnake.SelectOption(label="Ausente", value="idle", default=(current_presence == "idle"), emoji=ausente),
                    disnake.SelectOption(label="Transmitindo", value="transmitindo", default=(current_presence == "transmitindo"), emoji=transmitindo)
                ]
            )
        ),
        accent_colour=primary_color
    )

    back_button_row = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", custom_id="GerenciarPainelPersonalizar", style=disnake.ButtonStyle.secondary, emoji=voltar)
    )
    
    return [main_container, back_button_row]

def obter_token():
    with open("config.json") as config_file:
        config_db = json.load(config_file)
    return config_db["token"]

class EditarInformacoesBotModal(disnake.ui.Modal):
    def __init__(self):
        token = obter_token()
        url = "https://discord.com/api/v9/users/@me"
        headers = {"Authorization": f"Bot {token}"}
        response = requests.get(url, headers=headers)

        bot_nome = "Bot"
        if response.status_code == 200:
            bot_nome = response.json().get("username", "Bot")

        components = [
            disnake.ui.TextInput(
                label="Nome do Bot (Opcional)",
                placeholder="Digite o novo nome do bot",
                value=bot_nome,
                custom_id="nome_bot",
                style=disnake.TextInputStyle.short,
                required=False,
            ),
            disnake.ui.TextInput(
                label="URL do Avatar do Bot (Opcional)",
                placeholder="Digite a URL do novo avatar do bot",
                custom_id="avatar_bot",
                style=disnake.TextInputStyle.short,
                required=False,
            ),
            disnake.ui.TextInput(
                label="URL do Banner do Bot (Opcional)",
                placeholder="Digite a URL do novo banner do bot",
                custom_id="banner_bot",
                style=disnake.TextInputStyle.short,
                required=False,
            ),
        ]
        super().__init__(title="Editar Informações do Bot", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        nome_bot = inter.text_values.get("nome_bot")
        avatar_url = inter.text_values.get("avatar_bot")
        banner_url = inter.text_values.get("banner_bot")

        await inter.response.defer(ephemeral=True)

        token = obter_token()
        url = "https://discord.com/api/v9/users/@me"
        headers = {"Authorization": f"Bot {token}"}

        payload = {}
        if nome_bot:
            payload["username"] = nome_bot
        if avatar_url:
            avatar_data = requests.get(avatar_url).content
            payload["avatar"] = f"data:image/png;base64,{base64.b64encode(avatar_data).decode()}"
        if banner_url:
            banner_data = requests.get(banner_url).content
            payload["banner"] = f"data:image/png;base64,{base64.b64encode(banner_data).decode()}"

        response = requests.patch(url, headers=headers, json=payload)

        if response.status_code == 200:
            await inter.followup.send(f"{positivo} As alterações foram salvas com sucesso.", ephemeral=True)
        else:
            await inter.followup.send(
                f"`❌` Não foi possível atualizar as informações do bot: {response.status_code}\n{response.text}"
            )

class DefinirPrefixoModal(disnake.ui.Modal):
    def __init__(self):
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
            current_prefix = config.get("prefix", "")
        except (FileNotFoundError, json.JSONDecodeError):
            current_prefix = ""

        components = [
            disnake.ui.TextInput(
                label="Novo Prefixo do Bot",
                placeholder="Digite o novo prefixo",
                value=current_prefix,
                custom_id="novo_prefixo",
                style=disnake.TextInputStyle.short,
                required=True,
            )
        ]
        super().__init__(title="Alterar Prefixo do Bot", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        novo_prefixo = inter.text_values.get("novo_prefixo")

        try:
            with open("config.json", "r") as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            config = {}

        config["prefix"] = novo_prefixo

        with open("config.json", "w") as f:
            json.dump(config, f, indent=4)

        await inter.response.send_message(f"{positivo} O prefixo foi alterado para `{novo_prefixo}` com sucesso.", ephemeral=True)


class EditarStatusNomesModal(disnake.ui.Modal):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
        # Load modal structure from Modal.txt
        try:
            with open("Modal.txt", "r") as f:
                modal_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Fallback to default structure if Modal.txt is not found or invalid
            modal_data = {
                "title": "Configurar Nomes do Status (Fallback)",
                "components": [
                    {"label": "Nome 1 (Opcional)", "component": {"custom_id": "name1", "placeholder": "Ex: Seu Bot está online!", "style": 1}},
                    {"label": "Nome 2 (Opcional)", "component": {"custom_id": "name2", "placeholder": "Ex: Use /painel", "style": 1}},
                    {"label": "Nome 3 (Opcional)", "component": {"custom_id": "name3", "placeholder": "Ex: neverapps.com.br", "style": 1}},
                    {"label": "Nome 4 (Opcional)", "component": {"custom_id": "name4", "placeholder": "Ex: powered by never", "style": 1}},
                    {"label": "Nome 5 (Opcional)", "component": {"custom_id": "name5", "placeholder": "Ex: A sua melhor experiência!", "style": 1}},
                ]
            }
        
        modal_title = modal_data.get("title", "Configurar Nomes do Status")
        modal_raw_components = modal_data.get("components", [])

        # Load current names from config.json
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
            current_names_dict = {f"name{i}": config.get("status", {}).get(f"name{i}", "") for i in range(1, 6)}
        except (FileNotFoundError, json.JSONDecodeError):
            current_names_dict = {f"name{i}": "" for i in range(1, 6)}

        # Prepare components for disnake.ui.Modal
        disnake_components = []
        self.name_key_map = {} # To map modal's custom_id to config.json's nameX
        for i, comp_data in enumerate(modal_raw_components):
            # Assuming 'component' key holds the actual text input details
            if "component" in comp_data: 
                text_input_data = comp_data["component"]
                label = comp_data.get("label", f"Nome {i+1}")
                custom_id = text_input_data.get("custom_id", f"name_input_{i+1}")
                placeholder = text_input_data.get("placeholder", "Deixe vazio para não usar")
                style_int = text_input_data.get("style", 1)
                
                style = disnake.TextInputStyle.short if style_int == 1 else disnake.TextInputStyle.long

                # Map custom_id from Modal.txt to internal nameX keys for loading/saving
                internal_name_key = f"name{i+1}"
                self.name_key_map[custom_id] = internal_name_key

                disnake_components.append(
                    disnake.ui.TextInput(
                        label=label,
                        placeholder=placeholder,
                        custom_id=custom_id,
                        style=style,
                        required=False, 
                        value=current_names_dict.get(internal_name_key, "") 
                    )
                )
        
        super().__init__(title=modal_title, components=disnake_components)

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)

        try:
            with open("config.json", "r") as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            config = {"status": {}} 

        if "status" not in config:
            config["status"] = {}

        # Save values using the mapping
        for custom_id, internal_name_key in self.name_key_map.items():
            value = inter.text_values.get(custom_id)
            config["status"][internal_name_key] = value if value is not None else ""

        with open("config.json", "w") as f:
            json.dump(config, f, indent=4)
        
        # Refresh bot presence
        from Events.OnBotStart import obter_status
        status_type, activity = obter_status()
        await self.bot.change_presence(
            status=status_type,
            activity=activity
        )

        loading_container = disnake.ui.Container(
            disnake.ui.TextDisplay(f"{carregarAnimado} Carregando Informações...")
        )
        await inter.edit_original_message(embed=None, components=[loading_container])
        
        # Reload the status panel
        status_components = obterPainelConfigurarStatus(inter)
        await inter.edit_original_message(embed=None, components=status_components)

class Tema:
    class CorPersonalizadaModal(disnake.ui.Modal):
        def __init__(self, bot):
            self.bot = bot
            components = [
                disnake.ui.TextInput(
                    label="Cor em HEX",
                    placeholder="Ex: #FFFFFF",
                    custom_id="cor_hex",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    min_length=7,
                    max_length=7,
                )
            ]
            super().__init__(title="Definir Cor Personalizada", components=components)

        async def callback(self, inter: disnake.ModalInteraction):
            cor_hex = inter.text_values.get("cor_hex").upper()
            
            if not cor_hex.startswith("#") or len(cor_hex) != 7:
                await inter.response.send_message("`❌` Formato de cor HEX inválido. Use o formato `#RRGGBB`.", ephemeral=True)
                return

            try:
                with open("config.json", "r") as f:
                    config = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                config = {}

            config["theme"] = cor_hex

            with open("config.json", "w") as f:
                json.dump(config, f, indent=4)
            
            await atualizar_emojis_por_tema(self.bot, inter, cor_hex)


    @staticmethod
    def GerenciarTema(inter: disnake.MessageInteraction):
        cores = [
            disnake.SelectOption(label="Padrão (Blurple)", value="#5865F2"),
            disnake.SelectOption(label="Vermelho", value="#ED4245"),
            disnake.SelectOption(label="Verde", value="#57F287"),
            disnake.SelectOption(label="Amarelo", value="#FEE75C"),
            disnake.SelectOption(label="Laranja", value="#E67E22"),
            disnake.SelectOption(label="Roxo", value="#9B59B6"),
            disnake.SelectOption(label="Rosa", value="#E91E63"),
            disnake.SelectOption(label="Ciano", value="#1ABC9C"),
            disnake.SelectOption(label="Azul", value="#3498DB"),
            disnake.SelectOption(label="Verde Escuro", value="#1F8B4C"),
            disnake.SelectOption(label="Azul Escuro", value="#206694"),
            disnake.SelectOption(label="Roxo Escuro", value="#71368A"),
            disnake.SelectOption(label="Rosa Escuro", value="#AD1457"),
            disnake.SelectOption(label="Ouro", value="#C27C0E"),
            disnake.SelectOption(label="Laranja Escuro", value="#A84300"),
            disnake.SelectOption(label="Cinza Claro", value="#979C9F"),
            disnake.SelectOption(label="Cinza Escuro", value="#607D8B"),
            disnake.SelectOption(label="Azul Marinho", value="#34495E"),
            disnake.SelectOption(label="Branco", value="#FFFFFF"),
            disnake.SelectOption(label="Preto", value="#000000"),
        ]
        components = [
            disnake.ui.StringSelect(
                placeholder="Selecione uma cor para o tema",
                custom_id="EditarTemaDropdown",
                options=cores
            ),
            disnake.ui.Button(
                style=disnake.ButtonStyle.secondary,
                label="Cor Personalizada",
                custom_id="CorPersonalizada",
                emoji="🎨"
            ),
            disnake.ui.Button(
                label="Voltar",
                emoji=voltar,
                custom_id="GerenciarPainelPersonalizar"
            )
        ]
        return components
