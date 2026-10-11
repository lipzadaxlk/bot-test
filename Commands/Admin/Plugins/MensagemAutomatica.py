# MensagemAutomatica.py
import disnake
import json
from disnake.ext import commands
from disnake import *
from Functions.CarregarEmojis import *
from datetime import datetime
import uuid
from typing import Optional

# --- GERENCIAMENTO DE DATABASE ---

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

# --- MODAIS DE CONFIGURAÇÃO ---

class ModalConfigGeral(disnake.ui.Modal):
    def __init__(self, msg_config: dict):
        components = [
            disnake.ui.TextInput(
                label="Nome da Configuração (Ex: Cargos)",
                custom_id="name",
                value=msg_config.get("name")
            ),
            disnake.ui.TextInput(
                label="Canais (IDs, um por linha)",
                custom_id="canais",
                style=TextInputStyle.paragraph,
                value="\n".join(map(str, msg_config.get("canais", []))),
                required=False
            ),
            disnake.ui.TextInput(
                label="Delay (minutos, deixe vazio para não repetir)",
                custom_id="delay",
                value=str(msg_config.get("delay", "")),
                required=False
            ),
        ]
        super().__init__(
            title="Configuração Geral da Mensagem",
            custom_id=f"ma:m:geral:{msg_config['id']}",
            components=components
        )

class ModalConteudoPrincipal(disnake.ui.Modal):
    def __init__(self, msg_id: str, content: Optional[str]):
        super().__init__(
            title="Editar Conteúdo Principal",
            custom_id=f"ma:m:cont_princ:{msg_id}",
            components=[
                disnake.ui.TextInput(
                    label="Conteúdo da Mensagem",
                    custom_id="content",
                    style=TextInputStyle.paragraph,
                    value=content,
                    required=False,
                    max_length=2000
                )
            ]
        )

class ModalEmbedPrincipal(disnake.ui.Modal):
    def __init__(self, msg_id: str, embed_data: dict):
        # Determine the initial color value as a hex string
        color_value = embed_data.get("color")
        initial_hex = f"#{color_value:06x}" if isinstance(color_value, int) else "#2b2d31"

        components = [
            disnake.ui.TextInput(
                label="Título",
                custom_id="title",
                value=embed_data.get("title"),
                required=False,
                max_length=256
            ),
            disnake.ui.TextInput(
                label="Descrição",
                custom_id="description",
                style=TextInputStyle.paragraph,
                value=embed_data.get("description"),
                required=False,
                max_length=4000
            ),
            disnake.ui.TextInput(
                label="URL da Imagem Principal",
                custom_id="image_url",
                value=(embed_data.get("image") or {}).get("url"),
                required=False
            ),
            disnake.ui.TextInput(
                label="URL da Thumbnail",
                custom_id="thumbnail_url",
                value=(embed_data.get("thumbnail") or {}).get("url"),
                required=False
            ),
            disnake.ui.TextInput(
                label="Cor (HEX, ex: #2b2d31)",
                custom_id="color",
                value=initial_hex,  # <-- CORRECTED LINE
                required=False,
                max_length=7
            ),
        ]
        super().__init__(
            title="Editar Embed Principal",
            custom_id=f"ma:m:emb_princ:{msg_id}",
            components=components
        )
      
class ModalAparenciaBotao(disnake.ui.Modal):
    def __init__(self, msg_id: str, btn_id: str, btn_config: dict):
        components = [
            disnake.ui.TextInput(
                label="Label (Texto do Botão)",
                custom_id="label",
                value=btn_config.get("label"),
                max_length=80
            ),
            disnake.ui.TextInput(
                label="Emoji (Opcional)",
                custom_id="emoji",
                value=btn_config.get("emoji"),
                required=False,
                max_length=50
            ),
            disnake.ui.TextInput(
                label="Estilo (primary, secondary, success, danger)",
                custom_id="style",
                value=btn_config.get("style", "secondary"),
                max_length=10
            ),
            disnake.ui.TextInput(
                label="Linha (0 a 4)",
                custom_id="row",
                value=str(btn_config.get("row", "0")),
                max_length=1
            ),
        ]
        super().__init__(
            title="Editar Aparência do Botão",
            custom_id=f"ma:m:btn_apr:{msg_id}:{btn_id}",
            components=components
        )

