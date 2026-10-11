import disnake
import json
import logging
from disnake.ext import commands
from datetime import datetime

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('BoasVindas')

class MemberEvents(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.main_server_id = self.load_main_server_id()
        logger.info(f'Sistema de Boas-Vindas carregado para o servidor principal: {self.main_server_id}')

    def load_main_server_id(self):
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                return int(config.get('server'))
        except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f'Erro ao carregar server_id do config.json: {e}')
            return None

    def load_config(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f'Arquivo {file_path} não encontrado!')
            return None
        except json.JSONDecodeError:
            logger.error(f'Erro ao decodificar {file_path}!')
            return None

    def get_welcome_channel(self, guild):
        if str(guild.id) != str(self.main_server_id):
            logger.info(f'Servidor {guild.id} não é o servidor principal, ignorando...')
            return None

        # 1. Tenta pegar do canais.json
        canais = self.load_config('Database/Server/canais.json')
        if canais and canais.get('boasvindas'):
            channel = guild.get_channel(int(canais['boasvindas']))
            if channel:
                logger.info(f'Canal de boas-vindas encontrado em canais.json: {channel.id}')
                return channel
            logger.warning(f'Canal ID {canais["boasvindas"]} não encontrado no servidor!')

        # 2. Tenta pegar do boasvindas.json (backup)
        boasvindas = self.load_config('Database/Server/boasvindas.json')
        if boasvindas and boasvindas['mensagens']['boas-vindas'].get('channel_id'):
            channel = guild.get_channel(int(boasvindas['mensagens']['boas-vindas']['channel_id']))
            if channel:
                logger.info(f'Canal de boas-vindas encontrado em boasvindas.json: {channel.id}')
                return channel
            logger.warning(f'Canal ID {boasvindas["mensagens"]["boas-vindas"]["channel_id"]} não encontrado no servidor!')

        logger.error('Nenhum canal de boas-vindas configurado ou encontrado!')
        return None

    async def assign_auto_role(self, member):
        if str(member.guild.id) != str(self.main_server_id):
            return False

        try:
            cargos = self.load_config('Database/Server/cargos.json')
            boasvindas = self.load_config('Database/Server/boasvindas.json')
            
            if (boasvindas and boasvindas['funcoes']['autoRole'].get('membro', False) and 
                cargos and cargos.get('membro')):
                
                role = member.guild.get_role(int(cargos['membro']))
                if role and role.is_assignable():
                    await member.add_roles(role)
                    logger.info(f'Cargo {role.name} atribuído a {member.display_name}')
                    return True
        except Exception as e:
            logger.error(f'Erro ao atribuir auto-role: {e}')
        return False

    @commands.Cog.listener()
    async def on_member_join(self, member: disnake.Member):
        if member.bot:
            return

        logger.info(f'{member.display_name} entrou no servidor {member.guild.id}')

        # Verifica se é o servidor principal
        if str(member.guild.id) != str(self.main_server_id):
            logger.info('Não é o servidor principal, ignorando...')
            return

        # Sistema de auto-role
        await self.assign_auto_role(member)

        # Sistema de boas-vindas
        boasvindas = self.load_config('Database/Server/boasvindas.json')
        if not boasvindas or not boasvindas['mensagens']['boas-vindas'].get('enabled', False):
            logger.info('Sistema de boas-vindas desativado')
            return

        channel = self.get_welcome_channel(member.guild)
        if not channel:
            return

        config = boasvindas['mensagens']['boas-vindas']
        estilo = config.get('estiloMensagem', {})
        content = estilo.get('content', '')
        tempo_apagar = config.get('tempoApagar')

        # Processa placeholders
        if content:
            content = content.replace('{mencao}', member.mention)
            content = content.replace('{nome}', member.display_name)
            content = content.replace('{servidor}', member.guild.name)

        # Envia a mensagem
        try:
            if tempo_apagar and tempo_apagar > 0:
                msg = await channel.send(content, delete_after=tempo_apagar)
                logger.info(f'Mensagem de boas-vindas enviada (será apagada em {tempo_apagar}s): {msg.id}')
            else:
                msg = await channel.send(content)
                logger.info(f'Mensagem de boas-vindas enviada: {msg.id}')
        except disnake.Forbidden:
            logger.error('Sem permissão para enviar mensagem no canal!')
        except Exception as e:
            logger.error(f'Erro ao enviar mensagem: {e}')

def setup(bot: commands.Bot):
    bot.add_cog(MemberEvents(bot))