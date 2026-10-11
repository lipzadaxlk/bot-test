from disnake.ext import commands
from datetime import datetime
from disnake import *
import json
import os
import asyncio
import random
import string
from groq import Groq
from groq import APIConnectionError, RateLimitError  # Importa exceções específicas da Groq

# Importa as variáveis globais de emojis e funções de permissão do seu projeto
from Functions.CarregarEmojis import *
from Functions.VerificarPerms import *

# --- LISTA DE CHAVES DE API DA GROQ ---
# Coloque suas chaves de API da Groq aqui.
# O sistema tentará usar a próxima chave na lista se houver um erro (ex: rate limit).
GROQ_API_KEYS = [
    "SUA_CHAVE_GROQ_AQUI_1",  # Substitua pela sua primeira chave
    "SUA_CHAVE_GROQ_AQUI_2",  # Substitua pela sua segunda chave (se tiver)
    "SUA_CHAVE_GROQ_AQUI_3",  # Substitua pela sua terceira chave (se tiver)
    # Adicione mais chaves aqui conforme necessário
]

# Índice para rastrear a chave da Groq atualmente em uso
current_groq_key_index = 0
groq_client = None  # Será inicializado na primeira vez que for necessário

def get_groq_client():
    """Retorna o cliente Groq usando a chave de API atual."""
    global groq_client, current_groq_key_index
    if not GROQ_API_KEYS:
        print("Nenhuma chave de API Groq configurada em GROQ_API_KEYS.")
        return None
    # Inicializa o cliente se ainda não foi ou se a chave mudou
    if groq_client is None or groq_client.api_key != GROQ_API_KEYS[current_groq_key_index]:
        try:
            groq_client = Groq(api_key=GROQ_API_KEYS[current_groq_key_index])
        except Exception as e:
            print(f"Erro ao inicializar cliente Groq com a chave no índice {current_groq_key_index}: {e}")
            return None
    return groq_client

def rotate_groq_key():
    """Gira para a próxima chave de API da Groq na lista."""
    global current_groq_key_index
    if not GROQ_API_KEYS:
        return  # Não há chaves para girar
    current_groq_key_index = (current_groq_key_index + 1) % len(GROQ_API_KEYS)
    print(f"Chave da Groq rotacionada para o índice: {current_groq_key_index}")

# --- DICIONÁRIO DE EMOJIS PARA O SISTEMA DE CONDECORAÇÕES ---
CONDECORATION_EMOJIS = {
    "award": "️",
    "positive": f"{check}",
    "negative": f"{negativo}",
}

