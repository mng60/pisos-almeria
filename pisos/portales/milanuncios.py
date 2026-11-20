"""Milanuncios, por la API de búsqueda que usa su web (no oficial: si cambia, se desactiva en
config.PORTALES_DESACTIVADOS).

Medido el 20/11/2026 (tests/fixtures/milanuncios_listado.json):
- category=132 es «alquiler-de-pisos», city=8 es Almería capital, y priceFrom/priceTo filtran el precio;
- no hay barrio: el título suele ser la zona («Zapillo - C. California») o «Almería Capital», y en ese caso la
  zona se busca en la descripción (filtro.completar);
- transaction=demand son anuncios de gente que BUSCA piso: se excluyen;
- con 22 resultados todo cabe en una página (limit=50); nextToken no se ha visto funcionar, así que no se pagina
  y, si algún día hubiera más de 50, se avisa en el registro.
"""
from __future__ import annotations

import logging

import requests

from .. import config
from ..modelo import Piso
from . import PortalCaido, entero, pedir

NOMBRE = "milanuncios"
API = "https://searchapi.gw.milanuncios.com/v3/classifieds"
LIMITE = 50
PARAMS = {"category": 132, "city": 8, "priceFrom": config.PRECIO_MIN, "priceTo": config.PRECIO_MAX,
          "limit": LIMITE}
log = logging.getLogger(__name__)


def parsear(respuesta: dict) -> list[Piso]:
    if not isinstance(respuesta, dict) or "ads" not in respuesta:
        raise PortalCaido(NOMBRE, "formato irreconocible: falta ads")
    pisos = []
    for a in respuesta["ads"]:
        if a.get("transaction") != "supply":
            continue
        at = {x["field"]["raw"]: x["value"] for x in a.get("attributes") or []}
        precio = entero(((a.get("price") or {}).get("cash") or {}).get("value"))
        if precio is None:
            continue
        pisos.append(Piso(
            portal=NOMBRE,
            id=str(a["id"]),
            url="https://www.milanuncios.com" + a.get("url", ""),
            precio=precio,
            habitaciones=entero((at.get("bedrooms") or {}).get("raw")),
            banos=entero((at.get("bathrooms") or {}).get("raw")),
            m2=entero((at.get("squareMeters") or {}).get("raw")),
            planta=(at.get("floor") or {}).get("formatted"),
            barrio=a.get("title"),
            descripcion=a.get("description"),
        ))
    return pisos


def recoger(s: requests.Session) -> list[Piso]:
    r = pedir(s, NOMBRE, API, params=PARAMS,
              headers={"Accept": "application/json", "Origin": "https://www.milanuncios.com"})
    try:
        datos = r.json()
    except ValueError as e:
        raise PortalCaido(NOMBRE, "respuesta no es JSON") from e
    total = ((datos.get("pagination") or {}).get("totalHits") or {}).get("value", 0)
    if total > LIMITE:
        log.warning("milanuncios: %s resultados y solo se leen %s", total, LIMITE)
    return parsear(datos)
