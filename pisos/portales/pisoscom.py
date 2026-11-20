"""pisos.com, por su HTML.

Medido el 20/11/2026 (tests/fixtures/pisoscom_*.html):
- el precio se filtra en la ruta (/desde-500/hasta-700/) y se pagina con /2/, /3/…; cada anuncio es un
  .ad-preview con «precio | título | Barrio (Almería Capital) | N habs. | N baño(s) | m² | planta | extracto»;
- en la ficha, la descripción está en .description__content y el equipamiento son etiquetas
  .features__label («Ascensor», «Aire acondicionado»…): si la etiqueta no está, no se sabe (None), no es «no».
"""
from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup

from .. import config
from ..filtro import zona_de
from ..modelo import Piso
from ..texto import leer_precio, normalizar
from . import PAUSA, PortalCaido, entero, paginar, pedir

NOMBRE = "pisoscom"
BASE = "https://www.pisos.com"
LISTADO = f"{BASE}/alquiler/pisos-almeria_capital/desde-{config.PRECIO_MIN}/hasta-{config.PRECIO_MAX}/"


def _num(patron: str, texto: str) -> int | None:
    m = re.search(patron, texto)
    return entero(m.group(1)) if m else None


def parsear(html: str) -> list[Piso]:
    s = BeautifulSoup(html, "html.parser")
    anuncios = s.select(".ad-preview")
    if not anuncios and "Alquiler de pisos en" not in html:
        raise PortalCaido(NOMBRE, "formato irreconocible: sin .ad-preview")
    pisos = []
    for a in anuncios:
        enlace = a.get("data-lnk-href")
        partes = list(a.stripped_strings)
        texto = " | ".join(partes)
        precio = leer_precio(next((t for t in partes if re.fullmatch(r"[\d.]+ €", t)), ""))
        if not enlace or precio is None:
            continue
        barrio = next((t[: -len(" (Almería Capital)")] for t in partes if t.endswith("(Almería Capital)")), None)
        img = a.find("img")
        pisos.append(Piso(
            portal=NOMBRE,
            id=enlace.rstrip("/").split("-")[-1],
            url=BASE + enlace,
            precio=precio,
            habitaciones=_num(r"(\d+) habs?\.", texto),
            banos=_num(r"(\d+) baños?", texto),
            m2=_num(r"(\d+) m²", texto),
            planta=next((t for t in partes if re.fullmatch(r"\d+ª planta|Bajo|Ático|Entreplanta", t)), None),
            barrio=barrio,
            foto=img.get("src") if img else None,
        ))
    return pisos


def parsear_ficha(html: str) -> dict:
    s = BeautifulSoup(html, "html.parser")
    d = s.select_one(".description__content")
    etiquetas = [normalizar(x.get_text(" ", strip=True)) for x in s.select(".features__label")]
    return {
        "descripcion": d.get_text(" ", strip=True) if d else None,
        "ascensor": "si" if any(e.startswith("ascensor") for e in etiquetas) else None,
        "garaje": "si" if any(re.search(r"garaje|parking|plaza de aparcamiento", e) for e in etiquetas) else None,
    }


def recoger(s: requests.Session) -> list[Piso]:
    pisos = paginar(lambda n: parsear(pedir(s, NOMBRE, LISTADO if n == 1 else f"{LISTADO}{n}/").text),
                    pausa=PAUSA)
    for p in pisos:
        if (config.PRECIO_MIN <= p.precio <= config.PRECIO_MAX and p.habitaciones == config.HABITACIONES
                and zona_de(NOMBRE, p.barrio) is not None):
            f = parsear_ficha(pedir(s, NOMBRE, p.url).text)
            p.descripcion = f["descripcion"]
            p.ascensor = p.ascensor or f["ascensor"]
            p.garaje = p.garaje or f["garaje"]
    return pisos
