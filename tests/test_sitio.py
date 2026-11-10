"""Prueba del tablero web que se despliega en GitHub Pages."""
import pandas as pd

from conftest import RAIZ, cargar_script


def test_genera_index_con_indicadores_y_figuras(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_SHA", "abc1234def")
    monkeypatch.setenv("GITHUB_RUN_ID", "42")
    sitio = cargar_script("06_sitio.py")
    # Se usan los datos versionados de la EA1 como entrada
    monkeypatch.setattr(sitio.config, "DATA_DIR", RAIZ / "data")
    monkeypatch.setattr(sitio.config, "FIG_DIR", RAIZ / "figuras")
    monkeypatch.setattr(sitio, "SITE_DIR", tmp_path)

    sitio.main()

    index = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert index.startswith("<!doctype html>")
    assert "$874.950" in index                     # precio mediano
    assert "Publicaciones del Galaxy A55 (30)" in index
    assert "abc1234" in index and "actions/runs/42" in index
    assert len(list((tmp_path / "figuras").glob("*.png"))) == 3
    assert (tmp_path / ".nojekyll").exists()


def test_escapa_html_de_los_titulos():
    sitio = cargar_script("06_sitio.py")
    tel = pd.DataFrame([{"titulo": "A55 <script>", "condicion": "Nuevo", "capacidad_gb": 256,
                         "precio_actual": 1_000_000, "envio_gratis": True, "url": "https://x/MCO1#a"}])
    resumen = {"publicaciones_totales": 1, "publicaciones_a55": 1, "precio": {"50%": 1_000_000},
               "pct_envio_gratis": 100.0,
               "por_condicion": [{"condicion": "Nuevo", "count": 1, "min": 1, "median": 1, "max": 1}]}
    pagina = sitio.construir(resumen, tel)
    assert "<script>" not in pagina
    assert "A55 &lt;script&gt;" in pagina
