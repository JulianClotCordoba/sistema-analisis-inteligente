# Contrato de integración (backend de Julian)

Este es el único documento que Jose, Rachel y Shernna necesitan para integrarse.
Mientras estos tipos no cambien, cada quien puede trabajar en paralelo sin tocar
el código interno del backend.

## Punto de entrada

```python
from smarteda import AnalysisEngine, AnalysisConfig

engine = AnalysisEngine(config=None, descriptive_provider=None)
report = engine.analyze(source)   # source: ruta (str/Path) o archivo (Streamlit)
```

- `analyze()` devuelve un **`AnalysisReport`** o lanza una subclase de
  `SmartEdaError` si el archivo es inválido.
- `analyze_many(sources)` acepta **uno o varios** archivos y devuelve
  `dict[str, AnalysisReport]` (uno por archivo). Los archivos con error se
  omiten sin detener el resto.

## `AnalysisReport` (lo que se entrega)

| Campo | Tipo | Descripción |
|---|---|---|
| `profile` | `DatasetProfile` | filas, columnas y tipo de cada variable |
| `correlations` | `dict[str, CorrelationResult]` | claves `"pearson"` / `"spearman"` |
| `dependencies` | `list[CategoricalDependency]` | categórica → numérica (eta²) |
| `clustering` | `ClusteringResult \| None` | etiquetas, nº de grupos, proyección 2D |
| `anomalies` | `list[AnomalyResult]` | una por método (zscore, iqr, isolation_forest) |
| `descriptive` | `DescriptiveResult \| None` | lo llena el proveedor de Rachel |
| `insights` | `list[Insight]` | frases en español listas para mostrar |
| `metadata` | `dict` | fuente, tamaño, fecha, tiempo |

## Datos clave para graficar (Jose)

- **Heatmap de correlación:** `report.correlations["pearson"].matrix` (DataFrame).
- **Scatter de clusters:** `report.clustering.projection_2d` (coords) coloreado por
  `report.clustering.labels`.
- **Atípicos:** `report.anomalies[i].outlier_mask` (booleano por fila) para
  resaltar en boxplots/dispersión.
- **Panel de texto:** `report.insights` → `insight.message`, `insight.severity`.

## Contrato para Rachel (estadística descriptiva)

Basta con crear una clase con este método y pasarla al motor:

```python
class BasicDescriptiveStats:
    def compute(self, df, profile) -> DescriptiveResult:
        ...

engine = AnalysisEngine(descriptive_provider=BasicDescriptiveStats())
```

El motor la invoca automáticamente y coloca el resultado en `report.descriptive`.

## Configuración (opcional)

`AnalysisConfig` permite cambiar algoritmo de clustering (`"kmeans"`/`"dbscan"`),
umbral de correlación, métodos de anomalías, `random_state`, etc. Todos los
valores tienen un defecto sensato.
