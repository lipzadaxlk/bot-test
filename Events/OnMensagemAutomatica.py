import disnake
import json
from disnake.ext import commands

def ObterDatabase():
    filepath = "Database/Server/acoesauto.json"
    try:
        with open(filepath, "r", encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

class OnMensagemAutomatica(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _execute_action(self, inter: disnake.Interaction, action_to_perform: dict):
        action_type = action_to_perform.get("type")
        
        if action_type == "send_message":
            content = action_to_perform.get("content")
            embed_data = action_to_perform.get("embed")
            is_ephemeral = action_to_perform.get("ephemeral", True)
            
            final_embed = None
            if embed_data and any(v for v in embed_data.values() if v is not None):
                final_embed = disnake.Embed.from_dict(embed_data)
                if "color" not in embed_data or embed_data["color"] is None:
                    final_embed.color = 0x2f3136
            
            # Prepara os argumentos da mensagem
            message_kwargs = {"content": content, "ephemeral": is_ephemeral}
            # CORREÇÃO: Adiciona o embed ao dicionário de argumentos apenas se ele não for None.
            if final_embed is not None:
                message_kwargs["embed"] = final_embed

            # Envia a mensagem com os argumentos corretos
            if not inter.response.is_done():
                await inter.response.send_message(**message_kwargs)
            else:
                await inter.followup.send(**message_kwargs)

        elif action_type in ["add_role", "remove_role", "toggle_role"]:
            role_id = action_to_perform.get("role_id")
            if not role_id:
                return await inter.followup.send("❌ Ação de cargo mal configurada (sem ID de cargo).", ephemeral=True)
            
            role = inter.guild.get_role(role_id)
            if not role:
                return await inter.followup.send("❌ O cargo desta ação não existe mais.", ephemeral=True)
            
            member = inter.author
            has_role = role in member.roles
            
            final_action = action_type
            if action_type == "toggle_role":
                final_action = "remove_role" if has_role else "add_role"
            
            try:
                if final_action == "add_role":
                    if not has_role:
                        await member.add_roles(role, reason="Ação de botão automático")
                        await inter.followup.send(f"✅ Cargo {role.mention} adicionado!", ephemeral=True)
                    else:
                        await inter.followup.send(f"ℹ️ Você já possui o cargo {role.mention}.", ephemeral=True)
                elif final_action == "remove_role":
                    if has_role:
                        await member.remove_roles(role, reason="Ação de botão automático")
                        await inter.followup.send(f"✅ Cargo {role.mention} removido!", ephemeral=True)
                    else:
                        await inter.followup.send(f"ℹ️ Você não possui o cargo {role.mention}.", ephemeral=True)
            except disnake.Forbidden:
                await inter.followup.send(f"❌ Não tenho permissão para gerenciar o cargo {role.mention}. Verifique minhas permissões e a hierarquia de cargos.", ephemeral=True)


    @commands.Cog.listener("on_button_click")
    async def on_auto_message_button_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        if not custom_id.startswith("ma:b:"):
            return

        try:
            *_, msg_id, btn_id = custom_id.split(":")
        except ValueError:
            return

        db = ObterDatabase()
        msg_config = next((m for m in db.get("mensagens_automaticas", []) if m.get("id") == msg_id), None)
        if not msg_config: return

        btn_config = next((b for b in msg_config.get("buttons", []) if b.get("id") == btn_id), None)
        if not btn_config or not btn_config.get("action"):
            if not inter.response.is_done():
                 await inter.response.send_message("❌ Ação para este botão não foi encontrada ou foi removida.", ephemeral=True)
            return
        
        action = btn_config["action"]

        if action.get("type") == "send_message" and action.get("ephemeral", True):
            await self._execute_action(inter, action)
            return

        await inter.response.defer(ephemeral=True)
        await self._execute_action(inter, action)


    @commands.Cog.listener("on_dropdown")
    async def on_auto_message_dropdown_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        if not custom_id.startswith("ma:s:"):
            return

        try:
            *_, msg_id, menu_id = custom_id.split(":")
            selected_value = inter.values[0]
        except (ValueError, IndexError):
            return

        db = ObterDatabase()
        msg_config = next((m for m in db.get("mensagens_automaticas", []) if m.get("id") == msg_id), None)
        if not msg_config: return

        menu_config = next((sm for sm in msg_config.get("select_menus", []) if sm.get("id") == menu_id), None)
        if not menu_config: return

        option_config = next((opt for opt in menu_config.get("options", []) if opt.get("value") == selected_value), None)
        if not option_config or not option_config.get("action"):
            if not inter.response.is_done():
                await inter.response.send_message("❌ Ação para esta opção não foi encontrada ou foi removida.", ephemeral=True)
            return
            
        action = option_config["action"]

        if action.get("type") == "send_message" and action.get("ephemeral", True):
            await self._execute_action(inter, action)
            return
            
        await inter.response.defer(ephemeral=True)
        await self._execute_action(inter, action)


def setup(bot: commands.Bot):
    bot.add_cog(OnMensagemAutomatica(bot))