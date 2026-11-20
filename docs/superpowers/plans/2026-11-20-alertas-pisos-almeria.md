# Alertas de pisos en Almería: plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Objetivo**: cada mañana, sin intervención, Belén recibe por correo los pisos nuevos que cumplen sus criterios.
Hay una página pública con todos los vigentes, actualizada por GitHub Actions y, cuando el PC está encendido, también
por un script local que añade Idealista y yaencontre.

**Arquitectura**:

- un paquete Python `pisos/`, con un módulo por portal que devuelve `list[Piso]`;
- un núcleo puro (texto → garaje/ascensor, clasificar, duplicados, estado) probado con respuestas reales guardadas;
- dos puntos de entrada:
  - `pisos.servidor`, que lanza el workflow diario: recoge, actualiza el estado, publica la página y envía los correos;
  - `pisos.pc`, que lanza la tarea de Windows: Edge visible → `data/pc/*.json` → push → dispara el workflow.

**Tecnologías**: Python 3.12, `requests`, `beautifulsoup4`, `playwright` (solo en el PC, canal `msedge`), `pytest`,
GitHub Actions + GitHub Pages (`actions/upload-pages-artifact` + `actions/deploy-pages`), `smtplib` con Gmail
(SSL 465), Programador de tareas de Windows (`schtasks`).

**Diseño**: `docs/superpowers/specs/2026-11-20-alertas-pisos-almeria-design.md`. Léelo antes de cada tarea.

## Restricciones globales

- Criterios: alquiler · Almería capital · zonas `Centro`, `Oliveros`, `Altamira`, `Zapillo`, `Vega de Acá` ·
  precio 500-700 €/mes ambos incluidos · 2 habitaciones · 1 baño · garaje · ascensor.
- Coste cero: nada de pago, nada de llamadas a modelos de lenguaje.
- Repositorio público `mng60/pisos-almeria`.
- Ningún dato personal en el código ni en `data/`. Secrets: `GMAIL_USUARIO`, `GMAIL_CLAVE_APP`, `CORREO_DESTINO`
  (Belén), `CORREO_AVISOS` (Miguel).
- De cada anuncio se guardan solo los campos de `Piso` (abajo). Nunca teléfonos, nombres ni la descripción: la
  descripción vive solo en memoria.
- La página lleva `<meta name="robots" content="noindex">` y se lee bien a 390 px.
- **Antes de escribir el lector de un portal, se vuelca su respuesta real** a `tests/fixtures/` y se escribe el
  lector contra ese volcado. Nunca se deducen selectores ni campos.
- Tests sin red: todos los de `tests/` leen fixtures. La red solo en las sondas marcadas `@pytest.mark.red`
  (excluidas por defecto en `pytest.ini`).

## Foco de revisión

1. **Garaje que solo sale en la descripción**. Se espera «si». Test en la Tarea 2 y, con el anuncio real, en cada
   portal (Tareas 4-6).
2. **Un portal que devuelve 0 o falla un día**. Sus pisos no salen de la página ni vuelven luego como «nuevos», y al
   segundo día seguido hay correo a Miguel. Tarea 7.
3. **El mismo piso en dos portales con m² distintos (60 y 62)**. Una tarjeta con dos enlaces. Con m² 60 y 70, dos
   tarjetas. Tarea 7.
4. **El PC y el workflow hacen push a la vez**. Ningún commit se pierde: `git pull --rebase` con reintento y
   `concurrency` en el workflow. Tarea 10.
5. **Precio con formato «1.200 €/mes», «650€» o «650 € + gastos»**. Se lee como entero de euros. Si no se puede leer,
   el piso se descarta y se cuenta en el registro, sin romper la ejecución. Test en la Tarea 2.

---

### Tarea 1: Repositorio y sonda de bloqueo desde GitHub

**Ficheros**:
- Crear: `README.md` (esqueleto), `.gitignore`, `requirements.txt` (`requests`, `beautifulsoup4`, `pytest`),
  `requirements-pc.txt` (`-r requirements.txt` + `playwright`), `pytest.ini` (`-m "not red"`),
  `.github/workflows/sonda.yml`, `scripts/sonda_portales.py`.
- Mover: el diseño y este plan se quedan en `docs/superpowers/`.

- [ ] **Paso 1**: `git init` en `d:\Cosas sueltas\belen\pisos-almeria`, rama `main`. Luego
  `gh repo create mng60/pisos-almeria --public --source . --push`.
