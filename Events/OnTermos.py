import disnake
import json
from disnake.ext import commands
from Functions.CarregarEmojis import *

def obter_config_termos():
    """
    Lê o arquivo de configuração de termos de forma segura.

    Retorna o dicionário de configuração de 'termos_manual' se existir,
    ou um dicionário vazio caso contrário.
    """
    filepath = "Database/Vendas/configuracao.json"
    try:
        with open(filepath, "r", encoding='utf-8') as f:
            full_db = json.load(f)
        # Retorna a configuração específica, ou um dicionário vazio se a chave não existir
        return full_db.get("termos_manual", {})
    except (FileNotFoundError, json.JSONDecodeError):
        # Se o arquivo não existe ou está corrompido, não há configuração.
        return {}

class OnTermosCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def exibir_termos_listener(self, inter: disnake.MessageInteraction):
        """
        Listener que aguarda o clique no botão para exibir os termos.
        """
        if inter.component.custom_id != "exibirtermos":
            return # Ignora todos os outros botões

        # Adia a resposta para ter mais tempo de processar, de forma efêmera
        await inter.response.defer(ephemeral=True)

        # 1. Obter a configuração dos termos
        config = obter_config_termos()

        content = config.get("content")
        embed_data = config.get("embed", {})
        
        # Verifica se existe algum conteúdo no embed para ser exibido
        is_embed_configured = any(v is not None for v in embed_data.values())

        # 2. Verificar se os termos foram configurados
        if not content and not is_embed_configured:
            await inter.followup.send(
                f"{negativo} Os termos deste servidor ainda não foram configurados pela administração.",
                ephemeral=True
            )
            return

        # 3. Se foram configurados, construir a mensagem para enviar
        final_embed = None
        if is_embed_configured:
            try:
                # Constrói o embed a partir dos dados salvos
                color_hex = embed_data.get('color')
                color_int = disnake.Color.default()
                
                if color_hex:
                    # Verifica se já é um inteiro
                    if isinstance(color_hex, int):
                        color_int = color_hex
                    # Se for string, converte de hex para int
                    elif isinstance(color_hex, str) and color_hex.strip():
                        # Remove # se presente e espaços
                        color_hex_clean = color_hex.strip().lstrip('#')
                        # Verifica se é um hex válido
                        if color_hex_clean and len(color_hex_clean) == 6:
                            color_int = int(color_hex_clean, 16)
                
                final_embed = disnake.Embed(
                    title=embed_data.get('title'),
                    description=embed_data.get('description'),
                    color=color_int
                )
                if embed_data.get('banner_url'):
                    final_embed.set_image(url=embed_data['banner_url'])
                if embed_data.get('thumbnail_url'):
                    final_embed.set_thumbnail(url=embed_data['thumbnail_url'])

            except (ValueError, TypeError) as e:
                # Se houver um erro (ex: cor mal formatada), envia sem o embed para não quebrar
                await inter.followup.send(
                    f"⚠️ Os termos foram encontrados, mas há um erro na formatação do embed: {str(e)}\nAvise um administrador.",
                    ephemeral=True
                )
                return

        # 4. Enviar a mensagem final de forma efêmera
        try:
            await inter.followup.send(
                content=content,
                embed=final_embed,
                ephemeral=True
            )
        except Exception as e:
            # Fallback caso ainda haja algum erro
            await inter.followup.send(
                f"⚠️ Erro ao exibir os termos: {str(e)}\nAvise um administrador.",
                ephemeral=True
            )

def setup(bot: commands.Bot):
    bot.add_cog(OnTermosCommand(bot))