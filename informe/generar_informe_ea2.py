"""Genera el informe Word de la Evidencia de aprendizaje 2.

Lee informe/datos.json (recolectar_datos.py), data/resumen.json, las figuras
del análisis y las capturas de informe/capturas/. Los ayudantes de formato
son los mismos del informe de la EA1 para mantener el estilo.

Uso (desde la raíz del repositorio):
    python informe/recolectar_datos.py
    python informe/generar_informe_ea2.py
"""
import json
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Patch
from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
INFORME = RAIZ / "informe"
CAPTURAS = INFORME / "capturas"
FIG_DIR = RAIZ / "figuras"
TMP = Path(tempfile.mkdtemp(prefix="ea2_informe_"))

# --- Datos de portada --------------------------------------------------------
AUTOR = "John Neider Cuervo Quintero"
INSTITUCION = "Institución Universitaria Digital de Antioquia (IU Digital)"
PROGRAMA = "Ingeniería de Software y Datos"
ASIGNATURA = "Programación para Análisis de Datos (PREICA2602B020048)"
ACTIVIDAD = "Evidencia de aprendizaje 2"
DOCENTE = "Andrés Felipe Palacio"
CIUDAD = "Medellín"

SALIDA = RAIZ / "entrega" / "Cuervo_Quintero_John_EA2.docx"

TINTA = RGBColor(0x1B, 0x26, 0x3B)
ACENTO = RGBColor(0x0E, 0x7C, 0x7B)
GRIS = RGBColor(0x5B, 0x63, 0x70)
BLANCO = RGBColor(0xFF, 0xFF, 0xFF)
HEX_TINTA, HEX_ACENTO, HEX_SUAVE, HEX_LINEA = "1B263B", "0E7C7B", "EAF4F3", "D5DBE3"

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


def cop(x):
    return f"${x:,.0f}".replace(",", ".") if x is not None else "—"


def pct(x, dec=1):
    return f"{x:.{dec}f} %".replace(".", ",") if x is not None else "—"


def fecha_larga(iso):
    d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def duracion(s):
    return f"{s // 60} min {s % 60:02d} s" if s >= 60 else f"{s} s"


# --- Utilidades de formato (las mismas del informe de la EA1) ----------------
def _xml(tag, **attrs):
    el = OxmlElement(tag)
    for k, v in attrs.items():
        el.set(qn(f"w:{k}"), str(v))
    return el


def estilos(doc):
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.font.color.rgb = RGBColor(0x26, 0x2B, 0x33)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.2
    for nivel, tam, color, antes in ((1, 17, TINTA, 20), (2, 12.5, ACENTO, 12), (3, 11, TINTA, 8)):
        h = doc.styles[f"Heading {nivel}"]
        h.font.name = "Calibri"
        h.font.size = Pt(tam)
        h.font.bold = True
        h.font.italic = False
        h.font.color.rgb = color
        h.paragraph_format.space_before = Pt(antes)
        h.paragraph_format.space_after = Pt(6)
        for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
            h.element.rPr.rFonts.attrib.pop(qn(attr), None)
    ppr = doc.styles["Heading 1"].element.get_or_add_pPr()
    borde = _xml("w:pBdr")
    borde.append(_xml("w:bottom", val="single", sz=6, space=4, color=HEX_ACENTO))
    ppr.append(borde)
    for s in doc.sections:
        s.top_margin = Cm(2.3)
        s.bottom_margin = Cm(2.2)
        s.left_margin = s.right_margin = Cm(2.4)


def campo_pagina(run):
    for tipo, texto in (("begin", None), (None, "PAGE"), ("end", None)):
        if tipo:
            run._r.append(_xml("w:fldChar", fldCharType=tipo))
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = texto
            run._r.append(el)


def encabezado_y_pie(seccion):
    seccion.different_first_page_header_footer = True
    p = seccion.header.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p.add_run("Flujo DevOps · Scraper del Galaxy A55 en Mercado Libre")
    r.font.size, r.font.color.rgb = Pt(8.5), GRIS
    p = seccion.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p.add_run(f"{ACTIVIDAD} · IU Digital   |   ")
    r.font.size, r.font.color.rgb = Pt(8.5), GRIS
    r = p.add_run()
    campo_pagina(r)
    r.font.size, r.font.color.rgb, r.bold = Pt(8.5), ACENTO, True


def parrafo(doc, texto, negrita_inicial=None, cursiva=False, alinear=WD_ALIGN_PARAGRAPH.JUSTIFY):
    p = doc.add_paragraph()
    p.alignment = alinear
    if negrita_inicial:
        p.add_run(negrita_inicial).bold = True
    r = p.add_run(texto)
    r.italic = cursiva
    return p


def vinetas(doc, items, estilo="List Bullet"):
    for it in items:
        p = doc.add_paragraph(style=estilo)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_after = Pt(3)
        if isinstance(it, tuple):
            p.add_run(it[0]).bold = True
            p.add_run(it[1])
        else:
            p.add_run(it)


def sombrear(celda, color):
    celda._tc.get_or_add_tcPr().append(_xml("w:shd", val="clear", color="auto", fill=color))


def bordes_celda(celda, **lados):
    tc_bordes = _xml("w:tcBorders")
    for lado in ("top", "left", "bottom", "right"):
        valor = lados.get(lado)
        if valor:
            tc_bordes.append(_xml(f"w:{lado}", val="single", sz=valor[0], space=0, color=valor[1]))
        else:
            tc_bordes.append(_xml(f"w:{lado}", val="nil"))
    celda._tc.get_or_add_tcPr().append(tc_bordes)


def bordes_tabla(t, visibles=True):
    borders = _xml("w:tblBorders")
    for borde in ("top", "left", "bottom", "right", "insideH", "insideV"):
        if visibles and borde in ("top", "bottom"):
            borders.append(_xml(f"w:{borde}", val="single", sz=8, space=0, color=HEX_TINTA))
        elif visibles and borde == "insideH":
            borders.append(_xml(f"w:{borde}", val="single", sz=4, space=0, color=HEX_LINEA))
        else:
            borders.append(_xml(f"w:{borde}", val="nil"))
    t._tbl.tblPr.append(borders)
    margenes = _xml("w:tblCellMar")
    for lado, valor in (("top", 45), ("bottom", 45), ("left", 100), ("right", 100)):
        margenes.append(_xml(f"w:{lado}", w=valor, type="dxa"))
    t._tbl.tblPr.append(margenes)


def anchos_tabla(t, anchos):
    t.autofit = False
    for col, w in zip(t._tbl.tblGrid.findall(qn("w:gridCol")), anchos, strict=False):
        col.set(qn("w:w"), str(int(Cm(w).twips)))
    for fila in t.rows:
        for i, w in enumerate(anchos):
            fila.cells[i].width = Cm(w)


def mantener_junta(t):
    t.rows[0]._tr.get_or_add_trPr().append(_xml("w:tblHeader"))
    for fila in t.rows:
        fila._tr.get_or_add_trPr().append(_xml("w:cantSplit"))
    if len(t.rows) <= 14:
        for fila in t.rows[:-1]:
            for celda in fila.cells:
                for par in celda.paragraphs:
                    par.paragraph_format.keep_with_next = True


def titulo_apa(doc, etiqueta, titulo):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.keep_with_next = True
    p.add_run(etiqueta).bold = True
    p2 = doc.add_paragraph()
    p2.paragraph_format.keep_with_next = True
    p2.paragraph_format.space_after = Pt(4)
    p2.add_run(titulo).italic = True


def nota(doc, texto):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(3)
    r = p.add_run("Nota. ")
    r.italic, r.font.size, r.font.color.rgb = True, Pt(9), GRIS
    r = p.add_run(texto)
    r.font.size, r.font.color.rgb = Pt(9), GRIS


class Numerador:
    """Lleva la cuenta de tablas y figuras para los rótulos APA."""

    def __init__(self):
        self.tablas = 0
        self.figuras = 0

    def tabla(self):
        self.tablas += 1
        return f"Tabla {self.tablas}"

    def figura(self):
        self.figuras += 1
        return f"Figura {self.figuras}"


N = Numerador()


