import disnake
import json
from disnake.ext import commands
from datetime import datetime
from Functions.CarregarEmojis import *

# --- GERENCIAMENTO DE DATABASE (JSON) ---
def obter_db_duvidas():
    """
    Carrega a configuração do botão de dúvidas.
    Se a chave 'botao_duvidas' não existir no JSON, ela é criada com valores padrão sem apagar outros dados.
    """
    filepath = "Database/Vendas/configuracao.json"
    try:
        with open(filepath, "r", encoding='utf-8') as f:
            full_db = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        full_db = {}

    if "botao_duvidas" not in full_db:
        full_db["botao_duvidas"] = {
            "status": False,
            "nomebotao": "Dúvidas?",
            "emoji": "❓",
            "linkbotao": None
        }
        with open(filepath, "w", encoding='utf-8') as f:
            json.dump(full_db, f, indent=4, ensure_ascii=False)

    return full_db["botao_duvidas"]

def salvar_db_duvidas(data_duvidas):
    """
    Salva a configuração específica do botão de dúvidas sem apagar outras chaves no arquivo JSON.
    """
    filepath = "Database/Server/botao_duvidas.json"
    try:
        with open(filepath, "r", encoding='utf-8') as f:
            full_db = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        full_db = {}

    full_db["botao_duvidas"] = data_duvidas
    
    with open(filepath, "w", encoding='utf-8') as f:
        json.dump(full_db, f, indent=4, ensure_ascii=False)

# --- MODAL DE PERSONALIZAÇÃO ---
class PersonalizarBotaoModal(disnake.ui.Modal):
    def __init__(self, db_info: dict):
        self.db_info = db_info
        components = [
            disnake.ui.TextInput(
                label="Nome do Botão",
                custom_id="nome_botao",
                placeholder="Ex: Precisa de Ajuda?",
                value=db_info.get("nomebotao"),
                max_length=80,
                required=True
            ),
            disnake.ui.TextInput(
                label="Emoji do Botão (Opcional)",
                custom_id="emoji_botao",
                placeholder="❓ ou <:duvida:1388835385966067712>",
                value=db_info.get("emoji"),
                max_length=50,
                required=False
            ),
        ]
        super().__init__(title="Personalizar Botão de Dúvidas", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer()
        nome = inter.text_values["nome_botao"]
        emoji = inter.text_values["emoji_botao"]

        db = obter_db_duvidas()
        db["nomebotao"] = nome
        db["emoji"] = emoji if emoji else "❓"
        salvar_db_duvidas(db)

        painel_embed, painel_view = PainelDuvidas.obter_painel(inter)
        await inter.message.edit(embed=painel_embed, view=painel_view)
        await inter.followup.send(f"{positivo} Botão personalizado com sucesso!", ephemeral=True)


# --- GERADOR DE PAINEL ---
class PainelDuvidas:
    @staticmethod
    def obter_painel(inter: disnake.Interaction):
        """Cria e retorna o embed e a view do painel de configuração."""
        db_info = obter_db_duvidas()

        embed = disnake.Embed(
            color=0x660f7e,
            title="Configurar Botão de Dúvidas",
            description=f"Utilize os botões abaixo e configure o botão de dúvidas.",
            timestamp=datetime.now()
        )
        embed.add_field(name="Nome do Botão", value=f"`{db_info.get('nomebotao', 'Não Definido')}`", inline=True)
        embed.add_field(name="Emoji do Botão", value=f"{db_info.get('emoji', '`Sem Emoji`')}", inline=True)
        embed.add_field(name="Link do Canal", value=f"`{db_info.get('linkbotao', 'Não Definido')}`", inline=True)
        embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon.url if inter.guild.icon else None)

        view = disnake.ui.View(timeout=None)
        status_info = db_info.get("status", False)
        view.add_item(disnake.ui.Button(
            custom_id='duvidas_toggle_status',
            label="Botão Ativado" if status_info else "Botão Desativado",
            emoji=ligado if status_info else desligado,
            style=disnake.ButtonStyle.green if status_info else disnake.ButtonStyle.red
        ))
        view.add_item(disnake.ui.Button(custom_id='duvidas_definir_canal', label='Definir Canal', emoji=canalText, style=disnake.ButtonStyle.secondary))
        view.add_item(disnake.ui.Button(custom_id='duvidas_personalizar_botao', label='Personalizar Botão', emoji=editar, style=disnake.ButtonStyle.secondary))
        view.add_item(disnake.ui.Button(custom_id='GerenciarPainelVendas', label='Voltar', emoji=voltar, style=disnake.ButtonStyle.gray))

        return embed, view


