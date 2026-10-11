import disnake
from disnake.ext import commands
import json
import os
import asyncio
import random
import requests

try:
    from Functions.CarregarEmojis import *
except ImportError:
    tools, check, voltar, carregarAnimado, negativo, positivo, editar, apagar, preview, arrow, cargo, logs, users = "🛠️", "✅", "↩️", "⚙️", "❌", "👍", "📝", "🗑️", "👀", "➡️", "👤", "📜", "👥"

from Commands.Admin.Plugins.ECloud import API_URL, ObterAuthLocal

CAMINHO_CONFIG = os.path.join("Database", "Vendas", "configuracao.json")

def obter_config_e_garantir_estrutura():
    with open(CAMINHO_CONFIG, "r+", encoding="utf-8") as f:
        config = json.load(f)
        salers_ext = config.setdefault("salers_members", {})
        if "instalado" not in salers_ext: 
            salers_ext["instalado"] = False
        if "sistema_ativo" not in salers_ext: 
            salers_ext["sistema_ativo"] = False
        if "min_membros" not in salers_ext: 
            salers_ext["min_membros"] = 100
        if "valor_por_membro" not in salers_ext: 
            salers_ext["valor_por_membro"] = 0.01
        
        msg_config = salers_ext.setdefault("config_msg", {})
        if "content" not in msg_config: 
            msg_config["content"] = None
        if "embed" not in msg_config: 
            msg_config["embed"] = {"title": "Comprar Membros OAuth2", "description": "Clique no botão abaixo para comprar membros para o seu servidor."}
        if "button" not in msg_config: 
            msg_config["button"] = {"label": "Comprar Membros", "emoji": "👥"}
        
        f.seek(0)
        json.dump(config, f, indent=4)
        f.truncate()
    return config

def salvar_config(data):
    with open(CAMINHO_CONFIG, "w") as f:
        json.dump(data, f, indent=4)

class ModalConfigValor(disnake.ui.Modal):
    def __init__(self):
        config = obter_config_e_garantir_estrutura()["salers_members"]
        components = [
            disnake.ui.TextInput(
                label="Mínimo de Membros para Compra", 
                custom_id="min_membros", 
                value=str(config.get("min_membros", 100))
            ),
            disnake.ui.TextInput(
                label="Valor por Membro (Ex: 0.01)", 
                custom_id="valor_por_membro", 
                value=str(config.get("valor_por_membro", 0.01))
            ),
        ]
        super().__init__(title="Configurar Valores e Mínimos", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)
        try:
            min_membros = int(inter.text_values["min_membros"])
            valor_por_membro = float(inter.text_values["valor_por_membro"])
        except ValueError:
            return await inter.followup.send(f"{negativo} Por favor, insira apenas números válidos.", ephemeral=True)
        
        auth_local = ObterAuthLocal()
        if not auth_local.get("authorization"):
            return await inter.followup.send(f"{negativo} A API eCloud não está configurada.", ephemeral=True)
        
        headers = {"authorization": auth_local["authorization"]}
        try:
            members_response = requests.get(f"{API_URL}members", headers=headers, timeout=5)
            if members_response.status_code == 200:
                membros_disponiveis = int(members_response.json().get("message", 0))
                if min_membros > membros_disponiveis:
                    return await inter.followup.send(f"{negativo} Você não pode definir um mínimo de `{min_membros}`, pois só possui `{membros_disponiveis}` autenticados.", ephemeral=True)
            else:
                return await inter.followup.send(f"{negativo} Não foi possível verificar sua quantidade de membros na API.", ephemeral=True)
        except requests.exceptions.RequestException:
            return await inter.followup.send(f"{negativo} Não foi possível conectar à API eCloud.", ephemeral=True)

        config = obter_config_e_garantir_estrutura()
        config["salers_members"]["min_membros"] = min_membros
        config["salers_members"]["valor_por_membro"] = valor_por_membro
        salvar_config(config)
        await inter.followup.send(f"{positivo} Valores salvos com sucesso!", ephemeral=True)
        embed, components = obter_painel_gerenciar_salers()
        await inter.edit_original_message(embed=embed, components=components)