def tabla(doc, titulo, encabezado, filas, anchos=None, nota_txt=None, tam=9.5):
    titulo_apa(doc, N.tabla(), titulo)
    t = doc.add_table(rows=1, cols=len(encabezado))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    bordes_tabla(t)
    for i, h in enumerate(encabezado):
        c = t.rows[0].cells[i]
        c.text = ""
        r = c.paragraphs[0].add_run(h)
        r.bold, r.font.size, r.font.color.rgb = True, Pt(tam), BLANCO
        sombrear(c, HEX_TINTA)
    for k, fila in enumerate(filas):
        celdas = t.add_row().cells
        for i, v in enumerate(fila):
            celdas[i].text = ""
            p = celdas[i].paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.05
            r = p.add_run(str(v))
            r.font.size = Pt(tam)
            if k % 2:
                sombrear(celdas[i], "F4F6F9")
    mantener_junta(t)
    if anchos:
        anchos_tabla(t, anchos)
    if nota_txt:
        nota(doc, nota_txt)
    else:
        doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def destacado(doc, titulo, texto):
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    bordes_tabla(t, visibles=False)
    c = t.cell(0, 0)
    sombrear(c, HEX_SUAVE)
    bordes_celda(c, left=(36, HEX_ACENTO))
    p = c.paragraphs[0]
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(titulo.upper())
    r.bold, r.font.size, r.font.color.rgb = True, Pt(8.5), ACENTO
    p = c.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    p.add_run(texto).font.size = Pt(10.5)
    anchos_tabla(t, [16.2])
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def indicadores(doc, datos):
    t = doc.add_table(rows=2, cols=len(datos))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    bordes_tabla(t, visibles=False)
    for i, (valor, etiqueta) in enumerate(datos):
        for fila in (0, 1):
            sombrear(t.cell(fila, i), "F4F6F9")
        bordes_celda(t.cell(0, i), top=(18, HEX_ACENTO))
        p = t.cell(0, i).paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(str(valor))
        r.bold, r.font.size, r.font.color.rgb = True, Pt(13), TINTA
        p = t.cell(1, i).paragraphs[0]
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(etiqueta)
        r.font.size, r.font.color.rgb = Pt(8.5), GRIS
    anchos_tabla(t, [16.2 / len(datos)] * len(datos))
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def figura(doc, titulo, ruta, texto_nota, ancho=15.5):
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError(ruta)
    titulo_apa(doc, N.figura(), titulo)
    doc.add_picture(str(ruta), width=Cm(ancho))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.paragraphs[-1].paragraph_format.keep_with_next = True
    nota(doc, texto_nota)


def recorte(nombre, alto=None, borde=True):
    """Recorta una captura (alto en píxeles desde arriba) y le agrega un borde fino."""
    img = Image.open(CAPTURAS / nombre).convert("RGB")
    if alto and img.height > alto:
        img = img.crop((0, 0, img.width, alto))
    if borde:
        marco = Image.new("RGB", (img.width + 4, img.height + 4), (0xD5, 0xDB, 0xE3))
        marco.paste(img, (2, 2))
        img = marco
    destino = TMP / nombre
    img.save(destino)
    return destino


def codigo(doc, lineas, tam=7.5):
    for linea in lineas:
        cp = doc.add_paragraph()
        cp.paragraph_format.space_after = Pt(0)
        cp.paragraph_format.line_spacing = 1.0
        r = cp.add_run(linea if linea else " ")
        r.font.name = "Consolas"
        r._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
        r.font.size = Pt(tam)


def bloque_codigo(doc, rel):
    ruta = RAIZ / rel
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(rel)
    r.bold, r.font.color.rgb = True, ACENTO
    codigo(doc, ruta.read_text(encoding="utf-8").splitlines())


# --- Figuras propias del informe ---------------------------------------------
def figura_flujo():
    """Diagrama del flujo GitHub Flow + CI/CD implementado."""
    fig, ax = plt.subplots(figsize=(8.6, 4.3))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 46)
    ax.axis("off")
    azul, verde, rojo, gris, tinta = "#2a78d6", "#0e7c7b", "#c0392b", "#8a919c", "#1b263b"

    def caja(x, y, w, h, titulo, sub, color):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2",
                                    fc="white", ec=color, lw=1.6))
        ax.text(x + w / 2, y + h - 2.6, titulo, ha="center", va="center", fontsize=9.5, weight="bold",
                color=tinta)
        ax.text(x + w / 2, y + h / 2 - 1.6, sub, ha="center", va="center", fontsize=7.4, color="#52514e",
                linespacing=1.25)

    def flecha(a, b, color=gris, texto=None, rad=0.0, dy=1.6):
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=12, lw=1.3, color=color,
                                     connectionstyle=f"arc3,rad={rad}"))
        if texto:
            ax.text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + dy, texto, ha="center", fontsize=7.5, color=color,
                    weight="bold")

    # Fila superior: trabajo del desarrollador
    ax.text(1, 44, "DESARROLLO (GitHub Flow)", fontsize=8, color=azul, weight="bold")
    caja(1, 28, 15, 13, "Issue", "objetivo y\ncriterios", azul)
    caja(21, 28, 15, 13, "Rama", "feature/, fix/,\nci/, docs/", azul)
    caja(41, 28, 15, 13, "Commits", "Conventional\nCommits", azul)
    caja(61, 28, 16, 13, "Pull request", "plantilla +\nCloses #n", azul)
    caja(82, 28, 17, 13, "CI en el PR", "ruff · pytest ·\npipeline de datos\nPy 3.12 y 3.13", verde)
    flecha((16.8, 34.5), (20.2, 34.5))
    flecha((36.8, 34.5), (40.2, 34.5))
    flecha((56.8, 34.5), (60.2, 34.5))
    flecha((77.8, 34.5), (81.2, 34.5))
    flecha((88, 27.4), (49, 27.4), color=rojo, texto="falla: se corrige en la rama", rad=-0.12, dy=-4.2)

    # Fila inferior: integración y entrega
    ax.text(1, 19, "INTEGRACIÓN Y ENTREGA (GitHub Actions)", fontsize=8, color=verde, weight="bold")
    caja(82, 3, 17, 13, "Merge a main", "rama protegida:\ncheck «ci» + PR", verde)
    caja(61, 3, 16, 13, "CI en main", "mismas pruebas\nsobre el merge", verde)
    caja(40, 3, 16, 13, "Deploy", "workflow_run:\ndatos, figuras\ny sitio", verde)
    caja(19, 3, 16, 13, "GitHub Pages", "tablero público\nactualizado", verde)
    flecha((92, 27.4), (92, 16.8), color=verde)
    ax.text(93.2, 21.5, "pasa", fontsize=7.5, color=verde, weight="bold")
    flecha((81.2, 9.5), (77.8, 9.5))
    flecha((60.2, 9.5), (56.8, 9.5))
    flecha((39.2, 9.5), (35.8, 9.5))
    ax.text(1, 9.5, "usuario /\ndocente", fontsize=8, color=tinta, va="center")
    flecha((18.2, 9.5), (9.5, 9.5))
    destino = TMP / "fig_flujo_devops.png"
    fig.savefig(destino, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return destino


def figura_ejecuciones(ejec):
    """Duración de cada ejecución de GitHub Actions, en orden."""
    ejec = [e for e in ejec if e["conclusion"] in ("success", "failure")]
    fig, ax = plt.subplots(figsize=(8, 3.4))
    colores = {("CI", "success"): "#2a78d6", ("Deploy", "success"): "#0e7c7b", ("CI", "failure"): "#c0392b"}
    x = range(1, len(ejec) + 1)
    ax.bar(x, [e["duracion_s"] for e in ejec], color=[colores.get((e["workflow"], e["conclusion"]), "#8a919c")
                                                        for e in ejec], width=0.7)
    ax.set_xticks(list(x), [str(i) for i in x], fontsize=8)
    ax.set_ylabel("Segundos", color="#52514e")
    ax.set_xlabel("Ejecución (en orden cronológico)", color="#52514e")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color="#e4e3df", linewidth=0.6)
    ax.set_axisbelow(True)
    ax.legend(handles=[Patch(color="#2a78d6", label="CI (éxito)"), Patch(color="#c0392b", label="CI (falla)"),
                       Patch(color="#0e7c7b", label="Deploy (éxito)")], frameon=False, fontsize=8,
              loc="upper center", bbox_to_anchor=(0.5, 1.16), ncol=3)
    destino = TMP / "fig_ejecuciones.png"
    fig.tight_layout()
    fig.savefig(destino, dpi=220)
    plt.close(fig)
    return destino


