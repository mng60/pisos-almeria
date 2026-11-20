import pytest

from pisos.modelo import Piso
from pisos.texto import detectar_ascensor, detectar_garaje, leer_precio


@pytest.mark.parametrize("t,esperado", [
    ("Plaza de garaje incluida en el precio", ("si", None)),
    ("Garaje opcional por 50 €", ("si", "opcional 50 €")),
    ("Piso sin garaje, bien comunicado", ("no", None)),
    ("Zona fácil de aparcar", (None, None)),
    ("Incluye plaza de aparcamiento en sótano", ("si", None)),
    ("PARKING comunitario", ("si", None)),
    ("No dispone de plaza de garaje", ("no", None)),
    ("Posibilidad de alquilar plaza de garaje", ("si", "opcional")),
    ("Reformado, no fumadores. Garaje incluido", ("si", None)),
    ("Se alquila sin muebles y con garaje", ("si", None)),
    # Textos reales de Fotocasa (anuncio 190946960, 20/11/2026): aparcar en la calle no es garaje.
    ("• Fácil aparcamiento en la calle.", (None, None)),
    ("• Easy street parking available.", (None, None)),
    ("Zona con parking público cerca", (None, None)),
    (None, (None, None)),
])
def test_detectar_garaje(t, esperado):
    assert detectar_garaje(t) == esperado


@pytest.mark.parametrize("t,esperado", [
    ("Edificio con ascensor", "si"),
    ("Sin ascensor", "no"),
    ("cuarta planta sin ascensor", "no"),
    ("Exterior y luminoso", None),
    ("Finca con dos ascensores", "si"),
])
def test_detectar_ascensor(t, esperado):
    assert detectar_ascensor(t) == esperado


@pytest.mark.parametrize("t,esperado", [
    ("1.200 €/mes", 1200),
    ("650€", 650),
    ("650 € + gastos", 650),
    ("Consultar", None),
    ("", None),
])
def test_leer_precio(t, esperado):
    assert leer_precio(t) == esperado


def _piso(**kw):
    base = dict(portal="fotocasa", id="1", url="https://x", precio=600, habitaciones=2, banos=1,
                m2=70, planta="3", barrio="Centro")
    base.update(kw)
    return Piso(**base)


def test_a_dict_no_lleva_descripcion():
    d = _piso(descripcion="texto privado").a_dict()
    assert "descripcion" not in d
    assert d["precio"] == 600


def test_ida_y_vuelta():
    p = _piso(garaje="si", nota_garaje="opcional", ascensor="no", foto="https://f")
    assert Piso.de_dict(p.a_dict()) == p