class ModalEditarAparencia(disnake.ui.Modal):
    def __init__(self, item_type: str):
        self.item_type = item_type
        config = obter_config_e_garantir_estrutura()["salers_members"]["config_msg"]
        
        if item_type == "content":
            super().__init__(
                title="Editar Conteúdo", 
                components=[
                    disnake.ui.TextInput(
                        label="Conteúdo da Mensagem", 
                        custom_id="content", 
                        value=config.get("content", ""), 
                        style=disnake.TextInputStyle.paragraph, 
                        required=False
                    )
                ]
            )
        elif item_type == "embed":
            embed_config = config.get("embed", {})
            cor_hex = embed_config.get("color", "")
            super().__init__(
                title="Configurar Embed", 
                components=[
                    disnake.ui.TextInput(
                        label="Título", 
                        custom_id="title", 
                        value=embed_config.get("title", "")
                    ),
                    disnake.ui.TextInput(
                        label="Descrição", 
                        custom_id="description", 
                        value=embed_config.get("description", ""), 
                        style=disnake.TextInputStyle.paragraph
                    ),
                    disnake.ui.TextInput(
                        label="Cor (HEX: #FFFFFF)", 
                        custom_id="color", 
                        value=cor_hex, 
                        required=False
                    ),
                ]
            )
        elif item_type == "button":
            btn_config = config.get("button", {})
            super().__init__(
                title="Configurar Botão", 
                components=[
                    disnake.ui.TextInput(
                        label="Texto do Botão", 
                        custom_id="label", 
                        value=btn_config.get("label", "")
                    ),
                    disnake.ui.TextInput(
                        label="Emoji do Botão", 
                        custom_id="emoji", 
                        value=btn_config.get("emoji", ""), 
                        required=False
                    )
                ]
            )

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)
        config = obter_config_e_garantir_estrutura()
        msg_config = config["salers_members"]["config_msg"]

        if self.item_type == "content":
            msg_config["content"] = inter.text_values["content"]
        elif self.item_type == "embed":
            embed_config = msg_config.setdefault("embed", {})
            embed_config["title"] = inter.text_values["title"]
            embed_config["description"] = inter.text_values["description"]
            cor = inter.text_values["color"]
            if cor.startswith("#") and len(cor) == 7:
                embed_config["color"] = cor
            else:
                embed_config.pop("color", None)
        elif self.item_type == "button":
            btn_config = msg_config.setdefault("button", {})
            btn_config["label"] = inter.text_values["label"]
            btn_config["emoji"] = inter.text_values["emoji"]

        salvar_config(config)
        await inter.followup.send(f"{positivo} Aparência salva!", ephemeral=True)
        embed, components = obter_painel_configurar_aparencia_salers()
        await inter.edit_original_message(embed=embed, components=components)

def obter_painel_gerenciar_salers():
    config = obter_config_e_garantir_estrutura().get("salers_members", {})
    sistema_ativo = config.get("sistema_ativo", False)
    embed = disnake.Embed(title="Gerenciar Venda de Membros", color=0x3498DB)
    embed.add_field(
        name="Sistema de Vendas", 
        value=f"{positivo} Ativado" if sistema_ativo else f"{negativo} Desativado", 
        inline=False
    )
    embed.add_field(
        name="Configuração de Preço", 
        value=f"Mínimo: `{config.get('min_membros', 0)}`\nPreço/Membro: `R${config.get('valor_por_membro', 0):.2f}`", 
        inline=False
    )
    
    row1 = disnake.ui.ActionRow(
        disnake.ui.Button(
            label="Desativar Sistema" if sistema_ativo else "Ativar Sistema", 
            style=disnake.ButtonStyle.red if sistema_ativo else disnake.ButtonStyle.green, 
            emoji=reload,
            custom_id="salers_admin_toggle_sistema"
        ),
        disnake.ui.Button(
            label="Configurar Aparência", 
            style=disnake.ButtonStyle.secondary, 
            emoji=preview, 
            custom_id="salers_admin_config_aparencia"
        ),
        disnake.ui.Button(
            label="Configurar Valores", 
            style=disnake.ButtonStyle.secondary, 
            emoji=editar, 
            custom_id="salers_admin_config_valor"
        )
    )
    row2 = disnake.ui.ActionRow(
        disnake.ui.Button(
            label="Enviar Painel", 
            style=disnake.ButtonStyle.primary, 
            emoji=arrow, 
            custom_id="salers_admin_enviar_painel", 
            disabled=not sistema_ativo
        ),
        disnake.ui.Button(
            label="Excluir Extensão", 
            style=disnake.ButtonStyle.danger, 
            emoji=apagar, 
            custom_id="salers_admin_excluir_extensao"
        )
    )
    row3 = disnake.ui.ActionRow(
      disnake.ui.Button(
                label="Voltar",
                style=disnake.ButtonStyle.grey,
                custom_id="VoltarParaLoja"
      )
    )
    return embed, [row1, row2, row3]

