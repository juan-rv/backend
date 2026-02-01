import json
import openai
import os
import time
from dotenv import load_dotenv

# --- CONFIGURACIÓN ---
load_dotenv()
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
api_key = os.getenv("KEY03")

# Configurar openai para Groq
openai.api_key = api_key
openai.api_base = "https://api.groq.com/openai/v1"

print(f"✅ OpenAI configurado para feedback. Base URL: {openai.api_base}")

# --- HELPER: LLAMADA SEGURA (VERSIÓN ROBUSTA) ---
def llamada_segura_feedback(messages, model="llama-3.1-8b-instant", temperature=0.2, retries=5):
    """
    Intenta llamar a Groq manejando Rate Limits con una espera agresiva.
    Garantiza cubrir >60 segundos para reiniciar la ventana de tokens.
    """
    for i in range(retries):
        try:
            comp = openai.ChatCompletion.create(
                model=model,
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_object"}
            )
            return comp
        except openai.error.RateLimitError:
            # Espera agresiva: 10s, 20s, 30s, 40s, 50s
            # Esto permite "sobrevivir" al bloqueo de 1 minuto de Groq
            wait_time = (i + 1) * 10 
            print(f"⚠️ Rate Limit en Feedback (Intento {i+1}/{retries}). Pausando {wait_time}s para liberar cupo...")
            time.sleep(wait_time)
        except Exception as e:
            print(f"❌ Error desconocido en Feedback: {str(e)}")
            return None
    
    print("❌ Se agotaron los reintentos (incluso tras esperar >2 min).")
    return None

# --- FUNCIONES PRINCIPALES ---

def generar_comentario_global(objetivo, evaluaciones, perfil_edad, tipo="objetivo"):
    """
    Genera un análisis cualitativo (Pros/Contras) sin dar órdenes directas.
    Maneja reintentos robustos.
    """
    # Filtramos los puntos débiles (Notas 1, 2 y 3)
    puntos_debiles = [
        f"- {ev['indicador']} ({ev['calificacion']}/5): {ev['analisis'].get('razonamiento', '')}"
        for ev in evaluaciones if ev['calificacion'] <= 3
    ]
    
    # Construcción del prompt
    if not puntos_debiles:
        if tipo == "actividad":
            prompt_feedback = f'''
            La actividad "{objetivo[:200]}..." presenta un diseño pedagógico excelente para {perfil_edad}.
            Redacta una observación breve destacando su valor como estrategia educativa.
            Responde en JSON: {{"comentario_general": "..."}}
            '''
        else:
            prompt_feedback = f'''
            El objetivo "{objetivo}" presenta una alineación técnica excelente con el modelo y la edad {perfil_edad}.
            Redacta una observación breve destacando la coherencia pedagógica lograda.
            Responde en JSON: {{"comentario_general": "..."}}
            '''
    else:
        txt_debiles = "\n".join(puntos_debiles)
        
        if tipo == "actividad":
            prompt_feedback = f'''
            ACTÚA COMO UN EXPERTO EN PEDAGOGÍA CONSTRUCTIVISTA. 
            Analiza con rigor técnico y claridad la actividad: "{objetivo[:300]}..." 
            Destinatarios: {perfil_edad}
            Hallazgos técnicos detectados: {txt_debiles}

            GUÍA DE ESTILO Y REDACCIÓN (ESTRICTO):
            1. TONO: Firme, profesional y propositivo. Elimina verbos de duda como "parece", "podría" o "tal vez". Sé asertivo.
            2. SIN ETIQUETAS: Está prohibido usar encabezados, listas, viñetas o títulos como "Fortalezas" o "Oportunidades".
            3. ESTRUCTURA DE DOS PÁRRAFOS:
               - Párrafo 1: Valora la elección de la metodología o los recursos (ej. uso de objetos concretos) y explica por qué son efectivos para la psicología de {perfil_edad}.
               - Párrafo 2: Identifica el riesgo pedagógico de los hallazgos técnicos (notas bajas) y sugiere una evolución específica. No solo digas qué falta, di cómo implementarlo para elevar la calidad.
            4. ECONOMÍA DEL LENGUAJE: No repitas ideas. Si mencionas un ajuste, no vuelvas a él. Evita muletillas de relleno y no menciones el tema del taller más de una vez.

            FORMATO JSON DE RESPUESTA:
            {{
                "comentario_general": "[Tu análisis fluido aquí, separando los dos párrafos con \\n\\n]"
            }}
            '''
        else:
            prompt_feedback = f'''
            ACTÚA COMO UN EXPERTO EN PEDAGOGÍA.
            Analiza la estructura técnica del siguiente contenido para la audiencia: {perfil_edad}.

            DATOS:
            - Texto original: "{objetivo}"
            - Hallazgos técnicos: {txt_debiles}

            INSTRUCCIONES DE ESTILO (CRÍTICO):
            1. REDACCIÓN: Escribe un único texto narrativo y fluido de dos párrafos. 
            2. PROHIBICIONES: 
               - NO uses títulos, encabezados ni etiquetas como "LO QUE FUNCIONA" o "FORTALEZAS".
               - NO uses listas con viñetas o guiones.
               - NO repitas el tema del taller como muletilla.
            3. ESTRUCTURA DEL TEXTO:
               - Párrafo 1: Analiza la propuesta desde la intención pedagógica y su valor para {perfil_edad}.
               - Párrafo 2: Integra los hallazgos técnicos (notas bajas) como recomendaciones de mejora profesional, explicando QUÉ falta técnicamente (ej. falta de criterios, objetivos difusos, etc.).

            FORMATO JSON DE RESPUESTA:
            {{
                "comentario_general": "[Inserta aquí solo el texto fluido, usando \\n\\n entre párrafos]"
            }}
            '''
    # Usamos la llamada segura
    print("⏳ Generando feedback global (esto puede tardar si hay congestión)...")
    comp = llamada_segura_feedback(
        messages=[{"role": "user", "content": prompt_feedback}],
        temperature=0.1,
        retries=5 # Aseguramos 5 intentos
    )

    if comp:
        try:
            return json.loads(comp.choices[0].message.content)
        except Exception as e:
            return {"comentario_general": f"Error procesando JSON: {str(e)}"}
    else:
        return {"comentario_general": "No se pudo generar el análisis global (Rate Limit persistente)."}