# --- Secciones -----------------------------------------------------------------
def portada(doc, fecha, D):
    banda = doc.add_table(rows=1, cols=1)
    bordes_tabla(banda, visibles=False)
    c = banda.cell(0, 0)
    sombrear(c, HEX_TINTA)
    banda.rows[0]._tr.get_or_add_trPr().append(_xml("w:trHeight", val=int(Cm(9.5).twips), hRule="atLeast"))
    lineas = [
        ("INFORME TÉCNICO · " + ACTIVIDAD.upper(), 9, True, RGBColor(0x7F, 0xD1, 0xC9), 30),
        ("Flujo de trabajo DevOps para un proyecto de web scraping", 24, True, BLANCO, 10),
        ("Git, GitHub y CI/CD con GitHub Actions sobre el scraper del Samsung Galaxy A55 en Mercado Libre",
         13, False, BLANCO, 6),
        ("Git  ·  GitHub  ·  GitHub Actions  ·  GitHub Pages  ·  pytest", 10.5, False,
         RGBColor(0xB8, 0xC4, 0xD6), 16),
    ]
    p = c.paragraphs[0]
    for i, (texto, tam, neg, color, antes) in enumerate(lineas):
        if i:
            p = c.add_paragraph()
        p.paragraph_format.space_before = Pt(antes)
        p.paragraph_format.left_indent = Cm(0.8)
        p.paragraph_format.right_indent = Cm(0.8)
        r = p.add_run(texto)
        r.font.size, r.bold, r.font.color.rgb = Pt(tam), neg, color
    anchos_tabla(banda, [16.2])

    for _ in range(3):
        doc.add_paragraph()
    datos = [("Autor", AUTOR), ("Docente", DOCENTE), ("Asignatura", ASIGNATURA), ("Programa", PROGRAMA),
             ("Institución", INSTITUCION), ("Repositorio", D["url_repo"]), ("Tablero publicado", D["url_pages"]),
             ("Lugar y fecha", f"{CIUDAD}, {fecha}")]
    t = doc.add_table(rows=len(datos), cols=2)
    bordes_tabla(t, visibles=False)
    for i, (etiqueta, valor) in enumerate(datos):
        izq, der = t.cell(i, 0), t.cell(i, 1)
        bordes_celda(izq, top=(4, HEX_LINEA))
        bordes_celda(der, top=(4, HEX_LINEA))
        r = izq.paragraphs[0].add_run(etiqueta.upper())
        r.bold, r.font.size, r.font.color.rgb = True, Pt(8.5), ACENTO
        der.paragraphs[0].paragraph_format.space_after = Pt(1)
        der.paragraphs[0].add_run(valor).font.size = Pt(10.5 if valor.startswith("http") else 11)
    anchos_tabla(t, [4.2, 12])
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def resumen(doc, D, R, M):
    doc.add_heading("Resumen", 1)
    parrafo(doc, f"Este informe documenta cómo llevé a un flujo de trabajo DevOps el scraper que construí en la "
            f"Evidencia de aprendizaje 1, que extrae de Mercado Libre Colombia los precios del Samsung Galaxy A55 "
            f"con Selenium, BeautifulSoup y Scrapy. Puse el proyecto bajo control de versiones con Git en un "
            f"repositorio público de GitHub y organicé el trabajo con issues, ramas cortas y pull requests sobre una "
            f"rama main protegida: en total, {M['commits']} commits, {M['issues']} issues y {M['prs']} pull "
            f"requests, de los cuales {M['prs_fusionados']} se fusionaron. Después monté en GitHub Actions un "
            f"pipeline de integración continua que, en cada cambio, revisa el estilo, ejecuta {M['pruebas']} "
            f"pruebas automatizadas en Python 3.12 y 3.13 (cobertura de {pct(M['cobertura'], 0)}) y corre el "
            f"pipeline de datos completo. Otro workflow despliega automáticamente en GitHub Pages un tablero con "
            f"los resultados cada vez que un cambio validado llega a main.")
    parrafo(doc, f"En {M['ejecuciones']} ejecuciones, con una duración típica de alrededor de un minuto, el "
            f"pipeline reprodujo exactamente las cifras de la EA1 (mediana de {cop(R['precio']['50%'])} para "
            f"{R['publicaciones_a55']} publicaciones del A55) y demostró su utilidad en casos reales: detectó una "
            f"condición de producto que no había previsto («Caja abierta»), bloqueó un pull request de demostración "
            f"que reintroducía el error de selector de la EA1, me llevó a corregir un dato faltante en el tablero "
            f"publicado y señaló acciones obsoletas que actualicé.")
    p = doc.add_paragraph()
    p.add_run("Palabras clave: ").bold = True
    p.add_run("DevOps, Git, GitHub, integración continua, despliegue continuo, GitHub Actions, pruebas "
              "automatizadas, web scraping.").italic = True


def introduccion(doc):
    doc.add_heading("1. Introducción", 1)
    parrafo(doc, "En la Evidencia de aprendizaje 1 construí un scraper que funcionaba, pero solo en mi computador. "
            "Para obtener los resultados había que ejecutar cinco scripts en orden, no quedaba registro de qué "
            "había cambiado entre una versión y otra, y no había forma de saber si un ajuste rompía algo hasta "
            "revisar los datos a mano. De hecho, eso pasó: un selector CSS desactualizado hizo que durante un "
            "tiempo el envío gratis apareciera en 0 % sin que ningún script fallara.")
    parrafo(doc, "La Unidad 2 del curso propone resolver ese tipo de problemas con herramientas y flujos de trabajo "
            "de desarrollo. Git y GitHub permiten registrar cada cambio, trabajarlo en ramas aisladas y revisarlo "
            "antes de integrarlo (Chacon y Straub, 2014). DevOps reúne prácticas culturales y técnicas para que los "
            "cambios lleguen a producción de forma frecuente, pequeña y confiable (Kim et al., 2021). Dos de esas "
            "prácticas son centrales aquí. La integración continua (CI) consiste en integrar el trabajo a menudo "
            "y verificar cada integración con una compilación y pruebas automáticas (Fowler, 2024). El despliegue "
            "continuo (CD) entrega cada cambio que pasa esas verificaciones sin pasos manuales (Humble y Farley, "
            "2010).")
    parrafo(doc, "Este trabajo responde de manera práctica a la pregunta orientadora del curso: ¿qué tan seguro "
            "puedo estar de que mi proyecto de análisis de datos es escalable, integral y susceptible de ser "
            "automatizado? Para eso apliqué Git, GitHub y GitHub Actions al proyecto de la EA1 como si fuera parte "
            "de un equipo de desarrollo, y medí el resultado con los datos que el propio repositorio registra.")
    parrafo(doc, "El documento retoma primero la página y el producto analizados en la EA1. Luego presenta el tema, "
            "los objetivos y la metodología, tanto la del scraping como la del flujo DevOps, y termina con los "
            "resultados, las conclusiones y la relación con la Unidad 3 y el proyecto de cierre. El código fuente "
            "está en el repositorio, en el Anexo A y en el archivo ZIP que acompaña este informe.")


