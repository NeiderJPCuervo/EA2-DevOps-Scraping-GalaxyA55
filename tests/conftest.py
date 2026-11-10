"""Configuración común de pytest.

Las pruebas trabajan sin conexión a Mercado Libre: usan el HTML que Selenium
guardó en data/raw/ y escriben sus resultados en una carpeta temporal
(variable EA2_SALIDA), así nunca modifican los datos versionados.
"""
import importlib.util
import os
import sys
import tempfile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
SCRAPING = RAIZ / "scraping"
SCRAPY_PROYECTO = SCRAPING / "ml_scrapy"

# Debe definirse antes de importar config.py, que fija las rutas al cargarse
os.environ.setdefault("EA2_SALIDA", tempfile.mkdtemp(prefix="ea2_pruebas_"))
for ruta in (SCRAPING, SCRAPY_PROYECTO):
    sys.path.insert(0, str(ruta))


def cargar_script(nombre):
    """Importa un script cuyo nombre empieza por número (p. ej. 04_analisis.py)."""
    spec = importlib.util.spec_from_file_location(nombre.removesuffix(".py"), SCRAPING / nombre)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture(scope="session")
def salida():
    return Path(os.environ["EA2_SALIDA"])


@pytest.fixture(scope="session")
def html_listados():
    archivos = sorted((RAIZ / "data" / "raw").glob("listado_p*.html"))
    assert archivos, "faltan los HTML de data/raw/ capturados por Selenium"
    return [a.read_text(encoding="utf-8") for a in archivos]
