# Alertas de pisos en alquiler en Almería: diseño

Fecha: 20/11/2026 · Estado: borrador para aprobar

## Para qué es

Belén (su correo va solo en el secret CORREO_DESTINO, nunca en el repositorio) busca piso de alquiler en Almería capital. Queremos que reciba cada día, sin que
nadie tenga que hacer nada, los pisos nuevos que cumplen sus condiciones, y que tenga una página con todos los que
siguen publicados, que también pueda compartir. Tiene que ser **gratis** y **sin gastar tokens**: solo scripts.

**Criterios de búsqueda**

- Alquiler, Almería capital, zonas: **Centro, Oliveros, Altamira, Zapillo, Vega de Acá**.
- **500-700 €/mes**.
- **2 habitaciones, 1 baño**.
- **Con garaje y ascensor**.

## Objetivos, no objetivos y lo que lo haría fracasar

- **Objetivos**:
  - un correo diario solo con los pisos **nuevos**;
  - una página web pública con todos los pisos vigentes;
  - funcionar sin nadie, con el PC apagado, para Fotocasa, Habitaclia, pisos.com y Milanuncios;
  - si el PC está encendido, añadir también Idealista y yaencontre.
- **No objetivos**:
  - contactar con anunciantes;
  - guardar historial de precios;
  - una aplicación móvil;
  - el artefacto de claude.ai (actualizarlo exige a Claude y gasta tokens).
- **Fracaso aunque «funcione»**:
  - correos con pisos repetidos o que no cumplen;
  - que deje de llegar en silencio porque un portal cambió o bloqueó (tiene que avisar);
  - que dependa de que Miguel o Claude lo lancen.

## Lo medido el 20/11/2026, desde la conexión de casa

| Portal | Petición simple | Navegador invisible | Navegador visible (Edge) |
|---|---|---|---|
| Fotocasa, API `web.gw.fotocasa.es/v2/propertysearch/search` | 200, JSON con precio, habitaciones, baños, `elevator` y barrio (`address.location.level7`) | | |
| Milanuncios, API `searchapi.gw.milanuncios.com/v3/classifieds` | 200, JSON con `bedrooms` y `bathrooms` | 403 | captcha |
| pisos.com (HTML) | 200, con anuncios | | |
| Habitaclia (HTML) | 200 tras la redirección | | |
| Idealista | 403 captcha | 403 | **200, ~95 anuncios** |
| yaencontre | 403 captcha | 403 | **200, ~95 anuncios** |

**Sin medir**:

- si los portales «abiertos» bloquean las IP de los servidores de GitHub (es el primer paso del plan);
- si el garaje aparece como dato estructurado: en 10 pisos de Fotocasa ninguno lo traía, así que puede haber que
  sacarlo del texto.

## Enfoques considerados

- **A. Solo servidor (GitHub Actions)**: gratis y sin PC, pero sin Idealista ni yaencontre.
- **B. Solo PC (tarea programada de Windows con Edge visible)**: cubre los 6 portales, pero depende de que el PC esté
  encendido con la sesión abierta y abre una ventana cada vez.
- **C. A + B (elegido por Miguel)**: A es la base diaria que nunca falla por el PC. B añade Idealista y yaencontre
  cuando el PC está encendido. Además, Belén crea su **alerta guardada de Idealista**, gratuita, que cubre ese portal
  aunque el PC no se encienda.

## Cómo funciona

```
GitHub Actions (cron diario ~08:00 hora de España)
  1. recoge: Fotocasa, Habitaclia, pisos.com, Milanuncios
  2. suma lo que el PC haya subido (data/pc/*.json) en las últimas 48 h
  3. normaliza → filtra → quita duplicados entre portales
  4. compara con data/vistos.json → nuevos
  5. genera docs/index.html (GitHub Pages) y hace commit de los datos
  6. si hay nuevos, envía el correo por Gmail (SMTP + contraseña de aplicación)

PC de casa (Programador de tareas de Windows; al iniciar sesión y cada día a las 09:00 si está encendido)
  1. abre Edge visible con Playwright y lee Idealista y yaencontre
  2. guarda data/pc/<fecha>.json, hace commit y push
  3. lanza el workflow (workflow_dispatch) para que esos pisos entren ya en la página y el correo
```

**Decisiones**:

- **Repositorio en GitHub (cuenta mng60), público**: GitHub Pages gratis exige un repositorio público. En el código
  no hay datos personales. El correo de Belén y la contraseña de Gmail van como *secrets* del repositorio. La página
  lleva `noindex` para que no salga en buscadores.
- **Un solo formato de piso** para todos los portales: portal, id, url, precio, habitaciones, baños, m², planta,
  barrio, garaje (sí / no / sin dato), ascensor (sí / no / sin dato), foto, fecha de primera vez vista.
- **Zonas**: cada portal nombra los barrios a su manera (Fotocasa agrupa «Ciudad Jardín - Tagarete - El Zapillo»).
  Habrá una tabla de correspondencia por portal con los nombres reales sacados de los propios portales, y la zona
  agrupada entra entera. *Decisión mía*: es mejor que sobre un piso de Ciudad Jardín a que falte uno del Zapillo.
