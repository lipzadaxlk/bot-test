import disnake
import json
from disnake.ext import commands
from disnake import ChannelType
from datetime import datetime
from typing import Optional
from Functions.CarregarEmojis import *

# --- GERENCIAMENTO DE DATABASE ---
DB_TERMOS_PATH = "Database/Vendas/configuracao.json"

def obter_db_termos():
    try:
        with open(DB_TERMOS_PATH, "r", encoding='utf-8') as f:
            full_db = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        full_db = {}

    if "termos_manual" not in full_db:
        full_db["termos_manual"] = {
            "content": None,
            "embed": {
                "title": None,
                "description": None,
                "banner_url": None,
                "thumbnail_url": None,
                "color": None
            }
        }
        salvar_db_termos(full_db["termos_manual"])

    return full_db["termos_manual"]

def salvar_db_termos(data_termos):
    try:
        with open(DB_TERMOS_PATH, "r", encoding='utf-8') as f:
            full_db = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        full_db = {}

    full_db["termos_manual"] = data_termos
    
    with open(DB_TERMOS_PATH, "w", encoding='utf-8') as f:
        json.dump(full_db, f, indent=4, ensure_ascii=False)

# --- MODAIS ---
class DiscohookImportModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="Código JSON do DiscoHook",
                custom_id="discohook_json_input",
                style=disnake.TextInputStyle.paragraph,
                placeholder="Cole aqui o código JSON gerado pelo DiscoHook...",
                required=True
            )
        ]
        super().__init__(title="Importar JSON do DiscoHook", custom_id="discohook_modal", components=components)

class ConfigurarConteudoModal(disnake.ui.Modal):
    def __init__(self, current_content: Optional[str] = None):
        components = [
            disnake.ui.TextInput(
                label="Conteúdo da Mensagem",
                custom_id="manual_content_input",
                style=disnake.TextInputStyle.paragraph,
                placeholder="Digite o conteúdo de texto da sua mensagem de termos...",
                value=current_content,
                required=False,
                max_length=2000
            )
        ]
        super().__init__(title="Configurar Conteúdo Manual", custom_id="manual_content_modal", components=components)

class ConfigurarEmbedModal(disnake.ui.Modal):
    def __init__(self, embed_data: dict):
        components = [
            disnake.ui.TextInput(label="Título do Embed", custom_id="embed_title", value=embed_data.get("title"), required=False, max_length=256),
            disnake.ui.TextInput(label="Descrição do Embed", custom_id="embed_desc", value=embed_data.get("description"), style=disnake.TextInputStyle.paragraph, required=False, max_length=2000),
            disnake.ui.TextInput(label="URL do Banner (Imagem Principal)", custom_id="embed_banner", value=embed_data.get("banner_url"), required=False),
            disnake.ui.TextInput(label="URL da Thumbnail (Imagem Menor)", custom_id="embed_thumb", value=embed_data.get("thumbnail_url"), required=False),
            disnake.ui.TextInput(label="Cor em HEX (ex: #FFFFFF)", custom_id="embed_color", value=embed_data.get("color"), required=False, max_length=7),
        ]
        super().__init__(title="Configurar Embed Manual", custom_id="manual_embed_modal", components=components)

