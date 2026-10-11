import disnake
from disnake.ext import commands
import json
import os
import datetime

from Functions.CarregarEmojis import *
# Import da cog de Condecoracao
from Commands.Admin.Plugins.Condecoracao import ObterDatabaseCondecoracao, AdicionarCondecoracaoUsuario, DEFAULT_CONDECORATIONS_DATA

# --- Funções de Gerenciamento de Arquivos ---

def obter_config_sugestao():
    """Lê acoesauto.json e retorna apenas a configuração de sugestões."""
    filepath = "Database/Server/acoesauto.json"
    try:
        with open(filepath, "r", encoding='utf-8') as f:
            # Carrega todo o DB mas retorna apenas a parte de sugestões
            return json.load(f).get("sugestoes", {})
    except (FileNotFoundError, json.JSONDecodeError):
        # Retorna uma estrutura padrão se o arquivo não existir ou for inválido
        return {
            "sistema": False, "canal": None, "emoji_concordo": f"{positivo}",
            "emoji_discordo": f"{negativo}", "cor_embed": "0x2f3136" 
        }

def ler_votos():
    """Lê o arquivo de votos."""
    filepath = "Database/Server/sugestoes_votos.json"
    if not os.path.exists(os.path.dirname(filepath)):
        os.makedirs(os.path.dirname(filepath))
    
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, "r", encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def salvar_votos(data):
    """Salva os votos."""
    filepath = "Database/Server/sugestoes_votos.json"
    with open(filepath, "w", encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_porcentagem(valor, total):
    """Calcula a porcentagem."""
    if total == 0:
        return '0.0%'
    return f"{(valor / total) * 100:.1f}%"

# --- Cog Principal do Sistema de Sugestões ---

class OnSugestao(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Referência à cog de condecorações
        self.condecoracao_cog = None
        self.bot.loop.create_task(self._load_condecoracao_cog())

    async def _load_condecoracao_cog(self):
        await self.bot.wait_until_ready()
        self.condecoracao_cog = self.bot.get_cog("CondecoracaoCommand")
        if not self.condecoracao_cog:
            print("AVISO: A cog 'CondecoracaoCommand' não foi carregada. Condecorações de sugestões podem não funcionar.")

    @commands.Cog.listener("on_message")
    async def criar_sugestao(self, message: disnake.Message):
        if message.author.bot:
            return

        sugestoes_config = obter_config_sugestao()

        if not sugestoes_config.get("sistema", False):
            return
        
        canal_sugestoes_id = sugestoes_config.get("canal")
        if not canal_sugestoes_id or message.channel.id != canal_sugestoes_id:
            return

        try:
            await message.delete()
        except (disnake.Forbidden, disnake.NotFound):
            pass

        # Pega a cor do embed salva na configuração
        cor_salva_hex = sugestoes_config.get("cor_embed", "0x2f3136")
        cor_embed = int(cor_salva_hex.replace("#", "0x"), 16)
        
        # Emojis agora são puxados diretamente das variáveis padrão, que já possuem a cor do tema
        emoji_usuario = user
        emoji_sugestao = mensagem
        emoji_data = clock
        
        autor = message.author
        data_sugestao = datetime.datetime.now(datetime.timezone.utc)
        sugestao_id = f"{message.channel.id}_{disnake.utils.time_snowflake(data_sugestao)}"
        
        votos = ler_votos()
        votos[sugestao_id] = {
            "autor_id": autor.id, "autor_nome": autor.display_name, "sugestao": message.content,
            "data": data_sugestao.isoformat(), "votos": {"up": [], "down": []},
            "condecoracoes_verificadas": []
        }
        salvar_votos(votos)

        emoji_up = sugestoes_config.get("emoji_concordo") or "✅"
        emoji_down = sugestoes_config.get("emoji_discordo") or "❌"

        botoes = disnake.ui.ActionRow(
            disnake.ui.Button(style=disnake.ButtonStyle.secondary, custom_id=f"sugestao_up_{sugestao_id}", label="(0.0%)", emoji=emoji_up),
            disnake.ui.Button(style=disnake.ButtonStyle.secondary, custom_id=f"sugestao_down_{sugestao_id}", label="(0.0%)", emoji=emoji_down),
            disnake.ui.Button(style=disnake.ButtonStyle.secondary, custom_id=f"sugestao_info_{sugestao_id}", label="(0)", emoji="ℹ️")
        )
        
        embed = disnake.Embed(
            color=cor_embed,
            description=(
                f"{user} **Usuário(a)**\n<@{autor.id}> ({autor.id})\n\n"
                f"{mnsgbranco} **Sugestão**\n```\n{message.content}\n```"
            )
        )
        embed.set_author(name=autor.display_name, icon_url=autor.display_avatar)
        embed.set_thumbnail(url=autor.display_avatar)
        embed.add_field(
            name=f"{clock} Data",
            value=f"<t:{int(data_sugestao.timestamp())}:R>",
            inline=False
        )
        embed.set_footer(text=f"{self.bot.user.name} • Vote abaixo")
        embed.timestamp = data_sugestao

        msg_sugestao = await message.channel.send(embed=embed, components=[botoes])

        try:
            thread = await msg_sugestao.create_thread(name=f"Discussão da sugestão de {autor.display_name}", auto_archive_duration=1440)
            
            embed_thread = disnake.Embed(
                color=cor_embed,
                title="Regulamento do Tópico",
                description=f"Este tópico foi criado para discutir a sugestão de <@{autor.id}>.\n\n"
                            f"Mantenha **o foco no assunto e evite mensagens irrelevantes**. Caso ocorra alguma inconveniência, informe a moderação."
            )
            embed_thread.set_footer(text=autor.display_name, icon_url=autor.display_avatar)
            await thread.send(embed=embed_thread)
        except Exception as e:
            print(f"Erro ao criar o tópico da sugestão: {e}")

    @commands.Cog.listener("on_button_click")
    async def processar_voto_sugestao(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        if not custom_id or not custom_id.startswith("sugestao_"):
            return

        try:
            tipo, sugestao_id = custom_id.split("_", 2)[1:]
        except ValueError:
            return

        votos_db = ler_votos()
        sugestao = votos_db.get(sugestao_id)

        if not sugestao:
            await inter.response.send_message("Esta sugestão não foi encontrada na base de dados.", ephemeral=True)
            return
        
        user_id = inter.author.id
        sugestao_autor_id = sugestao["autor_id"]

        if tipo == "up" or tipo == "down":
            dados_votos = sugestao.setdefault("votos", {"up": [], "down": []})
            
            if user_id in dados_votos["up"]: dados_votos["up"].remove(user_id)
            if user_id in dados_votos["down"]: dados_votos["down"].remove(user_id)

            dados_votos[tipo].append(user_id)
            
            salvar_votos(votos_db)

            total_votos = len(dados_votos["up"]) + len(dados_votos["down"])
            up_pct_val = (len(dados_votos["up"]) / total_votos) * 100 if total_votos > 0 else 0.0
            down_pct_val = (len(dados_votos["down"]) / total_votos) * 100 if total_votos > 0 else 0.0
            
            up_pct = f"{up_pct_val:.1f}%"
            down_pct = f"{down_pct_val:.1f}%"

            sugestoes_config = obter_config_sugestao()
            emoji_up = sugestoes_config.get("emoji_concordo") or "✅"
            emoji_down = sugestoes_config.get("emoji_discordo") or "❌"

            novos_botoes = disnake.ui.ActionRow(
                disnake.ui.Button(style=disnake.ButtonStyle.secondary, custom_id=f"sugestao_up_{sugestao_id}", label=f"({up_pct})", emoji=emoji_up),
                disnake.ui.Button(style=disnake.ButtonStyle.secondary, custom_id=f"sugestao_down_{sugestao_id}", label=f"({down_pct})", emoji=emoji_down),
                disnake.ui.Button(style=disnake.ButtonStyle.secondary, custom_id=f"sugestao_info_{sugestao_id}", label=f"({total_votos})", emoji="ℹ️")
            )
            
            await inter.response.edit_message(components=[novos_botoes])
            
            await self.check_and_award_condecorations_sugestoes(sugestao_autor_id, sugestao_id, dados_votos, up_pct_val, inter)

        elif tipo == "info":
            dados_votos = sugestao.get("votos", {"up": [], "down": []})
            
            membros_up = ", ".join([f"<@{uid}>" for uid in dados_votos.get("up", [])]) or "Ninguém"
            membros_down = ", ".join([f"<@{uid}>" for uid in dados_votos.get("down", [])]) or "Ninguém"

            await inter.response.send_message(
                f"{positivo} **Aprovaram:** {membros_up}\n\n"
                f"{negativo} **Reprovaram:** {membros_down}",
                ephemeral=True
            )
    
    async def check_and_award_condecorations_sugestoes(self, autor_id: int, sugestao_id: str, dados_votos: dict, up_percentage: float, inter: disnake.Interaction):
        if not self.condecoracao_cog: return

        votos_db = ler_votos()
        sugestao_data = votos_db.get(sugestao_id)
        if not sugestao_data: return

        condecoracoes_verificadas = sugestao_data.setdefault("condecoracoes_verificadas", [])

        for condec_id, condec_info in DEFAULT_CONDECORATIONS_DATA.items():
            if condec_info["tipo"] != "sugestoes": continue
            if condec_id in condecoracoes_verificadas: continue

            condicao = condec_info["condicao"]
            met_condition = False

            if condicao["tipo"] == "porcentagem_aprovacao":
                if up_percentage >= condicao["valor"] and len(dados_votos["up"]) > 0:
                    met_condition = True
            elif condicao["tipo"] == "total_votos_sugestao":
                total_votos = len(dados_votos["up"]) + len(dados_votos["down"])
                if total_votos >= condicao["valor"]:
                    met_condition = True
            
            if met_condition:
                awarded = await self.condecoracao_cog.conceder_condecoracao(autor_id, condec_id, inter)
                if awarded:
                    condecoracoes_verificadas.append(condec_id)
                    salvar_votos(votos_db)

def setup(bot: commands.Bot):
    bot.add_cog(OnSugestao(bot))