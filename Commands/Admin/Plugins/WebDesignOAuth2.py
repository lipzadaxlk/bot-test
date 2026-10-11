import disnake
from disnake import *
from disnake.ext import commands
import requests
import json
import re

# Assume que estas variáveis são carregadas de outro arquivo
# Exemplo: positivo = "✅"; negativo = "❌"; editar = "✏️"; config3 = "⚙️"; apagar = "🗑️"; voltar = "⬅️"
from Functions.CarregarEmojis import *
from Commands.Admin.Plugins.ECloud import API_URL, ObterAuthLocal 

# --- Modais (Sem alteração na lógica) ---

class SimpleEditorModal(disnake.ui.Modal):
    def __init__(self, current_settings: dict):
        components = [
            disnake.ui.TextInput(label="Título da Página", custom_id="title", value=current_settings.get("title", ""), max_length=50),
            disnake.ui.TextInput(label="Texto Principal", custom_id="text", value=current_settings.get("text", ""), style=disnake.TextInputStyle.paragraph, max_length=200),
            disnake.ui.TextInput(label="Texto do Botão", custom_id="button_text", value=current_settings.get("button_text", ""), max_length=30),
            disnake.ui.TextInput(label="URL da Imagem de Fundo (https://...)", custom_id="background_url", value=current_settings.get("background_url", ""), required=False),
            disnake.ui.TextInput(label="Cor Principal do Texto (HEX: #RRGGBB)", custom_id="text_color", value=current_settings.get("text_color", ""), max_length=7, required=False),
        ]
        super().__init__(title="Editor Simples de Design", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)
        if inter.text_values["text_color"] and not re.fullmatch(r"^#(?:[0-9a-fA-F]{6})$", inter.text_values["text_color"]):
            return await inter.followup.send(f"{negativo} Cor HEX inválida.", ephemeral=True)
        if inter.text_values["background_url"] and not inter.text_values["background_url"].startswith("https://"):
            return await inter.followup.send(f"{negativo} URL de fundo deve começar com `https://`.", ephemeral=True)

        payload = {
            "mode": "simple",
            "data": { "title": inter.text_values["title"], "text": inter.text_values["text"], "button_text": inter.text_values["button_text"], "background_url": inter.text_values["background_url"], "text_color": inter.text_values["text_color"] }
        }
        success = await update_design_config(payload)
        if success:
            await send_design_panel(inter, use_followup=True) 
            await inter.followup.send(f"{positivo} Design Simples salvo com sucesso!", ephemeral=True)
        else:
            await inter.followup.send(f"{negativo} Falha ao salvar o design.", ephemeral=True)

class AdvancedEditorModal(disnake.ui.Modal):
    def __init__(self, current_html: str):
        components = [
            disnake.ui.TextInput(
                label="Código HTML Completo", custom_id="custom_html",
                value=current_html,
                style=disnake.TextInputStyle.paragraph,
                placeholder="Cole seu código HTML aqui. Tags como <script> serão removidas por segurança.",
                max_length=4000
            )
        ]
        super().__init__(title="Editor Avançado (HTML)", custom_id="advanced_html_modal", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)
        payload = {
            "mode": "advanced",
            "data": {"custom_html": inter.text_values["custom_html"]}
        }
        success = await update_design_config(payload)
        if success:
            await send_design_panel(inter, use_followup=True)
            await inter.followup.send(f"{positivo} Código HTML salvo!", ephemeral=True)
        else:
            await inter.followup.send(f"{negativo} Falha ao salvar o HTML.", ephemeral=True)

# --- Componentes da View (Dropdown e Botões) ---

class TemplateSelect(disnake.ui.StringSelect):
    def __init__(self):
        options = [
            disnake.SelectOption(label="Moderno (Padrão)", value="moderno", description="O design padrão, limpo e com animações."),
            disnake.SelectOption(label="Minimalista", value="minimalista", description="Um design simples, focado no texto."),
            disnake.SelectOption(label="Retrô Gamer", value="retro", description="Um design com estilo pixel art e cores vibrantes."),
        ]
        super().__init__(placeholder="Escolha um template da galeria...", min_values=1, max_values=1, options=options)

    async def callback(self, inter: disnake.MessageInteraction):
        await inter.response.defer()
        template_id = self.values[0]
        payload = { "mode": "template", "data": {"template_id": template_id} }
        
        success = await update_design_config(payload)
        if success:
            await send_design_panel(inter)
            await inter.followup.send(f"{positivo} Tema '{template_id}' selecionado!", ephemeral=True)
        else:
            await inter.followup.send(f"{negativo} Falha ao selecionar o template.", ephemeral=True)

class WebDesignView(disnake.ui.View):
    def __init__(self, config: dict):
        super().__init__(timeout=None)
        self.config = config
        
        # Adiciona os componentes
        self.add_item(TemplateSelect())

        # BOTÃO "VOLTAR" ADICIONADO SEM CALLBACK INTERNO
        # A interação para este botão deve ser capturada por um listener 
        # que verifique o custom_id="PainelInicial"
        self.add_item(disnake.ui.Button(
            label="Voltar", 
            style=disnake.ButtonStyle.grey, 
            emoji=voltar, 
            custom_id="PainelInicial", 
            row=2
        ))

    @disnake.ui.button(label="Editor Simples", style=disnake.ButtonStyle.primary, emoji=editar, row=1)
    async def simple_editor_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        current_settings = self.config.get("settings", {}) if self.config.get("mode") == "simple" else {}
        await inter.response.send_modal(SimpleEditorModal(current_settings))

    @disnake.ui.button(label="Editor Avançado (HTML)", style=disnake.ButtonStyle.secondary, emoji=config3, row=1)
    async def advanced_editor_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        current_html = self.config.get("raw_html", "") if self.config.get("mode") == "advanced" else ""
        await inter.response.send_modal(AdvancedEditorModal(current_html))
    
    @disnake.ui.button(label="Resetar para Padrão", style=disnake.ButtonStyle.danger, emoji=apagar, row=2)
    async def reset_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.defer()
        success = await update_design_config(None)
        if success:
            await send_design_panel(inter)
            await inter.followup.send(f"{positivo} Design resetado para o padrão!", ephemeral=True)
        else:
            await inter.followup.send(f"{negativo} Falha ao resetar o design.", ephemeral=True)

