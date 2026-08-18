"""Interfaz de línea de comandos.

Permite ejecutar el análisis desde la terminal, cumpliendo la opción de salida
"en consola" mencionada en la propuesta y sirviendo de respaldo si el dashboard
no estuviera disponible durante la presentación.

Uso::

    python -m smarteda ruta/al/archivo.csv
    python -m smarteda datos.xlsx --algorithm dbscan
"""

from __future__ import annotations

import argparse
import sys

from .analysis.descriptive import BasicDescriptiveStats
from .config import AnalysisConfig
from .engine import AnalysisEngine
from .exceptions import SmartEdaError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="smarteda",
        description="Análisis inteligente y exploratorio de datos tabulares.",
    )
    parser.add_argument(
        "files",
        nargs="+",
        help="Uno o varios archivos CSV o Excel a analizar.",
    )
    parser.add_argument(
        "--algorithm",
        choices=["kmeans", "dbscan"],
        default="kmeans",
        help="Algoritmo de clustering a utilizar (por defecto: kmeans).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada de la CLI. Devuelve el código de salida del proceso."""
    args = _build_parser().parse_args(argv)
    config = AnalysisConfig(clustering_algorithm=args.algorithm)
    engine = AnalysisEngine(config, descriptive_provider=BasicDescriptiveStats())

    exit_code = 0
    for file in args.files:
        try:
            report = engine.analyze(file)
        except SmartEdaError as exc:
            print(f"Error en '{file}': {exc}", file=sys.stderr)
            exit_code = 1
            continue
        _print_report(report)
    return exit_code


def _print_report(report) -> None:
    """Imprime en consola el resumen de un reporte."""
    print("\n" + "=" * 60)
    print(f"  ANÁLISIS DE: {report.metadata['source']}")
    print("=" * 60)
    print(
        f"  {report.metadata['n_rows']} registros x "
        f"{report.metadata['n_cols']} variables "
        f"({report.metadata['elapsed_seconds']} s)\n"
    )
    print("  INSIGHTS:")
    for insight in report.insights:
        marker = "[!]" if insight.severity == "warning" else " - "
        print(f"  {marker} {insight.message}")
    _print_descriptive(report)
    print("=" * 60 + "\n")


def _print_descriptive(report) -> None:
    """Imprime las medidas principales de cada variable numérica."""
    if report.descriptive is None or not report.descriptive.statistics:
        return
    print("\n  ESTADÍSTICA DESCRIPTIVA:")
    for variable, medidas in report.descriptive.statistics.items():
        print(
            f"   - {variable}: media={medidas['media']:.2f} | "
            f"mediana={medidas['mediana']:.2f} | "
            f"desviación={medidas['desviacion_estandar']:.2f} | "
            f"mínimo={medidas['minimo']:.2f} | máximo={medidas['maximo']:.2f}"
        )


if __name__ == "__main__":
    raise SystemExit(main())
