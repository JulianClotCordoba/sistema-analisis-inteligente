# app/ — Frontend (Jose)

Esta carpeta está reservada para el **dashboard / interfaz** (Jose). El backend
ya expone todo lo necesario; el frontend solo consume la API pública y **no
debe modificar** el paquete `smarteda`.

## Cómo conectarse al backend

```python
from smarteda import AnalysisEngine

engine = AnalysisEngine()
report = engine.analyze(archivo_subido)   # ruta o archivo de Streamlit

# Datos listos para graficar (sin recalcular nada):
report.correlations["pearson"].matrix     # -> heatmap
report.clustering.projection_2d           # coords 2D -> scatter
report.clustering.labels                  # color por cluster
report.anomalies[0].outlier_mask          # resaltar atípicos (boxplot)
report.insights                           # frases para el panel de texto
```

Consulta el contrato completo en [`docs/api_contract.md`](../docs/api_contract.md).
