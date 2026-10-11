import disnake
from disnake.ext import commands
from disnake.ext.commands import SlashCommandGroup
from disnake.ui import Container, TextDisplay
import json
import time
import asyncio
from datetime import timedelta

from Functions.CarregarEmojis import (
    check,
    cancelar,
    carregarAnimado,
    calendar,
    negativobranco, # Imported for ConfirmationView
)

# Class to create the View with the confirmation button
class ConfirmationView(disnake.ui.View):
    def __init__(self, bot, role, members_to_add, author, primary_color, timeout=120):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.role = role
        self.members_to_add = members_to_add
        self.author = author
        self.message = None
        self.primary_color = primary_color # Store primary color

    async def on_timeout(self):
        # Disable buttons if the interaction times out
        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(view=self)

    # Confirmation button
    @disnake.ui.button(label="Confirmar", style=disnake.ButtonStyle.success, custom_id="confirm_role_all")
    async def confirm_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        # Check if the clicker is the command author
        if inter.author.id != self.author.id:
            error_container = Container(TextDisplay(f"{negativobranco} Apenas o autor do comando pode confirmar esta ação."), accent_colour=self.primary_color)
            await inter.response.send_message(components=[error_container], ephemeral=True)
            return

        # Disable buttons to prevent multiple clicks
        for item in self.children:
            item.disabled = True
        await inter.response.edit_message(view=self)

        start_time = time.time() # Initialize start_time here

        # Start adding roles
        await inter.followup.send(f"{carregarAnimado} Iniciando a atribuição do cargo `{{self.role.name}}` para {len(self.members_to_add)} membros. Isso pode demorar um pouco...", ephemeral=True)

        added_count = 0
        failed_count = 0

        for member in self.members_to_add:
            try:
                await member.add_roles(self.role, reason=f"Comando adicionar cargo todos executado por {self.author.name}")
                added_count += 1
                await asyncio.sleep(1.5)  # 1.5 second interval
            except disnake.Forbidden:
                failed_count += 1
                print(f"Failed to add role for {member.name}: Insufficient permissions.")
            except Exception as e:
                failed_count += 1
                print(f"Failed to add role for {member.name}: {{e}}")
        
        # Final message using the requested format
        final_message_content = (
            f"{check} **Adicionar Cargo '{self.role.name}' a Todos**\n"
            f"**Membros processados:** {added_count + failed_count}\n"
            f"**Cargos adicionados com sucesso:** {added_count}\n"
            f"**Falhas:** {failed_count}\n"
            f"**Tempo de execução:** {str(timedelta(seconds=int(time.time() - start_time)))}"
        )