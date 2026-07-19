# Sistema Inteligente de Análisis Automatizado y Exploratorio de Datos

Backend de análisis inteligente de datos tabulares (CSV/Excel) para el curso
**SC-250 Paradigmas de Programación**. Este repositorio contiene la **parte de
Julian**: carga de datos, perfilado, análisis estadístico y algoritmos de
Machine Learning. El frontend (Jose) y la integración (Rachel) se conectan a
través de una API pública sencilla.

## ¿Qué hace?

A partir de un archivo, de forma automática:

- Carga y valida archivos **CSV, TSV y Excel**.
- **Detecta el tipo** de cada variable (numérica, categórica, temporal, booleana, texto).
- Calcula **correlaciones** de Pearson y Spearman y encuentra pares fuertes.
- Mide **dependencias** categórica → numérica (eta cuadrado).
- Agrupa registros con **K-Means** y **DBSCAN** (eligiendo parámetros solo).
- Detecta **valores atípicos** con **Z-Score**, **IQR** e **Isolation Forest**.
- Genera **insights en lenguaje natural** que explican los hallazgos.

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Uso

### Como librería (lo que usa el frontend)

```python
from smarteda import AnalysisEngine

engine = AnalysisEngine()
report = engine.analyze("data/samples/clientes.csv")

for insight in report.insights:
    print(insight.message)

# Uno o varios archivos a la vez:
reports = engine.analyze_many(["ventas.csv", "clientes.xlsx"])
```

### Desde la terminal

```bash
python -m smarteda data/samples/clientes.csv
python -m smarteda data/samples/clientes.csv --algorithm dbscan
python -m smarteda ventas.csv clientes.xlsx        # uno o varios archivos
```

## Estructura del proyecto

```
sistema-analisis-inteligente/
├── smarteda/                 # paquete del backend
│   ├── __init__.py           # API pública
│   ├── __main__.py           # interfaz de línea de comandos
│   ├── config.py             # AnalysisConfig
│   ├── exceptions.py         # errores propios
│   ├── logger.py             # logging básico
│   ├── models.py             # DTOs, enums y contrato de integración
│   ├── ingestion.py          # carga + validación de archivos
│   ├── profiling.py          # detección de tipos y perfilado
│   ├── preprocessing.py      # imputación, escalado, PCA 2D
│   ├── insights.py           # insights en lenguaje natural
│   ├── engine.py             # AnalysisEngine (orquestador)
│   └── analysis/
│       ├── correlation.py    # Pearson/Spearman + dependencias
│       ├── clustering.py     # K-Means + DBSCAN
│       └── anomaly.py        # Z-Score + IQR + Isolation Forest
├── app/                      # frontend de Jose (andamio)
├── data/samples/             # datasets de prueba
├── docs/api_contract.md      # contrato para el equipo
├── tests/                    # pruebas unitarias e integración
├── requirements.txt
└── pyproject.toml
```

## Pruebas

```bash
pytest
```

## Integración con el equipo

El backend expone un único objeto, `AnalysisEngine`, que devuelve un
`AnalysisReport` con todos los datos listos para graficar y mostrar. El contrato
completo (qué campos usar para cada gráfico, cómo conectar la estadística
descriptiva de Rachel) está en [`docs/api_contract.md`](docs/api_contract.md).

## Decisiones técnicas

- **Python + pandas + scikit-learn + scipy**: es lo asignado en la división de
  trabajo y el ecosistema estándar de ML. Sin base de datos, Docker ni servicios
  externos, por las limitaciones de la propuesta (sin tiempo real ni persistencia).
- **Arquitectura en capas simple**: ingestión → perfilado → análisis → insights,
  orquestadas por un motor. Cada análisis en su módulo (alta cohesión).
- **Interfaz común para clustering y anomalías**: permite intercambiar y agregar
  algoritmos sin tocar los existentes.
- **Selección automática de parámetros** (k por silhouette, eps por la rodilla de
  k-distancias) para que el sistema sea "inteligente" sin configuración manual.
- **`random_state` fijo** para resultados reproducibles en la presentación.
