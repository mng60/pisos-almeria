"""Una ficha que falla (404, captcha) no tira el portal entero: el piso se queda con los datos del listado.
Hallazgo de la revisión final (20/11/2026)."""
from pathlib import Path
from types import SimpleNamespace

from pisos.portales import PortalCaido, habitaclia, idealista, pisoscom

FIX = Path(__file__).parent / "fixtures"


def _falla_en_ficha(listado_url, html):
    def pedir(s, portal, url, **kw):
        if url == listado_url:
            return SimpleNamespace(text=html)
        if "/s/" in url or url.rstrip("/").split("/")[-1].isdigit():
            return SimpleNamespace(text="<html>ItemList Alquiler de pisos en</html>")
        raise PortalCaido(portal, "HTTP 404")
    return pedir


def test_habitaclia_ficha_404(monkeypatch):
    # VACUO con este volcado: ninguno de sus 13 anuncios es candidato (2 hab. en zona), así que no se abre
    # ninguna ficha. Se deja como protección de que el listado sigue leyéndose entero.
    html = (FIX / "habitaclia_listado.html").read_text(encoding="utf-8")
    monkeypatch.setattr(habitaclia, "pedir", _falla_en_ficha(habitaclia.LISTADO, html))
    monkeypatch.setattr(habitaclia, "PAUSA", 0)
    assert len(habitaclia.recoger(None)) == 13


def test_pisoscom_ficha_404(monkeypatch):
    html = (FIX / "pisoscom_listado.html").read_text(encoding="utf-8")
    monkeypatch.setattr(pisoscom, "pedir", _falla_en_ficha(pisoscom.LISTADO, html))
    monkeypatch.setattr(pisoscom, "PAUSA", 0)
    assert len(pisoscom.recoger(None)) == 30


def test_idealista_captcha_en_ficha():
    listado = (FIX / "idealista_listado.html").read_text(encoding="utf-8")

    def abrir(url):
        if "/inmueble/" in url:
            raise PortalCaido("navegador", "captcha sin resolver")
        return listado
    assert len(idealista.recoger(abrir)) == 12
