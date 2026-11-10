"""Scraper con Selenium (Firefox).

1. Abre el listado de búsqueda "samsung galaxy a55" en un navegador real,
   espera a que cargue el contenido generado con JavaScript y guarda el HTML
   de cada página en data/raw/ (lo reutilizan BeautifulSoup y Scrapy).
2. Entra a la ficha del Galaxy A55 más relevante y extrae precio, calificación,
   número de opiniones, vendedor, stock, especificaciones y opiniones visibles.

Uso:
    python 01_selenium_navegador.py            # navegador visible (recomendado)
    python 01_selenium_navegador.py --headless # sin ventana

Si Mercado Libre muestra una verificación, el script NO la evade: con el
navegador visible espera a que la persona la resuelva manualmente.
"""
import argparse
import json
import time
from datetime import datetime

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import config
from parsers import es_galaxy_a55, limpiar_precio, parsear_listado


def crear_driver(headless):
    opciones = Options()
    if headless:
        opciones.add_argument("--headless")
    opciones.set_preference("intl.accept_languages", "es-CO,es")
    driver = webdriver.Firefox(options=opciones)   # Selenium Manager descarga geckodriver
    driver.set_window_size(1366, 900)
    return driver


def esperar_verificacion(driver, headless):
    """Si aparece la verificación anti-bot, la resuelve la persona (no el script)."""
    if config.RUTA_VERIFICACION not in driver.current_url:
        return False
    if headless:
        raise RuntimeError("Mercado Libre pidió verificación. Ejecute sin --headless.")
    input(">> Mercado Libre pide verificación. Resuélvala en la ventana y pulse Enter...")
    return True


def cerrar_banner_cookies(driver):
    """Cierra el aviso de cookies eligiendo la opción menos invasiva disponible."""
    for texto in ("Rechazar", "Solo necesarias", "Entendido", "Aceptar cookies"):
        botones = driver.find_elements(By.XPATH, f"//button[contains(., '{texto}')]")
        if botones:
            try:
                botones[0].click()
                return
            except Exception:
                pass


def desplazar(driver, pasos=6):
    """Desplaza la página para forzar la carga diferida (lazy loading)."""
    for i in range(1, pasos + 1):
        driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight*{i}/{pasos});")
        time.sleep(0.8)


def texto_css(driver, selectores):
    for sel in selectores:
        try:
            return driver.find_element(By.CSS_SELECTOR, sel).text.strip()
        except NoSuchElementException:
            continue
    return None


def capturar_listado(driver, headless):
    """Recorre las páginas del listado y guarda el HTML renderizado."""
    productos, bloqueos = [], 0
    for n in range(1, config.MAX_PAGINAS + 1):
        driver.get(config.url_pagina(n))
        if esperar_verificacion(driver, headless):
            bloqueos += 1
            driver.get(config.url_pagina(n))
        if n == 1:
            cerrar_banner_cookies(driver)
        try:
            WebDriverWait(driver, config.TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, config.SEL_LISTADO["item"][0]))
            )
        except TimeoutException:
            print(f"Página {n}: no se encontraron resultados, se detiene la paginación.")
            break
        desplazar(driver)
        html = driver.page_source
        (config.RAW_DIR / f"listado_p{n}.html").write_text(html, encoding="utf-8")
        encontrados = parsear_listado(html)
        productos.extend(encontrados)
        print(f"Página {n}: {len(encontrados)} productos")
        time.sleep(config.RETARDO_SEGUNDOS)
    return productos, bloqueos


def elegir_producto(productos):
    """Ficha de catálogo (/p/MCO...) del Galaxy A55 nuevo mejor calificado."""
    candidatos = [p for p in productos if es_galaxy_a55(p["titulo"]) and p["url"]]
    catalogo = [p for p in candidatos if "/p/MCO" in p["url"]] or candidatos
    nuevos = [p for p in catalogo if not p["reacondicionado"]] or catalogo
    return max(nuevos, key=lambda p: (p["rating"] or 0, p["n_opiniones"] or 0)) if nuevos else None


