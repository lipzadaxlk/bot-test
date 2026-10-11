import disnake
from disnake import *
import json
import os
import re
from datetime import *
import requests
import mercadopago
from efipay import EfiPay
import asyncio
import random
import string
import base64
import shutil

def GerarString():
    caracteres = string.ascii_letters + string.digits
    return ''.join(random.choices(caracteres, k=33))

def ObterCarrinho(carrinhoID):
    with open("Database/Vendas/carrinhos.json") as f:
        db = json.load(f)
        return db.get(carrinhoID)

def ObterFormasPagamento():
    with open("Database/Vendas/pagamentos.json") as f:
        return json.load(f)

def SalvarFormasPagamento(dados):
    with open("Database/Vendas/pagamentos.json", "w") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

def criar_qr_code(response_data):
    try:
        with open("Database/Vendas/vendas.json") as f: db = json.load(f)
        corMain = db.get("marca", {}).get("cores", {}).get("principal", "000000")
        corSec = db.get("marca", {}).get("cores", {}).get("sec", "000000")
        logoUrl = db.get("marca", {}).get("url", "")
    except (FileNotFoundError, json.JSONDecodeError):
        corMain, corSec, logoUrl = "000000", "000000", ""

    logo_id = None
    if logoUrl:
        try:
            logo_response = requests.get(logoUrl, stream=True)
            if logo_response.status_code == 200:
                with open("logo_temp.png", "wb") as file:
                    shutil.copyfileobj(logo_response.raw, file)
                
                with open("logo_temp.png", "rb") as image_file:
                    files = {"file": ("logo.png", image_file, "image/png")}
                    upload_response = requests.post("https://api.qrcode-monkey.com/qr/uploadImage", files=files)
                
                if upload_response.status_code == 200:
                    logo_id = upload_response.json().get("file")
        except Exception as e:
            print(f"DEBUG: Erro ao processar logo para QR Code: {e}")
        finally:
            if os.path.exists("logo_temp.png"): os.remove("logo_temp.png")

    payload = {
        "data": str(response_data),
        "config": {
            "body": "square", "eye": "frame0", "eyeBall": "ball0",
            "bodyColor": f"#{corMain}", "bgColor": "#FFFFFF",
            "eye1Color": f"#{corMain}", "eye2Color": f"#{corMain}", "eye3Color": f"#{corMain}",
            "eyeBall1Color": f"#{corSec}", "eyeBall2Color": f"#{corSec}", "eyeBall3Color": f"#{corSec}",
            "gradientColor1": f"#{corMain}", "gradientColor2": f"#{corSec}",
            "gradientType": "linear", "gradientOnEyes": True,
            "logo": logo_id
        }, "size": 600, "download": "imageUrl", "file": "png"
    }
    
    qr_response = requests.post(url="https://api.qrcode-monkey.com/qr/custom", json=payload)
    if qr_response.status_code == 200:
        return f"https:{qr_response.json()['imageUrl']}"
    else:
        print(f"DEBUG: Erro ao gerar QR Code: {qr_response.text}")
        return None

class MercadoPagoPagamento():
    @staticmethod
    def GerarPagamento(valor: float):
        db = ObterFormasPagamento()
        mp = db["mercadopago"]
        sdk = mercadopago.SDK(str(mp["access_key"]))
        payment_data = {"transaction_amount": valor, "payment_method_id": "pix", "payer": {"email": "test@test.com"}}
        payment_response = sdk.payment().create(payment_data)
        payment = payment_response.get("response", {})
        if "point_of_interaction" in payment:
            qr_code = payment["point_of_interaction"]["transaction_data"]["qr_code"]
            payment_id = payment["id"]
            qrcodeURL = criar_qr_code(qr_code)
            return qr_code, qrcodeURL, payment_id
        return None, None, None
    
    @staticmethod
    async def VerificarPagamento(carrinhoID: str):
        db = ObterFormasPagamento()
        mp = db["mercadopago"]
        sdk = mercadopago.SDK(str(mp["access_key"]))
        carrinho = ObterCarrinho(carrinhoID)
        paymentID = carrinho["info"]["pagamento"]["paymentID"]
        payment_info_response = sdk.payment().get(paymentID)
        payment_info = payment_info_response["response"]
        if payment_info["status"] == "approved":
            return True
        return False

