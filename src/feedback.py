import json
import openai  # ← Solo importar openai, NO OpenAI
import os
from dotenv import load_dotenv

# --- CONFIGURACIÓN (CÓDIGO EXISTENTE - MODIFICAR) ---
load_dotenv()
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
api_key = os.getenv("KEY03")

# Configurar openai para Groq (v0.28.1) - SIN crear 'client'
openai.api_key = api_key
openai.api_base = "https://api.groq.com/openai/v1"

print(f"✅ OpenAI configurado para feedback. Base URL: {openai.api_base}")

# --- EL RESTO DEL CÓDIGO PERMANECE IGUAL ---
def generar_comentario_global(objetivo, evaluaciones, perfil_edad, tipo="objetivo"):
    """
    Genera un análisis cualitativo (Pros/Contras) sin dar órdenes directas.
    tipo: "objetivo" o "actividad" - para adaptar el prompt
    """
    # Filtramos los puntos débiles (Notas 1, 2 y 3)
    puntos_debiles = [
        f"- {ev['indicador']} ({ev['calificacion']}/5): {ev['analisis'].get('razonamiento', '')}"
        for ev in evaluaciones if ev['calificacion'] <= 3
    ]
    
    # Si todo es perfecto
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
        # Si hay brechas, hacemos un análisis observacional
        txt_debiles = "\n".join(puntos_debiles)
        
        if tipo == "actividad":
            prompt_feedback = f'''
            ACTÚA COMO UN DISEÑADOR INSTRUCCIONAL REFLEXIVO.
            Tu tono debe ser OBSERVACIONAL y CONSULTIVO, nunca imperativo. 
            No le digas al usuario qué hacer (evita "cambia", "agrega", "debes").
            En su lugar, señala las características observadas en la ACTIVIDAD.

            DATOS A ANALIZAR:
            - Actividad: "{objetivo[:300]}..."
            - Etapa Cognitiva: {perfil_edad}
            - Brechas detectadas: {txt_debiles}

            TU TAREA:
            Redactar un único análisis integrado que cubra tres dimensiones ESPECÍFICAS PARA ACTIVIDADES:
            1. FORTALEZAS COMO ESTRATEGIA: Qué valor tiene esta actividad como método de enseñanza en relación con el modelo pedagógico y la edad.
            2. BRECHAS EN IMPLEMENTACIÓN: Observación sobre aspectos que podrían mejorarse en el diseño o ejecución de la actividad.
            3. OPORTUNIDAD PEDAGÓGICA: Qué valor educativo se ganaría si se optimizaran estos aspectos en la actividad.

            FORMATO JSON DE RESPUESTA:
            {{
                "comentario_general": "FORTALEZAS COMO ESTRATEGIA: [Texto]. BRECHAS EN IMPLEMENTACIÓN: [Texto analítico sobre modelo y edad]. OPORTUNIDAD PEDAGÓGICA: [Texto]."
            }}
            '''
        else:
            prompt_feedback = f'''
            ACTÚA COMO UN ANALISTA PEDAGÓGICO REFLEXIVO.
            Tu tono debe ser OBSERVACIONAL y CONSULTIVO, nunca imperativo. 
            No le digas al usuario qué hacer (evita "cambia", "agrega", "debes").
            En su lugar, señala las características observadas.

            DATOS A ANALIZAR:
            - Objetivo: "{objetivo}"
            - Etapa Cognitiva: {perfil_edad}
            - Brechas detectadas: {txt_debiles}

            TU TAREA:
            Redactar un único análisis integrado que cubra tres dimensiones:
            1. FORTALEZAS (Pros): Qué valor tiene la temática o la intención del objetivo en relación con el modelo pedagógico y la edad.
            2. BRECHAS (Contras): Observación sobre la desconexión con el Modelo Pedagógico y la Edad. Explica la "Razón Pedagógica" de la brecha.
            3. OPORTUNIDAD: Qué valor pedagógico se ganaría si se alinearan estos aspectos.

            FORMATO JSON DE RESPUESTA:
            {{
                "comentario_general": "FORTALEZAS: [Texto]. BRECHAS OBSERVADAS: [Texto analítico sobre modelo y edad]. OPORTUNIDAD: [Texto]."
            }}
            '''

    try:
        comp = openai.ChatCompletion.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt_feedback}],
            temperature=0.2, 
            response_format={"type": "json_object"}
        )
        return json.loads(comp.choices[0].message.content)
    except Exception as e:
        return {"comentario_general": "No se pudo generar el análisis global."}

# --- NUEVA FUNCIÓN ESPECÍFICA PARA ACTIVIDADES (AÑADIR) ---
def generar_comentario_actividad(actividad, evaluaciones, perfil_edad):
    """
    Genera feedback específico para actividades educativas.
    Versión alternativa a generar_comentario_global() pero solo para actividades.
    """
    # Filtramos los puntos débiles (Notas 1, 2 y 3)
    puntos_debiles = [
        f"- {ev['indicador']} ({ev['calificacion']}/5): {ev['analisis'].get('razonamiento', '')}"
        for ev in evaluaciones if ev['calificacion'] <= 3
    ]
    
    # Si todo es perfecto
    if not puntos_debiles:
        prompt_feedback = f'''
        La actividad "{actividad[:200]}..." muestra un diseño pedagógico excelente para {perfil_edad}.
        
        Como especialista en diseño instruccional, redacta un comentario breve que destaque:
        - Su valor como estrategia de enseñanza
        - Su adecuación a la edad de los estudiantes
        - Su potencial para promover aprendizaje significativo
        
        Responde en JSON: {{"comentario_general": "..."}}
        '''
    else:
        # Si hay aspectos a mejorar
        txt_debiles = "\n".join(puntos_debiles)
        
        prompt_feedback = f'''
        ACTÚA COMO UN EXPERTO EN DISEÑO DE ACTIVIDADES EDUCATIVAS.
        
        ANALIZA ESTA ACTIVIDAD:
        - Descripción: "{actividad[:300]}..."
        - Para estudiantes de: {perfil_edad}
        - Aspectos identificados para mejorar: {txt_debiles}
        
        PROPORCIONA UN ANÁLISIS CONSTRUCTIVO EN 3 PARTES:
        
        1. VALOR INTRÍNSECO DE LA ACTIVIDAD:
           ¿Qué aspectos positivos tiene como estrategia educativa?
           ¿Cómo se relaciona con buenas prácticas pedagógicas?
        
        2. ÁREAS DE OPTIMIZACIÓN:
           ¿Qué elementos del diseño podrían mejorarse?
           ¿Cómo afecta esto la experiencia de aprendizaje?
        
        3. RECOMENDACIONES PARA EL DISEÑO:
           ¿Qué ajustes sugerirías para maximizar su impacto pedagógico?
           ¿Cómo podría convertirse en una actividad aún más efectiva?
        
        FORMATO DE RESPUESTA (JSON):
        {{
            "comentario_general": "VALOR INTRÍNSECO: [texto]. ÁREAS DE OPTIMIZACIÓN: [texto]. RECOMENDACIONES PARA EL DISEÑO: [texto]."
        }}
        '''
    
    try:
        comp = openai.ChatCompletion.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt_feedback}],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        return json.loads(comp.choices[0].message.content)
    except Exception as e:
        return {"comentario_general": f"No se pudo generar feedback para actividad: {str(e)}"}