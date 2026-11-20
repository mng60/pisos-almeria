"""Edge visible con un perfil propio, que espera a que una persona resuelva el captcha.

Idealista y yaencontre bloquean con captcha (DataDome) a los scripts, también a un Edge visible tras unas pocas
visitas (medido el 20/11/2026). Con un perfil persistente, la cookie del captcha resuelto se guarda y las visitas
de los días siguientes suelen pasar. Si sale el captcha, la ventana se queda abierta, se pone delante y se espera
hasta ESPERA_CAPTCHA segundos a que alguien lo resuelva (Miguel, 20/11/2026: «ábrelos y espera a que acepte»).
"""
from __future__ import annotations

import os
import random
import re
import time
from pathlib import Path

from .portales import PortalCaido

PERFIL = Path(os.path.expandvars(r"%LOCALAPPDATA%")) / "pisos-almeria" / "perfil-edge"
CAPTCHA = re.compile(r"captcha-delivery|geo\.captcha")
ESPERA_CAPTCHA = 15 * 60
PAUSA = (4.0, 8.0)   # segundos entre visitas, al azar, para no parecer un robot


def hay_captcha(html: str) -> bool:
    return bool(CAPTCHA.search(html)) and len(html) < 50000


class Navegador:
    def __init__(self, espera: int = ESPERA_CAPTCHA, aviso=print):
        self.espera = espera
        self.aviso = aviso
        self._primera = True

    def __enter__(self) -> "Navegador":
        from playwright.sync_api import sync_playwright

        PERFIL.mkdir(parents=True, exist_ok=True)
        self._pw = sync_playwright().start()
        self._ctx = self._pw.chromium.launch_persistent_context(
            str(PERFIL), channel="msedge", headless=False, locale="es-ES", viewport=None,
            args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
            ignore_default_args=["--enable-automation"])
        self._pg = self._ctx.pages[0] if self._ctx.pages else self._ctx.new_page()
        return self

    def __exit__(self, *exc) -> None:
        self._ctx.close()
        self._pw.stop()

    def abrir(self, url: str) -> str:
        if not self._primera:
            time.sleep(random.uniform(*PAUSA))
        self._primera = False
        self._pg.goto(url, timeout=60000)
        self._pg.wait_for_timeout(2500)
        html = self._pg.content()
        if hay_captcha(html):
            self._pg.bring_to_front()
            self.aviso("Pisos Almería: resuelve el captcha en la ventana de Edge (espero "
                       f"{self.espera // 60} min).")
            fin = time.time() + self.espera
            while hay_captcha(html) and time.time() < fin:
                self._pg.wait_for_timeout(5000)
                html = self._pg.content()
            if hay_captcha(html):
                raise PortalCaido("navegador", "captcha sin resolver")
            self._pg.wait_for_timeout(2500)
            html = self._pg.content()
        return html
