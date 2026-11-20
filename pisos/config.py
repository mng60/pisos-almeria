"""Criterios de búsqueda y ajustes. Para cambiar la búsqueda, se toca solo este fichero."""

PRECIO_MIN, PRECIO_MAX = 500, 700
HABITACIONES = 2
BANOS = 1
ZONAS = ("Centro", "Oliveros", "Altamira", "Zapillo", "Vega de Acá")

# Barrios cuyo nombre NO contiene el de la zona y aun así pertenecen a ella: portal -> {barrio: zona}.
# Lo que sí contiene el nombre de una zona («Ciudad Jardín - Tagarete - El Zapillo», «Oliveros - Altamira»)
# lo resuelve filtro.zona_de() sin tabla. Nombres de Fotocasa volcados el 20/11/2026 de su API
# (combinedLocationIds=724,1,4,276,486,4013,0,0,0, campo address.location.level7, alquiler y venta):
# los cinco que interesan son «Centro», «Ciudad Jardín - Tagarete - El Zapillo», «Oliveros - Altamira» y
# «Nueva Almería - Cortijo Grande - Vega de Acá»; ninguno necesita tabla.
BARRIOS: dict[str, dict[str, str]] = {
    "fotocasa": {},
}

# Dónde corre cada portal: medido con scripts/sonda_portales.py el 20/11/2026 (README, «Qué portal corre dónde»).
PORTALES_SERVIDOR = ("fotocasa", "habitaclia", "pisoscom", "milanuncios")
PORTALES_PC = ("idealista", "yaencontre")
# Interruptor: un portal aquí no se consulta ni avisa (p. ej. si la API no oficial de Milanuncios cambia).
PORTALES_DESACTIVADOS: set[str] = set()

DIAS_PARA_RETIRAR = 3   # ausencias seguidas para quitar un piso de la página
DIAS_FALLO_AVISO = 2    # fallos seguidos de un portal para avisar a Miguel
