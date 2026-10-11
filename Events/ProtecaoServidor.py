import disnake
from disnake.ext import commands
from datetime import datetime, timedelta, timezone
import json
import asyncio

def ObterDatabaseProtecao():
    try:
        with open("Database/Server/protecao.json", "r") as f:
            db = json.load(f)
    except FileNotFoundError:
        db = {
            "canais": {
                "logs_channel_id": None,
                "criar": {"sistema": False, "limite": 0, "tempo_segundos": 0, "acao": "ban", "imunes_cargos": [], "imunes_categorias": []},
                "editar": {"sistema": False, "limite": 0, "tempo_segundos": 0, "acao": "ban", "imunes_cargos": [], "imunes_categorias": []},
                "excluir": {"sistema": False, "limite": 0, "tempo_segundos": 0, "acao": "ban", "imunes_cargos": [], "imunes_categorias": []}
            },
            "cargos": {
                "logs_channel_id": None,
                "criar": {"sistema": False, "limite": 0, "tempo_segundos": 0, "acao": "ban", "imunes_cargos": []},
                "editar": {"sistema": False, "limite": 0, "tempo_segundos": 0, "acao": "ban", "imunes_cargos": []},
                "excluir": {"sistema": False, "limite": 0, "tempo_segundos": 0, "acao": "ban", "imunes_cargos": []}
            },
            "banimento": {
                "sistema": False, "limite": 0, "tempo_segundos": 0, "acao": "reverter", "logs_channel_id": None, "imunes_cargos": []
            },
            "expulsao": {
                "sistema": False, "limite": 0, "tempo_segundos": 0, "acao": "reverter", "logs_channel_id": None, "imunes_cargos": []
            },
            "mencao": {
                "sistema": False, "limite_mencoes": 0, "tempo_segundos": 0, "acao": "silenciar", "logs_channel_id": None, "imunes_cargos": []
            },
            "adicionar_bot": {
                "sistema": False, "logs_channel_id": None, "acao": "ban_adicionador", "imunes_cargos": [], "whitelist_bots": []
            }
        }
        with open("Database/Server/protecao.json", "w") as f:
            json.dump(db, f, indent=4)
    return db

async def send_log_embed(bot: commands.Bot, guild: disnake.Guild, channel_id: int, title: str, description: str, color: disnake.Color = disnake.Color.red()):
    if not channel_id:
        return
    
    log_channel = guild.get_channel(channel_id)
    if not log_channel:
        return
    
    embed = disnake.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text=guild.name, icon_url=guild.icon.url if guild.icon else None)
    
    try:
        await log_channel.send(embed=embed)
    except Exception as e:
        print(f"Erro ao enviar log para o canal {channel_id}: {e}")

_action_monitor = {}

def get_recent_actions(guild_id: int, user_id: int, action_type: str, time_window_seconds: int):
    guild_data = _action_monitor.get(guild_id, {})
    user_data = guild_data.get(user_id, {})
    actions = user_data.get(action_type, [])
    
    now = datetime.now(timezone.utc)
    recent_actions = [(ts, aid) for ts, aid in actions if (now - ts).total_seconds() <= time_window_seconds]
    user_data[action_type] = recent_actions
    guild_data[user_id] = user_data
    _action_monitor[guild_id] = guild_data
    
    return recent_actions

def add_action_to_monitor(guild_id: int, user_id: int, action_type: str, action_id: int = None):
    if guild_id not in _action_monitor:
        _action_monitor[guild_id] = {}
    if user_id not in _action_monitor[guild_id]:
        _action_monitor[guild_id][user_id] = {}
    if action_type not in _action_monitor[guild_id][user_id]:
        _action_monitor[guild_id][user_id][action_type] = []
    
    _action_monitor[guild_id][user_id][action_type].append((datetime.now(timezone.utc), action_id))

