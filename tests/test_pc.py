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


def _repo_con_remoto(tmp_path):
    import subprocess
    remoto, local = tmp_path / "remoto.git", tmp_path / "local"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remoto)], check=True)
    subprocess.run(["git", "clone", "-q", str(remoto), str(local)], check=True, capture_output=True)
    for k, v in (("user.name", "t"), ("user.email", "t@t"), ("commit.gpgsign", "false")):
        subprocess.run(["git", "-C", str(local), "config", k, v], check=True)
    (local / "README.md").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(local), "add", "."], check=True)
    subprocess.run(["git", "-C", str(local), "commit", "-q", "-m", "inicio"], check=True)
    subprocess.run(["git", "-C", str(local), "push", "-q", "-u", "origin", "main"], check=True, capture_output=True)
    return local


def test_sube_con_arbol_sucio_y_lo_pendiente_se_reintenta(tmp_path, monkeypatch):
    # Revisión final: con un cambio sin guardar, pull --rebase fallaba y el día se daba por bueno sin subir.
    local = _repo_con_remoto(tmp_path)
    (local / "README.md").write_text("cambio local sin commitear\n", encoding="utf-8")
    disparos = []
    monkeypatch.setattr(pc, "relanzar_workflow", lambda raiz: disparos.append(raiz))
    r = pc.ejecutar(local, {"idealista": lambda: [_p("1")]}, AHORA, git=True)
    assert r["escrito"] and pc.subido(local, local / "data" / "pc" / "2026-11-21.json")
    assert disparos == [local]
    assert (local / "README.md").read_text(encoding="utf-8") == "cambio local sin commitear\n"


def test_fichero_de_hoy_sin_subir_se_sube_en_la_siguiente(tmp_path, monkeypatch):
    local = _repo_con_remoto(tmp_path)
    monkeypatch.setattr(pc, "relanzar_workflow", lambda raiz: None)
    pc.ejecutar(local, {"idealista": lambda: [_p("1")]}, AHORA, git=False)   # escrito, no subido
    ruta = local / "data" / "pc" / "2026-11-21.json"
    assert not pc.subido(local, ruta)
    llamadas = []
    pc.ejecutar(local, {"idealista": lambda: llamadas.append(1) or []}, AHORA, git=True)
    assert llamadas == []              # no vuelve a visitar los portales…
    assert pc.subido(local, ruta)      # …pero sí sube lo pendiente


def test_servidor_lee_lo_que_escribe_el_pc(tmp_path):
    # Contrato entre las dos partes: el JSON del PC lo entiende servidor.datos_pc().
    from pisos.servidor import datos_pc
    pc.ejecutar(tmp_path, {"idealista": lambda: [_p("1")]}, AHORA, git=False)
    leidos = datos_pc(tmp_path / "data" / "pc", AHORA.date())
    assert [p.id for p in leidos["idealista"]] == ["1"]
