# app.py
from flask import Flask, jsonify, request # 1. Agregamos jsonify
from flask_cors import CORS
import openai
import os
from dotenv import load_dotenv
from src import config # 2. IMPORTACIÓN CRUCIAL: Traemos el interruptor

# 1. CARGAR VARIABLES DE ENTORNO PRIMERO
load_dotenv()

# 2. CONFIGURAR OPENAI PARA GROQ
api_key = os.getenv("KEY03")
if not api_key:
    print("❌ ERROR: KEY03 no encontrada en .env")
    exit(1)

openai.api_key = api_key
openai.api_base = "https://api.groq.com/openai/v1"
print(f"✅ OpenAI configurado. Base URL: {openai.api_base}")

# 3. INICIAR FLASK
app = Flask(__name__)
CORS(app)

# 4. IMPORTAR RUTAS
from src.routes import evaluar_apartado_route, analizar_taller_completo_route

# Registrar rutas
@app.route('/evaluar_apartado', methods=['POST'])
def evaluar_wrapper():
    config.evaluacion_activa = True # 3. Encendemos el interruptor al iniciar cada evaluación
    return evaluar_apartado_route()

app.route('/analizar_taller_completo', methods=['POST'])(analizar_taller_completo_route)

@app.route('/cancelar', methods=['POST'])
def cancelar():
    # Ahora 'config' sí está definido gracias al import de arriba
    config.evaluacion_activa = False 
    print("\n🛑 FRENO DE MANO: Deteniendo evaluación en el próximo indicador...")
    return jsonify({"status": "success", "message": "Señal de detención enviada"}), 200

# ... (Tus rutas de index y health check igual)

@app.route('/reset', methods=['POST'])
def reset_backend():
    print("\n♻️  REINICIO LÓGICO SOLICITADO")
    print("Limpiando memoria del backend...")
    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)