"""Lectura de garaje, ascensor y precio a partir del texto libre de un anuncio.

El garaje suele aparecer solo en la descripción y no en las características del portal
(Miguel, 20/11/2026), así que esto se aplica a la descripción de todos los anuncios.
"""
from __future__ import annotations

import re
import unicodedata

# Palabras que niegan si aparecen hasta VENTANA palabras antes del término.
NEGACIONES = {"sin", "no"}
VENTANA = 5
OPCIONAL = re.compile(r"opcional|posibilidad|aparte|adicional|se alquila por separado")
IMPORTE = re.compile(r"(\d+)\s*(?:€|euros?)")

GARAJE = re.compile(r"garaje|cochera|parking|plaza de aparcamiento|plazas de aparcamiento|aparcamiento privado")
ASCENSOR = re.compile(r"ascensor(?:es)?")


def normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFD", texto)
    sin_tildes = "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")
    return sin_tildes.lower()


def _menciones(texto: str, patron: re.Pattern) -> list[tuple[bool, str]]:
    """Por cada mención del término: (negada, contexto de alrededor)."""
    res = []
    for m in patron.finditer(texto):
        # Solo cuenta la misma frase o inciso: un «no» de la frase anterior no niega.
        tramo = re.split(r"[.,;:!?\n()]", texto[: m.start()])[-1]
        antes = re.findall(r"\w+", tramo)[-VENTANA:]
        # «sin muebles y con garaje»: un «con» posterior a la negación la anula.
        ultima_neg = max((i for i, p in enumerate(antes) if p in NEGACIONES), default=-1)
        negada = ultima_neg >= 0 and "con" not in antes[ultima_neg + 1:]
        contexto = texto[max(0, m.start() - 60): m.end() + 40]
        res.append((negada, contexto))
    return res


def detectar_garaje(texto: str | None) -> tuple[str | None, str | None]:
    """("si" | "no" | None, nota). Una negación explícita gana a cualquier afirmación."""
    if not texto:
        return None, None
    t = normalizar(texto)
    menciones = _menciones(t, GARAJE)
    if not menciones:
        return None, None
    if any(neg for neg, _ in menciones):
        return "no", None
    for _, ctx in menciones:
        if OPCIONAL.search(ctx):
            importe = IMPORTE.search(ctx)
            return "si", f"opcional {importe.group(1)} €" if importe else "opcional"
    return "si", None


def detectar_ascensor(texto: str | None) -> str | None:
    if not texto:
        return None
    menciones = _menciones(normalizar(texto), ASCENSOR)
    if not menciones:
        return None
    return "no" if any(neg for neg, _ in menciones) else "si"


def leer_precio(texto: str | None) -> int | None:
    """Entero de euros: «1.200 €/mes» → 1200, «650 € + gastos» → 650; sin número → None."""
    if not texto:
        return None
    m = re.search(r"(\d{1,3}(?:\.\d{3})+|\d+)", texto)
    return int(m.group(1).replace(".", "")) if m else None
