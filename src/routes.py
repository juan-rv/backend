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
    payload = request.json
    if not payload:
        return jsonify({"error": "No hay datos"}), 400

    # Extraemos las evaluaciones
    evaluaciones = payload.get('evaluaciones', payload)
    rango_edad = payload.get('rango_edad', 'Población general')

    # --- DEBUG: Esto te mostrará en la terminal qué llaves están llegando ---
    print(f"DEBUG - Llaves recibidas: {list(evaluaciones.keys())}")

    # VALIDACIÓN FLEXIBLE:
    # Buscamos si existe alguna llave que contenga la palabra "objetivo" (sin importar mayúsculas)
    llave_objetivo = next((k for k in evaluaciones.keys() if "objetivo" in k.lower()), None)
    
    if not llave_objetivo:
        # Si llegamos aquí, es porque realmente no hay nada que se parezca a un objetivo
        return jsonify({
            "error": "Faltan datos",
            "detalle": f"No se encontró el apartado de Objetivo. Recibido: {list(evaluaciones.keys())}"
        }), 400

    try:
        # Si pasó la validación, llamamos a la lógica
        analisis = analizar_resultados_taller(evaluaciones, rango_edad)
        return jsonify(analisis), 200
    except Exception as e:
        print(f"❌ Error crítico: {str(e)}")
        return jsonify({"error": str(e)}), 500