# Sprint 6 · Apertura de la Etapa 1 (11/11, 20:00)

**Probado en el entorno de diseño** (PostgreSQL 16, con navegador):
- **Tester:** 387 de 387, con 1 omitida (la página publicada, que solo se prueba contra GitHub Pages). Lo corrí desde cero, y también actualizando una base del Sprint 5.1 con datos.
- **Pruebas nuevas:** el Sprint 6 agrega 4: "Copiar mensaje" (2), el doble toque y los apellidos con caracteres raros.
- **Modo lectura con `--web`:** también su caso contrario. Con otro proyecto y con la clave de prueba visible, las 3 pruebas fallan, como deben.
- **`configurar.py`, contra una PRODUCCIÓN simulada:** abierta, con versión vieja, con otro `config.js`, aplicar, repetir y revertir.
- **Migración 12:** sin pg_cron (la base local: avisa y no falla) y con un pg_cron de imitación (programa los 2 trabajos, y se puede volver a correr). Una revisión independiente de la migración, con la documentación de Supabase, no encontró nada bloqueante. Agregué lo que propuso: los avisos de pg_cron se muestran, un trabajo diario borra el historial de pg_cron de más de 7 días, y `instalar.py --verificar` dice si la limpieza corre de verdad.
- **Prueba de ataque, en local:** resistió 44 de 44, con 6 notas, en 16 s.

**Migraciones 11 y 12** (versión `5.5-s6`): van a PRUEBA el **lunes 09/11**. A PRODUCCIÓN van ese mismo día, junto con la 10, que todavía no tiene. **Todo el SQL de PRODUCCIÓN de este sprint va el 09/11**: el congelamiento empieza el 10/11 a las 20:00 (24 h antes de abrir).

El orden de todo, con las horas y lo que hace cada uno, está en `sprints/sprint-6/GUIA.md`; las ventanas del congelamiento están al principio. Este archivo es la parte de Claude Code. **Cada paso va en la bitácora de `local-privado/INCIDENCIAS.md`.**

## Qué trae