def descripcion(doc, R):
    doc.add_heading("2. La página y el artículo analizados (retomados de la EA1)", 1)
    doc.add_heading("2.1 Mercado Libre Colombia", 2)
    parrafo(doc, "Mercado Libre (MercadoLibre, Inc., NASDAQ: MELI) nació en 1999 en Buenos Aires y hoy opera el "
            "ecosistema de comercio electrónico y pagos digitales más grande de América Latina, con presencia en 18 "
            "países (MercadoLibre, Inc., 2025). En Colombia funciona bajo el dominio mercadolibre.com.co.")
    parrafo(doc, "La plataforma es un marketplace: reúne a miles de vendedores, desde personas que venden su celular "
            "usado hasta tiendas oficiales de las marcas, que compiten en la misma búsqueda. Cada publicación "
            "muestra elementos que influyen en la compra: el medio de pago y la financiación (Mercado Pago), la "
            "logística y el envío gratis (Mercado Envíos), la reputación del vendedor y la condición del producto "
            "(nuevo, usado, reacondicionado o caja abierta).")
    parrafo(doc, "Para el scraping usé dos tipos de página. La primera es el listado de búsqueda "
            "(listado.mercadolibre.com.co/samsung-galaxy-a55), que muestra hasta 48 publicaciones por página en "
            "tarjetas con título, precio, descuento, envío y condición. La segunda es la ficha de producto (rutas "
            "/p/MCO…), con el vendedor, el stock y las especificaciones. El sitio combina HTML estático, contenido "
            "cargado con JavaScript y una verificación anti-bot que redirige a /gz/account-verification las "
            "peticiones que no vienen de un navegador real.")
    doc.add_heading("2.2 Samsung Galaxy A55 5G", 2)
    parrafo(doc, "El Galaxy A55 5G es un teléfono de gama media-alta que Samsung lanzó en marzo de 2024. Lo elegí "
            "porque es un modelo muy buscado en Colombia, sus unidades son comparables entre sí y lo venden tanto "
            "la tienda oficial como revendedores y personas naturales, lo que produce una oferta variada "
            "(Samsung Electronics, 2024).")
    tabla(doc, "Especificaciones principales del Samsung Galaxy A55 5G", ["Característica", "Especificación"], [
        ("Pantalla", "6,6\" Super AMOLED FHD+, 120 Hz"),
        ("Procesador", "Samsung Exynos 1480 (4 nm)"),
        ("Memoria RAM / almacenamiento", "8 GB / 128 GB o 256 GB, ampliable con microSD"),
        ("Cámaras", "Trasera de 50 MP con OIS, 12 MP ultra gran angular y 5 MP macro; frontal de 32 MP"),
        ("Batería", "5.000 mAh con carga rápida de 25 W"),
        ("Construcción", "Marco de aluminio, Gorilla Glass Victus+, resistencia IP67"),
    ], anchos=[5.2, 11], nota_txt="Tomado de Samsung Electronics (2024).")
    doc.add_heading("2.3 Lo que dejó la Evidencia de aprendizaje 1", 2)
    cond = {c["condicion"]: c for c in R["por_condicion"]}
    parrafo(doc, "La EA1 extrajo las tres primeras páginas de resultados de la búsqueda «samsung galaxy a55» el 25 "
            "de octubre de 2026. Estas son las cifras principales, que en esta evidencia se convierten en la línea "
            "base que el pipeline automatizado debe reproducir:")
    indicadores(doc, [(R["publicaciones_totales"], "publicaciones extraídas"),
                      (R["publicaciones_a55"], "son un Galaxy A55"),
                      (cop(cond["Nuevo"]["median"]), f"mediana nuevo (n={cond['Nuevo']['count']})"),
                      (cop(cond["Usado"]["median"]), f"mediana usado (n={cond['Usado']['count']})"),
                      (pct(R["pct_envio_gratis"], 0), "con envío gratis")])
    parrafo(doc, "Además de los datos, la EA1 dejó dos lecciones técnicas que orientan esta evidencia. La primera es "
            "que solo Selenium, con un navegador real, logró obtener las páginas; BeautifulSoup y Scrapy trabajaron "
            "sobre el HTML que Selenium guardó. La segunda es que un scraper puede ejecutarse sin errores y aun así "
            "entregar datos equivocados cuando el sitio cambia sus clases CSS.")


def tema(doc):
    doc.add_heading("3. Tema de interés para la Unidad 2", 1)
    destacado(doc, "Pregunta de esta evidencia",
              "¿Cómo garantizar que el scraper del Galaxy A55 y su análisis sigan entregando resultados correctos "
              "cada vez que cambia el código, y que esos resultados se publiquen sin pasos manuales?")
    parrafo(doc, "El tema que desarrollo es la automatización y el aseguramiento de la calidad de un pipeline de "
            "datos de precios. Los proyectos de scraping son especialmente frágiles: dependen de un HTML que "
            "controla un tercero, combinan varias herramientas y producen cifras que nadie verifica si el script "
            "no falla. Un flujo DevOps ataca esos puntos con historial de cambios, revisión antes de integrar, "
            "pruebas que se ejecutan solas y una entrega reproducible. Las preguntas que guiaron el trabajo fueron:")
    vinetas(doc, [
        "¿Cómo organizar el proyecto en Git y GitHub para que cada cambio sea trazable desde la tarea que lo "
        "motivó hasta su despliegue?",
        "¿Qué pruebas automatizadas tienen sentido para un scraper y cómo ejecutarlas sin depender del sitio en "
        "vivo ni de su protección anti-bot?",
        "¿Cómo encadenar en GitHub Actions las pruebas y el despliegue para que nada llegue a producción sin pasar "
        "las verificaciones?",
        "¿El flujo detecta de verdad los errores? ¿Cuánto tarda y cuánto cuesta mantenerlo?",
    ])


def objetivos(doc):
    doc.add_heading("4. Objetivos", 1)
    doc.add_heading("Escenario", 2)
    parrafo(doc, "Para plantear los objetivos imaginé que formo parte del equipo de datos de una empresa que vende "
            "celulares en línea y necesita seguir los precios de la competencia en Mercado Libre. El scraper de la "
            "EA1 es el proyecto de software del equipo. Varias personas lo modifican, el sitio cambia su HTML sin "
            "aviso y el área comercial consulta los resultados. Mi papel es establecer el flujo de trabajo que "
            "permita cambiar el proyecto con confianza y entregar resultados actualizados de forma automática.")
    doc.add_heading("4.1 Objetivo general", 2)
    parrafo(doc, "Implementar un flujo de trabajo DevOps para el proyecto de scraping del Samsung Galaxy A55, con "
            "control de versiones en Git y GitHub y un pipeline de CI/CD en GitHub Actions que ejecute pruebas "
            "automatizadas y despliegue de forma continua un tablero de resultados, documentado en un repositorio "
            "público de GitHub.")
    doc.add_heading("4.2 Objetivos específicos", 2)
    vinetas(doc, [
        "Versionar el proyecto con Git a partir de una línea base etiquetada de la EA1, con un .gitignore adecuado "
        "y una convención de mensajes de commit.",
        "Organizar el trabajo en GitHub con issues, ramas por tarea, pull requests y una rama main protegida, "
        "siguiendo GitHub Flow.",
        "Diseñar una suite de pruebas automatizadas (unitarias, de integración y de regresión) que se ejecute sin "
        "conexión sobre el HTML capturado por Selenium.",
        "Configurar un pipeline de integración continua que revise el estilo, ejecute las pruebas en varias "
        "versiones de Python y corra el pipeline de datos completo en cada cambio.",
        "Configurar el despliegue continuo de un tablero web en GitHub Pages, condicionado al éxito de la "
        "integración continua.",
        "Documentar el flujo en el repositorio y evaluarlo con métricas reales (ejecuciones, duración, cobertura) "
        "y con una prueba de fallo controlada.",
    ], estilo="List Number")


