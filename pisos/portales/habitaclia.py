"""Habitaclia, por su HTML. Desde 2026 corre sobre la plataforma de Fotocasa (mismos barrios, fotos en
static.fotocasa.es), así que muchos anuncios coinciden con los de Fotocasa; los junta duplicados.agrupar().

Medido el 20/11/2026 (tests/fixtures/habitaclia_*.html):
- el listado acepta ?minPrice=&maxPrice=&minRooms=&maxRooms= (el de habitaciones solo como mínimo) y se pagina
  con /s/2, /s/3…; cada anuncio es un <article> con «precio | título | barrio, Almería Capital | m² | hab. | baños |
  planta»;
- la descripción solo está en la ficha (h2 «Descripción» + div), y las características como pares «clave | valor».
"""
from __future__ import annotations

import re
import time

import requests
from bs4 import BeautifulSoup

from .. import config
from ..filtro import zona_de
from ..modelo import Piso
from ..texto import leer_precio, normalizar
from . import PAUSA, PortalCaido, entero, paginar, pedir

NOMBRE = "habitaclia"
BASE = "https://www.habitaclia.com"
LISTADO = BASE + "/alquiler/viviendas/almeria-provincia/almeria-capital/s"
PARAMS = {"minPrice": config.PRECIO_MIN, "maxPrice": config.PRECIO_MAX,
          "minRooms": config.HABITACIONES, "maxRooms": config.HABITACIONES}


def _barrio(partes: list[str]) -> str | None:
    for i, t in enumerate(partes):
        if re.search(r",\s*Almer[ií]a( Capital)?$", t):
            antes = t.split(",")[0].strip()
            if normalizar(antes) != "almeria capital":
                return antes
            titulo = partes[i - 1] if i else ""
            # «Piso con terraza en alquiler en Retamar»: el barrio va tras el ÚLTIMO « en ».
            return titulo.rsplit(" en ", 1)[1].strip() if " en " in titulo else None
    return None


def parsear(html: str) -> list[Piso]:
    s = BeautifulSoup(html, "html.parser")
    articulos = s.find_all("article")
    if not articulos and "ItemList" not in html:
        raise PortalCaido(NOMBRE, "formato irreconocible: sin anuncios ni ItemList")
    pisos = []
    for a in articulos:
        enlace = next((x["href"] for x in a.find_all("a", href=True) if x["href"].endswith("/d")), None)
        partes = list(a.stripped_strings)
        texto = " | ".join(partes)
        precio = leer_precio(next((t for t in partes if "€/mes" in t), ""))
        if not enlace or precio is None:
            continue
        img = a.find("img")
        planta = next((t for t in partes if re.fullmatch(r"\d+º|Bajo|Ático|Entresuelo", t)), None)
        pisos.append(Piso(
            portal=NOMBRE,
            id=enlace.rstrip("/").split("/")[-2],
            url=BASE + enlace,
            precio=precio,
            habitaciones=entero(re.search(r"(\d+) hab\.", texto) and re.search(r"(\d+) hab\.", texto).group(1)),
            banos=entero(re.search(r"(\d+) baños?", texto) and re.search(r"(\d+) baños?", texto).group(1)),
            m2=entero(re.search(r"(\d+) m²", texto) and re.search(r"(\d+) m²", texto).group(1)),
            planta=planta,
            barrio=_barrio(partes),
            foto=(img.get("src") or img.get("data-src")) if img else None,
        ))
    return pisos


def _si_no(v: str | None) -> str | None:
    if v is None:
        return None
    v = normalizar(v)
    return "si" if v.startswith("si") else "no" if v.startswith("no") else None


def parsear_ficha(html: str) -> dict:
    """{'descripcion', 'ascensor', 'garaje'} de la ficha; garaje/ascensor solo si vienen como característica."""
    s = BeautifulSoup(html, "html.parser")
    h = s.find(lambda t: t.name == "h2" and t.get_text(strip=True) == "Descripción")
    desc = h.find_next_sibling().get_text(" ", strip=True) if h and h.find_next_sibling() else None
    pares = list(s.stripped_strings)
    caract = {}
    for clave, valor in zip(pares, pares[1:]):
        caract.setdefault(normalizar(clave), valor)
    garaje = _si_no(caract.get("garaje") or caract.get("parking") or caract.get("plaza de garaje"))
    return {"descripcion": desc, "ascensor": _si_no(caract.get("ascensor")), "garaje": garaje}


def _candidato(p: Piso) -> bool:
    """Solo se abre la ficha de lo que ya cumple precio, habitaciones y zona (diseño)."""
    return (config.PRECIO_MIN <= p.precio <= config.PRECIO_MAX and p.habitaciones == config.HABITACIONES
            and zona_de(NOMBRE, p.barrio) is not None)


def recoger(s: requests.Session) -> list[Piso]:
    def obtener(n: int) -> list[Piso]:
        url = LISTADO if n == 1 else f"{LISTADO}/{n}"
        return parsear(pedir(s, NOMBRE, url, params=PARAMS).text)

    pisos = paginar(obtener, pausa=PAUSA)
    for p in pisos:
        if _candidato(p):
            ficha = parsear_ficha(pedir(s, NOMBRE, p.url).text)
            p.descripcion = ficha["descripcion"]
            p.ascensor = p.ascensor or ficha["ascensor"]
            p.garaje = p.garaje or ficha["garaje"]
            time.sleep(PAUSA)
    return pisos
