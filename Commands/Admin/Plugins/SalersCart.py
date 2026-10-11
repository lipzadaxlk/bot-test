import disnake
from disnake.ext import commands, tasks
import json
import os
import asyncio
import random
import string
import requests
from datetime import datetime, timedelta

try:
    from Functions.CarregarEmojis import *
    from Functions.Config.FormasPagamentos import ObterFormasPagamento, MercadoPagoPagamento, SemiAutoPagamento
    from Functions.VerificarPerms import verificar_permissao
    from Commands.Admin.Plugins.ECloud import ObterPsicoConfig, ObterAuthLocal, API_URL
except ImportError:
    positivo, negativo, carregarAnimado, editar, arrow, check, carrinhoCancelado, apagar, pix = "✅", "❌", "⚙️", "📝", "➡️", "✔️", "🗑️", "🗑️", "💳"
    def verificar_permissao(user_id): return True
    def ObterPsicoConfig(): return {}
    def ObterAuthLocal(): return {}
    API_URL = ""

SALERS_CARRINHOS_PATH = os.path.join("Database", "Vendas", "salers_carrinhos.json")
MAIN_CONFIG_PATH = os.path.join("Database", "Vendas", "configuracao.json")
LOGS_CANAIS_PATH = os.path.join("Database", "Server", "canais.json")

tasksPagamento = {}
salers_cart_tasks = {}

def obter_json(path):
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f: json.dump({}, f)
        return {}
    with open(path, "r", encoding="utf-8") as f: return json.load(f)

def salvar_json(data, path):
    with open(path, "w", encoding="utf-8") as f: json.dump(data, f, indent=4)

def obter_membros_disponiveis_ecloud():
    """Verifica a quantidade de membros disponíveis na API eCloud."""
    auth_local = ObterAuthLocal()
    if not auth_local.get("authorization"):
        return None, "A API eCloud principal não está configurada."

    headers = {"authorization": auth_local["authorization"]}
    try:
        response = requests.get(f"{API_URL}members", headers=headers, timeout=5)
        if response.status_code == 200:
            return int(response.json().get("message", 0)), None
        else:
            error_msg = response.json().get('message', f'Erro HTTP {response.status_code}')
            return None, f"Falha ao consultar membros na API: {error_msg}"
    except requests.exceptions.RequestException as e:
        return None, f"Não foi possível conectar à API eCloud: {e}"
    except (ValueError, KeyError):
        return None, "A resposta da API de membros foi inesperada."

def obter_salers_config():
    with open(MAIN_CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f).get("salers_members", {})

def obter_carrinho_membros(cart_id):
    return obter_json(SALERS_CARRINHOS_PATH).get(cart_id)

def gerar_string():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=13))

class Logs:
    @staticmethod
    async def Enviar(inter, embed):
        try:
            with open(LOGS_CANAIS_PATH, encoding="utf-8") as f: db = json.load(f)
            if not db.get("logs"): return
            channel = inter.guild.get_channel(int(db["logs"]))
            if channel: await channel.send(embed=embed)
        except Exception: pass

class SalersPagamentos:
    @staticmethod
    def SalvarCarrinho(carrinho, carrinhoID):
        carrinhos = obter_json(SALERS_CARRINHOS_PATH)
        carrinhos[carrinhoID] = carrinho
        salvar_json(carrinhos, SALERS_CARRINHOS_PATH)

    @staticmethod
    def GerarPagamento(carrinhoID: str):
        carrinho = obter_carrinho_membros(carrinhoID)
        valor_final = float(carrinho["info"]["valorFinal"])
        formas_pagamento = ObterFormasPagamento()
        if formas_pagamento.get("mercadopago", {}).get("habilitado"):
            qr_code, qrcodeURL, payment = MercadoPagoPagamento.GerarPagamento(valor_final)
            carrinho["info"]["pagamento"] = {"url": qrcodeURL, "paymentID": payment, "copiacola": qr_code, "metodo": "MercadoPago"}
            SalersPagamentos.SalvarCarrinho(carrinho, carrinhoID)
            return "MercadoPago"
        elif formas_pagamento.get("semiauto", {}).get("habilitado"):
            chave, qr_code = SemiAutoPagamento.GerarPagamento()
            if not chave.startswith("55") and formas_pagamento["semiauto"]["tipoPix"] == "telefone":
                chave = "55" + chave
            carrinho["info"]["pagamento"] = {"copiacola": chave, "url": qr_code, "metodo": "SemiAuto"}
            SalersPagamentos.SalvarCarrinho(carrinho, carrinhoID)
            return "SemiAuto"
        return None

