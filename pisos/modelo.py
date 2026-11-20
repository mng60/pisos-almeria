"""Formato común de un piso, el mismo para todos los portales."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields


@dataclass
class Piso:
    portal: str
    id: str
    url: str
    precio: int
    habitaciones: int | None
    banos: int | None
    m2: int | None
    planta: str | None
    barrio: str | None                 # tal y como lo nombra el portal
    zona: str | None = None            # una de config.ZONAS; la pone filtro.completar()
    garaje: str | None = None          # "si" | "no" | None (sin dato)
    nota_garaje: str | None = None     # p. ej. "opcional 50 €"
    ascensor: str | None = None        # "si" | "no" | None
    foto: str | None = None
    # La descripción solo vive en memoria para detectar garaje y ascensor: nunca se guarda ni se
    # publica (diseño, «Qué se guarda de cada anuncio»).
    descripcion: str | None = field(default=None, repr=False, compare=False)

    def a_dict(self) -> dict:
        d = asdict(self)
        d.pop("descripcion", None)
        return d

    @classmethod
    def de_dict(cls, d: dict) -> "Piso":
        nombres = {f.name for f in fields(cls)} - {"descripcion"}
        return cls(**{k: v for k, v in d.items() if k in nombres})
