from disnake.ext import commands
from datetime import *
from disnake import *
import requests
import disnake
import random
import string
import json
import re
import os

from Functions.CarregarEmojis import *
from Functions.VerificarPerms import *
from Functions.Config.Produto import *

def criar_loading_container(texto="Carregando..."):
    return disnake.ui.Container(
        disnake.ui.TextDisplay(f"{carregarAnimado} {texto}")
    )

# Modais

class AlterarInstrucoesModal(disnake.ui.Modal):
    def __init__(self):
        with open("Database/Vendas/vendas.json") as f:
            db = json.load(f)

        components = [
            disnake.ui.TextInput(
                label="Instruções",
                custom_id="instructions",
                value=db["instrucoes"],
                style=TextInputStyle.paragraph,
                required=False
            ),
        ]
        super().__init__(title="Configurar Instruções", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        instructions = inter.text_values["instructions"]
        with open("Database/Vendas/vendas.json") as f:
            db = json.load(f)
        
        db["instrucoes"] = instructions

        with open("Database/Vendas/vendas.json", "w") as f:
            json.dump(db, f, indent=4)
        
        await inter.response.send_message(f"{positivo} Alterações salvas com sucesso.", ephemeral=True)

class AlterarMarcaModal(disnake.ui.Modal):
    def __init__(self):
        with open("Database/Vendas/vendas.json") as f:
            db = json.load(f)

        components = [
            disnake.ui.TextInput(
                label="URL da sua imagem",
                custom_id="url",
                value=db["marca"]["url"],
                required=False,
                style=TextInputStyle.short,
            ),
            disnake.ui.TextInput(
                label="Cor primária (HEX)",
                custom_id="pri",
                max_length=6,
                min_length=6,
                required=False,
                value=db["marca"]["cores"]["principal"],
                style=TextInputStyle.short,
            ),
            disnake.ui.TextInput(
                label="Cor secundária (HEX)",
                custom_id="sec",
                value=db["marca"]["cores"]["sec"],
                max_length=6,
                min_length=6,
                required=False,
                style=TextInputStyle.short,
            ),
        ]
        super().__init__(title="Configurar Marca", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        url = inter.text_values.get("url")
        cor_primaria = inter.text_values.get("pri")
        cor_secundaria = inter.text_values.get("sec")
        erro = f"{negativo} Você forneceu alguma informação errada. Tente novamente"

        def cor_hex_valida(cor):
            return bool(re.fullmatch(r"^[0-9A-Fa-f]{6}$", cor))

        if not cor_hex_valida(cor_primaria):
            return await inter.response.send_message(erro, ephemeral=True)

        if not cor_hex_valida(cor_secundaria):
            return await inter.response.send_message(erro, ephemeral=True)

        with open("Database/Vendas/vendas.json") as f:
            db = json.load(f)

        db["marca"]["url"] = url
        db["marca"]["cores"]["principal"] = cor_primaria
        db["marca"]["cores"]["sec"] = cor_secundaria

        with open("Database/Vendas/vendas.json", "w") as f:
            json.dump(db, f, indent=4)

        await inter.response.send_message(f"{positivo} Configurações atualizadas com sucesso!", ephemeral=True)

# Databases

def ObterDatabase():
    with open("Database/Vendas/produtos.json") as f:
        db = json.load(f)
        return db

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

def ObterCupom(produtoID, cupom):
    with open("Database/Vendas/produtos.json") as f:
        db = json.load(f)
        try:
            produto = db[produtoID]
            cupom = produto["cupons"][cupom]
        except:
            cupom = None
        return cupom    

def GerarString():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=13))

# Paineis

def ObterPainelPrincipal(inter: disnake.MessageInteraction):
    from disnake.ui import Container, TextDisplay, Separator, ActionRow
    
    db = ObterDatabase()

    container_elems = [
        disnake.ui.TextDisplay(f"# {carrinho} Central de Loja"),
        disnake.ui.Separator(),
        disnake.ui.TextDisplay(f"Olá, **{inter.user.name}**! Utilize este painel para gerenciar o sistema de vendas."),
        disnake.ui.Separator(),
        disnake.ui.TextDisplay(f"**Total de produtos:** {caixa} `{len(db)} produto(s)`"),
        disnake.ui.Separator(),
        disnake.ui.ActionRow(
            disnake.ui.Button(style=disnake.ButtonStyle.green, label="Criar Produto", emoji=mais2, custom_id="CriarProdutoVendas"),
            disnake.ui.Button(style=disnake.ButtonStyle.green, label="Gerenciar Produtos", emoji=config3, custom_id="GerenciarProdutosVendas"),
            disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Customizar Loja", emoji=wand, custom_id="GerenciarPersonalizarLoja")
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Definir instruções", emoji=attach, custom_id="DefinirInstrucoesVendas"),
            disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Definir Termos", emoji=termos, custom_id="GerenciarTermos"),
            disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Condecorações", emoji=condecoracoes, custom_id="GerenciarCondecoracoes")
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Botão Dúvidas", emoji=duvida, custom_id="GerenciarBotaoDuvidas"),
            disnake.ui.Button(label="Voltar", emoji=voltar, custom_id="PainelInicial")
        )
    ]

    container = disnake.ui.Container(*container_elems)
    return [container]