- [ ] **Paso 2**: escribir `scripts/sonda_portales.py`. Pide con `requests` y el UA de Chrome 130 las 6 URL medidas el
  20/11 (las del diseño, más la API de Fotocasa con
  `combinedLocationIds=724,1,4,276,0,0,0,0,0&transactionTypeId=3&propertyTypeId=2&minPrice=500&maxPrice=700`).
  Imprime una línea por portal: `portal código bytes captcha=<bool> anuncios=<n>`. Sale con código 0 siempre: es una
  medición, no una puerta.
- [ ] **Paso 3**: `sonda.yml`, con `workflow_dispatch` y `ubuntu-latest`, ejecuta la sonda. Lanzarlo con
  `gh workflow run sonda.yml` y leer el resultado con `gh run view --log`.
- [ ] **Paso 4**: anotar la tabla de GitHub junto a la de casa en el README («Qué portal corre dónde»). Aplicar la
  regla del diseño: si un portal abierto da 403 o captcha desde GitHub, pasa a `PORTALES_PC` en la Tarea 3. Si caen
  los cuatro, **parar e informar a Miguel**.
- [ ] **Paso 5**: commit: `chore: repositorio y sonda de bloqueo desde GitHub` (cuerpo con la tabla medida).

### Tarea 2: Modelo `Piso` y lectura de texto

**Ficheros**: crear `pisos/__init__.py`, `pisos/modelo.py`, `pisos/texto.py` y el test `tests/test_texto.py`.

**Interfaces que produce**:

```python
@dataclass
class Piso:
    portal: str; id: str; url: str; precio: int
    habitaciones: int | None; banos: int | None; m2: int | None
    planta: str | None; barrio: str | None          # barrio tal y como lo nombra el portal
    zona: str | None = None                           # una de las 5, la pone filtro.zona_de()
    garaje: str | None = None; nota_garaje: str | None = None   # "si" | "no" | None
    ascensor: str | None = None                       # "si" | "no" | None
    foto: str | None = None
    descripcion: str | None = field(default=None, repr=False)   # nunca se serializa
    def a_dict(self) -> dict      # sin descripcion
    @classmethod
    def de_dict(cls, d: dict) -> "Piso"

def leer_precio(texto: str) -> int | None
def detectar_garaje(texto: str | None) -> tuple[str | None, str | None]   # (valor, nota)
def detectar_ascensor(texto: str | None) -> str | None
```

- [ ] **Paso 1**: tests que deben fallar.

```python
@pytest.mark.parametrize("t,esperado", [
  ("Plaza de garaje incluida en el precio", ("si", None)),
  ("Garaje opcional por 50 €", ("si", "opcional 50 €")),
  ("Piso sin garaje, bien comunicado", ("no", None)),
  ("Zona fácil de aparcar", (None, None)),
  ("Incluye plaza de aparcamiento en sótano", ("si", None)),
  ("PARKING comunitario", ("si", None)),
  ("No dispone de plaza de garaje", ("no", None)),
  (None, (None, None)),
])
def test_detectar_garaje(t, esperado): assert detectar_garaje(t) == esperado

@pytest.mark.parametrize("t,esperado", [("Edificio con ascensor", "si"), ("Sin ascensor", "no"),
  ("cuarta planta sin ascensor", "no"), ("Exterior y luminoso", None)])
def test_detectar_ascensor(t, esperado): assert detectar_ascensor(t) == esperado

@pytest.mark.parametrize("t,esperado", [("1.200 €/mes", 1200), ("650€", 650), ("650 € + gastos", 650),
  ("Consultar", None)])
def test_leer_precio(t, esperado): assert leer_precio(t) == esperado

def test_a_dict_no_lleva_descripcion(): ...  # Piso(..., descripcion="x").a_dict() no tiene la clave "descripcion"
```

- [ ] **Paso 2**: `pytest tests/test_texto.py` → FALLA (ImportError).
- [ ] **Paso 3**: implementar. Va sin tildes y en minúsculas (`unicodedata`). La negación («sin», «no dispone de»,
  «no tiene») se busca en una ventana de 4 palabras antes del término y gana a la afirmación. La nota de «opcional»
  recoge el importe si lo hay.
- [ ] **Paso 4**: PASA. Reintroduce a mano el fallo de quitar la negación y comprueba que «sin garaje» se pone en
  rojo; luego revierte.
- [ ] **Paso 5**: commit: `feat: modelo Piso y lectura de garaje, ascensor y precio del texto`.

