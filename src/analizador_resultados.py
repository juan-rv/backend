import json
import openai
import time  # <--- CRUCIAL para las esperas



def analizar_resultados_taller(resultados, perfil_edad="No especificado"):
    """
    Ahora recibe 'perfil_edad' desde la ruta.
    """
    datos_extraidos = extraer_datos_resultados(resultados)
    
    if datos_extraidos['tiene_datos_suficientes']:
        # PASAMOS el perfil_edad a la siguiente función
        return generar_sintesis_final(datos_extraidos, perfil_edad)
    else:
        return {"error": "Datos insuficientes para análisis integrado"}

def extraer_datos_resultados(resultados):
    print("\n--- 🔍 DEPURACIÓN DE EXTRACCIÓN ---")
    
    # El payload ahora viene dentro de una llave llamada 'evaluaciones'
    # o directamente en la raíz. Vamos a normalizar:
    evals = resultados.get('evaluaciones', resultados)
    print(f"Llaves detectadas: {list(evals.keys())}")

    datos = {
        "titulo": "Taller analizado",
        "introduccion": {},
        "objetivo": {},
        "actividades": [],
        "tiene_datos_suficientes": False,
        "metricas_totales": {}
    }
    
    # 1. BUSCAR INTRODUCCIÓN (Flexible)
    llave_intro = next((k for k in evals.keys() if "introducc" in k.lower()), None)
    if llave_intro and evals[llave_intro]:
        intro = evals[llave_intro]
        # Verificamos que sea un diccionario antes de usar .get()
        if isinstance(intro, dict):
            datos['introduccion'] = {
                "valoracion": intro.get('analisis_disciplinar', '')[:300],
                "frases_clave": intro.get('frases_discurso', []),
                "tiene_contenido": True
            }
            print("✅ Introducción procesada.")
    
    # 2. BUSCAR OBJETIVO
    llave_obj = next((k for k in evals.keys() if "objetivo" in k.lower()), None)
    if llave_obj and evals[llave_obj]:
        obj = evals[llave_obj]
        if isinstance(obj, dict):
            datos['objetivo'] = {
                "texto": obj.get('apartado', 'Objetivo'),
                "promedio": obj.get('estadisticas', {}).get('promedio', 0),
                "evaluaciones": obj.get('evaluaciones', [])[:3]
            }
            print(f"✅ Objetivo procesado. Nota: {datos['objetivo']['promedio']}")
    
    # 3. BUSCAR ACTIVIDADES (Manejo de Lista o Diccionario)
    # Aquí es donde fallaba: 'actividades' es una LISTA enviada desde React
    lista_actividades_raw = evals.get('actividades', [])
    
    if isinstance(lista_actividades_raw, list):
        for act in lista_actividades_raw:
            if isinstance(act, dict):
                datos['actividades'].append({
                    "nombre": act.get('apartado', 'Actividad'),
                    "promedio": act.get('estadisticas', {}).get('promedio', 0),
                    "feedback": act.get('feedback_global', {}).get('comentario_general', '')[:150]
                })
    
    print(f"✅ Actividades procesadas: {len(datos['actividades'])}")

    # --- VALIDACIÓN DE SALIDA ---
    # Si hay objetivo o actividades con nota, hay datos suficientes
    if datos['objetivo'].get('promedio', 0) > 0 or len(datos['actividades']) > 0:
        datos['tiene_datos_suficientes'] = True
        print("🚀 RESULTADO: Datos SUFICIENTES.")
    else:
        print("❌ RESULTADO: Datos INSUFICIENTES.")
        
    return datos

# --- HELPER: LLAMADA SEGURA PARA EL INFORME FINAL ---
def llamada_segura_informe(messages, model="llama-3.1-8b-instant", temperature=0.1, max_tokens=2000, retries=5):
    """
    Intenta generar el informe manejando Rate Limits con esperas largas.
    """
    for i in range(retries):
        try:
            comp = openai.ChatCompletion.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"} # Forzamos JSON siempre
            )
            return comp
        except openai.error.RateLimitError:
            # Esperas progresivas: 10s, 20s, 30s, 40s, 50s
            wait_time = (i + 1) * 10 
            print(f"⚠️ Rate Limit en Informe Final (Intento {i+1}/{retries}). Pausando {wait_time}s...")
            time.sleep(wait_time)
        except Exception as e:
            print(f"❌ Error desconocido en Informe Final: {str(e)}")
            return None
    
    print("❌ Se agotaron los reintentos para el informe final.")
    return None