class EfiBankPagamento():
    @staticmethod
    def ObterAccessToken():
        db = ObterFormasPagamento()["efi"]
        credentials = {"client_id": db["clientID"], "client_secret": db["clientSecret"]}
        certificado = 'Database/Vendas/certificado.pem'
        auth = base64.b64encode(f"{credentials['client_id']}:{credentials['client_secret']}".encode()).decode()
        url = "https://pix.api.efipay.com.br/oauth/token"
        payload="{\"grant_type\": \"client_credentials\"}"
        headers = {'Authorization': f"Basic {auth}", 'Content-Type': 'application/json'}
        try:
            response = requests.post(url, headers=headers, data=payload, cert=certificado)
            return response.json()["access_token"]
        except Exception as e:
            print(f"DEBUG: Erro ao obter Access Token Efi: {e}")
            return None

    @staticmethod
    def GerarPagamento(valor: float):
        db = ObterFormasPagamento()["efi"]
        credentials = {'client_id': db["clientID"],'client_secret': db["clientSecret"],'sandbox': False,'certificate': 'Database/Vendas/certificado.pem'}
        efi = EfiPay(credentials)
        body = {'calendario': {'expiracao': 600}, 'valor': {'original': f"{valor:.2f}"}, "chave": f"{db['chavePix']}"}
        try:
            response =  efi.pix_create_immediate_charge(body=body)
            if "txid" in response:
                qrcodeURL = criar_qr_code(response["pixCopiaECola"])
                return response["pixCopiaECola"], qrcodeURL, response["txid"]
        except Exception as e:
            print(f"DEBUG: Erro ao gerar cobrança Efi: {e}")
        return None, None, None

class AsaasPagamento():
    ASAAS_API_URL = "https://api.asaas.com/v3/"
    
    @staticmethod
    def GerarPagamento(valor: float):
        try:
            db = ObterFormasPagamento()
            asaas_config = db.get("asaas", {})
            if not asaas_config.get("api_key"):
                print("DEBUG: API Key da Asaas não configurada")
                return None, None, None
                
            headers = {"access_token": asaas_config["api_key"]}
            payload = {
                "billingType": "PIX",
                "value": valor,
                "dueDate": (datetime.now() + timedelta(minutes=30)).strftime("%Y-%m-%d")
            }
            
            response = requests.post(f"{AsaasPagamento.ASAAS_API_URL}payments", headers=headers, json=payload)
            
            if response.status_code == 200:
                payment_data = response.json()
                payment_id = payment_data["id"]
                
                # Buscar informações do PIX
                pix_response = requests.get(f"{AsaasPagamento.ASAAS_API_URL}payments/{payment_id}/pixQrCode", headers=headers)
                
                if pix_response.status_code == 200:
                    pix_data = pix_response.json()
                    qr_code = pix_data["payload"]
                    qr_code_url = criar_qr_code(qr_code)
                    return qr_code, qr_code_url, payment_id
                    
        except Exception as e:
            print(f"DEBUG: Erro ao gerar pagamento Asaas: {e}")
        
        return None, None, None
    
    @staticmethod
    async def VerificarPagamento(payment_id: str):
        try:
            db = ObterFormasPagamento()
            asaas_config = db.get("asaas", {})
            headers = {"access_token": asaas_config["api_key"]}
            
            response = requests.get(f"{AsaasPagamento.ASAAS_API_URL}payments/{payment_id}", headers=headers)
            
            if response.status_code == 200:
                payment_data = response.json()
                return payment_data["status"] == "RECEIVED"
                
        except Exception as e:
            print(f"DEBUG: Erro ao verificar pagamento Asaas: {e}")
        
        return False

