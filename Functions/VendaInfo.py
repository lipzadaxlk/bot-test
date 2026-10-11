import disnake
from disnake.ext import commands
from datetime import *
from Functions.CarregarEmojis import *
from Functions.VerificarPerms import *
import json 

def ObterDatabase():
    with open("Database/Vendas/historicos.json") as f:
        db = json.load(f)
        return db

def ObterVenda(id: str):
    """Obtém os dados de uma venda específica do banco de dados."""
    db = ObterDatabase()
    try:
        venda = db[id]
    except KeyError:
        venda = None
    return venda
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

def ObterVendaPainel(inter: disnake.MessageInteraction, id: str):
    db = ObterDatabase()

    try:
        db[id]
    except:
        return None, None

    produto = ObterProduto(db[id]["produtoID"])
    campo = ObterCampo(db[id]["produtoID"], db[id]["campoID"])

    if not produto: produtoNome = "Não encontrado"
    else: produtoNome = produto["nome"]

    if not campo: campoNome = "Não encontrado"
    else: campoNome = campo["nome"]

    try:
        user = inter.guild.get_member(int(db[id]["server"]["usuario"]))
        userMention = user.mention
    except:
        userMention = "Não encontrado"

    valor = db[id]["info"]["valorFinal"]
    quantidade = db[id]["info"]["quantidade"]
    informacoes = f"{quantidade}x {produtoNome} - {campoNome}"
    compradoEm = f"<t:{int(datetime.strptime(db[id]["info"]["timestamp"], '%d/%m/%Y %H:%M').timestamp())}:F>"

    embed = disnake.Embed(
        title="Informações do pedido",
        color=disnake.Color(0x00FFFF),
        timestamp=datetime.now()
    )
    embed.add_field(
        name="Produto",
        value=f"`{produtoNome}`",
        inline=True
    )
    embed.add_field(
        name="Campo",
        value=f"`{campoNome}`",
        inline=True
    )
    embed.add_field(
        name="ID da Compra",
        value=f"`{id}`",
        inline=True
    )

    pagamento_tipo = "Mercado Pago" if db[id]["info"]["pagamento"]["paymentID"] else "EFI Bank" if db[id]["info"]["pagamento"]["txid"] else "Semi Automático"
    pagamento_id = db[id]["info"]["pagamento"]["paymentID"] if pagamento_tipo == "Mercado Pago" else db[id]["info"]["pagamento"]["txid"] if pagamento_tipo == "EFI Bank" else "Não disponível"
    embed.add_field(
        name="Informações do pagamento",
        value=f"""
```
🏧 Pagamento: PIX - {pagamento_tipo}
🧾 ID do pagamento: {pagamento_id}
🛒 Reembolsado: {"Sim" if db[id]["info"]["reembolso"] == True else "Não"}
```""",
        inline=False
    )
    
    embed.add_field(
        name="Tempo de compra",
        value=f"{compradoEm}",
        inline=False
    )
    embed.add_field(
        name="Informações da venda",
        value=f"`{informacoes}`",
        inline=True
    )
    embed.add_field(
        name="Valor Pago",
        value=f"`R${valor}`",
        inline=True
    )
    embed.add_field(
        name="Usuário",
        value=f"{userMention}",
        inline=True
    )

    components = [
        disnake.ui.Button(
            style=disnake.ButtonStyle.red,
            label="Reembolsar",
            emoji=bancoBloqueado,
            custom_id=f"ReembolsarProduto_{id}",
            disabled = not db[id]["info"]["pagamento"]["paymentID"] or db[id]["info"]["reembolso"]
        )
    ]

    return embed, components
