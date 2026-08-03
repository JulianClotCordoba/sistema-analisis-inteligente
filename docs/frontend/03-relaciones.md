# 3. Pantalla Relaciones

[← Volver a Resumen](02-resumen.md)

## Objetivo de la pantalla

La pantalla **Relaciones** ayuda a descubrir qué variables numéricas suelen
cambiar juntas y si una variable numérica presenta diferencias importantes
entre las categorías de otra variable.

La experiencia completa se construye en
[`render_relationships_view()`](../../app/relationships.py#L423-L640). Su
responsabilidad es explicar y visualizar resultados que ya fueron calculados
por el backend.

La pantalla responde preguntas como:

- ¿Qué variables numéricas aumentan o disminuyen juntas?
- ¿El patrón se observa tanto con Pearson como con Spearman?
- ¿Cuál es la relación más intensa del conjunto?
- ¿Una variable como región o tipo permite diferenciar una medida numérica?
- ¿Qué patrones conviene investigar primero?

> Una relación estadística ayuda a encontrar patrones, pero no demuestra que una
> variable sea la causa de la otra.

## Flujo de datos

```text
Variables numéricas ──► Pearson y Spearman ──► report.correlations
                                                        │
                                                        ├─► métricas
                                                        ├─► tarjetas
                                                        └─► heatmap

Categorías + números ──► eta cuadrado ───────► report.dependencies
                                                        │
                                                        ├─► tarjetas
                                                        └─► barras

Ambos resultados ────────────────────────────► orientaciones de uso
```

Los campos consumidos por esta pantalla son:

| Campo | Contenido | Uso visual |
|---|---|---|
| `report.profile.numeric_columns` | Nombres de las variables numéricas detectadas. | Contexto y cantidad disponible. |
| `report.correlations["pearson"]` | Matriz y pares fuertes calculados con Pearson. | Selector, métricas, tarjetas y heatmap. |
| `report.correlations["spearman"]` | Matriz y pares fuertes calculados con Spearman. | Selector, métricas, tarjetas y heatmap. |
| `report.dependencies` | Asociaciones relevantes entre categorías y números. | Tarjetas, barras y recomendaciones. |

## 1. Qué calcula el backend

El análisis se encuentra en
[`CorrelationAnalyzer`](../../smarteda/analysis/correlation.py#L26-L126). El
frontend recibe sus resultados dentro de `AnalysisReport` y no necesita acceder
al DataFrame original.

### Correlaciones entre variables numéricas

El backend selecciona las columnas que el perfil clasificó como numéricas. Si
hay menos de dos, devuelve un diccionario vacío porque no existe una segunda
variable con la cual comparar.

Cuando hay suficientes variables, recorre los métodos configurados —Pearson y
Spearman de forma predeterminada— y utiliza `pandas.DataFrame.corr()` para crear
una matriz por método. Este recorrido está en
[`CorrelationAnalyzer.correlations()`](../../smarteda/analysis/correlation.py#L32-L52).

Cada resultado es un `CorrelationResult` con:

- `method`: nombre del método;
- `matrix`: matriz completa de coeficientes; y
- `strong_pairs`: pares que superaron el umbral de importancia.

Su contrato se define en
[`smarteda/models.py`](../../smarteda/models.py#L84-L90).

### Selección de relaciones fuertes

El backend recorre las combinaciones de columnas sin comparar dos veces el mismo
par ni incluir la diagonal. Conserva únicamente aquellas cuyo coeficiente
absoluto es igual o superior al umbral configurado, y las ordena desde la
relación más intensa hasta la menos intensa. La lógica está en
[`CorrelationAnalyzer._strong_pairs()`](../../smarteda/analysis/correlation.py#L74-L97).

El umbral actual es `0.70`, definido en
[`AnalysisConfig`](../../smarteda/config.py#L18-L23). Se usa el valor absoluto
porque tanto `+0.80` como `−0.80` representan patrones intensos; el signo indica
si las variables se mueven en el mismo sentido o en sentidos contrarios.

### Diferencias entre categorías: eta cuadrado

Además de relacionar números entre sí, el backend compara cada variable
categórica con cada variable numérica. Para ello calcula **eta cuadrado** o
`eta²`, un valor entre 0 y 1 que representa qué proporción de la variación
numérica está asociada con las diferencias entre categorías.

Por ejemplo, una relación `región → ventas` de `0.35` indica que los grupos de
región explican aproximadamente un 35 % de la variación observada en ventas. Es
una asociación para investigar, no una prueba de causalidad.

Solo se conservan resultados iguales o superiores a `0.14`, y la lista se
ordena de mayor a menor. Este proceso está en
[`CorrelationAnalyzer.dependencies()`](../../smarteda/analysis/correlation.py#L54-L70),
mientras que el cálculo de eta² se encuentra en
[`CorrelationAnalyzer._eta_squared()`](../../smarteda/analysis/correlation.py#L107-L126).

## 2. Encabezado y disponibilidad de resultados

La pantalla recibe el reporte y el nombre del archivo desde `main()`. Primero
comprueba que el reporte exista y después presenta:

- el archivo analizado; y
- la cantidad de variables numéricas detectadas.

Esta cabecera se construye en
[`app/relationships.py`](../../app/relationships.py#L423-L455). El nombre del
archivo se procesa con `html.escape` antes de insertarlo en el contenido visual.

Después se crea `available_methods`, una lista que incluye Pearson y Spearman
solamente si sus claves existen en `report.correlations`. La validación está en
[`app/relationships.py`](../../app/relationships.py#L457-L475).

Si no hay métodos disponibles, la vista explica que se necesitan al menos dos
columnas numéricas y termina de forma controlada. No intenta construir un
selector ni un gráfico con una matriz inexistente.

## 3. Selector Pearson/Spearman

Cuando existen resultados, `st.radio` crea el selector **Método de lectura**. El
usuario puede alternar entre Pearson y Spearman sin volver a analizar el
archivo, porque ambas matrices ya están almacenadas en el reporte. La selección
solo cambia cuál resultado se lee:

```python
result = report.correlations[selected_method]
```

La implementación está en
[`app/relationships.py`](../../app/relationships.py#L477-L489).

### Explicación sencilla de los métodos

| Método | Qué observa | Cuándo ayuda |
|---|---|---|
| **Pearson** | Si dos variables cambian siguiendo una dirección relativamente uniforme. | Para reconocer relaciones lineales; los valores extremos pueden influir más. |
| **Spearman** | Si el orden general de los valores se mantiene entre ambas variables. | Para reconocer una tendencia aunque el ritmo del cambio no sea constante. |

El texto breve que acompaña al selector viene de `METHOD_EXPLANATIONS`, definido
en [`app/relationships.py`](../../app/relationships.py#L23-L37), y se presenta en
[`app/relationships.py`](../../app/relationships.py#L500-L508).

## 4. Las cuatro tarjetas principales

La pantalla utiliza cuatro componentes `st.metric`, construidos en
[`app/relationships.py`](../../app/relationships.py#L491-L498).

| Tarjeta | Cálculo | Significado |
|---|---|---|
| **Variables comparadas** | `len(result.matrix.columns)` | Cantidad de variables incluidas en la matriz seleccionada. |
| **Relaciones fuertes** | `len(result.strong_pairs)` | Pares que alcanzan el umbral de `0.70` para el método activo. |
| **Relación más alta** | Mayor valor absoluto fuera de la diagonal. | Intensidad más alta observada, independientemente de su dirección. |
| **Diferencias por categoría** | `len(report.dependencies)` | Asociaciones categoría→número que superan el umbral de eta². |

Para encontrar la relación más alta, `_strongest_value()` convierte la matriz a
valores absolutos, reemplaza la diagonal por `NaN` y toma el mayor valor
restante. Esto evita mostrar `1.00` simplemente porque cada variable se
correlaciona perfectamente consigo misma. La función está en
[`app/relationships.py`](../../app/relationships.py#L196-L204).

La cantidad de diferencias por categoría no cambia al alternar Pearson y
Spearman, porque eta² es un análisis separado.

## 5. Tarjetas de relaciones fuertes

La sección **Relaciones que vale la pena revisar** recibe
`result.strong_pairs`. Si la lista está vacía, presenta un estado informativo y
recuerda que el mapa todavía puede contener relaciones más suaves.

Si existen pares, `_render_relationship_cards()` recorre la lista con un `for` y
crea una tarjeta por relación. La función completa está en
[`app/relationships.py`](../../app/relationships.py#L328-L376).

Cada tarjeta muestra:

- las dos variables involucradas;
- el método que produjo la relación;
- la intensidad indicada por el backend;
- el coeficiente con signo;
- una etiqueta de **Mismo sentido** o **Sentido contrario**; y
- una oración cotidiana que explica el patrón.

Por ejemplo, un coeficiente positivo se transforma en una idea como “cuando una
variable aumenta, la otra también tiende a aumentar”. Si es negativo, la frase
indica que la segunda tiende a disminuir. Esta traducción se realiza en
[`_relationship_sentence()`](../../app/relationships.py#L46-L54).

Cuando hay más de una relación, se crean dos columnas y cada tarjeta se coloca
con `index % 2`: índices pares a la primera columna e impares a la segunda. Así
se forma una cuadrícula sin escribir manualmente una posición para cada par.

Los nombres y mensajes se escapan con `html.escape`, y la apariencia de las
tarjetas está en
[`app/assets/styles.css`](../../app/assets/styles.css#L353-L439).

## 6. Mapa completo de relaciones

Las tarjetas anteriores muestran únicamente pares fuertes. El **heatmap**
muestra la matriz completa del método seleccionado, por lo que también permite
observar patrones que no alcanzaron el umbral de `0.70`.

[`build_correlation_heatmap()`](../../app/relationships.py#L207-L268) recibe el
`CorrelationResult` y construye un `go.Heatmap` de Plotly:

- `z` contiene la matriz numérica;
- `x` y `y` contienen los nombres humanizados de las variables;
- la escala siempre va de `−1` a `1` y tiene su centro en `0`;
- cada celda muestra el coeficiente con dos decimales;
- los tonos dorados representan relaciones positivas;
- los tonos naranjas representan relaciones negativas; y
- los tonos oscuros representan valores cercanos a cero.

La altura se ajusta de acuerdo con la cantidad de variables, dentro de un mínimo
de 390 y un máximo de 650 píxeles. El gráfico se inserta mediante
`st.plotly_chart` en [`app/relationships.py`](../../app/relationships.py#L526-L547).

La diagonal siempre muestra `1.00` porque compara cada variable consigo misma.
La matriz también es simétrica: la relación A→B tiene el mismo valor que B→A.

## 7. Diferencias entre categorías

Esta sección trabaja con `report.dependencies`, que ya viene ordenado desde la
asociación más alta hasta la más baja.

Cuando hay resultados, la pantalla se divide en dos columnas:

- a la izquierda aparecen tarjetas explicativas; y
- a la derecha aparece un gráfico horizontal de barras.

La composición se encuentra en
[`app/relationships.py`](../../app/relationships.py#L576-L608).

### Tarjetas de dependencia

[`_render_dependency_cards()`](../../app/relationships.py#L379-L401) recorre la
lista. Para cada elemento multiplica `eta_squared` por 100 y muestra:

- el porcentaje;
- la relación `variable categórica → variable numérica`;
- una explicación breve; y
- una etiqueta orientativa.

La etiqueta se asigna en [`_association_label()`](../../app/relationships.py#L57-L63):

| Valor eta² | Etiqueta del frontend |
|---|---|
| `0.50` o más | Muy marcada |
| `0.26` a menos de `0.50` | Marcada |
| `0.14` a menos de `0.26` | Relevante |

La apariencia de estas tarjetas está en
[`app/assets/styles.css`](../../app/assets/styles.css#L446-L489).

### Gráfico de barras

[`build_dependency_chart()`](../../app/relationships.py#L271-L312) transforma
cada dependencia en una etiqueta y un porcentaje. Plotly crea barras
horizontales con una escala fija de 0 a 100 %, lo que facilita comparar varias
asociaciones bajo la misma referencia.

Si no existen dependencias, la pantalla no falla ni muestra un gráfico vacío:
explica que quizá no hay variables categóricas o que los grupos tienen valores
numéricos similares.

## 8. Orientaciones para usar los hallazgos

La sección **Cómo usar estos hallazgos** construye tres tarjetas de orientación.
No son nuevos análisis estadísticos: son textos generados por el frontend a
partir de los resultados existentes.

[`_decision_guidance()`](../../app/relationships.py#L75-L193) aplica tres reglas:

1. **Priorizar o no forzar:** encuentra el par fuerte más intenso del método
   activo. Si no existe, recomienda evaluar las variables por separado.
2. **Interpretar o confirmar:** compara los pares fuertes de Pearson y Spearman.
   Si un par aparece únicamente en Spearman, lo presenta como una tendencia y
   no como una regla exacta. En caso contrario, recuerda validar el patrón con
   el contexto.
3. **Comparar o explorar:** toma la primera dependencia —la más alta porque el
   backend ordenó la lista— y sugiere comparar las categorías por separado. Si
   no hay dependencias, recomienda no segmentar sin evidencia suficiente.

`_render_decision_guidance()` recorre esas tres orientaciones junto con tres
columnas usando `zip`, y crea una tarjeta en cada una. La composición está en
[`app/relationships.py`](../../app/relationships.py#L404-L420).

Estas recomendaciones están redactadas como pistas para investigar. No deben
interpretarse como decisiones automáticas ni conclusiones causales.

## 9. Estados vacíos y casos especiales

La misma función `_render_empty_state()` permite comunicar de forma consistente
tres situaciones:

| Situación | Respuesta de la interfaz |
|---|---|
| Menos de dos variables numéricas | Explica que no se puede construir una comparación. |
| Matriz disponible, pero sin pares que superen `0.70` | Mantiene el heatmap y aclara que pueden existir relaciones más suaves. |
| Sin dependencias relevantes | Indica que pueden faltar categorías o que sus diferencias son pequeñas. |

La función está en
[`app/relationships.py`](../../app/relationships.py#L315-L325), y sus estilos se
encuentran en
[`app/assets/styles.css`](../../app/assets/styles.css#L492-L520).

La diferencia es importante: **sin correlaciones disponibles** se detiene la
pantalla, mientras que **sin relaciones fuertes** todavía se puede mostrar la
matriz completa.

## 10. Componentes y responsabilidades

| Función o componente | Responsabilidad |
|---|---|
| `render_relationships_view()` | Coordina la pantalla y el orden de sus secciones. |
| `st.radio` | Permite alternar entre Pearson y Spearman. |
| `st.metric` | Presenta los cuatro indicadores principales. |
| `_render_relationship_cards()` | Recorre y presenta los pares fuertes. |
| `build_correlation_heatmap()` | Convierte la matriz seleccionada en un heatmap. |
| `_render_dependency_cards()` | Explica individualmente cada dependencia relevante. |
| `build_dependency_chart()` | Compara los porcentajes de eta² con barras. |
| `_decision_guidance()` | Deriva orientaciones prudentes de los resultados existentes. |
| `_render_empty_state()` | Explica por qué una sección no tiene resultados. |
| Plotly | Proporciona interactividad a matrices y barras. |
| CSS | Mantiene la identidad visual de tarjetas, avisos y encabezados. |

## ¿Qué aporta esta pantalla al usuario?

Relaciones transforma matrices y coeficientes técnicos en una secuencia de
lectura progresiva:

1. presenta cantidades generales;
2. destaca los pares de mayor importancia;
3. permite revisar la matriz completa;
4. explica diferencias entre categorías; y
5. propone preguntas que el usuario puede investigar.

El backend decide qué cálculos son válidos y produce sus valores. El frontend
decide cómo compararlos, explicarlos y mostrarlos sin ocultar sus limitaciones.

## Explicación breve para una exposición

> La pantalla Relaciones utiliza `report.correlations` y
> `report.dependencies`. El backend de Julián ya calculó las matrices Pearson y
> Spearman, seleccionó los pares con una intensidad absoluta de al menos 0.70 y
> calculó las asociaciones entre categorías y números mediante eta cuadrado. En
> el frontend permitimos cambiar de método sin repetir el análisis, presentamos
> cuatro indicadores, recorremos los pares para crear tarjetas y usamos Plotly
> para generar el heatmap y las barras. Finalmente, comparamos los resultados
> existentes para ofrecer orientaciones prudentes, recordando que una relación
> no demuestra causalidad.

---

[← Capítulo 2: Resumen](02-resumen.md) · [Capítulo 4: Segmentos →](04-segmentos.md)
