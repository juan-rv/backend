import collections
import json
import openai
import time  
from src.loaders import cargar_perfil_edad, cargar_modelos_poblacion
from src.feedback import generar_comentario_global
from src import config

def es_contenido_invalido(texto):
    t = texto.strip()
    # 1. Demasiado corto (menos de 4 palabras)
    if len(t.split()) < 4:
        return "El texto es demasiado corto para realizar una evaluación pedagógica."
    
    # 2. Detección de "Gibberish" (letras al azar sin espacios)
    palabras_largas = [p for p in t.split() if len(p) > 25]
    if len(palabras_largas) > 0:
        return "El texto contiene palabras inusualmente largas o caracteres al azar."

    # 3. Entropía/Repetición (Si una sola letra domina más del 40% del texto)
    if len(t) > 20:
        counts = collections.Counter(t.lower().replace(" ", ""))
        letra_mas_comun = counts.most_common(1)[0][1]
        if letra_mas_comun / len(t.replace(" ", "")) > 0.4:
            return "El texto parece ser repetitivo o carece de estructura lingüística."
            
    return None

def llamada_segura_groq(messages, model="llama-3.1-8b-instant", temperature=0.1, retries=5):
    for i in range(retries):
        try:
            comp = openai.ChatCompletion.create(
                model=model,
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_object"}
            )
            return comp
        except openai.error.RateLimitError as e:
            wait_time = (i + 1) * 5  # Espera progresiva: 5s, 10s, 15s...
            print(f"⚠️ Rate Limit (Intento {i+1}/{retries}). Pausando {wait_time}s...")
            time.sleep(wait_time)
        except Exception as e:
            print(f"❌ Error desconocido API: {str(e)}")
            return None
    
    print("❌ Se agotaron los reintentos con Groq.")
    return None

#FUNCIÓN DE EVALUACIÓN DE INTRODUCCIÓN 
#FUNCIÓN DE EVALUACIÓN DE INTRODUCCIÓN 
def evaluar_introduccion(contenido, nombre_apartado):
    error_previo = es_contenido_invalido(contenido)
    if error_previo:
        return {
            "es_valido": False, 
            "mensaje_error": error_previo,
            "analisis_disciplinar": "Evaluación cancelada por contenido no apto."
        }

    prompt_intro = f'''
    Actúa como un Coordinador de Educación y Mediación en Museos.
    Tu misión es ENTRENAR a los guías. Estás validando el MANUAL DEL GUÍA (Introducción).
    
    FASE 1: FILTRO DE SEGURIDAD ---
    Antes de evaluar, analiza el texto del usuario:
    """
    {contenido[:3500]}
    """
    Si el texto NO tiene sentido educativo, o es una lista de palabras inconexas, 
    responde ÚNICAMENTE este JSON exacto:
    {{
        "es_valido": false,
        "mensaje_error": "El contenido ingresado no parece ser una introducción válida. Por favor verifica la redacción."
    }}
    
    --- FASE 2: VALORACIÓN PEDAGÓGICA (Solo si pasa la Fase 1) ---
    Si el texto es válido, procede con tu análisis habitual y responde SIEMPRE con este formato unificado:
    
    TU ENFOQUE:
    A diferencia de un académico puro, tú valoras la CLARIDAD, la UTILIDAD y la CAPACIDAD NARRATIVA.
    No critiques si falta profundidad enciclopédica; evalúa si el guía tiene los datos suficientes para defender el tema y responder preguntas del público.

    INSTRUCCIONES DE RESPUESTA:
    1. VALORACIÓN PEDAGÓGICA (Para el Guía):
       - Escribe un párrafo (150-200 palabras).
       - ¿El texto empodera al guía con conceptos claros?
       - NO incluyas aquí las frases clave que irán en el siguiente punto.
       - ¿Ofrece argumentos sólidos para desmitificar creencias (ej. mitos sobre el tema)?
       - Valora positivamente si conecta la teoría con la función o la vida real.

    2. PUNTOS DE CONVERSACIÓN (Storytelling):
       - Extrae 3 ideas fuerza (frases completas) que el guía pueda usar literalmente en su discurso.
       - Busca datos que generen conexión, asombro o entendimiento inmediato en el visitante.

    Responde ÚNICAMENTE con este JSON unificado:
    {{
      "es_valido": true,
      "analisis_disciplinar": "Tu valoración desde la perspectiva educativa.",
      "frases_discurso": ["Frase 1", "Frase 2", "Frase 3"]
    }}
    '''
  

    # Usamos un System Message más agresivo para forzar la Fase 2
    comp = llamada_segura_groq(
        messages=[
            {"role": "system", "content": "Eres un Coordinador de Museos. Si el texto es válido, DEBES ejecutar la FASE 2 y entregar el análisis disciplinar. No te detengas en la validación."},
            {"role": "user", "content": prompt_intro}
        ],
        temperature=0.2 # Elevamos ligeramente para evitar respuestas perezosas
    )

    if comp:
        try:
            raw_content = comp.choices[0].message.content.strip()
            # Limpiamos posibles decoraciones de Markdown
            clean_json = raw_content.replace("```json", "").replace("```", "").strip()
            
            # Localizamos el objeto JSON por si la IA agregó texto extra
            start = clean_json.find('{')
            end = clean_json.rfind('}') + 1
            res_json = json.loads(clean_json[start:end])
            
            # Aseguramos que el frontend siempre vea las llaves que necesita
            if "analisis_disciplinar" in res_json:
                res_json["es_valido"] = True
                res_json["mensaje_error"] = ""
            
            return res_json
        except Exception as e:
            print(f"❌ Error parseando JSON de Introducción: {e}")
            return {"es_valido": False, "mensaje_error": "Error en el formato de la respuesta de IA."}
            
    return {"es_valido": False, "mensaje_error": "No se pudo conectar con el servicio de evaluación."}
