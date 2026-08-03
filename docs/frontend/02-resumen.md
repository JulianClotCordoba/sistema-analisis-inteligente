# 2. Pantalla Resumen

[← Volver a Introducción, carga de datos e integración](README.md)

## Objetivo de la pantalla

**Resumen** es la primera pantalla que aparece después de analizar correctamente
un archivo. Su propósito es ofrecer una lectura rápida del conjunto de datos
antes de que el usuario visite análisis más específicos como Relaciones,
Segmentos o Datos inusuales.

La pantalla responde cuatro preguntas iniciales:

1. ¿Qué archivo se analizó y cuánto tardó?
2. ¿Cuántos registros, variables, valores faltantes y hallazgos existen?
3. ¿Qué tipos de variables detectó el motor?
4. ¿Qué aspectos del archivo conviene revisar primero?

Toda la pantalla se construye en
[`render_summary_view()`](../../app/main.py#L385-L471). Esta función no vuelve a
leer el archivo ni ejecuta algoritmos. Utiliza el `AnalysisReport` que fue
guardado previamente en `st.session_state.report`.

## Flujo de datos

```text
AnalysisEngine.analyze(archivo)
              │
              ▼
       AnalysisReport
              │
      ┌───────┼───────────┐
      ▼       ▼           ▼
   profile  metadata   insights
      │       │           │
      ▼       ▼           ▼
 tarjetas,  archivo y   hallazgos
 gráfico y  duración    explicados
 tabla
```

La relación entre los datos recibidos y los componentes visuales es la siguiente:

| Dato de origen | Transformación del frontend | Resultado visible |
|---|---|---|
| `st.session_state.active_file` | Se convierte a texto seguro. | Nombre del archivo. |
| `report.metadata["elapsed_seconds"]` | Se muestra con tres decimales. | Duración del análisis. |
| `report.profile.n_rows` | Se formatea con separador de miles. | Tarjeta **Registros**. |
| `report.profile.n_cols` | Se usa directamente. | Tarjeta **Variables**. |
| `column.missing_count` | Se suman los faltantes de todas las columnas. | Tarjeta **Valores faltantes**. |
| `report.insights` | Se cuenta la lista y se toman inicialmente cuatro elementos. | Tarjeta y panel de **Hallazgos**. |
| Listas de tipos de `report.profile` | Se cuenta cuántas columnas hay en cada grupo. | Gráfico de composición. |
| `report.profile.columns` | Se recorre y se crea un diccionario por columna. | Tabla de variables detectadas. |

## 1. Obtención y validación del reporte

Al iniciar la función, el frontend recupera el reporte desde el estado de la
sesión. Si por alguna razón no existe, muestra el mensaje **“Primero debes
analizar un archivo”** y detiene la construcción de la pantalla. Esta protección
está en [`app/main.py`](../../app/main.py#L385-L390).

Normalmente el usuario no encuentra este estado vacío, porque el botón Resumen
permanece deshabilitado hasta que el motor termina un análisis. Además,
[`analyze_source()`](../../app/main.py#L198-L202) guarda el reporte y dirige la
navegación automáticamente a esta pantalla.

## 2. Encabezado del archivo analizado

La primera sección confirma qué archivo produjo los resultados y cuánto tardó
el motor. Utiliza dos fuentes:

- `st.session_state.active_file`, que conserva el nombre seleccionado; y
- `report.metadata.get("elapsed_seconds", 0)`, que contiene la duración medida
  por el backend.

La implementación está en [`app/main.py`](../../app/main.py#L392-L407). Se usa
`.get(..., 0)` para que la pantalla pueda mostrar `0` como valor seguro si la
clave no estuviera disponible.

El nombre se procesa con `html.escape` antes de insertarlo en el bloque visual.
Esto evita que caracteres especiales presentes en un nombre de archivo sean
interpretados como etiquetas HTML.

La apariencia del bloque —borde, fondo, distribución horizontal y línea de
color— se define con las clases `.seda-file-line`, `.seda-file-name` y
`.seda-file-meta` en
[`app/assets/styles.css`](../../app/assets/styles.css#L229-L249).

## 3. Las cuatro tarjetas principales

La pantalla crea cuatro columnas del mismo tamaño con `st.columns(4)` y coloca
un componente `st.metric` dentro de cada una. La construcción puede consultarse
en [`app/main.py`](../../app/main.py#L409-L414).

### Registros

La tarjeta obtiene su valor de `report.profile.n_rows`. Representa la cantidad
de filas que quedaron disponibles después de la limpieza básica del backend.

Esto último es importante: antes de generar el perfil, el motor elimina filas
completamente vacías y duplicados exactos. Por tanto, el número puede ser menor
que el total de filas que tenía originalmente el archivo. La limpieza se define
en [`basic_clean()`](../../smarteda/cleaning.py#L35-L65).

### Variables

Utiliza `report.profile.n_cols` y representa la cantidad de columnas después de
la limpieza. Una columna completamente vacía puede ser eliminada por el motor y
no aparecer en este total.

### Valores faltantes

Este valor no existe como un único campo dentro del reporte. El frontend lo
calcula sumando `missing_count` de todos los perfiles de columna:

```python
total_missing = sum(column.missing_count for column in report.profile.columns)
```

En palabras sencillas, se recorre cada variable y se acumula la cantidad de
celdas vacías detectadas en ella. El resultado representa celdas faltantes, no
el número de filas que contienen algún faltante.

### Hallazgos

La cuarta tarjeta usa `len(report.insights)`. Muestra cuántos mensajes generó el
motor a partir del perfil, las relaciones, los segmentos y las anomalías.

Un hallazgo no equivale necesariamente a un error. También puede describir el
tamaño del conjunto, una relación interesante o la calidad de los segmentos.

Los estilos comunes de las cuatro tarjetas aprovechan los componentes métricos
de Streamlit y se personalizan en
[`app/assets/styles.css`](../../app/assets/styles.css#L831-L846).

## 4. Hallazgos: “Qué encontró SmartEDA”

El backend entrega los hallazgos como una lista de objetos `Insight`. Cada uno
tiene:

- `category`: origen del hallazgo;
- `message`: explicación lista para presentar; y
- `severity`: nivel `info` o `warning`.

Este contrato está definido en
[`smarteda/models.py`](../../smarteda/models.py#L126-L132). La lista puede
contener mensajes sobre el dataset, faltantes, correlaciones, dependencias,
segmentos y anomalías. El orden en que se generan esas categorías está en
[`InsightGenerator.generate()`](../../smarteda/insights.py#L30-L47).

### ¿Cómo se muestran?

La vista toma inicialmente los primeros cuatro elementos mediante
`report.insights[:4]`. Un ciclo `for` envía cada elemento a `render_insight()`:

```python
visible_insights = report.insights[:4]
for insight in visible_insights:
    render_insight(insight)
```

Esta lógica está en [`app/main.py`](../../app/main.py#L416-L425). Limitar la
primera vista a cuatro mensajes evita que una lista extensa desplace el resto
del resumen demasiado hacia abajo.

Si existen más de cuatro, se crea un panel desplegable que permite consultar la
lista completa. Ese panel está en [`app/main.py`](../../app/main.py#L438-L441).

### Diferencia visual de las advertencias

[`render_insight()`](../../app/main.py#L372-L382) revisa la propiedad `severity`.
Cuando su valor es `warning`, agrega la clase CSS
`.seda-insight-warning`; en cualquier otro caso utiliza el estilo normal.

Por ejemplo, el backend marca como advertencia una variable con más de 20 % de
datos faltantes y un detector de anomalías que señale más de 10 % de los
registros. Estas reglas pueden verse en
[`smarteda/insights.py`](../../smarteda/insights.py#L62-L78) y
[`smarteda/insights.py`](../../smarteda/insights.py#L149-L165).

Las tarjetas de hallazgo se estilizan en
[`app/assets/styles.css`](../../app/assets/styles.css#L251-L264). Nuevamente, el
mensaje se procesa con `html.escape` para mostrar como texto cualquier carácter
especial que venga del nombre de una variable.

## 5. Gráfico de composición

El gráfico permite ver rápidamente cuántas variables de cada tipo detectó el
backend. Se construye con **Plotly** en
[`build_variable_type_chart()`](../../app/main.py#L327-L369).

### De dónde salen los datos

El backend ya agrupó los nombres de las variables dentro de `report.profile`:

- `numeric_columns`;
- `categorical_columns`;
- `datetime_columns`;
- `boolean_columns`; y
- `text_columns`.

El frontend no vuelve a inferir los tipos. Solamente aplica `len()` a cada lista
para conocer el tamaño del grupo. La clasificación original se realiza en
[`DataProfiler.profile()`](../../smarteda/profiling.py#L35-L65), y la agrupación
se completa en
[`DataProfiler._group_by_type()`](../../smarteda/profiling.py#L127-L140).

### Cómo se construye el gráfico

La función prepara un diccionario de etiquetas y cantidades. Después elimina
los grupos cuyo valor sea cero y utiliza `go.Pie` para crear un gráfico circular
con un espacio central de 64 %, es decir, un gráfico de dona.

Plotly recibe:

- los nombres de los tipos como `labels`;
- sus cantidades como `values`;
- los colores definidos en `TYPE_COLORS`;
- el total de variables como anotación central; y
- una descripción interactiva que aparece al colocar el cursor.

La leyenda general se oculta porque cada sección del gráfico ya muestra su
nombre y cantidad. Al enviarlo a `st.plotly_chart`, también se oculta la barra de
herramientas y se activa el comportamiento adaptable al ancho disponible. La
integración del gráfico con Streamlit está en
[`app/main.py`](../../app/main.py#L426-L436).

Las variables clasificadas como `unknown` o **No identificado** aparecen en la
tabla, pero no forman parte de las cinco categorías representadas en esta dona.

## 6. Tabla de variables detectadas

La tabla muestra una fila por cada columna del dataset. La función
[`build_profile_table()`](../../app/main.py#L308-L324) transforma los objetos del
backend en un `pandas.DataFrame` que Streamlit puede presentar.

### Datos disponibles por variable

Cada elemento de `report.profile.columns` es un `ColumnProfile` con nombre,
tipo, cantidad y proporción de faltantes, cantidad de valores únicos y algunos
ejemplos. Su estructura está definida en
[`smarteda/models.py`](../../smarteda/models.py#L34-L43).

El backend genera estos valores al recorrer las columnas del DataFrame en
[`DataProfiler.profile()`](../../smarteda/profiling.py#L35-L50).

### Cómo funciona el ciclo de construcción

La función empieza con una lista vacía llamada `rows`. Después ejecuta un `for`
sobre `report.profile.columns`. En cada vuelta:

1. extrae el valor textual del tipo detectado;
2. lo traduce a una etiqueta en español mediante `TYPE_LABELS`;
3. une los valores de ejemplo en un solo texto separado por comas;
4. convierte la proporción de faltantes a porcentaje; y
5. agrega un diccionario a `rows`.

Cada diccionario se convierte en una fila con estas columnas:

| Columna visible | Propiedad de origen | Presentación |
|---|---|---|
| **Variable** | `column.name` | Nombre original. |
| **Tipo detectado** | `column.dtype` | Etiqueta traducida al español. |
| **Faltantes** | `column.missing_count` | Cantidad absoluta. |
| **% faltante** | `column.missing_ratio` | Proporción multiplicada por 100 y mostrada con un decimal. |
| **Valores únicos** | `column.unique_count` | Cantidad de valores diferentes, sin contar nulos. |
| **Ejemplos** | `column.sample_values` | Valores unidos por comas o un guion si no existen. |

Finalmente, `pd.DataFrame(rows)` convierte la lista en tabla. La vista la muestra
con `st.dataframe`, ocupa todo el ancho disponible y oculta el índice interno de
pandas. Esto ocurre en [`app/main.py`](../../app/main.py#L443-L452).

El backend guarda como máximo cinco ejemplos por columna con la configuración
actual. Además, omite valores nulos y evita repetir ejemplos. La selección puede
verse en [`DataProfiler._sample_values()`](../../smarteda/profiling.py#L112-L125).

## 7. Componentes y responsabilidades

| Función o componente | Responsabilidad |
|---|---|
| `render_summary_view()` | Coordina y organiza toda la pantalla. |
| `st.metric` | Presenta los cuatro indicadores principales. |
| `render_insight()` | Convierte un `Insight` en una tarjeta normal o de advertencia. |
| `build_variable_type_chart()` | Prepara la dona interactiva de Plotly. |
| `st.plotly_chart` | Inserta el gráfico en la página. |
| `build_profile_table()` | Transforma perfiles de columnas en un DataFrame. |
| `st.dataframe` | Presenta la tabla navegable. |
| `st.expander` | Mantiene ocultos los detalles adicionales hasta que el usuario los solicite. |

La composición principal usa `st.columns([1.35, 1])`: el panel de hallazgos
recibe un poco más de espacio que el gráfico. Esto permite leer los mensajes con
comodidad sin quitarle protagonismo a la composición de variables.

## 8. Acción “Analizar otro archivo”

Al final de la pantalla aparece un botón para comenzar de nuevo. Cuando el
usuario lo presiona, se eliminan de la sesión el reporte y el nombre activo, se
cambia la vista a **Carga de datos** y se solicita una nueva ejecución de
Streamlit. La lógica está en [`app/main.py`](../../app/main.py#L465-L471).

El algoritmo seleccionado no se borra, por lo que conserva la última elección
del usuario para el siguiente archivo.

## ¿Qué aporta esta pantalla al usuario?

Resumen funciona como control de calidad y punto de orientación. Antes de
interpretar relaciones o segmentos, el usuario puede comprobar si:

- se analizó el archivo correcto;
- la cantidad de datos coincide con lo esperado;
- existen demasiados valores faltantes;
- predominan variables útiles para ciertos análisis; y
- el motor encontró patrones que merecen una revisión posterior.

La pantalla presenta resultados producidos por el backend, pero la selección,
organización y forma de comunicarlos pertenecen al frontend.

## Explicación breve para una exposición

> Después de que el motor de Julián analiza el archivo, guardamos el
> `AnalysisReport` en la sesión de Streamlit. La pantalla Resumen usa tres partes
> de ese reporte: `profile`, `metadata` e `insights`. Con esos datos mostramos
> cuatro indicadores generales, los primeros hallazgos, una dona de tipos de
> variables y una tabla construida al recorrer el perfil de cada columna. El
> frontend no recalcula los análisis; solamente transforma la respuesta del
> backend en información visual y fácil de interpretar.

---

[← Capítulo 1: Introducción](README.md) · [Capítulo 3: Relaciones →](03-relaciones.md)
