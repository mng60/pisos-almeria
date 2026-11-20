# Pisos en Almería: alertas diarias

Busca cada día pisos de alquiler en Almería capital (Centro, Oliveros, Altamira, Zapillo y Vega de Acá; 500-700 €;
2 habitaciones, 1 baño, garaje y ascensor), publica una página con los vigentes y manda por correo los nuevos.

Diseño: `docs/superpowers/specs/2026-11-20-alertas-pisos-almeria-design.md`.

## Qué portal corre dónde

Medido el 20/11/2026 con `python scripts/sonda_portales.py`, desde casa y desde GitHub Actions (workflow
`sonda.yml`, ejecución 44790689034). Los resultados son idénticos en los dos sitios:

| Portal | Casa | GitHub | Dónde corre |
|---|---|---|---|
| Fotocasa (API) | 200 | 200 | GitHub |
| Habitaclia | 200 | 200 | GitHub |
| pisos.com | 200 | 200 | GitHub |
| Milanuncios (API) | 200 | 200 | GitHub |
| Idealista | 403 captcha | 403 captcha | PC (Edge visible) + alerta propia de Idealista |
| yaencontre | 403 captcha | 403 captcha | PC (Edge visible) |

Para volver a medirlo: `gh workflow run sonda.yml` y `gh run view --log`.

**Idealista y yaencontre**: tras unas 6 visitas automáticas el 20/11/2026, bloquearon con captcha también el Edge
visible desde casa. Por eso la parte del PC abre Edge con un perfil propio
(`%LOCALAPPDATA%\pisos-almeria\perfil-edge`) y, si sale el captcha, **espera a que una persona lo resuelva** con la
ventana abierta. La cookie queda guardada en ese perfil para las visitas siguientes.

## Cómo funciona

- **Cada hora de 07:00 a 22:00** (hora de España en invierno; una hora más en verano), GitHub Actions
  (`.github/workflows/diario.yml`). El correo solo sale cuando hay pisos nuevos, así que cada piso llega como mucho
  una hora después de publicarse. En cada pasada:
  - consulta Fotocasa, Habitaclia, pisos.com y Milanuncios;
  - suma lo que haya subido el PC hoy o ayer;
  - publica la página https://mng60.github.io/pisos-almeria/;
  - envía el correo de pisos nuevos a Belén y, si algún portal falla 2 días seguidos, otro a Miguel.
- **A las 15:00, si el PC está encendido** (o al entrar más tarde ese día), la tarea programada abre Edge, lee
  Idealista y yaencontre, sube `data/pc/<fecha>.json` y relanza el workflow: esos pisos llegan en el correo de esa
  misma tarde.
- **Cómo se clasifica cada piso**:
  - «Cumple todo»: precio, habitaciones, baño, zona, garaje y ascensor confirmados.
  - «Por confirmar»: el anuncio no dice si tiene garaje o ascensor.
  - Se descarta si dice «sin garaje» o «sin ascensor», o si no cumple el resto de criterios.
  - El garaje se busca también en la descripción, porque muchas veces solo aparece ahí. Aparcar en la calle no
    cuenta como garaje.
- **El mismo piso publicado en varios portales** sale una sola vez, con un botón para cada portal.

## Puesta en marcha (una sola vez)

1. **Crear el Gmail que envía** (uno nuevo, solo para esto):
   1. Crea la cuenta en https://accounts.google.com/signup.
   2. Activa la verificación en dos pasos en https://myaccount.google.com/security.
   3. Crea una contraseña de aplicación en https://myaccount.google.com/apppasswords (nombre: «pisos-almeria»).
      Son 16 letras.
2. **Guardar los 4 secretos** en el repositorio. Quedan cifrados: nadie puede leerlos, ni en GitHub.

   ```bash
   gh secret set GMAIL_USUARIO   --repo mng60/pisos-almeria   # el Gmail nuevo
   gh secret set GMAIL_CLAVE_APP --repo mng60/pisos-almeria   # la contraseña de aplicación
   gh secret set CORREO_DESTINO  --repo mng60/pisos-almeria   # el correo de Belén
   gh secret set CORREO_AVISOS   --repo mng60/pisos-almeria   # el correo de Miguel (fallos)
   ```

3. **Comprobar** con `gh workflow run diario.yml`. Para probar también el correo de fallos, pon el secret
   `PISOS_FORZAR_AVISO` a `1`, lanza el workflow y borra el secret después.
4. **Parte del PC** (opcional, para Idealista y yaencontre): `python scripts/instalar_pc.py`. Comprueba lo que
   hace falta, crea las tareas programadas y hace una pasada de prueba.
5. **Alerta propia de Idealista** (recomendada aunque esté la parte del PC):
   1. Entra en idealista.com y busca «Alquiler · Almería capital».
   2. Filtra por 500-700 €, 2 habitaciones, 1 baño, garaje y ascensor.
   3. Marca en el mapa las zonas Centro, Oliveros, Altamira, Zapillo y Vega de Acá.
   4. Pulsa «Guardar búsqueda» y elige el aviso por correo diario o inmediato.

   yaencontre tiene la misma opción («Crear alerta»).

## Cambiar cosas

- **Criterios** (precio, habitaciones, zonas): `pisos/config.py`.
- **Ritmo**: en `.github/workflows/diario.yml`. Ahora es `"0 6-21 * * *"` (cada hora). Para una sola vez al día
  a las 15:00 de España, `"0 14 * * *"`; cada 2 días, `"0 14 */2 * *"`.
- **Dejar de consultar un portal**: añádelo a `PORTALES_DESACTIVADOS` en `pisos/config.py`.

## Cuando llega un aviso de fallo

El correo dice qué portal falla, desde cuándo y el motivo.

- **«HTTP 403» o «captcha»**: el portal está bloqueando. Si es uno del servidor, pásalo a la parte del PC
  (`PORTALES_PC`) o desactívalo.
- **«formato irreconocible» o «error inesperado»**: el portal ha cambiado su web. Vuelve a volcar su respuesta
  (`python -m pytest -m red -k <portal>`), ajusta `pisos/portales/<portal>.py` y su test.
- **«0 resultados cuando antes había»**: puede ser real (no hay pisos) o un cambio silencioso. Compruébalo
  entrando en la web.

## Desarrollo

```bash
pip install -r requirements.txt
python -m pytest            # tests sin red, con respuestas reales guardadas en tests/fixtures
python -m pisos.servidor    # pasada real sin correo, si no hay credenciales (escribe sitio/ y data/)
```