def metodologia(doc, D, R, M, pruebas_por_archivo, fig_flujo):
    doc.add_heading("5. Metodología", 1)
    parrafo(doc, "El trabajo tuvo dos capas. La primera es la metodología de datos, heredada de la EA1: el proceso "
            "CRISP-DM y el scraping con tres herramientas. La segunda es la metodología de desarrollo: GitHub Flow "
            "para el control de versiones y un pipeline de CI/CD para automatizar la verificación y la entrega. La "
            "Tabla 2 muestra cómo se conectan.")
    tabla(doc, "Fases de CRISP-DM en el proyecto y su automatización en la EA2",
          ["Fase CRISP-DM", "En el proyecto", "Automatización en la EA2"], [
              ("Comprensión del negocio", "Pregunta sobre el precio del A55 y su variación",
               "Issues con objetivo y criterios de aceptación"),
              ("Comprensión de los datos", "robots.txt, estructura HTML y selectores CSS",
               "Prueba que valida que los selectores siguen vigentes"),
              ("Preparación de los datos", "Parsing, limpieza, deduplicación y filtrado del A55",
               "Pruebas unitarias y del pipeline de Scrapy"),
              ("Modelado", "Estadística descriptiva por condición y capacidad",
               "Ejecución del análisis en cada cambio"),
              ("Evaluación", "Revisión de las cifras contra la página",
               "Prueba de regresión con las cifras de la EA1"),
              ("Despliegue", "Informe Word generado a mano", "Tablero web publicado por GitHub Actions"),
          ], anchos=[3.8, 6.0, 6.4],
          nota_txt="CRISP-DM según Chapman et al. (2000). En este proyecto el «modelado» es descriptivo; no hay un "
                   "modelo predictivo.")

    doc.add_heading("5.1 Metodología de scraping", 2)
    parrafo(doc, "El proceso de extracción es el de la EA1 y se organiza en fases encadenadas. Toda la configuración "
            "común (URL, selectores CSS, pausas y rutas) está en un solo archivo, scraping/config.py, para que un "
            "cambio en el HTML del sitio se corrija en un único lugar.")
    tabla(doc, "Fases del scraping y dónde se ejecutan", ["Fase", "Qué se hace", "Herramienta", "Dónde se ejecuta"], [
        ("1. Reconocimiento", "Lectura de robots.txt e inspección del HTML para ubicar los selectores",
         "Navegador, config.py", "Manual"),
        ("2. Captura", "Carga del listado y la ficha en Firefox, espera del JavaScript y desplazamiento; guarda el "
         "HTML en data/raw/", "Selenium", "Equipo local (navegador real)"),
        ("3. Parsing", "Extracción de título, precio, descuento, envío y condición de cada tarjeta",
         "BeautifulSoup", "Local y CI"),
        ("4. Rastreo", "Spider con paginación, pipeline de limpieza y deduplicación, exportación a CSV",
         "Scrapy", "Local y CI"),
        ("5. Análisis", "Unión, filtrado del A55, estadísticos y figuras", "pandas, matplotlib", "Local y CI"),
        ("6. Publicación", "Tablero HTML con indicadores, figuras y publicaciones", "06_sitio.py",
         "CD (GitHub Pages)"),
    ], anchos=[3.3, 6.3, 3.0, 3.6])
    parrafo(doc, "La decisión de diseño más importante fue que el pipeline automatizado no hace scraping en vivo. "
            "Hay tres razones. Mercado Libre redirige a una verificación anti-bot las peticiones de requests y "
            "Scrapy; los servidores de GitHub no tienen una sesión gráfica para Selenium; y hacer peticiones al "
            "sitio en cada push sería poco respetuoso con su infraestructura (Krotov et al., 2020). Por eso, las "
            "páginas capturadas por Selenium en data/raw/ se versionan y funcionan como datos de prueba: "
            "BeautifulSoup (02_bs4_listado.py --local) y Scrapy (scrapy crawl galaxy_a55 -a origen=local) las "
            "procesan igual que si vinieran del sitio. La captura en vivo sigue siendo un paso manual con "
            "01_selenium_navegador.py, con robots.txt respetado, 3 segundos entre peticiones y una sola conexión.")
    parrafo(doc, "Para que las pruebas y el pipeline no sobrescriban los datos versionados agregué la variable de "
            "entorno EA2_SALIDA (issue #1): si existe, los CSV, el resumen y las figuras se escriben en esa "
            "carpeta y data/raw/ queda como entrada de solo lectura.")

    doc.add_heading("5.2 Control de versiones con Git", 2)
    parrafo(doc, "Creé el repositorio a partir de una copia limpia del proyecto de la EA1, sin el entorno virtual, "
            "sin los documentos de entrega y sin archivos temporales, que quedaron excluidos en el .gitignore. El "
            "primer commit es la línea base de la EA1 y lleva la etiqueta v0.1.0-ea1, de modo que siempre se "
            "puede comparar el estado actual con el punto de partida. Los mensajes siguen la convención "
            "Conventional Commits (feat, fix, test, ci, refactor, docs, chore), que hace legible el historial y "
            "facilita generar notas de versión (Conventional Commits, 2019).")
    tabla(doc, "Comandos de Git y GitHub CLI usados en el flujo", ["Comando", "Propósito"], [
        ("git init -b main", "Crear el repositorio con main como rama principal"),
        ("git tag -a v0.1.0-ea1", "Marcar la línea base heredada de la EA1"),
        ("gh repo create … --public --push", "Crear el repositorio en GitHub y subir main"),
        ("gh issue create -l <etiqueta>", "Registrar cada tarea con su objetivo y criterios"),
        ("git switch -c feature/<tema>", "Abrir una rama corta por tarea"),
        ("git commit -m \"test: …\"", "Registrar cambios pequeños con Conventional Commits"),
        ("git push -u origin <rama>", "Publicar la rama"),
        ("gh pr create / gh pr checks --watch", "Abrir el pull request y seguir el CI"),
        ("gh pr merge --merge --delete-branch", "Fusionar con un commit de merge y borrar la rama"),
    ], anchos=[6.6, 9.6])

    doc.add_heading("5.3 Colaboración en GitHub: issues, ramas y pull requests", 2)
    parrafo(doc, "Adopté GitHub Flow: main siempre debe estar lista para desplegarse, y todo cambio nace en una rama "
            "corta, se propone en un pull request, pasa la integración continua y se fusiona (GitHub, 2026c). "
            "Antes de escribir código registré cinco issues con etiquetas (refactor, pruebas, ci-cd, "
            "documentación) y luego trabajé una rama por issue. Cada pull request usa una plantilla con el resumen "
            "del cambio y cómo se probó, e incluye «Closes #n» para que GitHub cierre el issue al fusionar. La "
            "Tabla 5 muestra la trazabilidad completa.")
    issues = {i["numero"]: i["titulo"] for i in D["issues"]}
    filas = []
    for p in D["pull_requests"]:
        estado = "Fusionado" if p["fusionado"] else "Cerrado sin fusionar"
        checks = f"{p['checks_ok']}/{p['checks_total']}" if p["checks_total"] else "sin CI aún"
        origen = ", ".join(f"#{n}" for n in p["cierra"]) or "—"
        filas.append((f"#{p['numero']}", p["rama"], p["titulo"].split(": ", 1)[-1], origen, checks, estado))
    tabla(doc, "Pull requests del proyecto", ["PR", "Rama", "Cambio", "Issue", "Checks", "Resultado"], filas,
          anchos=[1.1, 4.3, 5.3, 1.3, 1.6, 2.6], tam=8.5,
          nota_txt="Datos obtenidos con la API de GitHub. Los PR #6 y #7 se fusionaron antes de que existiera el "
                   "workflow de CI, por eso no tienen checks. El PR #11 es la prueba de fallo controlada (sección "
                   "6.4).")
    issues_txt = "; ".join(f"#{n} {t}" for n, t in sorted(issues.items()))
    parrafo(doc, f"Issues registrados: {issues_txt}.")
    pm = D["proteccion_main"]
    parrafo(doc, "Cuando el CI estuvo funcionando, protegí la rama main con estas reglas (GitHub, 2026b): solo se "
            "puede cambiar mediante pull request; el check «" + ", ".join(pm["checks"]) + "» debe estar en verde; "
            "la rama del PR debe estar actualizada con main"
            + ("; y las reglas aplican también al administrador del repositorio, es decir, a mí."
               if pm["aplica_a_admins"] else "."))

    doc.add_heading("5.4 Pruebas automatizadas", 2)
    parrafo(doc, "Las pruebas se escribieron con pytest (pytest-dev, 2026) y se organizaron por nivel, desde "
            "funciones aisladas hasta el pipeline completo. Ninguna hace peticiones a Internet: usan el HTML de "
            "data/raw/ y escriben en una carpeta temporal mediante EA2_SALIDA (tests/conftest.py).")
    descr = {
        "tests/test_parsers.py": ("Unitarias", "Limpieza de precios, identificador MCO, capacidad, detección del A55 "
                                  "y parsing de una tarjeta de ejemplo"),
        "tests/test_listado_html.py": ("Integración", "BeautifulSoup sobre las 3 páginas reales: número de tarjetas, "
                                       "campos obligatorios y vigencia de los selectores"),
        "tests/test_scrapy.py": ("Unitarias e integración", "Pipeline de limpieza y spider real con origen=local: "
                                 "119 registros, 4 duplicados descartados"),
        "tests/test_analisis.py": ("Regresión", "El análisis reproduce las cifras de la EA1 y genera las figuras"),
        "tests/test_sitio.py": ("Integración", "Generación del tablero, escape de HTML y fecha de captura"),
    }
    filas = [(Path(a).name, descr[a][0], descr[a][1], n) for a, n in pruebas_por_archivo.items()]
    filas.append(("Total", "", "", sum(pruebas_por_archivo.values())))
    tabla(doc, "Suite de pruebas automatizadas", ["Archivo", "Tipo", "Qué valida", "Pruebas"], filas,
          anchos=[3.6, 2.8, 7.8, 2.0], tam=9)

    doc.add_heading("5.5 Integración continua con GitHub Actions", 2)
    parrafo(doc, "El workflow .github/workflows/ci.yml se ejecuta en cada pull request hacia main y en cada push a "
            "main (GitHub, 2026a). Usa una matriz con Python 3.12 y 3.13 para comprobar que el proyecto funciona "
            "en ambas versiones, guarda en caché las dependencias de pip y cancela ejecuciones viejas de la misma "
            "rama cuando llega un commit nuevo. Sus pasos son:")
    tabla(doc, "Pasos del workflow de integración continua (ci.yml)", ["Paso", "Acción o comando", "Propósito"], [
        ("1. Descargar el código", "actions/checkout", "Obtener el commit a verificar"),
        ("2. Instalar Python", "actions/setup-python (con caché de pip)", "Preparar 3.12 y 3.13 en paralelo"),
        ("3. Dependencias", "pip install -r requirements-dev.txt", "Instalar librerías, pytest y ruff"),
        ("4. Estilo", "ruff check .", "Detectar errores y problemas de estilo"),
        ("5. Pruebas", "pytest --cov", f"Ejecutar las {M['pruebas']} pruebas y medir la cobertura"),
        ("6. Pipeline de datos", "BeautifulSoup --local, Scrapy origen=local, 04_analisis.py",
         "Comprobar que el proceso completo corre"),
        ("7. Resumen", "Tabla en $GITHUB_STEP_SUMMARY", "Mostrar los indicadores en la ejecución"),
        ("8. Artefactos", "actions/upload-artifact", "Guardar CSV, figuras, cobertura y reporte JUnit"),
        ("Job «ci»", "needs: pruebas", "Check único que exige la protección de main"),
    ], anchos=[3.3, 6.3, 6.6], tam=9)

    doc.add_heading("5.6 Despliegue continuo en GitHub Pages", 2)
    parrafo(doc, "El workflow .github/workflows/deploy.yml no se dispara con cada push, sino con el evento "
            "workflow_run cuando el workflow CI termina en main. Su primer job revisa que CI haya terminado con "
            "éxito; si falló, no se despliega nada. Si pasó, descarga exactamente el commit que CI validó, "
            "regenera datos, figuras y tablero (06_sitio.py) y lo empaqueta con actions/upload-pages-artifact. El "
            "segundo job lo publica con actions/deploy-pages en el entorno github-pages (GitHub, 2026d). El "
            "tablero muestra en su pie el commit y la ejecución que lo produjeron, así que cualquier persona puede "
            "rastrear de qué versión del código salen las cifras que está viendo. La Figura 1 resume el flujo "
            "completo.")
    figura(doc, "Flujo de trabajo DevOps implementado", fig_flujo,
           "Elaboración propia. Arriba, el trabajo en ramas (GitHub Flow); abajo, la integración y la entrega "
           "automáticas. Si CI falla, el cambio vuelve a la rama y no llega a main ni a GitHub Pages.")
    parrafo(doc, "La documentación del flujo quedó en el propio repositorio: el README tiene insignias de estado, el "
            "diagrama del pipeline en Mermaid, instrucciones de uso y los resultados, y CONTRIBUTING.md explica "
            "cómo nombrar ramas, escribir commits y abrir pull requests. También hay plantillas de pull request y "
            "de issues para tareas y errores.")


