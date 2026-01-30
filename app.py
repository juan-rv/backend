# app.py - VERSIÓN COMPLETA CON AMBAS RUTAS
from flask import Flask
from flask_cors import CORS
import openai
import os
from dotenv import load_dotenv

# 1. CARGAR VARIABLES DE ENTORNO PRIMERO
load_dotenv()

# 2. CONFIGURAR OPENAI PARA GROQ
api_key = os.getenv("KEY03")
if not api_key:
    print("❌ ERROR: KEY03 no encontrada en .env")
    print("   Asegúrate de tener un archivo .env con: KEY03=tu_api_key")
    exit(1)

openai.api_key = api_key
openai.api_base = "https://api.groq.com/openai/v1"
print(f"✅ OpenAI configurado. Base URL: {openai.api_base}")

# 3. INICIAR FLASK
app = Flask(__name__)
CORS(app)

# 4. IMPORTAR RUTAS DESPUÉS de configurar OpenAI
# Importar AMBAS funciones de routes.py
from src.routes import evaluar_apartado_route, analizar_taller_completo_route

# Registrar AMBAS rutas
app.route('/evaluar_apartado', methods=['POST'])(evaluar_apartado_route)
app.route('/analizar_taller_completo', methods=['POST'])(analizar_taller_completo_route)  # ← NUEVA

# (Opcional) Añadir una ruta de prueba/health check
@app.route('/')
def index():
    return {
        "status": "online",
        "service": "API de Análisis Pedagógico",
        "endpoints": [
            {
                "path": "/evaluar_apartado",
                "method": "POST",
                "description": "Evaluar un apartado individual (introducción, objetivo o actividad)"
            },
            {
                "path": "/analizar_taller_completo",
                "method": "POST",
                "description": "Analizar resultados completos de un taller"
            }
        ]
    }

@app.route('/health', methods=['GET'])
def health_check():
    return {"status": "healthy", "service": "pedagogical-analysis"}

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 SERVICIO DE ANÁLISIS PEDAGÓGICO")
    print("=" * 50)
    print("📌 Endpoints activos:")
    print("   POST /evaluar_apartado")
    print("   POST /analizar_taller_completo")
    print("   GET  /health")
    print("   GET  /")
    print("\n🔗 URL: http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, port=5000)