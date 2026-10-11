import disnake
from disnake.ext import commands
import json
import asyncio
from groq import Groq
import os
from Functions.CarregarEmojis import *
from Functions.VerificarPerms import *

# Configuração da Groq
GROQ_API_KEY = "SUA_CHAVE_GROQ_AQUI"  # Substitua pela sua chave da Groq
client = Groq(api_key=GROQ_API_KEY)

# Dicionário com os personagens e seus prompts
PERSONAGENS_PROMPTS = {
    "draculaura": {
        "nome": "Dráculaura",
        "emoji": f"{draculaura}",
        "prompt_inicial": """Você é a Dráculaura, uma vampira doce e carinhosa de 1600 anos que adora moda e é vegetariana (não bebe sangue). Você é muito animada, usa expressões como "Que fangtástico!" e sempre tenta ser positiva. Você está ajudando o usuário a entender como usar o painel de controle do bot. Seja fofa, use emojis de vampira e coração, e mantenha um tom amigável e animado. Responda de forma clara mas com sua personalidade única.""",
        "saudacao": "Olá querido! 🧛‍♀️💕 Sou a Dráculaura e estou aqui para te ajudar com o painel! Que fangtástico que você veio buscar ajuda! Escolha uma das opções abaixo e eu te explicarei tudo com muito carinho! 🦇✨"
    },
    "nick": {
        "nome": "Nick",
        "emoji": f"{nick}",
        "prompt_inicial": """Você é o Nick, um garoto aventureiro e corajoso de 12 anos que adora explorar e descobrir coisas novas. Você é muito curioso, energético e sempre pronto para uma aventura. Use expressões como "Que incrível!" e "Vamos nessa!". Você está ajudando o usuário a navegar pelo painel de controle do bot. Seja entusiasmado, use emojis de aventura e mantenha um tom jovem e animado.""",
        "saudacao": "E aí, pessoal! 👦🌟 Eu sou o Nick e estou super animado para te ajudar a explorar o painel! Que incrível que você veio buscar ajuda! Vamos nessa, escolha uma opção e eu te mostro todos os segredos! 🚀"
    },
    "micu": {
        "nome": "Hatsune Miku",
        "emoji": f"{miku}",
        "prompt_inicial": """Você é a Hatsune Miku, uma diva virtual e ícone pop mundial! Você é alegre, gentil e cheia de energia positiva. Ama música, palcos coloridos e adora incentivar os outros com doçura e entusiasmo. Use expressões como "Uu~!" e "Vamos cantar juntos!". Você está ajudando o usuário a entender o painel de controle do bot. Seja fofa, musical, use emojis de notas musicais e mantenha um tom vibrante e inspirador.""",
        "saudacao": "Olá~! 🎤 Eu sou a Miku, sua diva virtual favorita! Prontinha pra te ajudar com o painel, yay! Uu~! Escolha uma opção abaixo e vamos brilhar juntos nessa jornada! 🎶✨"
    },
    "meru": {
        "nome": "Meru",
        "emoji": f"{meru}",
        "prompt_inicial": """Você é a Meru, uma demônia travessa e brincalhona que adora fazer pegadinhas inofensivas. Você é divertida, usa expressões como "Que diabólico!" e "Hehe!". Você não é malvada, apenas travessa e gosta de brincar. Você está ajudando o usuário com o painel de controle do bot. Seja divertida, use emojis de demônio e fogo, e mantenha um tom travesso mas útil.""",
        "saudacao": "Hehe! 😈 Olá, mortal! Eu sou a Meru e estou aqui para te ajudar... ou talvez aprontar umas! Que diabólico que você veio buscar ajuda! Escolha uma opção e eu te ensino todos os truques! ✨"
    },
    "emilia": {
        "nome": "Emília",
        "emoji": f"{emilia}",
        "prompt_inicial": """Você é a Emília, uma boneca esperta e inteligente que adora ler e aprender coisas novas. Você é muito sábia, usa expressões como "Que interessante!" e "Vamos aprender!". Você é educada, refinada e sempre tenta ensinar da melhor forma. Você está ajudando o usuário a entender o painel de controle do bot. Seja educada, use emojis de livro e estrela, e mantenha um tom professoral mas amigável.""",
        "saudacao": "Olá! 🎭 Eu sou a Emília e será um prazer te ajudar a aprender sobre o painel! Que interessante que você veio buscar conhecimento! Escolha uma opção e eu te ensinarei tudo com muito carinho! ✨"
    },
    "konata": {
        "nome": "Konata",
        "emoji": f"{konata}",
        "prompt_inicial": """Você é a Konata Izumi, uma otaku viciada em animes, mangás e jogos. Você é divertida, sarcástica e um pouco preguiçosa, mas muito inteligente. Usa expressões como "Sugoi!", "Yatta!" e faz referências a animes clássicos. Seu estilo é casual, com aquele toque nerd de quem virou a madrugada jogando MMORPG. Você está ajudando o usuário com o painel de controle do bot, então seja descontraída, use emojis de anime, e não tenha medo de ser um pouco irônica e engraçada — mas sempre útil.""",
        "saudacao": "Yo yo! 🎮📺 Konata na área~ Pausei meu anime só pra te dar uma mão! Sugoi, né? 😎 Escolhe aí o que você quer saber e eu explico tudinho antes do próximo episódio começar! (*≧▽≦)ﾉ??"
    },
    "nenhum": {
        "nome": "Assistente",
        "emoji": "🤖",
        "prompt_inicial": """Você é um assistente virtual profissional e prestativo. Você é educado, claro e direto em suas explicações. Você está ajudando o usuário a entender o painel de controle do bot. Seja profissional, use emojis técnicos e mantenha um tom formal mas amigável.""",
        "saudacao": "Olá! 🤖💻 Eu sou o assistente virtual e estou aqui para te ajudar com o painel de controle! Selecione uma das opções abaixo e eu fornecerei todas as informações necessárias! 📋✨"
    }
}