def resultados(doc, D, R, M, fig_ejec):
    doc.add_heading("6. Resultados", 1)
    doc.add_heading("6.1 Repositorio e historial", 2)
    parrafo(doc, f"El proyecto quedó publicado en {D['url_repo']}. A la fecha de este informe, el repositorio "
            f"registra lo siguiente:")
    indicadores(doc, [(M["commits"], "commits en main"), (M["prs_fusionados"], "pull requests fusionados"),
                      (f"{M['issues_cerrados']}/{M['issues']}", "issues cerrados"),
                      (M["ejecuciones"], "ejecuciones de Actions"), (pct(M["cobertura"], 0), "cobertura")])
    tipos = Counter(c["asunto"].split(":")[0].split("(")[0] for c in D["commits"] if not c["merge"])
    tipos_txt = ", ".join(f"{n} {t}" for t, n in tipos.most_common())
    parrafo(doc, f"De los {M['commits']} commits, {M['merges']} son commits de merge de pull requests y "
            f"{M['commits'] - M['merges']} son cambios de trabajo ({tipos_txt}). Como cada PR se fusionó con un "
            f"commit de merge, el historial de main conserva qué cambios entraron juntos y desde qué rama. La "
            f"etiqueta {D['tags'][0]} marca el punto de partida heredado de la EA1.")
    figura(doc, "Página principal del repositorio en GitHub", recorte("01_repo.png"),
           "Captura del repositorio público con el README, las insignias de CI y Deploy y el enlace al tablero.")
    figura(doc, "Pull requests del proyecto", recorte("03_pulls.png", alto=1700),
           "Cada PR muestra si sus checks pasaron (3/3) o fallaron (0/3, el PR de demostración #11, cerrado sin "
           "fusionar).")

    doc.add_heading("6.2 Ejecuciones del pipeline", 2)
    ejec = [e for e in D["ejecuciones"] if e["conclusion"] in ("success", "failure")]
    grupos = {}
    for e in ejec:
        clave = (e["workflow"], "pull request" if e["evento"] == "pull_request"
                 else "push a main" if e["evento"] == "push" else "tras CI en main")
        grupos.setdefault(clave, []).append(e)
    filas = []
    for (wf, ev), es in grupos.items():
        dur = [e["duracion_s"] for e in es]
        filas.append((wf, ev, len(es), sum(e["conclusion"] == "success" for e in es),
                      sum(e["conclusion"] == "failure" for e in es), duracion(round(sum(dur) / len(dur))),
                      f"{duracion(min(dur))} – {duracion(max(dur))}"))
    tabla(doc, "Ejecuciones de GitHub Actions por workflow y evento",
          ["Workflow", "Disparador", "Ejecuciones", "Éxitos", "Fallos", "Duración media", "Rango"], filas,
          anchos=[2.0, 2.9, 2.4, 1.5, 1.5, 2.4, 3.5], tam=8.5,
          nota_txt="Duración total de cada ejecución (de inicio a fin), obtenida con la API de GitHub. En CI, los "
                   "jobs de Python 3.12 y 3.13 corren en paralelo.")
    exito = sum(e["conclusion"] == "success" for e in ejec)
    parrafo(doc, f"De {len(ejec)} ejecuciones terminadas, {exito} fueron exitosas. La única falla fue la del PR de "
            f"demostración, que se diseñó para fallar. Una verificación completa toma alrededor de un minuto, así que "
            f"la retroalimentación llega casi de inmediato. Desde que se fusiona un PR hasta que el tablero queda "
            f"publicado pasan unos dos minutos: uno de CI sobre main y otro de despliegue. La Figura 4 muestra cada "
            f"ejecución en orden.")
    figura(doc, "Duración de las ejecuciones de GitHub Actions", fig_ejec,
           "Elaboración propia con datos de la API de GitHub.", ancho=14.5)
    figura(doc, "Ejecución del workflow CI sobre main", recorte("05_ci_main.png", alto=1600),
           "Los dos jobs de la matriz y el job «ci» terminan en verde; el resumen indica la duración total y el "
           "artefacto generado.")

    doc.add_heading("6.3 Pruebas y cobertura", 2)
    cob = D["cobertura"]
    filas = [(Path(a).as_posix().replace("scraping/", ""), pct(v, 0)) for a, v in cob["archivos"].items()
             if not a.endswith("__init__.py")]
    filas.append(("Total", pct(cob["total"], 0)))
    resultado = cob["resultado"].replace("passed", "aprobadas").replace(" in ", " en ")
    tabla(doc, "Cobertura de las pruebas por módulo", ["Módulo", "Cobertura"], filas, anchos=[10, 3],
          nota_txt=f"Resultado de pytest --cov: {resultado}. "
                   "01_selenium_navegador.py se excluye porque requiere un navegador real con sesión gráfica.")
    parrafo(doc, "Las funciones de limpieza (parsers.py) y el pipeline de Scrapy quedaron cubiertos al 100 %. En la "
            "primera medición, 02_bs4_listado.py aparecía con 0 % porque la prueba lo lanzaba en un subproceso que "
            "pytest-cov no ve. Al ejecutarlo en el mismo proceso (PR #16), la cobertura total pasó de 78 % a "
            f"{pct(cob['total'], 0)}. Las líneas que quedan sin cubrir son sobre todo las de descarga en vivo, que "
            "por diseño no se ejecutan en CI.")

    doc.add_heading("6.4 El pipeline detectando errores reales", 2)
    parrafo(doc, "La pregunta de fondo era si el flujo detecta de verdad los errores. Estos son los casos que "
            "ocurrieron durante el trabajo:")
    vinetas(doc, [
        ("Una condición no prevista. ", "Al escribir la prueba que valida los campos de cada publicación, supuse "
         "que la condición solo podía ser Nuevo, Usado o Reacondicionado. La prueba falló: una publicación del A55 "
         "estaba marcada como «Caja abierta». Los datos reales corrigieron mi supuesto antes de que llegara al "
         "repositorio."),
        ("El error de la EA1, reintroducido a propósito. ", "En el PR #11 volví al selector de envío anterior, el "
         "que en la EA1 dejaba el envío gratis en 0 % sin fallar. El CI lo detectó en ambas versiones de Python, "
         "con tres pruebas en rojo: la unitaria de la tarjeta, la de vigencia de selectores y la de regresión, que "
         "esperaba 90 % y obtuvo 0 %. La protección de main impidió fusionarlo y el PR se cerró sin fusionar "
         "(Figura 6)."),
        ("Un dato faltante en producción. ", "Al revisar el primer despliegue noté que el tablero publicado no "
         "mostraba la fecha de captura de los datos, aunque en mi equipo sí aparecía. La causa: en el pipeline, "
         "el resumen se genera en EA2_SALIDA, donde no está la métrica de Selenium. Lo registré como issue (#12), "
         "lo corregí con una prueba nueva (PR #13) y el siguiente despliegue ya mostraba la fecha."),
        ("Dependencias obsoletas. ", "Las ejecuciones advirtieron que varias acciones usaban Node.js 20, que GitHub "
         "declaró obsoleto. Mi primer intento (PR #14, upload-artifact v5) no bastó, porque esa versión todavía "
         "declaraba Node 20; lo comprobé en las anotaciones de la ejecución y en el PR #15 actualicé todas las "
         "acciones. Las ejecuciones siguientes no registraron advertencias."),
    ])
    figura(doc, "Ejecución fallida del CI en el pull request de demostración", recorte("08_ci_fallido.png", alto=1900),
           "Los tres jobs terminan en rojo. Sin un check «ci» exitoso, GitHub no permite fusionar el PR en main.")

    doc.add_heading("6.5 Despliegue continuo", 2)
    deploys = [e for e in ejec if e["workflow"] == "Deploy"]
    parrafo(doc, f"El workflow Deploy se ejecutó {len(deploys)} veces, todas con éxito y siempre después de un CI "
            f"exitoso en main. El tablero está disponible en {D['url_pages']} y muestra los indicadores, las tres "
            f"figuras del análisis, el precio por condición y las {R['publicaciones_a55']} publicaciones del A55, "
            f"con enlace a cada una. Funciona en celular y en computador, tiene modo claro y oscuro y no depende "
            f"de librerías externas.")
    figura(doc, "Tablero publicado en GitHub Pages", recorte("10_tablero.png", alto=2300),
           "Parte superior del tablero. El pie de página (no visible en la captura) enlaza el commit y la "
           "ejecución de GitHub Actions que lo publicaron.")

    doc.add_heading("6.6 Resultados del análisis, reproducidos por el pipeline", 2)
    parrafo(doc, "Cada ejecución del pipeline vuelve a calcular el análisis desde el HTML capturado. Las cifras son "
            "idénticas a las de la EA1, y la prueba de regresión garantiza que lo seguirán siendo mientras no "
            "cambien los datos de entrada:")
    filas = [(c["condicion"], c["count"], cop(c["min"]), cop(c["median"]), cop(c["max"]))
             for c in R["por_condicion"]]
    tabla(doc, "Precio del Galaxy A55 según la condición del equipo",
          ["Condición", "Publicaciones", "Mínimo", "Mediana", "Máximo"], filas, anchos=[3.2, 3.2, 3.2, 3.2, 3.2],
          nota_txt=f"Precios en pesos colombianos. Mediana general: {cop(R['precio']['50%'])}; coeficiente de "
                   f"variación: {pct(R['coef_variacion_pct'])}.")
    figura(doc, "Precio según la condición del equipo", FIG_DIR / "fig2_precio_por_condicion.png",
           "Generada por 04_analisis.py en cada ejecución del pipeline. Cada punto es una publicación y la raya "
           "horizontal marca la mediana.", ancho=14)
    parrafo(doc, f"La conclusión de la EA1 se mantiene: en la misma búsqueda conviven un mercado de equipos nuevos "
            f"y uno, mucho más grande, de equipos usados o reacondicionados ({pct(R['pct_reacondicionado'], 0)} "
            f"de las publicaciones). Con el pipeline, esa conclusión ya no depende de que alguien ejecute los "
            f"scripts a mano: queda verificada y publicada con cada cambio.")


