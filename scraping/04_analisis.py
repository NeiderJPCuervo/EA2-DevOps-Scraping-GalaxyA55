"""Análisis de los datos extraídos (pandas + matplotlib).

Une los listados de BeautifulSoup y Scrapy, separa los teléfonos Galaxy A55
de los accesorios, calcula estadísticos de precio y oferta, genera las
figuras en figuras/ y escribe data/resumen.json para el informe.
"""
import json
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config
from parsers import es_galaxy_a55

AZUL, NARANJA = "#2a78d6", "#eb6834"
TINTA, TINTA_2, REJILLA = "#0b0b0b", "#52514e", "#e4e3df"
ACCESORIOS = r"funda|estuche|carcasa|vidrio|templado|protector|mica|cargador|cable|case|forro|lamina|hidrogel"
PRECIO_MINIMO_TELEFONO = 400_000      # COP: por debajo casi siempre es un accesorio

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": REJILLA,
    "axes.labelcolor": TINTA_2, "xtick.color": TINTA_2, "ytick.color": TINTA_2,
    "axes.titlecolor": TINTA, "axes.titleweight": "bold", "axes.titlesize": 11,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": REJILLA, "grid.linewidth": 0.6,
})


def cop(x):
    return f"${x:,.0f}".replace(",", ".")


def cargar():
    marcos = []
    for nombre in ("scrapy_listado.csv", "bs4_listado.csv"):
        ruta = config.DATA_DIR / nombre
        if ruta.exists() and ruta.stat().st_size > 1:
            df = pd.read_csv(ruta)
            df["herramienta"] = "Scrapy" if nombre.startswith("scrapy") else "BeautifulSoup"
            marcos.append(df)
    if not marcos:
        raise SystemExit("No hay datos. Ejecute primero los scrapers (ver README.md).")
    return pd.concat(marcos, ignore_index=True)


def clasificar(df):
    df = df.drop_duplicates(subset=["id", "titulo", "precio_actual"]).copy()
    if "condicion" not in df:          # CSV generado con una versión anterior de los scrapers
        df["condicion"] = np.where(df["reacondicionado"], "Usado", "Nuevo")
    df["condicion"] = df["condicion"].fillna("Nuevo")
    df["es_a55"] = df["titulo"].apply(es_galaxy_a55)
    df["es_accesorio"] = df["titulo"].str.contains(ACCESORIOS, flags=re.I, regex=True) | (
        df["precio_actual"] < PRECIO_MINIMO_TELEFONO)
    return df


def guardar(fig, nombre):
    fig.tight_layout()
    fig.savefig(config.FIG_DIR / nombre, dpi=200)
    plt.close(fig)


def figuras(tel):
    millones = tel["precio_actual"] / 1e6

    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.hist(millones, bins=15, color=AZUL, edgecolor="white", linewidth=2)
    ax.axvline(millones.median(), color=TINTA, linestyle="--", linewidth=1.2)
    ax.annotate(f"Mediana {cop(tel['precio_actual'].median())}", xy=(millones.median(), ax.get_ylim()[1] * 0.92),
                xytext=(6, 0), textcoords="offset points", color=TINTA, fontsize=9)
    ax.set(title="Distribución del precio actual del Galaxy A55",
           xlabel="Precio (millones de COP)", ylabel="Publicaciones")
    ax.grid(axis="x", visible=False)
    guardar(fig, "fig1_histograma_precios.png")

    # Un punto por publicación y una raya en la mediana: los grupos son pequeños para un boxplot
    orden = tel.groupby("condicion")["precio_actual"].median().sort_values(ascending=False).index
    fig, ax = plt.subplots(figsize=(7, 3.6))
    for i, cond in enumerate(orden, start=1):
        y = np.sort(tel.loc[tel["condicion"] == cond, "precio_actual"].to_numpy() / 1e6)
        x = i + (np.linspace(-0.18, 0.18, len(y)) if len(y) > 1 else np.zeros(1))
        ax.scatter(x, y, s=34, color=AZUL, edgecolor="white", linewidth=1, zorder=3)
        ax.hlines(np.median(y), i - 0.3, i + 0.3, color=TINTA, linewidth=1.6, zorder=4)
        ax.annotate(cop(np.median(y) * 1e6), xy=(i + 0.32, np.median(y)), va="center", fontsize=8.5, color=TINTA)
    ax.set_xticks(range(1, len(orden) + 1),
                  [f"{c}\n(n={(tel['condicion'] == c).sum()})" for c in orden])
    ax.set_xlim(0.4, len(orden) + 0.8)
    ax.set(title="Precio según la condición del equipo", ylabel="Precio (millones de COP)")
    ax.grid(axis="x", visible=False)
    guardar(fig, "fig2_precio_por_condicion.png")

    indicadores = {
        "Envío gratis": tel["envio_gratis"].mean() * 100,
        "Envío Full": tel["full"].mean() * 100,
        "Con descuento": tel["descuento_pct"].notna().mean() * 100,
        "Usado o reacondicionado": tel["reacondicionado"].mean() * 100,
    }
    if not indicadores["Envío Full"]:
        del indicadores["Envío Full"]      # el diseño actual de las tarjetas no muestra Full
    fig, ax = plt.subplots(figsize=(7, 3.2))
    barras = ax.barh(list(indicadores), list(indicadores.values()), color=AZUL, height=0.55)
    ax.bar_label(barras, fmt="%.0f%%", padding=4, color=TINTA, fontsize=9)
    ax.set(title="Características de la oferta (% de publicaciones)", xlim=(0, 110))
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    guardar(fig, "fig3_caracteristicas_oferta.png")

    top = tel["vendedor"].value_counts().head(8)
    if top.get("Sin identificar", 0) > len(tel) / 2:
        # Las tarjetas del listado casi nunca muestran el vendedor: el gráfico no aportaría nada
        (config.FIG_DIR / "fig4_top_vendedores.png").unlink(missing_ok=True)
        return
    fig, ax = plt.subplots(figsize=(7, 3.4))
    barras = ax.barh(top.index, top.values, color=AZUL, height=0.55)
    ax.bar_label(barras, padding=4, color=TINTA, fontsize=9)
    ax.set(title="Vendedores con más publicaciones", xlabel="Publicaciones")
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    guardar(fig, "fig4_top_vendedores.png")


