import json
from pathlib import Path

import pytest

from pisos.filtro import clasificar, completar
from pisos.portales import PortalCaido, fotocasa

FIX = Path(__file__).parent / "fixtures" / "fotocasa_listado.json"


def _pisos():
    return fotocasa.parsear(json.loads(FIX.read_text(encoding="utf-8")))


def test_parsear_cuenta():
    assert len(_pisos()) == 8   # volcado del 20/11/2026: 8 realEstates


def test_parsear_campos_primer_anuncio():
    p = _pisos()[0]
    assert p.id == "191151501"
    assert p.precio == 600
    assert (p.habitaciones, p.banos, p.m2) == (2, 1, 60)
    assert p.barrio == "Ciudad Jardín - Tagarete - El Zapillo"
    assert p.url == "https://www.fotocasa.es/es/alquiler/vivienda/almeria-capital/calefaccion-amueblado/191151501/d"
    assert p.foto.startswith("https://static.fotocasa.es/")
    assert p.ascensor is None          # sin clave elevator: el portal no lo dice
    assert p.planta is None            # floor es un código, no la planta (ver fotocasa.py)


def test_ascensor_del_portal():
    p = next(x for x in _pisos() if x.id == "183685580")
    assert p.ascensor == "si"


def test_garaje_en_descripcion():
    # 183675216: el garaje solo sale en la descripción («piscina, plaza de garaje, gastos…»).
    p = completar(next(x for x in _pisos() if x.id == "183675216"))
    assert p.garaje == "si"


def test_sin_ascensor_en_descripcion_descarta():
    # 191151501, Zapillo: «Es una 3ª planta sin ascensor».
    p = completar(_pisos()[0])
    assert p.zona == "Zapillo" and p.ascensor == "no"
    assert clasificar(p) == "descartar"


def test_formato_irreconocible_es_portal_caido():
    with pytest.raises(PortalCaido):
        fotocasa.parsear({"otra": "cosa"})
