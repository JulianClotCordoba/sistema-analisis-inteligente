# 6. Pantalla Reporte

[← Volver a Datos inusuales](05-datos-inusuales.md)

## Objetivo de la pantalla

La pantalla **Reporte** funciona como cierre del análisis. Reúne la estructura
del archivo, relaciones, segmentos, datos inusuales y hallazgos en una lectura
ejecutiva que puede consultarse en la aplicación o descargarse como PDF.

La vista se construye en
[`render_report_view()`](../../app/reporting.py#L635-L800), mientras que el
documento descargable se genera en
[`generate_pdf_report()`](../../app/reporting.py#L371-L581).

Esta pantalla responde preguntas como:

- ¿Cuál es la conclusión general del análisis?
- ¿Qué encontró cada módulo?
- ¿Qué hallazgos deberían comunicarse primero?
- ¿Cuáles son los siguientes pasos prudentes?
- ¿Cómo se puede compartir el resultado sin abrir SmartEDA?

> El reporte organiza evidencia y propone próximos pasos. No convierte patrones
> estadísticos en decisiones automáticas.

## Flujo de datos

```text
                       AnalysisReport
                             │
        ┌──────────────┬──────┴──────┬──────────────┐
        ▼              ▼             ▼              ▼
     profile      correlations   clustering     anomalies
        │              │             │              │
        └──────────────┴──────┬──────┴──────────────┘
                              ▼
            resumen ejecutivo + recomendaciones
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
             vista Streamlit      PDF en memoria
                                        │
                                        ▼
                              botón de descarga
```

El reporte consume todos los bloques disponibles del contrato:

| Campo | Uso principal |
|---|---|
| `report.profile` | Registros, variables y faltantes. |
| `report.correlations` | Relaciones numéricas fuertes. |
| `report.dependencies` | Diferencias relevantes entre categorías. |
| `report.clustering` | Algoritmo, cantidad, tamaños y calidad de segmentos. |
| `report.anomalies` | Comparación de métodos y coincidencias. |
| `report.insights` | Hallazgos redactados por el backend. |
| `report.descriptive` | Estadísticas descriptivas opcionales. |
| `report.metadata` | Fecha, fuente y duración del análisis. |

La pantalla no vuelve a abrir el archivo ni a ejecutar `AnalysisEngine`.

## 1. Tecnologías utilizadas

La página visible continúa utilizando **Streamlit**, HTML y CSS. Para crear el
archivo descargable se utiliza **ReportLab**, una librería de Python que permite
construir documentos PDF mediante párrafos, tablas, espacios y saltos de página.

Los elementos principales se importan en
[`app/reporting.py`](../../app/reporting.py#L1-L28):

- `SimpleDocTemplate`, para configurar el documento;
- `Paragraph`, para textos;
- `Table` y `TableStyle`, para indicadores y tablas;
- `Spacer`, para controlar separación;
- `PageBreak`, para dividir secciones; y
- `BytesIO`, para mantener el archivo en memoria.

ReportLab y pypdf están declarados entre las dependencias del frontend en
[`requirements.txt`](../../requirements.txt#L12-L15). ReportLab genera el
archivo; pypdf se utiliza en las pruebas para comprobar su contenido.

## 2. Funciones auxiliares de integración

Antes de construir la vista, varias funciones resumen datos del contrato sin
repetir los algoritmos.

### Fecha y faltantes

[`_generated_at()`](../../app/reporting.py#L57-L65) obtiene
`metadata["generated_at"]`, interpreta su formato ISO y lo presenta como
`día/mes/año hora:minuto`. Si no está disponible, utiliza un texto seguro.

[`_missing_total()`](../../app/reporting.py#L68-L69) recorre los perfiles de
columnas y suma `missing_count`, igual que la pantalla Resumen.

### Relaciones sin duplicados

[`_strong_relationships()`](../../app/reporting.py#L72-L84) combina los pares
fuertes de Pearson y Spearman. Utiliza un `frozenset` con los dos nombres para
evitar presentar dos veces la misma pareja en diferente orden o método.

La función revisa Pearson primero, por lo que conserva esa versión si un mismo
par aparece también en Spearman. Finalmente ordena los pares conservados por la
intensidad absoluta del coeficiente.

### Coincidencias de anomalías

[`_consensus_count()`](../../app/reporting.py#L87-L92) combina las máscaras con
AND y cuenta los registros señalados por todos los métodos.

[`_any_anomaly_count()`](../../app/reporting.py#L94-L98) utiliza OR y cuenta los
registros que recibieron al menos una señal. Es la misma idea utilizada en la
pantalla Datos inusuales.

### Calidad de segmentos

[`_cluster_quality()`](../../app/reporting.py#L101-L108) traduce silhouette con
los mismos límites utilizados en Segmentos:

- `0.50` o más: buena;
- `0.25` a menos de `0.50`: moderada;
- menos de `0.25`: baja; y
- sin puntuación: no evaluable.

## 3. Construcción del resumen ejecutivo

[`build_executive_summary()`](../../app/reporting.py#L111-L140) crea un texto
corto a partir de piezas condicionales.

Siempre comienza con la cantidad de registros y variables. Después agrega una
oración si existe cada resultado:

1. relación numérica más destacada, coeficiente y dirección;
2. cantidad de segmentos, algoritmo y calidad; y
3. registros con alguna señal y coincidencias de todos los detectores.

Finalmente une las oraciones con espacios. Esto permite que el resumen siga
siendo válido aunque un dataset no produzca correlaciones, segmentos o
anomalías.

El frontend no le pide al backend una nueva narración ni utiliza un servicio
externo: compone el texto con valores existentes y frases controladas.

## 4. Encabezado y métricas de la vista

[`render_report_view()`](../../app/reporting.py#L635-L674) verifica que exista un
reporte y presenta:

- nombre del archivo;
- fecha de generación;
- tiempo de procesamiento; y
- cuatro métricas generales.

| Tarjeta | Origen |
|---|---|
| **Registros** | `report.profile.n_rows` |
| **Variables** | `report.profile.n_cols` |
| **Hallazgos** | `len(report.insights)` |
| **Faltantes** | Suma de `missing_count` de todas las columnas |

El nombre del archivo y los textos se protegen con `html.escape` antes de
insertarse en los componentes HTML.

## 5. Lectura general y tarjetas de módulos

El texto generado por `build_executive_summary()` aparece dentro de una tarjeta
destacada en [`app/reporting.py`](../../app/reporting.py#L676-L689).

Después, [`_render_summary_cards()`](../../app/reporting.py#L584-L633) prepara
tres tarjetas:

| Tarjeta | Información presentada |
|---|---|
| **Relaciones** | Cantidad de pares únicos y nombres del principal. |
| **Segmentos** | Cantidad de grupos, calidad y algoritmo. |
| **Revisión** | Coincidencias de todos los detectores y registros con alguna señal. |

La función crea una lista de tres tuplas y la combina con tres columnas mediante
`zip`. Si un módulo no produjo resultados, muestra una explicación en vez de
suponer valores inexistentes.

Los estilos del resumen y de estas tarjetas se encuentran en
[`app/assets/styles.css`](../../app/assets/styles.css#L729-L782).

## 6. Vista previa de hallazgos

La columna izquierda muestra los primeros seis elementos de `report.insights`.
Un ciclo `for` revisa `insight.severity` y utiliza el estilo de advertencia cuando
corresponde. Los mensajes se escapan antes de mostrarse.

Esta construcción está en
[`app/reporting.py`](../../app/reporting.py#L707-L725). Si existen más de seis,
se informa que el PDF incluye una selección ejecutiva; dentro del documento se
utilizan los primeros siete hallazgos.

## 7. Recomendaciones automáticas

[`build_recommendations()`](../../app/reporting.py#L143-L174) transforma
resultados existentes en próximos pasos verificables:

- revisar juntas las variables de la relación principal, sin asumir causalidad;
- comparar la variable numérica según la dependencia categórica más alta;
- comparar indicadores entre segmentos;
- comenzar por las coincidencias de todos los detectores; y
- validar siempre los resultados con conocimiento del contexto.

Solo agrega una recomendación cuando existe el resultado necesario, excepto la
validación contextual, que siempre se incluye. La función devuelve como máximo
cinco mensajes.

En la vista, las recomendaciones se recorren con `enumerate` y se distribuyen en
dos columnas mediante `index % 2`. La implementación está en
[`app/reporting.py`](../../app/reporting.py#L758-L775), y sus estilos están en
[`app/assets/styles.css`](../../app/assets/styles.css#L807-L829).

## 8. Generación del PDF en memoria

La columna **Exportar** llama a `generate_pdf_report(report, filename)`. La
función devuelve bytes que Streamlit entrega directamente al navegador.

El proceso comienza en
[`app/reporting.py`](../../app/reporting.py#L371-L402):

1. obtiene únicamente el nombre seguro mediante `Path(...).name`;
2. crea un búfer `BytesIO`;
3. configura un `SimpleDocTemplate` tamaño A4;
4. define márgenes y metadatos del documento;
5. prepara los estilos; y
6. crea una lista `story` con los elementos del PDF.

`story` funciona como una secuencia: cada párrafo, tabla, espacio o salto de
página se agrega en el orden en que debe aparecer. Al final, ReportLab procesa
la lista y escribe el resultado en el búfer.

El archivo no se guarda en `output/` ni en una base de datos. Vive en memoria
durante la sesión y se entrega mediante
[`st.download_button`](../../app/reporting.py#L727-L756) con:

- nombre `smarteda_reporte_<archivo>.pdf`;
- tipo MIME `application/pdf`; y
- los bytes generados como contenido.

## 9. Estilos y tablas del PDF

La paleta del PDF se define con colores propios en
[`app/reporting.py`](../../app/reporting.py#L31-L38). No reutiliza directamente el
CSS, porque ReportLab no representa una página web.

[`_pdf_styles()`](../../app/reporting.py#L177-L270) define tipografía, tamaño,
color, alineación y separación para títulos, cuerpo, textos pequeños, cabeceras,
métricas y llamados destacados.

La función [`_p()`](../../app/reporting.py#L273-L274) convierte valores en
párrafos y aplica escape XML. Así, nombres de archivos, variables y hallazgos no
se interpretan como etiquetas internas de ReportLab.

### Tabla de métricas

[`_metric_table()`](../../app/reporting.py#L281-L313) construye cuatro celdas con
registros, variables, hallazgos y segmentos. Cada celda contiene un valor grande
y su etiqueta.

### Tablas de datos

[`_data_table()`](../../app/reporting.py#L316-L347) recibe filas, anchos y estilos.
Recorre cada fila y cada celda, las convierte en párrafos y construye una tabla
con:

- cabecera oscura;
- cuadrícula;
- relleno interno;
- filas alternadas; y
- repetición de cabecera cuando una tabla continúa en otra página.

Esta función común evita repetir la configuración en las tablas de relaciones,
dependencias, segmentos, anomalías y estadística descriptiva.

## 10. Contenido del documento descargable

El PDF sigue esta estructura:

### Portada y primera lectura

- nombre del archivo;
- fecha y duración;
- métricas principales;
- resumen ejecutivo; y
- primeros siete hallazgos.

Esta parte se construye en
[`app/reporting.py`](../../app/reporting.py#L389-L426).

### Relaciones y segmentos

- hasta cinco relaciones numéricas fuertes y únicas;
- hasta cinco dependencias categóricas;
- algoritmo y calidad de segmentación;
- tabla de tamaños y porcentajes; y
- advertencia sobre la interpretación de los grupos.

La construcción se encuentra en
[`app/reporting.py`](../../app/reporting.py#L427-L498).

### Datos inusuales y cierre

- tabla comparativa de Z-Score, IQR e Isolation Forest;
- coincidencias de todos los métodos;
- cantidad con al menos una señal;
- próximos pasos recomendados;
- alcance y limitaciones;
- metodología; y
- estadística descriptiva, si `report.descriptive` está disponible.

Estas secciones se crean en
[`app/reporting.py`](../../app/reporting.py#L500-L570).

El PDF es una versión ejecutiva textual y tabular. No incorpora los gráficos
interactivos de Plotly, porque esos gráficos pertenecen a la experiencia dentro
de la aplicación.

## 11. Encabezado, pie y numeración

[`_draw_page_frame()`](../../app/reporting.py#L350-L368) se ejecuta en la primera
página y en las siguientes. Dibuja:

- una franja superior con SmartEDA y el nombre del archivo;
- una línea inferior;
- la advertencia “validar antes de decidir”; y
- el número de página.

Al llamar a `doc.build`, la misma función se registra como `onFirstPage` y
`onLaterPages`. Después se obtienen los bytes finales con `buffer.getvalue()` en
[`app/reporting.py`](../../app/reporting.py#L572-L581).

## 12. Alcance y limitaciones

La vista y el PDF recuerdan expresamente que:

- una relación no demuestra causalidad;
- los segmentos necesitan interpretación del contexto;
- un registro inusual no debe eliminarse automáticamente;
- los resultados dependen de la calidad del archivo; y
- la fila procesada puede diferir de la original si la limpieza eliminó vacíos o
  duplicados.

El panel visible está en
[`app/reporting.py`](../../app/reporting.py#L777-L787), mientras que el PDF agrega
estas advertencias en
[`app/reporting.py`](../../app/reporting.py#L539-L548).

## 13. Estados opcionales

La generación se adapta a resultados parciales:

| Resultado ausente | Tratamiento en el reporte |
|---|---|
| Sin relaciones fuertes | Incluye una frase explicativa. |
| Sin dependencias | Omite la tabla categórica. |
| Sin segmentos estables | Informa que no fue posible formarlos. |
| Sin anomalías | Indica que no se generaron resultados. |
| Sin estadística descriptiva | Omite esa sección opcional. |

Esto permite generar un documento útil aun cuando el dataset no sea adecuado
para todos los análisis.

## 14. Verificación del PDF

Las pruebas de integración comprueban que la pantalla carga, muestra sus
métricas y ofrece el botón de descarga. También generan un PDF real, verifican
que comience con la firma `%PDF`, lo leen con pypdf y comprueban que tenga al
menos tres páginas y sus secciones principales. Estas verificaciones están en
[`tests/test_frontend_report.py`](../../tests/test_frontend_report.py#L18-L56).

## 15. Componentes y responsabilidades

| Función o componente | Responsabilidad |
|---|---|
| `render_report_view()` | Coordina la pantalla final y la descarga. |
| `build_executive_summary()` | Compone la lectura general. |
| `_render_summary_cards()` | Resume Relaciones, Segmentos y Revisión. |
| `build_recommendations()` | Produce próximos pasos condicionados por los resultados. |
| `generate_pdf_report()` | Construye el documento y devuelve sus bytes. |
| `_pdf_styles()` | Define la identidad visual del PDF. |
| `_metric_table()` | Presenta indicadores en la primera página. |
| `_data_table()` | Reutiliza el formato de las tablas analíticas. |
| `_draw_page_frame()` | Dibuja encabezado, pie y numeración. |
| `st.download_button` | Entrega el PDF al usuario. |

## Explicación breve para una exposición

> La pantalla Reporte consume todas las partes de `AnalysisReport` y las reúne
> sin repetir el análisis. El frontend combina los resultados para crear un
> resumen ejecutivo, tres tarjetas de módulos, una selección de hallazgos y
> próximos pasos. Después, ReportLab construye un PDF A4 completamente en
> memoria: recorremos relaciones, dependencias, segmentos, anomalías y
> estadísticas para crear tablas, agregamos metodología y limitaciones, y
> numeramos las páginas. Finalmente, Streamlit entrega esos bytes con un botón de
> descarga; el servidor no guarda permanentemente el documento.

---

[← Capítulo 5: Datos inusuales](05-datos-inusuales.md) · [Volver al índice](README.md)
