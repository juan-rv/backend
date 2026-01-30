import json
import openai
from src.loaders import cargar_perfil_edad, cargar_modelos_poblacion
from src.feedback import generar_comentario_global

# --- FUNCIÓN DE EVALUACIÓN DE INTRODUCCIÓN (IDÉNTICA - NO CAMBIAR) ---
def evaluar_introduccion(contenido, nombre_apartado):
    prompt_intro = f'''
    Actúa como un Coordinador de Educación y Mediación en Museos.
    Tu misión es ENTRENAR a los guías. Estás validando el MANUAL DEL GUÍA (Introducción).
    
    TU ENFOQUE:
    A diferencia de un académico puro, tú valoras la CLARIDAD, la UTILIDAD y la CAPACIDAD NARRATIVA.
    No critiques si falta profundidad enciclopédica; evalúa si el guía tiene los datos suficientes para defender el tema y responder preguntas del público.

    TEXTO A ANALIZAR:
    """
    {contenido[:3500]}
    """

    INSTRUCCIONES DE RESPUESTA:
    1. VALORACIÓN PEDAGÓGICA (Para el Guía):
       - Escribe un párrafo (60-90 palabras).
       - ¿El texto empodera al guía con conceptos claros?
       - ¿Ofrece argumentos sólidos para desmitificar creencias (ej. mitos sobre el tema)?
       - Valora positivamente si conecta la teoría con la función o la vida real.

    2. PUNTOS DE CONVERSACIÓN (Storytelling):
       - Extrae 3 ideas fuerza (frases completas) que el guía pueda usar literalmente en su discurso.
       - Busca datos que generen conexión, asombro o entendimiento inmediato en el visitante.
       - Ejemplo: "Gracias a su mandíbula no fusionada, las serpientes pueden abrir la boca enormemente para alimentarse."

    Responde ÚNICAMENTE con este JSON:
    {{
      "analisis_disciplinar": "Tu valoración desde la perspectiva educativa.",
      "frases_discurso": ["Frase 1", "Frase 2", "Frase 3"],
      "recomendacion": "Sugerencia solo si el texto es confuso o insuficiente."
    }}
    '''

    try:
        comp = openai.ChatCompletion.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Eres un Coordinador de Educación en Museos."},
                {"role": "user", "content": prompt_intro}
            ],
            temperature=0.4,
            response_format={"type": "json_object"}
        )
        return json.loads(comp.choices[0].message.content)
    except Exception as e:
        return {"error": f"Error evaluando introducción: {str(e)}"}

# --- FUNCIÓN DE EVALUACIÓN DE OBJETIVOS (IDÉNTICA - NO CAMBIAR) ---
def evaluar_objetivo(contenido, nombre_apartado, poblacion, rango):
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

            # Preparación de la definición técnica del indicador (IDÉNTICO)
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

            # --- PROMPT NEUTRO (EXACTAMENTE IGUAL) ---
            prompt = f'''
            ERES UN EVALUADOR DE CONTENIDO EDUCATIVO CON EXCELENTE REDACCIÓN.
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

            4. FORMATO DE RESPUESTA (JSON):
            Responde únicamente en JSON.
            IMPORTANTE: El campo "calificacion" debe ser el resultado directo de aplicar la Rúbrica de la Sección 2.
            
            {{
                "calificacion": <Número entero 1-5 que corresponda EXACTAMENTE a la definición de la rúbrica seleccionada>,
                "analisis": {{
                    "razonamiento": "Justificación DIRECTA Y SIN REDUNDANCIAS Y el paso a paso de por qué el objetivo encaja en ese nivel, si mencionas la edad justifica la compatibilidad cognitiva",
                }}
            }}
            '''

            try:
                comp = openai.ChatCompletion.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": "Eres un evaluador objetivo que responde solo en JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.0,
                    response_format={"type": "json_object"}
                )
                
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
            except Exception as e: 
                print(f"Error en {ind_nombre}: {e}")

    # --- CÁLCULOS Y FEEDBACK GLOBAL (EXACTAMENTE IGUAL) ---
    if calificaciones:
        promedio = round(sum(calificaciones)/len(calificaciones), 2)
        res_final["estadisticas"] = {
            "promedio": promedio,
            "total_indicadores": len(calificaciones)
        }

        feedback = generar_comentario_global(contenido, res_final["evaluaciones"], perfil.get('etapa_cognitiva'))
        res_final["feedback_global"] = feedback

    return res_final

# ============================================================================
# NUEVAS FUNCIONES PARA EVALUACIÓN DE ACTIVIDADES (AÑADIR AL FINAL)
# ============================================================================

