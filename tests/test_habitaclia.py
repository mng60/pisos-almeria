from pathlib import Path

import pytest

from pisos.filtro import completar
from pisos.portales import PortalCaido, habitaclia

FIX = Path(__file__).parent / "fixtures"


def _listado():
    return habitaclia.parsear((FIX / "habitaclia_listado.html").read_text(encoding="utf-8"))


def test_parsear_cuenta():
    assert len(_listado()) == 13   # volcado del 20/11/2026: 13 <article>


def test_parsear_campos_primer_anuncio():
    p = _listado()[0]
    assert p.precio == 700
    assert (p.habitaciones, p.banos, p.m2) == (3, 3, 125)
    assert p.barrio == "El Toyo"
    assert p.url.startswith("https://www.habitaclia.com/alquiler/") and p.url.endswith("/d")
    assert p.foto and p.foto.startswith("https://")


def test_barrio_desde_el_titulo():
    # «Piso con terraza en alquiler en Retamar | Almería Capital, Almería»: el barrio va en el título.
    p = next(x for x in _listado() if x.precio == 550)
    assert p.barrio == "Retamar"


def test_ficha_descripcion_y_garaje():
    ficha = habitaclia.parsear_ficha((FIX / "habitaclia_ficha.html").read_text(encoding="utf-8"))
    assert ficha["descripcion"].startswith("Piso con muebles en alquiler.")
    assert "plaza de garaje" in ficha["descripcion"]
    assert ficha["ascensor"] is None      # la ficha no lista ascensor


def test_garaje_en_descripcion():
    p = next(x for x in _listado() if x.precio == 550)
    ficha = habitaclia.parsear_ficha((FIX / "habitaclia_ficha.html").read_text(encoding="utf-8"))
    p.descripcion = ficha["descripcion"]
    assert completar(p).garaje == "si"


@pytest.mark.parametrize("valor,esperado", [("Sí", "si"), ("No", "no")])
def test_caracteristica_ascensor(valor, esperado):
    html = (f"<h2>Características del inmueble</h2><div><span>Ascensor</span><span>{valor}</span></div>"
            "<h2>Descripción</h2><div>Texto</div>")
    assert habitaclia.parsear_ficha(html)["ascensor"] == esperado


def test_sin_articulos_ni_aviso_es_portal_caido():
    with pytest.raises(PortalCaido):
        habitaclia.parsear("<html><body>Algo distinto</body></html>")
