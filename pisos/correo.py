"""Correos: el diario a Belén (solo si hay pisos nuevos) y el de fallos a Miguel (decisión de Miguel: los
avisos técnicos no van a Belén). Se envían por Gmail con una contraseña de aplicación."""
from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

from .duplicados import Grupo
from .pagina import NOMBRES_PORTAL, separar, tarjeta

PAGINA_URL = os.environ.get("PAGINA_URL", "https://mng60.github.io/pisos-almeria/")


def asunto_belen(nuevos: list[Grupo]) -> str:
    cumple, _ = separar(nuevos)
    n = len(nuevos)
    return f"🏠 {n} piso{'s' if n != 1 else ''} nuevo{'s' if n != 1 else ''} en Almería ({len(cumple)} cumple todo)"


def correo_belen(nuevos: list[Grupo], remitente: str, destino: str, estado: dict | None = None) -> EmailMessage | None:
    if not nuevos:
        return None
    cumple, confirmar = separar(nuevos)
    estado = estado or {}
    partes = []
    if cumple:
        partes.append("<h2 style=\"font-size:18px\">Cumple todo</h2>" + "".join(tarjeta(g, estado) for g in cumple))
    if confirmar:
        partes.append("<h2 style=\"font-size:18px\">Por confirmar (preguntar garaje o ascensor)</h2>"
                      + "".join(tarjeta(g, estado) for g in confirmar))
    html = (f'<div style="font-family:system-ui,sans-serif;color:#1c1917">'
            f'<p>Pisos nuevos desde el último correo:</p>{"".join(partes)}'
            f'<p><a href="{PAGINA_URL}">Ver todos los pisos disponibles</a></p></div>')
    texto = "\n\n".join(
        f"{g.principal.precio} € · {g.principal.zona} · " + " ".join(url for _, url in g.enlaces) for g in nuevos
    ) + f"\n\nTodos los pisos: {PAGINA_URL}"
    msg = EmailMessage()
    msg["Subject"] = asunto_belen(nuevos)
    msg["From"] = remitente
    msg["To"] = destino
    msg.set_content(texto)
    msg.add_alternative(html, subtype="html")
    return msg


def correo_avisos(portales: list[str], salud: dict, remitente: str, destino: str) -> EmailMessage | None:
    if not portales:
        return None
    lineas = []
    for p in portales:
        s = salud.get(p, {})
        lineas.append(f"- {NOMBRES_PORTAL.get(p, p)} ({p}): {s.get('fallos_seguidos')} días seguidos sin "
                      f"respuesta válida. Motivo: {s.get('motivo')}. Última vez bien: {s.get('ultimo_ok') or 'nunca'}.")
    texto = ("Alertas de pisos en Almería: estos portales están fallando.\n\n" + "\n".join(lineas)
             + "\n\nQué hacer: README, apartado «Cuando llega un aviso». Para dejar de consultar un portal, "
               "añádelo a PORTALES_DESACTIVADOS en pisos/config.py.\n")
    msg = EmailMessage()
    msg["Subject"] = "⚠️ Pisos Almería: falla " + ", ".join(NOMBRES_PORTAL.get(p, p) for p in portales)
    msg["From"] = remitente
    msg["To"] = destino
    msg.set_content(texto)
    return msg


def enviar(msg: EmailMessage, usuario: str, clave: str) -> None:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as smtp:
        smtp.login(usuario, clave)
        smtp.send_message(msg)
