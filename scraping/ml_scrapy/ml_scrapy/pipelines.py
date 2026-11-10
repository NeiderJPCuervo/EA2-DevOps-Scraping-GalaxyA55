"""Pipeline: normaliza precios y elimina publicaciones duplicadas."""
from scrapy.exceptions import DropItem

from parsers import es_reacondicionado, extraer_capacidad, extraer_id, limpiar_precio


class LimpiezaPipeline:
    def open_spider(self, spider=None):
        self.vistos = set()

    def process_item(self, item, spider=None):
        if not item.get("titulo") or not item.get("precio_actual"):
            raise DropItem("sin título o precio")
        for campo in ("precio_actual", "precio_anterior", "descuento_pct", "n_opiniones"):
            item[campo] = limpiar_precio(item.get(campo))
        item["rating"] = float(item["rating"].replace(",", ".")) if item.get("rating") else None
        envio = (item.get("envio_gratis") or "").lower()
        item["envio_gratis"] = "gratis" in envio
        item["full"] = "full" in envio
        item["vendedor"] = (item.get("vendedor") or "").replace("Por ", "") or None
        item["id"] = extraer_id(item.get("url"))
        item["capacidad_gb"] = extraer_capacidad(item["titulo"])
        item["condicion"] = item.get("condicion") or "Nuevo"
        item["reacondicionado"] = es_reacondicionado(item["titulo"], item["condicion"])

        clave = (item["id"], item["titulo"], item["precio_actual"])
        if clave in self.vistos:
            raise DropItem("duplicado")
        self.vistos.add(clave)
        return item
