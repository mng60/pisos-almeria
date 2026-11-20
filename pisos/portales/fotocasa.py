"""Fotocasa, por su API JSON de búsqueda (la misma que usa su web).

Medido el 20/11/2026 sobre tests/fixtures/fotocasa_listado.json:
- `features` trae rooms, bathrooms, surface y elevator (solo si lo tiene); nunca garaje: el garaje
  sale de la descripción (campo `description`, completo en el listado).
- `floor` es un código, no la planta: el anuncio 191151501 dice «3ª planta» y trae floor=8. Por eso
  la planta de Fotocasa queda vacía.
"""
from __future__ import annotations

import requests

from .. import config
from ..modelo import Piso
from . import PAUSA, PortalCaido, entero, paginar, pedir

NOMBRE = "fotocasa"
API = "https://web.gw.fotocasa.es/v2/propertysearch/search"
# Almería capital: país 724, Andalucía 1, provincia 4, comarca 276, zona 486, municipio 4013.
PARAMS = {
    "combinedLocationIds": "724,1,4,276,486,4013,0,0,0", "culture": "es-ES", "isMap": "false",
    "platformId": "1", "propertyTypeId": "2", "sortOrderDesc": "true", "sortType": "publicationDate",
    "transactionTypeId": "3", "minPrice": str(config.PRECIO_MIN), "maxPrice": str(config.PRECIO_MAX),
    "minRooms": str(config.HABITACIONES), "maxRooms": str(config.HABITACIONES),
}


def _primero(features: dict, clave: str):
    v = features.get(clave)
    return v[0] if isinstance(v, list) and v else v


def parsear(respuesta: dict) -> list[Piso]:
    if not isinstance(respuesta, dict) or "realEstates" not in respuesta:
        raise PortalCaido(NOMBRE, "formato irreconocible: falta realEstates")
    pisos = []
    for r in respuesta["realEstates"]:
        f = {x["key"]: x["value"] for x in r.get("features") or []}
        precio = entero((r.get("transactions") or [{}])[0].get("value"))
        if precio is None:
            continue
        fotos = r.get("multimedias") or []
        pisos.append(Piso(
            portal=NOMBRE,
            id=str(r["id"]),
            url="https://www.fotocasa.es" + (r.get("detail") or {}).get("es", ""),
            precio=precio,
            habitaciones=entero(_primero(f, "rooms")),
            banos=entero(_primero(f, "bathrooms")),
            m2=entero(_primero(f, "surface")),
            planta=None,
            barrio=(r.get("address") or {}).get("location", {}).get("level7") or None,
            ascensor="si" if _primero(f, "elevator") else None,
            foto=fotos[0].get("url") if fotos else None,
            descripcion=r.get("description"),
        ))
    return pisos


def recoger(s: requests.Session) -> list[Piso]:
    def obtener(n: int) -> list[Piso]:
        try:
            return parsear(pedir(s, NOMBRE, API, params={**PARAMS, "pageNumber": str(n)}).json())
        except ValueError as e:
            raise PortalCaido(NOMBRE, "respuesta no es JSON") from e

    return paginar(obtener, pausa=PAUSA)
