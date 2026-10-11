import disnake
from disnake.ext import commands
from datetime import *
from disnake import *
import json
import os
import shutil

from Functions.CarregarEmojis import *

try:
    from Commands.Admin.Plugins.BotaoDuvidas import obter_db_duvidas
except ImportError:
    def obter_db_duvidas():
        return {"status": False}

# Databases

def ObterDatabase():
    with open("Database/Vendas/produtos.json") as f:
        return json.load(f)

def ObterProduto(produtoID):
    with open("Database/Vendas/produtos.json") as f:
        db = json.load(f)
        return db.get(produtoID)

def ObterCampo(produtoID, campoID):
    produto = ObterProduto(produtoID)
    return produto.get("campos", {}).get(campoID) if produto else None

def ObterCarrinho(carrinhoID):
    with open("Database/Vendas/carrinhos.json") as f:
        db = json.load(f)
        return db.get(carrinhoID)

def ObterCupom(produtoID, cupom):
    produto = ObterProduto(produtoID)
    return produto.get("cupons", {}).get(cupom) if produto else None

def ObterHistoricosVendasDB():
    """Carrega o banco de dados de históricos de vendas."""
    try:
        with open("Database/Vendas/historicos.json", "r", encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def ObterConfiguracaoLoja():
    try:
        with open("Database/Vendas/configuracao.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def ObterTemaAtual():
    """Obtém apenas o código de cor hexadecimal do tema selecionado."""
    config = ObterConfiguracaoLoja()
    tema = config.get("tema", "Azul")
    cores_hex = {
        "Preto": "0x000001",
        "Azul": "0x0080FF",
        "Vermelho": "0xFF0000",
        "Verde": "0x00FF00",
        "Amarelo": "0xFFFF00",
        "Roxo": "0x8000FF",
        "Laranja": "0xFF8000",
        "Branco": "0xFFFFFF"
    }
    return cores_hex.get(tema, cores_hex["Azul"])

class Entrega():
    @staticmethod
    def ObterEstoque(quantidade, produtoID, campoID):
        db = ObterDatabase()
        campo = db.get(produtoID, {}).get("campos", {}).get(campoID)
        if not campo: return None
        itens = []
        for _ in range(quantidade):
            if campo["estoque"]:
                item = campo["estoque"].pop(0)
                itens.append(item)
        with open("Database/Vendas/produtos.json", "w") as f: json.dump(db, f, indent=4)
        os.makedirs("Database/Vendas/temp", exist_ok=True)
        arquivo_nome = f"Database/Vendas/temp/estoque_{produtoID}_{campoID}.txt"
        with open(arquivo_nome, "w", encoding="utf-8") as arquivo:
            arquivo.write("\n".join(itens))
        return arquivo_nome

    @staticmethod
    async def RegistrarEntrega(inter: disnake.Interaction, carrinhoID: str, arquivo: str):
        carrinho = ObterCarrinho(carrinhoID)
        vendaID = Entrega.RegistrarVenda(carrinhoID, arquivo)
        produto = ObterProduto(carrinho["produtoID"])
        campo = ObterCampo(carrinho["produtoID"], carrinho["campoID"])
        user = inter.guild.get_member(int(carrinho["server"]["usuario"]))
        with open("Database/Server/canais.json") as f:
            canais = json.load(f)
            vendas_channel_id = canais.get("vendas")
        if not vendas_channel_id: return vendaID
        embed = disnake.Embed(title=f"{pedidoRealizado} Compra realizada", description=f"O usuário {user.mention} teve seu pedido entregue.", timestamp=datetime.now(), color=disnake.Color.green())
        embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon)
        embed.set_author(name=user.name, icon_url=user.avatar)
        channel_produto = inter.guild.get_channel(int(carrinho["server"]["produtoURL"]))
        components = []
        if channel_produto: components.append(disnake.ui.Button(label="Comprar Novamente", url=channel_produto.jump_url, emoji=caixa))
        embed.add_field(name="Pedido", value=f"`{carrinho['info']['quantidade']}x {campo['nome']} - {produto['nome']}`", inline=False)
        embed.add_field(name="Valor Pago", value=f"`R${carrinho['info']['valorFinal']}`", inline=True)
        embed.add_field(name="Comprador", value=f"{user.mention}", inline=True)
        try:
            vendas_channel = inter.guild.get_channel(int(vendas_channel_id))
            if vendas_channel: await vendas_channel.send(embed=embed, components=components)
        except: pass
        return vendaID
    
    @staticmethod
    def RegistrarVenda(carrinhoID, arquivo):
        carrinho = ObterCarrinho(carrinhoID)
        pasta_destino = "Database/Vendas/entregas"
        os.makedirs(pasta_destino, exist_ok=True)
        destino = os.path.join(pasta_destino, f"{carrinhoID}.txt")
        shutil.copy2(arquivo, destino)
        with open("Database/Vendas/historicos.json") as f: db = json.load(f)
        db[carrinhoID] = carrinho
        db[carrinhoID]["info"]["timestamp"] = datetime.now().strftime("%d/%m/%Y %H:%M")
        db[carrinhoID]["info"]["reembolso"] = False
        with open("Database/Vendas/historicos.json", "w") as f: json.dump(db, f, indent=4)
        return carrinhoID

async def NotificarUserEstoque(inter: disnake.MessageInteraction, produtoID: str, campoID: str):
    db = ObterDatabase()
    produto = db.get(produtoID)
    if not produto or campoID not in produto.get("campos", {}): return
    campo = produto["campos"][campoID]
    alertas = campo.get("estoqueinfo", {}).get("alertas", [])
    if not produto.get("ids"): return
    id_dict = produto["ids"][0]
    canal_id = next(iter(id_dict)) if id_dict else None
    if not canal_id: return
    botao = None
    try:
        canal = inter.guild.get_channel(int(canal_id))
        if canal: botao = disnake.ui.Button(label="Ver Produto", url=canal.jump_url)
    except: pass
    for user_id in alertas:
        try:
            user = await inter.guild.fetch_member(int(user_id))
            if user:
                embed = disnake.Embed(description=f"Olá {user.mention}, o estoque do produto `{produto['nome']}` foi reabastecido!", color=disnake.Color.green())
                await user.send(embed=embed, components=[botao] if botao else [])
        except: continue

async def SincronizarMensagens(inter: disnake.Interaction, produtoID: str):
    db = ObterDatabase()
    produto = db.get(produtoID)
    if not produto or "ids" not in produto: return 0
    contagem, ids_validos = 0, []
    for id_dict in produto["ids"]:
        try:
            channelID, msgID = list(id_dict.items())[0]
            channel = inter.guild.get_channel(int(channelID))
            if not channel: continue
            msg = await channel.fetch_message(int(msgID))
            if not msg: continue
            
            payload = GerarPainelProduto(inter, produtoID, para_venda=True)
            await msg.edit(**payload)
            
            contagem += 1
            ids_validos.append(id_dict)
        except (disnake.NotFound, disnake.Forbidden, KeyError, ValueError, IndexError):
            continue
    db[produtoID]["ids"] = ids_validos
    with open("Database/Vendas/produtos.json", "w") as f:
        json.dump(db, f, indent=4)
    return contagem

def GerarPainelProduto(inter: disnake.Interaction, produtoID: str, para_venda=False):
    produto = ObterProduto(produtoID)
    if not produto:
        return {"content": "❌ Produto não encontrado.", "embeds": [], "components": []}

    payload = { "content": None, "embeds": [], "components": [] }
    
    content_list = []
    if produto.get("content"):
        content_list.append(produto.get("content"))
    
    has_embed_data = produto.get('desc') or produto.get('nome') not in [None, "Produto Sem Nome"]
    if produto.get("image_url") and not has_embed_data:
        content_list.append(produto.get("image_url"))
    
    if content_list:
        payload["content"] = "\n".join(content_list)

    if has_embed_data:
        cor_hex_tema = ObterTemaAtual()
        try:
            color_hex = produto.get("assets", {}).get("hex", cor_hex_tema)
            color = disnake.Color(int(color_hex.replace("0x", ""), 16))
        except:
            color = disnake.Color(int(cor_hex_tema.replace("0x", ""), 16))

        descricao = produto.get("desc", "")
        if produto.get("entrega", False):
            # A string de emojis agora é fixa e usa os emojis padrão
            entrega_automatica = f"{raio}{en}{tre}{ga}{aut}{oma}{tic}{a_}"
            descricao = entrega_automatica + "\n" + descricao if descricao else entrega_automatica.rstrip()
        
        embed = disnake.Embed(title=produto.get("nome"), description=descricao, color=color, timestamp=datetime.now())
        
        if produto.get("assets", {}).get("icon"): embed.set_thumbnail(url=produto["assets"]["icon"])
        
        if produto.get("image_url"):
            embed.set_image(url=produto.get("image_url"))
        elif produto.get("assets", {}).get("banner"):
            embed.set_image(url=produto["assets"]["banner"])
            
        embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon)

        campos = produto.get("campos", {})
        if len(campos) == 1:
            campoID, campoData = next(iter(campos.items()))
            embed.add_field(name="Valor à vista", value=f"``R${campoData['preco']}``", inline=True)
            embed.add_field(name="Restam", value=f"``{len(campoData['estoque'])}``", inline=True)

        payload["embeds"].append(embed)

    if para_venda:
        campos = produto.get("campos", {})
        action_row = disnake.ui.ActionRow()
        if len(campos) > 1:
            options = [disnake.SelectOption(label=f'{campoData["nome"]}', description=f'R${campoData["preco"]}', value=campoID, emoji=campoData.get("emoji")) for campoID, campoData in campos.items()]
            action_row.add_select(placeholder="Selecione para comprar", custom_id=f"ComprarCampo_{produtoID}", options=options)
        elif len(campos) == 1:
            campoID, campoData = next(iter(campos.items()))
            action_row.add_button(label="Comprar", emoji=campoData.get("emoji") or "🛒", custom_id=f"ComprarProduto_{produtoID}_{campoID}", style=ButtonStyle.green)
        else:
            action_row.add_button(label="Indisponível", emoji="❌", custom_id="indisponivel", disabled=True)
        payload["components"].append(action_row)
        
        db_duvidas = obter_db_duvidas()
        if db_duvidas.get("status") and db_duvidas.get("linkbotao"):
            duvidas_row = disnake.ui.ActionRow()
            duvidas_row.add_button(label=db_duvidas.get("nomebotao", "Dúvidas"), emoji=db_duvidas.get("emoji", "❓"), style=disnake.ButtonStyle.link, url=db_duvidas.get("linkbotao"))
            payload["components"].append(duvidas_row)
            
    if not payload.get("embeds"): payload.pop("embeds")
    
    return payload