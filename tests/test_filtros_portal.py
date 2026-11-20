"""Los filtros que se piden a cada portal, medidos el 20/11/2026 aplicándolos a mano en la web (Chrome):
pedir de más son visitas de más, y en Idealista y yaencontre cada visita arriesga un captcha."""
import re
from pathlib import Path
from types import SimpleNamespace

from pisos.portales import milanuncios, pisoscom, yaencontre

FIX = Path(__file__).parent / "fixtures"


def test_yaencontre_pide_dos_habitaciones_y_precio():
    # Medido: 200 → 5 resultados en Almería ciudad.
    assert yaencontre.LISTADO == ("https://www.yaencontre.com/alquiler/pisos/almeria/distrito-almeria-ciudad/"
                                  "f-2-habitaciones,500-700euros")


def test_pisoscom_pide_dos_habitaciones_y_precio():
    # Medido: 37 → 23 resultados; el orden de los tramos importa (habitaciones antes que precio).
    assert pisoscom.LISTADO == "https://www.pisos.com/alquiler/pisos-almeria_capital/con-2-habitaciones/desde-500/hasta-700/"


def test_milanuncios_pide_dos_dormitorios():
    # Medido: 22 → 6 anuncios, todos de 2 dormitorios. Los baños no se filtran: perdería los que no lo dicen.
    assert milanuncios.PARAMS["bedroomsFrom"] == milanuncios.PARAMS["bedroomsTo"] == 2
    assert "bathroomsFrom" not in milanuncios.PARAMS


def test_pisoscom_total_declarado():
    assert pisoscom.total_declarado((FIX / "pisoscom_listado.html").read_text(encoding="utf-8")) == 37
    assert pisoscom.total_declarado("<html>nada</html>") is None


def test_pisoscom_no_lee_sugerencias_tras_el_total(monkeypatch):
    # pisos.com añade «sugerencias» (más caras) después de los resultados: se corta en el total declarado.
    html = (FIX / "pisoscom_listado.html").read_text(encoding="utf-8")
    html10 = re.sub(r"\b37 resultados", "10 resultados", html)
    vacio = "<html>Alquiler de pisos en Almería Capital</html>"
    monkeypatch.setattr(pisoscom, "pedir", lambda s, portal, url, **kw: SimpleNamespace(
        text=html10 if url == pisoscom.LISTADO else vacio))
    monkeypatch.setattr(pisoscom, "parsear_ficha", lambda h: {"descripcion": None, "ascensor": None, "garaje": None})
    assert len(pisoscom.recoger(None)) == 10
