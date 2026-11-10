"""Funciones de limpieza y parseo compartidas (BeautifulSoup)."""
import re
from bs4 import BeautifulSoup

from config import SEL_LISTADO


def limpiar_precio(texto):
    """'1.499.900' -> 1499900 (int, COP). Devuelve None si no hay número."""
    if not texto:
        return None
    digitos = re.sub(r"[^\d]", "", texto)
    return int(digitos) if digitos else None


def extraer_id(url):
    """Extrae el identificador MCO de una URL de Mercado Libre (MCO123456 o MCO-123456)."""
    if not url:
        return None
    m = re.search(r"MCO-?(\d+)", url)
    return f"MCO{m.group(1)}" if m else None


def extraer_capacidad(titulo):
    """Busca la capacidad de almacenamiento en el título: '256 GB' -> 256."""
    m = re.search(r"(\d{3})\s*gb", titulo or "", re.I)
    return int(m.group(1)) if m else None


def es_reacondicionado(titulo, condicion=None):
    return bool(re.search(r"reacondicionad|usado", f"{titulo or ''} {condicion or ''}", re.I))


def es_galaxy_a55(titulo):
    return bool(re.search(r"\ba\s?55\b", titulo or "", re.I))


def _primero(nodo, selectores):
    for sel in selectores:
        hallado = nodo.select_one(sel)
        if hallado is not None:
            return hallado
    return None


def _texto(nodo, selectores):
    hallado = _primero(nodo, selectores)
    return hallado.get_text(" ", strip=True) if hallado else None


def parsear_tarjeta(tarjeta):
    """Convierte una tarjeta del listado en un diccionario."""
    enlace = _primero(tarjeta, SEL_LISTADO["titulo"])
    titulo = enlace.get_text(" ", strip=True) if enlace else None
    url = enlace.get("href") if enlace else None
    descuento_txt = _texto(tarjeta, SEL_LISTADO["descuento"])
    envio_txt = (_texto(tarjeta, SEL_LISTADO["envio"]) or "").lower()
    n_op = _texto(tarjeta, SEL_LISTADO["n_opiniones"])
    rating = _texto(tarjeta, SEL_LISTADO["rating"])
    condicion = _texto(tarjeta, SEL_LISTADO["condicion"]) or "Nuevo"
    return {
        "id": extraer_id(url),
        "titulo": titulo,
        "precio_actual": limpiar_precio(_texto(tarjeta, SEL_LISTADO["precio_actual"])),
        "precio_anterior": limpiar_precio(_texto(tarjeta, SEL_LISTADO["precio_anterior"])),
        "descuento_pct": limpiar_precio(descuento_txt),
        "envio_gratis": "gratis" in envio_txt,
        "full": "full" in envio_txt,
        "vendedor": (_texto(tarjeta, SEL_LISTADO["vendedor"]) or "").replace("Por ", "") or None,
        "rating": float(rating.replace(",", ".")) if rating else None,
        "n_opiniones": limpiar_precio(n_op),
        "capacidad_gb": extraer_capacidad(titulo),
        "condicion": condicion,
        "reacondicionado": es_reacondicionado(titulo, condicion),
        "url": url,
    }


def parsear_listado(html):
    """Devuelve la lista de productos de una página de resultados."""
    soup = BeautifulSoup(html, "lxml")
    tarjetas = []
    for sel in SEL_LISTADO["item"]:
        tarjetas = soup.select(sel)
        if tarjetas:
            break
    productos = [parsear_tarjeta(t) for t in tarjetas]
    return [p for p in productos if p["titulo"] and p["precio_actual"]]
