import disnake
from disnake.ext import commands, tasks
from datetime import *
import json

from Functions.CarregarEmojis import *

def ObterDatabase():
    with open("Database/Server/canais.json") as f:
        db = json.load(f)
        return db

class EventsOnRegister(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.audit_task.start()
        
    def cog_unload(self):
        self.audit_task.cancel()

    @tasks.loop(seconds=10)
    async def audit_task(self):
        try:
            db = ObterDatabase()
            canal_id = db.get("registroauditoria", {})
            if not canal_id:
                return

            canal = self.bot.get_channel(int(canal_id))
            if not canal:
                return

            guild = self.bot.get_guild(canal.guild.id)
            if not guild:
                return

            try:
                async for entry in guild.audit_logs(limit=1):
                    if entry.created_at > datetime.now(tz=entry.created_at.tzinfo) - timedelta(seconds=10):
                        embed = disnake.Embed(
                            title="Alteração Detectada",
                            description="Este canal foi configurado para registrar alterações no servidor.",
                            timestamp=datetime.now(),
                            color=disnake.Color.orange()
                        )
                        embed.add_field(name="Mudança", value=f"**{entry.action.name.replace('_', ' ').title()}**", inline=False)
                        embed.add_field(name="Quem fez", value=f"{entry.user.mention}", inline=False)
                        embed.set_footer(text=f"ID: {entry.user.id}", icon_url=entry.user.display_avatar.url)

                        await canal.send(embed=embed)
            except Exception as e:
                print(f"Erro ao acessar o registro de auditoria: {e}")
        except: 
            pass

    # EVENTOS DE MEMBROS
    @commands.Cog.listener()
    async def on_member_join(self, member):
        db = ObterDatabase()
        canal_id = db.get("membro_entrou", None)
        if canal_id:
            canal = self.bot.get_channel(int(canal_id))
            if canal:
                embed = disnake.Embed(
                    title="🎉 Membro Entrou",
                    description=f"{member.mention} acabou de entrar no servidor.",
                    color=disnake.Color.green(),
                    timestamp=datetime.now()
                )
                embed.add_field(name="Conta criada em", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
                embed.add_field(name="ID", value=f"`{member.id}`", inline=True)
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.set_footer(text=f"Total de membros: {member.guild.member_count}")
                await canal.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        db = ObterDatabase()
        canal_id = db.get("membro_saiu", None)
        if canal_id:
            canal = self.bot.get_channel(int(canal_id))
            if canal:
                embed = disnake.Embed(
                    title="👋 Membro Saiu",
                    description=f"{member.mention} acabou de sair do servidor.",
                    color=disnake.Color.red(),
                    timestamp=datetime.now()
                )
                embed.add_field(name="Entrou no servidor em", value=f"<t:{int(member.joined_at.timestamp())}:R>", inline=True)
                embed.add_field(name="ID", value=f"`{member.id}`", inline=True)
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.set_footer(text=f"Total de membros: {member.guild.member_count}")
                await canal.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        db = ObterDatabase()
        
        # Nick change
        if before.nick != after.nick:
            canal_id = db.get("nick_change", None)
            if canal_id:
                canal = self.bot.get_channel(int(canal_id))
                if canal:
                    embed = disnake.Embed(
                        title="✏️ Apelido Alterado",
                        color=disnake.Color.blue(),
                        timestamp=datetime.now()
                    )
                    embed.add_field(name="Membro", value=after.mention, inline=False)
                    embed.add_field(name="Antes", value=before.nick or before.name, inline=True)
                    embed.add_field(name="Depois", value=after.nick or after.name, inline=True)
                    embed.set_thumbnail(url=after.display_avatar.url)
                    embed.set_footer(text=f"ID: {after.id}")
                    await canal.send(embed=embed)
        
        # Avatar change
        if before.display_avatar.url != after.display_avatar.url:
            canal_id = db.get("avatar_change", None)
            if canal_id:
                canal = self.bot.get_channel(int(canal_id))
                if canal:
                    embed = disnake.Embed(
                        title="🖼️ Avatar Alterado",
                        description=f"{after.mention} alterou seu avatar.",
                        color=disnake.Color.purple(),
                        timestamp=datetime.now()
                    )
                    embed.set_thumbnail(url=before.display_avatar.url)
                    embed.set_image(url=after.display_avatar.url)
                    embed.set_footer(text=f"ID: {after.id}")
                    await canal.send(embed=embed)
        
        # Role changes
        if before.roles != after.roles:
            added_roles = [r for r in after.roles if r not in before.roles]
            removed_roles = [r for r in before.roles if r not in after.roles]
            
            if added_roles:
                canal_id = db.get("cargo_add", None)
                if canal_id:
                    canal = self.bot.get_channel(int(canal_id))
                    if canal:
                        roles_text = ", ".join([r.mention for r in added_roles])
                        embed = disnake.Embed(
                            title="➕ Cargo Adicionado",
                            description=f"{after.mention} recebeu cargo(s).",
                            color=disnake.Color.green(),
                            timestamp=datetime.now()
                        )
                        embed.add_field(name="Cargo(s)", value=roles_text, inline=False)
                        embed.set_thumbnail(url=after.display_avatar.url)
                        embed.set_footer(text=f"ID: {after.id}")
                        await canal.send(embed=embed)
            
            if removed_roles:
                canal_id = db.get("cargo_remove", None)
                if canal_id:
                    canal = self.bot.get_channel(int(canal_id))
                    if canal:
                        roles_text = ", ".join([r.mention for r in removed_roles])
                        embed = disnake.Embed(
                            title="➖ Cargo Removido",
                            description=f"{after.mention} perdeu cargo(s).",
                            color=disnake.Color.red(),
                            timestamp=datetime.now()
                        )
                        embed.add_field(name="Cargo(s)", value=roles_text, inline=False)
                        embed.set_thumbnail(url=after.display_avatar.url)
                        embed.set_footer(text=f"ID: {after.id}")
                        await canal.send(embed=embed)
        
        # General member update
        canal_id = db.get("membro_update", None)
        if canal_id and (before.nick != after.nick or before.roles != after.roles):
            canal = self.bot.get_channel(int(canal_id))
            if canal:
                changes = []
                if before.nick != after.nick:
                    changes.append(f"**Nick:** `{before.nick or before.name}` → `{after.nick or after.name}`")
                if before.roles != after.roles:
                    changes.append("**Cargos alterados**")
                
                embed = disnake.Embed(
                    title="📝 Membro Atualizado",
                    description=f"{after.mention} teve alterações.",
                    color=disnake.Color.blue(),
                    timestamp=datetime.now()
                )
                embed.add_field(name="Mudanças", value="\n".join(changes), inline=False)
                embed.set_thumbnail(url=after.display_avatar.url)
                embed.set_footer(text=f"ID: {after.id}")
                await canal.send(embed=embed)

    # EVENTOS DE MENSAGENS
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return
            
        db = ObterDatabase()
        canal_id = db.get("mensagem_deletada", None)
        if canal_id:
            canal = self.bot.get_channel(int(canal_id))
            if canal:
                embed = disnake.Embed(
                    title="🗑️ Mensagem Deletada",
                    description=f"Mensagem de {message.author.mention} deletada em {message.channel.mention}",
                    color=disnake.Color.orange(),
                    timestamp=datetime.now()
                )
                if message.content:
                    embed.add_field(name="Conteúdo", value=f"```{message.content[:1000]}```", inline=False)
                if message.attachments:
                    embed.add_field(name="Anexos", value=f"{len(message.attachments)} anexo(s)", inline=True)
                embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
                embed.set_footer(text=f"ID: {message.author.id}")
                await canal.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or before.content == after.content:
            return
            
        db = ObterDatabase()
        canal_id = db.get("mensagem_editada", None)
        if canal_id:
            canal = self.bot.get_channel(int(canal_id))
            if canal:
                embed = disnake.Embed(
                    title="✏️ Mensagem Editada",
                    description=f"Mensagem de {after.author.mention} editada em {after.channel.mention}",
                    color=disnake.Color.blue(),
                    timestamp=datetime.now()
                )
                if before.content:
                    embed.add_field(name="Antes", value=f"```{before.content[:500]}```", inline=False)
                if after.content:
                    embed.add_field(name="Depois", value=f"```{after.content[:500]}```", inline=False)
                embed.add_field(name="Link", value=f"[Ir para mensagem]({after.jump_url})", inline=False)
                embed.set_author(name=after.author.display_name, icon_url=after.author.display_avatar.url)
                embed.set_footer(text=f"ID: {after.author.id}")
                await canal.send(embed=embed)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        db = ObterDatabase()
        canal_id = db.get("mensagem_bulk_delete", None)
        if canal_id:
            canal = self.bot.get_channel(int(canal_id))
            if canal:
                embed = disnake.Embed(
                    title="🗑️ Mensagens Deletadas em Massa",
                    description=f"{len(messages)} mensagens foram deletadas.",
                    color=disnake.Color.red(),
                    timestamp=datetime.now()
                )
                if messages:
                    channel = messages[0].channel
                    embed.add_field(name="Canal", value=channel.mention, inline=True)
                embed.add_field(name="Quantidade", value=f"`{len(messages)}`", inline=True)
                await canal.send(embed=embed)

    # EVENTOS DE REAÇÕES
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
            
        db = ObterDatabase()
        canal_id = db.get("reaction_add", None)
        if canal_id:
            canal = self.bot.get_channel(int(canal_id))
            if canal:
                embed = disnake.Embed(
                    title="👍 Reação Adicionada",
                    description=f"{user.mention} reagiu com {reaction.emoji}",
                    color=disnake.Color.green(),
                    timestamp=datetime.now()
                )
                embed.add_field(name="Canal", value=reaction.message.channel.mention, inline=True)
                embed.add_field(name="Link", value=f"[Ir para mensagem]({reaction.message.jump_url})", inline=True)
                embed.set_thumbnail(url=user.display_avatar.url)
                embed.set_footer(text=f"ID: {user.id}")
                await canal.send(embed=embed)

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        if user.bot:
            return
            
        db = ObterDatabase()
        canal_id = db.get("reaction_remove", None)
        if canal_id:
            canal = self.bot.get_channel(int(canal_id))
            if canal:
                embed = disnake.Embed(
                    title="👎 Reação Removida",
                    description=f"{user.mention} removeu a reação {reaction.emoji}",
                    color=disnake.Color.red(),
                    timestamp=datetime.now()
                )
                embed.add_field(name="Canal", value=reaction.message.channel.mention, inline=True)
                embed.add_field(name="Link", value=f"[Ir para mensagem]({reaction.message.jump_url})", inline=True)
                embed.set_thumbnail(url=user.display_avatar.url)
                embed.set_footer(text=f"ID: {user.id}")
                await canal.send(embed=embed)

    # EVENTOS DE CARGOS
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        db = ObterDatabase()
        canal_id = db.get("cargo_create", None)
        if canal_id:
            canal = self.bot.get_channel(int(canal_id))
            if canal:
                embed = disnake.Embed(
                    title="🎨 Cargo Criado",
                    description=f"Novo cargo criado: {role.mention}",
                    color=role.color,
                    timestamp=datetime.now()
                )
                embed.add_field(name="Nome", value=role.name, inline=True)
                embed.add_field(name="ID", value=f"`{role.id}`", inline=True)
                embed.add_field(name="Cor", value=str(role.color), inline=True)
                embed.set_footer(text=f"Total de cargos: {len(role.guild.roles)}")
                await canal.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        db = ObterDatabase()
        canal_id = db.get("cargo_delete", None)
        if canal_id:
            canal = self.bot.get_channel(int(canal_id))
            if canal:
                embed = disnake.Embed(
                    title="🗑️ Cargo Deletado",
                    description=f"Cargo deletado: **{role.name}**",
                    color=disnake.Color.red(),
                    timestamp=datetime.now()
                )
                embed.add_field(name="ID", value=f"`{role.id}`", inline=True)
                embed.set_footer(text=f"Total de cargos: {len(role.guild.roles)}")
                await canal.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        db = ObterDatabase()
        canal_id = db.get("cargo_update", None)
        if canal_id:
            canal = self.bot.get_channel(int(canal_id))
            if canal:
                changes = []
                if before.name != after.name:
                    changes.append(f"**Nome:** `{before.name}` → `{after.name}`")
                if before.color != after.color:
                    changes.append(f"**Cor:** `{before.color}` → `{after.color}`")
                if before.permissions != after.permissions:
                    changes.append("**Permissões alteradas**")
                if before.mentionable != after.mentionable:
                    changes.append(f"**Mencionável:** `{before.mentionable}` → `{after.mentionable}`")
                
                if changes:
                    embed = disnake.Embed(
                        title="✏️ Cargo Atualizado",
                        description=f"Cargo {after.mention} foi atualizado.",
                        color=after.color,
                        timestamp=datetime.now()
                    )
                    embed.add_field(name="Mudanças", value="\n".join(changes), inline=False)
                    embed.set_footer(text=f"ID: {after.id}")
                    await canal.send(embed=embed)

    # EVENTOS DE CANAIS
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        db = ObterDatabase()
        canal_id = db.get("canal_create", None)
        if canal_id:
            canal_log = self.bot.get_channel(int(canal_id))
            if canal_log:
                embed = disnake.Embed(
                    title="📢 Canal Criado",
                    description=f"Novo canal criado: {channel.mention}",
                    color=disnake.Color.green(),
                    timestamp=datetime.now()
                )
                embed.add_field(name="Nome", value=channel.name, inline=True)
                embed.add_field(name="Tipo", value=str(channel.type), inline=True)
                embed.add_field(name="ID", value=f"`{channel.id}`", inline=True)
                await canal_log.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        db = ObterDatabase()
        canal_id = db.get("canal_delete", None)
        if canal_id:
            canal_log = self.bot.get_channel(int(canal_id))
            if canal_log:
                embed = disnake.Embed(
                    title="🗑️ Canal Deletado",
                    description=f"Canal **{channel.name}** foi deletado.",
                    color=disnake.Color.red(),
                    timestamp=datetime.now()
                )
                embed.add_field(name="Tipo", value=str(channel.type), inline=True)
                embed.add_field(name="ID", value=f"`{channel.id}`", inline=True)
                await canal_log.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        db = ObterDatabase()
        canal_id = db.get("canal_update", None)
        if canal_id:
            canal = self.bot.get_channel(int(canal_id))
            if canal:
                changes = []
                if before.name != after.name:
                    changes.append(f"**Nome:** `{before.name}` → `{after.name}`")
                if hasattr(before, 'topic') and hasattr(after, 'topic') and before.topic != after.topic:
                    changes.append(f"**Tópico alterado**")
                if hasattr(before, 'slowmode_delay') and hasattr(after, 'slowmode_delay') and before.slowmode_delay != after.slowmode_delay:
                    changes.append(f"**Modo lento:** `{before.slowmode_delay}s` → `{after.slowmode_delay}s`")
                
                if changes:
                    embed = disnake.Embed(
                        title="✏️ Canal Atualizado",
                        description=f"Canal {after.mention} foi atualizado.",
                        color=disnake.Color.blue(),
                        timestamp=datetime.now()
                    )
                    embed.add_field(name="Mudanças", value="\n".join(changes), inline=False)
                    embed.set_footer(text=f"ID: {after.id}")
                    await canal.send(embed=embed)

    # EVENTOS DE VOZ
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        db = ObterDatabase()
        
        # Voice join
        if before.channel is None and after.channel is not None:
            canal_id = db.get("voice_join", None)
            if canal_id:
                canal = self.bot.get_channel(int(canal_id))
                if canal:
                    embed = disnake.Embed(
                        title="🔊 Entrou em Canal de Voz",
                        description=f"{member.mention} entrou em {after.channel.mention}",
                        color=disnake.Color.green(),
                        timestamp=datetime.now()
                    )
                    embed.set_thumbnail(url=member.display_avatar.url)
                    embed.set_footer(text=f"ID: {member.id}")
                    await canal.send(embed=embed)
        
        # Voice leave
        elif before.channel is not None and after.channel is None:
            canal_id = db.get("voice_leave", None)
            if canal_id:
                canal = self.bot.get_channel(int(canal_id))
                if canal:
                    embed = disnake.Embed(
                        title="🔇 Saiu de Canal de Voz",
                        description=f"{member.mention} saiu de {before.channel.mention}",
                        color=disnake.Color.red(),
                        timestamp=datetime.now()
                    )
                    embed.set_thumbnail(url=member.display_avatar.url)
                    embed.set_footer(text=f"ID: {member.id}")
                    await canal.send(embed=embed)
        
        # Voice move
        elif before.channel is not None and after.channel is not None and before.channel != after.channel:
            canal_id = db.get("voice_move", None)
            if canal_id:
                canal = self.bot.get_channel(int(canal_id))
                if canal:
                    embed = disnake.Embed(
                        title="🔀 Mudou de Canal de Voz",
                        description=f"{member.mention} mudou de canal.",
                        color=disnake.Color.blue(),
                        timestamp=datetime.now()
                    )
                    embed.add_field(name="De", value=before.channel.mention, inline=True)
                    embed.add_field(name="Para", value=after.channel.mention, inline=True)
                    embed.set_thumbnail(url=member.display_avatar.url)
                    embed.set_footer(text=f"ID: {member.id}")
                    await canal.send(embed=embed)
        
        # Voice mute
        if before.self_mute != after.self_mute or before.mute != after.mute:
            canal_id = db.get("voice_mute", None)
            if canal_id:
                canal = self.bot.get_channel(int(canal_id))
                if canal:
                    muted = after.self_mute or after.mute
                    embed = disnake.Embed(
                        title="🔇 Mute em Voz" if muted else "🔊 Desmutado em Voz",
                        description=f"{member.mention} {'mutou' if muted else 'desmutou'} o microfone.",
                        color=disnake.Color.orange() if muted else disnake.Color.green(),
                        timestamp=datetime.now()
                    )
                    if after.channel:
                        embed.add_field(name="Canal", value=after.channel.mention, inline=True)
                    embed.set_thumbnail(url=member.display_avatar.url)
                    embed.set_footer(text=f"ID: {member.id}")
                    await canal.send(embed=embed)
        
        # Voice deafen
        if before.self_deaf != after.self_deaf or before.deaf != after.deaf:
            canal_id = db.get("voice_deafen", None)
            if canal_id:
                canal = self.bot.get_channel(int(canal_id))
                if canal:
                    deafened = after.self_deaf or after.deaf
                    embed = disnake.Embed(
                        title="🔇 Ensurdecido" if deafened else "🔊 Desensurdecido",
                        description=f"{member.mention} {'ensurdeceu' if deafened else 'desensurdeceu'}.",
                        color=disnake.Color.orange() if deafened else disnake.Color.green(),
                        timestamp=datetime.now()
                    )
                    if after.channel:
                        embed.add_field(name="Canal", value=after.channel.mention, inline=True)
                    embed.set_thumbnail(url=member.display_avatar.url)
                    embed.set_footer(text=f"ID: {member.id}")
                    await canal.send(embed=embed)

    # EVENTOS DE SERVIDOR
    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        db = ObterDatabase()
        canal_id = db.get("server_update", None)
        if canal_id:
            canal = self.bot.get_channel(int(canal_id))
            if canal:
                changes = []
                if before.name != after.name:
                    changes.append(f"**Nome:** `{before.name}` → `{after.name}`")
                if before.icon != after.icon:
                    changes.append("**Ícone alterado**")
                if before.banner != after.banner:
                    changes.append("**Banner alterado**")
                if before.description != after.description:
                    changes.append("**Descrição alterada**")
                
                if changes:
                    embed = disnake.Embed(
                        title="🏠 Servidor Atualizado",
                        description="O servidor foi atualizado.",
                        color=disnake.Color.gold(),
                        timestamp=datetime.now()
                    )
                    embed.add_field(name="Mudanças", value="\n".join(changes), inline=False)
                    if after.icon:
                        embed.set_thumbnail(url=after.icon.url)
                    await canal.send(embed=embed)

    # EVENTOS DE EMOJIS
    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        db = ObterDatabase()
        
        added = [e for e in after if e not in before]
        removed = [e for e in before if e not in after]
        
        if added:
            canal_id = db.get("emoji_create", None)
            if canal_id:
                canal = self.bot.get_channel(int(canal_id))
                if canal:
                    for emoji in added:
                        embed = disnake.Embed(
                            title="😀 Emoji Criado",
                            description=f"Novo emoji adicionado: {emoji}",
                            color=disnake.Color.green(),
                            timestamp=datetime.now()
                        )
                        embed.add_field(name="Nome", value=emoji.name, inline=True)
                        embed.add_field(name="ID", value=f"`{emoji.id}`", inline=True)
                        embed.set_thumbnail(url=emoji.url)
                        await canal.send(embed=embed)
        
        if removed:
            canal_id = db.get("emoji_delete", None)
            if canal_id:
                canal = self.bot.get_channel(int(canal_id))
                if canal:
                    for emoji in removed:
                        embed = disnake.Embed(
                            title="🗑️ Emoji Deletado",
                            description=f"Emoji removido: **{emoji.name}**",
                            color=disnake.Color.red(),
                            timestamp=datetime.now()
                        )
                        embed.add_field(name="ID", value=f"`{emoji.id}`", inline=True)
                        await canal.send(embed=embed)

    # EVENTOS DE CONVITES
    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        db = ObterDatabase()
        canal_id = db.get("invite_create", None)
        if canal_id:
            canal = self.bot.get_channel(int(canal_id))
            if canal:
                embed = disnake.Embed(
                    title="📨 Convite Criado",
                    description=f"Novo convite criado por {invite.inviter.mention}",
                    color=disnake.Color.green(),
                    timestamp=datetime.now()
                )
                embed.add_field(name="Código", value=f"`{invite.code}`", inline=True)
                embed.add_field(name="Canal", value=invite.channel.mention, inline=True)
                embed.add_field(name="Usos máximos", value=invite.max_uses or "Ilimitado", inline=True)
                embed.set_thumbnail(url=invite.inviter.display_avatar.url)
                embed.set_footer(text=f"ID: {invite.inviter.id}")
                await canal.send(embed=embed)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        db = ObterDatabase()
        canal_id = db.get("invite_delete", None)
        if canal_id:
            canal = self.bot.get_channel(int(canal_id))
            if canal:
                embed = disnake.Embed(
                    title="🗑️ Convite Deletado",
                    description=f"Convite deletado.",
                    color=disnake.Color.red(),
                    timestamp=datetime.now()
                )
                embed.add_field(name="Código", value=f"`{invite.code}`", inline=True)
                if invite.channel:
                    embed.add_field(name="Canal", value=invite.channel.mention, inline=True)
                await canal.send(embed=embed)

    # EVENTOS DE MODERAÇÃO
    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        db = ObterDatabase()
        canal_id = db.get("ban", None)
        if canal_id:
            canal = self.bot.get_channel(int(canal_id))
            if canal:
                embed = disnake.Embed(
                    title="🔨 Membro Banido",
                    description=f"{user.mention} foi banido do servidor.",
                    color=disnake.Color.red(),
                    timestamp=datetime.now()
                )
                embed.add_field(name="Nome", value=user.name, inline=True)
                embed.add_field(name="ID", value=f"`{user.id}`", inline=True)
                embed.set_thumbnail(url=user.display_avatar.url)
                await canal.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        db = ObterDatabase()
        canal_id = db.get("unban", None)
        if canal_id:
            canal = self.bot.get_channel(int(canal_id))
            if canal:
                embed = disnake.Embed(
                    title="✅ Membro Desbanido",
                    description=f"{user.mention} foi desbanido do servidor.",
                    color=disnake.Color.green(),
                    timestamp=datetime.now()
                )
                embed.add_field(name="Nome", value=user.name, inline=True)
                embed.add_field(name="ID", value=f"`{user.id}`", inline=True)
                embed.set_thumbnail(url=user.display_avatar.url)
                await canal.send(embed=embed)

    @audit_task.before_loop
    async def before_audit_task(self):
        await self.bot.wait_until_ready()

def setup(bot: commands.Bot):
    bot.add_cog(EventsOnRegister(bot))