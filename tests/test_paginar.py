from pisos.modelo import Piso
from pisos.portales import paginar


def _p(i):
    return Piso(portal="x", id=str(i), url="u", precio=600, habitaciones=2, banos=1, m2=60, planta=None, barrio=None)


def test_para_si_la_pagina_repite_la_anterior():
    # Habitaclia (20/11/2026): con filtros, /s/2 devuelve otra vez la página 1.
    pedidas = []
    def obtener(n):
        pedidas.append(n)
        return [_p(1), _p(2)]
    assert [p.id for p in paginar(obtener)] == ["1", "2"]
    assert pedidas == [1, 2]


def test_para_en_pagina_vacia():
    paginas = {1: [_p(1)], 2: [_p(2)], 3: []}
    assert [p.id for p in paginar(lambda n: paginas[n])] == ["1", "2"]


def test_tope_de_paginas():
    assert len(paginar(lambda n: [_p(n)], maximo=4)) == 4
