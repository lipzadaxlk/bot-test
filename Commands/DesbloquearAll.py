import disnake
from disnake.ext import commands

class DesbloquearAllCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(
        name="desbloquearall",
        description="Desbloqueia todos os membros do servidor."
    )
    @commands.has_permissions(ban_members=True) # Assuming unblocking is related to managing bans
    async def desbloquearall(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.send_message("Este comando está em desenvolvimento. Unblocking all members logic will go here.", ephemeral=True)

def setup(bot: commands.Bot):
    bot.add_cog(DesbloquearAllCommand(bot))