"""Prueba de integración: BeautifulSoup sobre el HTML real capturado por Selenium.

Si Mercado Libre cambia sus clases y se vuelven a capturar las páginas, esta
prueba avisa de inmediato que los selectores de config.py dejaron de servir.
"""
from parsers import es_galaxy_a55, parsear_listado


def test_cada_pagina_tiene_publicaciones(html_listados):
    conteos = [len(parsear_listado(h)) for h in html_listados]
    assert conteos == [48, 48, 27]


def test_campos_obligatorios_y_precios_validos(html_listados):
    productos = [p for h in html_listados for p in parsear_listado(h)]
    for p in productos:
        assert p["titulo"]
        assert p["precio_actual"] > 0
        assert p["id"] and p["id"].startswith("MCO")
        assert p["url"].startswith("https://")
        assert p["condicion"] in {"Nuevo", "Usado", "Reacondicionado", "Caja abierta"}


def test_selectores_de_envio_y_condicion_siguen_vigentes(html_listados):
    """En la EA1 un selector viejo dejaba el envío gratis siempre en falso."""
    productos = [p for h in html_listados for p in parsear_listado(h)]
    a55 = [p for p in productos if es_galaxy_a55(p["titulo"])]
    assert a55, "no se reconoció ningún Galaxy A55"
    assert sum(p["envio_gratis"] for p in a55) / len(a55) > 0.5
    assert any(p["condicion"] != "Nuevo" for p in a55)
