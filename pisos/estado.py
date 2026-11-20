"""Qué pisos se han visto ya (data/vistos.json) y cómo va cada portal (data/salud.json).

Reglas del diseño:
- un piso es «nuevo» la primera vez que aparece y no se descarta;
- sale de la página tras DIAS_PARA_RETIRAR días seguidos sin aparecer;
- un portal caído (o con 0 resultados cuando antes tenía) no suma ausencias a sus pisos: ni desaparecen ni
  vuelven luego como nuevos;
- al llegar a DIAS_FALLO_AVISO días seguidos de fallo se avisa a Miguel, y luego cada 7 días mientras siga.

Ausencias y fallos cuentan UNA vez por día: el workflow corre por el cron y además cuando el PC sube datos.
Un portal que no viene en `recogidos` (Idealista con el PC apagado) no se ha consultado: no cuenta nada.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from . import config
from .filtro import clasificar
from .modelo import Piso
from .portales import PortalCaido

REPETIR_AVISO_DIAS = 7


def clave(p: Piso) -> str:
    return f"{p.portal}:{p.id}"


def cargar(ruta: Path) -> dict:
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}


def guardar(ruta: Path, datos: dict) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def _salud_inicial() -> dict:
    return {"fallos_seguidos": 0, "ultimo_fallo": None, "ultimo_ok": None, "ultimo_n": 0, "motivo": None}


def actualizar(estado: dict, salud: dict, recogidos: dict[str, list[Piso] | PortalCaido],
               hoy: date) -> tuple[list[Piso], list[str]]:
    """Devuelve (pisos nuevos no descartados, portales de los que hay que avisar hoy). Muta estado y salud."""
    dia = hoy.isoformat()
    nuevos: list[Piso] = []
    avisos: list[str] = []
    for portal, r in recogidos.items():
        sp = salud.setdefault(portal, _salud_inicial())
        caido = isinstance(r, PortalCaido)
        if caido or (not r and sp["ultimo_n"] > 0):
            if sp["ultimo_fallo"] != dia:
                sp["fallos_seguidos"] += 1
                sp["ultimo_fallo"] = dia
                exceso = sp["fallos_seguidos"] - config.DIAS_FALLO_AVISO
                if exceso >= 0 and exceso % REPETIR_AVISO_DIAS == 0:
                    avisos.append(portal)
            sp["motivo"] = r.motivo if caido else "0 resultados cuando antes había"
            continue
        sp.update(fallos_seguidos=0, ultimo_ok=dia, ultimo_n=len(r), motivo=None)

        vistos_hoy = set()
        for p in r:
            c = clave(p)
            if clasificar(p) == "descartar":
                estado.pop(c, None)   # p. ej. subió de precio: deja de mostrarse
                continue
            vistos_hoy.add(c)
            if c not in estado:
                nuevos.append(p)
                estado[c] = {"primera_vez": dia}
            estado[c].update(piso=p.a_dict(), ultima_vez=dia, ausencias=0, ultima_ausencia=None)

        for c in [c for c, v in estado.items() if v["piso"]["portal"] == portal and c not in vistos_hoy]:
            v = estado[c]
            if v.get("ultima_ausencia") != dia and v.get("ultima_vez") != dia:
                v["ausencias"] = v.get("ausencias", 0) + 1
                v["ultima_ausencia"] = dia
                if v["ausencias"] >= config.DIAS_PARA_RETIRAR:
                    del estado[c]
    return nuevos, avisos