# --- Funções de Lógica e API ---

async def get_design_config():
    auth_data = ObterAuthLocal()
    auth_token = auth_data.get("authorization")
    if not auth_token: return {}
    headers = {'Authorization': auth_token}
    endpoint = f"{API_URL}config/web-design"
    try:
        response = requests.get(endpoint, headers=headers)
        return response.json() if response.status_code == 200 else {}
    except requests.RequestException:
        return {}

async def update_design_config(payload: dict or None):
    auth_data = ObterAuthLocal()
    auth_token = auth_data.get("authorization")
    if not auth_token: return False
    headers = {'Authorization': auth_token, 'Content-Type': 'application/json'}
    try:
        if payload is None:
            endpoint = f"{API_URL}config/web-design-reset"
            response = requests.delete(endpoint, headers=headers)
        else:
            endpoint = f"{API_URL}config/web-design-update"
            response = requests.post(endpoint, headers=headers, json=payload)
        return response.status_code == 200
    except requests.RequestException:
        return False
        
async def send_design_panel(inter: disnake.MessageInteraction, use_followup: bool = False):
    config = await get_design_config()
    mode = config.get("mode", "padrão")
    
    container_elems = [
        disnake.ui.TextDisplay("# 🎨 Painel de Design do Site"),
        disnake.ui.Separator(),
        disnake.ui.TextDisplay("Personalize a aparência da sua página de verificação. As alterações são aplicadas instantaneamente."),
        disnake.ui.Separator(),
        disnake.ui.TextDisplay(f"**Modo de Edição Atual:** `{mode.replace('_', ' ').capitalize()}`"),
        disnake.ui.Separator(),
    ]

    if mode == "simple":
        settings = config.get("settings", {})
        title_text = settings.get('title') or "*Não definido*"
        button_text = settings.get('button_text') or "*Não definido*"
        main_text = settings.get('text') or "*Não definido*"
        
        container_elems.extend([
            disnake.ui.TextDisplay(f"**Título da Página:** {title_text}"),
            disnake.ui.TextDisplay(f"**Texto do Botão:** {button_text}"),
            disnake.ui.TextDisplay(f"**Texto Principal:**\n```\n{main_text}\n```"),
        ])

    elif mode == "advanced":
        container_elems.append(
            disnake.ui.TextDisplay("**< > Configuração Avançada Ativa**\nO site está usando um código HTML customizado definido por você.")
        )
    elif mode == "template":
        template_id = config.get("template_id", "N/A")
        container_elems.append(
            disnake.ui.TextDisplay(f"**Template Ativo**\nO site está usando o template da galeria: **{template_id.capitalize()}**.")
        )
    
    container_elems.extend([
        disnake.ui.Separator(),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Editor Simples", style=disnake.ButtonStyle.primary, emoji=editar, custom_id="simple_editor_webdesign"),
            disnake.ui.Button(label="Editor Avançado (HTML)", style=disnake.ButtonStyle.secondary, emoji=config3, custom_id="advanced_editor_webdesign"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Resetar para Padrão", style=disnake.ButtonStyle.danger, emoji=apagar, custom_id="reset_webdesign"),
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=voltar, custom_id="PainelInicial")
        ),
        disnake.ui.Separator(),
        disnake.ui.TextDisplay(f"-# ID do Servidor: {inter.guild.id}")
    ])
    
    container = disnake.ui.Container(*container_elems)

    if use_followup:
        await inter.edit_original_message(embed=None, components=[container])
    else:
        await inter.edit_original_message(embed=None, components=[container])

# --- Cog e Setup ---

class WebDesignCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def WebDesignButtonListener(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "WebSiteDesign_eCloud":
            await inter.response.defer(ephemeral=True)
            await send_design_panel(inter)
        
        elif inter.component.custom_id == "simple_editor_webdesign":
            config = await get_design_config()
            current_settings = config.get("settings", {}) if config.get("mode") == "simple" else {}
            await inter.response.send_modal(SimpleEditorModal(current_settings))
        
        elif inter.component.custom_id == "advanced_editor_webdesign":
            config = await get_design_config()
            current_html = config.get("raw_html", "") if config.get("mode") == "advanced" else ""
            await inter.response.send_modal(AdvancedEditorModal(current_html))
        
        elif inter.component.custom_id == "reset_webdesign":
            await inter.response.defer()
            success = await update_design_config(None)
            if success:
                await send_design_panel(inter)
                await inter.followup.send(f"{positivo} Design resetado para o padrão!", ephemeral=True)
            else:
                await inter.followup.send(f"{negativo} Falha ao resetar o design.", ephemeral=True)

def setup(bot):
    bot.add_cog(WebDesignCog(bot))