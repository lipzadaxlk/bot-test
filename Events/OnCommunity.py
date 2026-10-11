import disnake
from disnake.ext import commands
import json
import os
import uuid
import io
import aiohttp
import re
import asyncio
import random
import base64
import wave

# --- Dependências da IA ---
from groq import AsyncGroq
from PIL import Image, ImageDraw, ImageFont
import requests

# --- CONFIGURAÇÃO DAS API KEYS ---
# Adicione suas chaves da API do Groq aqui (pode colocar várias para rate limit)
GROQ_API_KEYS = [
    "SUA_CHAVE_GROQ_AQUI_1",
    "SUA_CHAVE_GROQ_AQUI_2",
    "SUA_CHAVE_GROQ_AQUI_3",
    "SUA_CHAVE_GROQ_AQUI_4"
    # Adicione quantas chaves quiser...
]

# Remove as chaves vazias/placeholder
GROQ_API_KEYS = [key for key in GROQ_API_KEYS if not key.startswith("SUA_CHAVE")]

if not GROQ_API_KEYS:
    print("AVISO: Nenhuma chave da API do Groq foi configurada. Funcionalidades de IA estarão desativadas.")

# Funções e constantes necessárias
def carregar_json(caminho, default=None):
    if default is None: default = {}
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    try:
        with open(caminho, "r", encoding='utf-8') as f: return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        salvar_json(caminho, default)
        return default

def salvar_json(caminho, data):
    with open(caminho, "w", encoding='utf-8') as f: json.dump(data, f, indent=4)

EMOJIS_TEMAS_INSTAGRAM = {
    "vermelho": {"like": "❤️", "comment": "💬", "profile": "", "info": "ℹ️", "delete": "🗑️"},
    "azul":     {"like": "👍", "comment": "✍️", "profile": "", "info": "❓", "delete": "❌"},
}

def ObterCanais(): return carregar_json("Database/Server/canais.json", {"logsformulario": None})
def verificar_permissao(user_id): return True

# Classe customizada para capturar áudio (substitui disnake.sinks)
class AudioRecorder:
    def __init__(self):
        self.audio_data = {}
    def write(self, data, user_id):
        """Escreve dados de áudio para um usuário específico"""
        if user_id not in self.audio_data:
            self.audio_data[user_id] = []
        self.audio_data[user_id].append(data)
    def get_audio_data(self, user_id):
        """Retorna os dados de áudio de um usuário"""
        return b''.join(self.audio_data.get(user_id, []))
    def clear_user_data(self, user_id):
        """Limpa os dados de áudio de um usuário"""
        if user_id in self.audio_data:
            del self.audio_data[user_id]

class GroqManager:
    """Gerenciador das APIs do Groq com rate limit automático"""
    def __init__(self, api_keys):
        self.api_keys = api_keys
        self.current_key_index = 0
        self.clients = {}
        self.failed_keys = set()
        # Inicializar clientes
        for i, key in enumerate(api_keys):
            self.clients[i] = AsyncGroq(api_key=key)

    def get_next_client(self):
        """Retorna o próximo cliente disponível"""
        if not self.api_keys:
            return None
        # Encontra uma chave que não falhou
        attempts = 0
        while attempts < len(self.api_keys):
            if self.current_key_index not in self.failed_keys:
                client = self.clients[self.current_key_index]
                return client, self.current_key_index
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            attempts += 1
        # Se todas as chaves falharam, reset o contador de falhas
        self.failed_keys.clear()
        return self.clients[0], 0

    def mark_key_failed(self, key_index):
        """Marca uma chave como falhada temporariamente"""
        self.failed_keys.add(key_index)
        # Remove da lista de falhas após 5 minutos
        asyncio.create_task(self._reset_key_after_delay(key_index))

    async def _reset_key_after_delay(self, key_index):
        """Remove uma chave da lista de falhas após delay"""
        await asyncio.sleep(300)  # 5 minutos
        self.failed_keys.discard(key_index)

    async def chat_completion(self, messages, model="llama-3.3-70b-versatile", **kwargs):
        """Faz uma requisição de chat com fallback automático"""
        client, key_index = self.get_next_client()
        if not client:
            raise Exception("Nenhuma API key disponível")
        try:
            response = await client.chat.completions.create(
                messages=messages,
                model=model,
                **kwargs
            )
            return response
        except Exception as e:
            if "rate_limit" in str(e).lower() or "quota" in str(e).lower():
                self.mark_key_failed(key_index)
                # Tenta com a próxima chave
                if len(self.failed_keys) < len(self.api_keys):
                    return await self.chat_completion(messages, model, **kwargs)
            raise e

    async def audio_transcription(self, audio_file, model="whisper-large-v3"):
        """Transcreve áudio usando Groq"""
        client, key_index = self.get_next_client()
        if not client:
            raise Exception("Nenhuma API key disponível")
        try:
            transcription = await client.audio.transcriptions.create(
                file=audio_file,
                model=model,
                language="pt"
            )
            return transcription
        except Exception as e:
            if "rate_limit" in str(e).lower() or "quota" in str(e).lower():
                self.mark_key_failed(key_index)
                if len(self.failed_keys) < len(self.api_keys):
                    return await self.audio_transcription(audio_file, model)
            raise e

