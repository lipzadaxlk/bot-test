import json
import disnake
from disnake.ext import commands
from Functions.CarregarEmojis import *

class BotInfo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):

        if message.author.bot:
            return

        if self.bot.user not in message.mentions:
            return

        try:
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)

            versao = config.get("versao", "Beta 0.0.0.0")
            prefixo = config.get("prefix", "!")
            owner_id = config.get("owner")

        except (FileNotFoundError, json.JSONDecodeError):
            return

        # Load primary color from Configuracoes.json
        try:
            with open("Database/Configuracoes.json", "r") as f_config_db:
                config_db = json.load(f_config_db)
                primary_color_str = config_db.get("Cores", {}).get("Color_Primary", "16777215") # Default to white if not found
                primary_color = disnake.Colour(int(primary_color_str))
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            primary_color = disnake.Colour(16777215) # Fallback to white if file not found or invalid

        latency_ms = round(self.bot.latency * 1000)
        owner_mention = f"<@{owner_id}>" if owner_id else "Não definido"

        container1 = disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {Never}\n"
                f"-# Informações do bot"
            ),
            accent_colour=primary_color
        )

        # Usando emojis que assumimos estarem em CarregarEmojis.py
        # {dev} {local} {cargo} {attach} {raio}
        # Se esses emojis não existirem, o código pode quebrar.
        # Baseado nos arquivos, vou usar os que existem: dev, cargo, attach
        # Para local e raio, usarei placeholders ou emojis existentes como casa e sparkles
        info_content = (
            f"Informações do seu **Never Pro**\n"
            f"**{dev} Desenvolvido pela** **[Never Applications](https://neverapplications.com.br)**\n"
            f"**{local} Exclusivo para o servidor** {message.guild.name}\n"
            f"**{cargo} Menção:** {self.bot.user.mention}\n"
            f"**{bot} Versão:** `{versao}`\n"
            f"**{attach} Prefixo:** `{prefixo}`\n"
            f"**{user} Dono:** {owner_mention}\n"
            f"**{raio} Tempo de Resposta:** `{latency_ms}ms`"
        )

        container2 = disnake.ui.Container(
            disnake.ui.TextDisplay(content=info_content),
            accent_colour=primary_color
        )

        container3 = disnake.ui.Container(
            disnake.ui.TextDisplay(
                content="-# caso precise de suporte clique no botão abaixo"
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Dashboard",
                    style=disnake.ButtonStyle.link,
                    url="https://neverapplications.com.br/Dashboard"
                ),
                disnake.ui.Button(
                    label="Servidor de Suporte",
                    style=disnake.ButtonStyle.link,
                    url="https://discord.gg/neverapplications"
                )
            ),
            accent_colour=primary_color
        )
        
        await message.reply(
            components=[container1, container2, container3],
            fail_if_not_exists=False
        )
        
        # A linha abaixo foi removida para evitar processamento duplicado de comandos
        # await self.bot.process_commands(message)


def setup(bot: commands.Bot):
    bot.add_cog(BotInfo(bot))