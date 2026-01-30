import json
import openai

def analizar_resultados_taller(resultados):
    """
    Analiza resultados de evaluación previos para generar informe integrado.
    resultados = {
        "introduccion": {...},  # Resultado de evaluar_introduccion()
        "objetivo": {...},      # Resultado de evaluar_objetivo()
        "actividades": [{...}, {...}]  # Resultados de evaluar_actividad()
    }
    """
    
    # 1. Extraer y estructurar datos de los resultados
    datos_extraidos = extraer_datos_resultados(resultados)
    
    # 2. Si hay suficiente información, generar análisis
    if datos_extraidos['tiene_datos_suficientes']:
        # 3. Usar SOLO UNA llamada a Groq para síntesis final
        return generar_sintesis_final(datos_extraidos)
    else:
        return {"error": "Datos insuficientes para análisis integrado"}

def extraer_datos_resultados(resultados):
    """
    Extrae información clave de los resultados de evaluación SIN llamar a Groq
    """
    datos = {
        "titulo": "Taller analizado",
        "introduccion": {},
        "objetivo": {},
        "actividades": [],
        "tiene_datos_suficientes": False,
        "metricas_totales": {}
    }
    
    # Extraer de introducción
    if resultados.get('introduccion'):
        intro = resultados['introduccion']
        datos['introduccion'] = {
            "valoracion": intro.get('analisis_disciplinar', '')[:100],
            "frases_clave": intro.get('frases_discurso', []),
            "tiene_contenido": bool(intro.get('analisis_disciplinar'))
        }
    
    # Extraer de objetivo
    if resultados.get('objetivo'):
        obj = resultados['objetivo']
        datos['objetivo'] = {
            "texto": obj.get('apartado', ''),
            "promedio": obj.get('estadisticas', {}).get('promedio', 0),
            "total_indicadores": obj.get('estadisticas', {}).get('total_indicadores', 0),
            "evaluaciones": obj.get('evaluaciones', [])[:3]  # Primeras 3
        }
    
    # Extraer de actividades
    if resultados.get('actividades'):
        for act in resultados['actividades']:
            datos_act = {
                "nombre": act.get('apartado', ''),
                "tipo": act.get('tipo_detectado', 'actividad'),
                "promedio": act.get('estadisticas', {}).get('promedio', 0),
                "total_indicadores": act.get('estadisticas', {}).get('total_indicadores', 0),
                "feedback": act.get('feedback_global', {}).get('comentario_general', '')[:150]
            }
            datos['actividades'].append(datos_act)
    
    # Calcular métricas totales
    promedios = []
    if datos['objetivo'].get('promedio'):
        promedios.append(datos['objetivo']['promedio'])
    for act in datos['actividades']:
        if act.get('promedio'):
            promedios.append(act['promedio'])
    
    if promedios:
        datos['metricas_totales'] = {
            "promedio_general": round(sum(promedios) / len(promedios), 2),
            "total_componentes": len(promedios),
            "rango_promedios": f"{min(promedios)}-{max(promedios)}" if promedios else "N/A"
        }
        datos['tiene_datos_suficientes'] = True
    
    return datos

def generar_sintesis_final(datos_extraidos):
    """
    Una SOLA llamada a Groq para sintetizar toda la información extraída
    """
    
    prompt = f'''
    ERES UN CONSULTOR PEDAGÓGICO. ANALIZA ESTOS RESULTADOS DE EVALUACIÓN:
    
    TALLER: {datos_extraidos['titulo']}
    
    MÉTRICAS GLOBALES:
    - Promedio general: {datos_extraidos['metricas_totales'].get('promedio_general', 'N/A')}/5
    - Componentes evaluados: {datos_extraidos['metricas_totales'].get('total_componentes', 0)}
    - Rango de calificaciones: {datos_extraidos['metricas_totales'].get('rango_promedios', 'N/A')}
    
    OBJETIVO PRINCIPAL:
    - Texto: {datos_extraidos['objetivo'].get('texto', 'N/A')}
    - Calificación: {datos_extraidos['objetivo'].get('promedio', 'N/A')}/5
    - Indicadores evaluados: {datos_extraidos['objetivo'].get('total_indicadores', 0)}
    
    INTRODUCCIÓN:
    - Valoración: {datos_extraidos['introduccion'].get('valoracion', 'No evaluada')}
    - Frases clave: {', '.join(datos_extraidos['introduccion'].get('frases_clave', []))}
    
    ACTIVIDADES ({len(datos_extraidos['actividades'])}):
    {formatear_actividades(datos_extraidos['actividades'])}
    
    TU TAREA: Generar un INFORME FINAL breve (máx 300 palabras) que:
    1. SINTETICE el desempeño general del taller
    2. DESTAQUE las principales fortalezas detectadas
    3. SEÑALE áreas de oportunidad clave
    4. PROPORCIONE 2-3 recomendaciones prácticas
    
    FORMATO JSON:
    {{
        "analisis_final": {{
            "sintesis_general": "Texto de síntesis...",
            "fortalezas_principales": ["Fortaleza 1", "Fortaleza 2"],
            "areas_oportunidad": ["Área 1", "Área 2"],
            "recomendaciones_practicas": ["Recomendación 1", "Recomendación 2"]
        }},
        "metricas_consolidadas": {{
            "promedio_general": {datos_extraidos['metricas_totales'].get('promedio_general', 0)},
            "componentes_evaluados": {datos_extraidos['metricas_totales'].get('total_componentes', 0)}
        }}
    }}
    '''
    
    try:
        response = openai.ChatCompletion.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Eres un analista pedagógico conciso y práctico."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=500
        )
        
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        # Fallback: análisis simple sin IA
        return generar_analisis_simple(datos_extraidos)

def formatear_actividades(actividades):
    """Formatea información de actividades para el prompt"""
    texto = ""
    for i, act in enumerate(actividades, 1):
        texto += f"\n{i}. {act.get('nombre', 'Actividad')}\n"
        texto += f"   - Calificación: {act.get('promedio', 'N/A')}/5\n"
        texto += f"   - Tipo: {act.get('tipo', 'actividad')}\n"
        texto += f"   - Feedback: {act.get('feedback', 'Sin feedback')}\n"
    return texto

def generar_analisis_simple(datos):
    """Análisis simple si falla la llamada a Groq"""
    return {
        "analisis_final": {
            "sintesis_general": f"Taller evaluado con promedio {datos['metricas_totales'].get('promedio_general', 0)}/5",
            "fortalezas_principales": ["Datos disponibles para análisis"],
            "areas_oportunidad": ["Mejorar coherencia entre componentes"],
            "recomendaciones_practicas": ["Revisar actividades con menor calificación"]
        },
        "metricas_consolidadas": datos['metricas_totales']
    }