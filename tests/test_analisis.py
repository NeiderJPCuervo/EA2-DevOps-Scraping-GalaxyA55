"""Prueba de regresión del análisis: debe reproducir las cifras de la EA1."""
import json
import os
import subprocess
import sys

import pandas as pd
import pytest

from conftest import SCRAPING, cargar_script


@pytest.fixture(scope="module")
def resumen(salida):
    subprocess.run([sys.executable, "02_bs4_listado.py", "--local"], cwd=SCRAPING,
                   env=os.environ | {"EA2_SALIDA": str(salida)}, check=True,
                   capture_output=True, timeout=120)
    cargar_script("04_analisis.py").main()
    return json.loads((salida / "data" / "resumen.json").read_text(encoding="utf-8"))


def test_cifras_de_la_ea1(resumen):
    assert resumen["publicaciones_totales"] == 119
    assert resumen["publicaciones_a55"] == 30
    assert resumen["precio"]["50%"] == 874950
    assert resumen["pct_envio_gratis"] == 90.0
    assert resumen["pct_reacondicionado"] == 80.0


def test_mediana_por_condicion(resumen):
    medianas = {c["condicion"]: c["median"] for c in resumen["por_condicion"]}
    assert medianas["Nuevo"] == 1895180
    assert medianas["Nuevo"] > medianas["Usado"]


def test_figuras_generadas(resumen, salida):
    for nombre in ("fig1_histograma_precios.png", "fig2_precio_por_condicion.png",
                   "fig3_caracteristicas_oferta.png"):
        assert (salida / "figuras" / nombre).stat().st_size > 10_000


def test_clasificar_separa_accesorios():
    analisis = cargar_script("04_analisis.py")
    df = pd.DataFrame({
        "id": ["MCO1", "MCO2", "MCO3", "MCO3"],
        "titulo": ["Samsung Galaxy A55 256 GB", "Funda Galaxy A55", "Samsung Galaxy A34", "Samsung Galaxy A34"],
        "precio_actual": [1_500_000, 35_000, 700_000, 700_000],
        "condicion": ["Nuevo", None, "Usado", "Usado"],
        "reacondicionado": [False, False, True, True],
    })
    r = analisis.clasificar(df)
    assert len(r) == 3                                   # quita el duplicado
    assert r["es_a55"].tolist() == [True, True, False]
    assert r["es_accesorio"].tolist() == [False, True, False]
    assert r["condicion"].tolist() == ["Nuevo", "Nuevo", "Usado"]
