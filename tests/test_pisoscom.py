from pathlib import Path

import pytest

from pisos.filtro import completar, zona_de
from pisos.portales import PortalCaido, pisoscom

FIX = Path(__file__).parent / "fixtures"


def _listado():
    return pisoscom.parsear((FIX / "pisoscom_listado.html").read_text(encoding="utf-8"))


def _ficha():
    return pisoscom.parsear_ficha((FIX / "pisoscom_ficha.html").read_text(encoding="utf-8"))


def test_parsear_cuenta():
    assert len(_listado()) == 30   # volcado del 20/11/2026: 30 .ad-preview en la página 1


def test_parsear_campos_primer_anuncio():
    p = _listado()[0]
    assert p.precio == 700
    assert (p.habitaciones, p.banos, p.m2, p.planta) == (2, 1, 142, "1ª planta")
    assert p.barrio == "Plaza de Toros-Santa Rita"
    assert p.url == "https://www.pisos.com/alquilar/piso-plaza_de_toros_santa_rita04008-67506183135_106100/"
    assert p.id == "67506183135_106100"
    assert p.foto.startswith("https://fotos.imghs.net/")


def test_zonas_de_pisoscom():
    assert zona_de("pisoscom", "Ciudad Jardín-Tagarete-Zapillo") == "Zapillo"
    assert zona_de("pisoscom", "Oliveros-Altamira-Barrio Alto") == "Oliveros / Altamira"
    assert zona_de("pisoscom", "Nueva Almería-Cortijo Grande-Vega de Acá") == "Vega de Acá"


def test_ficha_ascensor_y_descripcion():
    f = _ficha()
    assert f["ascensor"] == "si"
    assert f["garaje"] is None
    assert f["descripcion"].startswith("Descubre este amplio y luminoso piso")


def test_garaje_en_descripcion():
    # Anuncio real del listado (Retamar, 700 €): «Piso con muebles y plaza de garaje.» solo en el texto.
    p = next(x for x in _listado() if x.barrio == "Retamar" and x.banos == 2)
    p.descripcion = "Piso con muebles y plaza de garaje. Disponible curso escolar."
    assert completar(p).garaje == "si"


def test_etiqueta_garaje_en_ficha():
    html = ('<div class="description__content">Texto</div>'
            '<span class="features__label">Garaje privado</span>')
    assert pisoscom.parsear_ficha(html)["garaje"] == "si"


def test_pagina_ajena_es_portal_caido():
    with pytest.raises(PortalCaido):
        pisoscom.parsear("<html><body>Mantenimiento</body></html>")
