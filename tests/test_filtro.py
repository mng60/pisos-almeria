from pisos.filtro import clasificar, completar, zona_de
from pisos.modelo import Piso


def _p(**kw):
    base = dict(portal="fotocasa", id="1", url="https://x", precio=600, habitaciones=2, banos=1, m2=70,
                planta="3", barrio="Centro", garaje="si", ascensor="si")
    base.update(kw)
    return completar(Piso(**base))


def test_zona_agrupada_entra():
    assert zona_de("fotocasa", "Ciudad Jardín - Tagarete - El Zapillo") == "Zapillo"
    assert zona_de("fotocasa", "Nueva Almería - Cortijo Grande - Vega de Acá") == "Vega de Acá"


def test_zona_que_junta_dos():
    assert zona_de("fotocasa", "Oliveros - Altamira") == "Oliveros / Altamira"


def test_barrio_fuera_es_none():
    assert zona_de("fotocasa", "Retamar") is None
    assert zona_de("fotocasa", None) is None


def test_tabla_por_portal_gana():
    # Un barrio que no contiene el nombre de la zona se resuelve con config.BARRIOS.
    from pisos import config
    config.BARRIOS.setdefault("prueba", {})["Paseo de Almería"] = "Centro"
    assert zona_de("prueba", "paseo de almeria") == "Centro"


def test_cumple_todo():
    assert clasificar(_p()) == "cumple"


def test_sin_dato_garaje_es_confirmar():
    assert clasificar(_p(garaje=None)) == "confirmar"


def test_sin_dato_ascensor_es_confirmar():
    assert clasificar(_p(ascensor=None)) == "confirmar"


def test_sin_ascensor_es_descartar():
    assert clasificar(_p(ascensor="no")) == "descartar"


def test_sin_garaje_es_descartar():
    assert clasificar(_p(garaje="no")) == "descartar"


def test_precio_limites():
    assert clasificar(_p(precio=500)) == "cumple"
    assert clasificar(_p(precio=700)) == "cumple"
    assert clasificar(_p(precio=499)) == "descartar"
    assert clasificar(_p(precio=701)) == "descartar"


def test_tres_habitaciones_descarta():
    assert clasificar(_p(habitaciones=3)) == "descartar"


def test_habitaciones_desconocidas_descarta():
    assert clasificar(_p(habitaciones=None)) == "descartar"


def test_banos_desconocido_es_confirmar():
    assert clasificar(_p(banos=None)) == "confirmar"


def test_dos_banos_descarta():
    assert clasificar(_p(banos=2)) == "descartar"


def test_fuera_de_zona_descarta():
    assert clasificar(_p(barrio="Retamar")) == "descartar"


def test_completar_lee_garaje_de_descripcion():
    p = _p(garaje=None, descripcion="Bonito piso con plaza de garaje incluida")
    assert p.garaje == "si"


def test_completar_no_pisa_dato_del_portal():
    p = _p(garaje="si", ascensor="si", descripcion="")
    assert (p.garaje, p.ascensor) == ("si", "si")


def test_descripcion_negativa_gana_a_sin_dato():
    p = _p(ascensor=None, descripcion="Tercero sin ascensor")
    assert p.ascensor == "no"
    assert clasificar(p) == "descartar"
