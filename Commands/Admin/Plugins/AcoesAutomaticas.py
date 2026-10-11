import disnake
import json
import uuid
from disnake.ext import commands
from disnake import *
from Functions.CarregarEmojis import *
from datetime import datetime

async def show_loading(inter, message="Carregando..."):
    """Helper function to show loading message with Components V2"""
    loading_container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"{carregarAnimado} {message}")
    )
    await inter.response.edit_message(embed=None, components=[loading_container])

async def update_message_v2_safe(inter, embed=None, view=None):
    """Helper function to safely update message with Components V2 compatibility"""
    # Com Components V2, não podemos usar embed junto com view
    # Se view for uma lista de containers, usar components
    # Senão, usar apenas view e ignorar embed
    if isinstance(view, list) and len(view) > 0 and hasattr(view[0], '__class__') and 'Container' in str(view[0].__class__):
        await inter.edit_original_message(embed=None, components=view)
    else:
        await inter.edit_original_message(embed=None, view=view)

class Modals():
    class AlterarLimpezaModal(disnake.ui.Modal):
        def __init__(self):
            db = ObterDatabase()
            limpeza = db["limpeza"]

            components = [
                disnake.ui.TextInput(
                    label="IDs dos canais para limpar (linha)",
                    placeholder="Deixe em branco para desativar. Coloque um ID por linha.",
                    custom_id="idscanais",
                    style=TextInputStyle.long,
                    required=False,
                    value="\n".join(str(c) for c in limpeza.get("canal", []))
                ),
                disnake.ui.TextInput(
                    label="Delay da limpeza",
                    placeholder="Calculado em minutos",
                    custom_id="delay",
                    style=TextInputStyle.short,
                    required=False,
                    value=str(limpeza.get("delay", ""))
                ),
            ]
            super().__init__(title="Configurar Limpeza", components=components)

        async def callback(self, inter: disnake.ModalInteraction):
            loading_container = disnake.ui.Container(
                disnake.ui.TextDisplay(f"{carregarAnimado} Carregando informações...")
            )
            await inter.response.edit_message(embed=None, components=[loading_container])
            canais = inter.text_values["idscanais"]
            delay = inter.text_values["delay"]

            try:
                delay = int(delay) if delay else None
            except ValueError:
                embed, view = PanelsAcoesAuto.ObterPainelLimpeza(inter)
                await update_message_v2_safe(inter, embed, view)
                await inter.followup.send(f"{negativo} Não foi possível transformar o delay em minutos.", ephemeral=True, delete_after=3)
                return
            
            canais_parsed = []
            if canais:
                for canal_str in canais.split("\n"):
                    if canal_str.strip():
                        try:
                            canal_obj = inter.guild.get_channel(int(canal_str.strip()))
                            if canal_obj:
                                canais_parsed.append(canal_obj.id)
                            else:
                                await inter.followup.send(f"{negativo} ID de canal '{canal_str.strip()}' não encontrado no servidor, ignorado.", ephemeral=True, delete_after=3)
                        except ValueError:
                            await inter.followup.send(f"{negativo} ID de canal inválido ignorado: '{canal_str.strip()}'", ephemeral=True, delete_after=3)

            db = ObterDatabase()
            db["limpeza"]["canal"] = canais_parsed
            db["limpeza"]["delay"] = delay

            with open("Database/Server/acoesauto.json", "w") as f:
                json.dump(db, f, indent=4)

            embed, view = PanelsAcoesAuto.ObterPainelLimpeza(inter)
            await update_message_v2_safe(inter, embed, view)
            await inter.followup.send(f"{positivo} Configurações de limpeza salvas!", ephemeral=True, delete_after=3)

    class AlterarReacaoModal(disnake.ui.Modal):
        def __init__(self):
            db = ObterDatabase()
            reacoes = db["reacoes"]

            components = [
                disnake.ui.TextInput(
                    label="IDs dos canais para reações (linha)",
                    placeholder="Deixe em branco para desativar. Coloque um ID por linha.",
                    custom_id="idscanais",
                    style=TextInputStyle.long,
                    required=False,
                    value="\n".join(str(c) for c in reacoes.get("canal", []))
                ),
                disnake.ui.TextInput(
                    label="Emoji da reação",
                    placeholder="🎈 ou <:emoji:123456789101112>",
                    custom_id="emoji",
                    style=TextInputStyle.short,
                    required=False,
                    value=reacoes.get("emoji", "")
                ),
            ]
            super().__init__(title="Configurar Reações Automáticas", components=components)

        async def callback(self, inter: disnake.ModalInteraction):
            loading_container = disnake.ui.Container(
                disnake.ui.TextDisplay(f"{carregarAnimado} Carregando informações...")
            )
            await inter.response.edit_message(embed=None, components=[loading_container])
            
            canais_input = inter.text_values["idscanais"]
            emoji = inter.text_values["emoji"]

            canais_parsed = []
            if canais_input:
                for canal_str in canais_input.split("\n"):
                    if canal_str.strip():
                        try:
                            channel_id = int(canal_str.strip())
                            if inter.guild.get_channel(channel_id):
                                canais_parsed.append(channel_id)
                            else:
                                await inter.followup.send(f"{negativo} Canal ID '{canal_str.strip()}' não encontrado, ignorado.", ephemeral=True, delete_after=3)
                        except ValueError:
                            await inter.followup.send(f"{negativo} ID de canal inválido ignorado: '{canal_str.strip()}'", ephemeral=True, delete_after=3)

            db = ObterDatabase()
            db["reacoes"]["canal"] = canais_parsed
            db["reacoes"]["emoji"] = emoji

            with open("Database/Server/acoesauto.json", "w") as f:
                json.dump(db, f, indent=4)

            embed, view = PanelsAcoesAuto.ObterPainelReacoes(inter)
            await inter.edit_original_message(content=None, embed=embed, view=view)
            await inter.followup.send(f"{positivo} Configurações de reações salvas!", ephemeral=True, delete_after=3)

    class AlterarSugestaoCanalModal(disnake.ui.Modal):
        def __init__(self):
            db = ObterDatabase()
            sugestoes = db["sugestoes"]
            components = [
                disnake.ui.TextInput(
                    label="ID do canal de sugestões",
                    placeholder="Deixe em branco para desativar.",
                    custom_id="idcanal",
                    style=TextInputStyle.short,
                    required=False,
                    value=str(sugestoes.get("canal", "") or "")
                )
            ]
            super().__init__(title="Configurar Canal de Sugestão", components=components)

        async def callback(self, inter: disnake.ModalInteraction):
            loading_container = disnake.ui.Container(
                disnake.ui.TextDisplay(f"{carregarAnimado} Salvando...")
            )
            await inter.response.edit_message(embed=None, components=[loading_container])
            
            canal_id_str = inter.text_values["idcanal"].strip()
            canal_id = None

            if canal_id_str:
                try:
                    canal_obj = inter.guild.get_channel(int(canal_id_str))
                    if canal_obj:
                        canal_id = canal_obj.id
                    else:
                        await inter.followup.send(f"{negativo} ID de canal '{canal_id_str}' não encontrado.", ephemeral=True, delete_after=3)
                except ValueError:
                    await inter.followup.send(f"{negativo} ID de canal inválido: '{canal_id_str}'", ephemeral=True, delete_after=3)
            
            db = ObterDatabase()
            db["sugestoes"]["canal"] = canal_id
            with open("Database/Server/acoesauto.json", "w") as f:
                json.dump(db, f, indent=4)
            
            embed, view = PanelsAcoesAuto.ObterPainelSugestoes(inter)
            await update_message_v2_safe(inter, embed, view)
            await inter.followup.send(f"{positivo} Canal de sugestões salvo!", ephemeral=True, delete_after=3)

    class AlterarSugestaoEmojiModal(disnake.ui.Modal):
        def __init__(self, tipo_emoji: str):
            db = ObterDatabase()
            self.tipo_emoji = tipo_emoji
            emoji_key = f"emoji_{self.tipo_emoji}"
            emoji_atual = db["sugestoes"].get(emoji_key, "")
            
            components = [
                disnake.ui.TextInput(
                    label=f"Emoji de {self.tipo_emoji.capitalize()}",
                    placeholder="🎈 ou <:emoji:123456789101112>",
                    custom_id="emoji",
                    style=TextInputStyle.short,
                    required=False,
                    value=emoji_atual
                )
            ]
            super().__init__(title=f"Configurar Emoji de {self.tipo_emoji.capitalize()}", components=components)

        async def callback(self, inter: disnake.ModalInteraction):
            loading_container = disnake.ui.Container(
                disnake.ui.TextDisplay(f"{carregarAnimado} Salvando...")
            )
            await inter.response.edit_message(embed=None, components=[loading_container])
            
            emoji = inter.text_values["emoji"].strip()
            
            db = ObterDatabase()
            db["sugestoes"][f"emoji_{self.tipo_emoji}"] = emoji
            with open("Database/Server/acoesauto.json", "w") as f:
                json.dump(db, f, indent=4)

            embed, view = PanelsAcoesAuto.ObterPainelSugestoes(inter)
            await update_message_v2_safe(inter, embed, view)
            await inter.followup.send(f"{positivo} Emoji de {self.tipo_emoji} salvo!", ephemeral=True, delete_after=3)

    class AlterarLockUnlockCanalModal(disnake.ui.Modal):
        def __init__(self):
            db = ObterDatabase()
            lock_unlock = db.get("lock_unlock", {})
            components = [
                disnake.ui.TextInput(
                    label="IDs dos canais (separados por linha)",
                    placeholder="Deixe em branco para desativar. Coloque um ID por linha.",
                    custom_id="idscanais",
                    style=TextInputStyle.long,
                    required=False,
                    value="\n".join(str(c) for c in lock_unlock.get("canal", []))
                ),
            ]
            super().__init__(title="Configurar Canais Lock/Unlock", components=components)

        async def callback(self, inter: disnake.ModalInteraction):
            await inter.response.edit_message(f"{carregarAnimado} Salvando...", embed=None, view=None)
            canais_input = inter.text_values["idscanais"]
            canais_parsed = []
            if canais_input:
                for canal_str in canais_input.split("\n"):
                    if canal_str.strip():
                        try:
                            channel_id = int(canal_str.strip())
                            if inter.guild.get_channel(channel_id):
                                canais_parsed.append(channel_id)
                            else:
                                await inter.followup.send(f"{negativo} Canal ID '{canal_str.strip()}' não encontrado.", ephemeral=True, delete_after=3)
                        except ValueError:
                            await inter.followup.send(f"{negativo} ID de canal inválido: '{canal_str.strip()}'", ephemeral=True, delete_after=3)
            
            db = ObterDatabase()
            db["lock_unlock"]["canal"] = canais_parsed
            with open("Database/Server/acoesauto.json", "w") as f:
                json.dump(db, f, indent=4)
            
            embed, view = PanelsAcoesAuto.ObterPainelLockUnlock(inter)
            await inter.edit_original_message(embed=embed, view=view)
            await inter.followup.send(f"{positivo} Canais de Lock/Unlock salvos!", ephemeral=True, delete_after=3)

    class AlterarLockUnlockHorariosModal(disnake.ui.Modal):
        def __init__(self):
            db = ObterDatabase()
            lock_unlock = db.get("lock_unlock", {})
            hora_trancar = lock_unlock.get("hora_trancar", "")
            hora_destrancar = lock_unlock.get("hora_destrancar", "")

            components = [
                disnake.ui.TextInput(
                    label="Hora de Trancar (HH:MM)",
                    placeholder="Ex: 22:00",
                    custom_id="hora_trancar",
                    style=TextInputStyle.short,
                    required=False,
                    value=hora_trancar
                ),
                disnake.ui.TextInput(
                    label="Hora de Destrancar (HH:MM)",
                    placeholder="Ex: 08:00",
                    custom_id="hora_destrancar",
                    style=TextInputStyle.short,
                    required=False,
                    value=hora_destrancar
                ),
            ]
            super().__init__(title="Configurar Horários de Lock/Unlock", components=components)

        async def callback(self, inter: disnake.ModalInteraction):
            await inter.response.edit_message(f"{carregarAnimado} Salvando...", embed=None, view=None)
            hora_trancar = inter.text_values["hora_trancar"].strip()
            hora_destrancar = inter.text_values["hora_destrancar"].strip()

            valid = True
            if hora_trancar:
                try:
                    datetime.strptime(hora_trancar, "%H:%M")
                except ValueError:
                    valid = False
                    await inter.followup.send(f"{negativo} Formato inválido para Hora de Trancar. Use HH:MM.", ephemeral=True, delete_after=5)
            
            if hora_destrancar:
                try:
                    datetime.strptime(hora_destrancar, "%H:%M")
                except ValueError:
                    valid = False
                    await inter.followup.send(f"{negativo} Formato inválido para Hora de Destrancar. Use HH:MM.", ephemeral=True, delete_after=5)

            if not valid:
                embed, view = PanelsAcoesAuto.ObterPainelLockUnlock(inter)
                await inter.edit_original_message(embed=embed, view=view)
                return

            db = ObterDatabase()
            db["lock_unlock"]["hora_trancar"] = hora_trancar
            db["lock_unlock"]["hora_destrancar"] = hora_destrancar

            with open("Database/Server/acoesauto.json", "w") as f:
                json.dump(db, f, indent=4)
            
            embed, view = PanelsAcoesAuto.ObterPainelLockUnlock(inter)
            await inter.edit_original_message(embed=embed, view=view)
            await inter.followup.send(f"{positivo} Horários de Lock/Unlock salvos!", ephemeral=True, delete_after=3)

    class AlterarRandomGifsCanalModal(disnake.ui.Modal):
        def __init__(self, tipo_canal: str):
            self.tipo_canal = tipo_canal
            db = ObterDatabase()
            random_gifs = db.get("random_gifs", {})
            
            components = [
                disnake.ui.TextInput(
                    label=f"ID do canal de {tipo_canal}",
                    placeholder="Deixe em branco para desativar",
                    custom_id="idcanal",
                    style=TextInputStyle.short,
                    required=False,
                    value=str(random_gifs.get(f"canal_{self.tipo_canal}", "") or "")
                )
            ]
            super().__init__(title=f"Configurar Canal de {tipo_canal.capitalize()}", components=components)

        async def callback(self, inter: disnake.ModalInteraction):
            await inter.response.edit_message(f"{carregarAnimado} Salvando...", embed=None, view=None)
            canal_id_str = inter.text_values["idcanal"].strip()
            canal_id = None

            if canal_id_str:
                try:
                    canal_obj = inter.guild.get_channel(int(canal_id_str))
                    if canal_obj:
                        canal_id = canal_obj.id
                    else:
                        await inter.followup.send(f"{negativo} ID de canal '{canal_id_str}' não encontrado.", ephemeral=True, delete_after=3)
                except ValueError:
                    await inter.followup.send(f"{negativo} ID de canal inválido: '{canal_id_str}'", ephemeral=True, delete_after=3)
            
            db = ObterDatabase()
            if "random_gifs" not in db:
                db["random_gifs"] = {}
            db["random_gifs"][f"canal_{self.tipo_canal}"] = canal_id
            
            with open("Database/Server/acoesauto.json", "w") as f:
                json.dump(db, f, indent=4)
            
            embed, view = PanelsAcoesAuto.ObterPainelRandomGifs(inter)
            await inter.edit_original_message(embed=embed, view=view)
            await inter.followup.send(f"{positivo} Canal de {self.tipo_canal} configurado!", ephemeral=True, delete_after=3)

    class ConfigurarRespostasModal(disnake.ui.Modal):
        def __init__(self):
            db = ObterDatabase()
            respostas = db["respostas_automaticas"].get("respostas", [])
            
            texto_respostas = []
            for item in respostas:
                gatilhos = ",".join(item.get("gatilhos", []))
                resposta = item.get("resposta", "")
                texto_respostas.append(f"{gatilhos} | {resposta}")

            components = [
                disnake.ui.TextInput(
                    label="Gatilhos e Respostas",
                    placeholder="Use o formato: palavra1,palavra2 | resposta do bot (uma por linha)",
                    custom_id="respostas_config",
                    style=TextInputStyle.long,
                    required=False,
                    value="\n".join(texto_respostas)
                ),
            ]
            super().__init__(title="Configurar Respostas Automáticas", components=components)

        async def callback(self, inter: disnake.ModalInteraction):
            await inter.response.edit_message(f"{carregarAnimado} Salvando respostas...", embed=None, view=None)
            
            texto_config = inter.text_values["respostas_config"]
            novas_respostas = []
            
            for linha in texto_config.split("\n"):
                if "|" in linha:
                    partes = linha.split("|", 1)
                    gatilhos_str = partes[0].strip()
                    resposta_str = partes[1].strip()
                    
                    if gatilhos_str and resposta_str:
                        gatilhos = [g.strip() for g in gatilhos_str.split(",") if g.strip()]
                        if gatilhos:
                            novas_respostas.append({"gatilhos": gatilhos, "resposta": resposta_str})

            db = ObterDatabase()
            db["respostas_automaticas"]["respostas"] = novas_respostas
            
            with open("Database/Server/acoesauto.json", "w") as f:
                json.dump(db, f, indent=4)

            embed, view = PanelsAcoesAuto.ObterPainelRespostasAutomaticas(inter)
            await inter.edit_original_message(embed=embed, view=view)
            await inter.followup.send(f"{positivo} Respostas automáticas salvas!", ephemeral=True, delete_after=3)

    class AlterarCorSugestaoModal(disnake.ui.Modal):
        def __init__(self):
            db = ObterDatabase()
            sugestoes = db["sugestoes"]
            cor_atual = sugestoes.get("cor_embed", "0x3498db")
            
            components = [
                disnake.ui.TextInput(
                    label="Cor da Embed (Hex)",
                    placeholder="Ex: 0x3498db ou #3498db",
                    custom_id="cor",
                    style=TextInputStyle.short,
                    required=False,
                    value=cor_atual
                )
            ]
            super().__init__(title="Configurar Cor da Sugestão", components=components)

        async def callback(self, inter: disnake.ModalInteraction):
            loading_container = disnake.ui.Container(
                disnake.ui.TextDisplay(f"{carregarAnimado} Salvando...")
            )
            await inter.response.edit_message(embed=None, components=[loading_container])
            
            cor = inter.text_values["cor"].strip()
            
            # Validar formato da cor
            if cor and not (cor.startswith("0x") or cor.startswith("#")):
                cor = f"0x{cor}"
            
            db = ObterDatabase()
            db["sugestoes"]["cor_embed"] = cor or "0x3498db"
            
            with open("Database/Server/acoesauto.json", "w") as f:
                json.dump(db, f, indent=4)

            embed, view = PanelsAcoesAuto.ObterPainelSugestoes(inter)
            await update_message_v2_safe(inter, embed, view)
            await inter.followup.send(f"{positivo} Cor da sugestão salva!", ephemeral=True, delete_after=3)
    
    # --- NOVOS MODAIS PARA INVITE TRACKER ---
    
    class InviteTrackerLogsModal(disnake.ui.Modal):
        def __init__(self):
            db = ObterDatabase()
            config = db.get("invite_tracker", {})
            canal_id = config.get("canal_logs", "")
            
            components = [
                disnake.ui.TextInput(
                    label="ID do Canal de Logs",
                    placeholder="Deixe em branco para desativar.",
                    custom_id="canal_id",
                    style=TextInputStyle.short,
                    required=False,
                    value=str(canal_id or "")
                )
            ]
            super().__init__(title="Definir Canal de Logs", components=components)

        async def callback(self, inter: disnake.ModalInteraction):
            await inter.response.edit_message(f"{carregarAnimado} Salvando...", embed=None, view=None)
            canal_id_str = inter.text_values["canal_id"].strip()
            canal_id = None
            if canal_id_str:
                try:
                    canal_obj = inter.guild.get_channel(int(canal_id_str))
                    if canal_obj and isinstance(canal_obj, disnake.TextChannel):
                        canal_id = canal_obj.id
                    else:
                        # Resposta será enviada no `else` final
                        pass
                except (ValueError, TypeError):
                    pass # Silenciosamente falha se o ID for inválido
            
            db = ObterDatabase()
            db["invite_tracker"]["canal_logs"] = canal_id
            with open("Database/Server/acoesauto.json", "w") as f:
                json.dump(db, f, indent=4)
                
            embed, view = PanelsAcoesAuto.ObterPainelInviteTracker(inter)
            await inter.edit_original_message(embed=embed, view=view)

    class InviteTrackerContentModal(disnake.ui.Modal):
        def __init__(self):
            db = ObterDatabase()
            content = db.get("invite_tracker", {}).get("mensagem", {}).get("content", "")
            components = [
                disnake.ui.TextInput(
                    label="Conteúdo da Mensagem",
                    placeholder="Use as sintaxes disponíveis. Ex: Olá {user}!",
                    custom_id="content",
                    style=TextInputStyle.long,
                    required=False,
                    value=content
                )
            ]
            super().__init__(title="Definir Conteúdo da Mensagem", components=components)

        async def callback(self, inter: disnake.ModalInteraction):
            await inter.response.edit_message(f"{carregarAnimado} Salvando...", embed=None, view=None)
            content = inter.text_values["content"]
            db = ObterDatabase()
            db["invite_tracker"]["mensagem"]["content"] = content
            with open("Database/Server/acoesauto.json", "w") as f:
                json.dump(db, f, indent=4)
            embed, view = PanelsAcoesAuto.ObterPainelMensagemInviteTracker(inter)
            await inter.edit_original_message(embed=embed, view=view)
            
    class InviteTrackerEmbedModal(disnake.ui.Modal):
        def __init__(self):
            db = ObterDatabase()
            embed_data = db.get("invite_tracker", {}).get("mensagem", {}).get("embed", {})
            components = [
                disnake.ui.TextInput(label="Título", custom_id="title", style=TextInputStyle.short, required=False, value=embed_data.get("title")),
                disnake.ui.TextInput(label="Descrição", custom_id="description", style=TextInputStyle.long, required=False, value=embed_data.get("description")),
                disnake.ui.TextInput(label="Cor (Hex)", custom_id="color", placeholder="Ex: 0x3498db ou #3498db", style=TextInputStyle.short, required=False, value=embed_data.get("color")),
            ]
            super().__init__(title="Definir Embed da Mensagem", components=components)

        async def callback(self, inter: disnake.ModalInteraction):
            await inter.response.edit_message(f"{carregarAnimado} Salvando...", embed=None, view=None)
            db = ObterDatabase()
            db["invite_tracker"]["mensagem"]["embed"] = {
                "title": inter.text_values["title"] or None,
                "description": inter.text_values["description"] or None,
                "color": inter.text_values["color"] or None,
            }
            with open("Database/Server/acoesauto.json", "w") as f:
                json.dump(db, f, indent=4)
            embed, view = PanelsAcoesAuto.ObterPainelMensagemInviteTracker(inter)
            await inter.edit_original_message(embed=embed, view=view)

    class InviteTrackerSeparadorCustomModal(disnake.ui.Modal):
        def __init__(self):
            db = ObterDatabase()
            link = db.get("invite_tracker", {}).get("mensagem", {}).get("separador_custom", "")
            components = [
                disnake.ui.TextInput(
                    label="URL do Separador Customizado",
                    placeholder="https://i.imgur.com/example.gif",
                    custom_id="link",
                    style=TextInputStyle.short,
                    required=True,
                    value=link
                )
            ]
            super().__init__(title="Definir Separador Customizado", components=components)
        
        async def callback(self, inter: disnake.ModalInteraction):
            await inter.response.edit_message(f"{carregarAnimado} Salvando...", embed=None, view=None)
            link = inter.text_values["link"].strip()

            if not (link.startswith("http://") or link.startswith("https://")):
                # Não envia mensagem, apenas não salva e recarrega o painel
                embed, view = PanelsAcoesAuto.ObterPainelSeparadorInviteTracker(inter)
                await inter.edit_original_message(embed=embed, view=view)
                return

            db = ObterDatabase()
            db["invite_tracker"]["mensagem"]["separador"] = "custom"
            db["invite_tracker"]["mensagem"]["separador_custom"] = link
            with open("Database/Server/acoesauto.json", "w") as f:
                json.dump(db, f, indent=4)
                
            embed, view = PanelsAcoesAuto.ObterPainelSeparadorInviteTracker(inter)
            await inter.edit_original_message(embed=embed, view=view)
            
    class InviteTrackerPremioInvitesModal(disnake.ui.Modal):
        def __init__(self, premio_id: str):
            self.premio_id = premio_id
            db = ObterDatabase()
            premio = db["invite_tracker"]["premios"][premio_id]
            
            components = [
                disnake.ui.TextInput(
                    label="Invites Necessários",
                    placeholder="Ex: 10",
                    custom_id="invites",
                    style=TextInputStyle.short,
                    required=True,
                    value=str(premio.get("invites_necessarios", ""))
                )
            ]
            super().__init__(title="Definir Invites", components=components)

        async def callback(self, inter: disnake.ModalInteraction):
            await inter.response.edit_message(f"{carregarAnimado} Salvando...", embed=None, view=None)
            try:
                invites = int(inter.text_values["invites"])
                db = ObterDatabase()
                db["invite_tracker"]["premios"][self.premio_id]["invites_necessarios"] = invites
                with open("Database/Server/acoesauto.json", "w") as f:
                    json.dump(db, f, indent=4)
            except ValueError:
                pass # Silenciosamente ignora se não for um número

            embed, view = PanelsAcoesAuto.ObterPainelPremioEspecifico(inter, self.premio_id)
            await inter.edit_original_message(embed=embed, view=view)
            
    class InviteTrackerPremioDetalhesModal(disnake.ui.Modal):
        def __init__(self, premio_id: str):
            self.premio_id = premio_id
            db = ObterDatabase()
            premio = db["invite_tracker"]["premios"][premio_id]

            components = [
                disnake.ui.TextInput(
                    label="Prêmio (ID do Cargo)",
                    placeholder="Coloque o ID do cargo a ser entregue.",
                    custom_id="premio",
                    style=TextInputStyle.short,
                    required=True,
                    value=str(premio.get("premio_id", ""))
                )
            ]
            super().__init__(title="Configurar Prêmio", components=components)

        async def callback(self, inter: disnake.ModalInteraction):
            await inter.response.edit_message(f"{carregarAnimado} Salvando...", embed=None, view=None)
            premio_id_str = inter.text_values["premio"]
            
            try:
                # Apenas verifica se é um número, a validação de existência do cargo seria em outro local
                int(premio_id_str) 
                db = ObterDatabase()
                db["invite_tracker"]["premios"][self.premio_id]["premio_id"] = premio_id_str
                with open("Database/Server/acoesauto.json", "w") as f:
                    json.dump(db, f, indent=4)
            except ValueError:
                 pass # Silenciosamente ignora se não for um ID válido
                 
            embed, view = PanelsAcoesAuto.ObterPainelPremioEspecifico(inter, self.premio_id)
            await inter.edit_original_message(embed=embed, view=view)


