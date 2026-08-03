# 5. Pantalla Datos inusuales

[← Volver a Segmentos](04-segmentos.md)

## Objetivo de la pantalla

La pantalla **Datos inusuales** identifica registros que merecen revisión porque
contienen valores extremos o combinaciones numéricas poco frecuentes. En lugar
de depender de una sola definición, compara tres métodos: Z-Score, IQR e
Isolation Forest.

La vista se construye en
[`render_anomalies_view()`](../../app/anomalies.py#L371-L564) y consume los
resultados almacenados en `report.anomalies`.

La pantalla responde preguntas como:

- ¿Cuántos registros señaló cada método?
- ¿En cuáles filas coinciden todos los detectores?
- ¿Qué método encontró el conjunto más amplio?
- ¿Dónde se ubican las señales en la proyección de los datos?
- ¿Qué filas deberían revisarse primero?

> **Inusual no significa incorrecto.** Una señal puede corresponder a un error,
> pero también a un caso legítimo, poco frecuente o especialmente valioso. El
> sistema organiza la revisión; no elimina datos automáticamente.

## Flujo de datos

```text
Variables numéricas con faltantes imputados
                    │
        ┌───────────┼──────────────────┐
        ▼           ▼                  ▼
     Z-Score       IQR         Isolation Forest
        │           │                  │
        └───────────┼──────────────────┘
                    ▼
     lista de AnomalyResult en report.anomalies
                    │
       ┌────────────┼─────────────┐
       ▼            ▼             ▼
 método activo   consenso      unión de señales
       │            │             │
       └────────────┼─────────────┘
                    ▼
       métricas, mapa, comparación y prioridad
```

## 1. El contrato `AnomalyResult`

Cada detector devuelve un objeto
[`AnomalyResult`](../../smarteda/models.py#L107-L116) con los siguientes campos:

| Campo | Contenido | Uso en el frontend |
|---|---|---|
| `method` | Identificador del detector. | Selector, títulos y explicaciones. |
| `outlier_mask` | Arreglo booleano con una posición por registro. | Mapa, consenso y tabla de prioridad. |
| `outlier_count` | Cantidad de valores `True` en la máscara. | Tarjetas y métricas. |
| `outlier_ratio` | Proporción marcada respecto al total. | Porcentajes y gráfico comparativo. |
| `columns_analyzed` | Variables numéricas utilizadas. | Línea de contexto. |
| `details` | Parámetros y detalles específicos del método. | Panel técnico. |

Una posición `True` en `outlier_mask` significa que ese método recomienda
revisar la fila procesada en esa misma posición.

## 2. Preparación y ejecución en el backend

El motor intenta detectar anomalías cuando existe al menos una variable
numérica. Primero obtiene un DataFrame numérico y reemplaza faltantes con la
mediana de cada columna mediante
[`Preprocessor.numeric_frame()`](../../smarteda/preprocessing.py#L26-L37).

Luego [`run_anomaly_detection()`](../../smarteda/analysis/anomaly.py#L134-L145)
recorre los métodos indicados en la configuración, crea el detector
correspondiente y agrega su resultado a una lista.

Los tres métodos activos y sus parámetros predeterminados se definen en
[`AnalysisConfig`](../../smarteda/config.py#L32-L38). El motor integra esta lista
en el reporte desde
[`AnalysisEngine._analyze_anomalies()`](../../smarteda/engine.py#L153-L162).

Todos los detectores comparten la interfaz `AnomalyDetector`. Su método común
`_result()` calcula cantidad y proporción, y construye un `AnomalyResult`. Esta
estructura compartida está en
[`smarteda/analysis/anomaly.py`](../../smarteda/analysis/anomaly.py#L28-L56).

## 3. Los tres métodos en palabras sencillas

### Z-Score

Z-Score compara cada valor con el promedio de su variable y mide cuántas
desviaciones estándar lo separan de ese promedio. El umbral actual es `3.0`.

El detector recorre cada columna numérica. Si una fila supera el umbral en al
menos una variable, su posición queda marcada en la máscara general. También
guarda cuántas señales encontró por columna. La implementación está en
[`ZScoreDetector`](../../smarteda/analysis/anomaly.py#L59-L81).

Es fácil de explicar y localizar por variable, aunque el promedio y la
desviación pueden verse afectados por los propios extremos.

### IQR

IQR utiliza la zona central de los datos. Para cada variable obtiene el primer y
tercer cuartil, calcula su diferencia y amplía el rango con un multiplicador de
`1.5`.

Una fila se marca si al menos uno de sus valores queda por debajo del límite
inferior o por encima del superior. El detector guarda los límites utilizados
para cada columna. La implementación está en
[`IQRDetector`](../../smarteda/analysis/anomaly.py#L84-L104).

Este método suele ser menos sensible a la forma de la distribución que Z-Score.

### Isolation Forest

Isolation Forest observa todas las variables numéricas simultáneamente. Primero
las estandariza y después entrena un modelo que intenta aislar los registros. Las
combinaciones que se aíslan con facilidad se consideran poco frecuentes.

El modelo devuelve `-1` para una anomalía y `1` para un registro normal; el
backend convierte esa salida en una máscara booleana. La implementación está en
[`IsolationForestDetector`](../../smarteda/analysis/anomaly.py#L107-L124).

Como estudia combinaciones completas, no atribuye cada señal a una única
columna.

| Método | Perspectiva | Detalle disponible |
|---|---|---|
| Z-Score | Distancia frente al promedio por variable. | Señales por columna y umbral. |
| IQR | Distancia frente al rango central por variable. | Límites inferior y superior. |
| Isolation Forest | Rareza de la combinación de todas las variables. | Proporción esperada configurada. |

## 4. Validación y selector de método

La pantalla comprueba primero que exista un reporte y que
`report.anomalies` contenga resultados. Si la lista está vacía, muestra una
explicación y no intenta construir los demás componentes. Este control está en
[`app/anomalies.py`](../../app/anomalies.py#L371-L400).

El total de registros se obtiene de la longitud de la primera máscara, y las
variables analizadas se toman de `columns_analyzed`. Después `_result_map()`
convierte la lista en un diccionario cuya clave es el nombre del método. Esto
facilita recuperar la selección actual. La preparación se encuentra en
[`app/anomalies.py`](../../app/anomalies.py#L402-L427).

`st.radio` permite cambiar entre los detectores disponibles sin volver a
analizar el archivo: todas sus máscaras ya están guardadas en el reporte.

## 5. Consenso y unión de señales

El frontend no calcula una nueva anomalía. Compara las máscaras existentes
mediante operaciones booleanas:

- [`_consensus_mask()`](../../app/anomalies.py#L55-L59) aplica un **AND**: una
  posición es verdadera únicamente si todos los métodos la marcaron.
- [`_any_mask()`](../../app/anomalies.py#L62-L66) aplica un **OR**: una posición
  es verdadera si al menos un método la marcó.

Ejemplo sencillo:

```text
Z-Score:          [False, True,  True,  False]
IQR:              [False, True,  False, False]
Isolation Forest: [True,  True,  False, False]

Coincidencia:     [False, True,  False, False]
Alguna señal:     [True,  True,  True,  False]
```

Esta comparación permite establecer una prioridad sin modificar ni sustituir
los resultados de Julián.

## 6. Las cuatro tarjetas principales

Las métricas se construyen en
[`app/anomalies.py`](../../app/anomalies.py#L428-L445):

| Tarjeta | Cálculo | Significado |
|---|---|---|
| **Registros marcados** | `selected.outlier_count` | Filas señaladas por el método activo. |
| **Porcentaje del total** | `selected.outlier_ratio × 100` | Proporción marcada por ese método. |
| **Coincidencia total** | Suma de la máscara AND. | Filas señaladas por todos los detectores disponibles. |
| **Con alguna señal** | Suma de la máscara OR. | Filas señaladas por uno o más detectores. |

Las primeras dos tarjetas cambian cuando se selecciona otro método. Las últimas
dos resumen el conjunto completo y permanecen iguales.

[`_render_method_note()`](../../app/anomalies.py#L248-L267) agrega una explicación
del método activo y muestra el parámetro guardado dentro de `result.details`.

## 7. Mapa de revisión

El mapa reutiliza `report.clustering.projection_2d`; no crea otra proyección. Se
muestra únicamente cuando:

- existe `report.clustering`;
- la proyección 2D está disponible; y
- tiene la misma cantidad de filas que las máscaras de anomalías.

La validación está en
[`app/anomalies.py`](../../app/anomalies.py#L447-L475). Si no se cumple, las
detecciones siguen disponibles, pero la interfaz explica que no puede ubicarlas
visualmente.

[`build_anomaly_scatter()`](../../app/anomalies.py#L101-L193) separa los puntos en
tres grupos:

1. **Sin señal en este método:** el detector seleccionado no los marcó.
2. **Señal del método seleccionado:** están marcados por el método activo, pero
   no por todos.
3. **Coincidencia de todos:** todos los detectores los marcaron.

La función crea máscaras booleanas para seleccionar las coordenadas de cada
grupo y agrega una traza `go.Scatter` por categoría. Las señales individuales se
muestran como diamantes naranjas; las coincidencias, como cruces doradas más
grandes.

Los ejes **Vista resumida 1** y **Vista resumida 2** provienen de PCA. No
representan directamente edad, ingreso u otra variable original.

## 8. Detalle técnico por detector

Debajo del mapa, un `st.expander` llama a
[`_render_method_details()`](../../app/anomalies.py#L288-L313):

- para Z-Score, crea una tabla con señales encontradas por variable;
- para IQR, crea una tabla con los límites inferior y superior de cada variable;
- para Isolation Forest, explica que la señal es multivariada y no corresponde
  a una sola columna.

Las tablas se construyen mediante comprensiones de listas, se convierten a
`pandas.DataFrame` y se presentan con `st.dataframe`.

## 9. Comparación entre métodos

La sección **Qué detectó cada método** muestra una tarjeta por resultado.
[`_render_method_cards()`](../../app/anomalies.py#L270-L285) combina una columna
de Streamlit con cada detector usando `zip`. Cada tarjeta presenta:

- nombre del método;
- cantidad señalada;
- porcentaje del total; y
- descripción breve de su perspectiva.

Los estilos de estas tarjetas están en
[`app/assets/styles.css`](../../app/assets/styles.css#L684-L726).

Después,
[`build_method_comparison_chart()`](../../app/anomalies.py#L196-L231) construye
un gráfico horizontal con Plotly. Una barra representa el porcentaje marcado
por cada detector y su texto combina cantidad y porcentaje. El límite del eje se
ajusta al resultado más alto para dejar espacio a las etiquetas.

No se espera que las tres barras coincidan: la diferencia es precisamente la
razón para comparar varias perspectivas.

## 10. Tabla de prioridad de revisión

[`_review_queue()`](../../app/anomalies.py#L69-L98) transforma las máscaras en
una tabla práctica:

1. crea un diccionario `método → máscara`;
2. obtiene las posiciones marcadas por al menos un método;
3. recorre esas posiciones;
4. identifica qué detectores marcaron cada una;
5. cuenta las coincidencias; y
6. asigna una prioridad.

| Condición | Prioridad |
|---|---|
| Todos los métodos coinciden | Alta |
| Coinciden al menos dos | Media |
| Solamente uno la señala | Explorar |

La tabla muestra **Fila procesada**, **Métodos**, **Coincidencias** y
**Prioridad**. Se ordena primero por mayor cantidad de coincidencias y después
por número de fila ascendente.

El número comienza en 1 para facilitar la lectura, pero corresponde al conjunto
después de la limpieza. Si el motor eliminó filas vacías o duplicadas, puede no
coincidir con la posición original del archivo.

## 11. Orientaciones de uso

[`_decision_guidance()`](../../app/anomalies.py#L316-L348) prepara tres mensajes:

1. **Priorizar:** empezar por las coincidencias de todos los métodos.
2. **Contrastar:** utilizar el detector que marcó más casos como una mirada
   amplia y compararlo con métodos más estrictos.
3. **Validar:** revisar el origen y contexto de todas las filas con alguna señal
   antes de corregirlas o eliminarlas.

[`_render_decision_guidance()`](../../app/anomalies.py#L351-L368) distribuye
estas orientaciones en tres tarjetas. Son reglas de comunicación construidas a
partir de cantidades existentes, no un cuarto detector.

## 12. Estados y limitaciones

| Situación | Respuesta de la pantalla |
|---|---|
| No existe reporte | Solicita analizar primero un archivo. |
| No hay resultados de anomalías | Explica que se necesitan datos numéricos utilizables. |
| No existe una proyección compatible | Mantiene las métricas, tablas y comparación, pero omite el mapa. |
| Un método no encuentra señales | Muestra cero; no lo interpreta como un error. |

El `AnalysisReport` actual no incluye el DataFrame limpio ni los valores
originales de cada fila. Por esa razón, la pantalla no inventa detalles ni crea
boxplots con datos inexistentes; utiliza posición, máscaras y metadatos reales.
Esta decisión se explica en
[`app/anomalies.py`](../../app/anomalies.py#L547-L563).

## 13. Componentes y responsabilidades

| Función o componente | Responsabilidad |
|---|---|
| `render_anomalies_view()` | Coordina la experiencia completa. |
| `_result_map()` | Permite recuperar un resultado por nombre de método. |
| `_consensus_mask()` | Encuentra coincidencias de todos los detectores. |
| `_any_mask()` | Encuentra registros con al menos una señal. |
| `build_anomaly_scatter()` | Ubica señales sobre la proyección existente. |
| `_render_method_details()` | Presenta detalles específicos de cada detector. |
| `_render_method_cards()` | Resume cada método en una tarjeta. |
| `build_method_comparison_chart()` | Compara porcentajes con barras. |
| `_review_queue()` | Construye y ordena la prioridad de revisión. |
| `_decision_guidance()` | Convierte acuerdos y diferencias en próximos pasos. |

## Explicación breve para una exposición

> La pantalla Datos inusuales consume una lista de `AnomalyResult`. Julián
> ejecutó Z-Score, IQR e Isolation Forest y devolvió para cada uno una máscara
> booleana, cantidad, porcentaje, variables y detalles. El frontend permite
> alternar métodos sin repetir el análisis y combina las máscaras con AND para
> encontrar coincidencias y con OR para encontrar cualquier señal. Luego utiliza
> Plotly para el mapa y la comparación, y recorre las posiciones marcadas para
> crear una tabla de prioridad. Una señal solo indica que conviene revisar la
> fila; no autoriza eliminarla automáticamente.

---

[← Capítulo 4: Segmentos](04-segmentos.md) · [Capítulo 6: Reporte →](06-reporte.md)
