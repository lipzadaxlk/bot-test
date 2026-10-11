import disnake
from disnake import *
from disnake.ext import commands

import shutil
import os

import json
import random
import string
import asyncio
from datetime import *

# Imports para visuais e funcionalidades
from Functions.CarregarEmojis import *
from Functions.Config.FormasPagamentos import (
    MercadoPagoPagamento, 
    EfiBankPagamento, 
    SemiAutoPagamento, 
    AsaasPagamento,
    PicPayPagamento,
    PagBankPagamento,
    LivePixPagamento,
    InterPagamento,
    NubankImapPagamento,
    IMAPBankPagamento,
    ObterFormasPagamento
)
from Functions.Config.FormasPagamento.Mensagens import ObterMensagemLogs
from Functions.Config.Produto import ObterProduto, ObterCampo, ObterCupom, SincronizarMensagens
from Functions.VerificarPerms import verificar_permissao
from Functions.VendaInfo import ObterVenda, ObterVendaPainel


# Aqui ele registra as tasks (asyncio) que contam 10 minutos
# para apagar o carrinho. Ele encontra essa task e cancela
# se cada passo for concluido, como produto aprovado, etc.
tasks = {} # tasks => apagar carrinho 
tasksPagamento = {} # pagamento => verificar pagamento

def ObterDatabase():
    with open("Database/Vendas/produtos.json", encoding='utf-8') as f:
        db = json.load(f)
        return db

def ObterProduto(produtoID):
    try:
        with open("Database/Vendas/produtos.json", encoding='utf-8') as f:
            db = json.load(f)
            return db.get(produtoID)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def ObterCampo(produtoID, campoID):
    produto = ObterProduto(produtoID)
    if produto:
        return produto.get("campos", {}).get(campoID)
    return None

def ObterCarrinho(carrinhoID):
    try:
        with open("Database/Vendas/carrinhos.json", encoding='utf--8') as f:
            db = json.load(f)
            return db.get(carrinhoID)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def ObterCupom(produtoID, cupom):
    produto = ObterProduto(produtoID)
    if produto:
        return produto.get("cupons", {}).get(cupom)
    return None

def GerarString():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=13))

def ObterVenda(vendaID):
    with open("Database/Vendas/historicos.json", encoding='utf-8') as f:
        db = json.load(f)
        venda = db[vendaID]
        return venda

class Logs():
    async def EnviarLogs(inter: disnake.MessageInteraction, content: str, embed: disnake.Embed, components: tuple, files=None):
        with open("Database/Server/canais.json", encoding='utf-8') as f:
            db = json.load(f)
        
        if not db.get("logs"): return

        try: channel = inter.guild.get_channel(int(db["logs"]))
        except: return

        if channel:
            try: await channel.send(content=content, embed=embed, components=components, files=files)
            except: pass

class Pagamentos():
    @staticmethod
    def SalvarPagamento(carrinho, carrinhoID):
        with open("Database/Vendas/carrinhos.json", "r+", encoding='utf-8') as f:
            db = json.load(f)
            db[carrinhoID] = carrinho
            f.seek(0)
            json.dump(db, f, indent=4)
            f.truncate()

    @staticmethod
    def GerarPagamento(carrinhoID: str):
        fp = ObterFormasPagamento()
        carrinho = ObterCarrinho(carrinhoID)
        valor = float(carrinho["info"]["valorFinal"])
        
        payment_methods = [
            ("mercadopago", MercadoPagoPagamento), ("efi", EfiBankPagamento), ("asaas", AsaasPagamento),
            ("pagbank", PagBankPagamento), ("livepix", LivePixPagamento), ("inter", InterPagamento),
            ("picpay", PicPayPagamento), ("nubank_imap", NubankImapPagamento), ("itau_imap", IMAPBankPagamento),
            ("santander_imap", IMAPBankPagamento), ("bradesco_imap", IMAPBankPagamento),
            ("c6_imap", IMAPBankPagamento), ("semiauto", SemiAutoPagamento),
        ]
        
        for method_key, payment_class in payment_methods:
            if not fp.get(method_key, {}).get("habilitado"): continue
            
            try:
                if method_key == "mercadopago":
                    qr_code, qrcodeURL, payment = payment_class.GerarPagamento(valor)
                    if qr_code:
                        carrinho["info"]["pagamento"].update({"metodo": "MercadoPago", "url": qrcodeURL, "paymentID": payment, "copiacola": qr_code})
                        Pagamentos.SalvarPagamento(carrinho, carrinhoID); return "MercadoPago"
                elif method_key == "efi":
                    qr_code, qrcodeURL, txid = payment_class.GerarPagamento(valor)
                    if qr_code:
                        carrinho["info"]["pagamento"].update({"metodo": "EfiBank", "url": qrcodeURL, "txid": txid, "copiacola": qr_code})
                        Pagamentos.SalvarPagamento(carrinho, carrinhoID); return "EfiBank"
                elif method_key == "asaas":
                    qr_code, qrcodeURL, payment_id = payment_class.GerarPagamento(valor)
                    if qr_code:
                        carrinho["info"]["pagamento"].update({"metodo": "Asaas", "url": qrcodeURL, "paymentID": payment_id, "copiacola": qr_code})
                        Pagamentos.SalvarPagamento(carrinho, carrinhoID); return "Asaas"
                elif method_key == "pagbank":
                    qr_code, qrcodeURL, order_id = payment_class.GerarPagamento(valor)
                    if qr_code:
                        carrinho["info"]["pagamento"].update({"metodo": "PagBank", "url": qrcodeURL, "orderID": order_id, "copiacola": qr_code})
                        Pagamentos.SalvarPagamento(carrinho, carrinhoID); return "PagBank"
                elif method_key == "livepix":
                    qr_code, qrcodeURL, payment_id = payment_class.GerarPagamento(valor)
                    if qr_code:
                        carrinho["info"]["pagamento"].update({"metodo": "LivePix", "url": qrcodeURL, "paymentID": payment_id, "copiacola": qr_code})
                        Pagamentos.SalvarPagamento(carrinho, carrinhoID); return "LivePix"
                elif method_key == "inter":
                    qr_code, qrcodeURL, txid = payment_class.GerarPagamento(valor)
                    if qr_code:
                        carrinho["info"]["pagamento"].update({"metodo": "BancoInter", "url": qrcodeURL, "txid": txid, "copiacola": qr_code})
                        Pagamentos.SalvarPagamento(carrinho, carrinhoID); return "BancoInter"
                elif method_key == "picpay":
                    qr_code, qrcodeURL, payment_id = payment_class.GerarPagamento(valor)
                    if qr_code:
                        carrinho["info"]["pagamento"].update({"metodo": "PicPay", "url": qrcodeURL, "paymentID": payment_id, "copiacola": qr_code})
                        Pagamentos.SalvarPagamento(carrinho, carrinhoID); return "PicPay"
                elif method_key == "nubank_imap":
                    qr_code, qrcodeURL, valor_unico = payment_class.GerarPixUnico(carrinho)
                    if qr_code:
                        carrinho["info"]["pagamento"].update({"metodo": "NubankIMAP", "url": qrcodeURL, "valor_unico": valor_unico, "copiacola": qr_code})
                        Pagamentos.SalvarPagamento(carrinho, carrinhoID); return "NubankIMAP"
                elif method_key.endswith("_imap"):
                    banco_key = method_key.replace("_imap", "")
                    qr_code, qrcodeURL, valor_unico = payment_class.GerarPixUnico(carrinho, banco_key)
                    if qr_code:
                        carrinho["info"]["pagamento"].update({"metodo": f"{banco_key.capitalize()}IMAP", "url": qrcodeURL, "valor_unico": valor_unico, "copiacola": qr_code})
                        Pagamentos.SalvarPagamento(carrinho, carrinhoID); return f"{banco_key.capitalize()}IMAP"
                elif method_key == "semiauto":
                    chave, qr_code = payment_class.GerarPagamento()
                    if chave:
                        carrinho["info"]["pagamento"].update({"metodo": "SemiAuto", "copiacola": chave, "url": qr_code})
                        Pagamentos.SalvarPagamento(carrinho, carrinhoID); return "SemiAuto"
            except Exception as e:
                print(f"DEBUG: Erro ao tentar {method_key}: {e}")
                continue