### Tarea 3: Configuración, zonas y clasificación

**Ficheros**: crear `pisos/config.py`, `pisos/filtro.py` y el test `tests/test_filtro.py`.

**Interfaces que produce**:

```python
# config.py
PRECIO_MIN, PRECIO_MAX = 500, 700
HABITACIONES, BANOS = 2, 1
ZONAS = ("Centro", "Oliveros", "Altamira", "Zapillo", "Vega de Acá")
BARRIOS: dict[str, dict[str, str]]   # portal -> {nombre de barrio del portal: zona}
PORTALES_SERVIDOR: tuple[str, ...]   # según la sonda de la Tarea 1
PORTALES_PC = ("idealista", "yaencontre")
PORTALES_DESACTIVADOS: set[str] = set()   # interruptor (p. ej. "milanuncios")
DIAS_PARA_RETIRAR = 3
DIAS_FALLO_AVISO = 2
# filtro.py
def zona_de(portal: str, barrio: str | None) -> str | None
def clasificar(p: Piso) -> str          # "cumple" | "confirmar" | "descartar"
def completar(p: Piso) -> Piso          # rellena zona, garaje y ascensor desde la descripción si faltan
```

- [ ] **Paso 1**: volcar los nombres reales de barrio. Para Fotocasa, `address.location.level7` de todas las páginas de
  Almería capital (sin filtro de precio). Para los demás portales, en sus tareas. Rellenar `BARRIOS["fotocasa"]`. Una
  zona agrupada que contenga una de las 5 entra entera (diseño: «Ciudad Jardín - Tagarete - El Zapillo» → `Zapillo`).
  Anotar en un comentario la fecha y el comando del volcado.
- [ ] **Paso 2**: tests que deben fallar:
  - `test_zona_agrupada_entra`;
  - `test_barrio_fuera_es_none` («Retamar» → `None`);
  - `test_cumple_todo`;
  - `test_sin_dato_garaje_es_confirmar`;
  - `test_sin_ascensor_es_descartar`;
  - `test_precio_limites` (500 y 700 cumplen; 499 y 701 se descartan);
  - `test_tres_habitaciones_descarta`;
  - `test_banos_desconocido_es_confirmar`;
  - `test_completar_lee_garaje_de_descripcion` (garaje `None` y descripción «plaza de garaje incluida» → `"si"`; un
    `"si"` del portal no lo pisa un texto vacío).
- [ ] **Paso 3**: FALLA → implementar → PASA.
- [ ] **Paso 4**: commit: `feat: zonas y clasificación cumple / por confirmar / descartar`.

### Tareas 4-6: Lectores de portal del servidor

Las tres tareas siguen el mismo esquema, y se pueden repartir en paralelo cuando la 3 esté hecha.

**Interfaz común de cada `pisos/portales/<portal>.py`**:

```python
NOMBRE: str
def recoger(sesion: requests.Session) -> list[Piso]   # todos los anuncios de Almería capital entre 500 y 700 €,
                                                      # 2 hab., todas las páginas; descripción incluida
def parsear(respuesta: str | dict) -> list[Piso]      # puro: lo que prueban los tests
```

`recoger` lanza `PortalCaido(portal, motivo)` (definida en `pisos/portales/__init__.py`, Tarea 4) ante un 403, un
captcha o un formato irreconocible. Tope: 10 páginas y 1 segundo de pausa entre peticiones.

- **Tarea 4: Fotocasa** (API JSON) y `PortalCaido`. La descripción viene en el campo `description`. Las
  características, en `features` (`elevator`, `rooms`, `bathrooms`, `surface`, `floor`). La URL del anuncio se monta
  con `detail.es`; volcar un ejemplo para confirmarlo.
- **Tarea 5: Habitaclia y pisos.com** (HTML). Si el listado no trae la descripción, `recoger` abre la ficha **solo de
  los candidatos** que pasan precio, habitaciones y zona (diseño, «Garaje y ascensor sin dato»).
- **Tarea 6: Milanuncios** (API `searchapi.gw.milanuncios.com/v3/classifieds`). El 20/11 se midió que
  `s=piso&province=4` devuelve anuncios con `bedrooms`/`bathrooms`. Hay que encontrar los parámetros de alquiler y
  Almería capital volcando respuestas. Si no se consigue filtrar con fiabilidad, `PORTALES_DESACTIVADOS = {"milanuncios"}`
  y se dice en el resumen.