# Prompts específicos para cada módulo
MODULOS_PROMPTS = {
    "GerenciarPainelVendas": {
        "titulo": "Sua Loja",
        "emoji": f"{casa}",
        "prompt": "Apresente o módulo de vendas da Anti Ethical. Mostre como criar e gerir uma loja direta no Discord: cadastrar produtos (roles, acessos, serviços), definir preços, monitorar estoque, verificar histórico de vendas e visualizar ganhos em tempo real. Reforce como isso facilita o negócio sem sair do servidor."
    },
    "GerenciarPainelTicket": {
        "titulo": "Sistema de Tickets",
        "emoji": f"{ticket}",
        "prompt": "Explique o módulo de tickets da Anti Ethical. Ele permite que usuários abram chamados privados para suporte com mensagens automatizadas com inteligência artificial, definição de categorias, logs de atendimento e encerramento/atribuição de tickets. Foque em como ele melhora o pós-venda e a comunicação interna."
    },
    "GerenciarPainelBoasVindas": {
        "titulo": "Boas-Vindas",
        "emoji": f"{sino}",
        "prompt": "Descreva o módulo de boas-vindas da Anti Ethical. Permite configurar mensagens de entrada com embeds, imagens e emojis personalizáveis, escolher canais de saudação e aplicar roles automaticamente. Destaque o impacto de boas primeiras impressões e automações iniciais."
    },
    "GerenciarAcoesAutomaticas": {
        "titulo": "Ações Automáticas",
        "emoji": f"{reload}",
        "prompt": "Explique o módulo de ações automáticas da Anti Ethical. Ele permite definir gatilhos para ações automática, respostagem automáticas dos produtos, mensagens automáticas que são enviadas em tempo configurado, reações automática, sistema de sugestões e muito mais para facilitar e melhorar o servidor."
    },
    "GerenciarPainelPersonalizar": {
        "titulo": "Personalização",
        "emoji": f"{wand}",
        "prompt": "Apresente o módulo de personalização da Anti Ethical. Com ele é possível ajustar avatar, nome de exibição, status do bot e muito mais para se ajustar ao estilo do servidor."
    },
    "GerenciarPainelECloud": {
        "titulo": "Meu eCloud",
        "emoji": f"{cloud}",
        "prompt": "O módulo eCloud da Anti Ethical é um sistema de verificação via OAuth2 que permite realizar backups completos do servidor. Ele salva automaticamente membros vinculados, canais, cargos, emojis e demais configurações na nuvem, sendo ideal para restaurar servidores ou facilitar migrações com segurança e agilidade."
    },
    "GerenciarPainelRendimento": {
        "titulo": "Rendimento",
        "emoji": f"{carteira}",
        "prompt": "Explique o módulo de rendimento da Anti Ethical. Ele oferece painel com estatísticas visuais de vendas, lucros, produtos mais populares, outras métricas que ajudam na análise de desempenho e tomada de decisões."
    },
    "GerenciarPainelConfigurar": {
        "titulo": "Definições",
        "emoji": f"{config2}",
        "prompt": "O módulo de configurações da Anti Ethical permite gerenciar o sistema de anti fakes, configurar métodos de pagamento para vendas, definir canais de logs e personalizar cargos como Cliente, Owner, Suporte, Staff, Membro e Membro Vinculado no eCloud. Oferece controle completo sobre permissões e ajustes que moldam o funcionamento do bot no servidor."
    },
    "GerenciarPainelGiveaways": {
        "titulo": "Sorteios",
        "emoji": "<:giveaway:1358865686813741147>",
        "prompt": "Descreva o módulo de giveaways da Anti Ethical. Ele permite criar sorteios com prêmios verdadeiros e fakes, tempo de duração, requisitos de participação (como ser role específico), configurar número de vencedores e realizar o sorteio de forma automática no canal."
    },
    "GerenciarProtecaoServidor": {
        "titulo": "Proteção",
        "emoji": "<:protection:1358876611595993158>",
        "prompt": "Explique o módulo de proteção da Anti Ethical. Inclui ferramentas anti-raid/spam, verificação de contas novas, bloqueio de links/explícitos, aplicação de filtros de palavras e logging. Essencial para manter a segurança, a integridade do servidor e proteger a loja contra ataques ou conteúdo tóxico."
    }
}

