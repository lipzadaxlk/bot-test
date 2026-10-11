# -*- coding: utf-8 -*-

import disnake
import json
import re
import os
import asyncio
import pytz
import random
import string
from disnake.ext import commands
from disnake import (
    ButtonStyle,
    ChannelType,
    Colour,
    Embed,
    File,
    MessageInteraction,
    ModalInteraction,
    PermissionOverwrite,
    SelectOption,
    TextInputStyle,
    ui
)
from disnake.ui import Container, TextDisplay, Separator, ActionRow
from datetime import datetime, time
from groq import Groq
import aiohttp

# --- INÍCIO DOS PLACEHOLDERS ---
# Substitua os valores abaixo pelos emojis ou IDs do seu servidor.
# Exemplo: apagar = "🗑️" ou apagar = "<:lixo:123456789>"
from Functions.CarregarEmojis import *
# --- FIM DOS PLACEHOLDERS ---


# --- INÍCIO DAS FUNÇÕES HELPER ---

def safe_load_json(path: str):
    """Carrega um arquivo JSON de forma segura, retornando um dicionário vazio em caso de erro."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def safe_save_json(path: str, data):
    """Salva dados em um arquivo JSON de forma segura, criando diretórios se necessário."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def build_view_from_components(components):
    """Constrói uma disnake.ui.View a partir de uma lista de componentes."""
    view = ui.View(timeout=None)
    for comp in (components or []):
        try:
            view.add_item(comp)
        except Exception:
            try:
                for c in comp:
                    view.add_item(c)
            except Exception:
                pass
    return view

async def gerar_transcript_html_from_channel(channel: disnake.Thread):
    """Gera um arquivo HTML de transcript a partir das mensagens de um canal."""
    mensagens = []
    try:
        async for msg in channel.history(limit=None, oldest_first=True):
            hora = msg.created_at.strftime("%d/%m/%Y %H:%M:%S")
            autor = disnake.utils.escape_markdown(getattr(msg.author, "display_name", str(msg.author)))
            conteudo = msg.content or ""
            if msg.attachments:
                attach_urls = " ".join(a.url for a in msg.attachments)
                conteudo = (conteudo + " " + attach_urls).strip()
            mensagens.append({
                "hora": hora,
                "autor": autor,
                "conteudo": conteudo,
                "embeds": msg.embeds,
                "attachments": [a.url for a in msg.attachments]
            })
    except Exception as e:
        print(f"[Transcript] Erro ao coletar mensagens: {e}")

    html_lines = [
        f'<div class="mensagem"><span class="hora">[{m["hora"]}]</span> <span class="autor">{m["autor"]}:</span> <span class="conteudo">{disnake.utils.escape_html(m["conteudo"])}</span></div>'
        for m in mensagens
    ]
    
    html = f"""<!doctype html>
<html>
<head><meta charset='utf-8'><title>Transcript - {channel.name}</title>
<style>
body {{ background:#36393f;color:#dcddde;font-family:Arial, sans-serif;padding:16px; }}
h2 {{ color:#fff; }}
.mensagem {{ margin:8px 0; }}
.hora {{ color:#72767d; margin-right:6px; }}
.autor {{ font-weight:600; color:#fff; margin-right:6px; }}
.conteudo {{ color:#dcddde; display:inline; white-space: pre-wrap; }}
</style>
</head>
<body>
<h2>Transcript do ticket: {channel.name}</h2>
{''.join(html_lines)}
</body>
</html>"""
    pasta = "Database/Tickets/transcripts"
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, f"{channel.id}.html")
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(html)
        return caminho
    except Exception as e:
        print(f"[Transcript] Erro ao salvar HTML: {e}")
        return None

async def fechar_ticket_com_transcript(inter: MessageInteraction, tid_aberto: str, bot_instance: commands.Bot):
    """Fecha um ticket, gera o transcript, envia para os logs e notifica o usuário."""
    tickets_abertos = safe_load_json("Database/Tickets/ticketsAbertos.json")
    ticket_info = tickets_abertos.get(tid_aberto)

    if not ticket_info:
        try:
            await inter.edit_original_response("Ticket já fechado ou não encontrado.")
        except disnake.NotFound:
            pass
        return

    topic_id = ticket_info.get("server", {}).get("topicID")
    channel_obj = inter.guild.get_channel(int(topic_id)) if topic_id else None

    caminho_html = None
    if channel_obj:
        caminho_html = await gerar_transcript_html_from_channel(channel_obj)
    
    canais = safe_load_json("Database/Server/canais.json")
    log_id = canais.get("tickets") or canais.get("ticket_logs")
    if log_id:
        try:
            canal_log = inter.guild.get_channel(int(log_id))
            if canal_log:
                user_id = ticket_info.get('server', {}).get('userID')
                embed = Embed(title="Ticket Fechado", description=f"Ticket `{tid_aberto}` fechado.", timestamp=datetime.utcnow(), color=0xf79b11)
                embed.add_field(name="Criador", value=f"<@{user_id}>", inline=True)
                
                view = ui.View(timeout=None)
                view.add_item(ui.Button(label="Abrir Transcript", custom_id=f"Transcript_Open_{tid_aberto}", style=ButtonStyle.blurple))
                
                arquivo_transcript = File(caminho_html) if caminho_html and os.path.exists(caminho_html) else None
                await canal_log.send(embed=embed, file=arquivo_transcript, view=view)
        except Exception as e:
            print(f"[Transcript] Erro ao enviar para canal de logs: {e}")

    user_id = ticket_info.get('server', {}).get('userID')
    if user_id:
        try:
            user = await bot_instance.fetch_user(int(user_id))
            await user.send(embed=Embed(title="Ticket Fechado", description="Seu ticket foi fechado.", timestamp=datetime.utcnow(), color=disnake.Color.red()))
        except Exception as e:
            print(f"[Transcript] Erro ao notificar usuário por DM: {e}")

    if channel_obj:
        try:
            await channel_obj.delete()
        except Exception as e:
            print(f"[Transcript] Erro ao deletar canal do ticket: {e}")

    if tid_aberto in tickets_abertos:
        del tickets_abertos[tid_aberto]
        safe_save_json("Database/Tickets/ticketsAbertos.json", tickets_abertos)

    try:
        # Container para mostrar sucesso
        success_container = Container(
            TextDisplay("# ✅ Ticket fechado e transcript enviado para os logs."),
            Separator(divider=True)
        )
        await inter.edit_original_response(content="", embed=None, components=[success_container])
    except disnake.NotFound:
        pass

async def SincronizarTicket(inter: MessageInteraction, ticketID: str, bot: commands.Bot):
    """Sincroniza todas as mensagens de painel de um ticket com a configuração atual."""
    db = ObterDatabase()
    ticket_data = db.get(ticketID)
    if not ticket_data:
        container = Container(
            TextDisplay(f"# {negativo} Ticket não encontrado"),
            ActionRow(ui.Button(label="Voltar", emoji=voltar, custom_id="GerenciarPainelTicket"))
        )
        await inter.edit_original_response(content="", embed=None, components=[container])
        return

    message_ids = ticket_data.get("ids", [])
    if not message_ids:
        container = Container(
            TextDisplay(f"# {negativo} Nenhuma mensagem para sincronizar"),
            ActionRow(ui.Button(label="Voltar", emoji=voltar, custom_id=f"GerenciarTicket_{ticketID}"))
        )
        await inter.edit_original_response(content="", embed=None, components=[container])
        return

    try:
        message_parts = await ConstruirMensagemTicket(bot, ticketID, inter.guild)
        view = build_view_from_components(message_parts.get("components"))
    except Exception as e:
        container = Container(
            TextDisplay(f"# {negativo} Erro ao construir a mensagem do ticket\n{str(e)}"),
            ActionRow(ui.Button(label="Voltar", emoji=voltar, custom_id=f"GerenciarTicket_{ticketID}"))
        )
        await inter.edit_original_response(content="", embed=None, components=[container])
        return

    sucesso = 0
    falha = 0
    ids_removidos = []

    for msg_id_str in message_ids[:]:
        try:
            channel_id, message_id = map(int, msg_id_str.split("_"))
            channel = inter.guild.get_channel(channel_id)
            if not channel:
                falha += 1
                ids_removidos.append(msg_id_str)
                continue
            
            message = await channel.fetch_message(message_id)
            await message.edit(
                content=message_parts.get("content"),
                embed=message_parts.get("embed"),
                view=view
            )
            sucesso += 1
        except (disnake.NotFound, disnake.Forbidden):
            falha += 1
            ids_removidos.append(msg_id_str)
        except Exception as e:
            print(f"Falha ao sincronizar mensagem {msg_id_str}: {e}")
            falha += 1

    if ids_removidos:
        db[ticketID]["ids"] = [item for item in db[ticketID]["ids"] if item not in ids_removidos]
        SalvarDatabase(db)

    texto_container = f"""# {positivo} Sincronização Concluída
**Sucessos:** {sucesso}
**Falhas:** {falha}"""
    
    container = Container(
        TextDisplay(texto_container),
        Separator(divider=True),
        ActionRow(
            ui.Button(label="Voltar", emoji=voltar, custom_id=f"GerenciarTicket_{ticketID}")
        )
    )
    
    await inter.edit_original_response(content="", embed=None, components=[container])


# --- FIM DAS FUNÇÕES HELPER ---


GROK_API_KEYS = [
    # SUAS CHAVES AQUI
]
current_api_key_index = 0

def get_grok_client():
    global current_api_key_index
    if not GROK_API_KEYS or any(key.startswith("SUA_CHAVE") for key in GROK_API_KEYS):
        return None
    api_key = GROK_API_KEYS[current_api_key_index]
    current_api_key_index = (current_api_key_index + 1) % len(GROK_API_KEYS)
    return Groq(api_key=api_key)

# Funções de acesso ao banco de dados (JSON)
def ObterDatabase(): return safe_load_json("Database/Tickets/ticket.json")
def SalvarDatabase(db): safe_save_json("Database/Tickets/ticket.json", db)
def ObterTicketsAbertos(): return safe_load_json("Database/Tickets/ticketsAbertos.json")
def SalvarTicketsAbertos(db): safe_save_json("Database/Tickets/ticketsAbertos.json", db)
def ObterTicket(ticketID: str): return ObterDatabase().get(ticketID)
def ObterCategoria(ticketID: str, categoriaID: str): return ObterTicket(ticketID).get("categorias", {}).get(categoriaID)
def ObterTicketAberto(ticketID: str): return ObterTicketsAbertos().get(ticketID)
def GerarString(): return ''.join(random.choices(string.ascii_letters + string.digits, k=13))

