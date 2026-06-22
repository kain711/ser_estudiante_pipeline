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
- [x] Workflow de GitHub Actions (cron mensual + disparo manual) — `.github/workflows/pipeline.yml` (ver nota de automatización abajo)
- [ ] Dashboard Streamlit
- [ ] Deploy en Streamlit Community Cloud

## Nota sobre la automatización

El plan original era 100% automático con GitHub-hosted runners. Se descartó por tres bloqueos en cadena, documentados aquí porque son una lección real de ingeniería de datos:

1. **Bloqueo por IP/ASN del lado del INEVAL**: el portal `datosabiertos.gob.ec` responde `403 Forbidden` (Apache plano, sin desafío JS) a las IPs de datacenter de los runners de GitHub-hosted. Confirmado con diagnóstico de headers/body de la respuesta.
2. **Self-hosted runner como alternativa**: correr el runner en la laptop local resuelve el bloqueo de IP (usa la IP residencial), pero...
3. **Windows Smart App Control** (activo y no reversible sin reinstalar el SO) bloquea la carga del ensamblado `.dll` del runner con `FileLoadException`.

**Decisión final:** el pipeline (`descargar.py` + `procesar.py`) se ejecuta manualmente. Conserva toda la lógica de detección de cambios (no reprocesa si no hay novedades en la fuente), así que el costo de correrlo "de más" es mínimo. El workflow de GitHub Actions se deja en el repo como referencia/documentación de CI-CD, pero no se ejecuta de forma desatendida.

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