# --- GERADOR DE PAINÉIS ---
class PaineisTermos:
    @staticmethod
    def obter_painel_inicial(inter: disnake.Interaction):
        embed = disnake.Embed(
            title=" Gerenciar Termos",
            description="Escolha como deseja configurar a mensagem de termos da sua Loja.",
            color=0x2b2d31
        )
        view = disnake.ui.View(timeout=None)
        view.add_item(disnake.ui.Button(label="Importar via DiscoHook", custom_id="termos_escolha_discohook", emoji=import1))
        view.add_item(disnake.ui.Button(label="Configurar Manualmente", custom_id="termos_escolha_manual", emoji=text))
        view.add_item(disnake.ui.Button(label="Voltar", custom_id="GerenciarPainelVendas", emoji=voltar))
        return embed, view

    @staticmethod
    def obter_painel_discohook(inter: disnake.Interaction):
        embed = disnake.Embed(
            title="Importar via DiscoHook",
            description="Use os botões abaixo para criar e importar sua mensagem de termos.",
            color=0x5865F2
        )
        embed.add_field(name="Como usar?", value='>>> 1. Clique em **"DiscoHook"** para abrir o site.\n2. Crie sua mensagem.\n3. Vá na aba "JSON Data Editor" e copie o código.\n4. Volte e clique em **"Importar"** para colar o código.', inline=False)
        
        view = disnake.ui.View(timeout=None)
        view.add_item(disnake.ui.Button(label="DiscoHook", url="https://discohook.org/", style=disnake.ButtonStyle.link))
        view.add_item(disnake.ui.Button(label="Tutorial", url="https://discohook.org/faq", style=disnake.ButtonStyle.link))
        view.add_item(disnake.ui.Button(label="Importar", custom_id="termos_discohook_importar", style=disnake.ButtonStyle.green, emoji=import1))
        view.add_item(disnake.ui.Button(label="Voltar", custom_id="GerenciarTermos", style=disnake.ButtonStyle.gray, emoji=voltar))
        return embed, view

    @staticmethod
    def obter_painel_manual(inter: disnake.Interaction):
        db = obter_db_termos()
        embed = disnake.Embed(
            title="Configuração Manual de Termos",
            color=0x2b2d31
        )
        embed.add_field(name="Conteúdo de Texto", value=f"```\n{db.get('content') or 'Não definido'}\n```", inline=False)
        
        embed_data = db.get("embed", {})
        embed_status = f"""
        **Título:** `{embed_data.get('title') or 'Não Definido'}`
        **Descrição:** `{'Sim' if embed_data.get('description') else 'Não Definido'}`
        **Banner:** `{'Sim' if embed_data.get('banner_url') else 'Não Definido'}`
        **Thumbnail:** `{'Sim' if embed_data.get('thumbnail_url') else 'Não Definido'}`
        **Cor:** `{embed_data.get('color') or 'Padrão'}`
        """
        embed.add_field(name="Configuração do Embed", value=embed_status, inline=False)

        view = disnake.ui.View(timeout=None)
        view.add_item(disnake.ui.Button(label="Configurar Content", custom_id="termos_manual_config_content", emoji=editar))
        view.add_item(disnake.ui.Button(custom_id="termos_manual_limpar_content", emoji=apagar, style=disnake.ButtonStyle.red, disabled=db.get('content') is None))
        view.add_item(disnake.ui.Button(label="Configurar Embed", custom_id="termos_manual_config_embed", emoji=embedE))
        view.add_item(disnake.ui.Button(custom_id="termos_manual_limpar_embed", emoji=apagar, style=disnake.ButtonStyle.red, disabled=all(v is None for v in embed_data.values())))
        view.add_item(disnake.ui.Button(label="Preview", custom_id="termos_manual_preview", style=disnake.ButtonStyle.blurple, emoji=preview))
        view.add_item(disnake.ui.Button(label="Voltar", custom_id="GerenciarTermos", style=disnake.ButtonStyle.gray, emoji=voltar))
        
        return embed, view