class PicPayPagamento():
    @staticmethod
    def GerarPagamento(valor: float):
        try:
            db = ObterFormasPagamento()
            picpay_config = db.get("picpay", {})
            if not picpay_config.get("token"):
                print("DEBUG: Token do PicPay não configurado")
                return None, None, None
            
            # PicPay não tem API pública robusta para PIX ainda
            # Esta é uma implementação simplificada
            headers = {"Authorization": f"Bearer {picpay_config['token']}"}
            payload = {
                "referenceId": GerarString()[:20],
                "callbackUrl": "https://webhook.site/unique-id",
                "returnUrl": "https://www.picpay.com/",
                "value": valor,
                "buyer": {
                    "firstName": "Cliente",
                    "lastName": "Comprador",
                    "document": "123.456.789-10"
                }
            }
            
            # Endpoint hipotético - PicPay não tem API PIX pública ainda
            # return None, None, None  # Descomente esta linha se não quiser usar
            
        except Exception as e:
            print(f"DEBUG: Erro ao gerar pagamento PicPay: {e}")
        
        return None, None, None

class PagBankPagamento():
    @staticmethod
    def ObterAccessToken(client_id: str, client_secret: str):
        try:
            auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
            headers = {
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            data = "grant_type=client_credentials&scope=payments.create"
            
            response = requests.post("https://secure.api.pagseguro.com/pix/oauth2/", headers=headers, data=data)
            
            if response.status_code == 200:
                return response.json()["access_token"]
                
        except Exception as e:
            print(f"DEBUG: Erro ao obter token PagBank: {e}")
        
        return None
    
    @staticmethod
    def GerarPagamento(valor: float):
        try:
            db = ObterFormasPagamento()
            pagbank_config = db.get("pagbank", {})
            
            if not all([pagbank_config.get("client_id"), pagbank_config.get("client_secret")]):
                print("DEBUG: Credenciais do PagBank não configuradas")
                return None, None, None
            
            access_token = PagBankPagamento.ObterAccessToken(
                pagbank_config["client_id"], 
                pagbank_config["client_secret"]
            )
            
            if not access_token:
                return None, None, None
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "reference_id": GerarString()[:40],
                "customer": {
                    "name": "Cliente Comprador",
                    "email": "cliente@exemplo.com",
                    "tax_id": "12345678901"
                },
                "items": [
                    {
                        "reference_id": "item1",
                        "name": "Produto Digital",
                        "quantity": 1,
                        "unit_amount": int(valor * 100)
                    }
                ],
                "qr_codes": [
                    {
                        "amount": {
                            "value": int(valor * 100)
                        },
                        "expiration_date": (datetime.now() + timedelta(minutes=30)).isoformat()
                    }
                ]
            }
            
            response = requests.post("https://api.pagseguro.com/orders", headers=headers, json=payload)
            
            if response.status_code == 201:
                order_data = response.json()
                qr_code = order_data["qr_codes"][0]["text"]
                order_id = order_data["id"]
                qr_code_url = criar_qr_code(qr_code)
                return qr_code, qr_code_url, order_id
                
        except Exception as e:
            print(f"DEBUG: Erro ao gerar pagamento PagBank: {e}")
        
        return None, None, None
    
    @staticmethod
    async def VerificarPagamento(order_id: str):
        try:
            db = ObterFormasPagamento()
            pagbank_config = db.get("pagbank", {})
            
            access_token = PagBankPagamento.ObterAccessToken(
                pagbank_config["client_id"], 
                pagbank_config["client_secret"]
            )
            
            if not access_token:
                return False
            
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(f"https://api.pagseguro.com/orders/{order_id}", headers=headers)
            
            if response.status_code == 200:
                order_data = response.json()
                return order_data["status"] == "PAID"
                
        except Exception as e:
            print(f"DEBUG: Erro ao verificar pagamento PagBank: {e}")
        
        return False

