# Guía del frontend de SmartEDA

## 1. Introducción, carga de datos e integración con el backend

Esta guía explica cómo se construyó la interfaz de SmartEDA y cómo utiliza el
motor de análisis desarrollado por Julián. Está pensada para que cualquier
integrante del equipo pueda seguir el recorrido de los datos y, cuando necesite
más detalle, abrir directamente la parte correspondiente del código.

> **Alcance de este capítulo:** arquitectura general, tecnologías, configuración
> del frontend, carga del archivo y contrato con el backend. La construcción de
> las tarjetas, el gráfico de composición y la tabla de variables se explicará
> con detalle en el capítulo 2, **Resumen**.

### Navegación de la guía

1. **Introducción, carga de datos e integración** — este documento.
2. [**Resumen**](02-resumen.md) — indicadores, hallazgos, composición y variables detectadas.
3. [**Relaciones**](03-relaciones.md) — correlaciones, dependencias, visualizaciones y orientación.
4. [**Segmentos**](04-segmentos.md) — algoritmos, mapa de similitud, tamaños y calidad.
5. [**Datos inusuales**](05-datos-inusuales.md) — detectores, consenso, mapa y prioridad.
6. [**Reporte**](06-reporte.md) — cierre ejecutivo, recomendaciones y PDF descargable.

## ¿Qué es SmartEDA?

SmartEDA recibe un archivo con datos tabulares y produce automáticamente una
primera lectura de su estructura y sus patrones. El usuario no tiene que saber
qué algoritmo ejecutar ni preparar gráficos manualmente: selecciona un archivo,
elige opcionalmente un método de segmentación y consulta los resultados desde
seis pantallas.

El sistema puede:

- cargar y validar archivos CSV, TSV, TXT y Excel;
- identificar variables numéricas, categóricas, temporales, booleanas y de texto;
- calcular relaciones entre variables;
- encontrar segmentos o grupos de registros;
- señalar datos que podrían ser inusuales;
- traducir resultados técnicos a hallazgos en lenguaje sencillo; y
- reunir los resultados en un reporte descargable.