def conclusiones(doc, M):
    doc.add_heading("7. Conclusiones", 1)
    doc.add_heading("Sobre los objetivos", 2)
    parrafo(doc, f"Se cumplió el objetivo general. El proyecto de la EA1 quedó versionado en un repositorio público "
            f"con un historial trazable de issues, ramas y pull requests, y con un pipeline que verifica cada "
            f"cambio con {M['pruebas']} pruebas en dos versiones de Python y publica el tablero solo si todo pasa. "
            f"La respuesta a la pregunta de esta evidencia es que la garantía no viene de una herramienta, sino de "
            f"la combinación de pruebas que fijan el comportamiento esperado, una rama protegida que no acepta "
            f"cambios sin esas pruebas y un despliegue que depende del resultado del CI.")
    doc.add_heading("Lo que aprendí", 2)
    vinetas(doc, [
        ("Las pruebas convierten los errores silenciosos en errores visibles. ", "El fallo de selector que en la "
         "EA1 pasó inadvertido ahora rompe tres pruebas en menos de un minuto. En scraping, donde el sitio cambia "
         "sin aviso, esa red de seguridad es lo más valioso del flujo."),
        ("Separar captura y procesamiento hace el pipeline reproducible. ", "Versionar el HTML capturado permitió "
         "probar todo el proceso sin depender del sitio ni de su protección anti-bot, y sin enviarle tráfico."),
        ("Los cambios pequeños se revisan mejor. ", "Cada PR resolvió una sola cosa y se integró en minutos. "
         "Cuando una corrección no bastó (PR #14), el siguiente PR la completó sin afectar el resto."),
        ("Producción también enseña. ", "Dos de los problemas que corregí (la fecha faltante y las acciones "
         "obsoletas) solo aparecieron al desplegar y leer las ejecuciones, no en mi equipo."),
    ])
    doc.add_heading("Limitaciones", 2)
    vinetas(doc, [
        "El pipeline procesa una captura fija del 25 de octubre de 2026: verifica el código, pero no actualiza los "
        "precios. La captura en vivo sigue siendo manual.",
        "Trabajé solo, así que los pull requests no tuvieron revisión de otra persona; en un equipo real la regla "
        "de protección debería exigir al menos una aprobación.",
        "La ruta de descarga en vivo de BeautifulSoup y Scrapy no se prueba en CI, por la misma razón por la que no "
        "se hace scraping en vivo.",
    ])
    doc.add_heading("Relación con la Unidad 3 y el proyecto de cierre", 2)
    parrafo(doc, "Esta evidencia deja la base para la Unidad 3, dedicada a optimizar los procesos de desarrollo con "
            "GitHub Actions y a la puesta en producción de servicios. Los siguientes pasos naturales son: programar "
            "una captura periódica (evento schedule) en un runner propio o en un contenedor con navegador, para "
            "construir una serie de tiempo de precios; empaquetar el scraper en una imagen Docker; automatizar las "
            "actualizaciones de dependencias y las notas de versión; y agregar alertas cuando el pipeline falle. "
            "Para el proyecto de cierre, ese mismo flujo puede sostener una propuesta de negocio: un servicio de "
            "monitoreo de precios para vendedores de Mercado Libre, con datos verificados y publicados de forma "
            "automática.")


