import scrapy


class ProductoItem(scrapy.Item):
    id = scrapy.Field()
    titulo = scrapy.Field()
    precio_actual = scrapy.Field()
    precio_anterior = scrapy.Field()
    descuento_pct = scrapy.Field()
    envio_gratis = scrapy.Field()
    full = scrapy.Field()
    vendedor = scrapy.Field()
    rating = scrapy.Field()
    n_opiniones = scrapy.Field()
    capacidad_gb = scrapy.Field()
    condicion = scrapy.Field()
    reacondicionado = scrapy.Field()
    pagina = scrapy.Field()
    fuente = scrapy.Field()
    url = scrapy.Field()
