import disnake
from disnake.ext import commands
import json
import os
from datetime import datetime
import asyncio
from Functions.CarregarEmojis import *

class TempoFechamentoModal(disnake.ui.Modal):
    """Modal para configurar o tempo de fechamento automático do carrinho."""
    def __init__(self, cog_instance):
        self.cog = cog_instance
        current_config = self.cog.get_config()
        current_time = str(current_config.get("tempo_fechamento", 10))

        components = [
            disnake.ui.TextInput(
                label="Tempo de Fechamento do Carrinho (minutos)",
                placeholder="Digite 0 para que o carrinho nunca feche automaticamente.",
                custom_id="tempo_fechamento",
                value=current_time,
                min_length=1,
                max_length=4,
            )
        ]
        super().__init__(title="Configurar Tempo de Fechamento", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        try:
            # Defer the response first
            await inter.response.defer()
            
            try:
                novo_tempo = int(inter.text_values["tempo_fechamento"])
                if novo_tempo < 0:
                    await inter.followup.send("O tempo não pode ser um número negativo.", ephemeral=True)
                    return
            except ValueError:
                await inter.followup.send("Por favor, insira um número inteiro válido.", ephemeral=True)
                return

            config = self.cog.get_config()
            config["tempo_fechamento"] = novo_tempo
            self.cog.save_config(config)
            
            embed, components = self.cog.create_main_panel(inter)
            
            # Try to edit the original response with error handling
            try:
                await inter.edit_original_response(embed=embed, components=components)
            except disnake.errors.NotFound:
                # If original message not found, send new message
                await inter.followup.send(embed=embed, components=components, ephemeral=True)
            except Exception as e:
                print(f"Error editing message in TempoFechamentoModal: {e}")
                # Just send the confirmation message if we can't edit the embed
                pass

            confirmation_text = f"Tempo de fechamento do carrinho atualizado para `{novo_tempo} minutos`." if novo_tempo > 0 else "Carrinhos agora não fecharão automaticamente."
            await inter.followup.send(confirmation_text, ephemeral=True)
            
        except Exception as e:
            print(f"Error in TempoFechamentoModal callback: {e}")
            if not inter.response.is_done():
                await inter.response.send_message(
                    "Ocorreu um erro ao processar a configuração. Tente novamente.",
                    ephemeral=True
                )
            else:
                await inter.followup.send(
                    "Ocorreu um erro ao processar a configuração. Tente novamente.",
                    ephemeral=True
                )

class PersonalizarEmbedModal(disnake.ui.Modal):
    """Modal para personalizar título e descrição da embed."""
    def __init__(self, cog_instance, embed_type, current_embed):
        self.cog = cog_instance
        self.embed_type = embed_type
        self.current_embed = current_embed
        
        components = [
            disnake.ui.TextInput(
                label="Título",
                placeholder="Digite o novo título da embed",
                custom_id="titulo",
                value=current_embed.title or "",
                max_length=256,
                required=False
            ),
            disnake.ui.TextInput(
                label="Descrição",
                placeholder="Digite a nova descrição da embed",
                custom_id="descricao",
                value=current_embed.description or "",
                max_length=4000,
                style=disnake.TextInputStyle.long,
                required=False
            )
        ]
        super().__init__(title=f"Personalizar {embed_type}", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        try:
            # First, defer the response to avoid timeout
            await inter.response.defer()
            
            config = self.cog.get_config()
            if "embeds_personalizadas" not in config:
                config["embeds_personalizadas"] = {}
            
            config["embeds_personalizadas"][self.embed_type] = {
                "titulo": inter.text_values["titulo"],
                "descricao": inter.text_values["descricao"]
            }
            self.cog.save_config(config)
            
            # Procurar e editar a mensagem original do carrinho no tópico
            async for message in inter.channel.history(limit=50):
                if message.embeds and message.author == inter.client.user and len(message.components) > 0:
                    # Verificar se é a mensagem do carrinho (tem os botões específicos)
                    if any("personalizar_embed" in str(component.custom_id) for row in message.components for component in row.children if hasattr(component, 'custom_id')):
                        embed, components = self.cog.create_demo_cart_embed(self.embed_type)
                        await message.edit(embed=embed, components=components)
                        await inter.followup.send(f"{positivo} Embed `{self.embed_type}` personalizada com sucesso!", ephemeral=True)
                        return
            
            # Se não encontrar, enviar erro
            await inter.followup.send(f"{negativo} Não foi possível encontrar a mensagem do carrinho para atualizar.", ephemeral=True)
                
        except Exception as e:
            # Handle any errors in the modal processing
            print(f"Error in PersonalizarEmbedModal callback: {e}")
            if not inter.response.is_done():
                await inter.response.send_message(
                    "Ocorreu um erro ao processar a personalização. Tente novamente.",
                    ephemeral=True
                )
            else:
                await inter.followup.send(
                    "Ocorreu um erro ao processar a personalização. Tente novamente.",
                    ephemeral=True
                )

class LojaCustom(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Tipos de embed do carrinho
        self.embed_types = {
            "revisao": "Revisão do Pedido",
            "pagamento": "Tela de Pagamento", 
            "entrega": "Entrega do Produto",
            "sem_estoque": "Produto Sem Estoque",
            "cancelado": "Carrinho Cancelado"
        }
        
        # Estado atual do demo - agora armazena thread_id
        self.demo_states = {}  # {thread_id: current_embed_type}
        self.user_threads = {}  # {user_id: thread_id}

    def get_config(self):
        """Carrega a configuração do bot a partir de um arquivo JSON."""
        try:
            with open("Database/Vendas/configuracao_loja.json", "r", encoding='utf-8') as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            config = {}

        config.setdefault("tempo_fechamento", 10)
        config.setdefault("embeds_personalizadas", {})
        
        return config

    def save_config(self, config):
        """Salva a configuração do bot em um arquivo JSON."""
        os.makedirs("Database/Vendas", exist_ok=True)
        with open("Database/Vendas/configuracao_loja.json", "w", encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)

    def create_main_panel(self, inter: disnake.Interaction):
        """Cria a embed e os componentes do painel principal."""
        config = self.get_config()

        embed = disnake.Embed(
            title=f"{personalizarE} Painel de Personalização da Loja",
            description="Configure as opções da sua loja de vendas.",
            color=0x00FFFF,
            timestamp=datetime.now()
        )
        embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon)
        
        tempo_fechamento = config.get('tempo_fechamento', 10)
        tempo_str = f"`{tempo_fechamento} minutos`" if tempo_fechamento > 0 else "`Nunca`"

        embed.add_field(name=f"{clock} Fechamento Automático", value=tempo_str, inline=True)
        embed.add_field(name=f"{carrinho} Status do Carrinho", value="`Configurável`", inline=True)

        components = [
            disnake.ui.Button(
                label="Definir Tempo", 
                emoji=clock, 
                style=disnake.ButtonStyle.secondary, 
                custom_id="custom_tempo"
            ),
            disnake.ui.Button(
                label="Personalizar Carrinho", 
                emoji=carrinho, 
                style=disnake.ButtonStyle.primary, 
                custom_id="custom_carrinho"
            ),
            disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Configurar Marca", emoji=recibo, custom_id="GerenciarMarcaVendas"),
            disnake.ui.Button(
                label="Voltar", 
                emoji=voltar, 
                style=disnake.ButtonStyle.secondary, 
                custom_id="GerenciarPainelVendas"
            )
        ]
        return embed, components

    def create_demo_cart_embed(self, embed_type):
        """Cria embed de demonstração do carrinho."""
        config = self.get_config()
        custom_embeds = config.get("embeds_personalizadas", {})
        
        # Dados de exemplo
        mock_data = {
            'produto': 'Seu produto',
            'campo': 'Campo exemplo',
            'quantidade': 1,
            'valor': '25.00',
            'estoque': 5
        }

        embed = None
        components = []

        if embed_type == "revisao":
            # Embed padrão ou personalizada
            if embed_type in custom_embeds:
                custom = custom_embeds[embed_type]
                embed = disnake.Embed(
                    title=custom.get("titulo", "## Revisão do pedido"),
                    description=custom.get("descricao", "Confira os detalhes da sua compra abaixo."),
                    color=0x00FFFF,
                    timestamp=datetime.now()
                )
            else:
                embed = disnake.Embed(
                    title="## Revisão do pedido",
                    description="Confira os detalhes da sua compra abaixo.",
                    color=0x00FFFF,
                    timestamp=datetime.now()
                )

            embed.add_field(name="Valor à vista", value=f"``R${mock_data['valor']}``", inline=True)
            embed.add_field(name="Quantidade", value=f"``{mock_data['quantidade']}``", inline=True)
            embed.add_field(name="Em estoque", value=f"``{mock_data['estoque']}``", inline=True)
            embed.add_field(name="Informações do pedido", value=f"``{mock_data['quantidade']}x {mock_data['produto']} - {mock_data['campo']}``", inline=False)

            components = [
                disnake.ui.Button(style=disnake.ButtonStyle.green, label="Prosseguir para pagamento", emoji=arrow, disabled=True),
                disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Editar", emoji=editar, disabled=True),
                disnake.ui.Button(label="Utilizar Cupom", emoji=cupom, disabled=True),
                disnake.ui.Button(style=disnake.ButtonStyle.red, label="Cancelar pedido", emoji=apagar, disabled=True),
                # Botões extras de personalização
                disnake.ui.Button(label="Personalizar", emoji=personalizarE, style=disnake.ButtonStyle.secondary, custom_id=f"personalizar_embed_revisao"),
                disnake.ui.Button(label="Avançar", emoji=arrow, style=disnake.ButtonStyle.primary, custom_id="avancar_embed"),
                disnake.ui.Button(label="Fechar Demo", emoji=apagar, style=disnake.ButtonStyle.danger, custom_id="fechar_demo")
            ]

        elif embed_type == "pagamento":
            if embed_type in custom_embeds:
                custom = custom_embeds[embed_type]
                embed = disnake.Embed(
                    title=custom.get("titulo", f"{carrinho} Pagamento via PIX"),
                    description=custom.get("descricao", "Efetue o pagamento para prosseguir."),
                    color=0x00FFFF,
                    timestamp=datetime.now()
                )
            else:
                embed = disnake.Embed(
                    title=f"{carrinho} Pagamento via PIX",
                    description="Efetue o pagamento para prosseguir.",
                    color=0x00FFFF,
                    timestamp=datetime.now()
                )

            embed.add_field(name="Valor", value=f"``R$ {mock_data['valor']}``", inline=True)
            embed.add_field(name="Status", value="``Aguardando pagamento``", inline=True)
            embed.add_field(name="Método", value="``PIX``", inline=True)

            components = [
                disnake.ui.Button(label="Código Copia e Cola", emoji=copypast, disabled=True),
                disnake.ui.Button(label="QR Code", emoji=qrcode, disabled=True),
                disnake.ui.Button(style=disnake.ButtonStyle.red, label="Cancelar", emoji=apagar, disabled=True),
                # Botões extras de personalização
                disnake.ui.Button(label="Personalizar", emoji=personalizarE, style=disnake.ButtonStyle.secondary, custom_id=f"personalizar_embed_pagamento"),
                disnake.ui.Button(label="Avançar", emoji=arrow, style=disnake.ButtonStyle.primary, custom_id="avancar_embed"),
                disnake.ui.Button(label="Fechar Demo", emoji=apagar, style=disnake.ButtonStyle.danger, custom_id="fechar_demo")
            ]

        elif embed_type == "entrega":
            if embed_type in custom_embeds:
                custom = custom_embeds[embed_type]
                embed = disnake.Embed(
                    title=custom.get("titulo", f"{check} Pagamento aprovado"),
                    description=custom.get("descricao", "Seu produto foi entregue com sucesso!"),
                    color=0x00FF00,
                    timestamp=datetime.now()
                )
            else:
                embed = disnake.Embed(
                    title=f"{check} Pagamento aprovado",
                    description="Seu produto foi entregue com sucesso!",
                    color=0x00FF00,
                    timestamp=datetime.now()
                )

            embed.add_field(name="Produto", value=f"``{mock_data['produto']} - {mock_data['campo']}``", inline=False)
            embed.add_field(name="Quantidade", value=f"``{mock_data['quantidade']}``", inline=True)
            embed.add_field(name="Valor pago", value=f"``R$ {mock_data['valor']}``", inline=True)

            components = [
                disnake.ui.Button(label="Acessar produto", disabled=True),
                # Botões extras de personalização
                disnake.ui.Button(label="Personalizar", emoji=personalizarE, style=disnake.ButtonStyle.secondary, custom_id=f"personalizar_embed_entrega"),
                disnake.ui.Button(label="Avançar", emoji=arrow, style=disnake.ButtonStyle.primary, custom_id="avancar_embed"),
                disnake.ui.Button(label="Fechar Demo", emoji=apagar, style=disnake.ButtonStyle.danger, custom_id="fechar_demo")
            ]

        elif embed_type == "sem_estoque":
            if embed_type in custom_embeds:
                custom = custom_embeds[embed_type]
                embed = disnake.Embed(
                    title=custom.get("titulo", f"{negativo} Produto indisponível"),
                    description=custom.get("descricao", "Não há estoque disponível no momento."),
                    color=0xFF0000,
                    timestamp=datetime.now()
                )
            else:
                embed = disnake.Embed(
                    title=f"{negativo} Produto indisponível",
                    description="Não há estoque disponível no momento.",
                    color=0xFF0000,
                    timestamp=datetime.now()
                )

            embed.add_field(name="Produto", value=f"``{mock_data['produto']} - {mock_data['campo']}``", inline=False)
            embed.add_field(name="Status", value="``Sem estoque``", inline=True)

            components = [
                disnake.ui.Button(label="Ativar notificações", emoji=sino, disabled=True),
                disnake.ui.Button(label="Voltar", emoji=voltar, disabled=True),
                # Botões extras de personalização
                disnake.ui.Button(label="Personalizar", emoji=personalizarE, style=disnake.ButtonStyle.secondary, custom_id=f"personalizar_embed_sem_estoque"),
                disnake.ui.Button(label="Avançar", emoji=arrow, style=disnake.ButtonStyle.primary, custom_id="avancar_embed"),
                disnake.ui.Button(label="Fechar Demo", emoji=apagar, style=disnake.ButtonStyle.danger, custom_id="fechar_demo")
            ]

        elif embed_type == "cancelado":
            if embed_type in custom_embeds:
                custom = custom_embeds[embed_type]
                embed = disnake.Embed(
                    title=custom.get("titulo", f"{carrinhoCancelado} Carrinho fechado"),
                    description=custom.get("descricao", "O seu carrinho foi encerrado com sucesso."),
                    color=0xe31e10,
                    timestamp=datetime.now()
                )
            else:
                embed = disnake.Embed(
                    title=f"{carrinhoCancelado} Carrinho fechado",
                    description="O seu carrinho foi encerrado com sucesso.",
                    color=0xe31e10,
                    timestamp=datetime.now()
                )

            embed.add_field(name="Produto", value=f"``{mock_data['produto']} - {mock_data['campo']}``", inline=False)
            embed.add_field(name="Motivo", value="``Cancelado pelo usuário``", inline=True)

            components = [
                # Botões extras de personalização
                disnake.ui.Button(label="Personalizar", emoji=personalizarE, style=disnake.ButtonStyle.secondary, custom_id=f"personalizar_embed_cancelado"),
                disnake.ui.Button(label="Reiniciar", emoji=arrow, style=disnake.ButtonStyle.primary, custom_id="reiniciar_demo"),
                disnake.ui.Button(label="Fechar Demo", emoji=apagar, style=disnake.ButtonStyle.danger, custom_id="fechar_demo")
            ]

        if embed:
            embed.set_footer(text="🔧 Modo de personalização - Botões desabilitados")

        return embed, components

    def create_editor_embed(self, embed_type, current_embed):
        """Cria embed do editor de personalização."""
        embed = disnake.Embed(
            title=f"{personalizarE} Editando: {self.embed_types[embed_type]}",
            description="Use os botões abaixo para personalizar a embed atual.",
            color=0x00FFFF,
            timestamp=datetime.now()
        )
        
        embed.add_field(name="Título Atual", value=f"```{current_embed.title or 'Nenhum'}```", inline=False)
        embed.add_field(name="Descrição Atual", value=f"```{current_embed.description or 'Nenhuma'}```", inline=False)

        components = [
            disnake.ui.Button(label="Editar Título/Descrição", emoji=editar, style=disnake.ButtonStyle.primary, custom_id=f"editar_embed_{embed_type}"),
            disnake.ui.Button(label="Sincronizar", emoji=reload, style=disnake.ButtonStyle.success, custom_id=f"sincronizar_{embed_type}"),
            disnake.ui.Button(label="Resetar", emoji=apagar, style=disnake.ButtonStyle.danger, custom_id=f"resetar_embed_{embed_type}"),
            disnake.ui.Button(label="Voltar", emoji=voltar, style=disnake.ButtonStyle.secondary, custom_id=f"voltar_carrinho_{embed_type}")
        ]

        return embed, components

    @commands.Cog.listener()
    async def on_button_click(self, inter: disnake.MessageInteraction):
        """Listener para todos os botões."""
        cid = inter.component.custom_id

        # Botão inicial do painel
        if cid == "GerenciarPersonalizarLoja":
            if not inter.author.guild_permissions.administrator:
                await inter.response.send_message("Você precisa de permissão de administrador para usar isto.", ephemeral=True)
                return
            
            await inter.response.defer()
            embed, components = self.create_main_panel(inter)
            await inter.edit_original_response(embed=embed, components=components)
            return

        # Botões do painel principal
        if cid == "custom_tempo":
            if not inter.author.guild_permissions.administrator:
                await inter.response.send_message("Você precisa de permissão de administrador.", ephemeral=True)
                return
            await inter.response.send_modal(TempoFechamentoModal(self))
            return

        elif cid == "custom_carrinho":
            if not inter.author.guild_permissions.administrator:
                await inter.response.send_message("Você precisa de permissão de administrador.", ephemeral=True)
                return
            
            await inter.response.defer()
            
            try:
                # Fechar thread anterior se existir
                if inter.author.id in self.user_threads:
                    old_thread_id = self.user_threads[inter.author.id]
                    try:
                        old_thread = self.bot.get_channel(old_thread_id)
                        if old_thread:
                            await old_thread.delete()
                    except:
                        pass
                    if old_thread_id in self.demo_states:
                        del self.demo_states[old_thread_id]

                # Criar novo tópico
                thread_name = f"🛒 Personalização Carrinho - {inter.author.display_name}"
                thread = await inter.channel.create_thread(
                    name=thread_name,
                    type=disnake.ChannelType.private_thread if inter.channel.type == disnake.ChannelType.text else disnake.ChannelType.public_thread,
                    auto_archive_duration=60
                )
                
                # Adicionar o usuário ao tópico
                await thread.add_user(inter.author)
                
                # Armazenar IDs
                self.user_threads[inter.author.id] = thread.id
                self.demo_states[thread.id] = "revisao"
                
                # Enviar embed no tópico
                embed, components = self.create_demo_cart_embed("revisao")
                await thread.send(
                    content=f"{inter.author.mention}, aqui você pode personalizar as embeds do carrinho! Use os botões para navegar e personalizar.",
                    embed=embed, 
                    components=components
                )
                
                await inter.edit_original_response(
                    content=f"✅ Tópico de personalização criado: {thread.mention}",
                    embed=None,
                    components=[]
                )
                
            except Exception as e:
                print(f"Erro ao criar tópico: {e}")
                await inter.edit_original_response(
                    content="❌ Erro ao criar tópico. Verifique se tenho permissões para criar tópicos.",
                    embed=None,
                    components=[]
                )
            return

        # Verificar se a interação está acontecendo em um tópico de demo
        if not isinstance(inter.channel, disnake.Thread) or inter.channel.id not in self.demo_states:
            return

        # Botões do demo carrinho (apenas em tópicos)
        if cid == "avancar_embed":
            await inter.response.defer()
            current_type = self.demo_states.get(inter.channel.id, "revisao")
            
            # Define próxima embed
            types_order = list(self.embed_types.keys())
            current_index = types_order.index(current_type) if current_type in types_order else 0
            next_index = (current_index + 1) % len(types_order)
            next_type = types_order[next_index]
            
            self.demo_states[inter.channel.id] = next_type
            embed, components = self.create_demo_cart_embed(next_type)
            await inter.edit_original_response(embed=embed, components=components)

        elif cid == "reiniciar_demo":
            await inter.response.defer()
            self.demo_states[inter.channel.id] = "revisao"
            embed, components = self.create_demo_cart_embed("revisao")
            await inter.edit_original_response(embed=embed, components=components)

        elif cid == "fechar_demo":
            await inter.response.defer()
            
            # Limpar estados
            if inter.channel.id in self.demo_states:
                del self.demo_states[inter.channel.id]
            
            # Remover da lista de threads do usuário
            for user_id, thread_id in list(self.user_threads.items()):
                if thread_id == inter.channel.id:
                    del self.user_threads[user_id]
                    break
            
            # Fechar o tópico
            try:
                await inter.edit_original_response(
                    content="🔒 Demonstração finalizada. Este tópico será fechado.",
                    embed=None,
                    components=[]
                )
                await asyncio.sleep(2)
                await inter.channel.delete()
            except:
                pass

        # Botões de personalização de embeds (apenas em tópicos)
        elif cid.startswith("personalizar_embed_"):
            embed_type = cid.replace("personalizar_embed_", "")
            current_embed = inter.message.embeds[0] if inter.message.embeds else None
            embed, components = self.create_editor_embed(embed_type, current_embed)
            await inter.response.send_message(embed=embed, components=components, ephemeral=True)

        elif cid.startswith("editar_embed_"):
            embed_type = cid.replace("editar_embed_", "")
            current_embed = inter.message.embeds[0] if inter.message.embeds else disnake.Embed()
            await inter.response.send_modal(PersonalizarEmbedModal(self, embed_type, current_embed))

        elif cid.startswith("sincronizar_"):
            embed_type = cid.replace("sincronizar_", "")
            # Encontrar a mensagem original do carrinho no tópico
            async for message in inter.channel.history(limit=50):
                if message.embeds and message.author == self.bot.user and len(message.components) > 0:
                    # Verificar se é a mensagem do carrinho (tem os botões específicos)
                    if any("personalizar_embed" in str(component.custom_id) for row in message.components for component in row.children if hasattr(component, 'custom_id')):
                        embed, components = self.create_demo_cart_embed(embed_type)
                        await message.edit(embed=embed, components=components)
                        await inter.response.send_message("✅ Embed sincronizada com sucesso!", ephemeral=True)
                        return
            await inter.response.send_message("❌ Não foi possível encontrar a mensagem do carrinho para sincronizar.", ephemeral=True)

        elif cid.startswith("resetar_embed_"):
            embed_type = cid.replace("resetar_embed_", "")
            
            config = self.get_config()
            if embed_type in config.get("embeds_personalizadas", {}):
                del config["embeds_personalizadas"][embed_type]
                self.save_config(config)
            
            # Encontrar a mensagem original do carrinho no tópico
            async for message in inter.channel.history(limit=50):
                if message.embeds and message.author == self.bot.user and len(message.components) > 0:
                    # Verificar se é a mensagem do carrinho (tem os botões específicos)
                    if any("personalizar_embed" in str(component.custom_id) for row in message.components for component in row.children if hasattr(component, 'custom_id')):
                        embed, components = self.create_demo_cart_embed(embed_type)
                        await message.edit(embed=embed, components=components)
                        await inter.response.send_message("✅ Embed resetada para o padrão!", ephemeral=True)
                        return
            await inter.response.send_message("❌ Não foi possível encontrar a mensagem do carrinho para resetar.", ephemeral=True)

        elif cid.startswith("voltar_carrinho_"):
            embed_type = cid.replace("voltar_carrinho_", "")
            # Encontrar a mensagem original do carrinho no tópico
            async for message in inter.channel.history(limit=50):
                if message.embeds and message.author == self.bot.user and len(message.components) > 0:
                    # Verificar se é a mensagem do carrinho (tem os botões específicos)
                    if any("personalizar_embed" in str(component.custom_id) for row in message.components for component in row.children if hasattr(component, 'custom_id')):
                        embed, components = self.create_demo_cart_embed(embed_type)
                        await message.edit(embed=embed, components=components)
                        await inter.response.send_message("✅ Voltando para a visualização do carrinho.", ephemeral=True)
                        return
            await inter.response.send_message("❌ Não foi possível encontrar a mensagem do carrinho.", ephemeral=True)

def setup(bot):
    """Adiciona o Cog ao bot."""
    bot.add_cog(LojaCustom(bot))