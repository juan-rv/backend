import json
import os
from src.config import BASE_DIR

# FUNCIONES IDÉNTICAS a tu código original
def cargar_perfil_edad(poblacion, rango):
    try:
        path = os.path.join(BASE_DIR, "data", "edades", f"poblacion_{poblacion}.json")
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f).get(poblacion, {})
            for k, v in data.items():
                if rango in k: return v
            return {}
    except Exception as e:
        print(f"Error cargando perfil ({poblacion}): {e}")
        return {}

def cargar_modelos_poblacion(poblacion):
    archivos = ['ensenanza_para_la_comprension', 'indagacion_cientifica'] if poblacion == "joven" else ['didactica_del_patrimonio', 'pedagogia_critica']
    modelos = {}
    for a in archivos:
        try:
            path = os.path.join(BASE_DIR, 'data', 'models', f'{a}.json')
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                root = list(data.keys())[0]
                modelos[a] = {"nombre": root, "indicadores": data[root]}
        except Exception as e:
            print(f"Error cargando modelo ({a}): {e}")
            pass
    return modelos