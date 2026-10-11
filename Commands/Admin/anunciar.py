# anunciar.py
import disnake
import json
from disnake.ext import commands
from disnake import (
    TextInputStyle, ButtonStyle, ChannelType, Colour,
    MessageInteraction, ModalInteraction, ApplicationCommandInteraction
)
from disnake.ui import Container, TextDisplay, Separator, ActionRow
from datetime import datetime
import uuid
from typing import Optional, Dict, Any
from typing import List
from Functions.CarregarEmojis import * # Certifique-se de que este import está correto para seu ambiente

# --- Funções de Database ---
def ObterDatabase():
    filepath = "Database/Server/acoesauto.json"
    try:
        with open(filepath, "r", encoding='utf-8') as f:
            db = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        db = {}
    if "mensagens_automaticas" not in db:
        db["mensagens_automaticas"] = []
    return db

def SalvarDatabase(db):
    with open("Database/Server/acoesauto.json", "w", encoding='utf-8') as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

def ObterAnuncioDatabase():
    filepath = "Database/Server/anuncio.json"
    try:
        with open(filepath, "r", encoding='utf-8') as f:
            db = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Initial structure if file is not found or is empty/corrupted
        db = {'message': None, 'embed': {}, 'container': {'content': None}, 'imagens': {}, 'buttons': []}
    return db

def SalvarAnuncioDatabase(db):
    with open("Database/Server/anuncio.json", "w", encoding='utf-8') as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

def ObterAnuncioTemplateDatabase():
    filepath = "Database/Server/AnuncioTemplate.json"
    try:
        with open(filepath, "r", encoding='utf-8') as f:
            db = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        db = {}
    return db

def SalvarAnuncioTemplateDatabase(db):
    with open("Database/Server/AnuncioTemplate.json", "w", encoding='utf-8') as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

# --- Modais ---
class ModalAnuncioConteudo(disnake.ui.Modal):
    def __init__(self, ann_id: str, content: Optional[str]):
        super().__init__(
            title="Editar Conteúdo do Anúncio", custom_id=f"ann:m:cont:{ann_id}",
            components=[disnake.ui.TextInput(label="Conteúdo da Mensagem", custom_id="content", style=TextInputStyle.paragraph, value=content, required=False, max_length=2000)]
        )

class ModalAnuncioEmbed(disnake.ui.Modal):
    def __init__(self, ann_id: str, embed_data: dict):
        color_value = embed_data.get("color")
        initial_hex = f"#{color_value:06x}" if isinstance(color_value, int) else ""
        super().__init__(
            title="Editar Embed do Anúncio", custom_id=f"ann:m:emb:{ann_id}",
            components=[
                disnake.ui.TextInput(label="Título", custom_id="title", value=embed_data.get("title"), required=False, max_length=256),
                disnake.ui.TextInput(label="Descrição", custom_id="description", style=TextInputStyle.paragraph, value=embed_data.get("description"), required=False, max_length=4000),
                disnake.ui.TextInput(label="URL da Imagem Principal", custom_id="image_url", value=(embed_data.get("image") or {}).get("url"), required=False),
                disnake.ui.TextInput(label="URL da Thumbnail", custom_id="thumbnail_url", value=(embed_data.get("thumbnail") or {}).get("url"), required=False),
                disnake.ui.TextInput(label="Cor (HEX, ex: #2b2d31)", custom_id="color", value=initial_hex, required=False, max_length=7),
            ]
        )

class ModalAnuncioAparenciaBotao(disnake.ui.Modal):
    def __init__(self, ann_id: str, btn_id: str, btn_config: dict):
        super().__init__(
            title="Editar Aparência do Botão", custom_id=f"ann:m:btn_apr:{ann_id}:{btn_id}",
            components=[
                disnake.ui.TextInput(label="Label (Texto do Botão)", custom_id="label", value=btn_config.get("label"), max_length=80),
                disnake.ui.TextInput(label="Emoji (Opcional)", custom_id="emoji", value=btn_config.get("emoji"), required=False, max_length=50),
                disnake.ui.TextInput(label="Estilo (primary, secondary, success, danger)", custom_id="style", value=btn_config.get("style", "secondary"), max_length=10),
                disnake.ui.TextInput(label="Linha (0 a 4)", custom_id="row", value=str(btn_config.get("row", "0")), max_length=1),
            ]
        )