class Cupom():
    @staticmethod
    def Estatisticas(produtoID, nome, carrinhoID):
        carrinho = ObterCarrinho(carrinhoID)
        if not carrinho: return
        with open("Database/Vendas/produtos.json", "r+", encoding='utf-8') as f:
            db = json.load(f)
            try:
                if produtoID in db and nome in db[produtoID]["cupons"]:
                    valor_antes = float(carrinho["info"]["cupom"]["valorAntes"])
                    valor_final = float(carrinho["info"]["valorFinal"])
                    db[produtoID]["cupons"][nome]["estatistics"]["uses"] += 1
                    db[produtoID]["cupons"][nome]["estatistics"]["economizado"] += (valor_antes - valor_final)
                    f.seek(0)
                    json.dump(db, f, indent=4)
                    f.truncate()
            except (KeyError, IndexError):
                pass


class Carrinho():
    class EditarQuantidade(disnake.ui.Modal):
        def __init__(self, carrinhoID):
            self.carrinhoID = carrinhoID
            carrinho = ObterCarrinho(carrinhoID)
            components = [
                disnake.ui.TextInput(
                    label="Quantidade",
                    placeholder="Coloque um valor inteiro",
                    custom_id="quantidade",
                    value=f"{carrinho['info']['quantidade']}",
                    style=TextInputStyle.short,
                ),
            ]
            super().__init__(title="Alterar quantidade", components=components)

        async def callback(self, inter: disnake.ModalInteraction):
                try:
                    quant = int(inter.text_values["quantidade"])
                    if quant <= 0:
                        await inter.response.send_message(f"{negativo} A quantidade deve ser um número positivo.", ephemeral=True)
                        return
                except:
                        await inter.response.send_message(f"{negativo} A quantidade deve ser um número positivo.", ephemeral=True)
                        return
                
                carrinho = ObterCarrinho(self.carrinhoID)
                if not Carrinho.VerificarQuantidade(carrinho["produtoID"], carrinho["campoID"], quant):
                    await inter.response.send_message(f"{negativo} Quantidade inválida ou fora de estoque.", ephemeral=True)
                    return

                with open("Database/Vendas/carrinhos.json", "r+", encoding='utf-8') as f:
                    db = json.load(f)

                    carrinho = db[self.carrinhoID]
                    campo = ObterCampo(carrinho["produtoID"], carrinho["campoID"])
                    valor_total = round(int(quant) * float(campo["preco"]), 2)
                    carrinho['info']['cupom']['valorAntes'] = f"{valor_total:.2f}"

                    if carrinho["info"]["cupom"]["usado"]:
                        cupom = ObterCupom(carrinho["produtoID"], carrinho["info"]["cupom"]["usado"])
                        if cupom:
                            porcentagem = cupom.get("porcentagem", 0)
                            desconto = (valor_total * porcentagem) / 100 
                            valor_total -= round(desconto, 2)

                    db[self.carrinhoID]["info"]["quantidade"] = quant
                    db[self.carrinhoID]["info"]["valorFinal"] = "{:.2f}".format(valor_total)

                    f.seek(0)
                    json.dump(db, f, indent=4)
                    f.truncate()

                embed, components = await Carrinho.Mensagens.ObterMensagemCarrinho(inter, self.carrinhoID)
                await inter.response.edit_message(embed=embed, components=components)

    class AlterarCupom(disnake.ui.Modal):
        def __init__(self, carrinhoID):
            self.carrinhoID = carrinhoID
            components = [
                disnake.ui.TextInput(
                    label="Cupom",
                    placeholder="Coloque o valor do cupom",
                    custom_id="cupom",
                    style=TextInputStyle.short,
                ),
            ]
            super().__init__(title="Adicionar Cupom", components=components)

        async def callback(self, inter: disnake.ModalInteraction):
            carrinho = ObterCarrinho(self.carrinhoID)
            produtoID = carrinho["produtoID"]
            cupomInserido = inter.text_values["cupom"]

            cupomInfo = ObterCupom(produtoID, cupomInserido)

            if not cupomInfo:
                return await inter.response.send_message(f"{negativo} Cupom inserido não encontrado `{cupomInserido}`", ephemeral=True)

            if cupomInfo.get("estatistics", {}).get("uses", 0) >= cupomInfo.get("usage", {}).get("maxuses", float('inf')):
                return await inter.response.send_message(f"{negativo} O cupom `{cupomInserido}` já atingiu seu limite de usos.", ephemeral=True)

            subtotal = float(carrinho['info']['quantidade']) * float(ObterCampo(produtoID, carrinho['campoID'])['preco'])
            
            minValue = cupomInfo.get("usage", {}).get("minvalue")
            if minValue and subtotal < float(minValue):
                await inter.response.send_message(f"{negativo} Este cupom requer um valor mínimo de R$ {minValue}.", ephemeral=True)
                return

            if carrinho["info"]["cupom"]["usado"]:
                await inter.response.send_message(f"{negativo} Um cupom já está sendo utilizado. Para usar outro, crie outro carrinho.", ephemeral=True)
                return

            desconto_percent = cupomInfo.get("porcentagem", 0)
            desconto = subtotal * (desconto_percent / 100)
            valorComDesconto = subtotal - desconto
            
            with open("Database/Vendas/carrinhos.json", "r+", encoding='utf-8') as f:
                db = json.load(f)
                carrinho_db = db[self.carrinhoID]
                carrinho_db["info"]["valorFinal"] = "{:.2f}".format(valorComDesconto)
                carrinho_db["info"]["cupom"]["usado"] = cupomInserido
                carrinho_db["info"]["cupom"]["valorAntes"] = "{:.2f}".format(subtotal)
                f.seek(0)
                json.dump(db, f, indent=4)
                f.truncate()

            embed, components = await Carrinho.Mensagens.ObterMensagemCarrinho(inter, self.carrinhoID)
            await inter.response.edit_message(embed=embed, components=components)

    class Mensagens():
        @staticmethod
        def CarregarPersonalizacao():
            """Carrega as personalizações de embeds salvas."""
            try:
                with open("Database/Vendas/configuracao_loja.json", "r", encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get("embeds_personalizadas", {})
            except (FileNotFoundError, json.JSONDecodeError):
                return {}
        
        @staticmethod
        async def ObterMensagemCarrinho(inter: disnake.MessageInteraction, carrinhoID: str):
            carrinho = ObterCarrinho(carrinhoID)
            produto = ObterProduto(carrinho["produtoID"])
            campo = ObterCampo(carrinho["produtoID"], carrinho["campoID"])
            
            custom_embeds = Carrinho.Mensagens.CarregarPersonalizacao()
            
            if "revisao" in custom_embeds:
                custom = custom_embeds["revisao"]
                embed = disnake.Embed(
                    title=custom.get("titulo") or "## Revisão do pedido",
                    description=custom.get("descricao") or "",
                    timestamp=datetime.now(),
                    color=disnake.Color(0x00FFFF)
                )
            else:
                embed = disnake.Embed(
                    description="## Revisão do pedido",
                    timestamp=datetime.now(),
                    color=disnake.Color(0x00FFFF)
                )
            
            embed.set_author(name=f"Carrinho | {campo['nome']}", icon_url=inter.author.avatar)
            
            estoque_str = "Ilimitado" if campo.get("is_subscription", False) else str(len(campo.get("estoque", [])))

            if carrinho["info"]["cupom"]["usado"]:
                embed.add_field(name="Valor à vista", value=f"~~``R${carrinho['info']['cupom']['valorAntes']}``~~\n``R${carrinho['info']['valorFinal']}``", inline=True)
            else: 
                embed.add_field(name="Valor à vista", value=f"``R${carrinho['info']['valorFinal']}``", inline=True)

            embed.add_field(name="Quantidade", value=f"``{carrinho['info']['quantidade']}``", inline=True)
            embed.add_field(name="Em estoque", value=f"``{estoque_str}``", inline=True)
            embed.add_field(name="Informações do pedido", value=f"``{carrinho['info']['quantidade']}x {produto['nome']} - {campo['nome']}``", inline=False)
            embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon)

            components = [
                disnake.ui.Button(style=disnake.ButtonStyle.green, label="Prosseguir para pagamento", emoji=arrow, custom_id=f"ProsseguirPagamento_{carrinhoID}"),
                disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Editar", emoji=editar, custom_id=f"EditarQuantidade_{carrinhoID}"),
                disnake.ui.Button(label="Utilizar Cupom", emoji=cupom, custom_id=f"UsarCupom_{carrinhoID}"),
                disnake.ui.Button(style=disnake.ButtonStyle.red, label="Cancelar pedido", emoji=apagar, custom_id=f"CancelarCarrinho_{carrinhoID}")
            ]

            return embed, components

        @staticmethod
        async def ObterMensagemCarrinhoCancelado(inter: disnake.MessageInteraction, carrinhoID: str):
            custom_embeds = Carrinho.Mensagens.CarregarPersonalizacao()
            
            if "cancelado" in custom_embeds:
                custom = custom_embeds["cancelado"]
                embed = disnake.Embed(
                    title=custom.get("titulo") or f"{carrinhoCancelado} Carrinho fechado",
                    description=custom.get("descricao") or "O seu carrinho foi encerrado com sucesso.\nCaso precise realizar novas compras ou revisar seus itens, sinta-se à vontade para abrir um novo carrinho a qualquer momento.",
                    timestamp=datetime.now(),
                    color=disnake.Color(0xe31e10)
                )
            else:
                embed = disnake.Embed(
                    title=f"{carrinhoCancelado} Carrinho fechado",
                    description="O seu carrinho foi encerrado com sucesso.\nCaso precise realizar novas compras ou revisar seus itens, sinta-se à vontade para abrir um novo carrinho a qualquer momento.",
                    timestamp=datetime.now(),
                    color=disnake.Color(0xe31e10)
                )
            
            embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon)
            return embed, None

        @staticmethod
        async def ObterMensagemCarrinhoExpirado(inter: disnake.MessageInteraction):
            custom_embeds = Carrinho.Mensagens.CarregarPersonalizacao()
            
            if "cancelado" in custom_embeds:
                custom = custom_embeds["cancelado"]
                embed = disnake.Embed(
                    title=custom.get("titulo") or f"{carrinhoCancelado} Pedido cancelado",
                    description=custom.get("descricao") or "",
                    timestamp=datetime.now(),
                    color=disnake.Color.red()
                )
            else:
                embed = disnake.Embed(
                    title=f"{carrinhoCancelado} Pedido cancelado",
                    timestamp=datetime.now(),
                    color=disnake.Color.red()
                )
            
            embed.add_field(name="Razão", value="O tempo máximo (`10 minutos`) foi excedido.")
            return embed

        @staticmethod
        def ObterMensagemPagamento(inter: disnake.MessageInteraction, carrinhoID: str, metodo_pagamento: str):
            carrinho = ObterCarrinho(carrinhoID)
            produto = ObterProduto(carrinho["produtoID"])
            campo = ObterCampo(carrinho["produtoID"], carrinho["campoID"])
            
            custom_embeds = Carrinho.Mensagens.CarregarPersonalizacao()
            
            if "pagamento" in custom_embeds:
                custom = custom_embeds["pagamento"]
                embed = disnake.Embed(
                    title=custom.get("titulo") or f"{carrinho} Pagamento via {metodo_pagamento}",
                    description=custom.get("descricao") or "Efetue o pagamento utilizando o código PIX abaixo.",
                    timestamp=datetime.now(),
                    color=disnake.Color(0x00FFFF)
                )
            else:
                embed = disnake.Embed(
                    title=f"{carrinho} Pagamento via {metodo_pagamento}",
                    description="Efetue o pagamento utilizando o código PIX abaixo.",
                    timestamp=datetime.now(),
                    color=disnake.Color(0x00FFFF)
                )
            
            embed.set_author(name=f"Pagamento | {campo['nome']}", icon_url=inter.author.avatar)
            embed.add_field(name="Valor", value=f"``R$ {carrinho['info']['valorFinal']}``", inline=True)
            embed.add_field(name="Status", value="``Aguardando pagamento``", inline=True)
            embed.add_field(name="Método", value=f"``{metodo_pagamento}``", inline=True)
            embed.add_field(name="Produto", value=f"``{carrinho['info']['quantidade']}x {produto['nome']} - {campo['nome']}``", inline=False)
            embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon)
            
            return embed

        @staticmethod
        def ObterMensagemEntrega(inter: disnake.MessageInteraction, carrinhoID: str):
            carrinho = ObterCarrinho(carrinhoID)
            produto = ObterProduto(carrinho["produtoID"])
            campo = ObterCampo(carrinho["produtoID"], carrinho["campoID"])
            
            custom_embeds = Carrinho.Mensagens.CarregarPersonalizacao()
            
            if "entrega" in custom_embeds:
                custom = custom_embeds["entrega"]
                embed = disnake.Embed(
                    title=custom.get("titulo") or f"{check} Pagamento aprovado",
                    description=custom.get("descricao") or "Seu produto foi entregue com sucesso! Verifique sua DM.",
                    timestamp=datetime.now(),
                    color=disnake.Color.green()
                )
            else:
                embed = disnake.Embed(
                    title=f"{check} Pagamento aprovado",
                    description="Seu produto foi entregue com sucesso! Verifique sua DM.",
                    timestamp=datetime.now(),
                    color=disnake.Color.green()
                )
            
            embed.set_author(name=f"Entrega | {campo['nome']}", icon_url=inter.author.avatar)
            embed.add_field(name="Produto", value=f"``{produto['nome']} - {campo['nome']}``", inline=False)
            embed.add_field(name="Quantidade", value=f"``{carrinho['info']['quantidade']}``", inline=True)
            embed.add_field(name="Valor pago", value=f"``R$ {carrinho['info']['valorFinal']}``", inline=True)
            embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon)
            
            return embed

        @staticmethod
        def ObterMensagemSemEstoque(inter: disnake.MessageInteraction, produtoID: str, campoID: str):
            produto = ObterProduto(produtoID)
            campo = ObterCampo(produtoID, campoID)
            
            custom_embeds = Carrinho.Mensagens.CarregarPersonalizacao()
            
            if "sem_estoque" in custom_embeds:
                custom = custom_embeds["sem_estoque"]
                embed = disnake.Embed(
                    title=custom.get("titulo") or f"{negativo} Produto indisponível",
                    description=custom.get("descricao") or "Não há estoque disponível no momento. Você pode ativar as notificações para ser avisado quando houver reposição.",
                    timestamp=datetime.now(),
                    color=disnake.Color.red()
                )
            else:
                embed = disnake.Embed(
                    title=f"{negativo} Produto indisponível",
                    description="Não há estoque disponível no momento. Você pode ativar as notificações para ser avisado quando houver reposição.",
                    timestamp=datetime.now(),
                    color=disnake.Color.red()
                )
            
            embed.set_author(name=f"Estoque | {campo['nome']}", icon_url=inter.author.avatar)
            embed.add_field(name="Produto", value=f"``{produto['nome']} - {campo['nome']}``", inline=False)
            embed.add_field(name="Status", value="``Sem estoque``", inline=True)
            embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon)
            
            return embed

    @staticmethod
    def VerificarValores(carrinhoID) -> bool:
        carrinho = ObterCarrinho(carrinhoID)
        campo = ObterCampo(carrinho["produtoID"], carrinho["campoID"])
        condicoes = campo.get("condicoes", {})

        valorFinal = float(carrinho["info"]["valorFinal"])
        valorMin = condicoes.get("valorMin")
        valorMax = condicoes.get("valorMax")

        if valorMin is not None and valorFinal < float(valorMin):
            return False

        if valorMax is not None and valorFinal > float(valorMax):
            return False

        return True
    
    @staticmethod
    def VerificarID(inter: disnake.MessageInteraction, produtoID, campoID):
        campo = ObterCampo(produtoID, campoID)
        if not campo: return False
        try:
            restricted_roles_ids = {str(role_id) for role_id in campo.get("condicoes", {}).get("idCargo", [])}
            if not restricted_roles_ids: return True
            user_roles_ids = {str(role.id) for role in inter.author.roles}
            return not user_roles_ids.intersection(restricted_roles_ids)
        except: return True
    
    @staticmethod
    def VerificarQuantidade(produtoID, campoID, quantidade):
        campo = ObterCampo(produtoID, campoID)
        if not campo: return False
        if campo.get("is_subscription", False):
            return True
        return quantidade <= len(campo.get("estoque", []))

    @staticmethod
    def RegistrarAssinatura(user_id, carrinho_id, produto_id, campo_id):
        campo = ObterCampo(produto_id, campo_id)
        if not campo or not campo.get("is_subscription"):
            return

        now = datetime.now()
        expiracao = now + timedelta(days=campo["subscription_details"].get("duration_days", 30))
        nova_assinatura = {
            "assinatura_id": carrinho_id, "produto_id": produto_id, "campo_id": campo_id,
            "nome_produto": ObterProduto(produto_id)['nome'], "nome_campo": campo['nome'],
            "data_ativacao": now.isoformat(), "data_expiracao": expiracao.isoformat(),
            "id_cargo_assinatura": campo["subscription_details"].get("role_id")
        }

        filepath = "Database/Vendas/AssinaturasOn.json"
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        try:
            with open(filepath, "r", encoding='utf-8') as f: db = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError): db = {}

        user_id_str = str(user_id)
        if user_id_str not in db: db[user_id_str] = []
        db[user_id_str].append(nova_assinatura)
        with open(filepath, "w", encoding='utf-8') as f: json.dump(db, f, indent=4)

    @staticmethod
    async def AdicionarCargos(inter: disnake.MessageInteraction, carrinhoID):
        carrinho = ObterCarrinho(carrinhoID)
        user = inter.guild.get_member(int(carrinho["server"]["usuario"]))
        campo = ObterCampo(carrinho["produtoID"], carrinho["campoID"])

        with open("Database/Server/cargos.json", encoding='utf-8') as f:
            cargos = json.load(f)
        
        if cargos.get("cliente"):
            try:
                cargo = inter.guild.get_role(int(cargos["cliente"]))
                if cargo: await user.add_roles(cargo, reason="[Ease Bot] Cargo cliente")
            except Exception as e:
                print(f"Erro ao adicionar cargo 'cliente': {e}")
                pass
        
        for cargoID in campo.get("cargos", {}).get("add", []):
            try:
                cargo = inter.guild.get_role(int(cargoID))
                if cargo: await user.add_roles(cargo, reason=f"[Ease Bot] Cargo | Campo: {campo['nome']}")
            except Exception as e: print(f"Erro ao adicionar cargo {cargoID}: {e}")
        
        for cargoID in campo.get("cargos", {}).get("rem", []):
            try:
                cargo = inter.guild.get_role(int(cargoID))
                if cargo: await user.remove_roles(cargo, reason=f"[Ease Bot] Cargo | Campo: {campo['nome']}")
            except Exception as e: print(f"Erro ao remover cargo {cargoID}: {e}")
        
        if campo.get("is_subscription"):
            sub_details = campo.get("subscription_details", {})
            sub_role_id = sub_details.get("role_id")
            if sub_role_id:
                try:
                    cargo = inter.guild.get_role(int(sub_role_id))
                    if cargo: await user.add_roles(cargo, reason=f"[Ease Bot] Ativação da assinatura: {campo.get('nome')}")
                except Exception as e: print(f"Erro ao adicionar cargo de assinatura {sub_role_id}: {e}")
    
    @staticmethod
    async def Cancelar(inter: disnake.MessageInteraction, carrinhoID: str, send=True):
        carrinho = ObterCarrinho(carrinhoID)
        await Carrinho.CancelarPagamento(carrinhoID)
        await Carrinho.CancelarCarrinho(carrinhoID)
        
        if not carrinho: return

        produto = ObterProduto(carrinho["produtoID"])
        campo = ObterCampo(carrinho["produtoID"], carrinho["campoID"])

        try:
            channel = inter.guild.get_channel_or_thread(carrinho["server"]["carrinho"])
            await channel.delete(reason=f"[Ease Bot] Apagar carrinho: {inter.author.id}")
        except: pass

        with open("Database/Vendas/carrinhos.json", "r+", encoding='utf-8') as f:
            db = json.load(f)
            if carrinhoID in db:
                del db[carrinhoID]
                f.seek(0)
                json.dump(db, f, indent=4)
                f.truncate()
        
        if send:
            embed, _ = await Carrinho.Mensagens.ObterMensagemCarrinhoCancelado(inter, carrinhoID)
            embed.add_field(name="Informações do pedido", value=f"``{carrinho['info']['quantidade']}x {produto['nome']} - {campo['nome']}``", inline=False)
            embed.add_field(name="ID do pedido", value=f"`{carrinhoID}`")
            try:
                user = await inter.bot.fetch_user(carrinho['server']['usuario'])
                await user.send(embed=embed)
            except: pass
            
            embed.description = f"O carrinho do usuário {inter.author.mention} (`{inter.author.id}`) foi cancelado.\nConsulte as informações do carrinho abaixo"
            embed.add_field(name="Usuário", value=f"{inter.author.mention}", inline=False)
            try: await Logs.EnviarLogs(inter, content=None, embed=embed, components=None)
            except: pass

        await SincronizarMensagens(inter, carrinho["produtoID"])

    @staticmethod
    async def CriarCarrinho(inter: disnake.MessageInteraction, produtoID, campoID):
        await inter.response.send_message(f"{carregarAnimado} Aguarde, estamos criando seu carrinho", ephemeral=True)

        produto = ObterProduto(produtoID)
        campo = ObterCampo(produtoID, campoID)
        if not produto or not campo: 
            await inter.edit_original_message(f"{negativo} Produto ou campo não encontrados")
            await SincronizarMensagens(inter, produtoID)
            return

        await inter.edit_original_message(f"{carregarAnimado} Verificando permissões")
        if not Carrinho.VerificarID(inter, produtoID, campoID):
            return await inter.edit_original_message(f"{negativo} Você não tem permissão para comprar este item.")

        await inter.edit_original_message(f"{carregarAnimado} Verificando estoque")
        if not Carrinho.VerificarQuantidade(produtoID, campoID, 1):
            embed = Carrinho.Mensagens.ObterMensagemSemEstoque(inter, produtoID, campoID)
            return await inter.edit_original_message(
                content="",
                embed=embed,
                components=[
                    disnake.ui.Button(
                        style=disnake.ButtonStyle.blurple,
                        label="Ativar atualizações de estoque",
                        emoji=sino,
                        custom_id=f"AtivarNotificacoesEstoque_{produtoID}_{campoID}"
                    )
                ]
            )
        
        with open("Database/Vendas/carrinhos.json", encoding='utf-8') as f:
            db = json.load(f)

        await inter.edit_original_message(f"{carregarAnimado} Verificando carrinhos existentes")
        carrinho_existente = next((cid for cid, cdata in db.items() if isinstance(cdata, dict) and str(cdata.get("server", {}).get("usuario")) == str(inter.author.id)), None)
        if carrinho_existente:
            try:
                channel = await inter.bot.fetch_channel(db[carrinho_existente]["server"]["carrinho"])
                return await inter.edit_original_message(
                    content=f"{negativo} Você já possui um carrinho aberto. Por favor, finalize ou cancele o carrinho existente.",
                    components=[disnake.ui.Button(label="Ir para o Carrinho", url=channel.jump_url)]
                )
            except (disnake.NotFound, disnake.Forbidden, KeyError):
                await Carrinho.Cancelar(inter, carrinho_existente, send=False)

        await inter.edit_original_message(f"{carregarAnimado} Criando seu carrinho")
        carrinho_nome = f"🛒・{inter.author.name}"
        CarrinhoID = GerarString()

        try:
            topic = await inter.channel.create_thread(
                name=carrinho_nome,
                type=disnake.ChannelType.private_thread,
                invitable=False
            )
        except disnake.Forbidden:
            return await inter.edit_original_message(content=f"{negativo} **ERRO DE PERMISSÃO!**\nNão consigo criar um canal para o seu carrinho. Peça a um administrador para verificar se eu tenho a permissão de `Criar Tópicos Privados` neste canal.")
        except disnake.HTTPException as e:
            return await inter.edit_original_message(content=f"{negativo} Ocorreu um erro de comunicação com o Discord. Tente novamente.\n`{e}`")


        db[CarrinhoID] = {
            "produtoID": produtoID, "campoID": campoID, "carrinhoID": CarrinhoID,
            "server": {"produtoURL": inter.channel.id, "carrinho": topic.id, "usuario": inter.author.id},
            "info": {
                "quantidade": 1, "valorFinal": f"{float(campo['preco']):.2f}",
                "pagamento": {},
                "cupom": {"usado": None, "valorAntes": f"{float(campo['preco']):.2f}"}
            }
        }

        with open("Database/Vendas/carrinhos.json", "w", encoding='utf-8') as f:
            json.dump(db, f, indent=4)

        embed, components = await Carrinho.Mensagens.ObterMensagemCarrinho(inter, CarrinhoID)
        await topic.send(inter.author.mention, embed=embed, components=components)

        await inter.edit_original_message(f"{positivo} Carrinho criado com êxito: {topic.jump_url}", components=[
            disnake.ui.Button(label="Ir para o carrinho", url=topic.jump_url)
        ])
        tasks[CarrinhoID] = asyncio.create_task(Carrinho.IniciarCountdownCarrinho(carrinho_id=CarrinhoID, inter=inter))

    @staticmethod
    async def CancelarCarrinho(carrinhoID):
        if carrinhoID in tasks:
            tasks[carrinhoID].cancel()
            del tasks[carrinhoID]

    @staticmethod
    async def CancelarPagamento(carrinhoID):
        if carrinhoID in tasksPagamento:
            tasksPagamento[carrinhoID].cancel()
            del tasksPagamento[carrinhoID]

    @staticmethod
    async def IniciarCountdownCarrinho(carrinho_id: str, inter: disnake.MessageInteraction):
        # Substitua o tempo fixo pela configuração
        try:
            with open("Database/Vendas/configuracao_loja.json", "r", encoding='utf-8') as f:
                config = json.load(f)
            tempo_minutos = config.get("tempo_fechamento", 10)
        except (FileNotFoundError, json.JSONDecodeError):
            tempo_minutos = 10
        
        if tempo_minutos <= 0:
            return

        countdown_time = tempo_minutos * 60
        await asyncio.sleep(countdown_time)
        if ObterCarrinho(carrinho_id):
            await Carrinho.Cancelar(inter, carrinho_id)

    @staticmethod
    async def ProsseguirPagamento(inter: disnake.MessageInteraction, carrinhoID: str):
        carrinho = ObterCarrinho(carrinhoID)
        await Carrinho.CancelarCarrinho(carrinhoID)
        await inter.response.edit_message(f"{carregarAnimado} Aguarde um momento...", embed=None, components=None)

        if not Carrinho.VerificarQuantidade(carrinho["produtoID"], carrinho["campoID"], carrinho["info"]["quantidade"]):
            embed, components = await Carrinho.Mensagens.ObterMensagemCarrinho(inter, carrinhoID)
            await inter.edit_original_message("", embed=embed, components=components)
            await inter.followup.send(f"{negativo} A quantidade excede o estoque disponível.", ephemeral=True)
            return

        if not Carrinho.VerificarValores(carrinhoID):
            embed, components = await Carrinho.Mensagens.ObterMensagemCarrinho(inter, carrinhoID)
            await inter.edit_original_message("", embed=embed, components=components)
            await inter.followup.send(f"{negativo} O valor do carrinho excede/não alcança o limite definido para o produto.", ephemeral=True)
            return
        
        if float(carrinho["info"]["valorFinal"]) <= 0:
            await Carrinho.EntregarPedido(inter, carrinhoID)
            return

        forma = Pagamentos.GerarPagamento(carrinhoID)
        if not forma:
            embed, components = await Carrinho.Mensagens.ObterMensagemCarrinho(inter, carrinhoID)
            await inter.edit_original_message("", embed=embed, components=components)
            await inter.followup.send(f"{negativo} Nenhum método de pagamento disponível no momento.", ephemeral=True)
            return
        
        carrinho = ObterCarrinho(carrinhoID)
        embed = Carrinho.Mensagens.ObterMensagemPagamento(inter, carrinhoID, forma)
        
        components = [
            disnake.ui.Button(label="Código Copia e Cola", emoji=copypast, custom_id=f"CodigoCopiaCola_{carrinhoID}")
        ]

        payment_url = carrinho.get('info', {}).get('pagamento', {}).get('url')
        if payment_url:
            components.append(disnake.ui.Button(label="QR Code", emoji=qrcode, url=payment_url))
        
        components.append(disnake.ui.Button(style=disnake.ButtonStyle.red, label="Cancelar", emoji=apagar, custom_id=f"CancelarCarrinho_{carrinhoID}"))
        
        metodos_semi_auto = ["SemiAuto", "NubankIMAP", "ItauIMAP", "SantanderIMAP", "BradescoIMAP", "C6IMAP"]
        if forma in metodos_semi_auto:
            components.insert(1, disnake.ui.Button(label="Aprovar Manual", style=ButtonStyle.success, custom_id=f"AprovarCarrinho_{carrinhoID}"))
        
        await inter.edit_original_message(embed=embed, components=components)
        
        tasks[carrinhoID] = asyncio.create_task(Carrinho.IniciarCountdownCarrinho(carrinhoID, inter))
        
        verification_methods = {
            "MercadoPago": Carrinho.VerificarPagamentoMercadoPago, "EfiBank": Carrinho.VerificarPagamentoEfiBank,
            "Asaas": Carrinho.VerificarPagamentoAsaas, "PagBank": Carrinho.VerificarPagamentoPagBank,
            "LivePix": Carrinho.VerificarPagamentoLivePix, "BancoInter": Carrinho.VerificarPagamentoBancoInter,
        }
        
        if forma in verification_methods:
            tasksPagamento[carrinhoID] = asyncio.create_task(verification_methods[forma](inter, carrinhoID))
    
    @staticmethod
    async def EntregarPedido(inter: disnake.MessageInteraction, carrinhoID: str):
        await Carrinho.CancelarCarrinho(carrinhoID)
        await Carrinho.CancelarPagamento(carrinhoID)
        
        carrinho = ObterCarrinho(carrinhoID)
        if not carrinho: return

        await inter.edit_original_message(f"**Produto pago com sucesso.**\nAguarde um momento enquanto separamos seu pedido.", embed=None, components=None)
        user = await inter.bot.fetch_user(int(carrinho["server"]["usuario"]))

        produto = ObterProduto(carrinho["produtoID"])
        campo = ObterCampo(carrinho["produtoID"], carrinho["campoID"])
        is_subscription = campo.get("is_subscription", False)

        if is_subscription:
            Carrinho.RegistrarAssinatura(user.id, carrinhoID, carrinho["produtoID"], carrinho["campoID"])
            embed_assinatura = disnake.Embed(
                title=f"{check} Assinatura Ativada",
                description=f"Sua assinatura **{produto['nome']} - {campo['nome']}** foi ativada com sucesso!\n\nSeus benefícios e cargos já foram aplicados no servidor!",
                color=0x2ECC71
            )
            try:
                msg = await user.send(embed=embed_assinatura)
                await inter.edit_original_message(
                    f"**Entrega concluída com sucesso.**\nConsulte seu privado para obter as informações.\nEste carrinho será excluido em <t:{int((datetime.now() + timedelta(seconds=15)).timestamp())}:R>",
                    components=[disnake.ui.Button(label="Acessar Mensagem", url=msg.jump_url)]
                )
            except disnake.Forbidden:
                await inter.channel.send(f"{user.mention}, não foi possível te enviar a confirmação da assinatura na sua DM, pois ela está fechada. Seus cargos já foram aplicados.")
        else:
            if not Carrinho.VerificarQuantidade(carrinho["produtoID"], carrinho["campoID"], carrinho["info"]["quantidade"]):
                embed = Carrinho.Mensagens.ObterMensagemSemEstoque(inter, carrinho["produtoID"], carrinho["campoID"])
                await user.send(embed=embed)
                return

            arquivo_path = Entrega.ObterEstoque(carrinho["info"]["quantidade"], carrinho["produtoID"], carrinho["campoID"])
            embed_entrega = Carrinho.Mensagens.ObterMensagemEntrega(inter, carrinhoID)
            try:
                msg = await user.send(file=disnake.File(arquivo_path, filename="itens_comprados.txt"), embed=embed_entrega)
                await inter.edit_original_message(
                    f"**Entrega concluída com sucesso.**\nConsulte seu privado para obter as informações.\nEste carrinho será excluido em <t:{int((datetime.now() + timedelta(seconds=15)).timestamp())}:R>",
                    components=[disnake.ui.Button(label="Acessar produto", url=msg.jump_url)]
                )
            except disnake.Forbidden:
                await inter.channel.send(content=f"{user.mention} **Não foi possível enviar seu produto na sua DM**\nSalve o produto entregue. O carrinho fecha em `120 segundos`", file=disnake.File(arquivo_path, filename="itens_comprados.txt"), embed=embed_entrega)
            os.remove(arquivo_path)

        await Carrinho.AdicionarCargos(inter, carrinhoID)
        await Entrega.RegistrarEntrega(inter, carrinhoID)
        if carrinho["info"]["cupom"]["usado"]:
            Cupom.Estatisticas(carrinho["produtoID"], carrinho["info"]["cupom"]["usado"], carrinhoID)
        
        await SincronizarMensagens(inter, carrinho["produtoID"])

        await asyncio.sleep(15)
        await Carrinho.Cancelar(inter, carrinhoID, send=False)

    # --- Métodos de Verificação de Pagamento ---
    @staticmethod
    async def VerificarPagamentoMercadoPago(inter, carrinhoID):
        await asyncio.sleep(20)
        for _ in range(120):
            if not carrinhoID in tasksPagamento or not ObterCarrinho(carrinhoID): return await Carrinho.CancelarPagamento(carrinhoID)
            try:
                status = await MercadoPagoPagamento.VerificarPagamento(carrinhoID)
                if status is True: return await Carrinho.EntregarPedido(inter, carrinhoID)
                if status == "cancelled": return await Carrinho.Cancelar(inter, carrinhoID)
            except Exception as e: print(f"ERRO ao verificar pagamento Mercado Pago para {carrinhoID}: {e}")
            await asyncio.sleep(15)
        if carrinhoID in tasksPagamento: await Carrinho.Cancelar(inter, carrinhoID)

    @staticmethod
    async def VerificarPagamentoEfiBank(inter, carrinhoID):
        await asyncio.sleep(20)
        try: txid = ObterCarrinho(carrinhoID)["info"]["pagamento"]["txid"]
        except (KeyError, TypeError): return await Carrinho.CancelarPagamento(carrinhoID)
        for _ in range(180):
            if not carrinhoID in tasksPagamento or not ObterCarrinho(carrinhoID): return await Carrinho.CancelarPagamento(carrinhoID)
            try:
                status = EfiBankPagamento.VerificarPagamento(txid)
                if status == "CONCLUIDA": return await Carrinho.EntregarPedido(inter, carrinhoID)
                if status in ["REMOVIDA_PELO_USUARIO_RECEBEDOR", "REMOVIDA_PELO_PSP"]: return await Carrinho.Cancelar(inter, carrinhoID)
            except Exception as e: print(f"ERRO ao verificar pagamento Efi Bank para {carrinhoID}: {e}")
            await asyncio.sleep(10)
        if carrinhoID in tasksPagamento: await Carrinho.Cancelar(inter, carrinhoID)

    @staticmethod
    async def VerificarPagamentoAsaas(inter, carrinhoID):
        await asyncio.sleep(20)
        payment_id = ObterCarrinho(carrinhoID)["info"]["pagamento"]["paymentID"]
        for _ in range(120):
            if not carrinhoID in tasksPagamento or not ObterCarrinho(carrinhoID): return await Carrinho.CancelarPagamento(carrinhoID)
            try:
                if await AsaasPagamento.VerificarPagamento(payment_id): return await Carrinho.EntregarPedido(inter, carrinhoID)
            except Exception as e: print(f"ERRO ao verificar pagamento Asaas para {carrinhoID}: {e}")
            await asyncio.sleep(15)
        if carrinhoID in tasksPagamento: await Carrinho.Cancelar(inter, carrinhoID)
    
    @staticmethod
    async def VerificarPagamentoPagBank(inter, carrinhoID):
        await asyncio.sleep(20)
        order_id = ObterCarrinho(carrinhoID)["info"]["pagamento"]["orderID"]
        for _ in range(120):
            if not carrinhoID in tasksPagamento or not ObterCarrinho(carrinhoID): return await Carrinho.CancelarPagamento(carrinhoID)
            try:
                if await PagBankPagamento.VerificarPagamento(order_id): return await Carrinho.EntregarPedido(inter, carrinhoID)
            except Exception as e: print(f"ERRO ao verificar pagamento PagBank para {carrinhoID}: {e}")
            await asyncio.sleep(15)
        if carrinhoID in tasksPagamento: await Carrinho.Cancelar(inter, carrinhoID)
    
    @staticmethod
    async def VerificarPagamentoLivePix(inter, carrinhoID):
        await asyncio.sleep(20)
        payment_id = ObterCarrinho(carrinhoID)["info"]["pagamento"]["paymentID"]
        for _ in range(120):
            if not carrinhoID in tasksPagamento or not ObterCarrinho(carrinhoID): return await Carrinho.CancelarPagamento(carrinhoID)
            try:
                if await LivePixPagamento.VerificarPagamento(payment_id): return await Carrinho.EntregarPedido(inter, carrinhoID)
            except Exception as e: print(f"ERRO ao verificar pagamento LivePix para {carrinhoID}: {e}")
            await asyncio.sleep(15)
        if carrinhoID in tasksPagamento: await Carrinho.Cancelar(inter, carrinhoID)
    
    @staticmethod
    async def VerificarPagamentoBancoInter(inter, carrinhoID):
        await asyncio.sleep(20)
        txid = ObterCarrinho(carrinhoID)["info"]["pagamento"]["txid"]
        for _ in range(180):
            if not carrinhoID in tasksPagamento or not ObterCarrinho(carrinhoID): return await Carrinho.CancelarPagamento(carrinhoID)
            try:
                if await InterPagamento.VerificarPagamento(txid): return await Carrinho.EntregarPedido(inter, carrinhoID)
            except Exception as e: print(f"ERRO ao verificar pagamento Banco Inter para {carrinhoID}: {e}")
            await asyncio.sleep(10)
        if carrinhoID in tasksPagamento: await Carrinho.Cancelar(inter, carrinhoID)