La navegación de estas pantallas se define en
[`render_sidebar()`](../../app/main.py#L102-L172). Las pantallas de resultados
permanecen deshabilitadas hasta que exista un análisis, lo que evita que el
usuario entre en una sección que todavía no tiene datos para mostrar.

## Arquitectura: una aplicación, dos responsabilidades

Aunque se habla de *frontend* y *backend*, en esta versión no existe un servidor
web ni una API HTTP entre ambos. Las dos partes se ejecutan dentro del mismo
proceso de Python:

```text
Usuario
   │
   │ selecciona un archivo
   ▼
Frontend de Streamlit (`app/`)
   │
   │ llama a `AnalysisEngine.analyze(archivo)`
   ▼
Motor de Julián (`smarteda/`)
   │
   │ devuelve un objeto `AnalysisReport`
   ▼
Frontend transforma sus campos en tarjetas, tablas y gráficos
```

Aquí la palabra **API** significa la interfaz pública de la librería Python:
los objetos que otra parte del proyecto puede importar y utilizar. Los objetos
públicos están expuestos desde [`smarteda/__init__.py`](../../smarteda/__init__.py#L19-L52).

Esta separación permite que el frontend se concentre en presentar los datos y
que el backend se encargue de todos los cálculos. Por ejemplo, el frontend no
vuelve a calcular correlaciones ni grupos; solamente lee los resultados que ya
vienen en el reporte.

## ¿Qué se tomó del trabajo de Julián?

La integración aprovecha cuatro elementos principales del backend:

1. **`AnalysisConfig`**: concentra las opciones del análisis. El frontend lo
   utiliza para enviar la elección entre K-Means y DBSCAN. Sus valores
   predeterminados están en
   [`smarteda/config.py`](../../smarteda/config.py#L13-L41).
2. **`AnalysisEngine`**: es el punto de entrada que recibe el archivo, coordina
   todas las etapas y devuelve el resultado. La secuencia completa puede verse
   en [`AnalysisEngine.analyze()`](../../smarteda/engine.py#L59-L101).
3. **`AnalysisReport`**: es el contrato común que organiza todo lo producido por
   el motor. Su definición está en
   [`smarteda/models.py`](../../smarteda/models.py#L135-L146).
4. **Las excepciones de SmartEDA**: permiten que el frontend convierta un error
   técnico de lectura o validación en un mensaje comprensible para el usuario.

En términos sencillos, Julián construyó el **motor y el formato de salida**. El
frontend construyó la experiencia alrededor de ellos: carga, opciones,
navegación, estado de la sesión, manejo visual de errores, tablas, gráficos y
reporte final.

## Tecnologías utilizadas en el frontend

| Tecnología | Uso dentro del frontend |
|---|---|
| **Python** | Permite consumir directamente el paquete `smarteda`, sin traducir los resultados a JSON ni mantener otro servidor. |
| **Streamlit** | Construye la página, la barra lateral, botones, selector de archivos, tarjetas y tablas. |
| **Plotly** | Genera los gráficos interactivos que aparecen en las pantallas de resultados. |
| **pandas** | Convierte colecciones del reporte en tablas que Streamlit puede mostrar. |
| **CSS** | Define la identidad visual: colores, tipografía, espacios, tarjetas y estados. |

Las dependencias están declaradas en
[`requirements.txt`](../../requirements.txt#L12-L15). Streamlit actúa como el
marco principal del frontend, mientras que Plotly se especializa en las
visualizaciones. De esta forma no fue necesario agregar una aplicación separada
en React, Vue o JavaScript.

## Configuración básica del frontend

El archivo central es [`app/main.py`](../../app/main.py). Su función `main()`
realiza tres pasos antes de decidir qué pantalla mostrar:

1. configura la página;
2. inicializa el estado de la sesión; y
3. dibuja la navegación lateral.

Este punto de entrada y la selección de vistas están en
[`main()`](../../app/main.py#L474-L506).

### 1. Acceso al paquete del backend

Al ejecutar Streamlit desde la raíz, el frontend agrega la carpeta del proyecto
a la ruta de importación de Python. Después importa `AnalysisConfig` y
`AnalysisEngine` desde la interfaz pública de `smarteda`. Esta preparación se
encuentra en [`app/main.py`](../../app/main.py#L22-L33).

Esto no modifica el backend. Solamente hace que Python pueda encontrarlo cuando
la aplicación se inicia con `streamlit run app/main.py`.

### 2. Ventana, tema y estilos

[`configure_page()`](../../app/main.py#L58-L70) establece el título, el ícono, el
ancho de la página y el estado inicial de la barra lateral. La configuración
global de colores también se encuentra en
[`.streamlit/config.toml`](../../.streamlit/config.toml), y los estilos propios
se cargan desde [`app/assets/styles.css`](../../app/assets/styles.css).

Streamlit genera los componentes y la estructura base; el CSS ajusta su
apariencia. Cuando se necesita una composición visual más específica, se envía
una pequeña estructura HTML mediante `st.markdown`. Los textos dinámicos, como
el nombre del archivo o un hallazgo, se escapan antes con `html.escape` para no
interpretarlos como HTML accidentalmente.

### 3. Estado de la sesión

Streamlit vuelve a ejecutar el archivo cuando el usuario interactúa con un
control. Por eso [`initialize_state()`](../../app/main.py#L73-L83) guarda cuatro
datos que deben sobrevivir a esas ejecuciones:

| Clave | Qué conserva |
|---|---|
| `view` | La pantalla que el usuario está visitando. |
| `report` | El `AnalysisReport` devuelto por el backend. |
| `active_file` | El nombre del archivo analizado. |
| `selected_algorithm` | El método de segmentación elegido. |

El dato más importante es `report`. Una vez almacenado, las distintas pantallas
pueden reutilizar el mismo análisis sin volver a procesar el archivo.

## ¿Cómo se carga y analiza un archivo?

La pantalla inicial se construye en
[`render_upload_view()`](../../app/main.py#L256-L305). Su flujo es el siguiente:

### Paso 1: selección

`st.file_uploader` crea el control de carga y restringe las extensiones visibles
a CSV, TSV, TXT, XLSX y XLS. Streamlit entrega el archivo como un objeto en
memoria; no es necesario guardarlo primero en una carpeta.

También existe el botón **Usar datos de ejemplo**, que envía al mismo flujo la
ruta [`data/samples/clientes.csv`](../../data/samples/clientes.csv). Así, la
demostración y un archivo aportado por el usuario recorren la misma lógica.

### Paso 2: configuración opcional

Dentro de **Opciones avanzadas**, un botón de selección permite escoger:

- **K-Means**, que asigna todos los registros a un grupo; o
- **DBSCAN**, que también puede dejar fuera los registros que no encajan bien en
  ningún grupo.

La selección no ejecuta el algoritmo en el frontend. Solamente se utiliza para
crear un `AnalysisConfig` que será entregado al motor. El control puede verse en
[`app/main.py`](../../app/main.py#L272-L287).

### Paso 3: conexión con el motor

Al presionar **Analizar archivo**, el frontend llama a
[`analyze_source()`](../../app/main.py#L175-L202). Esta función:

1. coloca el cursor del archivo al inicio;
2. crea la configuración con el algoritmo seleccionado;
3. crea una instancia de `AnalysisEngine`;
4. llama a `engine.analyze(source)` mientras muestra un indicador de carga;
5. guarda el reporte, el nombre y la configuración en la sesión; y
6. cambia automáticamente a la pantalla **Resumen**.

El llamado esencial puede resumirse así:

```python
config = AnalysisConfig(clustering_algorithm=algorithm)
engine = AnalysisEngine(config)
report = engine.analyze(source)
```

Estas son las únicas líneas necesarias para montar el motor de Julián dentro del
frontend. El resto de `analyze_source()` se ocupa de la experiencia del usuario
y del estado de Streamlit.

### Paso 4: lectura y validación en el backend

El motor pasa el archivo a
[`load_dataset()`](../../smarteda/ingestion.py#L58-L105). Esta función identifica
la extensión, comprueba que el formato sea admitido, utiliza pandas para leer el
contenido y verifica que el resultado tenga al menos una fila y una columna.

Los CSV, TSV y TXT se leen con `pandas.read_csv`; los archivos de Excel se leen
con `pandas.read_excel`. Después, `AnalysisEngine` ejecuta en orden:

1. carga y limpieza básica;
2. perfilado y detección de tipos;
3. correlaciones y dependencias;
4. segmentación;
5. detección de anomalías;
6. estadística descriptiva, si hay un proveedor conectado; y
7. generación de hallazgos en lenguaje natural.

La orquestación está concentrada en
[`smarteda/engine.py`](../../smarteda/engine.py#L73-L101). Gracias a esto, el
frontend recibe un solo objeto en lugar de coordinar cada algoritmo por separado.

### Paso 5: manejo de errores

Si el backend reconoce un archivo vacío, un formato no soportado u otro problema
de validación, genera una excepción propia de SmartEDA. El frontend la captura y
muestra una explicación corta, además de dejar el detalle técnico dentro de un
panel desplegable. También existe una protección para errores inesperados. Este
manejo se encuentra en [`analyze_source()`](../../app/main.py#L184-L196).

## ¿Qué devuelve el backend?

`engine.analyze()` devuelve un **`AnalysisReport`**. Es importante aclarar que el
reporte no contiene métodos para dibujar pantallas: es una estructura de datos
con atributos. El frontend lee esos atributos y decide cómo presentarlos.

| Campo del reporte | Contenido | Pantalla que lo aprovecha |
|---|---|---|
| `profile` | Cantidad de filas y columnas, tipo, faltantes, valores únicos y ejemplos de cada variable. | Resumen |
| `correlations` | Matrices Pearson y Spearman, más las relaciones fuertes. | Relaciones |
| `dependencies` | Influencia de variables categóricas sobre variables numéricas. | Relaciones |
| `clustering` | Algoritmo, etiquetas, cantidad y tamaño de grupos, calidad y coordenadas 2D. | Segmentos |
| `anomalies` | Resultado de Z-Score, IQR e Isolation Forest, con una marca por registro. | Datos inusuales |
| `descriptive` | Estadísticas descriptivas, si se conectó el proveedor correspondiente. | Reporte o futuras vistas |
| `insights` | Hallazgos redactados en español, con categoría y nivel de importancia. | Resumen y Reporte |
| `metadata` | Archivo de origen, dimensiones, fecha y tiempo de ejecución. | Resumen y Reporte |

Las definiciones completas de estas estructuras están en
[`smarteda/models.py`](../../smarteda/models.py#L23-L146). Este archivo es el
contrato más importante para comprender cómo se comunican el frontend y el
backend.

## Primera conexión con la pantalla Resumen

Después de un análisis exitoso, `analyze_source()` cambia `view` a `"Resumen"`.
La función principal detecta ese valor y llama a
[`render_summary_view()`](../../app/main.py#L385-L471).

Esta pantalla utiliza principalmente tres partes del reporte:

- `report.profile`, para dimensiones, faltantes y tipos de variables;
- `report.metadata`, para el tiempo de análisis; y
- `report.insights`, para los hallazgos explicados al usuario.

No vuelve a ejecutar ningún algoritmo. Su responsabilidad es transformar esos
datos en cuatro tarjetas, una lista de hallazgos, un gráfico de composición y
una tabla de variables. El capítulo **Resumen** explicará cómo se construye cada
elemento y de qué atributo exacto sale su valor.

## Cómo ejecutar el frontend

Desde la raíz del proyecto:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app\main.py
```

Streamlit mostrará una dirección local, normalmente `http://localhost:8501`.
Mientras la aplicación esté abierta, el reporte vive en la sesión; esta versión
no guarda el archivo ni los resultados en una base de datos.

## Ideas clave para explicar esta parte

- El backend de Julián se integró como una **librería Python**, no mediante una
  petición HTTP.
- `AnalysisEngine.analyze()` es el punto de entrada del análisis.
- `AnalysisReport` es el contrato que entrega todos los resultados al frontend.
- El frontend no repite los cálculos: transforma el reporte en una experiencia
  visual y comprensible.
- `st.session_state` permite compartir el mismo reporte entre las seis pantallas.
- La selección del algoritmo solamente configura la segmentación; el resto del
  análisis sigue el mismo flujo.

## Documentación relacionada

- [Contrato original de integración](../api_contract.md)
- [Descripción y ejecución de la aplicación](../../app/README.md)
- [Descripción general del proyecto](../../README.md)
