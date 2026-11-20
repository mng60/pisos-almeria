"""Ejecución diaria (GitHub Actions): recoger → completar → estado → página → correos.

Uso: python -m pisos.servidor   (desde la raíz del repositorio)
Variables: GMAIL_USUARIO, GMAIL_CLAVE_APP, CORREO_DESTINO (Belén), CORREO_AVISOS (Miguel), PAGINA_URL,
PISOS_FORZAR_AVISO=1 (manda un aviso de prueba a CORREO_AVISOS).
"""
from __future__ import annotations

import importlib
import json
import logging
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from . import config
from .correo import correo_avisos, correo_belen, enviar as enviar_gmail
from .duplicados import agrupar
from .estado import actualizar, cargar, clave, guardar, vigentes
from .filtro import completar
from .modelo import Piso
from .pagina import generar_pagina
from .portales import PortalCaido, sesion

log = logging.getLogger("pisos")
DIAS_DATOS_PC = 1   # se usan los datos del PC de hoy y de ayer (≈ 48 h)


def portales_por_defecto() -> dict[str, Callable]:
    return {n: importlib.import_module(f"pisos.portales.{n}").recoger
            for n in config.PORTALES_SERVIDOR if n not in config.PORTALES_DESACTIVADOS}


def _recoger_todo(portales: dict[str, Callable]) -> dict[str, list[Piso] | PortalCaido]:
    s = sesion()
    recogidos: dict[str, list[Piso] | PortalCaido] = {}
    for nombre, recoger in portales.items():
        try:
            recogidos[nombre] = [completar(p) for p in recoger(s)]
            log.info("%s: %d anuncios", nombre, len(recogidos[nombre]))
        except PortalCaido as e:
            recogidos[nombre] = e
            log.warning("%s caído: %s", nombre, e.motivo)
        except Exception as e:  # noqa: BLE001 - un fallo de un lector no para a los demás
            recogidos[nombre] = PortalCaido(nombre, f"error inesperado: {type(e).__name__}: {e}")
            log.exception("%s: error inesperado", nombre)
    return recogidos


def datos_pc(carpeta: Path, hoy: date, portales_pc=config.PORTALES_PC) -> dict[str, list[Piso] | PortalCaido]:
    """Lo que subió el PC, por portal, según la fecha del fichero más reciente de data/pc:
    - de hoy: tal cual (pisos o caído);
    - de ayer: sus pisos siguen contando como vistos, pero su «caído» se omite porque ya se contó ayer
      (contarlo otra vez avisaba a Miguel al segundo día por un solo captcha: hallazgo de la revisión final);
    - más antiguo o ninguno: el portal cuenta como caído («el PC no ha subido datos»), y así a los 2 días avisa.
    """
    ultimo: dict[str, tuple[date, object]] = {}
    for f in sorted(carpeta.glob("*.json")) if carpeta.exists() else []:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            fecha = datetime.fromisoformat(d["fecha"]).date()
            portales = d["portales"]
        except (ValueError, KeyError, TypeError):
            log.warning("data/pc/%s no es un fichero del PC: se ignora", f.name)
            continue
        for portal, v in portales.items():
            if portal not in ultimo or fecha >= ultimo[portal][0]:
                ultimo[portal] = (fecha, v)
    res: dict[str, list[Piso] | PortalCaido] = {}
    for portal in portales_pc:
        fecha, v = ultimo.get(portal, (None, None))
        if fecha is None or fecha < hoy - timedelta(days=DIAS_DATOS_PC):
            res[portal] = PortalCaido(portal, "el PC no ha subido datos (¿apagado o sin sesión?)")
        elif isinstance(v, dict):
            if fecha == hoy:
                res[portal] = PortalCaido(portal, v.get("caido", "?"))
        else:
            res[portal] = [completar(Piso.de_dict(x)) for x in v]
    return res


def ejecutar(raiz: Path, portales: dict[str, Callable], hoy: date, enviar: Callable | None = None,
             entorno=os.environ, portales_pc=None) -> dict:
    if portales_pc is None:
        portales_pc = [n for n in config.PORTALES_PC if n not in config.PORTALES_DESACTIVADOS]
    datos = raiz / "data"
    estado = cargar(datos / "vistos.json")
    salud = cargar(datos / "salud.json")

    recogidos = _recoger_todo(portales)
    recogidos.update(datos_pc(datos / "pc", hoy, portales_pc))
    nuevos, avisos = actualizar(estado, salud, recogidos, hoy)

    grupos = agrupar(vigentes(estado))
    claves_nuevas = {clave(p) for p in nuevos}
    grupos_nuevos = [g for g in grupos if all(clave(m) in claves_nuevas for m in g.miembros)]

    sitio = raiz / "sitio"
    sitio.mkdir(parents=True, exist_ok=True)
    (sitio / "index.html").write_text(
        generar_pagina(grupos, estado, datetime.now(timezone.utc), salud), encoding="utf-8")
    guardar(datos / "vistos.json", estado)
    guardar(datos / "salud.json", salud)

    if entorno.get("PISOS_FORZAR_AVISO") == "1":
        salud.setdefault("prueba", {"fallos_seguidos": 2, "motivo": "aviso de prueba (PISOS_FORZAR_AVISO=1)"})
        avisos = avisos + ["prueba"]

    resumen = {"vigentes": len(grupos), "nuevos": len(grupos_nuevos), "avisos": avisos}
    usuario, clave_app = entorno.get("GMAIL_USUARIO"), entorno.get("GMAIL_CLAVE_APP")
    if not (usuario and clave_app):
        log.warning("sin credenciales de correo: no se envía (%s)", resumen)
        return resumen
    mandar = enviar or (lambda msg: enviar_gmail(msg, usuario, clave_app))
    if entorno.get("CORREO_DESTINO"):
        msg = correo_belen(grupos_nuevos, usuario, entorno["CORREO_DESTINO"], estado)
        if msg:
            mandar(msg)
    if entorno.get("CORREO_AVISOS"):
        msg = correo_avisos(avisos, salud, usuario, entorno["CORREO_AVISOS"])
        if msg:
            mandar(msg)
    log.info("hecho: %s", resumen)
    return resumen


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ejecutar(Path.cwd(), portales_por_defecto(), datetime.now(timezone.utc).date())


if __name__ == "__main__":
    main()
