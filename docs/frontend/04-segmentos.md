# 4. Pantalla Segmentos

[← Volver a Relaciones](03-relaciones.md)

## Objetivo de la pantalla

La pantalla **Segmentos** presenta grupos de registros que tienen combinaciones
numéricas parecidas. Su propósito es ayudar al usuario a identificar perfiles
dentro del conjunto de datos sin revisar cada fila manualmente.

La vista completa se construye en
[`render_segments_view()`](../../app/segments.py#L406-L636) y consume
`report.clustering`, un resultado que el backend ya calculó.

La pantalla responde preguntas como:

- ¿Cuántos grupos encontró el motor?
- ¿Qué tan clara es la separación entre ellos?
- ¿Cuántos registros contiene cada grupo?
- ¿Dónde aparecen los grupos en una representación visual?
- ¿DBSCAN dejó registros sin segmento?
- ¿Cómo se pueden utilizar los grupos sin sobreinterpretarlos?

> Un segmento representa similitud matemática. El algoritmo no sabe por sí solo
> si un grupo significa “clientes frecuentes”, “alto valor” o cualquier otra
> etiqueta del contexto real.

## Flujo de datos

```text
Columnas numéricas
       │
       ▼
Imputación de faltantes + estandarización
       │
       ▼
K-Means o DBSCAN
       │
       ├──► etiquetas y tamaños
       ├──► calidad silhouette
       ├──► parámetros seleccionados
       └──► proyección PCA de dos dimensiones
                    │
                    ▼
             report.clustering
                    │
                    ▼
   métricas, mapa, tarjetas, barras y orientaciones
```

## 1. Qué información entrega el backend

El contrato de clustering se define en
[`ClusteringResult`](../../smarteda/models.py#L93-L104). Sus campos son:

| Campo | Contenido | Uso en el frontend |
|---|---|---|
| `algorithm` | Método utilizado: `kmeans` o `dbscan`. | Encabezado y explicación del método. |
| `labels` | Una etiqueta de grupo por cada registro procesado. | Colores y selección de puntos en el mapa. |
| `n_clusters` | Cantidad de grupos encontrados, sin contar el ruido de DBSCAN. | Tarjeta **Segmentos encontrados**. |
| `features_used` | Nombres de las variables numéricas utilizadas. | Línea de contexto. |
| `cluster_sizes` | Cantidad de registros por etiqueta. | Tarjetas y gráfico de tamaños. |
| `silhouette` | Calidad matemática de separación o `None`. | Tarjeta y explicación de calidad. |
| `params` | Parámetros elegidos para el algoritmo. | Detalle técnico del método. |
| `projection_2d` | Coordenadas resumidas de cada registro. | Mapa de similitud. |

La pantalla no vuelve a ejecutar clustering. Solamente transforma estos campos
en componentes visuales y explicaciones.

## 2. Preparación de los datos

Antes de agrupar registros, el backend utiliza únicamente las variables que el
perfil identificó como numéricas. La clase
[`Preprocessor`](../../smarteda/preprocessing.py#L23-L66) realiza dos operaciones
necesarias:

1. reemplaza los valores numéricos faltantes con la mediana de su columna; y
2. estandariza las variables para colocarlas en una escala comparable.

La estandarización evita que una columna con valores muy grandes domine las
distancias. Por ejemplo, una variable expresada en miles no debería pesar más
que otra expresada entre 1 y 10 únicamente por utilizar unidades distintas.

El motor actual intenta crear segmentos cuando existen al menos dos columnas
numéricas y cinco filas. Estas condiciones y el manejo seguro de errores están
en [`AnalysisEngine._analyze_clustering()`](../../smarteda/engine.py#L139-L151),
y el mínimo de filas forma parte de
[`AnalysisConfig`](../../smarteda/config.py#L40-L44).

## 3. K-Means y DBSCAN

El usuario escoge el algoritmo antes de analizar el archivo, en **Carga de
datos**. A diferencia del selector de Pearson/Spearman, cambiar el método de
segmentación sí requiere volver a ejecutar el análisis.

Los dos algoritmos comparten una interfaz y producen el mismo tipo de resultado.
La selección se realiza en
[`run_clustering()`](../../smarteda/analysis/clustering.py#L164-L181).

### K-Means

K-Means asigna todos los registros al grupo cuyo centro resulta más cercano. Es
útil cuando se necesita dividir todo el conjunto en una cantidad clara de
grupos.

Si el usuario no fija `k`, el backend prueba cantidades entre 2 y 10 —limitadas
por el número de registros— y conserva la que obtiene la mejor puntuación
silhouette. La implementación está en
[`KMeansClustering`](../../smarteda/analysis/clustering.py#L81-L110).

El resultado guarda el valor seleccionado dentro de `params["k"]`.

### DBSCAN

DBSCAN forma grupos donde encuentra suficientes registros cercanos. Puede
descubrir agrupaciones sin obligar a todos los casos a pertenecer a una de ellas.
Los registros aislados reciben la etiqueta especial `-1`.

Cuando no se configura `eps`, el backend lo estima a partir de las distancias a
los vecinos más cercanos. También utiliza `min_samples`, cuyo valor
predeterminado es 5. La implementación está en
[`DBSCANClustering`](../../smarteda/analysis/clustering.py#L113-L161).

El resultado conserva `eps` y `min_samples` dentro de `params`.

| K-Means | DBSCAN |
|---|---|
| Todos los registros reciben un grupo. | Puede dejar registros sin segmento. |
| Necesita una cantidad `k` de grupos. | Utiliza distancia y vecinos mínimos. |
| El backend selecciona automáticamente el mejor `k` si no se proporciona. | El backend estima automáticamente `eps` si no se proporciona. |
| Funciona bien para una división completa. | Es útil cuando existen zonas densas y casos aislados. |

La pantalla explica ambos métodos dentro de un panel desplegable en
[`app/segments.py`](../../app/segments.py#L592-L615).

## 4. Construcción del resultado común

Después de ejecutar cualquiera de los algoritmos, el backend crea un
`ClusteringResult` mediante
[`ClusteringAlgorithm._build_result()`](../../smarteda/analysis/clustering.py#L42-L65).

En ese punto:

- cuenta las etiquetas con `Counter` para producir `cluster_sizes`;
- excluye `-1` al calcular `n_clusters`;
- calcula silhouette cuando es matemáticamente válido; y
- genera la proyección de dos dimensiones.

Esta construcción común permite que el frontend utilice los mismos componentes
para K-Means y DBSCAN. Las diferencias se resuelven leyendo `algorithm`,
`params` y la posible etiqueta `-1`.

## 5. Validaciones y encabezado

La pantalla comprueba primero que exista un reporte. Después extrae
`report.clustering` y presenta el nombre del archivo.

Si `report.clustering` es `None`, muestra un estado vacío y termina. Esto puede
ocurrir si no hay suficientes filas, faltan variables numéricas o el algoritmo
no puede ejecutarse con los datos disponibles. El control está en
[`app/segments.py`](../../app/segments.py#L406-L440).

Cuando sí existe un resultado, la línea de contexto muestra:

- archivo analizado;
- algoritmo utilizado; y
- variables numéricas empleadas.

Los nombres técnicos se vuelven más legibles reemplazando guiones bajos y
capitalizando el texto. Los contenidos dinámicos se protegen con `html.escape`.

DBSCAN puede devolver un resultado válido con `n_clusters == 0` cuando todos los
registros quedan como ruido. En ese caso, la pantalla explica que no se formó un
grupo estable y evita forzar el resto de las visualizaciones. Este segundo
control está en [`app/segments.py`](../../app/segments.py#L442-L465).

## 6. Organización de etiquetas y ruido

[`_segment_items()`](../../app/segments.py#L75-L83) transforma
`result.cluster_sizes` en pares `(etiqueta, tamaño)`. Durante esta preparación:

- convierte etiquetas y tamaños a enteros;
- excluye la etiqueta `-1`; y
- ordena los segmentos del más grande al más pequeño.

La cantidad de registros sin segmento se obtiene por separado con
[`_noise_count()`](../../app/segments.py#L86-L87), que consulta el tamaño asociado
a `-1` y devuelve cero si esa etiqueta no existe.

Aunque internamente las etiquetas comienzan en `0`, el frontend suma uno al
presentarlas. Por eso la etiqueta interna `0` aparece como **Segmento 1**. Esta
decisión hace que la numeración sea más natural para el usuario.

## 7. Las cuatro tarjetas principales

La pantalla crea cuatro métricas en
[`app/segments.py`](../../app/segments.py#L467-L485):

| Tarjeta | Origen | Significado |
|---|---|---|
| **Segmentos encontrados** | `result.n_clusters` | Grupos válidos, sin contar registros `-1`. |
| **Calidad de separación** | Traducción de `result.silhouette`. | Lectura sencilla de qué tan definidos están los grupos. |
| **Grupo más grande** | Mayor tamaño devuelto por `_segment_items()`. | Cantidad de registros del segmento con mayor representación. |
| **Sin segmento** | Tamaño de la etiqueta `-1`. | Registros que DBSCAN no asignó a un grupo. |

K-Means normalmente muestra cero en **Sin segmento**, porque asigna todos los
registros.

Después de las métricas, `_render_method_details()` explica el algoritmo y
muestra su configuración técnica. Para K-Means presenta `k`; para DBSCAN muestra
`eps` y `min_samples`. La función está en
[`app/segments.py`](../../app/segments.py#L373-L403).

## 8. Mapa de similitud

El mapa representa cada registro como un punto. Los puntos con la misma etiqueta
comparten color y los registros cercanos tienen combinaciones numéricas
parecidas.

Es importante no interpretar los ejes como variables originales. El backend
reduce la matriz estandarizada a dos componentes mediante **PCA** en
[`Preprocessor.project_2d()`](../../smarteda/preprocessing.py#L57-L66). Por eso
se llaman **Vista resumida 1** y **Vista resumida 2**.

### Construcción con Plotly

[`build_segment_scatter()`](../../app/segments.py#L90-L172) crea el gráfico:

1. convierte la proyección y las etiquetas a arreglos de NumPy;
2. recorre los segmentos ordenados;
3. crea una máscara como `labels == label`;
4. utiliza esa máscara para seleccionar las coordenadas del grupo; y
5. agrega una traza `go.Scatter` con un color propio.

Los colores se eligen de `SEGMENT_COLORS` y se reutilizan mediante el operador
módulo si existen más segmentos que colores. El número mostrado al pasar el
cursor corresponde a la posición del registro procesado, comenzando en 1.

Si existe la etiqueta `-1`, se agrega una traza adicional llamada **Sin
segmento**. Sus puntos son grises y utilizan el símbolo `x`, lo que permite
diferenciarlos de los grupos aun sin depender únicamente del color.

La vista inserta el resultado con `st.plotly_chart` en
[`app/segments.py`](../../app/segments.py#L487-L515). Si la proyección no está
disponible, presenta una explicación en lugar de un gráfico vacío.

## 9. Calidad silhouette

Silhouette resume si cada registro está cerca de su propio grupo y separado de
los demás. El backend solo la calcula cuando existen al menos dos grupos válidos
y suficientes puntos. En DBSCAN excluye los registros marcados como ruido antes
de calcularla. Esta validación se encuentra en
[`ClusteringAlgorithm._safe_silhouette()`](../../smarteda/analysis/clustering.py#L67-L78).

El frontend traduce la puntuación en
[`_quality_details()`](../../app/segments.py#L36-L72):

| Puntuación | Lectura | Interpretación |
|---|---|---|
| `None` | No evaluable | Solo existe un grupo útil o no hay suficientes datos comparables. |
| `0.50` o más | Buena | Los grupos están razonablemente separados. |
| `0.25` a menos de `0.50` | Moderada | Existe estructura, pero algunos registros podrían encajar en varios grupos. |
| Menos de `0.25` | Baja | Los grupos están poco definidos y deben tratarse como hipótesis. |

La pantalla muestra tanto la categoría como el valor con dos decimales, si está
disponible. También incluye una explicación cotidiana usando la analogía de
personas sentadas en mesas. La tarjeta y el panel explicativo se construyen en
[`app/segments.py`](../../app/segments.py#L517-L553), y sus estilos están en
[`app/assets/styles.css`](../../app/assets/styles.css#L654-L682).

Una puntuación alta mide separación matemática; no garantiza que los grupos sean
útiles para una decisión real.

## 10. Tamaño de los segmentos

Esta sección presenta la misma información de dos maneras: tarjetas individuales
y un gráfico comparativo.

### Tarjetas por segmento

[`_render_segment_cards()`](../../app/segments.py#L231-L283) obtiene los segmentos
ordenados y crea hasta tres columnas. Después recorre cada par `(etiqueta,
tamaño)` y calcula:

```python
percentage = size / total * 100
```

Cada tarjeta muestra número de segmento, cantidad de registros, porcentaje del
total y una barra proporcional. También indica si es el grupo más grande, el más
pequeño o uno de tamaño intermedio.

La posición se decide con `index % len(columns)`, de modo que los segmentos se
distribuyen entre las columnas sin escribir una ubicación fija para cada uno.

Si existe ruido de DBSCAN, se agrega una tarjeta independiente. Esta aclara que
los registros sin segmento no son necesariamente errores; pueden representar
casos válidos poco frecuentes. Los estilos de ambas clases de tarjeta están en
[`app/assets/styles.css`](../../app/assets/styles.css#L572-L652).

### Gráfico de tamaños

[`build_segment_size_chart()`](../../app/segments.py#L175-L214) crea una barra por
segmento con su cantidad de registros. Si existe ruido, añade una barra gris
**Sin segmento**. Los valores aparecen sobre las barras y también en el detalle
interactivo de Plotly.

La función no vuelve a contar las etiquetas: consume los tamaños que ya entregó
el backend.

## 11. Orientaciones de uso

La sección **Cómo usar estos segmentos** genera tres tarjetas a partir de reglas
de presentación. No ejecuta un modelo nuevo.

[`_decision_guidance()`](../../app/segments.py#L286-L350) evalúa:

1. **Calidad:** si silhouette es al menos `0.50`, propone comparar resultados por
   segmento; en caso contrario, pide tratar los grupos como una hipótesis.
2. **Equilibrio:** si el grupo más grande representa al menos 60 % del conjunto,
   advierte que no se deben ignorar los grupos pequeños. Si no domina, propone
   probar estrategias diferenciadas.
3. **Validación:** si DBSCAN dejó ruido, recomienda revisar esos casos. Si no,
   recuerda que el significado de cada grupo debe obtenerse con conocimiento del
   contexto.

`_render_decision_guidance()` combina las tres orientaciones con tres columnas y
crea una tarjeta en cada una. Su implementación está en
[`app/segments.py`](../../app/segments.py#L353-L370), y comparte los estilos de
orientación definidos en
[`app/assets/styles.css`](../../app/assets/styles.css#L523-L570).

## 12. Estados especiales

| Situación | Respuesta de la pantalla |
|---|---|
| No existe reporte | Solicita analizar primero un archivo. |
| `report.clustering is None` | Explica que no fue posible crear grupos. |
| `n_clusters == 0` | Informa que DBSCAN no encontró grupos estables. |
| `projection_2d is None` | Mantiene el resultado, pero omite el mapa 2D. |
| `silhouette is None` | Muestra calidad **No evaluable**. |
| Existen etiquetas `-1` | Las presenta como registros **Sin segmento**. |

Estos estados permiten diferenciar entre “no se pudo ejecutar”, “no se encontró
una estructura estable” y “sí hay grupos, pero una visualización o métrica no es
válida”.

## 13. Componentes y responsabilidades

| Función o componente | Responsabilidad |
|---|---|
| `render_segments_view()` | Coordina el contenido y los estados de la pantalla. |
| `_segment_items()` | Ordena segmentos y excluye el ruido. |
| `_noise_count()` | Cuenta los registros con etiqueta `-1`. |
| `_quality_details()` | Traduce silhouette a lenguaje sencillo. |
| `build_segment_scatter()` | Convierte etiquetas y coordenadas en el mapa Plotly. |
| `_render_segment_cards()` | Crea las tarjetas de tamaño mediante un ciclo. |
| `build_segment_size_chart()` | Compara los tamaños con barras. |
| `_render_method_details()` | Explica K-Means o DBSCAN y sus parámetros. |
| `_decision_guidance()` | Deriva orientaciones de los resultados existentes. |
| `_render_empty_state()` | Comunica por qué no hay un resultado visualizable. |

## Limitación actual

El reporte indica qué etiqueta recibió cada registro y qué variables se usaron,
pero no entrega promedios o características resumidas por grupo. Por ello, el
frontend puede mostrar tamaño, ubicación y calidad, pero no afirmar qué define a
cada segmento.

Para describirlos como “grupo joven”, “alto consumo” o similares sería necesario
que el backend proporcionara perfiles por segmento o que se incorporara una
nueva transformación acordada con el equipo. La propia pantalla deja constancia
de esta limitación en
[`app/segments.py`](../../app/segments.py#L617-L635).

## Explicación breve para una exposición

> La pantalla Segmentos consume `report.clustering`, que contiene el algoritmo,
> una etiqueta por registro, tamaños, variables utilizadas, calidad silhouette,
> parámetros y una proyección 2D. El backend de Julián imputa los datos faltantes,
> estandariza las variables y ejecuta K-Means o DBSCAN. También calcula los
> tamaños, la calidad y la proyección PCA. En el frontend recorremos las etiquetas
> para separar los puntos por color, creamos tarjetas por grupo y generamos dos
> gráficos con Plotly. La visualización muestra similitud matemática, pero el
> significado real de cada segmento debe validarse con el contexto.

---

[← Capítulo 3: Relaciones](03-relaciones.md) · [Capítulo 5: Datos inusuales →](05-datos-inusuales.md)