# --- COG PRINCIPAL E LISTENERS ---
class BotaoDuvidasCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def painel_duvidas_listener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id

        if custom_id == "GerenciarBotaoDuvidas":
            await inter.response.defer()
            embed, view = PainelDuvidas.obter_painel(inter)
            await inter.edit_original_message(content=None, embed=embed, view=view)

        elif custom_id == "duvidas_toggle_status":
            await inter.response.defer()
            db = obter_db_duvidas()
            db["status"] = not db.get("status", False)
            salvar_db_duvidas(db)
            
            embed, view = PainelDuvidas.obter_painel(inter)
            await inter.edit_original_message(embed=embed, view=view)
            status_text = "ativado" if db['status'] else "desativado"
            await inter.followup.send(f"{positivo} O botão de dúvidas foi **{status_text}**.", ephemeral=True)

        # Listener para o botão que abre o menu de seleção de canal (LÓGICA ALTERADA)
        elif custom_id == "duvidas_definir_canal":
            select_menu = disnake.ui.ChannelSelect(
                custom_id="duvidas_channel_select",
                placeholder="Selecione o canal de dúvidas...",
                channel_types=[disnake.ChannelType.text, disnake.ChannelType.forum]
            )
            # Cria uma view temporária com o select e um botão de cancelar
            temp_view = disnake.ui.View(timeout=180)
            temp_view.add_item(select_menu)
            # O botão de cancelar simplesmente recarrega o painel original
            temp_view.add_item(disnake.ui.Button(label="Cancelar",emoji=negativo, style=disnake.ButtonStyle.red, custom_id="GerenciarBotaoDuvidas"))

            await inter.response.edit_message(
                content="Por favor, selecione para qual canal as dúvidas devem ser direcionadas.",
                view=temp_view,
                embed=None # Limpa o embed para focar na seleção
            )

        elif custom_id == "duvidas_personalizar_botao":
            db_info = obter_db_duvidas()
            await inter.response.send_modal(PersonalizarBotaoModal(db_info))

    @commands.Cog.listener("on_dropdown")
    async def duvidas_dropdown_listener(self, inter: disnake.MessageInteraction):
        # Listener para quando um canal é selecionado no dropdown
        if inter.component.custom_id == "duvidas_channel_select":
            await inter.response.defer()
            channel_id = int(inter.values[0])
            channel = inter.guild.get_channel(channel_id)

            if not channel:
                # Se o canal não for encontrado, apenas recarrega o painel
                embed, view = PainelDuvidas.obter_painel(inter)
                await inter.edit_original_message(content=None, embed=embed, view=view)
                await inter.followup.send(f"{negativo} Canal não encontrado.", ephemeral=True)
                return

            db = obter_db_duvidas()
            db["linkbotao"] = channel.jump_url
            salvar_db_duvidas(db)
            
            # Restaura o painel original, agora com as informações atualizadas
            embed, view = PainelDuvidas.obter_painel(inter)
            await inter.edit_original_message(content=None, embed=embed, view=view)
            
            # Confirma a ação para o usuário
            await inter.followup.send(f"{positivo} O link do botão de dúvidas foi definido para o canal {channel.mention}!", ephemeral=True)


def setup(bot: commands.Bot):
    bot.add_cog(BotaoDuvidasCommand(bot))