def generar_sintesis_final(datos_extraidos, perfil_edad="No especificado"):
    """
    Genera el informe final usando la llamada segura.
    """
    
    prompt = f'''
    ERES UN EXPERTO EN PEDAGOGÍA. Tu misión es redactar un INFORME TÉCNICO EXHAUSTIVO.
    Busco un análisis de ALTA VERBOSIDAD y PROFUNDIDAD.
    
    --- DATOS DE AUDITORÍA ---
    TALLER: {datos_extraidos['titulo']}
    POBLACIÓN: {perfil_edad}
    OBJETIVO: "{datos_extraidos['objetivo'].get('texto', 'N/A')}" (Nota: {datos_extraidos['objetivo'].get('promedio', 'N/A')})
    INTRODUCCIÓN (Sustento bibliográfico para el Guía): {datos_extraidos['introduccion'].get('valoracion', 'N/A')}
    ACTIVIDADES: {formatear_actividades(datos_extraidos['actividades'])}
    
    --- REGLAS DE OBLIGATORIO CUMPLIMIENTO---
    1. No repitas ideas ya expresadas en otros apartados.NO SEAS REDUNDANTE.
    2. NATURALEZA DE LA INTRODUCCIÓN: No la evalúes como material didáctico para el estudiante. Es NETAMENTE BIBLIOGRÁFICA Y DE APOYO PARA EL MEDIADOR O GUÍA, DIME CUALES SON LAS FORTALEZAS QUE APORTAN AL TALLER.
    3. COHERENCIA ESTRATÉGICA: Evalúa el binomio OBJETIVO-ACTIVIDAD como un hilo conductor. ¿la actividad y el objetivo tienen relación? Evita analizar las piezas como islas; analízalas como un sistema.
    4. CONTROL DE REDUNDANCIA: Está estrictamente prohibido repetir frases o diagnósticos entre la 'SÍNTESIS', el 'DIAGNÓSTICO' y las 'FORTALEZAS'. Cada sección debe aportar una perspectiva nueva. 
    5. SÍNTESIS GENERAL: Mínimo 200 palabras. No resumas lo que ya leí; analiza la RELACIÓN ENTRE EL MODELO, OBJETIVO y el impacto en {perfil_edad}.
    6. FORMATO: Responde EXCLUSIVAMENTE en un objeto JSON válido. Usa "\\n" para saltos de línea.

    --- FORMATO JSON ESPERADO ---
    {{
        "analisis_final": {{
            "sintesis_ejecutiva": "Ensayo extenso sobre la solidez del taller y el dominio técnico del facilitador...",
            "diagnostico_coherencia": "Análisis minucioso sobre si la ación propuesta cumple con la promesa del objetivo...",
           
            "ruta_de_accion": [
                {{ 
                   "estrategia": "Técnica pedagógica concreta, aporta ideas TENIENDO EN CUENTA el perfil {perfil_edad}...", 
                   "fundamentacion": "Vínculo con {perfil_edad}...",
            ]
        }},
        "metricas_consolidadas": {{
            "promedio": {datos_extraidos['metricas_totales'].get('promedio_general', 0)},
            "estado": "Cualificación cualitativa del ecosistema pedagógico"
        }}
    }}
    '''
    print("⏳ Generando Informe Final con IA (puede tardar por congestión)...")
    
    # Usamos la nueva llamada segura
    response = llamada_segura_informe(
        messages=[
            {"role": "system", "content": "Eres un analista pedagógico conciso y práctico que responde en JSON."},
            {"role": "user", "content": prompt}
        ]
    )
        
    if response:
        try:
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Error parseando JSON final: {e}")
            return generar_analisis_simple(datos_extraidos)
    else:
        # Si fallan todos los reintentos, ahí sí usamos el fallback
        return generar_analisis_simple(datos_extraidos)

def formatear_actividades(actividades):
    """Formatea información de actividades para el prompt"""
    texto = ""
    for i, act in enumerate(actividades, 1):
        texto += f"\n{i}. {act.get('nombre', 'Actividad')}\n"
        texto += f"   - Nota: {act.get('promedio', 'N/A')}/5\n"
        texto += f"   - Feedback previo: {act.get('feedback', 'Sin feedback')}\n"
    return texto

def generar_analisis_simple(datos):
    """Análisis simple (FALLBACK) si falla la llamada a Groq"""
    return {
        "analisis_final": {
            "sintesis_general": f"El sistema no pudo conectar con la IA para el reporte final. El taller obtuvo un promedio de {datos['metricas_totales'].get('promedio_general', 0)}/5.",
            "fortalezas_principales": ["Datos cuantificados disponibles", "Evaluación completada"],
            "areas_oportunidad": ["Reintentar para obtener análisis cualitativo", "Revisar conexión a IA"],
            "recomendaciones_practicas": ["Verifique los detalles de cada apartado individualmente"]
        },
        "metricas_consolidadas": datos['metricas_totales']
    }