"""Pruebas unitarias de las funciones de limpieza de parsers.py."""
import pytest
from bs4 import BeautifulSoup

from parsers import es_galaxy_a55, es_reacondicionado, extraer_capacidad, extraer_id, limpiar_precio, parsear_tarjeta


@pytest.mark.parametrize("texto, esperado", [
    ("1.849.520", 1849520),
    ("$ 874.950", 874950),
    ("24% OFF", 24),
    ("", None),
    (None, None),
    ("sin precio", None),
])
def test_limpiar_precio(texto, esperado):
    assert limpiar_precio(texto) == esperado


@pytest.mark.parametrize("url, esperado", [
    ("https://www.mercadolibre.com.co/samsung-galaxy-a55/p/MCO2000060471#pos=1", "MCO2000060471"),
    ("https://articulo.mercadolibre.com.co/MCO-1234567-samsung-a55", "MCO1234567"),
    ("https://www.mercadolibre.com.co/x/up/MCOU5310303229?wid=MCO4491574070", "MCO4491574070"),
    ("https://www.mercadolibre.com.co/ayuda", None),
    (None, None),
])
def test_extraer_id(url, esperado):
    assert extraer_id(url) == esperado


@pytest.mark.parametrize("titulo, esperado", [
    ("Samsung Galaxy A55 5G 256 GB Azul", 256),
    ("Galaxy A55 128gb 8gb Ram", 128),
    ("Samsung Galaxy A55 5g", None),
    (None, None),
])
def test_extraer_capacidad(titulo, esperado):
    assert extraer_capacidad(titulo) == esperado


@pytest.mark.parametrize("titulo, esperado", [
    ("Samsung Galaxy A55 5G", True),
    ("Samsung Galaxy A 55 128 GB", True),
    ("Samsung Galaxy A54 5G", False),
    ("Samsung Galaxy A550 (no existe)", False),
    ("", False),
])
def test_es_galaxy_a55(titulo, esperado):
    assert es_galaxy_a55(titulo) is esperado


def test_es_reacondicionado_por_titulo_o_condicion():
    assert es_reacondicionado("Galaxy A55 - Bueno (Reacondicionado)")
    assert es_reacondicionado("Galaxy A55", "Usado")
    assert not es_reacondicionado("Galaxy A55 nuevo sellado", "Nuevo")


TARJETA = """
<li class="ui-search-layout__item"><div class="poly-card">
  <a class="poly-component__title" href="https://www.mercadolibre.com.co/a55/p/MCO123">
    Samsung Galaxy A55 5G 256 GB</a>
  <span class="poly-component__item-condition">Reacondicionado</span>
  <s class="andes-money-amount--previous"><span class="andes-money-amount__fraction">2.000.000</span></s>
  <div class="poly-price__current"><span class="andes-money-amount__fraction">1.520.000</span></div>
  <span class="poly-price__discount-polylabel">24% OFF</span>
  <div class="poly-component__shipping-v2">Envío gratis</div>
  <span class="poly-component__review-compacted"><span class="polylabel-label">4,8</span></span>
</div></li>
"""


def test_parsear_tarjeta_con_todos_los_campos():
    tarjeta = BeautifulSoup(TARJETA, "lxml").select_one("li")
    p = parsear_tarjeta(tarjeta)
    assert p["id"] == "MCO123"
    assert p["titulo"] == "Samsung Galaxy A55 5G 256 GB"
    assert p["precio_actual"] == 1520000
    assert p["precio_anterior"] == 2000000
    assert p["descuento_pct"] == 24
    assert p["envio_gratis"] is True
    assert p["rating"] == 4.8
    assert p["capacidad_gb"] == 256
    assert p["condicion"] == "Reacondicionado"
    assert p["reacondicionado"] is True


def test_parsear_tarjeta_sin_condicion_se_asume_nuevo():
    html = TARJETA.replace('<span class="poly-component__item-condition">Reacondicionado</span>', "")
    p = parsear_tarjeta(BeautifulSoup(html, "lxml").select_one("li"))
    assert p["condicion"] == "Nuevo"
    assert p["reacondicionado"] is False
