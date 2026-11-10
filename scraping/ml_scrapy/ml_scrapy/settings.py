"""Configuración de Scrapy: rastreo lento y respetuoso con el servidor."""
import sys
from pathlib import Path

# Reutiliza config.py y parsers.py de la carpeta scraping/
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config  # noqa: E402

BOT_NAME = "ml_scrapy"
SPIDER_MODULES = ["ml_scrapy.spiders"]
NEWSPIDER_MODULE = "ml_scrapy.spiders"

ROBOTSTXT_OBEY = True                 # respeta robots.txt
USER_AGENT = config.USER_AGENT
DEFAULT_REQUEST_HEADERS = {"Accept-Language": "es-CO,es;q=0.9"}
DOWNLOAD_DELAY = config.RETARDO_SEGUNDOS
CONCURRENT_REQUESTS_PER_DOMAIN = 1
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = config.RETARDO_SEGUNDOS
RETRY_TIMES = 1
COOKIES_ENABLED = True

ITEM_PIPELINES = {"ml_scrapy.pipelines.LimpiezaPipeline": 300}
FEEDS = {
    str(config.DATA_DIR / "scrapy_listado.csv"): {
        "format": "csv", "encoding": "utf8", "overwrite": True,
    },
}
FEED_EXPORT_FIELDS = [
    "id", "titulo", "precio_actual", "precio_anterior", "descuento_pct", "envio_gratis",
    "full", "vendedor", "rating", "n_opiniones", "capacidad_gb", "condicion", "reacondicionado",
    "pagina", "fuente", "url",
]
LOG_LEVEL = "INFO"