**Pasos de cada una**:

- [ ] **Paso 1**: sonda `tests/test_<portal>_red.py::test_volcar` (`@pytest.mark.red`) que guarda la respuesta real en
  `tests/fixtures/<portal>_listado.(json|html)` (y `_ficha.html` si aplica). Ejecutarla una vez. Leer el volcado.
- [ ] **Paso 2**: tests sobre el volcado:
  - `test_parsear_cuenta` (n = el número de anuncios contados a mano en el volcado);
  - `test_parsear_campos_primer_anuncio` (precio, habitaciones, url y barrio exactos de ese anuncio);
  - `test_garaje_en_descripcion`, con un anuncio real del volcado cuya descripción mencione el garaje. Si no hay
    ninguno, se fabrica copiando uno real y editando solo la descripción, y se dice en el test.
- [ ] **Paso 3**: FALLA → implementar `parsear` y `recoger` → PASA. Volcar los barrios del portal y completar
  `BARRIOS[<portal>]`.
- [ ] **Paso 4**: ejecutar la sonda de red de nuevo y comprobar que `recoger()` devuelve más de 0 pisos con
  `zona_de` no nula en alguno.
- [ ] **Paso 5**: commit: `feat: lector de <portal>`.

### Tarea 7: Duplicados y estado

**Ficheros**: crear `pisos/duplicados.py`, `pisos/estado.py` y los tests `tests/test_duplicados.py` y
`tests/test_estado.py`.

**Interfaces**:

```python
# duplicados.py
@dataclass
class Grupo: principal: Piso; enlaces: list[tuple[str, str]]   # (portal, url)
def agrupar(pisos: list[Piso]) -> list[Grupo]
#   mismo grupo solo si: precio igual, habitaciones igual, zona igual y no None,
#   y (m2 de alguno es None) o |m2a - m2b| <= 3
# estado.py
def clave(p: Piso) -> str                      # f"{portal}:{id}"
def actualizar(estado: dict, salud: dict, recogidos: dict[str, list[Piso] | PortalCaido],
               hoy: date) -> tuple[list[Piso], list[str]]
#   devuelve (nuevos que no se descartan, portales en aviso). Muta estado y salud:
#   estado[clave] = {"piso": a_dict, "primera_vez", "ultima_vez", "ausencias"}
#   un portal caído, o con 0 recogidos cuando salud[p]["ultimo_n"] > 0, no suma ausencias a sus pisos
#   y suma salud[p]["fallos_seguidos"]; DIAS_PARA_RETIRAR ausencias → se borra
#   aviso si fallos_seguidos >= DIAS_FALLO_AVISO
def cargar(ruta: Path) -> dict ; def guardar(ruta: Path, datos: dict) -> None   # JSON ordenado, UTF-8
```

`data/vistos.json` guarda `estado` y `data/salud.json` guarda `salud`.

- [ ] **Paso 1**: tests que deben fallar:
  - `test_m2_60_y_62_un_grupo`;
  - `test_m2_60_y_70_dos_grupos`;
  - `test_m2_desconocido_agrupa`;
  - `test_nuevo_solo_una_vez` (dos días seguidos con el mismo piso → nuevo solo el primero);
  - `test_portal_caido_no_retira_ni_renueva` (día 1 lo ve, días 2-4 portal caído, día 5 lo ve → sigue en el estado y
    no es nuevo);
  - `test_cero_resultados_cuenta_como_fallo`;
  - `test_aviso_al_segundo_dia`;
  - `test_retirado_tras_3_ausencias`;
  - `test_descartado_no_es_nuevo`;
  - `test_guardar_no_lleva_descripcion`.
- [ ] **Paso 2**: FALLA → implementar → PASA. Mutar `<= 3` a `< 3` y `>= DIAS_FALLO_AVISO` a `>`; cada mutación
  tiene que poner algún test en rojo. Revertir.
- [ ] **Paso 3**: commit: `feat: duplicados entre portales y estado de vistos y salud`.

### Tarea 8: Página y correos

**Ficheros**: crear `pisos/pagina.py`, `pisos/correo.py`, `pisos/plantillas/` (HTML con estilos en línea) y el test
`tests/test_salida.py`.

**Interfaces**:

```python
def generar_pagina(grupos: list[Grupo], actualizado: datetime, salud: dict) -> str
#   apartados "Cumple todo" y "Por confirmar" (qué falta confirmar), más recientes primero,
#   tarjeta: foto, precio, hab/baños/m², planta, barrio, garaje (+nota), ascensor, enlaces a cada portal,
#   "visto por primera vez el …"; pie con fecha de actualización y portales consultados
def correo_belen(nuevos: list[Grupo]) -> email.message.EmailMessage | None     # None si no hay nuevos
def correo_avisos(portales: list[str], salud: dict) -> email.message.EmailMessage | None
def enviar(msg, usuario: str, clave: str) -> None      # smtplib.SMTP_SSL("smtp.gmail.com", 465)
```

- [ ] **Paso 1**: tests que deben fallar:
  - `test_pagina_noindex`;
  - `test_pagina_dos_apartados`;
  - `test_pagina_escapa_html` (un barrio con `<script>` sale escapado);
  - `test_correo_none_sin_nuevos`;
  - `test_correo_belen_no_menciona_fallos`;
  - `test_correo_avisos_nombra_portal_y_dias`;
  - `test_asunto` (`"🏠 3 pisos nuevos en Almería (1 cumple todo)"`).
- [ ] **Paso 2**: FALLA → implementar con `string.Template` o `html.escape` (sin dependencias nuevas) → PASA.
- [ ] **Paso 3**: generar una página con los fixtures de las Tareas 4-6 y abrirla a 390 px y a 1440 px para
  comprobarla a ojo. Adjuntar las capturas al resumen de la tarea.
- [ ] **Paso 4**: commit: `feat: página pública y correos`.

### Tarea 9: Ejecución diaria en GitHub

**Ficheros**: crear `pisos/servidor.py`, `.github/workflows/diario.yml` y el test `tests/test_servidor.py`.

**Interfaces**: `def ejecutar(raiz: Path, portales: dict[str, Callable], hoy: date, enviar: Callable | None) -> dict`
(devuelve un resumen). Pasos: recoge cada portal de `PORTALES_SERVIDOR` capturando `PortalCaido`; añade los
`data/pc/*.json` de las últimas 48 h como recogidos de sus portales; `completar` → `actualizar` → `agrupar` → página
en `sitio/index.html` → correos.

- [ ] **Paso 1**: `test_ejecutar_extremo_a_extremo`, con portales falsos que devuelven los fixtures, en un directorio
  temporal. Día 1: correo con N nuevos. Día 2, mismos datos: sin correo a Belén. Día 2 con Fotocasa caído: sin
  correo. Día 3, caído otra vez: correo a avisos. FALLA → implementar → PASA.
- [ ] **Paso 2**: `diario.yml`:
  - `schedule: cron "0 6 * * *"` (07:00 en invierno, 08:00 en verano, hora de España) y `workflow_dispatch`;
  - `concurrency: {group: diario, cancel-in-progress: false}`;
  - `permissions: contents: write, pages: write, id-token: write`;
  - pasos: checkout → setup-python 3.12 → `pip install -r requirements.txt` → `pytest` → `python -m pisos.servidor` →
    commit de `data/` si cambió (`git pull --rebase` antes del push) → `upload-pages-artifact` (path `sitio`) →
    `deploy-pages`.
  - Activar Pages con origen «GitHub Actions»: `gh api -X POST repos/mng60/pisos-almeria/pages -f build_type=workflow`.
- [ ] **Paso 3**: comprobar en la documentación oficial de GitHub si el commit diario del workflow evita la
  desactivación a los 60 días. Si no la evita, añadir el paso que la evite según esa documentación y citarla en el
  README.
- [ ] **Paso 4**: con los secrets aún sin poner, `gh workflow run diario.yml`. Comprobar que la página publicada
  enseña pisos (`curl` a la URL de Pages) y que el log dice «sin credenciales de correo: no se envía». Ese modo tiene
  su test.
- [ ] **Paso 5**: commit: `feat: ejecución diaria en GitHub Actions y publicación en Pages`.

### Tarea 10: Parte del PC (Idealista y yaencontre)

**Ficheros**: crear `pisos/portales/idealista.py`, `pisos/portales/yaencontre.py`, `pisos/pc.py`,
`scripts/instalar_pc.py` y los tests `tests/test_idealista.py` y `tests/test_yaencontre.py`.