- **Garaje y ascensor «sin dato»**: el piso no se descarta. La página y el correo tienen dos apartados:
  - **«Cumple todo»**;
  - **«Por confirmar»**: cumple precio, habitaciones, baño y zona, pero el anuncio no dice si tiene garaje o
    ascensor.

  Se busca también en el texto del anuncio («garaje», «plaza de aparcamiento», «parking», «ascensor»). Si dice
  «sin ascensor» o «sin garaje», se descarta. **El garaje suele aparecer solo en la descripción y no en las
  características (Miguel, 20/11/2026)**, así que leer la descripción es obligatorio en todos los portales. Si el
  listado de un portal no trae la descripción completa (la API de Fotocasa sí trae el campo `description`), se abre
  la ficha del anuncio, solo para los candidatos que ya cumplen precio, habitaciones, baño y zona. Los tests llevan
  casos con «plaza de garaje incluida», «garaje opcional por 50 €» (cuenta como garaje, con la nota del extra), «sin
  garaje» y «zona fácil de aparcar» (no es garaje). *Decisión mía*: muchos anuncios no rellenan esos campos, y descartarlos
  dejaría fuera pisos válidos.
- **Duplicados**: el mismo piso suele estar en varios portales. Se agrupa por precio + m² + habitaciones + barrio, y
  la página enseña un piso con los enlaces de cada portal. *Decisión mía*.
- **Correo a Belén**: solo si hay pisos nuevos, para no acostumbrarla a correos vacíos. No lleva avisos técnicos.
- **Correo de fallos a Miguel (decisión de Miguel)**: aparte del de Belén. Se envía cuando un portal falla dos días
  seguidos (error, bloqueo, o 0 resultados cuando antes había) o cuando falla el PC. Así un fallo nunca pasa en
  silencio. Su dirección va en el secret `CORREO_AVISOS`.
- **Remitente (decisión de Miguel)**: un Gmail nuevo, creado solo para esto, con verificación en dos pasos y
  contraseña de aplicación (secrets `GMAIL_USUARIO` y `GMAIL_CLAVE_APP`). El correo de Belén va en `CORREO_DESTINO`.
- **Retirados**: un piso que deja de aparecer 3 días seguidos sale de la página.
- **Ritmo**: diario. Si Belén prefiere cada dos días, se cambia una línea del cron.
- **Si GitHub está bloqueado** para algún portal «abierto» (lo mide el primer paso), ese portal **pasa a la parte del
  PC**, sin cambiar nada más. Si lo estuvieran todos, se para y se replantea con Miguel antes de seguir. *Decisión
  mía*.
- **Milanuncios es prescindible**: su API no es oficial. Si falla de forma continuada, se desactiva con un interruptor
  de configuración y el aviso deja de salir. *Decisión mía*.
- **«Por confirmar» en el correo**: va en el correo como pisos nuevos, debajo de «Cumple todo» y en formato compacto.
  Si resulta demasiado ruido, se pasa solo a la página con un ajuste. *Decisión mía*: el garaje casi nunca viene como
  dato, y quitarlos del correo dejaría el correo casi vacío.
- **Duplicados, mejor de menos que de más**: solo se fusionan si coinciden precio exacto, habitaciones y barrio, y los
  m² con un margen de ±3 cuando ambos los traen. Ante la duda se enseñan dos tarjetas, para no esconder nunca un
  piso. *Decisión mía*.
- **Un portal que falla no borra sus pisos**: ese día sus pisos no cuentan como ausentes, así que ni desaparecen ni
  vuelven luego como «nuevos». *Decisión mía*.
- **Qué se guarda de cada anuncio**: los campos del formato común, la URL de una foto (enlazada, no copiada) y el
  enlace al anuncio. Nunca teléfonos, nombres ni el texto completo, que solo se usa en memoria para detectar garaje y
  ascensor. *Decisión mía*.
- **Fallos del PC** (sesión bloqueada, captcha en Edge): se anotan en `data/pc/estado.json` y entran en el mismo aviso
  de «portal caído» del correo. *Decisión mía*.

## Lo que hace falta de las personas

- Crear el Gmail remitente nuevo, activar la verificación en dos pasos y generar la **contraseña de aplicación**.
  Es un paso humano que no se puede automatizar; las instrucciones irán en el README.
- Repositorio público `pisos-almeria` en GitHub (mng60): **confirmado por Miguel**. Claude lo crea al aprobarse el
  diseño, y lo primero es la prueba de bloqueo desde GitHub.
- Que Belén cree su alerta guardada en Idealista con los mismos filtros (las instrucciones irán en el README).
- Para la parte del PC: Edge instalado (ya lo está) y Python 3.12 con Playwright (ya instalado en esta máquina).

## Riesgos

- **Los portales cambian o bloquean**: el aviso de «portal caído» lo hace visible. Cada portal va en su propio módulo
  con su test sobre una respuesta real guardada, para arreglarlo sin tocar los demás.
- **GitHub desactiva los cron** de un repositorio público tras 60 días sin actividad. Como el workflow hace commit
  cada día, *creemos* que eso cuenta como actividad (sin verificar; hay que comprobarlo en la documentación de GitHub).
- **El uso de los portales**: son consultas de lectura, una vez al día y en pocas páginas, para uso personal. No se
  republica contenido masivamente: la página enlaza a cada anuncio original.

## Lo que queda para quien lo construya

- Los parámetros exactos de cada portal (ids de barrio, paginación) y la lectura de pisos.com y Habitaclia.
- La estructura del repositorio y el aspecto de la página, que debe ser simple y legible en móvil.
- El instalador y la guía (norma de Miguel): `README` con qué hace falta y por qué, y un script que deja lista la
  parte del PC (dependencias y tarea programada) y comprueba que funciona.