class PuxarMembrosModal(disnake.ui.Modal):
    def __init__(self, carrinho_id):
        self.carrinho_id = carrinho_id
        super().__init__(
            title="Puxar Membros para o Servidor",
            components=[
                disnake.ui.TextInput(
                    label="ID do Servidor de Destino",
                    custom_id="guild_id",
                    placeholder="Cole o ID do servidor onde você adicionou o bot"
                )
            ]
        )
    
    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)
        guild_id_str = inter.text_values["guild_id"]
        bot = inter.bot
        
        try:
            guild_id = int(guild_id_str)
            if not bot.get_guild(guild_id):
                await inter.followup.send(f"{negativo} O bot não está no servidor com o ID fornecido.", ephemeral=True)
                return
        except (ValueError, TypeError):
            await inter.followup.send(f"{negativo} ID de servidor inválido.", ephemeral=True)
            return

        auth_local = ObterAuthLocal()
        if not auth_local.get("authorization"):
            await inter.followup.send(f"{negativo} A API eCloud principal não está configurada.", ephemeral=True)
            return
            
        headers = {"authorization": auth_local["authorization"]}
        carrinho = obter_carrinho_membros(self.carrinho_id)
        quantidade = carrinho["info"]["quantidade"]

        payload = {
            "guildID": guild_id_str,
            "quantity": quantidade
        }
        url_endpoint = f"{API_URL}pullmembers/1"

        try:
            response = requests.post(url=url_endpoint, headers=headers, json=payload, timeout=10)
            
            if response.status_code == 202 or response.status_code == 200:
                await inter.followup.send(f"{positivo} A transferência de **{quantidade}** membros foi iniciada! Este carrinho será fechado.", ephemeral=True)
                log_embed = disnake.Embed(title="Membros Puxados com Sucesso", description=f"{inter.author.mention} puxou `{quantidade}` membros para o servidor `{guild_id_str}`.", color=disnake.Color.green())
                await Logs.Enviar(inter, log_embed)
                await asyncio.sleep(2)
                await inter.channel.delete()
            else:
                await inter.followup.send(f"{negativo} Falha ao iniciar o processo: {response.json().get('message')}", ephemeral=True)
        
        except requests.exceptions.Timeout:
             await inter.followup.send(f"{positivo} Processo iniciado (API demorou). Este carrinho será fechado.", ephemeral=True)
             await asyncio.sleep(2)
             await inter.channel.delete()
        except requests.exceptions.RequestException:
            await inter.followup.send(f"{negativo} Não foi possível conectar à API eCloud.", ephemeral=True)
          
class EditarMembrosModal(disnake.ui.Modal):
    def __init__(self, carrinho_id):
        self.carrinho_id = carrinho_id
        carrinho = obter_carrinho_membros(carrinho_id)
        super().__init__(title="Editar Quantidade de Membros", components=[disnake.ui.TextInput(label="Quantidade Desejada", custom_id="quantidade", value=str(carrinho["info"]["quantidade"]))])

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)

        # 1. Validar quantidade mínima
        salers_config = obter_salers_config()
        min_membros = salers_config.get("min_membros", 100)
        try:
            quantidade = int(inter.text_values["quantidade"])
            if quantidade < min_membros:
                await inter.followup.send(f"{negativo} A quantidade não pode ser menor que `{min_membros}`.", ephemeral=True)
                return
        except ValueError:
            await inter.followup.send(f"{negativo} Por favor, insira um número válido.", ephemeral=True)
            return

        # 2. Verificar limite de membros disponíveis na eCloud
        membros_disponiveis, erro = obter_membros_disponiveis_ecloud()
        if erro:
            await inter.followup.send(f"{negativo} {erro}", ephemeral=True)
            return
        
        if quantidade > membros_disponiveis:
            await inter.followup.send(f"{negativo} O pedido máximo é de `{membros_disponiveis}` membros.", ephemeral=True)
            return

        # 3. Salvar e atualizar a mensagem do carrinho
        carrinho = obter_carrinho_membros(self.carrinho_id)
        carrinho["info"]["quantidade"] = quantidade
        SalersPagamentos.SalvarCarrinho(carrinho, self.carrinho_id)
        embed, components = obter_mensagem_carrinho_membros(self.carrinho_id)
        
        # Edita a mensagem original no canal que contém o carrinho
        await inter.message.edit(embed=embed, components=components)
        await inter.followup.send(f"{positivo} Quantidade atualizada.", ephemeral=True)