| Parte | Qué hace |
|---|---|
| `supabase/11_sprint6_textos.sql` | Los textos que escribe la gente ya se guardaban sin caracteres de control y sin `= + - @` al inicio. Son los nombres, apellidos y correo, y los textos de actividades y padrón. Ahora, además, se guardan sin caracteres invisibles ni de dirección (`U+200B…`, `U+202E…`). Lo encontró la prueba de ataque: esos caracteres se guardaban tal cual, y un `U+202E` invierte cómo se ve el texto en el panel y en la exportación (R-47) |
| `supabase/12_sprint6_limpieza_programada.sql` | **Incidencia #40.** La base misma, con pg_cron, borra los intentos terminados cada 5 minutos. Una fila dura a lo más su ventana de 10 minutos, más 5, sin depender del horario de GitHub. Un segundo trabajo, diario, borra el historial de pg_cron de más de 7 días. Si pg_cron no se puede activar, la migración no falla: avisa, y todo sigue como hoy. `instalar.py` (también con `--verificar`, que solo lee) dice si la limpieza está activa, cuándo corrió por última vez y cuántos intentos viejos quedan |
| `sprints/sprint-6/configurar.py` | Pasa `docs/config.js` a PRODUCCIÓN. **(1)** Lee la URL y la clave de `.env.local`: no pasan por el chat. **(2)** Comprueba que esa API responde, que está en `5.5-s6` y que está **cerrada**. **(3)** Muestra el cambio con los valores tapados. **(4)** Cambia solo `API_URL` y `ANON_KEY`, y agrega `PANEL_PRUEBA: false`. **(5)** Se niega si tu `config.js` no es el `fa8884d5a6f7` del Sprint 5.1, si los datos son los de PRUEBA o si algo más cambiaría: el aviso, `MODO`, `SUPABASE_JS` o el SRI. **(6)** Guarda una copia del anterior para `--revertir` |
| Panel | **(1)** Con `PANEL_PRUEBA: false`, el panel no muestra "Entrar con la clave de prueba". **(2)** En Operación → Buscar, cada inscripción confirmada tiene **"Copiar mensaje"**. Pregunta si la persona escribe desde su celular y dio su documento, y copia la confirmación con las actividades y los enlaces de sus grupos. Así se responde a quien perdió la suya. **(3)** "Guardar" en Nueva actividad ya no crea dos con un doble toque. **(4)** El panel no se deja abrir dentro de un marco de otro sitio (clickjacking) |
| `tester/tester.py` | **(1)** En modo lectura con `--web`, **sin inyectar `config.js`**, mira el tráfico real del navegador. La página y el panel publicados deben llamar solo al proyecto de `--api`, el panel no debe ofrecer la clave de prueba y la base debe estar en `5.5-s6`. Es la comprobación que faltó en el caso `f73da2e`. **(2)** Se niega a correr pruebas completas si `config.js` ya apunta a PRODUCCIÓN y no le pasas `--api`. **(3)** Tapa la IP del runner en la salida (`20.12.•.•`). **(4)** Prueba "Copiar mensaje", el doble toque y los apellidos con caracteres raros |
| `tester/ataque.py` | La prueba de ataque, **solo contra PRUEBA**. Se niega si la base está en modo PRODUCCION o si la API es la de `config.js` en PRODUCCIÓN. Tiene 8 bloques (lista abajo), dura de 3 a 5 minutos, deja PRUEBA como estaba y escribe `resultados/ataque/ataque.md`, fuera de Git |
| `.claude/skills/ciic-desarrollo` | **Al día para Windows:** las variables `PGHOST`, `PGUSER`, `PGCLIENTENCODING=UTF8` y `PYTHONUTF8=1`, y rutas en `resultados/` en vez de `/tmp`. Además: `--personas-w 300` desde la PC, la bitácora en `INCIDENCIAS.md`, el modo lectura, la prueba de ataque, el congelamiento y el formato de reporte con las 3 corridas |
| `.gitattributes` | `.woff2`, `.webp` e `.ico` se declaran binarios. Git ya no los toca, y su huella es la del archivo tal cual |
| "Mantener activo" | Sigue redirecciones (`curl -L`), por si se usa el dominio propio. Queda solo para que Supabase no pause los proyectos |
| `sprints/sprint-6/GUIA.md` | **(1)** Fechas y ventanas del congelamiento. **(2)** Correo propio de Supabase (bloqueante) y ajustes de Auth. **(3)** Las 3 fases y las cuentas. **(4)** Qué hacer si el ensayo encuentra un problema, y la decisión de seguir o no el 11/11 a las 11:30. **(5)** Carga, Pasar a producción y apertura. **(6)** El dominio opcional con su plan B. **(7)** El incidente del TOTP. **(8)** El texto de difusión. **(9)** El cronograma |
| `sprints/sprint-5/GUIA.md` | "Perdí mi confirmación" ahora usa "Copiar mensaje", y "Buscar" está en la pestaña **Operación** |
| Documentación | Revisión 12: R-25 (limpieza con pg_cron), R-37 (panel publicado), R-47 nueva (textos limpios), §19.8 (borrar a más tardar el 19/02/2027), §20.1 (congelamiento de la apertura), §21.1 ("Mantener activo"), §22.3 y §22.4 (prueba de ataque) y §23 (fechas). También `PLAN.md` y `CLAUDE.md` |

## Respuestas a las dudas del reporte del 5.1 y a la incidencia #40

| Duda | Respuesta |
|---|---|
| Las huellas de los `.woff2` que mostró `fuente.py` no coincidían con las tuyas | `fuente.py` mostraba la huella "normalizada" (cambiando `\r\n` por `\n`), que en un binario no tiene sentido. `aplicar.py` acepta las dos, por eso no falló. **Las tuyas, del archivo tal cual, son las buenas:** OFL.txt `f2665d4718b4`, saira.css `2995707617c1`, saira-latin-ext.woff2 `b2494ed89408` y saira-latin.woff2 `d5f1ee1ce85a`. Desde ahora, los manifiestos usan la huella tal cual para los binarios, y `.gitattributes` los declara binarios |
| Si nadie visita la página, los intentos pueden quedar hasta unos 70 minutos | Era correcto. Con la incidencia #40 (GitHub no corre el horario), el tiempo ya no tenía tope. La migración 12 lo resuelve dentro de la base: **a lo más unos 15 minutos**, sin depender de GitHub. El aviso no cambia: dice "después se borran automáticamente", y ahora es así aunque nadie visite la página |
| La IP del runner sale completa en el registro de GitHub | Ahora el tester la tapa (`20.12.•.•`), también en IPv6. No es la IP de una persona (es una máquina de GitHub), pero el registro es visible para quien tenga acceso al repositorio |
| Incidencia #40 · "Mantener activo" sin corridas por horario desde `f938b63` | El horario de GitHub es de mejor esfuerzo: puede atrasarse horas o saltarse. Para la pausa de Supabase (7 días sin actividad) el riesgo es bajo, y más con las inscripciones abiertas. Revisa una vez que el flujo diga **active**: `gh workflow list` o Actions → "Mantener Supabase activo", sin el aviso de desactivado. Si en una semana no corrió solo, córrelo a mano y anótalo |