def generar_comentario_actividad(actividad, evaluaciones, perfil_edad):
    """
    Versión alternativa para actividades.
    """
    puntos_debiles = [
        f"- {ev['indicador']} ({ev['calificacion']}/5): {ev['analisis'].get('razonamiento', '')}"
        for ev in evaluaciones if ev['calificacion'] <= 3
    ]
    
    if not puntos_debiles:
        prompt_feedback = f'''
        La actividad "{actividad[:200]}..." es excelente para {perfil_edad}.
        Redacta comentario positivo breve.
        Responde en JSON: {{"comentario_general": "..."}}
        '''
    else:
        txt_debiles = "\n".join(puntos_debiles)
        prompt_feedback = f'''
        ACTÚA COMO UN EXPERTO EN DISEÑO DE ACTIVIDADES.
        ANALIZA: "{actividad[:300]}..." para {perfil_edad}.
        MEJORAR: {txt_debiles}
        
        GENERAR FEEDBACK (Valor, Optimización, Recomendaciones).
        
        FORMATO JSON:
        {{
            "comentario_general": "VALOR: [...]. OPTIMIZACIÓN: [...]. RECOMENDACIONES: [...]."
        }}
        '''
    
    print("⏳ Generando feedback de actividad...")
    comp = llamada_segura_feedback(
        messages=[{"role": "user", "content": prompt_feedback}],
        temperature=0.2,
        retries=5
    )
    
    if comp:
        try:
            return json.loads(comp.choices[0].message.content)
        except Exception as e:
            return {"comentario_general": f"Error JSON actividad: {str(e)}"}
    else:
        return {"comentario_general": "No se pudo generar feedback de actividad."}