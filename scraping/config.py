"""Configuración común para los scrapers de Mercado Libre Colombia.

Todos los scripts importan desde aquí la URL, los selectores CSS y las rutas
de salida, de modo que si Mercado Libre cambia su HTML basta con ajustar
este archivo.
"""
from pathlib import Path

# --- Rutas del proyecto -----------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"          # HTML capturado por Selenium
FIG_DIR = BASE_DIR / "figuras"
for d in (DATA_DIR, RAW_DIR, FIG_DIR):
    d.mkdir(parents=True, exist_ok=True)

# --- Objetivo del scraping --------------------------------------------------
SITIO = "Mercado Libre Colombia"
TERMINO_BUSQUEDA = "samsung galaxy a55"
URL_LISTADO = "https://listado.mercadolibre.com.co/samsung-galaxy-a55"
ITEMS_POR_PAGINA = 48               # Mercado Libre pagina con _Desde_49, _Desde_97...
MAX_PAGINAS = 3                     # volumen bajo: uso académico

def url_pagina(n: int) -> str:
    """URL de la página n (1, 2, 3...) del listado."""
    if n <= 1:
        return URL_LISTADO
    desde = (n - 1) * ITEMS_POR_PAGINA + 1
    return f"{URL_LISTADO}_Desde_{desde}_NoIndex_True"

# --- Cortesía con el servidor ----------------------------------------------
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0 "
    "(proyecto academico EA1)"
)
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "es-CO,es;q=0.9",
}
RETARDO_SEGUNDOS = 3                # pausa entre peticiones
TIMEOUT = 20

# Si la respuesta termina en esta ruta, Mercado Libre pidió verificación
# anti-bot. NO se intenta evadirla: se registra y se usa el HTML que el
# usuario capturó con Selenium en un navegador real.
RUTA_VERIFICACION = "/gz/account-verification"

# --- Selectores CSS (con alternativas: diseño "poly-card" y diseño anterior) -
SEL_LISTADO = {
    "item":        ["li.ui-search-layout__item", "div.ui-search-result__wrapper", "div.poly-card"],
    "titulo":      ["a.poly-component__title", "h3.poly-component__title-wrapper a",
                    "h2.ui-search-item__title", "a.ui-search-link__title-card"],
    "precio_actual": ["div.poly-price__current span.andes-money-amount__fraction",
                      "div.ui-search-price__second-line span.andes-money-amount__fraction",
                      "span.andes-money-amount__fraction"],
    "precio_anterior": ["s.andes-money-amount--previous span.andes-money-amount__fraction",
                        "s span.andes-money-amount__fraction"],
    "descuento":   ["span.poly-price__discount-polylabel", "span.andes-money-amount__discount", "span.poly-price__disc_label",
                    "span.ui-search-price__discount"],
    "envio":       ["div.poly-component__shipping-v2", "div.poly-component__shipping", "p.ui-search-item__shipping"],
    "vendedor":    ["span.poly-component__seller", "p.ui-search-official-store-label"],
    "rating":      ["span.poly-component__review-compacted span.polylabel-label",
                    "span.poly-reviews__rating", "span.ui-search-reviews__rating-number"],
    "condicion":   ["span.poly-component__item-condition"],        # "Reacondicionado", "Usado"
    "n_opiniones": ["span.poly-reviews__total", "span.ui-search-reviews__amount"],
    "siguiente":   ["li.andes-pagination__button--next a"],
}

SEL_DETALLE = {
    "titulo":      ["h1.ui-pdp-title"],
    "subtitulo":   ["span.ui-pdp-subtitle"],             # "Nuevo | +1000 vendidos"
    "precio":      ["div.ui-pdp-price__second-line span.andes-money-amount__fraction"],
    "rating":      ["span.ui-pdp-review__rating"],
    "n_opiniones": ["span.ui-pdp-review__amount"],
    "vendedor":    ["div.ui-pdp-seller-summary__header__title", "div.ui-pdp-seller__header__title", "button.ui-pdp-seller__link-trigger-button",
                    "span.ui-pdp-seller__label-sold"],
    "reputacion":  ["div.ui-pdp-seller-summary__header__subtitle"],  # "MercadoLíder | +50 mil ventas"
    "stock":       ["span.ui-pdp-buybox__quantity__available", "p.ui-pdp-stock-information__title"],
    "fila_spec":   ["tr.andes-table__row"],
    "opinion":     ["p.ui-review-capability-comments__comment__content",
                    "article.ui-review-capability-comments__comment p"],
}
