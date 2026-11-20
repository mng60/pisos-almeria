"""Idealista y yaencontre (parte del PC), contra volcados reales hechos con Edge visible el 20/11/2026."""
from pathlib import Path

import pytest

from pisos.filtro import clasificar, completar
from pisos.portales import PortalCaido, idealista, yaencontre

FIX = Path(__file__).parent / "fixtures"


def _leer(nombre):
    return (FIX / nombre).read_text(encoding="utf-8")


# ---------- Idealista ----------

def test_idealista_cuenta():
    assert len(idealista.parsear(_leer("idealista_listado.html"))) == 12


def test_idealista_primer_anuncio():
    p = idealista.parsear(_leer("idealista_listado.html"))[0]
    assert (p.id, p.precio, p.habitaciones, p.m2) == ("110123388", 600, 2, 70)
    assert p.barrio == "Zapillo"
    assert p.ascensor == "no"                      # «1ª planta exterior sin ascensor»
    assert p.url == "https://www.idealista.com/inmueble/110123388/"
    assert p.foto.startswith("https://img4.idealista.com/")


def test_idealista_garaje_incluido_en_listado():
    p = next(x for x in idealista.parsear(_leer("idealista_listado.html")) if x.id == "98422847")
    assert (p.garaje, p.ascensor, p.barrio) == ("si", "si", "Retamar")


def test_idealista_barrio_compuesto():
    p = next(x for x in idealista.parsear(_leer("idealista_listado.html")) if x.id == "99141095")
    assert completar(p).zona == "Oliveros / Altamira"


def test_idealista_ficha():
    f = idealista.parsear_ficha(_leer("idealista_ficha.html"))
    assert f["descripcion"].startswith("Vivienda disponible hasta junio.")
    assert "Sin ascensor" in f["descripcion"]       # las características van al texto que se analiza
    assert f["banos"] == 1


def test_idealista_garaje_en_descripcion_de_ficha():
    p = next(x for x in idealista.parsear(_leer("idealista_listado.html")) if x.id == "109485526")
    p.descripcion = "Piso reformado en el centro. Plaza de garaje por 60 €/mes adicionales."
    p = completar(p)
    assert (p.zona, p.garaje, p.nota_garaje, p.ascensor) == ("Centro", "si", "opcional 60 €", "si")


def test_idealista_captcha_es_portal_caido():
    with pytest.raises(PortalCaido):
        idealista.parsear('<html><script src="https://ct.captcha-delivery.com/c.js"></script></html>')


# ---------- yaencontre ----------

def test_yaencontre_cuenta():
    # 43 <article>, pero uno es publicidad («Encuentra tu vivienda con tranquilidad»): 42 pisos.
    assert len(yaencontre.parsear(_leer("yaencontre_listado.html"))) == 42


def test_yaencontre_primer_anuncio():
    p = yaencontre.parsear(_leer("yaencontre_listado.html"))[0]
    assert (p.id, p.precio, p.habitaciones, p.banos, p.m2) == ("87437-113082873", 850, 3, 2, 155)
    assert p.barrio == "Retamar"
    assert p.planta == "Planta 2ª"
    assert p.url == "https://www.yaencontre.com/alquiler/piso/inmueble-87437-113082873"


def test_yaencontre_ficha_etiquetas():
    f = yaencontre.parsear_ficha(_leer("yaencontre_ficha.html"))
    assert (f["ascensor"], f["garaje"]) == ("si", "si")
    assert f["descripcion"].startswith("Magnifico piso en alquiler")


def test_yaencontre_404_es_portal_caido():
    with pytest.raises(PortalCaido):
        yaencontre.parsear("<html><title>Error 404 - yaencontre</title></html>")


# ---------- recoger con un navegador falso ----------

def test_recoger_idealista_solo_abre_fichas_por_confirmar():
    abiertas = []

    def abrir(url):
        abiertas.append(url)
        if "/inmueble/" in url:
            return _leer("idealista_ficha.html")
        return _leer("idealista_listado.html") if "pagina" not in url else _leer("idealista_listado.html")

    pisos = idealista.recoger(abrir)
    fichas = [u for u in abiertas if "/inmueble/" in u]
    # Con los datos del listado quedan «por confirmar» solo 102535568 (Zapillo, con ascensor) y 109485526
    # (Centro, con ascensor). Los de zona «sin ascensor» (110123388, 112505553, 99141095) ya están descartados:
    # cada visita de más arriesga un captcha.
    assert sorted(u.split("/")[-2] for u in fichas) == ["102535568", "109485526"]
    assert len(pisos) == 12
    assert all(clasificar(completar(p)) in ("cumple", "confirmar", "descartar") for p in pisos)