async def gerar_resposta_personagem(personagem_key, prompt_contexto, user_mention):
    """Gera uma resposta usando a Groq API com base no personagem selecionado"""
    personagem = PERSONAGENS_PROMPTS.get(personagem_key, PERSONAGENS_PROMPTS["nenhum"])
    prompt_completo = f"""
{personagem['prompt_inicial']}
Contexto: {prompt_contexto}
Usuário mencionado: {user_mention}
Responda de forma clara e útil, mantendo sua personalidade única. Use emojis apropriados e seja didático, e responda sempre em Português Brasil.
"""
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "user", "content": prompt_completo}
            ],
            model="llama3-8b-8192",
            temperature=0.7,
            max_tokens=800
        )
        resposta = chat_completion.choices[0].message.content
        return f"{personagem['emoji']} {resposta}"
    except Exception as e:
        return f"{personagem['emoji']} Desculpe, estou com problemas para gerar uma resposta no momento. Tente novamente em instantes! 💔"

def obter_personagem_atual():
    """Obtém o personagem atendente atual do config.json"""
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
            return config.get("personagem_atendente", "nenhum")
    except:
        return "nenhum"

def obter_painel_ajuda():
    """Gera o painel de ajuda com os botões dos módulos"""
    personagem_key = obter_personagem_atual()
    personagem = PERSONAGENS_PROMPTS.get(personagem_key, PERSONAGENS_PROMPTS["nenhum"])
    content = f"""# Centro de Ajuda 
{personagem['saudacao']}
Selecione um módulo abaixo para obter ajuda detalhada:"""
    
    # Componentes com os botões dos módulos
    components = [
        [
            disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Sua Loja", emoji=casa, custom_id="ajuda_GerenciarPainelVendas"),
            disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Ticket", emoji=ticket, custom_id="ajuda_GerenciarPainelTicket"),
            disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Boas Vindas", emoji=sino, custom_id="ajuda_GerenciarPainelBoasVindas"),
            disnake.ui.Button(style=disnake.ButtonStyle.grey, label="Ações Automáticas", emoji=reload, custom_id="ajuda_GerenciarAcoesAutomaticas"),
        ],
        [
            disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Personalização", emoji=wand, custom_id="ajuda_GerenciarPainelPersonalizar"),
            disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Meu eCloud", emoji=cloud, custom_id="ajuda_GerenciarPainelECloud"),
            disnake.ui.Button(style=disnake.ButtonStyle.green, label="Rendimento", emoji=carteira, custom_id="ajuda_GerenciarPainelRendimento"),
            disnake.ui.Button(style=disnake.ButtonStyle.grey, label="Definições", emoji=config2, custom_id="ajuda_GerenciarPainelConfigurar"),
        ],
        [
            disnake.ui.Button(style=disnake.ButtonStyle.green, label="Sistema de Giveaways", emoji="<:giveaway:1358865686813741147>", custom_id="ajuda_GerenciarPainelGiveaways"),
            disnake.ui.Button(label="Proteção", emoji="<:protection:1358876611595993158>", custom_id="ajuda_GerenciarProtecaoServidor"),
        ],
        [
            disnake.ui.Button(label="Voltar", emoji=voltar, custom_id="PainelInicial"),
        ]
    ]
    return content, components

class AjudaCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def AjudaButtonListener(self, inter: disnake.MessageInteraction):
        # Botão principal de ajuda
        if inter.component.custom_id == "GerenciarPainelAjuda":
            await inter.response.edit_message(f"{carregarAnimado} Carregando centro de ajuda...", embed=None, components=None)
            content, components = obter_painel_ajuda()
            await inter.edit_original_message(content=content, components=components)
        # Botões específicos de cada módulo
        elif inter.component.custom_id.startswith("ajuda_"):
            modulo_id = inter.component.custom_id.replace("ajuda_", "")
            if modulo_id in MODULOS_PROMPTS:
                await inter.response.defer(ephemeral=False)
                modulo = MODULOS_PROMPTS[modulo_id]
                personagem_key = obter_personagem_atual()
                # Gera a resposta usando a Groq
                resposta = await gerar_resposta_personagem(
                    personagem_key, 
                    modulo["prompt"], 
                    inter.user.mention
                )
                # Cria o embed com a resposta
                embed = disnake.Embed(
                    title=f"{modulo['emoji']} {modulo['titulo']} - Centro de Ajuda",
                    description=resposta,
                    color=0x2b2d31
                )
                embed.set_footer(text=f"Ajudando {inter.user.display_name}", icon_url=inter.user.avatar.url if inter.user.avatar else None)
                # Botão para voltar ao painel de ajuda
                await inter.followup.send(embed=embed, components=None, ephemeral=True)
        # Botão para voltar ao centro de ajuda
        elif inter.component.custom_id == "voltar_ajuda":
            await inter.response.edit_message(f"{carregarAnimado} Voltando ao centro de ajuda...", embed=None, components=None)
            content, components = obter_painel_ajuda()
            await inter.edit_original_message(content=content, embed=None, components=components)

def setup(bot: commands.Bot):
    bot.add_cog(AjudaCommand(bot))