class ModalAcaoLink(disnake.ui.Modal):
    def __init__(self, msg_id: str, btn_id: str, action_data: dict):
        super().__init__(
            title="Configurar Ação de Link",
            custom_id=f"ma:m:acao_link:{msg_id}:{btn_id}",
            components=[
                disnake.ui.TextInput(
                    label="URL do Link",
                    custom_id="url",
                    value=action_data.get("url"),
                    required=True
                )
            ]
        )

class ModalAcaoMensagem(disnake.ui.Modal):
    def __init__(self, msg_id: str, btn_id: str, action_data: dict):
        embed_data = action_data.get("embed", {}) or {}
        components = [
            disnake.ui.TextInput(
                label="Conteúdo da Resposta",
                custom_id="content",
                style=TextInputStyle.paragraph,
                value=action_data.get("content"),
                required=False,
                max_length=2000
            ),
            disnake.ui.TextInput(
                label="Título do Embed da Resposta",
                custom_id="title",
                value=embed_data.get("title"),
                required=False
            ),
            disnake.ui.TextInput(
                label="Descrição do Embed da Resposta",
                custom_id="description",
                style=TextInputStyle.paragraph,
                value=embed_data.get("description"),
                required=False
            ),
        ]
        super().__init__(
            title="Configurar Ação: Enviar Mensagem",
            custom_id=f"ma:m:acao_msg:{msg_id}:{btn_id}",
            components=components
        )

# --- COG E LISTENERS ---

class MensagemAutomaticaCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # --- MÉTODOS DE PAINEL (UI) ---

    async def _show_panel_principal(self, inter: disnake.Interaction):
        if not inter.response.is_done():
            await inter.response.defer()
            
        db = ObterDatabase()
        messages = db.get("mensagens_automaticas", [])
        
        container_elems = [
            disnake.ui.TextDisplay("# 🔨 Construtor de Mensagens Automáticas"),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay("Gerencie as mensagens automáticas do seu servidor. Selecione uma mensagem para editar ou crie uma nova."),
            disnake.ui.Separator(),
        ]
        
        options = [
            disnake.SelectOption(
                label=f"{f'{ligado}' if m.get('sistema_ativo') else f'{desligado}'} {m.get('name', 'Sem Nome')}",
                value=f"ma:n:cfg:{m['id']}",
                description=f"Botões: {len(m.get('buttons', []))}"
            ) for m in messages
        ] or [disnake.SelectOption(label="Nenhuma mensagem criada", value="null")]
        
        container_elems.extend([
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    placeholder="Selecione uma mensagem para gerenciar",
                    options=options,
                    custom_id="ma_select_nav",
                    disabled=not messages
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Criar Nova Mensagem", custom_id="ma:a:cmsg", style=ButtonStyle.green, emoji=mais2),
                disnake.ui.Button(label="Voltar", emoji=voltar, custom_id="GerenciarAcoesAutomaticas")
            )
        ])
        
        container = disnake.ui.Container(*container_elems)
        await inter.edit_original_message(embed=None, components=[container])

    async def _show_panel_config_msg(self, inter: disnake.Interaction, msg_id: str):
        if not inter.response.is_done():
            await inter.response.defer()

        db = ObterDatabase()
        msg_config = next((m for m in db["mensagens_automaticas"] if m["id"] == msg_id), None)
        if not msg_config:
            return await self._show_panel_principal(inter)
            
        status = f"{ligado} Ativo" if msg_config.get("sistema_ativo") else f"{desligado} Inativo"
        
        embed = disnake.Embed(
            title=f"Configurando: {msg_config.get('name', 'Sem Nome')}",
            description=f"**Status:** {status}",
            color=0x2f3136
        )
        embed.add_field(name="Conteúdo Principal", value=f"```{msg_config.get('content') or 'Não definido'}```", inline=False)
        embed.add_field(name="Total de Botões", value=f"`{len(msg_config.get('buttons', []))}`", inline=True)
        embed.add_field(name="Canais Agendados", value=f"`{len(msg_config.get('canais', []))}`", inline=True)
        embed.add_field(name="Delay (Minutos)", value=f"`{msg_config.get('delay') or 'Nenhum'}`", inline=True)
        
        view = disnake.ui.View(timeout=None)
        view.add_item(disnake.ui.Button(label="Habilitar" if not msg_config.get("sistema_ativo") else "Desabilitar", emoji=reload, custom_id=f"ma:a:tgl_msg:{msg_id}", style=ButtonStyle.green if not msg_config.get("sistema_ativo") else ButtonStyle.red))
        view.add_item(disnake.ui.Button(label="Editar Geral", custom_id=f"ma:m:geral:{msg_id}", emoji=config3))
        view.add_item(disnake.ui.Button(label="Editar Conteúdo", custom_id=f"ma:m:cont_princ:{msg_id}", emoji=mensagem))
        view.add_item(disnake.ui.Button(label="Editar Embed", custom_id=f"ma:m:emb_princ:{msg_id}", emoji=embedE))
        view.add_item(disnake.ui.Button(label="Gerenciar Botões", custom_id=f"ma:n:gbtn:{msg_id}", style=ButtonStyle.blurple, emoji=editar))
        view.add_item(disnake.ui.Button(label="Deletar Mensagem", custom_id=f"ma:a:del_msg:{msg_id}", style=ButtonStyle.danger, emoji=apagar))
        view.add_item(disnake.ui.Button(label="Voltar", custom_id="AcessarMensagensAcoesAuto", emoji=voltar))
        
        await inter.edit_original_message(embed=embed, view=view, content=None)

    async def _show_panel_gerenciar_botoes(self, inter: disnake.Interaction, msg_id: str):
        if not inter.response.is_done():
            await inter.response.defer()

        db = ObterDatabase()
        msg_config = next((m for m in db["mensagens_automaticas"] if m["id"] == msg_id), None)
        if not msg_config:
            return await self._show_panel_principal(inter)
            
        embed = disnake.Embed(
            title=f"Gerenciando Botões de: {msg_config.get('name', 'Sem Nome')}",
            description="Selecione um botão para editar ou adicione um novo.",
            color=0x2f3136
        )
        
        options = [
            disnake.SelectOption(
                label=f"{b.get('emoji', '')} {b.get('label', 'S/ Label')}".strip(),
                value=f"ma:n:cbtn:{msg_id}:{b['id']}",
                description=f"Ação: {b.get('action', {}).get('type', 'Nenhuma')}"
            ) for b in msg_config.get("buttons", [])
        ] or [disnake.SelectOption(label="Nenhum botão configurado", value="null")]
        
        view = disnake.ui.View(timeout=None)
        view.add_item(
            disnake.ui.StringSelect(
                placeholder="Selecione um botão para editar",
                options=options,
                custom_id="ma_select_nav",
                disabled=not msg_config.get("buttons", [])
            )
        )
        view.add_item(disnake.ui.Button(label="Adicionar Novo Botão", custom_id=f"ma:a:cbtn:{msg_id}", style=ButtonStyle.green, emoji=mais2))
        view.add_item(disnake.ui.Button(label="Voltar", custom_id=f"ma:n:cfg:{msg_id}", emoji=voltar))
        
        await inter.edit_original_message(embed=embed, view=view, content=None)

    async def _show_panel_config_botao(self, inter: disnake.Interaction, msg_id: str, btn_id: str):
        if not inter.response.is_done():
            await inter.response.defer()

        db = ObterDatabase()
        msg_config = next((m for m in db["mensagens_automaticas"] if m["id"] == msg_id), None)
        if not msg_config:
            return await self._show_panel_principal(inter)
            
        btn_config = next((b for b in msg_config.get("buttons", []) if b["id"] == btn_id), None)
        if not btn_config:
            return await self._show_panel_gerenciar_botoes(inter, msg_id)
        
        action = btn_config.get("action", {})
        action_type = action.get("type", "Nenhuma")
        action_desc_map = {
            "send_message": "Responde com uma mensagem.",
            "add_role": f"Adiciona o cargo <@&{action.get('role_id')}>" if action.get('role_id') else "Adiciona um cargo (não selecionado).",
            "remove_role": f"Remove o cargo <@&{action.get('role_id')}>" if action.get('role_id') else "Remove um cargo (não selecionado).",
            "toggle_role": f"Alterna o cargo <@&{action.get('role_id')}>" if action.get('role_id') else "Alterna um cargo (não selecionado).",
            "open_link": f"Abre o link: {action.get('url')}"
        }
        action_desc = action_desc_map.get(action_type, "Nenhuma ação definida.")
        
        embed = disnake.Embed(
            title=f"Configurando Botão: {btn_config.get('label')}",
            description=f"**Ação Atual:** {action_desc}",
            color=0x2f3136
        )
        
        view = disnake.ui.View(timeout=None)
        view.add_item(disnake.ui.Button(label="Editar Aparência", custom_id=f"ma:m:btn_apr:{msg_id}:{btn_id}", emoji=personalizarE))
        view.add_item(disnake.ui.Button(label="Definir Ação", custom_id=f"ma:n:dacao:{msg_id}:{btn_id}", style=ButtonStyle.blurple, emoji=config2))
        view.add_item(disnake.ui.Button(label="Deletar Botão", custom_id=f"ma:a:del_btn:{msg_id}:{btn_id}", style=ButtonStyle.danger, emoji=apagar))
        view.add_item(disnake.ui.Button(label="Voltar", custom_id=f"ma:n:gbtn:{msg_id}", emoji=voltar))
        
        await inter.edit_original_message(embed=embed, view=view, content=None)
        
    async def _show_panel_definir_acao(self, inter: disnake.Interaction, msg_id: str, btn_id: str):
        if not inter.response.is_done():
            await inter.response.defer()

        btn_config = next((b for m in ObterDatabase()["mensagens_automaticas"] if m["id"] == msg_id for b in m.get("buttons", []) if b["id"] == btn_id), None)
        action_type = btn_config.get("action", {}).get("type")
        
        options = [
            disnake.SelectOption(label="Enviar Mensagem", value="send_message"),
            disnake.SelectOption(label="Adicionar Cargo", value="add_role"),
            disnake.SelectOption(label="Remover Cargo", value="remove_role"),
            disnake.SelectOption(label="Alternar Cargo", value="toggle_role"),
            disnake.SelectOption(label="Definir como Link", value="open_link")
        ]
        
        view = disnake.ui.View(timeout=None)
        view.add_item(disnake.ui.StringSelect(custom_id=f"ma:s:atype:{msg_id}:{btn_id}", placeholder="Selecione o tipo de ação...", options=options))
        
        if action_type == "send_message":
            ephemeral_label = "Resposta Privada" if btn_config["action"].get("ephemeral", True) else "Resposta Pública"
            view.add_item(disnake.ui.Button(label="Editar Resposta", custom_id=f"ma:m:acao_msg:{msg_id}:{btn_id}", emoji=editar))
            view.add_item(disnake.ui.Button(label=ephemeral_label, custom_id=f"ma:a:tgl_eph:{msg_id}:{btn_id}", style=ButtonStyle.secondary, emoji="👻"))
        elif action_type in ["add_role", "remove_role", "toggle_role"]:
            view.add_item(disnake.ui.RoleSelect(custom_id=f"ma:s:arole:{msg_id}:{btn_id}", placeholder="Selecione o cargo para a ação"))
        elif action_type == "open_link":
            view.add_item(disnake.ui.Button(label="Definir URL", custom_id=f"ma:m:acao_link:{msg_id}:{btn_id}", emoji=link))
            
        view.add_item(disnake.ui.Button(label="Voltar", custom_id=f"ma:n:cbtn:{msg_id}:{btn_id}", emoji=voltar))
        
        content = (
            f"**Configurando a Ação do Botão**\n"
            f"Tipo atual: `{action_type or 'Nenhum'}`\n\n"
            f"1. Escolha um novo tipo de ação no menu, se desejar.\n"
            f"2. Use os botões/menus abaixo para configurar a ação selecionada."
        )
        await inter.edit_original_message(content=content, view=view, embed=None)

    # --- MÉTODO CENTRAL DE NAVEGAÇÃO ---

    async def _handle_navigation(self, inter: disnake.Interaction, nav_value: str):
        try:
            _, main_type, context = nav_value.split(":", 2)
            if main_type != "n": return

            parts = context.split(":")
            nav_target = parts[0]
            msg_id = parts[1]

            if nav_target == "cfg":
                await self._show_panel_config_msg(inter, msg_id)
            elif nav_target == "gbtn":
                await self._show_panel_gerenciar_botoes(inter, msg_id)
            elif len(parts) > 2:
                btn_id = parts[2]
                if nav_target == "cbtn":
                    await self._show_panel_config_botao(inter, msg_id, btn_id)
                elif nav_target == "dacao":
                    await self._show_panel_definir_acao(inter, msg_id, btn_id)
        except (ValueError, IndexError):
            # Ignora custom_ids de navegação malformados ou incompletos
            pass

    # --- LISTENERS DE INTERAÇÃO ---

    @commands.Cog.listener("on_button_click")
    async def auto_msg_button_listener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        if custom_id == "AcessarMensagensAcoesAuto":
            return await self._show_panel_principal(inter)
            
        if not custom_id.startswith("ma:"):
            return

        try:
            _, main_type, context = custom_id.split(":", 2)
            parts = context.split(":")
        except ValueError:
            return

        if main_type == "n":
            return await self._handle_navigation(inter, custom_id)
        
        elif main_type == "a":
            action_target = parts[0]
            db = ObterDatabase()

            if action_target == "cmsg":
                new_id = str(uuid.uuid4())
                db["mensagens_automaticas"].append({
                    "id": new_id, "name": "Nova Mensagem", "sistema_ativo": False,
                    "buttons": [], "canais": [], "delay": None,
                    "content": None, "embed": {}
                })
                SalvarDatabase(db)
                await self._show_panel_config_msg(inter, new_id)
                
            elif len(parts) >= 2:
                msg_id = parts[1]
                msg_config = next((m for m in db["mensagens_automaticas"] if m["id"] == msg_id), None)
                if not msg_config:
                    return await inter.response.send_message(f"{negativo} Mensagem não encontrada.", ephemeral=True)

                if action_target == "del_msg":
                    db["mensagens_automaticas"] = [m for m in db["mensagens_automaticas"] if m["id"] != msg_id]
                    SalvarDatabase(db)
                    await self._show_panel_principal(inter)
                    
                elif action_target == "tgl_msg":
                    msg_config["sistema_ativo"] = not msg_config.get("sistema_ativo", False)
                    SalvarDatabase(db)
                    await self._show_panel_config_msg(inter, msg_id)
                    
                elif action_target == "cbtn":
                    btn_id = str(uuid.uuid4())
                    msg_config.setdefault("buttons", []).append({
                        "id": btn_id, "label": "Novo Botão", "style": "secondary",
                        "row": 0, "action": {}
                    })
                    SalvarDatabase(db)
                    await self._show_panel_config_botao(inter, msg_id, btn_id)
                    
                elif len(parts) >= 3:
                    btn_id = parts[2]
                    btn_config = next((b for b in msg_config.get("buttons", []) if b["id"] == btn_id), None)
                    if not btn_config:
                        return await inter.response.send_message(f"{negativo} Botão não encontrado.", ephemeral=True)

                    if action_target == "del_btn":
                        msg_config["buttons"] = [b for b in msg_config.get("buttons", []) if b["id"] != btn_id]
                        SalvarDatabase(db)
                        await self._show_panel_gerenciar_botoes(inter, msg_id)
                        
                    elif action_target == "tgl_eph":
                        btn_config.setdefault("action", {})["ephemeral"] = not btn_config.get("action", {}).get("ephemeral", True)
                        SalvarDatabase(db)
                        await self._show_panel_definir_acao(inter, msg_id, btn_id)

        elif main_type == "m":
            modal_target, msg_id = parts[0], parts[1]
            db = ObterDatabase()
            msg_config = next((m for m in db["mensagens_automaticas"] if m["id"] == msg_id), None)
            if not msg_config: return
            
            if modal_target == "geral":
                await inter.response.send_modal(ModalConfigGeral(msg_config))
            elif modal_target == "cont_princ":
                await inter.response.send_modal(ModalConteudoPrincipal(msg_id, msg_config.get("content")))
            elif modal_target == "emb_princ":
                await inter.response.send_modal(ModalEmbedPrincipal(msg_id, msg_config.get("embed", {})))
            elif len(parts) >= 3:
                btn_id = parts[2]
                btn_config = next((b for b in msg_config.get("buttons", []) if b["id"] == btn_id), None)
                if not btn_config: return
                
                if modal_target == "btn_apr":
                    await inter.response.send_modal(ModalAparenciaBotao(msg_id, btn_id, btn_config))
                elif modal_target == "acao_link":
                    await inter.response.send_modal(ModalAcaoLink(msg_id, btn_id, btn_config.get("action", {})))
                elif modal_target == "acao_msg":
                    await inter.response.send_modal(ModalAcaoMensagem(msg_id, btn_id, btn_config.get("action", {})))

    @commands.Cog.listener("on_modal_submit")
    async def auto_msg_modal_listener(self, inter: disnake.ModalInteraction):
        custom_id = inter.custom_id
        if not custom_id.startswith("ma:m:"):
            return

        # Deferir a resposta para não dar timeout, mas sem atualizar a mensagem original ainda.
        await inter.response.defer(ephemeral=True)

        _, _, modal_type, context = custom_id.split(":", 3)
        parts = context.split(":")
        msg_id = parts[0]
        
        db = ObterDatabase()
        msg_config = next((m for m in db["mensagens_automaticas"] if m["id"] == msg_id), None)
        if not msg_config: 
            return await inter.followup.send(f"{negativo} A mensagem original foi deletada.", ephemeral=True)

        success_message = f"{positivo} Configuração atualizada com sucesso!"

        if modal_type == "geral":
            canais_str = inter.text_values["canais"].split("\n")
            canais_int = [int(c.strip()) for c in canais_str if c.strip().isdigit()]
            delay_str = inter.text_values["delay"]
            msg_config.update({
                "name": inter.text_values["name"],
                "canais": canais_int,
                "delay": int(delay_str) if delay_str.isdigit() else None
            })

        elif modal_type == "cont_princ":
            msg_config["content"] = inter.text_values["content"] or None

        elif modal_type == "emb_princ":
            color_str = inter.text_values["color"]
            try:
                color_val = int(color_str.lstrip("#"), 16) if color_str else None
            except ValueError:
                color_val = 0x2b2d31 # Fallback para cor padrão
            embed_data = msg_config.setdefault("embed", {})
            embed_data.update({
                "title": inter.text_values["title"] or None,
                "description": inter.text_values["description"] or None,
                "image": {"url": u} if (u := inter.text_values["image_url"]) else None,
                "thumbnail": {"url": u} if (u := inter.text_values["thumbnail_url"]) else None,
                "color": color_val
            })

        elif len(parts) >= 2:
            btn_id = parts[1]
            btn_config = next((b for b in msg_config.get("buttons", []) if b["id"] == btn_id), None)
            if not btn_config:
                return await inter.followup.send(f"{negativo} O botão original foi deletado.", ephemeral=True)

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
                    "style": "link", # Botões com link DEVEM ter o estilo "link"
                    "label": btn_config.get("label") or inter.text_values.get("url") or "Link"
                })

            elif modal_type == "acao_msg":
                action = btn_config.setdefault("action", {"type": "send_message", "ephemeral": True})
                action.update({
                    "content": inter.text_values["content"] or None,
                    "embed": {
                        "title": inter.text_values["title"] or None,
                        "description": inter.text_values["description"] or None
                    }
                })
        
        SalvarDatabase(db)
        # OTIMIZAÇÃO: Não redesenha o painel, apenas envia a confirmação.
        # As alterações aparecerão na próxima vez que o usuário navegar para o painel.
        await inter.followup.send(success_message, ephemeral=True)


    @commands.Cog.listener("on_dropdown")
    async def auto_msg_dropdown_listener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        value = inter.values[0]

        if custom_id == "ma_select_nav":
            if value == "null":
                return await inter.response.defer()
            return await self._handle_navigation(inter, value)

        elif custom_id.startswith("ma:s:"):
            _, _, select_type, context = custom_id.split(":", 3)
            msg_id, btn_id = context.split(":")
            
            db = ObterDatabase()
            btn_config = next((b for m in db["mensagens_automaticas"] if m["id"] == msg_id for b in m.get("buttons", []) if b["id"] == btn_id), None)
            if not btn_config:
                return await inter.response.send_message(f"{negativo} O botão foi deletado.", ephemeral=True)

            if select_type == "atype":
                btn_config["action"] = {"type": value}
                if value == "send_message":
                    btn_config["action"]["ephemeral"] = True
                elif value == "open_link":
                    # Força a atualização do estilo para link, evitando erros.
                    btn_config["style"] = "link"
            elif select_type == "arole":
                btn_config["action"]["role_id"] = int(value)
                
            SalvarDatabase(db)
            await self._show_panel_definir_acao(inter, msg_id, btn_id)

def setup(bot: commands.Bot):
    bot.add_cog(MensagemAutomaticaCommand(bot))