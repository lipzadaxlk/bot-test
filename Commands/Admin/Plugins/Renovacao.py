# Renovacao.py - Versão Corrigida
import disnake
from disnake.ext import commands
import asyncio
import io
import aiohttp
import os
import base64
from datetime import datetime

# --- Configuração OBRIGATÓRIA ---
# API Key do ImgBB para upload de imagens
IMGBB_API_KEY = "cb7fdbb1705c13693e8dda633fb60a28"

# URL da API removida - sistema de manager desabilitado
# MANAGER_API_URL = "https://antiethical.squareweb.app"

# URL de uma imagem que será mostrada junto com o PIX (pode ser um QR Code).
IMAGEM_PIX_URL = "https://i.imgur.com/your_pix_image.png"

# Chave PIX que será mostrada ao usuário.
CHAVE_PIX = "snoowonly@gmail.com"

# Preços por duração (opcional, para mostrar ao usuário)
PRECOS = {
    "30": "R$ 10,00",
    "90": "R$ 25,00", 
    "365": "R$ 80,00"
}

# Carrega as funções de emoji, se você as tiver em um local central.
try:
    from Functions.CarregarEmojis import *
except ImportError:
    # Emojis de fallback caso o arquivo de emojis não seja encontrado
    sucesso = "✅"
    positivo = "✅"
    negativo = "❌"
    carregarAnimado = "🔄"
    dinheiro = "💰"
    dollar = "💰"
    aviso = "⚠️"
    warn = "⚠️"
# --------------------------------