class Produto():
    class CriarProdutoModal(disnake.ui.Modal):
        def __init__(self):
            components = [
                disnake.ui.TextInput(
                    label="Nome",
                    custom_id="name",
                    placeholder="Insira o nome do seu produto",
                    style=TextInputStyle.short,
                ),
                disnake.ui.TextInput(
                    label="Descrição",
                    custom_id="desc",
                    placeholder="Insira uma descrição para seu produto",
                    required=False,
                    style=TextInputStyle.long,
                ),
                disnake.ui.TextInput(
                    label="Ícone (Opcional)",
                    placeholder="Insira uma URL de uma imagem ou gif",
                    custom_id="icon",
                    required=False,
                    style=TextInputStyle.short,
                ),
                disnake.ui.TextInput(
                    label="Banner (Opcional)",
                    placeholder="Insira uma URL de uma imagem ou gif",
                    custom_id="banner",
                    required=False,
                    style=TextInputStyle.short,
                ),
            ]
            super().__init__(title="Criar Produto", components=components)

        async def callback(self, inter: disnake.ModalInteraction):
            await inter.response.edit_message(embed=None, components=[criar_loading_container("Carregando informações")])
            db = ObterDatabase()
            
            produtoID = GerarString()
            nome = inter.text_values["name"]
            descricao = inter.text_values.get("desc", None)
            entrega_auto = "s"
            icone = inter.text_values.get("icon", None)
            banner = inter.text_values.get("banner", None)

            if entrega_auto == "s" or entrega_auto == "n":
                db[produtoID] = {
                    "nome": nome,
                    "desc": descricao,
                    "entrega": True if entrega_auto == "s" else False,
                    "assets": {
                        "icon": icone,
                        "banner": banner,
                        "hex": "00FFFF"
                    },
                    "campos": {},
                    "criadoEm": int(datetime.now().timestamp()),
                    "cupons": {},
                    "ids": []
                }

                with open("Database/Vendas/produtos.json", "w") as f:
                    json.dump(db, f, indent=4)
                
                components = Produto.ObterPainelGerenciarProduto(inter, produtoID)
                await inter.edit_original_message(embed=None, components=components)
                await inter.followup.send(f"{positivo} Produto **{nome}** criado com sucesso", delete_after=3, ephemeral=True)
            else:
                error_container = disnake.ui.Container(
                    disnake.ui.TextDisplay(f"{negativo} Você não informou corretamente a entrega automática.")
                )
                await inter.edit_original_message(embed=None, components=[error_container])

    class EditarProdutoModal(disnake.ui.Modal):
        def __init__(self, produtoID):
            self.produtoID = produtoID
            db = ObterProduto(produtoID)
            components = [
                disnake.ui.TextInput(label="Título do Embed", custom_id="name", placeholder="Insira o nome do seu produto", style=TextInputStyle.short, value=db.get("nome")),
                disnake.ui.TextInput(label="Descrição do Embed", custom_id="desc", placeholder="Insira uma descrição para seu produto", required=False, value=db.get("desc"), style=TextInputStyle.long),
                disnake.ui.TextInput(label="Ícone do Embed (URL)", custom_id="icon", required=False, value=db.get("assets", {}).get("icon"), style=TextInputStyle.short),
                disnake.ui.TextInput(label="Banner do Embed (URL)", custom_id="banner", required=False, value=db.get("assets", {}).get("banner"), style=TextInputStyle.short),
                disnake.ui.TextInput(label="Cor em HEX (sem #)", custom_id="hex", placeholder="Ex: 00FFFF", style=TextInputStyle.short, value=db.get("assets", {}).get("hex"), min_length=6, max_length=6),
            ]
            super().__init__(title=f"Editar Embed do Produto", components=components)

        async def callback(self, inter: disnake.ModalInteraction):
            await inter.response.defer()
            db = ObterDatabase()
            produto = db[self.produtoID]
            def cor_hex_valida(cor): return bool(re.fullmatch(r"^[0-9A-Fa-f]{6}$", cor))
            hex_val = inter.text_values["hex"]
            if not cor_hex_valida(hex_val): return await inter.followup.send(f"{negativo} O código HEX é inválido.", ephemeral=True)
            produto["nome"] = inter.text_values["name"]
            produto["desc"] = inter.text_values.get("desc")
            produto["assets"]["icon"] = inter.text_values.get("icon")
            produto["assets"]["banner"] = inter.text_values.get("banner")
            produto["assets"]["hex"] = hex_val
            with open("Database/Vendas/produtos.json", "w") as f: json.dump(db, f, indent=4)
            await inter.followup.send(f"{positivo} Embed atualizada!", ephemeral=True, delete_after=3)
            await SincronizarMensagens(inter, self.produtoID)
            embed, components = Produto.ObterPainelEditarProduto(inter, self.produtoID)
            await inter.edit_original_message(embed=embed, components=components)

    class EditarContentModal(disnake.ui.Modal):
        def __init__(self, produtoID):
            self.produtoID = produtoID
            produto = ObterProduto(produtoID)
            components = [disnake.ui.TextInput(label="Conteúdo da Mensagem (texto fora do embed)", custom_id="content", style=TextInputStyle.paragraph, value=produto.get("content", ""), required=False)]
            super().__init__(title="Editar Conteúdo", components=components)
        async def callback(self, inter: disnake.ModalInteraction):
            await inter.response.defer()
            db = ObterDatabase()
            db[self.produtoID]["content"] = inter.text_values["content"] or None
            with open("Database/Vendas/produtos.json", "w") as f: json.dump(db, f, indent=4)
            await inter.followup.send(f"{positivo} Conteúdo atualizado!", ephemeral=True, delete_after=3)
            await SincronizarMensagens(inter, self.produtoID)
            embed, components = Produto.ObterPainelEditarProduto(inter, self.produtoID)
            await inter.edit_original_message(embed=embed, components=components)

    class ConfigurarImagemModal(disnake.ui.Modal):
        def __init__(self, produtoID):
            self.produtoID = produtoID
            produto = ObterProduto(produtoID)
            components = [disnake.ui.TextInput(label="URL da Imagem Avulsa", custom_id="image_url", placeholder="Insira o link da imagem a ser exibida.", style=TextInputStyle.short, value=produto.get("image_url", ""), required=False)]
            super().__init__(title="Configurar Imagem Avulsa", components=components)
        async def callback(self, inter: disnake.ModalInteraction):
            await inter.response.defer()
            db = ObterDatabase()
            db[self.produtoID]["image_url"] = inter.text_values["image_url"] or None
            with open("Database/Vendas/produtos.json", "w") as f: json.dump(db, f, indent=4)
            await inter.followup.send(f"{positivo} Imagem atualizada!", ephemeral=True, delete_after=3)
            await SincronizarMensagens(inter, self.produtoID)
            embed, components = Produto.ObterPainelEditarProduto(inter, self.produtoID)
            await inter.edit_original_message(embed=embed, components=components)

    @staticmethod
    async def GerenciarProdutos(inter: disnake.MessageInteraction):
        await inter.response.edit_message(embed=None, components=[criar_loading_container("Carregando informações")])
        db = ObterDatabase()

        options = []
        for product_id, product_data in db.items():
            options.append(
                disnake.SelectOption(
                    label=product_data["nome"],
                    description=f"Campos: {len(product_data['campos'])} | Cupons: {len(product_data['cupons'])}",
                    value=product_id,
                    emoji=caixa
                )
            )
        
        if not options:
            options.append(
                disnake.SelectOption(
                    label="Nenhum produto disponível",
                    value="null"
                ) 
            )
        
        select = disnake.ui.StringSelect(
            placeholder=f"[{len(db)}] Clique aqui para selecionar",
            custom_id="SelecionarProdutoDropdownVendas",
            options=options,
            disabled=True if len(db) == 0 else False
        )

        container_elems = [
            disnake.ui.TextDisplay(f"# {config3} Gerenciar Produtos"),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(f"{inter.user.mention} Qual produto deseja gerenciar?"),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(select),
            disnake.ui.ActionRow(
                disnake.ui.Button(style=disnake.ButtonStyle.green, label="Criar Produto", emoji=mais2, custom_id="CriarProdutoVendas"),
                disnake.ui.Button(label="Voltar", emoji=voltar, custom_id="GerenciarPainelVendas")
            )
        ]

        container = disnake.ui.Container(*container_elems)
        await inter.edit_original_message(embed=None, components=[container])

    @staticmethod
    def ObterPainelGerenciarProduto(inter: disnake.MessageInteraction, produtoID: str):
        from disnake.ui import Container, TextDisplay, Separator, ActionRow
        
        db = ObterDatabase()
        produto = ObterProduto(produtoID)
        desc = f"{negativo} ``Não definida``" if produto["desc"] == "" else produto["desc"]

        container_elems = [
            disnake.ui.TextDisplay(f"# {config3} Gerenciando: {produto['nome']}"),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(f"**Descrição do produto:**\n{desc}"),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(f"**Campos:** `{len(produto['campos'])}` campo(s) | **Cupons:** `{len(produto['cupons'])}` cupom(ns)"),
            disnake.ui.TextDisplay(f"**Entrega automática:** {'Sim' if produto['entrega'] else 'Não'} | **Criado em:** <t:{produto['criadoEm']}:f>"),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(
                disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Editar Produto", emoji=editar, custom_id=f"EditarProduto_{produtoID}"),
                disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Gerenciar Campos", emoji=caixa, custom_id=f"GerenciarCampos_{produtoID}"),
                disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Gerenciar Cupons", emoji=cupom, custom_id=f"GerenciarCupons_{produtoID}")
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(style=disnake.ButtonStyle.green, label="Colocar a venda", emoji=arrow, custom_id=f"ColocarVenda_{produtoID}"),
                disnake.ui.Button(
                    label="Entrega automática",
                    emoji=reload,
                    style=disnake.ButtonStyle.green if produto["entrega"] == True else disnake.ButtonStyle.red,
                    custom_id=f"AtivarDesativarEntregaAuto_{produtoID}"
                ),
                disnake.ui.Button(style=disnake.ButtonStyle.red, label="Excluir produto", emoji=apagar, custom_id=f"ApagarProduto_{produtoID}")
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Sincronizar Mensagens", emoji=reload, custom_id=f"SincronizarProduto_{produtoID}"),
                disnake.ui.Button(label="Voltar", emoji=voltar, custom_id="GerenciarProdutosVendas")
            )
        ]

        container = disnake.ui.Container(*container_elems)
        return [container]

    @staticmethod
    def ObterPainelEditarProduto(inter: disnake.MessageInteraction, produtoID: str):
        produto = ObterProduto(produtoID)
        is_content_set = bool(produto.get("content"))
        is_embed_set = bool(produto.get("desc") or produto.get("nome") or produto.get("assets", {}).get("icon") or produto.get("assets", {}).get("banner"))
        is_image_set = bool(produto.get("image_url"))
        
        embed = disnake.Embed(title=f"Painel de Edição: {produto.get('nome')}", description="Selecione o que você deseja editar neste produto.", color=disnake.Color(0x00FFFF))
        
        row1 = disnake.ui.ActionRow()
        row1.add_button(label="Editar Conteúdo", emoji=editar, custom_id=f"EditarConteudo_{produtoID}", style=ButtonStyle.primary)
        row1.add_button(emoji=apagar, custom_id=f"LimparConteudo_{produtoID}", style=ButtonStyle.red, disabled=not is_content_set)
        
        row2 = disnake.ui.ActionRow()
        row2.add_button(label="Editar Embed", emoji=editar, custom_id=f"EditarEmbed_{produtoID}", style=ButtonStyle.primary)
        row2.add_button(emoji=apagar, custom_id=f"LimparEmbed_{produtoID}", style=ButtonStyle.red, disabled=not is_embed_set)
        
        row3 = disnake.ui.ActionRow()
        row3.add_button(label="Configurar Imagem", emoji=config3, custom_id=f"ConfigurarImagem_{produtoID}", style=ButtonStyle.secondary)
        row3.add_button(emoji=apagar, custom_id=f"LimparImagem_{produtoID}", style=ButtonStyle.red, disabled=not is_image_set)
        
        row4 = disnake.ui.ActionRow()
        row4.add_button(label="Voltar", emoji=voltar, custom_id=f"GerenciarProduto_{produtoID}")

        return embed, [row1, row2, row3, row4]

    @staticmethod
    def Apagar(produtoID: str):
        db = ObterDatabase()

        del(db[produtoID])

        with open("Database/Vendas/produtos.json", "w") as f:
            json.dump(db, f, indent=4)

