import disnake
from disnake.ext import commands
import json
import os
import aiohttp
import io
import random
import asyncio
from datetime import datetime, timedelta

API_BASE_URL = "https://routeapieconomia.squareweb.app"

MAIN_CONFIG_FILE = "config.json"
ECONOMY_CONFIG_FILE = "Database/Economia/configuracao.json"
USERS_DATA_FILE = "Database/Economia/users.json"
PETS_DATA_FILE = "Database/Economia/petusers.json"
MINER_DATA_FILE = "Database/Economia/mineradoras.json"
REP_DATA_FILE = "Database/Economia/reputacao.json"
MULTAS_DATA_FILE = "Database/Economia/multas.json"
INVENTORY_DATA_FILE = "Database/Economia/inventario.json"

# Comandos por categoria
COMMANDS_BY_CATEGORY = {
    "Economia": ["daily", "trabalhar", "roubar", "banco", "aposta", "crime", "pagar", "rep", "profile", "contribuição", "minerar", "pescar", "slots"],
    "Roleplay": ["abraçar", "casar", "divórcio", "beijar", "gf", "lua de mel", "afk", "x1", "whatsapp", "ship", "pet", "pet battle", "loja", "prefeitura", "mercador"],
    "Diversão": ["8ball", "akinator", "waifu", "snake", "raul", "manga", "joke", "jokenpo", "ironmen", "hangmen", "guess", "diabo", "buti"],
    "Nsfw": ["anal", "hentai", "neko", "feet", "lesbian", "boobs", "pussy"]
}

def get_default_config():
    config = {"categorias": {}}
    for category, cmds in COMMANDS_BY_CATEGORY.items():
        config["categorias"][category.lower()] = {cmd.lower(): True for cmd in cmds}
    return config

def load_json(file_path, is_econ_config=False):
    dir_path = os.path.dirname(file_path)
    if dir_path: 
        os.makedirs(dir_path, exist_ok=True)
    if not os.path.exists(file_path):
        default_data = get_default_config() if is_econ_config else {}
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, indent=4)
        return default_data
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not data and is_econ_config:
                return get_default_config()
            return data
    except (json.JSONDecodeError, FileNotFoundError):
        return get_default_config() if is_econ_config else {}