def main():
    df = clasificar(cargar())
    tel = df[df["es_a55"] & ~df["es_accesorio"]].copy()
    tel["vendedor"] = tel["vendedor"].fillna("Sin identificar")
    tel.to_csv(config.DATA_DIR / "a55_limpio.csv", index=False, encoding="utf-8")
    if tel.empty:
        raise SystemExit("No se identificaron publicaciones del Galaxy A55.")
    figuras(tel)

    p = tel["precio_actual"]
    con_desc = tel.dropna(subset=["descuento_pct"])
    por_cond = (tel.groupby("condicion")["precio_actual"].agg(["count", "min", "median", "max"])
                .sort_values("median", ascending=False).reset_index())
    por_cond_cap = (tel.dropna(subset=["capacidad_gb"]).groupby(["condicion", "capacidad_gb"])["precio_actual"]
                    .agg(["count", "median"]).reset_index())
    metricas = {}
    for h in ("selenium", "bs4", "scrapy"):
        ruta = config.DATA_DIR / f"metricas_{h}.json"
        if ruta.exists():
            metricas[h] = json.loads(ruta.read_text(encoding="utf-8"))
    detalle_ruta = config.DATA_DIR / "selenium_detalle.json"

    resumen = {
        "publicaciones_totales": int(len(df)),
        "publicaciones_a55": int(len(tel)),
        "accesorios_u_otros": int(len(df) - len(tel)),
        "precio": {k: float(v) for k, v in p.describe().items()},
        "coef_variacion_pct": float(p.std() / p.mean() * 100),
        "pct_envio_gratis": float(tel["envio_gratis"].mean() * 100),
        "pct_full": float(tel["full"].mean() * 100),
        "pct_con_descuento": float(len(con_desc) / len(tel) * 100),
        "descuento_promedio_pct": float(con_desc["descuento_pct"].mean()) if len(con_desc) else None,
        "descuento_max_pct": float(con_desc["descuento_pct"].max()) if len(con_desc) else None,
        "pct_reacondicionado": float(tel["reacondicionado"].mean() * 100),
        "por_condicion": por_cond.to_dict(orient="records"),
        "por_condicion_capacidad": por_cond_cap.to_dict(orient="records"),
        "top_vendedores": tel["vendedor"].value_counts().head(8).to_dict(),
        "mas_barato": tel.nsmallest(3, "precio_actual")[["titulo", "precio_actual", "vendedor"]].to_dict("records"),
        "mas_caro": tel.nlargest(3, "precio_actual")[["titulo", "precio_actual", "vendedor"]].to_dict("records"),
        "metricas_herramientas": metricas,
        "detalle_selenium": json.loads(detalle_ruta.read_text(encoding="utf-8")) if detalle_ruta.exists() else {},
    }
    (config.DATA_DIR / "resumen.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Galaxy A55: {len(tel)} publicaciones | mediana {cop(p.median())} | "
          f"rango {cop(p.min())} – {cop(p.max())}")
    print("Figuras en figuras/ y resumen en data/resumen.json")


if __name__ == "__main__":
    main()
