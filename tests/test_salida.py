from datetime import datetime

from pisos.correo import asunto_belen, correo_avisos, correo_belen
from pisos.duplicados import agrupar
from pisos.modelo import Piso
from pisos.pagina import generar_pagina

AHORA = datetime(2026, 11, 21, 8, 0)


def _p(id_="1", **kw):
    base = dict(portal="fotocasa", id=id_, url=f"https://www.fotocasa.es/{id_}", precio=600, habitaciones=2,
                banos=1, m2=60, planta="3ª planta", barrio="Centro", zona="Centro", garaje="si", ascensor="si")
    base.update(kw)
    return Piso(**base)


def _grupos():
    return agrupar([_p("1"), _p("2", precio=650, garaje=None, zona="Zapillo", barrio="El Zapillo")])


def test_pagina_noindex():
    assert '<meta name="robots" content="noindex' in generar_pagina(_grupos(), {}, AHORA, {})


def test_pagina_dos_apartados():
    h = generar_pagina(_grupos(), {}, AHORA, {})
    assert h.index("Cumple todo") < h.index("Por confirmar")
    assert "garaje sin confirmar" in h


def test_pagina_escapa_html():
    h = generar_pagina(agrupar([_p(barrio="<script>alert(1)</script>")]), {}, AHORA, {})
    assert "<script>alert" not in h and "&lt;script&gt;" in h


def test_pagina_vacia_lo_dice():
    assert "Ahora mismo no hay ningún piso" in generar_pagina([], {}, AHORA, {})


def test_pagina_visto_desde():
    estado = {"fotocasa:1": {"primera_vez": "2026-11-19"}}
    assert "desde el 19/11" in generar_pagina(agrupar([_p("1")]), estado, AHORA, {})


def test_correo_none_sin_nuevos():
    assert correo_belen([], "a@b.c", "d@e.f") is None


def test_correo_belen_no_menciona_fallos():
    msg = correo_belen(_grupos(), "rem@x.com", "belen@x.com")
    cuerpo = msg.get_body(("html",)).get_content()
    assert "fall" not in cuerpo.lower() and "caído" not in cuerpo.lower()
    assert msg["To"] == "belen@x.com" and msg["From"] == "rem@x.com"


def test_asunto():
    assert asunto_belen(_grupos()) == "🏠 2 pisos nuevos en Almería (1 cumple todo)"
    assert asunto_belen(_grupos()[:1]) == "🏠 1 piso nuevo en Almería (1 cumple todo)"


def test_correo_avisos_nombra_portal_y_dias():
    salud = {"fotocasa": {"fallos_seguidos": 2, "motivo": "HTTP 403", "ultimo_ok": "2026-11-19"}}
    msg = correo_avisos(["fotocasa"], salud, "rem@x.com", "miguel@x.com")
    texto = msg.get_body(("plain",)).get_content()
    assert "fotocasa" in texto and "2 días" in texto and "HTTP 403" in texto
    assert correo_avisos([], salud, "rem@x.com", "miguel@x.com") is None
