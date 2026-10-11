import disnake
import requests
from Functions.CarregarEmojis import *
from datetime import datetime
import asyncio
import json
from disnake.ui import ActionRow, Button, Container, TextDisplay, Separator # Explicitly import Button, Container, TextDisplay, Separator

banner = r"""
     _     __  
    ( \   /  \  developed by guilherme
     ) )_(_/\_) https://mdsmax.dev
    (_/(_)     
"""

def obter_status(status_index):
    with open("config.json") as file:
        config = json.load(file)
        
    status_section = config.get("status") # Get the 'status' section safely

    name = None # Initialize name to None
    config_type = "online" # Default presence

    if isinstance(status_section, dict): # Check if 'status' section is a dict
        name_key = f"name{status_index}"
        name = status_section.get(name_key) # Get name, will be None if not found
        config_type = status_section.get("type", "online")

    # If name is None or an empty string, it's not configured
    if not name or not name.strip():
        return None, None # Indicate that this status should be skipped

    # Determine disnake.Status based on config_type and create appropriate activity
    status_presence = disnake.Status.online # Default
    activity_obj = None

    if config_type == "online": 
        status_presence = disnake.Status.online
        activity_obj = disnake.CustomActivity(name=name) 
    elif config_type == "idle": 
        status_presence = disnake.Status.idle
        activity_obj = disnake.CustomActivity(name=name) 
    elif config_type == "dnd": 
        status_presence = disnake.Status.dnd
        activity_obj = disnake.CustomActivity(name=name) 
    elif config_type == "streaming": 
        status_presence = disnake.Status.streaming
        # Use a default Twitch URL as requested by the user not to put it in config.json
        streaming_url = "https://www.twitch.tv/neverapplications" 
        activity_obj = disnake.Activity(name=name, type=disnake.ActivityType.streaming, url=streaming_url)
    
    return status_presence, activity_obj

def alterar_descricao_bot(bot):
    with open("config.json") as file:
        config = json.load(file)
        token = config['token']

    # Load emojis from Database/emojis.json
    try:
        with open("Database/emojis.json") as emoji_file:
            emojis_data = json.load(emoji_file)
    except (FileNotFoundError, json.JSONDecodeError):
        emojis_data = {} # Handle case where file might not exist or is invalid

    # Hardcoded template as per user's request
    template = "{n1}{n2}{n3}{n4}{n5}{n6}{n7}\nhttps://neverapplications.com.br"
    
    # Populate template with emoji strings
    formatted_description = template
    for i in range(1, 8): # Check for n1 to n7
        emoji_key = f"n{i}"
        # Get the emoji string from emojis_data, default to empty string if not found
        emoji_string = emojis_data.get(emoji_key, "") 
        formatted_description = formatted_description.replace(f"{{{emoji_key}}}", emoji_string)
    
    descricao = formatted_description.strip() # Remove any extra whitespace

    url = f"https://discord.com/api/v9/applications/{bot.user.id}"
    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "description": descricao
    }
    response = requests.patch(url, headers=headers, json=payload)
    return response.status_code, response.text

async def startBotlogs(bot):
    try:
        with open("Database/Server/canais.json") as server_file:
            server_db = json.load(server_file)
            logs = server_db["sistema"]
        
        with open("config.json") as file:
            config = json.load(file)
            versao = config['versao']
            owner = config['owner']
            prefix = config.get('prefix', '!') # Get prefix from config

        # Load emojis from Database/emojis.json
        try:
            with open("Database/emojis.json") as emoji_file:
                emojis_data = json.load(emoji_file)
        except (FileNotFoundError, json.JSONDecodeError):
            emojis_data = {} # Handle case where file might not exist or is invalid

        if not logs:
            await startBotlogs_simple(bot)
            return

        canal = bot.get_channel(int(logs))
        if not canal:
            await startBotlogs_simple(bot)
            return

        # Prepare dynamic replacements
        replacements = {
            "{Never}": emojis_data.get("Never", "Never"), # Assuming 'Never' emoji exists
            "{reload}": emojis_data.get("reload"),
            "{bot}": emojis_data.get("bot"),
            "{@Bot}": bot.user.mention,
            "{cargo}": emojis_data.get("cargo"),
            "{Version}": f"`{versao}`",
            "{attach}": emojis_data.get("attach"),
            "{Prefixo}": f"`{prefix}`",
            "{user}": emojis_data.get("user"),
            "{@owner}": f"<@{owner}>",
            "{calendar}": emojis_data.get("calendar"), # Added calendar emoji
            "{time}": int(datetime.now().timestamp()) # Add current timestamp
        }

        # Accent colour from Configuracoes.json (if exists)
        accent_color = disnake.Colour(16777215) # Default to white
        try:
            with open("Database/Configuracoes.json", "r") as f_config_db:
                config_db = json.load(f_config_db)
                primary_color_str = config_db.get("Cores", {}).get("Color_Primary")
                if primary_color_str:
                    accent_color = disnake.Colour(int(primary_color_str, 16) if primary_color_str.startswith("0x") else int(primary_color_str))
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            pass # Use default accent_color

        # --- Reconstruct components using disnake.ui.Container, TextDisplay, Separator, ActionRow ---
        initial_message_components = []
        
        # Text for the first Container
        container1_text = (
            f"# {replacements['{Never}']}\n"
            f"-# Informações do Sistema > **Reinicialização**"
        )
        initial_message_components.append(Container(TextDisplay(container1_text), accent_colour=accent_color))

        # Text for the second Container
        container2_text = (
            f"{replacements['{reload}']} O **Never Pro** foi reiniciado @everyone\n"
            f"{replacements['{cargo}']} **Menção:** {replacements['{@Bot}']}\n"
            f"{replacements['{bot}']} **Versão:** {replacements['{Version}']}\n"
            f"{replacements['{attach}']} **Prefixo:** {replacements['{Prefixo}']}\n"
            f"{replacements['{user}']}**Dono:** {replacements['{@owner}']}\n"
            f"{replacements['{calendar}']}**data** <t:{replacements['{time}']}:R>"
        )
        initial_message_components.append(Container(TextDisplay(container2_text), accent_colour=accent_color))

        # Text and buttons for the third Container
        container3_elements = [
            TextDisplay("-# Se precisar de suporte clique no botão abaixo."),
            ActionRow(
                Button(label="Acesse a Dashboard", url="https://neverapplications.com.br/Dashboard", style=disnake.ButtonStyle.link),
                Button(label="Suporte ", url=config.get("site", "https://discord.gg/neverapplications"), style=disnake.ButtonStyle.link) 
            )
        ]
        initial_message_components.append(Container(*container3_elements, accent_colour=accent_color))

        # Envia a primeira mensagem com componentes
        await canal.send(components=initial_message_components)
        
        # Aguarda o bot ficar completamente pronto com timeout mais longo
        ready_status = await wait_for_bot_ready(bot, timeout=600)  # Aumentado para 10 minutos
        
        if not ready_status:
            # Build components for error message (simpler error display)
            error_message_components = [
                Container(
                    TextDisplay(f"⚠️ — **Erro na inicialização**\n❌ Timeout: O bot não ficou pronto no tempo esperado."),
                    ActionRow(Button(label="Relatar Erro", style=disnake.ButtonStyle.red)),
                    accent_colour=disnake.Colour.red() # Red accent for error
                )
            ]
            await canal.send(components=error_message_components)

    except Exception as e:
        print(f"Erro ao executar startBotlogs: {e}") # Print error to console for debugging

