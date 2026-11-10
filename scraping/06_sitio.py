"""Genera el tablero web estático que se publica en GitHub Pages.

Lee data/resumen.json, data/a55_limpio.csv y las figuras de 04_analisis.py y
escribe site/index.html (o la carpeta indicada en EA2_SITIO). En GitHub Actions
agrega el commit y el número de ejecución que produjeron el despliegue.
"""
import html
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import config

SITE_DIR = Path(os.environ.get("EA2_SITIO", config.BASE_DIR / "site"))
REPO = os.environ.get("GITHUB_REPOSITORY", "NeiderJPCuervo/EA2-DevOps-Scraping-GalaxyA55")
FIGURAS = [
    ("fig1_histograma_precios.png", "Distribución del precio actual"),
    ("fig2_precio_por_condicion.png", "Precio según la condición del equipo"),
    ("fig3_caracteristicas_oferta.png", "Características de la oferta"),
]

ESTILO = """
:root{--bg:#f7f6f3;--panel:#fff;--tinta:#1b1b1a;--tinta2:#5c5b57;--borde:#e4e3df;--acento:#2a78d6;--chip:#eef4fc}
@media (prefers-color-scheme:dark){:root{--bg:#141413;--panel:#1f1f1d;--tinta:#f1f0ec;--tinta2:#a9a8a2;
--borde:#34332f;--acento:#6aa6ef;--chip:#1d2a3a}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tinta);font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1040px;margin:0 auto;padding:32px 16px 48px}
header p{color:var(--tinta2);margin:.3rem 0 0}
h1{font-size:1.8rem;line-height:1.2;margin:0}
h2{font-size:1.15rem;margin:2.2rem 0 .8rem}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-top:24px}
.kpi{background:var(--panel);border:1px solid var(--borde);border-radius:10px;padding:14px 16px}
.kpi b{display:block;font-size:1.45rem;font-variant-numeric:tabular-nums}
.kpi span{color:var(--tinta2);font-size:.85rem}
.figs{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}
figure{margin:0;background:#fff;border:1px solid var(--borde);border-radius:10px;padding:8px}
figure img{width:100%;height:auto;display:block}
figcaption{color:#5c5b57;font-size:.82rem;padding:4px 4px 0}
.tabla{overflow-x:auto;background:var(--panel);border:1px solid var(--borde);border-radius:10px}
table{border-collapse:collapse;width:100%;font-size:.9rem}
th,td{padding:8px 12px;border-bottom:1px solid var(--borde);text-align:left;vertical-align:top}
th{color:var(--tinta2);font-weight:600;white-space:nowrap}
th.num{text-align:right}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
tr:last-child td{border-bottom:0}
a{color:var(--acento)}
.chip{display:inline-block;background:var(--chip);border-radius:99px;padding:1px 9px;font-size:.8rem;white-space:nowrap}
footer{margin-top:2.5rem;color:var(--tinta2);font-size:.85rem;border-top:1px solid var(--borde);padding-top:14px}
code{font-size:.85em}
"""


def cop(x):
    return f"${x:,.0f}".replace(",", ".")


def kpi(valor, etiqueta):
    return f'<div class="kpi"><b>{valor}</b><span>{etiqueta}</span></div>'


def fecha_captura(resumen):
    """Fecha en que Selenium capturó el HTML (no la fecha del build)."""
    selenium = resumen.get("metricas_herramientas", {}).get("selenium")
    if not selenium:
        # En CI el resumen se escribe en EA2_SALIDA, donde no está la métrica de
        # Selenium: se lee la versionada junto al HTML capturado.
        ruta = config.RAW_DIR.parent / "metricas_selenium.json"
        selenium = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
    return selenium.get("fecha", "")[:10]


