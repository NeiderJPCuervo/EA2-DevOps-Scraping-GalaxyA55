# Cómo contribuir

El proyecto sigue **GitHub Flow**: `main` siempre está lista para desplegarse y
todo cambio entra por un pull request que pasó el pipeline de CI.

## 1. Planear con un issue
Cada trabajo empieza con un issue que describe el objetivo y los criterios de
aceptación. Etiquetas: `pruebas`, `ci-cd`, `refactor`, `documentación`, `bug`.

## 2. Crear una rama corta desde `main`

```bash
git switch main && git pull
git switch -c feature/<tema>      # nueva funcionalidad
git switch -c fix/<tema>          # corrección
git switch -c refactor/<tema>     # mejora interna
git switch -c docs/<tema>         # documentación
```

## 3. Commits pequeños con Conventional Commits

| Prefijo | Uso |
|---|---|
| `feat:` | nueva funcionalidad |
| `fix:` | corrección de un error |
| `test:` | pruebas |
| `ci:` | workflows de GitHub Actions |
| `refactor:` | cambio interno sin alterar el resultado |
| `docs:` | documentación |
| `chore:` | mantenimiento |

Incluya `Refs #n` o `Closes #n` para enlazar el issue.

## 4. Verificar antes de subir

```bash
ruff check .
pytest
```

## 5. Abrir el pull request
`git push -u origin <rama>` y `gh pr create`. La plantilla pide el resumen y
cómo se probó. La rama `main` está protegida: solo acepta cambios por PR y
exige que el check **ci** esté en verde y que la rama esté actualizada.

## 6. Fusionar y desplegar
Al fusionar, CI se ejecuta sobre `main` y, si pasa, el workflow **Deploy**
publica el tablero en GitHub Pages. La rama se borra tras la fusión.

## Si Mercado Libre cambia su HTML
1. Vuelva a capturar las páginas con `python scraping/01_selenium_navegador.py`
   (navegador visible; resuelva la verificación a mano si aparece).
2. Ajuste los selectores en `scraping/config.py`.
3. Actualice los valores esperados de `tests/test_listado_html.py` y
   `tests/test_analisis.py`, y abra un PR `fix/selectores`.
