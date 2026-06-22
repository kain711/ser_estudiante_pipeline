"""
Pipeline Ser Estudiante — paso 1: descarga con detección de cambios.

Lógica:
1. Consultamos la API pública de CKAN (package_show) para el dataset "ser-estudiante".
2. Comparamos resource_id + last_modified de cada recurso contra el manifiesto
   guardado en data/processed/manifest.json (ese sí se versiona en git).
3. Si no hay cambios -> no descargamos nada y terminamos (exit code 0, sin novedad).
4. Si hay cambios -> descargamos solo los recursos nuevos/modificados a data/raw/
   y escribimos data/raw/cambios_detectados.json para que procesar.py sepa qué pasó.

Importante: el manifest.json NO se actualiza aquí. Se actualiza al final de
procesar.py, solo si el reprocesamiento fue exitoso. Así, si algo falla a mitad
de camino, la próxima corrida vuelve a intentar los mismos cambios.
"""

import json
import os
import sys
import requests

DATASET = "ser-estudiante"
API_URL = f"https://www.datosabiertos.gob.ec/api/3/action/package_show?id={DATASET}"

# El portal bloquea con 403 las peticiones que llegan con el User-Agent por
# defecto de requests ("python-requests/x.x"). Con un User-Agent de navegador
# normal lo deja pasar sin problema.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, */*;q=0.8",
}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
MANIFEST_PATH = os.path.join(BASE_DIR, "data", "processed", "manifest.json")
CAMBIOS_PATH = os.path.join(RAW_DIR, "cambios_detectados.json")


def obtener_metadata_remota() -> dict:
    """Consulta la API de CKAN y devuelve un dict {resource_id: info_recurso}
    solo para los recursos que nos interesan: CSV de resultados y ODS de diccionario.
    """
    resp = requests.get(API_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if not data.get("success"):
        raise RuntimeError(f"La API de CKAN respondió success=False: {data}")

    recursos = {}
    for r in data["result"]["resources"]:
        nombre = r["name"].strip().lower()
        formato = r["format"].upper()

        # Nos interesan: CSV de resultados, y ODS que sean diccionario (no los "PM" de metodología)
        es_resultado = formato == "CSV"
        es_diccionario = formato == "ODS" and "_dd_" in nombre.replace(" ", "_") or "diccionario" in nombre

        if not (es_resultado or es_diccionario):
            continue  # ignoramos los archivos "PM" (metodología), no los usamos en el modelo

        recursos[r["id"]] = {
            "nombre": r["name"].strip(),
            "tipo": "resultado" if es_resultado else "diccionario",
            "formato": formato,
            "url": r["url"],
            "last_modified": r["last_modified"],
            "size": r["size"],
        }
    return recursos


def cargar_manifest() -> dict:
    if not os.path.exists(MANIFEST_PATH):
        return {}
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def detectar_cambios(remoto: dict, manifest: dict) -> dict:
    """Devuelve solo los recursos que son nuevos o cuyo last_modified cambió."""
    cambios = {}
    for resource_id, info in remoto.items():
        previo = manifest.get(resource_id)
        if previo is None or previo.get("last_modified") != info["last_modified"]:
            cambios[resource_id] = info
    return cambios


def descargar_recurso(resource_id: str, info: dict) -> str:
    os.makedirs(RAW_DIR, exist_ok=True)
    nombre_archivo = info["url"].split("/")[-1]
    destino = os.path.join(RAW_DIR, nombre_archivo)

    print(f"Descargando {info['nombre']} -> {nombre_archivo}")
    resp = requests.get(info["url"], headers=HEADERS, timeout=120)
    resp.raise_for_status()
    with open(destino, "wb") as f:
        f.write(resp.content)
    return destino


def main():
    print("Consultando metadata del dataset en datosabiertos.gob.ec...")
    remoto = obtener_metadata_remota()
    manifest = cargar_manifest()

    cambios = detectar_cambios(remoto, manifest)

    if not cambios:
        print("Sin cambios. El dataset remoto coincide con el manifiesto. No se descarga nada.")
        sys.exit(0)

    print(f"Se detectaron {len(cambios)} recurso(s) nuevos o modificados:")
    for resource_id, info in cambios.items():
        print(f"  - {info['nombre']} ({info['tipo']}, modificado {info['last_modified']})")

    # Importante: procesar.py concatena los 6 ciclos completos, no solo el que
    # cambió. data/raw/ no se versiona (se descarta entre corridas), así que si
    # algo cambió, descargamos TODOS los recursos relevantes (no solo el delta)
    # para que el reprocesamiento completo tenga los 12 archivos disponibles.
    # Es más simple y robusto que mantener un caché persistente de lo no-cambiado.
    print("\nDescargando el set completo (12 archivos) para reprocesar desde cero...")
    rutas_descargadas = {}
    for resource_id, info in remoto.items():
        ruta = descargar_recurso(resource_id, info)
        rutas_descargadas[resource_id] = {**info, "ruta_local": ruta}

    os.makedirs(RAW_DIR, exist_ok=True)
    with open(CAMBIOS_PATH, "w", encoding="utf-8") as f:
        json.dump(rutas_descargadas, f, ensure_ascii=False, indent=2)

    print(f"Cambios guardados en {CAMBIOS_PATH}. Listo para que procesar.py los incorpore.")


if __name__ == "__main__":
    main()