class Campo():
    class Assinatura():
        @staticmethod
        def ObterPainelGerenciarAssinatura(inter: disnake.MessageInteraction, produtoID: str, campoID: str):
            campo = ObterCampo(produtoID=produtoID, campoID=campoID)
            detalhes = campo.get("subscription_details", {})

            role_id = detalhes.get("role_id")
            role_info = f"<@&{role_id}>" if role_id and inter.guild.get_role(int(role_id)) else f"{negativo} ``Não definido``"
            duration = detalhes.get('duration_days', 30)

            vip_status = "Ativado" if detalhes.get("vip_enabled") else "Desativado"
            inatividade_status = "Ativado" if detalhes.get("inactivity_enabled") else "Desativado"
            esconder_call_status = "Ativado" if detalhes.get("hide_call_enabled") else "Desativado"

            embed = disnake.Embed(
                title="Gerenciando Assinatura",
                description=f"""
Configure os detalhes da assinatura para o campo **{campo['nome']}**.

**Cargo da Assinatura:** {role_info}
**Duração:** ``{duration} dias``

**Recursos Adicionais:**
> **VIP:** {vip_status}
> **Controle de Inatividade:** {inatividade_status}
> **Esconder Call:** {esconder_call_status}
                """,
                color=disnake.Color(0x00FFFF)
            )
            embed.set_footer(text="Configure o cargo e recursos abaixo.")

            # Buscar cargos configurados para adicionar/remover
            roleAdd = []
            for roleID in campo["cargos"]["add"]:
                try:
                    role = inter.guild.get_role(int(roleID))
                    if role:
                        roleAdd.append(SelectDefaultValue(id=role.id, type=SelectDefaultValueType.role))
                except: 
                    pass

            roleRem = []
            for roleID in campo["cargos"]["rem"]:
                try:
                    role = inter.guild.get_role(int(roleID))
                    if role:
                        roleRem.append(SelectDefaultValue(id=role.id, type=SelectDefaultValueType.role))
                except: 
                    pass

            components = [
                # Row 1: Dropdowns para cargos
                [
                    disnake.ui.RoleSelect(
                        placeholder="Selecione os cargos para serem adicionados",
                        max_values=25,
                        min_values=0,
                        custom_id=f"GerenciarCargos_Adicionar_{produtoID}_{campoID}",
                        default_values=roleAdd if roleAdd else None
                    )
                ],
                [
                    disnake.ui.RoleSelect(
                        placeholder="Selecione os cargos para serem removidos",
                        max_values=25,
                        min_values=0,
                        custom_id=f"GerenciarCargos_Remover_{produtoID}_{campoID}",
                        default_values=roleRem if roleRem else None
                    )
                ],
                # Row 2: Configurações de recursos
                [
                    disnake.ui.Button(
                        label=f"VIP: {vip_status}",
                        custom_id=f"ToggleVIP_{produtoID}_{campoID}",
                        emoji=reload,
                        style=ButtonStyle.green if detalhes.get("vip_enabled") else ButtonStyle.red
                    ),
                    disnake.ui.Button(
                        label=f"Inatividade: {inatividade_status}",
                        custom_id=f"ToggleInatividade_{produtoID}_{campoID}",
                        emoji=reload,
                        style=ButtonStyle.green if detalhes.get("inactivity_enabled") else ButtonStyle.red
                    ),
                    disnake.ui.Button(
                        label=f"Esconder Call: {esconder_call_status}",
                        custom_id=f"ToggleEsconderCall_{produtoID}_{campoID}",
                        emoji=reload,
                        style=ButtonStyle.green if detalhes.get("hide_call_enabled") else ButtonStyle.red
                    ),
                ],
                # Row 3: Configurar cargo da assinatura e voltar
                [
                    disnake.ui.Button(
                        label="Configurar Cargo da Assinatura", 
                        emoji=config3, 
                        custom_id=f"ConfigurarCargoAssinatura_{produtoID}_{campoID}", 
                        style=ButtonStyle.primary
                    ),
                    disnake.ui.Button(label="Voltar", emoji=voltar, custom_id=f"GerenciarCampo_{produtoID}_{campoID}")
                ]
            ]
            return embed, components

        class ConfigurarCargoAssinaturaModal(disnake.ui.Modal):
            def __init__(self, produtoID, campoID):
                self.produtoID = produtoID
                self.campoID = campoID
                campo = ObterCampo(produtoID=produtoID, campoID=campoID)
                detalhes = campo.get("subscription_details", {})

                components = [
                    disnake.ui.TextInput(
                        label="ID do Cargo da Assinatura",
                        custom_id="role_id",
                        placeholder="Insira o ID do cargo que será entregue",
                        style=TextInputStyle.short,
                        value=str(detalhes.get("role_id", "")),
                        required=True,
                    ),
                    disnake.ui.TextInput(
                        label="Duração da Assinatura (dias)",
                        custom_id="duration_days",
                        placeholder="Padrão: 30 dias",
                        style=TextInputStyle.short,
                        value=str(detalhes.get("duration_days", 30)),
                        required=False,
                    ),
                ]
                super().__init__(title="Configurar Cargo da Assinatura", components=components)

            async def callback(self, inter: disnake.ModalInteraction):
                await inter.response.defer()
                role_id_str = inter.text_values["role_id"].strip()
                duration_days_str = inter.text_values["duration_days"].strip() or "30"

                try:
                    role_id = int(role_id_str)
                    if not inter.guild.get_role(role_id):
                        return await inter.followup.send(f"{negativo} O ID do cargo informado é inválido ou não foi encontrado neste servidor.", ephemeral=True)
                except ValueError:
                    return await inter.followup.send(f"{negativo} O ID do cargo deve ser um número.", ephemeral=True)

                try:
                    duration_days = int(duration_days_str)
                    if duration_days <= 0:
                        return await inter.followup.send(f"{negativo} A duração deve ser um número positivo de dias.", ephemeral=True)
                except ValueError:
                    return await inter.followup.send(f"{negativo} A duração deve ser um número válido de dias.", ephemeral=True)

                db = ObterDatabase()
                db[self.produtoID]["campos"][self.campoID]["subscription_details"]["role_id"] = role_id
                db[self.produtoID]["campos"][self.campoID]["subscription_details"]["duration_days"] = duration_days

                with open("Database/Vendas/produtos.json", "w") as f:
                    json.dump(db, f, indent=4)

                await inter.followup.send(f"{positivo} Detalhes da assinatura atualizados!", ephemeral=True, delete_after=3)
                embed, components = Campo.Assinatura.ObterPainelGerenciarAssinatura(inter, self.produtoID, self.campoID)
                await inter.edit_original_message(embed=embed, components=components)

    class DefinirPrecoComparacaoModal(disnake.ui.Modal):
        def __init__(self, produtoID, campoID):
            self.produtoID = produtoID
            self.campoID = campoID
            campo = ObterCampo(produtoID=produtoID, campoID=campoID)
            preco_comparacao = campo.get("comparison_price", "")

            components = [
                disnake.ui.TextInput(
                    label="Preço de Comparação (Opcional)",
                    custom_id="comparison_price",
                    placeholder="Ex: 99.90 (Deixe em branco para remover)",
                    style=TextInputStyle.short,
                    value=str(preco_comparacao) if preco_comparacao is not None else "",
                    required=False
                ),
            ]
            super().__init__(title="Definir Preço de Comparação", components=components)

        async def callback(self, inter: disnake.ModalInteraction):
            preco_texto = inter.text_values["comparison_price"].strip().replace(",",".")
            preco_final = None

            if preco_texto:
                try:
                    preco_final = float(preco_texto)
                    preco_final = "{:.2f}".format(preco_final)
                except ValueError:
                    return await inter.response.send_message(f"{negativo} Você informou um preço de comparação inválido.", ephemeral=True)

            db = ObterDatabase()
            db[self.produtoID]["campos"][self.campoID]["comparison_price"] = preco_final

            with open("Database/Vendas/produtos.json", "w") as f:
                json.dump(db, f, indent=4)

            await inter.response.send_message(f"{positivo} Preço de comparação atualizado!", ephemeral=True, delete_after=3)
            await SincronizarMensagens(inter, self.produtoID)
            embed, components = Campo.ObterPainelGerenciarCampo(inter, self.produtoID, self.campoID)
            await inter.edit_original_message(embed=embed, components=components)

    class Criar(disnake.ui.Modal):
        def __init__(self, produtoID):
            self.produtoID = produtoID
            components = [
                disnake.ui.TextInput(
                    label="Nome do campo",
                    placeholder="Insira o nome desejado",
                    custom_id="name",
                    style=TextInputStyle.short,
                    max_length=50,
                ),
                disnake.ui.TextInput(
                    label="Descrição do campo",
                    placeholder="Insira a descrição desejada",
                    custom_id="desc",
                    required=False,
                    style=TextInputStyle.paragraph,
                ),
                disnake.ui.TextInput(
                    label="Preço do campo",
                    placeholder="Insira o preço desejado (BRL)",
                    custom_id="price",
                    style=TextInputStyle.short,
                ),
              disnake.ui.TextInput(
                    label="Emoji do campo (Opcional)",
                    placeholder="Ex: 🛒 ou <:emoji:12345>",
                    custom_id="emoji",
                    style=TextInputStyle.short,
                    required=False
                ),
            ]
            super().__init__(title="Criar Campo", components=components)

        async def callback(self, inter: disnake.ModalInteraction):
            db = ObterDatabase()
            produto = ObterProduto(self.produtoID)
            campoID = GerarString()
            nome = inter.text_values["name"]
            desc = inter.text_values["desc"]
            preco = inter.text_values["price"]
            emoji = inter.text_values.get("emoji", None)
          

            try:
                preco = float(preco)
                preco = "{:.2f}".format(preco)
            except: return await inter.response.send_message(f"{negativo} Você informou um valor errado. Utilize números inteiros/quebrados positivos.", ephemeral=True)

            await inter.response.edit_message(embed=None, components=[criar_loading_container("Carregando informações")])

            db[self.produtoID]["campos"][campoID] = {
                "nome": nome,
                "desc": desc,
                "preco": preco,
                "emoji": emoji,
                "comparison_price": None,
                "is_subscription": False,
                "subscription_details": {
                    "role_id": None,
                    "duration_days": 30,
                    "vip_enabled": False,
                    "inactivity_enabled": False,
                    "hide_call_enabled": False
                },
                "condicoes": {
                    "valorMin": None,
                    "valorMax": None,
                    "quantidadeMin": None,
                    "quantidadeMax": None,
                    "idCargo": []
                },
                "estoque": [],
                "estoqueinfo": {
                    "last": None,
                    "alertas": []
                },
                "cargos": {
                    "add": [],
                    "rem": []
                }
            }

            with open("Database/Vendas/produtos.json", "w") as f:
                json.dump(db, f, indent=4)
            
            embed, components = Campo.ObterPainelGerenciarCampo(inter, self.produtoID, campoID)
            await inter.edit_original_message(embed=embed, components=components)
            await SincronizarMensagens(inter, self.produtoID)

    class Editar(disnake.ui.Modal):
        def __init__(self, produtoID, campoID):
            self.produtoID = produtoID
            self.campoID = campoID

            campo = ObterCampo(produtoID=produtoID, campoID=campoID)

            components = [
                disnake.ui.TextInput(
                    label="Nome do campo",
                    placeholder="Insira o nome desejado",
                    custom_id="name",
                    value=campo["nome"],
                    style=TextInputStyle.short,
                    max_length=50,
                ),
                disnake.ui.TextInput(
                    label="Descrição do campo",
                    placeholder="Insira a descrição desejada",
                    custom_id="desc",
                    required=False,
                    value=campo["desc"],
                    style=TextInputStyle.paragraph,
                ),
                disnake.ui.TextInput(
                    label="Preço do campo",
                    placeholder="Insira o preço desejado (BRL)",
                    custom_id="price",
                    value=f"{campo['preco']}",
                    style=TextInputStyle.short,
                ),
              disnake.ui.TextInput(
                    label="Emoji do campo (Opcional)",
                    placeholder="Ex: 🛒 ou <:emoji:12345>",
                    custom_id="emoji",
                    style=TextInputStyle.short,
                    required=False,
                    value=campo.get("emoji", "")
                ),
            ]
            super().__init__(title="Editar Campo", components=components)

        async def callback(self, inter: disnake.ModalInteraction):
            db = ObterDatabase()
            produto = ObterProduto(self.produtoID)
            nome = inter.text_values["name"]
            desc = inter.text_values["desc"]
            preco = inter.text_values["price"]
            emoji = inter.text_values.get("emoji", None)
      
            try:
                preco = float(preco)
                preco = "{:.2f}".format(preco)
            except: return await inter.response.send_message(f"{negativo} Você informou um valor errado. Utilize números inteiros/quebrados positivos.", ephemeral=True)

            await inter.response.edit_message(embed=None, components=[criar_loading_container("Carregando informações")])

            db[self.produtoID]["campos"][self.campoID]["nome"] = nome
            db[self.produtoID]["campos"][self.campoID]["desc"] = desc
            db[self.produtoID]["campos"][self.campoID]["preco"] = preco
            db[self.produtoID]["campos"][self.campoID]["emoji"] = emoji

            with open("Database/Vendas/produtos.json", "w") as f:
                json.dump(db, f, indent=4)
            
            embed, components = Campo.ObterPainelGerenciarCampo(inter, self.produtoID, self.campoID)
            await inter.edit_original_message(embed=embed, components=components)
            await SincronizarMensagens(inter, self.produtoID)

    class Condicoes(disnake.ui.Modal):
        def __init__(self, produtoID, campoID):
            self.produtoID = produtoID
            self.campoID = campoID

            campo = ObterCampo(produtoID=produtoID, campoID=campoID)
            idsFormatado = "\n".join(map(str, campo["condicoes"]["idCargo"]))
            valorMin = str(campo["condicoes"]["valorMin"]) if campo["condicoes"]["valorMin"] else ""
            valorMax = str(campo["condicoes"]["valorMin"]) if campo["condicoes"]["valorMax"] else ""
            quantidadeMin = str(campo["condicoes"]["quantidadeMin"]) if campo["condicoes"]["quantidadeMin"] else ""
            quantidadeMax = str(campo["condicoes"]["quantidadeMax"]) if campo["condicoes"]["quantidadeMax"] else ""

            components = [
                disnake.ui.TextInput(
                    label="Valor mínimo",
                    placeholder="Coloque o valor mínimo para comprar",
                    custom_id="valuemin",
                    required=False,
                    value=valorMin,
                    style=TextInputStyle.short,
                    max_length=50,
                ),
                disnake.ui.TextInput(
                    label="Valor máximo",
                    placeholder="Coloque o valor máximo para comprar",
                    custom_id="valuemax",
                    required=False,
                    value=valorMax,
                    style=TextInputStyle.short,
                ),
                disnake.ui.TextInput(
                    label="Quantidade mínima",
                    placeholder="Coloque a quantidade mínima para comprar",
                    custom_id="quantidademin",
                    required=False,
                    value=quantidadeMin,
                    style=TextInputStyle.short,
                ),
                disnake.ui.TextInput(
                    label="Quantidade máxima",
                    placeholder="Coloque a quantidade máxima para comprar",
                    custom_id="quantidademax",
                    required=False,
                    value=quantidadeMax,
                    style=TextInputStyle.short, 
                ),
            ]
            super().__init__(title="Gerenciar Condições", components=components)

        async def callback(self, inter: disnake.ModalInteraction):
            try:
                valuemin = float(inter.text_values["valuemin"]) if inter.text_values["valuemin"] else None
                valuemax = float(inter.text_values["valuemax"]) if inter.text_values["valuemax"] else None
                quantidademin = int(inter.text_values["quantidademin"]) if inter.text_values["quantidademin"] else None
                quantidademax = int(inter.text_values["quantidademax"]) if inter.text_values["quantidademax"] else None
            except:
                await inter.response.send_message(f"{negativo} Você informou algum valor inválido.")

            db = ObterDatabase()
            campo = db[self.produtoID]["campos"][self.campoID]
            campo["condicoes"]["valorMin"] = valuemin
            campo["condicoes"]["valorMax"] = valuemax
            campo["condicoes"]["quantidadeMin"] = quantidademin
            campo["condicoes"]["quantidadeMax"] = quantidademax
        
            with open("Database/Vendas/produtos.json", "w") as f:
                json.dump(db, f, indent=4)
            
            embed, components = Campo.ObterPainelGerenciarCampo(inter, self.produtoID, self.campoID)
            await inter.response.edit_message(embed=embed, components=components)

    class Cargos():
        @staticmethod
        def ObterDropdown(inter: disnake.MessageInteraction, produtoID: str, campoID: str):
            campo = ObterCampo(produtoID=produtoID, campoID=campoID)

            roleAdd = []
            for roleID in campo["cargos"]["add"]:
                try:
                    role = inter.guild.get_role(int(roleID))
                    if role:
                        roleAdd.append(SelectDefaultValue(id=role.id, type=SelectDefaultValueType.role))
                except: 
                    pass

            roleRem = []
            for roleID in campo["cargos"]["rem"]:
                try:
                    role = inter.guild.get_role(int(roleID))
                    if role:
                        roleRem.append(SelectDefaultValue(id=role.id, type=SelectDefaultValueType.role))
                except: 
                    pass

            dropdownCargos = [
                disnake.ui.RoleSelect(
                    placeholder="Selecione os cargos para serem adicionados",
                    max_values=25,
                    min_values=0,
                    custom_id=f"GerenciarCargos_Adicionar_{produtoID}_{campoID}",
                    default_values=roleAdd if roleAdd else None
                ),
                disnake.ui.RoleSelect(
                    placeholder="Selecione os cargos para serem removidos",
                    max_values=25,
                    min_values=0,
                    custom_id=f"GerenciarCargos_Remover_{produtoID}_{campoID}",
                    default_values=roleRem if roleRem else None
                ),
            ]

            return dropdownCargos
        
        @staticmethod
        def atualizarDB(produtoID: str, campoID: str, cargosAdd=None, cargosRem=None):
            db = ObterDatabase()

            if cargosAdd is not None:
                db[produtoID]["campos"][campoID]["cargos"]["add"] = cargosAdd
            
            if cargosRem is not None:
                db[produtoID]["campos"][campoID]["cargos"]["rem"] = cargosRem

            with open("Database/Vendas/produtos.json", "w") as f:
                json.dump(db, f, indent=4)

    @staticmethod
    async def Apagar(inter, produtoID: str, campoID: str):
        db = ObterDatabase()
        del(db[produtoID]["campos"][campoID])

        with open("Database/Vendas/produtos.json", "w") as f:
            json.dump(db, f, indent=4)

        await SincronizarMensagens(inter, produtoID)


    @staticmethod
    async def GerenciarCampos(inter: disnake.MessageInteraction, produtoID: str):
        await inter.response.edit_message(embed=None, components=[criar_loading_container("Carregando informações")])
        db = ObterDatabase()
        campos = db[produtoID]["campos"]

        options = []
        for campoID, campodata in campos.items():
            options.append(
                disnake.SelectOption(
                    label=campodata["nome"],
                    description=f"R${campodata['preco']}",
                    value=f"{produtoID}_{campoID}",
                    emoji=config3
                )
            )
        
        if not options:
            options.append(
                disnake.SelectOption(
                    label="Nenhum campo disponível",
                    value="null"
                ) 
            )
        
        select = disnake.ui.StringSelect(
            placeholder=f"[{len(campos)}] Clique aqui para selecionar",
            custom_id="SelecionarCampoDropdownVendas",
            options=options,
            disabled=True if len(campos) == 0 else False
        )

        container_elems = [
            disnake.ui.TextDisplay(f"# {caixa} Gerenciar Campos"),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(f"{inter.user.mention} Qual campo deseja gerenciar?"),
            disnake.ui.Separator(),
            disnake.ui.ActionRow(select),
            disnake.ui.ActionRow(
                disnake.ui.Button(style=disnake.ButtonStyle.green, label="Criar Campo", emoji=mais2, custom_id=f"CriarCampo_{produtoID}"),
                disnake.ui.Button(label="Voltar", emoji=voltar, custom_id=f"GerenciarProduto_{produtoID}")
            )
        ]

        container = disnake.ui.Container(*container_elems)
        await inter.edit_original_message(embed=None, components=[container])

    @staticmethod
    def ObterPainelGerenciarCampo(inter: disnake.MessageInteraction, produtoID: str, campoID: str):
        produto = ObterProduto(produtoID=produtoID)
        campo = ObterCampo(produtoID=produtoID, campoID=campoID)
        emoji_configurado = campo.get("emoji") or f"{negativo} ``Não definido``"
        is_subscription = campo.get("is_subscription", False)
        preco_comparacao = campo.get("comparison_price")
        preco_str = f"~~`R${preco_comparacao}`~~ **R${campo['preco']}**" if preco_comparacao else f"**R${campo['preco']}**"

        embed = disnake.Embed(
            description=f"""
### Detalhes
**Nome do produto:** ``{produto["nome"]}``
**Nome do campo:** ``{campo["nome"]}``
**Preço do campo:** {preco_str}
**Emoji do campo:** {emoji_configurado} 
**Descrição:**
{f"{negativo} ``Não informado``" if not campo.get("desc") else campo["desc"]}
            """,
            color=disnake.Color(0x00FFFF),
            timestamp=datetime.now()
        )
        embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon)
        embed.add_field(name="Condições", 
        value=f"""
-# Valor mínimo: {f"{negativo} ``Não informado``" if campo["condicoes"]["valorMin"] == None else f"`R${campo['condicoes']['valorMin']}`"}
-# Valor máximo: {f"{negativo} ``Não informado``" if campo["condicoes"]["valorMax"] == None else f"`R${campo['condicoes']['valorMax']}`"}
-# Quantidade mínima: {f"{negativo} ``Não informado``" if campo["condicoes"]["quantidadeMin"] == None else f"`{campo['condicoes']['quantidadeMin']}`"}
-# Quantidade máxima: {f"{negativo} ``Não informado``" if campo["condicoes"]["quantidadeMax"] == None else f"`{campo['condicoes']['quantidadeMax']}`"}
-# Quem não pode comprar? {len(campo["condicoes"]["idCargo"])} cargos
        """,
        inline=False)

        if is_subscription:
            detalhes = campo.get("subscription_details", {})
            role_id = detalhes.get("role_id")
            role_info = f"<@&{role_id}>" if role_id and inter.guild.get_role(int(role_id)) else f"{negativo} ``Cargo não definido``"
            duration = detalhes.get('duration_days', 30)
            vip_status = "Ativado" if detalhes.get("vip_enabled") else "Desativado"
            
            embed.add_field(
                name="Detalhes da Assinatura",
                value=f"""
> **Cargo:** {role_info}
> **Duração:** `{duration} dias`
> **VIP:** `{vip_status}`
-# > *Com o VIP ativado, o membro ganha acesso a recursos exclusivos. Desativado, é uma assinatura padrão.*
                """,
                inline=False
            )
        else:
            embed.add_field(name="Estoque disponível", value=f"``{len(campo['estoque'])}``", inline=True)
            embed.add_field(name="Última reposição", value=f"{f'<t:{campo['estoqueinfo']['last']}:f>' if campo['estoqueinfo']['last'] else f'{negativo} ``Não disponível``'}", inline=True)

        embed.add_field(name="Cargos Pós-Compra", value=f"""
-# Para adicionar: `{len(campo["cargos"]["add"])}`
-# Para remover: `{len(campo["cargos"]["rem"])}`
        """,
        inline=False)

        # BUTTONS
        components = []
        row1 = [
            disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Editar Campo", emoji=editar, custom_id=f"EditarCampo_{produtoID}_{campoID}"),
            disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Gerenciar Estoque", emoji=caixa, custom_id=f"GerenciarEstoque_{produtoID}_{campoID}", disabled=is_subscription),
        ]
        if is_subscription:
            row1.append(disnake.ui.Button(style=disnake.ButtonStyle.green, label="Gerenciar Assinatura", emoji=config3, custom_id=f"GerenciarAssinatura_{produtoID}_{campoID}"))
        components.append(row1)

        components.append(
            [
                disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Gerenciar Condições", emoji=attach, custom_id=f"GerenciarCondicoes_{produtoID}_{campoID}"),
                disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Gerenciar Cargos", emoji=users, custom_id=f"GerenciarCargos_{produtoID}_{campoID}"),
            ]
        )
        
        components.append(
            [
                disnake.ui.Button(style=disnake.ButtonStyle.red, label="Excluir campo", emoji=apagar, custom_id=f"ApagarCampo_{produtoID}_{campoID}"),
                disnake.ui.Button(style=disnake.ButtonStyle.red, label="Limpar Estoque", emoji=wand, custom_id=f"LimparEstoque_{produtoID}_{campoID}", disabled=is_subscription),
                disnake.ui.Button(
                    label="Tornar Produto" if is_subscription else "Tornar Assinatura",
                    emoji=reload,
                    custom_id=f"TornarProduto_{produtoID}_{campoID}" if is_subscription else f"TornarAssinatura_{produtoID}_{campoID}"
                ),
            ]
        )

        components.append(
            [
                disnake.ui.Button(label="Preço de Comparação", emoji=dollar, custom_id=f"DefinirPrecoComparacao_{produtoID}_{campoID}"),
                disnake.ui.Button(label="Sincronizar Mensagens", emoji=reload, custom_id=f"SincronizarProduto_{produtoID}"),
                disnake.ui.Button(label="Voltar", emoji=voltar, custom_id=f"GerenciarCampos_{produtoID}"),
            ]
        )
        return embed, components


    class Estoque():
        class AdicionarEstoqueFantasmaModal(disnake.ui.Modal):
            def __init__(self, produtoID: str, campoID: str):
                self.produtoID = produtoID
                self.campoID = campoID
                components = [
                    disnake.ui.TextInput(
                        label="Quantidade do Estoque Fantasma",
                        custom_id="quantidade_fantasma",
                        style=disnake.TextInputStyle.short,
                        placeholder="Digite a quantidade (número inteiro)",
                    ),
                    disnake.ui.TextInput(
                        label="Valor/Informação Entregue",
                        custom_id="valor_fantasma",
                        style=disnake.TextInputStyle.paragraph,
                        placeholder="Exemplo: Abra um suporte para resolver o problema",
                        required=True
                    ),
                ]
                super().__init__(title="Adicionar Estoque Fantasma", components=components)

            async def callback(self, inter: disnake.ModalInteraction):
                quantidade_texto = inter.text_values.get("quantidade_fantasma", "").strip()
                valor_fantasma = inter.text_values.get("valor_fantasma", "").strip()

                try:
                    quantidade = int(quantidade_texto)
                    if quantidade <= 0:
                        return await inter.response.send_message(f"{negativo} Quantidade inválida: insira um número inteiro maior que zero.", ephemeral=True)
                except ValueError:
                    await inter.response.send_message(f"{negativo} Quantidade inválida: insira um número inteiro maior que zero.", ephemeral=True)
                    return
            
                db = ObterDatabase()
                estoque_fantasma = [valor_fantasma] * quantidade
                db[self.produtoID]["campos"][self.campoID]["estoque"].extend(estoque_fantasma)
                db[self.produtoID]["campos"][self.campoID]["estoqueinfo"]["last"] = int(datetime.now().timestamp())

                with open("Database/Vendas/produtos.json", "w") as f:
                    json.dump(db, f, indent=4)

                embed, components = Campo.ObterPainelGerenciarCampo(inter, self.produtoID, self.campoID)
                await inter.response.edit_message("", embed=embed, components=components)
                await inter.followup.send(f"{positivo} Estoque adicionado com sucesso.\nInformações: ``{quantidade_texto}x {valor_fantasma}``", ephemeral=True)
                await SincronizarMensagens(inter, self.produtoID)
                await NotificarUserEstoque(inter, self.produtoID, self.campoID)

        class AdicionarEstoqueModal(disnake.ui.Modal):
            def __init__(self, produtoID, campoID):
                self.produtoID = produtoID
                self.campoID = campoID
                components = [
                    disnake.ui.TextInput(
                        label="Estoque (separado por linha)",
                        custom_id="estoque",
                        style=TextInputStyle.long,
                    ),
                ]
                super().__init__(title="Adicionar Estoque", components=components)

            async def callback(self, inter: disnake.ModalInteraction):
                await inter.response.edit_message(embed=None, components=[criar_loading_container("Carregando informações")])

                estoque_texto = inter.text_values.get("estoque")
                estoque_itens = [item.strip() for item in estoque_texto.split("\n") if item.strip()]
                
                if not estoque_itens:
                    await inter.response.send_message(f"{negativo} Nenhum item válido detectado no estoque.", ephemeral=True)
                    return

                db = ObterDatabase()
                db[self.produtoID]["campos"][self.campoID]["estoque"].extend(estoque_itens)
                db[self.produtoID]["campos"][self.campoID]["estoqueinfo"]["last"] = int(datetime.now().timestamp())

                with open("Database/Vendas/produtos.json", "w") as f:
                    json.dump(db, f, indent=4)

                embed, components = Campo.ObterPainelGerenciarCampo(inter, self.produtoID, self.campoID)
                await inter.edit_original_message(embed=embed, components=components)
                await inter.followup.send(f"{positivo} Estoque adicionado com sucesso.", ephemeral=True)
                await SincronizarMensagens(inter, self.produtoID)
                await NotificarUserEstoque(inter, self.produtoID, self.campoID)

        @staticmethod
        def ObterPainelGerenciarEstoque(inter: disnake.MessageInteraction, produtoID: str, campoID: str):
            embed = None
            components = [
                [
                    disnake.ui.Button(style=disnake.ButtonStyle.green, label="Adicionar", emoji=mais2, custom_id=f"AdicionarEstoque_{produtoID}_{campoID}"),
                    disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Adicionar Estoque Fantasma", emoji=fantasma, custom_id=f"AdicionarEstoqueFantasma_{produtoID}_{campoID}"),
                ],
                [
                    disnake.ui.Button(style=disnake.ButtonStyle.green, label="Enviar Arquivo", emoji=diretorio, custom_id=f"EnviarArquivoEstoque_{produtoID}_{campoID}"),
                    disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Pegar item do estoque", emoji=arrow, custom_id=f"PegarItemEstoque_{produtoID}_{campoID}"),
                ],
                [
                   disnake.ui.Button(label="Ver estoque", emoji=lupa, custom_id=f"VerEstoque_{produtoID}_{campoID}"),
                   disnake.ui.Button(label="Voltar", emoji=voltar, custom_id=f"GerenciarCampo_{produtoID}_{campoID}"),
                ]
            ]

            return embed, components
    
        @staticmethod
        async def AdicionarEstoqueArquivo(inter: disnake.MessageInteraction, produtoID: str, campoID: str):
            db = ObterDatabase()
            await inter.response.send_message("Envie o arquivo `.txt` contendo o estoque.", ephemeral=True)
            
            def check(message):
                return message.author == inter.author and isinstance(message, disnake.Message) and message.attachments
            
            try:
                msg = await inter.bot.wait_for("message", check=check, timeout=60.0)
            except Exception as e:
                error_container = disnake.ui.Container(
                    disnake.ui.TextDisplay(f"{negativo} Tempo esgotado. Operação cancelada.")
                )
                return await inter.edit_original_message(embed=None, components=[error_container])
            
            for attachment in msg.attachments:
                if attachment.filename.endswith(".txt"):
                    file_content = await attachment.read()
                    file_content = file_content.decode("utf-8")
                    
                    estoque_itens = [item.strip() for item in file_content.split("\n") if item.strip()]
                    
                    db[produtoID]["campos"][campoID]["estoque"].extend(estoque_itens)
                    db[produtoID]["campos"][campoID]["estoqueinfo"]["last"] = int(datetime.now().timestamp())
                    
                    with open("Database/Vendas/produtos.json", "w") as f:
                        json.dump(db, f, indent=4)
                    
                    await msg.delete()
            
            embed, components = Campo.ObterPainelGerenciarCampo(inter, produtoID, campoID)
            await inter.edit_original_message(embed=embed, components=components)
            
            await inter.followup.send(f"{positivo} Estoque adicionado com sucesso.", ephemeral=True)
            await SincronizarMensagens(inter, produtoID)
            await NotificarUserEstoque(inter, produtoID, campoID)

        @staticmethod
        def ApagarEstoque(produtoID: str, campoID: str):
            db = ObterDatabase()
            db[produtoID]["campos"][campoID]["estoque"] = []

            with open("Database/Vendas/produtos.json", "w") as f:
                json.dump(db, f, indent=4)

        @staticmethod
        def ObterEstoque(produtoID: str, campoID: str):
            nome_arquivo = f"Estoque_{produtoID}_{campoID}.txt"
            caminho_pasta = os.path.join("Database", "Vendas", "temp")
            caminho_completo = os.path.join(caminho_pasta, nome_arquivo)
            
            campo = ObterCampo(produtoID, campoID)
            os.makedirs(caminho_pasta, exist_ok=True)
            
            with open(caminho_completo, "w", encoding="utf-8") as arquivo:
                for linha in campo["estoque"]:
                    arquivo.write(linha + "\n")
            
            return caminho_completo

        @staticmethod
        def ObterItemEstoque(produtoID: str, campoID: str):
            db = ObterDatabase()
            estoque = db[produtoID]["campos"][campoID]["estoque"]
            item = estoque.pop(0)
            
            with open("Database/Vendas/produtos.json", "w") as f:
                json.dump(db, f, indent=4)
            
            return item