class Entrega():
    def ObterEstoque(quantidade, produtoID, campoID):
        campo = ObterCampo(produtoID, campoID)
        itens = []
        for _ in range(quantidade):
            if campo["estoque"]:
                item = campo["estoque"].pop(0)
                itens.append(item)
        
        db = ObterDatabase()
        db[produtoID]["campos"][campoID]["estoque"] = campo["estoque"]

        with open("Database/Vendas/produtos.json", "w", encoding='utf-8') as f:
            json.dump(db, f, indent=4)

        arquivo_nome = f"Database/Vendas/temp/estoque_{produtoID}_{campoID}.txt"
        os.makedirs(os.path.dirname(arquivo_nome), exist_ok=True)
        with open(arquivo_nome, "w", encoding="utf-8") as arquivo:
            arquivo.write("\n".join(itens))
        
        return arquivo_nome

    @staticmethod
    async def RegistrarEntrega(inter: disnake.MessageInteraction, carrinhoID: str):
        vendaID = Entrega.RegistrarVenda(carrinhoID)
        carrinho = ObterCarrinho(carrinhoID)
        produto = ObterProduto(carrinho["produtoID"])
        campo = ObterCampo(carrinho["produtoID"], carrinho["campoID"])
        user = await inter.bot.fetch_user(int(carrinho["server"]["usuario"]))

        with open("Database/Server/canais.json", encoding='utf-8') as f:
            canais = json.load(f)
            vendas_channel_id = canais.get("vendas")
            logs_channel_id = canais.get("logs")
        
        if vendas_channel_id:
            try:
                channel = inter.guild.get_channel(int(vendas_channel_id))
                if channel:
                    embed_venda = disnake.Embed(
                        title=f"{pedidoRealizado} Compra realizada",
                        description=f"O usuário {user.mention} teve seu pedido entregue.",
                        timestamp=datetime.now(), color=disnake.Color.green()
                    )
                    embed_venda.set_footer(text=inter.guild.name, icon_url=inter.guild.icon)
                    embed_venda.set_author(name=user.name, icon_url=user.avatar)
                    embed_venda.add_field(name="Item Comprado", value=f"```{carrinho['info']['quantidade']}x {produto['nome']} - {campo['nome']}```", inline=False)
                    embed_venda.add_field(name="Valor pago", value=f"`R${carrinho['info']['valorFinal']}`", inline=True)
                    await channel.send(embed=embed_venda)
            except Exception as e: print(f"Erro ao enviar log de venda: {e}")

        if logs_channel_id:
            try:
                channel = inter.guild.get_channel(int(logs_channel_id))
                if channel:
                    embed_log, _ = ObterMensagemLogs(inter, "4", carrinhoID)
                    embed_log.add_field(name="Usuário", value=f"{user.mention}", inline=True)
                    embed_log.add_field(name="ID do Pedido", value=f"`{vendaID}`", inline=True)
                    log_components = [
                        disnake.ui.Button(label="Info da Compra", custom_id=f"VendaInfo_{vendaID}", style=ButtonStyle.blurple),
                        disnake.ui.Button(label="Reembolsar", custom_id=f"ReembolsarProduto_{vendaID}", style=ButtonStyle.danger)
                    ]
                    
                    is_subscription = campo.get("is_subscription", False)
                    if not is_subscription:
                        entrega_path = f"Database/Vendas/entregas/{vendaID}.txt"
                        await channel.send(embed=embed_log, components=log_components, file=disnake.File(entrega_path))
                    else:
                        await channel.send(embed=embed_log, components=log_components)

            except Exception as e: print(f"Erro ao enviar log de entrega: {e}")
        
        return vendaID

    @staticmethod
    def RegistrarVenda(carrinhoID):
        carrinho = ObterCarrinho(carrinhoID)
        campo = ObterCampo(carrinho["produtoID"], carrinho["campoID"])
        is_subscription = campo.get("is_subscription", False)
        
        if not is_subscription:
            temp_path = f"Database/Vendas/temp/estoque_{carrinho['produtoID']}_{carrinho['campoID']}.txt"
            pasta_destino = "Database/Vendas/entregas"
            os.makedirs(pasta_destino, exist_ok=True)
            destino = os.path.join(pasta_destino, f"{carrinhoID}.txt")
            if os.path.exists(temp_path):
                shutil.copy2(temp_path, destino)

        with open("Database/Vendas/historicos.json", "r+", encoding='utf-8') as f:
            try: db = json.load(f)
            except json.JSONDecodeError: db = {}
            
            db[carrinhoID] = carrinho
            db[carrinhoID]["info"]["timestamp"] = datetime.now().strftime("%d/%m/%Y %H:%M")
            db[carrinhoID]["info"]["reembolso"] = False

            f.seek(0)
            json.dump(db, f, indent=4)
            f.truncate()
        
        return carrinhoID

    def ObterPainelGerenciarEstoque(inter: disnake.MessageInteraction, produtoID: str, campoID: str):
        embed = None
        components = [
                disnake.ui.Button(style=disnake.ButtonStyle.green, label="Adicionar", emoji=mais2, custom_id=f"AdicionarEstoque_{produtoID}_{campoID}"),
                disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Adicionar Estoque Fantasma", emoji=fantasma, custom_id=f"AdicionarEstoqueFantasma_{produtoID}_{campoID}"),
                disnake.ui.Button(style=disnake.ButtonStyle.green, label="Enviar Arquivo", emoji=diretorio, custom_id=f"EnviarArquivoEstoque_{produtoID}_{campoID}"),
                disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Pegar item do estoque", emoji=arrow, custom_id=f"PegarItemEstoque_{produtoID}_{campoID}"),
                disnake.ui.Button(label="Ver estoque", emoji=lupa, custom_id=f"VerEstoque_{produtoID}_{campoID}"),
                disnake.ui.Button(label="Voltar", emoji=voltar, custom_id=f"GerenciarCampo_{produtoID}_{campoID}"),
        ]

        return embed, components

