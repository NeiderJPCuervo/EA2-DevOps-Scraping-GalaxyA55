# EA1 — Web scraping: Samsung Galaxy A55 en Mercado Libre Colombia

Extracción y análisis de las publicaciones del Samsung Galaxy A55 en
mercadolibre.com.co usando **Selenium**, **BeautifulSoup** y **Scrapy**, con
generación automática del informe en Word.

## Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Se necesita Firefox instalado (Selenium Manager descarga `geckodriver` solo).

## Ejecución (en este orden, desde la carpeta `scraping/`)

| Paso | Comando | Resultado |
|---|---|---|
| 1. Selenium | `python 01_selenium_navegador.py` | `data/raw/listado_p*.html`, `data/selenium_detalle.json` |
| 2. BeautifulSoup | `python 02_bs4_listado.py` | `data/bs4_listado.csv` |
| 3. Scrapy | `cd ml_scrapy && scrapy crawl galaxy_a55 && cd ..` | `data/scrapy_listado.csv` |
| 4. Análisis | `python 04_analisis.py` | `figuras/*.png`, `data/resumen.json` |
| 5. Informe | `python 05_generar_informe.py` | `Informe_Scraping_MercadoLibre_GalaxyA55.docx` |

O todo seguido: `bash run_all.sh`.

### Notas

- **Verificación anti-bot.** Mercado Libre redirige las peticiones HTTP simples a
  `/gz/account-verification`. Los scripts no la evaden: Selenium abre una ventana
  real de Firefox y, si aparece la verificación, espera a que usted la resuelva y
  pulse Enter. BeautifulSoup y Scrapy, si son bloqueados, analizan el HTML que
  Selenium guardó en `data/raw/` (también se puede forzar: `python 02_bs4_listado.py --local`
  y `scrapy crawl galaxy_a55 -a origen=local`).
- **robots.txt.** Para agentes genéricos permite el listado y las fichas `/p/`;
  Scrapy está configurado con `ROBOTSTXT_OBEY = True`, 3 s de pausa y 1 conexión.
- **Selectores.** Si Mercado Libre cambia su HTML, ajuste solo `scraping/config.py`.
- **Portada.** Complete nombre, institución, asignatura y docente en las
  constantes al inicio de `05_generar_informe.py` y vuelva a ejecutarlo.