def obter_painel_configurar_aparencia_salers():
    embed = disnake.Embed(
        title="Configurar Aparência (Venda de Membros)", 
        description="Personalize a mensagem que os usuários verão.", 
        color=0x9B59B6
    )
    config = obter_config_e_garantir_estrutura()["salers_members"]["config_msg"]
    tem_content = bool(config.get("content"))
    tem_embed = bool(config.get("embed") and (config.get("embed").get("title") or config.get("embed").get("description")))
    
    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Editar Conteúdo", 
                custom_id="salers_admin_aparencia_content", 
                emoji=editar
            ),
            disnake.ui.Button(
                
                custom_id="salers_admin_aparencia_limpar_content", 
                emoji=apagar, 
                style=disnake.ButtonStyle.danger, 
                disabled=not tem_content
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Editar Embed", 
                custom_id="salers_admin_aparencia_embed", 
                emoji=editar
            ),
            disnake.ui.Button(
                
                custom_id="salers_admin_aparencia_limpar_embed", 
                emoji=apagar, 
                style=disnake.ButtonStyle.danger, 
                disabled=not tem_embed
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Editar Botão", 
                custom_id="salers_admin_aparencia_button", 
                emoji=editar
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Voltar", 
                emoji=voltar, 
                custom_id="salers_admin_voltar_gerenciar"
            )
        )
    ]
    return embed, components

def obter_painel_instalar_salers():
    """
    Gera um painel com embed e botões para a instalação da extensão de venda de membros.
    """
    
    # Descrição atualizada com formatação Markdown
    nova_descricao = (
        "# Extensão Oficial\n"
        "- Use essa extensão para gerenciar o sistema de vender membros do seu eCloud\n\n"
        "> **Sistema em fase beta, poderá conter erros, e só é possível vender a "
        "quantidade que você tem de verificados no seu eCloud!**"
    )

    embed = disnake.Embed(
        
        description=nova_descricao,
        color=0x2ECC71  # Verde
    )

    # Lista de componentes (botões) organizados em ActionRows
    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Instalar Extensão",
                emoji=check,
                style=disnake.ButtonStyle.success,
                custom_id="salers_admin_instalar_extensao"
            ),
            disnake.ui.Button(
                label="Apresentação",
                style=disnake.ButtonStyle.link,
                url="https://google.com"  # Altere este link se necessário
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Voltar para loja",
                emoji=voltar,
                style=disnake.ButtonStyle.grey,
                custom_id="VoltarParaLoja"
            )
        )
    ]

    return embed, components

