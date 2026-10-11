# Nome do Arquivo: Comunidade.py
import disnake
from disnake.ext import commands
import json
import os
import uuid
import io

# Assumimos que estes imports e suas respectivas funções existem no seu projeto.
from Functions.CarregarEmojis import *

os.makedirs("Database/Comunidade", exist_ok=True)

CORES_TEMAS = {
    "preto": 0x000000, "azul": 0x0066FF, "vermelho": 0xFF0000, "verde": 0x00FF00,
    "amarelo": 0xFFFF00, "roxo": 0x9900FF, "laranja": 0xFF6600, "branco": 0xFFFFFF
}

def carregar_json(caminho, default=None):
    if default is None: default = {}
    try:
        with open(caminho, "r", encoding='utf-8') as f: return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        salvar_json(caminho, default)
        return default

def salvar_json(caminho, data):
    with open(caminho, "w", encoding='utf-8') as f: json.dump(data, f, indent=4)

class ComunidadeCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Garante que os arquivos de configuração existam
        carregar_json("Database/Comunidade/ia.json", {
            "status_conversa": False, "status_imagem": False, "status_audio": False,
            "status_voz": False, "canal_texto_id": None, "canal_voz_id": None,
            "prompt": "Você é um assistente prestativo integrado a um bot do Discord chamado Gemini."
        })
        carregar_json("Database/Comunidade/instapet.json", {"canal_id": None, "prefixo": "pet!", "cargo_id": None, "tema": "amarelo"})
        carregar_json("Database/Comunidade/influenciar.json", {"canal_id": None, "prefixo": "inf!", "cargo_id": None, "tema": "roxo", "hall_channel_id": None})


    @commands.Cog.listener("on_button_click")
    async def ComunidadeListener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id

        #region Navegação Principal e Sub-paineis
        if custom_id == "GerenciarPainelComunidade":
            if not self.bot.verificar_permissao(inter.author.id, "panel", "GerenciarPainelComunidade"):
                return await inter.response.send_message(f"{negativo} Você não tem permissão para acessar este painel.", ephemeral=True)
            
            embed = disnake.Embed(title="Painel de Comunidade", description="Selecione um módulo abaixo para gerenciar as funcionalidades do seu bot.", color=0x00ff00)
            components = [
                disnake.ui.Select(
                    custom_id="comunidade_main_select",
                    placeholder="Escolha um módulo para configurar...",
                    options=[
                        disnake.SelectOption(label="Formulário", value="comunidade_formulario", emoji=termos),
                        disnake.SelectOption(label="Instagram", value="comunidade_instagram_selecao", emoji=instagram),
                        disnake.SelectOption(label="Temp Call", value="comunidade_tempcall", emoji=telefone),
                        disnake.SelectOption(label="Keys", value="comunidade_keys", emoji=chave),
                        disnake.SelectOption(label="Inteligência Artificial", value="comunidade_ia", emoji=ia)
                    ]
                ),
                disnake.ui.Button(label="Voltar", emoji=voltar, style=disnake.ButtonStyle.grey, custom_id="PainelInicial")
            ]
            await inter.response.edit_message(embed=None, components=components, content="Oque você deseja configurar?", attachments=[])
        
        elif custom_id == "comunidade_instagram_selecao_btn": await self.mostrar_painel_instagram_selecao(inter)
        elif custom_id == "comunidade_instagram": await self.mostrar_painel_instagram(inter)
        elif custom_id == "comunidade_instapet": await self.mostrar_painel_instapet(inter)
        elif custom_id == "comunidade_influenciar": await self.mostrar_painel_influenciar(inter)
        elif custom_id == "comunidade_tempcall": await self.mostrar_painel_tempcall(inter)
        elif custom_id == "comunidade_keys": await self.mostrar_painel_keys(inter)
        elif custom_id == "comunidade_formulario": await self.mostrar_painel_selecao_formulario(inter, edit=True)
        elif custom_id == "comunidade_ia": await self.mostrar_painel_ia(inter)
        #endregion

        #region Handlers Instagram
        elif custom_id == "instagram_canal":
            await inter.response.edit_message(components=[
                disnake.ui.ChannelSelect(custom_id="instagram_select_canal", placeholder="Selecione o canal para os posts", channel_types=[disnake.ChannelType.text]),
                disnake.ui.Button(label="Cancelar", style=disnake.ButtonStyle.grey, custom_id="comunidade_instagram")])
        elif custom_id == "instagram_prefixo":
            config = carregar_json("Database/Comunidade/instagram.json")
            await inter.response.send_modal(title="Definir Prefixo do Instagram", custom_id="instagram_modal_prefixo", components=[
                disnake.ui.TextInput(label="Novo Prefixo", custom_id="prefixo", value=config.get("prefixo", "ig!"), max_length=10, required=True)])
        elif custom_id == "instagram_cargo":
            await inter.response.edit_message(components=[
                disnake.ui.RoleSelect(custom_id="instagram_select_cargo", placeholder="Selecione o cargo de permissão"),
                disnake.ui.Button(label="Cancelar", style=disnake.ButtonStyle.grey, custom_id="comunidade_instagram")])
        elif custom_id == "instagram_tema":
            options = [disnake.SelectOption(label=cor.title(), value=cor) for cor in CORES_TEMAS.keys()]
            await inter.response.edit_message(components=[
                disnake.ui.Select(custom_id="instagram_select_tema", placeholder="Selecione uma cor de tema", options=options),
                disnake.ui.Button(label="Cancelar", style=disnake.ButtonStyle.grey, custom_id="comunidade_instagram")])
        #endregion
        
        #region Handlers Instapet
        elif custom_id == "instapet_canal":
            await inter.response.edit_message(components=[
                disnake.ui.ChannelSelect(custom_id="instapet_select_canal", placeholder="Selecione o canal para os posts", channel_types=[disnake.ChannelType.text]),
                disnake.ui.Button(label="Cancelar", style=disnake.ButtonStyle.grey, custom_id="comunidade_instapet")])
        elif custom_id == "instapet_prefixo":
            config = carregar_json("Database/Comunidade/instapet.json")
            await inter.response.send_modal(title="Definir Prefixo do Instapet", custom_id="instapet_modal_prefixo", components=[
                disnake.ui.TextInput(label="Novo Prefixo", custom_id="prefixo", value=config.get("prefixo", "pet!"), max_length=10, required=True)])
        elif custom_id == "instapet_cargo":
            await inter.response.edit_message(components=[
                disnake.ui.RoleSelect(custom_id="instapet_select_cargo", placeholder="Selecione o cargo de permissão"),
                disnake.ui.Button(label="Cancelar", style=disnake.ButtonStyle.grey, custom_id="comunidade_instapet")])
        elif custom_id == "instapet_tema":
            options = [disnake.SelectOption(label=cor.title(), value=cor) for cor in CORES_TEMAS.keys()]
            await inter.response.edit_message(components=[
                disnake.ui.Select(custom_id="instapet_select_tema", placeholder="Selecione uma cor de tema", options=options),
                disnake.ui.Button(label="Cancelar", style=disnake.ButtonStyle.grey, custom_id="comunidade_instapet")])
        #endregion

        #region Handlers Influenciar
        elif custom_id == "influenciar_canal":
            await inter.response.edit_message(components=[
                disnake.ui.ChannelSelect(custom_id="influenciar_select_canal", placeholder="Selecione o canal para os posts", channel_types=[disnake.ChannelType.text]),
                disnake.ui.Button(label="Cancelar", style=disnake.ButtonStyle.grey, custom_id="comunidade_influenciar")])
        elif custom_id == "influenciar_prefixo":
            config = carregar_json("Database/Comunidade/influenciar.json")
            await inter.response.send_modal(title="Definir Prefixo de Influencer", custom_id="influenciar_modal_prefixo", components=[
                disnake.ui.TextInput(label="Novo Prefixo", custom_id="prefixo", value=config.get("prefixo", "inf!"), max_length=10, required=True)])
        elif custom_id == "influenciar_cargo":
            await inter.response.edit_message(components=[
                disnake.ui.RoleSelect(custom_id="influenciar_select_cargo", placeholder="Selecione o cargo de permissão"),
                disnake.ui.Button(label="Cancelar", style=disnake.ButtonStyle.grey, custom_id="comunidade_influenciar")])
        elif custom_id == "influenciar_tema":
            options = [disnake.SelectOption(label=cor.title(), value=cor) for cor in CORES_TEMAS.keys()]
            await inter.response.edit_message(components=[
                disnake.ui.Select(custom_id="influenciar_select_tema", placeholder="Selecione uma cor de tema", options=options),
                disnake.ui.Button(label="Cancelar", style=disnake.ButtonStyle.grey, custom_id="comunidade_influenciar")])
        elif custom_id == "influenciar_hall":
            await inter.response.edit_message(components=[
                disnake.ui.ChannelSelect(custom_id="influenciar_select_hall", placeholder="Selecione o canal do Hall da Fama", channel_types=[disnake.ChannelType.text]),
                disnake.ui.Button(label="Cancelar", style=disnake.ButtonStyle.grey, custom_id="comunidade_influenciar")])
        #endregion

        #region Handlers Temp Call
        elif custom_id == "tempcall_canal_voz":
            await inter.response.edit_message(components=[
                disnake.ui.ChannelSelect(custom_id="tempcall_select_canal_voz", placeholder="Selecione o canal 'Junte-se para criar'", channel_types=[disnake.ChannelType.voice]),
                disnake.ui.Button(label="Cancelar", style=disnake.ButtonStyle.grey, custom_id="comunidade_tempcall")])
        elif custom_id == "tempcall_categoria":
            await inter.response.edit_message(components=[
                disnake.ui.ChannelSelect(custom_id="tempcall_select_categoria", placeholder="Selecione a categoria para criar as calls", channel_types=[disnake.ChannelType.category]),
                disnake.ui.Button(label="Cancelar", style=disnake.ButtonStyle.grey, custom_id="comunidade_tempcall")])
        elif custom_id == "tempcall_cargo":
            await inter.response.edit_message(components=[
                disnake.ui.RoleSelect(custom_id="tempcall_select_cargo", placeholder="Selecione o cargo de bypass/permissão"),
                disnake.ui.Button(label="Cancelar", style=disnake.ButtonStyle.grey, custom_id="comunidade_tempcall")])
        elif custom_id == "tempcall_toggle":
            config = carregar_json("Database/Comunidade/calltemp.json")
            config["ativo"] = not config.get("ativo", False)
            salvar_json("Database/Comunidade/calltemp.json", config)
            await self.mostrar_painel_tempcall(inter)
        #endregion

        #region Handlers do Sistema de Formulário
        elif custom_id.startswith("form_"):
            parts = custom_id.split('_')
            action = parts[1]
            form_id = parts[2] if len(parts) > 2 else None
            if action == "modal" and parts[2] == "criar": await self.criar_formulario(inter, "modal")
            elif action == "topico" and parts[2] == "criar": await self.criar_formulario(inter, "topico")
            elif action == "delete" and len(parts) >= 4 and parts[2] == "confirm":
                form_id_to_delete = parts[3]
                formularios = carregar_json("Database/Comunidade/formularios.json")
                if form_id_to_delete in formularios:
                    del formularios[form_id_to_delete]
                    salvar_json("Database/Comunidade/formularios.json", formularios)
                await self.mostrar_painel_selecao_formulario(inter, edit=True)
            elif form_id:
                if action == "show": await self.mostrar_painel_formulario(inter, form_id)
                elif action == "aparencia": await self.mostrar_edicao_aparencia(inter, form_id, edit=True)
                elif action == "perguntas": await self.mostrar_edicao_perguntas(inter, form_id, edit=True)
                elif action == "cargo": await self.mostrar_edicao_cargo(inter, form_id)
                elif action == "delete":
                    components = [[disnake.ui.Button(label="Confirmar Exclusão", style=disnake.ButtonStyle.danger, custom_id=f"form_delete_confirm_{form_id}"), disnake.ui.Button(label="Cancelar", style=disnake.ButtonStyle.secondary, custom_id=f"form_show_{form_id}")]]
                    await inter.response.edit_message(content="**Você tem certeza que deseja apagar este formulário? Esta ação é irreversível.**", embed=None, components=components)
        elif custom_id.startswith("add_pergunta_"):
            form_id = custom_id.split('_')[2]
            modal = disnake.ui.Modal(title="Adicionar Nova Pergunta", custom_id=f"modal_form_pergunta_{form_id}", components=[disnake.ui.TextInput(label="Texto da Pergunta", placeholder="Ex: Qual o seu nome e idade?", custom_id="pergunta", style=disnake.TextInputStyle.long, max_length=256, required=True)])
            await inter.response.send_modal(modal)
        elif custom_id.startswith("remove_pergunta_"):
            form_id = custom_id.split('_')[2]
            formularios = carregar_json("Database/Comunidade/formularios.json")
            perguntas = formularios.get(form_id, {}).get("perguntas", [])
            if not perguntas: return await inter.response.send_message("❌ Não há perguntas para remover.", ephemeral=True)
            options = [disnake.SelectOption(label=f"{i+1}. {p[:80]}", value=str(i)) for i, p in enumerate(perguntas)]
            select = disnake.ui.Select(placeholder="Selecione a pergunta para remover...", custom_id=f"remover_pergunta_dropdown_{form_id}", options=options)
            await inter.response.send_message("Selecione uma pergunta para remover.", components=[select], ephemeral=True)
        elif custom_id.startswith("enviar_form_"):
            form_id = custom_id.split('_')[2]
            channel_select = disnake.ui.ChannelSelect(custom_id=f"send_form_channel_select_{form_id}", channel_types=[disnake.ChannelType.text], placeholder="Selecione o canal para enviar")
            await inter.response.send_message("Onde você gostaria de enviar este formulário?", components=[channel_select], ephemeral=True)
        elif custom_id.startswith("edit_content_"):
            form_id = custom_id.split('_')[-1]
            formularios = carregar_json("Database/Comunidade/formularios.json")
            content = formularios.get(form_id, {}).get("content", "")
            await inter.response.send_modal(title="Editar Conteúdo da Mensagem", custom_id=f"modal_edit_content_{form_id}", components=[disnake.ui.TextInput(label="Conteúdo (texto acima do embed)", custom_id="content", style=disnake.TextInputStyle.paragraph, placeholder="Deixe em branco para nenhum.", value=content, max_length=2000, required=False)])
        elif custom_id.startswith("clear_content_"):
            form_id = custom_id.split('_')[-1]
            formularios = carregar_json("Database/Comunidade/formularios.json")
            if form_id in formularios:
                formularios[form_id]["content"] = None
                salvar_json("Database/Comunidade/formularios.json", formularios)
                await self.mostrar_edicao_aparencia(inter, form_id, edit=True)
        elif custom_id.startswith("edit_embed_"):
            form_id = custom_id.split('_')[-1]
            formularios = carregar_json("Database/Comunidade/formularios.json")
            embed_data = formularios.get(form_id, {}).get("embed", {})
            cor_hex = hex(embed_data.get("color", 0x3498db)).replace("0x", "#")
            await inter.response.send_modal(title="Editar Embed", custom_id=f"modal_edit_embed_{form_id}", components=[disnake.ui.TextInput(label="Título", custom_id="title", value=embed_data.get("title", ""), max_length=256, required=True), disnake.ui.TextInput(label="Descrição", custom_id="description", value=embed_data.get("description", ""), style=disnake.TextInputStyle.paragraph, max_length=4000, required=False), disnake.ui.TextInput(label="Cor (Hex ex: #3498db)", custom_id="color", value=cor_hex, max_length=7, required=True),])
        elif custom_id.startswith("reset_embed_"):
            form_id = custom_id.split('_')[-1]
            formularios = carregar_json("Database/Comunidade/formularios.json")
            if form_id in formularios:
                form_data = formularios[form_id]
                form_data["embed"] = {"title": form_data.get("nome", "Formulário"),"description": "Clique no botão abaixo para responder ao formulário.","color": 0x3498db}
                salvar_json("Database/Comunidade/formularios.json", formularios)
                await self.mostrar_edicao_aparencia(inter, form_id, edit=True)
        elif custom_id.startswith("edit_button_"):
            form_id = custom_id.split('_')[-1]
            formularios = carregar_json("Database/Comunidade/formularios.json")
            botao_data = formularios.get(form_id, {}).get("botao", {})
            await inter.response.send_modal(title="Editar Botão do Formulário", custom_id=f"modal_edit_button_{form_id}", components=[disnake.ui.TextInput(label="Texto do Botão (Label)", custom_id="label", value=botao_data.get("label", "Responder"), max_length=80, required=True), disnake.ui.TextInput(label="Emoji do Botão", custom_id="emoji", value=botao_data.get("emoji", ""), max_length=50, required=False), disnake.ui.TextInput(label="Cor (success, danger, primary, secondary)", custom_id="style", value=botao_data.get("style", "success"), max_length=10, required=True),])
        #endregion

        #region Handlers do Sistema de Keys
        elif custom_id == "keys_onoff":
            config = carregar_json("Database/Comunidade/keys.json")
            config["status"] = not config.get("status", False)
            salvar_json("Database/Comunidade/keys.json", config)
            await self.mostrar_painel_keys(inter)
        elif custom_id == "keys_canallogs":
            await inter.response.edit_message(components=[
                disnake.ui.ChannelSelect(custom_id="keys_select_canallogs", placeholder="Selecione o canal de logs", channel_types=[disnake.ChannelType.text]),
                disnake.ui.Button(label="Cancelar", style=disnake.ButtonStyle.grey, custom_id="comunidade_keys")])
        elif custom_id == "keys_configcargo":
            await inter.response.edit_message(components=[
                disnake.ui.RoleSelect(custom_id="keys_select_cargo", placeholder="Selecione o cargo de acesso"),
                disnake.ui.Button(label="Cancelar", style=disnake.ButtonStyle.grey, custom_id="comunidade_keys")])
        elif custom_id == "keys_canalkeys":
            await inter.response.edit_message(components=[
                disnake.ui.ChannelSelect(custom_id="keys_select_canalkeys", placeholder="Selecione o canal de resgate de keys", channel_types=[disnake.ChannelType.text]),
                disnake.ui.Button(label="Cancelar", style=disnake.ButtonStyle.grey, custom_id="comunidade_keys")])
        elif custom_id == "keys_resetartudo":
            await inter.response.edit_message(content="**# Tem certeza que deseja resetar TODA a configuração do sistema de keys?**", embed=None, components=[
                disnake.ui.Button(label="Confirmar Reset da Configuração", style=disnake.ButtonStyle.danger, custom_id="keys_confirm_reset_config"),
                disnake.ui.Button(label="Cancelar", style=disnake.ButtonStyle.secondary, custom_id="comunidade_keys")])
        elif custom_id == "keys_confirm_reset_config":
            salvar_json("Database/Comunidade/keys.json", {"status": False, "canal_logs_id": None, "cargo_id": None, "canal_keys_id": None})
            await self.mostrar_painel_keys(inter)
        elif custom_id == "keys_criarkeys":
            await inter.response.send_modal(title="Gerar Novas Keys", custom_id="keys_modal_criar", components=[
                disnake.ui.TextInput(label="Quantidade", custom_id="quantidade", placeholder="Número de keys a serem geradas (ex: 10)", required=True),
                disnake.ui.TextInput(label="Prefixo (Opcional)", custom_id="prefixo", placeholder="Texto no início da key (ex: VIP-)", required=False)])
        elif custom_id == "keys_deletarkeys":
            keys = carregar_json("Database/Comunidade/generated_keys.json", [])
            if not keys: return await inter.response.send_message("Não há keys para deletar.", ephemeral=True)
            options = [disnake.SelectOption(label=key, value=key) for key in keys[:25]]
            await inter.response.edit_message(components=[
                disnake.ui.StringSelect(custom_id="keys_select_delete", placeholder="Selecione as keys para deletar", options=options, min_values=1, max_values=len(options)),
                disnake.ui.Button(label="Cancelar", style=disnake.ButtonStyle.grey, custom_id="comunidade_keys")])
        elif custom_id == "keys_resetarkeys":
            await inter.response.edit_message(content="**# Tem certeza que deseja deletar TODAS as keys geradas? Esta ação é irreversível!**", embed=None, components=[
                disnake.ui.Button(label="Confirmar Deleção de TODAS as Keys", style=disnake.ButtonStyle.danger, custom_id="keys_confirm_reset_keys"),
                disnake.ui.Button(label="Cancelar", style=disnake.ButtonStyle.secondary, custom_id="comunidade_keys")])
        elif custom_id == "keys_confirm_reset_keys":
            salvar_json("Database/Comunidade/generated_keys.json", [])
            await inter.response.send_message(f"{positivo} Todas as keys foram deletadas com sucesso!", ephemeral=True)
            await self.mostrar_painel_keys(inter)
        elif custom_id == "keys_save_dm":
            if inter.message.attachments:
                arquivo = inter.message.attachments[0]
                try:
                    await inter.author.send(f"{arrow} Aqui estão as suas keys geradas:", file=await arquivo.to_file())
                    await inter.response.edit_message(content=f"{positivo} Keys enviadas para sua DM!", components=[], attachments=[])
                except disnake.Forbidden:
                    await inter.response.edit_message(content=f"{negativo} Não foi possível enviar a DM. Verifique suas configurações de privacidade.", components=[], attachments=[])
            else:
                 await inter.response.send_message(f"{negativo} Nenhum arquivo de key encontrado para enviar.", ephemeral=True)
        #endregion

        #region Handlers da IA
        elif custom_id.startswith("ia_toggle_"):
            feature = custom_id.replace("ia_toggle_", "")
            config = carregar_json("Database/Comunidade/ia.json")
            
            # Lógica de exclusividade entre Conversa e Áudio
            if feature == "conversa" and not config["status_conversa"]:
                if config.get("status_audio"): config["status_audio"] = False
            elif feature == "audio" and not config["status_audio"]:
                if config.get("status_conversa"): config["status_conversa"] = False

            # Alterna o status do recurso
            key = f"status_{feature}"
            config[key] = not config.get(key, False)
            salvar_json("Database/Comunidade/ia.json", config)
            await self.mostrar_painel_ia(inter)
        
        elif custom_id == "ia_canal_texto":
            await inter.response.edit_message(components=[
                disnake.ui.ChannelSelect(custom_id="ia_select_canal_texto", placeholder="Selecione o canal de texto da IA", channel_types=[disnake.ChannelType.text]),
                disnake.ui.Button(label="Cancelar", style=disnake.ButtonStyle.grey, custom_id="comunidade_ia")])

        elif custom_id == "ia_canal_voz":
            await inter.response.edit_message(components=[
                disnake.ui.ChannelSelect(custom_id="ia_select_canal_voz", placeholder="Selecione o canal de voz da IA", channel_types=[disnake.ChannelType.voice]),
                disnake.ui.Button(label="Cancelar", style=disnake.ButtonStyle.grey, custom_id="comunidade_ia")])

        elif custom_id == "ia_configurar_prompt":
            config = carregar_json("Database/Comunidade/ia.json")
            await inter.response.send_modal(
                title="Configurar Prompt da IA",
                custom_id="ia_modal_prompt",
                components=[disnake.ui.TextInput(
                    label="Prompt do Sistema (Personalidade da IA)",
                    custom_id="prompt",
                    value=config.get("prompt", ""),
                    style=disnake.TextInputStyle.paragraph,
                    max_length=2000,
                    required=True
                )]
            )
        #endregion

    @commands.Cog.listener("on_dropdown")
    async def ComunidadeDropdownListener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        values = inter.values

        #region Main Select Handler
        if custom_id == "comunidade_main_select":
            selection = values[0]
            if selection == "comunidade_formulario": await self.mostrar_painel_selecao_formulario(inter, edit=True)
            elif selection == "comunidade_instagram_selecao": await self.mostrar_painel_instagram_selecao(inter)
            elif selection == "comunidade_tempcall": await self.mostrar_painel_tempcall(inter)
            elif selection == "comunidade_keys": await self.mostrar_painel_keys(inter)
            elif selection == "comunidade_ia": await self.mostrar_painel_ia(inter)
            return
        #endregion

        #region Select Handlers Instagram
        if custom_id == "instagram_select_canal":
            config = carregar_json("Database/Comunidade/instagram.json")
            config["canal_id"] = int(values[0])
            salvar_json("Database/Comunidade/instagram.json", config)
            await self.mostrar_painel_instagram(inter)
        elif custom_id == "instagram_select_cargo":
            config = carregar_json("Database/Comunidade/instagram.json")
            config["cargo_id"] = int(values[0])
            salvar_json("Database/Comunidade/instagram.json", config)
            await self.mostrar_painel_instagram(inter)
        elif custom_id == "instagram_select_tema":
            config = carregar_json("Database/Comunidade/instagram.json")
            config["tema"] = values[0]
            salvar_json("Database/Comunidade/instagram.json", config)
            await self.mostrar_painel_instagram(inter)
        #endregion
        
        #region Select Handlers Instapet
        elif custom_id == "instapet_select_canal":
            config = carregar_json("Database/Comunidade/instapet.json")
            config["canal_id"] = int(values[0])
            salvar_json("Database/Comunidade/instapet.json", config)
            await self.mostrar_painel_instapet(inter)
        elif custom_id == "instapet_select_cargo":
            config = carregar_json("Database/Comunidade/instapet.json")
            config["cargo_id"] = int(values[0])
            salvar_json("Database/Comunidade/instapet.json", config)
            await self.mostrar_painel_instapet(inter)
        elif custom_id == "instapet_select_tema":
            config = carregar_json("Database/Comunidade/instapet.json")
            config["tema"] = values[0]
            salvar_json("Database/Comunidade/instapet.json", config)
            await self.mostrar_painel_instapet(inter)
        #endregion

        #region Select Handlers Influenciar
        elif custom_id == "influenciar_select_canal":
            config = carregar_json("Database/Comunidade/influenciar.json")
            config["canal_id"] = int(values[0])
            salvar_json("Database/Comunidade/influenciar.json", config)
            await self.mostrar_painel_influenciar(inter)
        elif custom_id == "influenciar_select_cargo":
            config = carregar_json("Database/Comunidade/influenciar.json")
            config["cargo_id"] = int(values[0])
            salvar_json("Database/Comunidade/influenciar.json", config)
            await self.mostrar_painel_influenciar(inter)
        elif custom_id == "influenciar_select_tema":
            config = carregar_json("Database/Comunidade/influenciar.json")
            config["tema"] = values[0]
            salvar_json("Database/Comunidade/influenciar.json", config)
            await self.mostrar_painel_influenciar(inter)
        elif custom_id == "influenciar_select_hall":
            config = carregar_json("Database/Comunidade/influenciar.json")
            config["hall_channel_id"] = int(values[0])
            salvar_json("Database/Comunidade/influenciar.json", config)
            await self.mostrar_painel_influenciar(inter)
        #endregion

        #region Select Handlers Temp Call
        elif custom_id == "tempcall_select_canal_voz":
            config = carregar_json("Database/Comunidade/calltemp.json")
            config["canal_voz_id"] = int(values[0])
            salvar_json("Database/Comunidade/calltemp.json", config)
            await self.mostrar_painel_tempcall(inter)
        elif custom_id == "tempcall_select_categoria":
            config = carregar_json("Database/Comunidade/calltemp.json")
            config["categoria_id"] = int(values[0])
            salvar_json("Database/Comunidade/calltemp.json", config)
            await self.mostrar_painel_tempcall(inter)
        elif custom_id == "tempcall_select_cargo":
            config = carregar_json("Database/Comunidade/calltemp.json")
            config["cargo_id"] = int(values[0])
            salvar_json("Database/Comunidade/calltemp.json", config)
            await self.mostrar_painel_tempcall(inter)
        #endregion

        #region Select Handlers Formulário
        elif custom_id == "gerenciar_formulario": await self.mostrar_painel_formulario(inter, values[0])
        elif custom_id.startswith("selecionar_cargo_form_role_"):
            form_id = custom_id.split('_')[-1]
            cargo_id = int(values[0])
            formularios = carregar_json("Database/Comunidade/formularios.json")
            if form_id in formularios:
                formularios[form_id]["cargo_aprovado"] = cargo_id
                salvar_json("Database/Comunidade/formularios.json", formularios)
                role_obj = inter.guild.get_role(cargo_id)
                await inter.response.edit_message(content=f"{positivo} Cargo de aprovado definido para: {role_obj.mention}", view=None)
            else: await inter.response.edit_message(content=f"{negativo} Formulário não encontrado!", view=None)
        elif custom_id.startswith("remover_pergunta_dropdown_"):
            form_id = custom_id.split('_')[-1]
            pergunta_index = int(values[0])
            formularios = carregar_json("Database/Comunidade/formularios.json")
            if form_id in formularios and pergunta_index < len(formularios[form_id]["perguntas"]):
                formularios[form_id]["perguntas"].pop(pergunta_index)
                salvar_json("Database/Comunidade/formularios.json", formularios)
                await self.mostrar_edicao_perguntas(inter, form_id, edit=True)
            else: await inter.response.edit_message(f"{negativo} Erro ao remover pergunta!", view=None)
        elif custom_id.startswith("send_form_channel_select_"):
            form_id = custom_id.split('_')[-1]
            channel_id = int(values[0])
            channel = inter.guild.get_channel(channel_id)
            if not channel: return await inter.response.edit_message(f"{negativo} Canal não encontrado.", view=None)
            formularios = carregar_json("Database/Comunidade/formularios.json")
            form_data = formularios.get(form_id)
            if not form_data: return await inter.response.edit_message(f"{negativo} Dados do formulário não encontrados.", view=None)
            embed_data, botao_data = form_data.get("embed", {}), form_data.get("botao", {})
            form_embed = disnake.Embed.from_dict(embed_data) if embed_data else disnake.Embed(title="Formulário", description="Clique no botão abaixo para responder.", color=0x3498db)
            btn_custom_id = f"open_form_modal_{form_id}" if form_data.get("tipo") == "modal" else f"open_form_topic_{form_id}"
            form_button = disnake.ui.Button(label=botao_data.get("label", "Responder"), emoji=botao_data.get("emoji"), style=getattr(disnake.ButtonStyle, botao_data.get("style", "green")), custom_id=btn_custom_id)
            try:
                msg = await channel.send(content=form_data.get("content"), embed=form_embed, components=[form_button])
                formularios[form_id]["mensagem_id"], formularios[form_id]["canal_id"] = msg.id, msg.channel.id
                salvar_json("Database/Comunidade/formularios.json", formularios)
                await inter.response.edit_message(f"{positivo} Formulário enviado em {channel.mention}!", view=None)
            except disnake.Forbidden: await inter.response.edit_message(f"{negativo} Sem permissão para enviar em {channel.mention}.", view=None)
            except Exception as e: await inter.response.edit_message(f"{negativo} Erro ao enviar formulário: {str(e)}", view=None)
        #endregion

        #region Select Handlers Keys
        elif custom_id == "keys_select_canallogs":
            config = carregar_json("Database/Comunidade/keys.json")
            config["canal_logs_id"] = int(values[0])
            salvar_json("Database/Comunidade/keys.json", config)
            await self.mostrar_painel_keys(inter)
        elif custom_id == "keys_select_cargo":
            config = carregar_json("Database/Comunidade/keys.json")
            config["cargo_id"] = int(values[0])
            salvar_json("Database/Comunidade/keys.json", config)
            await self.mostrar_painel_keys(inter)
        elif custom_id == "keys_select_canalkeys":
            config = carregar_json("Database/Comunidade/keys.json")
            config["canal_keys_id"] = int(values[0])
            salvar_json("Database/Comunidade/keys.json", config)
            await self.mostrar_painel_keys(inter)
        elif custom_id == "keys_select_delete":
            all_keys = carregar_json("Database/Comunidade/generated_keys.json", [])
            keys_to_delete = values
            updated_keys = [key for key in all_keys if key not in keys_to_delete]
            salvar_json("Database/Comunidade/generated_keys.json", updated_keys)
            await inter.response.send_message(f"{positivo} {len(keys_to_delete)} key(s) deletada(s) com sucesso!", ephemeral=True)
            await self.mostrar_painel_keys(inter)
        #endregion
        
        #region Select Handlers IA
        elif custom_id == "ia_select_canal_texto":
            config = carregar_json("Database/Comunidade/ia.json")
            config["canal_texto_id"] = int(values[0])
            salvar_json("Database/Comunidade/ia.json", config)
            await self.mostrar_painel_ia(inter)
        elif custom_id == "ia_select_canal_voz":
            config = carregar_json("Database/Comunidade/ia.json")
            channel_id = int(values[0])
            config["canal_voz_id"] = channel_id
            salvar_json("Database/Comunidade/ia.json", config)
            
            # Limita o canal de voz a 2 usuários
            try:
                vc = await self.bot.fetch_channel(channel_id)
                await vc.edit(user_limit=2)
            except disnake.Forbidden:
                await inter.followup.send("⚠️ Não tenho permissão para alterar o limite de usuários deste canal de voz.", ephemeral=True)
            except Exception as e:
                await inter.followup.send(f"{negativo} Erro ao configurar o canal de voz: {e}", ephemeral=True)

            await self.mostrar_painel_ia(inter)
        #endregion

    @commands.Cog.listener("on_modal_submit")
    async def ComunidadeModalListener(self, inter: disnake.ModalInteraction):
        custom_id = inter.custom_id

        #region Modal Handlers Instagram
        if custom_id == "instagram_modal_prefixo":
            prefixo = inter.text_values["prefixo"].strip()
            if not prefixo: return await inter.response.send_message(f"{negativo} O prefixo não pode estar vazio.", ephemeral=True)
            config = carregar_json("Database/Comunidade/instagram.json")
            config["prefixo"] = prefixo
            salvar_json("Database/Comunidade/instagram.json", config)
            await self.mostrar_painel_instagram(inter)
        #endregion
        
        #region Modal Handlers Instapet
        elif custom_id == "instapet_modal_prefixo":
            prefixo = inter.text_values["prefixo"].strip()
            if not prefixo: return await inter.response.send_message(f"{negativo} O prefixo não pode estar vazio.", ephemeral=True)
            config = carregar_json("Database/Comunidade/instapet.json")
            config["prefixo"] = prefixo
            salvar_json("Database/Comunidade/instapet.json", config)
            await self.mostrar_painel_instapet(inter)
        #endregion

        #region Modal Handlers Influenciar
        elif custom_id == "influenciar_modal_prefixo":
            prefixo = inter.text_values["prefixo"].strip()
            if not prefixo: return await inter.response.send_message(f"{negativo} O prefixo não pode estar vazio.", ephemeral=True)
            config = carregar_json("Database/Comunidade/influenciar.json")
            config["prefixo"] = prefixo
            salvar_json("Database/Comunidade/influenciar.json", config)
            await self.mostrar_painel_influenciar(inter)
        #endregion

        #region Modal Handlers Formulário
        elif custom_id.startswith("modal_form_pergunta_"):
            form_id = custom_id.replace("modal_form_pergunta_", "")
            formularios = carregar_json("Database/Comunidade/formularios.json")
            if form_id not in formularios: return await inter.response.send_message(f"{negativo} Formulário não encontrado!", ephemeral=True)
            form_data = formularios[form_id]
            if form_data['tipo'] == 'modal' and len(form_data['perguntas']) >= 5: return await inter.response.send_message(f"{negativo} Formulários do tipo Modal só podem ter no máximo 5 perguntas.", ephemeral=True)
            pergunta = inter.text_values["pergunta"]
            form_data["perguntas"].append(pergunta)
            salvar_json("Database/Comunidade/formularios.json", formularios)
            await self.mostrar_edicao_perguntas(inter, form_id, edit=True)
        elif custom_id.startswith("modal_criar_formulario_"):
            tipo = custom_id.split('_')[-1]
            nome = inter.text_values["nome"]
            if not nome or len(nome.strip()) < 3: return await inter.response.send_message(f"{negativo} Nome do formulário deve ter pelo menos 3 caracteres!", ephemeral=True)
            form_id = str(uuid.uuid4())
            formularios = carregar_json("Database/Comunidade/formularios.json")
            formularios[form_id] = {"nome": nome.strip(),"tipo": tipo,"perguntas": [],"cargo_aprovado": None,"embed": {"title": nome.strip(),"description": "Clique no botão abaixo para responder ao formulário.","color": 0x3498db},"botao": {"label": "Responder","emoji": "📝","style": "success"},"content": None}
            salvar_json("Database/Comunidade/formularios.json", formularios)
            await self.mostrar_painel_formulario(inter, form_id)
        elif custom_id.startswith("modal_edit_content_"):
            form_id = custom_id.replace("modal_edit_content_", "")
            formularios = carregar_json("Database/Comunidade/formularios.json")
            if form_id in formularios:
                content = inter.text_values["content"].strip()
                formularios[form_id]["content"] = content if content else None
                salvar_json("Database/Comunidade/formularios.json", formularios)
                await self.mostrar_edicao_aparencia(inter, form_id, edit=True)
        elif custom_id.startswith("modal_edit_embed_"):
            form_id = custom_id.replace("modal_edit_embed_", "")
            formularios = carregar_json("Database/Comunidade/formularios.json")
            if form_id in formularios:
                try: color_int = int(inter.text_values["color"].replace("#", "").strip(), 16)
                except ValueError: return await inter.response.send_message(f"{negativo} Cor inválida. Use um formato hexadecimal (ex: #FF0000).", ephemeral=True)
                embed_data = formularios[form_id].get("embed", {})
                embed_data["title"], embed_data["description"], embed_data["color"] = inter.text_values["title"], inter.text_values["description"], color_int
                formularios[form_id]["embed"] = embed_data
                salvar_json("Database/Comunidade/formularios.json", formularios)
                await self.mostrar_edicao_aparencia(inter, form_id, edit=True)
        elif custom_id.startswith("modal_edit_button_"):
            form_id = custom_id.replace("modal_edit_button_", "")
            formularios = carregar_json("Database/Comunidade/formularios.json")
            if form_id in formularios:
                label, emoji, style = inter.text_values["label"], inter.text_values["emoji"], inter.text_values["style"].lower().strip()
                valid_styles = ["success", "danger", "primary", "secondary"]
                if style not in valid_styles: return await inter.response.send_message(f"{negativo} Cor/Estilo inválido. Use um dos: {', '.join(valid_styles)}.", ephemeral=True)
                botao_data = formularios[form_id].get("botao", {})
                botao_data["label"], botao_data["emoji"], botao_data["style"] = label, emoji if emoji else None, style
                formularios[form_id]["botao"] = botao_data
                salvar_json("Database/Comunidade/formularios.json", formularios)
                await self.mostrar_edicao_aparencia(inter, form_id, edit=True)
        #endregion

        #region Modal Handlers Keys
        elif custom_id == "keys_modal_criar":
            try:
                quantidade = int(inter.text_values["quantidade"])
                if not (0 < quantidade <= 100):
                    return await inter.response.send_message(f"{negativo} A quantidade deve ser um número entre 1 e 100.", ephemeral=True)
            except ValueError:
                return await inter.response.send_message(f"{negativo} A quantidade deve ser um número válido.", ephemeral=True)
            
            prefixo = inter.text_values.get("prefixo", "")
            all_keys = carregar_json("Database/Comunidade/generated_keys.json", [])
            
            novas_keys = [f"{prefixo}{str(uuid.uuid4())}" for _ in range(quantidade)]
            all_keys.extend(novas_keys)
            salvar_json("Database/Comunidade/generated_keys.json", all_keys)

            keys_text = "\n".join(novas_keys)
            keys_file = io.BytesIO(keys_text.encode('utf-8'))
            
            await inter.response.send_message(
                f"{positivo} {quantidade} keys geradas com sucesso! Salve-as na sua DM.",
                file=disnake.File(fp=keys_file, filename="keys.txt"),
                components=[disnake.ui.Button(label="Salvar na DM", custom_id="keys_save_dm")])
        #endregion

        #region Modal Handlers IA
        elif custom_id == "ia_modal_prompt":
            prompt = inter.text_values["prompt"].strip()
            config = carregar_json("Database/Comunidade/ia.json")
            config["prompt"] = prompt
            salvar_json("Database/Comunidade/ia.json", config)
            await self.mostrar_painel_ia(inter)
        #endregion

    #region Funções de Exibição de Painel
    async def mostrar_painel_ia(self, inter: disnake.Interaction):
        config = carregar_json("Database/Comunidade/ia.json")

        status_conversa = config.get("status_conversa", False)
        status_imagem = config.get("status_imagem", False)
        status_audio = config.get("status_audio", False)
        status_voz = config.get("status_voz", False)
        
        canal_texto = self.bot.get_channel(config.get("canal_texto_id"))
        canal_voz = self.bot.get_channel(config.get("canal_voz_id"))

        embed = disnake.Embed(title="🤖 Painel de Inteligência Artificial", description="Configure os módulos de IA do bot. Lembre-se que **Conversa** e **Áudio** não podem ser ativados ao mesmo tempo.", color=disnake.Color.blue())
        
        field_status = (
            f"**Conversa (Texto):** {ligado if status_conversa else desligado}\n"
            f"**Geração de Imagem:** {ligado if status_imagem else desligado}\n"
            f"**Geração de Áudio:** {f'{ligado} Ativo' if status_audio else desligado}\n"
            f"**Conversa (Voz):** {ligado if status_voz else desligado}"
        )
        field_config = (
            f"**Canal de Texto:** {canal_texto.mention if canal_texto else 'Não definido'}\n"
            f"**Canal de Voz:** {canal_voz.mention if canal_voz else 'Não definido'}"
        )
        
        embed.add_field(name="Status dos Módulos", value=field_status, inline=False)
        embed.add_field(name="Configurações", value=field_config, inline=False)
        embed.add_field(name="Prompt Atual", value=f"```{config.get('prompt', 'Nenhum')}```", inline=False)
        
        components = [
            [
                disnake.ui.Button(label="Conversa", custom_id="ia_toggle_conversa", style=disnake.ButtonStyle.success if status_conversa else disnake.ButtonStyle.danger, emoji=reload),
                disnake.ui.Button(label="Imagens", custom_id="ia_toggle_imagem", style=disnake.ButtonStyle.success if status_imagem else disnake.ButtonStyle.danger, emoji=reload),
                disnake.ui.Button(label="Áudio", custom_id="ia_toggle_audio", style=disnake.ButtonStyle.success if status_audio else disnake.ButtonStyle.danger, emoji=reload),
                disnake.ui.Button(label="Voz", custom_id="ia_toggle_voz", style=disnake.ButtonStyle.success if status_voz else disnake.ButtonStyle.danger, emoji=reload),
            ],
            [
                disnake.ui.Button(label="Canal da IA", custom_id="ia_canal_texto", emoji=canalText),
                disnake.ui.Button(label="Canal de Voz", custom_id="ia_canal_voz", emoji="📞", disabled=not status_voz),
                disnake.ui.Button(label="Configurar IA", custom_id="ia_configurar_prompt", emoji=config2)
            ],
            [
                disnake.ui.Button(label="Voltar", emoji=voltar, style=disnake.ButtonStyle.grey, custom_id="GerenciarPainelComunidade")
            ]
        ]
        
        try:
            await inter.response.edit_message(embed=embed, components=components, content=None, attachments=[])
        except disnake.errors.InteractionResponded:
            await inter.edit_original_message(embed=embed, components=components, content=None, attachments=[])

    async def mostrar_painel_instagram_selecao(self, inter: disnake.Interaction):
        embed = disnake.Embed(
            title="Módulos do Instagram",
            description="Escolha qual sistema relacionado ao Instagram você deseja configurar.",
            color=0xc4302b
        )
        components = [
            [
                disnake.ui.Button(label="Instagram", emoji="<:instagram:1376634810256326707>", custom_id="comunidade_instagram"),
                disnake.ui.Button(label="Instapet", emoji="<:instagram:1376634810256326707>", custom_id="comunidade_instapet"),
                disnake.ui.Button(label="Influenciar", emoji="<:instagram:1376634810256326707>", custom_id="comunidade_influenciar")
            ],
            [
                disnake.ui.Button(label="Voltar", emoji=voltar, style=disnake.ButtonStyle.grey, custom_id="GerenciarPainelComunidade")
            ]
        ]
        await inter.response.edit_message(embed=embed, components=components, content=None, attachments=[])

    async def mostrar_painel_instagram(self, inter: disnake.Interaction):
        config = carregar_json("Database/Comunidade/instagram.json", {"canal_id": None, "prefixo": "ig!", "cargo_id": None, "tema": "azul"})
        embed = disnake.Embed(title="Sistema Instagram", description="Configure o sistema de integração com Instagram:", color=CORES_TEMAS.get(config["tema"], 0x0066FF))
        canal = self.bot.get_channel(config["canal_id"]) if config["canal_id"] else None
        role_obj = inter.guild.get_role(config["cargo_id"]) if config["cargo_id"] else None
        embed.add_field(name="Configurações Atuais", value=f"> **Canal:** {canal.mention if canal else 'Não definido'}\n> **Prefixo:** `{config['prefixo']}`\n> **Cargo:** {role_obj.mention if role_obj else 'Não definido'}\n> **Tema:** {config['tema'].title()}", inline=False)
        components = [[disnake.ui.Button(label="Definir Canal", emoji=canalText, custom_id="instagram_canal"), disnake.ui.Button(label="Definir Prefixo", emoji=config2, custom_id="instagram_prefixo")], [disnake.ui.Button(label="Definir Cargo", emoji=cargo, custom_id="instagram_cargo"), disnake.ui.Button(label="Selecionar Tema", emoji=personalizarE, custom_id="instagram_tema")], [disnake.ui.Button(label="Voltar", emoji=voltar, style=disnake.ButtonStyle.grey, custom_id="comunidade_instagram_selecao_btn")]]
        await inter.response.edit_message(embed=embed, components=components, content=None, attachments=[])

    async def mostrar_painel_instapet(self, inter: disnake.Interaction):
        config = carregar_json("Database/Comunidade/instapet.json", {"canal_id": None, "prefixo": "pet!", "cargo_id": None, "tema": "amarelo"})
        embed = disnake.Embed(title="Sistema Instapet", description="Configure o sistema de integração com Instapet:", color=CORES_TEMAS.get(config["tema"], 0xFFFF00))
        canal = self.bot.get_channel(config["canal_id"]) if config["canal_id"] else None
        role_obj = inter.guild.get_role(config["cargo_id"]) if config["cargo_id"] else None
        embed.add_field(name="Configurações Atuais", value=f"> **Canal:** {canal.mention if canal else 'Não definido'}\n> **Prefixo:** `{config['prefixo']}`\n> **Cargo:** {role_obj.mention if role_obj else 'Não definido'}\n> **Tema:** {config['tema'].title()}", inline=False)
        components = [[disnake.ui.Button(label="Definir Canal", emoji=canalText, custom_id="instapet_canal"), disnake.ui.Button(label="Definir Prefixo", emoji=config2, custom_id="instapet_prefixo")], [disnake.ui.Button(label="Definir Cargo", emoji=cargo, custom_id="instapet_cargo"), disnake.ui.Button(label="Selecionar Tema", emoji=personalizarE, custom_id="instapet_tema")], [disnake.ui.Button(label="Voltar", emoji=voltar, style=disnake.ButtonStyle.grey, custom_id="comunidade_instagram_selecao_btn")]]
        await inter.response.edit_message(embed=embed, components=components, content=None, attachments=[])

    async def mostrar_painel_influenciar(self, inter: disnake.Interaction):
        config = carregar_json("Database/Comunidade/influenciar.json")
        embed = disnake.Embed(title="Sistema Influenciar", description="Configure o sistema para influenciadores:", color=CORES_TEMAS.get(config.get("tema"), 0x9900FF))
        canal = self.bot.get_channel(config.get("canal_id"))
        role_obj = inter.guild.get_role(config.get("cargo_id"))
        hall_channel = self.bot.get_channel(config.get("hall_channel_id"))
        embed.add_field(name="Configurações Atuais", value=f"> **Canal de Posts:** {canal.mention if canal else 'Não definido'}\n> **Prefixo:** `{config.get('prefixo', 'inf!')}`\n> **Cargo de Permissão:** {role_obj.mention if role_obj else 'Não definido'}\n> **Tema:** {config.get('tema', 'roxo').title()}\n> **Hall da Fama:** {hall_channel.mention if hall_channel else 'Não definido'}", inline=False)
        components = [[disnake.ui.Button(label="Definir Canal", emoji=canalText, custom_id="influenciar_canal"), disnake.ui.Button(label="Definir Prefixo", emoji=config2, custom_id="influenciar_prefixo")], [disnake.ui.Button(label="Definir Cargo", emoji=cargo, custom_id="influenciar_cargo"), disnake.ui.Button(label="Selecionar Tema", emoji=personalizarE, custom_id="influenciar_tema")], [disnake.ui.Button(label="Configurar Hall", emoji="🏆", custom_id="influenciar_hall")],[disnake.ui.Button(label="Voltar", emoji=voltar, style=disnake.ButtonStyle.grey, custom_id="comunidade_instagram_selecao_btn")]]
        await inter.response.edit_message(embed=embed, components=components, content=None, attachments=[])

    async def mostrar_painel_tempcall(self, inter: disnake.Interaction):
        config = carregar_json("Database/Comunidade/calltemp.json", {"categoria_id": None, "cargo_id": None, "ativo": False, "canal_voz_id": None})
        embed = disnake.Embed(title="Sistema Temp Call", description="Configure o sistema de canais de voz temporários:", color=0x9b59b6)
        categoria = inter.guild.get_channel(config.get("categoria_id"))
        role_obj = inter.guild.get_role(config.get("cargo_id"))
        canal_voz = inter.guild.get_channel(config.get("canal_voz_id"))
        embed.add_field(name="Configurações Atuais", value=f"> **Canal 'Junte-se para criar':** {canal_voz.mention if canal_voz else 'Não definido'}\n> **Categoria para Calls:** {categoria.name if categoria else 'Não definida'}\n> **Cargo Bypass:** {role_obj.mention if role_obj else 'Não definido'}\n> **Status:** {'🟢 Ativo' if config.get('ativo') else '🔴 Inativo'}", inline=False)
        components = [[disnake.ui.Button(label="Definir Canal de Voz", emoji="<:thxcall:1396066223241953341>", custom_id="tempcall_canal_voz"), disnake.ui.Button(label="Definir Categoria", emoji=canalText, custom_id="tempcall_categoria")], [disnake.ui.Button(label="Definir Cargo", emoji=cargo, custom_id="tempcall_cargo"), disnake.ui.Button(label="Desativar" if config.get('ativo') else "Ativar", emoji=reload if config.get('ativo') else reload, style=disnake.ButtonStyle.red if config.get('ativo') else disnake.ButtonStyle.green, custom_id="tempcall_toggle")], [disnake.ui.Button(label="Voltar", emoji=voltar, style=disnake.ButtonStyle.grey, custom_id="GerenciarPainelComunidade")]]
        await inter.response.edit_message(embed=embed, components=components, content=None, attachments=[])

    async def mostrar_painel_keys(self, inter: disnake.Interaction):
        config = carregar_json("Database/Comunidade/keys.json", {"status": False, "canal_logs_id": None, "cargo_id": None, "canal_keys_id": None})
        generated_keys = carregar_json("Database/Comunidade/generated_keys.json", [])
        status = config.get("status", False)
        canal_logs = self.bot.get_channel(config.get("canal_logs_id"))
        cargo_obj = inter.guild.get_role(config.get("cargo_id"))
        canal_keys = self.bot.get_channel(config.get("canal_keys_id"))
        embed = disnake.Embed(title="Sistema de Keys", description="Gerencie o sistema de geração e resgate de keys.", color=disnake.Color.gold())
        embed.add_field(name="Configuração Atual", value=f"**Status:** { f'{ligado} Ativo' if status else f'{desligado} Inativo'}\n**Canal de Logs:** {canal_logs.mention if canal_logs else 'Não definido'}\n**Cargo de Acesso:** {cargo_obj.mention if cargo_obj else 'Não definido'}\n**Canal de Resgate:** {canal_keys.mention if canal_keys else 'Não definido'}", inline=False)
        embed.add_field(name="Banco de Dados", value=f"**Keys Geradas:** {len(generated_keys)}", inline=False)
        on_off_button = disnake.ui.Button(label="Desativar" if status else "Ativar", custom_id="keys_onoff", emoji=reload if status else reload, style=disnake.ButtonStyle.danger if status else disnake.ButtonStyle.success)
        components = [
            [on_off_button, disnake.ui.Button(label="Logs", custom_id="keys_canallogs", emoji=canalText), disnake.ui.Button(label="Cargo", custom_id="keys_configcargo", emoji=cargo), disnake.ui.Button(label="Canal Resgate", custom_id="keys_canalkeys", emoji="📺")],
            [disnake.ui.Button(label="Criar Keys", custom_id="keys_criarkeys", emoji=mais2, style=disnake.ButtonStyle.secondary), disnake.ui.Button(label="Deletar Keys", custom_id="keys_deletarkeys", emoji=apagar, style=disnake.ButtonStyle.secondary, disabled=not generated_keys)],
            [disnake.ui.Button(label="Resetar Keys", custom_id="keys_resetarkeys", emoji=apagar, style=disnake.ButtonStyle.danger, disabled=not generated_keys), disnake.ui.Button(label="Resetar Config", custom_id="keys_resetartudo", emoji=reload, style=disnake.ButtonStyle.danger)],
            [disnake.ui.Button(label="Voltar", emoji=voltar, style=disnake.ButtonStyle.grey, custom_id="GerenciarPainelComunidade")]]
        try:
            await inter.response.edit_message(embed=embed, components=components, content=None, attachments=[])
        except disnake.errors.InteractionResponded:
            await inter.edit_original_message(embed=embed, components=components, content=None, attachments=[])
    #endregion
    
    #region Funções de Formulário
    async def criar_formulario(self, inter: disnake.Interaction, tipo: str):
        modal = disnake.ui.Modal(title=f"Criar Formulário ({tipo.title()})", custom_id=f"modal_criar_formulario_{tipo}", components=[disnake.ui.TextInput(label="Nome do Formulário", placeholder="Ex: Formulário de Candidatura", custom_id="nome", style=disnake.TextInputStyle.short, max_length=100, required=True)])
        await inter.response.send_modal(modal)
    async def mostrar_painel_selecao_formulario(self, inter: disnake.Interaction, edit: bool = False):
        embed = disnake.Embed(title="Sistema de Formulários", description="Gerencie formulários para sua comunidade:", color=0x3498db)
        embed.add_field(name="Opções Disponíveis", value="> Crie ou selecione um formulário abaixo para gerenciar.", inline=False)
        formularios = carregar_json("Database/Comunidade/formularios.json")
        components = []
        if formularios:
            options = [disnake.SelectOption(label=form_data.get("nome", f"Formulário {form_id[:8]}"), value=form_id, description=f"Tipo: {form_data.get('tipo', 'N/A').title()} | Perguntas: {len(form_data.get('perguntas', []))}") for form_id, form_data in list(formularios.items())]
            if options: components.append([disnake.ui.Select(placeholder="Selecione um formulário para gerenciar...", custom_id="gerenciar_formulario", options=options[:25])])
        components.append([disnake.ui.Button(label="Criar Formulário (Modal)", emoji=mensagem, custom_id="form_modal_criar"), disnake.ui.Button(label="Criar Formulário (Tópico)", emoji=diretorio, custom_id="form_topico_criar")])
        components.append([disnake.ui.Button(label="Voltar", emoji=voltar, style=disnake.ButtonStyle.grey, custom_id="GerenciarPainelComunidade")])
        
        if edit:
            await inter.response.edit_message(embed=embed, components=components, content=None, attachments=[])
        else:
            # Esta parte provavelmente não será usada com a nova lógica de select, mas mantida por segurança.
            await inter.response.send_message(embed=embed, components=components, ephemeral=True)

    async def mostrar_painel_formulario(self, inter, form_id):
        formularios = carregar_json("Database/Comunidade/formularios.json")
        if form_id not in formularios: return await inter.response.send_message(f"{negativo} Formulário não encontrado!", ephemeral=True)
        form_data = formularios[form_id]
        cargo_obj = inter.guild.get_role(form_data.get("cargo_aprovado")) if form_data.get("cargo_aprovado") else None
        embed = disnake.Embed(title=f"Editando: {form_data['nome']}", description=f"Gerencie as configurações do formulário.\n\n**ID:** `{form_id}`\n**Tipo:** {form_data['tipo'].title()}", color=0x3498db)
        embed.add_field(name="Configurações", value=f"**Cargo Aprovado:** {cargo_obj.mention if cargo_obj else 'Não definido'}\n**Perguntas:** {len(form_data['perguntas'])}", inline=False)
        components = [
            [
                disnake.ui.Button(label="Aparência", emoji=personalizarE, custom_id=f"form_aparencia_{form_id}"),
                disnake.ui.Button(label="Perguntas", emoji=duvida, custom_id=f"form_perguntas_{form_id}"),
                disnake.ui.Button(label="Cargo", emoji=cargo, custom_id=f"form_cargo_{form_id}")
            ],
            [
                disnake.ui.Button(label="Enviar", emoji=arrow, style=disnake.ButtonStyle.green, custom_id=f"enviar_form_{form_id}"),
                disnake.ui.Button(label="Apagar", style=disnake.ButtonStyle.danger, emoji=apagar, custom_id=f"form_delete_{form_id}")
            ],
            [
                disnake.ui.Button(label="Voltar", emoji=voltar, style=disnake.ButtonStyle.grey, custom_id="comunidade_formulario")
            ]
        ]
        try: await inter.response.edit_message(embed=embed, components=components, content=None, attachments=[])
        except disnake.errors.InteractionResponded: await inter.edit_original_message(embed=embed, components=components, content=None, attachments=[])
        except Exception: await inter.response.send_message(embed=embed, components=components, ephemeral=True)
    async def mostrar_edicao_perguntas(self, inter, form_id, edit=False):
        formularios = carregar_json("Database/Comunidade/formularios.json")
        form_data = formularios.get(form_id, {})
        perguntas = form_data.get("perguntas", [])
        limite = 5 if form_data.get("tipo") == "modal" else 25
        embed = disnake.Embed(title="Editar Perguntas", description=f"Gerencie as perguntas do formulário.\n\n**Total de perguntas:** {len(perguntas)}/{limite}", color=0xf39c12)
        if perguntas: embed.add_field(name="Perguntas Atuais", value="\n".join([f"{i+1}. {p}" for i, p in enumerate(perguntas)])[:1024], inline=False)
        components = [[disnake.ui.Button(label="Adicionar Pergunta", emoji=mais2, style=disnake.ButtonStyle.success, custom_id=f"add_pergunta_{form_id}", disabled=(len(perguntas) >= limite)), disnake.ui.Button(label="Remover Pergunta", emoji=menos2, style=disnake.ButtonStyle.danger, custom_id=f"remove_pergunta_{form_id}", disabled=(not perguntas))], [disnake.ui.Button(label="Voltar", emoji=voltar, style=disnake.ButtonStyle.grey, custom_id=f"form_show_{form_id}")]]
        await inter.response.edit_message(embed=embed, components=components, content=None, attachments=[])
    async def mostrar_edicao_cargo(self, inter, form_id):
        role_select = disnake.ui.RoleSelect(custom_id=f"selecionar_cargo_form_role_{form_id}", placeholder="Selecione o cargo de aprovado...")
        await inter.response.send_message("Selecione o cargo de aprovado para o formulário.", components=[role_select], ephemeral=True)
    async def mostrar_edicao_aparencia(self, inter, form_id, edit=False):
        formularios = carregar_json("Database/Comunidade/formularios.json")
        form_data = formularios.get(form_id, {})
        embed_data = form_data.get("embed", {})
        botao_data = form_data.get("botao", {})
        content = form_data.get("content", "Nenhum")
        embed = disnake.Embed(title="Editar Aparência", description="Configure a aparência da mensagem do seu formulário.", color=embed_data.get("color", 0xe74c3c))
        embed.add_field(name="Conteúdo da Mensagem", value=f"```{content[:1000] if content else 'Nenhum'}```", inline=False)
        embed.add_field(name="Botão", value=f"**Label:** {botao_data.get('label', 'N/A')}\n**Emoji:** {botao_data.get('emoji', 'N/A') or 'Nenhum'}\n**Cor:** {botao_data.get('style', 'N/A').title()}", inline=True)
        embed.add_field(name="Embed", value=f"**Título:** {embed_data.get('title', 'N/A')}", inline=True)
        components = [[disnake.ui.Button(label="Editar Conteúdo", emoji=mensagem, custom_id=f"edit_content_{form_id}"), disnake.ui.Button(emoji=apagar, style=disnake.ButtonStyle.danger, custom_id=f"clear_content_{form_id}")], [disnake.ui.Button(label="Editar Embed", emoji=embedE, custom_id=f"edit_embed_{form_id}"), disnake.ui.Button(emoji=apagar, style=disnake.ButtonStyle.danger, custom_id=f"reset_embed_{form_id}")], [disnake.ui.Button(label="Editar Botão", emoji=editar, custom_id=f"edit_button_{form_id}")], [disnake.ui.Button(label="Voltar", emoji=voltar, style=disnake.ButtonStyle.grey, custom_id=f"form_show_{form_id}")]]
        if edit:
            try: await inter.response.edit_message(embed=embed, components=components, content=None)
            except disnake.errors.InteractionResponded: await inter.edit_original_message(embed=embed, components=components, content=None)
        else: await inter.response.edit_message(embed=None, components=components, content=None)
    #endregion
    
def setup(bot: commands.Bot):
    bot.add_cog(ComunidadeCommand(bot))