def construir(resumen, tel):
    medianas = {c["condicion"]: c for c in resumen["por_condicion"]}
    tarjetas = [
        kpi(resumen["publicaciones_totales"], "publicaciones extraídas"),
        kpi(resumen["publicaciones_a55"], "son un Galaxy A55"),
        kpi(cop(resumen["precio"]["50%"]), "precio mediano"),
    ]
    for cond in ("Nuevo", "Usado"):
        if cond in medianas:
            tarjetas.append(kpi(cop(medianas[cond]["median"]), f"mediana {cond.lower()} (n={medianas[cond]['count']})"))
    tarjetas.append(kpi(f"{resumen['pct_envio_gratis']:.0f} %", "con envío gratis"))

    figuras = "".join(
        f'<figure><img src="figuras/{f}" alt="{t}" loading="lazy"><figcaption>{t}</figcaption></figure>'
        for f, t in FIGURAS if (config.FIG_DIR / f).exists())

    filas_cond = "".join(
        f"<tr><td>{html.escape(c['condicion'])}</td><td class='num'>{c['count']}</td>"
        f"<td class='num'>{cop(c['min'])}</td><td class='num'>{cop(c['median'])}</td>"
        f"<td class='num'>{cop(c['max'])}</td></tr>" for c in resumen["por_condicion"])

    filas_pub = []
    for _, p in tel.sort_values("precio_actual").iterrows():
        cap = f"{int(p['capacidad_gb'])} GB" if pd.notna(p["capacidad_gb"]) else "—"
        envio = "Gratis" if p["envio_gratis"] else "—"
        filas_pub.append(
            f"<tr><td><a href='{html.escape(str(p['url']).split('#')[0])}' rel='nofollow noopener'>"
            f"{html.escape(p['titulo'])}</a></td><td><span class='chip'>{html.escape(p['condicion'])}</span></td>"
            f"<td class='num'>{cap}</td><td class='num'>{cop(p['precio_actual'])}</td><td>{envio}</td></tr>")

    sha = os.environ.get("GITHUB_SHA", "")
    ejecucion = os.environ.get("GITHUB_RUN_ID")
    origen = (f'commit <a href="https://github.com/{REPO}/commit/{sha}"><code>{sha[:7]}</code></a>'
              if sha else "compilación local")
    if ejecucion:
        origen += (f' · <a href="https://github.com/{REPO}/actions/runs/{ejecucion}">'
                   f'ejecución n.º {os.environ.get("GITHUB_RUN_NUMBER", "")}</a>')
    construido = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    fecha_datos = fecha_captura(resumen)

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Precios Galaxy A55</title>
<meta name="description" content="Tablero de precios del Samsung Galaxy A55 en Mercado Libre Colombia, \
publicado automáticamente con GitHub Actions.">
<style>{ESTILO}</style>
</head>
<body>
<main>
<header>
<h1>Samsung Galaxy A55 en Mercado Libre Colombia</h1>
<p>Precios y condiciones de oferta extraídos con Selenium, BeautifulSoup y Scrapy{
    f" (captura del {fecha_datos})" if fecha_datos else ""}. Este tablero se reconstruye
y se publica automáticamente cada vez que un cambio pasa las pruebas y llega a <code>main</code>.</p>
</header>
<section class="kpis">{"".join(tarjetas)}</section>

<h2>Gráficas</h2>
<section class="figs">{figuras}</section>

<h2>Precio por condición</h2>
<div class="tabla"><table>
<thead><tr><th>Condición</th><th class="num">Publicaciones</th><th class="num">Mínimo</th><th class="num">Mediana</th>
<th class="num">Máximo</th></tr></thead>
<tbody>{filas_cond}</tbody></table></div>

<h2>Publicaciones del Galaxy A55 ({len(tel)})</h2>
<div class="tabla"><table>
<thead><tr><th>Publicación</th><th>Condición</th><th class="num">Capacidad</th><th class="num">Precio</th>
<th>Envío</th></tr></thead>
<tbody>{"".join(filas_pub)}</tbody></table></div>

<footer>
Generado el {construido} desde el {origen}.
Código fuente: <a href="https://github.com/{REPO}">github.com/{REPO}</a>.
Proyecto académico de la asignatura Programación para Análisis de Datos (IU Digital).
</footer>
</main>
</body>
</html>
"""


def main():
    resumen = json.loads((config.DATA_DIR / "resumen.json").read_text(encoding="utf-8"))
    tel = pd.read_csv(config.DATA_DIR / "a55_limpio.csv")
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "figuras").mkdir(exist_ok=True)
    for nombre, _ in FIGURAS:
        if (config.FIG_DIR / nombre).exists():
            shutil.copy2(config.FIG_DIR / nombre, SITE_DIR / "figuras" / nombre)
    (SITE_DIR / "index.html").write_text(construir(resumen, tel), encoding="utf-8")
    (SITE_DIR / ".nojekyll").touch()
    print(f"Sitio generado en {SITE_DIR / 'index.html'}")


if __name__ == "__main__":
    main()
