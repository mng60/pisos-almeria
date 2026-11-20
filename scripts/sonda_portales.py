"""Mide si cada portal deja leer sus anuncios a un script desde la máquina donde corre.

Es una medición, no una puerta: sale siempre con 0. Se usa para decidir qué portal corre en
GitHub Actions y cuál en el PC (ver README, «Qué portal corre dónde»).
"""
import re
import sys

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")

URLS = {
    "fotocasa_api": "https://web.gw.fotocasa.es/v2/propertysearch/search?combinedLocationIds=724,1,4,276,0,0,0,0,0"
                    "&culture=es-ES&isMap=false&pageNumber=1&platformId=1&propertyTypeId=2&sortOrderDesc=true"
                    "&sortType=publicationDate&transactionTypeId=3&minPrice=500&maxPrice=700",
    "fotocasa_web": "https://www.fotocasa.es/es/alquiler/viviendas/almeria-capital/todas-las-zonas/l",
    "habitaclia": "https://www.habitaclia.com/alquiler-almeria.htm",
    "pisoscom": "https://www.pisos.com/alquiler/pisos-almeria_capital/",
    "milanuncios_api": "https://searchapi.gw.milanuncios.com/v3/classifieds?s=piso&province=4&limit=5",
    "idealista": "https://www.idealista.com/alquiler-viviendas/almeria-almeria/",
    "yaencontre": "https://www.yaencontre.com/alquiler/pisos/almeria",
}

# Señal de anuncios por portal: cuenta aproximada, solo para distinguir "hay datos" de "página vacía".
SENAL = r'"realEstates"|"ads"|class="ad-preview|€/mes|list-item-container|item-info-container'


def main() -> int:
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "es-ES,es;q=0.9"})
    for nombre, url in URLS.items():
        try:
            r = s.get(url, timeout=30)
            t = r.text
            captcha = bool(re.search(r"captcha|datadome", t[:20000], re.I)) and r.status_code != 200
            n = len(re.findall(SENAL, t))
            print(f"{nombre:16} {r.status_code} bytes={len(r.content)} captcha={captcha} senales={n}")
        except Exception as e:  # noqa: BLE001 - es una sonda, se informa y se sigue
            print(f"{nombre:16} ERROR {type(e).__name__}: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