class Renovacao(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Armazena usuários que iniciaram um processo de renovação para evitar duplicidade
        self.active_renewal_users = {}
        
    async def _upload_to_imgbb(self, file_bytes: bytes, filename: str) -> str:
        """
        Faz upload de arquivo para ImgBB.
        Retorna a URL do arquivo ou None em caso de erro.
        """
        try:
            # ImgBB API endpoint
            upload_url = "https://api.imgbb.com/1/upload"
            
            # Converte para base64 (ImgBB aceita base64)
            file_base64 = base64.b64encode(file_bytes).decode('utf-8')
            
            # Prepara os dados
            data = {
                'key': IMGBB_API_KEY,
                'image': file_base64,
                'name': filename.split('.')[0]  # Nome sem extensão
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    upload_url,
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        response_json = await response.json()
                        
                        if response_json.get('success'):
                            # Retorna a URL da imagem
                            return response_json['data']['url']
                        else:
                            print(f"Erro na resposta do ImgBB: {response_json}")
                            return None
                    else:
                        error_text = await response.text()
                        print(f"Erro no upload para ImgBB ({response.status}): {error_text}")
                        return None
                        
        except Exception as e:
            print(f"Erro no upload para ImgBB: {e}")
            return None

    @commands.Cog.listener("on_button_click")
    async def renovacao_listener(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id != "RenovarPlano":
            return
            
        # Verifica se o usuário já tem um processo em andamento
        if inter.author.id in self.active_renewal_users:
            await inter.response.send_message(
                f"{warn} Você já possui um processo de renovação em andamento. "
                f"Por favor, envie o comprovante ou aguarde.", 
                ephemeral=True
            )
            return

        await inter.response.defer(ephemeral=True)

        embed = disnake.Embed(
            title="✨ Renovação de Plano",
            description="Escolha por quanto tempo você deseja renovar seu plano. "
                       "Após selecionar, você receberá as instruções para o pagamento.",
            color=disnake.Color.blue()
        )
        embed.set_footer(text="Selecione uma opção abaixo para continuar.")

        options = [
            disnake.SelectOption(
                label="30 Dias", 
                value="30", 
                description=f"Renove por mais um mês - {PRECOS.get('30', 'Consulte preço')}", 
                emoji="🗓️"
            ),
            disnake.SelectOption(
                label="90 Dias", 
                value="90", 
                description=f"Renove por três meses - {PRECOS.get('90', 'Consulte preço')}", 
                emoji="🗓️"
            ),
            disnake.SelectOption(
                label="1 Ano", 
                value="365", 
                description=f"O melhor custo-benefício! - {PRECOS.get('365', 'Consulte preço')}", 
                emoji="⭐"
            ),
        ]

        select_menu = disnake.ui.Select(
            custom_id="selecionar_duracao_renovacao",
            placeholder="Escolha a duração da renovação",
            options=options
        )

        view = disnake.ui.View()
        view.add_item(select_menu)

        await inter.followup.send(embed=embed, view=view, ephemeral=True)

    @commands.Cog.listener("on_dropdown")
    async def duracao_renovacao_listener(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id != "selecionar_duracao_renovacao":
            return
            
        await inter.response.defer()
        
        dias_selecionados = inter.values[0]
        self.active_renewal_users[inter.author.id] = {
            'dias': dias_selecionados,
            'timestamp': datetime.now()
        }

        preco = PRECOS.get(dias_selecionados, "Consulte o valor")
        
        embed = disnake.Embed(
            title=f"{dollar} Instruções de Pagamento - {dias_selecionados} Dias",
            description=(
                f"**Valor:** {preco}\n\n"
                f"Para continuar, realize um pagamento PIX para a chave abaixo.\n\n"
                f"**Após o pagamento, envie o comprovante (imagem) aqui neste chat.**\n"
                f"**Você tem 5 minutos para enviar o comprovante.**"
            ),
            color=disnake.Color.green()
        )
        embed.add_field(
            name="Chave PIX (E-mail)", 
            value=f"```{CHAVE_PIX}```", 
            inline=False
        )
        
        if IMAGEM_PIX_URL and IMAGEM_PIX_URL != "https://i.imgur.com/your_pix_image.png":
            embed.set_image(url=IMAGEM_PIX_URL)
            
        embed.set_footer(text="Aguardando o envio do seu comprovante...")

        await inter.edit_original_message(embed=embed, view=None)

        def check(message: disnake.Message):
            return (
                message.author == inter.author and
                message.channel == inter.channel and
                message.attachments and
                len(message.attachments) > 0 and
                any(att.content_type and att.content_type.startswith('image/') 
                    for att in message.attachments)
            )

        try:
            comprovante_msg = await self.bot.wait_for("message", timeout=300.0, check=check)
            await comprovante_msg.add_reaction(carregarAnimado)
            
            # Processa o comprovante
            success = await self._processar_comprovante(
                comprovante_msg, inter.author, dias_selecionados
            )
            
            if success:
                await comprovante_msg.add_reaction(positivo)
                await comprovante_msg.reply(
                    f"{positivo} Seu comprovante foi enviado para análise! "
                    f"Você será notificado(a) assim que sua solicitação for processada.",
                    mention_author=False
                )
            else:
                await comprovante_msg.add_reaction(negativo)
                await comprovante_msg.reply(
                    f"{negativo} Não foi possível processar seu comprovante. "
                    f"Por favor, contate o suporte.",
                    mention_author=False
                )

        except asyncio.TimeoutError:
            await inter.followup.send(
                f"{negativo} O tempo para enviar o comprovante esgotou (5 minutos). "
                f"Por favor, inicie o processo de renovação novamente.", 
                ephemeral=True
            )
        except Exception as e:
            print(f"Erro no processo de renovação para {inter.author}: {e}")
            await inter.followup.send(
                f"{negativo} Ocorreu um erro inesperado. Por favor, contate o suporte.",
                ephemeral=True
            )
        finally:
            # Remove o usuário da lista de processos ativos
            if inter.author.id in self.active_renewal_users:
                del self.active_renewal_users[inter.author.id]

    async def _processar_comprovante(self, message: disnake.Message, user: disnake.User, dias: str) -> bool:
        """Sistema de manager removido - função desabilitada."""
        return False
        # try:
            # 1. Prepara o comprovante
            comprovante_anexo = message.attachments[0]
            comprovante_bytes = await comprovante_anexo.read()
            
            # Valida o tamanho do arquivo (máximo 32MB - limite do ImgBB)
            if len(comprovante_bytes) > 32 * 1024 * 1024:
                await message.reply(f"{negativo} O arquivo é muito grande. Máximo: 32MB.")
                return False
            
            # Gera um nome único para o arquivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_extension = comprovante_anexo.filename.split('.')[-1] if '.' in comprovante_anexo.filename else 'png'
            file_name = f"comprovante_{user.id}_{timestamp}.{file_extension}"
            
            # 2. Faz upload para ImgBB
            print(f"Fazendo upload do comprovante para ImgBB...")
            comprovante_url = await self._upload_to_imgbb(comprovante_bytes, file_name)
            
            if not comprovante_url:
                print("Upload para ImgBB falhou")
                await message.reply(f"{negativo} Não foi possível fazer upload do comprovante. Tente novamente.")
                return False
                
            print(f"Upload realizado com sucesso: {comprovante_url}")

            # 3. Pega o ID do bot AUTOMATICAMENTE
            bot_id = self.bot.user.id

            # 4. Monta os dados para enviar para a API do Manager
            payload = {
                "userId": str(user.id),
                "userName": user.display_name,
                "userAvatar": str(user.display_avatar.url),
                "botId": str(bot_id),
                "days": int(dias),
                "proofUrl": comprovante_url,
                "timestamp": datetime.now().isoformat(),
                "fileData": {
                    "filename": file_name,
                    "size": len(comprovante_bytes),
                    "content_type": comprovante_anexo.content_type,
                    "upload_service": "imgbb"
                }
            }

            # 5. Envia a solicitação para a API do Manager usando aiohttp
            api_endpoint = f"{MANAGER_API_URL}/api/renewal-request"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    api_endpoint, 
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        print(f"Solicitação de renovação enviada com sucesso para {user}")
                        return True
                    else:
                        error_text = await response.text()
                        print(f"Erro da API do Manager ({response.status}): {error_text}")
                        return False

        except aiohttp.ClientError as e:
            print(f"Erro de conexão com a API do Manager: {e}")
            return False
        except Exception as e:
            print(f"Erro ao processar comprovante: {e}")
            return False


def setup(bot: commands.Bot):
    """Função que o disnake usa para registrar a cog."""
    bot.add_cog(Renovacao(bot))