def save_json(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

async def gerar_imagem_api(endpoint: str, payload: dict) -> bytes | None:
    if not API_BASE_URL or API_BASE_URL == "https://routeapieconomia.squareweb.app":
        return None
    url = f"{API_BASE_URL}/{endpoint}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    return await response.read()
                return None
    except Exception:
        return None

def get_or_create_user(user_id):
    users_data = load_json(USERS_DATA_FILE)
    user_id_str = str(user_id)
    if user_id_str not in users_data:
        users_data[user_id_str] = {
            "wallet": 0, 
            "bank": 0, 
            "cooldowns": {},
            "xp": 0,
            "level": 1,
            "married_to": None,
            "marriage_date": None
        }
    return users_data, users_data[user_id_str]

def get_or_create_inventory(user_id):
    inventory_data = load_json(INVENTORY_DATA_FILE)
    user_id_str = str(user_id)
    if user_id_str not in inventory_data:
        inventory_data[user_id_str] = {
            "armas": {},
            "coletes": {},
            "licencas": {
                "arma": False,
                "colete": False
            }
        }
    return inventory_data, inventory_data[user_id_str]

def get_or_create_multas(user_id):
    multas_data = load_json(MULTAS_DATA_FILE)
    user_id_str = str(user_id)
    if user_id_str not in multas_data:
        multas_data[user_id_str] = {
            "total": 0,
            "multas": []
        }
    return multas_data, multas_data[user_id_str]

def format_timedelta(td: timedelta):
    s = td.total_seconds()
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    parts = []
    if d > 0: parts.append(f"{int(d)}d")
    if h > 0: parts.append(f"{int(h)}h")
    if m > 0: parts.append(f"{int(m)}m")
    if s > 0 and not parts: parts.append(f"{int(s)}s")
    return " ".join(parts) if parts else "agora"

def add_multa(user_id, motivo: str, valor: int):
    all_multas_data, user_multas = get_or_create_multas(user_id)
    user_multas["total"] += valor
    user_multas["multas"].append({
        "motivo": motivo,
        "valor": valor,
        "data": datetime.now().isoformat()
    })
    save_json(all_multas_data, MULTAS_DATA_FILE)

# Configurações da loja
LOJA_ITEMS = {
    "armas_brancas": {
        "faca": {"nome": "Faca", "preco": 500, "dano": 15, "emoji": "🔪"},
        "machado": {"nome": "Machado", "preco": 1200, "dano": 25, "emoji": "🪓"},
        "katana": {"nome": "Katana", "preco": 2500, "dano": 40, "emoji": "⚔️"},
        "espada": {"nome": "Espada", "preco": 3000, "dano": 45, "emoji": "🗡️"}
    },
    "armas_fogo": {
        "pistola": {"nome": "Pistola", "preco": 5000, "dano": 60, "emoji": "🔫"},
        "rifle": {"nome": "Rifle", "preco": 12000, "dano": 85, "emoji": "🔫"},
        "sniper": {"nome": "Sniper", "preco": 20000, "dano": 120, "emoji": "🔫"},
        "ak47": {"nome": "AK-47", "preco": 18000, "dano": 100, "emoji": "🔫"}
    },
    "coletes": {
        "colete_leve": {"nome": "Colete Leve", "preco": 2000, "protecao": 20, "emoji": "🦺"},
        "colete_pesado": {"nome": "Colete Pesado", "preco": 4500, "protecao": 40, "emoji": "🦺"},
        "colete_blindado": {"nome": "Colete Blindado", "preco": 8000, "protecao": 60, "emoji": "🦺"}
    }
}

# Modals
class PetUparModal(disnake.ui.Modal):
    def __init__(self, pet_data: dict, currency_symbol: str):
        self.pet_data = pet_data
        self.currency_symbol = currency_symbol
        self.nivel_atual = pet_data.get('nivel', 1)
        components = [
            disnake.ui.TextInput(
                label=f"Nível Atual: {self.nivel_atual}",
                custom_id="nivel_desejado",
                placeholder="Digite o nível que deseja alcançar",
                style=disnake.TextInputStyle.short,
                required=True
            )
        ]
        super().__init__(title="Upar Pet", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)
        try:
            nivel_desejado = int(inter.text_values["nivel_desejado"])
        except ValueError:
            await inter.followup.send("❌ Por favor, insira um número válido.")
            return

        if nivel_desejado <= self.nivel_atual:
            await inter.followup.send(f"❌ O nível desejado ({nivel_desejado}) deve ser maior que o atual ({self.nivel_atual}).")
            return

        niveis_a_upar = nivel_desejado - self.nivel_atual
        custo_total = sum((self.nivel_atual + i + 1) * 1000 for i in range(niveis_a_upar))

        all_users_data, user_data = get_or_create_user(inter.author.id)
        if user_data['wallet'] < custo_total:
            await inter.followup.send(f"❌ Você precisa de **{custo_total:,} {self.currency_symbol}**, mas você só tem {user_data['wallet']:,} {self.currency_symbol}.")
            return
            
        user_data['wallet'] -= custo_total
        save_json(all_users_data, USERS_DATA_FILE)

        pets_data = load_json(PETS_DATA_FILE)
        pet_user_data = pets_data.get(str(inter.author.id))
        if pet_user_data:
            pet_user_data['nivel'] = nivel_desejado
            pet_user_data['damage'] += niveis_a_upar * 10
            pet_user_data['shield'] += niveis_a_upar * 8
            pet_user_data['health'] += niveis_a_upar * 15
            pet_user_data['critical'] += niveis_a_upar * 0.5
            save_json(pets_data, PETS_DATA_FILE)

        await inter.followup.send(f"✨ Pet upado para o nível **{nivel_desejado}**! Custou **{custo_total:,} {self.currency_symbol}**.")

class ApostaModal(disnake.ui.Modal):
    def __init__(self, currency_symbol: str, cog):
        self.currency_symbol = currency_symbol
        self.cog = cog
        components = [
            disnake.ui.TextInput(
                label="Valor da Aposta",
                custom_id="valor_aposta",
                placeholder="Digite o valor que deseja apostar",
                style=disnake.TextInputStyle.short,
                required=True
            )
        ]
        super().__init__(title="Fazer Aposta", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        try:
            valor = int(inter.text_values["valor_aposta"])
        except ValueError:
            await inter.response.send_message("❌ Por favor, insira um valor válido.", ephemeral=True)
            return

        if valor <= 0:
            await inter.response.send_message("❌ O valor deve ser positivo.", ephemeral=True)
            return

        all_users_data, user_data = get_or_create_user(inter.author.id)
        if user_data['wallet'] < valor:
            await inter.response.send_message(f"❌ Você não tem **{valor:,} {self.currency_symbol}**.", ephemeral=True)
            return

        # Sistema de aposta simples (50% chance)
        if random.random() < 0.5:
            ganho = int(valor * 1.8)  # Ganha 80% a mais
            user_data['wallet'] += ganho - valor  # Remove aposta e adiciona ganho
            resultado = f"🎉 **GANHOU!** Você apostou **{valor:,}** e ganhou **{ganho:,} {self.currency_symbol}**!"
        else:
            user_data['wallet'] -= valor
            resultado = f"😔 **PERDEU!** Você perdeu **{valor:,} {self.currency_symbol}**."

        save_json(all_users_data, USERS_DATA_FILE)
        
        embed = disnake.Embed(
            title="🎰 Resultado da Aposta",
            description=resultado,
            color=disnake.Color.green() if "GANHOU" in resultado else disnake.Color.red()
        )
        embed.add_field(name="Saldo Atual", value=f"{user_data['wallet']:,} {self.currency_symbol}")
        
        await inter.response.send_message(embed=embed)

# Views
class PetActionView(disnake.ui.View):
    def __init__(self, author: disnake.User, cog_instance):
        super().__init__(timeout=180)
        self.author = author
        self.cog = cog_instance

    async def interaction_check(self, inter: disnake.MessageInteraction):
        if inter.author.id != self.author.id:
            await inter.response.send_message("❌ Esta não é uma interação para você!", ephemeral=True)
            return False
        return True

    @disnake.ui.string_select(
        placeholder="Escolha uma ação...",
        custom_id="pet_action_select"
    )
    async def on_select(self, select: disnake.ui.StringSelect, inter: disnake.MessageInteraction):
        action = inter.values[0]

        if action == "comprar":
            _, user_data = get_or_create_user(self.author.id)
            custo = 5000
            
            if user_data['wallet'] < custo:
                await inter.response.send_message(f"❌ Você precisa de **{custo:,} {self.cog.moeda_emoji}** para comprar um pet.", ephemeral=True)
                return
            
            pets_disponiveis = ["🐕 Cachorro", "🐱 Gato", "🐦 Pássaro", "🐹 Hamster", "🐰 Coelho"]
            pet_escolhido = random.choice(pets_disponiveis)
            
            user_data['wallet'] -= custo
            all_users_data = load_json(USERS_DATA_FILE)
            all_users_data[str(self.author.id)] = user_data
            save_json(all_users_data, USERS_DATA_FILE)
            
            pets_data = load_json(PETS_DATA_FILE)
            pets_data[str(self.author.id)] = {
                "nome": pet_escolhido,
                "nivel": 1,
                "xp": 0,
                "damage": 20,
                "shield": 15,
                "health": 100,
                "critical": 5.0,
                "last_reward": None
            }
            save_json(pets_data, PETS_DATA_FILE)
            
            await inter.response.send_message(f"🎉 Parabéns! Você comprou um **{pet_escolhido}** por **{custo:,} {self.cog.moeda_emoji}**!", ephemeral=True)

        elif action == "vender":
            pet_data = load_json(PETS_DATA_FILE).get(str(self.author.id))
            if not pet_data:
                return await inter.response.send_message("❌ Você não tem um pet para vender.", ephemeral=True)
            
            valor_venda = 2500 + (pet_data.get('nivel', 1) * 100)
            view = disnake.ui.View()
            confirm_button = disnake.ui.Button(label="Confirmar Venda", style=disnake.ButtonStyle.green, custom_id="confirm_venda_pet")
            cancel_button = disnake.ui.Button(label="Cancelar", style=disnake.ButtonStyle.red, custom_id="cancel_venda_pet")
            view.add_item(confirm_button)
            view.add_item(cancel_button)
            
            await inter.response.send_message(f"Tem certeza que deseja vender seu pet por **{valor_venda:,} {self.cog.moeda_emoji}**?", view=view, ephemeral=True)
            
            try:
                btn_inter = await self.cog.bot.wait_for(
                    "button_click", 
                    check=lambda i: i.author.id == self.author.id and i.custom_id in ["confirm_venda_pet", "cancel_venda_pet"], 
                    timeout=60.0
                )
                if btn_inter.component.custom_id == "confirm_venda_pet":
                    pets_data = load_json(PETS_DATA_FILE)
                    if str(self.author.id) in pets_data:
                        del pets_data[str(self.author.id)]
                        save_json(pets_data, PETS_DATA_FILE)
                        all_users_data, user_data = get_or_create_user(self.author.id)
                        user_data['wallet'] += valor_venda
                        save_json(all_users_data, USERS_DATA_FILE)
                        await btn_inter.response.edit_message(content=f"✅ Pet vendido com sucesso por **{valor_venda:,} {self.cog.moeda_emoji}**!", view=None)
                else:
                    await btn_inter.response.edit_message(content="✅ Venda cancelada.", view=None)
            except asyncio.TimeoutError:
                await inter.edit_original_message(content="⏰ Tempo esgotado.", view=None)

        elif action == "recompensa":
            pets_data = load_json(PETS_DATA_FILE)
            pet_data = pets_data.get(str(self.author.id))
            if not pet_data:
                return
            
            last_reward_str = pet_data.get('last_reward')
            cooldown_duration = timedelta(days=1)
            if last_reward_str:
                last_reward = datetime.fromisoformat(last_reward_str)
                if datetime.now() < last_reward + cooldown_duration:
                    remaining = format_timedelta((last_reward + cooldown_duration) - datetime.now())
                    return await inter.response.send_message(f"❌ Você precisa esperar mais **{remaining}**.", ephemeral=True)
            
            recompensa = 1000 + (pet_data.get('nivel', 1) * 100)
            all_users_data, user_data = get_or_create_user(self.author.id)
            user_data['wallet'] += recompensa
            pet_data['last_reward'] = datetime.now().isoformat()
            save_json(all_users_data, USERS_DATA_FILE)
            save_json(pets_data, PETS_DATA_FILE)
            await inter.response.send_message(f"🎁 Seu pet trouxe **{recompensa:,} {self.cog.moeda_emoji}** para você!", ephemeral=True)

        elif action == "upar":
            pet_data = load_json(PETS_DATA_FILE).get(str(self.author.id))
            if pet_data:
                await inter.response.send_modal(PetUparModal(pet_data, self.cog.moeda_emoji))

class LojaView(disnake.ui.View):
    def __init__(self, author: disnake.User, cog_instance):
        super().__init__(timeout=300)
        self.author = author
        self.cog = cog_instance
        self.categoria_atual = None

    async def interaction_check(self, inter: disnake.MessageInteraction):
        if inter.author.id != self.author.id:
            await inter.response.send_message("❌ Esta não é uma interação para você!", ephemeral=True)
            return False
        return True

    @disnake.ui.string_select(
        placeholder="Escolha uma categoria...",
        custom_id="categoria_select",
        options=[
            disnake.SelectOption(label="Armas Brancas", value="armas_brancas", emoji="🔪"),
            disnake.SelectOption(label="Armas de Fogo", value="armas_fogo", emoji="🔫"),
            disnake.SelectOption(label="Coletes", value="coletes", emoji="🦺")
        ]
    )
    async def categoria_select(self, select: disnake.ui.StringSelect, inter: disnake.MessageInteraction):
        self.categoria_atual = inter.values[0]
        
        # Remove o select de categoria e adiciona os items
        self.clear_items()
        
        items = LOJA_ITEMS[self.categoria_atual]
        options = []
        
        for item_id, item_data in items.items():
            options.append(
                disnake.SelectOption(
                    label=item_data["nome"],
                    value=item_id,
                    description=f"💰 {item_data['preco']:,} {self.cog.moeda_emoji}",
                    emoji=item_data["emoji"]
                )
            )
        
        item_select = disnake.ui.StringSelect(
            placeholder=f"Escolha um item de {select.values[0].replace('_', ' ').title()}...",
            custom_id="item_select",
            options=options
        )
        
        self.add_item(item_select)
        
        # Botão para voltar
        voltar_btn = disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.secondary, custom_id="voltar")
        self.add_item(voltar_btn)
        
        embed = disnake.Embed(
            title=f"🛍️ Loja - {select.values[0].replace('_', ' ').title()}",
            description="Escolha um item para comprar:",
            color=disnake.Color.blue()
        )
        
        for item_id, item_data in items.items():
            embed.add_field(
                name=f"{item_data['emoji']} {item_data['nome']}",
                value=f"💰 **{item_data['preco']:,} {self.cog.moeda_emoji}**\n📊 Dano/Proteção: {item_data.get('dano', item_data.get('protecao', 0))}",
                inline=True
            )
        
        await inter.response.edit_message(embed=embed, view=self)

    @disnake.ui.string_select(custom_id="item_select")
    async def item_select(self, select: disnake.ui.StringSelect, inter: disnake.MessageInteraction):
        item_id = inter.values[0]
        item_data = LOJA_ITEMS[self.categoria_atual][item_id]
        
        _, user_data = get_or_create_user(self.author.id)
        all_inventory_data, user_inventory = get_or_create_inventory(self.author.id)
        
        # Verificar se precisa de licença
        if self.categoria_atual == "armas_fogo" and not user_inventory["licencas"]["arma"]:
            await inter.response.send_message("❌ Você precisa de uma licença de arma para comprar armas de fogo! Visite a prefeitura.", ephemeral=True)
            return
        
        if self.categoria_atual == "coletes" and not user_inventory["licencas"]["colete"]:
            await inter.response.send_message("❌ Você precisa de uma licença de colete para comprar coletes! Visite a prefeitura.", ephemeral=True)
            return
        
        # Verificar dinheiro
        if user_data['wallet'] < item_data['preco']:
            await inter.response.send_message(f"❌ Você não tem dinheiro suficiente! Precisa de **{item_data['preco']:,} {self.cog.moeda_emoji}**.", ephemeral=True)
            return
        
        # Comprar item
        user_data['wallet'] -= item_data['preco']
        
        if self.categoria_atual in ["armas_brancas", "armas_fogo"]:
            if item_id not in user_inventory["armas"]:
                user_inventory["armas"][item_id] = 0
            user_inventory["armas"][item_id] += 1
        else:  # coletes
            if item_id not in user_inventory["coletes"]:
                user_inventory["coletes"][item_id] = 0
            user_inventory["coletes"][item_id] += 1
        
        # Salvar dados
        all_users_data = load_json(USERS_DATA_FILE)
        all_users_data[str(self.author.id)] = user_data
        save_json(all_users_data, USERS_DATA_FILE)
        save_json(all_inventory_data, INVENTORY_DATA_FILE)
        
        await inter.response.send_message(f"🎉 Você comprou **{item_data['nome']} {item_data['emoji']}** por **{item_data['preco']:,} {self.cog.moeda_emoji}**!", ephemeral=True)

    @disnake.ui.button(label="Voltar", style=disnake.ButtonStyle.secondary, custom_id="voltar")
    async def voltar(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        # Resetar para a seleção de categoria
        self.clear_items()
        self.categoria_atual = None
        
        categoria_select = disnake.ui.StringSelect(
            placeholder="Escolha uma categoria...",
            custom_id="categoria_select",
            options=[
                disnake.SelectOption(label="Armas Brancas", value="armas_brancas", emoji="🔪"),
                disnake.SelectOption(label="Armas de Fogo", value="armas_fogo", emoji="🔫"),
                disnake.SelectOption(label="Coletes", value="coletes", emoji="🦺")
            ]
        )
        self.add_item(categoria_select)
        
        embed = disnake.Embed(
            title="🛍️ Loja de Equipamentos",
            description="Bem-vindo à loja! Aqui você pode comprar armas e coletes para usar no X1.\n\n**⚠️ ATENÇÃO:** Para comprar armas de fogo e coletes, você precisa das licenças correspondentes da prefeitura!",
            color=disnake.Color.blue()
        )
        embed.add_field(name="🔪 Armas Brancas", value="Não precisam de licença", inline=True)
        embed.add_field(name="🔫 Armas de Fogo", value="**Licença obrigatória**", inline=True)
        embed.add_field(name="🦺 Coletes", value="**Licença obrigatória**", inline=True)
        
        await inter.response.edit_message(embed=embed, view=self)

class PrefeituraView(disnake.ui.View):
    def __init__(self, author: disnake.User, cog_instance):
        super().__init__(timeout=300)
        self.author = author
        self.cog = cog_instance

    async def interaction_check(self, inter: disnake.MessageInteraction):
        if inter.author.id != self.author.id:
            await inter.response.send_message("❌ Esta não é uma interação para você!", ephemeral=True)
            return False
        return True

    @disnake.ui.string_select(
        placeholder="Escolha um serviço...",
        custom_id="servico_select",
        options=[
            disnake.SelectOption(label="Pagar Multas", value="pagar_multas", emoji="💸"),
            disnake.SelectOption(label="Licença de Arma", value="licenca_arma", emoji="🔫", description="10,000 moedas"),
            disnake.SelectOption(label="Licença de Colete", value="licenca_colete", emoji="🦺", description="8,000 moedas")
        ]
    )
    async def servico_select(self, select: disnake.ui.StringSelect, inter: disnake.MessageInteraction):
        servico = inter.values[0]
        
        if servico == "pagar_multas":
            _, user_multas = get_or_create_multas(self.author.id)
            
            if user_multas["total"] == 0:
                await inter.response.send_message("✅ Você não tem multas pendentes!", ephemeral=True)
                return
            
            _, user_data = get_or_create_user(self.author.id)
            
            if user_data['wallet'] < user_multas["total"]:
                await inter.response.send_message(f"❌ Você não tem dinheiro suficiente para pagar suas multas! Total: **{user_multas['total']:,} {self.cog.moeda_emoji}**", ephemeral=True)
                return
            
            # Pagar multas
            user_data['wallet'] -= user_multas["total"]
            total_pago = user_multas["total"]
            user_multas["total"] = 0
            user_multas["multas"] = []
            
            # Salvar dados
            all_users_data = load_json(USERS_DATA_FILE)
            all_users_data[str(self.author.id)] = user_data
            save_json(all_users_data, USERS_DATA_FILE)
            
            all_multas_data = load_json(MULTAS_DATA_FILE)
            all_multas_data[str(self.author.id)] = user_multas
            save_json(all_multas_data, MULTAS_DATA_FILE)
            
            await inter.response.send_message(f"✅ Multas pagas com sucesso! Total: **{total_pago:,} {self.cog.moeda_emoji}**", ephemeral=True)
        
        elif servico == "licenca_arma":
            _, user_data = get_or_create_user(self.author.id)
            all_inventory_data, user_inventory = get_or_create_inventory(self.author.id)
            
            if user_inventory["licencas"]["arma"]:
                await inter.response.send_message("❌ Você já possui uma licença de arma!", ephemeral=True)
                return
            
            custo = 10000
            if user_data['wallet'] < custo:
                await inter.response.send_message(f"❌ Você precisa de **{custo:,} {self.cog.moeda_emoji}** para comprar a licença de arma.", ephemeral=True)
                return
            
            # Comprar licença
            user_data['wallet'] -= custo
            user_inventory["licencas"]["arma"] = True
            
            # Salvar dados
            all_users_data = load_json(USERS_DATA_FILE)
            all_users_data[str(self.author.id)] = user_data
            save_json(all_users_data, USERS_DATA_FILE)
            save_json(all_inventory_data, INVENTORY_DATA_FILE)
            
            await inter.response.send_message(f"🎉 Licença de arma adquirida com sucesso por **{custo:,} {self.cog.moeda_emoji}**! Agora você pode comprar armas de fogo na loja.", ephemeral=True)
        
        elif servico == "licenca_colete":
            _, user_data = get_or_create_user(self.author.id)
            all_inventory_data, user_inventory = get_or_create_inventory(self.author.id)
            
            if user_inventory["licencas"]["colete"]:
                await inter.response.send_message("❌ Você já possui uma licença de colete!", ephemeral=True)
                return
            
            custo = 8000
            if user_data['wallet'] < custo:
                await inter.response.send_message(f"❌ Você precisa de **{custo:,} {self.cog.moeda_emoji}** para comprar a licença de colete.", ephemeral=True)
                return
            
            # Comprar licença
            user_data['wallet'] -= custo
            user_inventory["licencas"]["colete"] = True
            
            # Salvar dados
            all_users_data = load_json(USERS_DATA_FILE)
            all_users_data[str(self.author.id)] = user_data
            save_json(all_users_data, USERS_DATA_FILE)
            save_json(all_inventory_data, INVENTORY_DATA_FILE)
            
            await inter.response.send_message(f"🎉 Licença de colete adquirida com sucesso por **{custo:,} {self.cog.moeda_emoji}**! Agora você pode comprar coletes na loja.", ephemeral=True)

# Cog Principal
class EconomiaComandosCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._load_config()

    def _load_config(self):
        self.main_config = load_json(MAIN_CONFIG_FILE)
        self.theme_color = self.main_config.get("theme", "#7289DA")
        self.moeda_nome = self.main_config.get("moeda_nome", "Moedas")
        self.moeda_emoji = self.main_config.get("moeda_emoji", "🪙")

    def is_command_enabled(self, command_name: str, category: str = "economia"):
        """Verifica se um comando está habilitado"""
        economy_config = load_json(ECONOMY_CONFIG_FILE, is_econ_config=True)
        return economy_config.get("categorias", {}).get(category.lower(), {}).get(command_name.lower(), True)

    async def cog_check(self, ctx: commands.Context):
        """Check global para todos os comandos do cog"""
        if not ctx.guild:
            return False
        
        self._load_config()
        
        # Verificar se é o servidor correto
        server_id = self.main_config.get("server")
        if server_id and str(ctx.guild.id) != str(server_id):
            return False
        
        # Verificar se o comando está habilitado
        command_name = ctx.command.name
        if not self.is_command_enabled(command_name):
            await ctx.reply(f"❌ O comando `{command_name}` está desabilitado neste servidor.")
            return False
        
        return True

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CheckFailure):
            # Erro já tratado no cog_check
            return
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(f"❌ Opa! Você esqueceu um argumento necessário: `{error.param.name}`.")
        elif isinstance(error, commands.CommandNotFound):
            pass
        else:
            print(f"Erro no comando {ctx.command}: {error}")

    async def api_fallback_embed(self, ctx: commands.Context, title: str, description: str, color=None):
        """Embed de fallback quando a API não está disponível"""
        if color is None:
            color = disnake.Color(int(self.theme_color.replace("#", "0x"), 16))
        
        embed = disnake.Embed(title=title, description=description, color=color)
        embed.set_footer(text="Aparência customizada indisponível. A API de imagens pode estar offline.")
        await ctx.reply(embed=embed)

    # ============= COMANDOS DE ECONOMIA =============
    
    @commands.command(aliases=['bal', 'saldo'])
    async def banco(self, ctx: commands.Context):
        """Mostra o saldo do usuário"""
        _, user_data = get_or_create_user(ctx.author.id)
        
        payload = {
            "themeColor": self.theme_color,
            "currencyName": self.moeda_nome,
            "currencySymbol": self.moeda_emoji,
            "data": {
                "username": ctx.author.display_name,
                "balance": f"{user_data.get('wallet', 0):,}",
                "bankBalance": f"{user_data.get('bank', 0):,}",
            }
        }
        
        image_bytes = await gerar_imagem_api('banco', payload)
        if image_bytes:
            await ctx.reply(file=disnake.File(io.BytesIO(image_bytes), filename="banco.png"))
        else:
            await self.api_fallback_embed(
                ctx, 
                f"🏦 Banco de {ctx.author.display_name}", 
                f"**Carteira:** {user_data.get('wallet', 0):,} {self.moeda_emoji}\n**Banco:** {user_data.get('bank', 0):,} {self.moeda_emoji}"
            )

    @commands.command()
    async def trabalhar(self, ctx: commands.Context):
        """Trabalha para ganhar dinheiro"""
        all_data, user_data = get_or_create_user(ctx.author.id)
        
        # Verificar cooldown
        cooldown_end_str = user_data["cooldowns"].get("trabalhar")
        if cooldown_end_str:
            cooldown_end = datetime.fromisoformat(cooldown_end_str)
            if datetime.now() < cooldown_end:
                remaining = format_timedelta(cooldown_end - datetime.now())
                return await ctx.reply(f"⏰ Você precisa esperar **{remaining}** para trabalhar novamente.")
        
        # Trabalhar
        salario = random.randint(150, 400)
        user_data["wallet"] += salario
        user_data["cooldowns"]["trabalhar"] = (datetime.now() + timedelta(hours=1)).isoformat()
        save_json(all_data, USERS_DATA_FILE)

        payload = {
            "themeColor": self.theme_color,
            "currencyName": self.moeda_nome,
            "currencySymbol": self.moeda_emoji,
            "data": {
                "username": ctx.author.display_name,
                "avatar": str(ctx.author.display_avatar.url),
                "job": "Programador(a)",
                "earnings": f"{salario:,}",
                "newBalance": f"{user_data['wallet']:,}",
                "story": "Você passou uma hora codificando e como recompensa ganhou",
            }
        }
        
        image_bytes = await gerar_imagem_api('trabalhar', payload)
        if image_bytes:
            await ctx.reply(file=disnake.File(io.BytesIO(image_bytes), filename="trabalhar.png"))
        else:
            await self.api_fallback_embed(
                ctx, 
                "🔨 Trabalho Concluído", 
                f"Você trabalhou como programador e ganhou **{salario:,} {self.moeda_emoji}**!\n\n**Novo saldo:** {user_data['wallet']:,} {self.moeda_emoji}",
                disnake.Color.green()
            )

    @commands.command()
    async def daily(self, ctx: commands.Context):
        """Coleta a recompensa diária"""
        all_data, user_data = get_or_create_user(ctx.author.id)
        
        # Verificar cooldown
        cooldown_end_str = user_data["cooldowns"].get("daily")
        if cooldown_end_str:
            cooldown_end = datetime.fromisoformat(cooldown_end_str)
            if datetime.now() < cooldown_end:
                remaining = format_timedelta(cooldown_end - datetime.now())
                return await ctx.reply(f"⏰ Você já coletou seu daily hoje! Próximo em **{remaining}**.")
        
        # Dar recompensa
        recompensa = random.randint(500, 1200)
        bonus_consecutivo = user_data.get('daily_streak', 0) * 50
        recompensa_total = recompensa + bonus_consecutivo
        
        user_data["wallet"] += recompensa_total
        user_data["cooldowns"]["daily"] = (datetime.now() + timedelta(days=1)).isoformat()
        user_data['daily_streak'] = user_data.get('daily_streak', 0) + 1
        save_json(all_data, USERS_DATA_FILE)
        
        embed = disnake.Embed(
            title="💰 Recompensa Diária Coletada!",
            description=f"Você coletou **{recompensa_total:,} {self.moeda_emoji}**!",
            color=disnake.Color.gold()
        )
        embed.add_field(name="Recompensa Base", value=f"{recompensa:,} {self.moeda_emoji}", inline=True)
        if bonus_consecutivo > 0:
            embed.add_field(name="Bônus Consecutivo", value=f"+{bonus_consecutivo:,} {self.moeda_emoji}", inline=True)
        embed.add_field(name="Sequência", value=f"{user_data['daily_streak']} dias", inline=True)
        embed.add_field(name="Novo Saldo", value=f"{user_data['wallet']:,} {self.moeda_emoji}", inline=False)
        
        await ctx.reply(embed=embed)

    @commands.command()
    async def aposta(self, ctx: commands.Context):
        """Sistema de apostas"""
        all_data, user_data = get_or_create_user(ctx.author.id)
        
        # Verificar cooldown
        cooldown_end_str = user_data["cooldowns"].get("aposta")
        if cooldown_end_str:
            cooldown_end = datetime.fromisoformat(cooldown_end_str)
            if datetime.now() < cooldown_end:
                remaining = format_timedelta(cooldown_end - datetime.now())
                return await ctx.reply(f"⏰ Você precisa esperar **{remaining}** para apostar novamente.")
        
        # Verificar se tem dinheiro mínimo
        if user_data['wallet'] < 100:
            return await ctx.reply(f"❌ Você precisa de pelo menos **100 {self.moeda_emoji}** para apostar.")
        
        # Adicionar cooldown
        user_data["cooldowns"]["aposta"] = (datetime.now() + timedelta(minutes=10)).isoformat()
        save_json(all_data, USERS_DATA_FILE)
        
        # Mostrar modal para apostar
        await ctx.reply("🎰 Use o modal abaixo para fazer sua aposta!")
        
        # Criar e enviar modal
        modal = ApostaModal(self.moeda_emoji, self)
        # Nota: O modal será enviado através de uma interação, não diretamente aqui
        
        embed = disnake.Embed(
            title="🎰 Sistema de Apostas",
            description="Clique no botão abaixo para fazer sua aposta!",
            color=disnake.Color.purple()
        )
        embed.add_field(name="Chances", value="50% de ganhar", inline=True)
        embed.add_field(name="Multiplicador", value="1.8x o valor apostado", inline=True)
        embed.add_field(name="Seu Saldo", value=f"{user_data['wallet']:,} {self.moeda_emoji}", inline=True)
        
        view = disnake.ui.View()
        apostar_btn = disnake.ui.Button(label="Fazer Aposta", style=disnake.ButtonStyle.primary, emoji="🎰")
        
        async def apostar_callback(interaction):
            if interaction.author.id != ctx.author.id:
                await interaction.response.send_message("❌ Esta não é sua aposta!", ephemeral=True)
                return
            await interaction.response.send_modal(modal)
        
        apostar_btn.callback = apostar_callback
        view.add_item(apostar_btn)
        
        await ctx.reply(embed=embed, view=view)

    @commands.command()
    async def crime(self, ctx: commands.Context):
        """Comete um crime para tentar ganhar dinheiro"""
        all_data, user_data = get_or_create_user(ctx.author.id)
        
        # Verificar cooldown
        cooldown_end_str = user_data["cooldowns"].get("crime")
        if cooldown_end_str:
            cooldown_end = datetime.fromisoformat(cooldown_end_str)
            if datetime.now() < cooldown_end:
                remaining = format_timedelta(cooldown_end - datetime.now())
                return await ctx.reply(f"⏰ Você precisa esperar **{remaining}** para cometer outro crime.")

        user_data["cooldowns"]["crime"] = (datetime.now() + timedelta(minutes=30)).isoformat()
        
        crimes = [
            {"nome": "Roubar uma loja", "sucesso": 0.4},
            {"nome": "Hackear um banco", "sucesso": 0.3},
            {"nome": "Contrabando", "sucesso": 0.5},
            {"nome": "Falsificar documentos", "sucesso": 0.6}
        ]
        
        crime_escolhido = random.choice(crimes)
        
        if random.random() < crime_escolhido["sucesso"]:
            # Sucesso
            ganho = random.randint(800, 2500)
            user_data["wallet"] += ganho
            
            embed = disnake.Embed(
                title="✅ Crime Bem-Sucedido!",
                description=f"Você conseguiu executar: **{crime_escolhido['nome']}**",
                color=disnake.Color.green()
            )
            embed.add_field(name="Ganhos", value=f"{ganho:,} {self.moeda_emoji}", inline=True)
            embed.add_field(name="Novo Saldo", value=f"{user_data['wallet']:,} {self.moeda_emoji}", inline=True)
        else:
            # Falha
            multa = random.randint(300, 800)
            user_data["wallet"] = max(0, user_data["wallet"] - multa)
            
            # Adicionar multa oficial
            add_multa(ctx.author.id, f"Crime: {crime_escolhido['nome']}", multa)
            
            embed = disnake.Embed(
                title="❌ Crime Fracassou!",
                description=f"Você foi pego tentando: **{crime_escolhido['nome']}**",
                color=disnake.Color.red()
            )
            embed.add_field(name="Multa", value=f"{multa:,} {self.moeda_emoji}", inline=True)
            embed.add_field(name="Novo Saldo", value=f"{user_data['wallet']:,} {self.moeda_emoji}", inline=True)
            embed.set_footer(text="💡 Vá à prefeitura para pagar suas multas!")
        
        save_json(all_data, USERS_DATA_FILE)
        await ctx.reply(embed=embed)

    @commands.command()
    async def roubar(self, ctx: commands.Context, membro: disnake.Member):
        """Tenta roubar dinheiro de outro usuário"""
        if membro.id == ctx.author.id:
            return await ctx.reply("❌ Você não pode roubar a si mesmo.")
        
        if membro.bot:
            return await ctx.reply("❌ Você não pode roubar bots.")
        
        all_data, author_data = get_or_create_user(ctx.author.id)
        _, target_data = get_or_create_user(membro.id)
        
        # Verificar cooldown
        cooldown_end_str = author_data["cooldowns"].get("roubar")
        if cooldown_end_str:
            cooldown_end = datetime.fromisoformat(cooldown_end_str)
            if datetime.now() < cooldown_end:
                remaining = format_timedelta(cooldown_end - datetime.now())
                return await ctx.reply(f"⏰ Você precisa esperar **{remaining}** para roubar novamente.")

        author_data["cooldowns"]["roubar"] = (datetime.now() + timedelta(minutes=45)).isoformat()
        
        # Verificar se o alvo tem dinheiro suficiente
        if target_data['wallet'] < 200:
            save_json(all_data, USERS_DATA_FILE)
            return await ctx.reply(f"❌ {membro.display_name} é muito pobre para ser roubado.")
            
        # Chance de sucesso (35%)
        if random.random() < 0.35:
            # Sucesso
            valor_roubado = random.randint(100, min(int(target_data['wallet'] * 0.3), 1500))
            author_data['wallet'] += valor_roubado
            target_data['wallet'] -= valor_roubado
            
            embed = disnake.Embed(
                title="💰 Roubo Bem-Sucedido!",
                description=f"Você roubou **{valor_roubado:,} {self.moeda_emoji}** de {membro.mention}!",
                color=disnake.Color.green()
            )
            embed.add_field(name="Seu Novo Saldo", value=f"{author_data['wallet']:,} {self.moeda_emoji}")
        else:
            # Falha
            multa = random.randint(200, 600)
            author_data['wallet'] = max(0, author_data['wallet'] - multa)
            
            # Adicionar multa oficial
            add_multa(ctx.author.id, f"Tentativa de roubo contra {membro.display_name}", multa)
            
            embed = disnake.Embed(
                title="🚔 Roubo Fracassou!",
                description=f"Você foi pego tentando roubar {membro.mention}!",
                color=disnake.Color.red()
            )
            embed.add_field(name="Multa", value=f"{multa:,} {self.moeda_emoji}")
            embed.add_field(name="Seu Novo Saldo", value=f"{author_data['wallet']:,} {self.moeda_emoji}")
            embed.set_footer(text="💡 Vá à prefeitura para pagar suas multas!")
        
        save_json(all_data, USERS_DATA_FILE)
        await ctx.reply(embed=embed)

    @commands.command()
    async def rep(self, ctx: commands.Context, membro: disnake.Member):
        """Dá reputação para outro usuário"""
        if membro.id == ctx.author.id:
            return await ctx.reply("❌ Você não pode dar reputação a si mesmo.")
        
        if membro.bot:
            return await ctx.reply("❌ Bots não podem receber reputação.")

        all_users_data, user_data = get_or_create_user(ctx.author.id)
        
        # Verificar cooldown
        cooldown_end_str = user_data["cooldowns"].get("rep")
        if cooldown_end_str:
            cooldown_end = datetime.fromisoformat(cooldown_end_str)
            if datetime.now() < cooldown_end:
                remaining = format_timedelta(cooldown_end - datetime.now())
                return await ctx.reply(f"⏰ Você já deu reputação hoje! Próxima em **{remaining}**.")
        
        # Dar reputação
        user_data["cooldowns"]["rep"] = (datetime.now() + timedelta(days=1)).isoformat()
        save_json(all_users_data, USERS_DATA_FILE)

        rep_data = load_json(REP_DATA_FILE)
        membro_id_str = str(membro.id)
        rep_data[membro_id_str] = rep_data.get(membro_id_str, 0) + 1
        save_json(rep_data, REP_DATA_FILE)
        
        embed = disnake.Embed(
            title="✨ Reputação Concedida!",
            description=f"Você deu um ponto de reputação para {membro.mention}!",
            color=disnake.Color.gold()
        )
        embed.add_field(name="Reputação Total", value=f"{rep_data[membro_id_str]} ⭐")
        embed.set_thumbnail(url=membro.display_avatar.url)
        
        await ctx.reply(embed=embed)

    @commands.command()
    async def pagar(self, ctx: commands.Context, membro: disnake.Member, valor: int):
        """Paga dinheiro para outro usuário"""
        if valor <= 0:
            return await ctx.reply("❌ O valor deve ser positivo.")
        
        if membro.id == ctx.author.id:
            return await ctx.reply("❌ Você não pode pagar a si mesmo.")
        
        if membro.bot:
            return await ctx.reply("❌ Você não pode pagar para bots.")
        
        all_data, author_data = get_or_create_user(ctx.author.id)
        _, target_data = get_or_create_user(membro.id)
        
        if author_data['wallet'] < valor:
            return await ctx.reply(f"❌ Você não tem **{valor:,} {self.moeda_emoji}** na carteira.")
        
        # Transferir dinheiro
        author_data['wallet'] -= valor
        target_data['wallet'] += valor
        save_json(all_data, USERS_DATA_FILE)
        
        embed = disnake.Embed(
            title="💸 Pagamento Realizado!",
            description=f"Você pagou **{valor:,} {self.moeda_emoji}** para {membro.mention}!",
            color=disnake.Color.blue()
        )
        embed.add_field(name="Seu Novo Saldo", value=f"{author_data['wallet']:,} {self.moeda_emoji}")
        
        await ctx.reply(embed=embed)

    @commands.command(aliases=['perfil'])
    async def profile(self, ctx: commands.Context, membro: disnake.Member = None):
        """Mostra o perfil de um usuário"""
        target = membro or ctx.author
        _, user_data = get_or_create_user(target.id)
        
        # Dados de reputação
        rep_data = load_json(REP_DATA_FILE)
        reputacao = rep_data.get(str(target.id), 0)
        
        # Dados de multas
        _, user_multas = get_or_create_multas(target.id)
        
        # Dados de inventário
        _, user_inventory = get_or_create_inventory(target.id)
        
        embed = disnake.Embed(
            title=f"👤 Perfil de {target.display_name}",
            color=disnake.Color(int(self.theme_color.replace("#", "0x"), 16))
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        
        # Economia
        total_patrimonio = user_data.get('wallet', 0) + user_data.get('bank', 0)
        embed.add_field(
            name="💰 Economia",
            value=f"**Carteira:** {user_data.get('wallet', 0):,} {self.moeda_emoji}\n**Banco:** {user_data.get('bank', 0):,} {self.moeda_emoji}\n**Total:** {total_patrimonio:,} {self.moeda_emoji}",
            inline=True
        )
        
        # Status
        embed.add_field(
            name="📊 Status",
            value=f"**Reputação:** {reputacao} ⭐\n**Level:** {user_data.get('level', 1)}\n**XP:** {user_data.get('xp', 0)}",
            inline=True
        )
        
        # Outros
        married_status = "💍 Casado(a)" if user_data.get('married_to') else "💔 Solteiro(a)"
        multas_status = f"🚨 {user_multas['total']:,} {self.moeda_emoji}" if user_multas['total'] > 0 else "✅ Sem multas"
        
        embed.add_field(
            name="🔗 Outros",
            value=f"**Estado Civil:** {married_status}\n**Multas:** {multas_status}",
            inline=True
        )
        
        # Licenças
        licencas = []
        if user_inventory["licencas"]["arma"]:
            licencas.append("🔫 Porte de Arma")
        if user_inventory["licencas"]["colete"]:
            licencas.append("🦺 Uso de Colete")
        
        if licencas:
            embed.add_field(name="📋 Licenças", value="\n".join(licencas), inline=False)
        
        await ctx.reply(embed=embed)

    # ============= COMANDOS DE SISTEMAS =============
    
    @commands.command()
    async def pet(self, ctx: commands.Context):
        """Sistema de pets"""
        pet_data = load_json(PETS_DATA_FILE).get(str(ctx.author.id))
        
        if pet_data:
            # Usuário tem pet
            view = PetActionView(ctx.author, self)
            select_menu = view.children[0]
            select_menu.options = [
                disnake.SelectOption(label="Vender Pet", value="vender", emoji="💰", description="Venda seu pet por dinheiro"),
                disnake.SelectOption(label="Resgatar Recompensa", value="recompensa", emoji="🎁", description="Recompensa diária do pet"),
                disnake.SelectOption(label="Upar Pet", value="upar", emoji="⭐", description="Aumente o nível do seu pet")
            ]
            
            payload = {
                "themeColor": self.theme_color,
                "currencyName": self.moeda_nome,
                "currencySymbol": self.moeda_emoji,
                "pet": pet_data,
                "user": {
                    "id": ctx.author.id,
                    "username": ctx.author.display_name
                }
            }
            
            image_bytes = await gerar_imagem_api('petinfo', payload)
            if image_bytes:
                await ctx.reply(file=disnake.File(io.BytesIO(image_bytes), filename="pet.png"), view=view)
            else:
                embed = disnake.Embed(
                    title=f"🐾 {pet_data['nome']} - Pet de {ctx.author.display_name}",
                    color=disnake.Color.green()
                )
                embed.add_field(name="📊 Status", value=f"**Nível:** {pet_data['nivel']}\n**XP:** {pet_data['xp']}")
                embed.add_field(name="⚔️ Combate", value=f"**Dano:** {pet_data['damage']}\n**Escudo:** {pet_data['shield']}\n**Vida:** {pet_data['health']}")
                embed.add_field(name="🎯 Crítico", value=f"{pet_data['critical']}%")
                await ctx.reply(embed=embed, view=view)
        else:
            # Usuário não tem pet
            _, user_data = get_or_create_user(ctx.author.id)
            
            embed = disnake.Embed(
                title="🐾 Sistema de Pets",
                description='Você ainda não possui um pet! Que tal adotar um companheiro?',
                color=disnake.Color.orange()
            )
            embed.add_field(
                name='💡 Como começar',
                value='Use o menu abaixo para comprar seu primeiro pet por **5,000** moedas!',
                inline=False
            )
            embed.add_field(
                name=f'{self.moeda_emoji} Seu Saldo',
                value=f"{user_data.get('wallet', 0):,} {self.moeda_nome}",
                inline=False
            )
            
            view = PetActionView(ctx.author, self)
            select_menu = view.children[0]
            select_menu.options = [
                disnake.SelectOption(
                    label="Comprar Pet",
                    value="comprar",
                    emoji="🛍️",
                    description="Custa 5,000 moedas"
                )
            ]
            
            await ctx.reply(embed=embed, view=view)

    @commands.command()
    async def loja(self, ctx: commands.Context):
        """Loja de equipamentos"""
        _, user_data = get_or_create_user(ctx.author.id)
        
        embed = disnake.Embed(
            title="🛍️ Loja de Equipamentos",
            description="Bem-vindo à loja! Aqui você pode comprar armas e coletes para usar no X1.\n\n**⚠️ ATENÇÃO:** Para comprar armas de fogo e coletes, você precisa das licenças correspondentes da prefeitura!",
            color=disnake.Color.blue()
        )
        embed.add_field(name="🔪 Armas Brancas", value="Não precisam de licença", inline=True)
        embed.add_field(name="🔫 Armas de Fogo", value="**Licença obrigatória**", inline=True)
        embed.add_field(name="🦺 Coletes", value="**Licença obrigatória**", inline=True)
        embed.add_field(name=f"{self.moeda_emoji} Seu Saldo", value=f"{user_data['wallet']:,} {self.moeda_nome}", inline=False)
        
        view = LojaView(ctx.author, self)
        await ctx.reply(embed=embed, view=view)

    @commands.command()
    async def prefeitura(self, ctx: commands.Context):
        """Prefeitura - Pagar multas e comprar licenças"""
        _, user_data = get_or_create_user(ctx.author.id)
        _, user_multas = get_or_create_multas(ctx.author.id)
        _, user_inventory = get_or_create_inventory(ctx.author.id)
        
        embed = disnake.Embed(
            title="🏛️ Prefeitura Municipal",
            description="Bem-vindo à prefeitura! Aqui você pode resolver questões legais e adquirir licenças.",
            color=disnake.Color.blue()
        )
        
        # Status de multas
        if user_multas["total"] > 0:
            embed.add_field(
                name="🚨 Multas Pendentes",
                value=f"**Total:** {user_multas['total']:,} {self.moeda_emoji}\n**Quantidade:** {len(user_multas['multas'])} multa(s)",
                inline=True
            )
        else:
            embed.add_field(name="✅ Situação Legal", value="Sem multas pendentes", inline=True)
        
        # Status de licenças
        licencas_status = []
        if user_inventory["licencas"]["arma"]:
            licencas_status.append("🔫 Porte de Arma ✅")
        else:
            licencas_status.append("🔫 Porte de Arma ❌")
        
        if user_inventory["licencas"]["colete"]:
            licencas_status.append("🦺 Uso de Colete ✅")
        else:
            licencas_status.append("🦺 Uso de Colete ❌")
        
        embed.add_field(name="📋 Licenças", value="\n".join(licencas_status), inline=True)
        embed.add_field(name=f"{self.moeda_emoji} Seu Saldo", value=f"{user_data['wallet']:,} {self.moeda_nome}", inline=True)
        
        view = PrefeituraView(ctx.author, self)
        await ctx.reply(embed=embed, view=view)

    @commands.command()
    async def inventario(self, ctx: commands.Context):
        """Mostra o inventário do usuário"""
        _, user_inventory = get_or_create_inventory(ctx.author.id)
        
        embed = disnake.Embed(
            title=f"🎒 Inventário de {ctx.author.display_name}",
            color=disnake.Color.purple()
        )
        
        # Armas
        armas_texto = []
        for arma_id, quantidade in user_inventory["armas"].items():
            if quantidade > 0:
                arma_data = None
                for categoria in ["armas_brancas", "armas_fogo"]:
                    if arma_id in LOJA_ITEMS[categoria]:
                        arma_data = LOJA_ITEMS[categoria][arma_id]
                        break
                
                if arma_data:
                    armas_texto.append(f"{arma_data['emoji']} **{arma_data['nome']}** x{quantidade}")
        
        if armas_texto:
            embed.add_field(name="⚔️ Armas", value="\n".join(armas_texto), inline=False)
        else:
            embed.add_field(name="⚔️ Armas", value="Nenhuma arma", inline=False)
        
        # Coletes
        coletes_texto = []
        for colete_id, quantidade in user_inventory["coletes"].items():
            if quantidade > 0:
                if colete_id in LOJA_ITEMS["coletes"]:
                    colete_data = LOJA_ITEMS["coletes"][colete_id]
                    coletes_texto.append(f"{colete_data['emoji']} **{colete_data['nome']}** x{quantidade}")
        
        if coletes_texto:
            embed.add_field(name="🦺 Coletes", value="\n".join(coletes_texto), inline=False)
        else:
            embed.add_field(name="🦺 Coletes", value="Nenhum colete", inline=False)
        
        # Licenças
        licencas = []
        if user_inventory["licencas"]["arma"]:
            licencas.append("🔫 Porte de Arma")
        if user_inventory["licencas"]["colete"]:
            licencas.append("🦺 Uso de Colete")
        
        if licencas:
            embed.add_field(name="📋 Licenças", value="\n".join(licencas), inline=False)
        else:
            embed.add_field(name="📋 Licenças", value="Nenhuma licença", inline=False)
        
        await ctx.reply(embed=embed)

    @commands.command()
    async def minerar(self, ctx: commands.Context):
        """Sistema de mineração"""
        all_data, user_data = get_or_create_user(ctx.author.id)
        
        # Verificar cooldown
        cooldown_end_str = user_data["cooldowns"].get("minerar")
        if cooldown_end_str:
            cooldown_end = datetime.fromisoformat(cooldown_end_str)
            if datetime.now() < cooldown_end:
                remaining = format_timedelta(cooldown_end - datetime.now())
                return await ctx.reply(f"⏰ Você precisa esperar **{remaining}** para minerar novamente.")
        
        # Minerar
        user_data["cooldowns"]["minerar"] = (datetime.now() + timedelta(hours=2)).isoformat()
        
        # Chances de encontrar diferentes recursos
        recursos = [
            {"nome": "Carvão", "valor": 50, "chance": 0.4, "emoji": "⚫"},
            {"nome": "Ferro", "valor": 120, "chance": 0.3, "emoji": "🔩"},
            {"nome": "Ouro", "valor": 300, "chance": 0.2, "emoji": "🟨"},
            {"nome": "Diamante", "valor": 800, "chance": 0.08, "emoji": "💎"},
            {"nome": "Esmeralda", "valor": 1200, "chance": 0.02, "emoji": "💚"}
        ]
        
        recurso_encontrado = None
        rand = random.random()
        chance_acumulada = 0
        
        for recurso in recursos:
            chance_acumulada += recurso["chance"]
            if rand <= chance_acumulada:
                recurso_encontrado = recurso
                break
        
        if not recurso_encontrado:
            recurso_encontrado = recursos[0]  # Fallback para carvão
        
        quantidade = random.randint(1, 3)
        valor_total = recurso_encontrado["valor"] * quantidade
        
        user_data["wallet"] += valor_total
        save_json(all_data, USERS_DATA_FILE)
        
        embed = disnake.Embed(
            title="⛏️ Mineração Concluída!",
            description=f"Você passou 2 horas minerando e encontrou:",
            color=disnake.Color.gold()
        )
        embed.add_field(
            name="💎 Recurso Encontrado",
            value=f"{recurso_encontrado['emoji']} **{quantidade}x {recurso_encontrado['nome']}**",
            inline=True
        )
        embed.add_field(
            name="💰 Valor Ganho",
            value=f"{valor_total:,} {self.moeda_emoji}",
            inline=True
        )
        embed.add_field(
            name="💳 Novo Saldo",
            value=f"{user_data['wallet']:,} {self.moeda_emoji}",
            inline=True
        )
        
        await ctx.reply(embed=embed)

    @commands.command()
    async def pescar(self, ctx: commands.Context):
        """Sistema de pesca"""
        all_data, user_data = get_or_create_user(ctx.author.id)
        
        # Verificar cooldown
        cooldown_end_str = user_data["cooldowns"].get("pescar")
        if cooldown_end_str:
            cooldown_end = datetime.fromisoformat(cooldown_end_str)
            if datetime.now() < cooldown_end:
                remaining = format_timedelta(cooldown_end - datetime.now())
                return await ctx.reply(f"⏰ Você precisa esperar **{remaining}** para pescar novamente.")
        
        # Pescar
        user_data["cooldowns"]["pescar"] = (datetime.now() + timedelta(minutes=45)).isoformat()
        
        # Chances de pescar diferentes peixes
        peixes = [
            {"nome": "Sardinha", "valor": 80, "chance": 0.35, "emoji": "🐟"},
            {"nome": "Salmão", "valor": 150, "chance": 0.25, "emoji": "🐠"},
            {"nome": "Atum", "valor": 250, "chance": 0.2, "emoji": "🐟"},
            {"nome": "Peixe Dourado", "valor": 500, "chance": 0.1, "emoji": "🟨"},
            {"nome": "Tubarão", "valor": 1000, "chance": 0.08, "emoji": "🦈"},
            {"nome": "Lula Gigante", "valor": 1500, "chance": 0.02, "emoji": "🦑"}
        ]
        
        peixe_pescado = None
        rand = random.random()
        chance_acumulada = 0
        
        for peixe in peixes:
            chance_acumulada += peixe["chance"]
            if rand <= chance_acumulada:
                peixe_pescado = peixe
                break
        
        if not peixe_pescado:
            peixe_pescado = peixes[0]  # Fallback para sardinha
        
        quantidade = random.randint(1, 2)
        valor_total = peixe_pescado["valor"] * quantidade
        
        user_data["wallet"] += valor_total
        save_json(all_data, USERS_DATA_FILE)
        
        embed = disnake.Embed(
            title="🎣 Pesca Concluída!",
            description=f"Você passou um tempo pescando e conseguiu:",
            color=disnake.Color.blue()
        )
        embed.add_field(
            name="🐟 Peixe Pescado",
            value=f"{peixe_pescado['emoji']} **{quantidade}x {peixe_pescado['nome']}**",
            inline=True
        )
        embed.add_field(
            name="💰 Valor Ganho",
            value=f"{valor_total:,} {self.moeda_emoji}",
            inline=True
        )
        embed.add_field(
            name="💳 Novo Saldo",
            value=f"{user_data['wallet']:,} {self.moeda_emoji}",
            inline=True
        )
        
        await ctx.reply(embed=embed)

    @commands.command()
    async def slots(self, ctx: commands.Context, valor: int = None):
        """Jogo de caça-níqueis"""
        if valor is None:
            embed = disnake.Embed(
                title="🎰 Caça-Níqueis",
                description="Use: `slots <valor>` para jogar!\n\nExemplo: `slots 500`",
                color=disnake.Color.purple()
            )
            embed.add_field(name="💰 Apostas Mínimas", value="100 moedas", inline=True)
            embed.add_field(name="🎯 Prêmios", value="🍒🍒🍒 = 2x\n🍋🍋🍋 = 3x\n🍊🍊🍊 = 4x\n🍇🍇🍇 = 5x\n💎💎💎 = 10x", inline=True)
            return await ctx.reply(embed=embed)
        
        if valor < 100:
            return await ctx.reply("❌ A aposta mínima é de 100 moedas.")
        
        all_data, user_data = get_or_create_user(ctx.author.id)
        
        if user_data['wallet'] < valor:
            return await ctx.reply(f"❌ Você não tem **{valor:,} {self.moeda_emoji}** na carteira.")
        
        # Símbolos do slot
        simbolos = ["🍒", "🍋", "🍊", "🍇", "💎", "❌"]
        pesos = [30, 25, 20, 15, 5, 5]  # Pesos para cada símbolo
        
        # Gerar resultado
        resultado = random.choices(simbolos, weights=pesos, k=3)
        
        # Verificar prêmio
        premio = 0
        if resultado[0] == resultado[1] == resultado[2]:
            if resultado[0] == "🍒":
                premio = valor * 2
            elif resultado[0] == "🍋":
                premio = valor * 3
            elif resultado[0] == "🍊":
                premio = valor * 4
            elif resultado[0] == "🍇":
                premio = valor * 5
            elif resultado[0] == "💎":
                premio = valor * 10
        
        # Atualizar saldo
        if premio > 0:
            user_data['wallet'] += premio - valor  # Remove aposta e adiciona prêmio
            cor = disnake.Color.gold()
            titulo = "🎉 JACKPOT!"
            descricao = f"Você ganhou **{premio:,} {self.moeda_emoji}**!"
        else:
            user_data['wallet'] -= valor
            cor = disnake.Color.red()
            titulo = "😔 Que pena!"
            descricao = f"Você perdeu **{valor:,} {self.moeda_emoji}**."
        
        save_json(all_data, USERS_DATA_FILE)
        
        embed = disnake.Embed(title=titulo, description=descricao, color=cor)
        embed.add_field(name="🎰 Resultado", value=f"┃ {' ┃ '.join(resultado)} ┃", inline=False)
        embed.add_field(name="💳 Novo Saldo", value=f"{user_data['wallet']:,} {self.moeda_emoji}", inline=True)
        
        await ctx.reply(embed=embed)

    # ============= COMANDOS DE ROLEPLAY =============
    
    @commands.command(aliases=['hug'])
    async def abraçar(self, ctx: commands.Context, membro: disnake.Member):
        """Abraça outro usuário"""
        if membro.id == ctx.author.id:
            return await ctx.reply("❌ Você não pode abraçar a si mesmo... isso seria estranho! 🤔")
        
        if membro.bot:
            return await ctx.reply("🤖 Os bots não podem sentir abraços, mas eles agradecem o carinho!")
        
        embed = disnake.Embed(
            title="🤗 Abraço Carinhoso!",
            description=f"{ctx.author.mention} deu um abraço apertado em {membro.mention}!",
            color=disnake.Color.pink()
        )
        embed.set_footer(text="💝 Espalhe amor e carinho!")
        
        await ctx.reply(embed=embed)

    @commands.command()
    async def beijar(self, ctx: commands.Context, membro: disnake.Member):
        """Beija outro usuário"""
        if membro.id == ctx.author.id:
            return await ctx.reply("❌ Você não pode beijar a si mesmo!")
        
        if membro.bot:
            return await ctx.reply("🤖 Os bots ficam envergonhados com beijos!")
        
        embed = disnake.Embed(
            title="💋 Beijo Romântico!",
            description=f"{ctx.author.mention} deu um beijo em {membro.mention}!",
            color=disnake.Color.red()
        )
        embed.set_footer(text="❤️ Que momento fofo!")
        
        await ctx.reply(embed=embed)

    @commands.command()
    async def casar(self, ctx: commands.Context, membro: disnake.Member):
        """Casa com outro usuário"""
        if membro.id == ctx.author.id:
            return await ctx.reply("❌ Você não pode casar consigo mesmo!")
        
        if membro.bot:
            return await ctx.reply("❌ Bots não podem casar!")
        
        all_users_data, author_data = get_or_create_user(ctx.author.id)
        _, target_data = get_or_create_user(membro.id)
        
        # Verificar se já estão casados
        if author_data.get('married_to'):
            return await ctx.reply("❌ Você já está casado(a)!")
        
        if target_data.get('married_to'):
            return await ctx.reply(f"❌ {membro.display_name} já está casado(a)!")
        
        # Proposta de casamento
        embed = disnake.Embed(
            title="💍 Pedido de Casamento!",
            description=f"{ctx.author.mention} está pedindo {membro.mention} em casamento!\n\n{membro.mention}, você aceita?",
            color=disnake.Color.gold()
        )
        
        view = disnake.ui.View(timeout=60)
        aceitar_btn = disnake.ui.Button(label="Aceitar 💍", style=disnake.ButtonStyle.green)
        recusar_btn = disnake.ui.Button(label="Recusar 💔", style=disnake.ButtonStyle.red)
        
        async def aceitar_callback(interaction):
            if interaction.author.id != membro.id:
                await interaction.response.send_message("❌ Apenas quem foi pedido em casamento pode responder!", ephemeral=True)
                return
            
            # Casar
            author_data['married_to'] = membro.id
            author_data['marriage_date'] = datetime.now().isoformat()
            target_data['married_to'] = ctx.author.id
            target_data['marriage_date'] = datetime.now().isoformat()
            
            save_json(all_users_data, USERS_DATA_FILE)
            
            embed_sucesso = disnake.Embed(
                title="🎉 Casamento Realizado!",
                description=f"🎊 {ctx.author.mention} e {membro.mention} agora estão casados!\n\n💐 Que sejam muito felizes juntos!",
                color=disnake.Color.gold()
            )
            embed_sucesso.set_footer(text=f"Data do casamento: {datetime.now().strftime('%d/%m/%Y')}")
            
            await interaction.response.edit_message(embed=embed_sucesso, view=None)
        
        async def recusar_callback(interaction):
            if interaction.author.id != membro.id:
                await interaction.response.send_message("❌ Apenas quem foi pedido em casamento pode responder!", ephemeral=True)
                return
            
            embed_recusa = disnake.Embed(
                title="💔 Pedido Recusado",
                description=f"{membro.mention} recusou o pedido de casamento de {ctx.author.mention}.",
                color=disnake.Color.red()
            )
            embed_recusa.set_footer(text="Talvez numa próxima vez...")
            
            await interaction.response.edit_message(embed=embed_recusa, view=None)
        
        aceitar_btn.callback = aceitar_callback
        recusar_btn.callback = recusar_callback
        view.add_item(aceitar_btn)
        view.add_item(recusar_btn)
        
        await ctx.reply(embed=embed, view=view)

    @commands.command(aliases=['divorcio'])
    async def divórcio(self, ctx: commands.Context):
        """Se divorcia do cônjuge atual"""
        all_users_data, author_data = get_or_create_user(ctx.author.id)
        
        if not author_data.get('married_to'):
            return await ctx.reply("❌ Você não está casado(a)!")
        
        # Encontrar cônjuge
        spouse_id = author_data['married_to']
        _, spouse_data = get_or_create_user(spouse_id)
        
        try:
            spouse = ctx.guild.get_member(spouse_id)
            spouse_name = spouse.display_name if spouse else "Usuário desconhecido"
        except:
            spouse_name = "Usuário desconhecido"
        
        # Confirmação de divórcio
        embed = disnake.Embed(
            title="💔 Pedido de Divórcio",
            description=f"Tem certeza que deseja se divorciar de **{spouse_name}**?\n\nEsta ação é irreversível!",
            color=disnake.Color.red()
        )
        
        view = disnake.ui.View(timeout=30)
        confirmar_btn = disnake.ui.Button(label="Confirmar Divórcio", style=disnake.ButtonStyle.red)
        cancelar_btn = disnake.ui.Button(label="Cancelar", style=disnake.ButtonStyle.grey)
        
        async def confirmar_callback(interaction):
            if interaction.author.id != ctx.author.id:
                await interaction.response.send_message("❌ Apenas quem pediu o divórcio pode confirmar!", ephemeral=True)
                return
            
            # Divorciar
            author_data['married_to'] = None
            author_data['marriage_date'] = None
            spouse_data['married_to'] = None
            spouse_data['marriage_date'] = None
            
            save_json(all_users_data, USERS_DATA_FILE)
            
            embed_sucesso = disnake.Embed(
                title="📋 Divórcio Concluído",
                description=f"💔 {ctx.author.mention} e **{spouse_name}** agora estão divorciados.",
                color=disnake.Color.orange()
            )
            embed_sucesso.set_footer(text="Esperamos que ambos encontrem a felicidade novamente.")
            
            await interaction.response.edit_message(embed=embed_sucesso, view=None)
        
        async def cancelar_callback(interaction):
            if interaction.author.id != ctx.author.id:
                await interaction.response.send_message("❌ Apenas quem pediu o divórcio pode cancelar!", ephemeral=True)
                return
            
            embed_cancelado = disnake.Embed(
                title="✅ Divórcio Cancelado",
                description="O pedido de divórcio foi cancelado. O casamento continua!",
                color=disnake.Color.green()
            )
            
            await interaction.response.edit_message(embed=embed_cancelado, view=None)
        
        confirmar_btn.callback = confirmar_callback
        cancelar_btn.callback = cancelar_callback
        view.add_item(confirmar_btn)
        view.add_item(cancelar_btn)
        
        await ctx.reply(embed=embed, view=view)

    @commands.command()
    async def ship(self, ctx: commands.Context, membro1: disnake.Member, membro2: disnake.Member = None):
        """Calcula a compatibilidade entre duas pessoas"""
        if membro2 is None:
            membro2 = ctx.author
        
        if membro1.id == membro2.id:
            return await ctx.reply("❌ Não faz sentido calcular compatibilidade consigo mesmo!")
        
        # Calcular compatibilidade (baseado nos IDs para ser consistente)
        compatibilidade = abs(hash(f"{membro1.id}{membro2.id}")) % 101
        
        # Determinar emoji e descrição baseado na compatibilidade
        if compatibilidade >= 90:
            emoji = "💖"
            descricao = "Alma gêmeas! Perfeita sintonia!"
        elif compatibilidade >= 80:
            emoji = "💕"
            descricao = "Muito compatíveis! Relacionamento promissor!"
        elif compatibilidade >= 70:
            emoji = "💘"
            descricao = "Boa compatibilidade! Pode dar certo!"
        elif compatibilidade >= 50:
            emoji = "💛"
            descricao = "Compatibilidade média. Precisa de esforço!"
        elif compatibilidade >= 30:
            emoji = "🧡"
            descricao = "Baixa compatibilidade. Muitos desafios."
        else:
            emoji = "💔"
            descricao = "Praticamente incompatíveis."
        
        # Criar nome do ship
        nome1 = membro1.display_name[:3]
        nome2 = membro2.display_name[-3:]
        ship_name = nome1 + nome2
        
        embed = disnake.Embed(
            title=f"💕 Ship: {ship_name}",
            description=f"Compatibilidade entre {membro1.mention} e {membro2.mention}",
            color=disnake.Color.pink()
        )
        
        # Barra de progresso visual
        barra_completa = 20
        barra_preenchida = int((compatibilidade / 100) * barra_completa)
        barra = "█" * barra_preenchida + "░" * (barra_completa - barra_preenchida)
        
        embed.add_field(
            name=f"{emoji} {compatibilidade}%",
            value=f"`{barra}`\n{descricao}",
            inline=False
        )
        
        await ctx.reply(embed=embed)

    @commands.command()
    async def afk(self, ctx: commands.Context, *, motivo: str = "Sem motivo especificado"):
        """Define status AFK"""
        # Por simplicidade, vamos apenas enviar uma mensagem
        embed = disnake.Embed(
            title="😴 Status AFK Ativado",
            description=f"{ctx.author.mention} agora está AFK!",
            color=disnake.Color.blue()
        )
        embed.add_field(name="Motivo", value=motivo)
        embed.set_footer(text="💡 Para desativar, envie qualquer mensagem!")
        
        await ctx.reply(embed=embed)

def setup(bot):
    bot.add_cog(EconomiaComandosCog(bot))