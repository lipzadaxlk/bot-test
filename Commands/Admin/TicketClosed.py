import disnake
import json
from disnake.ext import commands
from Functions.CarregarEmojis import *

# ==================================================================================================================== #
#                                              FUNÇÕES DO DATABASE (COPIADAS E ADAPTADAS)                              #
# ==================================================================================================================== #

def ObterTicketsAbertos():
    """Carrega os dados de ticketsAbertos.json."""
    try:
        with open("Database/Tickets/ticketsAbertos.json", 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {} # Retorna um dicionário vazio se o arquivo não existir
    except json.JSONDecodeError:
        return {} # Retorna um dicionário vazio se o JSON for inválido

def SalvarTicketsAbertos(db):
    """Salva os dados no ticketsAbertos.json."""
    with open("Database/Tickets/ticketsAbertos.json", 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=4)

def ObterConfigCanais():
    """Carrega as configurações de canais."""
    try:
        with open("Database/Server/canais.json", 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}

# ==================================================================================================================== #
#                                                CLASSE DO NOVO COMANDO                                               #
# ==================================================================================================================== #

class CloseAllTickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def verificar_permissao_staff(self, member: disnake.Member) -> bool:
        """Verifica se o membro possui o cargo de suporte."""
        try:
            with open("Database/Server/cargos.json") as f:
                cargos = json.load(f)
            suporte_cargo_id = cargos.get("suporte")
            if not suporte_cargo_id: return False
            if any(str(role.id) == str(suporte_cargo_id) for role in member.roles):
                return True
            return False
        except Exception:
            return False

    @commands.slash_command(name="fecharticket", description="Fecha todos os tickets abertos do servidor.")
    @commands.default_member_permissions(manage_channels=True) # Permissão padrão para quem pode gerenciar canais
    async def fechar_todos_tickets(self, inter: disnake.ApplicationCommandInteraction):
        """
        Fecha todos os tickets abertos no servidor.
        """
        if not self.verificar_permissao_staff(inter.author):
            return await inter.response.send_message(f"{negativo} Você não tem permissão para usar este comando.", ephemeral=True)

        await inter.response.defer(ephemeral=True)

        tickets_abertos = ObterTicketsAbertos()
        fechados_com_sucesso = 0
        falhas = 0
        canais_config = ObterConfigCanais()
        logs_channel_id = canais_config.get("tickets")
        logs_channel = None

        if logs_channel_id:
            try:
                logs_channel = inter.guild.get_channel(int(logs_channel_id))
            except:
                logs_channel = None

        for ticket_aberto_id, ticket_info in list(tickets_abertos.items()): # Usa list() para permitir modificação durante a iteração
            topic_id = ticket_info.get("server", {}).get("topicID")
            user_id = ticket_info.get("server", {}).get("userID")

            if topic_id:
                try:
                    thread = inter.guild.get_thread(topic_id)
                    if thread:
                        await thread.delete()
                        fechados_com_sucesso += 1
                        
                        # Remover do database de tickets abertos
                        del tickets_abertos[ticket_aberto_id]
                        SalvarTicketsAbertos(tickets_abertos) # Salva a cada remoção para garantir consistência

                        # Notificar o usuário se possível
                        if user_id:
                            try:
                                user = await self.bot.fetch_user(int(user_id))
                                if user:
                                    embed_dm = disnake.Embed(title="Ticket Fechado", description=f"Seu ticket foi fechado por um moderador ({inter.author.mention}).", color=disnake.Color.red())
                                    await user.send(embed=embed_dm)
                            except disnake.NotFound:
                                pass # Usuário não encontrado, pode ter saído do servidor
                            except Exception as e:
                                print(f"Erro ao enviar DM para o usuário {user_id}: {e}")

                        # Enviar log para o canal de logs
                        if logs_channel:
                            embed_log = disnake.Embed(title="Ticket Fechado (Comando)", description=f"Um ticket foi fechado pelo comando `/fecharticket`.", color=disnake.Color.dark_red())
                            embed_log.add_field(name="Fechado por", value=inter.author.mention, inline=True)
                            if user_id:
                                embed_log.add_field(name="Usuário do Ticket", value=f"<@{user_id}> (`{user_id}`)", inline=True)
                            embed_log.add_field(name="ID do Tópico", value=f"`{topic_id}`", inline=False)
                            await logs_channel.send(embed=embed_log)

                    else:
                        # Se a thread não for encontrada, remove do DB, mas não conta como "falha de deleção"
                        del tickets_abertos[ticket_aberto_id]
                        SalvarTicketsAbertos(tickets_abertos)
                        falhas += 1 # Conta como falha se não encontrou o canal
                except Exception as e:
                    print(f"Erro ao fechar ticket {topic_id}: {e}")
                    falhas += 1
                    # Em caso de erro na deleção, ainda tenta remover do DB para evitar tickets "fantasmas"
                    if ticket_aberto_id in tickets_abertos:
                        del tickets_abertos[ticket_aberto_id]
                        SalvarTicketsAbertos(tickets_abertos)
            else:
                # Se não tem topicID, remove do DB
                del tickets_abertos[ticket_aberto_id]
                SalvarTicketsAbertos(tickets_abertos)
                falhas += 1 # Considera falha na estrutura do DB

        # Salva o estado final após todas as iterações
        SalvarTicketsAbertos(tickets_abertos)

        await inter.edit_original_response(
            f"{positivo} Finalizado! Foram fechados `{fechados_com_sucesso}` tickets. "
            f"Houve `{falhas}` falha(s) (tickets que não foram encontrados ou erro ao apagar)."
        )

def setup(bot: commands.Bot):
    bot.add_cog(CloseAllTickets(bot))