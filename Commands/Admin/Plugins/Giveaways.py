import disnake
from disnake.ext import commands, tasks
import json
import random
import time
import re
import os
import asyncio
import aiohttp
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

# --- Configuração da API Key do Proxy (substitua pela sua chave) ---
PROXYCHECK_API_KEY = "h01716-528bu6-057204-875u02"  # Substitua pela sua chave real

# --- Funções e Emojis ---
from Functions.CarregarEmojis import *

try:
    from Functions.VerificarPerms import *
    from Functions.Config.Produto import ObterProduto, ObterHistoricosVendasDB
    from Functions.GerenciarCargosCanais import ObterCanais, ObterCargos
except ImportError:
    def ObterHistoricosVendasDB():
        return {}
    def ObterCargos():
        return {"cliente": None}

# --- Funções para carregar configurações dinamicamente ---
def obter_ecloud_config() -> dict:
    try:
        with open("Database/eCloud/auth_config.json", "r", encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def obter_main_config() -> dict:
    try:
        with open("config.json", "r", encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# --- Classe de Sistema do Sorteio (Lógica Interna) ---
class GiveawaySystem:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.giveaways: Dict[str, dict] = {}
        self.db_path = "Database/Giveaways/sorteios.json"
        self._ensure_db_path()
        self.load_giveaways()

    def _ensure_db_path(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def load_giveaways(self):
        try:
            with open(self.db_path, "r", encoding='utf-8') as f: 
                self.giveaways = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.giveaways = {}
            self.save_giveaways()

    def save_giveaways(self):
        try:
            with open(self.db_path, "w", encoding='utf-8') as f: 
                json.dump(self.giveaways, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar giveaways: {e}")

    def generate_id(self) -> str:
        while True:
            gid = str(random.randint(10000, 99999))
            if gid not in self.giveaways: 
                return gid

    def parse_duration(self, text: str) -> Optional[int]:
        if not text or not text.strip():
            return None
        matches = re.findall(r'(\d+)([smhd])', text.lower())
        if not matches: 
            return None
        total = 0
        for amount, unit in matches:
            multiplier = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
            total += int(amount) * multiplier.get(unit, 0)
        return total if total > 0 else None

    def get_user_ip(self, user_id: int, bot_id: int) -> Optional[str]:
        try:
            user_db_path = f"Database/Auth/{bot_id}_users.json"
            if not os.path.exists(user_db_path): 
                return None
            with open(user_db_path, "r", encoding='utf-8') as f:
                users_data = json.load(f)
            return users_data.get(str(user_id), {}).get("ip")
        except Exception:
            return None

    async def check_all_requirements(self, member: disnake.Member, giveaway_id: str) -> Tuple[bool, str]:
        giveaway = self.giveaways.get(giveaway_id)
        if not giveaway or not (reqs := giveaway.get("requirements")): 
            return True, ""
        
        try:
            # Requisitos de Perfil Discord
            if reqs.get("custom_name") and reqs["custom_name"] not in member.display_name: 
                return False, f"Seu nome de usuário precisa conter `{reqs['custom_name']}`."
            
            if reqs.get("custom_status"):
                custom_act = next((a for a in member.activities if isinstance(a, disnake.CustomActivity)), None)
                if not custom_act or reqs["custom_status"] not in str(custom_act.name): 
                    return False, f"Seu status personalizado precisa conter `{reqs['custom_status']}`."
            
            if (days := reqs.get("min_account_age_days", 0)) > 0:
                account_age = (datetime.now(timezone.utc) - member.created_at).days
                if account_age < days: 
                    return False, f"Sua conta precisa ter no mínimo {days} dias (atual: {account_age} dias)."
            
            # Requisitos de Cargos
            member_roles = {str(r.id) for r in member.roles}
            if (roles := reqs.get("required_roles")) and not any(r in member_roles for r in roles): 
                return False, "Você não possui um dos cargos necessários."
            
            if (roles := reqs.get("banned_roles")) and any(r in member_roles for r in roles): 
                return False, "Você possui um cargo que o impede de participar."
            
            try:
                all_cargos = ObterCargos()
                if reqs.get("client_role") and str(all_cargos.get("cliente")) not in member_roles: 
                    return False, "Você precisa ter o cargo de cliente."
            except Exception:
                pass
            
            # Requisitos de Voz
            if reqs.get("in_voice_call") and not member.voice: 
                return False, "Você precisa estar em um canal de voz."
            
            if member.voice:
                if reqs.get("is_unmuted") and member.voice.mute: 
                    return False, "Você precisa estar desmutado no servidor."
                if reqs.get("is_undeafened") and member.voice.deaf: 
                    return False, "Você precisa estar com o áudio ativado."
            
            # Requisitos eCloud
            if reqs.get("ecloud_verified"):
                ecloud_config = obter_ecloud_config()
                ecloud_auth = ecloud_config.get("authorization")
                if not ecloud_auth: 
                    return False, "A configuração do eCloud não foi encontrada."
                try:
                    headers = {"Authorization": ecloud_auth}
                    async with self.bot.session.get(f"https://ecloudxesteerdaocu.squareweb.app/api/verify/{member.id}?client_id={self.bot.user.id}", headers=headers) as resp:
                        if resp.status != 200 or not (await resp.json()).get("authenticated"): 
                            return False, "Você precisa ser verificado no sistema eCloud."
                except Exception: 
                    return False, "Não foi possível verificar seu status no eCloud."
            
            # Requisitos de Localização
            if any(k in reqs for k in ["country", "state", "city"]):
                ip = self.get_user_ip(member.id, self.bot.user.id)
                if not ip: 
                    return False, "Sua localização não pôde ser verificada."
                try:
                    async with self.bot.session.get(f"https://proxycheck.io/v2/{ip}?key={PROXYCHECK_API_KEY}&asn=1") as resp:
                        if resp.status != 200:
                            return False, "Erro ao verificar localização."
                        data = (await resp.json()).get(ip, {})
                        if (c := reqs.get("country")) and c.lower() != data.get("country", "").lower(): 
                            return False, f"Você precisa ser do país: {c}."
                        if (s := reqs.get("state")) and s.lower() != data.get("region", "").lower(): 
                            return False, f"Você precisa ser do estado: {s}."
                        if (t := reqs.get("city")) and t.lower() != data.get("city", "").lower(): 
                            return False, f"Você precisa ser da cidade: {t}."
                except Exception: 
                    return False, "Sua localização não pôde ser confirmada."

            # Requisitos de Loja
            if any(k in reqs for k in ["min_spent", "max_spent", "first_purchase_days", "last_purchase_days"]):
                try:
                    purchases = [v for v in ObterHistoricosVendasDB().values() if str(v.get("server", {}).get("usuario")) == str(member.id)]
                    total_spent = sum(float(p.get('info', {}).get('valorFinal', 0)) for p in purchases)
                    
                    if (min_s := reqs.get("min_spent", 0.0)) > 0 and total_spent < min_s: 
                        return False, f"Você precisa ter gasto no mínimo R$ {min_s:.2f} (atual: R$ {total_spent:.2f})."
                    
                    if (max_s := reqs.get("max_spent")) and total_spent > max_s: 
                        return False, f"Você não pode ter gasto mais de R$ {max_s:.2f} (atual: R$ {total_spent:.2f})."
                    
                    if purchases and any(k in reqs for k in ["first_purchase_days", "last_purchase_days"]):
                        purchase_dates = []
                        for p in purchases:
                            try:
                                timestamp = p.get("info", {}).get("timestamp", "")
                                if timestamp:
                                    purchase_dates.append(datetime.strptime(timestamp, "%d/%m/%Y %H:%M"))
                            except ValueError:
                                continue
                        
                        if purchase_dates:
                            purchase_dates.sort()
                            now = datetime.now()
                            
                            if reqs.get("first_purchase_days"):
                                days_since_first = (now - purchase_dates[0]).days
                                if days_since_first > reqs["first_purchase_days"]: 
                                    return False, f"Sua primeira compra deve ter sido nos últimos {reqs['first_purchase_days']} dias."
                            
                            if reqs.get("last_purchase_days"):
                                days_since_last = (now - purchase_dates[-1]).days
                                if days_since_last > reqs["last_purchase_days"]: 
                                    return False, f"Sua última compra deve ter sido nos últimos {reqs['last_purchase_days']} dias."
                except Exception:
                    pass
            
            # Requisitos de Convites
            if (min_invites := reqs.get("min_invites", 0)) > 0:
                try:
                    invites = await member.guild.invites()
                    user_invites = sum(invite.uses for invite in invites if invite.inviter and invite.inviter.id == member.id)
                    if user_invites < min_invites:
                        return False, f"Você precisa ter no mínimo {min_invites} convites (atual: {user_invites})."
                except Exception:
                    return False, "Não foi possível verificar seus convites."
            
        except Exception as e:
            print(f"Erro ao verificar requisitos: {e}")
            return False, "Erro interno ao verificar requisitos."
        
        return True, ""

# --- Classe Cog ---
class GiveawayCog(commands.Cog, name="Giveaways"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.system = GiveawaySystem(bot)
        
        # Configurar sessão aiohttp se não existir
        if not hasattr(bot, 'session'):
            loop = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            bot.session = aiohttp.ClientSession(loop=loop)
        
        # Iniciar tasks após o bot estar pronto
        self.bot.loop.create_task(self._start_tasks())

    async def _start_tasks(self):
        await self.bot.wait_until_ready()
        if not self.giveaway_ender.is_running():
            self.giveaway_ender.start()
        if not self.giveaway_monitor.is_running():
            self.giveaway_monitor.start()

    def cog_unload(self):
        if self.giveaway_ender.is_running():
            self.giveaway_ender.cancel()
        if self.giveaway_monitor.is_running():
            self.giveaway_monitor.cancel()
        if hasattr(self.bot, 'session'):
            asyncio.create_task(self.bot.session.close())

    @tasks.loop(seconds=10)
    async def giveaway_ender(self):
        try:
            now = int(time.time())
            for gid, g in list(self.system.giveaways.items()):
                if not g.get("ended") and g.get("end_timestamp") and now >= g.get("end_timestamp"):
                    await self.end_giveaway(gid)
        except Exception as e:
            print(f"Erro no giveaway_ender: {e}")

    @tasks.loop(minutes=10)
    async def giveaway_monitor(self):
        try:
            for giveaway_id, giveaway in list(self.system.giveaways.items()):
                if giveaway.get("monitor_enabled") and not giveaway.get("ended"):
                    participants_to_remove = []
                    guild = self.bot.get_guild(giveaway.get("guild_id"))
                    if not guild: 
                        continue
                    
                    current_participants = giveaway.get("participants", [])
                    for user_id in current_participants:
                        try:
                            member = guild.get_member(int(user_id))
                            if not member:
                                participants_to_remove.append(user_id)
                                continue
                            
                            can_participate, _ = await self.system.check_all_requirements(member, giveaway_id)
                            if not can_participate:
                                participants_to_remove.append(user_id)
                        except Exception:
                            participants_to_remove.append(user_id)
                    
                    if participants_to_remove:
                        for user_id in participants_to_remove:
                            if user_id in current_participants:
                                current_participants.remove(user_id)
                        self.system.save_giveaways()
                        await self.update_all_messages(giveaway_id)
        except Exception as e:
            print(f"Erro no giveaway_monitor: {e}")

    async def show_main_panel(self, inter: disnake.Interaction):
        try:
            active_giveaways = {gid: g for gid, g in self.system.giveaways.items() if not g.get("ended")}
            embed = disnake.Embed(
                title=f"Sistema de Sorteios",
                description="Use os botões abaixo para criar ou gerenciar os sorteios do servidor.",
                color=0x2B2D31
            ).set_footer(text=f"Total de Sorteios Ativos: {len(active_giveaways)}")
            
            view = disnake.ui.View(timeout=300)
            
            if active_giveaways:
                options = []
                for gid, g in list(active_giveaways.items())[:25]:  # Limite de 25 opções
                    name = g.get('name', f'Sorteio ID: {gid}')
                    if len(name) > 100:
                        name = name[:97] + "..."
                    options.append(
                        disnake.SelectOption(
                            label=name,
                            value=gid,
                            description=f"Participantes: {len(g.get('participants', []))}"
                        )
                    )
                
                select = disnake.ui.StringSelect(
                    placeholder="Selecione um sorteio para gerenciar",
                    custom_id="giveaway_manage_select",
                    options=options
                )
                view.add_item(select)
            
            create_button = disnake.ui.Button(
                label="Criar Novo Sorteio",
                style=disnake.ButtonStyle.green,
                custom_id="giveaway_create_new",
                emoji=mais2
            )

            voltar_button = disnake.ui.Button(
                label="Voltar",
                style=disnake.ButtonStyle.secondary,
                custom_id="PainelInicial",
                emoji=voltar
            )
            view.add_item(create_button)
            
            await inter.edit_original_response(embed=embed, view=view, content=None)
        except Exception as e:
            print(f"Erro em show_main_panel: {e}")
            await inter.edit_original_response(content=f"Erro ao exibir painel: {e}", embed=None, view=None)

    async def show_manage_panel(self, inter: disnake.Interaction, giveaway_id: str):
        try:
            giveaway = self.system.giveaways.get(giveaway_id)
            if not giveaway:
                return await inter.edit_original_response(content="❌ Sorteio não encontrado.", embed=None, view=None)
            
            task_config = giveaway.get("task_config", {})
            embed_config = giveaway.get("embed_config", {})
            
            embed = disnake.Embed(
                title=f"🎯 Gerenciando Sorteio: {giveaway.get('name', 'N/A')}",
                description=f"**Prêmio:** `{giveaway.get('prize', 'N/A')}`\n**Duração:** `{self.format_duration(task_config.get('duration_seconds', 0))}`\n**Vencedores:** `{task_config.get('winner_count', 1)}`\n**Participantes:** `{len(giveaway.get('participants', []))}`",
                color=int(embed_config.get("color", "2B2D31").replace("#", ""), 16)
            ).set_footer(text=f"ID: {giveaway_id}")
            
            is_active = bool(giveaway.get("sent_messages"))
            view = disnake.ui.View(timeout=300)
            
            # Primeira linha
            view.add_item(disnake.ui.Button(label="Embed", emoji=embedE, custom_id=f"giveaway_cfg_embed_{giveaway_id}"))
            view.add_item(disnake.ui.Button(label="Premiação", emoji=trofeu, custom_id=f"giveaway_cfg_prize_{giveaway_id}"))
            view.add_item(disnake.ui.Button(label="Task", emoji=config2, custom_id=f"giveaway_cfg_task_{giveaway_id}"))
            view.add_item(disnake.ui.Button(label="Requisitos", emoji=fields, custom_id=f"giveaway_cfg_reqs_{giveaway_id}"))
            
            # Segunda linha
            view.add_item(disnake.ui.Button(label="Vencedor (opcional)", emoji=dev, custom_id=f"giveaway_cfg_winner_{giveaway_id}"))
            
            monitor_label = "Desabilitar Monitor" if giveaway.get('monitor_enabled') else "Habilitar Monitor"
            monitor_style = disnake.ButtonStyle.red if giveaway.get('monitor_enabled') else disnake.ButtonStyle.green
            view.add_item(disnake.ui.Button(label=monitor_label, emoji=visible, style=monitor_style, custom_id=f"giveaway_toggle_monitor_{giveaway_id}"))
            
            view.add_item(disnake.ui.Button(label="Enviar", emoji=arrow, style=disnake.ButtonStyle.green, custom_id=f"giveaway_send_{giveaway_id}", disabled=is_active))
            view.add_item(disnake.ui.Button(label="Apagar", emoji=apagar, style=disnake.ButtonStyle.danger, custom_id=f"giveaway_delete_{giveaway_id}"))
            
            # Terceira linha
            view.add_item(disnake.ui.Button(label="Voltar", emoji=voltar, style=disnake.ButtonStyle.primary, custom_id=f"giveaway_back_to_main"))
            
            await inter.edit_original_response(embed=embed, view=view, content=None)
        except Exception as e:
            print(f"Erro em show_manage_panel: {e}")
            await inter.edit_original_response(content=f"Erro ao exibir painel de gerenciamento: {e}", embed=None, view=None)

    def format_duration(self, total_seconds):
        if not total_seconds: 
            return "Não definida"
        
        parts = []
        days, remainder = divmod(int(total_seconds), 86400)
        if days: 
            parts.append(f"{days}d")
        
        hours, remainder = divmod(remainder, 3600)
        if hours: 
            parts.append(f"{hours}h")
        
        minutes, seconds = divmod(remainder, 60)
        if minutes: 
            parts.append(f"{minutes}m")
        
        if seconds and not parts: 
            parts.append(f"{seconds}s")
        
        return " ".join(parts) or "0s"
        
    async def update_all_messages(self, giveaway_id: str):
        try:
            giveaway = self.system.giveaways.get(giveaway_id)
            if not giveaway or not giveaway.get("sent_messages"): 
                return
            
            content, embed, components = self.build_giveaway_message(giveaway_id)
            
            for channel_id, message_id in list(giveaway["sent_messages"].items()):
                try:
                    channel = self.bot.get_channel(int(channel_id))
                    if not channel:
                        channel = await self.bot.fetch_channel(int(channel_id))
                    
                    message = await channel.fetch_message(int(message_id))
                    await message.edit(content=content, embed=embed, components=components)
                    await asyncio.sleep(0.5)  # Rate limit
                except (disnake.NotFound, disnake.Forbidden, disnake.HTTPException) as e:
                    print(f"Erro ao atualizar mensagem {message_id}: {e}")
                    # Remove mensagem inválida
                    del giveaway["sent_messages"][channel_id]
                    self.system.save_giveaways()
                except Exception as e:
                    print(f"Erro inesperado ao atualizar mensagem: {e}")
        except Exception as e:
            print(f"Erro em update_all_messages: {e}")

    def build_giveaway_message(self, giveaway_id: str) -> Tuple[Optional[str], disnake.Embed, List[disnake.ui.ActionRow]]:
        try:
            giveaway = self.system.giveaways[giveaway_id]
            embed_config = giveaway.get("embed_config", {})
            task_config = giveaway.get("task_config", {})
            reqs = giveaway.get("requirements", {})
            
            color_hex = embed_config.get("color", "2B2D31").replace("#", "")
            try:
                color = int(color_hex, 16)
            except ValueError:
                color = 0x2B2D31
            
            title = embed_config.get('title') or giveaway.get('name') or "Sorteio"
            description = embed_config.get("description", "Clique no botão para participar!")
            
            embed = disnake.Embed(
                title=f"{presente} {title}",
                description=description,
                color=color
            )
            
            # Adicionar imagens se configuradas
            if embed_config.get("image_url"): 
                embed.set_image(url=embed_config["image_url"])
            if embed_config.get("thumbnail_url"): 
                embed.set_thumbnail(url=embed_config["thumbnail_url"])
            
            # Calcular tempo restante
            end_time = giveaway.get("end_timestamp")
            if end_time:
                time_str = f"<t:{end_time}:R> (<t:{end_time}:f>)"
            else:
                time_str = "`Não iniciado`"
            
            # Campos do embed
            embed.add_field(name="🎁 Prêmio", value=f"`{giveaway.get('prize', 'Não definido')}`", inline=True)
            embed.add_field(name="🏆 Vencedores", value=f"`{task_config.get('winner_count', 1)}`", inline=True)
            embed.add_field(name="👥 Participantes", value=f"**`{len(giveaway.get('participants', []))}`**", inline=True)
            embed.add_field(name="⏰ Termina em", value=time_str, inline=False)
            
            # Adicionar requisitos se existirem
            req_text = []
            req_descriptions = self.get_requirements_text(reqs)
            for key, description in req_descriptions.items():
                req_text.append(f"▫️ {description}")
            
            if req_text:
                embed.add_field(name="📋 Requisitos", value="\n".join(req_text[:10]), inline=False)  # Limite para não ultrapassar limite de caracteres
            
            embed.set_footer(text=f"ID: {giveaway_id}")
            
            # Botão de participar
            button = disnake.ui.Button(
                label="Participar",
                emoji="🎉",
                style=disnake.ButtonStyle.primary,
                custom_id=f"giveaway_participate_{giveaway_id}"
            )
            
            action_row = disnake.ui.ActionRow(button)
            
            return None, embed, [action_row]
        except Exception as e:
            print(f"Erro em build_giveaway_message: {e}")
            # Retornar mensagem de erro básica
            error_embed = disnake.Embed(
                title="❌ Erro no Sorteio",
                description="Houve um erro ao construir a mensagem do sorteio.",
                color=0xFF0000
            )
            return None, error_embed, []

    def get_requirements_text(self, reqs: dict) -> dict:
        texts = {}
        try:
            if reqs.get("required_roles"):
                role_mentions = []
                for role_id in reqs["required_roles"]:
                    role_mentions.append(f'<@&{role_id}>')
                texts["req_roles"] = f"**Cargos Obrigatórios:** {', '.join(role_mentions)}"
            
            if reqs.get("banned_roles"):
                role_mentions = []
                for role_id in reqs["banned_roles"]:
                    role_mentions.append(f'<@&{role_id}>')
                texts["ban_roles"] = f"**Cargos Proibidos:** {', '.join(role_mentions)}"
            
            if reqs.get("min_invites", 0) > 0:
                texts["invites"] = f"**Mínimo de {reqs['min_invites']} convites**"
            
            if reqs.get("min_account_age_days", 0) > 0:
                texts["account_age"] = f"**Conta com {reqs['min_account_age_days']} dias ou mais**"
            
            if reqs.get("min_spent", 0) > 0:
                texts["min_spent"] = f"**Gasto mínimo: R$ {reqs['min_spent']:.2f}**"
            
            if reqs.get("client_role"):
                texts["client_role"] = "**Ser cliente da loja**"
            
            if reqs.get("ecloud_verified"):
                texts["ecloud"] = "**Verificado no eCloud**"
            
            if reqs.get("in_voice_call"):
                texts["voice"] = "**Estar em canal de voz**"
            
            if reqs.get("custom_name"):
                texts["custom_name"] = f"**Nome contendo '{reqs['custom_name']}'**"
                
        except Exception as e:
            print(f"Erro ao gerar texto de requisitos: {e}")
        
        return texts

    async def end_giveaway(self, giveaway_id: str):
        try:
            giveaway = self.system.giveaways.get(giveaway_id)
            if not giveaway or giveaway.get("ended"): 
                return
            
            giveaway["ended"] = True
            guild = self.bot.get_guild(giveaway.get("guild_id"))
            task_config = giveaway.get("task_config", {})
            min_participants = task_config.get("min_participants", 0)
            
            valid_participants = []
            if guild:
                for user_id in giveaway.get("participants", []):
                    try:
                        member = guild.get_member(int(user_id))
                        if member:
                            can_participate, _ = await self.system.check_all_requirements(member, giveaway_id)
                            if can_participate:
                                valid_participants.append(member)
                    except Exception:
                        continue
            
            winners = []
            end_reason = "Não houve participantes suficientes ou válidos para sortear um vencedor."
            
            if len(valid_participants) < min_participants:
                end_reason = f"O sorteio não atingiu o mínimo de {min_participants} participantes válidos."
            else:
                winner_count = task_config.get("winner_count", 1)
                if giveaway.get("is_fake") and giveaway.get("predefined_winner"):
                    try: 
                        winner_user = await self.bot.fetch_user(int(giveaway["predefined_winner"]))
                        winners.append(winner_user)
                    except disnake.NotFound: 
                        pass
                elif len(valid_participants) >= winner_count:
                    winners = random.sample(valid_participants, k=min(winner_count, len(valid_participants)))

            color_hex = giveaway.get("embed_config", {}).get("color", "2B2D31").replace("#", "")
            try:
                color = int(color_hex, 16)
            except ValueError:
                color = 0x2B2D31
            
            ended_embed = disnake.Embed(
                title=f"{presente} Sorteio Finalizado: {giveaway.get('embed_config', {}).get('title', giveaway.get('name'))}",
                color=color
            )
            
            if winners:
                winner_mentions = ", ".join(w.mention for w in winners)
                ended_embed.description = f"🎉 **Parabéns aos vencedores:** {winner_mentions}!"
            else:
                ended_embed.description = f"❌ **{end_reason}**"
            
            ended_embed.add_field(name="🎁 Prêmio", value=f"`{giveaway.get('prize', 'Não definido')}`", inline=False)
            ended_embed.set_footer(text=f"Sorteio finalizado • ID: {giveaway_id}")
            
            # Enviar mensagem de finalização e editar mensagens originais
            for channel_id, message_id in giveaway.get("sent_messages", {}).items():
                try:
                    channel = self.bot.get_channel(int(channel_id))
                    if not channel:
                        continue
                    
                    # Enviar nova mensagem de finalização
                    content = f"🎊 O sorteio **'{giveaway.get('name')}'** foi finalizado!"
                    if winners:
                        content += f" {winner_mentions}"
                    
                    await channel.send(content=content, embed=ended_embed)
                    
                    # Editar mensagem original
                    try:
                        msg_to_edit = await channel.fetch_message(int(message_id))
                        await msg_to_edit.edit(embed=ended_embed, components=None)
                    except (disnake.NotFound, disnake.Forbidden):
                        pass
                        
                except Exception as e:
                    print(f"Erro ao finalizar sorteio no canal {channel_id}: {e}")
            
            # Enviar prêmios por DM
            if winners and giveaway.get("prize") and giveaway.get("prize") != "Entrega Manual":
                for winner in winners:
                    try: 
                        await winner.send(
                            f"🎉 **Parabéns!** Você ganhou o sorteio **'{giveaway.get('name')}'**!\n\n"
                            f"**Seu prêmio:**\n```\n{giveaway.get('prize')}\n```\n\n"
                            f"Entre em contato com a administração do servidor para retirar seu prêmio."
                        )
                    except disnake.Forbidden: 
                        pass
                    except Exception as e:
                        print(f"Erro ao enviar DM para vencedor {winner.id}: {e}")
            
            self.system.save_giveaways()
            
        except Exception as e:
            print(f"Erro ao finalizar sorteio {giveaway_id}: {e}")

    @commands.Cog.listener("on_button_click")
    async def on_giveaway_button(self, inter: disnake.MessageInteraction):
        try:
            cid = inter.component.custom_id
            if not cid.startswith("giveaway_"): 
                return

            # Modal responses (devem ser primeiro)
            if cid == "giveaway_create_new":
                modal = CreateGiveawayModal(self)
                return await inter.response.send_modal(modal=modal)
            
            parts = cid.split("_")
            if len(parts) < 2:
                return
                
            action = parts[1]
            
            if action == "cfg" and len(parts) >= 4:
                gid = parts[-1]
                cfg_type = parts[2]
                
                modals = {
                    "embed": EmbedConfigModal(self, gid),
                    "prize": PrizeModal(self, gid),
                    "task": TaskConfigModal(self, gid),
                    "winner": WinnerModal(self, gid)
                }
                
                if cfg_type in modals:
                    return await inter.response.send_modal(modal=modals[cfg_type])
                elif cfg_type == "reqs":
                    view = RequirementsMainView(self, gid)
                    await inter.response.defer()
                    return await inter.edit_original_response(content=None, embed=None, view=view)

            # Handle participate button (ephemeral response)
            if action == "participate" and len(parts) >= 3:
                await inter.response.defer(ephemeral=True)
                gid = parts[-1]
                giveaway = self.system.giveaways.get(gid)
                
                if not giveaway:
                    return await inter.edit_original_response(content="❌ Este sorteio não existe mais.")
                
                if giveaway.get("ended"):
                    return await inter.edit_original_response(content="❌ Este sorteio já foi finalizado.")
                
                task_config = giveaway.get("task_config", {})
                max_participants = task_config.get("max_participants")
                participants = giveaway.setdefault("participants", [])
                user_id_str = str(inter.author.id)

                if user_id_str not in participants:
                    # Verificar limite máximo
                    if max_participants and len(participants) >= max_participants:
                        return await inter.edit_original_response(content="❌ O sorteio atingiu o número máximo de participantes.")
                    
                    # Verificar requisitos
                    can_enter, reason = await self.system.check_all_requirements(inter.author, gid)
                    if not can_enter: 
                        return await inter.edit_original_response(content=f"❌ Você não pode entrar no sorteio:\n{reason}")
                    
                    # Adicionar participante
                    participants.append(user_id_str)
                    await inter.edit_original_response(content="✅ Você entrou no sorteio! Boa sorte! 🍀")
                else:
                    # Remover participante
                    participants.remove(user_id_str)
                    await inter.edit_original_response(content="↩️ Você saiu do sorteio.")
                
                self.system.save_giveaways()
                await self.update_all_messages(gid)
                return

            # Outras interações (defer normal)
            if not inter.response.is_done():
                await inter.response.defer()

            if len(parts) < 3:
                return await inter.edit_original_response(content="❌ Ação inválida.")

            # Handle back button
            if action == "back" and parts[2] == "to" and parts[3] == "main":
                return await self.show_main_panel(inter)

            giveaway_id = parts[-1]
            giveaway = self.system.giveaways.get(giveaway_id)
            
            if not giveaway:
                return await inter.edit_original_response(content="❌ Este sorteio não existe mais.")

            if action == "delete":
                del self.system.giveaways[giveaway_id]
                self.system.save_giveaways()
                await self.show_main_panel(inter)
                
            elif action == "toggle" and parts[2] == "monitor":
                giveaway["monitor_enabled"] = not giveaway.get("monitor_enabled", False)
                self.system.save_giveaways()
                if giveaway["monitor_enabled"] and not self.giveaway_monitor.is_running():
                    self.giveaway_monitor.restart()
                await self.show_manage_panel(inter, giveaway_id)
                
            elif action == "send":
                if not giveaway.get("task_config", {}).get("duration_seconds"):
                    return await inter.edit_original_response(content="❌ Defina uma duração (Task) antes de enviar o sorteio.", view=None)
                
                # Create channel select
                channel_select = disnake.ui.ChannelSelect(
                    placeholder="Selecione o canal para enviar o sorteio...",
                    custom_id=f"giveaway_send_channel_{giveaway_id}",
                    channel_types=[disnake.ChannelType.text, disnake.ChannelType.news]
                )
                view = disnake.ui.View(timeout=300)
                view.add_item(channel_select)
                
                await inter.edit_original_response(content="📝 Selecione o canal para postar o sorteio:", embed=None, view=view)

        except Exception as e:
            print(f"Erro em on_giveaway_button: {e}")
            try:
                if not inter.response.is_done():
                    await inter.response.defer(ephemeral=True)
                await inter.edit_original_response(content=f"❌ Erro interno: {str(e)[:100]}")
            except:
                pass

    @commands.Cog.listener("on_dropdown")
    async def on_giveaway_dropdown(self, inter: disnake.MessageInteraction):
        try:
            cid = inter.component.custom_id
            if not cid.startswith("giveaway_"):
                return

            # Handle requirement modals first
            if cid.startswith("giveaway_reqs_select"):
                gid = cid.split("_")[-1]
                if not inter.values:
                    return
                    
                req_type = inter.values[0]
                modal_types = ["spending", "account_age", "invites", "text", "location", "purchase_date"]
                view_types = ["roles", "voice", "profile"]
                
                if req_type in modal_types:
                    modal = self.get_req_modal(req_type, gid)
                    if modal:
                        return await inter.response.send_modal(modal)
                elif req_type in view_types:
                    view = self.get_req_view(req_type, gid)
                    if view:
                        await inter.response.defer()
                        return await inter.edit_original_response(
                            content=f"⚙️ Configure os requisitos de **{req_type.capitalize()}**:",
                            embed=None,
                            view=view
                        )

            # Other dropdown interactions
            if not inter.response.is_done():
                await inter.response.defer()
            
            parts = cid.split("_")
            if len(parts) < 2:
                return
                
            action = parts[1]
            
            if action == "manage" and parts[2] == "select":
                if inter.values:
                    return await self.show_manage_panel(inter, inter.values[0])
            
            elif action == "send" and parts[2] == "channel":
                giveaway_id = parts[-1]
                giveaway = self.system.giveaways.get(giveaway_id)
                
                if not giveaway:
                    return await inter.edit_original_response(content="❌ Sorteio não existe mais.")
                
                if not inter.values:
                    return await inter.edit_original_response(content="❌ Nenhum canal selecionado.")
                
                channel = self.bot.get_channel(int(inter.values[0]))
                if not channel:
                    return await inter.edit_original_response(content="❌ Canal não encontrado.")
                
                # Verificar permissões no canal
                permissions = channel.permissions_for(inter.guild.me)
                if not (permissions.send_messages and permissions.embed_links):
                    return await inter.edit_original_response(
                        content="❌ Não tenho permissões suficientes neste canal (preciso de 'Enviar Mensagens' e 'Incorporar Links')."
                    )
                
                # Configurar timestamps
                giveaway.setdefault("sent_messages", {})
                duration = giveaway.get("task_config", {}).get("duration_seconds", 0)
                giveaway["end_timestamp"] = int(time.time()) + duration
                
                try:
                    content, embed, components = self.build_giveaway_message(giveaway_id)
                    msg = await channel.send(content=content, embed=embed, components=components)
                    giveaway["sent_messages"][str(channel.id)] = str(msg.id)
                    self.system.save_giveaways()
                    
                    await inter.edit_original_response(
                        content=f"✅ Sorteio enviado com sucesso em {channel.mention}!",
                        view=None
                    )
                except Exception as e:
                    await inter.edit_original_response(
                        content=f"❌ Falha ao enviar sorteio: {str(e)[:200]}",
                        view=None
                    )
            
            elif action == "reqs" and parts[2] == "set":
                giveaway_id = parts[-1]
                giveaway = self.system.giveaways.get(giveaway_id)
                
                if not giveaway:
                    return await inter.edit_original_response(content="❌ Sorteio não existe mais.")
                
                if not inter.values:
                    return await inter.edit_original_response(content="❌ Nenhum valor selecionado.")
                
                key = "required_roles" if "required" in cid else "banned_roles"
                giveaway.setdefault("requirements", {})[key] = [str(r.id) for r in inter.values]
                self.system.save_giveaways()
                
                view = self.get_req_view("roles", giveaway_id)
                await inter.edit_original_response(content="✅ Requisitos de cargo salvos!", view=view)

        except Exception as e:
            print(f"Erro em on_giveaway_dropdown: {e}")
            try:
                if not inter.response.is_done():
                    await inter.response.defer(ephemeral=True)
                await inter.edit_original_response(content=f"❌ Erro interno: {str(e)[:100]}")
            except:
                pass

    @commands.Cog.listener()
    async def on_modal_submit(self, inter: disnake.ModalInteraction):
        try:
            cid = inter.custom_id
            if not cid.startswith("giveaway_modal_"):
                return
            
            if not inter.response.is_done():
                await inter.response.defer()

            parts = cid.split("_")
            if len(parts) < 3:
                return
                
            modal_type = parts[2]
            
            if modal_type == "create":
                gid = self.system.generate_id()
                name = inter.text_values.get("name", f"Sorteio {gid}").strip()
                
                self.system.giveaways[gid] = {
                    "id": gid,
                    "name": name,
                    "prize": "Entrega Manual",
                    "is_fake": False,
                    "predefined_winner": None,
                    "embed_config": {
                        "title": name,
                        "description": "Clique no botão para participar!",
                        "color": "2B2D31"
                    },
                    "task_config": {
                        "duration_seconds": 0,
                        "winner_count": 1,
                        "min_participants": 0,
                        "max_participants": None
                    },
                    "requirements": {},
                    "monitor_enabled": True,
                    "participants": [],
                    "sent_messages": {},
                    "ended": False,
                    "guild_id": inter.guild.id
                }
                self.system.save_giveaways()
                return await self.show_manage_panel(inter, gid)

            if len(parts) < 4:
                return
                
            giveaway_id = parts[-1]
            giveaway = self.system.giveaways.get(giveaway_id)
            
            if not giveaway:
                return await inter.edit_original_response(content="❌ Sorteio não existe mais.")

            if modal_type == "embed":
                embed_config = giveaway.setdefault("embed_config", {})
                embed_config.update({
                    "title": inter.text_values.get("title", "").strip() or giveaway.get("name", "Sorteio"),
                    "description": inter.text_values.get("desc", "").strip() or "Clique no botão para participar!",
                    "image_url": inter.text_values.get("img", "").strip(),
                    "thumbnail_url": inter.text_values.get("thumb", "").strip()
                })
                
                # Validar cor hex
                color = inter.text_values.get("color", "").strip().replace("#", "")
                if len(color) == 6 and all(c in "0123456789abcdefABCDEF" for c in color):
                    embed_config["color"] = color
                else:
                    embed_config["color"] = "2B2D31"
                    
            elif modal_type == "prize":
                prize = inter.text_values.get("prize", "").strip()
                giveaway["prize"] = prize if prize else "Entrega Manual"
                
            elif modal_type == "task":
                duration_text = inter.text_values.get("duration", "").strip()
                duration_sec = self.system.parse_duration(duration_text)
                
                if duration_sec is None or duration_sec <= 0:
                    return await inter.edit_original_response(
                        content="❌ Formato de duração inválido. Use formatos como: 1d 2h 30m, 5h, 90m, etc."
                    )
                
                try:
                    winners = int(inter.text_values.get("winners", "1"))
                    min_p = int(inter.text_values.get("min_p", "0") or "0")
                    max_p_text = inter.text_values.get("max_p", "0").strip()
                    max_p = int(max_p_text) if max_p_text and max_p_text != "0" else None
                    
                    if winners < 1 or min_p < 0 or (max_p is not None and max_p < 0):
                        raise ValueError("Valores inválidos")
                        
                except (ValueError, AssertionError):
                    return await inter.edit_original_response(
                        content="❌ Valores de Task devem ser números válidos e positivos."
                    )
                
                task_config = giveaway.setdefault("task_config", {})
                task_config.update({
                    "duration_seconds": duration_sec,
                    "winner_count": winners,
                    "min_participants": min_p,
                    "max_participants": max_p
                })
                
            elif modal_type == "winner":
                winner_id = inter.text_values.get("winner_id", "").strip()
                if not winner_id.isdigit():
                    return await inter.edit_original_response(
                        content="❌ ID do vencedor deve ser um número válido."
                    )
                
                giveaway.update({
                    "is_fake": True,
                    "predefined_winner": winner_id
                })
                
            elif modal_type == "reqs" and len(parts) >= 5:
                req_type = parts[3]
                reqs = giveaway.setdefault("requirements", {})
                
                try:
                    if req_type == "spending":
                        min_spent = inter.text_values.get("min_spent", "").strip()
                        max_spent = inter.text_values.get("max_spent", "").strip()
                        
                        reqs["min_spent"] = float(min_spent) if min_spent else 0.0
                        reqs["max_spent"] = float(max_spent) if max_spent else None
                        
                    elif req_type == "accountage":
                        days = inter.text_values.get("days", "").strip()
                        reqs["min_account_age_days"] = int(days) if days else 0
                        
                    elif req_type == "invites":
                        min_invites = inter.text_values.get("min_invites", "").strip()
                        reqs["min_invites"] = int(min_invites) if min_invites else 0
                        
                    elif req_type == "text":
                        reqs["custom_name"] = inter.text_values.get("custom_name", "").strip()
                        reqs["custom_status"] = inter.text_values.get("custom_status", "").strip()
                        
                    elif req_type == "location":
                        reqs["country"] = inter.text_values.get("country", "").strip()
                        reqs["state"] = inter.text_values.get("state", "").strip()
                        reqs["city"] = inter.text_values.get("city", "").strip()
                        
                    elif req_type == "purchasedate":
                        first = inter.text_values.get("first_purchase", "").strip()
                        last = inter.text_values.get("last_purchase", "").strip()
                        
                        reqs["first_purchase_days"] = int(first) if first else 0
                        reqs["last_purchase_days"] = int(last) if last else 0
                        
                except ValueError:
                    return await inter.edit_original_response(
                        content="❌ Valor numérico inválido inserido."
                    )
                
                self.system.save_giveaways()
                view = RequirementsMainView(self, giveaway_id)
                return await inter.edit_original_response(
                    content="✅ Requisito salvo com sucesso!",
                    embed=None,
                    view=view
                )

            self.system.save_giveaways()
            await self.update_all_messages(giveaway_id)
            await self.show_manage_panel(inter, giveaway_id)
            
        except Exception as e:
            print(f"Erro em on_modal_submit: {e}")
            try:
                if not inter.response.is_done():
                    await inter.response.defer(ephemeral=True)
                await inter.edit_original_response(content=f"❌ Erro ao processar modal: {str(e)[:100]}")
            except:
                pass

    # Handle requirement toggle buttons
    @commands.Cog.listener("on_button_click")
    async def on_requirement_toggle(self, inter: disnake.MessageInteraction):
        try:
            cid = inter.component.custom_id
            if not cid.startswith("giveaway_toggle_req_"):
                return
            
            await inter.response.defer()
            
            parts = cid.split("_")
            if len(parts) < 5:
                return
                
            req_key = parts[3]
            giveaway_id = parts[-1]
            
            giveaway = self.system.giveaways.get(giveaway_id)
            if not giveaway:
                return await inter.edit_original_response(content="❌ Sorteio não existe mais.")
            
            reqs = giveaway.setdefault("requirements", {})
            current_value = reqs.get(req_key, False)
            reqs[req_key] = not current_value
            
            self.system.save_giveaways()
            
            # Determine view type based on req_key
            if req_key in ["in_voice_call", "is_unmuted", "is_undeafened"]:
                view = self.get_req_view("voice", giveaway_id)
            elif req_key in ["client_role", "ecloud_verified"]:
                view = self.get_req_view("profile", giveaway_id)
            else:
                view = RequirementsMainView(self, giveaway_id)
            
            await inter.edit_original_response(
                content=f"✅ Requisito {'ativado' if reqs[req_key] else 'desativado'}!",
                view=view
            )
            
        except Exception as e:
            print(f"Erro em on_requirement_toggle: {e}")
            try:
                await inter.edit_original_response(content=f"❌ Erro: {str(e)[:100]}")
            except:
                pass
    
    def get_req_modal(self, req_type: str, gid: str):
        try:
            modals = {
                "spending": SpendingReqModal,
                "account_age": AccountAgeReqModal,
                "invites": InvitesReqModal,
                "text": TextReqModal,
                "location": LocationReqModal,
                "purchase_date": PurchaseDateReqModal
            }
            modal_class = modals.get(req_type)
            return modal_class(self, gid) if modal_class else None
        except Exception as e:
            print(f"Erro ao criar modal {req_type}: {e}")
            return None

    def get_req_view(self, req_type: str, gid: str):
        try:
            views = {
                "roles": RolesReqView,
                "voice": VoiceReqView,
                "profile": ProfileReqView
            }
            view_class = views.get(req_type)
            return view_class(self, gid) if view_class else None
        except Exception as e:
            print(f"Erro ao criar view {req_type}: {e}")
            return None

# --- Classes de Componentes (Modals e Views) ---

class CreateGiveawayModal(disnake.ui.Modal):
    def __init__(self, cog: GiveawayCog):
        components = [
            disnake.ui.TextInput(
                label="Nome do Sorteio",
                custom_id="name",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=100,
                placeholder="Digite o nome do sorteio..."
            )
        ]
        super().__init__(title="Criar Novo Sorteio", custom_id="giveaway_modal_create_0", components=components)

class EmbedConfigModal(disnake.ui.Modal):
    def __init__(self, cog: GiveawayCog, gid: str):
        giveaway = cog.system.giveaways.get(gid, {})
        embed_config = giveaway.get("embed_config", {})
        
        components = [
            disnake.ui.TextInput(
                label="Título",
                custom_id="title",
                value=embed_config.get("title", ""),
                required=True,
                max_length=256,
                placeholder="Título do embed do sorteio"
            ),
            disnake.ui.TextInput(
                label="Descrição",
                custom_id="desc",
                value=embed_config.get("description", ""),
                style=disnake.TextInputStyle.paragraph,
                required=True,
                max_length=4000,
                placeholder="Descrição do sorteio"
            ),
            disnake.ui.TextInput(
                label="URL da Imagem",
                custom_id="img",
                value=embed_config.get("image_url", ""),
                required=False,
                placeholder="https://exemplo.com/imagem.png"
            ),
            disnake.ui.TextInput(
                label="URL da Thumbnail",
                custom_id="thumb",
                value=embed_config.get("thumbnail_url", ""),
                required=False,
                placeholder="https://exemplo.com/thumbnail.png"
            ),
            disnake.ui.TextInput(
                label="Cor HEX (ex: 2B2D31)",
                custom_id="color",
                value=embed_config.get("color", "2B2D31"),
                required=False,
                max_length=7,
                placeholder="2B2D31"
            )
        ]
        super().__init__(title="Configurar Embed", custom_id=f"giveaway_modal_embed_{gid}", components=components)

class PrizeModal(disnake.ui.Modal):
    def __init__(self, cog: GiveawayCog, gid: str):
        giveaway = cog.system.giveaways.get(gid, {})
        components = [
            disnake.ui.TextInput(
                label="Prêmio",
                custom_id="prize",
                style=disnake.TextInputStyle.paragraph,
                value=giveaway.get("prize", ""),
                required=False,
                max_length=1000,
                placeholder="Deixe em branco para entrega manual"
            )
        ]
        super().__init__(title="Configurar Premiação", custom_id=f"giveaway_modal_prize_{gid}", components=components)

class TaskConfigModal(disnake.ui.Modal):
    def __init__(self, cog: GiveawayCog, gid: str):
        giveaway = cog.system.giveaways.get(gid, {})
        task_config = giveaway.get("task_config", {})
        
        components = [
            disnake.ui.TextInput(
                label="Duração (ex: 1d 2h 30m)",
                custom_id="duration",
                value=cog.format_duration(task_config.get("duration_seconds", 0)),
                required=True,
                placeholder="1d 12h 30m"
            ),
            disnake.ui.TextInput(
                label="Número de Vencedores",
                custom_id="winners",
                value=str(task_config.get("winner_count", 1)),
                required=True,
                placeholder="1"
            ),
            disnake.ui.TextInput(
                label="Mínimo de Participantes",
                custom_id="min_p",
                value=str(task_config.get("min_participants", 0)),
                required=False,
                placeholder="0"
            ),
            disnake.ui.TextInput(
                label="Máximo de Participantes (0=ilimitado)",
                custom_id="max_p",
                value=str(task_config.get("max_participants", 0) if task_config.get("max_participants") else 0),
                required=False,
                placeholder="0"
            )
        ]
        super().__init__(title="Configurar Task", custom_id=f"giveaway_modal_task_{gid}", components=components)

class WinnerModal(disnake.ui.Modal):
    def __init__(self, cog: GiveawayCog, gid: str):
        components = [
            disnake.ui.TextInput(
                label="ID do Vencedor Predefinido",
                custom_id="winner_id",
                required=True,
                placeholder="123456789012345678"
            )
        ]
        super().__init__(title="Definir Vencedor (Fake)", custom_id=f"giveaway_modal_winner_{gid}", components=components)

class RequirementsMainView(disnake.ui.View):
    def __init__(self, cog: GiveawayCog, gid: str):
        super().__init__(timeout=300)
        
        options = [
            disnake.SelectOption(
                label="Cargos",
                value="roles",
                description="Definir cargos obrigatórios e proibidos",
                emoji="👤"
            ),
            disnake.SelectOption(
                label="Tempo de Conta",
                value="account_age",
                description="Exigir idade mínima da conta Discord",
                emoji="📅"
            ),
            disnake.SelectOption(
                label="Gastos na Loja",
                value="spending",
                description="Exigir valor mínimo/máximo de compras",
                emoji="💰"
            ),
            disnake.SelectOption(
                label="Datas de Compra",
                value="purchase_date",
                description="Limitar por primeira/última compra",
                emoji="🛒"
            ),
            disnake.SelectOption(
                label="Convites",
                value="invites",
                description="Exigir número mínimo de convites",
                emoji="📨"
            ),
            disnake.SelectOption(
                label="Nome/Status",
                value="text",
                description="Exigir texto no nome ou status",
                emoji="📝"
            ),
            disnake.SelectOption(
                label="Localização",
                value="location",
                description="Exigir país, estado ou cidade específica",
                emoji="🌍"
            ),
            disnake.SelectOption(
                label="Requisitos de Voz",
                value="voice",
                description="Estar em call, desmutado, etc.",
                emoji="🎤"
            ),
            disnake.SelectOption(
                label="Requisitos de Perfil",
                value="profile",
                description="Ser cliente, verificado no eCloud, etc.",
                emoji="✅"
            )
        ]
        
        select = disnake.ui.StringSelect(
            placeholder="Escolha um requisito para configurar...",
            options=options,
            custom_id=f"giveaway_reqs_select_{gid}"
        )
        self.add_item(select)
        
        back_button = disnake.ui.Button(
            label="Voltar ao Gerenciamento",
            emoji=voltar,
            style=disnake.ButtonStyle.grey,
            custom_id=f"giveaway_cfg_back_{gid}"
        )
        self.add_item(back_button)

class BaseReqView(disnake.ui.View):
    def __init__(self, cog: GiveawayCog, gid: str):
        super().__init__(timeout=300)
        back_button = disnake.ui.Button(
            label="Voltar aos Requisitos",
            emoji=voltar,
            style=disnake.ButtonStyle.grey,
            custom_id=f"giveaway_cfg_reqs_{gid}"
        )
        self.add_item(back_button)

class RolesReqView(BaseReqView):
    def __init__(self, cog: GiveawayCog, gid: str):
        super().__init__(cog, gid)
        
        giveaway = cog.system.giveaways.get(gid, {})
        reqs = giveaway.get("requirements", {})
        
        # Select para cargos obrigatórios
        required_roles = reqs.get("required_roles", [])
        required_select = RoleSelect(
            "Selecione cargos obrigatórios...",
            f"giveaway_reqs_set_required_{gid}",
            required_roles
        )
        self.add_item(required_select)
        
        # Select para cargos proibidos
        banned_roles = reqs.get("banned_roles", [])
        banned_select = RoleSelect(
            "Selecione cargos proibidos...",
            f"giveaway_reqs_set_banned_{gid}",
            banned_roles
        )
        self.add_item(banned_select)

class VoiceReqView(BaseReqView):
    def __init__(self, cog: GiveawayCog, gid: str):
        super().__init__(cog, gid)
        
        giveaway = cog.system.giveaways.get(gid, {})
        reqs = giveaway.get("requirements", {})
        
        # Botão para "estar em call"
        in_voice = reqs.get("in_voice_call", False)
        voice_button = disnake.ui.Button(
            label="Estar em Canal de Voz",
            style=disnake.ButtonStyle.green if in_voice else disnake.ButtonStyle.red,
            custom_id=f"giveaway_toggle_req_in_voice_call_{gid}",
            emoji="✅" if in_voice else "❌"
        )
        self.add_item(voice_button)
        
        # Botão para "estar desmutado"
        unmuted = reqs.get("is_unmuted", False)
        unmuted_button = disnake.ui.Button(
            label="Estar Desmutado",
            style=disnake.ButtonStyle.green if unmuted else disnake.ButtonStyle.red,
            custom_id=f"giveaway_toggle_req_is_unmuted_{gid}",
            emoji="✅" if unmuted else "❌"
        )
        self.add_item(unmuted_button)
        
        # Botão para "estar ouvindo"
        undeafened = reqs.get("is_undeafened", False)
        undeafened_button = disnake.ui.Button(
            label="Estar Ouvindo",
            style=disnake.ButtonStyle.green if undeafened else disnake.ButtonStyle.red,
            custom_id=f"giveaway_toggle_req_is_undeafened_{gid}",
            emoji="✅" if undeafened else "❌"
        )
        self.add_item(undeafened_button)

class ProfileReqView(BaseReqView):
    def __init__(self, cog: GiveawayCog, gid: str):
        super().__init__(cog, gid)
        
        giveaway = cog.system.giveaways.get(gid, {})
        reqs = giveaway.get("requirements", {})
        
        # Botão para "ser cliente"
        client_role = reqs.get("client_role", False)
        client_button = disnake.ui.Button(
            label="Ser Cliente da Loja",
            style=disnake.ButtonStyle.green if client_role else disnake.ButtonStyle.red,
            custom_id=f"giveaway_toggle_req_client_role_{gid}",
            emoji="✅" if client_role else "❌"
        )
        self.add_item(client_button)
        
        # Botão para "verificado no eCloud"
        ecloud_verified = reqs.get("ecloud_verified", False)
        ecloud_button = disnake.ui.Button(
            label="Verificado no eCloud",
            style=disnake.ButtonStyle.green if ecloud_verified else disnake.ButtonStyle.red,
            custom_id=f"giveaway_toggle_req_ecloud_verified_{gid}",
            emoji="✅" if ecloud_verified else "❌"
        )
        self.add_item(ecloud_button)

class RoleSelect(disnake.ui.RoleSelect):
    def __init__(self, placeholder, custom_id, defaults=None):
        default_values = []
        if defaults:
            for role_id in defaults:
                try:
                    default_values.append(disnake.Object(id=int(role_id)))
                except (ValueError, TypeError):
                    continue
        
        super().__init__(
            placeholder=placeholder,
            custom_id=custom_id,
            min_values=0,
            max_values=25,
            default_values=default_values
        )

# --- Modals para Requisitos ---

class SpendingReqModal(disnake.ui.Modal):
    def __init__(self, cog: GiveawayCog, gid: str):
        giveaway = cog.system.giveaways.get(gid, {})
        reqs = giveaway.get("requirements", {})
        
        components = [
            disnake.ui.TextInput(
                label="Gasto Mínimo (ex: 50.00)",
                custom_id="min_spent",
                value=str(reqs.get("min_spent", "")),
                required=False,
                placeholder="0.00"
            ),
            disnake.ui.TextInput(
                label="Gasto Máximo (opcional)",
                custom_id="max_spent",
                value=str(reqs.get("max_spent", "")),
                required=False,
                placeholder="Deixe vazio para sem limite"
            )
        ]
        super().__init__(title="Requisitos de Gastos", custom_id=f"giveaway_modal_reqs_spending_{gid}", components=components)

class AccountAgeReqModal(disnake.ui.Modal):
    def __init__(self, cog: GiveawayCog, gid: str):
        giveaway = cog.system.giveaways.get(gid, {})
        reqs = giveaway.get("requirements", {})
        
        components = [
            disnake.ui.TextInput(
                label="Mínimo de dias da conta",
                custom_id="days",
                value=str(reqs.get("min_account_age_days", "")),
                required=False,
                placeholder="30"
            )
        ]
        super().__init__(title="Requisito de Tempo de Conta", custom_id=f"giveaway_modal_reqs_accountage_{gid}", components=components)

class PurchaseDateReqModal(disnake.ui.Modal):
    def __init__(self, cog: GiveawayCog, gid: str):
        giveaway = cog.system.giveaways.get(gid, {})
        reqs = giveaway.get("requirements", {})
        
        components = [
            disnake.ui.TextInput(
                label="Primeira compra nos últimos X dias",
                custom_id="first_purchase",
                value=str(reqs.get("first_purchase_days", "")),
                required=False,
                placeholder="365"
            ),
            disnake.ui.TextInput(
                label="Última compra nos últimos X dias",
                custom_id="last_purchase",
                value=str(reqs.get("last_purchase_days", "")),
                required=False,
                placeholder="30"
            )
        ]
        super().__init__(title="Requisitos de Data de Compra", custom_id=f"giveaway_modal_reqs_purchasedate_{gid}", components=components)

class InvitesReqModal(disnake.ui.Modal):
    def __init__(self, cog: GiveawayCog, gid: str):
        giveaway = cog.system.giveaways.get(gid, {})
        reqs = giveaway.get("requirements", {})
        
        components = [
            disnake.ui.TextInput(
                label="Mínimo de Convites",
                custom_id="min_invites",
                value=str(reqs.get("min_invites", "")),
                required=False,
                placeholder="5"
            )
        ]
        super().__init__(title="Requisito de Convites", custom_id=f"giveaway_modal_reqs_invites_{gid}", components=components)

class TextReqModal(disnake.ui.Modal):
    def __init__(self, cog: GiveawayCog, gid: str):
        giveaway = cog.system.giveaways.get(gid, {})
        reqs = giveaway.get("requirements", {})
        
        components = [
            disnake.ui.TextInput(
                label="Texto no Nome de Usuário",
                custom_id="custom_name",
                value=reqs.get("custom_name", ""),
                required=False,
                placeholder="Ex: [Membro]"
            ),
            disnake.ui.TextInput(
                label="Texto no Status Personalizado",
                custom_id="custom_status",
                value=reqs.get("custom_status", ""),
                required=False,
                placeholder="Ex: Participando do sorteio!"
            )
        ]
        super().__init__(title="Requisitos de Texto", custom_id=f"giveaway_modal_reqs_text_{gid}", components=components)

class LocationReqModal(disnake.ui.Modal):
    def __init__(self, cog: GiveawayCog, gid: str):
        giveaway = cog.system.giveaways.get(gid, {})
        reqs = giveaway.get("requirements", {})
        
        components = [
            disnake.ui.TextInput(
                label="País (ex: Brazil)",
                custom_id="country",
                value=reqs.get("country", ""),
                required=False,
                placeholder="Brazil"
            ),
            disnake.ui.TextInput(
                label="Estado (ex: Goias)",
                custom_id="state",
                value=reqs.get("state", ""),
                required=False,
                placeholder="Goias"
            ),
            disnake.ui.TextInput(
                label="Cidade (ex: Goiania)",
                custom_id="city",
                value=reqs.get("city", ""),
                required=False,
                placeholder="Goiania"
            )
        ]
        super().__init__(title="Requisitos de Localização", custom_id=f"giveaway_modal_reqs_location_{gid}", components=components)

# --- Comando Slash para Admins ---
@commands.slash_command(name="sorteios", description="Gerenciar sistema de sorteios")
@commands.has_permissions(administrator=True)
async def giveaways_command(inter: disnake.ApplicationCommandInteraction):
    """Comando principal para acessar o sistema de sorteios"""
    try:
        await inter.response.defer(ephemeral=True)
        
        cog = inter.bot.get_cog("Giveaways")
        if not cog:
            return await inter.edit_original_response(content="❌ Sistema de sorteios não está carregado.")
        
        await cog.show_main_panel(inter)
        
    except Exception as e:
        print(f"Erro em giveaways_command: {e}")
        try:
            await inter.edit_original_response(content=f"❌ Erro interno: {str(e)[:100]}")
        except:
            pass

# --- Função Setup ---
def setup(bot: commands.Bot):
    """Função para carregar o cog"""
    try:
        # Verificar se já existe
        existing_cog = bot.get_cog("Giveaways")
        if existing_cog:
            print("Removendo cog Giveaways existente...")
            bot.remove_cog("Giveaways")
        
        # Adicionar novo cog
        cog_instance = GiveawayCog(bot)
        bot.add_cog(cog_instance)
        
        # Adicionar comando slash
        bot.add_slash_command(giveaways_command)
        
        # Listener global para botões de painel
        @bot.listen("on_button_click")
        async def gateway_button_listener(inter: disnake.MessageInteraction):
            """Listener para botão de acesso ao painel de sorteios"""
            try:
                if inter.component.custom_id == "GerenciarPainelGiveaways":
                    await inter.response.defer(ephemeral=True)
                    
                    # Verificar permissões
                    if not inter.author.guild_permissions.administrator:
                        return await inter.edit_original_response(
                            content="❌ Você precisa ser administrador para acessar este painel."
                        )
                    
                    giveaway_cog = bot.get_cog("Giveaways")
                    if giveaway_cog:
                        await giveaway_cog.show_main_panel(inter)
                    else:
                        await inter.edit_original_response(
                            content="❌ Sistema de sorteios não está disponível."
                        )
            except Exception as e:
                print(f"Erro em gateway_button_listener: {e}")
                try:
                    if not inter.response.is_done():
                        await inter.response.defer(ephemeral=True)
                    await inter.edit_original_response(content="❌ Erro interno.")
                except:
                    pass
        
        print("✅ Sistema de Giveaways carregado com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro ao carregar sistema de Giveaways: {e}")
        raise