def ObterPainelTicket(inter: MessageInteraction):
    from disnake.ui import Container, TextDisplay, Separator, ActionRow
    
    db = ObterDatabase()
    
    texto_container = f"""# {ticket} Sistema de Tickets
-# Gerencie e configure o sistema de atendimento do seu servidor."""
    
    options = [SelectOption(value=ticketID, label=ticketData['nome'], description=f"Categorias: {len(ticketData.get('categorias', {}))}", emoji=config2) for ticketID, ticketData in db.items() if ticketData.get('nome')]
    if not options:
        options = [SelectOption(label="Nenhum ticket disponível", value="placeholder")]
    
    container = Container(
        TextDisplay(texto_container),
        Separator(divider=True),
        ActionRow(
            ui.StringSelect(
                custom_id="GerenciarTicket", 
                placeholder="Selecione um Ticket para gerenciar", 
                options=options, 
                disabled=not options or options[0].value == "placeholder"
            )
        ),
        ActionRow(
            ui.Button(label="Criar Ticket", emoji=mais2, custom_id="CriarTicket", style=ButtonStyle.green),
            ui.Button(label="Voltar", emoji=voltar, custom_id="PainelInicial")
        )
    )
    
    components = [container]
    
    return components

def ConstruirEmbedPreview(embed_data: dict, guild: disnake.Guild):
    if not any(v for k, v in embed_data.items() if k not in ['fields', 'timestamp']) and not embed_data.get('fields'):
        return Embed(description="A embed está vazia. Configure-a para ver uma prévia.", color=disnake.Color.red())
    
    temp_embed_data = embed_data.copy()
    color_val = temp_embed_data.pop("color", None)
    
    if isinstance(color_val, str) and color_val.startswith("#"):
        try:
            color_val = int(color_val.lstrip("#"), 16)
        except ValueError:
            color_val = disnake.Color.default()
            
    final_embed = Embed.from_dict({k: v for k, v in temp_embed_data.items() if v is not None and k != 'timestamp'})
    final_embed.color = color_val
    if temp_embed_data.get("timestamp"):
        final_embed.timestamp = datetime.now(pytz.utc)
        
    return final_embed

async def ConstruirMensagemTicket(bot: commands.Bot, ticketID: str, guild: disnake.Guild):
    ticket_data = ObterTicket(ticketID)
    if not ticket_data:
        return {"content": "Erro: Configuração do ticket não encontrada."}

    config = ticket_data.get("message_config", {})
    content = config.get("content")
    file_url = config.get("file_url")
    embed_data = config.get("embed", {})
    
    final_embed = ConstruirEmbedPreview(embed_data, guild) if any(embed_data.values()) else None
    
    final_file = None
    if file_url:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(file_url) as resp:
                    if resp.status == 200:
                        final_file = File(await resp.read(), filename=file_url.split('/')[-1])
        except Exception as e:
            print(f"Erro ao processar URL do arquivo do ticket {ticketID}: {e}")

    options = [
        SelectOption(label=cat_data.get("nome", "Categoria Sem Nome"), value=cat_id, description=cat_data.get("pre_descricao"), emoji=cat_data.get("emoji"))
        for cat_id, cat_data in ticket_data.get("categorias", {}).items()
    ]
    
    if not options:
        dropdown = ui.StringSelect(placeholder="Nenhuma categoria disponível", options=[SelectOption(label="placeholder", value="placeholder")], disabled=True)
    else:
        dropdown = ui.StringSelect(custom_id=f"AbrirCategoriaDropdown_{ticketID}", placeholder="Selecione uma categoria para abrir o ticket", options=options, min_values=1, max_values=1)
        
    return {"content": content, "embed": final_embed, "file": final_file, "components": [dropdown]}

