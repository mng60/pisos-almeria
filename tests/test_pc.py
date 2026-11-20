import json
from datetime import datetime
from pathlib import Path

from pisos import pc
from pisos.modelo import Piso
from pisos.portales import PortalCaido

AHORA = datetime(2026, 11, 21, 9, 0)


def _p(id_):
    return Piso(portal="idealista", id=id_, url="u", precio=650, habitaciones=2, banos=1, m2=60, planta=None,
                barrio="Zapillo", ascensor="si", descripcion="Plaza de garaje incluida")


def test_pc_seco_escribe_json(tmp_path):
    def caido():
        raise PortalCaido("navegador", "captcha sin resolver")

    r = pc.ejecutar(tmp_path, {"idealista": lambda: [_p("1")], "yaencontre": caido}, AHORA, git=False)
    d = json.loads((tmp_path / "data" / "pc" / "2026-11-21.json").read_text(encoding="utf-8"))
    assert d["fecha"] == "2026-11-21T09:00:00"
    piso = d["portales"]["idealista"][0]
    assert piso["zona"] == "Zapillo" and piso["garaje"] == "si"      # se completa antes de perder la descripción
    assert "descripcion" not in piso
    assert d["portales"]["yaencontre"] == {"caido": "captcha sin resolver"}
    assert r["escrito"]


def test_no_repite_el_mismo_dia_si_salio_bien(tmp_path):
    llamadas = []
    rec = {"idealista": lambda: llamadas.append(1) or [_p("1")]}
    pc.ejecutar(tmp_path, rec, AHORA, git=False)
    r = pc.ejecutar(tmp_path, rec, AHORA, git=False)
    assert llamadas == [1] and not r["escrito"]


def test_repite_si_hoy_fallo(tmp_path):
    def caido():
        raise PortalCaido("navegador", "captcha sin resolver")
    pc.ejecutar(tmp_path, {"idealista": caido}, AHORA, git=False)
    r = pc.ejecutar(tmp_path, {"idealista": lambda: [_p("1")]}, AHORA, git=False)
    assert r["escrito"]


def test_error_inesperado_no_rompe(tmp_path):
    def roto():
        raise ValueError("x")
    pc.ejecutar(tmp_path, {"idealista": roto, "yaencontre": lambda: []}, AHORA, git=False)
    d = json.loads((tmp_path / "data" / "pc" / "2026-11-21.json").read_text(encoding="utf-8"))
    assert "ValueError" in d["portales"]["idealista"]["caido"]
    assert d["portales"]["yaencontre"] == []


def test_servidor_lee_lo_que_escribe_el_pc(tmp_path):
    # Contrato entre las dos partes: el JSON del PC lo entiende servidor.datos_pc().
    from pisos.servidor import datos_pc
    pc.ejecutar(tmp_path, {"idealista": lambda: [_p("1")]}, AHORA, git=False)
    leidos = datos_pc(tmp_path / "data" / "pc", AHORA.date())
    assert [p.id for p in leidos["idealista"]] == ["1"]
