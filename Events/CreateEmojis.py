import disnake
from disnake.ext import commands
import json
import os
import base64
import aiohttp
import sys
import asyncio
from typing import Dict, Optional, Tuple

from Functions.VerificarPerms import *

with open("config.json") as f:
    config = json.load(f)
    BOT_TOKEN = config["token"]

EMOJIS_DB = "Database/emojis.json"
EMOJI_FOLDER = "Emojis/"

# Rate limiting configuration
RATE_LIMIT_DELAY = 0.3  # Delay entre uploads (300ms)
BATCH_SIZE = 10  # Processar em lotes de 10 emojis
MAX_CONCURRENT_UPLOADS = 3  # Máximo de uploads simultâneos

async def ObterIDBOT(token):
    url = "https://discord.com/api/v9/users/@me"
    headers = {"Authorization": f"Bot {token}"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data["id"]
            else:
                return None

async def upload_emoji(session, app_id, name, image_path):
    with open(image_path, "rb") as image_file:
        image_data = image_file.read()

    if image_path.endswith(".gif"):
        base64_image = f"data:image/gif;base64,{base64.b64encode(image_data).decode()}"
    else:
        base64_image = f"data:image/png;base64,{base64.b64encode(image_data).decode()}"

    url = f"https://discord.com/api/v9/applications/{app_id}/emojis"
    headers = {"Authorization": f"Bot {BOT_TOKEN}", "Content-Type": "application/json"}
    payload = {"name": name, "image": base64_image}

    async with session.post(url, headers=headers, json=payload) as response:
        if response.status == 201:
            data = await response.json()
            return data["id"]
        elif response.status == 400:
            error_data = await response.json()
            # Verificar se o erro é devido ao emoji já existir
            if "already exists" in str(error_data).lower():
                print(f"    - Emoji '{name}' já existe no bot")
                return "already_exists"
            else:
                print(f"    - Erro ao criar emoji '{name}': {error_data}")
                return None
        else:
            print(f"    - Erro ao criar emoji '{name}': Status {response.status}")
            return None

async def get_existing_emojis(app_id) -> Dict[str, dict]:
    """Busca todos os emojis existentes no bot com tratamento de erro melhorado"""
    url = f"https://discord.com/api/v9/applications/{app_id}/emojis"
    headers = {"Authorization": f"Bot {BOT_TOKEN}"}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                print(f"DEBUG: Resposta da API - Tipo: {type(data)}")
                
                # Verificar se é uma lista
                if isinstance(data, list):
                    return {emoji['name']: emoji for emoji in data if isinstance(emoji, dict)}
                # Se for um dicionário com 'items' (formato alternativo da API)
                elif isinstance(data, dict) and 'items' in data:
                    items = data['items']
                    if isinstance(items, list):
                        return {emoji['name']: emoji for emoji in items if isinstance(emoji, dict)}
                # Se for um dicionário com os emojis diretamente
                elif isinstance(data, dict):
                    # Tentar diferentes formatos de resposta
                    if 'data' in data and isinstance(data['data'], list):
                        return {emoji['name']: emoji for emoji in data['data'] if isinstance(emoji, dict)}
                    elif 'emojis' in data and isinstance(data['emojis'], list):
                        return {emoji['name']: emoji for emoji in data['emojis'] if isinstance(emoji, dict)}
                    else:
                        print(f"DEBUG: Estrutura do dict: {list(data.keys())}")
                        return {}
                else:
                    print(f"AVISO: Resposta da API não é uma lista nem dict válido - Tipo: {type(data)}")
                    return {}
            else:
                print(f"Erro ao buscar emojis existentes: {response.status}")
                response_text = await response.text()
                print(f"DEBUG: Resposta de erro: {response_text}")
                return {}

async def sync_existing_emojis(emojis_data: dict, existing_emojis: dict) -> Tuple[dict, int]:
    """Sincroniza emojis existentes no bot com o JSON"""
    sync_count = 0
    
    for name, emoji_info in existing_emojis.items():
        # Verificar se o emoji está no JSON mas sem tag válida
        if name in emojis_data:
            current_tag = emojis_data[name]
            if not current_tag or not str(current_tag).startswith('<'):
                # Reconstruir a tag do emoji
                if emoji_info.get('animated'):
                    emoji_tag = f"<a:{name}:{emoji_info['id']}>"
                else:
                    emoji_tag = f"<:{name}:{emoji_info['id']}>"
                
                emojis_data[name] = emoji_tag
                sync_count += 1
                print(f"    - Sincronizado: {name}")
        else:
            # Emoji existe no bot mas não no JSON - adicionar
            if emoji_info.get('animated'):
                emoji_tag = f"<a:{name}:{emoji_info['id']}>"
            else:
                emoji_tag = f"<:{name}:{emoji_info['id']}>"
            
            emojis_data[name] = emoji_tag
            sync_count += 1
            print(f"    - Adicionado ao JSON: {name}")
    
    return emojis_data, sync_count

async def process_emoji_batch(session, app_id, emoji_batch, emojis_data, semaphore, existing_emojis):
    """Processa um lote de emojis com controle de concorrência"""
    results = []
    
    for name in emoji_batch:
        async with semaphore:  # Controla o número de uploads simultâneos
            # Verificar se o emoji já existe no bot ANTES de tentar criar
            if name in existing_emojis:
                # Emoji já existe, adicionar ao JSON
                emoji_info = existing_emojis[name]
                if emoji_info.get('animated'):
                    emoji_tag = f"<a:{name}:{emoji_info['id']}>"
                else:
                    emoji_tag = f"<:{name}:{emoji_info['id']}>"
                
                emojis_data[name] = emoji_tag
                results.append((name, "already_exists"))
                print(f"    - Já existe (adicionado ao JSON): {name}")
                
                # Salvar imediatamente no JSON
                try:
                    with open(EMOJIS_DB, "w", encoding="utf-8") as f:
                        json.dump(emojis_data, f, indent=4, ensure_ascii=False)
                except Exception as e:
                    print(f"    - Erro ao salvar {name}: {e}")
                continue
            
            # Procurar arquivo do emoji
            image_path = os.path.join(EMOJI_FOLDER, f"{name}.gif")
            if not os.path.isfile(image_path):
                image_path = os.path.join(EMOJI_FOLDER, f"{name}.png")
            if not os.path.isfile(image_path):
                print(f"    - Arquivo não encontrado: {name}")
                results.append((name, "file_not_found"))
                continue
            
            try:
                emoji_id = await upload_emoji(session, app_id, name, image_path)
                
                if emoji_id == "already_exists":
                    # Se retornou "already_exists", buscar o emoji novamente
                    updated_emojis = await get_existing_emojis(app_id)
                    if name in updated_emojis:
                        emoji_info = updated_emojis[name]
                        if emoji_info.get('animated'):
                            emoji_tag = f"<a:{name}:{emoji_info['id']}>"
                        else:
                            emoji_tag = f"<:{name}:{emoji_info['id']}>"
                        
                        emojis_data[name] = emoji_tag
                        print(f"    - Já existia (sincronizado): {name}")
                        
                        # Salvar imediatamente no JSON
                        try:
                            with open(EMOJIS_DB, "w", encoding="utf-8") as f:
                                json.dump(emojis_data, f, indent=4, ensure_ascii=False)
                        except Exception as e:
                            print(f"    - Erro ao salvar {name}: {e}")
                    results.append((name, "already_exists"))
                elif emoji_id:
                    # Criar a tag do emoji
                    emoji_tag = f"<a:{name}:{emoji_id}>" if image_path.endswith('.gif') else f"<:{name}:{emoji_id}>"
                    emojis_data[name] = emoji_tag
                    results.append((name, "success"))
                    print(f"    - Criado: {name}")
                    
                    # Salvar imediatamente no JSON
                    try:
                        with open(EMOJIS_DB, "w", encoding="utf-8") as f:
                            json.dump(emojis_data, f, indent=4, ensure_ascii=False)
                    except Exception as e:
                        print(f"    - Erro ao salvar {name}: {e}")
                else:
                    results.append((name, "failed"))
                
                # Delay para evitar rate limit
                await asyncio.sleep(RATE_LIMIT_DELAY)
                
            except Exception as e:
                print(f"    - Erro ao processar {name}: {e}")
                results.append((name, "error"))
    
    return results

async def initialize_emojis(bot):
    print("--- Iniciando verificação e upload de emojis ---")
    bot.emojis_ready = False
    
    app_id = await ObterIDBOT(BOT_TOKEN)
    if not app_id:
        print("!!! ERRO: Não foi possível obter o ID da aplicação.")
        bot.emojis_ready = False
        return

    if not os.path.exists(EMOJIS_DB):
        print("!!! ERRO: Arquivo de emojis não encontrado.")
        bot.emojis_ready = False
        return

    # Carregar dados do JSON
    with open(EMOJIS_DB, "r", encoding="utf-8") as f:
        emojis_data = json.load(f)
    
    # Buscar emojis existentes no bot
    print("--- Sincronizando emojis existentes ---")
    existing_emojis = await get_existing_emojis(app_id)
    
    # Sincronizar emojis existentes com o JSON
    emojis_data, sync_count = await sync_existing_emojis(emojis_data, existing_emojis)
    
    if sync_count > 0:
        print(f"--- {sync_count} emojis sincronizados ---")
        # Salvar sincronizações
        with open(EMOJIS_DB, "w", encoding="utf-8") as f:
            json.dump(emojis_data, f, indent=4, ensure_ascii=False)
    
    # Identificar emojis que precisam ser carregados
    emojis_to_upload = []
    for name, emoji_tag in emojis_data.items():
        if not emoji_tag or not str(emoji_tag).startswith('<'):
            # Verificar se já existe no bot (pode ter sido criado mas não sincronizado)
            if name not in existing_emojis:
                emojis_to_upload.append(name)
    
    if not emojis_to_upload:
        print("--- Todos os emojis já estão sincronizados ---")
        bot.emojis_ready = True
        return

    total_to_upload = len(emojis_to_upload)
    print(f"--- Encontrados {total_to_upload} emojis para upload ---")
    
    # Processar em lotes com controle de concorrência
    uploaded_count = 0
    failed_count = 0
    already_exists_count = 0
    
    # Semáforo para controlar uploads simultâneos
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_UPLOADS)
    
    async with aiohttp.ClientSession() as session:
        # Dividir em lotes
        for i in range(0, total_to_upload, BATCH_SIZE):
            batch = emojis_to_upload[i:i + BATCH_SIZE]
            print(f"--- Processando lote {i//BATCH_SIZE + 1} ({len(batch)} emojis) ---")
            
            results = await process_emoji_batch(session, app_id, batch, emojis_data, semaphore, existing_emojis)
            
            # Processar resultados
            for name, result in results:
                if result == "success":
                    uploaded_count += 1
                elif result == "already_exists":
                    already_exists_count += 1
                else:
                    failed_count += 1
            
            # Progresso já é salvo durante o processamento individual
            print(f"    - Lote processado: {uploaded_count} criados, {already_exists_count} já existiam, {failed_count} falharam")
            
            # Pequeno delay entre lotes
            if i + BATCH_SIZE < total_to_upload:
                await asyncio.sleep(1)

    # Verificar se há emojis que "já existem" mas ainda não foram sincronizados
    if already_exists_count > 0:
        print(f"--- Verificação final de sincronização ---")
        # Buscar emojis novamente para garantir sincronização completa
        existing_emojis = await get_existing_emojis(app_id)
        
        additional_sync = 0
        for name, emoji_tag in emojis_data.items():
            if not emoji_tag or not str(emoji_tag).startswith('<'):
                if name in existing_emojis:
                    emoji_info = existing_emojis[name]
                    if emoji_info.get('animated'):
                        emoji_tag = f"<a:{name}:{emoji_info['id']}>"
                    else:
                        emoji_tag = f"<:{name}:{emoji_info['id']}>"
                    
                    emojis_data[name] = emoji_tag
                    additional_sync += 1
                    print(f"    - Sincronização final: {name}")
        
        if additional_sync > 0:
            print(f"    - {additional_sync} emojis sincronizados na verificação final")
            with open(EMOJIS_DB, "w", encoding="utf-8") as f:
                json.dump(emojis_data, f, indent=4, ensure_ascii=False)

    # Salvamento final
    try:
        with open(EMOJIS_DB, "w", encoding="utf-8") as f:
            json.dump(emojis_data, f, indent=4, ensure_ascii=False)
        print(f"--- Dados finais salvos ---")
    except Exception as e:
        print(f"!!! ERRO ao salvar dados finais: {e}")

    print(f"--- Resultado: {uploaded_count} criados, {already_exists_count} já existiam, {failed_count} falharam ---")
    
    # Marcar como pronto se não houve falhas críticas
    if failed_count == 0:
        bot.emojis_ready = True
        print("✅ Todos os emojis foram processados com sucesso!")
    else:
        bot.emojis_ready = False
        print(f"❌ {failed_count} emojis falharam no processamento.")
        return
    
    # Reiniciar apenas se novos emojis foram criados
    if uploaded_count > 0:
        print("🔄 Novos emojis criados! Reiniciando bot...")
        await asyncio.sleep(2)
        await bot.close()
        os.execv(sys.executable, [sys.executable] + sys.argv)

async def delete_emoji(session, app_id, emoji_id):
    """Deleta um emoji do bot"""
    url = f"https://discord.com/api/v9/applications/{app_id}/emojis/{emoji_id}"
    headers = {"Authorization": f"Bot {BOT_TOKEN}"}
    
    async with session.delete(url, headers=headers) as response:
        return response.status == 204