class ModalAnuncioAcaoLink(disnake.ui.Modal):
    def __init__(self, ann_id: str, btn_id: str, action_data: dict):
        super().__init__(title="Configurar Ação de Link", custom_id=f"ann:m:acao_link:{ann_id}:{btn_id}", components=[disnake.ui.TextInput(label="URL do Link", custom_id="url", value=action_data.get("url"), required=True)])

class ModalAnuncioAcaoMensagem(disnake.ui.Modal):
    def __init__(self, ann_id: str, btn_id: str, action_data: dict):
        embed_data = action_data.get("embed", {}) or {}
        super().__init__(title="Configurar Ação: Enviar Mensagem", custom_id=f"ann:m:acao_msg:{ann_id}:{btn_id}", components=[disnake.ui.TextInput(label="Conteúdo da Resposta", custom_id="content", style=TextInputStyle.paragraph, value=action_data.get("content"), required=False, max_length=2000), disnake.ui.TextInput(label="Título do Embed da Resposta", custom_id="title", value=embed_data.get("title"), required=False), disnake.ui.TextInput(label="Descrição do Embed da Resposta", custom_id=TextInputStyle.paragraph, value=embed_data.get("description"), required=False)])

class ModalAnuncioContainer(disnake.ui.Modal):
    def __init__(self, ann_id: str, container_data: dict):
        super().__init__(
            title="Editar Container do Anúncio", custom_id=f"ann:m:container:{ann_id}",
            components=[disnake.ui.TextInput(label="Conteúdo do Container", custom_id="content", style=TextInputStyle.paragraph, value=container_data.get("content"), required=False, max_length=4000)]
        )

class ModalAnuncioImagens(disnake.ui.Modal):
    def __init__(self, ann_id: str, imagens_data: dict):
        super().__init__(
            title="Editar Imagens do Anúncio", custom_id=f"ann:m:images:{ann_id}",
            components=[disnake.ui.TextInput(label="URL do Banner", custom_id="banner", value=imagens_data.get("banner"), required=False)]
        )

# --- COG DE ANÚNCIO ---

class AnuncioCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.temp_announcements: Dict[str, Dict[str, Any]] = {}

    def _get_announcement_editor_panel(self, ann_id: str, ann_data: Dict[str, Any]) -> List[disnake.ui.Container]:
        components = []

        # Container 1 (Header)
        container1_elements = [
            disnake.ui.TextDisplay(f"# {Never}"),
            disnake.ui.TextDisplay("Crie um anúncio personalizado, poste em um canal específico, salve e reutilize templates, utilize os botões abaixo.")
        ]
        components.append(disnake.ui.Container(*container1_elements))

        # --- Content Checks for Button States ---
        has_message = ann_data.get("message") is not None
        has_embed = ann_data.get("embed") and any(v for v in ann_data["embed"].values() if v is not None)
        has_container_content = ann_data.get("container", {}).get("content") is not None
        has_images_banner = ann_data.get("imagens", {}).get("banner") is not None
        has_buttons = bool(ann_data.get("buttons"))
        has_any_content = any([has_message, has_embed, has_container_content, has_images_banner, has_buttons])

        # Check for saved templates
        saved_templates = ObterAnuncioTemplateDatabase()
        has_saved_templates = bool(saved_templates)

        # Container 2 (Configuration Buttons)
        container2_elements = [
            disnake.ui.TextDisplay("Configure seu Anúncio utilizando os botões abaixo"),
            disnake.ui.ActionRow(
                disnake.ui.Button(style=disnake.ButtonStyle.danger, emoji=apagar, custom_id=f"ann:b:clear_msg:{ann_id}", disabled=not has_message),
                disnake.ui.Button(label="Definir Mensagem", style=disnake.ButtonStyle.secondary, emoji=conversas, custom_id=f"ann:b:modal_cont:{ann_id}")
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(style=disnake.ButtonStyle.danger, emoji=apagar, custom_id=f"ann:b:clear_embed:{ann_id}", disabled=not has_embed),
                disnake.ui.Button(label="Definir Embed", style=disnake.ButtonStyle.secondary, emoji=embedE, custom_id=f"ann:b:modal_emb:{ann_id}")
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(style=disnake.ButtonStyle.danger, emoji=apagar, custom_id=f"ann:b:clear_container:{ann_id}", disabled=not has_container_content),
                disnake.ui.Button(label="Definir Container", style=disnake.ButtonStyle.secondary, emoji=extensao, custom_id=f"ann:b:modal_container:{ann_id}")
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(style=disnake.ButtonStyle.danger, emoji=apagar, custom_id=f"ann:b:clear_images:{ann_id}", disabled=not has_images_banner),
                disnake.ui.Button(label="Definir Imagens", style=disnake.ButtonStyle.secondary, emoji=foto, custom_id=f"ann:b:modal_images:{ann_id}")
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(style=disnake.ButtonStyle.danger, emoji=apagar, custom_id=f"ann:b:clear_buttons:{ann_id}", disabled=not has_buttons),
                disnake.ui.Button(label="Configurar Botões", style=disnake.ButtonStyle.secondary, emoji=buttons, custom_id=f"ann:b:gbtn:{ann_id}")
            ),
        ]
        components.append(disnake.ui.Container(*container2_elements))

        # Container 3 (Action Buttons - Publish, Preview)
        container3_elements = [
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Publicar Anúncio", style=disnake.ButtonStyle.success, emoji=arrow, custom_id=f"ann:b:send_start:{ann_id}", disabled=not has_any_content),
                disnake.ui.Button(label="Preview", style=disnake.ButtonStyle.secondary, emoji=lupa, custom_id=f"ann:b:preview:{ann_id}", disabled=not has_any_content)
            )
        ]
        components.append(disnake.ui.Container(*container3_elements))

        # Container 4 (Utility Buttons - Clear All, Save Template, Load Templates)
        container4_elements = [
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Apagar Tudo", style=disnake.ButtonStyle.danger, emoji=apagar, custom_id=f"ann:b:clear_all:{ann_id}", disabled=not has_any_content),
                disnake.ui.Button(label="Salvar template", style=disnake.ButtonStyle.secondary, emoji=save, custom_id=f"ann:b:save_template:{ann_id}", disabled=not has_any_content),
                disnake.ui.Button(label="Templates Salvos", style=disnake.ButtonStyle.primary, emoji=canal, custom_id=f"ann:b:load_templates:{ann_id}", disabled=not has_saved_templates)
            )
        ]
        components.append(disnake.ui.Container(*container4_elements))

        return components


    # --- Comando Principal ---
    @commands.slash_command(name="anunciar", description="Cria e envia um anúncio customizável.")
    @commands.has_permissions(mention_everyone=True)
    async def announcement(self, inter: ApplicationCommandInteraction):
        await inter.response.send_message(f"{carregarAnimado} Carregando Informações...", ephemeral=True)
        ann_id = str(uuid.uuid4())
        self.temp_announcements[ann_id] = {"content": None, "embed": {}, "buttons": [], "id": ann_id}
        
        components = self._get_announcement_editor_panel(ann_id, self.temp_announcements[ann_id])
        await inter.edit_original_response(
            content=None,
            components=components
        )

    # --- Listeners ---
    @commands.Cog.listener("on_button_click")
    async def announcement_button_listener(self, inter: MessageInteraction):
        custom_id = inter.component.custom_id
        if not custom_id.startswith("ann:b:"): return

        _, _, action, context = custom_id.split(":", 3)
        params = context.split(":")
        ann_id = params[0]

        if ann_id not in self.temp_announcements:
            await inter.response.edit_message(content="Este editor de anúncio expirou.", components=[], embed=None)
            return
        
        ann_data = self.temp_announcements[ann_id]
        btn_id = params[1] if len(params) > 1 else None

        # Defer actions that will update the panel
        panel_refresh_actions = ["clear_", "add_btn", "del_btn", "gbtn", "panel"]
        if any(action.startswith(prefix) for prefix in panel_refresh_actions):
            await inter.response.defer()

        # --- Handle actions that DON'T need a defer first ---
        if action.startswith("modal_"):
            modal_type = action.split("_", 1)[1]
            if modal_type == "cont":
                await inter.response.send_modal(ModalAnuncioConteudo(ann_id, ann_data.get("message")))
            elif modal_type == "emb":
                await inter.response.send_modal(ModalAnuncioEmbed(ann_id, ann_data.get("embed", {})))
            elif modal_type == "btn_apr":
                await inter.response.send_modal(ModalAnuncioAparenciaBotao(ann_id, btn_id, next(b for b in ann_data["buttons"] if b["id"] == btn_id)))
            elif modal_type == "acao_link":
                await inter.response.send_modal(ModalAnuncioAcaoLink(ann_id, btn_id, next(b for b in ann_data["buttons"] if b["id"] == btn_id).get("action", {})))
            elif modal_type == "acao_msg":
                await inter.response.send_modal(ModalAnuncioAcaoMensagem(ann_id, btn_id, next(b for b in ann_data["buttons"] if b["id"] == btn_id).get("action", {})))
            elif modal_type == "container":
                await inter.response.send_modal(ModalAnuncioContainer(ann_id, ann_data.get("container", {})))
            elif modal_type == "images":
                await inter.response.send_modal(ModalAnuncioImagens(ann_id, ann_data.get("imagens", {})))
            return

        if action == "save_template":
            await inter.response.send_modal(
                title="Salvar Template",
                custom_id=f"ann:m:save_template:{ann_id}",
                components=[disnake.ui.TextInput(label="Nome do Template", custom_id="template_name", placeholder="Ex: Anúncio de Evento", required=True, max_length=50)]
            )
            return

        if action == "load_templates":
            templates = ObterAnuncioTemplateDatabase()
            if not templates:
                await inter.response.send_message("Nenhum template salvo encontrado.", ephemeral=True)
                return
            
            options = [disnake.SelectOption(label=name, value=name) for name in templates.keys()]
            template_select = disnake.ui.StringSelect(custom_id=f"ann:s:load_template_select:{ann_id}", placeholder="Selecione um template para carregar...", options=options)
            await inter.response.send_message("Selecione um template para carregar:", components=[template_select], ephemeral=True)
            return

        if action == "send_start":
            select_channel_view = disnake.ui.View(timeout=None)
            select_channel_view.add_item(disnake.ui.ChannelSelect(custom_id=f"ann:s_action:send_confirm:{ann_id}", placeholder="Selecione os canais para o envio", min_values=1, max_values=25, channel_types=[ChannelType.text]))
            select_channel_view.add_item(disnake.ui.Button(label="Cancelar", custom_id=f"ann:b:panel:{ann_id}", style=ButtonStyle.danger))
            await inter.response.edit_message(content="**Selecione os canais para publicar o anúncio.", view=select_channel_view, components=[])
            return

        if action == "preview":
            await inter.response.defer(ephemeral=True)
            content_msg = ann_data.get("message")
            embed_obj = disnake.Embed.from_dict(ann_data["embed"]) if ann_data.get("embed") and any(v for v in ann_data["embed"].values() if v is not None) else None
            
            container_content = ann_data.get("container", {}).get("content")
            if container_content:
                if content_msg: content_msg += "\n\n"
                else: content_msg = ""
                content_msg += f"```\n{container_content}\n```"

            banner_url = ann_data.get("imagens", {}).get("banner")
            if banner_url and embed_obj:
                embed_obj.set_image(url=banner_url)
            elif banner_url and not embed_obj:
                embed_obj = disnake.Embed(color=disnake.Colour.blue()).set_image(url=banner_url)

            preview_view = disnake.ui.View(timeout=None)
            style_map = {"primary": ButtonStyle.primary, "secondary": ButtonStyle.secondary, "success": ButtonStyle.success, "danger": ButtonStyle.danger, "link": ButtonStyle.link}
            if ann_data.get("buttons"):
                for btn in ann_data["buttons"]:
                    action_type = btn.get("action", {}).get("type")
                    url = btn.get("action", {}).get("url") if action_type == "open_link" else None
                    preview_view.add_item(disnake.ui.Button(
                        style=style_map.get(btn.get("style", "secondary"), ButtonStyle.secondary),
                        label=btn.get("label"), emoji=btn.get("emoji"),
                        custom_id=f"ma:b:{ann_id}:{btn['id']}" if action_type != "open_link" else None,
                        url=url, row=btn.get("row", 0)
                    ))
            
            await inter.followup.send(
                content=content_msg or "Preview do anúncio. (Sem conteúdo de mensagem)",
                embed=embed_obj,
                view=preview_view if preview_view.children else None,
                ephemeral=True
            )
            return

        # --- Process actions that were deferred ---
        if action.startswith("clear_"):
            clear_type = action.split("_", 1)[1]
            if clear_type == "msg":
                ann_data["message"] = None
            elif clear_type == "embed":
                ann_data["embed"] = {}
            elif clear_type == "container":
                ann_data["container"] = {"content": None}
            elif clear_type == "images":
                ann_data["imagens"] = {}
            elif clear_type == "buttons":
                ann_data["buttons"] = []
            elif clear_type == "all":
                ann_data.update({"message": None, "embed": {}, "container": {"content": None}, "imagens": {}, "buttons": []})
        
        elif action == "add_btn":
            new_btn_id = str(uuid.uuid4())
            ann_data.setdefault("buttons", []).append({"id": new_btn_id, "label": "Novo Botão", "style": "secondary", "row": 0, "action": {}})
        
        elif action == "del_btn":
            ann_data["buttons"] = [b for b in ann_data.get("buttons", []) if b["id"] != btn_id]

        # Actions 'gbtn' and 'panel' fall through here, and will just trigger a refresh.
        
        components = self._get_announcement_editor_panel(ann_id, ann_data)
        await inter.edit_original_message(content=None, components=components)

    @commands.Cog.listener("on_dropdown")
    async def announcement_dropdown_listener(self, inter: MessageInteraction):
        custom_id = inter.component.custom_id
        if not custom_id.startswith("ann:"): return
        
        if custom_id.startswith(f"ann:s:load_template_select:"):
            await inter.response.defer()
            
            _, _, _, ann_id = custom_id.split(":", 3)
            template_name = inter.values[0]
            
            if ann_id not in self.temp_announcements:
                await inter.edit_original_message(content="Este editor de anúncio expirou.", components=[])
                return

            templates = ObterAnuncioTemplateDatabase()
            loaded_template = templates.get(template_name)

            if loaded_template:
                self.temp_announcements[ann_id].update(loaded_template)
                components = self._get_announcement_editor_panel(ann_id, self.temp_announcements[ann_id])
                await inter.edit_original_message(content=None, components=components)
            else:
                await inter.edit_original_message(content=f"Erro ao carregar o template '{template_name}'.", components=self._get_announcement_editor_panel(ann_id, self.temp_announcements[ann_id]))
            return
        
        await inter.response.defer()


    @commands.Cog.listener("on_modal_submit")
    async def announcement_modal_submit_listener(self, inter: ModalInteraction):
        custom_id = inter.custom_id
        if not custom_id.startswith("ann:m:"): return

        await inter.response.defer()

        _, _, modal_type, context = custom_id.split(":", 3)
        parts = context.split(":")
        ann_id = parts[0]

        if ann_id not in self.temp_announcements:
            await inter.followup.send("Editor expirado.", ephemeral=True)
            return
        
        ann_data = self.temp_announcements[ann_id]

        if modal_type == "cont":
            ann_data["message"] = inter.text_values["content"] or None
        elif modal_type == "emb":
            color_str = inter.text_values["color"]
            try:
                color_val = int(color_str.lstrip("#"), 16) if color_str else None
            except (ValueError, TypeError):
                color_val = None
            ann_data["embed"] = {
                "title": inter.text_values["title"] or None,
                "description": inter.text_values["description"] or None,
                "image": {"url": u} if (u := inter.text_values["image_url"]) else None,
                "thumbnail": {"url": u} if (u := inter.text_values["thumbnail_url"]) else None,
                "color": color_val
            }
        elif modal_type == "container":
            ann_data.setdefault("container", {})["content"] = inter.text_values["content"] or None
        elif modal_type == "images":
            ann_data.setdefault("imagens", {})["banner"] = inter.text_values["banner"] or None
        elif modal_type == "save_template":
            template_name = inter.text_values["template_name"]
            templates_db = ObterAnuncioTemplateDatabase()
            templates_db[template_name] = ann_data.copy()
            SalvarAnuncioTemplateDatabase(templates_db)
        
        elif len(parts) >= 2: # Existing button-related modals
            btn_id = parts[1]
            btn_config = next((b for b in ann_data.get("buttons", []) if b["id"] == btn_id), None)
            if btn_config:
                if modal_type == "btn_apr":
                    row_str = inter.text_values["row"]
                    btn_config.update({
                        "label": inter.text_values["label"],
                        "emoji": inter.text_values["emoji"] or None,
                        "style": inter.text_values["style"].lower() or "secondary",
                        "row": int(row_str) if row_str.isdigit() and 0 <= int(row_str) <= 4 else 0
                    })
                elif modal_type == "acao_link":
                    btn_config.update({
                        "action": {"type": "open_link", "url": inter.text_values["url"]},
                        "style": "link",
                        "label": btn_config.get("label") or inter.text_values.get("url") or "Link"
                    })
                elif modal_type == "acao_msg":
                    action_data = btn_config.setdefault("action", {"type": "send_message", "ephemeral": True})
                    action_data.update({
                        "content": inter.text_values["content"] or None,
                        "embed": {
                            "title": inter.text_values["title"] or None,
                            "description": inter.text_values["description"] or None
                        }
                    })
        
        # After any modal submission, re-render the panel
        components = self._get_announcement_editor_panel(ann_id, ann_data)
        await inter.edit_original_message(content=None, components=components)

def setup(bot: commands.Bot):
    bot.add_cog(AnuncioCommand(bot))