class CarrinhoExtension(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command()
    async def deliver(
        self,
        inter: disnake.ApplicationCommandInteraction,
        campo: str = commands.Param(description="Selecione um campo", autocomplete=True),
        quantidade: int = commands.Param(description="Coloque a quantidade para ser recebida", default=1),
        user: disnake.User = commands.Param(description="Selecione um usuário para entregar o produto")
    ):
        if not verificar_permissao(inter.author.id):
            return await inter.response.send_message(f"{negativo} Faltam permissões para executar essa ação.", ephemeral=True)

        if campo == "FaltamPermissoes":
            return await inter.response.send_message(f"{negativo} Faltam permissões para executar essa ação.", ephemeral=True)

        produto_id, campo_id = campo.split(":")
        produto = ObterProduto(produto_id)
        campo_data = ObterCampo(produto_id, campo_id)
        
        if not Carrinho.VerificarQuantidade(produto_id, campo_id, quantidade):
            return await inter.response.send_message(f"{negativo} A quantidade solicitada é maior que o estoque disponível.", ephemeral=True)

        await inter.response.send_message(f"{carregarAnimado} Aguarde um momento...", ephemeral=True)

        embed = disnake.Embed(
            title="Entrega manual",
            description="Você recebeu um produto manualmente por um moderador.\nVisualize as informações sobre o produto abaixo.",
            color=disnake.Color(0xdb0d9a),
            timestamp=datetime.now()
        )
        embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon)
        embed.add_field(name="Informações do produto", value=f"`{quantidade}x {produto['nome']} - {campo_data['nome']}`", inline=False)
        embed.add_field(name="Moderador", value=inter.author.mention, inline=True)
        arquivo = Entrega.ObterEstoque(quantidade, produto_id, campo_id)
        try:
            await user.send(embed=embed, file=disnake.File(arquivo, filename="itens_recebidos.txt"))
        except disnake.Forbidden:
            await inter.edit_original_message(f"{negativo} Não foi possível entregar o produto, a DM do usuário está fechada.")
            with open(arquivo, 'r', encoding='utf-8') as f:
                itens_devolvidos = f.read().splitlines()
            db = ObterDatabase()
            db[produto_id]["campos"][campo_id]["estoque"].extend(itens_devolvidos)
            with open("Database/Vendas/produtos.json", "w", encoding='utf-8') as f_db:
                json.dump(db, f_db, indent=4)
            os.remove(arquivo)
            return

        embed.description = "Um moderador entregou um produto manualmente para um usuário.\nAcompanhe os detalhes abaixo."
        embed.add_field(name="Usuário", value=user.mention)
        components = [
            disnake.ui.Button(
                label="Gerenciar Estoque", custom_id=f"GerenciarEstoqueVenda_{produto_id}_{campo_id}",
                style=disnake.ButtonStyle.blurple, emoji=caixa
            ),
        ]

        await Logs.EnviarLogs(inter, None, embed, components, [disnake.File(arquivo, filename="itens_recebidos.txt")])
        os.remove(arquivo)
        await inter.edit_original_message(f"{positivo} Pedido entregado com sucesso para {user.mention}")

    @deliver.autocomplete("campo")
    async def campo_autocomplete(self, inter: disnake.ApplicationCommandInteraction, string: str):
        produtos_db = ObterDatabase()
        suggestions = []
        if verificar_permissao(inter.author.id):
            for produto_id, produto_data in produtos_db.items():
                nome_produto = produto_data["nome"]
                campos = produto_data.get("campos", {})
                for campo_id, campo_data in campos.items():
                    nome_campo = campo_data["nome"]
                    display_name = f"🛒 {nome_produto} ⭢ {nome_campo}"
                    value = f"{produto_id}:{campo_id}"
                    if string.lower() in display_name.lower():
                        suggestions.append(disnake.OptionChoice(name=display_name, value=value))
        else:
            suggestions.append(disnake.OptionChoice(name="❌ Faltam permissões", value="FaltamPermissoes"))
        return suggestions[:25]

    @commands.Cog.listener("on_button_click")
    async def CarrinhoListener(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if cid.startswith("ComprarProduto_"):
            _, produtoID, campoID = cid.split("_")
            await Carrinho.CriarCarrinho(inter, produtoID, campoID)
        elif cid.startswith("CancelarCarrinho_"):
            carrinhoID = cid.replace("CancelarCarrinho_", "")
            await Carrinho.Cancelar(inter, carrinhoID)
        elif cid.startswith("EditarQuantidade_"):
            carrinhoID = cid.replace("EditarQuantidade_", "")
            await inter.response.send_modal(Carrinho.EditarQuantidade(carrinhoID))
        elif cid.startswith("UsarCupom_"):
            carrinhoID = cid.replace("UsarCupom_", "")
            await inter.response.send_modal(Carrinho.AlterarCupom(carrinhoID))
        elif cid.startswith("ProsseguirPagamento_"):
            carrinhoID = cid.replace("ProsseguirPagamento_", "")
            await Carrinho.ProsseguirPagamento(inter, carrinhoID)
        elif cid.startswith("CodigoCopiaCola_"):
            carrinhoID = cid.replace("CodigoCopiaCola_", "")
            carrinho = ObterCarrinho(carrinhoID)
            if carrinho: await inter.response.send_message(f"{carrinho['info']['pagamento']['copiacola']}", ephemeral=True)
        elif cid.startswith("AprovarCarrinho_"):
            if verificar_permissao(inter.author.id):
                carrinhoID = cid.replace("AprovarCarrinho_", "")
                await Carrinho.EntregarPedido(inter, carrinhoID)
            else:
                await inter.response.defer()
        elif cid.startswith("ReembolsarProduto_"):
            if not verificar_permissao(inter.author.id):
                return await inter.response.send_message(f"{negativo} Faltam permissões para executar essa ação.", ephemeral=True)
            vendaID = cid.replace("ReembolsarProduto_", "")
            venda = ObterVenda(vendaID)
            if not venda:
                return await inter.response.send_message(f"{negativo} Venda `{vendaID}` não encontrada.", ephemeral=True)
            await inter.response.send_message("Funcionalidade de reembolso a ser implementada.", ephemeral=True)
        elif cid.startswith("GerenciarEstoqueVenda_"):
            if not verificar_permissao(inter.author.id): return await inter.response.defer()
            _, produtoID, campoID = cid.split("_")
            embed, components = Entrega.ObterPainelGerenciarEstoque(inter, produtoID, campoID)
            await inter.response.send_message(components=components, ephemeral=True)
        elif cid.startswith("AtivarNotificacoesEstoque_"):
            _, produtoID, campoID = cid.split("_")
            await inter.response.send_message(f"{carregarAnimado} Registrando informações", ephemeral=True)
            db = ObterDatabase()
            alertas = db[produtoID]["campos"][campoID]["estoqueinfo"]["alertas"]
            if inter.author.id in alertas:
                alertas.remove(inter.author.id)
                mensagem = f"{positivo} Você **não receberá** mais atualizações."
            else:
                alertas.append(inter.author.id)
                mensagem = f"{positivo} Você **receberá** atualizações de estoque."
            with open("Database/Vendas/produtos.json", "w", encoding='utf-8') as f:
                json.dump(db, f, indent=4)
            await inter.edit_original_message(mensagem)
        elif cid.startswith("VendaInfo_"):
            vendaID = cid.replace("VendaInfo_", "")
            if verificar_permissao(inter.author.id):
                await inter.response.send_message(f"{carregarAnimado} Carregando informações", ephemeral=True)
                embed, components = ObterVendaPainel(inter, vendaID)
                if embed is None:
                    return await inter.edit_original_message(f"{negativo} Venda `{vendaID}` não encontrada.")
                
                entrega_path = f"Database/Vendas/entregas/{vendaID}.txt"
                file = disnake.File(entrega_path) if os.path.exists(entrega_path) else None
                await inter.edit_original_message("", embed=embed, components=components, file=file)
            else:
                await inter.response.send_message(f"{negativo} Faltam permissões para executar essa ação", ephemeral=True)

    @commands.Cog.listener("on_dropdown")
    async def CarrinhoDropdownListener(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id.startswith("ComprarCampo_"):
            produtoID = inter.component.custom_id.replace("ComprarCampo_", "")
            campoID = inter.values[0]
            await Carrinho.CriarCarrinho(inter, produtoID, campoID)

def setup(bot: commands.Bot):
    bot.add_cog(CarrinhoExtension(bot))