import disnake
from disnake.ext import commands, tasks
from disnake import *
import asyncio
import json
from datetime import datetime, timedelta, timezone
import re
from Functions.Config.Repostagem.Vendas import *

def ObterDatabase():
    filepath = "Database/Server/acoesauto.json"
    default_db = {
        "repostagem": {"sistema": False},
        "limpeza": {"sistema": False, "canal": [], "delay": 0},
        "reacoes": {"sistema": False, "canal": [], "emoji": ""},
        "sugestoes": {"sistema": False, "canal": None, "emoji_concordo": "", "emoji_discordo": "", "cor_embed": "0x3498db"},
        "lock_unlock": {"sistema": False, "canal": [], "hora_trancar": "", "hora_destrancar": "", "canais_travados": []},
        "mensagens_content": [],
        "mensagens_embed": [],
        "random_gifs": {
            "sistema": False,
            "canal_icones": None,
            "canal_gifs": None,
            "canal_banners": None,
            "tema": "0x3498db"
        },
        "respostas_automaticas": {"sistema": False, "respostas": []},
        "contador": {"sistema": False, "canal_voz": None, "canal_texto": None, "template_voz": "", "template_texto": ""},
        "invite_tracker": {
            "sistema": False,
            "canal_logs": None,
            "mensagem": {
                "content": None,
                "embed": {},
                "separador": None,
                "separador_custom": None
            },
            "premios": {}
        }
    }
    
    try:
        with open(filepath, "r", encoding='utf-8') as f:
            db = json.load(f)
        
        keys_updated = False
        for key, value in default_db.items():
            if key not in db:
                db[key] = value
                keys_updated = True
            elif isinstance(value, dict):
                 for sub_key, sub_value in value.items():
                     if sub_key not in db.get(key, {}):
                         db[key][sub_key] = sub_value
                         keys_updated = True
                     elif isinstance(sub_value, dict):
                         for sub_sub_key in sub_value:
                             if sub_sub_key not in db.get(key, {}).get(sub_key, {}):
                                 db[key][sub_key][sub_sub_key] = sub_value[sub_sub_key]
                                 keys_updated = True
        
        if keys_updated:
            SalvarDatabase(db)

    except (FileNotFoundError, json.JSONDecodeError):
        db = default_db
        SalvarDatabase(db)
    
    if "limpeza" in db and "delay" in db["limpeza"]:
        try:
            db["limpeza"]["delay"] = int(db["limpeza"]["delay"])
        except (ValueError, TypeError):
            db["limpeza"]["delay"] = 0
    
    return db

def SalvarDatabase(db):
    with open("Database/Server/acoesauto.json", "w", encoding='utf-8') as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

async def acao_repostagem(bot):
    await bot.wait_until_ready()
    while not bot.is_closed():
        db = ObterDatabase()
        repostagem = db.get("repostagem", {})
        if repostagem.get("sistema", False):
            try:
                await RepostagemTodasMensagensVendas(bot)
            except Exception as e:
                print(f"Erro na acao_repostagem: {e}")
        await asyncio.sleep(5 * 60 * 60)

async def acao_limpeza(bot: commands.Bot):
    await bot.wait_until_ready()
    while not bot.is_closed():
        db = ObterDatabase()
        limpeza_config = db.get("limpeza", {})
        if limpeza_config.get("sistema", False):
            canais = [int(c) for c in limpeza_config.get("canal", []) if str(c).isdigit()]
            delay = int(limpeza_config.get("delay", 0))
            
            if delay > 0:
                await asyncio.sleep(delay * 60)
                for canal_id in canais:
                    channel = bot.get_channel(canal_id)
                    if channel:
                        try:
                            await channel.purge(limit=None)
                            print(f"Canal {channel.id} limpo com sucesso")
                        except disnake.Forbidden:
                            print(f"Sem permissão para limpar canal {channel.id}")
                        except Exception as e:
                            print(f"Erro ao limpar canal {channel.id}: {e}")
            else:
                await asyncio.sleep(60)
        else:
            await asyncio.sleep(60)

