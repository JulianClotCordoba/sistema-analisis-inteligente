# app/ — Frontend SmartEDA

Dashboard construido con **Streamlit**. Consume la API pública del backend sin
modificar el paquete `smarteda`.

## Estado actual

La aplicación ya incluye:

1. Carga de CSV, TSV, TXT y Excel.
2. Selección opcional entre K-Means y DBSCAN.
3. Ejecución de `AnalysisEngine`.
4. Conservación del `AnalysisReport` en la sesión.
5. Resumen de filas, variables, faltantes, hallazgos y tipos detectados.
6. Manejo amigable de errores.
7. Pantalla de Relaciones con:
   - selector Pearson/Spearman;
   - relaciones fuertes explicadas en lenguaje cotidiano;
   - heatmap interactivo;
   - dependencias categóricas representadas como porcentajes;
   - estados vacíos para datasets sin suficientes variables.
8. Pantalla de Segmentos con mapa, tamaños, silhouette y explicación de métodos.
9. Pantalla de Datos inusuales con comparación Z-Score/IQR/Isolation Forest,
   mapa de señales, consenso y prioridad de revisión.

La vista de Reporte se agregará progresivamente.

## Instalación local

Desde la raíz del repositorio:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Ejecución

```powershell
python -m streamlit run app\main.py
```

Streamlit mostrará una dirección local, normalmente `http://localhost:8501`.
La terminal debe permanecer abierta mientras se usa la aplicación.

## Cómo se conecta con el backend de Julián

```python
from smarteda import AnalysisConfig, AnalysisEngine

config = AnalysisConfig(clustering_algorithm="kmeans")
engine = AnalysisEngine(config)
report = engine.analyze(archivo_subido)
```

En la pantalla actual:

- `report.profile` alimenta la tabla de variables y sus tipos.
- `report.metadata` proporciona filas, columnas y duración.
- `report.insights` proporciona los hallazgos en lenguaje natural.
- `AnalysisConfig` permite seleccionar K-Means o DBSCAN.
- La pantalla **Segmentos** utiliza las etiquetas, tamaños, calidad y proyección
  que devuelve el backend para mostrar los grupos sin recalcular el clustering.
- La pantalla **Datos inusuales** compara las máscaras ya generadas por los tres
  detectores y las ubica sobre la proyección del backend.

Las próximas pantallas utilizarán:

```python
report.correlations["pearson"].matrix  # heatmap
report.clustering.projection_2d        # dispersión de segmentos
report.clustering.labels               # color de cada registro
report.anomalies[0].outlier_mask       # registros atípicos
```

El contrato completo está en
[`docs/api_contract.md`](../docs/api_contract.md).

## Estilos

Streamlit maneja la estructura y los componentes. La identidad visual vive en
`app/assets/styles.css` y el tema global en `.streamlit/config.toml`.
No se usa Tailwind porque requeriría una cadena de compilación separada y no
aporta una ventaja clara dentro del DOM administrado por Streamlit.
