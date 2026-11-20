"""Un módulo por portal. Cada uno expone NOMBRE, parsear(respuesta) -> list[Piso] (puro) y recoger(...)."""
from __future__ import annotations

import re

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
MAX_PAGINAS = 10
PAUSA = 1.0


class PortalCaido(Exception):
    """El portal bloquea, falla o cambió de formato. Sus pisos no cuentan como ausentes ese día."""

    def __init__(self, portal: str, motivo: str):
        super().__init__(f"{portal}: {motivo}")
        self.portal = portal
        self.motivo = motivo


def sesion() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "es-ES,es;q=0.9"})
    return s


def pedir(s: requests.Session, portal: str, url: str, **kw) -> requests.Response:
    """GET que convierte bloqueos y errores en PortalCaido."""
    try:
        r = s.get(url, timeout=30, **kw)
    except requests.RequestException as e:
        raise PortalCaido(portal, f"error de red: {type(e).__name__}") from e
    if r.status_code != 200:
        raise PortalCaido(portal, f"HTTP {r.status_code}")
    if re.search(r"captcha|datadome", r.text[:5000], re.I) and len(r.content) < 20000:
        raise PortalCaido(portal, "captcha")
    return r


def entero(v) -> int | None:
    if v is None:
        return None
    m = re.search(r"\d+", str(v))
    return int(m.group()) if m else None
