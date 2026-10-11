import disnake
from disnake.ext import commands
import asyncio
from datetime import timedelta

# Você pode manter suas funções de emoji ou remover se não for usar
from Functions.CarregarEmojis import *

# --- Mockup dos Emojis para o código funcionar de forma independente ---
#
# Classe para criar a View com o botão de confirmação
class ConfirmationView(disnake.ui.View):
    def __init__(self, bot, role, members_to_add, author, timeout=120):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.role = role
        self.members_to_add = members_to_add
        self.author = author
        self.message = None

    async def on_timeout(self):
        # Desabilita os botões se o tempo de interação acabar
        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(view=self)

    # Botão de confirmação
    @disnake.ui.button(label="Confirmar", style=disnake.ButtonStyle.success, custom_id="confirm_role_all")
    async def confirm_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        # Verifica se quem clicou foi o autor do comando
        if inter.author.id != self.author.id:
            await inter.response.send_message(f"{negativo} Apenas o autor do comando pode confirmar esta ação.", ephemeral=True)
            return

        # Desabilita os botões para evitar cliques múltiplos
        for item in self.children:
            item.disabled = True
        await inter.response.edit_message(view=self)

        # Inicia o processo de adicionar cargos
        await inter.followup.send(f"{carregarAnimado} Iniciando a atribuição do cargo `{self.role.name}` para {len(self.members_to_add)} membros. Isso pode demorar um pouco...", ephemeral=True)

        added_count = 0
        failed_count = 0

        for member in self.members_to_add:
            try:
                await member.add_roles(self.role, reason=f"Comando roleall executado por {self.author.name}")
                added_count += 1
                await asyncio.sleep(1.5)  # Intervalo de 1.5 segundos
            except disnake.Forbidden:
                failed_count += 1
                # Pode adicionar um log aqui se quiser saber quem falhou
                print(f"Falha ao adicionar cargo para {member.name}: Permissões insuficientes.")
            except Exception as e:
                failed_count += 1
                print(f"Falha ao adicionar cargo para {member.name}: {e}")
        
        # Mensagem final
        await inter.followup.send(f"{positivo} Operação concluída!\n`{added_count}` membros receberam o cargo `{self.role.name}`.\n`{failed_count}` falhas.", ephemeral=True)


    # Botão de cancelamento
    @disnake.ui.button(label="Cancelar", style=disnake.ButtonStyle.danger, custom_id="cancel_role_all")
    async def cancel_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
         # Verifica se quem clicou foi o autor do comando
        if inter.author.id != self.author.id:
            await inter.response.send_message(f"{negativo} Apenas o autor do comando pode cancelar esta ação.", ephemeral=True)
            return
        
        # Desabilita os botões
        for item in self.children:
            item.disabled = True
        
        await inter.response.edit_message(content=f"{negativo} Operação cancelada pelo usuário.", embed=None, view=self)


class RoleAllCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(description="Adiciona um cargo a todos os membros que ainda não o possuem.")
    @commands.has_permissions(manage_roles=True)
    async def roleall(self, inter: disnake.ApplicationCommandInteraction, role: disnake.Role):
        await inter.response.defer(ephemeral=True)

        # Verifica se o bot tem permissão para gerenciar cargos
        if not inter.guild.me.guild_permissions.manage_roles:
            return await inter.followup.send(f"{negativo} Eu não tenho a permissão `Gerenciar Cargos` para executar este comando.", ephemeral=True)

        # Verifica se a posição do cargo do bot é maior que a do cargo a ser adicionado
        if inter.guild.me.top_role <= role:
            return await inter.followup.send(f"{negativo} Não posso adicionar o cargo `{role.name}` porque ele está em uma posição hierárquica igual ou superior à minha.", ephemeral=True)
        
        # Filtra os membros que não são bots e que ainda não têm o cargo
        members_to_add = [member for member in inter.guild.members if not member.bot and role not in member.roles]

        if not members_to_add:
            return await inter.followup.send(f"{positivo} Todos os membros elegíveis já possuem o cargo `{role.name}`.", ephemeral=True)

        # Calcula o tempo estimado
        total_seconds = len(members_to_add) * 1.5
        readable_time = str(timedelta(seconds=round(total_seconds)))

        # Cria a embed de confirmação
        embed = disnake.Embed(
            title="⚠️ Confirmação de Ação",
            description=f"Você está prestes a adicionar o cargo {role.mention} para **{len(members_to_add)}** membros.",
            color=disnake.Color.orange()
        )
        embed.add_field(name="Cargo a ser Adicionado", value=role.mention, inline=False)
        embed.add_field(name="Membros Afetados", value=f"`{len(members_to_add)}` membros", inline=True)
        embed.add_field(name="Tempo Estimado", value=f"`{readable_time}`", inline=True)
        embed.set_footer(text="Esta ação não pode ser desfeita em massa. Confirme para continuar.")

        # Cria a view e envia a mensagem de confirmação
        view = ConfirmationView(self.bot, role, members_to_add, inter.author)
        message = await inter.followup.send(embed=embed, view=view, ephemeral=True)
        view.message = message # Armazena a mensagem na view para poder editá-la no timeout

    @roleall.error
    async def roleall_error(self, inter: disnake.ApplicationCommandInteraction, error: Exception):
        if isinstance(error, commands.MissingPermissions):
            await inter.response.send_message(f"{negativo} Você não tem permissão para `Gerenciar Cargos`.", ephemeral=True, delete_after=15)
        else:
            await inter.response.send_message(f"{negativo} Ocorreu um erro inesperado: {error}", ephemeral=True, delete_after=15)


def setup(bot: commands.Bot):
    bot.add_cog(RoleAllCommand(bot))