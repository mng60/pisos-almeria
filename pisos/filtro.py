"""Zona de cada piso y clasificación en «cumple», «confirmar» o «descartar»."""
from __future__ import annotations

import re
from dataclasses import replace

from . import config
from .modelo import Piso
from .texto import detectar_ascensor, detectar_garaje, normalizar


def zona_de(portal: str, barrio: str | None) -> str | None:
    """Zona de config.ZONAS a la que pertenece el barrio del portal, o None.

    Una zona agrupada entra entera (diseño: mejor que sobre un piso de Ciudad Jardín a que falte uno
    del Zapillo). Si el barrio nombra dos zonas, se devuelven las dos: «Oliveros / Altamira».
    """
    if not barrio:
        return None
    b = normalizar(barrio).strip()
    for nombre, zona in config.BARRIOS.get(portal, {}).items():
        if normalizar(nombre).strip() == b:
            return zona
    halladas = [z for z in config.ZONAS if re.search(rf"\b{re.escape(normalizar(z))}\b", b)]
    return " / ".join(halladas) or None


def completar(p: Piso) -> Piso:
    """Rellena zona y, si el portal no los da, garaje y ascensor leyendo la descripción.

    El dato estructurado del portal manda; la descripción solo rellena lo que falta.
    """
    garaje, nota = detectar_garaje(p.descripcion)
    return replace(
        p,
        zona=p.zona or zona_de(p.portal, p.barrio),
        garaje=p.garaje or garaje,
        nota_garaje=p.nota_garaje or nota,
        ascensor=p.ascensor or detectar_ascensor(p.descripcion),
    )


def clasificar(p: Piso) -> str:
    base = (
        config.PRECIO_MIN <= p.precio <= config.PRECIO_MAX
        and p.habitaciones == config.HABITACIONES
        and p.zona is not None
        and p.banos in (config.BANOS, None)
    )
    if not base or "no" in (p.garaje, p.ascensor):
        return "descartar"
    if p.garaje == "si" and p.ascensor == "si" and p.banos == config.BANOS:
        return "cumple"
    return "confirmar"