# --- COG E LISTENERS ---
class TermosCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.temp_json_data = {}

    async def _handle_interaction_safely(self, inter: disnake.MessageInteraction, callback):
        """
        Função auxiliar para lidar com interações de forma segura
        """
        try:
            await callback()
        except disnake.errors.NotFound:
            # Webhook expirou, tentar com followup
            print(f"Webhook expirado para interação {inter.id}, usando fallback")
            try:
                if not inter.response.is_done():
                    await inter.response.send_message(
                        "Esta interação expirou. Por favor, execute o comando novamente.",
                        ephemeral=True
                    )
                else:
                    await inter.followup.send(
                        "Esta interação expirou. Por favor, execute o comando novamente.",
                        ephemeral=True
                    )
            except Exception as e:
                print(f"Erro no fallback de interação: {e}")
        except disnake.errors.InteractionNotResponded:
            # Interação não foi respondida
            try:
                embed, view = PaineisTermos.obter_painel_inicial(inter)
                await inter.response.send_message(
                    content="Selecione a forma que deseja configurar os termos da sua loja.",
                    embed=embed,
                    view=view
                )
            except Exception as e:
                print(f"Erro ao responder interação não respondida: {e}")
        except Exception as e:
            print(f"Erro no listener de termos: {e}")
            # Tentar responder com erro genérico
            try:
                if not inter.response.is_done():
                    await inter.response.send_message(
                        "Ocorreu um erro. Tente novamente.",
                        ephemeral=True
                    )
                else:
                    await inter.followup.send(
                        "Ocorreu um erro. Tente novamente.",
                        ephemeral=True
                    )
            except:
                pass

    @commands.Cog.listener("on_button_click")
    async def termos_listener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id

        if custom_id == "GerenciarTermos":
            async def callback():
                embed, view = PaineisTermos.obter_painel_inicial(inter)
                if not inter.response.is_done():
                    await inter.response.edit_message(
                        content="Selecione a forma que deseja configurar os termos da sua loja.",
                        embed=embed,
                        view=view
                    )
                else:
                    await inter.edit_original_message(
                        content="Selecione a forma que deseja configurar os termos da sua loja.",
                        embed=embed,
                        view=view
                    )
            await self._handle_interaction_safely(inter, callback)
        
        elif custom_id == "termos_escolha_discohook":
            async def callback():
                embed, view = PaineisTermos.obter_painel_discohook(inter)
                if not inter.response.is_done():
                    await inter.response.edit_message(content=None, embed=embed, view=view)
                else:
                    await inter.edit_original_message(content=None, embed=embed, view=view)
            await self._handle_interaction_safely(inter, callback)

        elif custom_id == "termos_escolha_manual":
            async def callback():
                embed, view = PaineisTermos.obter_painel_manual(inter)
                if not inter.response.is_done():
                    await inter.response.edit_message(content=None, embed=embed, view=view)
                else:
                    await inter.edit_original_message(content=None, embed=embed, view=view)
            await self._handle_interaction_safely(inter, callback)

        elif custom_id == "termos_discohook_importar":
            try:
                await inter.response.send_modal(DiscohookImportModal())
            except Exception as e:
                print(f"Erro ao abrir modal: {e}")
        
        elif custom_id == "termos_manual_config_content":
            try:
                db = obter_db_termos()
                await inter.response.send_modal(ConfigurarConteudoModal(db.get("content")))
            except Exception as e:
                print(f"Erro ao abrir modal de conteúdo: {e}")
        
        elif custom_id == "termos_manual_limpar_content":
            async def callback():
                db = obter_db_termos()
                db["content"] = None
                salvar_db_termos(db)
                embed, view = PaineisTermos.obter_painel_manual(inter)
                if not inter.response.is_done():
                    await inter.response.edit_message(embed=embed, view=view)
                else:
                    await inter.edit_original_message(embed=embed, view=view)
            await self._handle_interaction_safely(inter, callback)

        elif custom_id == "termos_manual_config_embed":
            try:
                db = obter_db_termos()
                await inter.response.send_modal(ConfigurarEmbedModal(db.get("embed", {})))
            except Exception as e:
                print(f"Erro ao abrir modal de embed: {e}")
        
        elif custom_id == "termos_manual_limpar_embed":
            async def callback():
                db = obter_db_termos()
                db["embed"] = { "title": None, "description": None, "banner_url": None, "thumbnail_url": None, "color": None }
                salvar_db_termos(db)
                embed, view = PaineisTermos.obter_painel_manual(inter)
                if not inter.response.is_done():
                    await inter.response.edit_message(embed=embed, view=view)
                else:
                    await inter.edit_original_message(embed=embed, view=view)
            await self._handle_interaction_safely(inter, callback)
        
        elif custom_id == "termos_manual_preview":
            try:
                db = obter_db_termos()
                content = db.get("content")
                embed_data = db.get("embed", {})
                
                if not content and all(v is None for v in embed_data.values()):
                    await inter.response.send_message("Nada configurado para pré-visualizar!", ephemeral=True)
                    return

                preview_embed = None
                if not all(v is None for v in embed_data.values()):
                    try:
                        color_hex = embed_data.get('color')
                        color_int = disnake.Color.default()
                        
                        if color_hex:
                            # Verifica se já é um inteiro
                            if isinstance(color_hex, int):
                                color_int = color_hex
                            # Se for string, converte de hex para int
                            elif isinstance(color_hex, str):
                                # Remove # se presente e converte
                                color_hex_clean = color_hex.lstrip('#')
                                color_int = int(color_hex_clean, 16)
                        
                        preview_embed = disnake.Embed(
                            title=embed_data.get('title'),
                            description=embed_data.get('description'),
                            color=color_int
                        )
                        if embed_data.get('banner_url'): 
                            preview_embed.set_image(url=embed_data['banner_url'])
                        if embed_data.get('thumbnail_url'): 
                            preview_embed.set_thumbnail(url=embed_data['thumbnail_url'])
                            
                    except (ValueError, TypeError) as e:
                        await inter.response.send_message(f"Erro na configuração do embed: {str(e)}\nVerifique se a cor está no formato correto (ex: #FFFFFF).", ephemeral=True)
                        return
                
                await inter.response.send_message(
                    content=content,
                    embed=preview_embed,
                    ephemeral=True
                )
            except Exception as e:
                print(f"Erro no preview: {e}")
                try:
                    if not inter.response.is_done():
                        await inter.response.send_message(f"Erro ao gerar preview: {str(e)}", ephemeral=True)
                    else:
                        await inter.followup.send(f"Erro ao gerar preview: {str(e)}", ephemeral=True)
                except:
                    pass

    @commands.Cog.listener("on_modal_submit")
    async def termos_modal_listener(self, inter: disnake.ModalInteraction):
        custom_id = inter.custom_id

        if custom_id == "discohook_modal":
            json_str = inter.text_values["discohook_json_input"]
            try:
                data = json.loads(json_str)
                if not data or (not data.get("content") and not data.get("embeds")):
                    await inter.response.send_message(f"{negativo} O JSON fornecido é inválido ou não contém 'content' ou 'embeds'.", ephemeral=True)
                    return
                
                self.temp_json_data[inter.author.id] = data
                
                select = disnake.ui.ChannelSelect(
                    custom_id="termos_selecionar_canal",
                    placeholder="Selecione um canal para enviar...",
                    channel_types=[ChannelType.text]
                )
                await inter.response.send_message(
                    f"{positivo} JSON válido! Selecione o canal para enviar a mensagem:",
                    components=[select],
                    ephemeral=True
                )

            except json.JSONDecodeError:
                await inter.response.send_message(f"{negativo} Ocorreu um erro ao processar o código JSON. Verifique a formatação.", ephemeral=True)
            except Exception as e:
                print(f"Erro no modal discohook: {e}")
                await inter.response.send_message("Ocorreu um erro ao processar o JSON.", ephemeral=True)
        
        elif custom_id == "manual_content_modal":
            try:
                content = inter.text_values["manual_content_input"]
                db = obter_db_termos()
                db["content"] = content if content else None
                salvar_db_termos(db)
                embed, view = PaineisTermos.obter_painel_manual(inter)
                await inter.response.edit_message(embed=embed, view=view)
            except Exception as e:
                print(f"Erro no modal de conteúdo: {e}")
                await inter.response.send_message("Erro ao salvar conteúdo.", ephemeral=True)

        elif custom_id == "manual_embed_modal":
            try:
                db = obter_db_termos()
                db["embed"]["title"] = inter.text_values["embed_title"] or None
                db["embed"]["description"] = inter.text_values["embed_desc"] or None
                db["embed"]["banner_url"] = inter.text_values["embed_banner"] or None
                db["embed"]["thumbnail_url"] = inter.text_values["embed_thumb"] or None
                db["embed"]["color"] = inter.text_values["embed_color"] or None
                salvar_db_termos(db)
                embed, view = PaineisTermos.obter_painel_manual(inter)
                await inter.response.edit_message(embed=embed, view=view)
            except Exception as e:
                print(f"Erro no modal de embed: {e}")
                await inter.response.send_message("Erro ao salvar configuração do embed.", ephemeral=True)

    @commands.Cog.listener("on_dropdown")
    async def termos_dropdown_listener(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "termos_selecionar_canal":
            try:
                channel_id = int(inter.values[0])
                channel = inter.guild.get_channel(channel_id)

                if not channel:
                    await inter.response.edit_message(content=f"{negativo} Canal não encontrado.", view=None)
                    return

                user_data = self.temp_json_data.get(inter.author.id)
                if not user_data:
                    await inter.response.edit_message(content=f"{negativo} Sessão expirada. Por favor, importe o código novamente.", view=None)
                    return

                # Salvar no JSON
                db = obter_db_termos()
                db["content"] = user_data.get("content")
                
                if user_data.get("embeds"):
                    embed_data = user_data["embeds"][0]
                    db["embed"] = {
                        "title": embed_data.get("title"),
                        "description": embed_data.get("description"),
                        "banner_url": embed_data.get("image", {}).get("url"),
                        "thumbnail_url": embed_data.get("thumbnail", {}).get("url"),
                        "color": embed_data.get("color")
                    }
                
                salvar_db_termos(db)

                # Enviar mensagem
                try:
                    await channel.send(
                        content=db["content"],
                        embeds=[disnake.Embed.from_dict(e) for e in user_data.get("embeds", [])]
                    )
                    await inter.response.edit_message(
                        content=f"{positivo} Mensagem enviada e configuração salva em {channel.mention}!",
                        view=None
                    )
                except disnake.Forbidden:
                    await inter.response.edit_message(
                        content=f"{negativo} Sem permissão para enviar em {channel.mention}.",
                        view=None
                    )
                except Exception as e:
                    print(f"Erro ao enviar mensagem: {e}")
                    await inter.response.edit_message(
                        content=f"{negativo} Erro ao enviar: {e}",
                        view=None
                    )

                # Limpar dados temporários
                if inter.author.id in self.temp_json_data:
                    del self.temp_json_data[inter.author.id]
                    
            except Exception as e:
                print(f"Erro no dropdown de canal: {e}")
                try:
                    await inter.response.edit_message(
                        content="Erro ao processar seleção de canal.",
                        view=None
                    )
                except:
                    pass

def setup(bot: commands.Bot):
    bot.add_cog(TermosCommand(bot))