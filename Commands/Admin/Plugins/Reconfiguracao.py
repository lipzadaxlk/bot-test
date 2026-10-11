import disnake
from disnake.ext import commands
import json
import os
import sys
import asyncio

# Supondo que essas funções e variáveis existam nos caminhos especificados
from Functions.CarregarEmojis import *
from Functions.VerificarPerms import *

# Para manter a cog autocontida, o dicionário de personagens é incluído aqui.
PERSONAGENS = {
    "draculaura": {"nome": "Dráculaura", "emoji": f"{draculaura}"},
    "nick": {"nome": "Nick", "emoji": f"{nick}"},
    "micu": {"nome": "Miku", "emoji": f"{miku}"},
    "meru": {"nome": "Meru", "emoji": f"{meru}"},
    "emilia": {"nome": "Emília", "emoji": f"{emilia}"},
    "konata": {"nome": "Konata", "emoji": f"{konata}"},
    "nenhum": {"nome": "Nenhum", "emoji": "👋"}
}

def ObterPainelSelecaoPersonagemReconfig():
    content = f"""# Trocar de Personagem Atendente

> - Escolha um novo personagem para ser o atendente do seu bot!

## **Personagens Disponíveis:**
> {PERSONAGENS["draculaura"]["emoji"]} **Dráculaura**
> {PERSONAGENS["nick"]["emoji"]} **Nick**
> {PERSONAGENS["meru"]["emoji"]} **Meru**
> {PERSONAGENS["emilia"]["emoji"]} **Emília**
> {PERSONAGENS["konata"]["emoji"]} **Konata**
> {PERSONAGENS["nenhum"]["emoji"]} **Nenhum**

-# Selecione um personagem no menu abaixo para alterar."""

    select_menu = disnake.ui.Select(
        placeholder="Escolha um novo personagem...",
        custom_id="reconfig_selecionar_personagem",
        options=[
            disnake.SelectOption(
                label=data["nome"],
                value=key,
                emoji=data["emoji"],
                description=f"Usar {data['nome']} como novo atendente"
            )
            for key, data in PERSONAGENS.items()
        ]
    )
    
    botao_voltar = disnake.ui.Button(
        label="Voltar",
        style=disnake.ButtonStyle.grey,
        custom_id="GerenciarReconfiguracao"
    )
    
    components = [[select_menu], [botao_voltar]]
    
    return content, components

class ReconfiguracaoCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def get_theme_color(self):
        with open("config.json", "r") as f:
            config = json.load(f)
        return int(config.get("theme", "#FEE75C").replace("#", "0x"), 16)

    # --- CLASSE DO MODAL PARA TROCA DE SERVIDOR ---
    class TrocarServidorModal(disnake.ui.Modal):
        def __init__(self, cog_instance: 'ReconfiguracaoCog'):
            self.cog = cog_instance
            components = [
                disnake.ui.TextInput(
                    label="ID do Novo Servidor Principal",
                    placeholder="Cole o ID do servidor aqui...",
                    custom_id="servidor_id_input",
                    min_length=17,
                    max_length=20,
                ),
            ]
            super().__init__(title="Trocar Servidor Principal", custom_id="reconfig_servidor_modal", components=components)

        async def callback(self, inter: disnake.ModalInteraction):
            await inter.response.defer()
            novo_servidor_id_str = inter.text_values["servidor_id_input"]

            try:
                novo_servidor_id = int(novo_servidor_id_str)
                guild = self.cog.bot.get_guild(novo_servidor_id)

                if guild:
                    # SUCESSO: Bot está no servidor, altera a config
                    with open("config.json", "r+") as f:
                        config = json.load(f)
                        config["server"] = str(novo_servidor_id)
                        f.seek(0)
                        json.dump(config, f, indent=4)
                        f.truncate()
                    
                    embed = disnake.Embed(
                        title=f"{positivo} Servidor Principal Alterado!",
                        description=f"O servidor principal foi alterado para **{guild.name}** (`{guild.id}`).\n\n**AÇÃO NECESSÁRIA:**\n> Para que os comandos e as configurações sejam aplicados corretamente no novo servidor, **reinicie o seu bot através do seu painel de gerenciamento (Bot Manager).**",
                        color=self.cog.get_theme_color()
                    )
                    await inter.edit_original_message(embed=embed, components=[])
                else:
                    # FALHA: Bot não está no servidor ou ID é inválido
                    embed = disnake.Embed(
                        title=f"{negativo} Operação Falhou",
                        description=f"O ID `{novo_servidor_id}` é inválido ou o bot não faz parte deste servidor.\n\n> Por favor, convide o bot para o servidor desejado e tente novamente.",
                        color=disnake.Color.red()
                    )
                    components = [
                        disnake.ui.Button(label="Tentar Novamente", emoji=reload, style=disnake.ButtonStyle.primary, custom_id="reconfig_trocar_servidor"),
                        disnake.ui.Button(label="Voltar", emoji=voltar, style=disnake.ButtonStyle.grey, custom_id="GerenciarReconfiguracao")
                    ]
                    await inter.edit_original_message(embed=embed, components=components, content=None)

            except ValueError:
                # FALHA: ID não contém apenas números
                embed = disnake.Embed(
                    title=f"{negativo} ID Inválido",
                    description="O ID do servidor deve conter apenas números. Por favor, tente novamente.",
                    color=disnake.Color.red()
                )
                components = [
                    disnake.ui.Button(label="Tentar Novamente", emoji=reload, style=disnake.ButtonStyle.primary, custom_id="reconfig_trocar_servidor"),
                    disnake.ui.Button(label="Voltar", emoji=voltar, style=disnake.ButtonStyle.grey, custom_id="GerenciarReconfiguracao")
                ]
                await inter.edit_original_message(embed=embed, components=components, content=None)

    @commands.Cog.listener("on_button_click")
    async def ReconfiguracaoPainelListener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        reconfig_ids = ["GerenciarReconfiguracao", "reconfig_trocar_servidor", "reconfig_trocar_personagem", "reconfig_desligar_bot", "confirmar_desligar", "PainelInicial"]
        if custom_id not in reconfig_ids:
            return

        if custom_id != "PainelInicial":
            if not verificar_permissao(inter.user.id):
                return await inter.response.send_message(f"{negativo} Faltam permissões para executar essa ação.", ephemeral=True)

        if custom_id == "GerenciarReconfiguracao":
            await inter.response.defer()
            embed = disnake.Embed(
                title="⚙️ Painel de Reconfiguração",
                description="> Selecione uma das opções abaixo para reconfigurar seu bot.",
                color=self.get_theme_color()
            )
            embed.set_footer(text="Cuidado! Algumas ações são irreversíveis.")
            
            components = [
                disnake.ui.Button(label="Trocar Servidor Principal", emoji="↔️", style=disnake.ButtonStyle.blurple, custom_id="reconfig_trocar_servidor"),
                disnake.ui.Button(label="Trocar Personagem", emoji="🔄", style=disnake.ButtonStyle.blurple, custom_id="reconfig_trocar_personagem"),
                disnake.ui.Button(label="Desligar Bot", emoji="🔌", style=disnake.ButtonStyle.red, custom_id="reconfig_desligar_bot"),
                disnake.ui.Button(label="Voltar ao Painel", emoji=voltar, style=disnake.ButtonStyle.grey, custom_id="PainelInicial")
            ]
            
            await inter.edit_original_message(content=None, embed=embed, components=components)

        elif custom_id == "reconfig_trocar_servidor":
            modal = self.TrocarServidorModal(self)
            await inter.response.send_modal(modal)
            
        elif custom_id == "reconfig_trocar_personagem":
            await inter.response.defer()
            content, components = ObterPainelSelecaoPersonagemReconfig()
            await inter.edit_original_message(content=content, embed=None, components=components)
            
        elif custom_id == "reconfig_desligar_bot":
            await inter.response.defer()
            embed = disnake.Embed(
                title="⚠️ Confirmação de Desligamento ⚠️",
                description="Você tem certeza que deseja desligar o bot? Esta ação é **irreversível** e o bot precisará ser reiniciado manually no host.",
                color=disnake.Color.red()
            )
            
            components = [
                disnake.ui.Button(label="Confirmar Desligamento", style=disnake.ButtonStyle.red, custom_id="confirmar_desligar"),
                disnake.ui.Button(label="Cancelar", style=disnake.ButtonStyle.grey, custom_id="GerenciarReconfiguracao")
            ]
            
            await inter.edit_original_message(content=None, embed=embed, components=components)
            
        elif custom_id == "confirmar_desligar":
            await inter.response.edit_message(content=f"🔌 Desligando o bot. Até a próxima!", embed=None, components=[], attachments=[])
            await self.bot.close()

    @commands.Cog.listener("on_dropdown")
    async def ReconfiguracaoDropdownListener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id

        if custom_id != "reconfig_selecionar_personagem":
            return

        await inter.response.defer()

        if not verificar_permissao(inter.user.id):
             return await inter.followup.send(f"{negativo} Faltam permissões para executar essa ação.", ephemeral=True)
             
        personagem_selecionado = inter.values[0]
            
        with open("config.json", "r+") as f:
            config = json.load(f)
            config["personagem_atendente"] = personagem_selecionado
            f.seek(0)
            json.dump(config, f, indent=4)
            f.truncate()
        
        personagem_info = PERSONAGENS[personagem_selecionado]
        
        embed = disnake.Embed(
            title="Personagem Alterado!",
            description=f'{positivo} O personagem atendente foi alterado para **{personagem_info["nome"]}** {personagem_info["emoji"]}.',
            color=self.get_theme_color()
        )
        
        components = [
            disnake.ui.Button(label="Voltar ao Painel", emoji=voltar, style=disnake.ButtonStyle.grey, custom_id="PainelInicial")
        ]
        
        await inter.edit_original_message(content=None, embed=embed, components=components)

def setup(bot: commands.Bot):
    bot.add_cog(ReconfiguracaoCog(bot))