async def startBotlogs_simple(bot):
    """Versão simplificada para quando não há canal de logs configurado"""
    try:
        # Aguarda o bot ficar completamente pronto
        ready_status = await wait_for_bot_ready(bot, timeout=600)  # Aumentado para 10 minutos
        
        if ready_status:
            print("    ✅ Bot totalmente inicializado e pronto para uso!")
        else:
            print("    ❌ TIMEOUT: Bot não ficou pronto no tempo esperado.")
        
    except Exception as e:
        print(f"Erro ao executar startBotlogs_simple: {e}") # Print error to console for debugging

# Função helper para verificar se o bot está pronto
async def wait_for_bot_ready(bot, timeout=600):  # Aumentado para 10 minutos
    """Aguarda o bot ficar pronto ou timeout"""
    start_time = asyncio.get_event_loop().time()
    
    while not bot.is_ready():  # Mudança: usando is_ready() ao invés de fully_ready
        if asyncio.get_event_loop().time() - start_time > timeout:
            return False
        await asyncio.sleep(1)
    
    # Aguarda um pouco mais para garantir que todos os componentes estejam carregados
    await asyncio.sleep(5)
    return True

async def mandarLogsServer(inter: disnake.MessageInteraction, embed):
    # Verifica se o bot está pronto antes de enviar logs
    if not inter.bot.is_ready():  # Mudança: usando is_ready() ao invés de fully_ready
        print("    ⚠️  Tentativa de enviar log antes do bot estar pronto")
        return
    
    try:
        with open("Database/Server/canais.json") as server_file:
            server_db = json.load(server_file)
            logs = server_db["logs"]

        if not logs:
            return

        canal = inter.guild.get_channel(int(logs))
        if not canal: 
            return

        await canal.send(embed=embed)
    except Exception as e:
        print(f"Erro ao enviar log para servidor: {e}")

_current_status_index = 1 # Initialize outside to maintain state across calls

async def rotacionar_status(bot):
    global _current_status_index # Declare global to modify the outer variable
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            status_presence, activity_obj = obter_status(_current_status_index)
            
            # If obter_status returned None, it means this nameX was not configured, so skip
            if activity_obj is None:
                # Increment index and immediately go to next iteration to find a configured status
                _current_status_index += 1
                if _current_status_index > 5: # Assuming name1 to name5
                    _current_status_index = 1
                await asyncio.sleep(1) # Small delay to prevent tight loop if all are unconfigured
                continue 

            await bot.change_presence(status=status_presence, activity=activity_obj)
            
            _current_status_index += 1
            if _current_status_index > 5: # Assuming name1 to name5
                _current_status_index = 1
            
            await asyncio.sleep(5) # Atualiza a cada 5 segundos
        except Exception as e:
            print(f"Erro ao rotacionar status: {e}")
            await asyncio.sleep(60) # Espera um pouco antes de tentar novamente

# Função adicional para verificar se todos os emojis estão carregados
def verificar_emojis():
    """Verifica se todos os emojis necessários estão definidos"""
    emojis_necessarios = ['lupa', 'config3', 'clock', 'user', 'reload', 'positivo']
    emojis_faltando = []
    
    # This function expects emojis to be loaded into global scope, which is not how the provided `emojis_data` works.
    # It should rather check the `emojis_data` dictionary. For now, commenting out its usage.
    # for emoji in emojis_necessarios:
    #     try:
    #         # This check would be against `emojis_data` not globals()
    #         # if emoji not in emojis_data:
    #         #     emojis_faltando.append(emoji)
    #         pass # Placeholder, correct logic needed if this function is actually used
    #     except KeyError:
    #         emojis_faltando.append(emoji)
    
    # if emojis_faltando:
    #     print(f"    ⚠️  Emojis não carregados: {', '.join(emojis_faltando)}")
    #     return False
    return True