def obter_mensagem_carrinho_membros(carrinho_id):
    carrinho = obter_carrinho_membros(carrinho_id)
    salers_config = obter_salers_config()
    quantidade = carrinho["info"]["quantidade"]
    valor = quantidade * salers_config.get("valor_por_membro")
    
    embed = disnake.Embed(
        title=f"Olá, bem-vindo ao carrinho de compra de Membros!",
        description=f"-# Você está prestes a comprar **{quantidade} Membros reais** para o seu servidor, com controle de qualidade e **Premium**.",
        color=0x3498DB
    )
    
    embed.add_field(
        name="**Membros Premium (Selecionado)**",
        value=f"{quantidade} membros reais - **R$ {valor:.2f}**",
        inline=False
    )
    
    embed.add_field(
        name="**Importante**",
        value="Todos os membros são reais e ativos, sem nenhum risco de banimento",
        inline=False
    )
    
    embed.set_footer(text=f"Hoje às {datetime.now().strftime('%H:%M')}")
    
    row = [
        disnake.ui.Button(emoji=menos2, style=disnake.ButtonStyle.red, custom_id=f"salers_cart_diminuir_{carrinho_id}"),
        disnake.ui.Button(emoji=editar, style=disnake.ButtonStyle.secondary, custom_id=f"salers_cart_editar_{carrinho_id}"),
        disnake.ui.Button(emoji=mais2, style=disnake.ButtonStyle.green, custom_id=f"salers_cart_aumentar_{carrinho_id}"),
    ]
    row_pagamento = [
        disnake.ui.Button(label="Continuar", emoji=arrow, style=disnake.ButtonStyle.primary, custom_id=f"salers_cart_continuar_{carrinho_id}"),
        disnake.ui.Button(label="Cancelar", emoji=apagar, style=disnake.ButtonStyle.grey, custom_id=f"salers_cart_cancelar_{carrinho_id}")
    ]
    return embed, [row, row_pagamento]

def obter_mensagem_pagamento_salers(inter, cart_id):
    carrinho = obter_carrinho_membros(cart_id)
    embed = disnake.Embed(title=f"{pix} Pagamento via PIX Criado", color=disnake.Color(0x00FFFF), timestamp=datetime.now())
    embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon.url if inter.guild.icon else None)
    embed.add_field(name="Expira em", value=f"<t:{int((datetime.now() + timedelta(minutes=10)).timestamp())}:R>", inline=True)
    embed.add_field(name="Valor final", value=f"`R${carrinho['info']['valorFinal']}`", inline=True)
    embed.add_field(name="Código Copia e Cola", value=f"```{carrinho['info']['pagamento']['copiacola']}```", inline=False)
    embed.set_author(name=inter.author.name, icon_url=inter.author.display_avatar.url)
    embed.set_image(url=carrinho["info"]["pagamento"]["url"])
    components = [
        disnake.ui.Button(label="Código Copia e Cola", emoji=check, custom_id=f"salers_cart_copiacola_{cart_id}"),
        disnake.ui.Button(style=disnake.ButtonStyle.red, label="Cancelar", emoji=apagar, custom_id=f"salers_cart_cancelar_{cart_id}")
    ]
    return embed, components

