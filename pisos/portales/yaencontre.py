"""yaencontre, desde el PC con Edge visible (desde un servidor bloquea con captcha: README).

Medido el 20/11/2026 (tests/fixtures/yaencontre_*.html):
- la URL con filtros que se DEDUJO (/f-2-habitaciones/p-500-700) daba 404; la real, sacada usando los filtros
  en la web, es /distrito-almeria-ciudad/f-2-habitaciones,500-700euros (ver LISTADO); se pagina con /pag-N;
- cada anuncio es un article.real-estate-card: «Ático en Retamar, Almería | 850 | € | /mes | 3 habs. | 2 baños |
  155 m² | … | Planta 2ª»;
- la ficha trae el equipamiento como etiquetas li.yae-tag («Ascensor», «Garaje») y la descripción tras un h3
  «Descripción».
"""
from __future__ import annotations

import re
from typing import Callable

from bs4 import BeautifulSoup

from .. import config
from ..filtro import clasificar, completar
from ..modelo import Piso
from ..texto import normalizar
from . import PortalCaido, entero, paginar

NOMBRE = "yaencontre"
BASE = "https://www.yaencontre.com"
# Medido el 20/11/2026 aplicando los filtros a mano en la web: 200 → 5 resultados. Las habitaciones solo
# admiten mínimo («2+»): los de 3 o más se descartan después.
LISTADO = (f"{BASE}/alquiler/pisos/almeria/distrito-almeria-ciudad/"
           f"f-{config.HABITACIONES}-habitaciones,{config.PRECIO_MIN}-{config.PRECIO_MAX}euros")
MAX_PAGINAS_PC = 6


def _num(patron: str, texto: str) -> int | None:
    m = re.search(patron, texto)
    return entero(m.group(1).replace(".", "")) if m else None


def parsear(html: str) -> list[Piso]:
    if "Error 404" in html[:3000]:
        raise PortalCaido(NOMBRE, "404: la URL del listado ya no existe")
    if re.search(r"captcha-delivery|geo\.captcha", html[:20000]) and "real-estate-card" not in html:
        raise PortalCaido(NOMBRE, "captcha")
    s = BeautifulSoup(html, "html.parser")
    tarjetas = s.select("article.real-estate-card")
    if not tarjetas:
        raise PortalCaido(NOMBRE, "formato irreconocible: sin article.real-estate-card")
    pisos = []
    for a in tarjetas:
        enlace = next((x["href"] for x in a.find_all("a", href=True) if "/inmueble-" in x["href"]), None)
        partes = list(a.stripped_strings)
        texto = " | ".join(partes)
        precio = _num(r"\| ([\d.]+) \| € \| /mes", texto)
        if not enlace or precio is None:
            continue
        titulo = next((t for t in partes if re.search(r" en .+, Almería$", t)), "")
        img = a.find("img")
        pisos.append(Piso(
            portal=NOMBRE,
            id=enlace.rsplit("inmueble-", 1)[1],
            url=BASE + enlace,
            precio=precio,
            habitaciones=_num(r"(\d+) habs?\.", texto),
            banos=_num(r"(\d+) baños?", texto),
            m2=_num(r"(\d+) m²", texto),
            planta=next((t for t in partes if t.startswith("Planta ") or t in ("Bajo", "Ático")), None),
            barrio=titulo.rsplit(" en ", 1)[1].rsplit(",", 1)[0].strip() if titulo else None,
            foto=img.get("src") if img else None,
        ))
    return pisos


def parsear_ficha(html: str) -> dict:
    s = BeautifulSoup(html, "html.parser")
    etiquetas = [normalizar(x.get_text(" ", strip=True)) for x in s.select("li.yae-tag")]
    h = s.find(lambda t: t.name in ("h2", "h3") and t.get_text(strip=True) == "Descripción")
    sig = h.find_next_sibling() if h else None
    return {
        "descripcion": sig.get_text(" ", strip=True) if sig else None,
        "ascensor": "si" if "ascensor" in etiquetas else None,
        "garaje": "si" if any(re.search(r"garaje|parking", e) for e in etiquetas) else None,
    }


def recoger(abrir: Callable[[str], str]) -> list[Piso]:
    pisos = paginar(lambda n: parsear(abrir(LISTADO if n == 1 else f"{LISTADO}/pag-{n}")), maximo=MAX_PAGINAS_PC)
    for p in pisos:
        if clasificar(completar(p)) == "confirmar":
            try:
                f = parsear_ficha(abrir(p.url))
            except PortalCaido:
                continue   # una ficha caída no tira el portal: el piso se queda con lo del listado
            p.descripcion = f["descripcion"]
            p.ascensor = p.ascensor or f["ascensor"]
            p.garaje = p.garaje or f["garaje"]
    return pisos
