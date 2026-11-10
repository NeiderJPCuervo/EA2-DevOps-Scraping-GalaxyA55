"""Spider de Scrapy para el listado "samsung galaxy a55" de Mercado Libre Colombia.

Uso (desde scraping/ml_scrapy):
    scrapy crawl galaxy_a55                 # intenta el sitio en vivo
    scrapy crawl galaxy_a55 -a origen=local # usa el HTML guardado por Selenium

Si el sitio responde con la página de verificación anti-bot, el spider no la
evade: cambia automáticamente al HTML guardado en data/raw/.
"""
import json
import time
from datetime import datetime

import scrapy

import config
from ml_scrapy.items import ProductoItem


def css_primero(nodo, selectores, attr=None):
    """Primer selector CSS que devuelva algo (texto o atributo)."""
    for sel in selectores:
        consulta = f"{sel}::attr({attr})" if attr else f"{sel} ::text"
        valores = [v.strip() for v in nodo.css(consulta).getall() if v.strip()]
        if valores:
            return valores[0] if attr else " ".join(valores)
    return None


class GalaxyA55Spider(scrapy.Spider):
    name = "galaxy_a55"

    def __init__(self, origen="web", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.origen = origen
        self.bloqueado = False
        self.paginas = 0
        self.inicio = time.time()

    async def start(self):
        if self.origen == "local":
            for req in self.peticiones_locales():
                yield req
        else:
            yield scrapy.Request(config.url_pagina(1), cb_kwargs={"n": 1})

    def peticiones_locales(self):
        archivos = sorted(config.RAW_DIR.glob("listado_p*.html"))
        if not archivos:
            self.logger.error("No hay HTML en data/raw/. Ejecute 01_selenium_navegador.py")
        for i, ruta in enumerate(archivos, start=1):
            yield scrapy.Request(ruta.as_uri(), cb_kwargs={"n": i},
                                 meta={"dont_obey_robotstxt": True}, dont_filter=True)

    def parse(self, response, n):
        if config.RUTA_VERIFICACION in response.url:
            self.logger.warning("Verificación anti-bot detectada; se usa el HTML local.")
            self.bloqueado = True
            yield from self.peticiones_locales()
            return

        self.paginas += 1
        fuente = "html_selenium" if response.url.startswith("file:") else "en_vivo"
        sel = config.SEL_LISTADO
        tarjetas = []
        for s in sel["item"]:
            tarjetas = response.css(s)
            if tarjetas:
                break
        for t in tarjetas:
            yield ProductoItem(
                titulo=css_primero(t, sel["titulo"]),
                url=css_primero(t, sel["titulo"], attr="href"),
                precio_actual=css_primero(t, sel["precio_actual"]),
                precio_anterior=css_primero(t, sel["precio_anterior"]),
                descuento_pct=css_primero(t, sel["descuento"]),
                envio_gratis=css_primero(t, sel["envio"]),   # el pipeline lo convierte a bool
                vendedor=css_primero(t, sel["vendedor"]),
                rating=css_primero(t, sel["rating"]),
                n_opiniones=css_primero(t, sel["n_opiniones"]),
                condicion=css_primero(t, sel["condicion"]),
                pagina=n,
                fuente=fuente,
            )

        # Paginación en vivo: seguir el botón "Siguiente" hasta MAX_PAGINAS
        if fuente == "en_vivo" and n < config.MAX_PAGINAS:
            siguiente = css_primero(response, sel["siguiente"], attr="href")
            if siguiente:
                yield response.follow(siguiente, cb_kwargs={"n": n + 1})

    def closed(self, reason):
        stats = self.crawler.stats.get_stats()
        metricas = {
            "herramienta": "Scrapy",
            "registros": stats.get("item_scraped_count", 0),
            "descartados": stats.get("item_dropped_count", 0),
            "paginas": self.paginas,
            "bloqueo_en_vivo": self.bloqueado,
            "origen": self.origen,
            "segundos": round(time.time() - self.inicio, 1),
            "fecha": datetime.now().isoformat(timespec="seconds"),
        }
        (config.DATA_DIR / "metricas_scrapy.json").write_text(json.dumps(metricas, indent=2),
                                                              encoding="utf-8")