class Ticket:
    class CriarTicket(ui.Modal):
        def __init__(self):
            components = [
                ui.TextInput(label="Nome do Painel", custom_id="name", placeholder="Ex: Suporte Geral", style=TextInputStyle.short, max_length=100),
                ui.TextInput(label="Descrição do Painel", custom_id="description", required=False, style=TextInputStyle.paragraph, placeholder="Descrição que aparece no painel de gerenciamento", max_length=1024),
            ]
            super().__init__(title="Criar Novo Painel de Ticket", components=components)

        async def callback(self, inter: ModalInteraction):
            name = inter.text_values["name"]
            desc = inter.text_values["description"] or None
            db = ObterDatabase()
            if len(db) >= 25:
                await inter.response.send_message(f"{negativo} Você não pode ter mais que 25 painéis de ticket.", ephemeral=True)
                return
            ticket_id = GerarString()
            db[ticket_id] = {
                "nome": name, "description": desc, "categorias": {}, "ids": [],
                "message_config": {"content": None, "file_url": None, "embed": {"title": None, "description": None, "color": None, "author": None, "footer": None, "image": None, "thumbnail": None, "timestamp": False, "fields": []}},
                "schedule": {"enabled": False, "days": {day: {"enabled": False, "start": "09:00", "end": "18:00"} for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]}},
                "ia": {"enabled": False, "prompt": "Você é um assistente de suporte prestativo e amigável.", "model": "llama3-8b-8192", "temperature": 0.7}
            }
            SalvarDatabase(db)
            components = await Ticket.ObterPainel(inter, ticket_id)
            await inter.response.edit_message(content="", embed=None, components=components)

    @staticmethod
    async def ObterPainel(inter: MessageInteraction, ticketID: str):
        from disnake.ui import Container, TextDisplay, Separator, ActionRow
        
        ticket = ObterTicket(ticketID)
        if not ticket:
            # Container para mostrar erro
            error_container = Container(
                TextDisplay(f"# {negativo} Ticket não encontrado"),
                Separator(divider=True)
            )
            return await inter.edit_original_response(content="", embed=None, components=[error_container])

        descricao = f"{ticket['description']}" if ticket.get("description") else "Não definida"
        
        texto_container = f"""# {ticket['nome']}
**Descrição:** {descricao}
**Categorias:** {len(ticket.get('categorias', {}))} categoria(s)"""
        
        container = Container(
            TextDisplay(texto_container),
            Separator(divider=True),
            ActionRow(
                ui.Button(label="Editar Mensagem", emoji=editar, custom_id=f"EditarMsgTicket_{ticketID}", style=ButtonStyle.blurple),
                ui.Button(label="Horários", emoji=clock, custom_id=f"HorarioTicket_{ticketID}", style=ButtonStyle.secondary),
                ui.Button(label="IA", emoji=ia, custom_id=f"IACfg_{ticketID}", style=ButtonStyle.secondary)
            ),
            ActionRow(
                ui.Button(label="Categorias", emoji=diretorio, custom_id=f"GerenciarCategoriasTicket_{ticketID}", style=ButtonStyle.green),
                ui.Button(label="Apagar", custom_id=f"ApagarTicket_{ticketID}", emoji=apagar, style=ButtonStyle.red),
                ui.Button(label="Enviar", custom_id=f"EnviarTicket_{ticketID}", emoji=arrow, style=ButtonStyle.blurple)
            ),
            ActionRow(
                ui.Button(label="Sincronizar", custom_id=f"SincronizarTicket_{ticketID}", emoji=reload),
                ui.Button(label="Voltar", emoji=voltar, custom_id="GerenciarPainelTicket")
            )
        )
        
        components = [container]
        
        return components

    class Edicao:
        @staticmethod
        async def ObterPainelPrincipal(inter: disnake.Interaction, ticketID: str, message: str = None):
            ticket = ObterTicket(ticketID)
            config = ticket.get("message_config", {})
            
            texto_container = f"""# {editar} Editor de Mensagem - {ticket['nome']}
-# Selecione o que deseja configurar na mensagem de abertura do ticket."""
            
            container = Container(
                TextDisplay(texto_container),
                Separator(divider=True),
                ActionRow(
                    ui.Button(label="Configurar Conteúdo",emoji=mensagem, custom_id=f"EditContent_{ticketID}", style=ButtonStyle.green),
                    ui.Button(emoji=apagar, custom_id=f"ClearContent_{ticketID}", style=ButtonStyle.red, disabled=not config.get("content"))
                ),
                ActionRow(
                    ui.Button(label="Configurar Embed",emoji=editar,custom_id=f"EditEmbed_{ticketID}", style=ButtonStyle.green),
                    ui.Button(emoji=apagar, custom_id=f"ResetEmbed_{ticketID}", style=ButtonStyle.red, disabled=not any(config.get("embed", {}).values()))
                ),
                ActionRow(
                    ui.Button(emoji= diretorio, label="Configurar Imagem", custom_id=f"EditFile_{ticketID}", style=ButtonStyle.green),
                    ui.Button(emoji=apagar, custom_id=f"ClearFile_{ticketID}", style=ButtonStyle.red, disabled=not config.get("file_url"))
                ),
                ActionRow(
                    ui.Button(emoji=import1, label="Importar Discohook", custom_id=f"ImportJson_{ticketID}", style=ButtonStyle.blurple),
                    ui.Button(label="Voltar", emoji=voltar, custom_id=f"GerenciarTicket_{ticketID}")
                )
            )
            
            components = [container]
            
            if inter.response.is_done():
                await inter.edit_original_message(content="", embed=None, components=components)
            else:
                await inter.response.edit_message(content="", embed=None, components=components)

        class SetContentModal(ui.Modal):
            def __init__(self, ticket_id: str):
                self.ticket_id = ticket_id
                content = ObterTicket(ticket_id).get("message_config", {}).get("content", "")
                super().__init__(title="Configurar Conteúdo", components=[ui.TextInput(label="Conteúdo da Mensagem", custom_id="content", style=TextInputStyle.paragraph, value=content, max_length=2000, required=False)])
            async def callback(self, inter: ModalInteraction):
                db = ObterDatabase()
                db[self.ticket_id]["message_config"]["content"] = inter.text_values["content"] or None
                SalvarDatabase(db)
                await Ticket.Edicao.ObterPainelPrincipal(inter, self.ticket_id, message=f"{positivo} Conteúdo salvo!")

        class SetFileModal(ui.Modal):
            def __init__(self, ticket_id: str):
                self.ticket_id = ticket_id
                file_url = ObterTicket(ticket_id).get("message_config", {}).get("file_url", "")
                super().__init__(title="Configurar Arquivo", components=[ui.TextInput(label="URL do Arquivo/Imagem", custom_id="file_url", style=TextInputStyle.short, value=file_url, placeholder="https://i.imgur.com/...", required=False)])
            async def callback(self, inter: ModalInteraction):
                db = ObterDatabase()
                db[self.ticket_id]["message_config"]["file_url"] = inter.text_values["file_url"] or None
                SalvarDatabase(db)
                await Ticket.Edicao.ObterPainelPrincipal(inter, self.ticket_id, message=f"{positivo} URL do arquivo salva!")
        
        class ImportJsonModal(ui.Modal):
            def __init__(self, ticket_id: str):
                self.ticket_id = ticket_id
                super().__init__(title="Importar JSON do Discohook", components=[ui.TextInput(label="Cole o JSON aqui", custom_id="json_data", style=TextInputStyle.paragraph)])
            async def callback(self, inter: ModalInteraction):
                json_data = inter.text_values["json_data"]
                try:
                    data = json.loads(json_data)
                    db = ObterDatabase()
                    config = db[self.ticket_id]["message_config"]
                    config["content"] = data.get("content")
                    if "embeds" in data and data["embeds"]:
                        embed_json = data["embeds"][0]
                        color = embed_json.get("color")
                        config["embed"] = {
                            "title": embed_json.get("title"),
                            "description": embed_json.get("description"),
                            "color": f"#{color:06x}" if color else None,
                            "author": embed_json.get("author"),
                            "footer": embed_json.get("footer"),
                            "image": embed_json.get("image"),
                            "thumbnail": embed_json.get("thumbnail"),
                            "timestamp": "timestamp" in embed_json,
                            "fields": embed_json.get("fields", [])
                        }
                    SalvarDatabase(db)
                    await Ticket.Edicao.ObterPainelPrincipal(inter, self.ticket_id, message=f"{positivo} JSON importado com sucesso!")
                except json.JSONDecodeError:
                    await inter.response.send_message(f"{negativo} JSON inválido.", ephemeral=True)
                except Exception as e:
                    await inter.response.send_message(f"{negativo} Erro ao processar o JSON: {e}", ephemeral=True)

        class Embed:
            @staticmethod
            async def ObterPainelConfigEmbed(inter: disnake.Interaction, ticketID: str):
                ticket = ObterTicket(ticketID)
                embed_data = ticket["message_config"]["embed"]
                
                # Criar preview em texto da embed
                preview_text = "# 📝 Configuração da Embed\n"
                preview_text += f"**Título:** {embed_data.get('title') or 'Não definido'}\n"
                preview_text += f"**Descrição:** {embed_data.get('description') or 'Não definida'}\n"
                preview_text += f"**Cor:** {embed_data.get('color') or 'Não definida'}\n"
                
                author = embed_data.get('author')
                preview_text += f"**Autor:** {author.get('name') if author else 'Não definido'}\n"
                
                footer = embed_data.get('footer')
                preview_text += f"**Footer:** {footer.get('text') if footer else 'Não definido'}\n"
                
                preview_text += f"**Timestamp:** {'Ativado' if embed_data.get('timestamp') else 'Desativado'}\n"
                preview_text += f"**Fields:** {len(embed_data.get('fields', []))} field(s)"
                
                container = Container(
                    TextDisplay(preview_text),
                    Separator(divider=True),
                    ActionRow(
                        ui.Button(label="Autor", custom_id=f"EmbEdit_Author_{ticketID}"),
                        ui.Button(label="Título", custom_id=f"EmbEdit_Title_{ticketID}"),
                        ui.Button(label="Descrição", custom_id=f"EmbEdit_Desc_{ticketID}"),
                        ui.Button(label="Cor (Hex)", custom_id=f"EmbEdit_Color_{ticketID}")
                    ),
                    ActionRow(
                        ui.Button(label="Footer", custom_id=f"EmbEdit_Footer_{ticketID}"),
                        ui.Button(label="Thumbnail", custom_id=f"EmbEdit_Thumb_{ticketID}"),
                        ui.Button(label="Imagem", custom_id=f"EmbEdit_Image_{ticketID}"),
                        ui.Button(label="Timestamp", custom_id=f"EmbEdit_Timestamp_{ticketID}", style=ButtonStyle.green if embed_data.get('timestamp') else ButtonStyle.red)
                    ),
                    ActionRow(
                        ui.Button(label="Gerenciar Fields", custom_id=f"EmbEdit_Fields_{ticketID}", style=ButtonStyle.blurple),
                        ui.Button(label="Limpar Partes", custom_id=f"EmbEdit_Clear_{ticketID}", style=ButtonStyle.red),
                        ui.Button(label="Voltar", emoji=voltar, custom_id=f"EditarMsgTicket_{ticketID}")
                    )
                )
                
                components = [container]
                
                if inter.response.is_done():
                    await inter.edit_original_message(content="", embed=None, components=components)
                else:
                    await inter.response.edit_message(content="", embed=None, components=components)

            class GenericModal(ui.Modal):
                def __init__(self, ticket_id, part_name, label, value, required=False, style=TextInputStyle.short, max_length=None):
                    self.ticket_id = ticket_id
                    self.part_name = part_name
                    components = [ui.TextInput(label=label, custom_id="value", value=value, required=required, style=style, max_length=max_length)]
                    super().__init__(title=f"Editar {label}", components=components)
                
            class SetTitleModal(GenericModal):
                def __init__(self, ticket_id): super().__init__(ticket_id, "title", "Título", ObterTicket(ticket_id)["message_config"]["embed"].get("title", ""), max_length=256)
                async def callback(self, inter: ModalInteraction): 
                    db=ObterDatabase(); db[self.ticket_id]["message_config"]["embed"]["title"] = inter.text_values["value"] or None; SalvarDatabase(db); await Ticket.Edicao.Embed.ObterPainelConfigEmbed(inter, self.ticket_id)

            class SetDescriptionModal(GenericModal):
                def __init__(self, ticket_id): super().__init__(ticket_id, "description", "Descrição", ObterTicket(ticket_id)["message_config"]["embed"].get("description", ""), style=TextInputStyle.paragraph, max_length=4000)
                async def callback(self, inter: ModalInteraction): 
                    db=ObterDatabase(); db[self.ticket_id]["message_config"]["embed"]["description"] = inter.text_values["value"] or None; SalvarDatabase(db); await Ticket.Edicao.Embed.ObterPainelConfigEmbed(inter, self.ticket_id)

            class SetColorModal(GenericModal):
                def __init__(self, ticket_id): super().__init__(ticket_id, "color", "Cor Hexadecimal", ObterTicket(ticket_id)["message_config"]["embed"].get("color", ""), max_length=7)
                async def callback(self, inter: ModalInteraction):
                    color = inter.text_values["value"].upper()
                    if color and not re.fullmatch(r"^#(?:[0-9A-F]{6})$", color): 
                        await inter.response.send_message(f"{negativo} Cor inválida. Use o formato #RRGGBB.", ephemeral=True); return
                    db=ObterDatabase(); db[self.ticket_id]["message_config"]["embed"]["color"] = color or None; SalvarDatabase(db); await Ticket.Edicao.Embed.ObterPainelConfigEmbed(inter, self.ticket_id)

            class SetAuthorModal(ui.Modal):
                def __init__(self, ticket_id): 
                    self.ticket_id = ticket_id; author = ObterTicket(ticket_id)["message_config"]["embed"].get("author", {}) or {}
                    super().__init__(title="Editar Autor", components=[
                        ui.TextInput(label="Nome do Autor", custom_id="name", value=author.get("name", "")), 
                        ui.TextInput(label="URL do Autor", custom_id="url", value=author.get("url", ""), required=False), 
                        ui.TextInput(label="URL do Ícone do Autor", custom_id="icon_url", value=author.get("icon_url", ""), required=False)])
                async def callback(self, inter: ModalInteraction): 
                    author_data = {"name": inter.text_values["name"], "url": inter.text_values["url"] or None, "icon_url": inter.text_values["icon_url"] or None}; 
                    db=ObterDatabase(); db[self.ticket_id]["message_config"]["embed"]["author"] = author_data if author_data["name"] else None; SalvarDatabase(db); await Ticket.Edicao.Embed.ObterPainelConfigEmbed(inter, self.ticket_id)

            class SetFooterModal(ui.Modal):
                def __init__(self, ticket_id):
                    self.ticket_id = ticket_id; footer = ObterTicket(ticket_id)["message_config"]["embed"].get("footer", {}) or {}
                    super().__init__(title="Editar Footer", components=[
                        ui.TextInput(label="Texto do Footer", custom_id="text", value=footer.get("text", "")), 
                        ui.TextInput(label="URL do Ícone do Footer", custom_id="icon_url", value=footer.get("icon_url", ""), required=False)])
                async def callback(self, inter: ModalInteraction): 
                    footer_data = {"text": inter.text_values["text"], "icon_url": inter.text_values["icon_url"] or None} 
                    db=ObterDatabase(); db[self.ticket_id]["message_config"]["embed"]["footer"] = footer_data if footer_data["text"] else None; SalvarDatabase(db); await Ticket.Edicao.Embed.ObterPainelConfigEmbed(inter, self.ticket_id)
            
            class SetImageModal(GenericModal):
                def __init__(self, ticket_id): super().__init__(ticket_id, "image", "URL da Imagem", ObterTicket(ticket_id)["message_config"]["embed"].get("image", {}).get("url", ""))
                async def callback(self, inter: ModalInteraction):
                    db=ObterDatabase(); value = inter.text_values["value"]; db[self.ticket_id]["message_config"]["embed"]["image"] = {"url": value} if value else None; SalvarDatabase(db); await Ticket.Edicao.Embed.ObterPainelConfigEmbed(inter, self.ticket_id)

            class SetThumbnailModal(GenericModal):
                def __init__(self, ticket_id): super().__init__(ticket_id, "thumbnail", "URL da Thumbnail", ObterTicket(ticket_id)["message_config"]["embed"].get("thumbnail", {}).get("url", ""))
                async def callback(self, inter: ModalInteraction):
                    db=ObterDatabase(); value = inter.text_values["value"]; db[self.ticket_id]["message_config"]["embed"]["thumbnail"] = {"url": value} if value else None; SalvarDatabase(db); await Ticket.Edicao.Embed.ObterPainelConfigEmbed(inter, self.ticket_id)

            class FieldModal(ui.Modal):
                def __init__(self, ticket_id: str, field_index: int = None):
                    self.ticket_id, self.field_index = ticket_id, field_index
                    title, field_name, field_value, field_inline = "Adicionar Field", "", "", "Não"
                    if field_index is not None:
                        title = "Editar Field"; field = ObterTicket(ticket_id)["message_config"]["embed"]["fields"][field_index]; field_name, field_value, field_inline = field["name"], field["value"], "Sim" if field.get("inline", False) else "Não"
                    super().__init__(title=title, components=[
                        ui.TextInput(label="Nome do Field", custom_id="name", value=field_name, max_length=256), 
                        ui.TextInput(label="Valor do Field", custom_id="value", value=field_value, style=TextInputStyle.paragraph, max_length=1024), 
                        ui.TextInput(label="Inline (Sim/Não)", custom_id="inline", value=field_inline, max_length=3)])
                async def callback(self, inter: ModalInteraction):
                    inline = inter.text_values["inline"].lower() in ['sim', 's', 'yes', 'y', 'true']
                    field_data = {"name": inter.text_values["name"], "value": inter.text_values["value"], "inline": inline}
                    db = ObterDatabase(); fields = db[self.ticket_id]["message_config"]["embed"]["fields"]
                    if self.field_index is not None: fields[self.field_index] = field_data
                    else: fields.append(field_data)
                    SalvarDatabase(db); await Ticket.Edicao.Embed.ObterPainelFields(inter, self.ticket_id)

            @staticmethod
            async def ObterPainelFields(inter: disnake.Interaction, ticketID: str):
                ticket = ObterTicket(ticketID); fields = ticket["message_config"]["embed"].get("fields", [])
                
                texto_container = f"""# {fields} Gerenciador de Fields
**Fields:** {len(fields)}/25
-# Gerencie os fields da embed do seu ticket."""
                
                action_rows = []
                
                if fields:
                    options = [SelectOption(label=f"{i+1}. {f['name']}", value=str(i)) for i, f in enumerate(fields)]
                    action_rows.append(ActionRow(
                        ui.StringSelect(custom_id=f"EmbField_Select_{ticketID}", placeholder="Selecione um field para gerenciar", options=options)
                    ))
                
                action_rows.append(ActionRow(
                    ui.Button(label="Adicionar Field", custom_id=f"EmbField_Add_{ticketID}", style=ButtonStyle.green, disabled=len(fields) >= 25),
                    ui.Button(label="Voltar", emoji=voltar, custom_id=f"EditEmbed_{ticketID}")
                ))
                
                container = Container(
                    TextDisplay(texto_container),
                    Separator(divider=True),
                    *action_rows
                )
                
                components = [container]
                
                await inter.response.edit_message(content="", embed=None, components=components)

            @staticmethod
            def ClearEmbedView(ticket_id: str):
                parts = {"author": "Autor", "title": "Título", "description": "Descrição", "color": "Cor", "footer": "Footer", "thumbnail": "Thumbnail", "image": "Imagem", "fields": "Todos os Fields"}
                options = [SelectOption(label=label, value=key) for key, label in parts.items() if ObterTicket(ticket_id)["message_config"]["embed"].get(key)]
                
                texto_container = """# 🗑️ Limpar Partes da Embed
-# Selecione as partes da embed que deseja limpar."""
                
                action_rows = []
                
                if options:
                    action_rows.append(ActionRow(
                        ui.StringSelect(custom_id=f"EmbClear_Select_{ticket_id}", placeholder="Selecione as partes para limpar", options=options, min_values=1, max_values=len(options))
                    ))
                
                action_rows.append(ActionRow(
                    ui.Button(label="Voltar", emoji=voltar, custom_id=f"EditEmbed_{ticket_id}")
                ))
                
                container = Container(
                    TextDisplay(texto_container),
                    Separator(divider=True),
                    *action_rows
                )
                
                return [container]
    
    class Horario:
        DIAS = {"monday": "Segunda", "tuesday": "Terça", "wednesday": "Quarta", "thursday": "Quinta", "friday": "Sexta", "saturday": "Sábado", "sunday": "Domingo"}
        
        @staticmethod
        def get_schedule(ticketID, categoriaID):
            if categoriaID: return ObterCategoria(ticketID, categoriaID).get("schedule", {})
            return ObterTicket(ticketID).get("schedule", {})

        @staticmethod
        async def ObterPainelHorario(inter: disnake.Interaction, ticketID: str, categoriaID: str = None, message: str = None):
            is_category = bool(categoriaID)
            schedule = Ticket.Horario.get_schedule(ticketID, categoriaID)
            ticket_data = ObterTicket(ticketID)
            
            title = f"# {clock} Horários - {ticket_data['nome']}"
            if is_category: 
                title += f" > {ObterCategoria(ticketID, categoriaID)['nome']}"
                
            desc = "Configure os horários de funcionamento. Fora desses horários, os usuários não poderão abrir tickets."
            if is_category:
                override_status = "ATIVADO (Este horário da categoria sobrescreve o geral)" if schedule.get("override") else "DESATIVADO (O horário geral está em uso)"
                desc += f"\n**Status da Sobrescrita:** {override_status}"
            
            # Construir texto dos dias
            dias_texto = ""
            for key, name in Ticket.Horario.DIAS.items():
                day_config = schedule["days"][key]
                status = f"{day_config['start']} - {day_config['end']}" if day_config["enabled"] else "Desativado"
                dias_texto += f"**{name}:** {status}\n"
                
            texto_container = f"""{title}
{desc}

{dias_texto}"""
            
            # Criar botões dos dias
            action_rows = []
            buttons_row1 = []
            buttons_row2 = []
            
            for i, (key, name) in enumerate(Ticket.Horario.DIAS.items()):
                custom_id = f"Horario_Dia_{ticketID}_{key}"
                if is_category:
                    custom_id = f"Horario_Cat_Dia_{ticketID}_{categoriaID}_{key}"
                
                button = ui.Button(label=name, custom_id=custom_id)
                if i < 4:
                    buttons_row1.append(button)
                else:
                    buttons_row2.append(button)
            
            action_rows.append(ActionRow(*buttons_row1))
            if buttons_row2:
                action_rows.append(ActionRow(*buttons_row2))
            
            # Botões adicionais
            additional_buttons = []
            if is_category:
                additional_buttons.append(ui.Button(label="Alternar Sobrescrita", custom_id=f"Horario_Override_{ticketID}_{categoriaID}", style=ButtonStyle.blurple))
            
            back_button_id = f"GerenciarTicket_{ticketID}"
            if is_category:
                back_button_id = f"GerenciarSingleCategoria_{ticketID}_{categoriaID}"
            additional_buttons.append(ui.Button(label="Voltar", emoji=voltar, custom_id=back_button_id))
            
            if additional_buttons:
                action_rows.append(ActionRow(*additional_buttons))
            
            container = Container(
                TextDisplay(texto_container),
                Separator(divider=True),
                *action_rows
            )
            
            components = [container]
            
            if inter.response.is_done():
                await inter.edit_original_message(content="", embed=None, components=components)
            else:
                await inter.response.edit_message(content="", embed=None, components=components)

        class ConfigurarDiaModal(ui.Modal):
            def __init__(self, ticket_id, day_key, categoria_id=None):
                self.ticket_id, self.day_key, self.categoria_id = ticket_id, day_key, categoria_id
                schedule = Ticket.Horario.get_schedule(ticket_id, categoria_id)
                day_config = schedule["days"][day_key]
                super().__init__(title=f"Configurar {Ticket.Horario.DIAS[day_key]}", components=[
                    ui.TextInput(label="Habilitado (Sim/Não)", custom_id="enabled", value="Sim" if day_config["enabled"] else "Não", max_length=3),
                    ui.TextInput(label="Horário de Início (HH:MM)", custom_id="start", value=day_config["start"], max_length=5),
                    ui.TextInput(label="Horário de Fim (HH:MM)", custom_id="end", value=day_config["end"], max_length=5)])
            async def callback(self, inter: ModalInteraction):
                start, end = inter.text_values["start"], inter.text_values["end"]
                if not re.fullmatch(r"^(?:[01]\d|2[0-3]):[0-5]\d$", start) or not re.fullmatch(r"^(?:[01]\d|2[0-3]):[0-5]\d$", end):
                    await inter.response.send_message(f"{negativo} Formato de hora inválido. Use HH:MM.", ephemeral=True); return
                db = ObterDatabase()
                schedule_target = db[self.ticket_id]
                if self.categoria_id: 
                    schedule_target = schedule_target["categorias"][self.categoria_id]
                
                schedule_target["schedule"]["days"][self.day_key] = {"enabled": inter.text_values["enabled"].lower().startswith('s'), "start": start, "end": end}
                SalvarDatabase(db)
                await Ticket.Horario.ObterPainelHorario(inter, self.ticket_id, self.categoria_id)

    class IA:
        @staticmethod
        async def ObterPainelIA(inter: MessageInteraction, ticketID: str):
            ticket = ObterTicket(ticketID); ia_cfg = ticket.get("ia", {})
            status, style = ("Ativado", ButtonStyle.green) if ia_cfg.get("enabled") else ("Desativado", ButtonStyle.red)
            
            texto_container = f"""# {ia} Configuração da Inteligência Artificial
**Ticket:** {ticket['nome']}
**Status:** {status}
**Modelo:** {ia_cfg.get('model', 'Não definido')}
**Temperatura:** {ia_cfg.get('temperature', 'Não definido')}
**Prompt:** {ia_cfg.get('prompt', 'Não definido')}"""
            
            container = Container(
                TextDisplay(texto_container),
                Separator(divider=True),
                ActionRow(
                    ui.Button(label=f"{status}",emoji=reload, custom_id=f"IAToggle_{ticketID}", style=style),
                    ui.Button(label="Prompt",emoji=prompt, custom_id=f"IAPrompt_{ticketID}", style=ButtonStyle.blurple),
                    ui.Button(label="Modelo",emoji=block, custom_id=f"IAModel_{ticketID}", style=ButtonStyle.blurple)
                ),
                ActionRow(
                    ui.Button(label="Temperatura",emoji=temperatura, custom_id=f"IATemp_{ticketID}", style=ButtonStyle.blurple),
                    ui.Button(label="Voltar",emoji=voltar, custom_id=f"GerenciarTicket_{ticketID}")
                )
            )
            
            components = [container]
            
            return components

        class SetPromptModal(ui.Modal):
            def __init__(self, ticket_id: str, current_prompt: str):
                self.ticket_id = ticket_id
                components = [ui.TextInput(label="Prompt do Sistema da IA", custom_id="prompt", style=TextInputStyle.paragraph, value=current_prompt, max_length=2000)]
                super().__init__(title="Configurar Prompt da IA", components=components)
            async def callback(self, inter: ModalInteraction):
                db = ObterDatabase(); db[self.ticket_id]["ia"]["prompt"] = inter.text_values["prompt"]; SalvarDatabase(db)
                components = await Ticket.IA.ObterPainelIA(inter, self.ticket_id)
                await inter.response.edit_message(content="", embed=None, components=components)


        class SetTempModal(ui.Modal):
            def __init__(self, ticket_id: str, current_temp: float):
                self.ticket_id = ticket_id
                components = [ui.TextInput(label="Temperatura (0.0 a 2.0)", custom_id="temp", style=TextInputStyle.short, value=str(current_temp), max_length=4)]
                super().__init__(title="Configurar Temperatura da IA", components=components)
            async def callback(self, inter: ModalInteraction):
                try:
                    temp = float(inter.text_values["temp"].replace(",", ".")); assert 0.0 <= temp <= 2.0
                except (ValueError, AssertionError): 
                    await inter.response.send_message("Temperatura inválida. Deve ser um número entre 0.0 e 2.0.", ephemeral=True); return
                db = ObterDatabase(); db[self.ticket_id]["ia"]["temperature"] = temp; SalvarDatabase(db)
                components = await Ticket.IA.ObterPainelIA(inter, self.ticket_id)
                await inter.response.edit_message(content="", embed=None, components=components)

    @staticmethod
    async def ApagarTicket(ticketID: str):
        db = ObterDatabase(); 
        if ticketID in db:
            del db[ticketID]
        SalvarDatabase(db)

    @staticmethod
    async def EnviarMensagem(bot: commands.Bot, inter: MessageInteraction, ticketID: str):
        channel_id_str = inter.values[0]
        channel = inter.guild.get_channel(int(channel_id_str))
        if not channel:
            # Container para mostrar erro
            error_container = Container(
                TextDisplay(f"# {negativo} Canal não encontrado."),
                Separator(divider=True)
            )
            await inter.edit_original_message(content="", embed=None, components=[error_container])
            return
            
        # Container temporário para mostrar status de envio
        temp_container = Container(
            TextDisplay(f"# {carregarAnimado} Estamos enviando sua mensagem..."),
            Separator(divider=True)
        )
        await inter.edit_original_message(content="", embed=None, components=[temp_container])
        
        try:
            message_parts = await ConstruirMensagemTicket(bot, ticketID, inter.guild)
            view = build_view_from_components(message_parts.get("components"))
            msg = await channel.send(content=message_parts.get("content"), embed=message_parts.get("embed"), file=message_parts.get("file"), view=view)
        except Exception as e: 
            container = Container(TextDisplay(f"# {negativo} Não foi possível enviar a mensagem\n{str(e)}"))
            await inter.edit_original_message(content="", embed=None, components=[container])
            return
            
        db = ObterDatabase()
        if "ids" not in db[ticketID]:
            db[ticketID]["ids"] = []
        db[ticketID]["ids"].append(f"{channel.id}_{msg.id}")
        SalvarDatabase(db)
        # Container para mostrar sucesso
        success_container = Container(
            TextDisplay(f"# {positivo} Mensagem enviada em {channel.mention}: {msg.jump_url}"),
            Separator(divider=True)
        )
        await inter.edit_original_message(content="", embed=None, components=[success_container])

    class Categorias:
        class CriarCategoria(ui.Modal):
            def __init__(self, ticket_id: str):
                self.ticket_id = ticket_id
                components = [
                    ui.TextInput(label="Nome", placeholder="Suporte", custom_id="name", style=TextInputStyle.short, max_length=50), 
                    ui.TextInput(label="Descrição", custom_id="description", placeholder="Aparece na embed do ticket", required=False, max_length=1024, style=TextInputStyle.paragraph), 
                    ui.TextInput(label="Pré Descrição", custom_id="pre-description", max_length=100, placeholder="Aparece no dropdown", style=TextInputStyle.paragraph, required=False), 
                    ui.TextInput(label="Emoji", placeholder="Emoji da categoria no dropdown", custom_id="emoji", required=False, style=TextInputStyle.short)]
                super().__init__(title="Criar Categoria", components=components)
                
            async def callback(self, inter: ModalInteraction):
                db = ObterDatabase()
                categoriaID = GerarString()
                db[self.ticket_id]["categorias"][categoriaID] = {
                    "nome": inter.text_values["name"],
                    "descricao": inter.text_values["description"] or None,
                    "pre_descricao": inter.text_values["pre-description"] or None,
                    "emoji": inter.text_values["emoji"] or None,
                    "schedule": {"override": False, "days": {day: {"enabled": False, "start": "09:00", "end": "18:00"} for day in Ticket.Horario.DIAS}}
                }
                SalvarDatabase(db)
                components = await Ticket.Categorias.ObterPainelCategoria(self.ticket_id, categoriaID)
                await inter.response.edit_message(content="", embed=None, components=components)

        class EditarCategoria(ui.Modal):
            def __init__(self, ticket_id, categoria_id):
                self.ticket_id, self.categoria_id = ticket_id, categoria_id
                categoria = ObterCategoria(ticket_id, categoria_id)
                super().__init__(title="Editar Categoria", components=[
                    ui.TextInput(label="Nome", custom_id="name", value=categoria.get("nome", "")), 
                    ui.TextInput(label="Descrição", custom_id="description", value=categoria.get("descricao", ""), required=False, style=TextInputStyle.paragraph), 
                    ui.TextInput(label="Pré Descrição", custom_id="pre-description", value=categoria.get("pre_descricao", ""), required=False), 
                    ui.TextInput(label="Emoji", custom_id="emoji", value=categoria.get("emoji", ""), required=False)])
                    
            async def callback(self, inter: ModalInteraction):
                db = ObterDatabase()
                db[self.ticket_id]["categorias"][self.categoria_id].update({
                    "nome": inter.text_values["name"],
                    "descricao": inter.text_values["description"] or None,
                    "pre_descricao": inter.text_values["pre-description"] or None,
                    "emoji": inter.text_values["emoji"] or None
                })
                SalvarDatabase(db)
                components = await Ticket.Categorias.ObterPainelCategoria(self.ticket_id, self.categoria_id)
                await inter.response.edit_message(content="", embed=None, components=components)

        @staticmethod
        async def ObterPainelGerenciarCategorias(ticketID: str):
            ticket = ObterTicket(ticketID)
            options = [SelectOption(label=catData.get("nome", "Sem Nome"), value=catID, description=catData.get("pre_descricao", "Sem descrição"), emoji=catData.get("emoji") or diretorio) for catID, catData in ticket.get("categorias", {}).items()]
            if not options: 
                options.append(SelectOption(label="Nenhuma categoria criada", value="placeholder"))
            
            texto_container = f"""# {diretorio} Gerenciar Categorias
**Ticket:** {ticket['nome']}
**Categorias:** {len(ticket.get('categorias', {}))} categoria(s)
-# Selecione uma categoria para gerenciar ou crie uma nova."""
            
            container = Container(
                TextDisplay(texto_container),
                Separator(divider=True),
                ActionRow(
                    ui.StringSelect(placeholder="Selecione uma categoria para gerenciar", custom_id=f"GerenciarSingleCategoria_{ticketID}", options=options, disabled=len(ticket.get("categorias", {})) == 0)
                ),
                ActionRow(
                    ui.Button(label="Criar Categoria", emoji=mais2, custom_id=f"CriarCategoria_{ticketID}", style=ButtonStyle.green),
                    ui.Button(label="Voltar", emoji=voltar, custom_id=f"GerenciarTicket_{ticketID}")
                )
            )
            
            components = [container]
            return components
            
        @staticmethod
        async def ObterPainelCategoria(ticketID: str, categoriaID: str):
            categoria, ticket = ObterCategoria(ticketID, categoriaID), ObterTicket(ticketID)
            if not categoria: return None
            
            texto_container = f"""# {diretorio} Gerenciar Categoria
**Ticket:** {ticket['nome']}
**Categoria:** {categoria['nome']}
**Pré-descrição:** {categoria.get('pre_descricao') or 'Não definido'}
**Descrição:** {categoria.get('descricao') or 'Não definido'}
**Emoji:** {categoria.get('emoji') or 'Não definido'}"""
            
            container = Container(
                TextDisplay(texto_container),
                Separator(divider=True),
                ActionRow(
                    ui.Button(label="Editar", emoji=editar, custom_id=f"EditarCategoria_{ticketID}_{categoriaID}", style=ButtonStyle.blurple),
                    ui.Button(label="Horários", emoji=clock, custom_id=f"HorarioCategoria_{ticketID}_{categoriaID}", style=ButtonStyle.secondary),
                    ui.Button(label="Apagar", custom_id=f"ApagarCategoria_{ticketID}_{categoriaID}", emoji=apagar, style=ButtonStyle.red)
                ),
                ActionRow(
                    ui.Button(label="Voltar", custom_id=f"GerenciarCategoriasTicket_{ticketID}", emoji=voltar)
                )
            )
            
            components = [container]
            return components

        @staticmethod
        async def ApagarCategoria(ticketID: str, categoriaID: str):
            db = ObterDatabase()
            if ticketID in db and "categorias" in db[ticketID] and categoriaID in db[ticketID]["categorias"]:
                del db[ticketID]["categorias"][categoriaID]
            SalvarDatabase(db)

