# api_client.py
import aiohttp
import io

# !!! IMPORTANTE: Substitua pela URL real da sua API quando ela estiver no ar !!!
API_BASE_URL = "https://routeapieconomia.squareweb.app" 

async def gerar_imagem_api(endpoint: str, data: dict) -> bytes | None:
    """
    Envia dados para a API de geração de imagem e retorna os bytes da imagem.
    
    Args:
        endpoint: O endpoint específico para o tipo de imagem (ex: 'banco', 'petinfo').
        data: Um dicionário com os dados a serem enviados para a API (incluindo themeColor).

    Returns:
        Os bytes da imagem PNG, ou None se ocorrer um erro.
    """
    if API_BASE_URL == "https://routeapieconomia.squareweb.app":
        print(f"AVISO: A URL da API não foi configurada em api_client.py. A geração de imagem será pulada.")
        return None

    url = f"{API_BASE_URL}/{endpoint}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    print(f"[API_CLIENT] Erro na API para '{endpoint}': Status {response.status} | Resposta: {await response.text()}")
                    return None
    except Exception as e:
        print(f"[API_CLIENT] Erro fatal ao conectar-se à API: {e}")
        return None