## Fase 1 · lunes 09/11 · local, PRUEBA y PRODUCCIÓN (🤖)

Antes de esto, el propietario registra de nuevo su autenticador de PRUEBA (GUIA, parte 7) y configura el correo propio y Auth (partes 1 y 2).

**1 · En local**

```bash
python sprints/sprint-6/aplicar.py                              # copia los archivos y vuelve a armar las demos
python supabase/instalar.py --dsn "dbname=ciic" --verificar     # "Pendientes: 11_sprint6_textos.sql, 12_sprint6_limpieza_programada.sql"
python supabase/instalar.py --dsn "dbname=ciic"                 # al final: "esta base no tiene pg_cron (normal en local)…"
```

Reinicia el servidor local y corre el tester con `--web`, como dice la skill: debe dar **387 de 387** (1 omitida). Luego, la prueba de ataque en local:

```bash
python tester/ataque.py --api http://127.0.0.1:8787 --anon local --key "$CLAVE" --local --web http://127.0.0.1:8787/
```

Debe decir **"Resistió 44 de 44 ataques"**, con 6 notas.

`docs/config.js` **no cambia en esta fase**: sigue en PRUEBA, con huella `fa8884d5a6f7`.

**2 · En PRUEBA**

1. `instalar.py --dsn "$DSN_PRUEBA" --confirmar "$REF_PRUEBA" --verificar` → "Pendientes: 11_sprint6_textos.sql, 12_sprint6_limpieza_programada.sql". Luego, el mismo comando sin `--verificar`. Al final debe decir **"Limpieza programada de intentos: activa, \*/5 \* \* \* \* · todavía sin corridas"**.
   - **10 minutos después,** el mismo comando con `--verificar` (solo lee) debe decir "última corrida: succeeded hace … min · intentos terminados hace más de 10 min: 0". Eso prueba que corre en Supabase.
   - Si dice "NO programada" o "pg_cron NO está activo", no es bloqueante: todo sigue como hoy. Copia al reporte la línea y el aviso que mostró `instalar.py`.
2. Commit y push de lo de la entrega. Si la app bloquea el push, dale el comando al propietario.
3. Cuando GitHub Pages publique, corre el tester contra PRUEBA desde la PC, con `--dsn`, `--web` (la página publicada) y `--personas-w 300`. No debe haber ninguna FALLA.
4. GitHub → "Tester del sistema" (completo, 150, W 1000).
5. **Prueba de ataque en PRUEBA.** PRUEBA tiene que estar **abierta**: pídele al propietario que la abra en el panel (Operación → Abrir), y que la cierre al terminar.
   ```bash
   python tester/ataque.py --api <URL de PRUEBA> --anon <ANON_KEY de PRUEBA> --key "$ADMIN_KEY" --web https://abidancopa2-netizen.github.io/inscripciones-ciic-2026/
   ```
   - **Valores:** son los mismos que usa el tester contra PRUEBA. Tómalos de `.env.local`: no van en el chat ni en el reporte.
   - **Duración:** de 3 a 5 minutos. Durante el bloque 2, la red de tu PC queda frenada en PRUEBA unos segundos; el script la libera al final.
   - **Resultado:** queda en `resultados/ataque/ataque.md`. Al reporte va **cuántos ataques resistió y las notas**.
   - **Si hay una FALLA,** un ataque pasó. **No sigas a PRODUCCIÓN:** copia esa fila al reporte.
   - **Si la única FALLA es "Nadie puede crear su propia cuenta",** falta el ajuste de la GUIA, parte 2. El propietario apaga "Allow new users to sign up" en PRUEBA, y repites la prueba.

