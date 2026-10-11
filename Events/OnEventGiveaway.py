import disnake
from disnake.ext import commands, tasks
import json
import os
import asyncio
import random
from datetime import datetime, timezone
from typing import Dict, List, Optional
from Functions.CarregarEmojis import *

# Import da cog de Condecoracao
from Commands.Admin.Plugins.Condecoracao import ObterDatabaseCondecoracao, AdicionarCondecoracaoUsuario, DEFAULT_CONDECORATIONS_DATA

class GiveawayParticipation:
    def __init__(self, bot):
        self.bot = bot
        self.giveaways: Dict[str, dict] = {}
        self.load_giveaways()
        self.check_giveaways.start()
        # Referência à cog de condecorações
        self.condecoracao_cog = None
        self.bot.loop.create_task(self._load_condecoracao_cog())

    async def _load_condecoracao_cog(self):
        await self.bot.wait_until_ready()
        self.condecoracao_cog = self.bot.get_cog("CondecoracaoCommand")
        if not self.condecoracao_cog:
            print("AVISO: A cog 'CondecoracaoCommand' não foi carregada. Condecorações de sorteios podem não funcionar.")

    def load_giveaways(self):
        if os.path.exists("sorteios.json"):
            try:
                with open("sorteios.json", "r", encoding='utf-8') as f:
                    data = f.read()
                    self.giveaways = json.loads(data) if data else {}
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Erro ao carregar sorteios: {e}")
                self.giveaways = {}

    def save_giveaways(self):
        try:
            temp_file = "sorteios_temp.json"
            with open(temp_file, "w", encoding='utf-8') as f:
                json.dump(self.giveaways, f, indent=4, ensure_ascii=False)
            
            if os.path.exists(temp_file):
                os.replace(temp_file, "sorteios.json")
        except Exception as e:
            print(f"Erro ao salvar sorteios: {e}")

    def get_user_roles(self, member: disnake.Member) -> List[str]:
        return [str(role.id) for role in member.roles if role.name != "@everyone"]

    def check_required_roles(self, member: disnake.Member, required_roles: List[str]) -> bool:
        if not required_roles:
            return True
        
        user_roles = self.get_user_roles(member)
        return any(role_id in user_roles for role_id in required_roles)

    def check_banned_roles(self, member: disnake.Member, banned_roles: List[str]) -> bool:
        if not banned_roles:
            return False
        
        user_roles = self.get_user_roles(member)
        return any(role_id in user_roles for role_id in banned_roles)

    def calculate_extra_entries(self, member: disnake.Member, extra_entries: Dict[str, int]) -> int:
        if not extra_entries:
            return 0
        
        user_roles = self.get_user_roles(member)
        total_extra = 0
        
        for role_id, entries in extra_entries.items():
            if role_id in user_roles:
                total_extra += entries
        
        return total_extra

    def get_user_participation_count(self, giveaway_id: str, user_id: str) -> int:
        giveaway = self.giveaways.get(giveaway_id)
        if not giveaway:
            return 0
        
        participants = giveaway.get("participants", [])
        return participants.count(user_id)

    def is_user_participating(self, giveaway_id: str, user_id: str) -> bool:
        return self.get_user_participation_count(giveaway_id, user_id) > 0

    @tasks.loop(seconds=30)
    async def check_giveaways(self):
        current_time = datetime.now(timezone.utc).timestamp()
        
        for giveaway_id, giveaway in list(self.giveaways.items()):
            if giveaway.get("ended", False):
                continue
                
            end_time = giveaway.get("end_time")
            if end_time and current_time >= end_time:
                await self.end_giveaway(giveaway_id)

    @check_giveaways.before_loop
    async def before_check_giveaways(self):
        await self.bot.wait_until_ready()

    async def end_giveaway(self, giveaway_id: str):
        giveaway = self.giveaways.get(giveaway_id)
        if not giveaway or giveaway.get("ended", False):
            return

        try:
            giveaway["ended"] = True
            giveaway["ended_at"] = datetime.now(timezone.utc).timestamp()

            channel = self.bot.get_channel(int(giveaway["channel_id"]))
            if not channel:
                self.save_giveaways()
                return

            message = await channel.fetch_message(int(giveaway["message_id"]))
            if not message:
                self.save_giveaways()
                return

            participants = giveaway.get("participants", [])
            
            if not participants:
                await self.announce_no_winner(channel, message, giveaway)
                self.save_giveaways()
                return

            winner_id = random.choice(participants)
            giveaway["winner_id"] = winner_id

            await self.update_ended_giveaway_message(message, giveaway, winner_id)
            await self.announce_winner(channel, giveaway, winner_id)
            
            # --- LÓGICA DE CONDECORAÇÕES DE SORTEIOS AQUI ---
            if self.condecoracao_cog:
                await self.check_and_award_condecorations_giveaways(int(winner_id), None) # Passar None para 'inter'
            # --- FIM DA LÓGICA DE CONDECORAÇÕES DE SORTEIOS ---

            self.save_giveaways()

        except Exception as e:
            print(f"Erro ao finalizar sorteio {giveaway_id}: {e}")

    async def announce_winner(self, channel, giveaway, winner_id: str):
        is_fake = giveaway.get("is_fake", False)
        title = giveaway.get("title", "Sorteio")
        
        if is_fake:
            embed = disnake.Embed(
                title="🎉 Sorteio Finalizado (FAKE)",
                description=f"**{title}**\n\n🏆 **Ganhador:** <@{winner_id}>\n\n*⚠️ Este era um sorteio fake para teste!*",
                color=0xff6b6b
            )
        else:
            embed = disnake.Embed(
                title="🎉 Sorteio Finalizado!",
                description=f"**{title}**\n\n🏆 **Parabéns** <@{winner_id}>! **Você ganhou!**",
                color=0x00ff00
            )
            
        embed.set_footer(text="Sorteio finalizado automaticamente")
        await channel.send(f"<@{winner_id}> parabéns, você ganhou o sorteio !", embed=None)

    async def announce_no_winner(self, channel, message, giveaway):
        title = giveaway.get("title", "Sorteio")
        
        # O embed foi removido e substituído por 'content'
        content = f"**{title}**\n\n{negativo} **Nenhum participante!**\nO sorteio foi finalizado sem ganhador."
        
        view = disnake.ui.View()
        button = disnake.ui.Button(
            style=disnake.ButtonStyle.secondary,
            label="Sorteio Finalizado",
            disabled=True,
            emoji=check
        )
        view.add_item(button)
        
        original_embed = message.embeds[0]
        original_embed.color = 0x95a5a6
        original_embed.set_footer(text="#Sorteio finalizado\n> Sem participantes")
        
        await message.edit(embed=original_embed, view=view)
        await channel.send(content=content)

    async def update_ended_giveaway_message(self, message, giveaway, winner_id: str):
        try:
            embed = message.embeds[0]
            is_fake = giveaway.get("is_fake", False)
            embed.color = 0xff6b6b if is_fake else 0x00ff00
            
            embed.add_field(
                name="Ganhador",
                value=f"-# <@{winner_id}>",
                inline=True
            )
            

            view = disnake.ui.View()
            button = disnake.ui.Button(
                style=disnake.ButtonStyle.secondary,
                label="Sorteio Finalizado",
                disabled=True,
                emoji=check
            )
            view.add_item(button)
            
            await message.edit(embed=embed, view=view)
            
        except Exception as e:
            print(f"{negativo} Erro ao atualizar mensagem finalizada: {e}")

    async def handle_participation(self, inter: disnake.MessageInteraction, giveaway_id: str):
        self.load_giveaways()
        
        giveaway = self.giveaways.get(giveaway_id)
        if not giveaway:
            print(f"{negativo} Sorteio não encontrado. IDs disponíveis: {list(self.giveaways.keys())}")
            await inter.response.send_message(f"{negativo} Sorteio não encontrado!", ephemeral=True)
            return

        if giveaway.get("ended", False):
            await inter.response.send_message(f"{negativo} Este sorteio já terminou!", ephemeral=True)
            return

        user_id = str(inter.author.id)
        member = inter.author

        if self.is_user_participating(giveaway_id, user_id):
            await self.show_leave_confirmation(inter, giveaway_id)
            return

        required_roles = giveaway.get("required_roles", [])
        if not self.check_required_roles(member, required_roles):
            role_mentions = [f"<@&{role_id}>" for role_id in required_roles]
            await inter.response.send_message(
                f"{negativo} **Você precisa ter pelo menos um destes cargos:**\n{', '.join(role_mentions)}",
                ephemeral=True
            )
            return

        banned_roles = giveaway.get("banned_roles", [])
        if self.check_banned_roles(member, banned_roles):
            role_mentions = [f"<@&{role_id}>" for role_id in banned_roles]
            await inter.response.send_message(
                f"{negativo} **Você não pode participar por ter um destes cargos:**\n{', '.join(role_mentions)}",
                ephemeral=True
            )
            return

        await self.add_user_participation(inter, giveaway_id, user_id, member)

    async def add_user_participation(self, inter: disnake.MessageInteraction, giveaway_id: str, user_id: str, member: disnake.Member):
        giveaway = self.giveaways[giveaway_id]
        extra_entries_config = giveaway.get("extra_entries", {})
        extra_entries = self.calculate_extra_entries(member, extra_entries_config)
        total_entries = 1 + extra_entries
        
        if "participants" not in giveaway:
            giveaway["participants"] = []
        
        for _ in range(total_entries):
            giveaway["participants"].append(user_id)
        
        self.save_giveaways()
        await self.update_giveaway_embed(giveaway_id)
        
        response_text = f"{positivo} **Você entrou no sorteio!**\n**Suas entradas:** {total_entries}"
        
        if extra_entries > 0:
            extra_info = []
            user_roles = self.get_user_roles(member)
            for role_id, entries in extra_entries_config.items():
                if role_id in user_roles:
                    extra_info.append(f"<@&{role_id}>: +{entries}")
            
            response_text += f"\n**Entradas extras:** {', '.join(extra_info)}"
        
        await inter.response.send_message(response_text, ephemeral=True)

    async def show_leave_confirmation(self, inter: disnake.MessageInteraction, giveaway_id: str):
        user_id = str(inter.author.id)
        participation_count = self.get_user_participation_count(giveaway_id, user_id)
        
        # O embed foi removido e substituído por 'content'
        content = (
            f"Você já está participando deste sorteio com **{participation_count} entradas**.\n\n"
            "Deseja realmente sair do sorteio?"
        )
        
        confirm_btn = disnake.ui.Button(
            style=disnake.ButtonStyle.danger,
            label="Sim, sair",
            custom_id=f"leave_confirm_{giveaway_id}",
            emoji=f"{positivo}"
        )
        
        cancel_btn = disnake.ui.Button(
            style=disnake.ButtonStyle.secondary,
            label="Cancelar",
            custom_id=f"leave_cancel_{giveaway_id}",
            emoji=f"{negativo}"
        )
        
        await inter.response.send_message(
            content=content,
            components=[disnake.ui.ActionRow(confirm_btn, cancel_btn)],
            ephemeral=True
        )

    async def remove_user_participation(self, inter: disnake.MessageInteraction, giveaway_id: str):
        giveaway = self.giveaways.get(giveaway_id)
        if not giveaway:
            await inter.response.send_message(f"{negativo} Sorteio não encontrado!", ephemeral=True)
            return

        user_id = str(inter.author.id)
        participants = giveaway.get("participants", [])
        
        removed_count = 0
        while user_id in participants:
            participants.remove(user_id)
            removed_count += 1
        
        giveaway["participants"] = participants
        self.save_giveaways()
        await self.update_giveaway_embed(giveaway_id)
        
        await inter.response.send_message(
            f"{positivo} **Você saiu do sorteio!**\n**Entradas removidas:** {removed_count}",
            ephemeral=True
        )

    async def update_giveaway_embed(self, giveaway_id: str):
        giveaway = self.giveaways.get(giveaway_id)
        if not giveaway or not giveaway.get("message_id"):
            return

        try:
            channel = self.bot.get_channel(int(giveaway["channel_id"]))
            if not channel:
                return

            message = await channel.fetch_message(int(giveaway["message_id"]))
            if not message:
                return

            participants = giveaway.get("participants", [])
            unique_participants = len(set(participants))
            total_entries = len(participants)

            embed = message.embeds[0]
            
            for i, field in enumerate(embed.fields):
                if "Participantes" in field.name:
                    embed.set_field_at(
                        i,
                        name="Participantes",
                        value=f"-# {unique_participants}",
                        inline=True
                    )
                    break

            await message.edit(embed=embed)

        except Exception as e:
            print(f"Erro ao atualizar embed: {e}")

    # --- Funções de verificação e concessão de condecorações de Sorteios ---
    async def check_and_award_condecorations_giveaways(self, winner_user_id: int, inter: Optional[disnake.Interaction] = None):
        if not self.condecoracao_cog: return

        # Obter histórico de sorteios ganhos do usuário (simulando, se não houver um arquivo dedicado)
        # Para um sistema mais robusto, você precisaria de um DB de usuários para isso.
        # Aqui, vamos pegar as condecorações já concedidas para ter uma ideia do histórico.
        condecoracoes_ganhas_usuario = self.condecoracao_cog.ObterCondecoracoesUsuario(winner_user_id)
        
        # Condecorações de SORTEIOS
        for condec_id, condec_data in DEFAULT_CONDECORATIONS_DATA.items():
            if condec_data["tipo"] != "sorteios": continue
            
            condicao = condec_data["condicao"]
            met_condition = False

            if condicao["tipo"] == "total_sorteios_ganhos":
                # Esta lógica é um pouco complexa sem um registro de sorteios ganhos explicitamente.
                # Para simplificar e evitar mexer em "sorteios.json" de forma não invasiva,
                # vamos simular o "total_sorteios_ganhos" contando as condecorações de sorteio já concedidas.
                # ISSO PODE NÃO SER 100% PRECISO SE HOUVER MUITAS CONDECORAÇÕES DE SORTEIO.
                # A forma ideal seria ter um campo "giveaways_won_count" no DB do usuário.
                
                # Conta quantas condecorações de sorteio o usuário já possui
                # e adiciona +1 para o sorteio atual que ele acabou de ganhar
                current_giveaway_condec_count = len([c for c in condecoracoes_ganhas_usuario if DEFAULT_CONDECORATIONS_DATA.get(c, {}).get("tipo") == "sorteios"]) + 1

                if current_giveaway_condec_count >= condicao["valor"]:
                    met_condition = True
            
            if met_condition:
                await self.condecoracao_cog.conceder_condecoracao(winner_user_id, condec_id, inter)


class GiveawayParticipationCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.participation_system = GiveawayParticipation(bot)

    @commands.Cog.listener()
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if not inter.component.custom_id:
            return

        custom_id = inter.component.custom_id

        try:
            if custom_id.startswith("participate_"):
                giveaway_id = custom_id.split("_")[1]
                await self.participation_system.handle_participation(inter, giveaway_id)

            elif custom_id.startswith("leave_confirm_"):
                giveaway_id = custom_id.split("_")[2]
                await self.participation_system.remove_user_participation(inter, giveaway_id)

            elif custom_id.startswith("leave_cancel_"):
                await inter.response.send_message(f"{negativo} Ação cancelada!", ephemeral=True)

        except Exception as e:
            print(f"Erro na participação: {e}")
            if not inter.response.is_done():
                await inter.response.send_message(f"{negativo} Erro ao processar participação!", ephemeral=True)

    def cog_unload(self):
        self.participation_system.check_giveaways.cancel()


def setup(bot):
    bot.add_cog(GiveawayParticipationCommands(bot))