class LivePixPagamento():
    @staticmethod
    def ObterAccessToken(client_id: str, client_secret: str):
        try:
            payload = {
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret
            }
            
            response = requests.post("https://api.livepix.gg/oauth/token", json=payload)
            
            if response.status_code == 200:
                return response.json()["access_token"]
                
        except Exception as e:
            print(f"DEBUG: Erro ao obter token LivePix: {e}")
        
        return None
    
    @staticmethod
    def GerarPagamento(valor: float):
        try:
            db = ObterFormasPagamento()
            livepix_config = db.get("livepix", {})
            
            if not all([livepix_config.get("client_id"), livepix_config.get("client_secret")]):
                print("DEBUG: Credenciais da LivePix não configuradas")
                return None, None, None
            
            access_token = LivePixPagamento.ObterAccessToken(
                livepix_config["client_id"], 
                livepix_config["client_secret"]
            )
            
            if not access_token:
                return None, None, None
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "amount": valor,
                "description": "Compra de produto digital",
                "external_id": GerarString()[:30]
            }
            
            response = requests.post("https://api.livepix.gg/v1/pix/create", headers=headers, json=payload)
            
            if response.status_code == 200:
                payment_data = response.json()
                qr_code = payment_data["qr_code"]
                payment_id = payment_data["id"]
                qr_code_url = criar_qr_code(qr_code)
                return qr_code, qr_code_url, payment_id
                
        except Exception as e:
            print(f"DEBUG: Erro ao gerar pagamento LivePix: {e}")
        
        return None, None, None
    
    @staticmethod
    async def VerificarPagamento(payment_id: str):
        try:
            db = ObterFormasPagamento()
            livepix_config = db.get("livepix", {})
            
            access_token = LivePixPagamento.ObterAccessToken(
                livepix_config["client_id"], 
                livepix_config["client_secret"]
            )
            
            if not access_token:
                return False
            
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(f"https://api.livepix.gg/v1/pix/{payment_id}", headers=headers)
            
            if response.status_code == 200:
                payment_data = response.json()
                return payment_data["status"] == "paid"
                
        except Exception as e:
            print(f"DEBUG: Erro ao verificar pagamento LivePix: {e}")
        
        return False

class InterPagamento():
    @staticmethod
    def ObterAccessToken(client_id: str, client_secret: str, cert_path: str, key_path: str):
        try:
            payload = {
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "pix.write pix.read"
            }
            
            response = requests.post(
                "https://cdpj.partners.bancointer.com.br/oauth/token",
                json=payload,
                cert=(cert_path, key_path)
            )
            
            if response.status_code == 200:
                return response.json()["access_token"]
                
        except Exception as e:
            print(f"DEBUG: Erro ao obter token Banco Inter: {e}")
        
        return None
    
    @staticmethod
    def GerarPagamento(valor: float):
        try:
            db = ObterFormasPagamento()
            inter_config = db.get("inter", {})
            
            required_fields = ["client_id", "client_secret", "cert_path", "key_path"]
            if not all(inter_config.get(field) for field in required_fields):
                print("DEBUG: Credenciais do Banco Inter não configuradas completamente")
                return None, None, None
            
            access_token = InterPagamento.ObterAccessToken(
                inter_config["client_id"],
                inter_config["client_secret"],
                inter_config["cert_path"],
                inter_config["key_path"]
            )
            
            if not access_token:
                return None, None, None
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "calendario": {
                    "expiracao": 1800
                },
                "valor": {
                    "original": f"{valor:.2f}"
                },
                "chave": inter_config.get("chave_pix", ""),
                "solicitacaoPagador": "Pagamento de produto digital"
            }
            
            response = requests.post(
                "https://cdpj.partners.bancointer.com.br/pix/v2/cob",
                headers=headers,
                json=payload,
                cert=(inter_config["cert_path"], inter_config["key_path"])
            )
            
            if response.status_code == 201:
                payment_data = response.json()
                qr_code = payment_data["pixCopiaECola"]
                txid = payment_data["txid"]
                qr_code_url = criar_qr_code(qr_code)
                return qr_code, qr_code_url, txid
                
        except Exception as e:
            print(f"DEBUG: Erro ao gerar pagamento Banco Inter: {e}")
        
        return None, None, None
    
    @staticmethod
    async def VerificarPagamento(txid: str):
        try:
            db = ObterFormasPagamento()
            inter_config = db.get("inter", {})
            
            access_token = InterPagamento.ObterAccessToken(
                inter_config["client_id"],
                inter_config["client_secret"],
                inter_config["cert_path"],
                inter_config["key_path"]
            )
            
            if not access_token:
                return False
            
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(
                f"https://cdpj.partners.bancointer.com.br/pix/v2/cob/{txid}",
                headers=headers,
                cert=(inter_config["cert_path"], inter_config["key_path"])
            )
            
            if response.status_code == 200:
                payment_data = response.json()
                return payment_data.get("status") == "CONCLUIDA"
                
        except Exception as e:
            print(f"DEBUG: Erro ao verificar pagamento Banco Inter: {e}")
        
        return False

