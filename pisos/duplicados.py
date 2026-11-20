"""El mismo piso suele estar en varios portales: se agrupa para enseñarlo una vez con todos sus enlaces.

Criterio (diseño, «mejor de menos que de más»): mismo precio, mismas habitaciones, misma zona no nula, y m²
a ±3 si los dos los traen. Dos anuncios del mismo portal nunca se juntan. Ante la duda, dos tarjetas.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields, replace

from .modelo import Piso

MARGEN_M2 = 3


@dataclass
class Grupo:
    principal: Piso                                  # datos fusionados de todos los anuncios
    miembros: list[Piso] = field(default_factory=list)

    @property
    def enlaces(self) -> list[tuple[str, str]]:
        return [(p.portal, p.url) for p in self.miembros]


def mismo_piso(a: Piso, b: Piso) -> bool:
    if a.portal == b.portal or a.zona is None:
        return False
    if (a.precio, a.habitaciones, a.zona) != (b.precio, b.habitaciones, b.zona):
        return False
    return a.m2 is None or b.m2 is None or abs(a.m2 - b.m2) <= MARGEN_M2


def _si_no(valores: list[str | None]) -> str | None:
    """Un «no» explícito de cualquier portal gana; si no, un «si»; si no, sin dato."""
    return "no" if "no" in valores else "si" if "si" in valores else None


def fusionar(miembros: list[Piso]) -> Piso:
    base = miembros[0]
    cambios = {}
    for f in fields(Piso):
        if f.name in ("garaje", "ascensor"):
            cambios[f.name] = _si_no([getattr(p, f.name) for p in miembros])
        elif getattr(base, f.name) is None:
            cambios[f.name] = next((getattr(p, f.name) for p in miembros if getattr(p, f.name) is not None), None)
    return replace(base, **cambios)


def agrupar(pisos: list[Piso]) -> list[Grupo]:
    grupos: list[list[Piso]] = []
    for p in pisos:
        destino = next((g for g in grupos
                        if all(mismo_piso(p, q) for q in g)), None)
        if destino is None:
            grupos.append([p])
        else:
            destino.append(p)
    return [Grupo(principal=fusionar(g), miembros=g) for g in grupos]
