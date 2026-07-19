# data/samples

Datasets de prueba para desarrollo y demostraciones.

- **`clientes.csv`** — dataset sintético de clientes (edad, ingreso anual, gasto
  anual, región, cliente activo). Generado con `generate_sample.py` con semilla
  fija, por lo que es reproducible. Contiene tres grupos naturales por región,
  correlación fuerte entre ingreso y gasto, dependencia región → ingreso y unos
  pocos valores atípicos inyectados. Ideal para probar clustering, correlación y
  detección de anomalías.

Para regenerarlo:

```bash
python data/samples/generate_sample.py
```

## Otros datasets públicos recomendados para pruebas

- **Mall Customers** (Kaggle): edad, ingreso anual, spending score — clásico de
  clustering, muy parecido al ejemplo de la propuesta.
- **Iris** / **Wine** (`sklearn.datasets`): numéricos y limpios.
- **Penguins** / **Tips** (`seaborn`): mezcla de numéricas y categóricas con NaN,
  útiles para probar la detección de tipos.
