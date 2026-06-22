# ser_estudiante_pipeline

Pipeline de datos + dashboard para los resultados de la evaluación **Ser Estudiante** (INEVAL, Ecuador). Proyecto de portafolio personal: descarga y procesamiento automatizado de los datos abiertos del INEVAL, con un dashboard en Streamlit como capa de visualización.

Dataset fuente: [datosabiertos.gob.ec/dataset/ser-estudiante](https://datosabiertos.gob.ec/dataset/ser-estudiante)

## Estructura

```
ser_estudiante_pipeline/
├── pipeline/           # scripts de descarga y procesamiento
├── app/                # dashboard Streamlit
├── data/
│   ├── raw/            # datos crudos descargados (no versionado)
│   └── processed/      # CSV consolidado + dimensiones (sí versionado, lo lee la app)
├── .github/workflows/  # automatización (GitHub Actions, cron mensual)
└── requirements.txt
```

## Estado del proyecto

- [x] Estructura del repo
- [x] Confirmar URLs de descarga estables en datosabiertos.gob.ec (API CKAN `package_show`, actualización anual confirmada)
- [x] Script de descarga con detección de cambios (`pipeline/descargar.py`)
- [x] Script de procesamiento (`pipeline/procesar.py`) — verificado contra los datos reales (222,103 filas, promedio INEV 687.62)
- [x] Workflow de GitHub Actions (cron mensual + disparo manual) — `.github/workflows/pipeline.yml`
- [ ] Dashboard Streamlit
- [ ] Deploy en Streamlit Community Cloud

## Cómo correr el pipeline localmente

```bash
pip install -r requirements.txt
python pipeline/descargar.py
python pipeline/procesar.py
```

## Cómo correr el dashboard localmente

```bash
streamlit run app/streamlit_app.py
```