**3 · En PRODUCCIÓN: solo si el propietario lo pide en esta sesión, y con la prueba de ataque en verde**

PRODUCCIÓN está en `5.5-s4.1`, vacía y cerrada. Recibe las migraciones 10 a 12 con `instalar.py`, sin ningún otro SQL.

```bash
python supabase/instalar.py --dsn "$DSN_PRODUCCION" --confirmar "$REF_PRODUCCION" --verificar   # "Pendientes: 10_…, 11_…, 12_…"
python supabase/instalar.py --dsn "$DSN_PRODUCCION" --confirmar "$REF_PRODUCCION"
```

Debe terminar con 2 líneas:
- "Listo: versión 5.5-s6 · modo … · integridad OK";
- "Limpieza programada de intentos: activa, \*/5 \* \* \* \* · todavía sin corridas".

**10 minutos después**, o en cualquier momento del 09/11 o del 10/11 **antes de las 20:00**, corre el mismo comando con `--verificar` (solo lee). Debe decir "última corrida: succeeded…".

La migración 10 deja el límite por red en 300. `instalar.py` también dirá "Pendiente: propietario…": eso lo hace el propietario ese mismo día, con la GUIA (parte 4, paso 4). Claude Code no corre esa sentencia.

Si el propietario ya puso `PRODUCCION_API_URL` y `PRODUCCION_ANON_KEY` en `.env.local`, corre también la vista previa:

```bash
python sprints/sprint-6/configurar.py      # no escribe nada
```

Debe decir "PRODUCCIÓN responde · versión 5.5-s6 · cerrada". **No uses `--aplicar` todavía.**

Con esto, PRODUCCIÓN ya tiene todo su SQL. **Desde el 10/11 a las 20:00, Claude Code no corre `instalar.py` en PRODUCCIÓN**, salvo la excepción de §20.1 que autorice el propietario en esa sesión (GUIA, parte 4.1).

## Fase 2 · martes 10/11, después del ensayo · `config.js` a PRODUCCIÓN (🤖)

Empieza cuando el propietario confirma que el ensayo terminó. Debe quedar **antes de las 20:00 del 10/11**. Si el ensayo se atrasó, puede terminar el 11/11 antes de las 09:00: no es SQL, y la carga del 11/11 necesita el panel en PRODUCCIÓN.

1. `python sprints/sprint-6/configurar.py`: la vista previa debe mostrar la huella actual `fa8884d5a6f7`, "PRODUCCIÓN responde · versión 5.5-s6 · cerrada" y solo 3 cambios (API_URL, ANON_KEY y PANEL_PRUEBA).
2. 👤 El propietario lo aprueba. Luego: `python sprints/sprint-6/configurar.py --aplicar`. **Anota la huella nueva.**
3. Commit y push de `docs/config.js` (solo ese archivo).
4. Cuando GitHub Pages publique (mira que el commit aparezca en Actions → "pages build and deployment"):
   ```bash
   python tester/tester.py --modo lectura --api <URL de PRODUCCIÓN> --anon <ANON_KEY de PRODUCCIÓN> --web https://abidancopa2-netizen.github.io/inscripciones-ciic-2026/
   ```
   - **Valores:** son los de `.env.local`. Si se usa el dominio propio, `--web https://inscripciones.viicideic.space/`.
   - **Debe salir todo en verde.** Las 3 pruebas nuevas dicen "index.html publicada llama solo al proyecto de --api", "panel.html publicada llama solo…" y "Panel publicado sin Entrar con la clave de prueba".
   - **Si GitHub Pages todavía sirve la versión anterior,** la prueba falla diciendo que llama a otro proyecto. Espera 2 minutos y repite.
   - **Si sigue fallando:** `configurar.py --revertir`, commit, push y al reporte.
5. Desde aquí, el tester **completo** (en la PC y en GitHub) necesita `--api` y `--anon` de PRUEBA: sin ellos se niega. En GitHub ya los tiene como variables.

**Si el ensayo encontró un problema de la página o del panel** (GUIA, parte 4.1), llega como `sprint-6.x`. Se aplica y se prueba igual: tester en local y en PRUEBA, push y tester de lectura. Hay tiempo **hasta el 11/11 a las 11:00**.

## Fase 3 · miércoles 11/11 (🤖, a pedido del propietario)

