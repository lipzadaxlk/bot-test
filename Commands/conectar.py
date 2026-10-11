import disnake
from disnake.ext import commands
from disnake.ui import Container, TextDisplay, Separator, ActionRow
import json

from Functions.CarregarEmojis import (
    carregarAnimado,
    voice,
    voltar,
    editar,
    cancelar, # Assuming 'cancelar' is for permission errors
)
# Placeholder for permission checking function
# In a real scenario, you'd likely import this from Functions.VerificarPerms
def verificar_permissao(user_id):
    # For now, let's just allow everyone for testing
    return True

# --- Voice Configuration Management ---
VOICE_CONFIG_PATH = "Database/Server/Voice.json"

def load_voice_config():
    try:
        with open(VOICE_CONFIG_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Return default structure if file not found or invalid
        return {
            "Voice_channel": None,
            "connected": False,
            "nomes": {
                "Nome1": "", "Nome2": "", "Nome3": "", "Nome4": "", "Nome5": ""
            }
        }

def save_voice_config(config):
    with open(VOICE_CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)
# --- End Voice Configuration Management ---

class ConnectCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def get_connect_panel(self): # Make it async
        config = load_voice_config()
        connected_channel_id = config["Voice_channel"]
        is_connected = config["connected"]

        channel_status_text = "Nenhum canal configurado."
        if connected_channel_id:
            voice_channel = self.bot.get_channel(connected_channel_id)
            if voice_channel and isinstance(voice_channel, disnake.VoiceChannel):
                channel_status_text = f"{voice_channel.mention}" # Display only mention
            else:
                channel_status_text = f"Canal inválido/inexistente (`{connected_channel_id}`)."

        connect_button_style = disnake.ButtonStyle.red if is_connected else disnake.ButtonStyle.green
        connect_button_label = "Desconectar" if is_connected else "Conectar"

        container_elements = [
            TextDisplay("Conecte seu Bot a um canal de Voz do seu servidor utilizando os botões abaixo."),
            Separator(),
            TextDisplay(f"{voice} **Canal Atual:** {channel_status_text}"), # Removed backticks from here
            Separator(),
            ActionRow(
                disnake.ui.Button(
                    label=connect_button_label,
                    custom_id="connect_toggle",
                    style=connect_button_style,
                    emoji=voice # Changed emoji to 'voice' as requested
                ),
                disnake.ui.Button(
                    label="Editar canal",
                    custom_id="edit_channel",
                    style=disnake.ButtonStyle.secondary,
                    emoji=editar
                )
            )
        ]
        return Container(*container_elements, accent_colour=disnake.Colour.blurple())

    def get_edit_channel_panel(self):
        container_elements = [
            TextDisplay("Selecione o canal de Voz desejado para a conexão do bot."),
            Separator(),
            ActionRow(
                disnake.ui.ChannelSelect(
                    custom_id="channel_select_menu",
                    placeholder="Selecione um canal abaixo",
                    channel_types=[disnake.ChannelType.voice], # Only show voice channels
                    min_values=1,
                    max_values=1
                )
            ),
            ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    custom_id="back_to_connect",
                    style=disnake.ButtonStyle.secondary,
                    emoji=voltar
                )
            )
        ]
        return Container(*container_elements, accent_colour=disnake.Colour.blurple())

    @commands.slash_command(description="Gerencia a conexão do bot a um canal de voz.")
    async def conectar(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer(ephemeral=True)

        if not verificar_permissao(inter.user.id):
            error_container = Container(TextDisplay(f"{cancelar} Você não tem permissão."))
            return await inter.followup.send(components=[error_container], ephemeral=True)
        
        panel = await self.get_connect_panel()
        await inter.followup.send(content="", components=[panel], ephemeral=True)

    @commands.Cog.listener("on_button_click")
    async def connect_button_listener(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "connect_toggle":
            await inter.response.defer(ephemeral=True)
            
            config = load_voice_config()
            config["connected"] = not config["connected"]
            save_voice_config(config)

            is_connected = config["connected"]
            connected_channel_id = config["Voice_channel"]

            feedback_message = None # Initialize feedback_message at the start

            if is_connected: # Attempting to connect
                if connected_channel_id:
                    try:
                        voice_channel = self.bot.get_channel(connected_channel_id)
                        if voice_channel and isinstance(voice_channel, disnake.VoiceChannel):
                            # Cannot connect without PyNaCl, so provide feedback
                            config["connected"] = False # Revert state
                            save_voice_config(config)
                            feedback_message = "Não foi possível conectar ao canal de voz. A funcionalidade de voz requer a biblioteca `PyNaCl`. Por favor, instale-a para usar este recurso."
                        else:
                            config["connected"] = False # Revert state
                            save_voice_config(config)
                            feedback_message = "Erro: Canal de voz não encontrado ou inválido para conexão."
                    except Exception as e:
                        config["connected"] = False # Revert state
                        save_voice_config(config)
                        feedback_message = f"Não foi possível conectar ao canal de voz devido a um erro. A funcionalidade de voz requer a biblioteca `PyNaCl`. Detalhes: {e}"
                else:
                    config["connected"] = False # Revert state
                    save_voice_config(config)
                    feedback_message = "Nenhum canal de voz selecionado. Use 'Editar canal' para selecionar um."
            else: # Attempting to disconnect
                if inter.guild.voice_client:
                    await inter.guild.voice_client.disconnect()
                    feedback_message = "O bot foi desconectado do canal de voz. Lembre-se que a funcionalidade de voz é limitada sem a biblioteca `PyNaCl`."
                else:
                    feedback_message = "O bot não estava conectado a um canal de voz. Lembre-se que a funcionalidade de voz é limitada sem a biblioteca `PyNaCl`."
                config["connected"] = False # Ensure state is updated after "disconnection"
                save_voice_config(config) # Save here, as state is fully determined for disconnection

            # Send feedback message if any
            if feedback_message:
                await inter.followup.send(feedback_message, ephemeral=True)
            
            updated_panel = await self.get_connect_panel()
            await inter.edit_original_message(components=[updated_panel])

        elif inter.component.custom_id == "edit_channel":
            await inter.response.defer(ephemeral=True)
            
            # Show loading message with a simple Container
            loading_container = Container(TextDisplay(f"{carregarAnimado} Carregando Informações..."))
            await inter.edit_original_message(components=[loading_container])
            
            # Now send the panel after the loading message
            edit_panel = self.get_edit_channel_panel()
            await inter.edit_original_message(components=[edit_panel], content="") # Clear content to show only components

        elif inter.component.custom_id == "back_to_connect":
            await inter.response.defer(ephemeral=True)
            
            initial_panel = await self.get_connect_panel()
            await inter.edit_original_message(components=[initial_panel])

    @commands.Cog.listener("on_dropdown")
    async def channel_select_listener(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "channel_select_menu":
            await inter.response.defer(ephemeral=True)
            
            selected_channel_id = int(inter.values[0])
            
            config = load_voice_config()
            config["Voice_channel"] = selected_channel_id
            save_voice_config(config)
            
            # If bot was connected and a new channel is selected, inform about PyNaCl
            if config["connected"]:
                if inter.guild.voice_client:
                    await inter.guild.voice_client.disconnect() # Still disconnect if it was connected
                
                # Cannot connect to the newly selected voice channel without PyNaCl
                voice_channel = self.bot.get_channel(selected_channel_id)
                if voice_channel and isinstance(voice_channel, disnake.VoiceChannel):
                    await inter.followup.send("Não foi possível conectar ao novo canal de voz. A funcionalidade de voz requer a biblioteca `PyNaCl`. Por favor, instale-a para usar este recurso.", ephemeral=True)
                else:
                    await inter.followup.send("Erro: O novo canal selecionado não é um canal de voz válido, e a conexão de voz requer `PyNaCl`.", ephemeral=True)
                
                # Since connection failed, ensure 'connected' state is False
                config["connected"] = False
                save_voice_config(config)

            
            updated_panel = await self.get_connect_panel()
            await inter.edit_original_message(components=[updated_panel])


def setup(bot):
    bot.add_cog(ConnectCommand(bot))