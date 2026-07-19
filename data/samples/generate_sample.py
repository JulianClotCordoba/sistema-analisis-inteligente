"""Genera un dataset de muestra tipo 'clientes' para pruebas y demostraciones.

Produce grupos naturales (para clustering), correlaciones claras, una
dependencia categórica -> numérica y algunos valores atípicos. Ejecutar con:

    python data/samples/generate_sample.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

RANDOM_STATE = 42


def generate(n_per_group: int = 60) -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_STATE)
    regions = ["Norte", "Sur", "Centro"]
    # Cada región tiene un perfil distinto de edad e ingreso (crea grupos).
    centers = {
        "Norte": (28, 30_000),
        "Sur": (45, 65_000),
        "Centro": (60, 90_000),
    }
    rows = []
    for region in regions:
        age_c, income_c = centers[region]
        for _ in range(n_per_group):
            age = rng.normal(age_c, 4)
            income = rng.normal(income_c, 6_000)
            # gasto correlacionado con el ingreso.
            spending = income * 0.35 + rng.normal(0, 3_000)
            rows.append(
                {
                    "edad": round(float(age)),
                    "ingreso_anual": round(float(income), 2),
                    "gasto_anual": round(float(spending), 2),
                    "region": region,
                    "cliente_activo": bool(rng.random() > 0.3),
                }
            )
    df = pd.DataFrame(rows)

    # Inyectar unos pocos atípicos evidentes.
    outliers = pd.DataFrame(
        {
            "edad": [95, 18, 90],
            "ingreso_anual": [250_000.0, 5_000.0, 300_000.0],
            "gasto_anual": [10_000.0, 90_000.0, 5_000.0],
            "region": ["Norte", "Sur", "Centro"],
            "cliente_activo": [True, False, True],
        }
    )
    df = pd.concat([df, outliers], ignore_index=True)
    return df.sample(frac=1, random_state=RANDOM_STATE).reset_index(drop=True)


if __name__ == "__main__":
    output = Path(__file__).parent / "clientes.csv"
    generate().to_csv(output, index=False)
    print(f"Dataset generado en: {output}")
