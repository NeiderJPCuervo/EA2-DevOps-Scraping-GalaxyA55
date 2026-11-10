"""Recolecta los datos reales del repositorio para el informe de la EA2.

Usa la CLI de GitHub (gh, con sesión iniciada) y git, y ejecuta pytest con
cobertura. Escribe informe/datos.json, que lee generar_informe_ea2.py.

Uso (desde la raíz del repositorio):
    python informe/recolectar_datos.py
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
REPO = "NeiderJPCuervo/EA2-DevOps-Scraping-GalaxyA55"
SALIDA = RAIZ / "informe" / "datos.json"


def sh(*cmd):
    return subprocess.run(cmd, cwd=RAIZ, check=True, capture_output=True, text=True).stdout


def api(ruta):
    """Una página de la API envuelta en lista (todas las listas tienen < 100 elementos)."""
    return [json.loads(sh("gh", "api", ruta))]


def segundos(inicio, fin):
    a = datetime.fromisoformat(inicio.replace("Z", "+00:00"))
    b = datetime.fromisoformat(fin.replace("Z", "+00:00"))
    return round((b - a).total_seconds())


def commits():
    formato = "%h%x1f%ad%x1f%s%x1f%P"
    filas = []
    for linea in sh("git", "log", "main", "--date=iso-strict", f"--pretty=format:{formato}").splitlines():
        h, fecha, asunto, padres = linea.split("\x1f")
        filas.append({"hash": h, "fecha": fecha, "asunto": asunto, "merge": len(padres.split()) > 1})
    return filas[::-1]


def pull_requests():
    prs = []
    for p in sorted((x for pag in api(f"repos/{REPO}/pulls?state=all&per_page=100") for x in pag),
                    key=lambda x: x["number"]):
        checks = api(f"repos/{REPO}/commits/{p['head']['sha']}/check-runs?per_page=100")
        runs = [c for pag in checks for c in pag["check_runs"]]
        prs.append({
            "numero": p["number"], "titulo": p["title"], "rama": p["head"]["ref"],
            "fusionado": bool(p["merged_at"]), "estado": p["state"],
            "etiquetas": [e["name"] for e in p["labels"]],
            "checks_ok": sum(c["conclusion"] == "success" for c in runs),
            "checks_total": len(runs),
            "cierra": [int(n) for n in re.findall(r"Closes #(\d+)", p["body"] or "")],
        })
    return prs


def issues():
    return [{"numero": i["number"], "titulo": i["title"], "estado": i["state"],
             "etiquetas": [e["name"] for e in i["labels"]]}
            for pag in api(f"repos/{REPO}/issues?state=all&per_page=100") for i in pag
            if "pull_request" not in i]


def ejecuciones():
    runs = [r for pag in api(f"repos/{REPO}/actions/runs?per_page=100") for r in pag["workflow_runs"]]
    filas = []
    for r in sorted(runs, key=lambda r: r["run_started_at"]):
        filas.append({
            "id": r["id"], "workflow": r["name"], "evento": r["event"], "rama": r["head_branch"],
            "sha": r["head_sha"][:7], "conclusion": r["conclusion"], "titulo": r["display_title"],
            "inicio": r["run_started_at"], "duracion_s": segundos(r["run_started_at"], r["updated_at"]),
        })
    return filas


def cobertura():
    with tempfile.TemporaryDirectory() as tmp:
        reporte = Path(tmp) / "cov.json"
        res = subprocess.run([sys.executable, "-m", "pytest", "-q", "--cov", f"--cov-report=json:{reporte}"],
                             cwd=RAIZ, capture_output=True, text=True,
                             env=os.environ | {"EA2_SALIDA": tmp})
        datos = json.loads(reporte.read_text())
    resumen = res.stdout.strip().splitlines()[-1]
    archivos = {Path(k).as_posix(): round(v["summary"]["percent_covered"], 1) for k, v in datos["files"].items()}
    return {"resultado": resumen, "total": round(datos["totals"]["percent_covered"], 1), "archivos": archivos}


def main():
    prot = json.loads(sh("gh", "api", f"repos/{REPO}/branches/main/protection"))
    release = json.loads(sh("gh", "api", f"repos/{REPO}/releases"))
    datos = {
        "repo": REPO,
        "url_repo": f"https://github.com/{REPO}",
        "url_pages": json.loads(sh("gh", "api", f"repos/{REPO}/pages"))["html_url"],
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "commits": commits(),
        "pull_requests": pull_requests(),
        "issues": issues(),
        "ejecuciones": ejecuciones(),
        "cobertura": cobertura(),
        "proteccion_main": {
            "checks": prot["required_status_checks"]["contexts"],
            "rama_actualizada": prot["required_status_checks"]["strict"],
            "requiere_pr": prot.get("required_pull_request_reviews") is not None,
            "aplica_a_admins": prot["enforce_admins"]["enabled"],
        },
        "releases": [{"tag": r["tag_name"], "nombre": r["name"], "fecha": r["published_at"]} for r in release],
        "tags": sh("git", "tag").split(),
    }
    SALIDA.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(datos['commits'])} commits, {len(datos['pull_requests'])} PR, {len(datos['issues'])} issues, "
          f"{len(datos['ejecuciones'])} ejecuciones, cobertura {datos['cobertura']['total']} % → {SALIDA}")


if __name__ == "__main__":
    main()