Todo lo hace el propietario desde el panel (GUIA, parte 5). Claude Code solo:

1. Verifica cada respaldo: `python supabase/restaurar.py <archivo> --verificar`. Los respaldos **no** se copian al repositorio ni al chat.
2. Después de "Pasar a producción", corre el mismo tester de lectura de la Fase 2: todo en verde.
3. Desde ahí, ningún commit, ni `config.js`, ni SQL hasta el fin del congreso (21/11). Solo `restaurar.py --verificar` y el tester de lectura, si el propietario los pide.

## Prueba de ataque · qué intenta

| Bloque | Qué intenta alguien de afuera |
|---|---|
| 1 · Supabase directo | Leer o escribir las tablas con la clave pública, llamar a funciones privadas, ver el esquema por GraphQL, registrarse sin invitación |
| 2 · Enumerar y saltarse los límites | Probar documentos al azar por encima del límite de la red (y mirar que no salga ningún dato personal), cambiar cabeceras para parecer otra IP, inventar dispositivos |
| 3 · Documentos raros | Vacío, larguísimo, con espacios, SQL, unicode, emojis, NUL, números, objetos |
| 4 · Inscribir de más o duplicar | 20 inscripciones a la vez del mismo documento, repetir, 2 visitas, el mismo día, cruces de horario, una etapa que no abre, reutilizar la solicitud |
| 5 · Campos raros | HTML, fórmulas de hoja de cálculo, caracteres invisibles y de dirección, 5000 letras, celular, correo y país inválidos |
| 6 · Panel sin rol | Las 17 acciones del panel sin sesión, con clave falsa, con sesión sin código, con sesiones falsificadas (`alg: none`, otra firma, `service_role`, vencida) y con un rol menor |
| 7 · Verificar celular y exportar | Sin rol, y cuánto puede consultar un operador (riesgo aceptado: queda en la bitácora) |
| 8 · Enmarcar el panel | Abrir el panel dentro de un marco de otro sitio |

No prueba saturación (DoS): de eso se encarga Supabase, que está detrás de Cloudflare, y el tester ya mide la carga.

## Qué esperar

| Medida | Entorno de diseño | En Supabase (para el reporte) |
|---|---|---|
| Versión | `5.5-s6` (12 migraciones) | PRUEBA y PRODUCCIÓN en `5.5-s6` desde el 09/11 |
| Limpieza programada | Sin pg_cron (normal); con uno de imitación, activa | Activa, cada 5 min, en las dos bases, con una corrida "succeeded" |
| Tester local | 387 de 387, 1 omitida | — |
| Prueba de ataque | 44 de 44 en local, con 6 notas | PRUEBA: **62 de 62**, con 3 notas. Se suman 18 pruebas que solo valen contra Supabase (tablas, GraphQL, registro de cuentas, cabeceras falsas y sesiones falsificadas) y salen 2 que solo valen en local. Las 3 notas son riesgos aceptados |
| `config.js` | — | `fa8884d5a6f7` hasta la Fase 2. Después, la huella nueva que anotes |
| Lectura publicada | — | Llama solo a PRODUCCIÓN y el panel sin clave de prueba |

## Si algo sale mal

- **`instalar.py`** aplica las migraciones pendientes en una sola transacción: si falla, la base queda como estaba. La 12 no falla por pg_cron: solo avisa.
- **`python sprints/sprint-6/configurar.py --revertir`** devuelve `config.js` a PRUEBA. Luego, commit y push.
- **`python sprints/sprint-6/aplicar.py --revertir`** restaura los archivos del proyecto. Si ya corriste `configurar.py --aplicar`, también devuelve `config.js` a PRUEBA.
- **Quitar la limpieza programada** (no debería hacer falta) son 2 sentencias en PRODUCCIÓN. Solo fuera del congelamiento y a pedido del propietario: `select cron.unschedule('ciic-limpiar-intentos'); select cron.unschedule('ciic-limpiar-historial-cron');`.
- **El reporte** va a la conversación de diseño con el formato de la skill (actualizada en este sprint). Incluye:
  - las cifras de cada fase;
  - la línea de la limpieza programada;
  - la huella nueva de `config.js`;
  - el resumen de `ataque.md`;
  - los números de la bitácora.

  Nunca lleva datos de personas, claves ni respaldos.