**Interfaces**:
- Mismas `parsear(html: str) -> list[Piso]` que las Tareas 4-6.
- `recoger(pagina: playwright Page) -> list[Piso]`.
- `pisos.pc.main(seco: bool = False)`.
  - Abre Edge con `channel="msedge"` y `headless=False` (medido: en modo invisible da 403).
  - Recoge con pausas de 3-6 s y escribe `data/pc/AAAA-MM-DD.json` como `{portal: [a_dict] | {"caido": motivo}}`.
  - Después: `git pull --rebase` → commit → push (3 reintentos) → `gh workflow run diario.yml`.
  - Con `--seco`, no hace git.

- [ ] **Paso 1**: volcar el DOM real de cada portal con Edge visible (lista con los filtros en la URL, si el portal
  los admite, y una ficha) a `tests/fixtures/`. Los tests se escriben contra ese volcado, con el mismo esquema de las
  Tareas 4-6, incluido `test_garaje_en_descripcion`. Si sale captcha, se lanza `PortalCaido`.
- [ ] **Paso 2**: FALLA → implementar → PASA. Rellenar `BARRIOS["idealista"]` y `BARRIOS["yaencontre"]`.
- [ ] **Paso 3**: `test_pc_seco_escribe_json`, con páginas falsas.
- [ ] **Paso 4**: `scripts/instalar_pc.py`:
  - comprueba Python 3.12, `pip install -r requirements-pc.txt`, Edge, `git` con remoto, `gh auth status`, y para cada
    falta dice cómo arreglarla;
  - crea dos tareas con `schtasks`: «Pisos Almería - diario», `/SC DAILY /ST 09:00`, y «Pisos Almería - al iniciar»,
    `/SC ONLOGON` con 5 min de retraso. Las dos ejecutan `pythonw -m pisos.pc` con el directorio del repo y solo con la
    sesión iniciada, porque Edge tiene que ser visible;
  - termina con `python -m pisos.pc --seco` y enseña cuántos pisos ha leído;
  - se puede relanzar sin duplicar las tareas (`/F`).
- [ ] **Paso 5**: ejecutar el instalador en esta máquina y una pasada real sin `--seco`. Comprobar que el workflow se
  dispara y que la página enseña algún piso de Idealista, si alguno cumple. Si ninguno cumple, comprobarlo con el
  JSON de `data/pc/`.
- [ ] **Paso 6**: commit: `feat: recogida de Idealista y yaencontre desde el PC con tarea programada`.

### Tarea 11: Guía, alta de correo y cierre

**Ficheros**: modificar `README.md`.

- [ ] **Paso 1**: README con:
  - qué hace y por qué está repartido (tabla medida de portales);
  - cómo crear el Gmail remitente, la verificación en dos pasos y la contraseña de aplicación;
  - cómo poner los 4 secrets (`gh secret set …`);
  - cómo instalar la parte del PC (`python scripts/instalar_pc.py`);
  - **cómo crear Belén su alerta de Idealista** con los mismos filtros;
  - cómo cambiar el ritmo a cada 2 días (`cron "0 6 */2 * *"`), los criterios (`config.py`) y desactivar un portal;
  - qué hacer cuando llega un correo de aviso.
- [ ] **Paso 2**: cuando Miguel haya puesto los secrets, `gh workflow run diario.yml` y comprobar en el log que se
  envía el correo, y que Belén lo recibe (preguntárselo a Miguel). Para probar el correo de avisos, lanzar una vez
  con la variable `PISOS_FORZAR_AVISO=1` (tiene su test).
- [ ] **Paso 3**: `pytest` completo en verde. Commit: `docs: guía de instalación y uso`.

---

## Autorrevisión (20/11/2026)

- **Cobertura del diseño**:
  - criterios → T3;
  - garaje en la descripción → T2, T3 y T4-6/T10;
  - zonas agrupadas → T3;
  - por confirmar → T3 y T8;
  - duplicados → T7;
  - un portal caído no borra → T7;
  - correo solo con nuevos → T8 y T9;
  - avisos solo a Miguel → T8 y T9;
  - remitente nuevo → T11;
  - repositorio público con secrets → T1 y T9;
  - noindex → T8;
  - retirados a los 3 días → T7;
  - si GitHub está bloqueado, el portal va al PC → T1 y T3;
  - Milanuncios prescindible → T3 y T6;
  - qué se guarda → T2 y T7;
  - fallos del PC → T10 (`{"caido": …}`) + T7;
  - 60 días → T9;
  - instalador y guía → T10 y T11;
  - alerta de Idealista → T11.
- **Pendiente del dueño**: la dirección de `CORREO_AVISOS` y el alta del Gmail remitente (T11). Nada de lo anterior
  bloquea las Tareas 1-10.