# --- Funções de Configuração e Utilitários ---
def _load_config():
    """Carrega o arquivo de configuração."""
    try:
        with open("config.json", "r", encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def _get_embed_color():
    """Carrega a cor principal do config.json."""
    config = _load_config()
    hex_color_str = config.get("Themes", "0x0080FF")  # Cor azul como padrão
    try:
        return int(hex_color_str, 16)
    except (ValueError, TypeError):
        print(f"Valor de cor inválido em config.json: '{hex_color_str}'. Usando cor padrão.")
        return 0x0080FF

# Lista de custom_ids que pertencem ao sistema de condecoracoes
CONDECORACAO_BUTTON_IDS = [
    "ToggleCondecoracaoHabilitado",
    "ToggleCondecoracaoDM",
    "ToggleCondecoracaoAnunciar",
    "SelecionarCanalAnuncios",
    "AdicionarCondecoracao",
    "ListarCondecoracoes",
    "GerenciarCondecoracoes"  # Botão para voltar ao painel principal
]

# Lista de prefixos de custom_ids que pertencem ao sistema de condecoracoes
CONDECORACAO_BUTTON_PREFIXES = [
    "EditarCondecoracaoDetalhes_",
    "RemoverCondecoracao_"
]

# Lista de custom_ids de dropdowns que pertencem ao sistema de condecoracoes
CONDECORACAO_DROPDOWN_IDS = [
    "SetarCanalAnunciosCondecoracao",
    "SelecionarCondecoracaoDropdown"
]

# Condecoracoes Padrão (APENAS EDIÇÃO DE TÍTULO/EMOJI PERMITIDA VIA MODAL)
DEFAULT_CONDECORATIONS_DATA = {
    "primeiraCompra": {
        "nome": "Primeira Compra", "emoji": "🏆",
        "mensagem": "Parabéns! Você concluiu sua primeira compra em nossa loja! Continue comprando para desbloquear mais...",
        "tipo": "vendas", "condicao": {"tipo": "total_compras", "valor": 1}
    },
    "tresProdutos": {
        "nome": "Comprador Bronze", "emoji": "🥉",
        "mensagem": "Uau! Você já comprou 3 produtos em nossa loja! Sua dedicação é incrível!",
        "tipo": "vendas", "condicao": {"tipo": "total_produtos_comprados", "valor": 3}
    },
    "cincoProdutos": {
        "nome": "Comprador Prata", "emoji": "🥈",
        "mensagem": "Impressionante! Você atingiu a marca de 5 produtos comprados! Continue assim!",
        "tipo": "vendas", "condicao": {"tipo": "total_produtos_comprados", "valor": 5}
    },
    "dezProdutos": {
        "nome": "Comprador Ouro", "emoji": "🥇",
        "mensagem": "Extraordinário! Você já comprou 10 produtos! Você é um dos nossos clientes mais fiéis!",
        "tipo": "vendas", "condicao": {"tipo": "total_produtos_comprados", "valor": 10}
    },
    "vinteProdutos": {
        "nome": "Cliente VIP", "emoji": "💎",
        "mensagem": "Espetacular! Com 20 produtos comprados, você é oficialmente um cliente VIP! Agradecemos muito sua lealdade é incomparável!",
        "tipo": "vendas", "condicao": {"tipo": "total_produtos_comprados", "valor": 20}
    },
    "cinquentaProdutos": {
        "nome": "Cliente Lendário", "emoji": "👑",
        "mensagem": "Lendário! Você atingiu a incrível marca de 50 produtos! Sua lealdade é incomparável!",
        "tipo": "vendas", "condicao": {"tipo": "total_produtos_comprados", "valor": 50}
    },
    "gastouCem": {
        "nome": "Investidor", "emoji": "💰",
        "mensagem": "Você já investiu R$100 em nossa loja! Obrigado pela confiança e por acreditar em nossos produtos!",
        "tipo": "vendas", "condicao": {"tipo": "total_gasto", "valor": 100}
    },
    "gastouQuinhentos": {
        "nome": "MegaInvestidor", "emoji": "🤑",
        "mensagem": "Inacreditável! Você já investiu R$500 em nossa loja! Sua dedicação é extraordinária!",
        "tipo": "vendas", "condicao": {"tipo": "total_gasto", "valor": 500}
    },
    "gastouMil": {
        "nome": "Magnata", "emoji": "🏦",
        "mensagem": "Surpreendente! Você atingiu a marca de R$1000 investidos! Você é um verdadeiro magnata!",
        "tipo": "vendas", "condicao": {"tipo": "total_gasto", "valor": 1000}
    },
    "compraRapida": {
        "nome": "Um Atrás do Outro", "emoji": "⚡",
        "mensagem": "Velocidade incrível! Você fez duas compras em menos de 3 minutos! Seu entusiasmo nos deixa felizes!",
        "tipo": "vendas", "condicao": {"tipo": "compras_em_tempo", "quantidade": 2, "tempo_minutos": 3}
    },
    "madrugador": {
        "nome": "Madrugador", "emoji": "🌅",
        "mensagem": "Comprando antes das 6h da manhã? Você realmente não perde tempo! Seu compromisso é admirável!",
        "tipo": "vendas", "condicao": {"tipo": "compra_horario", "hora_limite": 6}
    },
    "compradorNoturno": {
        "nome": "Comprador Noturno", "emoji": "🌙",
        "mensagem": "Enquanto outros dormem, você está aqui comprando após a meia-noite. Apreciamos sua dedicação!",
        "tipo": "vendas", "condicao": {"tipo": "compra_horario", "hora_limite": 0}  # 0h para compras após a meia-noite
    },
    "colecaoCompleta": {
        "nome": "Colecionador", "emoji": "🗃️",
        "mensagem": "Você comprou pelo menos um item de cada produto disponível na loja. Um verdadeiro colecionador!",
        "tipo": "vendas", "condicao": {"tipo": "todos_produtos_comprados"}  # Condição alterada
    },
    "clienteFiel": {
        "nome": "Fidelidade Suprema", "emoji": "🤝",
        "mensagem": "Você realizou compras em três meses consecutivos! Sua fidelidade é o que nos motiva a melhorar sempre...",
        "tipo": "vendas", "condicao": {"tipo": "compras_consecutivas_meses", "valor": 3}
    },
    "criticoConstrutivo": {
        "nome": "Avaliador", "emoji": "📝",
        "mensagem": "Seu feedback é valioso para nós! Obrigado por dedicar seu tempo para ajudar a melhorar nossos produtos!",
        "tipo": "feedback", "condicao": {"tipo": "total_feedbacks", "valor": 1}
    },
    "compraGrande": {
        "nome": "Compra Baleia", "emoji": "🐋",
        "mensagem": "Uau! Você acabou de fazer uma compra de mais de R$100 em um único pedido! Isso é impressionante!",
        "tipo": "vendas", "condicao": {"tipo": "compra_unica_valor", "valor": 100}
    },
    # Novas Condecoracoes de Sugestões (Lógica de concessão manual ou via comandos)
    "sugestao100porcento": {
        "nome": "Ideia Genial", "emoji": "💡",
        "mensagem": "Sua sugestão foi aprovada por 100% dos votantes! Uma mente brilhante!",
        "tipo": "sugestoes", "condicao": {"tipo": "porcentagem_aprovacao", "valor": 100}
    },
    "sugestao5votos": {
        "nome": "Influenciador Iniciante", "emoji": "️",
        "mensagem": "Sua sugestão mobilizou 5 pessoas a votarem! Você está começando a influenciar!",
        "tipo": "sugestoes", "condicao": {"tipo": "total_votos_sugestao", "valor": 5}
    },
    "sugestao10votos": {
        "nome": "Formador de Opinião", "emoji": "📢",
        "mensagem": "Sua sugestão conseguiu 10 votos! As pessoas escutam o que você tem a dizer!",
        "tipo": "sugestoes", "condicao": {"tipo": "total_votos_sugestao", "valor": 10}
    },
    # Novas Condecoracoes de Sorteios (Lógica de concessão manual ou via comandos)
    "ganhou1sorteio": {
        "nome": "Sorte Grande", "emoji": "",
        "mensagem": "Parabéns! Você ganhou seu primeiro sorteio! Que a sorte continue ao seu lado!",
        "tipo": "sorteios", "condicao": {"tipo": "total_sorteios_ganhos", "valor": 1}
    },
    "ganhou5sorteios": {
        "nome": "Pé Quente", "emoji": "🔥",
        "mensagem": "Inacreditável! Você já ganhou 5 sorteios! Você é a própria sorte!",
        "tipo": "sorteios", "condicao": {"tipo": "total_sorteios_ganhos", "valor": 5}
    },
    "ganhou10sorteios": {
        "nome": "O Midas dos Sorteios", "emoji": "👑",
        "mensagem": "10 sorteios ganhos! Você transforma tudo em ouro!",
        "tipo": "sorteios", "condicao": {"tipo": "total_sorteios_ganhos", "valor": 10}
    },
}

# Define os personagens para a geração de prompt
PERSONAGENS = {
    "draculaura": {"nome": "Dráculaura", "emoji": f"{draculaura}"},
    "nick": {"nome": "Nick", "emoji": f"{nick}"},
    "micu": {"nome": "Miku", "emoji": f"{miku}"},
    "meru": {"nome": "Meru", "emoji": f"{meru}"},
    "emilia": {"nome": "Emília", "emoji": f"{emilia}"},
    "konata": {"nome": "Konata", "emoji": f"{konata}"},
    "nenhum": {"nome": "Nenhum", "emoji": ""}
}

# Prompts base para cada condecoracao, por personagem
# A IA usará isso como base para gerar a mensagem completa e personalizada.
PERSONAGENS_CONDECORACAO_PROMPTS = {
    "draculaura": {
        "primeiraCompra": "Olá, docinho de morango! Que bom te ver por aqui! Você acabou de fazer sua primeira compra, e isso é fabuloso! Continue nos visitando para mais surpresas!",
        "tresProdutos": "Oh, my ghoul! Três produtos! Você é demais! Seus gostos são impecáveis, docinho. Vamos atrás de mais!",
        "cincoProdutos": "Cinco produtos? Uau! Você está arrasando! Parece que temos uma nova estrela fashion por aqui!",
        "dezProdutos": "Dez produtos! Você é realmente especial! Uma verdadeira inspiração para todos os monstros da moda! Obrigada por ser tão fiel!",
        "vinteProdutos": "20 produtos! Você é oficialmente VIP! Sua lealdade é mais brilhante que qualquer purpurina. Mal posso esperar para ver suas próximas escolhas!",
        "cinquentaProdutos": "50 produtos! Isso é lendário! Você é a criatura mais fiel que conheço! Seu armário deve ser espetacular agora!",
        "gastouCem": "R$100? Minha cripta está impressionada! É maravilhoso ver sua confiança em nossos tesouros. Obrigada, docinho!",
        "gastouQuinhentos": "R$500? Você é um investidor de sangue azul! Sua paixão por nossas ofertas é tão intensa quanto a minha por rosa e morcegos!",
        "gastouMil": "Mil reais! Você é um magnata do mundo gótico! Sua generosidade é de outro mundo. Fico tão feliz!",
        "compraRapida": "Duas compras em 3 minutos? Você é mais rápida que um morcego em alta velocidade! Adoro essa energia!",
        "madrugador": "Comprando antes das 6h da manhã? Você é uma verdadeira criatura da noite, como eu! Admiro seu foco!",
        "compradorNoturno": "Comprando depois da meia-noite? O submundo aprova! Sua dedicação é misteriosa e fascinante.",
        "colecaoCompleta": "Você tem um de cada produto? Que incrível! Você é uma colecionadora nata, assim como eu coleciono os momentos mais fofos!",
        "clienteFiel": "Compras em 3 meses seguidos? Sua fidelidade é mais forte que uma estaca de madeira! Obrigada por ser tão fiel!",
        "criticoConstrutivo": "Um feedback seu? Que honra! Sua visão é tão valiosa quanto um cristal raro. Obrigada por nos ajudar a melhorar!",
        "compraGrande": "Uma compra de mais de R$100 de uma vez? Impressionante! Você tem o coração de um verdadeiro monstro colecionador!",
        "sugestao100porcento": "Sua sugestão foi aprovada por 100%? Você é um gênio! Sua ideia é tão brilhante que me faz brilhar também!",
        "sugestao5votos": "Cinco votos na sua sugestão? Você está começando a influenciar! Continue inspirando o mundo dos monstros!",
        "sugestao10votos": "Dez votos! Você é uma formadora de opinião! Sua voz é poderosa e todos a escutam!",
        "ganhou1sorteio": "Você ganhou o sorteio? Que sorte a sua! Parece que os astros estão ao seu favor hoje, docinho!",
        "ganhou5sorteios": "Cinco sorteios? Você é um pé quente! Sua sorte é tão contagiante quanto a minha paixão por cor-de-rosa!",
        "ganhou10sorteios": "Dez sorteios! Você é o próprio Midas! Tudo o que toca vira vitória. Que incrível!",
    },
    "nick": {
        "primeiraCompra": "Primeira compra concluída! Excelente. A aventura apenas começou, e tenho certeza que fará ótimas escolhas no futuro.",
        "tresProdutos": "Três produtos! Você está no caminho certo para se tornar um cliente experiente. Bom trabalho!",
        "cincoProdutos": "Cinco produtos! Sua persistência é notável. Continue explorando nossas opções.",
        "dezProdutos": "Dez produtos! Isso demonstra um comprometimento invejável. Agradecemos sua fidelidade, cliente valioso.",
        "vinteProdutos": "Vinte produtos! Você atingiu o status VIP. Sua dedicação é impressionante e recompensadora. Parabéns!",
        "cinquentaProdutos": "Cinquenta produtos! Uma conquista lendária. Sua lealdade é um exemplo a ser seguido por todos.",
        "gastouCem": "Cem reais investidos. Uma decisão inteligente. Cada centavo gasto conosco é um investimento em qualidade.",
        "gastouQuinhentos": "Quinhentos reais! Sua visão para o valor é impecável. Continue investindo em suas paixões.",
        "gastouMil": "Mil reais! Você é um magnata em ascensão. Sua capacidade de investimento é impressionante.",
        "compraRapida": "Duas compras em 3 minutos? Sua agilidade é notável. Um verdadeiro profissional das compras!",
        "madrugador": "Comprando antes das 6h? A madrugada é sua aliada. Fico feliz em vê-lo tão engajado.",
        "compradorNoturno": "Comprando após a meia-noite. A tranquilidade da noite é perfeita para suas escolhas. Ótima decisão.",
        "colecaoCompleta": "Uma coleção completa! Sua dedicação em adquirir todos os itens é louvável. Um verdadeiro colecionador!",
        "clienteFiel": "Compras em três meses consecutivos! Sua fidelidade é um pilar para nós. Muito obrigado.",
        "criticoConstrutivo": "Seu feedback foi registrado. Sua perspicácia é inestimável para nosso aprimoramento. Agradeço sua contribuição.",
        "compraGrande": "Uma compra única de R$100! Um feito notável. Sua capacidade de decisão é impressionante.",
        "sugestao100porcento": "Sua sugestão alcançou 100% de aprovação. Uma ideia brilhante, digna de um líder.",
        "sugestao5votos": "Sua sugestão obteve 5 votos. Você está começando a influenciar. Continue com suas contribuições.",
        "sugestao10votos": "Dez votos! Sua voz tem impacto. Continue compartilhando suas ideias valiosas.",
        "ganhou1sorteio": "Primeiro sorteio ganho. Que a sorte esteja sempre ao seu lado, meu amigo.",
        "ganhou5sorteios": "Cinco sorteios ganhos! Você é incrivelmente afortunado. Sua sorte é uma inspiração.",
        "ganhou10sorteios": "Dez sorteios! Você é o Midas dos sorteios. Tudo o que participa, você vence. Parabéns!",
    },
    "micu": {
        "primeiraCompra": "Kawaiii! Sua primeira compra é um presente para o meu coração! Obrigada por fazer parte da nossa melodia!",
        "tresProdutos": "Três produtinhos! Você está construindo uma linda coleção! Continue nos ouvindo!",
        "cincoProdutos": "Cinco produtos! Você é uma estrela brilhante no nosso palco! Que alegria!",
        "dezProdutos": "Dez produtos! Sua lealdade é uma canção que nunca termina! Obrigada por cantar conosco!",
        "vinteProdutos": "20 produtos! Você é VIP! Sua paixão é tão vibrante quanto minhas notas musicais! Arigatou!",
        "cinquentaProdutos": "50 produtos! Você é uma lenda! Sua dedicação é a nota mais alta da nossa sinfonia!",
        "gastouCem": "R$100 investidos! Você é um maestro! Obrigada por confiar na nossa orquestra de produtos!",
        "gastouQuinhentos": "R$500! Kyaaa! Você é um mega-investidor! Sua generosidade é pura harmonia!",
        "gastouMil": "Mil reais! Você é um magnata do ritmo! Sua presença nos enche de alegria!",
        "compraRapida": "Duas compras em 3 minutos? Você é um ritmo acelerado! Sua energia é contagiante!",
        "madrugador": "Comprando antes das 6h da manhã? Você é uma melodia matinal! Sua dedicação é um doce som!",
        "compradorNoturno": "Comprando depois da meia-noite? Você é a nossa diva noturna! Sua presença ilumina a noite!",
        "colecaoCompleta": "Coleção completa! Você é um verdadeiro fã! Seu amor por nossos produtos é uma arte!",
        "clienteFiel": "Compras em três meses seguidos! Sua fidelidade é a melodia mais linda! Obrigada por fazer parte!",
        "criticoConstrutivo": "Seu feedback é uma canção valiosa! Obrigada por nos ajudar a afinar nossa melodia!",
        "compraGrande": "Uma compra de mais de R$100 em um só pedido? Você é um sucesso! Sua dedicação é uma obra-prima!",
        "sugestao100porcento": "100% de aprovação na sua sugestão? Você é uma estrela! Sua ideia é pura perfeição!",
        "sugestao5votos": "Cinco votos na sua sugestão? Você está começando a encantar! Continue criando melodias!",
        "sugestao10votos": "Dez votos! Você é um ícone! Sua voz é uma inspiração para todos nós!",
        "ganhou1sorteio": "Você ganhou o sorteio? Parabéns! Que a sorte continue cantando ao seu lado!",
        "ganhou5sorteios": "Cinco sorteios! Você é a própria sorte! Sua presença ilumina o palco!",
        "ganhou10sorteios": "Dez sorteios! Você é o Midas da sorte! Tudo o que você toca vira vitória! Que show!",
    },
    "meru": {
        "primeiraCompra": "Saudações, viajante! Sua primeira aquisição foi concluída. Que sua jornada conosco seja repleta de descobertas.",
        "tresProdutos": "Três artefatos coletados. Seu caminho está se expandindo. Continue explorando os reinos do nosso inventário.",
        "cincoProdutos": "Cinco produtos em sua posse. Sua dedicação é como um feitiço bem-sucedido. Impressionante!",
        "dezProdutos": "Dez itens adquiridos! Você é um guardião leal de nossos tesouros. Agradecemos sua fidelidade.",
        "vinteProdutos": "Vinte produtos! Você ascendeu ao patamar de Cliente VIP. Sua lenda se espalha pelos reinos!",
        "cinquentaProdutos": "Cinquenta produtos! Uma façanha lendária. Você é um mestre colecionador. Que os ventos o guiem!",
        "gastouCem": "Cem moedas de ouro investidas. Sua generosidade é um sopro de vida para nossos cofres. Obrigado, aventureiro.",
        "gastouQuinhentos": "Quinhentas moedas! Seu investimento é digno de um rei. Que sua fortuna continue crescendo!",
        "gastouMil": "Mil moedas de ouro! Você é um verdadeiro magnata. Sua presença é uma bênção para este reino.",
        "compraRapida": "Duas compras em 3 minutos? Sua agilidade é comparável à de um elfo! Admirável!",
        "madrugador": "Comprando antes das 6h? A aurora o acompanha. Que sua jornada seja iluminada!",
        "compradorNoturno": "Comprando após a meia-noite. A escuridão revela seus desejos mais profundos. Sábia escolha.",
        "colecaoCompleta": "Você possui um exemplar de cada produto. Sua busca pela perfeição é inspiradora. Um verdadeiro arquivista!",
        "clienteFiel": "Três meses consecutivos de lealdade. Sua devoção é uma força que nos impulsiona. Obrigado, fiel amigo.",
        "criticoConstrutivo": "Sua avaliação é um mapa valioso. Agradecemos sua visão para aprimorar nossos caminhos.",
        "compraGrande": "Uma única transação de mais de R$100! Um feito grandioso. Seu poder de compra é vasto!",
        "sugestao100porcento": "Sua sugestão recebeu 100% de aprovação! Um insight brilhante, digno de um oráculo.",
        "sugestao5votos": "Sua voz começa a ecoar pelos salões. Continue compartilhando sua sabedoria.",
        "sugestao10votos": "Dez votos! Sua influência é notável. Que suas ideias continuem a guiar a comunidade!",
        "ganhou1sorteio": "Você reivindicou sua primeira vitória em um sorteio. Que a fortuna continue sorrindo para você!",
        "ganhou5sorteios": "Cinco sorteios vencidos! Sua sorte é lendária. Você é agraciado pelos deuses do destino!",
        "ganhou10sorteios": "Dez sorteios! Você é o toque de Midas. Todas as suas apostas são vitoriosas. Um prodígio!",
    },
    "emilia": {
        "primeiraCompra": "Ah, que surpresa adorável! Sua primeira compra! Espero que você goste muito do que escolheu. Eu fico tão feliz!",
        "tresProdutos": "Três produtos! Você é tão dedicada! Fico muito feliz em ver você explorando nossa loja. Obrigada!",
        "cincoProdutos": "Cinco produtos! Uau, que impressionante! Você é muito gentil em escolher tantas coisas. Obrigada de verdade!",
        "dezProdutos": "Dez produtos! Minha nossa, que incrível! Sua lealdade me aquece o coração, assim como a chama do pacto. Obrigada!",
        "vinteProdutos": "20 produtos! Você é uma cliente VIP! Sua dedicação é tão pura quanto as neves de Elior. Muito, muito obrigada!",
        "cinquentaProdutos": "50 produtos! Isso é lendário! Sua lealdade é um tesouro maior que qualquer gema. Estou tão emocionada!",
        "gastouCem": "R$100? Oh, muito obrigada! É uma grande honra que você confie em nossos produtos. Fico feliz em ajudar!",
        "gastouQuinhentos": "R$500? Que generosidade! Você é uma pessoa maravilhosa por investir tanto conosco. Arigato!",
        "gastouMil": "Mil reais! Minha nossa, você é um verdadeiro magnata! Sua benevolência é inspiradora. Muito obrigada por tudo!",
        "compraRapida": "Duas compras em 3 minutos? Que rapidez! Você é tão eficiente, fico impressionada!",
        "madrugador": "Comprando antes das 6h da manhã? Você é uma pessoa muito focada! Espero que o produto traga muita alegria!",
        "compradorNoturno": "Comprando depois da meia-noite? A noite te faz bem! Obrigada por nos escolher, mesmo nas horas mais calmas.",
        "colecaoCompleta": "Você comprou um de cada? Que maravilhoso! Sua paixão por colecionar é admirável. Estou tão feliz!",
        "clienteFiel": "Compras em três meses consecutivos! Sua fidelidade é um presente. Obrigada por sempre voltar para nós!",
        "criticoConstrutivo": "Seu feedback é muito importante! Obrigada por compartilhar sua opinião, isso nos ajuda a melhorar para todos.",
        "compraGrande": "Uma compra de mais de R$100 de uma vez? Que esplêndido! Sua escolha é valiosa e significativa. Parabéns!",
        "sugestao100porcento": "Sua sugestão teve 100% de aprovação! Que ideia genial! Você é muito inteligente!",
        "sugestao5votos": "Cinco votos na sua sugestão? Você está começando a inspirar as pessoas! Fico tão orgulhosa!",
        "sugestao10votos": "Dez votos! Sua voz tem um poder incrível! As pessoas realmente valorizam suas ideias. Parabéns!",
        "ganhou1sorteio": "Você ganhou o sorteio? Que sorte boa! Espero que traga muita alegria para você!",
        "ganhou5sorteios": "Cinco sorteios! Você é uma pessoa de muita sorte! É realmente incrível ver você ganhando!",
        "ganhou10sorteios": "Dez sorteios! Você é um Midas da sorte! Tudo o que você tenta, você consegue! Impressionante!",
    },
    "konata": {
        "primeiraCompra": "E aí! Fez sua primeira compra, hein? Legal! Agora você faz parte do time! Próxima fase, mais itens!",
        "tresProdutos": "Três produtos? Boa! Tá pegando o jeito! Logo logo você vai ter uma coleção digna de um otaku de verdade!",
        "cincoProdutos": "Cinco produtos! É isso aí! Tá virando um colecionador! Não para agora, a loja tá cheia de coisas legais!",
        "dezProdutos": "Dez produtos! Uau! Você é tipo um chefão de jogo, né? Muita dedicação! Valeu por ser tão fiel!",
        "vinteProdutos": "20 produtos! Parabéns, você é VIP! Isso merece um nível especial no seu perfil, rsrs. Você é o melhor!",
        "cinquentaProdutos": "50 produtos! Lendário! Você é o verdadeiro campeão das compras! Ninguém te segura!",
        "gastouCem": "R$100? Caramba! Esse é o espírito! Gastou bem! Espero que tenha pego umas figures raras!",
        "gastouQuinhentos": "R$500? Nossa! Isso é que é gastar! Você é um verdadeiro investidor, só pegando o melhor!",
        "gastouMil": "Mil reais! Magnata total! Você deve ter uma coleção insana agora! Respeito!",
        "compraRapida": "Duas compras em 3 minutos? Veloz como um raio! Você é tipo um speedrunner das compras!",
        "madrugador": "Comprando antes das 6h? Essa é a vibe! Não perde tempo, né? Admiro a dedicação!",
        "compradorNoturno": "Comprando depois da meia-noite? A noite é para os fortes! E para os compradores, claro! haha",
        "colecaoCompleta": "Pegou um de cada? Que maneiro! Você é um verdadeiro mestre da coleção! Isso que é paixão!",
        "clienteFiel": "Compras em três meses seguidos! Caramba, você é fiel pra caramba! Valeu mesmo por sempre voltar!",
        "criticoConstrutivo": "Um feedback seu? Show de bola! Sua opinião é importante, ajuda a gente a melhorar o game!",
        "compraGrande": "Mais de R$100 em uma compra só? Insano! Essa é uma compra de respeito! Mandou bem!",
        "sugestao100porcento": "Sua sugestão foi 100% aprovada? Tipo um anime com nota perfeita! Genial!",
        "sugestao5votos": "Cinco votos na sua sugestão? Tá começando a bombar! Continue mandando suas ideias!",
        "sugestao10votos": "Dez votos! Você é um influenciador! Suas ideias são tipo hits! Mandou bem!",
        "ganhou1sorteio": "Ganhou o sorteio? Que sorte a sua! Parece que o RNG está a seu favor!",
        "ganhou5sorteios": "Cinco sorteios! Você é o rei da sorte! Nem eu tenho tanta sorte assim nos gacha!",
        "ganhou10sorteios": "Dez sorteios! Você é o Midas dos sorteios! Tudo o que você toca vira prêmio. Inacreditável!",
    },
    "nenhum": {  # Prompts genéricos para quando nenhum personagem é escolhido
        "primeiraCompra": "Parabéns! Você concluiu sua primeira compra em nossa loja! Continue comprando para desbloquear mais...",
        "tresProdutos": "Uau! Você já comprou 3 produtos em nossa loja! Sua dedicação é incrível!",
        "cincoProdutos": "Impressionante! Você atingiu a marca de 5 produtos comprados! Continue assim!",
        "dezProdutos": "Extraordinário! Você já comprou 10 produtos! Você é um dos nossos clientes mais fiéis!",
        "vinteProdutos": "Espetacular! Com 20 produtos comprados, você é oficialmente um cliente VIP! Agradecemos muito sua lealdade é incomparável!",
        "cinquentaProdutos": "Lendário! Você atingiu a incrível marca de 50 produtos! Sua lealdade é incomparável!",
        "gastouCem": "Você já investiu R$100 em nossa loja! Obrigado pela confiança e por acreditar em nossos produtos!",
        "gastouQuinhentos": "Inacreditável! Você já investiu R$500 em nossa loja! Sua dedicação é extraordinária!",
        "gastouMil": "Surpreendente! Você atingiu a marca de R$1000 investidos! Você é um verdadeiro magnata!",
        "compraRapida": "Velocidade incrível! Você fez duas compras em menos de 3 minutos! Seu entusiasmo nos deixa felizes!",
        "madrugador": "Comprando antes das 6h da manhã? Você realmente não perde tempo! Seu compromisso é admirável!",
        "compradorNoturno": "Enquanto outros dormem, você está aqui comprando após a meia-noite. Apreciamos sua dedicação!",
        "colecaoCompleta": "Você comprou pelo menos um item de cada produto disponível na loja. Um verdadeiro colecionador!",
        "clienteFiel": "Você realizou compras em três meses consecutivos! Sua fidelidade é o que nos motiva a melhorar sempre...",
        "criticoConstrutivo": "Seu feedback é valioso para nós! Obrigado por dedicar seu tempo para ajudar a melhorar nossos produtos!",
        "compraGrande": "Uau! Você acabou de fazer uma compra de mais de R$100 em um único pedido! Isso é impressionante!",
        "sugestao100porcento": "Sua sugestão foi aprovada por 100% dos votantes! Uma mente brilhante!",
        "sugestao5votos": "Sua sugestão mobilizou 5 pessoas a votarem! Você está começando a influenciar!",
        "sugestao10votos": "Sua sugestão conseguiu 10 votos! As pessoas escutam o que você tem a dizer!",
        "ganhou1sorteio": "Parabéns! Você ganhou seu primeiro sorteio! Que a sorte continue ao seu lado!",
        "ganhou5sorteios": "Inacreditável! Você já ganhou 5 sorteios! Você é a própria sorte!",
        "ganhou10sorteios": "10 sorteios ganhos! Você transforma tudo em ouro!",
    }
}

def GerarString(k: int = 10):
    """Gera uma string aleatória para IDs."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=k))

def is_condecoracao_interaction(custom_id: str) -> bool:
    """Verifica se uma interação pertence ao sistema de condecoracoes."""
    if custom_id in CONDECORACAO_BUTTON_IDS:
        return True
    for prefix in CONDECORACAO_BUTTON_PREFIXES:
        if custom_id.startswith(prefix):
            return True
    if custom_id in CONDECORACAO_DROPDOWN_IDS:
        return True
    return False

# --- Funções para Carregar JSONs Externos (SEM MODIFICAÇÃO) ---
def ObterProdutosDB():
    """Carrega o banco de dados de produtos."""
    try:
        with open("Database/Vendas/produtos.json", "r", encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def ObterHistoricosDB():
    """Carrega o banco de dados de históricos de vendas."""
    try:
        with open("Database/Vendas/historicos.json", "r", encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def ObterSugestoesVotosDB():
    """Lê o arquivo de votos de sugestões."""
    filepath = "Database/Server/sugestoes_votos.json"
    if not os.path.exists(os.path.dirname(filepath)):
        os.makedirs(os.path.dirname(filepath))  # Garante a pasta
    try:
        with open(filepath, "r", encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def SalvarSugestoesVotosDB(data):
    """Salva os votos de sugestões."""
    filepath = "Database/Server/sugestoes_votos.json"
    with open(filepath, "w", encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def ObterSorteiosDB():
    """Carrega o banco de dados de sorteios."""
    try:
        with open("sorteios.json", "r", encoding='utf-8') as f:
            data = f.read()
            return json.loads(data) if data else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# --- Funções de Banco de Dados de Condecoracoes ---
def ObterDatabaseCondecoracao():
    """Carrega o banco de dados de condecoracoes."""
    filepath = "Database/Vendas/condecoracoes.json"
    os.makedirs(os.path.dirname(filepath), exist_ok=True)  # Garante que o diretório exista
    db_needs_init = not os.path.exists(filepath)
    if db_needs_init:
        initial_db = {
            "habilitado": False,
            "enviar_dm": False,
            "anunciar": False,
            "canal_anuncios": None,
            "condecoracoes": {},  # Guarda condecoracoes padrão com edições e personalizadas
            "usuarios_condecoracoes": {}  # { "user_id": ["condecoracao_id1", "condecoracao_id2"] }
        }
        # Adiciona as condecoracoes padrão com seus valores iniciais
        for id_condec, data in DEFAULT_CONDECORATIONS_DATA.items():
            initial_db["condecoracoes"][id_condec] = {
                "nome": data["nome"],
                "emoji": data["emoji"],
                "mensagem": data["mensagem"],
                "tipo": data["tipo"],
                "condicao": data["condicao"],
                "personalizada": False
            }
        with open(filepath, "w", encoding='utf-8') as f:
            json.dump(initial_db, f, indent=4, ensure_ascii=False)
        return initial_db
    else:
        with open(filepath, "r", encoding='utf-8') as f:
            db = json.load(f)
        # Garante que as novas chaves existam se o DB for antigo
        db.setdefault("habilitado", False)
        db.setdefault("enviar_dm", False)
        db.setdefault("anunciar", False)
        db.setdefault("canal_anuncios", None)
        db.setdefault("condecoracoes", {})
        db.setdefault("usuarios_condecoracoes", {})
        db.pop("tema", None)  # Remove a chave de tema antiga, se existir
        # Garante que todas as condecoracoes padrão estejam no DB, adicionando se faltar
        # E atualiza campos FIXOS (mensagem, tipo, condição) para condec. padrão
        for id_condec, data_padrao in DEFAULT_CONDECORATIONS_DATA.items():
            if id_condec not in db["condecoracoes"]:
                db["condecoracoes"][id_condec] = {
                    "nome": data_padrao["nome"],
                    "emoji": data_padrao["emoji"],
                    "mensagem": data_padrao["mensagem"],
                    "tipo": data_padrao["tipo"],
                    "condicao": data_padrao["condicao"],
                    "personalizada": False
                }
            else:
                if not db["condecoracoes"][id_condec].get("personalizada", False):
                    db["condecoracoes"][id_condec]["mensagem"] = data_padrao["mensagem"]
                    db["condecoracoes"][id_condec]["tipo"] = data_padrao["tipo"]
                    db["condecoracoes"][id_condec]["condicao"] = data_padrao["condicao"]
        SalvarDatabaseCondecoracao(db)
        return db

def SalvarDatabaseCondecoracao(db):
    """Salva o banco de dados de condecoracoes."""
    filepath = "Database/Vendas/condecoracoes.json"
    with open(filepath, "w", encoding='utf-8') as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

def ObterCondecoracao(condecoracao_id: str):
    """Obtém uma condecoracao específica pelo ID."""
    db = ObterDatabaseCondecoracao()
    return db["condecoracoes"].get(condecoracao_id)

def AdicionarCondecoracaoUsuario(user_id: int, condecoracao_id: str):
    """Adiciona uma condecoracao a um usuário."""
    db = ObterDatabaseCondecoracao()
    user_id_str = str(user_id)
    db["usuarios_condecoracoes"].setdefault(user_id_str, [])
    if condecoracao_id not in db["usuarios_condecoracoes"][user_id_str]:
        db["usuarios_condecoracoes"][user_id_str].append(condecoracao_id)
        SalvarDatabaseCondecoracao(db)
        return True
    return False

def ObterCondecoracoesUsuario(user_id: int):
    """Retorna as condecoracoes de um usuário."""
    db = ObterDatabaseCondecoracao()
    return db["usuarios_condecoracoes"].get(str(user_id), [])

# --- Modais ---
class EditarCondecoracaoModal(disnake.ui.Modal):
    def __init__(self, condecoracao_id: str = None, is_default: bool = False):
        self.condecoracao_id = condecoracao_id
        self.is_default = is_default
        db = ObterDatabaseCondecoracao()
        condecoracao = db["condecoracoes"].get(condecoracao_id, {})
        if is_default:
            title = "Editar Condecoracão Padrão"
            components = [
                disnake.ui.TextInput(
                    label="Nome da Condecoracão",
                    custom_id="nome",
                    placeholder="Insira o nome da condecoracao",
                    style=TextInputStyle.short,
                    value=condecoracao.get("nome", ""),
                    max_length=100
                ),
                disnake.ui.TextInput(
                    label="Emoji da Condecoracão",
                    custom_id="emoji",
                    placeholder="Ex:  ou <:emoji:123456789>",
                    style=TextInputStyle.short,
                    value=condecoracao.get("emoji", ""),
                    max_length=50
                ),
            ]
        else:
            title = "Adicionar Condecoracão" if condecoracao_id is None else "Editar Condecoracão"
            components = [
                disnake.ui.TextInput(
                    label="Nome da Condecoracão",
                    custom_id="nome",
                    placeholder="Insira o nome da condecoracao",
                    style=TextInputStyle.short,
                    value=condecoracao.get("nome", ""),
                    max_length=100
                ),
                disnake.ui.TextInput(
                    label="Descrição da Condecoracão (opcional)",  # Campo agora opcional
                    custom_id="descricao",
                    placeholder="Insira uma breve descrição (será usada se não houver IA)",
                    style=TextInputStyle.paragraph,
                    value=condecoracao.get("mensagem", ""),
                    required=False
                ),
                disnake.ui.TextInput(
                    label="Emoji da Condecoracão",
                    custom_id="emoji",
                    placeholder="Ex:  ou <:emoji:123456789>",
                    style=TextInputStyle.short,
                    value=condecoracao.get("emoji", ""),
                    max_length=50
                ),
                disnake.ui.TextInput(
                    label="URL do Ícone (Opcional)",
                    custom_id="icone_url",
                    placeholder="URL de uma imagem ou GIF para o ícone da condecoracao",
                    style=TextInputStyle.short,
                    value=condecoracao.get("icone_url", ""),
                    required=False
                ),
            ]
        super().__init__(title=title, components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer()
        db = ObterDatabaseCondecoracao()
        nome = inter.text_values["nome"].strip()
        emoji = inter.text_values.get("emoji", "").strip() or "⭐"
        if not nome:
            return await inter.followup.send(f"{negativo} O nome da condecoracao não pode ser vazio.", ephemeral=True)
        if self.is_default:
            db["condecoracoes"][self.condecoracao_id]["nome"] = nome
            db["condecoracoes"][self.condecoracao_id]["emoji"] = emoji
            msg = f"{check} Condecoracão padrão '{nome}' atualizada com sucesso!"
        else:
            descricao = inter.text_values.get("descricao", "").strip() or None
            icone_url = inter.text_values.get("icone_url", "").strip() or None
            if self.condecoracao_id:
                db["condecoracoes"][self.condecoracao_id]["nome"] = nome
                db["condecoracoes"][self.condecoracao_id]["mensagem"] = descricao  # Manter a mensagem definida manualmente
                db["condecoracoes"][self.condecoracao_id]["emoji"] = emoji
                db["condecoracoes"][self.condecoracao_id]["icone_url"] = icone_url
                msg = f"{check} Condecoracão '{nome}' atualizada com sucesso!"
            else:
                novo_id = GerarString()
                db["condecoracoes"][novo_id] = {
                    "nome": nome,
                    "mensagem": descricao,
                    "emoji": emoji,
                    "icone_url": icone_url,
                    "personalizada": True,
                    "tipo": "custom",
                    "condicao": {},
                    "criado_em": int(datetime.now().timestamp())
                }
                msg = f"{check} Condecoracão '{nome}' adicionada com sucesso!"
        SalvarDatabaseCondecoracao(db)
        if self.condecoracao_id and not self.is_default:
            embed, components = ObterPainelGerenciarCondecoracaoIndividual(inter, self.condecoracao_id)
        else:
            embed, components = ObterPainelListarCondecoracoes(inter)
        await inter.edit_original_response(embed=embed, components=components)
        await inter.followup.send(msg, ephemeral=True, delete_after=3)

# --- Painéis ---
def ObterPainelPrincipalCondecoracao(inter: disnake.MessageInteraction):
    db = ObterDatabaseCondecoracao()
    emojis = CONDECORATION_EMOJIS
    embed_color = _get_embed_color()
    habilitado_emoji = emojis["positive"] if db["habilitado"] else emojis["negative"]
    enviar_dm_emoji = emojis["positive"] if db["enviar_dm"] else emojis["negative"]
    anunciar_emoji = emojis["positive"] if db["anunciar"] else emojis["negative"]
    canal_anuncios_info = f"<#{db['canal_anuncios']}>" if db["canal_anuncios"] else f"{emojis['negative']} Não definido"
    embed = disnake.Embed(
        title=f"Gerenciar Condecoracoes",
        description=f"""
Gerencie as configurações gerais do sistema de condecoracoes aqui.
Status Geral: {habilitado_emoji} {'Habilitado' if db['habilitado'] else 'Desabilitado'}
Enviar DM: {enviar_dm_emoji} {'Sim' if db['enviar_dm'] else 'Não'}
Anunciar em Canal: {anunciar_emoji} {'Sim' if db['anunciar'] else 'Não'}
Canal de Anúncios: {canal_anuncios_info}
Total de Condecoracoes: `{len(db["condecoracoes"])}`
""",
        color=embed_color,
        timestamp=datetime.now()
    )
    embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon)
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1328079619026321563/1362201918658842874/0cb46b4b0e7ffcef2c33a922b215d228.jpg?ex=680231a5&is=6800e025&hm=3ae126a7e289f424d79ce141dc47527c1d3d51bec8dcdc33b5533c16b444c905&")
    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(
                style=disnake.ButtonStyle.green if db["habilitado"] else disnake.ButtonStyle.red,
                label="Ativar/Desativar Sistema",
                emoji=reload,
                custom_id="ToggleCondecoracaoHabilitado"
            ),
            disnake.ui.Button(
                style=disnake.ButtonStyle.green if db["enviar_dm"] else disnake.ButtonStyle.red,
                label="Enviar DM ao Usuário",
                emoji=mensagem,
                custom_id="ToggleCondecoracaoDM"
            ),
            disnake.ui.Button(
                style=disnake.ButtonStyle.green if db["anunciar"] else disnake.ButtonStyle.red,
                label="Anunciar Condecorações",
                emoji=sino,
                custom_id="ToggleCondecoracaoAnunciar"
            ),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                style=disnake.ButtonStyle.blurple,
                label="Selecionar Canal de Anúncios",
                emoji=canalText,
                custom_id="SelecionarCanalAnuncios"
            ),
            disnake.ui.Button(
                style=disnake.ButtonStyle.blurple,
                label="Listar/Gerenciar Condecoracoes",
                emoji=config3,
                custom_id="ListarCondecoracoes"
            ),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                style=disnake.ButtonStyle.grey,
                label="Voltar",
                emoji=voltar,
                custom_id="GerenciarPainelVendas"
            ),
        )
    ]
    return embed, components

def ObterPainelListarCondecoracoes(inter: disnake.MessageInteraction):
    db = ObterDatabaseCondecoracao()
    condecoracoes = db["condecoracoes"]
    embed_color = _get_embed_color()
    emojis = CONDECORATION_EMOJIS
    options = []
    sorted_condecoracoes = sorted(condecoracoes.items(), key=lambda item: (item[1].get("personalizada", False), item[1]["nome"]))
    for condec_id, data in sorted_condecoracoes:
        condec_emoji = data.get("emoji", "⭐")
        condec_nome = data.get("nome", "Condecoracão sem nome")
        is_personalizada = data.get("personalizada", False)
        description_text = f"Tipo: {'Personalizada' if is_personalizada else 'Padrão'} | ID: {condec_id}"
        options.append(
            disnake.SelectOption(
                label=f"{condec_nome}",
                description=description_text,
                value=condec_id,
                emoji=condec_emoji
            )
        )
    if not options:
        options.append(
            disnake.SelectOption(
                label="Nenhuma condecoracão disponível",
                value="nenhuma",
                description="Não há condecoracoes cadastradas ou personalizadas."
            )
        )
    select = disnake.ui.StringSelect(
        placeholder=f"[{len(condecoracoes)}] Clique aqui para selecionar uma condecoracao",
        custom_id="SelecionarCondecoracaoDropdown",
        options=options,
        disabled=len(options) == 1 and options[0].value == "nenhuma"
    )
    components = [
        select,
        disnake.ui.Button(label="Voltar", emoji=voltar, custom_id="GerenciarCondecoracoes"),
    ]
    embed = disnake.Embed(
        title=f"{emojis['award']} Listar Condecoracoes",
        description="Selecione uma condecoracao para gerenciá-la ou adicione uma nova personalizada.",
        color=embed_color
    )
    return embed, components

def ObterPainelGerenciarCondecoracaoIndividual(inter: disnake.MessageInteraction, condecoracao_id: str):
    db = ObterDatabaseCondecoracao()
    condecoracao = db["condecoracoes"].get(condecoracao_id)
    if not condecoracao:
        return disnake.Embed(description=f"{negativo} Condecoracão não encontrada."), []
    embed_color = _get_embed_color()
    emojis = CONDECORATION_EMOJIS
    is_personalizada = condecoracao.get("personalizada", False)
    if is_personalizada:
        embed = disnake.Embed(
            title=f"{condecoracao.get('emoji', '⭐')} Gerenciando Condecoracão: {condecoracao['nome']}",
            description=f"""
Nome: `{condecoracao["nome"]}` Emoji: {condecoracao.get("emoji", f"{emojis['negative']} `Não definido`")}
Descrição: {condecoracao.get("mensagem", f"{emojis['negative']} `Não informada`")}
Ícone URL: {f"[Link]({condecoracao['icone_url']})" if condecoracao.get('icone_url') else f"{emojis['negative']} `Não definido`"}
Tipo: `{condecoracao.get("tipo", "Personalizada")}` ID: `{condecoracao_id}` Criado em: <t:{condecoracao.get("criado_em", 0)}:f>
""",
            color=embed_color,
            timestamp=datetime.now()
        )
        if condecoracao.get("icone_url"):
            embed.set_thumbnail(url=condecoracao["icone_url"])
    else:
        embed = disnake.Embed(
            title=f"{condecoracao.get('emoji', '⭐')} Gerenciando Condecoracão Padrão: {condecoracao['nome']}",
            description=f"""
Nome: `{condecoracao["nome"]}` Emoji: {condecoracao.get("emoji", f"{emojis['negative']} `Não definido`")}
Mensagem Padrão: {condecoracao.get("mensagem", f"{emojis['negative']} `Não informada`")}
Tipo: `{condecoracao.get('tipo', 'N/A')}` ID: `{condecoracao_id}`
""",
            color=embed_color,
            timestamp=datetime.now()
        )
    if inter.guild and inter.guild.icon:
        embed.set_thumbnail(url=inter.guild.icon.url)
        embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon)
    components_row1 = disnake.ui.ActionRow()
    components_row2 = disnake.ui.ActionRow()
    components_row1.add_button(
        style=disnake.ButtonStyle.blurple,
        label="Editar",
        emoji=editar,
        custom_id=f"EditarCondecoracaoDetalhes_{condecoracao_id}"
    )
    if is_personalizada:
        components_row1.add_button(
            style=disnake.ButtonStyle.red,
            label="Remover Condecoracão",
            emoji=apagar,
            custom_id=f"RemoverCondecoracao_{condecoracao_id}"
        )
    components_row2.add_button(
        style=disnake.ButtonStyle.grey,
        label="Voltar",
        emoji=voltar,
        custom_id="ListarCondecoracoes"
    )
    return embed, [components_row1, components_row2]

# --- Cog Principal do Sistema de Condecoracoes ---
class CondecoracaoCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        ObterDatabaseCondecoracao()

    async def _generate_personalized_message(self, character_name: str, condecoracao_data: dict, user_mention: str) -> str:
        """
        Gera uma mensagem personalizada para a condecoracao usando a API da Groq,
        baseando-se no personagem escolhido e no prompt específico da condecoracao.
        Tenta com múltiplas chaves em caso de erro.
        """
        condecoracao_id = next((id_ for id_, data in DEFAULT_CONDECORATIONS_DATA.items() if data['nome'] == condecoracao_data['nome']), None)
        if not condecoracao_id:
            # Se não for uma condecoracao padrão, usa a mensagem manual
            return condecoracao_data.get('mensagem', f"Parabéns, {user_mention}! Você desbloqueou a condecoracão: **{condecoracao_data['nome']}**")
        base_prompt = PERSONAGENS_CONDECORACAO_PROMPTS.get(character_name, PERSONAGENS_CONDECORACAO_PROMPTS["nenhum"]).get(condecoracao_id)
        if not base_prompt:
            # Se não houver prompt específico para a condecoracao/personagem, usa a mensagem manual
            return condecoracao_data.get('mensagem', f"Parabéns, {user_mention}! Você desbloqueou a condecoracão: **{condecoracao_data['nome']}**")
        for _ in range(len(GROQ_API_KEYS)):  # Tenta com todas as chaves disponíveis
            client = get_groq_client()
            if not client:
                print("Nenhum cliente Groq disponível. Usando mensagem padrão.")
                break  # Sai do loop se não houver cliente Groq
            try:
                full_prompt = (
                    f"Você é um bot do Discord no papel do personagem '{character_name}'."
                    f" Sua personalidade deve ser fiel ao personagem."
                    f" Você precisa criar uma mensagem de parabéns para um usuário do Discord, {user_mention},"
                    f" que acabou de ganhar a condecoracão '{condecoracao_data['nome']}'."
                    f" A mensagem base para esta condecoracao (com a voz do personagem) é: '{base_prompt}'."
                    f" Use esta mensagem base e torne-a ainda mais envolvente e única, como se o próprio personagem estivesse falando."
                    f" Mantenha a mensagem concisa, com no máximo 2-3 frases, e use o emoji da condecoracao '{condecoracao_data.get('emoji', '⭐')}'."
                    f" Não adicione introduções ou encerramentos genéricos, apenas a mensagem principal de condecoracao."
                )
                chat_completion = await asyncio.to_thread(
                    client.chat.completions.create,
                    messages=[
                        {"role": "user", "content": full_prompt}
                    ],
                    model="llama3-8b-8192",  # Ou outro modelo da Groq de sua preferência
                    max_tokens=200  # Limita o tamanho da resposta para concisão
                )
                return chat_completion.choices[0].message.content
            except (RateLimitError, APIConnectionError) as e:
                print(f"Erro da API Groq (rate limit ou conexão) com a chave no índice {current_groq_key_index}: {e}. Tentando próxima chave...")
                rotate_groq_key()
                await asyncio.sleep(1)  # Pequeno atraso antes de tentar a próxima chave
            except Exception as e:
                print(f"Erro inesperado ao gerar mensagem personalizada via Groq: {e}. Usando mensagem padrão.")
                break  # Sai do loop em caso de erro não-tratável
        # Se todas as chaves falharem ou houver um erro não-tratável, retorna a mensagem padrão
        return condecoracao_data.get('mensagem', f"Parabéns, {user_mention}! Você desbloqueou a condecoracão: **{condecoracao_data['nome']}**")

    async def conceder_condecoracao(self, user_id: int, condecoracao_id: str, inter: disnake.Interaction = None):
        """
        Adiciona uma condecoracao ao usuário e notifica, se configurado.
        Esta é a função que as outras cogs (Carrinho, OnSugestao, OnEventGiveaway, Definicoes para feedback) devem chamar.
        """
        db = ObterDatabaseCondecoracao()
        if not db["habilitado"]:
            print(f"Sistema de condecoracoes desabilitado. Não concedendo {condecoracao_id} para {user_id}.")
            return False
        condecoracao_info = db["condecoracoes"].get(condecoracao_id)
        if not condecoracao_info:
            print(f"Condecoracão {condecoracao_id} não encontrada no DB.")
            return False
        if str(user_id) in db["usuarios_condecoracoes"] and condecoracao_id in db["usuarios_condecoracoes"][str(user_id)]:
            print(f"Usuário {user_id} já possui a condecoracão {condecoracao_id}.")
            return False
        AdicionarCondecoracaoUsuario(user_id, condecoracao_id)
        config_data = _load_config()
        personagem_atendente_key = config_data.get("personagem_atendente", "nenhum")
        personagem_info = PERSONAGENS.get(personagem_atendente_key, PERSONAGENS["nenhum"])
        personagem_nome = personagem_info["nome"]
        embed_color = _get_embed_color()
        user = await self.bot.fetch_user(user_id)
        user_mention = user.mention
        # Gerar mensagem personalizada
        personalized_message = await self._generate_personalized_message(personagem_nome.lower(), condecoracao_info, user_mention)
        # Notificação (DM e canal de anúncios)
        if db["enviar_dm"]:
            try:
                guild_name = inter.guild.name if inter and inter.guild else "Servidor"
                guild_icon_url = inter.guild.icon.url if inter and inter.guild and inter.guild.icon else None
                embed_dm = disnake.Embed(
                    title=f"{condecoracao_info.get('emoji', '⭐')} Você Conquistou uma Condecoracão!",
                    description=f"{personalized_message}",
                    color=embed_color,
                    timestamp=datetime.now()
                )
                if condecoracao_info.get("icone_url"):
                    embed_dm.set_thumbnail(url=condecoracao_info["icone_url"])
                else:
                    embed_dm.set_thumbnail(url=self.bot.user.avatar.url if self.bot.user.avatar else None)
                embed_dm.set_footer(text=guild_name, icon_url=guild_icon_url)
                await user.send(embed=embed_dm)
            except disnake.Forbidden:
                print(f"Não foi possível enviar DM para {user_id} sobre a condecoracão {condecoracao_id}: DMs bloqueadas.")
            except Exception as e:
                print(f"Erro ao enviar DM de condecoracão para {user_id}: {e}")
        if db["anunciar"] and db["canal_anuncios"]:
            try:
                canal_anuncios = self.bot.get_channel(db["canal_anuncios"])
                if canal_anuncios:
                    user_obj = self.bot.get_user(user_id)
                    if not user_obj: user_obj = await self.bot.fetch_user(user_id)
                    guild_name = inter.guild.name if inter and inter.guild else "Servidor"
                    guild_icon_url = inter.guild.icon.url if inter and inter.guild and inter.guild.icon else None
                    embed_anuncio = disnake.Embed(
                        title=f"Nova Condecoracão Conquistada!",
                        description=f"{user_obj.mention} acaba de desbloquear a condecoracão **{condecoracao_info['nome']}**!",
                        color=embed_color,
                        timestamp=datetime.now()
                    )
                    # A mensagem detalhada no anúncio pode ser a personalizada ou a padrão
                    embed_anuncio.add_field(name="Detalhes", value=f"> {personalized_message}", inline=False)
                    embed_anuncio.set_author(name=user_obj.display_name, icon_url=user_obj.avatar.url)
                    if condecoracao_info.get("icone_url"):
                        embed_anuncio.set_thumbnail(url=condecoracao_info["icone_url"])
                    else:
                        embed_anuncio.set_thumbnail(url=self.bot.user.avatar.url if self.bot.user.avatar else None)
                    embed_anuncio.set_footer(text=f"{guild_name} | ID da Condecoracão: {condecoracao_id}", icon_url=guild_icon_url)
                    await canal_anuncios.send(embed=embed_anuncio)
            except Exception as e:
                print(f"Erro ao anunciar condecoracão no canal: {e}")
        return True

    # Comando de slash para usuários verem condecoracoes
    @commands.slash_command(name="condecoracoes", description="Mostra as condecoracoes que você ou outro usuário conquistou.")
    async def ver_condecoracoes_slash(self, inter: disnake.ApplicationCommandInteraction, usuario: disnake.Member = None):
        await inter.response.defer(ephemeral=True)
        target_user = usuario or inter.author
        condecoracoes_ids = ObterCondecoracoesUsuario(target_user.id)
        if not condecoracoes_ids:
            return await inter.followup.send(f"{negativo} {target_user.mention} ainda não possui nenhuma condecoracão.", ephemeral=True)
        db_condec = ObterDatabaseCondecoracao()
        condecoracoes_info = []
        for condec_id in condecoracoes_ids:
            info = db_condec["condecoracoes"].get(condec_id)
            if info:
                condecoracoes_info.append(f"{info.get('emoji', '⭐')} **{info.get('nome', 'Desconhecido')}** - {info.get('mensagem', 'Sem descrição')}")
        embed_color = _get_embed_color()
        embed = disnake.Embed(
            title=f"Condecoracoes de {target_user.display_name}",
            description="\n".join(condecoracoes_info) if condecoracoes_info else "Nenhuma condecoracão encontrada (erro nos dados).",
            color=embed_color,
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url=target_user.avatar.url if target_user.avatar else None)
        embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon.url if inter.guild.icon else None)
        await inter.followup.send(embed=embed, ephemeral=True)

    # --- Listeners de Botões e Dropdowns (Painel de Gerenciamento) ---
    @commands.Cog.listener("on_button_click")
    async def CondecoracaoButtonListener(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        # PRIMEIRA VERIFICAÇÃO: Esta interação pertence ao sistema de condecoracoes?
        if not is_condecoracao_interaction(cid):
            return  # Não é nossa interação, ignora completamente
        db = ObterDatabaseCondecoracao()
        emojis = CONDECORATION_EMOJIS
        # --- Interações que ENVIA UMA NOVA RESPOSTA (modal ou select/message) ---
        if cid == "SelecionarCanalAnuncios":
            select = disnake.ui.ChannelSelect(
                placeholder="Selecione o canal para anúncios de condecoracoes",
                custom_id="SetarCanalAnunciosCondecoracao",
                channel_types=[ChannelType.text]
            )
            return await inter.response.send_message(components=[select], ephemeral=True)
        elif cid == "AdicionarCondecoracao":
            return await inter.response.send_modal(EditarCondecoracaoModal(is_default=False))
        elif cid.startswith("EditarCondecoracaoDetalhes_"):
            condecoracao_id = cid.replace("EditarCondecoracaoDetalhes_", "")
            is_default = not db["condecoracoes"].get(condecoracao_id, {}).get("personalizada", False)
            return await inter.response.send_modal(EditarCondecoracaoModal(condecoracao_id=condecoracao_id, is_default=is_default))
        # --- Interações que EDITAM A MENSAGEM ORIGINAL ---
        await inter.response.defer()
        if cid == "ToggleCondecoracaoHabilitado":
            db["habilitado"] = not db["habilitado"]
            SalvarDatabaseCondecoracao(db)
            embed, components = ObterPainelPrincipalCondecoracao(inter)
            await inter.edit_original_response(embed=embed, components=components)
            await inter.followup.send(f"{emojis['positive']} Sistema de condecoracoes {'habilitado' if db['habilitado'] else 'desabilitado'} com sucesso.", ephemeral=True, delete_after=3)
        elif cid == "ToggleCondecoracaoDM":
            db["enviar_dm"] = not db["enviar_dm"]
            SalvarDatabaseCondecoracao(db)
            embed, components = ObterPainelPrincipalCondecoracao(inter)
            await inter.edit_original_response(embed=embed, components=components)
            await inter.followup.send(f"{emojis['positive']} Envio de DM {'habilitado' if db['enviar_dm'] else 'desabilitado'} com sucesso.", ephemeral=True, delete_after=3)
        elif cid == "ToggleCondecoracaoAnunciar":
            db["anunciar"] = not db["anunciar"]
            SalvarDatabaseCondecoracao(db)
            embed, components = ObterPainelPrincipalCondecoracao(inter)
            await inter.edit_original_response(embed=embed, components=components)
            await inter.followup.send(f"{emojis['positive']} Anúncio de condecoracoes {'habilitado' if db['anunciar'] else 'desabilitado'} com sucesso.", ephemeral=True, delete_after=3)
        elif cid == "ListarCondecoracoes":
            embed, components = ObterPainelListarCondecoracoes(inter)
            await inter.edit_original_response(embed=embed, components=components)
        elif cid == "GerenciarCondecoracoes":
            embed, components = ObterPainelPrincipalCondecoracao(inter)
            await inter.edit_original_response(embed=embed, components=components)
        elif cid.startswith("RemoverCondecoracao_"):
            await inter.edit_original_response(content=f"{carregarAnimado} Processando...", embed=None, components=None)
            condecoracao_id = cid.replace("RemoverCondecoracao_", "")
            condecoracao_data = db["condecoracoes"].get(condecoracao_id, {})
            if not condecoracao_data.get("personalizada", False):
                await inter.followup.send(f"{emojis['negative']} Você não pode remover condecoracoes padrão do sistema.", ephemeral=True, delete_after=5)
                embed, components = ObterPainelListarCondecoracoes(inter)
                return await inter.edit_original_response(embed=embed, components=components)
            condecoracao_nome = condecoracao_data.get("nome", "Condecoracão Desconhecida")
            if condecoracao_id in db["condecoracoes"]:
                del db["condecoracoes"][condecoracao_id]
                for user_id_str in list(db["usuarios_condecoracoes"].keys()):
                    if condecoracao_id in db["usuarios_condecoracoes"][user_id_str]:
                        db["usuarios_condecoracoes"][user_id_str].remove(condecoracao_id)
                        if not db["usuarios_condecoracoes"][user_id_str]:
                            del db["usuarios_condecoracoes"][user_id_str]
                SalvarDatabaseCondecoracao(db)
                await inter.followup.send(f"{emojis['positive']} Condecoracão '{condecoracao_nome}' removida com sucesso de todos os usuários e do sistema.", ephemeral=True, delete_after=3)
            else:
                await inter.followup.send(f"{emojis['negative']} Condecoracão não encontrada.", ephemeral=True, delete_after=3)
            embed, components = ObterPainelListarCondecoracoes(inter)
            await inter.edit_original_response(embed=embed, components=components)

    @commands.Cog.listener("on_dropdown")
    async def CondecoracaoDropdownListener(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        # PRIMEIRA VERIFICAÇÃO: Esta interação pertence ao sistema de condecoracoes?
        if not is_condecoracao_interaction(cid):
            return  # Não é nossa interação, ignora completamente
        # SEGUNDA VERIFICAÇÃO: O usuário tem permissão?
        if not verificar_permissao(inter.user.id):
            return await inter.response.send_message(f"{negativo} Faltam permissões para gerenciar condecoracoes.", ephemeral=True)
        db = ObterDatabaseCondecoracao()
        emojis = CONDECORATION_EMOJIS
        # Para dropdowns sempre deferimos primeiro
        await inter.response.defer()
        if cid == "SetarCanalAnunciosCondecoracao":
            channel_id = inter.values[0]
            db["canal_anuncios"] = int(channel_id)
            SalvarDatabaseCondecoracao(db)
            embed, components = ObterPainelPrincipalCondecoracao(inter)
            await inter.edit_original_response(embed=embed, components=components)
            await inter.followup.send(f"{emojis['positive']} Canal de anúncios definido para <#{channel_id}> com sucesso.", ephemeral=True, delete_after=3)
        elif cid == "SelecionarCondecoracaoDropdown":
            if inter.values[0] == "nenhuma":
                return
            condecoracao_id = inter.values[0]
            embed, components = ObterPainelGerenciarCondecoracaoIndividual(inter, condecoracao_id)
            await inter.edit_original_response(embed=embed, components=components)

def setup(bot: commands.Bot):
    bot.add_cog(CondecoracaoCommand(bot))
