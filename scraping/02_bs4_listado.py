"""Scraper con requests + BeautifulSoup.

Descarga el listado de resultados (HTML estático) y extrae de cada tarjeta:
título, precio actual, precio anterior, % de descuento, envío gratis/Full,
vendedor, calificación, número de opiniones y URL.

Mercado Libre puede redirigir los clientes HTTP sin navegador a una página
de verificación. En ese caso el script no intenta evadirla: lo registra y
parsea con BeautifulSoup el HTML que Selenium guardó en data/raw/.
"""
import argparse
import json
import time
from datetime import datetime

import pandas as pd
import requests

import config
from parsers import parsear_listado


def descargar(session, url):
    """Devuelve el HTML o None si hubo bloqueo/verificación."""
    try:
        r = session.get(url, headers=config.HEADERS, timeout=config.TIMEOUT)
    except requests.RequestException as e:
        print(f"  error de red: {e}")
        return None
    if config.RUTA_VERIFICACION in r.url or r.status_code != 200:
        print(f"  bloqueado (HTTP {r.status_code}, {r.url[:70]}...)")
        return None
    return r.text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--local", action="store_true",
                        help="no descargar; parsear solo el HTML guardado por Selenium")
    args = parser.parse_args()

    inicio = time.time()
    session = requests.Session()
    filas, bloqueos = [], 0

    for n in range(1, config.MAX_PAGINAS + 1):
        url = config.url_pagina(n)
        print(f"Página {n}: {url}")
        html = None if args.local else descargar(session, url)
        fuente = "en_vivo"
        if html is None:
            bloqueos += not args.local
            respaldo = config.RAW_DIR / f"listado_p{n}.html"
            if not respaldo.exists():
                print("  sin HTML de respaldo; ejecute primero 01_selenium_navegador.py")
                continue
            html, fuente = respaldo.read_text(encoding="utf-8"), "html_selenium"
        productos = parsear_listado(html)
        for p in productos:
            p.update(pagina=n, fuente=fuente)
        filas.extend(productos)
        print(f"  {len(productos)} productos ({fuente})")
        if not args.local:
            time.sleep(config.RETARDO_SEGUNDOS)

    df = pd.DataFrame(filas)
    if not df.empty:
        df = df.drop_duplicates(subset=["id", "titulo", "precio_actual"])
    df.to_csv(config.DATA_DIR / "bs4_listado.csv", index=False, encoding="utf-8")

    metricas = {
        "herramienta": "BeautifulSoup",
        "registros": len(df),
        "paginas_bloqueadas_en_vivo": bloqueos,
        "fuente": sorted(df["fuente"].unique().tolist()) if not df.empty else [],
        "segundos": round(time.time() - inicio, 1),
        "fecha": datetime.now().isoformat(timespec="seconds"),
    }
    (config.DATA_DIR / "metricas_bs4.json").write_text(json.dumps(metricas, indent=2), encoding="utf-8")
    print(json.dumps(metricas, indent=2))


if __name__ == "__main__":
    main()
