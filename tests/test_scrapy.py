"""Pruebas del proyecto Scrapy: pipeline de limpieza y spider fuera de línea."""
import json
import os
import subprocess
import sys

import pandas as pd
import pytest
from scrapy.exceptions import DropItem

from conftest import SCRAPY_PROYECTO
from ml_scrapy.pipelines import LimpiezaPipeline


@pytest.fixture
def pipeline():
    p = LimpiezaPipeline()
    p.open_spider()
    return p


def item(**extra):
    base = {"titulo": "Samsung Galaxy A55 128 GB", "precio_actual": "1.199.000",
            "url": "https://www.mercadolibre.com.co/a55/p/MCO999", "envio_gratis": "Envío gratis"}
    return base | extra


def test_pipeline_normaliza_campos(pipeline):
    r = pipeline.process_item(item(rating="4,7", descuento_pct="10% OFF"))
    assert r["precio_actual"] == 1199000
    assert r["descuento_pct"] == 10
    assert r["rating"] == 4.7
    assert r["envio_gratis"] is True
    assert r["id"] == "MCO999"
    assert r["capacidad_gb"] == 128
    assert r["condicion"] == "Nuevo"


def test_pipeline_descarta_incompletos(pipeline):
    with pytest.raises(DropItem):
        pipeline.process_item(item(precio_actual=None))


def test_pipeline_descarta_duplicados(pipeline):
    pipeline.process_item(item())
    with pytest.raises(DropItem):
        pipeline.process_item(item())


def test_spider_fuera_de_linea(salida):
    """Ejecuta el spider real con origen=local, como lo hace el pipeline de CI."""
    subprocess.run(
        [sys.executable, "-m", "scrapy", "crawl", "galaxy_a55", "-a", "origen=local",
         "-s", "LOG_LEVEL=ERROR", "-s", "DOWNLOAD_DELAY=0", "-s", "AUTOTHROTTLE_ENABLED=False"],
        cwd=SCRAPY_PROYECTO, env=os.environ | {"EA2_SALIDA": str(salida)}, check=True, timeout=120,
    )
    df = pd.read_csv(salida / "data" / "scrapy_listado.csv")
    metricas = json.loads((salida / "data" / "metricas_scrapy.json").read_text(encoding="utf-8"))

    assert len(df) == 119
    assert not df.duplicated(subset=["id", "titulo", "precio_actual"]).any()
    assert metricas["descartados"] == 4          # repetidos entre páginas
    assert metricas["paginas"] == 3
    assert set(df["fuente"]) == {"html_selenium"}