class CogComunidade(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_topic_forms = {}
        self.session = None
        self.active_temp_calls = {}
        # Sistemas de IA
        self.voice_clients = {}
        self.audio_recorders = {}
        self.user_conversations = {}
        # Inicializar Groq
        if GROQ_API_KEYS:
            self.groq_manager = GroqManager(GROQ_API_KEYS)
            print(f"✅ Groq inicializado com {len(GROQ_API_KEYS)} chave(s) de API")
        else:
            self.groq_manager = None
            print("AVISO: Groq não foi inicializado devido à falta de API Keys.")

    def cog_load(self):
        self.session = aiohttp.ClientSession(loop=self.bot.loop)

    def cog_unload(self):
        if self.session:
            self.bot.loop.create_task(self.session.close())
        for vc in self.voice_clients.values():
            self.bot.loop.create_task(vc.disconnect())

    # ================================================================================= #
    #                                  SISTEMA DE IA
    # ================================================================================= #
    async def detect_intent(self, message_content: str) -> str:
        """Detecta a intenção da mensagem: 'image', 'code', 'audio' ou 'text'"""
        try:
            detection_prompt = f"""
Analise esta mensagem e determine se é um pedido para:
GERAR IMAGEM (image): Palavras como "desenhe", "crie uma imagem", "gere uma foto", "faça um desenho", "ilustração", etc.
GERAR CÓDIGO (code): Pedidos específicos de programação, scripts, funções, etc.
CONVERSA NORMAL (text): Perguntas, conversas, explicações, etc.
Mensagem: "{message_content}"
Responda APENAS com: image, code ou text
"""
            messages = [
                {"role": "system", "content": "Você é um classificador de intenções. Responda apenas com uma palavra."},
                {"role": "user", "content": detection_prompt}
            ]
            response = await self.groq_manager.chat_completion(
                messages=messages,
                model="llama-3.1-8b-instant",
                max_tokens=5
            )
            intent = response.choices[0].message.content.strip().lower()
            return intent if intent in ['image', 'code', 'text'] else 'text'
        except:
            return 'text'  # Default para conversa normal

    async def generate_image_with_ai(self, prompt: str) -> tuple[io.BytesIO, str]:
        """Gera uma imagem usando IA para criar um prompt melhorado e uma imagem artística"""
        try:
            # 1. Melhorar o prompt usando IA
            enhancement_messages = [
                {
                    "role": "system",
                    "content": """Você é um especialista em criar prompts detalhados para geração de imagens.
                    Transforme prompts simples em prompts profissionais, artísticos e detalhados.
                    Adicione detalhes sobre: estilo, iluminação, composição, cores, qualidade.
                    Mantenha em português e seja criativo."""
                },
                {
                    "role": "user",
                    "content": f"Transforme este pedido em um prompt profissional para geração de imagem: {prompt}"
                }
            ]
            response = await self.groq_manager.chat_completion(
                messages=enhancement_messages,
                model="llama-3.3-70b-versatile",
                max_tokens=300
            )
            enhanced_prompt = response.choices[0].message.content
            # 2. Gerar uma imagem artística usando PIL com base no prompt melhorado
            return await self.create_artistic_image(prompt, enhanced_prompt), enhanced_prompt
        except Exception as e:
            print(f"Erro ao gerar imagem com IA: {e}")
            return await self.create_artistic_image(prompt, "Imagem solicitada"), "Prompt padrão"

    async def create_artistic_image(self, original_prompt: str, enhanced_prompt: str) -> io.BytesIO:
        """Cria uma imagem artística usando PIL"""
        # Criar imagem com gradiente baseado no tipo de prompt
        width, height = 1024, 1024
        img = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(img)
        # Escolher cores baseadas no prompt
        colors = self.get_colors_from_prompt(original_prompt)
        # Criar gradiente
        for i in range(height):
            ratio = i / height
            r = int(colors[0][0] * (1 - ratio) + colors[1][0] * ratio)
            g = int(colors[0][1] * (1 - ratio) + colors[1][1] * ratio)
            b = int(colors[0][2] * (1 - ratio) + colors[1][2] * ratio)
            draw.line([(0, i), (width, i)], fill=(r, g, b))
        # Adicionar formas geométricas baseadas no prompt
        self.add_artistic_shapes(draw, width, height, original_prompt)
        # Adicionar texto
        try:
            font_large = ImageFont.truetype("arial.ttf", 48)
            font_medium = ImageFont.truetype("arial.ttf", 24)
        except:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
        # Título
        title = "🎨 IMAGEM GERADA POR IA"
        title_bbox = draw.textbbox((0, 0), title, font=font_large)
        title_width = title_bbox[2] - title_bbox[0]
        draw.text(((width - title_width) // 2, 50), title, font=font_large, fill=(255, 255, 255))
        # Prompt original
        prompt_lines = [original_prompt[i:i+50] for i in range(0, len(original_prompt), 50)]
        y_offset = 150
        for line in prompt_lines[:3]:  # Máximo 3 linhas
            line_bbox = draw.textbbox((0, 0), line, font=font_medium)
            line_width = line_bbox[2] - line_bbox[0]
            draw.text(((width - line_width) // 2, y_offset), line, font=font_medium, fill=(255, 255, 255))
            y_offset += 40
        # Prompt melhorado (menor)
        enhanced_lines = [enhanced_prompt[i:i+60] for i in range(0, len(enhanced_prompt), 60)]
        y_offset = height - 200
        draw.text((50, y_offset - 30), "✨ Prompt Melhorado pela IA:", font=font_medium, fill=(200, 200, 200))
        for line in enhanced_lines[:4]:  # Máximo 4 linhas
            if y_offset < height - 50:
                draw.text((50, y_offset), line, font=font_medium, fill=(180, 180, 180))
                y_offset += 30
        # Salvar em BytesIO
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG', quality=95)
        img_bytes.seek(0)
        return img_bytes

    def get_colors_from_prompt(self, prompt: str) -> list:
        """Retorna cores baseadas no prompt"""
        prompt_lower = prompt.lower()
        if any(word in prompt_lower for word in ['fogo', 'vermelho', 'quente', 'pôr do sol']):
            return [(255, 69, 0), (255, 140, 0)]  # Laranja/Vermelho
        elif any(word in prompt_lower for word in ['água', 'azul', 'mar', 'céu']):
            return [(30, 144, 255), (0, 191, 255)]  # Azul
        elif any(word in prompt_lower for word in ['natureza', 'verde', 'floresta', 'planta']):
            return [(34, 139, 34), (50, 205, 50)]  # Verde
        elif any(word in prompt_lower for word in ['roxo', 'magia', 'místico', 'fantasia']):
            return [(138, 43, 226), (75, 0, 130)]  # Roxo
        elif any(word in prompt_lower for word in ['dourado', 'ouro', 'luxo', 'elegante']):
            return [(255, 215, 0), (255, 165, 0)]  # Dourado
        else:
            return [(75, 0, 130), (25, 25, 112)]  # Roxo/Azul padrão

    def add_artistic_shapes(self, draw, width, height, prompt: str):
        """Adiciona formas artísticas baseadas no prompt"""
        prompt_lower = prompt.lower()
        # Círculos para temas orgânicos
        if any(word in prompt_lower for word in ['circular', 'sol', 'lua', 'bola', 'redondo']):
            for i in range(5):
                x = random.randint(100, width - 100)
                y = random.randint(100, height - 100)
                radius = random.randint(20, 80)
                draw.ellipse([x-radius, y-radius, x+radius, y+radius],
                           outline=(255, 255, 255, 100), width=3)
        # Linhas para temas geométricos
        elif any(word in prompt_lower for word in ['linear', 'linha', 'geometric', 'moderno']):
            for i in range(8):
                x1, y1 = random.randint(0, width), random.randint(0, height)
                x2, y2 = random.randint(0, width), random.randint(0, height)
                draw.line([x1, y1, x2, y2], fill=(255, 255, 255, 80), width=2)
        # Estrelas para temas cósmicos
        elif any(word in prompt_lower for word in ['estrela', 'espaço', 'cosmos', 'galáxia']):
            for i in range(10):
                x, y = random.randint(50, width-50), random.randint(50, height-50)
                size = random.randint(3, 8)
                draw.polygon([(x, y-size), (x+2, y-2), (x+size, y),
                            (x+2, y+2), (x, y+size), (x-2, y+2),
                            (x-size, y), (x-2, y-2)],
                           fill=(255, 255, 255))

    async def text_to_speech_groq(self, text: str) -> str | None:
        """Converte texto em áudio usando modelos TTS disponíveis"""
        # Por enquanto, o Groq não tem TTS público, mas vamos usar uma implementação alternativa
        # Você pode integrar com outras APIs de TTS ou usar bibliotecas locais
        try:
            # Placeholder para TTS - você pode integrar com outras APIs como:
            # - Azure Cognitive Services
            # - Amazon Polly
            # - gTTS (Google Text-to-Speech)
            # - Coqui TTS (local)
            # Exemplo usando gTTS (precisa instalar: pip install gtts)
            from gtts import gTTS
            tts = gTTS(text=text, lang='pt', slow=False)
            filepath = f"temp_audio_{uuid.uuid4()}.mp3"
            tts.save(filepath)
            # Limpar arquivo depois de um tempo
            self.bot.loop.call_later(60, lambda: os.remove(filepath) if os.path.exists(filepath) else None)
            return filepath
        except Exception as e:
            print(f"Erro no TTS: {e}")
            return None

    async def speech_to_text_groq(self, audio_file_path: str) -> str | None:
        """Converte áudio em texto usando Whisper do Groq"""
        try:
            with open(audio_file_path, "rb") as audio_file:
                transcription = await self.groq_manager.audio_transcription(
                    audio_file=audio_file,
                    model="whisper-large-v3"
                )
                return transcription.text
        except Exception as e:
            print(f"Erro no STT Groq: {e}")
            return None

    async def handle_ai_message(self, message: disnake.Message):
        ia_config = carregar_json("Database/Comunidade/ia.json")
        if not self.groq_manager or not ia_config.get("canal_texto_id") == message.channel.id:
            return
        is_audio_on = ia_config.get("status_audio", False)
        is_imagem_on = ia_config.get("status_imagem", False)
        is_conversa_on = ia_config.get("status_conversa", False)
        prompt_text = message.content
        try:
            # --- Modo Áudio (Prioridade Máxima) ---
            if is_audio_on:
                async with message.channel.typing():
                    # 1. Gerar resposta em texto primeiro
                    messages = [
                        {"role": "system", "content": "Você é um assistente de voz. Seja conciso e natural em suas respostas de áudio. Máximo 2 parágrafos."},
                        {"role": "user", "content": prompt_text}
                    ]
                    response = await self.groq_manager.chat_completion(
                        messages=messages,
                        model="llama-3.3-70b-versatile",
                        max_tokens=300
                    )
                    response_text = response.choices[0].message.content
                    # 2. Sintetizar o texto em áudio
                    audio_file = await self.text_to_speech_groq(response_text)
                    if audio_file:
                        await message.reply(file=disnake.File(fp=audio_file, filename="resposta.mp3"))
                    else:
                        await message.reply(f"🔊 **Resposta em Áudio (erro no TTS):**\n{response_text}")
                return
            # --- Detecção Inteligente de Intenção ---
            if is_conversa_on:
                intent = await self.detect_intent(prompt_text)
                # --- Modo Imagem (Detecção Automática) ---
                if is_imagem_on and intent == 'image':
                    async with message.channel.typing():
                        await message.reply(f" Detectei um pedido de imagem! Criando arte para: `{prompt_text}`")
                        # Gerar imagem com IA
                        image_bytes, enhanced_prompt = await self.generate_image_with_ai(prompt_text)
                        embed = disnake.Embed(
                            title="🎨 Imagem Gerada por IA",
                            description=f"**Prompt Original:** {prompt_text}\n\n**Prompt Melhorado:** {enhanced_prompt[:200]}...",
                            color=disnake.Color.purple()
                        )
                        embed.set_footer(text="Powered by Groq AI + PIL Artístico")
                        await message.reply(
                            embed=embed,
                            file=disnake.File(fp=image_bytes, filename="groq_art.png")
                        )
                    return
            # --- Modo Conversa (Texto, Visão e Código) ---
            if is_conversa_on:
                # Inicializar conversa se não existir
                if message.channel.id not in self.user_conversations:
                    system_prompt = ia_config.get("prompt", "Você é um assistente prestativo e inteligente.")
                    self.user_conversations[message.channel.id] = [
                        {"role": "system", "content": system_prompt}
                    ]
                conversation = self.user_conversations[message.channel.id]
                async with message.channel.typing():
                    # Verifica se há anexos (Visão)
                    if message.attachments:
                        for attachment in message.attachments:
                            if "image" in attachment.content_type:
                                try:
                                    image_bytes = await attachment.read()
                                    # Converter para base64
                                    image_b64 = base64.b64encode(image_bytes).decode('utf-8')
                                    # Usar modelo de visão
                                    vision_messages = [
                                        {"role": "system", "content": "Você é um assistente que pode analisar imagens. Seja detalhado e útil."},
                                        {
                                            "role": "user",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": prompt_text if prompt_text else "Analise esta imagem detalhadamente."
                                                },
                                                {
                                                    "type": "image_url",
                                                    "image_url": {
                                                        "url": f"data:image/jpeg;base64,{image_b64}"
                                                    }
                                                }
                                            ]
                                        }
                                    ]
                                    response = await self.groq_manager.chat_completion(
                                        messages=vision_messages,
                                        model="llama-3.2-90b-vision-preview",
                                        max_tokens=1500
                                    )
                                    reply_text = response.choices[0].message.content
                                    break
                                except Exception as e:
                                    print(f"Erro ao processar imagem: {e}")
                                    reply_text = "❌ Erro ao processar a imagem."
                            # Processar áudio se houver
                            elif "audio" in attachment.content_type:
                                try:
                                    audio_bytes = await attachment.read()
                                    audio_path = f"temp_audio_input_{uuid.uuid4()}.{attachment.filename.split('.')[-1]}"
                                    with open(audio_path, "wb") as f:
                                        f.write(audio_bytes)
                                    # Transcrever usando Groq Whisper
                                    transcript = await self.speech_to_text_groq(audio_path)
                                    # Limpar arquivo
                                    os.remove(audio_path)
                                    if transcript:
                                        # Processar transcrição como texto normal
                                        full_prompt = f"{prompt_text} [ÁUDIO TRANSCRITO: {transcript}]"
                                        conversation.append({"role": "user", "content": full_prompt})
                                        response = await self.groq_manager.chat_completion(
                                            messages=conversation[-10:],  # Últimas 10 mensagens
                                            model="llama-3.3-70b-versatile",
                                            max_tokens=1000
                                        )
                                        reply_text = f"🎙️ **Transcrição:** {transcript}\n\n**Resposta:** {response.choices[0].message.content}"
                                        conversation.append({"role": "assistant", "content": response.choices[0].message.content})
                                    else:
                                        reply_text = "❌ Não consegui transcrever o áudio."
                                except Exception as e:
                                    print(f"Erro ao processar áudio: {e}")
                                    reply_text = "❌ Erro ao processar o áudio."
                                break
                    else:
                        # Conversa normal - escolher modelo baseado na intenção
                        conversation.append({"role": "user", "content": prompt_text})
                        # Manter apenas as últimas 20 mensagens
                        if len(conversation) > 21:
                            conversation = conversation[:1] + conversation[-20:]
                        # Escolher modelo baseado no tipo de conteúdo
                        if intent == 'code':
                            model = "llama-3.3-70b-versatile"  # Melhor para código
                            max_tokens = 2000
                        else:
                            model = "llama-3.3-70b-versatile"  # Modelo geral
                            max_tokens = 1000
                        response = await self.groq_manager.chat_completion(
                            messages=conversation,
                            model=model,
                            max_tokens=max_tokens
                        )
                        reply_text = response.choices[0].message.content
                        # Adicionar resposta da IA ao histórico
                        conversation.append({"role": "assistant", "content": reply_text})
                        self.user_conversations[message.channel.id] = conversation
                    # Enviar resposta em chunks se for muito longa
                    chunks = [reply_text[i:i + 2000] for i in range(0, len(reply_text), 2000)]
                    for i, chunk in enumerate(chunks):
                        if i == 0:
                            await message.reply(chunk)
                        else:
                            await message.channel.send(chunk)
        except Exception as e:
            error_msg = str(e)
            if "rate_limit" in error_msg.lower():
                await message.reply("🤖 Muitas requisições! Tente novamente em alguns segundos.")
            elif "quota" in error_msg.lower():
                await message.reply("🤖 Cota da API esgotada. Tente novamente mais tarde.")
            else:
                await message.reply(f"🤖 Ocorreu um erro: `{error_msg}`")

    async def after_speaking(self, error, member: disnake.Member):
        if error: print(f"Erro ao tocar áudio: {error}")
        try:
            await member.edit(mute=False)
        except Exception as e:
            print(f"Erro ao desmutar membro {member.id}: {e}")

    async def process_voice_input(self, member: disnake.Member, audio_data: bytes):
        """Processa entrada de voz de um membro usando Groq"""
        if member.bot: return
        vc = self.voice_clients.get(member.guild.id)
        if not vc: return
        try:
            await member.edit(mute=True)
        except Exception as e:
            print(f"Não foi possível mutar o membro {member.id}: {e}")
            return
        # Salvar áudio temporariamente para transcrição
        audio_path = f"temp_voice_{uuid.uuid4()}.wav"
        try:
            with wave.open(audio_path, 'wb') as wf:
                wf.setnchannels(2)
                wf.setsampwidth(2)
                wf.setframerate(48000)
                wf.writeframes(audio_data)
            # Transcrever usando Groq
            transcript = await self.speech_to_text_groq(audio_path)
            os.remove(audio_path)
            if not transcript:
                await self.after_speaking(None, member)
                return
            print(f"Texto Transcrito de {member.display_name}: {transcript}")
            # Gerar resposta usando Groq
            ia_config = carregar_json("Database/Comunidade/ia.json")
            system_prompt = ia_config.get("prompt", "Você é um assistente de voz. Seja breve e natural em suas respostas faladas.")
            messages = [
                {"role": "system", "content": f"{system_prompt}\n\nUSUÁRIO FALOU POR VOZ, seja breve na resposta (máximo 100 palavras)."},
                {"role": "user", "content": transcript}
            ]
            response = await self.groq_manager.chat_completion(
                messages=messages,
                model="llama-3.3-70b-versatile",
                max_tokens=150
            )
            response_text = response.choices[0].message.content
            print(f"Resposta da IA: {response_text}")
            # Converter resposta em áudio
            audio_response_file = await self.text_to_speech_groq(response_text)
            if audio_response_file:
                source = disnake.FFmpegPCMAudio(audio_response_file)
                vc.play(source, after=lambda e: self.bot.loop.create_task(self.after_speaking(e, member)))
            else:
                await self.after_speaking(None, member)
        except Exception as e:
            print(f"Erro ao processar voz: {e}")
            if os.path.exists(audio_path):
                os.remove(audio_path)
            await self.after_speaking(e, member)

    # ================================================================================= #
    #                      LISTENERS E HANDLERS DE OUTROS SISTEMAS
    # ================================================================================= #
    @commands.Cog.listener("on_message")
    async def on_message_handler(self, message: disnake.Message):
        if message.author.bot or not message.guild: return
        # Lógica de IA (Conversa, Imagem, Áudio)
        await self.handle_ai_message(message)
        if message.author.id in self.active_topic_forms:
            if isinstance(message.channel, disnake.Thread) and message.channel.id == self.active_topic_forms[message.author.id]["thread_id"]:
                await self.on_topic_form_message(message)
                return
        config_keys = carregar_json("Database/Comunidade/keys.json")
        if config_keys.get("status") and message.channel.id == config_keys.get("canal_keys_id"):
            await self.handle_key_redemption(message)
            return
        config_ig = carregar_json("Database/Comunidade/instagram.json")
        prefix = config_ig.get("prefixo", "ig!")
        if not message.content.startswith(prefix):
            return
        args = message.content[len(prefix):].strip().split()
        if not args: return
        cmd = args[0].lower()
        if cmd == "post": await self.handle_instagram_post(message)
        elif cmd == "vincular": await self.handle_instagram_link(message)

    @commands.Cog.listener("on_button_click")
    async def on_button_click_handler(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        if custom_id.startswith("open_form_") or custom_id.startswith("form_topic_start_") or custom_id.startswith("form_approve_") or custom_id.startswith("form_refuse_"):
            await self.on_form_button_click(inter)
        elif custom_id.startswith("ig_"):
            await self.instagram_button_handler(inter)

    @commands.Cog.listener("on_modal_submit")
    async def on_modal_submit_handler(self, inter: disnake.ModalInteraction):
        custom_id = inter.custom_id
        if custom_id.startswith("submit_form_modal_"):
            await self.on_form_modal_submit(inter)
        elif custom_id.startswith("ig_"):
            await self.instagram_modal_handler(inter)
        elif custom_id.startswith("tempcall_"):
            await self.temp_call_modal_handler(inter)

    @commands.Cog.listener("on_voice_state_update")
    async def universal_voice_state_handler(self, member: disnake.Member, before: disnake.VoiceState, after: disnake.VoiceState):
        await self.temp_call_handler(member, before, after)
        await self.ai_voice_handler(member, before, after)

    async def ai_voice_handler(self, member: disnake.Member, before: disnake.VoiceState, after: disnake.VoiceState):
        ia_config = carregar_json("Database/Comunidade/ia.json")
        if not ia_config.get("status_voz") or not (vc_id := ia_config.get("canal_voz_id")):
            return
        guild_id = member.guild.id
        if after.channel and after.channel.id == vc_id and not member.bot:
            if not self.voice_clients.get(guild_id) or not self.voice_clients[guild_id].is_connected():
                try:
                    vc = await after.channel.connect()
                    self.voice_clients[guild_id] = vc
                    self.audio_recorders[guild_id] = AudioRecorder()
                    print(f"IA conectada ao canal de voz: {after.channel.name}")
                except Exception as e:
                    print(f"Erro ao conectar ao canal de voz da IA: {e}")
        if before.channel and before.channel.id == vc_id:
            vc = self.voice_clients.get(guild_id)
            if vc and vc.is_connected():
                if len(before.channel.members) == 1 and before.channel.members[0].id == self.bot.user.id:
                    await vc.disconnect()
                    if guild_id in self.voice_clients:
                        del self.voice_clients[guild_id]
                    if guild_id in self.audio_recorders:
                        del self.audio_recorders[guild_id]
                    print("IA desconectada do canal de voz por estar vazio.")

    async def temp_call_handler(self, member: disnake.Member, before: disnake.VoiceState, after: disnake.VoiceState):
        config = carregar_json("Database/Comunidade/calltemp.json", {"ativo": False})
        if not config.get("ativo"): return
        if before.channel and before.channel.id in self.active_temp_calls and len(before.channel.members) == 0:
            try:
                await before.channel.delete(reason="Canal temporário vazio.")
                if (text_channel_id := self.active_temp_calls[before.channel.id].get("text_channel_id")) and (text_channel := member.guild.get_channel(text_channel_id)):
                    await text_channel.delete()
                del self.active_temp_calls[before.channel.id]
            except (disnake.NotFound, KeyError): pass
        if not after.channel or after.channel.id != config.get("canal_voz_id"): return
        if not (categoria_id := config.get("categoria_id")) or not (category := member.guild.get_channel(categoria_id)): return
        if (cargo_id := config.get("cargo_id")) and not any(role.id == cargo_id for role in member.roles):
            try: await member.move_to(None, reason="TempCall: Sem permissão de cargo.")
            except disnake.HTTPException: pass
            return
        try:
            temp_vc = await category.create_voice_channel(name=f"Call de {member.display_name}", reason="Canal de Voz Temporário")
            await member.move_to(temp_vc)
            text_channel = None
            if config.get("ativo", False):
                overwrites = { member.guild.default_role: disnake.PermissionOverwrite(read_messages=False), member: disnake.PermissionOverwrite(read_messages=True, send_messages=True) }
                text_channel = await category.create_text_channel(name=f"painel-{member.name.lower()}", overwrites=overwrites, reason="Painel da Call Temporária")
                embed = disnake.Embed(title=f"Painel de Controle - {temp_vc.name}", description="Use o menu abaixo para gerenciar seu canal.", color=disnake.Color.blurple())
                select_menu = disnake.ui.StringSelect(custom_id=f"tempcall_control_{temp_vc.id}", placeholder="Escolha uma opção...", options=[ disnake.SelectOption(label="Mudar Nome", value="rename", emoji="✏️"), disnake.SelectOption(label="Alterar Limite", value="limit", emoji="👥"), disnake.SelectOption(label="Trancar/Destrancar Canal", value="lock", emoji="🔒"),])
                await text_channel.send(member.mention, embed=embed, components=[select_menu])
            self.active_temp_calls[temp_vc.id] = {"owner_id": member.id, "text_channel_id": text_channel.id if text_channel else None}
        except Exception:
            try: await member.move_to(None)
            except disnake.HTTPException: pass

    @commands.Cog.listener("on_dropdown")
    async def temp_call_dropdown_handler(self, inter: disnake.MessageInteraction):
        if not inter.component.custom_id.startswith("tempcall_control_"): return
        vc_id = int(inter.component.custom_id.split('_')[2])
        if vc_id not in self.active_temp_calls or self.active_temp_calls[vc_id]["owner_id"] != inter.author.id:
            return await inter.response.send_message("Você não é o dono desta call ou ela não tem um painel ativo.", ephemeral=True)
        action = inter.values[0]
        if action == "rename": await inter.response.send_modal(title="Novo nome da Call", custom_id=f"tempcall_rename_{vc_id}", components=[disnake.ui.TextInput(label="Nome", custom_id="new_name", required=True)])
        elif action == "limit": await inter.response.send_modal(title="Novo limite de usuários", custom_id=f"tempcall_limit_{vc_id}", components=[disnake.ui.TextInput(label="Limite (0 para ilimitado)", custom_id="new_limit", required=True)])
        elif action == "lock":
            await inter.response.defer(ephemeral=True)
            voice_channel = inter.guild.get_channel(vc_id)
            if not voice_channel: return await inter.followup.send("Call não existe mais.", ephemeral=True)
            current_perms = voice_channel.overwrites_for(inter.guild.default_role)
            if current_perms.connect is False:
                await voice_channel.set_permissions(inter.guild.default_role, connect=None)
                await inter.followup.send("🔓 Canal destrancado.", ephemeral=True)
            else:
                await voice_channel.set_permissions(inter.guild.default_role, connect=False)
                await inter.followup.send("🔒 Canal trancado.", ephemeral=True)

    async def on_form_modal_submit(self, inter: disnake.ModalInteraction):
        form_id = inter.custom_id.replace("submit_form_modal_", "")
        formularios = carregar_json("Database/Comunidade/formularios.json")
        form_data = formularios.get(form_id)
        if not form_data: return await inter.response.send_message("Este formulário não existe mais.", ephemeral=True)
        await inter.response.defer(ephemeral=True)
        questions = form_data.get("perguntas", [])
        answers = [inter.text_values.get(f"form_q_{i}") for i in range(len(questions))]
        await self._enviar_log_formulario(inter.guild, form_id, inter.author, questions, answers)
        await inter.followup.send("✅ Seu formulário foi enviado com sucesso para análise!", ephemeral=True)

    async def on_topic_form_message(self, message: disnake.Message):
        state = self.active_topic_forms[message.author.id]
        try: await message.delete()
        except disnake.Forbidden: pass
        state["answers"].append(message.content)
        state["question_index"] += 1
        formularios = carregar_json("Database/Comunidade/formularios.json")
        form_data = formularios.get(state["form_id"])
        questions = form_data.get("perguntas", [])
        bot_message = await message.channel.fetch_message(state["message_id"])
        if state["question_index"] < len(questions):
            next_question = questions[state["question_index"]]
            embed = bot_message.embeds[0]; embed.title = f"Pergunta {state['question_index'] + 1}/{len(questions)}"; embed.description = next_question
            await bot_message.edit(embed=embed)
        else:
            embed = bot_message.embeds[0]; embed.title = "Formulário Concluído!"; embed.description = "Obrigado! Sua aplicação foi enviada e este tópico será fechado em breve."
            await bot_message.edit(embed=embed, components=None)
            await self._enviar_log_formulario(message.guild, state["form_id"], message.author, questions, state["answers"])
            del self.active_topic_forms[message.author.id]
            await asyncio.sleep(20)
            await message.channel.edit(archived=True, locked=True)

    async def on_form_button_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        if custom_id.startswith("open_form_"):
            parts = custom_id.split('_'); form_type = parts[2]; form_id = parts[3]
            formularios = carregar_json("Database/Comunidade/formularios.json"); form_data = formularios.get(form_id)
            if not form_data or not form_data.get("perguntas"): return await inter.response.send_message("Este formulário não pode ser respondido.", ephemeral=True)
            if form_type == "modal":
                modal_components = [disnake.ui.TextInput(label=pergunta[:45], custom_id=f"form_q_{i}", style=disnake.TextInputStyle.long) for i, pergunta in enumerate(form_data["perguntas"])]
                await inter.response.send_modal(title=form_data.get("embed", {}).get("title", "Formulário")[:45], custom_id=f"submit_form_modal_{form_id}", components=modal_components)
            elif form_type == "topic":
                if inter.author.id in self.active_topic_forms: return await inter.response.send_message("Você já tem um formulário em andamento.", ephemeral=True)
                await inter.response.defer(ephemeral=True)
                try: thread = await inter.channel.create_thread(name=f"Formulário - {inter.author.name}", type=disnake.ChannelType.private_thread)
                except disnake.Forbidden: return await inter.followup.send("Não tenho permissão para criar tópicos aqui.", ephemeral=True)
                embed = disnake.Embed(title="Iniciando Formulário", description=f"Olá {inter.author.mention}, clique abaixo para começar.", color=disnake.Color.green())
                start_button = disnake.ui.Button(label="Começar", style=disnake.ButtonStyle.success, custom_id=f"form_topic_start_{form_id}_{inter.author.id}")
                msg = await thread.send(content=inter.author.mention, embed=embed, components=[start_button])
                self.active_topic_forms[inter.author.id] = {"form_id": form_id, "question_index": 0, "answers": [], "thread_id": thread.id, "message_id": msg.id}
                await inter.followup.send(f"Seu formulário foi iniciado em {thread.mention}!", ephemeral=True)
        elif custom_id.startswith("form_topic_start_"):
            parts = custom_id.split('_'); form_id, user_id = parts[3], int(parts[4])
            if inter.author.id != user_id: return await inter.response.send_message("Este formulário não é para você.", ephemeral=True)
            formularios = carregar_json("Database/Comunidade/formularios.json"); form_data = formularios.get(form_id, {}); questions = form_data.get("perguntas", [])
            if not questions: return await inter.response.edit_message(content="Este formulário não tem perguntas.", embed=None, components=None)
            first_question = questions[0]; embed = inter.message.embeds[0]; embed.title = f"Pergunta 1/{len(questions)}"; embed.description = first_question
            await inter.response.edit_message(embed=embed, components=None)
        elif custom_id.startswith("form_approve_") or custom_id.startswith("form_refuse_"):
            if not verificar_permissao(inter.author.id): return await inter.response.send_message("Você não tem permissão.", ephemeral=True)
            await inter.response.defer()
            parts = custom_id.split('_'); action = parts[1]; form_id = parts[2]; applicant_id = int(parts[3])
            applicant = inter.guild.get_member(applicant_id)
            if not applicant: return await inter.followup.send("Membro não encontrado.", ephemeral=True)
            formularios = carregar_json("Database/Comunidade/formularios.json"); form_data = formularios.get(form_id)
            role_id = form_data.get("cargo_aprovado") if form_data else None; role = inter.guild.get_role(role_id) if role_id else None
            original_embed = inter.message.embeds[0]
            if action == "approve":
                original_embed.color = disnake.Color.green(); original_embed.title = "✅ Formulário APROVADO"
                original_embed.add_field(name="Aprovado por", value=inter.author.mention, inline=False)
                dm_message = "Parabéns! Seu formulário foi aprovado."
                if role:
                    try:
                        await applicant.add_roles(role, reason=f"Aprovado em formulário por {inter.author.name}")
                        dm_message += f" Você recebeu o cargo **{role.name}**."
                    except disnake.Forbidden: await inter.followup.send(f"Não tenho permissão para dar o cargo `{role.name}`.", ephemeral=True)
                try: await applicant.send(dm_message)
                except disnake.Forbidden: pass
            else:
                original_embed.color = disnake.Color.red(); original_embed.title = " Formulário RECUSADO"
                original_embed.add_field(name="Recusado por", value=inter.author.mention, inline=False)
                try: await applicant.send("Infelizmente seu formulário foi recusado.")
                except disnake.Forbidden: pass
            await inter.message.edit(embed=original_embed, components=None)
            await inter.followup.send("Ação concluída.", ephemeral=True)

    async def _enviar_log_formulario(self, guild, form_id, applicant, questions, answers):
        canais = ObterCanais()
        log_channel_id = canais.get("logsformulario")
        if not log_channel_id: return
        log_channel = guild.get_channel(int(log_channel_id))
        if not log_channel: return
        embed = disnake.Embed(title="📝 Novo Formulário Recebido", color=disnake.Color.blue())
        embed.set_author(name=f"{applicant.name} ({applicant.id})", icon_url=applicant.display_avatar.url)
        embed.set_thumbnail(url=applicant.display_avatar.url)
        for i, question in enumerate(questions):
            answer = answers[i] if i < len(answers) else "Não respondido"
            embed.add_field(name=f"❓ {question}", value=f"```\n{answer}\n```", inline=False)
        embed.set_footer(text=f"ID do Formulário: {form_id}")
        components = [disnake.ui.Button(label="Aprovar", style=disnake.ButtonStyle.success, custom_id=f"form_approve_{form_id}_{applicant.id}"), disnake.ui.Button(label="Recusar", style=disnake.ButtonStyle.danger, custom_id=f"form_refuse_{form_id}_{applicant.id}")]
        await log_channel.send(embed=embed, components=components)

    async def handle_key_redemption(self, message: disnake.Message):
        key_attempt = message.content.strip()
        config, all_keys = carregar_json("Database/Comunidade/keys.json"), carregar_json("Database/Comunidade/generated_keys.json", [])
        log_channel = self.bot.get_channel(config.get("canal_logs_id"))
        await message.delete()
        if key_attempt in all_keys:
            if not (role := message.guild.get_role(config.get("cargo_id"))): return
            try:
                await message.author.add_roles(role, reason=f"Resgate de Key")
                all_keys.remove(key_attempt); salvar_json("Database/Comunidade/generated_keys.json", all_keys)
                await message.channel.send(f"✅ Key resgatada! Você recebeu o cargo **{role.name}**.", delete_after=5)
                if log_channel: await log_channel.send(f"🔑 **Resgate (Sucesso)** | {message.author.mention} | `{key_attempt}` | {role.mention}")
            except disnake.Forbidden: pass
        else:
            await message.channel.send(f"{message.author.mention}, a key informada é inválida.", delete_after=5)
            if log_channel: await log_channel.send(f"⚠️ **Tentativa (Falha)** | {message.author.mention} | `{key_attempt}`")

    async def handle_instagram_post(self, message: disnake.Message):
        config = carregar_json("Database/Comunidade/instagram.json")
        prefix = config.get("prefixo", "ig!")
        target_channel_id = config.get("canal_id")
        if not target_channel_id: return
        target_channel = self.bot.get_channel(target_channel_id)
        if not target_channel: return
        if (cargo_id := config.get("cargo_id")) and not any(r.id == cargo_id for r in message.author.roles): return
        if not message.attachments: return
        webhooks = await target_channel.webhooks()
        webhook = disnake.utils.find(lambda w: w.name == self.bot.user.name, webhooks) or await target_channel.create_webhook(name=self.bot.user.name)
        tema = config.get("tema", "vermelho")
        emojis = EMOJIS_TEMAS_INSTAGRAM.get(tema, EMOJIS_TEMAS_INSTAGRAM["vermelho"])
        legenda = message.content.replace(f"{prefix}post", "", 1).strip()
        components = [disnake.ui.Button(label="0", emoji=emojis["like"], custom_id=f"ig_like_{message.id}"), disnake.ui.Button(label="Comentar", emoji=emojis["comment"], custom_id=f"ig_comment_{message.id}"), disnake.ui.Button(label="Instagram", emoji=emojis["profile"], custom_id=f"ig_profile_{message.id}"), disnake.ui.Button(label="Info", emoji=emojis["info"], custom_id=f"ig_info_{message.id}"), disnake.ui.Button(label="Deletar", emoji=emojis["delete"], custom_id=f"ig_delete_{message.id}")]
        try:
            sent_message = await webhook.send(content=f"{message.author.mention} {legenda}", file=await message.attachments[0].to_file(), username=message.author.display_name, avatar_url=message.author.display_avatar.url, components=components, wait=True)
            posts_db = carregar_json("Database/Instagram/posts.json"); posts_db[str(message.id)] = {"author_id": message.author.id, "webhook_msg_id": sent_message.id, "likes": [], "comments": [], "tema": tema}; salvar_json("Database/Instagram/posts.json", posts_db)
            await message.delete()
        except Exception: pass

    async def handle_instagram_link(self, message: disnake.Message):
        prefix = carregar_json("Database/Comunidade/instagram.json").get("prefixo", "ig!")
        args = message.content.replace(f"{prefix}vincular", "", 1).strip().split()
        if not args: return
        url = args[0]
        if not (match := re.match(r"(?:https?:\/\/)?(?:www\.)?instagram\.com\/([a-zA-Z0-9_.]+)\/?", url)): return
        try:
            async with self.session.get(f"https://www.instagram.com/{match.group(1)}/?__a=1&__d=dis") as r:
                if r.status == 200:
                    vinculos = carregar_json("Database/Instagram/vinculos.json"); vinculos[str(message.author.id)] = url; salvar_json("Database/Instagram/vinculos.json", vinculos)
                    await message.reply(f"✅ Perfil do Instagram vinculado!")
        except Exception: pass

    async def instagram_button_handler(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        action = custom_id.split("_")[1]
        original_message_id = custom_id.split("_")[2]
        if action == "comment":
            return await inter.response.send_modal(title="Adicionar Comentário", custom_id=f"ig_comment_modal_{original_message_id}", components=[disnake.ui.TextInput(label="Seu Comentário", custom_id="comment_text", style=disnake.TextInputStyle.paragraph, required=True)])
        await inter.response.defer()
        posts_db = carregar_json("Database/Instagram/posts.json"); post_data = posts_db.get(original_message_id)
        if not post_data: return await inter.followup.send("Post não encontrado.", ephemeral=True)
        if action == "like":
            if inter.author.id in post_data["likes"]: post_data["likes"].remove(inter.author.id)
            else: post_data["likes"].append(inter.author.id)
            salvar_json("Database/Instagram/posts.json", posts_db)
            tema = post_data.get("tema", "vermelho")
            emojis = EMOJIS_TEMAS_INSTAGRAM.get(tema, EMOJIS_TEMAS_INSTAGRAM["vermelho"])
            new_components = [ disnake.ui.Button(label=str(len(post_data['likes'])), emoji=emojis["like"], custom_id=f"ig_like_{original_message_id}"), disnake.ui.Button(label="Comentar", emoji=emojis["comment"], custom_id=f"ig_comment_{original_message_id}"), disnake.ui.Button(label="Instagram", emoji=emojis["profile"], custom_id=f"ig_profile_{original_message_id}"), disnake.ui.Button(label="Info", emoji=emojis["info"], custom_id=f"ig_info_{original_message_id}"), disnake.ui.Button(label="Deletar", emoji=emojis["delete"], custom_id=f"ig_delete_{original_message_id}")]
            await inter.edit_original_message(components=new_components)
        elif action == "profile":
            if (profile_url := carregar_json("Database/Instagram/vinculos.json").get(str(post_data["author_id"]))): await inter.followup.send(f"Perfil do autor: {profile_url}", ephemeral=True)
            else: await inter.followup.send("Autor não vinculou um perfil.", ephemeral=True)
        elif action == "info":
            embed = disnake.Embed(title="Informações do Post", color=disnake.Color.blurple()).add_field(name="Curtidas", value=str(len(post_data["likes"])), inline=False)
            comments_text = "\n".join([f"**{c['author']}**: {c['text']}" for c in post_data["comments"]]) if post_data["comments"] else "Nenhum comentário."
            embed.add_field(name="Comentários", value=comments_text[:1024], inline=False)
            await inter.followup.send(embed=embed, ephemeral=True)
        elif action == "delete":
            if inter.author.id != post_data["author_id"] and not verificar_permissao(inter.author.id): return await inter.followup.send("Você não pode deletar este post.", ephemeral=True)
            await inter.message.delete()
            del posts_db[original_message_id]; salvar_json("Database/Instagram/posts.json", posts_db)
            await inter.followup.send("Post deletado.", ephemeral=True, delete_after=3)

    async def instagram_modal_handler(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)
        original_message_id = inter.custom_id.replace("ig_comment_modal_", "")
        posts_db = carregar_json("Database/Instagram/posts.json")
        if not (post_data := posts_db.get(original_message_id)): return
        post_data["comments"].append({"author": inter.author.display_name, "author_id": inter.author.id, "text": inter.text_values["comment_text"]}); salvar_json("Database/Instagram/posts.json", posts_db)
        await inter.followup.send("Comentário adicionado!")

    async def temp_call_modal_handler(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)
        vc_id = int(inter.custom_id.split('_')[2])
        if vc_id not in self.active_temp_calls or self.active_temp_calls[vc_id]["owner_id"] != inter.author.id: return
        if not (voice_channel := inter.guild.get_channel(vc_id)): return
        action = inter.custom_id.split('_')[1]
        if action == "rename":
            await voice_channel.edit(name=inter.text_values["new_name"]); await inter.followup.send(f"Nome alterado.", ephemeral=True)
        elif action == "limit":
            try:
                new_limit = int(inter.text_values["new_limit"])
                if not 0 <= new_limit <= 99: raise ValueError
                await voice_channel.edit(user_limit=new_limit); await inter.followup.send(f"Limite alterado.", ephemeral=True)
            except ValueError: await inter.followup.send("Insira um número válido (0-99).", ephemeral=True)

def setup(bot: commands.Bot):
    bot.add_cog(CogComunidade(bot))