def capturar_detalle(driver, url, headless):
    driver.get(url)
    esperar_verificacion(driver, headless)
    WebDriverWait(driver, config.TIMEOUT).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "h1.ui-pdp-title"))
    )
    desplazar(driver, pasos=8)
    (config.RAW_DIR / "detalle.html").write_text(driver.page_source, encoding="utf-8")

    sel = config.SEL_DETALLE
    subtitulo = texto_css(driver, sel["subtitulo"]) or ""
    specs = {}
    for fila in driver.find_elements(By.CSS_SELECTOR, sel["fila_spec"][0]):
        try:
            clave = fila.find_element(By.TAG_NAME, "th").text.strip()
            valor = fila.find_element(By.TAG_NAME, "td").text.strip()
            if clave:
                specs[clave] = valor
        except NoSuchElementException:
            continue
    opiniones = []
    for s in sel["opinion"]:
        opiniones = [e.text.strip() for e in driver.find_elements(By.CSS_SELECTOR, s) if e.text.strip()]
        if opiniones:
            break

    # Datos estructurados schema.org (JSON-LD), más estables que las clases CSS
    json_ld = {}
    for script in driver.find_elements(By.CSS_SELECTOR, 'script[type="application/ld+json"]'):
        try:
            dato = json.loads(script.get_attribute("innerHTML"))
        except json.JSONDecodeError:
            continue
        if isinstance(dato, dict) and dato.get("@type") == "Product":
            json_ld = dato
            break
    oferta = json_ld.get("offers") or {}
    if isinstance(oferta, list):
        oferta = oferta[0] if oferta else {}
    rating_ld = json_ld.get("aggregateRating") or {}

    rating_txt = texto_css(driver, sel["rating"])
    return {
        "url": driver.current_url,
        "titulo": texto_css(driver, sel["titulo"]),
        "condicion_y_ventas": subtitulo,
        "precio": limpiar_precio(texto_css(driver, sel["precio"])) or oferta.get("price"),
        "moneda": oferta.get("priceCurrency", "COP"),
        "rating": float(rating_txt.replace(",", ".")) if rating_txt else rating_ld.get("ratingValue"),
        "n_opiniones": limpiar_precio(texto_css(driver, sel["n_opiniones"])) or rating_ld.get("reviewCount"),
        "vendedor": (texto_css(driver, sel["vendedor"]) or "").replace("Vendido por", "").strip() or None,
        "reputacion_vendedor": texto_css(driver, sel["reputacion"]),
        "stock": texto_css(driver, sel["stock"]),
        "especificaciones": specs,
        "opiniones": opiniones[:15],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    inicio = time.time()
    driver = crear_driver(args.headless)
    try:
        productos, bloqueos = capturar_listado(driver, args.headless)
        elegido = elegir_producto(productos)
        detalle = capturar_detalle(driver, elegido["url"], args.headless) if elegido else {}
    finally:
        driver.quit()

    detalle["fecha_extraccion"] = datetime.now().isoformat(timespec="seconds")
    (config.DATA_DIR / "selenium_detalle.json").write_text(
        json.dumps(detalle, ensure_ascii=False, indent=2), encoding="utf-8")
    metricas = {
        "herramienta": "Selenium",
        "registros": len(productos),
        "paginas": len(list(config.RAW_DIR.glob("listado_p*.html"))),
        "verificaciones_manuales": bloqueos,
        "segundos": round(time.time() - inicio, 1),
        "fecha": detalle["fecha_extraccion"],
    }
    (config.DATA_DIR / "metricas_selenium.json").write_text(json.dumps(metricas, indent=2), encoding="utf-8")
    print(json.dumps(metricas, indent=2))
    print("Detalle guardado en data/selenium_detalle.json")


if __name__ == "__main__":
    main()
