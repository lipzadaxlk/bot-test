import json
import disnake
from disnake import *
from disnake.ext import commands
from Functions.CarregarEmojis import * # Assuming this loads positive, negativo, reload, editar, preview, voltar, carregarAnimado, mensagem, apagar, embedE, foto, clock, config3, mais2
from datetime import *
import logging # Recomendo adicionar logging para melhor depuração

logger = logging.getLogger('disnake')

################# MENSAGEM BOAS VINDAS #################
class BoasVindas():

    # --- Get panel for the single welcome message ---
    def obterPainelMensagemBoasVindas(inter: disnake.MessageInteraction):
        with open("Database/Server/boasvindas.json", "r") as f:
            db = json.load(f)
        
        # Access the single welcome message data
        message_data = db["mensagens"]["boas-vindas"]

        tempo_apagar = message_data.get("tempoApagar")
        sistema = message_data.get("enabled", False)
        channel_id = message_data.get("channel_id")

        if channel_id:
            canal = inter.guild.get_channel(int(channel_id))
            canal_text = f"{positivo} {canal.mention}" if canal else f"{negativo} ``Canal inválido``"
        else:
            canal_text = f"{negativo} ``Não configurado``"

        tempo_apagar_text = f"{positivo} ``{tempo_apagar} segundos``" if tempo_apagar else f"{negativo} ``Não configurado``"

        if sistema:
            sistema_text = f"{positivo} ``Ativado``"
            button_toggle = {
                "Label": "Desabilitar",
                "Emoji": reload,
                "Style": disnake.ButtonStyle.red,
            }
        else:
            sistema_text = f"{negativo} ``Desativado``"
            button_toggle = {
                "Label": "Habilitar",
                "Emoji": reload,
                "Style": disnake.ButtonStyle.green,
            }

        embed = disnake.Embed(
            title=f"Sistema de Boas-Vindas",
            description=(
                "Aqui você pode configurar sua mensagem de Boas-Vindas.\n"
                "Ela será acionada sempre que um membro entrar no servidor.\n"
                "Configure o canal de boas vindas nas configurações."
            ),
            timestamp=datetime.now(),
            color=disnake.Color(0x00FFFF)
        )
        embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon)

        embed.add_field(name="Canal Configurado", value=canal_text, inline=True)
        embed.add_field(name="Tempo para Apagar Mensagem", value=tempo_apagar_text, inline=True)
        embed.add_field(name="Status do Sistema", value=sistema_text, inline=True)

        components = [
            disnake.ui.ActionRow( # Row 1: Toggle, Edit Message, Preview
                disnake.ui.Button(label=button_toggle["Label"], emoji=button_toggle["Emoji"], style=button_toggle["Style"], custom_id="ToggleMensagemBoasVindas"),
                disnake.ui.Button(
                    style=disnake.ButtonStyle.blurple,
                    label="Editar Mensagem",
                    custom_id="EditarConfigMensagemBoasVindas", # No message_id needed
                    emoji=editar
                ),
                disnake.ui.Button(
                    style=disnake.ButtonStyle.blurple,
                    label="Pre-visualização",
                    custom_id="PreviewMensagemBoasVindas",
                    emoji=preview
                ),
            ),
            disnake.ui.ActionRow( # Row 2: Back
                disnake.ui.Button(label="Voltar", emoji=voltar, style=disnake.ButtonStyle.grey, custom_id="GerenciarPainelBoasVindas_Voltar"), # Go back to the intermediate panel
            )
        ]
        return embed, components

    # --- Main message configuration editor ---
    def obterPainelEditarMensagemBoasVindas(inter: disnake.MessageInteraction):
        embed = disnake.Embed(
            title=f"Editor de Mensagem de Boas-Vindas",
            description="Selecione o que você deseja configurar na mensagem de boas-vindas.",
            timestamp=datetime.now(),
            color=disnake.Color(0x00FFFF)
        )
        embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon)

        components = [
            disnake.ui.ActionRow( # Row 1
                disnake.ui.Button(label="Definir Content",emoji=mensagem, style=disnake.ButtonStyle.blurple, custom_id="ConfigContent"),
                disnake.ui.Button(emoji=apagar, style=disnake.ButtonStyle.red, custom_id="ClearContent"),
            ),
            disnake.ui.ActionRow( # Row 2
                disnake.ui.Button(label="Definir Embed",emoji=embedE, style=disnake.ButtonStyle.blurple, custom_id="ConfigEmbed"),
                disnake.ui.Button(emoji=apagar, style=disnake.ButtonStyle.red, custom_id="ClearEmbed"),
            ),
            disnake.ui.ActionRow( # Row 3
                disnake.ui.Button(label="Definir Imagem",emoji=foto, style=disnake.ButtonStyle.blurple, custom_id="ConfigImage"),
                disnake.ui.Button(label="Tempo para Apagar",emoji=clock, style=disnake.ButtonStyle.blurple, custom_id="ConfigTempoApagar"),
            ),
            disnake.ui.ActionRow( # Row 4
                disnake.ui.Button(label="Gerenciar Botões",emoji=config3, style=disnake.ButtonStyle.blurple, custom_id="GerenciarBotoes"),
                disnake.ui.Button(label="Voltar",emoji=voltar, style=disnake.ButtonStyle.grey, custom_id="GerenciarMensagemBoasVindas"), # Back to specific message panel
            )
        ]
        return embed, components


    # --- Modals for specific message configurations (no message_id in custom_id or init) ---
    class ConfigurarContentModal(disnake.ui.Modal):
        def __init__(self):
            with open("Database/Server/boasvindas.json", "r") as f:
                db = json.load(f)
            message_data = db["mensagens"]["boas-vindas"]
            current_content = message_data["estiloMensagem"].get("content", "")

            components = [
                disnake.ui.TextInput(
                    label="Conteúdo da mensagem",
                    placeholder="{mencao} - Mencione o usuário\n{nome} - Nome do usuário\n{servidor} - Nome do servidor\n{membros} - Quantidade de membros",
                    custom_id="content",
                    value=current_content,
                    style=disnake.TextInputStyle.paragraph,
                    required=False
                )
            ]
            super().__init__(title="Editar Conteúdo da Mensagem", components=components, custom_id="Modal_ConfigContent")

        async def callback(self, inter: disnake.ModalInteraction):
            content = inter.text_values["content"]
            try:
                with open("Database/Server/boasvindas.json", "r+") as f:
                    db = json.load(f)
                    db["mensagens"]["boas-vindas"]["estiloMensagem"]["content"] = content
                    f.seek(0)
                    json.dump(db, f, indent=4)
                    f.truncate()
                
                await inter.response.send_message(
                    content=f"{positivo} Conteúdo da mensagem configurado com sucesso!",
                    ephemeral=True,
                    delete_after=3
                )
            except Exception as e:
                await inter.response.send_message(
                    content=f"{negativo} Ocorreu um erro ao salvar o conteúdo: {str(e)}",
                    ephemeral=True,
                    delete_after=3
                )

    class ConfigurarEmbedModal(disnake.ui.Modal):
        def __init__(self):
            with open("Database/Server/boasvindas.json", "r") as f:
                db = json.load(f)
            message_data = db["mensagens"]["boas-vindas"]
            
            current_embed = message_data["estiloMensagem"].get("embed", {})
            current_title = current_embed.get("title", "")
            current_description = current_embed.get("description", "")
            current_image = current_embed.get("image", "")
            current_thumbnail = current_embed.get("thumbnail", "")
            current_color = hex(current_embed["color"]) if current_embed.get("color") is not None else ""

            components = [
                disnake.ui.TextInput(label="Título", custom_id="title", value=current_title, style=disnake.TextInputStyle.short, required=False),
                disnake.ui.TextInput(label="Descrição", custom_id="description", value=current_description, style=disnake.TextInputStyle.paragraph, required=False, placeholder="{mencao} - Mencione o usuário\n{nome} - Nome do usuário\n{servidor} - Nome do servidor\n{membros} - Quantidade de membros"),
                disnake.ui.TextInput(label="URL da Imagem (Embed)", custom_id="image", value=current_image, style=disnake.TextInputStyle.short, required=False),
                disnake.ui.TextInput(label="URL da Thumbnail", custom_id="thumbnail", value=current_thumbnail, style=disnake.TextInputStyle.short, required=False),
                disnake.ui.TextInput(label="Cor (Hex, ex: 0xFFFFFF)", custom_id="color", value=str(current_color), style=disnake.TextInputStyle.short, required=False),
            ]
            super().__init__(title="Editar Embed da Mensagem", components=components, custom_id="Modal_ConfigEmbed")

        async def callback(self, inter: disnake.ModalInteraction):
            title = inter.text_values["title"]
            description = inter.text_values["description"]
            image = inter.text_values["image"]
            thumbnail = inter.text_values["thumbnail"]
            color_str = inter.text_values["color"]
            
            color = None
            if color_str:
                try:
                    if not color_str.startswith('0x'):
                        color_str = '0x' + color_str
                    color = int(color_str, 16)
                except ValueError:
                    await inter.response.send_message(
                        content=f"{negativo} Formato de cor inválido. Use um valor hexadecimal (ex: 0xFFFFFF ou 0x00FF00).",
                        ephemeral=True,
                        delete_after=5
                    )
                    return

            try:
                with open("Database/Server/boasvindas.json", "r+") as f:
                    db = json.load(f)
                    db["mensagens"]["boas-vindas"]["estiloMensagem"]["embed"] = {
                        "title": title,
                        "description": description,
                        "image": image,
                        "thumbnail": thumbnail,
                        "color": color
                    }
                    f.seek(0)
                    json.dump(db, f, indent=4)
                    f.truncate()
                
                await inter.response.send_message(
                    content=f"{positivo} Embed da mensagem configurado com sucesso!",
                    ephemeral=True,
                    delete_after=3
                )
            except Exception as e:
                await inter.response.send_message(
                    content=f"{negativo} Ocorreu um erro ao salvar o embed: {str(e)}",
                    ephemeral=True,
                    delete_after=3
                )

    class ConfigurarImageModal(disnake.ui.Modal):
        def __init__(self):
            with open("Database/Server/boasvindas.json", "r") as f:
                db = json.load(f)
            message_data = db["mensagens"]["boas-vindas"]
            current_image_url = message_data["estiloMensagem"].get("image_url", "")

            components = [
                disnake.ui.TextInput(
                    label="URL da Imagem Direta",
                    placeholder="Cole o link direto da imagem aqui",
                    custom_id="image_url",
                    value=current_image_url,
                    style=disnake.TextInputStyle.short,
                    required=False
                )
            ]
            super().__init__(title="Configurar Imagem da Mensagem", components=components, custom_id="Modal_ConfigImage")

        async def callback(self, inter: disnake.ModalInteraction):
            image_url = inter.text_values["image_url"]
            try:
                with open("Database/Server/boasvindas.json", "r+") as f:
                    db = json.load(f)
                    db["mensagens"]["boas-vindas"]["estiloMensagem"]["image_url"] = image_url
                    f.seek(0)
                    json.dump(db, f, indent=4)
                    f.truncate()
                
                await inter.response.send_message(
                    content=f"{positivo} Imagem da mensagem configurada com sucesso!",
                    ephemeral=True,
                    delete_after=3
                )
            except Exception as e:
                await inter.response.send_message(
                    content=f"{negativo} Ocorreu um erro ao salvar a imagem: {str(e)}",
                    ephemeral=True,
                    delete_after=3
                )

    class ConfigurarTempoApagarModal(disnake.ui.Modal):
        def __init__(self):
            with open("Database/Server/boasvindas.json", "r") as f:
                db = json.load(f)
            message_data = db["mensagens"]["boas-vindas"]
            current_tempo_apagar = str(message_data.get("tempoApagar", ""))

            components = [
                disnake.ui.TextInput(
                    label="Tempo para apagar mensagem (segundos)",
                    placeholder="Deixe vazio para não apagar",
                    custom_id="tempo",
                    value=current_tempo_apagar,
                    style=disnake.TextInputStyle.short,
                    required=False
                )
            ]
            super().__init__(title="Configurar Tempo para Apagar", components=components, custom_id="Modal_ConfigTempoApagar")

        async def callback(self, inter: disnake.ModalInteraction):
            tempo_str = inter.text_values["tempo"]
            tempo = None
            if tempo_str:
                try:
                    tempo = int(tempo_str)
                    if tempo < 0:
                        raise ValueError("O tempo deve ser um número positivo.")
                except ValueError:
                    await inter.response.send_message(
                        content=f"{negativo} O valor do tempo deve ser um número inteiro positivo ou vazio.",
                        ephemeral=True,
                        delete_after=5
                    )
                    return

            try:
                with open("Database/Server/boasvindas.json", "r+") as f:
                    db = json.load(f)
                    db["mensagens"]["boas-vindas"]["tempoApagar"] = tempo
                    f.seek(0)
                    json.dump(db, f, indent=4)
                    f.truncate()
                
                await inter.response.send_message(
                    content=f"{positivo} Tempo para apagar mensagem configurado com sucesso!",
                    ephemeral=True,
                    delete_after=3
                )
            except Exception as e:
                await inter.response.send_message(
                    content=f"{negativo} Ocorreu um erro ao salvar o tempo: {str(e)}",
                    ephemeral=True,
                    delete_after=3
                )

    async def PreviewMensagemBoasVindas(inter: disnake.MessageInteraction):
        try:
            with open("Database/Server/boasvindas.json", "r") as f:
                db = json.load(f)
            message_data = db["mensagens"]["boas-vindas"]

            content = message_data["estiloMensagem"].get("content")
            deleteafter = message_data.get("tempoApagar")
            embed_data = message_data["estiloMensagem"].get("embed", {})
            image_url_direct = message_data["estiloMensagem"].get("image_url", None)
            buttons_data = message_data["estiloMensagem"].get("buttons", [])
            
            # Helper function for replacements
            def replace_placeholders(text: str) -> str:
                if not text:
                    return None
                return (
                    text.replace("{mencao}", inter.author.mention)
                    .replace("{nome}", inter.author.name)
                    .replace("{servidor}", inter.guild.name)
                    .replace("{membros}", str(inter.guild.member_count))
                )

            # Replace placeholders in content
            content_preview = replace_placeholders(content)

            # Construct embed
            embed = None
            if embed_data and any(embed_data.get(key) for key in ["title", "description", "image", "thumbnail", "color"]):
                
                # Replace placeholders in embed fields
                embed_title = replace_placeholders(embed_data.get("title"))
                embed_description = replace_placeholders(embed_data.get("description"))

                embed = disnake.Embed(
                    title=embed_title,
                    description=embed_description,
                    color=disnake.Color(embed_data["color"]) if embed_data.get("color") is not None else disnake.Color.default(),
                    timestamp=datetime.now()
                )
                if embed_data.get("image"):
                    embed.set_image(url=embed_data["image"])
                if embed_data.get("thumbnail"):
                    embed.set_thumbnail(url=embed_data["thumbnail"])
                embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon)

            # Add direct image if available
            if image_url_direct:
                if embed is None: # Create a blank embed if one doesn't exist
                     embed = disnake.Embed(color=disnake.Color.default())
                embed.set_image(url=image_url_direct)

            # Construct buttons for preview
            preview_components = []
            if buttons_data:
                row_buttons = []
                for btn_data in buttons_data:
                    if btn_data.get("url") and (btn_data["url"].startswith("http://") or btn_data["url"].startswith("https://")):
                        row_buttons.append(
                            disnake.ui.Button(
                                label=btn_data["label"],
                                emoji=btn_data.get("emoji"),
                                url=btn_data["url"],
                                style=disnake.ButtonStyle.link
                            )
                        )
                if row_buttons:
                    preview_components.append(disnake.ui.ActionRow(*row_buttons))

            preview_components.append(disnake.ui.ActionRow(disnake.ui.Button(label="Mensagem do Sistema (Prévia)", style=disnake.ButtonStyle.gray, disabled=True)))


            if not content_preview and not embed:
                await inter.response.send_message(
                    content=f"{negativo} A mensagem de boas-vindas não tem conteúdo nem embed configurados para prévia.",
                    ephemeral=True
                )
                return

            await inter.response.send_message(
                content=content_preview,
                embed=embed,
                components=preview_components,
                ephemeral=True,
                delete_after=deleteafter if deleteafter is not None else None
            )

        except Exception as e:
            await inter.response.send_message(
                content=f"{negativo} Ocorreu um erro ao gerar a prévia: {str(e)}",
                ephemeral=True
            )

    # --- Button Management Panel and Modals ---
    def obterPainelGerenciarBotoes(inter: disnake.MessageInteraction):
        with open("Database/Server/boasvindas.json", "r") as f:
            db = json.load(f)
        message_data = db["mensagens"]["boas-vindas"]
        
        buttons_list = message_data["estiloMensagem"].get("buttons", [])

        embed = disnake.Embed(
            title=f"Gerenciar Botões da Mensagem",
            description="Aqui você pode adicionar, editar ou remover botões de link da sua mensagem de boas-vindas.",
            timestamp=datetime.now(),
            color=disnake.Color(0x00FFFF)
        )
        embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon)

        if buttons_list:
            buttons_desc = ""
            for i, btn in enumerate(buttons_list):
                buttons_desc += f"{i+1}. {btn.get('emoji', '')} {btn['label']} ([Link]({btn['url']}))\n"
            embed.add_field(name="Botões Atuais", value=buttons_desc, inline=False)
        else:
            embed.add_field(name="Botões Atuais", value="Nenhum botão configurado.", inline=False)

        # *** FIX START ***
        # Build the first row of buttons dynamically
        first_row_buttons = [
            disnake.ui.Button(label="Criar Botão", emoji=mais2, style=disnake.ButtonStyle.green, custom_id="CriarBotao")
        ]
        
        # Only add Edit and Delete buttons if there are buttons to manage
        if buttons_list:
            first_row_buttons.append(
                disnake.ui.Button(label="Editar Botão", emoji=editar, style=disnake.ButtonStyle.blurple, custom_id="EditarBotao")
            )
            first_row_buttons.append(
                disnake.ui.Button(label="Deletar Botão", emoji=apagar, style=disnake.ButtonStyle.red, custom_id="DeletarBotao")
            )

        # Create the component list
        components = [
            disnake.ui.ActionRow(*first_row_buttons),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=voltar, style=disnake.ButtonStyle.grey, custom_id="EditarConfigMensagemBoasVindas")
            )
        ]
        # *** FIX END ***

        return embed, components

    class CriarEditarBotaoModal(disnake.ui.Modal):
        def __init__(self, button_index: int = None, button_data: dict = None):
            self.button_index = button_index
            
            title = "Criar Novo Botão"
            current_label = ""
            current_emoji = ""
            current_url = ""

            if button_data:
                title = "Editar Botão Existente"
                current_label = button_data.get("label", "")
                current_emoji = button_data.get("emoji", "")
                current_url = button_data.get("url", "")

            components = [
                disnake.ui.TextInput(label="Label do Botão", custom_id="label", value=current_label, style=disnake.TextInputStyle.short, required=True),
                disnake.ui.TextInput(label="Emoji (opcional)", custom_id="emoji", value=current_emoji, style=disnake.TextInputStyle.short, required=False),
                disnake.ui.TextInput(label="URL do Link", custom_id="url", value=current_url, style=disnake.TextInputStyle.short, required=True),
            ]
            super().__init__(title=title, components=components, custom_id=f"Modal_CriarEditarBotao_{button_index if button_index is not None else 'new'}")

        async def callback(self, inter: disnake.ModalInteraction):
            label = inter.text_values["label"]
            emoji = inter.text_values["emoji"] or None
            url = inter.text_values["url"]

            if not url.startswith("http://") and not url.startswith("https://"):
                await inter.response.send_message(
                    content=f"{negativo} O URL deve começar com 'http://' ou 'https://'.",
                    ephemeral=True,
                    delete_after=5
                )
                return

            try:
                with open("Database/Server/boasvindas.json", "r+") as f:
                    db = json.load(f)
                    
                    if "estiloMensagem" not in db["mensagens"]["boas-vindas"]:
                        db["mensagens"]["boas-vindas"]["estiloMensagem"] = {}
                    if "buttons" not in db["mensagens"]["boas-vindas"]["estiloMensagem"]:
                        db["mensagens"]["boas-vindas"]["estiloMensagem"]["buttons"] = []
                    
                    buttons = db["mensagens"]["boas-vindas"]["estiloMensagem"]["buttons"]
                    new_button = {"label": label, "emoji": emoji, "url": url}

                    if self.button_index is not None:
                        buttons[self.button_index] = new_button
                        success_msg = "Botão editado com sucesso!"
                    else:
                        if len(buttons) >= 5:
                            await inter.response.send_message(
                                content=f"{negativo} Você pode ter no máximo 5 botões por mensagem.",
                                ephemeral=True,
                                delete_after=5
                            )
                            return
                        buttons.append(new_button)
                        success_msg = "Botão criado com sucesso!"
                    
                    f.seek(0)
                    json.dump(db, f, indent=4)
                    f.truncate()
                
                # After saving, update the button management panel
                embed, components = BoasVindas.obterPainelGerenciarBotoes(inter)
                await inter.response.edit_message(content=None, embed=embed, components=components)
                await inter.followup.send(
                    content=f"{positivo} {success_msg}",
                    ephemeral=True,
                    delete_after=3
                )
            except Exception as e:
                await inter.response.send_message(
                    content=f"{negativo} Ocorreu um erro ao salvar o botão: {str(e)}",
                    ephemeral=True,
                    delete_after=3
                )

    async def delete_button(inter: disnake.MessageInteraction, button_index: int):
        try:
            with open("Database/Server/boasvindas.json", "r+") as f:
                db = json.load(f)
                buttons = db["mensagens"]["boas-vindas"]["estiloMensagem"].get("buttons", [])
                
                if 0 <= button_index < len(buttons):
                    del buttons[button_index]
                
                f.seek(0)
                json.dump(db, f, indent=4)
                f.truncate()
            
            embed, components = BoasVindas.obterPainelGerenciarBotoes(inter)
            await inter.response.edit_message(content=None, embed=embed, components=components)
            await inter.followup.send(
                content=f"{positivo} Botão deletado com sucesso!",
                ephemeral=True,
                delete_after=3
            )
        except Exception as e:
            await inter.response.send_message(
                content=f"{negativo} Ocorreu um erro ao deletar o botão: {str(e)}",
                ephemeral=True,
                delete_after=3
            )

    # --- Clear functions ---
    async def clear_content(inter: disnake.MessageInteraction):
        try:
            with open("Database/Server/boasvindas.json", "r+") as f:
                db = json.load(f)
                db["mensagens"]["boas-vindas"]["estiloMensagem"]["content"] = ""
                f.seek(0)
                json.dump(db, f, indent=4)
                f.truncate()
            await inter.response.send_message(f"{positivo} Conteúdo da mensagem limpo com sucesso!", ephemeral=True, delete_after=3)
        except Exception as e:
            await inter.response.send_message(f"{negativo} Ocorreu um erro ao limpar o conteúdo: {str(e)}", ephemeral=True, delete_after=3)

    async def clear_embed(inter: disnake.MessageInteraction):
        try:
            with open("Database/Server/boasvindas.json", "r+") as f:
                db = json.load(f)
                db["mensagens"]["boas-vindas"]["estiloMensagem"]["embed"] = {}
                f.seek(0)
                json.dump(db, f, indent=4)
                f.truncate()
            await inter.response.send_message(f"{positivo} Embed da mensagem limpo com sucesso!", ephemeral=True, delete_after=3)
        except Exception as e:
            await inter.response.send_message(f"{negativo} Ocorreu um erro ao limpar o embed: {str(e)}", ephemeral=True, delete_after=3)