def ObterDatabase():
    default_db = {
        "repostagem": {"sistema": False},
        "limpeza": {"sistema": False, "canal": [], "delay": 0},
        "reacoes": {"sistema": False, "canal": [], "emoji": ""},
        "sugestoes": {"sistema": False, "canal": None, "emoji_concordo": "", "emoji_discordo": "", "cor_embed": "0x3498db"},
        "lock_unlock": {"sistema": False, "canal": [], "hora_trancar": "", "hora_destrancar": ""},
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
        with open("Database/Server/acoesauto.json", "r") as f:
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
            with open("Database/Server/acoesauto.json", "w") as f:
                json.dump(db, f, indent=4)
        
        return db

    except (FileNotFoundError, json.JSONDecodeError):
        with open("Database/Server/acoesauto.json", "w") as f:
            json.dump(default_db, f, indent=4)
        return default_db

class PanelsAcoesAuto():
    @staticmethod
    def ObterPainelRepostagem(inter: disnake.MessageInteraction):
        db = ObterDatabase()
        repostagem = db.get("repostagem", {})
        sistema = repostagem.get("sistema", False)
        
        sistemaText = f"{positivo} Habilitado" if sistema else f"{negativo} Desabilitado"
        Button = {"Label": "Desabilitar" if sistema else "Habilitar", "Style": disnake.ButtonStyle.red if sistema else disnake.ButtonStyle.green}
        
        container_elems = [
            disnake.ui.TextDisplay("# 🔄 Repostagem | Ações Automáticas"),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay("Seu bot NeverPro vai repostar seus produtos periodicamente (a cada 3 horas), apagando a mensagem antiga e enviando-a novamente."),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(f"**Sistema:** {sistemaText}"),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(
                disnake.ui.Button(label=Button["Label"], style=Button["Style"], emoji=reload, custom_id="AtivarDesativarSistemaAcoesAuto_repostagem"),
                disnake.ui.Button(label="Voltar", emoji=voltar, custom_id="GerenciarAcoesAutomaticas")
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(f"-# Servidor: {inter.guild.name}")
        ]
        
        container = disnake.ui.Container(*container_elems)
        return None, [container]

    @staticmethod
    def ObterPainelLimpeza(inter: disnake.MessageInteraction):
        db = ObterDatabase()
        limpeza = db.get("limpeza", {})
        sistema = limpeza.get("sistema", False)
        canal = limpeza.get("canal", [])
        delay = limpeza.get("delay", 0)
        
        canais_formatados = "\n".join(f"<#{c}>" for c in canal) if canal else f"{negativo} Não definido"
        delay_formatted = f"{positivo} {delay} minutos" if delay else f"{negativo} Não definido"
        sistemaText = f"{positivo} Habilitado" if sistema else f"{negativo} Desabilitado"
        Button = {"Label": "Desabilitar" if sistema else "Habilitar", "Style": disnake.ButtonStyle.red if sistema else disnake.ButtonStyle.green}
        
        container_elems = [
            disnake.ui.TextDisplay("# 🧹 Limpeza | Ações Automáticas"),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay("Seu bot NeverPro realizará a limpeza automática das mensagens nos canais selecionados por você, conforme o horário estabelecido."),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(f"**Sistema:** {sistemaText}"),
            disnake.ui.TextDisplay(f"**Delay:** {delay_formatted}"),
            disnake.ui.TextDisplay(f"**Canais:**\n{canais_formatados}"),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(
                disnake.ui.Button(label=Button["Label"], style=Button["Style"], emoji=reload, custom_id="AtivarDesativarSistemaAcoesAuto_limpeza"),
                disnake.ui.Button(label="Configurar", style=disnake.ButtonStyle.blurple, emoji=editar, custom_id="ConfigurarSistemaLimpeza"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=voltar, custom_id="GerenciarAcoesAutomaticas")
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(f"-# Servidor: {inter.guild.name}")
        ]
        
        container = disnake.ui.Container(*container_elems)
        return None, [container]

    @staticmethod
    def ObterPainelReacoes(inter: disnake.MessageInteraction):
        db = ObterDatabase()
        reacoes = db.get("reacoes", {})
        sistema = reacoes.get("sistema", False)
        canal = reacoes.get("canal", [])
        emoji = reacoes.get("emoji", "")
        
        sistemaText = f"{positivo} Habilitado" if sistema else f"{negativo} Desabilitado"
        Button = {"Label": "Desabilitar" if sistema else "Habilitar", "Style": disnake.ButtonStyle.red if sistema else disnake.ButtonStyle.green}
        canais_formatados = "\n".join(f"<#{c}>" for c in canal) if canal else f"{negativo} Não definido"
        emoji_display = f"{emoji}" if emoji else f"{negativo} Não definido"
        
        container_elems = [
            disnake.ui.TextDisplay("# 😀 Reações | Ações Automáticas"),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay("Seu bot NeverPro reagirá a todas mensagens enviadas em um canal definido."),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(f"**Sistema:** {sistemaText}"),
            disnake.ui.TextDisplay(f"**Emoji:** {emoji_display}"),
            disnake.ui.TextDisplay(f"**Canais:**\n{canais_formatados}"),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(
                disnake.ui.Button(label=Button["Label"], style=Button["Style"], emoji=reload, custom_id="AtivarDesativarSistemaAcoesAuto_reacoes"),
                disnake.ui.Button(label="Configurar", style=disnake.ButtonStyle.blurple, emoji=editar, custom_id="ConfigurarSistemaReacoes"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=voltar, custom_id="GerenciarAcoesAutomaticas")
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(f"-# Servidor: {inter.guild.name}")
        ]
        
        container = disnake.ui.Container(*container_elems)
        return None, [container]

    @staticmethod
    def ObterPainelSugestoes(inter: disnake.MessageInteraction):
        db = ObterDatabase()
        sugestoes = db.get("sugestoes", {})
        sistema = sugestoes.get("sistema", False)
        canal = sugestoes.get("canal")
        emoji_concordo = sugestoes.get("emoji_concordo", "")
        emoji_discordo = sugestoes.get("emoji_discordo", "")
        cor_sugestao_salva = sugestoes.get("cor_embed", "0x3498db")

        sistema_text = f"{positivo} Habilitado" if sistema else f"{negativo} Desabilitado"
        button_toggle = {"Label": "Desabilitar" if sistema else "Habilitar", "Style": disnake.ButtonStyle.red if sistema else disnake.ButtonStyle.green}
        canal_text = f"<#{canal}>" if canal else f"{negativo} Não definido"
        concordo_text = emoji_concordo if emoji_concordo else f"{negativo} Não definido"
        discordo_text = emoji_discordo if emoji_discordo else f"{negativo} Não definido"
        cor_text = f"{cor_sugestao_salva}"
        
        container_elems = [
            disnake.ui.TextDisplay("# 💡 Sugestões | Ações Automáticas"),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay("Configure o sistema de sugestões do seu bot NeverPro. A cor configurada será usada nos embeds enviados pelo bot no canal de sugestão."),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(f"**Sistema:** {sistema_text}"),
            disnake.ui.TextDisplay(f"**Canal:** {canal_text}"),
            disnake.ui.TextDisplay(f"**Cor da Sugestão:** {cor_text}"),
            disnake.ui.TextDisplay(f"**Emoji Concordo:** {concordo_text}"),
            disnake.ui.TextDisplay(f"**Emoji Discordo:** {discordo_text}"),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(
                disnake.ui.Button(label=button_toggle["Label"], style=button_toggle["Style"], emoji=reload, custom_id="AtivarDesativarSistemaAcoesAuto_sugestoes"),
                disnake.ui.Button(label="Selecionar Canal", style=disnake.ButtonStyle.blurple, emoji=editar, custom_id="ConfigurarSistemaSugestoes_Canal"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Cor da Sugestão", style=disnake.ButtonStyle.blurple, custom_id="ConfigurarSistemaSugestoes_Cor"),
                disnake.ui.Button(label="Emoji Concordo", style=disnake.ButtonStyle.blurple, custom_id="ConfigurarSistemaSugestoes_Concordo"),
                disnake.ui.Button(label="Emoji Discordo", style=disnake.ButtonStyle.blurple, custom_id="ConfigurarSistemaSugestoes_Discordo"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=voltar, custom_id="GerenciarAcoesAutomaticas")
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(f"-# Servidor: {inter.guild.name}")
        ]
        
        container = disnake.ui.Container(*container_elems)
        return None, [container]

    @staticmethod
    def ObterPainelLockUnlock(inter: disnake.MessageInteraction):
        db = ObterDatabase()
        lock_unlock = db.get("lock_unlock", {})
        sistema = lock_unlock.get("sistema", False)
        canais = lock_unlock.get("canal", [])
        hora_trancar = lock_unlock.get("hora_trancar", "")
        hora_destrancar = lock_unlock.get("hora_destrancar", "")

        sistema_text = f"{positivo} Habilitado" if sistema else f"{negativo} Desabilitado"
        button_toggle = {"Label": "Desabilitar" if sistema else "Habilitar", "Style": disnake.ButtonStyle.red if sistema else disnake.ButtonStyle.green}
        canais_text = "\n".join(f"<#{c}>" for c in canais) if canais else f"{negativo} Não definido"
        trancar_text = f"{positivo} {hora_trancar}" if hora_trancar else f"{negativo} Não definido"
        destrancar_text = f"{positivo} {hora_destrancar}" if hora_destrancar else f"{negativo} Não definido"

        container_elems = [
            disnake.ui.TextDisplay("# 🔒 Lock/Unlock | Ações Automáticas"),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay("Seu bot NeverPro vai trancar e destrancar automaticamente os canais em horários específicos."),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(f"**Sistema:** {sistema_text}"),
            disnake.ui.TextDisplay(f"**Hora de Trancar:** {trancar_text}"),
            disnake.ui.TextDisplay(f"**Hora de Destrancar:** {destrancar_text}"),
            disnake.ui.TextDisplay(f"**Canais:**\n{canais_text}"),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(
                disnake.ui.Button(label=button_toggle["Label"], style=button_toggle["Style"], emoji=reload, custom_id="AtivarDesativarSistemaAcoesAuto_lock_unlock"),
                disnake.ui.Button(label="Configurar Canais", style=disnake.ButtonStyle.blurple, emoji=editar, custom_id="ConfigurarSistemaLockUnlock_Canal"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Configurar Horários", emoji=clock, style=disnake.ButtonStyle.blurple, custom_id="ConfigurarSistemaLockUnlock_Horarios"),
                disnake.ui.Button(label="Voltar", emoji=voltar, custom_id="GerenciarAcoesAutomaticas")
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(f"-# Servidor: {inter.guild.name}")
        ]
        
        container = disnake.ui.Container(*container_elems)
        return None, [container]

    @staticmethod
    def ObterPainelRandomGifs(inter: disnake.MessageInteraction):
        db = ObterDatabase()
        random_gifs = db.get("random_gifs", {})
        sistema = random_gifs.get("sistema", False)
        canal_icones = random_gifs.get("canal_icones")
        canal_gifs = random_gifs.get("canal_gifs")
        canal_banners = random_gifs.get("canal_banners")
        tema = random_gifs.get("tema", "0x3498db")

        sistema_text = f"{positivo} Habilitado" if sistema else f"{negativo} Desabilitado"
        button_toggle = {"Label": "Desabilitar" if sistema else "Habilitar", "Style": disnake.ButtonStyle.red if sistema else disnake.ButtonStyle.green}
        icones_text = f"<#{canal_icones}>" if canal_icones else f"{negativo} Não definido"
        gifs_text = f"<#{canal_gifs}>" if canal_gifs else f"{negativo} Não definido"
        banners_text = f"<#{canal_banners}>" if canal_banners else f"{negativo} Não definido"
        tema_text = f"{tema}"

        container_elems = [
            disnake.ui.TextDisplay("# 🎲 Random Gifs | Ações Automáticas"),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay("Configure o sistema de Random Gifs do seu bot NeverPro. O bot enviará periodicamente gifs, ícones e banners aleatórios nos canais configurados."),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(f"**Sistema:** {sistema_text}"),
            disnake.ui.TextDisplay(f"**Canal de Ícones:** {icones_text}"),
            disnake.ui.TextDisplay(f"**Canal de Gifs:** {gifs_text}"),
            disnake.ui.TextDisplay(f"**Canal de Banners:** {banners_text}"),
            disnake.ui.TextDisplay(f"**Tema:** {tema_text}"),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(
                disnake.ui.Button(label=button_toggle["Label"], style=button_toggle["Style"], emoji=reload, custom_id="AtivarDesativarRandomGifs"),
                disnake.ui.Button(label="Configurar Tema", style=disnake.ButtonStyle.blurple, custom_id="ConfigurarTemaRandomGifs"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Canal de Ícones", style=disnake.ButtonStyle.blurple, emoji=editar, custom_id="ConfigurarCanalRandomGifs_icones"),
                disnake.ui.Button(label="Canal de Gifs", style=disnake.ButtonStyle.blurple, emoji=editar, custom_id="ConfigurarCanalRandomGifs_gifs"),
                disnake.ui.Button(label="Canal de Banners", style=disnake.ButtonStyle.blurple, emoji=editar, custom_id="ConfigurarCanalRandomGifs_banners"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=voltar, custom_id="GerenciarAcoesAutomaticas")
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(f"-# Servidor: {inter.guild.name}")
        ]
        
        container = disnake.ui.Container(*container_elems)
        return None, [container]

    @staticmethod
    def ObterPainelTemaRandomGifs(inter: disnake.MessageInteraction):
        embed = disnake.Embed(
            title="Selecione um Tema para Random Gifs",
            description="Escolha a cor que será usada nos embeds do sistema de Random Gifs.",
            color=disnake.Color.blue()
        )
        
        options = [
            disnake.SelectOption(label="Preto", value="0x000000"),
            disnake.SelectOption(label="Azul (Padrão)", value="0x3498db"),
            disnake.SelectOption(label="Vermelho", value="0xe74c3c"),
            disnake.SelectOption(label="Verde", value="0x2ecc71"),
            disnake.SelectOption(label="Amarelo", value="0xf1c40f"),
            disnake.SelectOption(label="Roxo", value="0x9b59b6"),
            disnake.SelectOption(label="Laranja", value="0xe67e22"),
            disnake.SelectOption(label="Branco", value="0xffffff"),
        ]
        
        select = disnake.ui.Select(placeholder="Escolha o tema...", options=options, custom_id="SelecionarTemaRandomGifs")
        back_button = disnake.ui.Button(label="Voltar", custom_id="AcessarRandomGifsAcoesAuto", emoji=voltar)
        
        view = disnake.ui.View()
        view.add_item(select)
        view.add_item(back_button)
        
        return embed, view
    
    @staticmethod
    def ObterPainelRespostasAutomaticas(inter: disnake.MessageInteraction):
        db = ObterDatabase()
        config = db.get("respostas_automaticas", {})
        sistema = config.get("sistema", False)
        respostas = config.get("respostas", [])

        sistema_text = f"{positivo} Habilitado" if sistema else f"{negativo} Desabilitado"
        button_toggle = {"Label": "Desabilitar" if sistema else "Habilitar", "Style": disnake.ButtonStyle.red if sistema else disnake.ButtonStyle.green}

        container_elems = [
            disnake.ui.TextDisplay("# 💬 Respostas Automáticas | Ações Automáticas"),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay("O bot NeverPro responderá a mensagens que contenham palavras-chave específicas."),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(f"**Sistema:** {sistema_text}"),
        ]

        if not respostas:
            container_elems.append(disnake.ui.TextDisplay("**Respostas Configuradas:** Nenhuma resposta configurada."))
        else:
            display_text = "**Respostas Configuradas:**\n"
            for i, item in enumerate(respostas[:5]):
                gatilhos = ", ".join(f"`{g}`" for g in item["gatilhos"])
                display_text += f"• **Gatilhos:** {gatilhos}\n  **Resposta:** *{item['resposta'][:50]}...*\n\n"
            if len(respostas) > 5:
                display_text += f"*... e mais {len(respostas) - 5} respostas.*"
            container_elems.append(disnake.ui.TextDisplay(display_text))

        container_elems.extend([
            disnake.ui.Separator(),
            disnake.ui.ActionRow(
                disnake.ui.Button(label=button_toggle["Label"], style=button_toggle["Style"], emoji=reload, custom_id="AtivarDesativarSistemaAcoesAuto_respostas_automaticas"),
                disnake.ui.Button(label="Editar Respostas", style=disnake.ButtonStyle.blurple, emoji=editar, custom_id="ConfigurarSistemaRespostas"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=voltar, custom_id="GerenciarAcoesAutomaticas")
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(f"-# Servidor: {inter.guild.name}")
        ])

        container = disnake.ui.Container(*container_elems)
        return None, [container]

    @staticmethod
    def ObterPainelContador(inter: disnake.MessageInteraction):
        db = ObterDatabase()
        config = db.get("contador", {})
        sistema = config.get("sistema", False)
        canal_voz_id = config.get("canal_voz")
        canal_texto_id = config.get("canal_texto")

        sistema_text = f"{positivo} Habilitado" if sistema else f"{negativo} Desabilitado"
        button_toggle = {"Label": "Desabilitar" if sistema else "Habilitar", "Style": disnake.ButtonStyle.red if sistema else disnake.ButtonStyle.green}
        
        canal_voz_text = f"<#{canal_voz_id}>" if canal_voz_id else f"{negativo} Não definido"
        canal_texto_text = f"<#{canal_texto_id}>" if canal_texto_id else f"{negativo} Não definido"

        container_elems = [
            disnake.ui.TextDisplay("# 📊 Contador de Membros | Ações Automáticas"),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay("Atualiza o nome de um canal de voz e/ou o tópico de um canal de texto com a contagem de membros do servidor."),
            disnake.ui.TextDisplay("Para funcionar, o nome/tópico do canal deve conter `{contadornever}`."),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(f"**Sistema:** {sistema_text}"),
            disnake.ui.TextDisplay(f"**Canal de Voz:** {canal_voz_text}"),
            disnake.ui.TextDisplay(f"**Canal de Texto:** {canal_texto_text}"),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(
                disnake.ui.Button(label=button_toggle["Label"], style=button_toggle["Style"], emoji=reload, custom_id="AtivarDesativarSistemaAcoesAuto_contador")
            ),
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    custom_id="SelecionarCanalContador_voz",
                    placeholder="Selecionar canal de voz",
                    channel_types=[ChannelType.voice],
                    min_values=0, max_values=1
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    custom_id="SelecionarCanalContador_texto",
                    placeholder="Selecionar canal de texto",
                    channel_types=[ChannelType.text],
                    min_values=0, max_values=1
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=voltar, custom_id="GerenciarAcoesAutomaticas")
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(f"-# Servidor: {inter.guild.name}")
        ]
        
        container = disnake.ui.Container(*container_elems)
        return None, [container]
        
        view.add_item(voice_channel_select)
        view.add_item(text_channel_select)
        view.add_item(disnake.ui.Button(label="Voltar", emoji=voltar, custom_id="GerenciarAcoesAutomaticas", row=3))
        return embed, view

    # --- NOVOS PAINEIS PARA INVITE TRACKER ---

    @staticmethod
    def ObterPainelInviteTracker(inter: disnake.MessageInteraction):
        db = ObterDatabase()
        config = db.get("invite_tracker", {})
        sistema = config.get("sistema", False)
        canal_logs = config.get("canal_logs")
        
        sistema_text = f"{positivo} ``Habilitado``" if sistema else f"{negativo} ``Desabilitado``"
        button_toggle = {"Label": "Desabilitar" if sistema else "Habilitar", "Style": disnake.ButtonStyle.red if sistema else disnake.ButtonStyle.green}
        logs_text = f"<#{canal_logs}>" if canal_logs else f"{negativo} ``Não definido``"

        embed = disnake.Embed(
            title="Invite Tracker | Ações Automáticas",
            description="Configure o sistema de boas-vindas e recompensas por convites.",
            timestamp=datetime.now(),
            color=disnake.Color.blue()
        ).set_footer(text=inter.guild.name, icon_url=inter.guild.icon.url if inter.guild.icon else None)
        embed.add_field(name="Sistema", value=sistema_text, inline=True)
        embed.add_field(name="Canal de Logs", value=logs_text, inline=True)
        
        view = disnake.ui.View()
        view.add_item(disnake.ui.Button(label=button_toggle["Label"], style=button_toggle["Style"], emoji=reload, custom_id="AtivarDesativarSistemaAcoesAuto_invite_tracker", row=0))
        view.add_item(disnake.ui.Button(label="Configurar Mensagem", style=disnake.ButtonStyle.blurple, emoji=mensagem, custom_id="ConfigurarMensagemInviteTracker", row=1))
        view.add_item(disnake.ui.Button(label="Definir Logs", style=disnake.ButtonStyle.blurple, emoji=editar, custom_id="DefinirLogsInviteTracker", row=1))
        view.add_item(disnake.ui.Button(label="Definir Prêmios", style=disnake.ButtonStyle.blurple, emoji="🏆", custom_id="DefinirPremiosInviteTracker", row=1))
        view.add_item(disnake.ui.Button(label="Voltar", emoji=voltar, custom_id="GerenciarAcoesAutomaticas", row=2))
        return embed, view

    @staticmethod
    def ObterPainelMensagemInviteTracker(inter: disnake.MessageInteraction):
        db = ObterDatabase()
        msg_config = db.get("invite_tracker", {}).get("mensagem", {})
        
        has_content = bool(msg_config.get("content"))
        has_embed = any(msg_config.get("embed", {}).values())
        has_separator = bool(msg_config.get("separador"))
        
        embed = disnake.Embed(
            title="Configurar Mensagem | Invite Tracker",
            description="Defina o conteúdo, embed e separador da mensagem de boas-vindas.",
            color=disnake.Color.blue()
        )
        
        view = disnake.ui.View()
        view.add_item(disnake.ui.Button(label="Definir Content", style=disnake.ButtonStyle.green, custom_id="DefinirContentInviteTracker", row=0))
        view.add_item(disnake.ui.Button(label="Limpar Content", style=disnake.ButtonStyle.red, custom_id="LimparContentInviteTracker", row=0, disabled=not has_content))
        view.add_item(disnake.ui.Button(label="Definir Embed", style=disnake.ButtonStyle.green, custom_id="DefinirEmbedInviteTracker", row=1))
        view.add_item(disnake.ui.Button(label="Limpar Embed", style=disnake.ButtonStyle.red, custom_id="LimparEmbedInviteTracker", row=1, disabled=not has_embed))
        view.add_item(disnake.ui.Button(label="Definir Separador", style=disnake.ButtonStyle.green, custom_id="DefinirSeparadorInviteTracker", row=2))
        view.add_item(disnake.ui.Button(label="Limpar Separador", style=disnake.ButtonStyle.red, custom_id="LimparSeparadorInviteTracker", row=2, disabled=not has_separator))
        view.add_item(disnake.ui.Button(label="Exibir Syntax", style=disnake.ButtonStyle.blurple, emoji="✨", custom_id="ExibirSyntaxInviteTracker", row=3))
        view.add_item(disnake.ui.Button(label="Voltar", emoji=voltar, custom_id="AcessarInviteTrackerAcoesAuto", row=3))
        
        return embed, view

    @staticmethod
    def ObterPainelSeparadorInviteTracker(inter: disnake.MessageInteraction):
        embed = disnake.Embed(
            title="Definir Separador | Invite Tracker",
            description="Escolha um dos separadores predefinidos, ou envie um customizado.",
            color=disnake.Color.blue()
        )
        view = disnake.ui.View()
        # Row 1: Números
        for i in range(1, 6):
            view.add_item(disnake.ui.Button(label=str(i), style=disnake.ButtonStyle.secondary, custom_id=f"SetSeparadorInviteTracker_{i}", row=0))
        # Row 2: Previews
        for i in range(1, 6):
            view.add_item(disnake.ui.Button(label="Preview", emoji="👁️", style=disnake.ButtonStyle.blurple, custom_id=f"PreviewSeparadorInviteTracker_{i}", row=1))
        # Row 3: Ações
        view.add_item(disnake.ui.Button(label="Customizado", style=disnake.ButtonStyle.green, custom_id="CustomSeparadorInviteTracker", row=2))
        view.add_item(disnake.ui.Button(label="Voltar", emoji=voltar, custom_id="ConfigurarMensagemInviteTracker", row=2))

        return embed, view

    @staticmethod
    def ObterPainelPremiosInviteTracker(inter: disnake.MessageInteraction):
        db = ObterDatabase()
        premios = db.get("invite_tracker", {}).get("premios", {})

        embed = disnake.Embed(
            title="Definir Prêmios | Invite Tracker",
            description="Crie e gerencie as recompensas por convites.",
            color=disnake.Color.blue()
        )
        view = disnake.ui.View()

        if premios:
            options = []
            for premio_id, config in premios.items():
                invites = config.get('invites_necessarios', '?')
                premio = config.get('premio_id', 'Não definido')
                status = "Ativo" if config.get("ativo") else "Inativo"
                options.append(disnake.SelectOption(
                    label=f"{invites} invites - {status}",
                    description=f"Prêmio: Cargo ID {premio}",
                    value=premio_id
                ))
            
            select = disnake.ui.Select(
                placeholder="Selecione uma configuração para editar...",
                options=options,
                custom_id="SelecionarPremioInviteTracker"
            )
            view.add_item(select)
        
        view.add_item(disnake.ui.Button(label="Criar Configuração", style=disnake.ButtonStyle.green, emoji="➕", custom_id="CriarPremioInviteTracker", row=1))
        view.add_item(disnake.ui.Button(label="Voltar", emoji=voltar, custom_id="AcessarInviteTrackerAcoesAuto", row=1))
        
        return embed, view

    @staticmethod
    def ObterPainelPremioEspecifico(inter: disnake.MessageInteraction, premio_id: str):
        db = ObterDatabase()
        premio = db["invite_tracker"]["premios"].get(premio_id)
        
        if not premio:
             return PanelsAcoesAuto.ObterPainelPremiosInviteTracker(inter)

        ativo = premio.get("ativo", False)
        invites = premio.get("invites_necessarios", "N/A")
        premio_cargo = premio.get("premio_id", "N/A")

        status_text = f"{positivo} ``Ativado``" if ativo else f"{negativo} ``Desativado``"
        button_toggle = {"Label": "Desativar" if ativo else "Ativar", "Style": disnake.ButtonStyle.red if ativo else disnake.ButtonStyle.green}

        embed = disnake.Embed(
            title=f"Configurando Prêmio ({invites} invites)",
            description="Gerencie os detalhes desta recompensa.",
            color=disnake.Color.blue()
        )
        embed.add_field(name="Status", value=status_text)
        embed.add_field(name="Invites Necessários", value=f"``{invites}``")
        embed.add_field(name="Prêmio (ID do Cargo)", value=f"``{premio_cargo}``")

        view = disnake.ui.View()
        view.add_item(disnake.ui.Button(label=button_toggle["Label"], style=button_toggle["Style"], custom_id=f"TogglePremioInviteTracker_{premio_id}", row=0))
        view.add_item(disnake.ui.Button(label="Invites Necessários", style=disnake.ButtonStyle.blurple, emoji="🔢", custom_id=f"ConfigurarPremioInvites_{premio_id}", row=1))
        view.add_item(disnake.ui.Button(label="Configurar Prêmio", style=disnake.ButtonStyle.blurple, emoji="🏆", custom_id=f"ConfigurarPremioDetalhes_{premio_id}", row=1))
        view.add_item(disnake.ui.Button(label="Apagar Configuração", style=disnake.ButtonStyle.red, emoji=apagar, custom_id=f"ApagarPremioInviteTracker_{premio_id}", row=2))
        view.add_item(disnake.ui.Button(label="Voltar", emoji=voltar, custom_id="DefinirPremiosInviteTracker", row=2))

        return embed, view

class AcoesAutoCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def AcoesAutoInteractionListener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        if custom_id == "GerenciarAcoesAutomaticas":
            if not self.bot.verificar_permissao(inter.author.id, "panel", "GerenciarAcoesAutomaticas"):
                return await inter.response.send_message(f"{negativo} Você não tem permissão para acessar este painel.", ephemeral=True)
            
            loading_container = disnake.ui.Container(
                disnake.ui.TextDisplay(f"{carregarAnimado} Carregando informações...")
            )
            await inter.response.edit_message(embed=None, components=[loading_container])
            
            container_elems = [
                disnake.ui.TextDisplay("# 🤖 Ações Automáticas"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("Escolha uma ação para configurar"),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Repostagem", emoji=reload, custom_id="AcessarRepostagemAcoesAuto"),
                    disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Limpeza", emoji=apagar, custom_id="AcessarLimpezaAcoesAuto"),
                    disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Reações", emoji=cloud, custom_id="AcessarReacoesAcoesAuto"),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Mensagens Auto", emoji=mensagem, custom_id="AcessarMensagensAcoesAuto"),
                    disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Respostas Auto", emoji="💬", custom_id="AcessarRespostasAutomaticasAcoesAuto"),
                    disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Sugestões", emoji=sugestoes, custom_id="AcessarSugestoesAcoesAuto"),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Lock/Unlock", emoji=cadeado, custom_id="AcessarLockUnlockAcoesAuto"),
                    disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Invite Tracker", emoji="🎉", custom_id="AcessarInviteTrackerAcoesAuto"),
                    disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Contador", emoji=reload, custom_id="AcessarContadorAcoesAuto"),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Random Gifs", emoji="🎲", custom_id="AcessarRandomGifsAcoesAuto"),
                    disnake.ui.Button(label="Voltar", emoji=voltar, custom_id="PainelInicial"),
                )
            ]
            
            container = disnake.ui.Container(*container_elems)
            await inter.edit_original_message(embed=None, components=[container])
        
        elif custom_id == "AcessarRepostagemAcoesAuto":
            loading_container = disnake.ui.Container(
                disnake.ui.TextDisplay(f"{carregarAnimado} Carregando...")
            )
            await inter.response.edit_message(embed=None, components=[loading_container])
            embed, view = PanelsAcoesAuto.ObterPainelRepostagem(inter)
            # Converter embed e view para container se necessário
            if hasattr(view, 'children') and embed:
                container_elems = [
                    disnake.ui.TextDisplay(f"# {embed.title}"),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay(embed.description or ""),
                ]
                # Adicionar campos do embed se existirem
                for field in embed.fields:
                    container_elems.append(disnake.ui.TextDisplay(f"**{field.name}:** {field.value}"))
                
                container_elems.append(disnake.ui.Separator())
                
                # Converter botões da view para ActionRows
                buttons = []
                for child in view.children:
                    if isinstance(child, disnake.ui.Button):
                        buttons.append(child)
                
                # Agrupar botões em ActionRows (máximo 5 por row)
                for i in range(0, len(buttons), 5):
                    row_buttons = buttons[i:i+5]
                    container_elems.append(disnake.ui.ActionRow(*row_buttons))
                
                container = disnake.ui.Container(*container_elems)
                await inter.edit_original_message(embed=None, components=[container])
            else:
                await inter.edit_original_message(embed=embed, view=view)

        elif custom_id == "AcessarLimpezaAcoesAuto":
            loading_container = disnake.ui.Container(
                disnake.ui.TextDisplay(f"{carregarAnimado} Carregando...")
            )
            await inter.response.edit_message(embed=None, components=[loading_container])
            embed, view = PanelsAcoesAuto.ObterPainelLimpeza(inter)
            await update_message_v2_safe(inter, embed, view)

        elif custom_id == "AcessarReacoesAcoesAuto":
            await show_loading(inter, "Carregando...")
            embed, view = PanelsAcoesAuto.ObterPainelReacoes(inter)
            await update_message_v2_safe(inter, embed, view)
        
        elif custom_id == "AcessarSugestoesAcoesAuto":
            await show_loading(inter, "Carregando...")
            embed, view = PanelsAcoesAuto.ObterPainelSugestoes(inter)
            await update_message_v2_safe(inter, embed, view)

        elif custom_id == "AcessarLockUnlockAcoesAuto":
            await show_loading(inter, "Carregando...")
            embed, view = PanelsAcoesAuto.ObterPainelLockUnlock(inter)
            await update_message_v2_safe(inter, embed, view)

        elif custom_id == "AcessarRandomGifsAcoesAuto":
            await show_loading(inter, "Carregando...")
            embed, view = PanelsAcoesAuto.ObterPainelRandomGifs(inter)
            await update_message_v2_safe(inter, embed, view)
            
        elif custom_id == "AcessarRespostasAutomaticasAcoesAuto":
            await show_loading(inter, "Carregando...")
            embed, view = PanelsAcoesAuto.ObterPainelRespostasAutomaticas(inter)
            await update_message_v2_safe(inter, embed, view)

        elif custom_id == "AcessarContadorAcoesAuto":
            await show_loading(inter, "Carregando...")
            embed, view = PanelsAcoesAuto.ObterPainelContador(inter)
            await update_message_v2_safe(inter, embed, view)

        elif custom_id.startswith("AtivarDesativarSistemaAcoesAuto_"):
            loading_container = disnake.ui.Container(
                disnake.ui.TextDisplay(f"{carregarAnimado} Atualizando...")
            )
            await inter.response.edit_message(embed=None, components=[loading_container])
            sistema_tipo = custom_id.replace("AtivarDesativarSistemaAcoesAuto_", "")
            
            db = ObterDatabase()
            if sistema_tipo in db:
                db[sistema_tipo]["sistema"] = not db[sistema_tipo].get("sistema", False)
                with open("Database/Server/acoesauto.json", "w") as f:
                    json.dump(db, f, indent=4)
            
            if sistema_tipo == "repostagem":
                embed, view = PanelsAcoesAuto.ObterPainelRepostagem(inter)
            elif sistema_tipo == "limpeza":
                embed, view = PanelsAcoesAuto.ObterPainelLimpeza(inter)
            elif sistema_tipo == "reacoes":
                embed, view = PanelsAcoesAuto.ObterPainelReacoes(inter)
            elif sistema_tipo == "sugestoes":
                embed, view = PanelsAcoesAuto.ObterPainelSugestoes(inter)
            elif sistema_tipo == "lock_unlock":
                embed, view = PanelsAcoesAuto.ObterPainelLockUnlock(inter)
            elif sistema_tipo == "respostas_automaticas":
                embed, view = PanelsAcoesAuto.ObterPainelRespostasAutomaticas(inter)
            elif sistema_tipo == "contador":
                embed, view = PanelsAcoesAuto.ObterPainelContador(inter)
            elif sistema_tipo == "invite_tracker":
                embed, view = PanelsAcoesAuto.ObterPainelInviteTracker(inter)
            
            await update_message_v2_safe(inter, embed, view)

        elif custom_id == "AtivarDesativarRandomGifs":
            loading_container = disnake.ui.Container(
                disnake.ui.TextDisplay(f"{carregarAnimado} Atualizando...")
            )
            await inter.response.edit_message(embed=None, components=[loading_container])
            db = ObterDatabase()
            db["random_gifs"]["sistema"] = not db["random_gifs"].get("sistema", False)
            
            with open("Database/Server/acoesauto.json", "w") as f:
                json.dump(db, f, indent=4)
            
            embed, view = PanelsAcoesAuto.ObterPainelRandomGifs(inter)
            await update_message_v2_safe(inter, embed, view)

        elif custom_id == "ConfigurarSistemaLimpeza": 
            await inter.response.send_modal(Modals.AlterarLimpezaModal())
        elif custom_id == "ConfigurarSistemaReacoes": 
            await inter.response.send_modal(Modals.AlterarReacaoModal())
        elif custom_id == "ConfigurarSistemaRespostas":
            await inter.response.send_modal(Modals.ConfigurarRespostasModal())

        elif custom_id == "ConfigurarSistemaSugestoes_Canal":
            await inter.response.send_modal(Modals.AlterarSugestaoCanalModal())
        elif custom_id == "ConfigurarSistemaSugestoes_Concordo":
            await inter.response.send_modal(Modals.AlterarSugestaoEmojiModal("concordo"))
        elif custom_id == "ConfigurarSistemaSugestoes_Discordo":
            await inter.response.send_modal(Modals.AlterarSugestaoEmojiModal("discordo"))

        elif custom_id == "ConfigurarSistemaSugestoes_Cor":
            await inter.response.send_modal(Modals.AlterarCorSugestaoModal())

        elif custom_id == "ConfigurarSistemaLockUnlock_Canal":
            await inter.response.send_modal(Modals.AlterarLockUnlockCanalModal())
        elif custom_id == "ConfigurarSistemaLockUnlock_Horarios":
            await inter.response.send_modal(Modals.AlterarLockUnlockHorariosModal())

        elif custom_id.startswith("ConfigurarCanalRandomGifs_"):
            tipo_canal = custom_id.replace("ConfigurarCanalRandomGifs_", "")
            await inter.response.send_modal(Modals.AlterarRandomGifsCanalModal(tipo_canal))
            
        elif custom_id == "ConfigurarTemaRandomGifs":
            await show_loading(inter, "Carregando...")
            embed, view = PanelsAcoesAuto.ObterPainelTemaRandomGifs(inter)
            await update_message_v2_safe(inter, embed, view)

        # --- NOVAS INTERAÇÕES DO INVITE TRACKER ---
        elif custom_id == "AcessarInviteTrackerAcoesAuto":
            await show_loading(inter, "Carregando...")
            embed, view = PanelsAcoesAuto.ObterPainelInviteTracker(inter)
            await update_message_v2_safe(inter, embed, view)

        elif custom_id == "ConfigurarMensagemInviteTracker":
            await show_loading(inter, "Carregando...")
            embed, view = PanelsAcoesAuto.ObterPainelMensagemInviteTracker(inter)
            await inter.edit_original_message(embed=embed, view=view)

        elif custom_id == "DefinirLogsInviteTracker":
            await inter.response.send_modal(Modals.InviteTrackerLogsModal())

        elif custom_id == "DefinirPremiosInviteTracker":
            await show_loading(inter, "Carregando...")
            embed, view = PanelsAcoesAuto.ObterPainelPremiosInviteTracker(inter)
            await update_message_v2_safe(inter, embed, view)

        elif custom_id == "DefinirContentInviteTracker":
            await inter.response.send_modal(Modals.InviteTrackerContentModal())

        elif custom_id == "LimparContentInviteTracker":
            loading_container = disnake.ui.Container(
                disnake.ui.TextDisplay(f"{carregarAnimado} Limpando...")
            )
            await inter.response.edit_message(embed=None, components=[loading_container])
            db = ObterDatabase()
            db["invite_tracker"]["mensagem"]["content"] = None
            with open("Database/Server/acoesauto.json", "w") as f:
                json.dump(db, f, indent=4)
            embed, view = PanelsAcoesAuto.ObterPainelMensagemInviteTracker(inter)
            await update_message_v2_safe(inter, embed, view)

        elif custom_id == "DefinirEmbedInviteTracker":
            await inter.response.send_modal(Modals.InviteTrackerEmbedModal())
            
        elif custom_id == "LimparEmbedInviteTracker":
            loading_container = disnake.ui.Container(
                disnake.ui.TextDisplay(f"{carregarAnimado} Limpando...")
            )
            await inter.response.edit_message(embed=None, components=[loading_container])
            db = ObterDatabase()
            db["invite_tracker"]["mensagem"]["embed"] = {}
            with open("Database/Server/acoesauto.json", "w") as f:
                json.dump(db, f, indent=4)
            embed, view = PanelsAcoesAuto.ObterPainelMensagemInviteTracker(inter)
            await update_message_v2_safe(inter, embed, view)

        elif custom_id == "DefinirSeparadorInviteTracker":
            await show_loading(inter, "Carregando...")
            embed, view = PanelsAcoesAuto.ObterPainelSeparadorInviteTracker(inter)
            await update_message_v2_safe(inter, embed, view)

        elif custom_id == "LimparSeparadorInviteTracker":
            loading_container = disnake.ui.Container(
                disnake.ui.TextDisplay(f"{carregarAnimado} Limpando...")
            )
            await inter.response.edit_message(embed=None, components=[loading_container])
            db = ObterDatabase()
            db["invite_tracker"]["mensagem"]["separador"] = None
            db["invite_tracker"]["mensagem"]["separador_custom"] = None
            with open("Database/Server/acoesauto.json", "w") as f:
                json.dump(db, f, indent=4)
            embed, view = PanelsAcoesAuto.ObterPainelMensagemInviteTracker(inter)
            await update_message_v2_safe(inter, embed, view)

        elif custom_id == "ExibirSyntaxInviteTracker":
            embed = disnake.Embed(title="✨ Sintaxes Disponíveis para o Invite Tracker", color=disnake.Color.gold())
            embed.description = (
                "Você pode usar as seguintes variáveis na mensagem de boas-vindas. Elas serão substituídas automaticamente.\n\n"
                "`{user}` - Menciona o usuário que entrou.\n"
                "`{user.name}` - Nome do usuário.\n"
                "`{inviter}` - Menciona quem convidou.\n"
                "`{inviter.name}` - Nome de quem convidou.\n"
                "`{invites}` - Total de convites de quem convidou.\n"
                "`{server}` - Nome do servidor.\n"
                "`{count}` - Contagem total de membros."
            )
            await inter.send(embed=embed, ephemeral=True)
            # Não edita a mensagem original, apenas envia a efêmera

        elif custom_id.startswith("SetSeparadorInviteTracker_"):
            loading_container = disnake.ui.Container(
                disnake.ui.TextDisplay(f"{carregarAnimado} Salvando...")
            )
            await inter.response.edit_message(embed=None, components=[loading_container])
            num = int(custom_id.split("_")[-1])
            db = ObterDatabase()
            db["invite_tracker"]["mensagem"]["separador"] = num
            db["invite_tracker"]["mensagem"]["separador_custom"] = None
            with open("Database/Server/acoesauto.json", "w") as f:
                json.dump(db, f, indent=4)
            embed, view = PanelsAcoesAuto.ObterPainelSeparadorInviteTracker(inter)
            await update_message_v2_safe(inter, embed, view)

        elif custom_id.startswith("PreviewSeparadorInviteTracker_"):
            num = int(custom_id.split("_")[-1])
            await inter.send(f"Esta é uma pré-visualização para o separador número {num}.", ephemeral=True)

        elif custom_id == "CustomSeparadorInviteTracker":
            await inter.response.send_modal(Modals.InviteTrackerSeparadorCustomModal())

        elif custom_id == "CriarPremioInviteTracker":
            loading_container = disnake.ui.Container(
                disnake.ui.TextDisplay(f"{carregarAnimado} Criando...")
            )
            await inter.response.edit_message(embed=None, components=[loading_container])
            db = ObterDatabase()
            premio_id = uuid.uuid4().hex
            db["invite_tracker"]["premios"][premio_id] = {
                "ativo": False,
                "invites_necessarios": 0,
                "premio_id": None
            }
            with open("Database/Server/acoesauto.json", "w") as f:
                json.dump(db, f, indent=4)
            
            embed, view = PanelsAcoesAuto.ObterPainelPremioEspecifico(inter, premio_id)
            await update_message_v2_safe(inter, embed, view)

        elif custom_id.startswith("TogglePremioInviteTracker_"):
            loading_container = disnake.ui.Container(
                disnake.ui.TextDisplay(f"{carregarAnimado} Atualizando...")
            )
            await inter.response.edit_message(embed=None, components=[loading_container])
            premio_id = custom_id.split("_")[-1]
            db = ObterDatabase()
            db["invite_tracker"]["premios"][premio_id]["ativo"] = not db["invite_tracker"]["premios"][premio_id].get("ativo", False)
            with open("Database/Server/acoesauto.json", "w") as f:
                json.dump(db, f, indent=4)
            embed, view = PanelsAcoesAuto.ObterPainelPremioEspecifico(inter, premio_id)
            await update_message_v2_safe(inter, embed, view)
            
        elif custom_id.startswith("ConfigurarPremioInvites_"):
            premio_id = custom_id.split("_")[-1]
            await inter.response.send_modal(Modals.InviteTrackerPremioInvitesModal(premio_id))

        elif custom_id.startswith("ConfigurarPremioDetalhes_"):
            premio_id = custom_id.split("_")[-1]
            await inter.response.send_modal(Modals.InviteTrackerPremioDetalhesModal(premio_id))

        elif custom_id.startswith("ApagarPremioInviteTracker_"):
            loading_container = disnake.ui.Container(
                disnake.ui.TextDisplay(f"{carregarAnimado} Apagando...")
            )
            await inter.response.edit_message(embed=None, components=[loading_container])
            premio_id = custom_id.split("_")[-1]
            db = ObterDatabase()
            if premio_id in db["invite_tracker"]["premios"]:
                del db["invite_tracker"]["premios"][premio_id]
                with open("Database/Server/acoesauto.json", "w") as f:
                    json.dump(db, f, indent=4)
            embed, view = PanelsAcoesAuto.ObterPainelPremiosInviteTracker(inter)
            await update_message_v2_safe(inter, embed, view)


    @commands.Cog.listener("on_dropdown")
    async def AcoesAutoDropdownListener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        if custom_id == "SelectCorSugestao":
            cor_selecionada = inter.values[0]
            db = ObterDatabase()
            db["sugestoes"]["cor_embed"] = cor_selecionada
            with open("Database/Server/acoesauto.json", "w") as f:
                json.dump(db, f, indent=4)
            
            await inter.response.edit_message(f"{carregarAnimado} Atualizando...", embed=None, view=None)
            embed, view = PanelsAcoesAuto.ObterPainelSugestoes(inter)
            await inter.edit_original_message(embed=embed, view=view)
            await inter.followup.send(f"{positivo} Cor da embed de sugestão alterada!", ephemeral=True, delete_after=3)

        elif custom_id == "SelecionarTemaRandomGifs":
            tema_selecionado = inter.values[0]
            db = ObterDatabase()
            db["random_gifs"]["tema"] = tema_selecionado
            
            with open("Database/Server/acoesauto.json", "w") as f:
                json.dump(db, f, indent=4)
            
            await inter.response.edit_message(f"{carregarAnimado} Atualizando...", embed=None, view=None)
            embed, view = PanelsAcoesAuto.ObterPainelRandomGifs(inter)
            await inter.edit_original_message(embed=embed, view=view)
            await inter.followup.send(f"{positivo} Tema do Random Gifs alterado!", ephemeral=True, delete_after=3)

        elif custom_id.startswith("SelecionarCanalContador_"):
            await inter.response.defer()
            tipo_canal = custom_id.replace("SelecionarCanalContador_", "")
            canal_selecionado = inter.values[0] if inter.values else None

            db = ObterDatabase()
            db["contador"][f"canal_{tipo_canal}"] = int(canal_selecionado) if canal_selecionado else None
            db["contador"][f"template_{tipo_canal}"] = ""
            
            with open("Database/Server/acoesauto.json", "w") as f:
                json.dump(db, f, indent=4)
            
            embed, view = PanelsAcoesAuto.ObterPainelContador(inter)
            await inter.edit_original_message(embed=embed, view=view)
            await inter.followup.send(f"{positivo} Canal do contador atualizado!", ephemeral=True, delete_after=3)

        elif custom_id == "SelecionarPremioInviteTracker":
            await show_loading(inter, "Carregando configuração...")
            premio_id = inter.values[0]
            embed, view = PanelsAcoesAuto.ObterPainelPremioEspecifico(inter, premio_id)
            await inter.edit_original_message(content=None, embed=embed, view=view)


def setup(bot: commands.Bot):
    bot.add_cog(AcoesAutoCommand(bot))