"""
Pipeline Ser Estudiante — paso 2: procesamiento.

Adaptado de unificacion_ser_estudiante.ipynb (notebook original del proyecto).
Toma los archivos descargados por descargar.py en data/raw/ y genera:
  - data/processed/serestudiante_consolidado.csv   (hecho: 1 fila por estudiante evaluado)
  - data/processed/Dim_Institucion_Maestro.csv
  - data/processed/Dim_Canton_Maestro.csv
  - data/processed/Dim_Parroquia_Maestro.csv
  - data/processed/manifest.json                   (se actualiza SOLO si todo lo de arriba salió bien)

Gotchas heredados del notebook (no son intuitivos, ver justificación en README/notebook):
  - Los 6 CSV crudos no usan el mismo separador (5 usan ';', el ciclo 2021-2022 usa ',').
  - Solo se queda estado_eval == "2" (evaluado); "1" es ausente, sin puntaje válido.
  - Los puntajes traen valores basura (999999, "-", etc.) que hay que convertir a NaN.
  - Los códigos de cantón/parroquia pierden el cero inicial al leer el Excel/ODS
    (zfill los restaura).
"""

import json
import os
import sys
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
CAMBIOS_PATH = os.path.join(RAW_DIR, "cambios_detectados.json")
MANIFEST_PATH = os.path.join(PROCESSED_DIR, "manifest.json")

COLUMNAS_SELECCIONADAS = [
    "ciclo",
    "nm_regi", "id_zona", "id_prov", "id_cant", "id_parr",
    "amie", "sostenimiento", "financiamiento", "tp_area",
    "grado", "estado_eval", "tp_sexo", "na_eano", "etnibee", "quintil", "isec",
    "inev", "imat", "ilyl", "icn", "ies",
    "nl_imat", "nl_ilyl", "nl_icn", "nl_ies",
]
PUNTAJES = ["inev", "imat", "ilyl", "icn", "ies", "isec"]
BASURA = {"999999", "999998", "9999", "-", ""}


def detectar_separador(ruta: str) -> str:
    with open(ruta, "r", encoding="utf-8-sig", errors="replace") as f:
        primera_linea = f.readline()
    return ";" if primera_linea.count(";") >= primera_linea.count(",") else ","


def cargar_lista_archivos():
    """Lee cambios_detectados.json (lo escribió descargar.py) y separa
    los archivos en 'resultado' (CSV) y 'diccionario' (ODS)."""
    if not os.path.exists(CAMBIOS_PATH):
        sys.exit("No hay data/raw/cambios_detectados.json. Corre descargar.py primero.")
    with open(CAMBIOS_PATH, "r", encoding="utf-8") as f:
        cambios = json.load(f)

    resultados = [info["ruta_local"] for info in cambios.values() if info["tipo"] == "resultado"]
    diccionarios = [info["ruta_local"] for info in cambios.values() if info["tipo"] == "diccionario"]
    return cambios, sorted(resultados), sorted(diccionarios)


def unificar_resultados(archivos_csv: list) -> pd.DataFrame:
    """Replica los Pasos 1, 5, 6, 7 y 9 del notebook: detectar separador,
    filtrar evaluados, seleccionar columnas, concatenar y limpiar puntajes."""
    dfs = []
    for ruta in archivos_csv:
        sep = detectar_separador(ruta)
        df_raw = pd.read_csv(ruta, sep=sep, encoding="utf-8-sig", dtype=str, low_memory=False)

        df_eval = df_raw[df_raw["estado_eval"] == "2"].copy()
        cols_disponibles = [c for c in COLUMNAS_SELECCIONADAS if c in df_eval.columns]
        df_sel = df_eval[cols_disponibles].copy()

        ciclo = df_sel["ciclo"].iloc[0] if "ciclo" in df_sel.columns and len(df_sel) else "?"
        print(f"  {ciclo}: {len(df_raw):,} total -> {len(df_eval):,} evaluados "
              f"({len(cols_disponibles)}/{len(COLUMNAS_SELECCIONADAS)} columnas)")
        dfs.append(df_sel)

    df_unificado = pd.concat(dfs, ignore_index=True)

    for col in PUNTAJES:
        if col in df_unificado.columns:
            serie = df_unificado[col].str.replace(",", ".", regex=False)
            serie = serie.where(~df_unificado[col].isin(BASURA))
            serie = pd.to_numeric(serie, errors="coerce")
            serie.loc[serie >= 999990] = None
            df_unificado[col] = serie

    return df_unificado


def consolidar_catalogo(archivos_ods: list, hoja: str, ancho_padding: int,
                         nombre_clave: str, nombre_valor: str) -> pd.DataFrame:
    """Replica el Paso 12: combina la misma hoja de los N diccionarios en un
    catálogo único, restaurando ceros iniciales perdidos y sin duplicados."""
    frames = []
    for archivo in archivos_ods:
        d = pd.read_excel(archivo, sheet_name=hoja, engine="odf")
        d = d.iloc[:, [0, 1]]
        d.columns = [nombre_clave, nombre_valor]
        frames.append(d)

    combinado = pd.concat(frames, ignore_index=True).dropna(subset=[nombre_clave])
    combinado[nombre_clave] = (
        combinado[nombre_clave].astype(str)
        .str.replace(r"\.0$", "", regex=True)
        .str.strip()
        .str.zfill(ancho_padding)
    )
    return combinado.drop_duplicates(subset=nombre_clave, keep="first").reset_index(drop=True)


def main():
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    cambios, archivos_csv, archivos_ods = cargar_lista_archivos()

    print(f"Unificando {len(archivos_csv)} archivos de resultados...")
    df_unificado = unificar_resultados(archivos_csv)
    print(f"Total: {len(df_unificado):,} filas x {len(df_unificado.columns)} columnas")

    ruta_hecho = os.path.join(PROCESSED_DIR, "serestudiante_consolidado.csv")
    df_unificado.to_csv(ruta_hecho, index=False, encoding="utf-8-sig")
    print(f"Guardado: {ruta_hecho}")

    print(f"\nConsolidando catálogos de {len(archivos_ods)} diccionarios...")
    dim_institucion = consolidar_catalogo(archivos_ods, "Instituciones_Educativas", 0, "amie", "nombre_institucion")
    dim_canton = consolidar_catalogo(archivos_ods, "Cantón", 4, "id_cant", "nombre_canton")
    dim_parroquia = consolidar_catalogo(archivos_ods, "Parroquia", 6, "id_parr", "nombre_parroquia")

    dim_institucion.to_csv(os.path.join(PROCESSED_DIR, "Dim_Institucion_Maestro.csv"), index=False, encoding="utf-8-sig")
    dim_canton.to_csv(os.path.join(PROCESSED_DIR, "Dim_Canton_Maestro.csv"), index=False, encoding="utf-8-sig")
    dim_parroquia.to_csv(os.path.join(PROCESSED_DIR, "Dim_Parroquia_Maestro.csv"), index=False, encoding="utf-8-sig")
    print(f"  Instituciones: {len(dim_institucion):,} | Cantones: {len(dim_canton):,} | Parroquias: {len(dim_parroquia):,}")

    # Solo si todo lo anterior salió bien, confirmamos el manifest.
    manifest_nuevo = {rid: {"last_modified": info["last_modified"], "nombre": info["nombre"]}
                       for rid, info in cambios.items()}
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest_nuevo, f, ensure_ascii=False, indent=2)
    print(f"\nmanifest.json actualizado ({len(manifest_nuevo)} recursos confirmados).")


if __name__ == "__main__":
    main()