async def acao_lock_unlock(bot: commands.Bot):
    await bot.wait_until_ready()
    while not bot.is_closed():
        await asyncio.sleep(60)
        try:
            db = ObterDatabase()
            config = db.get("lock_unlock", {})

            if not config.get("sistema", False):
                continue

            hora_trancar = config.get("hora_trancar")
            hora_destrancar = config.get("hora_destrancar")
            canais_configurados = [int(c) for c in config.get("canal", []) if str(c).isdigit()]
            
            agora = datetime.now(timezone(timedelta(hours=-3))).strftime("%H:%M")
            
            for canal_id in canais_configurados:
                channel = bot.get_channel(canal_id)
                if not channel or not isinstance(channel, (disnake.TextChannel, disnake.VoiceChannel, disnake.CategoryChannel)):
                    continue
                
                everyone_role = channel.guild.default_role
                perms = channel.overwrites_for(everyone_role)
                
                try:
                    if agora == hora_trancar and perms.send_messages is not False:
                        perms.send_messages = False
                        await channel.set_permissions(everyone_role, overwrite=perms, reason="Travamento automático")
                        print(f"Canal {canal_id} travado automaticamente.")

                    elif agora == hora_destrancar and perms.send_messages is not True:
                        perms.send_messages = True
                        await channel.set_permissions(everyone_role, overwrite=perms, reason="Destravamento automático")
                        print(f"Canal {canal_id} destravado automaticamente.")

                except Exception as e:
                    print(f"Erro ao trancar/destrancar canal {canal_id}: {e}")

        except Exception as e:
            print(f"Erro no loop de acao_lock_unlock: {e}")