# FUNCIÓN DE EVALUACIÓN DE OBJETIVOS
def evaluar_objetivo(contenido, nombre_apartado, poblacion, rango):
    # --- AJUSTE AQUÍ: Recibimos solo una variable ---
    mensaje_error = es_contenido_invalido(contenido)
    
    # Si mensaje_error tiene texto (no es None), significa que es inválido
    if mensaje_error:
        return {
            "es_valido": False, 
            "mensaje_error": mensaje_error,
            "apartado": nombre_apartado,
            "feedback_global": {"comentario_general": "Evaluación cancelada: " + mensaje_error}
        }
        
    perfil = cargar_perfil_edad(poblacion, rango)
    modelos = cargar_modelos_poblacion(poblacion)
    if not perfil: 
        return {"error": "Faltan datos de perfil o edad."}

    res_final = {"apartado": nombre_apartado, "evaluaciones": []}
    calificaciones = []

    for m_key, m_val in modelos.items():
        for ind_nombre, ind_info in m_val['indicadores'].items():
            if ind_nombre.lower() in ['definicion', 'nombre', 'titulo']: 
                continue
            if not config.evaluacion_activa:
                print(f"🛑 Proceso abortado: Saltando indicador {ind_nombre}")
                # Retornamos lo que llevamos acumulado en res_final hasta el momento
                return res_final

            # Preparación de la definición técnica del indicador
            def_tec = str(ind_info)
            if isinstance(ind_info, dict):
                parts = []
                if 'Definicion' in ind_info: 
                    parts.append(f"DEFINICIÓN: {ind_info['Definicion']}")
                if 'Indicadores' in ind_info: 
                    inds = ind_info['Indicadores']
                    txt = ", ".join(inds) if isinstance(inds, list) else str(inds)
                    parts.append(f"ELEMENTOS ESPERADOS: {txt}")
                def_tec = "\n".join(parts)

            prompt = f'''
            ERES UN EVALUADOR DE CONTENIDO EDUCATIVO CON EXCELENTE REDACCIÓN Y ORTOGRAFÍA.
            
            Analiza el texto: "{contenido}"
            FASE 1: FILTRO DE SEGURIDAD ---
            Si el texto NO tiene sentido educativo, o es una lista de palabras inconexas:
            Responde ÚNICAMENTE: {{"es_valido": false, "mensaje_error": "CONTENIDO_IRRELEVANTE"}}
            Responde ÚNICAMENTE este JSON exacto:
            {{
                "es_valido": false,
                "mensaje_error": "El contenido ingresado no parece ser una introducción válida. Por favor verifica la redacción."
            }}
           
            --- FASE 2: EVALUACIÓN (Solo si es válido) ---
            Tu tarea es determinar el NIVEL DE ALINEACIÓN pedagógica entre un Objetivo, un Indicador Pedagógico y la edad DE ACUERDO A LA RÚBRICA DEL PUNTO 2.

            1. LOS DATOS A COMPARAR:
            - OBJETIVO A EVALUAR: "{contenido}"
            - INDICADOR DEL MODELO ({ind_nombre}): {def_tec}
            - CONTEXTO (EDAD): {perfil.get('etapa_cognitiva')} ({perfil.get('caracteristicas')})

            2. RÚBRICA DE EVALUACIÓN (TU ÚNICA REFERENCIA):
            Usa estas definiciones para asignar la calificación. Basa tu decisión únicamente en la correspondencia entre el significado del objetivo, la definición del indicador y la pertinencia de la edad.

            
            - NIVEL 1 (No observado): Las características evaluadas no se mencionan ni se infieren en el objetivo.
            - NIVEL 2 (Observado en menor medida): Las características se presentan de forma limitada y sin continuidad, apareciendo esporádicamente y con poca integración en la estructura pedagógica. 
            En este nivel, la aplicación es mínima y carece de una relación clara con los modelos pedagógicos.
            - NIVEL 3 (Observado parcialmente): Las características están presentes en el objetivo, pero de forma limitada en cuanto a su alineación con el modelo pedagógico y edad.
            - NIVEL 4 (Observado con frecuencia):Las características evaluadas están presentes y se utilizan de manera continua en el objetivo. Hay una buena integración en el diseño pedagógico,
            aunque ciertos detalles o consistencias podrían mejorar para alinearse completamente al modelo.
            - NIVEL 5 (Completamente observado): Las características evaluadas están presentes de manera completa y efectiva en todo el objetivo, y su uso está plenamente alineado con los principios 
            pedagógicos y la edad. La característica no solo se encuentra integrada en el diseño y desarrollo, sino que también está articulada para maximizar el impacto pedagógico deseado.
            
            3. INSTRUCCIÓN DE ANÁLISIS:
            - Analiza el significado del OBJETIVO.
            - Compáralo con la DEFINICIÓN del indicador.
            - Evalúa si el objetivo es coherente con la EDAD del estudiante.
            - Asigna el nivel que mejor describa esta relación de acuerdo a la rúbrica de evaluación.
            EVALUACIÓN CRÍTICA: No asumas intenciones que no estén escritas. Si el OBJETIVO es vago, no puede alcanzar niveles altos.
            - USO DEL CONTEXTO: Es OBLIGATORIO usar el dato "{perfil.get('etapa_cognitiva')}" para la compatibilidad. Si el objetivo pide algo demasiado complejo para esa etapa, la calificación debe bajar.
            - REGLA DE DESEMPATE: Ante la duda o falta de detalle en el texto, opta siempre por el nivel inferior inmediato. El Nivel 5 se reserva únicamente para alineaciones perfectas y explícitas.
            - PROHIBICIÓN DE CIRCULARIDAD: En el análisis, no repitas la definición de la rúbrica; explica qué palabras del texto justifican tu decisión.
            TEN MUY EN CUENTA LA EVALUACIÓN Y LA REFLEXIÓN, TIENE QUE ESTÁR INMERSO EN EL TEXTO INGRESADO.

            4. FORMATO DE RESPUESTA (JSON):
            Responde únicamente en JSON.
            IMPORTANTE: El campo "calificacion" debe ser el resultado directo de aplicar la Rúbrica de la Sección 2.
            El lenguaje debe ser netamente constructivista y pedagógico.
            
            {{
                "calificacion": <Número entero 1-5 que corresponda EXACTAMENTE a la definición de la rúbrica seleccionada>,
                "analisis": {{
                    "evidencia_pedagogica": "Cita textual del objetivo y su conexión técnica con el indicador. ¿Qué proceso mental se activa?",
                    "justificacion_edad": "Análisis de por qué el contenido es apto (o no) para la etapa {perfil.get('etapa_cognitiva')}, mencionando un hito del desarrollo cognitivo.",
                    "razonamiento_nivel": "Diferenciación técnica: Explica qué elemento específico tiene para estar en Nivel X y qué le falta EXACTAMENTE para subir al Nivel X+1."
                }}
            }}
            '''

            # FUNCIÓN SEGURA
            comp = llamada_segura_groq(
                messages=[
                    {"role": "system", "content": "Eres un evaluador objetivo que responde solo en JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0
            )

            if comp:
                try:
                    content_resp = comp.choices[0].message.content.replace("```json", "").replace("```", "").strip()
                    res_json = json.loads(content_resp)
                    cal = int(res_json.get('calificacion', 1))
                    analisis = res_json.get('analisis', {})
                    if isinstance(analisis, str): 
                        analisis = {"razonamiento": analisis}
                    res_final["evaluaciones"].append({
                        "modelo": m_val['nombre'],
                        "indicador": ind_nombre,
                        "calificacion": cal,
                        "analisis": analisis 
                    })
                    calificaciones.append(cal)                 
                    # --- RETRASO PREVENTIVO ---
                    # Esperar 2 segundos entre indicadores para Rate Limit
                    print(f"✅ {ind_nombre} evaluado. Esperando 2s...")
                    time.sleep(2) 

                except Exception as e: 
                    print(f"Error procesando respuesta JSON en {ind_nombre}: {e}")

    # CÁLCULOS Y FEEDBACK GLOBAL 
    if calificaciones:
        promedio = round(sum(calificaciones)/len(calificaciones), 2)
        res_final["estadisticas"] = {
            "promedio": promedio,
            "total_indicadores": len(calificaciones)
        }

        feedback = generar_comentario_global(contenido, res_final["evaluaciones"], perfil.get('etapa_cognitiva'))
        res_final["feedback_global"] = feedback

    return res_final

def es_una_actividad(nombre_apartado, contenido):
    nombre = nombre_apartado.lower()
    texto = contenido.lower()
    
    palabras_actividad = [
        "actividad", "ejercicio", "taller", "práctica", "practica",
        "juego", "simulación", "simulacion", "dinámica", "dinamica",
        "workshop", "laboratorio", "experimento", "proyecto",
        "tarea", "consigna", "ejercitación", "ejercitacion", "dinamica"
    ]
    
    if any(palabra in nombre for palabra in palabras_actividad):
        return True
    
    patrones_actividad = [
        "dirigido a", "destinatarios", "participantes",
        "duración", "duracion", "tiempo estimado", "minutos",
        "materiales", "recursos", "necesitarás", "necesitaras",
        "paso 1", "1.", "procedimiento", "instrucciones",
        "desarrollo", "cierre", "reflexión", "reflexion", "finalizar"
    ]
    
    encontrados = 0
    for patron in patrones_actividad:
        if patron in texto:
            encontrados += 1
    
    return encontrados >= 3

def evaluar_actividad(contenido, nombre_apartado, poblacion, rango):
    # --- AJUSTE DE VALIDACIÓN ---
    mensaje_error = es_contenido_invalido(contenido)
    
    if mensaje_error:
        return {
            "es_valido": False, 
            "mensaje_error": mensaje_error,
            "apartado": nombre_apartado,
            "tipo_detectado": "actividad",
            "feedback_global": {"comentario_general": "Evaluación cancelada: " + mensaje_error}
        }
    
    perfil = cargar_perfil_edad(poblacion, rango)
    modelos = cargar_modelos_poblacion(poblacion)
    
    if not perfil:
        return {"error": "Faltan datos de perfil o edad."}
    
    res_final = {
        "apartado": nombre_apartado,
        "tipo_detectado": "actividad",
        "evaluaciones": []
    }
    calificaciones = []
    
    print(f"--- EVALUANDO ACTIVIDAD: {nombre_apartado} ---")
    
    for m_key, m_val in modelos.items():
        for ind_nombre, ind_info in m_val['indicadores'].items():
            if ind_nombre.lower() in ['definicion', 'nombre', 'titulo', 'descripcion']:
                continue
            
            if not config.evaluacion_activa:
                print(f"🛑 Proceso abortado: Saltando indicador {ind_nombre}")
                # Retornamos lo que llevamos acumulado en res_final hasta el momento
                return res_final
            
            def_tec = str(ind_info)
            if isinstance(ind_info, dict):
                parts = []
                if 'Definicion' in ind_info:
                    parts.append(f"DEFINICIÓN: {ind_info['Definicion']}")
                if 'Indicadores' in ind_info:
                    inds = ind_info['Indicadores']
                    txt = ", ".join(inds) if isinstance(inds, list) else str(inds)
                    parts.append(f"ELEMENTOS ESPERADOS: {txt}")
                def_tec = "\n".join(parts)
            
            prompt = f'''
            ERES UN EVALUADOR DE ACTIVIDADES EDUCATIVAS CON EXCELENTE REDACCIÓN Y ORTOGRAFÍA.
            
            Analiza el texto: "{contenido[:1000]}..."
            FASE 1: FILTRO DE SEGURIDAD ---
            Si el texto NO tiene sentido educativo, o es una lista de palabras inconexas:
            Responde ÚNICAMENTE: {{"es_valido": false, "mensaje_error": "CONTENIDO_IRRELEVANTE"}}
            Responde ÚNICAMENTE este JSON exacto:
            {{
                "es_valido": false,
                "mensaje_error": "El contenido ingresado no parece ser una introducción válida. Por favor verifica la redacción."
            }}
           
            --- FASE 2: EVALUACIÓN (Solo si es válido) ---
            
            TU TAREA: Determinar si una ACTIVIDAD implementa o aplica un indicador pedagógico.
            
            DATOS A EVALUAR:
            - ACTIVIDAD: "{contenido[:1000]}..."
            - INDICADOR PEDAGÓGICO ({ind_nombre}): {def_tec}
            - CONTEXTO (EDAD): {perfil.get('etapa_cognitiva', '')} 
              Características: {perfil.get('caracteristicas', '')}
            
            RÚBRICA DE EVALUACIÓN:
            - NIVEL 1 (No observado): Las características evaluadas no se mencionan ni se infieren en la actividad.
            - NIVEL 2 (Observado en menor medida): Las características se presentan de forma limitada y sin continuidad, apareciendo esporádicamente y con poca integración en la estructura pedagógica. 
            En este nivel, la aplicación es mínima y carece de una relación clara con los modelos pedagógicos.
            - NIVEL 3 (Observado parcialmente): Las características están presentes en la actividad, pero de forma limitada en cuanto a su alineación con el modelo pedagógico y edad.
            - NIVEL 4 (Observado con frecuencia):Las características evaluadas están presentes y se utilizan de manera continua en la actividad. Hay una buena integración en el diseño pedagógico,
            aunque ciertos detalles o consistencias podrían mejorar para alinearse completamente al modelo.
            - NIVEL 5 (Completamente observado): Las características evaluadas están presentes de manera completa y efectiva en todo la actividad, y su uso está plenamente alineado con los principios 
            pedagógicos y la edad. La característica no solo se encuentra integrada en el diseño y desarrollo, sino que también está articulada para maximizar el impacto pedagógico deseado.
            
            INSTRUCCIÓN DE ANÁLISIS:
            - Analiza la ACTIVIDAD completa
            - Determina si IMPLEMENTA o APLICA el indicador "{ind_nombre}"
            - Considera si es apropiada para la EDAD del estudiante
            - Asigna nivel 1-5 según la rúbrica
            - IMPLEMENTACIÓN REAL: No evalúes si la actividad es "bonita". Evalúa si el paso a paso de la actividad obliga al estudiante a ejecutar lo que dice el indicador "{ind_nombre}".
            - PERTINENCIA DE DESARROLLO: Contrasta la actividad con la etapa "{perfil.get('etapa_cognitiva', '')}". ¿Tienen los estudiantes la madurez necesaria para los retos propuestos?
            TEN MUY EN CUENTA LA EVALUACIÓN Y LA REFLEXIÓN, TIENE QUE ESTÁR INMERSO EN EL TEXTO INGRESADO.
            FORMATO DE RESPUESTA (JSON):
            {{
                "calificacion": <Número entero 1-5>,
                "analisis": {{
                    "ejecucion_indicador": "Análisis de cómo la secuencia de la actividad activa (o no) el indicador técnico.",
                    "adecuacion_cognitiva": "Justificación de por qué la actividad es apta para la etapa {perfil.get('etapa_cognitiva', '')}, citando un hito de esta edad.",
                }}
            }}
            Responde ÚNICAMENTE en JSON.
            '''
            
            comp = llamada_segura_groq(
                messages=[
                    {"role": "system", "content": "Eres un evaluador objetivo que responde solo en JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0
            )
            
            if comp:
                try:
                    content_resp = comp.choices[0].message.content.replace("```json", "").replace("```", "").strip()
                    res_json = json.loads(content_resp)
                    
                    cal = int(res_json.get('calificacion', 1))
                    analisis = res_json.get('analisis', {})
                    if isinstance(analisis, str):
                        analisis = {"razonamiento": analisis}
                    
                    res_final["evaluaciones"].append({
                        "modelo": m_val['nombre'],
                        "indicador": ind_nombre,
                        "calificacion": cal,
                        "analisis": analisis
                    })
                    calificaciones.append(cal)
                    
                    # --- RETRASO PREVENTIVO ---
                    print(f"✅ {ind_nombre} evaluado. Esperando 2s...")
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"Error procesando respuesta JSON en {ind_nombre}: {e}")
    
    if calificaciones:
        promedio = round(sum(calificaciones) / len(calificaciones), 2)
        res_final["estadisticas"] = {
            "promedio": promedio,
            "total_indicadores": len(calificaciones)
        }
        
        # Ojo: Aquí usaba feedback_global que está en tu archivo original.
        # Asegúrate que generar_comentario_global soporta el parámetro 'tipo'
        # o importa la función correcta.
        feedback = generar_comentario_global(
            contenido, 
            res_final["evaluaciones"], 
            perfil.get('etapa_cognitiva', ''),
            tipo="actividad"
        )
        res_final["feedback_global"] = feedback
    
    return res_final