def es_una_actividad(nombre_apartado, contenido):
    """
    Detecta si el contenido es una actividad educativa.
    NO modifica nada existente - solo añade esta función.
    """
    nombre = nombre_apartado.lower()
    texto = contenido.lower()
    
    # 1. Palabras clave en el título que INDICAN actividad
    palabras_actividad = [
        "actividad", "ejercicio", "taller", "práctica", "practica",
        "juego", "simulación", "simulacion", "dinámica", "dinamica",
        "workshop", "laboratorio", "experimento", "proyecto",
        "tarea", "consigna", "ejercitación", "ejercitacion", "dinamica"
    ]
    
    # Si el título claramente dice "actividad"
    if any(palabra in nombre for palabra in palabras_actividad):
        return True
    
    # 2. Estructura típica de actividades en el contenido
    patrones_actividad = [
        "dirigido a", "destinatarios", "participantes",
        "duración", "duracion", "tiempo estimado", "minutos",
        "materiales", "recursos", "necesitarás", "necesitaras",
        "paso 1", "1.", "procedimiento", "instrucciones",
        "desarrollo", "cierre", "reflexión", "reflexion", "finalizar"
    ]
    
    # Contar cuántos patrones encuentra
    encontrados = 0
    for patron in patrones_actividad:
        if patron in texto:
            encontrados += 1
    
    # Umbral: si tiene 3 o más patrones, probablemente es actividad
    return encontrados >= 3


def evaluar_actividad(contenido, nombre_apartado, poblacion, rango):
    """
    Evalúa una actividad educativa usando la MISMA LÓGICA que evaluar_objetivo()
    pero con prompts adaptados para actividades.
    """
    # 1. Cargar perfil y modelos (MISMAS funciones existentes)
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
            # Saltar metadatos (igual que en objetivos)
            if ind_nombre.lower() in ['definicion', 'nombre', 'titulo', 'descripcion']:
                continue
            
            # Preparar definición técnica del indicador (MISMA lógica)
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
            
            # --- PROMPT ADAPTADO PARA ACTIVIDADES ---
            # ÚNICA diferencia con evaluación de objetivos
            prompt = f'''
            ERES UN EVALUADOR DE ACTIVIDADES EDUCATIVAS.
            
            TU TAREA: Determinar si una ACTIVIDAD implementa o aplica un indicador pedagógico.
            
            DATOS A EVALUAR:
            - ACTIVIDAD: "{contenido[:1000]}..."
            - INDICADOR PEDAGÓGICO ({ind_nombre}): {def_tec}
            - CONTEXTO (EDAD): {perfil.get('etapa_cognitiva', '')} 
              Características: {perfil.get('caracteristicas', '')}
            
            RÚBRICA DE EVALUACIÓN (MISMA que para objetivos):
            - NIVEL 1 (No observado): La actividad NO implementa características del indicador
            - NIVEL 2 (Observado en menor medida): Implementa superficialmente algunas características
            - NIVEL 3 (Observado parcialmente): Implementa algunas características relevantes
            - NIVEL 4 (Observado con frecuencia): Implementa bien las características
            - NIVEL 5 (Completamente observado): Implementa excelentemente todas las características
            
            INSTRUCCIÓN DE ANÁLISIS:
            - Analiza la ACTIVIDAD completa
            - Determina si IMPLEMENTA o APLICA el indicador "{ind_nombre}"
            - Considera si es apropiada para la EDAD del estudiante
            - Asigna nivel 1-5 según la rúbrica
            
            FORMATO DE RESPUESTA (JSON):
            {{
                "calificacion": <Número entero 1-5>,
                "analisis": {{
                    "razonamiento": "Explica CÓMO esta actividad implementa (o no) el indicador, considerando la edad"
                }}
            }}
            
            Responde ÚNICAMENTE en JSON.
            '''
            
            try:
                # LLAMADA A API (MISMA que en evaluación de objetivos)
                comp = openai.ChatCompletion.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": "Eres un evaluador objetivo que responde solo en JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.0,
                    response_format={"type": "json_object"}
                )
                
                content_resp = comp.choices[0].message.content
                content_resp = content_resp.replace("```json", "").replace("```", "").strip()
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
                
            except Exception as e:
                print(f"Error evaluando actividad en indicador {ind_nombre}: {e}")
    
    # --- CÁLCULOS Y FEEDBACK GLOBAL ---
    if calificaciones:
        promedio = round(sum(calificaciones) / len(calificaciones), 2)
        res_final["estadisticas"] = {
            "promedio": promedio,
            "total_indicadores": len(calificaciones)
        }
        
        # Usar la MISMA función de feedback pero indicando que es actividad
        # Para esto necesitamos modificar ligeramente generar_comentario_global
        # Por ahora usamos la misma función
        feedback = generar_comentario_global(
            contenido, 
            res_final["evaluaciones"], 
            perfil.get('etapa_cognitiva', ''),
            tipo="actividad"
        )
        res_final["feedback_global"] = feedback
    
    return res_final