class SalersMembersExtension(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def salers_admin_button_listener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        if not custom_id.startswith("salers_admin_"): 
            return
        
        config = obter_config_e_garantir_estrutura()
        
        if custom_id == "salers_admin_instalar_extensao":
            await inter.response.edit_message(
                content=f"{carregarAnimado} Instalando extensão...", 
                embed=None, 
                components=[]
            )
            await asyncio.sleep(3)
            config["salers_members"]["instalado"] = True
            salvar_config(config)
            embed, comps = obter_painel_gerenciar_salers()
            await inter.edit_original_message(
                embed=embed, 
                components=comps,
                content=None
            )
        elif custom_id == "salers_admin_excluir_extensao":
            await inter.response.edit_message(
                content=f"{carregarAnimado} Excluindo extensão...", 
                embed=None, 
                components=[]
            )
            await asyncio.sleep(4)
            config["salers_members"] = {"instalado": False}
            salvar_config(config)
            embed, comps = obter_painel_instalar_salers()
            await inter.edit_original_message(
                embed=embed, 
                content=None,
                components=comps
            )
        elif custom_id == "salers_admin_config_aparencia":
            embed, comps = obter_painel_configurar_aparencia_salers()
            await inter.response.edit_message(embed=None, components=comps)
        elif custom_id == "salers_admin_voltar_gerenciar":
            embed, comps = obter_painel_gerenciar_salers()
            await inter.response.edit_message(embed=embed, components=comps)
        elif custom_id == "salers_admin_aparencia_content": 
            await inter.response.send_modal(ModalEditarAparencia("content"))
        elif custom_id == "salers_admin_aparencia_embed": 
            await inter.response.send_modal(ModalEditarAparencia("embed"))
        elif custom_id == "salers_admin_aparencia_button": 
            await inter.response.send_modal(ModalEditarAparencia("button"))
        elif custom_id == "salers_admin_config_valor": 
            await inter.response.send_modal(ModalConfigValor())
        elif custom_id == "salers_admin_enviar_painel":
            view = disnake.ui.View().add_item(
                disnake.ui.ChannelSelect(
                    custom_id="salers_admin_select_canal_enviar", 
                    placeholder="Selecione o canal para envio"
                )
            )
            await inter.response.send_message("Onde devo enviar o painel?", view=view, ephemeral=True)
        elif custom_id == "salers_admin_aparencia_limpar_content":
            config["salers_members"]["config_msg"]["content"] = None
            salvar_config(config)
            embed, comps = obter_painel_configurar_aparencia_salers()
            await inter.response.edit_message(embed=None, components=comps)
        elif custom_id == "salers_admin_aparencia_limpar_embed":
            config["salers_members"]["config_msg"]["embed"] = {}
            salvar_config(config)
            embed, comps = obter_painel_configurar_aparencia_salers()
            await inter.response.edit_message(embed=None, components=comps)
        elif custom_id == "salers_admin_toggle_sistema":
            config["salers_members"]["sistema_ativo"] = not config["salers_members"].get("sistema_ativo", False)
            salvar_config(config)
            embed, comps = obter_painel_gerenciar_salers()
            await inter.response.edit_message(embed=embed, components=comps)

    @commands.Cog.listener("on_dropdown")
    async def salers_admin_dropdown_listener(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "salers_admin_select_canal_enviar":
            await inter.response.defer(ephemeral=True)
            channel = self.bot.get_channel(int(inter.values[0]))
            if not channel: 
                return await inter.followup.send(f"{negativo} Canal não encontrado.", ephemeral=True)
            
            config = obter_config_e_garantir_estrutura().get("salers_members", {}).get("config_msg", {})
            content = config.get("content")
            embed_data = config.get("embed")
            button_data = config.get("button", {})
            
            embed = disnake.Embed.from_dict(embed_data) if embed_data and embed_data.get("title") else None
            if embed and embed_data.get("color"):
                try: 
                    embed.color = int(embed_data["color"].lstrip("#"), 16)
                except (ValueError, TypeError): 
                    pass
            
            button = disnake.ui.Button(
                label=button_data.get("label"), 
                emoji=button_data.get("emoji"), 
                style=disnake.ButtonStyle.success, 
                custom_id="salers_cart_comprar"
            )
            
            try:
                kwargs = {}
                if content: 
                    kwargs["content"] = content
                if embed: 
                    kwargs["embed"] = embed
                if button: 
                    kwargs["components"] = [button]
                await channel.send(**kwargs)
                await inter.followup.send(f"{positivo} Painel enviado com sucesso em {channel.mention}!", ephemeral=True)
            except Exception as e:
                await inter.followup.send(f"{negativo} Falha ao enviar o painel: {e}", ephemeral=True)

def setup(bot):
    bot.add_cog(SalersMembersExtension(bot))