class NubankImapPagamento:
    @staticmethod
    def _gerar_payload_brcode(chave_pix, valor, nome, cidade):
        # Implementação simplificada do BRCODE
        ID_PAYLOAD_FORMAT = '000201'
        ID_MERCHANT_ACCOUNT_INFO = '26'
        ID_MERCHANT_ACCOUNT_GUI = '0014BR.GOV.BCB.PIX'
        ID_MERCHANT_ACCOUNT_KEY = f'01{len(chave_pix):02}{chave_pix}'
        ID_MERCHANT_CATEGORY_CODE = '52040000'
        ID_TRANSACTION_CURRENCY = '5303986'
        ID_TRANSACTION_AMOUNT = f'54{len(f"{valor:.2f}"):02}{valor:.2f}'
        ID_COUNTRY_CODE = '5802BR'
        ID_MERCHANT_NAME = f'59{len(nome):02}{nome}'
        ID_MERCHANT_CITY = f'60{len(cidade):02}{cidade}'
        ID_CRC16 = '6304'
        
        payload_sem_crc = (f"{ID_PAYLOAD_FORMAT}"
                           f"{ID_MERCHANT_ACCOUNT_INFO}{len(ID_MERCHANT_ACCOUNT_GUI + ID_MERCHANT_ACCOUNT_KEY):02}"
                           f"{ID_MERCHANT_ACCOUNT_GUI}{ID_MERCHANT_ACCOUNT_KEY}"
                           f"{ID_MERCHANT_CATEGORY_CODE}"
                           f"{ID_TRANSACTION_CURRENCY}"
                           f"{ID_TRANSACTION_AMOUNT}"
                           f"{ID_COUNTRY_CODE}"
                           f"{ID_MERCHANT_NAME}"
                           f"{ID_MERCHANT_CITY}"
                           f"{ID_CRC16}")

        # Cálculo do CRC16 (simplificado, ideal seria usar uma biblioteca)
        crc = 0xFFFF
        for c in payload_sem_crc:
            crc ^= ord(c) << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc <<= 1
        crc &= 0xFFFF
        
        return f"{payload_sem_crc}{crc:04X}"
        
    @staticmethod
    def GerarPixUnico(carrinho):
        fp = ObterFormasPagamento()
        nubank_config = fp.get("nubank_imap", {})
        chave_pix = nubank_config.get("chave_pix")
        if not chave_pix: return None, None, None

        valor_total = float(carrinho["info"]["valorFinal"])
        valor_unico = round(valor_total + (random.randint(1, 99) / 100), 2)
        
        # Gera o payload BRCODE para o copia e cola
        payload = NubankImapPagamento._gerar_payload_brcode(chave_pix, valor_unico, "Sua Loja", "SAO PAULO")
        qr_code_url = criar_qr_code(payload)

        return payload, qr_code_url, valor_unico

# Implementação simplificada para bancos IMAP (Itaú, Santander, Bradesco, C6)
class IMAPBankPagamento:
    @staticmethod
    def _gerar_payload_brcode(chave_pix, valor, nome, cidade):
        # Mesma implementação do Nubank
        return NubankImapPagamento._gerar_payload_brcode(chave_pix, valor, nome, cidade)
    
    @staticmethod
    def GerarPixUnico(carrinho, banco_key):
        fp = ObterFormasPagamento()
        banco_config = fp.get(f"{banco_key}_imap", {})
        chave_pix = banco_config.get("chave_pix")
        if not chave_pix: 
            return None, None, None

        valor_total = float(carrinho["info"]["valorFinal"])
        valor_unico = round(valor_total + (random.randint(1, 99) / 100), 2)
        
        payload = IMAPBankPagamento._gerar_payload_brcode(chave_pix, valor_unico, "Sua Loja", "SAO PAULO")
        qr_code_url = criar_qr_code(payload)

        return payload, qr_code_url, valor_unico

class SemiAutoPagamento():
    @staticmethod
    def GerarPagamento():
        db = ObterFormasPagamento()
        chave = db["semiauto"]["chavePix"]
        qrcode_url = criar_qr_code(chave)
        return chave, qrcode_url