async def apply_protection_action(bot: commands.Bot, guild: disnake.Guild, member: disnake.Member, action: str, reason: str):
    try:
        if action == "ban":
            await member.ban(reason=reason)
            return f"usuário banido: {member.name}"
        elif action == "kick":
            await member.kick(reason=reason)
            return f"usuário expulso: {member.name}"
        elif action == "timeout":
            await member.timeout(duration=timedelta(minutes=10), reason=reason)
            return f"usuário silenciado (timeout): {member.name}"
        elif action == "reverter":
            return f"Ação de reversão (depende do contexto do evento de auditoria)."
        elif action == "ban_agressor":
            await member.ban(reason=reason)
            return f"agressor banido: {member.name}"
        elif action == "kick_agressor":
            await member.kick(reason=reason)
            return f"agressor expulso: {member.name}"
        elif action == "delete_message":
            return "Mensagem apagada."
        elif action == "reverter_bot":
            return "Bot revertido."
    except disnake.Forbidden:
        return f"falha na ação ({action}): Permissões insuficientes."
    except Exception as e:
        return f"falha na ação ({action}): {e}"

class EventsProtecaoServidor(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def check_member_immunity(self, member: disnake.Member, imune_cargos_ids: list):
        if not member: return False
        for role in member.roles:
            if role.id in imune_cargos_ids:
                return True
        return False

    async def check_category_immunity(self, category_id: int, imunes_categorias_ids: list):
        return category_id in imunes_categorias_ids

    @commands.Cog.listener("on_guild_channel_create")
    async def on_guild_channel_create_protection(self, channel: disnake.abc.GuildChannel):
        if not channel.guild: return
        db = ObterDatabaseProtecao()
        config = db["canais"]["criar"]
        
        if not config.get("sistema", False): return

        guild = channel.guild
        logs_channel_id = db["canais"].get("logs_channel_id")
        imunes_cargos = config.get("imunes_cargos", [])
        imunes_categorias = config.get("imunes_categorias", [])
        
        await asyncio.sleep(1)
        entry = None
        async for log_entry in guild.audit_logs(limit=1, action=disnake.AuditLogAction.channel_create):
            if log_entry.target.id == channel.id:
                entry = log_entry
                break

        if not entry or not entry.user or entry.user.bot:
            return
        
        member = guild.get_member(entry.user.id)
        if not member: return

        if await self.check_member_immunity(member, imunes_cargos):
            await send_log_embed(self.bot, guild, logs_channel_id, 
                                 f"⚠️ Proteção de Criação de Canal Ignorada",
                                 f"Usuário {member.mention} ({member.id}) criou o canal {channel.mention} mas possui cargo imune.",
                                 disnake.Color.yellow())
            return
        
        if isinstance(channel, disnake.TextChannel) or isinstance(channel, disnake.VoiceChannel):
            if channel.category and await self.check_category_immunity(channel.category.id, imunes_categorias):
                await send_log_embed(self.bot, guild, logs_channel_id,
                                     f"⚠️ Proteção de Criação de Canal Ignorada",
                                     f"Canal {channel.mention} ({channel.id}) criado na categoria imune {channel.category.name}.",
                                     disnake.Color.yellow())
                return

        add_action_to_monitor(guild.id, member.id, "channel_create", channel.id)
        recent_creates = get_recent_actions(guild.id, member.id, "channel_create", config["tempo_segundos"])

        if len(recent_creates) > config["limite"]:
            action_result = await apply_protection_action(self.bot, guild, member, config["acao"], 
                                                          f"Criou muitos canais ({len(recent_creates)} em {config['tempo_segundos']}s) - Proteção Anti-Raid")
            await send_log_embed(self.bot, guild, logs_channel_id,
                                 f"🚨 Proteção de Criação de Canal Acionada!",
                                 f"Usuário: {member.mention} ({member.id})\nAção: ``{action_result}``\nDetalhes: Criou {len(recent_creates)} canais em {config['tempo_segundos']} segundos.",
                                 disnake.Color.brand_red())
        else:
            await send_log_embed(self.bot, guild, logs_channel_id,
                                 f"📝 Criação de Canal Monitorada",
                                 f"Usuário {member.mention} criou o canal {channel.mention} ({len(recent_creates)} canais em {config['tempo_segundos']}s).",
                                 disnake.Color.dark_teal())

    @commands.Cog.listener("on_guild_channel_update")
    async def on_guild_channel_update_protection(self, before: disnake.abc.GuildChannel, after: disnake.abc.GuildChannel):
        if not after.guild: return
        db = ObterDatabaseProtecao()
        config = db["canais"]["editar"]
        
        if not config.get("sistema", False): return

        guild = after.guild
        logs_channel_id = db["canais"].get("logs_channel_id")
        imunes_cargos = config.get("imunes_cargos", [])
        imunes_categorias = config.get("imunes_categorias", [])

        if before.name != after.name:
            await asyncio.sleep(1) 
            entry = None
            async for log_entry in guild.audit_logs(limit=1, action=disnake.AuditLogAction.channel_update):
                if log_entry.target.id == after.id and log_entry.changes.before.name == before.name:
                    entry = log_entry
                    break
            
            if not entry or not entry.user or entry.user.bot: return
            member = guild.get_member(entry.user.id)
            if not member: return

            if await self.check_member_immunity(member, imunes_cargos): return
            if isinstance(after, (disnake.TextChannel, disnake.VoiceChannel)) and after.category and await self.check_category_immunity(after.category.id, imunes_categorias): return

            add_action_to_monitor(guild.id, member.id, "channel_edit", after.id)
            recent_edits = get_recent_actions(guild.id, member.id, "channel_edit", config["tempo_segundos"])

            if len(recent_edits) > config["limite"]:
                action_result = await apply_protection_action(self.bot, guild, member, config["acao"],
                                                              f"Editou muitos canais ({len(recent_edits)} em {config['tempo_segundos']}s) - Proteção Anti-Raid")
                await send_log_embed(self.bot, guild, logs_channel_id,
                                     f"🚨 Proteção de Edição de Canal Acionada!",
                                     f"Usuário: {member.mention} ({member.id})\nAção: ``{action_result}``\nDetalhes: Editou {len(recent_edits)} canais em {config['tempo_segundos']} segundos.",
                                     disnake.Color.brand_red())
            else:
                await send_log_embed(self.bot, guild, logs_channel_id,
                                     f"📝 Edição de Canal Monitorada",
                                     f"Usuário {member.mention} editou o canal {after.mention} (Nome: {before.name} -> {after.name}).",
                                     disnake.Color.dark_teal())

    @commands.Cog.listener("on_guild_channel_delete")
    async def on_guild_channel_delete_protection(self, channel: disnake.abc.GuildChannel):
        if not channel.guild: return
        db = ObterDatabaseProtecao()
        config = db["canais"]["excluir"]
        
        if not config.get("sistema", False): return

        guild = channel.guild
        logs_channel_id = db["canais"].get("logs_channel_id")
        imunes_cargos = config.get("imunes_cargos", [])
        imunes_categorias = config.get("imunes_categorias", [])

        await asyncio.sleep(1)
        entry = None
        async for log_entry in guild.audit_logs(limit=1, action=disnake.AuditLogAction.channel_delete):
            if log_entry.target.id == channel.id:
                entry = log_entry
                break
        
        if not entry or not entry.user or entry.user.bot: return
        member = guild.get_member(entry.user.id)
        if not member: return

        if await self.check_member_immunity(member, imunes_cargos): return
        if isinstance(channel, (disnake.TextChannel, disnake.VoiceChannel)) and channel.category and await self.check_category_immunity(channel.category.id, imunes_categorias): return

        add_action_to_monitor(guild.id, member.id, "channel_delete", channel.id)
        recent_deletes = get_recent_actions(guild.id, member.id, "channel_delete", config["tempo_segundos"])

        if len(recent_deletes) > config["limite"]:
            action_result = await apply_protection_action(self.bot, guild, member, config["acao"],
                                                          f"Deletou muitos canais ({len(recent_deletes)} em {config['tempo_segundos']}s) - Proteção Anti-Raid")
            await send_log_embed(self.bot, guild, logs_channel_id,
                                 f"🚨 Proteção de Exclusão de Canal Acionada!",
                                 f"Usuário: {member.mention} ({member.id})\nAção: ``{action_result}``\nDetalhes: Deletou {len(recent_deletes)} canais em {config['tempo_segundos']} segundos.",
                                 disnake.Color.brand_red())
        else:
            await send_log_embed(self.bot, guild, logs_channel_id,
                                 f"📝 Exclusão de Canal Monitorada",
                                 f"Usuário {member.mention} deletou o canal {channel.name}.",
                                 disnake.Color.dark_teal())

    @commands.Cog.listener("on_member_ban")
    async def on_member_ban_protection(self, guild: disnake.Guild, user: disnake.User):
        db = ObterDatabaseProtecao()
        config = db["banimento"]
        if not config.get("sistema", False): return

        logs_channel_id = config.get("logs_channel_id")
        imunes_cargos = config.get("imunes_cargos", [])

        await asyncio.sleep(1)
        entry = None
        async for log_entry in guild.audit_logs(limit=1, action=disnake.AuditLogAction.ban):
            if log_entry.target.id == user.id:
                entry = log_entry
                break
        
        if not entry or not entry.user or entry.user.bot: return
        member_agressor = guild.get_member(entry.user.id)
        if not member_agressor: return

        if await self.check_member_immunity(member_agressor, imunes_cargos):
            await send_log_embed(self.bot, guild, logs_channel_id,
                                 f"⚠️ Proteção de Banimento Ignorada",
                                 f"Usuário {member_agressor.mention} ({member_agressor.id}) baniu {user.name} mas possui cargo imune.",
                                 disnake.Color.yellow())
            return

        add_action_to_monitor(guild.id, member_agressor.id, "member_ban", user.id)
        recent_bans = get_recent_actions(guild.id, member_agressor.id, "member_ban", config["tempo_segundos"])

        if len(recent_bans) > config["limite"]:
            reason = f"Baniu muitos membros ({len(recent_bans)} em {config['tempo_segundos']}s) - Proteção Anti-Raid"
            action_result_msg = ""

            if config["acao"] == "reverter":
                for _, banned_user_id in recent_bans:
                    try:
                        banned_user = await self.bot.fetch_user(banned_user_id)
                        await guild.unban(banned_user, reason=f"Revertido por proteção de banimento: {reason}")
                        action_result_msg += f"\n- Desbaniu {banned_user.name}"
                    except Exception as e:
                        action_result_msg += f"\n- Falha ao desbanir {banned_user_id}: {e}"
            else:
                action_result_msg = await apply_protection_action(self.bot, guild, member_agressor, config["acao"], reason)

            await send_log_embed(self.bot, guild, logs_channel_id,
                                 f"🚨 Proteção de Banimento Acionada!",
                                 f"Agressor: {member_agressor.mention} ({member_agressor.id})\nDetalhes: Baniu {len(recent_bans)} membros em {config['tempo_segundos']} segundos.\nAção Tomada: {action_result_msg}",
                                 disnake.Color.brand_red())
        else:
            await send_log_embed(self.bot, guild, logs_channel_id,
                                 f"📝 Banimento Monitorado",
                                 f"Usuário {member_agressor.mention} baniu {user.name}.",
                                 disnake.Color.dark_teal())

    @commands.Cog.listener("on_message")
    async def on_message_mention_protection(self, message: disnake.Message):
        if not message.guild or message.author.bot: return
        db = ObterDatabaseProtecao()
        config = db["mencao"]
        if not config.get("sistema", False): return

        guild = message.guild
        member = message.author
        logs_channel_id = config.get("logs_channel_id")
        imunes_cargos = config.get("imunes_cargos", [])

        if await self.check_member_immunity(member, imunes_cargos): return

        mentions_count = len(message.mentions) + len(message.role_mentions) + len(message.channel_mentions)
        
        if mentions_count > config["limite_mencoes"]:
            add_action_to_monitor(guild.id, member.id, "excessive_mention", message.id)
            recent_mentions_messages = get_recent_actions(guild.id, member.id, "excessive_mention", config["tempo_segundos"])

            if len(recent_mentions_messages) > config["limite"]:
                reason = f"Excedeu limite de menções ({mentions_count} em uma mensagem, ou {len(recent_mentions_messages)} mensagens com menções em {config['tempo_segundos']}s) - Proteção Anti-Raid"
                
                action_result_msg = ""
                if config["acao"] == "timeout":
                    action_result_msg = await apply_protection_action(self.bot, guild, member, "timeout", reason)
                elif config["acao"] == "delete_message":
                    try:
                        await message.delete()
                        action_result_msg = "Mensagem apagada."
                    except Exception as e:
                        action_result_msg = f"Falha ao apagar mensagem: {e}"
                
                await send_log_embed(self.bot, guild, logs_channel_id,
                                     f"🚨 Proteção de Menção Acionada!",
                                     f"Usuário: {member.mention} ({member.id})\nCanal: {message.channel.mention}\nConteúdo: ```{message.content[:100]}```\nTotal de menções: {mentions_count}\n"
                                     f"Ação Tomada: ``{action_result_msg}``",
                                     disnake.Color.brand_red())
            else:
                await send_log_embed(self.bot, guild, logs_channel_id,
                                     f"📝 Menções Monitoradas",
                                     f"Usuário {member.mention} enviou uma mensagem com {mentions_count} menções no canal {message.channel.mention}.",
                                     disnake.Color.dark_teal())

    @commands.Cog.listener("on_guild_add")
    async def on_bot_add_protection(self, guild: disnake.Guild, user: disnake.User):
        if not user.bot: return
        db = ObterDatabaseProtecao()
        config = db["adicionar_bot"]
        if not config.get("sistema", False): return

        logs_channel_id = config.get("logs_channel_id")
        imunes_cargos = config.get("imunes_cargos", [])
        whitelist_bots = config.get("whitelist_bots", [])

        if user.id in whitelist_bots:
            await send_log_embed(self.bot, guild, logs_channel_id,
                                 f"✅ Bot Adicionado (Whitelist)",
                                 f"Bot {user.mention} ({user.id}) foi adicionado e está na whitelist.",
                                 disnake.Color.green())
            return

        await asyncio.sleep(1)
        entry = None
        async for log_entry in guild.audit_logs(limit=1, action=disnake.AuditLogAction.bot_add):
            if log_entry.target.id == user.id:
                entry = log_entry
                break
        
        adicionador = None
        if entry and entry.user:
            adicionador = guild.get_member(entry.user.id)
            if adicionador and await self.check_member_immunity(adicionador, imunes_cargos):
                await send_log_embed(self.bot, guild, logs_channel_id,
                                     f"⚠️ Adição de Bot Ignorada (Usuário Imune)",
                                     f"Bot {user.mention} ({user.id}) adicionado por {adicionador.mention} que possui cargo imune.",
                                     disnake.Color.yellow())
                return
        
        reason = f"Adição de bot não permitido ({user.name})."
        action_result_msg = ""

        if config["acao"] == "ban_adicionador" and adicionador:
            action_result_msg = await apply_protection_action(self.bot, guild, adicionador, "ban", reason)
            await send_log_embed(self.bot, guild, logs_channel_id,
                                 f"🚨 Proteção de Adição de Bot Acionada!",
                                 f"Bot: {user.mention} ({user.id})\nAdicionador: {adicionador.mention if adicionador else 'Desconhecido'}\n"
                                 f"Ação Tomada: ``{action_result_msg}``",
                                 disnake.Color.brand_red())
        elif config["acao"] == "reverter_bot":
            try:
                bot_member = guild.get_member(user.id)
                if bot_member:
                    await bot_member.kick(reason=reason)
                    action_result_msg = f"Bot {user.name} expulso."
                else:
                    action_result_msg = "Bot ainda não é membro, não foi possível expulsar."
            except Exception as e:
                action_result_msg = f"Falha ao reverter adição do bot: {e}"

            await send_log_embed(self.bot, guild, logs_channel_id,
                                 f"🚨 Proteção de Adição de Bot Acionada!",
                                 f"Bot: {user.mention} ({user.id})\nAdicionador: {adicionador.mention if adicionador else 'Desconhecido'}\n"
                                 f"Ação Tomada: ``{action_result_msg}``",
                                 disnake.Color.brand_red())
        else:
            await send_log_embed(self.bot, guild, logs_channel_id,
                                 f"📝 Adição de Bot Monitorada",
                                 f"Bot {user.mention} foi adicionado por {adicionador.mention if adicionador else 'Desconhecido'}.",
                                 disnake.Color.dark_teal())

def setup(bot: commands.Bot):
    bot.add_cog(EventsProtecaoServidor(bot))