class Cupom():
    class CriarModal(disnake.ui.Modal):
        def __init__(self, produtoID: str):
            self.produtoID = produtoID
            components = [
                disnake.ui.TextInput(
                    label="Código do cupom",
                    placeholder="Ex: DESCONTO10",
                    custom_id="code",
                    style=disnake.TextInputStyle.short,
                    max_length=50,
                ),
                disnake.ui.TextInput(
                    label="Porcentagem de desconto (%)",
                    placeholder="Ex: 10 para 10% ou 5.5 para 5,5%",
                    custom_id="porcentagem",
                    style=disnake.TextInputStyle.short,
                ),
            ]
            super().__init__(title="Criar Cupom", components=components)

        async def callback(self, inter: disnake.ModalInteraction):
            nome_cupom = inter.text_values["code"].strip()
            porcentagem_texto = inter.text_values["porcentagem"].strip()

            try:
                porcentagem = float(porcentagem_texto)
                if porcentagem <= 0 or porcentagem > 100:
                    return await inter.response.send_message(f"{negativo} Insira um valor numérico válido entre 0 e 100!", ephemeral=True)
            except ValueError:
                return await inter.response.send_message(f"{negativo} Insira um valor numérico válido entre 0 e 100!", ephemeral=True)

            Cupom.Criar(nome_cupom, porcentagem, self.produtoID)
            embed, components = Cupom.ObterPainel(inter, self.produtoID, nome_cupom)
            await inter.response.edit_message("", embed=embed, components=components)

    class EditarModal(disnake.ui.Modal):
        def __init__(self, produtoID: str, nome: str):
            self.produtoID = produtoID
            self.nome = nome

            cupom = ObterCupom(produtoID, nome)

            components = [
                disnake.ui.TextInput(
                    label="Código do cupom",
                    placeholder="Ex: DESCONTO10",
                    custom_id="code",
                    style=disnake.TextInputStyle.short,
                    value=cupom["nome"],
                    max_length=50,
                ),
                disnake.ui.TextInput(
                    label="Porcentagem de desconto (%)",
                    placeholder="Ex: 10 para 10% ou 5.5 para 5,5%",
                    custom_id="porcentagem",
                    value=f"{cupom['porcentagem']}",
                    style=disnake.TextInputStyle.short,
                ),
            ]
            super().__init__(title="Editar Cupom", components=components)

        async def callback(self, inter: disnake.ModalInteraction):
            nome_cupom = inter.text_values["code"].strip()
            porcentagem_texto = inter.text_values["porcentagem"].strip()

            try:
                porcentagem = float(porcentagem_texto)
                if porcentagem <= 0 or porcentagem > 100:
                    return await inter.response.send_message(f"{negativo} Insira um valor numérico válido entre 0 e 100!", ephemeral=True)
            except ValueError:
                return await inter.response.send_message(f"{negativo} Insira um valor numérico válido entre 0 e 100!", ephemeral=True)

            Cupom.Editar(nome_cupom, porcentagem, self.produtoID)
            embed, components = Cupom.ObterPainel(inter, self.produtoID, nome_cupom)
            await inter.response.edit_message("", embed=embed, components=components)

    class AvançadosModal(disnake.ui.Modal):
        def __init__(self, produtoID: str, nome: str):
            self.produtoID = produtoID
            self.nome = nome

            cupom = ObterCupom(produtoID, nome)

            components = [
                disnake.ui.TextInput(
                    label="Valor mínimo para usar",
                    placeholder="Ex: 10 para 10 reais",
                    custom_id="value",
                    required=False,
                    style=disnake.TextInputStyle.short,
                    value=str(cupom["usage"]["minvalue"]),
                ),
                disnake.ui.TextInput(
                    label="Uso máximos (TOTAL)",
                    placeholder="Ex: 10 para 10 usos total",
                    custom_id="uses",
                    required=False,
                    value=str(cupom["usage"]["maxuses"]),
                    style=disnake.TextInputStyle.short,
                ),
            ]
            super().__init__(title="Editar Avançados Cupom", components=components)

        async def callback(self, inter: disnake.ModalInteraction):
            try:
                valormin = int(inter.text_values["value"].strip()) if inter.text_values["value"].strip() else ""
                usemax = int(inter.text_values["uses"].strip()) if inter.text_values["uses"].strip() else ""
            except:
                return await inter.response.send_message(f"{negativo} Forneça números válidos.", ephemeral=True)

            db = ObterDatabase()
            db[self.produtoID]["cupons"][self.nome] = {
                "nome": db[self.produtoID]["cupons"][self.nome]["nome"],
                "porcentagem": db[self.produtoID]["cupons"][self.nome]["porcentagem"],
                "usage": {
                    "minvalue": valormin,
                    "maxuses": usemax
                },
                "estatistics": {
                    "uses": db[self.produtoID]["cupons"][self.nome]["estatistics"]["uses"],
                    "economizado": db[self.produtoID]["cupons"][self.nome]["estatistics"]["economizado"]
                },
            }

            with open("Database/Vendas/produtos.json", "w") as f:
                json.dump(db, f, indent=4)

            embed, components = Cupom.ObterPainel(inter, self.produtoID, self.nome)
            await inter.response.edit_message("", embed=embed, components=components)

    @staticmethod
    def Criar(nome, porcentagem, produtoID):
        db = ObterDatabase()

        db[produtoID]["cupons"][nome] = {
            "nome": nome,
            "porcentagem": float(porcentagem),
            "usage": {
                "minvalue": "",
                "maxuses": ""
            },
            "estatistics": {
                "uses": 0,
                "economizado": 0
            },
        }

        with open("Database/Vendas/produtos.json", "w") as f:
            json.dump(db, f, indent=4)

    @staticmethod
    def Editar(nome, porcentagem, produtoID):
        db = ObterDatabase()

        db[produtoID]["cupons"][nome] = {
            "nome": nome,
            "porcentagem": float(porcentagem),
            "usage": {
                "minvalue": db[produtoID]["cupons"][nome]["usage"]["minvalue"],
                "maxuses": db[produtoID]["cupons"][nome]["usage"]["maxuses"]
            },
            "estatistics": {
                "uses": db[produtoID]["cupons"][nome]["estatistics"]["uses"],
                "economizado": db[produtoID]["cupons"][nome]["estatistics"]["economizado"]
            },
        }

        with open("Database/Vendas/produtos.json", "w") as f:
            json.dump(db, f, indent=4)
    
    @staticmethod
    def Apagar(produtoID, nome):
        db = ObterDatabase()
        del db[produtoID]["cupons"][nome]

        with open("Database/Vendas/produtos.json", "w") as f:
            json.dump(db, f, indent=4)


    @staticmethod
    async def GerenciarCupons(inter: disnake.MessageInteraction, produtoID: str):
        await inter.response.edit_message(embed=None, components=[criar_loading_container("Carregando cupons...")])

        db = ObterDatabase()

        product_data = db[produtoID]
        cupons = product_data.get("cupons", {})

        options = []
        for cupom_id, cupom_data in cupons.items():
            desconto = cupom_data.get("porcentagem", "Desconhecido")
            options.append(
                disnake.SelectOption(
                    label=f"{cupom_id}",
                    description=f"Porcentagem: {desconto}%",
                    value=f"{produtoID}_{cupom_id}"
                )
            )

        if not options:
            options.append(
                disnake.SelectOption(
                    label="Nenhum cupom disponível",
                    value="nenhum",
                    description="Não há cupons cadastrados."
                )
            )

        select = disnake.ui.StringSelect(
            placeholder=f"[{len(cupons)}] Selecione um cupom para gerenciar",
            custom_id="SelecionarCupomDropdownVendas",
            options=options,
            disabled=len(options) == 1 and options[0].value == "nenhum"
        )

        components = [
            select,
            disnake.ui.Button(style=disnake.ButtonStyle.green, label="Adicionar Cupom", emoji=mais2, custom_id=f"AdicionarCupom_{produtoID}"),
            disnake.ui.Button(label="Voltar", emoji=voltar, custom_id=f"GerenciarProduto_{produtoID}"),
        ]

        await inter.edit_original_message(
            content=f"{inter.user.mention} Qual cupom deseja gerenciar?",
            embed=None,
            components=components
        )

    @staticmethod
    def ObterPainel(inter, produtoID, nome):
        db = ObterDatabase()
        cupom = db[produtoID]["cupons"][nome]
        valorMin = f"R${cupom['usage']['minvalue']}" if cupom['usage']['minvalue'] else "Não definido"
        maxUses = f"{cupom['usage']['maxuses']}" if cupom['usage']['maxuses'] else "Não definido"
        usos = f"{cupom['estatistics']['uses']}"
        economizado = f"R${cupom['estatistics']['economizado']}"

        embed = disnake.Embed(
            description=f"""
### Detalhes
**Nome/Código:** ``{nome}``
**Porcentagem:** ``{cupom["porcentagem"]}%``
            """,
            color=disnake.Color(0x00FFFF),
            timestamp=datetime.now()
        )
        embed.set_author(name=f"Gerenciando o cupom: {nome}")
        embed.add_field(name="Informações Avançadas", value=f"-# Valor mínimo: {valorMin}\n-# Usos máximos: {maxUses}", inline=True)
        embed.add_field(name="Estatísticas", value=f"-# Usos: {usos}\n-# Valor economizado: {economizado}", inline=True)
        embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon)

        components = [
            [
                disnake.ui.Button(style=disnake.ButtonStyle.blurple, label="Editar", emoji=editar, custom_id=f"EditarCupom_{produtoID}_{nome}"),
                disnake.ui.Button(style=disnake.ButtonStyle.grey, label="Avançados", emoji=config2, custom_id=f"Avancados_{produtoID}_{nome}"),
            ],
            [

                disnake.ui.Button(style=disnake.ButtonStyle.red, label="Excluir Cupom", emoji=apagar, custom_id=f"ApagarCupom_{produtoID}_{nome}"),
                disnake.ui.Button(label="Voltar", emoji=voltar, custom_id=f"GerenciarCupons_{produtoID}"),
            ]
        ]

        if cupom: return embed, components
        else: return None, None