def bibliografia(doc):
    doc.add_heading("Referencias", 1)
    refs = [
        ("Chacon, S., y Straub, B. (2014). ", "Pro Git", " (2.ª ed.). Apress. https://git-scm.com/book/es/v2"),
        ("Chapman, P., Clinton, J., Kerber, R., Khabaza, T., Reinartz, T., Shearer, C., y Wirth, R. (2000). ",
         "CRISP-DM 1.0: Step-by-step data mining guide", ". SPSS Inc."),
        ("Conventional Commits. (2019). ", "Conventional Commits 1.0.0",
         ". https://www.conventionalcommits.org/es/v1.0.0/"),
        ("Cuervo Quintero, J. N., y Cuervo Quintero, Y. M. (2026). ", "Web scraping en el comercio electrónico: "
         "precio y oferta del Samsung Galaxy A55 en Mercado Libre Colombia",
         " [Evidencia de aprendizaje 1, Programación para Análisis de Datos]. Institución Universitaria Digital "
         "de Antioquia."),
        ("Forsgren, N., Humble, J., y Kim, G. (2018). ", "Accelerate: The science of lean software and DevOps",
         ". IT Revolution Press."),
        ("Fowler, M. (2024, 18 de enero). ", "Continuous integration",
         ". martinfowler.com. https://martinfowler.com/articles/continuousIntegration.html"),
        ("GitHub. (2026a). ", "Documentación de GitHub Actions", ". https://docs.github.com/es/actions"),
        ("GitHub. (2026b). ", "Acerca de las ramas protegidas",
         ". https://docs.github.com/es/repositories/configuring-branches-and-merges-in-your-repository/"
         "managing-protected-branches/about-protected-branches"),
        ("GitHub. (2026c). ", "Flujo de GitHub", ". https://docs.github.com/es/get-started/using-github/github-flow"),
        ("GitHub. (2026d). ", "Documentación de GitHub Pages", ". https://docs.github.com/es/pages"),
        ("Humble, J., y Farley, D. (2010). ", "Continuous delivery: Reliable software releases through build, test, "
         "and deployment automation", ". Addison-Wesley."),
        ("Kim, G., Humble, J., Debois, P., Willis, J., y Forsgren, N. (2021). ", "The DevOps handbook: How to "
         "create world-class agility, reliability, and security in technology organizations",
         " (2.ª ed.). IT Revolution Press."),
        ("Krotov, V., Johnson, L., y Silva, L. (2020). Tutorial: Legality and ethics of web scraping. ",
         "Communications of the Association for Information Systems, 47", ", 539–563. "
         "https://doi.org/10.17705/1CAIS.04724"),
        ("MercadoLibre, Inc. (2025). ", "Annual report (Form 10-K) for the fiscal year ended December 31, 2024",
         ". U.S. Securities and Exchange Commission. https://investor.mercadolibre.com/"),
        ("Mitchell, R. (2024). ", "Web scraping with Python: Data extraction from the modern web",
         " (3.ª ed.). O'Reilly Media."),
        ("pytest-dev. (2026). ", "pytest documentation", ". https://docs.pytest.org/"),
        ("Samsung Electronics. (2024). ", "Galaxy A55 5G: Especificaciones",
         ". https://www.samsung.com/co/smartphones/galaxy-a/galaxy-a55-5g/"),
        ("Scrapy developers. (2026). ", "Scrapy documentation", ". https://docs.scrapy.org/"),
        ("Selenium Project. (2026). ", "The Selenium browser automation project: Documentation",
         ". https://www.selenium.dev/documentation/"),
    ]
    for antes, cursiva, despues in refs:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(1.27)
        p.paragraph_format.first_line_indent = Cm(-1.27)
        p.add_run(antes)
        p.add_run(cursiva).italic = True
        p.add_run(despues)


def anexo(doc, D):
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    doc.add_heading("Anexo A. Código fuente e implementación", 1)
    parrafo(doc, f"Todo el código está en {D['url_repo']} (rama main, commit {D['commits'][-1]['hash']}) y en el "
            "archivo ZIP que acompaña este informe. La estructura del repositorio es:")
    codigo(doc, [
        "EA2-DevOps-Scraping-GalaxyA55/",
        "├── .github/",
        "│   ├── workflows/ci.yml           integración continua",
        "│   ├── workflows/deploy.yml       despliegue continuo en GitHub Pages",
        "│   ├── pull_request_template.md",
        "│   └── ISSUE_TEMPLATE/            plantillas de tarea y error",
        "├── scraping/",
        "│   ├── config.py                  URL, selectores, cortesía y rutas (EA2_SALIDA)",
        "│   ├── parsers.py                 limpieza y parsing compartidos",
        "│   ├── 01_selenium_navegador.py   captura con navegador real (manual)",
        "│   ├── 02_bs4_listado.py          requests + BeautifulSoup (--local)",
        "│   ├── ml_scrapy/                 spider, item y pipeline de Scrapy",
        "│   ├── 04_analisis.py             pandas + matplotlib",
        "│   └── 06_sitio.py                tablero para GitHub Pages",
        "├── tests/                         pytest: unitarias, integración y regresión",
        "├── data/raw/                      HTML capturado por Selenium (entrada de las pruebas)",
        "├── data/, figuras/                resultados de la EA1 (línea base)",
        "├── informe/                       recolección de datos y generación de este informe",
        "├── README.md, CONTRIBUTING.md",
        "├── pyproject.toml                 configuración de pytest, cobertura y ruff",
        "└── requirements.txt, requirements-dev.txt",
    ], tam=8.5)
    doc.add_paragraph()
    doc.add_heading("Cómo reproducir el proyecto", 2)
    codigo(doc, [
        f"git clone {D['url_repo']}.git",
        "cd EA2-DevOps-Scraping-GalaxyA55",
        "python3 -m venv .venv && source .venv/bin/activate",
        "pip install -r requirements-dev.txt",
        "ruff check . && pytest --cov",
        "export EA2_SALIDA=$PWD/salida && cd scraping",
        "python 02_bs4_listado.py --local",
        "(cd ml_scrapy && scrapy crawl galaxy_a55 -a origen=local)",
        "python 04_analisis.py && python 06_sitio.py",
    ], tam=8.5)
    doc.add_paragraph()
    parrafo(doc, "A continuación se incluye el código de los archivos creados o modificados en esta evidencia. Los "
            "scripts de scraping heredados de la EA1 (01_selenium_navegador.py, 02_bs4_listado.py, 04_analisis.py "
            "y el proyecto Scrapy) están completos en el repositorio y en el ZIP.")
    for rel in [".github/workflows/ci.yml", ".github/workflows/deploy.yml", "scraping/config.py",
                "scraping/parsers.py", "scraping/06_sitio.py", "tests/conftest.py", "tests/test_parsers.py",
                "tests/test_listado_html.py", "tests/test_scrapy.py", "tests/test_analisis.py",
                "tests/test_sitio.py", "pyproject.toml"]:
        bloque_codigo(doc, rel)

    doc.add_heading("Anexo B. Enlaces", 1)
    vinetas(doc, [
        ("Repositorio: ", D["url_repo"]),
        ("Tablero publicado: ", D["url_pages"]),
        ("Ejecuciones de GitHub Actions: ", D["url_repo"] + "/actions"),
        ("Pull requests: ", D["url_repo"] + "/pulls?q=is%3Apr"),
        ("Issues: ", D["url_repo"] + "/issues?q=is%3Aissue"),
    ])


def pruebas_por_archivo():
    salida = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q"], cwd=RAIZ,
                            capture_output=True, text=True, check=True).stdout
    conteo = Counter(linea.split("::")[0] for linea in salida.splitlines() if "::" in linea)
    orden = ["tests/test_parsers.py", "tests/test_listado_html.py", "tests/test_scrapy.py",
             "tests/test_analisis.py", "tests/test_sitio.py"]
    return {a: conteo[a] for a in orden}


def main():
    D = json.loads((INFORME / "datos.json").read_text(encoding="utf-8"))
    R = json.loads((RAIZ / "data" / "resumen.json").read_text(encoding="utf-8"))
    ppa = pruebas_por_archivo()
    ejec = [e for e in D["ejecuciones"] if e["conclusion"] in ("success", "failure")]
    M = {
        "commits": len(D["commits"]),
        "merges": sum(c["merge"] for c in D["commits"]),
        "prs": len(D["pull_requests"]),
        "prs_fusionados": sum(p["fusionado"] for p in D["pull_requests"]),
        "issues": len(D["issues"]),
        "issues_cerrados": sum(i["estado"] == "closed" for i in D["issues"]),
        "ejecuciones": len(ejec),
        "pruebas": sum(ppa.values()),
        "cobertura": D["cobertura"]["total"],
    }
    hoy = datetime.now()
    fecha = f"{MESES[hoy.month - 1]} de {hoy.year}"

    doc = Document()
    estilos(doc)
    encabezado_y_pie(doc.sections[0])
    portada(doc, fecha, D)
    resumen(doc, D, R, M)
    introduccion(doc)
    descripcion(doc, R)
    tema(doc)
    objetivos(doc)
    metodologia(doc, D, R, M, ppa, figura_flujo())
    resultados(doc, D, R, M, figura_ejecuciones(D["ejecuciones"]))
    conclusiones(doc, M)
    bibliografia(doc)
    anexo(doc, D)
    SALIDA.parent.mkdir(exist_ok=True)
    doc.save(SALIDA)
    print(f"Informe generado: {SALIDA}")


if __name__ == "__main__":
    main()
