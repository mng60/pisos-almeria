"""Parte del PC: Idealista y yaencontre con Edge visible → data/pc/<fecha>.json → push → relanza el workflow.

Uso: python -m pisos.pc [--seco] [--forzar]
  --seco    no hace git ni relanza el workflow (prueba)
  --forzar  consulta aunque hoy ya haya datos buenos
Lo lanza la tarea programada (scripts/instalar_pc.py) al iniciar sesión y a las 09:00. Como mucho consulta una vez
al día con éxito: cada visita de más arriesga otro captcha.
"""
from __future__ import annotations

import argparse
import importlib
import json
import logging
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

from . import config
from .filtro import completar
from .portales import PortalCaido

RAIZ = Path(__file__).resolve().parents[1]
log = logging.getLogger("pisos.pc")


def _hoy_ya_bien(ruta: Path) -> bool:
    if not ruta.exists():
        return False
    d = json.loads(ruta.read_text(encoding="utf-8"))
    return all(isinstance(v, list) for v in d.get("portales", {}).values()) and bool(d.get("portales"))


def ejecutar(raiz: Path, recolectores: dict[str, Callable[[], list]], ahora: datetime, git: bool = True,
             forzar: bool = False) -> dict:
    ruta = raiz / "data" / "pc" / f"{ahora.date().isoformat()}.json"
    if not forzar and _hoy_ya_bien(ruta):
        log.info("hoy ya hay datos buenos (%s): no se vuelve a consultar", ruta.name)
        if git and not subido(raiz, ruta):
            log.info("…pero no se llegó a subir: se sube ahora")
            subir(raiz, ruta)
        return {"escrito": False}
    portales: dict[str, list | dict] = {}
    for nombre, recoger in recolectores.items():
        try:
            # Se completa aquí porque la descripción no viaja en el JSON (diseño: nunca se guarda).
            portales[nombre] = [completar(p).a_dict() for p in recoger()]
            log.info("%s: %d anuncios", nombre, len(portales[nombre]))
        except PortalCaido as e:
            portales[nombre] = {"caido": e.motivo}
            log.warning("%s: %s", nombre, e.motivo)
        except Exception as e:  # noqa: BLE001 - un portal roto no impide subir el otro
            portales[nombre] = {"caido": f"error inesperado: {type(e).__name__}: {e}"}
            log.exception("%s: error inesperado", nombre)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps({"fecha": ahora.isoformat(), "portales": portales}, ensure_ascii=False, indent=1)
                    + "\n", encoding="utf-8")
    if git:
        subir(raiz, ruta)
    return {"escrito": True, "ruta": str(ruta)}


def _git(raiz: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(raiz), *args], capture_output=True, text=True)


def subido(raiz: Path, ruta: Path) -> bool:
    """El fichero está en origin/main tal cual (sin cambios locales)."""
    rel = ruta.relative_to(raiz).as_posix()
    _git(raiz, "fetch", "-q", "origin")
    limpio = _git(raiz, "status", "--porcelain", "--", rel).stdout.strip() == ""
    en_remoto = _git(raiz, "log", "-1", "--format=%H", "origin/main", "--", rel).stdout.strip() != ""
    return limpio and en_remoto


def relanzar_workflow(raiz: Path) -> None:
    subprocess.run(["gh", "workflow", "run", "diario.yml"], cwd=raiz, check=True)


def subir(raiz: Path, ruta: Path) -> None:
    """Commit SOLO del fichero del PC y push. --autostash: un cambio local sin guardar en el repositorio no
    impide subir (antes «You have unstaged changes» lo tumbaba en silencio: revisión final)."""
    rel = ruta.relative_to(raiz).as_posix()
    _git(raiz, "add", "--", rel)
    _git(raiz, "commit", "-q", "-m", f"datos PC: {ruta.stem}", "--", rel)
    for intento in range(3):
        if (_git(raiz, "pull", "--rebase", "--autostash", "-q", "origin", "main").returncode == 0
                and _git(raiz, "push", "-q", "origin", "HEAD:main").returncode == 0):
            break
        time.sleep(10)
    else:
        raise RuntimeError("no se pudo subir data/pc tras 3 intentos")
    relanzar_workflow(raiz)
    log.info("subido %s y relanzado el workflow", ruta.name)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seco", action="store_true")
    ap.add_argument("--forzar", action="store_true")
    ap.add_argument("--retraso", type=int, default=0, help="segundos de espera antes de empezar (al iniciar sesión)")
    a = ap.parse_args()
    time.sleep(a.retraso)
    registro = Path.home() / "AppData" / "Local" / "pisos-almeria" / "pc.log"
    registro.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        handlers=[logging.FileHandler(registro, encoding="utf-8"), logging.StreamHandler()])
    from .navegador import Navegador

    portales = [n for n in config.PORTALES_PC if n not in config.PORTALES_DESACTIVADOS]
    with Navegador(aviso=log.warning) as nav:
        recolectores = {n: (lambda m=importlib.import_module(f"pisos.portales.{n}"): m.recoger(nav.abrir))
                        for n in portales}
        r = ejecutar(RAIZ, recolectores, datetime.now().replace(microsecond=0), git=not a.seco, forzar=a.forzar)
    print(r)


if __name__ == "__main__":
    main()
