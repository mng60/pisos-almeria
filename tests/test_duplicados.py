from pisos.duplicados import agrupar
from pisos.filtro import clasificar
from pisos.modelo import Piso


def _p(portal, id_, m2=60, **kw):
    base = dict(portal=portal, id=id_, url=f"https://{portal}/{id_}", precio=600, habitaciones=2, banos=1,
                m2=m2, planta=None, barrio="Centro", zona="Centro")
    base.update(kw)
    return Piso(**base)


def test_m2_60_y_62_un_grupo():
    g = agrupar([_p("fotocasa", "1", 60), _p("pisoscom", "2", 62)])
    assert len(g) == 1
    assert {e[0] for e in g[0].enlaces} == {"fotocasa", "pisoscom"}


def test_m2_60_y_70_dos_grupos():
    assert len(agrupar([_p("fotocasa", "1", 60), _p("pisoscom", "2", 70)])) == 2


def test_m2_limite_3():
    assert len(agrupar([_p("fotocasa", "1", 60), _p("pisoscom", "2", 63)])) == 1
    assert len(agrupar([_p("fotocasa", "1", 60), _p("pisoscom", "2", 64)])) == 2


def test_m2_desconocido_agrupa():
    assert len(agrupar([_p("fotocasa", "1", 60), _p("milanuncios", "2", None)])) == 1


def test_precio_distinto_no_agrupa():
    assert len(agrupar([_p("fotocasa", "1"), _p("pisoscom", "2", precio=650)])) == 2


def test_mismo_portal_no_agrupa():
    # Dos anuncios del mismo portal son dos pisos (p. ej. dos puertas del mismo edificio).
    assert len(agrupar([_p("fotocasa", "1"), _p("fotocasa", "2")])) == 2


def test_fusion_completa_datos():
    # Un portal da el ascensor y otro el garaje: juntos cumplen todo.
    g = agrupar([_p("fotocasa", "1", ascensor="si"), _p("pisoscom", "2", garaje="si", foto="https://f")])
    assert (g[0].principal.garaje, g[0].principal.ascensor, g[0].principal.foto) == ("si", "si", "https://f")
    assert clasificar(g[0].principal) == "cumple"


def test_fusion_un_no_gana():
    g = agrupar([_p("fotocasa", "1", ascensor="si"), _p("pisoscom", "2", ascensor="no")])
    assert g[0].principal.ascensor == "no"