class Abertura:
    @staticmethod
    def VerificarTicketAberto(userID: int):
        return any(t_data["server"]["userID"] == userID for t_data in ObterTicketsAbertos().values())

    @staticmethod
    def VerificarHorario(schedule_config):
        if not schedule_config or not schedule_config.get("enabled", True): # Assume enabled if key missing
            return True, None
            
        dias_map = {0: "monday", 1: "tuesday", 2: "wednesday", 3: "thursday", 4: "friday", 5: "saturday", 6: "sunday"}
        fuso_sp = pytz.timezone('America/Sao_Paulo')
        now_sp = datetime.now(pytz.utc).astimezone(fuso_sp)
        config_dia = schedule_config.get("days", {}).get(dias_map[now_sp.weekday()])

        if not config_dia or not config_dia.get("enabled"):
            return False, f"Os tickets para esta categoria estão fechados hoje ({now_sp.strftime('%A')})."

        try:
            hora_inicio = time.fromisoformat(config_dia["start"])
            hora_fim = time.fromisoformat(config_dia["end"])
            hora_atual = now_sp.time()
            
            if hora_inicio <= hora_fim:
                if not (hora_inicio <= hora_atual <= hora_fim):
                    return False, f"O horário de atendimento hoje é das {hora_inicio.strftime('%H:%M')} às {hora_fim.strftime('%H:%M')}."
            else: # Overnight schedule
                if not (hora_atual >= hora_inicio or hora_atual <= hora_fim):
                    return False, f"O horário de atendimento é das {hora_inicio.strftime('%H:%M')} às {hora_fim.strftime('%H:%M')}."
        except (ValueError, KeyError):
            return False, "Erro na formatação da configuração de horário."
            
        return True, None

    @staticmethod
    async def AbrirTicket(inter: MessageInteraction, ticketID: str, categoriaID: str):
        ticket, categoria = ObterTicket(ticketID), ObterCategoria(ticketID, categoriaID)
        if not categoria or not ticket: 
            await inter.response.send_message(f"{negativo} O ticket/categoria não foi encontrado.", ephemeral=True); return
        
        horario_valido, motivo = (False, "")
        final_schedule = categoria.get("schedule") if categoria.get("schedule", {}).get("override") else ticket.get("schedule")
        
        horario_valido, motivo = Abertura.VerificarHorario(final_schedule)
        if not horario_valido: 
            await inter.response.send_message(f"{negativo} {motivo}", ephemeral=True); return

        if Abertura.VerificarTicketAberto(inter.user.id): 
            await inter.response.send_message(f"{negativo} Você já possui um ticket aberto.", ephemeral=True); return
            
        await inter.response.send_message(f"{carregarAnimado} Abrindo seu ticket...", ephemeral=True)
        ticketIDAberto = GerarString()
        
        try: 
            topic = await inter.channel.create_thread(
                name=f"{categoria['nome']}・{inter.user.name}・{inter.user.id}", 
                type=ChannelType.private_thread, 
                invitable=False
            )
        except Exception as e: 
            container = Container(TextDisplay(f"# {negativo} Não foi possível criar o canal do ticket\n{str(e)}"))
            await inter.edit_original_message(content="", embed=None, components=[container])
            return
        
        ticketsAbertos = ObterTicketsAbertos()
        ticketsAbertos[ticketIDAberto] = {
            "ticketID": ticketID, "categoriaID": categoriaID, 
            "server": {"userID": inter.user.id, "topicID": topic.id}, 
            "ia": {"enabled": ticket.get("ia", {}).get("enabled", False), "assumed": False}
        }
        SalvarTicketsAbertos(ticketsAbertos)
        
        cargos = safe_load_json("Database/Server/cargos.json")
        suporte_cargo = f"<@&{cargos['suporte']}>" if cargos.get("suporte") else ""
        
        embed_controle = Embed(title=f"{categoria['nome']}", description=categoria.get('descricao') or "Seu ticket foi criado com sucesso.", timestamp=datetime.now(), color=0x00FFFF)
        embed_controle.set_footer(text=inter.guild.name, icon_url=inter.guild.icon)
        embed_controle.set_author(name=f"{inter.author.name}", icon_url=inter.author.display_avatar.url)
        
        view_controle = ui.View(timeout=None)
        view_controle.add_item(ui.Button(label="Staff", emoji=staff, custom_id=f"StaffPainel_{ticketIDAberto}", style=ButtonStyle.secondary))
        view_controle.add_item(ui.Button(label="Fechar", custom_id=f"ApagarTicketAberto_{ticketIDAberto}", emoji=apagar, style=ButtonStyle.red))
        
        await topic.send(content=f"{inter.user.mention} {suporte_cargo}", embed=embed_controle, view=view_controle)
        
        if ticket.get("ia", {}).get("enabled", False): 
            await topic.send(f"Olá {inter.user.mention}, sou um assistente de IA. Por favor, descreva seu problema detalhadamente.")
            
        container = Container(
            TextDisplay(f"# {positivo} Seu Ticket foi aberto\n{topic.mention}"),
            ActionRow(ui.Button(label="Acessar", url=topic.jump_url))
        )
        await inter.edit_original_message(content="", embed=None, components=[container])
        
        canais = safe_load_json("Database/Server/canais.json")
        if canais.get("tickets"):
            try:
                channel_log = inter.guild.get_channel(int(canais["tickets"]))
                embed_log = Embed(title="Ticket Aberto", description=f"O usuário {inter.user.mention} abriu um ticket.", timestamp=datetime.now(), color=0xf79b11)
                embed_log.add_field(name="Categoria", value=f"`{ticket['nome']}` > `{categoria['nome']}`", inline=True)
                embed_log.add_field(name="Criador", value=f"{inter.user.mention}\n`{inter.user.id}`", inline=True)
                embed_log.add_field(name="Canal", value=f"{topic.mention}", inline=False)
                await channel_log.send(embed=embed_log, view=build_view_from_components([ui.Button(label="Acessar", url=topic.jump_url)]))
            except Exception as e:
                 print(f"Erro ao logar abertura de ticket: {e}")

class TicketCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Lista de todos os custom_ids ou seus prefixos que este cog gerencia.
        self.TICKET_PREFIXES = [
            "GerenciarPainelTicket", "CriarTicket", "GerenciarTicket_", "ApagarTicket_", 
            "EditarMsgTicket_", "HorarioTicket_", "IACfg_", "GerenciarCategoriasTicket_", 
            "EnviarTicket_", "SincronizarTicket_", "EditContent_", "ClearContent_", 
            "EditEmbed_", "ResetEmbed_", "EditFile_", "ClearFile_", "ImportJson_", 
            "EmbEdit_", "EmbField_", "EmbClear_", "Horario_Dia_", "Horario_Cat_Dia_",
            "Horario_Override_", "IAToggle_", "IAPrompt_", "IAModel_", "IATemp_", 
            "CriarCategoria_", "EditarCategoria_", "ApagarCategoria_", "HorarioCategoria_",
            "ApagarTicketAberto_", "StaffPainel_", "Transcript_Open_", "CloseTranscript_", 
            "SummarizeAI_", "GerenciarTicket", "GerenciarSingleCategoria_", "AbrirCategoriaDropdown_",
            "SelecionarCanalTicket_", "staff_actions_", "IAModelSelect_"
        ]


    def verificar_permissao_staff(self, member: disnake.Member) -> bool:
        try:
            cargos = safe_load_json("Database/Server/cargos.json")
            suporte_id = cargos.get("suporte")
            if not suporte_id: return False
            return any(str(role.id) == str(suporte_id) for role in member.roles)
        except Exception:
            return False

    @commands.Cog.listener("on_message")
    async def on_ticket_message(self, message: disnake.Message):
        if message.author.bot or not message.guild or not isinstance(message.channel, disnake.Thread): return
        
        tickets_abertos = ObterTicketsAbertos()
        ticket_info, ticket_aberto_id = None, None
        for tid, tinfo in tickets_abertos.items():
            if tinfo.get("server", {}).get("topicID") == message.channel.id:
                ticket_info, ticket_aberto_id = tinfo, tid
                break
        if not ticket_info: return

        if self.verificar_permissao_staff(message.author):
            if not ticket_info.get("ia", {}).get("assumed"):
                ticket_info["ia"]["assumed"] = True
                SalvarTicketsAbertos(tickets_abertos)
                embed = Embed(title="Atendimento Assumido", description=f"{message.author.mention} assumiu este ticket. A IA foi desativada.", color=disnake.Color.orange())
                view = ui.View().add_item(ui.Button(label="Resumir Atendimento", custom_id=f"SummarizeAI_{ticket_aberto_id}", emoji="📋"))
                await message.channel.send(embed=embed, view=view)
            return

        if not ticket_info.get("ia", {}).get("enabled") or ticket_info.get("ia", {}).get("assumed"): return
        
        if ticket_info.get("server", {}).get("userID") == message.author.id:
            async with message.channel.typing():
                client = get_grok_client()
                if not client: return
                try:
                    ticket_config = ObterTicket(ticket_info["ticketID"])
                    ia_config = ticket_config["ia"]
                    history = await message.channel.history(limit=20).flatten()
                    history.reverse()
                    
                    messages_for_api = [{"role": "system", "content": ia_config["prompt"]}]
                    for msg in history:
                        if msg.embeds and "Atendimento Assumido" in msg.embeds[0].title: 
                            messages_for_api = [{"role": "system", "content": ia_config["prompt"]}]
                            continue
                        role = "assistant" if msg.author.id == self.bot.user.id else "user"
                        messages_for_api.append({"role": role, "content": msg.content})
                        
                    chat_completion = await asyncio.to_thread(
                        client.chat.completions.create, 
                        messages=messages_for_api, 
                        model=ia_config["model"], 
                        temperature=ia_config["temperature"]
                    )
                    await message.channel.send(chat_completion.choices[0].message.content)
                except Exception as e: 
                    await message.channel.send(f"Ocorreu um erro com a IA: {e}")

    class RenomearTicketModal(ui.Modal):
        def __init__(self, thread: disnake.Thread):
            self.thread = thread
            partes_nome = thread.name.split('・')
            self.sufixo = ""
            if len(partes_nome) >= 3:
                self.sufixo = f"・{partes_nome[-2].strip()}・{partes_nome[-1].strip()}"
            super().__init__(title="Renomear Ticket", components=[
                ui.TextInput(label="Novo nome do Ticket", custom_id="novo_nome", style=TextInputStyle.short, placeholder="Digite o novo título aqui...", max_length=50)
            ])
        async def callback(self, inter: ModalInteraction):
            novo_nome_canal = f"{inter.text_values['novo_nome'].strip()}{self.sufixo}"
            await inter.response.defer(ephemeral=True)
            try: 
                await self.thread.edit(name=novo_nome_canal)
                await inter.edit_original_response(f"{positivo} Ticket renomeado para: `{novo_nome_canal}`")
            except Exception as e: 
                await inter.edit_original_response(f"{negativo} Não foi possível renomear o ticket. Erro: {e}")

    @commands.Cog.listener("on_button_click")
    async def TicketButtonListener(self, inter: MessageInteraction):
        cid = inter.component.custom_id
        
        # --- CLÁUSULA DE GUARDA ---
        if not any(cid.startswith(p) for p in self.TICKET_PREFIXES):
            return
            
        # --- VERIFICAÇÃO DE PERMISSÃO PARA O PAINEL PRINCIPAL ---
        if cid == "GerenciarPainelTicket":
            if not self.bot.verificar_permissao(inter.author.id, tipo="panel", nome_permissao="GerenciarPainelTicket"):
                try:
                    await inter.response.send_message(f"{negativo} Você não tem permissão para acessar o painel de tickets.", ephemeral=True)
                except disnake.errors.HTTPException:
                    pass
                return

        # --- LÓGICA DE MODAIS E RESPOSTAS EFÊMERAS (retornos imediatos) ---
        if cid == "CriarTicket": 
            return await inter.response.send_modal(Ticket.CriarTicket())
        if cid.startswith("EditContent_"): 
            return await inter.response.send_modal(Ticket.Edicao.SetContentModal(cid.split("_")[1]))
        if cid.startswith("EditFile_"): 
            return await inter.response.send_modal(Ticket.Edicao.SetFileModal(cid.split("_")[1]))
        if cid.startswith("ImportJson_"): 
            return await inter.response.send_modal(Ticket.Edicao.ImportJsonModal(cid.split("_")[1]))
        if cid.startswith("EmbEdit_Title_"): 
            return await inter.response.send_modal(Ticket.Edicao.Embed.SetTitleModal(cid.split("_")[-1]))
        if cid.startswith("EmbEdit_Desc_"): 
            return await inter.response.send_modal(Ticket.Edicao.Embed.SetDescriptionModal(cid.split("_")[-1]))
        if cid.startswith("EmbEdit_Color_"): 
            return await inter.response.send_modal(Ticket.Edicao.Embed.SetColorModal(cid.split("_")[-1]))
        if cid.startswith("EmbEdit_Author_"): 
            return await inter.response.send_modal(Ticket.Edicao.Embed.SetAuthorModal(cid.split("_")[-1]))
        if cid.startswith("EmbEdit_Footer_"): 
            return await inter.response.send_modal(Ticket.Edicao.Embed.SetFooterModal(cid.split("_")[-1]))
        if cid.startswith("EmbEdit_Image_"): 
            return await inter.response.send_modal(Ticket.Edicao.Embed.SetImageModal(cid.split("_")[-1]))
        if cid.startswith("EmbEdit_Thumb_"): 
            return await inter.response.send_modal(Ticket.Edicao.Embed.SetThumbnailModal(cid.split("_")[-1]))
        if cid.startswith("EmbField_Add_"): 
            return await inter.response.send_modal(Ticket.Edicao.Embed.FieldModal(cid.split("_")[-1]))
        if cid.startswith("EmbField_Edit_"):
            parts = cid.split("_")
            tid, index = parts[-2], int(parts[-1])
            return await inter.response.send_modal(Ticket.Edicao.Embed.FieldModal(tid, index))
        if cid.startswith("IAPrompt_"): 
            tid = cid.split("_")[1]; return await inter.response.send_modal(Ticket.IA.SetPromptModal(tid, ObterTicket(tid)["ia"]["prompt"]))
        if cid.startswith("IATemp_"): 
            tid = cid.split("_")[1]; return await inter.response.send_modal(Ticket.IA.SetTempModal(tid, ObterTicket(tid)["ia"]["temperature"]))
        if cid.startswith("CriarCategoria_"): 
            return await inter.response.send_modal(Ticket.Categorias.CriarCategoria(cid.split("_")[-1]))
        if cid.startswith("EditarCategoria_"): 
            _, tid, catid = cid.split("_", 2); return await inter.response.send_modal(Ticket.Categorias.EditarCategoria(tid, catid))
        if cid.startswith("Horario_Dia_"): 
            parts = cid.split("_"); tid, day = parts[2], parts[3]; return await inter.response.send_modal(Ticket.Horario.ConfigurarDiaModal(tid, day))
        if cid.startswith("Horario_Cat_Dia_"): 
            parts = cid.split("_"); tid, catid, day = parts[3], parts[4], parts[5]; return await inter.response.send_modal(Ticket.Horario.ConfigurarDiaModal(tid, day, catid))
        if cid.startswith("EnviarTicket_"):
            tid = cid.split("_")[1]; dropdown = ui.ChannelSelect(custom_id=f"SelecionarCanalTicket_{tid}", channel_types=[ChannelType.text], placeholder="Selecione um canal")
            return await inter.response.send_message(view=build_view_from_components([dropdown]), ephemeral=True)
        if cid.startswith("StaffPainel_"):
            if not self.verificar_permissao_staff(inter.author): return await inter.response.send_message(f"{negativo} Sem permissão.", ephemeral=True)
            tid_aberto = cid.split("_")[1]; options = [SelectOption(label="Renomear Ticket", value=f"renomear_ticket_{tid_aberto}"), SelectOption(label="Criar Call Privada", value=f"criar_call_{tid_aberto}"), SelectOption(label="Lembrar Usuário", value=f"lembrar_usuario_{tid_aberto}")]; select = ui.StringSelect(placeholder="Selecione uma ação...", options=options, custom_id=f"staff_actions_{tid_aberto}")
            return await inter.response.send_message(view=build_view_from_components([select]), ephemeral=True)
        if cid.startswith("IAModel_"):
            tid = cid.split("_")[1]; models = ["llama3-8b-8192", "llama3-70b-8192", "mixtral-8x7b-32768", "gemma-7b-it", "gemma2-9b-it"]; options = [SelectOption(label=m, value=m) for m in models]; select = ui.StringSelect(custom_id=f"IAModelSelect_{tid}", placeholder="Selecione um modelo", options=options)
            return await inter.response.send_message(view=build_view_from_components([select]), ephemeral=True)
        
        # --- AÇÕES QUE USAM DEFER E EDITAM A MENSAGEM ORIGINAL ---
        # Se a interação ainda não foi respondida, defer a resposta.
        # Isso evita o erro 40060.
        try:
            await inter.response.defer()
        except disnake.errors.HTTPException:
            pass
        
        if cid == "GerenciarPainelTicket":
            components = ObterPainelTicket(inter)
            await inter.edit_original_message(content="", embed=None, components=components)
        elif cid.startswith("GerenciarTicket_"):
            tid = cid.split("_")[1]; components = await Ticket.ObterPainel(inter, tid)
            await inter.edit_original_message(content="", embed=None, components=components)
        elif cid.startswith("ApagarTicket_"):
            tid = cid.split("_")[1]; await Ticket.ApagarTicket(tid); components = ObterPainelTicket(inter)
            await inter.edit_original_message(content="", embed=None, components=components)
        elif cid.startswith("GerenciarCategoriasTicket_"):
            tid = cid.split("_")[1]; components = await Ticket.Categorias.ObterPainelGerenciarCategorias(tid)
            await inter.edit_original_message(content="", embed=None, components=components)
        elif cid.startswith("ApagarCategoria_"):
            _, tid, catid = cid.split("_", 2); await Ticket.Categorias.ApagarCategoria(tid, catid); components = await Ticket.Categorias.ObterPainelGerenciarCategorias(tid)
            await inter.edit_original_message(content="", embed=None, components=components)
        elif cid.startswith("SincronizarTicket_"):
            tid = cid.split("_")[1]
            
            # Container temporário para mostrar status de sincronização
            temp_container = Container(
                TextDisplay(f"# {carregarAnimado} Sincronizando..."),
                Separator(divider=True)
            )
            await inter.edit_original_message(content="", embed=None, components=[temp_container])
            await SincronizarTicket(inter, tid, self.bot)
        elif cid.startswith("ApagarTicketAberto_"):
            if not self.verificar_permissao_staff(inter.author): await inter.followup.send(f"{negativo} Sem permissão.", ephemeral=True); return
            tid_aberto = cid.split("_")[1]; await fechar_ticket_com_transcript(inter, tid_aberto, self.bot)
        elif cid.startswith("Transcript_Open_"):
            await inter.followup.send(f"{carregarAnimado} Replicando transcript...", ephemeral=True)
            tid_aberto = cid.split("_")[1];
            caminho_html = f"Database/Tickets/transcripts/{inter.channel.id}.html"
            if not os.path.exists(caminho_html): 
                container = Container(TextDisplay(f"# {negativo} Arquivo de transcript não encontrado"))
                await inter.edit_original_message(content="", embed=None, components=[container])
                return
            try:
                channel_name = f"transcript-{tid_aberto[:8]}"; temp_chan = await inter.guild.create_text_channel(channel_name); webhook = await temp_chan.create_webhook(name="TranscriptReplicator")
                with open(caminho_html, 'r', encoding='utf-8') as fh: data = fh.read()
                pattern = r'<div class="mensagem"><span class="hora">\[(.*?)\]</span> <span class="autor">(.*?):</span> <span class="conteudo">(.*?)</span></div>'
                matches = re.findall(pattern, data, flags=re.S)
                for _, autor, conteudo in matches:
                    conteudo_decodificado = disnake.utils.escape_mentions(re.sub('<[^<]+?>', '', conteudo))
                    for part in [conteudo_decodificado[i:i+1950] for i in range(0, len(conteudo_decodificado), 1950)]:
                        await webhook.send(content=part, username=autor.strip())
                view_trans = ui.View(timeout=None); view_trans.add_item(ui.Button(label="Fechar Transcript", custom_id=f"CloseTranscript_{temp_chan.id}", style=ButtonStyle.red))
                await temp_chan.send(f"Transcript de `{tid_aberto}`. Este canal é temporário.", view=view_trans)
                # Container para mostrar sucesso
                success_container = Container(
                    TextDisplay(f"# {positivo} Transcript replicado em {temp_chan.mention}"),
                    Separator(divider=True)
                )
                await inter.edit_original_message(content="", embed=None, components=[success_container])
            except Exception as e:
                # Container para mostrar erro
                error_container = Container(
                    TextDisplay(f"# {negativo} Erro ao criar transcript: {e}"),
                    Separator(divider=True)
                )
                await inter.edit_original_message(content="", embed=None, components=[error_container])
        elif cid.startswith("CloseTranscript_"):
            chanid = int(cid.split("_")[1]); chan = inter.guild.get_channel(chanid)
            if chan: 
                await chan.delete()
                container = Container(TextDisplay(f"# {positivo} Canal de transcript fechado"))
                await inter.edit_original_message(content="", embed=None, components=[container])
            else: 
                container = Container(TextDisplay(f"# {negativo} Canal não encontrado"))
                await inter.edit_original_message(content="", embed=None, components=[container])
        elif cid.startswith("EditarMsgTicket_"): await Ticket.Edicao.ObterPainelPrincipal(inter, cid.split("_")[1])
        elif cid.startswith("ClearContent_"): tid = cid.split("_")[1]; db=ObterDatabase(); db[tid]["message_config"]["content"] = None; SalvarDatabase(db); await Ticket.Edicao.ObterPainelPrincipal(inter, tid, f"{positivo} Conteúdo limpo!")
        elif cid.startswith("ResetEmbed_"): tid = cid.split("_")[1]; db=ObterDatabase(); db[tid]["message_config"]["embed"] = {"title": None, "description": None, "color": None, "author": None, "footer": None, "image": None, "thumbnail": None, "timestamp": False, "fields": []}; SalvarDatabase(db); await Ticket.Edicao.ObterPainelPrincipal(inter, tid, f"{positivo} Embed resetado!")
        elif cid.startswith("EditEmbed_"): await Ticket.Edicao.Embed.ObterPainelConfigEmbed(inter, cid.split("_")[-1])
        elif cid.startswith("ClearFile_"): tid = cid.split("_")[1]; db=ObterDatabase(); db[tid]["message_config"]["file_url"] = None; SalvarDatabase(db); await Ticket.Edicao.ObterPainelPrincipal(inter, tid, f"{positivo} Arquivo limpo!")
        elif cid.startswith("EmbField_Remove_"):
            parts = cid.split("_"); tid, index = parts[-2], int(parts[-1])
            db = ObterDatabase()
            if tid in db and 0 <= index < len(db[tid]["message_config"]["embed"]["fields"]):
                db[tid]["message_config"]["embed"]["fields"].pop(index)
                SalvarDatabase(db)
            await Ticket.Edicao.Embed.ObterPainelFields(inter, tid)
        elif cid.startswith("EmbEdit_"):
            parts = cid.split("_"); part, tid = parts[1], parts[-1]
            if part == "Timestamp": db=ObterDatabase(); db[tid]["message_config"]["embed"]["timestamp"] = not db[tid]["message_config"]["embed"]["timestamp"]; SalvarDatabase(db); await Ticket.Edicao.Embed.ObterPainelConfigEmbed(inter, tid)
            elif part == "Fields": await Ticket.Edicao.Embed.ObterPainelFields(inter, tid)
            elif part == "Clear": components = Ticket.Edicao.Embed.ClearEmbedView(tid); await inter.edit_original_message(content="", embed=None, components=components)
        elif cid.startswith("HorarioTicket_"): await Ticket.Horario.ObterPainelHorario(inter, cid.split("_")[-1])
        elif cid.startswith("HorarioCategoria_"): _, tid, catid = cid.split("_", 2); await Ticket.Horario.ObterPainelHorario(inter, tid, catid)
        elif cid.startswith("Horario_Override_"): 
            _, _, tid, catid = cid.split("_", 3); db=ObterDatabase(); db[tid]["categorias"][catid]["schedule"]["override"] = not db[tid]["categorias"][catid]["schedule"]["override"]; SalvarDatabase(db); await Ticket.Horario.ObterPainelHorario(inter, tid, catid, f"{positivo} Status de sobrescrita alterado!")
        elif cid.startswith("IACfg_"): tid = cid.split("_")[1]; components = await Ticket.IA.ObterPainelIA(inter, tid); await inter.edit_original_message(content="", embed=None, components=components)
        elif cid.startswith("IAToggle_"): tid = cid.split("_")[1]; db=ObterDatabase(); db[tid]["ia"]["enabled"] = not db[tid]["ia"].get("enabled", False); SalvarDatabase(db); components = await Ticket.IA.ObterPainelIA(inter, tid); await inter.edit_original_message(content="", embed=None, components=components)
        elif cid.startswith("SummarizeAI_"):
            # Container temporário para mostrar status de geração
            temp_container = Container(
                TextDisplay(f"# {carregarAnimado} Gerando resumo..."),
                Separator(divider=True)
            )
            await inter.edit_original_message(content="", embed=None, components=[temp_container])
            tid_aberto = cid.split("_")[1]; history = await inter.channel.history(limit=100).flatten(); history.reverse(); conversation = ""
            for msg in history:
                if msg.embeds and "Atendimento Assumido" in msg.embeds[0].title: break
                conversation += f"{msg.author.display_name}: {msg.content}\n"
            client = get_grok_client()
            if not client or not conversation.strip(): 
                container = Container(TextDisplay("# Sem conversa para resumir ou IA não configurada"))
                await inter.edit_original_message(content="", embed=None, components=[container])
                return
            try:
                prompt = f"Resuma a seguinte conversa de um ticket de suporte em português, em terceira pessoa e de forma concisa:\n\n{conversation}"; chat_completion = await asyncio.to_thread(client.chat.completions.create, messages=[{"role": "user", "content": prompt}], model="llama3-8b-8192")
                container = Container(
                    TextDisplay(f"# 📋 Resumo do Atendimento\n{chat_completion.choices[0].message.content}")
                )
                await inter.edit_original_message(content="", embed=None, components=[container])
            except Exception as e: 
                container = Container(TextDisplay(f"# Erro ao gerar resumo\n{str(e)}"))
                await inter.edit_original_message(content="", embed=None, components=[container])

    @commands.Cog.listener("on_dropdown")
    async def TicketDropdownListener(self, inter: MessageInteraction):
        cid = inter.component.custom_id
        
        # --- CLÁUSULA DE GUARDA ---
        if not any(cid.startswith(p) for p in self.TICKET_PREFIXES):
            return

        values = inter.values
        
        # --- AÇÕES ESPECÍFICAS QUE NÃO PRECISAM DE DEFER ---
        if cid.startswith("AbrirCategoriaDropdown_"):
            tid = cid.split("_")[1]
            catid = values[0]
            await Abertura.AbrirTicket(inter, tid, catid)
            return
            
        if cid.startswith("staff_actions_"):
            val = values[0]
            if val.startswith("renomear_ticket_"):
                await inter.response.send_modal(self.RenomearTicketModal(inter.channel))
                return

        await inter.response.defer()

        if cid == "GerenciarTicket":
            if values[0] == "placeholder": return
            tid = values[0]; components = await Ticket.ObterPainel(inter, tid)
            await inter.edit_original_message(content="", embed=None, components=components)
        elif cid.startswith("GerenciarSingleCategoria_"):
            if values[0] == "placeholder": return
            tid = cid.split("_")[1]; catid = values[0]; components = await Ticket.Categorias.ObterPainelCategoria(tid, catid)
            await inter.edit_original_message(content="", embed=None, components=components)
        elif cid.startswith("SelecionarCanalTicket_"):
            tid = cid.split("_")[1]; await Ticket.EnviarMensagem(self.bot, inter, tid)
        elif cid.startswith("staff_actions_"):
            val = values[0]; tid_aberto = val.split("_")[-1]; ticket_aberto = ObterTicketAberto(tid_aberto)
            if not ticket_aberto: await inter.followup.send(f"{negativo} Ticket não encontrado.", ephemeral=True); return
            
            if val.startswith("criar_call_"):
                autor_ticket = inter.guild.get_member(ticket_aberto["server"]["userID"]); cargos = safe_load_json("Database/Server/cargos.json"); cargo_suporte = inter.guild.get_role(int(cargos["suporte"]))
                if not autor_ticket or not cargo_suporte: 
                    container = Container(TextDisplay(f"# {negativo} Autor ou cargo de suporte não encontrado"))
                    await inter.edit_original_message(content="", embed=None, components=[container])
                    return
                overwrites = {inter.guild.default_role: PermissionOverwrite(view_channel=False), autor_ticket: PermissionOverwrite(view_channel=True, connect=True), cargo_suporte: PermissionOverwrite(view_channel=True, connect=True, manage_channels=True)}
                try:
                    cat_call = disnake.utils.get(inter.guild.categories, name="Calls Tickets") or await inter.guild.create_category("Calls Tickets", overwrites={inter.guild.default_role: PermissionOverwrite(view_channel=False)})
                    vc = await inter.guild.create_voice_channel(f"Call-{autor_ticket.name}", category=cat_call, overwrites=overwrites)
                    container = Container(TextDisplay(f"# {positivo} Canal de voz criado\n{vc.mention}"))
                    await inter.edit_original_message(content="", embed=None, components=[container])
                    await inter.channel.send(f"📞 Canal de voz privado {vc.mention} criado.")
                except Exception as e: 
                    container = Container(TextDisplay(f"# {negativo} Erro ao criar canal\n{str(e)}"))
                    await inter.edit_original_message(content="", embed=None, components=[container])
            elif val.startswith("lembrar_usuario_"):
                try:
                    user = await self.bot.fetch_user(int(ticket_aberto["server"]["userID"])); await user.send(f"{user.mention}, seu ticket aguarda resposta.", view=build_view_from_components([ui.Button(label="Ir para o ticket", url=inter.channel.jump_url)]))
                    container = Container(TextDisplay(f"# {positivo} Usuário lembrado"))
                    await inter.edit_original_message(content="", embed=None, components=[container])
                except: 
                    container = Container(TextDisplay(f"# {negativo} Não foi possível contatar o usuário"))
                    await inter.edit_original_message(content="", embed=None, components=[container])
        elif cid.startswith("EmbField_Select_"):
            tid = cid.split("_")[-1]; index = int(values[0]); ticket = ObterTicket(tid); field = ticket["message_config"]["embed"]["fields"][index]
            
            texto_container = f"""# 📝 Gerenciando Field
**Nome:** {field['name']}
**Valor:** {field.get('value', 'Não definido')}
**Inline:** {'Sim' if field.get('inline', False) else 'Não'}"""
            
            container = Container(
                TextDisplay(texto_container),
                Separator(divider=True),
                ActionRow(
                    ui.Button(label="Editar este Field", custom_id=f"EmbField_Edit_{tid}_{index}", style=ButtonStyle.blurple),
                    ui.Button(label="Remover este Field", custom_id=f"EmbField_Remove_{tid}_{index}", style=ButtonStyle.red),
                    ui.Button(label="Voltar", emoji=voltar, custom_id=f"EmbEdit_Fields_{tid}")
                )
            )
            
            await inter.edit_original_message(content="", embed=None, components=[container])
        elif cid.startswith("EmbClear_Select_"):
            tid = cid.split("_")[-1]; db = ObterDatabase()
            for part in values:
                if part in db[tid]["message_config"]["embed"]:
                    if part == "fields":
                        db[tid]["message_config"]["embed"][part] = []
                    elif part == "timestamp":
                        db[tid]["message_config"]["embed"][part] = False
                    else:
                        db[tid]["message_config"]["embed"][part] = None
            SalvarDatabase(db); await Ticket.Edicao.Embed.ObterPainelConfigEmbed(inter, tid)
        elif cid.startswith("IAModelSelect_"):
            tid, model = cid.split("_")[1], values[0]; db = ObterDatabase(); db[tid]["ia"]["model"] = model; SalvarDatabase(db)
            await inter.followup.send(f"{positivo} Modelo definido como `{model}`.", ephemeral=True)
            try:
                original_message = await inter.original_message()
                components = await Ticket.IA.ObterPainelIA(inter, tid)
                await original_message.edit(content="", embed=None, components=components)
            except disnake.NotFound:
                pass

def setup(bot: commands.Bot):
    bot.add_cog(TicketCommand(bot))