class AutoTasks(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.placeholder = "{contadornever}"
        self.invite_cache = {}
        self.acao_contador.start()

    def cog_unload(self):
        self.acao_contador.cancel()

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if message.author.bot or not message.guild:
            return

        db = ObterDatabase()
        config = db.get("respostas_automaticas", {})

        if not config.get("sistema"):
            return

        conteudo = message.content.lower()
        for item in config.get("respostas", []):
            gatilhos = item.get("gatilhos", [])
            resposta = item.get("resposta", "")
            
            if any(re.search(r'\b' + re.escape(g.lower()) + r'\b', conteudo) for g in gatilhos):
                try:
                    embed = disnake.Embed(
                        description=resposta,
                        color=disnake.Color.blue()
                    )
                    await message.reply(embed=embed)
                    return
                except disnake.Forbidden:
                    print(f"Sem permissão para responder no canal {message.channel.id}")
                except Exception as e:
                    print(f"Erro ao enviar resposta automática: {e}")

    @commands.Cog.listener()
    async def on_member_join(self, member: disnake.Member):
        db = ObterDatabase()
        config = db.get("invite_tracker", {})
        guild = member.guild

        if not config.get("sistema") or not config.get("canal_logs"):
            return

        inviter = None
        was_vanity = False
        
        try:
            invites_before = self.invite_cache.get(guild.id, {})
            invites_after = await guild.invites()
            self.invite_cache[guild.id] = {invite.code: invite.uses for invite in invites_after}

            for invite in invites_after:
                if invite.code in invites_before and invite.uses > invites_before.get(invite.code, 0):
                    inviter = invite.inviter
                    break
            
            if not inviter:
                vanity = await guild.vanity_invite()
                if vanity and vanity.uses > invites_before.get(vanity.code, 0):
                     was_vanity = True
        except Exception as e:
            print(f"Erro ao determinar o convite: {e}")

        log_channel = self.bot.get_channel(config["canal_logs"])
        if not log_channel:
            return

        total_invites = 0
        if inviter:
            total_invites = sum(i.uses for i in invites_after if i.inviter and i.inviter.id == inviter.id)
        
        replacements = {
            "{user}": member.mention, "{user.name}": member.name,
            "{server}": guild.name, "{count}": str(guild.member_count),
            "{inviter}": inviter.mention if inviter else "Não encontrado",
            "{inviter.name}": inviter.name if inviter else "Não encontrado",
            "{invites}": str(total_invites) if inviter else "0",
        }
        if was_vanity:
            replacements["{inviter}"] = "URL Personalizada"
            replacements["{inviter.name}"] = "URL Personalizada"

        msg_config = config.get("mensagem", {})
        content = msg_config.get("content")
        embed_data = msg_config.get("embed", {})

        if content:
            for key, value in replacements.items(): content = content.replace(key, value)
        
        final_embed = None
        if any(embed_data.values()):
            title = embed_data.get("title", "")
            desc = embed_data.get("description", "")
            try: color_val = int(str(embed_data.get("color", "0x3498db")).replace("#", ""), 16)
            except: color_val = 0x3498db
            for key, value in replacements.items():
                title = title.replace(key, value)
                desc = desc.replace(key, value)
            final_embed = disnake.Embed(title=title, description=desc, color=color_val)

        try:
            if content or final_embed:
                await log_channel.send(content=content, embed=final_embed)
        except Exception as e:
            print(f"Erro ao enviar mensagem de invite tracker: {e}")

        separator_links = {
            1: "https://i.imgur.com/2mA3oA8.gif", 2: "https://i.imgur.com/7GolP5A.gif",
            3: "https://i.imgur.com/pYm4a33.gif", 4: "https://i.imgur.com/A6IMp6p.gif",
            5: "https://i.imgur.com/J3a5Y9u.gif"
        }
        separador = msg_config.get("separador")
        separador_url = msg_config.get("separador_custom") if separador == "custom" else separator_links.get(separador)
        
        if separador_url:
            try: await log_channel.send(separador_url)
            except Exception as e: print(f"Erro ao enviar separador: {e}")
            
        if inviter:
            for premio_config in config.get("premios", {}).values():
                if premio_config.get("ativo") and total_invites >= premio_config.get("invites_necessarios", 99999):
                    role_id = int(premio_config.get("premio_id", 0))
                    role = guild.get_role(role_id)
                    if role and role not in inviter.roles:
                        try:
                            await inviter.add_roles(role, reason=f"Atingiu {premio_config['invites_necessarios']} convites")
                        except Exception as e:
                            print(f"Erro ao dar cargo de prêmio: {e}")

    @tasks.loop(minutes=1)
    async def acao_contador(self):
        db = ObterDatabase()
        config = db.get("contador", {})

        if not config.get("sistema") or not self.bot.guilds:
            return

        guild = self.bot.guilds[0]
        member_count = guild.member_count
        db_modificada = False

        canal_voz_id = config.get("canal_voz")
        if canal_voz_id:
            channel = self.bot.get_channel(canal_voz_id)
            if isinstance(channel, disnake.VoiceChannel):
                template_voz = config.get("template_voz", "")
                if not template_voz and self.placeholder in channel.name:
                    template_voz = channel.name
                    db["contador"]["template_voz"] = template_voz
                    db_modificada = True
                if template_voz:
                    novo_nome = template_voz.replace(self.placeholder, str(member_count))
                    if channel.name != novo_nome:
                        try: await channel.edit(name=novo_nome, reason="Contador")
                        except: pass
        
        canal_texto_id = config.get("canal_texto")
        if canal_texto_id:
            channel = self.bot.get_channel(canal_texto_id)
            if isinstance(channel, disnake.TextChannel):
                template_texto = config.get("template_texto", "")
                if not template_texto and channel.topic and self.placeholder in channel.topic:
                    template_texto = channel.topic
                    db["contador"]["template_texto"] = template_texto
                    db_modificada = True
                if template_texto:
                    novo_topico = template_texto.replace(self.placeholder, str(member_count))
                    if channel.topic != novo_topico:
                        try: await channel.edit(topic=novo_topico, reason="Contador")
                        except: pass
        
        if db_modificada:
            SalvarDatabase(db)

    @acao_contador.before_loop
    async def before_acao_contador(self):
        await self.bot.wait_until_ready()
        print("Populando cache de convites...")
        for guild in self.bot.guilds:
            try:
                invites = await guild.invites()
                self.invite_cache[guild.id] = {invite.code: invite.uses for invite in invites}
            except disnake.Forbidden:
                print(f"Sem permissão para ver convites no servidor: {guild.name}")
            except Exception as e:
                print(f"Erro ao popular cache de convites para {guild.name}: {e}")

def setup(bot: commands.Bot):
    bot.add_cog(AutoTasks(bot))
    bot.loop.create_task(acao_repostagem(bot))
    bot.loop.create_task(acao_limpeza(bot))
    bot.loop.create_task(acao_lock_unlock(bot))