class SalersCartExtension(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _cancel_task(self, cart_id):
        if cart_id in salers_cart_tasks:
            salers_cart_tasks[cart_id].cancel()
            del salers_cart_tasks[cart_id]
        if cart_id in tasksPagamento:
            tasksPagamento[cart_id].cancel()
            del tasksPagamento[cart_id]

    async def _start_cart_countdown(self, inter, cart_id, duration_seconds):
        await asyncio.sleep(duration_seconds)
        if cart_id in obter_json(SALERS_CARRINHOS_PATH):
            await self._cancel_cart(inter, cart_id, reason="O carrinho expirou por inatividade.")

    async def _cancel_cart(self, inter, cart_id, reason="O carrinho foi cancelado pelo usuário."):
        await self._cancel_task(cart_id)
        carrinhos = obter_json(SALERS_CARRINHOS_PATH)
        carrinho = carrinhos.pop(cart_id, None)
        if not carrinho: return
        salvar_json(carrinhos, SALERS_CARRINHOS_PATH)
        
        try:
            channel = await self.bot.fetch_channel(carrinho["server"]["carrinho"])
            await channel.delete()
        except (disnake.NotFound, AttributeError, KeyError):
            pass
            
        log_embed = disnake.Embed(title=f"{carrinhoCancelado} Carrinho de Membros Cancelado", description=reason, color=disnake.Color.red())
        log_embed.add_field(name="Usuário", value=f"{inter.author.mention} (`{inter.author.id}`)")
        await Logs.Enviar(inter, log_embed)
        
        try:
            dm_embed = disnake.Embed(title=f"{carrinhoCancelado} Carrinho Fechado", description=f"O seu carrinho de membros foi encerrado com sucesso. Caso precise comprar membros ou revisar o preço e quantidade, sinta-se à vontade para abrir um novo carrinho a qualquer momento.\n\n**Motivo:** {reason}", color=disnake.Color.red())
            await inter.author.send(embed=dm_embed)
        except (disnake.Forbidden, AttributeError):
            pass

    async def _update_cart_quantity(self, inter, cart_id, amount_change):
        await inter.response.defer()

        carrinhos = obter_json(SALERS_CARRINHOS_PATH)
        carrinho = carrinhos.get(cart_id)
        if not carrinho:
            return await inter.edit_original_response(content="Carrinho não encontrado.", embed=None, components=[])

        nova_quantidade = carrinho["info"]["quantidade"] + amount_change
        salers_config = obter_salers_config()
        min_membros = salers_config.get("min_membros", 100)

        if nova_quantidade < min_membros:
            await inter.followup.send(f"{negativo} A quantidade não pode ser menor que `{min_membros}`.", ephemeral=True)
            return await inter.edit_original_response(content=None) # Remove o "carregando..."

        if amount_change > 0:
            membros_disponiveis, erro = obter_membros_disponiveis_ecloud()
            if erro:
                await inter.followup.send(f"{negativo} {erro}", ephemeral=True)
                return await inter.edit_original_response(content=None)

            if nova_quantidade > membros_disponiveis:
                nova_quantidade = membros_disponiveis
                await inter.followup.send(f"{negativo} Você só possui `{membros_disponiveis}` membros. A quantidade foi ajustada para o máximo.", ephemeral=True)

        carrinho["info"]["quantidade"] = nova_quantidade
        SalersPagamentos.SalvarCarrinho(carrinho, cart_id)
        embed, comps = obter_mensagem_carrinho_membros(cart_id)
        await inter.edit_original_response(embed=embed, components=comps)

    async def _proceed_to_payment(self, inter, cart_id):
        await self._cancel_task(cart_id)
        carrinhos = obter_json(SALERS_CARRINHOS_PATH)
        carrinho = carrinhos.get(cart_id)
        if not carrinho: return

        salers_config = obter_salers_config()
        quantidade = carrinho["info"]["quantidade"]
        valor_final = quantidade * salers_config.get("valor_por_membro")
        carrinho["info"]["valorFinal"] = f"{valor_final:.2f}"
        SalersPagamentos.SalvarCarrinho(carrinho, cart_id)
        
        metodo_pagamento = SalersPagamentos.GerarPagamento(cart_id)
        if not metodo_pagamento:
            return await inter.response.edit_message(content=f"{negativo} Nenhuma forma de pagamento está configurada.", components=[], embed=None)
        
        embed, components = obter_mensagem_pagamento_salers(inter, cart_id)
        
        if metodo_pagamento == "SemiAuto":
            botao_aprovar = disnake.ui.Button(
                style=disnake.ButtonStyle.green, 
                label="Confirmar Pagamento", 
                emoji=check, 
                custom_id=f"salers_cart_aprovar_manual_{cart_id}"
            )
            components.insert(1, botao_aprovar)
        
        await inter.response.edit_message(embed=embed, components=components)
        
        salers_cart_tasks[cart_id] = self.bot.loop.create_task(self._start_cart_countdown(inter, cart_id, 900))

        if metodo_pagamento == "MercadoPago":
            tasksPagamento[cart_id] = self.bot.loop.create_task(self.verificar_pagamento_mp(inter, cart_id))
          
    async def _finalize_purchase(self, inter, cart_id):
        await self._cancel_task(cart_id)
        
        log_embed = disnake.Embed(title=f"{positivo} Compra de Membros Aprovada", color=disnake.Color.green())
        carrinho = obter_carrinho_membros(cart_id)
        log_embed.add_field(name="Comprador", value=f"{inter.author.mention} (`{inter.author.id}`)")
        log_embed.add_field(name="Quantidade", value=f"`{carrinho['info']['quantidade']}`")
        log_embed.add_field(name="Valor Pago", value=f"`R$ {carrinho['info']['valorFinal']}`")
        await Logs.Enviar(inter, log_embed)
        embed = disnake.Embed(title=f"{positivo} Pagamento Aprovado!", description="Siga os passos abaixo para receber seus membros:", color=disnake.Color.green())
        embed.add_field(name="Passo 1: Adicione o Bot", value=f"Clique no botão para adicionar nosso bot ao servidor que deseja receber os membros.", inline=False)
        embed.add_field(name="Passo 2: Puxe os Membros", value="Após adicionar o bot, clique no botão 'Puxar Membros' e insira o ID do seu servidor.", inline=False)
        bot_invite_link = f"https://discord.com/api/oauth2/authorize?client_id={self.bot.user.id}&permissions=8&scope=bot%20applications.commands"
        components = [
            disnake.ui.Button(label="Adicionar Bot ao Servidor", style=disnake.ButtonStyle.url, url=bot_invite_link),
            disnake.ui.Button(label="Puxar Membros", style=disnake.ButtonStyle.primary, custom_id=f"salers_cart_puxar_membros_{cart_id}")
        ]
        await inter.response.edit_message(embed=embed, components=components, content=None)

    async def verificar_pagamento_mp(self, inter, cart_id):
        while True:
            await asyncio.sleep(5)
            if not obter_carrinho_membros(cart_id): break
            status = await MercadoPagoPagamento.VerificarPagamento(cart_id)
            if status is True:
                await self._finalize_purchase(inter, cart_id)
                break
            elif status == "Cancelled":
                await self._cancel_cart(inter, cart_id, "O pagamento expirou ou foi cancelado.")
                break
        if cart_id in tasksPagamento: del tasksPagamento[cart_id]

    @commands.Cog.listener("on_button_click")
    async def salers_cart_listener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        if custom_id == "salers_cart_comprar":
            await inter.response.send_message(f"{carregarAnimado} Aguarde, estamos criando seu carrinho...", ephemeral=True)
            try:
                psico_config = ObterPsicoConfig()
                if psico_config.get("verificado_obrigatorio"):
                    auth_local = ObterAuthLocal()
                    authorization = auth_local.get("authorization")
                    if not authorization: print("[SalersCart] Verificação obrigatória ON, mas API eCloud não configurada.")
                    else:
                        headers = {"authorization": authorization}
                        verify_url = f"{API_URL}verify/{inter.author.id}?client_id={self.bot.user.id}"
                        is_verified = False
                        try:
                            response = requests.get(verify_url, headers=headers, timeout=5)
                            if response.status_code == 200 and response.json().get("authenticated") is True: is_verified = True
                        except requests.RequestException:
                            await inter.edit_original_response(content=f"{negativo} O sistema de verificação está instável.")
                            return
                        if not is_verified:
                            login_response = requests.get(f"{API_URL}login?guild_id={inter.guild.id}&client_id={self.bot.user.id}")
                            if login_response.status_code == 200 and login_response.json().get("authUrl"):
                                auth_url = login_response.json()["authUrl"]
                                button = disnake.ui.Button(label="Verifique-se para comprar", style=disnake.ButtonStyle.url, url=auth_url)
                                await inter.edit_original_response(content=f"{negativo} Para comprar, você precisa se autenticar.", components=[button])
                                return
            except Exception as e: print(f"[SalersCart] Erro na verificação: {e}")
            
            salers_config = obter_salers_config()
            if not salers_config.get("sistema_ativo"):
                return await inter.edit_original_response(content=f"{negativo} O sistema de venda de membros está desativado.")
            
            carrinhos = obter_json(SALERS_CARRINHOS_PATH)
            for cart in carrinhos.values():
                if cart.get("server", {}).get("usuario") == inter.author.id:
                    try:
                        thread = await self.bot.fetch_channel(cart["server"]["carrinho"])
                        await inter.edit_original_response(content=f"{negativo} Você já tem um carrinho de membros aberto: {thread.mention}")
                        return
                    except (disnake.NotFound, AttributeError, KeyError): continue
            
            carrinho_id = gerar_string()
            min_membros = salers_config.get("min_membros", 100)
            valor_inicial = min_membros * salers_config.get("valor_por_membro", 0.01)
            novo_carrinho = {"carrinhoID": carrinho_id, "type": "members", "server": {"usuario": inter.author.id, "guild_id": inter.guild.id}, "info": {"quantidade": min_membros, "valorFinal": f"{valor_inicial:.2f}"}}
            
            carrinho_nome = f"👥・{inter.author.name}"
            try:
                topic = await inter.channel.create_thread(name=carrinho_nome, type=disnake.ChannelType.private_thread, invitable=False)
                novo_carrinho["server"]["carrinho"] = topic.id
                carrinhos[carrinho_id] = novo_carrinho
                salvar_json(carrinhos, SALERS_CARRINHOS_PATH)
                embed, components = obter_mensagem_carrinho_membros(carrinho_id)
                await topic.send(f"{inter.author.mention}", embed=embed, components=components)
                await inter.edit_original_response(content=f"{positivo} Carrinho criado: {topic.mention}", components=[disnake.ui.Button(label="Ir para o carrinho", url=topic.jump_url)])
                log_embed = disnake.Embed(title="🛒 Carrinho de Membros Criado", description=f"{inter.author.mention} abriu um carrinho.", color=disnake.Color.blurple())
                await Logs.Enviar(inter, log_embed)
                salers_cart_tasks[carrinho_id] = self.bot.loop.create_task(self._start_cart_countdown(inter, carrinho_id, 600))
            except Exception as e:
                await inter.edit_original_response(content=f"{negativo} Não foi possível criar seu carrinho aqui. Erro: {e}")
                if carrinho_id in carrinhos:
                    del carrinhos[carrinho_id]
                    salvar_json(carrinhos, SALERS_CARRINHOS_PATH)

        elif custom_id.startswith("salers_cart_"):
            try:
                action_part = custom_id.replace("salers_cart_", "")
                *action_list, cart_id = action_part.split('_')
                action = "_".join(action_list)
            except ValueError: return

            if action == "aumentar": await self._update_cart_quantity(inter, cart_id, 100)
            elif action == "diminuir": await self._update_cart_quantity(inter, cart_id, -100)
            elif action == "editar": await inter.response.send_modal(EditarMembrosModal(cart_id))
            elif action == "continuar": await self._proceed_to_payment(inter, cart_id)
            elif action == "aprovar_manual":
                if verificar_permissao(inter.author.id): await self._finalize_purchase(inter, cart_id)
                else: await inter.response.send_message(f"{negativo} Você não tem permissão para aprovar pagamentos.", ephemeral=True)
            elif action == "puxar_membros": await inter.response.send_modal(PuxarMembrosModal(cart_id))
            elif action == "cancelar": await self._cancel_cart(inter, cart_id)
            elif action == "copiacola":
                carrinho = obter_carrinho_membros(cart_id)
                if carrinho: await inter.response.send_message(f"```{carrinho['info']['pagamento']['copiacola']}```", ephemeral=True)

def setup(bot):
    bot.add_cog(SalersCartExtension(bot))