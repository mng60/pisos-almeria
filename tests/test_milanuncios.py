import json
from pathlib import Path

import pytest

from pisos.filtro import clasificar, completar
from pisos.portales import PortalCaido, milanuncios

FIX = Path(__file__).parent / "fixtures" / "milanuncios_listado.json"


def _pisos():
    return milanuncios.parsear(json.loads(FIX.read_text(encoding="utf-8")))


def test_parsear_cuenta_sin_demandas():
    # Volcado del 20/11/2026: 22 anuncios, 2 de ellos «Busco piso» (transaction=demand).
    ps = _pisos()
    assert len(ps) == 20
    assert not {"557896806", "621690278"} & {p.id for p in ps}


def test_parsear_campos():
    p = next(x for x in _pisos() if x.id == "619794489")
    assert p.precio == 600
    assert (p.habitaciones, p.banos) == (2, 1)
    assert p.barrio == "Zapillo - C. California"
    assert p.url == "https://www.milanuncios.com/alquiler-de-pisos-en-almeria-almeria/zapillo-c-california-619794489.htm"


def test_sin_ascensor_en_descripcion():
    p = completar(next(x for x in _pisos() if x.id == "619794489"))
    assert p.zona == "Zapillo" and p.ascensor == "no"
    assert clasificar(p) == "descartar"


def test_garaje_en_descripcion():
    # 626423392: «… – GARAJE INCLUIDO» solo en la descripción; «centro comercial» no es la zona Centro.
    p = completar(next(x for x in _pisos() if x.id == "626423392"))
    assert p.garaje == "si"
    assert p.zona is None


def test_formato_irreconocible():
    with pytest.raises(PortalCaido):
        milanuncios.parsear({"error": "x"})
