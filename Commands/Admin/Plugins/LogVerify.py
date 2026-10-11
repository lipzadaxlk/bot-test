import disnake
from disnake.ext import commands
import json
import aiohttp
from datetime import datetime
import asyncio
import os

class LogsVerificacao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.webhook_cache = {}
    
    def carregar_config_webhook(self):
        """Carrega a configuração de webhooks do arquivo JSON"""
        try:
            with open("Database/eCloud/webhook_config.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def salvar_config_webhook(self, config):
        """Salva a configuração de webhooks no arquivo JSON"""
        import os
        os.makedirs("Database/eCloud", exist_ok=True)
        with open("Database/eCloud/webhook_config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    
    async def criar_webhook_para_canal(self, canal_id):
        """Cria uma webhook para o canal especificado"""
        try:
            canal = self.bot.get_channel(int(canal_id))
            if not canal:
                return None
            
            webhook = await canal.create_webhook(name="eCloud Verificação")
            
            # Salva a webhook no arquivo de configuração
            config = self.carregar_config_webhook()
            config[str(canal_id)] = webhook.url
            self.salvar_config_webhook(config)
            
            return webhook.url
        except Exception as e:
            print(f"[LogsVerificacao] Erro ao criar webhook: {e}")
            return None
    
    async def obter_webhook_url(self, canal_id):
        """Obtém a URL da webhook para o canal"""
        config = self.carregar_config_webhook()
        return config.get(str(canal_id))
    
    async def remover_webhook(self, canal_id):
        """Remove a webhook do canal"""
        try:
            config = self.carregar_config_webhook()
            webhook_url = config.get(str(canal_id))
            
            if webhook_url:
                # Remove a webhook do Discord
                async with aiohttp.ClientSession() as session:
                    await session.delete(webhook_url)
                
                # Remove do arquivo de configuração
                del config[str(canal_id)]
                self.salvar_config_webhook(config)
                
        except Exception as e:
            print(f"[LogsVerificacao] Erro ao remover webhook: {e}")
    
    async def enviar_log_verificacao(self, user_data, guild_id, ip_address):
        """Envia log de verificação através da webhook"""
        try:
            # Carrega a configuração de canais
            from Functions.GerenciarCargosCanais import ObterCanais
            canais = ObterCanais()
            canal_verificados_id = canais.get("verificados")
            
            if not canal_verificados_id:
                return
            
            webhook_url = await self.obter_webhook_url(canal_verificados_id)
            if not webhook_url:
                return
            
            # Cria o embed
            embed = {
                "title": "🔒 Novo Mhhhhhhhhhgggembro Verificado",
                "color": 0x2ECC71,
                "thumbnail": {
                    "url": f"https://cdn.discordapp.com/avatars/{user_data['id']}/{user_data['avatar']}.png?size=128" if user_data.get('avatar') else "https://cdn.discordapp.com/embed/avatars/0.png"
                },
                "fields": [
                    {
                        "name": "📋 Membro",
                        "value": f"<@{user_data['id']}> (`{user_data['username']}#{user_data['discriminator']}`)",
                        "inline": False
                    },
                    {
                        "name": "🆔 ID do Usuário",
                        "value": f"`{user_data['id']}`",
                        "inline": True
                    },
                    {
                        "name": "🌐 Endereço IP",
                        "value": f"`{ip_address}`",
                        "inline": True
                    },
                    {
                        "name": "📧 Email",
                        "value": f"`{user_data.get('email', 'N/A')}`",
                        "inline": True
                    },
                    {
                        "name": "🏠 Servidor",
                        "value": f"ID: `{guild_id}`",
                        "inline": False
                    }
                ],
                "timestamp": datetime.now().isoformat(),
                "footer": {
                    "text": f"eCloud Verification System",
                    "icon_url": self.bot.user.avatar.url if self.bot.user.avatar else None
                }
            }
            
            # Envia através da webhook
            async with aiohttp.ClientSession() as session:
                payload = {
                    "embeds": [embed],
                    "username": "eCloud Verification",
                    "avatar_url": self.bot.user.avatar.url if self.bot.user.avatar else None
                }
                
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 204:
                        print(f"[LogsVerificacao] Log enviado com sucesso para {user_data['username']}")
                    else:
                        print(f"[LogsVerificacao] Erro ao enviar log: {response.status}")
                        
        except Exception as e:
            print(f"[LogsVerificacao] Erro ao enviar log de verificação: {e}")
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Listener executado quando o bot está pronto"""
        print("[LogsVerificacao] Sistema de logs de verificação carregado!")

def setup(bot):
    bot.add_cog(LogsVerificacao(bot))