# Personalizar Loja
class PersonalizarLoja():
    async def PersonalizarLoja(inter: disnake.MessageInteraction):
        with open("Database/Vendas/vendas.json") as f:
            config = json.load(f)
        
        embed = disnake.Embed(
            title="Personalizar Loja",
            description="""
Aqui você consegue personalizar e configurar a sua loja do seu jeito. Use sua criatividade para alterar cores, cargos e instruções.
**Lembre-se:** as alterações são utilizadas apenas na parte do carrinho.
""",
            color=disnake.Color(0x00FFFF),
            timestamp=datetime.now()
        )

# Events Listener

class VendasCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Commands

    @commands.slash_command()
    async def manage(self, inter):
        pass

    @manage.sub_command(description="Use to manage a specific product")
    async def produto(
        self,
        inter: disnake.ApplicationCommandInteraction,
        produto: str = commands.Param(description="Selecione um produto", autocomplete=True),
    ):
        if not VerificarDM(inter):
            return await inter.response.send_message(f"{negativo} Use este comando apenas em servidores", ephemeral=True)
        
        if produto != "FaltamPermissoes":
            components = Produto.ObterPainelGerenciarProduto(inter, produto)
            await inter.response.send_message(embed=None, components=components, ephemeral=True)
        else: await inter.response.send_message(f"{negativo} Faltam permissões.", ephemeral=True)

    @produto.autocomplete("produto")
    async def produto_autocomplete(
        self, inter: disnake.ApplicationCommandInteraction, string: str
    ):
        produtos_db = ObterDatabase()

        if verificar_permissao(inter.author.id):
            suggestions = [
                disnake.OptionChoice(
                    name=f"🛒 {dados['nome']}",
                    value=produto_id
                )
                for produto_id, dados in produtos_db.items()
                if string.lower() in dados["nome"].lower()
            ]
        else:
            suggestions = [
                disnake.OptionChoice(
                    name="❌ Faltam permissões",
                    value="FaltamPermissoes"
                )
            ]

        return suggestions[:25]

    @manage.sub_command(description="Use to manage a specific item")
    async def item(
        self,
        inter: disnake.ApplicationCommandInteraction,
        opcao: str = commands.Param(description="Selecione um produto e campo", autocomplete=True),
    ):
        if not VerificarDM(inter):
            return await inter.response.send_message(f"{negativo} Use este comando apenas em servidores", ephemeral=True)
        
        if opcao != "FaltamPermissoes":
            produto_id, campo_id = opcao.split(":")
            embed, components = Campo.ObterPainelGerenciarCampo(inter, produto_id, campo_id)
            await inter.response.send_message(embed=embed, components=components, ephemeral=True)
        else: await inter.response.send_message(f"{negativo} Faltam permissões.", ephemeral=True)

    @item.autocomplete("opcao")
    async def campo_autocomplete(
        self, inter: disnake.ApplicationCommandInteraction, string: str
    ):
        produtos_db = ObterDatabase()

        if verificar_permissao(inter.author.id):
            suggestions = []
            for produto_id, produto_data in produtos_db.items():
                nome_produto = produto_data["nome"]
                campos = produto_data.get("campos", {})
                for campo_id, campo_data in campos.items():
                    nome_campo = campo_data["nome"]

                    display_name = f"🛒 {nome_produto} ▸ {nome_campo}"
                    value = f"{produto_id}:{campo_id}"
                    if string.lower() in display_name.lower():
                        suggestions.append(disnake.OptionChoice(name=display_name, value=value))
        else:
            suggestions = [
                disnake.OptionChoice(
                    name="❌ Faltam permissões",
                    value="FaltamPermissoes"
                )
            ]

        return suggestions[:25]

    # Listener

    @commands.Cog.listener("on_button_click")
    async def VendasButtonListener(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id

        if cid == "GerenciarPainelVendas":
            if not self.bot.verificar_permissao(inter.author.id, "panel", "GerenciarPainelVendas"):
                return await inter.response.send_message(
                    f"{negativo} Você não tem permissão para acessar este painel.", 
                    ephemeral=True
                )
            
            loading_container = disnake.ui.Container(
                disnake.ui.TextDisplay(f"{carregarAnimado} Carregando...")
            )
            await inter.response.edit_message(embed=None, components=[loading_container])
            components = ObterPainelPrincipal(inter)
            await inter.edit_original_message(embed=None, components=components)
        
        # Sistema de extensões removido
        # elif cid == "GerenciarExtensoesDeSaldo":
              
        elif cid == "DefinirInstrucoesVendas": 
            await inter.response.send_modal(AlterarInstrucoesModal())
        
        elif cid == "GerenciarMarcaVendas": await inter.response.send_modal(AlterarMarcaModal())
        
        elif cid == "CriarProdutoVendas": await inter.response.send_modal(Produto.CriarProdutoModal())
        elif cid == "GerenciarProdutosVendas": await Produto.GerenciarProdutos(inter=inter)

        elif cid.startswith("EditarProduto_"):
            produtoID = cid.replace("EditarProduto_", "")
            await inter.response.edit_message(embed=None, components=[criar_loading_container("Carregando painel de edição...")])
            embed, components = Produto.ObterPainelEditarProduto(inter, produtoID)
            await inter.edit_original_message(embed=embed, components=components)
        elif cid.startswith("EditarConteudo_"):
            produtoID = cid.replace("EditarConteudo_", "")
            await inter.response.send_modal(Produto.EditarContentModal(produtoID))
        elif cid.startswith("LimparConteudo_"):
            await inter.response.defer(ephemeral=True)
            produtoID = cid.replace("LimparConteudo_", "")
            db = ObterDatabase()
            db[produtoID]["content"] = None
            with open("Database/Vendas/produtos.json", "w") as f: json.dump(db, f, indent=4)
            await SincronizarMensagens(inter, produtoID)
            await inter.followup.send(f"{positivo} Conteúdo limpo com sucesso!", ephemeral=True)
        elif cid.startswith("EditarEmbed_"):
            produtoID = cid.replace("EditarEmbed_", "")
            await inter.response.send_modal(Produto.EditarProdutoModal(produtoID))
        elif cid.startswith("LimparEmbed_"):
            await inter.response.defer(ephemeral=True)
            produtoID = cid.replace("LimparEmbed_", "")
            db = ObterDatabase()
            # CORREÇÃO: Não limpar o nome do produto, manter o nome original
            db[produtoID]["desc"] = None
            db[produtoID]["assets"]["icon"] = None
            db[produtoID]["assets"]["banner"] = None
            db[produtoID]["assets"]["hex"] = "000000"
            with open("Database/Vendas/produtos.json", "w") as f: json.dump(db, f, indent=4)
            await SincronizarMensagens(inter, produtoID)
            await inter.followup.send(f"{positivo} Embed limpa com sucesso!", ephemeral=True)
        elif cid.startswith("ConfigurarImagem_"):
            produtoID = cid.replace("ConfigurarImagem_", "")
            await inter.response.send_modal(Produto.ConfigurarImagemModal(produtoID))
        elif cid.startswith("LimparImagem_"):
            await inter.response.defer(ephemeral=True)
            produtoID = cid.replace("LimparImagem_", "")
            db = ObterDatabase()
            db[produtoID]["image_url"] = None
            with open("Database/Vendas/produtos.json", "w") as f: json.dump(db, f, indent=4)
            await SincronizarMensagens(inter, produtoID)
            await inter.followup.send(f"{positivo} Imagem limpa com sucesso!", ephemeral=True)
        
        elif cid.startswith("GerenciarProduto_"):
            await inter.response.edit_message(embed=None, components=[criar_loading_container("Carregando informações")])
            produtoID = cid.replace("GerenciarProduto_", "")
            produto = ObterProduto(produtoID)
            if produto:
                components = Produto.ObterPainelGerenciarProduto(inter, produtoID)
                await inter.edit_original_message(embed=None, components=components)
            else: 
                error_container = disnake.ui.Container(
                    disnake.ui.TextDisplay(f"{negativo} O produto não foi encontrado. Tente novamente.")
                )
                await inter.edit_original_message(embed=None, components=[error_container])

        elif cid.startswith("ApagarProduto_"):
            produtoID = cid.replace("ApagarProduto_", "")
            Produto.Apagar(produtoID)
            await Produto.GerenciarProdutos(inter)
            await SincronizarMensagens(inter, produtoID, delete=True)

        elif cid.startswith("GerenciarCupons_"):
            produtoID = cid.replace("GerenciarCupons_", "")
            await Cupom.GerenciarCupons(inter, produtoID)
        
        elif cid.startswith("AdicionarCupom_"):
            produtoID = cid.replace("AdicionarCupom_", "")
            await inter.response.send_modal(Cupom.CriarModal(produtoID))

        elif cid.startswith("EditarCupom_"):
            _, produtoID, cupom = cid.split("_")
            await inter.response.send_modal(Cupom.EditarModal(produtoID=produtoID, nome=cupom))

        elif cid.startswith("Avancados_"):
            _, produtoID, cupom = cid.split("_")
            await inter.response.send_modal(Cupom.AvançadosModal(produtoID, cupom))

        elif cid.startswith("ApagarCupom_"):
            _, produtoID, cupom = cid.split("_")
            Cupom.Apagar(produtoID=produtoID, nome=cupom)

            await Cupom.GerenciarCupons(inter, produtoID)

        elif cid.startswith("GerenciarCampos_"):
            produtoID = cid.replace("GerenciarCampos_", "")
            await Campo.GerenciarCampos(inter, produtoID)
        
        elif cid.startswith("CriarCampo_"):
            produtoID = cid.replace("CriarCampo_", "")
            await inter.response.send_modal(Campo.Criar(produtoID))

        elif cid.startswith("GerenciarCampo_"):
            await inter.response.edit_message(embed=None, components=[criar_loading_container("Carregando informações")])
            _, produtoID, campoID = cid.split("_")
            embed, components = Campo.ObterPainelGerenciarCampo(inter, produtoID, campoID)
            await inter.edit_original_message(embed=embed, components=components)

        elif cid.startswith("EditarCampo_"):
            _, produtoID, campoID = cid.split("_")
            await inter.response.send_modal(Campo.Editar(produtoID=produtoID, campoID=campoID))
        
        elif cid.startswith("ApagarCampo_"):
            _, produtoID, campoID = cid.split("_")
            await Campo.Apagar(inter, produtoID, campoID)
            await Campo.GerenciarCampos(inter, produtoID)
        
        elif cid.startswith("GerenciarCondicoes_"):
            _, produtoID, campoID = cid.split("_")
            await inter.response.send_modal(Campo.Condicoes(produtoID=produtoID, campoID=campoID))
        
        elif cid.startswith("GerenciarCargos_"):
            _, produtoID, campoID = cid.split("_")
            components = Campo.Cargos.ObterDropdown(inter, produtoID, campoID)
            components.append(
                disnake.ui.Button(
                    label="Voltar",
                    emoji=voltar,
                    custom_id=f"GerenciarCampo_{produtoID}_{campoID}"),
            )
            await inter.response.edit_message(components=components)
        
        # --- HANDLERS DE ASSINATURA ---
        elif cid.startswith("TornarAssinatura_"):
            await inter.response.edit_message(embed=None, components=[criar_loading_container()])
            _, produtoID, campoID = cid.split("_")
            db = ObterDatabase()
            db[produtoID]["campos"][campoID]["is_subscription"] = True
            with open("Database/Vendas/produtos.json", "w") as f:
                json.dump(db, f, indent=4)
            await SincronizarMensagens(inter, produtoID)
            embed, components = Campo.ObterPainelGerenciarCampo(inter, produtoID, campoID)
            await inter.edit_original_message(embed=embed, components=components)

        elif cid.startswith("TornarProduto_"):
            await inter.response.edit_message(embed=None, components=[criar_loading_container()])
            _, produtoID, campoID = cid.split("_")
            db = ObterDatabase()
            db[produtoID]["campos"][campoID]["is_subscription"] = False
            with open("Database/Vendas/produtos.json", "w") as f:
                json.dump(db, f, indent=4)
            await SincronizarMensagens(inter, produtoID)
            embed, components = Campo.ObterPainelGerenciarCampo(inter, produtoID, campoID)
            await inter.edit_original_message(embed=embed, components=components)

        elif cid.startswith("DefinirPrecoComparacao_"):
            _, produtoID, campoID = cid.split("_")
            await inter.response.send_modal(Campo.DefinirPrecoComparacaoModal(produtoID, campoID))

        elif cid.startswith("GerenciarAssinatura_"):
            await inter.response.edit_message(embed=None, components=[criar_loading_container()])
            _, produtoID, campoID = cid.split("_")
            embed, components = Campo.Assinatura.ObterPainelGerenciarAssinatura(inter, produtoID, campoID)
            await inter.edit_original_message(content=None, embed=embed, components=components)

        elif cid.startswith("ConfigurarCargoAssinatura_"):
            _, produtoID, campoID = cid.split("_")
            await inter.response.send_modal(Campo.Assinatura.ConfigurarCargoAssinaturaModal(produtoID, campoID))

        elif cid.startswith("ToggleVIP_") or cid.startswith("ToggleInatividade_") or cid.startswith("ToggleEsconderCall_"):
            await inter.response.defer()
            toggle_type, produtoID, campoID = cid.split("_")
            
            db = ObterDatabase()
            campo = db[produtoID]["campos"][campoID]
            detalhes = campo.get("subscription_details", {})
            
            key_map = {
                "ToggleVIP": "vip_enabled",
                "ToggleInatividade": "inactivity_enabled",
                "ToggleEsconderCall": "hide_call_enabled"
            }
            key_to_toggle = key_map[toggle_type]

            detalhes[key_to_toggle] = not detalhes.get(key_to_toggle, False)
            campo["subscription_details"] = detalhes
            
            with open("Database/Vendas/produtos.json", "w") as f:
                json.dump(db, f, indent=4)
                
            embed, components = Campo.Assinatura.ObterPainelGerenciarAssinatura(inter, produtoID, campoID)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        # --- FIM DOS HANDLERS DE ASSINATURA ---
            
        elif cid.startswith("GerenciarEstoque_"):
            await inter.response.edit_message(embed=None, components=[criar_loading_container("Carregando informações")])
            if verificar_permissao(inter.author.id):
                _, produtoID, campoID = cid.split("_")
                embed, components = Campo.Estoque.ObterPainelGerenciarEstoque(inter, produtoID, campoID)
                await inter.edit_original_message(embed=embed, components=components)
            else: 
                error_container = disnake.ui.Container(
                    disnake.ui.TextDisplay(f"{negativo} Você não tem permissão para executar essa função.")
                )
                await inter.edit_original_message(embed=None, components=[error_container])
            
        elif cid.startswith("LimparEstoque_"):
            await inter.response.edit_message(embed=None, components=[criar_loading_container("Carregando informações")])
            _, produtoID, campoID = cid.split("_")
            Campo.Estoque.ApagarEstoque(produtoID, campoID)
            embed, components = Campo.ObterPainelGerenciarCampo(inter, produtoID, campoID)
            await inter.edit_original_message(embed=embed, components=components)
            await SincronizarMensagens(inter, produtoID)

        elif cid.startswith("AdicionarEstoqueFantasma_"):
            _, produtoID, campoID = cid.split("_")
            await inter.response.send_modal(Campo.Estoque.AdicionarEstoqueFantasmaModal(produtoID, campoID))

        elif cid.startswith("AdicionarEstoque_"):
            _, produtoID, campoID = cid.split("_")
            await inter.response.send_modal(Campo.Estoque.AdicionarEstoqueModal(produtoID, campoID))

        elif cid.startswith("VerEstoque_"):
            _, produtoID, campoID = cid.split("_")
            campo = ObterCampo(produtoID, campoID)
            if len(campo["estoque"]) <= 0:
                return await inter.response.send_message(f"{negativo} Não há estoque no produto.", ephemeral=True, delete_after=3)
            
            estoquefp = Campo.Estoque.ObterEstoque(produtoID, campoID)
            await inter.response.send_message(files=[disnake.File(fp=estoquefp)], ephemeral=True)
            os.remove(estoquefp)
        
        elif cid.startswith("PegarItemEstoque_"):
            _, produtoID, campoID = cid.split("_")
            campo = ObterCampo(produtoID, campoID)
            if len(campo["estoque"]) <= 0:
                return await inter.response.send_message(f"{negativo} Não há estoque no produto.", ephemeral=True, delete_after=3)
            
            item = Campo.Estoque.ObterItemEstoque(produtoID, campoID)
            await inter.response.send_message(f"{positivo} Seu item está pronto:\n```{item}```", ephemeral=True)
            await SincronizarMensagens(inter, produtoID)

        elif cid.startswith("EnviarArquivoEstoque_"):
            _, produtoID, campoID = cid.split("_")
            await Campo.Estoque.AdicionarEstoqueArquivo(inter, produtoID, campoID)

        elif cid.startswith("ColocarVenda_"):
            produtoID = cid.replace("ColocarVenda_", "")
            select = disnake.ui.ChannelSelect(
                placeholder="Selecione o canal onde o produto será enviado",
                custom_id=f"EnviarProduto_{produtoID}",
                channel_types=[ChannelType.text]
            )
            await inter.response.send_message(components=select, ephemeral=True)

        elif cid.startswith("SincronizarProduto_"):
            await inter.response.send_message(f"{carregarAnimado} Sincronizando mensagens", ephemeral=True)
            produtoID = cid.replace("SincronizarProduto_", "")
            await SincronizarMensagens(inter, produtoID)
            success_container = disnake.ui.Container(
                disnake.ui.TextDisplay(f"{positivo} Mensagens sincronizadas com sucesso")
            )
            await inter.edit_original_message(embed=None, components=[success_container])

        elif cid.startswith("AtivarDesativarEntregaAuto_"):
            produtoID = cid.replace("AtivarDesativarEntregaAuto_", "")
            await inter.response.edit_message(embed=None, components=[criar_loading_container("Carregando informações")])
            db = ObterDatabase()
            produto = ObterProduto(produtoID)
            if not produto: 
                error_container = disnake.ui.Container(
                    disnake.ui.TextDisplay(f"{negativo} Produto não encontrado")
                )
                return await inter.edit_original_message(embed=None, components=[error_container])

            db[produtoID]["entrega"] = not produto["entrega"]

            with open("Database/Vendas/produtos.json", "w") as f:
                json.dump(db, f, indent=4)
            
            components = Produto.ObterPainelGerenciarProduto(inter, produtoID)
            await inter.edit_original_message(embed=None, components=components)

    @commands.Cog.listener("on_dropdown")
    async def VendasDropdownListener(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if cid == "SelecionarProdutoDropdownVendas":
            if inter.values[0] == "null": return await inter.response.defer()
            await inter.response.edit_message(embed=None, components=[criar_loading_container()])
            components = Produto.ObterPainelGerenciarProduto(inter, inter.values[0])
            await inter.edit_original_message(embed=None, components=components)
          
        elif cid == "SelecionarCampoDropdownVendas":
            if inter.values[0] == "null": return await inter.response.defer()
            await inter.response.edit_message(embed=None, components=[criar_loading_container("Carregando informações")])
            produtoID, campoID = inter.values[0].split("_")
            embed, components = Campo.ObterPainelGerenciarCampo(inter, produtoID, campoID)
            await inter.edit_original_message(embed=embed, components=components)

        elif cid == "SelecionarCupomDropdownVendas":
            if inter.values[0] == "nenhum": return await inter.response.defer()
            await inter.response.edit_message(embed=None, components=[criar_loading_container("Carregando informações")])
            produtoID, cupomID = inter.values[0].split("_")
            embed, components = Cupom.ObterPainel(inter, produtoID, cupomID)
            await inter.edit_original_message(embed=embed, components=components)

        elif cid.startswith("EnviarProduto_"):
            channel_id = inter.values[0]
            produtoID = cid.replace("EnviarProduto_", "")
            channel = inter.guild.get_channel(int(channel_id))
            
            payload = GerarPainelProduto(inter, produtoID, para_venda=True)
            
            if not payload.get("content") and not payload.get("embeds"):
                return await inter.response.edit_message(f"{negativo} Impossível enviar: o produto está vazio.", components=None)
            
            try:
                msg = await channel.send(**payload)
                db = ObterDatabase()
                db[produtoID]["ids"].append({f"{msg.channel.id}": f"{msg.id}"})
                with open("Database/Vendas/produtos.json", "w") as f: json.dump(db, f, indent=4)
                await inter.response.edit_message(f"{positivo} Mensagem enviada com sucesso em: {msg.jump_url}", components=None)
            except Exception as e:
                await inter.response.edit_message(f"{negativo} Ocorreu um erro ao enviar o produto: {e}", components=None)
              
        elif cid.startswith("GerenciarCargos_"):
            _, type, produtoID, campoID = cid.split("_")
            
            if type == "Adicionar":
                cargosAdd = [int(role_id) for role_id in inter.values]
                Campo.Cargos.atualizarDB(produtoID, campoID, cargosAdd=cargosAdd, cargosRem=None)
            elif type == "Remover":
                cargosRem = [int(role_id) for role_id in inter.values]
                Campo.Cargos.atualizarDB(produtoID, campoID, cargosAdd=None, cargosRem=cargosRem)

            # Verificar se estamos no contexto de assinatura
            campo = ObterCampo(produtoID, campoID)
            if campo and campo.get("is_subscription"):
                embed, components = Campo.Assinatura.ObterPainelGerenciarAssinatura(inter, produtoID, campoID)
            else:
                embed, components = Campo.ObterPainelGerenciarCampo(inter, produtoID, campoID)
            
            await inter.response.edit_message("", embed=embed, components=components)

def setup(bot: commands.Bot):
    bot.add_cog(VendasCommand(bot))