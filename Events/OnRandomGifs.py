import disnake
import json
import random
import asyncio
from disnake.ext import commands, tasks
from datetime import datetime

class RandomGifsSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.is_running = False
        self.send_interval = 3.5  # segundos
        self.start_system()

    def start_system(self):
        if not self.is_running:
            self.is_running = True
            self.send_random_content.start()

    def stop_system(self):
        if self.is_running:
            self.is_running = False
            self.send_random_content.cancel()

    def load_config(self):
        try:
            with open('Database/Server/acoesauto.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def get_valid_channels(self, guild):
        config = self.load_config()
        if not config or not config.get("random_gifs", {}).get("sistema", False):
            return None

        random_gifs = config["random_gifs"]
        channels = {
            "icones": guild.get_channel(random_gifs.get("canal_icones", 0)),
            "gifs": guild.get_channel(random_gifs.get("canal_gifs", 0)),
            "banners": guild.get_channel(random_gifs.get("canal_banners", 0))
        }

        return {k: v for k, v in channels.items() if v is not None}

    def get_random_members(self, guild, count=5):
        members = [m for m in guild.members if not m.bot]
        return random.sample(members, min(count, len(members))) if members else []

    async def create_embeds(self, members, tema, content_type):
        hex_color = tema.lstrip("0x") if tema.startswith("0x") else "3498db"
        color = int(hex_color, 16)
        embeds = []

        for member in members:
            embed = disnake.Embed(color=color)
            
            if content_type == "icones":
                if member.display_avatar:
                    embed.set_author(name=f"Ícone de {member.display_name}", icon_url=member.display_avatar)
                    embed.set_image(url=member.display_avatar.with_size(256))
                    embeds.append(embed)
            
            elif content_type == "gifs":
                if member.display_avatar and member.display_avatar.is_animated():
                    embed.set_author(name=f"GIF de {member.display_name}", icon_url=member.display_avatar)
                    embed.set_image(url=member.display_avatar.with_format("gif").with_size(256))
                    embeds.append(embed)
            
            elif content_type == "banners":
                try:
                    user = await self.bot.fetch_user(member.id)
                    if user.banner:
                        embed.set_author(name=f"Banner de {user.display_name}", icon_url=user.display_avatar)
                        embed.set_image(url=user.banner.with_size(600))
                        embeds.append(embed)
                except Exception as e:
                    print(f"Erro ao buscar banner para o usuário {member.id}: {e}")
        
        return embeds

    @tasks.loop(seconds=3.5)
    async def send_random_content(self):
        config = self.load_config()
        if not config or not config.get("random_gifs", {}).get("sistema", False):
            return

        random_gifs = config["random_gifs"]
        tema = random_gifs.get("tema", "0x3498db")

        for guild in self.bot.guilds:
            channels = self.get_valid_channels(guild)
            if not channels:
                continue

            members = self.get_random_members(guild, 5)
            if not members:
                continue

            # Envia 5 ícones
            if channels.get("icones"):
                embeds = await self.create_embeds(members, tema, "icones")
                if embeds:
                    try:
                        await channels["icones"].send(embeds=embeds[:5])
                    except Exception as e:
                        print(f"Erro ao enviar ícones: {e}")

            # Envia 5 GIFs
            if channels.get("gifs"):
                embeds = await self.create_embeds(members, tema, "gifs")
                if embeds:
                    try:
                        await channels["gifs"].send(embeds=embeds[:5])
                    except Exception as e:
                        print(f"Erro ao enviar gifs: {e}")

            # Envia 5 banners
            if channels.get("banners"):
                embeds = await self.create_embeds(members, tema, "banners")
                if embeds:
                    try:
                        await channels["banners"].send(embeds=embeds[:5])
                    except Exception as e:
                        print(f"Erro ao enviar banners: {e}")

    @send_random_content.before_loop
    async def before_send_random_content(self):
        await self.bot.wait_until_ready()

def setup(bot: commands.Bot):
    bot.add_cog(RandomGifsSystem(bot))