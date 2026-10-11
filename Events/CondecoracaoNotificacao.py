# CondecoracaoNotificacao.py

import disnake
from disnake.ext import commands
from datetime import datetime
import json
import os

# Importa as variáveis globais de emojis
from Functions.CarregarEmojis import *

# Importa funções e dados do Condecoracao.py
# A variável CONDECORATION_THEMES foi removida daqui para corrigir o erro.
from Commands.Admin.Plugins.Condecoracao import ObterDatabaseCondecoracao, DEFAULT_CONDECORATIONS_DATA

class CondecoracaoNotificacao(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Referência à cog principal de condecorações para chamar conceder_condecoracao
        self.condecoracao_main_cog = None 
        self.bot.loop.create_task(self._load_main_condecoracao_cog())

    async def _load_main_condecoracao_cog(self):
        await self.bot.wait_until_ready()
        # Tenta obter a instância da cog CondecoracaoCommand
        self.condecoracao_main_cog = self.bot.get_cog("CondecoracaoCommand")
        if not self.condecoracao_main_cog:
            print("AVISO: A cog 'CondecoracaoCommand' não foi carregada. As notificações de condecoração podem não funcionar corretamente.")

    # --- Lógica para Condecoração "Avaliador" (Feedback) ---
    # Esta função será chamada pelo Definicoes.py quando um feedback for detectado.
    async def check_and_award_feedback_condecorations(self, user_id: int, inter: disnake.Interaction = None):
        """
        Verifica e concede a condecoração "Avaliador" (criticoConstrutivo) a um usuário.
        Esta função é chamada quando um feedback é detectado.
        """
        if not self.condecoracao_main_cog:
            print("Erro: Cog CondecoracaoCommand não disponível para verificação de feedback.")
            return

        # Para esta condecoração específica, a condição é "total_feedbacks": 1
        # Ou seja, basta o primeiro feedback para ganhar a condecoração.
        # A função 'conceder_condecoracao' já verifica se o usuário já a possui no DB.
        condec_id = "criticoConstrutivo"
        condec_info = DEFAULT_CONDECORATIONS_DATA.get(condec_id)

        if condec_info and condec_info["tipo"] == "feedback":
            # Chamamos a função conceder_condecoracao da cog principal
            # Ela mesma verificará se o usuário já a possui e fará a notificação (DM/anúncio).
            await self.condecoracao_main_cog.conceder_condecoracao(user_id, condec_id, inter)
        else:
            print(f"Condecoração '{condec_id}' não encontrada ou não é do tipo 'feedback'.")

# setup da cog
def setup(bot: commands.Bot):
    bot.add_cog(CondecoracaoNotificacao(bot))