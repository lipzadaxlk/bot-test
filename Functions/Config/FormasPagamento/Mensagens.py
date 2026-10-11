import json
import disnake
from disnake import *
from datetime import *

from Functions.CarregarEmojis import *

def ObterProduto(produtoID):
    with open("Database/Vendas/produtos.json") as f:
        db = json.load(f)
        try:
            produto = db[produtoID]
        except:
            produto = None
        return produto

def ObterCampo(produtoID, campoID):
    with open("Database/Vendas/produtos.json") as f:
        db = json.load(f)
        try:
            produto = db[produtoID]
            campo = produto["campos"][campoID]
        except:
            campo = None
        return campo

def ObterCarrinho(carrinhoID):
    with open("Database/Vendas/carrinhos.json") as f:
        db = json.load(f)
        carrinho = db[carrinhoID]
        return carrinho

def ObterMensagemLogs(inter: disnake.CommandInteraction, type: str, carrinhoID):
    carrinho = ObterCarrinho(carrinhoID)

    # --- Lógica de Agregação para Múltiplos Produtos ---
    # Em vez de buscar um único produto, criamos uma descrição resumida de todos os itens.
    desc_agregada = []
    if carrinho and carrinho.get('itens'):
        for item in carrinho['itens']:
            produto = ObterProduto(item['produtoID'])
            campo = ObterCampo(item['produtoID'], item['campoID'])
            if produto and campo:
                desc_agregada.append(f"{item['quantidade']}x {campo['nome']} - {produto['nome']}")
    
    # Junta todos os nomes em uma única string para ser usada nos logs.
    info_pedido_str = " | ".join(desc_agregada) + f" | R${carrinho['info']['valorFinal']}"


    if type == "1":
        embed = disnake.Embed(
            title=f"{pedidoSolicitado} Pedido solicitado",
            description=f"Usuário {inter.user.mention} solicitou um pedido e está no pagamento.",
            color=disnake.Color.yellow(),
            timestamp=datetime.now()
        )
        embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon)
        embed.add_field(name="Detalhes do pedido", value=f"`{info_pedido_str}`", inline=False)
        embed.add_field(name="ID do pedido", value=f"`{carrinhoID}`", inline=True)
        embed.add_field(name="Forma de Pagamento", value=f"{pix} `Pagamento: PIX`")
        components = [
            disnake.ui.Button(label="Ir para carrinho", url=inter.channel.jump_url, emoji=caixa)
        ]

    elif type == "2":
        embed = disnake.Embed(
            title=f"{pix} Pagamento via PIX Criado",
            color=disnake.Color(0x00FFFF),
            timestamp=datetime.now()
        )
        embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon)
        embed.add_field(
            name="Expira em",
            value=f"<t:{int((datetime.now() + timedelta(minutes=10)).timestamp())}:R>",
            inline=True
        )
        embed.add_field(
            name="Valor final",
            value=f"`R${carrinho['info']['valorFinal']}`",
            inline=True
        )
        embed.add_field(
            name="Código Copia e Cola",
            value=f"```{carrinho['info']['pagamento']['copiacola']}```",
            inline=False
        )
        embed.set_author(name=inter.user.name, icon_url=inter.user.avatar)
        embed.set_image(url=carrinho['info']['pagamento'].get('url'))

        components = [
            disnake.ui.Button(
                label="Código Copia e Cola",
                emoji=f"{mensagem}",
                custom_id=f"CodigoCopiaCola_{carrinhoID}"
            ),
            disnake.ui.Button(style=disnake.ButtonStyle.red, label="Cancelar", emoji=apagar, custom_id=f"CancelarCarrinho_{carrinhoID}")
        ]
    
    elif type == "3":
        embed = disnake.Embed(
            title=f"{pedidoEntregue} Pagamento concluído",
            description="Seu pagamento foi aprovado, e o processo de entrega já foi iniciado.\nAguarde um momento enquanto separamos seu produto.",
            timestamp=datetime.now(),
            color=disnake.Color(0x0be34c)
        )
        embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon)
        embed.add_field(
            name="Informações do pedido",
            value=f"`{info_pedido_str}`",
            inline=True
        )
        embed.add_field(
            name="ID do pedido",
            value=f"`{carrinhoID}`",
            inline=True
        )
        # Botão de Gerenciar Estoque é ambíguo em um carrinho de múltiplos produtos, então foi removido do log.
        components = []

    elif type == "4":
        embed = disnake.Embed(
            title=f"{produtoEntregue} Entrega realizada",
            description="Seu pedido foi concluído e processado!\nSeu pedido foi anexado a essa mensagem.",
            color=disnake.Color(0x3808bd),
            timestamp=datetime.now()
        )
        embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon)
        embed.add_field(
            name="Horário da entrega",
            value=f"<t:{int(datetime.now().timestamp())}:f>",
            inline=True
        )
        embed.add_field(
            name="ID do pedido",
            value=f"`{carrinhoID}`",
            inline=True
        )
        # Botões de ação de produto único foram removidos do log de múltiplos produtos para evitar ambiguidade.
        components = []

    elif type == "blocked":
        embed = disnake.Embed(
            title=f"{bancoBloqueado} Banco bloqueado",
            description=f'O banco que você utilizou no pagamento foi bloqueado pela loja.\nPor causa disso, reembolsamos seu pagamento (`R${carrinho["info"]["valorFinal"]}`)\nCaso ocorreu algum engano, contate o suporte.',
            color=disnake.Color(0xe31e10),
            timestamp=datetime.now()
        )
        embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon)
        components = None
    
    elif type == "ticket":
        with open("Database/Server/cargos.json", encoding='utf-8') as db:
            cargos = json.load(db)
        with open("config.json", encoding='utf-8') as config:
            owner = json.load(config).get("owner")
            
        suporte = cargos.get("suporte")
        if not suporte: suporte = f"<@{owner}>" 
        else: suporte = f"<@&{suporte}>"
        content = f"{inter.user.mention} {suporte}"

        embed = disnake.Embed(
            title="Entrega não automática",
            description="Utilize o ticket atual para receber sua entrega.\nAbaixo estão as informações do carrinho.",
            color=disnake.Color(0x00FFFF),
            timestamp=datetime.now()
        )
        embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon)
        embed.add_field(
            name="Informações do pedido",
            value=f"```{info_pedido_str}```",
            inline=False
        )
        embed.add_field(
            name="ID do Pedido",
            value=f"`{carrinhoID}`"
        )
        embed.set_thumbnail(url="https://media.discordapp.net/attachments/1327815504865398854/1333664443258900583/a_d78e7542df8823e9c10eac06609d7473.gif")
        components = [
            disnake.ui.Button(style=disnake.ButtonStyle.red, label="Fechar", emoji=apagar, custom_id=f"CancelarCarrinho_{carrinhoID}")
        ]
    
    elif type == "indisponivel":
        embed = disnake.Embed(
            title=f"{carrinhoCancelado} Produto indisponível",
            description="Não foi possível separar seu pedido pois o estoque acabou, se o método de pagamento usado for extornável, seu dinheiro foi devolvido.",
            color=disnake.Color(0xe31e10),
            timestamp=datetime.now()
        )
        embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon)
        embed.add_field(
            name="ID da Compra",
            value=f"`{carrinhoID}`"
        )
        # Botão de Gerenciar Estoque é ambíguo em um carrinho de múltiplos produtos, então foi removido do log.
        components = []
    
    return embed, components