################# SISTEMA AUTO-ROLE ###################
class AutoRole():
    def obterPainelAutoRole(inter: disnake.MessageInteraction):
        try:
            with open("Database/Server/cargos.json", "r") as f:
                db_cargos = json.load(f)
                cargo_id = db_cargos["membro"]
        except:
            cargo_id = None

        try:
            with open("Database/Server/boasvindas.json", "r") as f:
                db = json.load(f)
                sistema = db["funcoes"]["autoRole"]["membro"]
        except:
            sistema = False

        if sistema:
            sistema_text = f"{positivo} ``Ativado``"
            button = {
                "Label": "Desabilitar",
                "Emoji": reload,
                "Style": disnake.ButtonStyle.red,
            }
        else:
            sistema_text = f"{negativo} ``Desativado``"
            button = {
                "Label": "Habilitar",
                "Emoji": reload,
                "Style": disnake.ButtonStyle.green,
            }

        if cargo_id:
            cargo = inter.guild.get_role(int(cargo_id))
            cargo_text = f"{positivo} {cargo.mention}" if cargo else f"{negativo} ``Cargo inválido``"
        else:
            cargo_text = f"{negativo} ``Não configurado``"

        embed = disnake.Embed(
            title="Sistema de Auto Role",
            description=(
                "Aqui você pode gerenciar o sistema de Auto Role.\n"
                "Ele atribuirá automaticamente um cargo aos membros que entrarem no servidor.\n"
                "Certifique-se de configurar um cargo válido."
            ),
            timestamp=datetime.now(),
            color=disnake.Color(0x00FFFF)
        )
        embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon)
        embed.add_field(name="Status do Sistema", value=sistema_text, inline=True)
        embed.add_field(name="Cargo Configurado", value=cargo_text, inline=True)

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label=button["Label"],
                    emoji=button["Emoji"],
                    style=button["Style"],
                    custom_id="AtivarDesativarAutoRole"
                ),
                disnake.ui.Button(
                    label="Voltar",
                    emoji=voltar,
                    style=disnake.ButtonStyle.grey,
                    custom_id="GerenciarPainelBoasVindas_Voltar"
                ),
            )
        ]

        return embed, components
