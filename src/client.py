# src/client.py - VERSIÓN CORRECTA para openai==0.28.1
# src/client.py - NUEVA VERSIÓN como helper
import os
from dotenv import load_dotenv
import openai

load_dotenv()

def configurar_openai():
    """Configurar OpenAI para Groq"""
    api_key = os.getenv("KEY03")
    if not api_key:
        raise ValueError("KEY03 no encontrada en .env")
    
    openai.api_key = api_key
    openai.api_base = "https://api.groq.com/openai/v1"
    return openai

# Llamar esta función al inicio
configurar_openai()