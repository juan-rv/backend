# routes.py - VERSIÓN CORREGIDA
from flask import request, jsonify
from src.evaluators import evaluar_introduccion, evaluar_objetivo, es_una_actividad, evaluar_actividad
from src.analizador_resultados import analizar_resultados_taller

def evaluar_apartado_route():
    data = request.json
    
    contenido = data.get('apartado', {}).get('Contenido', '')
    nombre_apartado = data.get('apartado', {}).get('Apartado', 'Objetivo General')
    poblacion = data.get('poblacion', 'joven')
    rango = data.get('rango_edad', '')

    print(f"--- PROCESANDO: {nombre_apartado} ---")
    nombre_normalizado = nombre_apartado.strip().lower()
    
    # 1. INTRODUCCIÓN
    if "introducción" in nombre_normalizado or "introduccion" in nombre_normalizado:
        print(">>> Detectado modo: COORDINADOR DE MUSEOS (Introducción)")
        return jsonify(evaluar_introduccion(contenido, nombre_apartado))
    
    # 2. ACTIVIDADES (NUEVO)
    elif es_una_actividad(nombre_apartado, contenido):
        print(">>> Detectado modo: EVALUADOR DE ACTIVIDADES")
        return jsonify(evaluar_actividad(contenido, nombre_apartado, poblacion, rango))
    
    # 3. OBJETIVOS (por defecto)
    else:
        print(">>> Detectado modo: EVALUADOR PEDAGÓGICO (Objetivos)")
        return jsonify(evaluar_objetivo(contenido, nombre_apartado, poblacion, rango))

# ============================================================================
# NUEVA FUNCIÓN PARA ANÁLISIS INTEGRADO
# ============================================================================

def analizar_taller_completo_route():
    """
    Analiza resultados previos de evaluación de un taller completo
    """
    data = request.json
    
    # Validar que hay datos
    if not data:
        return jsonify({
            "error": "No se proporcionaron datos",
            "detalle": "El cuerpo de la solicitud debe contener los resultados de evaluación"
        }), 400
    
    # Validar estructura mínima (necesitamos al menos objetivo según tu función)
    if not data.get('objetivo'):
        return jsonify({
            "error": "Se requiere al menos el resultado del objetivo",
            "estructura_esperada": {
                "introduccion": {
                    "analisis_disciplinar": "...", 
                    "frases_discurso": []
                },
                "objetivo": {
                    "apartado": "...", 
                    "estadisticas": {
                        "promedio": 0.0,
                        "total_indicadores": 0
                    }, 
                    "evaluaciones": []
                },
                "actividades": [
                    {
                        "apartado": "...", 
                        "estadisticas": {
                            "promedio": 0.0,
                            "total_indicadores": 0
                        }
                    }
                ]
            }
        }), 400
    
    try:
        # Llamar a tu función de análisis integrado
        analisis = analizar_resultados_taller(data)
        
        # Si la función retorna error por datos insuficientes
        if "error" in analisis:
            return jsonify(analisis), 400
        
        # Añadir metadatos a la respuesta
        if isinstance(analisis, dict):
            analisis["metadata"] = {
                "endpoint": "/analizar_taller_completo",
                "componentes_recibidos": list(data.keys())
            }
            
        return jsonify(analisis), 200
        
    except Exception as e:
        # Log del error
        print(f"❌ Error en analizar_taller_completo: {str(e)}")
        
        return jsonify({
            "error": "Error interno del servidor al analizar el taller",
            "detalle": str(e)
        }), 500