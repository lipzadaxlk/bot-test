import disnake
from disnake.ext import commands
import json
import os
import asyncio
from datetime import datetime
import sys

from Events.OnBotStart import *
# REMOVIDO: from Events.AcoesAutomaticas import executar_acoes
from Events.CreateEmojis import initialize_emojis


# =====================================================================================
# Função para carregar o prefixo dinamicamente do config.json
# =====================================================================================
def obter_prefixo(bot, message):
    with open("config.json", 'r') as f:
        config = json.load(f)
    
    # Permite que o bot responda ao prefixo do config E quando for mencionado
    prefixo = config.get('prefix', '!') # Usa '!' como padrão se não houver prefixo no config
    return commands.when_mentioned_or(prefixo)(bot, message)
# =====================================================================================

intents = disnake.Intents.default()
intents.message_content = True # <-- LINHA ESSENCIAL
intents.members = True # Também é bom ter esta

# Garantir que exista um event loop (corrige: "There is no current event loop in thread 'MainThread'.")
try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

# Carregar configurações
with open("config.json") as file:
    config = json.load(file)
    token = config["token"]
    owner = config["owner"]
    server_id = config.get("server")

# =====================================================================================
# A inicialização do Bot agora usa a função obter_prefixo
# Registra comandos apenas no servidor especificado se a chave "server" existir
# =====================================================================================
if server_id:
    # Se houver um server_id configurado, registra apenas naquele servidor
    bot = commands.Bot(command_prefix=obter_prefixo, intents=disnake.Intents.all(), test_guilds=[int(server_id)])
    print(f"✓ Comandos serão registrados apenas no servidor ID: {server_id}")
else:
    # Se não houver server_id, registra globalmente em todos os servidores
    bot = commands.Bot(command_prefix=obter_prefixo, intents=disnake.Intents.all())
    print("✓ Comandos serão registrados globalmente em todos os servidores")
# =====================================================================================

bot.emojis_ready = False
bot.fully_ready = False

@bot.event
async def on_ready():
    if bot.fully_ready:
        return
        
    os.system('cls') if os.name == "nt" else os.system("clear")
    print()
    # Adicionei uma variável banner de exemplo, caso não a tenha definida
    try:
        banner
    except NameError:
        banner = "--- Bot Banner ---"
    print(banner)
    print()
    print(f"    Conectado em {bot.user.name} | {bot.user.id}")
    print(f"    Servidores: {len(bot.guilds)}")
    print(f"    Latência: {round(bot.latency * 1000)}ms")
    print()
    print("    ⏳ Aguardando carregamento de emojis...")
    
    if len(bot.guilds) > 10:
        print("\n!!! ATENÇÃO: Bot detectado em mais de 10 servidores.")
        await bot.close()
        return

    if len(bot.guilds) == 1 and not server_id:
         print(f"    AVISO: O bot está em apenas 1 servidor, mas nenhum servidor principal foi definido. Use /panel para definir.")


    # Inicializar emojis primeiro
    await initialize_emojis(bot)
    
    # Só continua se os emojis estiverem prontos
    if not bot.emojis_ready:
        print("    ❌ Falha no carregamento de emojis. Bot não será iniciado.")
        return
    
    print("    ✅ Todos os emojis carregados com sucesso!")

    # Inicia a rotação de status
    bot.loop.create_task(rotacionar_status(bot))

    # Altera a bio/descrição do bot usando a função de OnBotStart
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, alterar_descricao_bot, bot)
    
    await startBotlogs(bot)
    # REMOVIDO: bot.loop.create_task(executar_acoes(bot))
    
    bot.fully_ready = True
    print("    🎉 Bot totalmente pronto para uso!")

# Middleware para verificar se o bot está pronto
@bot.event
async def on_slash_command(inter):
    if not bot.fully_ready:
        if not inter.response.is_done():
            await inter.response.send_message("🔄 O bot ainda está inicializando. Aguarde alguns instantes...", ephemeral=True)
        return

@bot.event
async def on_message(message: disnake.Message):
    # Permite que os comandos de prefixo sejam processados
    if message.author.bot or not bot.fully_ready:
        return
    await bot.process_commands(message)

@bot.event
async def on_message_command(inter):
    if not bot.fully_ready:
        return await inter.response.send_message(
            "🔄 O bot ainda está inicializando. Aguarde alguns instantes...", 
            ephemeral=True
        )

@bot.event
async def on_user_command(inter):
    if not bot.fully_ready:
        return await inter.response.send_message(
            "🔄 O bot ainda está inicializando. Aguarde alguns instantes...", 
            ephemeral=True
        )

# =====================================================================================
# NOVA FUNÇÃO PARA CARREGAR COGS AUTOMATICAMENTE
# Esta função substitui a lista manual de cogs.
# =====================================================================================
def carregar_cogs_automaticamente(bot):
    """
    Escaneia as pastas de cogs, converte os caminhos dos arquivos para o formato
    de importação do Python e carrega cada extensão encontrada.
    """
    print("\n--- Carregando extensões dinamicamente ---")
    # Defina as pastas onde suas cogs estão localizadas
    pastas_cogs = ['Commands', 'Events', 'Functions']
    cogs_carregadas = 0
    cogs_falharam = 0

    for pasta_raiz in pastas_cogs:
        # Verifica se a pasta raiz existe para evitar erros
        if not os.path.isdir(pasta_raiz):
            print(f"AVISO: A pasta de cogs '{pasta_raiz}' não foi encontrada e será ignorada.")
            continue

        # os.walk percorre recursivamente a pasta e suas subpastas
        for dirpath, _, filenames in os.walk(pasta_raiz):
            for filename in filenames:
                # Carrega apenas arquivos .py e ignora arquivos de sistema do python
                if filename.endswith('.py') and not filename.startswith('__'):
                    # Converte o caminho do arquivo para o formato de importação do Python
                    # Ex: Commands/Admin/Painel.py -> Commands.Admin.Painel
                    caminho_cog = os.path.join(dirpath, filename)[:-3].replace(os.path.sep, '.')
                    
                    # Adiciona exclusão para arquivos que não são cogs
                    if caminho_cog == "Events.OnBotStart":
                        print(f"  [-] Ignorado: {caminho_cog} (Não é um cog)")
                        continue
                    
                    try:
                        bot.load_extension(caminho_cog)
                        print(f"  [+] Carregado: {caminho_cog}")
                        cogs_carregadas += 1
                    except Exception as e:
                        # Informa qual cog falhou e o motivo, mas continua o processo
                        print(f"  [!] FALHA ao carregar {caminho_cog}:\n      -> {e}")
                        cogs_falharam += 1
    
    print("\n--- Carregamento de extensões concluído ---")
    print(f"  Total de {cogs_carregadas} extensões carregadas com sucesso.")
    if cogs_falharam > 0:
        print(f"  Total de {cogs_falharam} extensões falharam ao carregar.")
    print("-" * 40 + "\n")
# =====================================================================================

# A lista manual de cogs foi removida e substituída pela chamada da função automática.
carregar_cogs_automaticamente(bot)

if __name__ == "__main__":
    if not token or not owner:
        print(f"Token ou Dono não encontrados em config.json.")
        exit()
    try:
        bot.run(token)
    except Exception as e:
        print(f"Ocorreu um erro crítico que impediu o bot de rodar: {e}")