#################### INÍCIO ###########################
class BoasVindasCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def BoasVindasButtonListener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id

        # This is the initial entry point from the bot's main menu
        if custom_id == "GerenciarPainelBoasVindas":
            if not self.bot.verificar_permissao(inter.author.id, tipo="panel", nome_permissao="GerenciarPainelBoasVindas"):
                await inter.response.send_message(f"{negativo} Você não tem permissão para acessar este painel.", ephemeral=True, delete_after=5)
                return

            content = "Selecione um sistema para gerenciar ;)"
            buttons = [
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        style=disnake.ButtonStyle.blurple,
                        label="Gerenciar Mensagem de Boas-Vindas",
                        custom_id="GerenciarMensagemBoasVindas", # This button now leads directly to the single message panel
                        emoji=mensagem
                    ),
                    disnake.ui.Button(
                        style=disnake.ButtonStyle.blurple,
                        label="Gerenciar Sistema de Auto Role",
                        custom_id="GerenciarAutoRoleBoasVindas",
                        emoji=reload
                    )
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Voltar", emoji=voltar, custom_id="PainelInicial"),
                )
            ]
            await inter.response.edit_message(content=content, components=buttons, embed=None)
        
        # This is the button clicked from the intermediate panel to manage the single welcome message
        elif custom_id == "GerenciarMensagemBoasVindas":
            await inter.response.edit_message(f"{carregarAnimado} Carregando informações da mensagem...", embed=None, components=None)
            embed, components = BoasVindas.obterPainelMensagemBoasVindas(inter) # Now directly calls the single message panel
            await inter.edit_original_message(content=None, embed=embed, components=components)

        # This is the "Voltar" button from the single message management panel or AutoRole panel
        elif custom_id == "GerenciarPainelBoasVindas_Voltar":
            content = "Selecione um sistema para gerenciar ;)"
            buttons = [
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        style=disnake.ButtonStyle.blurple,
                        label="Gerenciar Mensagem de Boas-Vindas",
                        custom_id="GerenciarMensagemBoasVindas",
                        emoji=mensagem
                    ),
                    disnake.ui.Button(
                        style=disnake.ButtonStyle.blurple,
                        label="Gerenciar Sistema de Auto Role",
                        custom_id="GerenciarAutoRoleBoasVindas",
                        emoji=reload
                    )
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Voltar", emoji=voltar, custom_id="PainelInicial"),
                )
            ]
            await inter.response.edit_message(content=content, components=buttons, embed=None)

        # Actions on the single welcome message
        elif custom_id == "ToggleMensagemBoasVindas":
            await inter.response.edit_message(f"{carregarAnimado} Alterando status...", embed=None, components=None)
            with open("Database/Server/boasvindas.json", "r+") as f:
                db = json.load(f)
                current_status = db["mensagens"]["boas-vindas"].get("enabled", False)
                db["mensagens"]["boas-vindas"]["enabled"] = not current_status
                status_msg = "habilitado" if db["mensagens"]["boas-vindas"]["enabled"] else "desabilitado"
                f.seek(0)
                json.dump(db, f, indent=4)
                f.truncate()
            
            embed, components = BoasVindas.obterPainelMensagemBoasVindas(inter)
            await inter.edit_original_message(content=None, embed=embed, components=components)
            await inter.followup.send(f"{positivo} O sistema de Mensagem de Boas Vindas foi {status_msg}.", ephemeral=True, delete_after=5)

        elif custom_id == "EditarConfigMensagemBoasVindas":
            await inter.response.edit_message(f"{carregarAnimado} Carregando editor de mensagem...", embed=None, components=None)
            embed, components = BoasVindas.obterPainelEditarMensagemBoasVindas(inter)
            await inter.edit_original_message(content=None, embed=embed, components=components)

        elif custom_id == "ConfigContent":
            await inter.response.send_modal(BoasVindas.ConfigurarContentModal())
        elif custom_id == "ClearContent":
            await BoasVindas.clear_content(inter)
        
        elif custom_id == "ConfigEmbed":
            await inter.response.send_modal(BoasVindas.ConfigurarEmbedModal())
        elif custom_id == "ClearEmbed":
            await BoasVindas.clear_embed(inter)

        elif custom_id == "ConfigImage":
            await inter.response.send_modal(BoasVindas.ConfigurarImageModal())
        
        elif custom_id == "ConfigTempoApagar":
            await inter.response.send_modal(BoasVindas.ConfigurarTempoApagarModal())

        elif custom_id == "PreviewMensagemBoasVindas":
            await BoasVindas.PreviewMensagemBoasVindas(inter)

        # Button Management
        elif custom_id == "GerenciarBotoes":
            await inter.response.edit_message(f"{carregarAnimado} Carregando gerenciador de botões...", embed=None, components=None)
            embed, components = BoasVindas.obterPainelGerenciarBotoes(inter)
            await inter.edit_original_message(content=None, embed=embed, components=components)

        elif custom_id == "CriarBotao":
            await inter.response.send_modal(BoasVindas.CriarEditarBotaoModal())
        
        elif custom_id == "EditarBotao":
            with open("Database/Server/boasvindas.json", "r") as f:
                db = json.load(f)
            buttons_list = db["mensagens"]["boas-vindas"]["estiloMensagem"].get("buttons", [])

            if not buttons_list:
                await inter.response.send_message(f"{negativo} Não há botões para editar.", ephemeral=True, delete_after=3)
                return

            options = [disnake.SelectOption(label=f"{b.get('emoji', '')} {b['label']}", value=str(i)) for i, b in enumerate(buttons_list)]
            
            await inter.response.send_message(
                "Selecione o botão para editar:",
                components=[disnake.ui.ActionRow(disnake.ui.Select(custom_id="select_button_to_edit", options=options))],
                ephemeral=True
            )

        elif custom_id == "DeletarBotao":
            with open("Database/Server/boasvindas.json", "r") as f:
                db = json.load(f)
            buttons_list = db["mensagens"]["boas-vindas"]["estiloMensagem"].get("buttons", [])

            if not buttons_list:
                await inter.response.send_message(f"{negativo} Não há botões para deletar.", ephemeral=True, delete_after=3)
                return

            options = [disnake.SelectOption(label=f"{b.get('emoji', '')} {b['label']}", value=str(i)) for i, b in enumerate(buttons_list)]
            
            await inter.response.send_message(
                "Selecione o botão para deletar:",
                components=[disnake.ui.ActionRow(disnake.ui.Select(custom_id="select_button_to_delete", options=options))],
                ephemeral=True
            )

        # AutoRole Management
        elif custom_id == "GerenciarAutoRoleBoasVindas":
            await inter.response.edit_message(f"{carregarAnimado} Carregando informações", embed=None, components=None)
            embed, components = AutoRole.obterPainelAutoRole(inter)
            await inter.edit_original_message(content=None, embed=embed, components=components)

        # Fixed version of the AtivarDesativarAutoRole button handler
        elif custom_id == "AtivarDesativarAutoRole":
            await inter.response.edit_message(f"{carregarAnimado} Atualizando Auto Role...", embed=None, components=None)
    
            try:
                with open("Database/Server/boasvindas.json", "r+") as f:
                    db = json.load(f)
            
            # Move all file operations inside the with block
                    novo_status = not db["funcoes"]["autoRole"].get("membro", False)
                    db["funcoes"]["autoRole"]["membro"] = novo_status
            
                    f.seek(0)
                    json.dump(db, f, indent=4)
                    f.truncate()
        
        # File operations are now complete, continue with UI updates
                embed, components = AutoRole.obterPainelAutoRole(inter)
                await inter.edit_original_message(content=None, embed=embed, components=components)
        
                status_msg = "habilitado" if novo_status else "desabilitado"
                await inter.followup.send(
                    f"{positivo} O sistema de Auto Role foi {status_msg}.",
                    ephemeral=True,
                    delete_after=5
                )
        
            except Exception as e:
                logger.error(f"Erro ao atualizar Auto Role: {e}")
                await inter.followup.send(
                    f"{negativo} Erro ao atualizar Auto Role: {str(e)}",
                    ephemeral=True,
                    delete_after=5
                )
      
    @commands.Cog.listener("on_select_option")
    async def BoasVindasSelectListener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        if custom_id == "select_button_to_edit":
            selected_index = int(inter.values[0])
            
            # Defer update to prevent interaction failed on the select menu
            await inter.response.defer(ephemeral=True)
            
            with open("Database/Server/boasvindas.json", "r") as f:
                db = json.load(f)
            buttons_list = db["mensagens"]["boas-vindas"]["estiloMensagem"].get("buttons", [])
            
            if 0 <= selected_index < len(buttons_list):
                button_to_edit = buttons_list[selected_index]
                # Send the modal as a new interaction
                await inter.send_modal(BoasVindas.CriarEditarBotaoModal(selected_index, button_to_edit))
            else:
                await inter.followup.send(f"{negativo} Botão não encontrado para edição.", ephemeral=True, delete_after=3)
            
            # Remove the select menu message
            await inter.delete_original_message()


        elif custom_id == "select_button_to_delete":
            selected_index = int(inter.values[0])
            await BoasVindas.delete_button(inter, selected_index)
            # The delete_button function already edits the main panel and sends a followup
            # We just need to remove the select menu message
            await inter.delete_original_message()


def setup(bot: commands.Bot):
    bot.add_cog(BoasVindasCommand(bot))