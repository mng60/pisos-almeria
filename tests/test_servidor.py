import json
from datetime import date, datetime, timedelta

from pisos.modelo import Piso
from pisos.portales import PortalCaido
from pisos.servidor import ejecutar

D1 = date(2026, 11, 21)
CRED = {"GMAIL_USUARIO": "rem@x.com", "GMAIL_CLAVE_APP": "clave", "CORREO_DESTINO": "belen@x.com",
        "CORREO_AVISOS": "miguel@x.com"}


def _p(id_, portal="fotocasa", **kw):
    base = dict(portal=portal, id=id_, url=f"https://{portal}/{id_}", precio=600, habitaciones=2, banos=1, m2=60,
                planta=None, barrio="Centro", ascensor="si", descripcion="Con plaza de garaje")
    base.update(kw)
    return Piso(**base)


def _correr(raiz, portales, n, entorno=CRED):
    enviados = []
    ejecutar(raiz, portales, D1 + timedelta(days=n), lambda msg: enviados.append(msg), entorno)
    return enviados


def test_ejecutar_extremo_a_extremo(tmp_path):
    ok = {"fotocasa": lambda s: [_p("1"), _p("2", precio=900)], "pisoscom": lambda s: [_p("7", "pisoscom", m2=61)]}
    env = _correr(tmp_path, ok, 0)
    assert [m["To"] for m in env] == ["belen@x.com"]
    assert "1 piso nuevo" in env[0]["Subject"]          # fotocasa:1 y pisoscom:7 son el mismo piso
    pagina = (tmp_path / "sitio" / "index.html").read_text(encoding="utf-8")
    assert "Ver en Fotocasa" in pagina and "Ver en pisos.com" in pagina
    assert "plaza de garaje" not in (tmp_path / "data" / "vistos.json").read_text(encoding="utf-8").lower()

    assert _correr(tmp_path, ok, 1) == []                # mismos datos: nada nuevo

    caido = dict(ok, fotocasa=lambda s: (_ for _ in ()).throw(PortalCaido("fotocasa", "HTTP 403")))
    assert _correr(tmp_path, caido, 2) == []             # primer día de fallo: aún no se avisa
    env = _correr(tmp_path, caido, 3)
    assert [m["To"] for m in env] == ["miguel@x.com"]
    assert "Fotocasa" in env[0]["Subject"]
    assert "Ver en Fotocasa" in (tmp_path / "sitio" / "index.html").read_text(encoding="utf-8")


def test_error_inesperado_de_un_portal_no_para_los_demas(tmp_path):
    def roto(s):
        raise KeyError("campo")
    env = _correr(tmp_path, {"fotocasa": roto, "pisoscom": lambda s: [_p("7", "pisoscom")]}, 0)
    assert len(env) == 1
    salud = json.loads((tmp_path / "data" / "salud.json").read_text(encoding="utf-8"))
    assert "KeyError" in salud["fotocasa"]["motivo"]


def test_sin_credenciales_no_envia(tmp_path, caplog):
    env = _correr(tmp_path, {"fotocasa": lambda s: [_p("1")]}, 0, entorno={})
    assert env == []
    assert "sin credenciales de correo" in caplog.text
    assert (tmp_path / "sitio" / "index.html").exists()


def test_datos_del_pc_recientes_cuentan(tmp_path):
    pc = tmp_path / "data" / "pc"
    pc.mkdir(parents=True)
    ahora = datetime(2026, 11, 21, 9, 0)
    (pc / "2026-11-21.json").write_text(json.dumps({
        "fecha": ahora.isoformat(),
        "portales": {"idealista": [_p("99", "idealista", precio=650).a_dict() | {"garaje": "si"}],
                     "yaencontre": {"caido": "captcha"}}}), encoding="utf-8")
    (pc / "2026-11-10.json").write_text(json.dumps({
        "fecha": "2026-11-10T09:00:00", "portales": {"idealista": [_p("viejo", "idealista").a_dict()]}}),
        encoding="utf-8")
    env = _correr(tmp_path, {}, 0)
    assert "Ver en Idealista" in env[0].get_body(("html",)).get_content()
    vistos = (tmp_path / "data" / "vistos.json").read_text(encoding="utf-8")
    assert "idealista:99" in vistos and "viejo" not in vistos
    salud = json.loads((tmp_path / "data" / "salud.json").read_text(encoding="utf-8"))
    assert salud["yaencontre"]["fallos_seguidos"] == 1


def test_forzar_aviso(tmp_path):
    env = _correr(tmp_path, {"fotocasa": lambda s: [_p("1")]}, 0, entorno=CRED | {"PISOS_FORZAR_AVISO": "1"})
    assert "miguel@x.com" in [m["To"] for m in env]
