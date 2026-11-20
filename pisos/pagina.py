"""Página pública (GitHub Pages) con todos los pisos vigentes, y la tarjeta que comparte con el correo.

Las tarjetas llevan los estilos en línea para que el mismo HTML sirva en el correo (los clientes de correo
ignoran las hojas de estilo).
"""
from __future__ import annotations

from datetime import date, datetime
from html import escape

from . import config
from .duplicados import Grupo
from .estado import clave
from .filtro import clasificar

NOMBRES_PORTAL = {"fotocasa": "Fotocasa", "habitaclia": "Habitaclia", "pisoscom": "pisos.com",
                  "milanuncios": "Milanuncios", "idealista": "Idealista", "yaencontre": "yaencontre"}


def pendientes(g: Grupo) -> list[str]:
    """Lo que falta confirmar de un piso «Por confirmar»."""
    p = g.principal
    falta = []
    if p.garaje is None:
        falta.append("garaje sin confirmar")
    if p.ascensor is None:
        falta.append("ascensor sin confirmar")
    if p.banos is None:
        falta.append("baños sin confirmar")
    return falta


def primera_vez(g: Grupo, estado: dict) -> str | None:
    fechas = [estado.get(clave(m), {}).get("primera_vez") for m in g.miembros]
    fechas = [f for f in fechas if f]
    return min(fechas) if fechas else None


def _fecha_corta(iso: str) -> str:
    return date.fromisoformat(iso).strftime("%d/%m")


def tarjeta(g: Grupo, estado: dict) -> str:
    p = g.principal
    e = escape
    datos = " · ".join(x for x in [
        f"{p.habitaciones} hab." if p.habitaciones else None,
        f"{p.banos} baño{'s' if (p.banos or 0) > 1 else ''}" if p.banos else None,
        f"{p.m2} m²" if p.m2 else None,
        p.planta,
    ] if x)
    garaje = {"si": "Garaje ✔" + (f" ({p.nota_garaje})" if p.nota_garaje else ""), None: "Garaje ?"}.get(p.garaje, "")
    ascensor = {"si": "Ascensor ✔", None: "Ascensor ?"}.get(p.ascensor, "")
    enlaces = " ".join(
        f'<a href="{e(url)}" style="display:inline-block;margin:4px 6px 0 0;padding:6px 12px;border-radius:6px;'
        f'background:#0f766e;color:#fff;text-decoration:none;font-size:14px">Ver en {e(NOMBRES_PORTAL.get(portal, portal))}</a>'
        for portal, url in g.enlaces)
    foto = (f'<img src="{e(p.foto)}" alt="" loading="lazy" style="width:100%;max-height:220px;object-fit:cover;'
            f'border-radius:8px 8px 0 0;display:block">' if p.foto else "")
    desde = primera_vez(g, estado)
    falta = pendientes(g)
    return (
        '<div class="tarjeta" style="border:1px solid #d6d3d1;border-radius:8px;margin:0 0 16px;overflow:hidden;'
        'max-width:560px">'
        f'{foto}<div style="padding:12px 14px">'
        f'<div style="font-size:22px;font-weight:700">{p.precio} €<span style="font-size:14px;font-weight:400">/mes</span></div>'
        f'<div style="font-size:15px;margin:2px 0">{e(p.zona or "")} · {e(p.barrio or "")}</div>'
        f'<div style="font-size:14px;opacity:.8">{e(datos)}</div>'
        f'<div style="font-size:14px;margin-top:4px">{e(garaje)} &nbsp; {e(ascensor)}</div>'
        + (f'<div style="font-size:13px;color:#b45309;margin-top:4px">Por confirmar: {e(", ".join(falta))}</div>'
           if falta else "")
        + (f'<div style="font-size:12px;opacity:.7;margin-top:4px">Publicado desde el {_fecha_corta(desde)}</div>'
           if desde else "")
        + f'<div style="margin-top:6px">{enlaces}</div></div></div>'
    )


def separar(grupos: list[Grupo]) -> tuple[list[Grupo], list[Grupo]]:
    cumple = [g for g in grupos if clasificar(g.principal) == "cumple"]
    confirmar = [g for g in grupos if clasificar(g.principal) == "confirmar"]
    return cumple, confirmar


def _orden(grupos: list[Grupo], estado: dict) -> list[Grupo]:
    return sorted(grupos, key=lambda g: primera_vez(g, estado) or "", reverse=True)


def generar_pagina(grupos: list[Grupo], estado: dict, actualizado: datetime, salud: dict) -> str:
    cumple, confirmar = separar(grupos)
    e = escape

    def apartado(titulo: str, explicacion: str, gs: list[Grupo]) -> str:
        cuerpo = "".join(tarjeta(g, estado) for g in _orden(gs, estado)) or '<p class="vacio">Ninguno ahora mismo.</p>'
        return f"<h2>{titulo} <small>({len(gs)})</small></h2><p class=\"nota\">{explicacion}</p>{cuerpo}"

    portales = ", ".join(NOMBRES_PORTAL.get(p, p) + ("" if not s.get("fallos_seguidos") else " (sin respuesta)")
                         for p, s in sorted(salud.items()))
    contenido = (
        apartado("Cumple todo", "Precio, habitaciones, baño, zona, garaje y ascensor confirmados.", cumple)
        + apartado("Por confirmar", "Cumplen precio, habitaciones y zona, pero el anuncio no dice si tiene "
                   "garaje o ascensor. Conviene preguntar.", confirmar)
        if grupos else '<p class="vacio">Ahora mismo no hay ningún piso publicado que cumpla los criterios.</p>'
    )
    zonas = ", ".join(config.ZONAS)
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Pisos en Almería</title>
<style>
:root {{ --fondo:#fafaf9; --texto:#1c1917; --suave:#57534e; }}
@media (prefers-color-scheme: dark) {{ :root {{ --fondo:#1c1917; --texto:#f5f5f4; --suave:#a8a29e; }} }}
body {{ margin:0; background:var(--fondo); color:var(--texto); font-family:system-ui,-apple-system,"Segoe UI",sans-serif; }}
main {{ max-width:600px; margin:0 auto; padding:16px; }}
h1 {{ font-size:24px; margin:8px 0 4px; }} h2 {{ font-size:19px; margin:28px 0 4px; }}
h2 small {{ font-weight:400; color:var(--suave); }}
.nota, .vacio, footer {{ color:var(--suave); font-size:14px; }}
footer {{ margin:32px 0 16px; border-top:1px solid #d6d3d1; padding-top:12px; }}
</style></head><body><main>
<h1>Pisos en alquiler en Almería</h1>
<p class="nota">{e(zonas)} · {config.PRECIO_MIN}-{config.PRECIO_MAX} € · {config.HABITACIONES} habitaciones ·
{config.BANOS} baño · garaje y ascensor</p>
{contenido}
<footer>Actualizado el {actualizado.strftime("%d/%m/%Y a las %H:%M")} (hora UTC). Portales consultados: {e(portales)}.
Idealista se revisa aparte, con su propia alerta por correo.</footer>
</main></body></html>
"""
