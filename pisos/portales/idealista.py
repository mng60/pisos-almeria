"""Idealista, desde el PC con Edge visible (desde un servidor bloquea con captcha: README).

Medido el 20/11/2026 (tests/fixtures/idealista_*.html, Edge visible tras resolver el captcha a mano):
- la URL admite filtros en la ruta (con-precio-hasta_700,precio-desde_500,de-dos-dormitorios) y se pagina con
  pagina-N.htm; cada anuncio es un article.item con .item-link («Piso en Calle X, 99, Zapillo, Almería»),
  .item-price y .item-detail («2 hab.», «70 m²», «1ª planta exterior sin ascensor», «Garaje incluido»);
- la ficha trae la descripción en .comment y las características en .details-property_features.
"""
from __future__ import annotations

import re
from typing import Callable

from bs4 import BeautifulSoup

from .. import config
from ..filtro import clasificar, completar
from ..modelo import Piso
from ..texto import detectar_ascensor, leer_precio
from . import PortalCaido, entero, paginar

NOMBRE = "idealista"
BASE = "https://www.idealista.com"
LISTADO = (f"{BASE}/alquiler-viviendas/almeria-almeria/con-precio-hasta_{config.PRECIO_MAX},"
           f"precio-desde_{config.PRECIO_MIN},de-dos-dormitorios/")
CAPTCHA = re.compile(r"captcha-delivery|geo\.captcha")
MAX_PAGINAS_PC = 5


def _barrio(titulo: str) -> str | None:
    partes = [x.strip() for x in titulo.split(",")]
    if len(partes) < 2:
        return None
    b = partes[-2]
    return b.rsplit(" en ", 1)[1] if " en " in b and len(partes) == 2 else b


def parsear(html: str) -> list[Piso]:
    if CAPTCHA.search(html[:20000]) and "article" not in html:
        raise PortalCaido(NOMBRE, "captcha")
    s = BeautifulSoup(html, "html.parser")
    articulos = s.select("article.item[data-element-id]")
    if not articulos and "items-container" not in html:
        raise PortalCaido(NOMBRE, "formato irreconocible: sin article.item")
    pisos = []
    for a in articulos:
        enlace = a.select_one(".item-link")
        precio = leer_precio(a.select_one(".item-price").get_text(" ", strip=True)) if a.select_one(".item-price") else None
        if not enlace or precio is None:
            continue
        detalles = [x.get_text(" ", strip=True) for x in a.select(".item-detail")]
        texto = " | ".join(detalles)
        planta = next((d for d in detalles if re.search(r"planta|Bajo|Entreplanta|Ático", d)), None)
        img = next((i.get("src") for i in a.select("img") if "idealista.com" in (i.get("src") or "")
                    and "placeholder" not in i.get("src")), None)
        m_hab, m_m2 = re.search(r"(\d+) hab\.", texto), re.search(r"(\d+) m²", texto)
        pisos.append(Piso(
            portal=NOMBRE,
            id=a["data-element-id"],
            url=BASE + enlace["href"],
            precio=precio,
            habitaciones=entero(m_hab.group(1)) if m_hab else None,
            banos=None,   # el listado no lo trae; la ficha sí
            m2=entero(m_m2.group(1)) if m_m2 else None,
            planta=planta,
            barrio=_barrio(enlace.get_text(" ", strip=True)),
            garaje="si" if re.search(r"Garaje incluido", texto) else None,
            ascensor=detectar_ascensor(planta),
            foto=img,
        ))
    return pisos


def parsear_ficha(html: str) -> dict:
    s = BeautifulSoup(html, "html.parser")
    comentario = s.select_one(".comment")
    caract = [x.get_text(" ", strip=True) for x in s.select(".details-property_features li")]
    texto = " ".join(caract)
    m = re.search(r"(\d+) baños?", texto)
    # Las características («Sin ascensor», «Plaza de garaje incluida en el precio») se añaden al texto que
    # analiza filtro.completar(), como frases separadas.
    descripcion = ". ".join(([comentario.get_text(" ", strip=True)] if comentario else []) + caract)
    return {"descripcion": descripcion or None, "banos": entero(m.group(1)) if m else None}


def recoger(abrir: Callable[[str], str]) -> list[Piso]:
    """`abrir(url) -> html` lo pone pisos.navegador (Edge visible, espera al captcha)."""
    pisos = paginar(lambda n: parsear(abrir(LISTADO if n == 1 else f"{LISTADO}pagina-{n}.htm")),
                    maximo=MAX_PAGINAS_PC)
    for p in pisos:
        if clasificar(completar(p)) == "confirmar":
            f = parsear_ficha(abrir(p.url))
            p.descripcion = f["descripcion"]
            p.banos = p.banos or f["banos"]
    return pisos
