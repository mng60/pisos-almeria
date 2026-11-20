import json
from datetime import date, timedelta

from pisos.estado import actualizar, cargar, guardar, clave
from pisos.modelo import Piso
from pisos.portales import PortalCaido

D1 = date(2026, 11, 21)


def _p(id_="1", portal="fotocasa", **kw):
    base = dict(portal=portal, id=id_, url="u", precio=600, habitaciones=2, banos=1, m2=60, planta=None,
                barrio="Centro", zona="Centro", garaje=None, ascensor="si")
    base.update(kw)
    return Piso(**base)


def _dia(estado, salud, recogidos, n):
    return actualizar(estado, salud, recogidos, D1 + timedelta(days=n))


def test_nuevo_solo_una_vez():
    e, s = {}, {}
    nuevos, _ = _dia(e, s, {"fotocasa": [_p()]}, 0)
    assert [p.id for p in nuevos] == ["1"]
    nuevos, _ = _dia(e, s, {"fotocasa": [_p()]}, 1)
    assert nuevos == []


def test_descartado_no_es_nuevo_ni_se_guarda():
    e, s = {}, {}
    nuevos, _ = _dia(e, s, {"fotocasa": [_p(precio=900)]}, 0)
    assert nuevos == [] and e == {}


def test_retirado_tras_3_ausencias():
    e, s = {}, {}
    _dia(e, s, {"fotocasa": [_p("1"), _p("2")]}, 0)
    for n in (1, 2):
        _dia(e, s, {"fotocasa": [_p("2")]}, n)
        assert clave(_p("1")) in e
    _dia(e, s, {"fotocasa": [_p("2")]}, 3)
    assert clave(_p("1")) not in e


def test_varias_ejecuciones_el_mismo_dia_cuentan_una():
    # El PC dispara el workflow además del cron: dos pasadas el mismo día son una ausencia.
    e, s = {}, {}
    _dia(e, s, {"fotocasa": [_p("1"), _p("2")]}, 0)
    for _ in range(5):
        _dia(e, s, {"fotocasa": [_p("2")]}, 1)
    assert e[clave(_p("1"))]["ausencias"] == 1


def test_portal_caido_no_retira_ni_renueva():
    e, s = {}, {}
    _dia(e, s, {"fotocasa": [_p()]}, 0)
    for n in (1, 2, 3):
        _dia(e, s, {"fotocasa": PortalCaido("fotocasa", "HTTP 403")}, n)
    assert clave(_p()) in e
    nuevos, _ = _dia(e, s, {"fotocasa": [_p()]}, 4)
    assert nuevos == []


def test_cero_resultados_cuenta_como_fallo():
    e, s = {}, {}
    _dia(e, s, {"fotocasa": [_p()]}, 0)
    _dia(e, s, {"fotocasa": []}, 1)
    assert s["fotocasa"]["fallos_seguidos"] == 1
    assert e[clave(_p())]["ausencias"] == 0


def test_aviso_al_segundo_dia_y_una_vez():
    e, s = {}, {}
    caido = {"fotocasa": PortalCaido("fotocasa", "captcha")}
    assert _dia(e, s, caido, 0)[1] == []
    assert _dia(e, s, caido, 1)[1] == ["fotocasa"]
    assert _dia(e, s, caido, 1)[1] == []          # misma fecha: no se repite
    assert _dia(e, s, caido, 2)[1] == []
    assert _dia(e, s, {"fotocasa": [_p()]}, 3)[1] == []
    assert s["fotocasa"]["fallos_seguidos"] == 0


def test_aviso_se_repite_cada_7_dias():
    e, s = {}, {}
    caido = {"fotocasa": PortalCaido("fotocasa", "captcha")}
    avisos = [n for n in range(20) if _dia(e, s, caido, n)[1]]
    assert avisos == [1, 8, 15]


def test_portal_no_consultado_no_cuenta():
    # Idealista solo llega cuando el PC está encendido: si no viene, ni ausencias ni fallos.
    e, s = {}, {}
    _dia(e, s, {"idealista": [_p("9", "idealista")]}, 0)
    for n in (1, 2, 3, 4):
        _dia(e, s, {"fotocasa": [_p()]}, n)
    assert clave(_p("9", "idealista")) in e
    assert s["idealista"]["fallos_seguidos"] == 0


def test_guardar_no_lleva_descripcion(tmp_path):
    e, s = {}, {}
    _dia(e, s, {"fotocasa": [_p(descripcion="texto privado")]}, 0)
    ruta = tmp_path / "vistos.json"
    guardar(ruta, e)
    assert "texto privado" not in ruta.read_text(encoding="utf-8")
    assert cargar(ruta) == json.loads(ruta.read_text(encoding="utf-8"))
    assert cargar(tmp_path / "no-existe.json") == {}
