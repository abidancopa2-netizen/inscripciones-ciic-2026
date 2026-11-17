# Sprint 6.4 · Ya inscrito: ver tus grupos

**Excepción §20.1 durante el congreso, decidida por el propietario el 17/11/2026.** Cambio de contrato aprobado (R-16 y R-31). Base: `9d5dba3`.

Quien verifica un documento con una inscripción **CONFIRMADA** ve la pantalla 3 en modo consulta: "Ya estás inscrito. Estos son tus grupos", con sus actividades (tipo, nombre, fecha, horario y lugar) y el botón "Unirme al grupo" de las que tienen entrega ENLACE. **Nunca** muestra el código, el celular, el correo ni el nombre. Con entrega MANUAL, un texto sin el número. Las anuladas no cuentan. Funciona también con las inscripciones **cerradas**, y se puede consultar cuantas veces se quiera.

> ⚠️ **Orden obligatorio: primero el SQL en PRODUCCIÓN y después la página.** Así nunca hay una página nueva con el SQL anterior. Entre los dos pasos, la página publicada (la anterior) sigue mostrando el mismo aviso de siempre: el texto del aviso no cambia.
>
> ⚠️ **No hagas commit ni push hasta el paso C6.** La página se publica recién ahí.

## Qué trae

| Archivo | Cambio |
|---|---|
| `supabase/13_sprint64_ya_inscrito.sql` (**nuevo**) | Versión `5.5-s6.4`. Agrega `privado.ya_inscrito` y redefine `privado.duplicado`: con el código de una inscripción CONFIRMADA (lo que pasa `verificar`), devuelve `duplicado` con `yaInscrito`, `doc`, `etapa` y `actividades`; sin código (lo que pasa `registrar`), el aviso solo, como antes. **`verificar`, `registrar` y `public.api` no cambian.** Se niega con PRODUCCIÓN abierta, va en una transacción, se puede volver a correr y comprueba la integridad |
| `docs/index.html` | Pantalla 3 en modo consulta. Si `registrar` responde "duplicado" (otro dispositivo inscribió el mismo documento), la página vuelve a verificar y muestra los grupos. Modo demo: opción "Pantalla 3 · ya inscrito" |
| `docs/demo/demo-api.js` | Igual que la base |
| `tester/tester.py` | 9 pruebas nuevas en D, L, S y P: la consulta por API y en el navegador, sin datos personales, MANUAL sin enlace ni celular, el mismo enlace de la confirmación, con el sistema cerrado, y una anulada que vuelve al flujo normal. **Modo lectura:** "Página publicada con la consulta" (nueva) y la base en `5.5-s6.4` o posterior |
| `tester/ataque.py` | Bloque 4: verificar un documento inscrito → sus grupos, sin código ni datos personales. Una nota más: las consultas de un inscrito no gastan intentos (riesgo aceptado) |
| `documentacion/…-documentacion.md` | Revisión 15: principio "Sin datos personales por DNI", D1, R-01, R-16, R-31, 10.2, 10.5, 13, 17, 18 y 18.3 (riesgo aceptado nuevo), tester S |
| `sprints/PLAN.md` | Sprint 6.4 |
| `sprints/sprint-6.4/revertir_14.sql` | **Marcha atrás ya probada, no se aplica sola** (`instalar.py` no la ve). Ver "Si hay que volver atrás" |

**Probado en el entorno de diseño** (PostgreSQL 16, con navegador):

| Prueba | Resultado |
|---|---|
| Tester desde cero con `--web` | **399/399**, 1 omitida (antes 390) |
| Tester actualizando desde `5.5-s6` | **399/399**, 1 omitida |
| Tester con la página servida aparte de la API, como en la parte B | **399/399**, 1 omitida |
| Tester en modo lectura | 18 pruebas: "Página publicada con la consulta" y "`5.5-s6.4` o posterior" en verde |
| Ataque `--local` | **45/45**, 7 notas (antes 44/44 y 6) |
| Base `5.5-s6` con 3201 en el padrón, 28 actividades y 720 inscripciones → `5.5-s6.4` | Integridad OK. Las **700** confirmadas responden todas sus actividades completas; 0 respuestas con datos personales; ninguna MANUAL trae enlace; 0 de las 20 anuladas cuentan como inscritas |
| La migración con PRODUCCIÓN abierta | Se niega: "Cierra las inscripciones antes de aplicar esta migración." |
| Aplicarla dos veces | Sin efecto |
| Carrera en el navegador: otro dispositivo inscribe el documento mientras la persona elige | Al confirmar, la página muestra "Ya estás inscrito" con sus grupos |
| `revertir_14.sql` sobre la base con inscripciones | Vuelve el aviso solo (`5.5-s6.4-r`), integridad OK |

## Pasos

Cada paso va en la bitácora de `local-privado/INCIDENCIAS.md`, con fecha y hora. 🤖 Claude Code · 👤 propietario. Si algo no da lo esperado, **detente y reporta**: no improvises.

### A · Local (🤖, unos 10 minutos)

1. Comprueba el sha256 de `sprint-6.4.zip` con el que te dio el propietario. Si no coincide, detente.
2. `git pull` → `9d5dba3`, `git status` limpio, `docs/config.js` en `7f963609c88e`.
3. Descomprímelo en la raíz: queda en `sprints/sprint-6.4/`.
4. `python sprints/sprint-6.4/aplicar.py --verificar` → **1 nuevo, 6 cambian, sin conflictos**. Si se detiene, **no uses `--forzar`**: copia el mensaje al reporte.
5. `python sprints/sprint-6.4/aplicar.py` (rearma las demos: `demo/*.html` cambian).
6. Base local desde cero y tester con `--web`: **399/399, 1 omitida**. Ataque `--local`: **45/45**.
7. **Sin commit ni push.**

### B · PRUEBA (🤖, unos 15 minutos)

El tester y el ataque de GitHub siguen en pausa (#49): todo se corre desde la PC.

1. `python supabase/instalar.py --dsn "$DSN_PRUEBA" --confirmar "$REF_PRUEBA" --verificar` → "Pendientes: 13_sprint64_ya_inscrito.sql".
2. `python supabase/instalar.py --dsn "$DSN_PRUEBA" --confirmar "$REF_PRUEBA"`, y otra vez con `--verificar` → **`5.5-s6.4`, Pendientes: ninguna**, integridad OK.
3. La página nueva todavía no está publicada: sírvela desde la PC, en otra terminal: `python -m http.server 8790 --bind 127.0.0.1 --directory docs`.
4. Tester completo contra PRUEBA, como siempre pero con `--web http://127.0.0.1:8790/` (el tester inyecta la configuración de PRUEBA). **Esperado: 0 fallas** y **9 pruebas más** que la corrida completa del 11/11 (354/354, 6 omitidas), con las mismas omitidas. Si esa corrida fue sin `--web`, son 7 más.
5. Ataque contra PRUEBA: **63/63** (antes 62/62), con 1 nota más.
6. Detén el servidor del paso 3. `instalar.py --verificar` de PRUEBA: **cerrada**. Si quedó abierta, ciérrala desde el panel de PRUEBA.

### C · PRODUCCIÓN (👤 y 🤖, unos 20 minutos; inscripciones cerradas entre C2 y C9)

1. 👤 Sistema → **Respaldo** (#1) y guárdalo en la carpeta de respaldos de PRODUCCIÓN. 🤖 `python supabase/restaurar.py <archivo> --verificar` → íntegro.
2. 👤 Operación → **Cerrar ahora**. Quien esté eligiendo vuelve al inicio; quien consulte con la página anterior sigue viendo el aviso.
3. 👤 Sistema → **Respaldo** (#2, ya cerrado). 🤖 `--verificar` → íntegro.
4. 🤖 `python supabase/instalar.py --dsn "$DSN_PRODUCCION" --confirmar "$REF_PRODUCCION" --verificar` → **`5.5-s6`, Pendientes: 13_sprint64_ya_inscrito.sql, modo PRODUCCION, cerrada**. Si dice otra cosa, detente.
5. 👤 autoriza. 🤖 El mismo comando sin `--verificar`, y después otra vez con `--verificar` → **`5.5-s6.4`, Pendientes: ninguna**, integridad OK. Si la migración falla, no se aplicó nada (es una transacción): detente, 👤 abre y se reporta a diseño.
6. 🤖 **Publicar la página.** `git status`: los 7 archivos de la tabla, `demo/demo-participante.html`, `demo/demo-panel.html` y `sprints/sprint-6.4/` (sin `archivos/` ni `anteriores/`). Commit "Sprint 6.4: ya inscrito, ver tus grupos" y push. Si la app bloquea el push, dale el comando al propietario. Espera a Pages (1 a 3 min) hasta que `curl -s https://inscripciones.viicideic.space/index.html | grep -c 'id="paso-3"'` dé **1**. `config.js` publicado sin cambios: `7f963609c88e`.
7. 🤖 Tester de lectura desde la PC: `--modo lectura`, `--api`/`--anon` de PRODUCCIÓN, `--web https://inscripciones.viicideic.space/`. **Esperado: 18/18** (las 17 de siempre, con "actividades de al menos 2 días" ya en verde, más "Página publicada con la consulta"). Debe decir `5.5-s6.4`.
8. 👤 Prueba en vivo desde un celular, con el documento de alguien del equipo que esté inscrito y dé su permiso: "Ya estás inscrito. Estos son tus grupos", sin su celular, correo ni nombre, y el botón del grupo abre WhatsApp. Si ves la página anterior, recárgala (Pages guarda la copia hasta 10 minutos).
9. 👤 Operación → **Abrir**, si estaba abierta antes del paso 2. Opcional: Respaldo #3.

## Qué esperar

| Paso | Resultado |
|---|---|
| A4 `aplicar.py --verificar` | 1 nuevo · 6 cambian · sin conflictos |
| A6 local | Tester **399/399** (1 omitida) · ataque **45/45** |
| B2 PRUEBA | `5.5-s6.4` · Pendientes: ninguna |
| B4 / B5 PRUEBA | Tester sin fallas (+9 respecto del 11/11) · ataque **63/63** |
| C4 PRODUCCIÓN antes | `5.5-s6` · Pendientes: 13 · PRODUCCION · cerrada |
| C5 PRODUCCIÓN después | `5.5-s6.4` · Pendientes: ninguna · integridad OK |
| C6 página | `id="paso-3"` publicado · `config.js` `7f963609c88e` |
| C7 lectura | **18/18** |

## Si hay que volver atrás

| Qué | Cómo | Efecto |
|---|---|---|
| **Solo la página** (se ve mal o falla) | `python sprints/sprint-6.4/aplicar.py --revertir`, commit y push | Vuelve la página anterior, que funciona con la base nueva: muestra el aviso solo. Los grupos ya no se ven en pantalla, pero la API los sigue devolviendo |
| **Dejar de devolver los grupos** (decisión del propietario) | Copiar `sprints/sprint-6.4/revertir_14.sql` a `supabase/14_sprint64_revertir.sql` y aplicarlo con la secuencia C1 a C5 y C9. Después, también la página | `duplicado` vuelve al aviso solo (`5.5-s6.4-r`). Probado en diseño |
| La migración 13 falló en C5 | Nada que deshacer: no se aplicó. Abrir y reportar | — |

Ninguna marcha atrás borra datos. Los respaldos #1 y #2 quedan por si acaso.

## Riesgo residual (aceptado por el propietario)

- Quien conozca un DNI inscrito (están publicados en las puertas del coliseo) ve **qué actividades eligió esa persona** (fecha, horario y lugar) y los enlaces de sus grupos. Esas consultas **no cuentan para los límites**: contarlas bloquearía la red wifi del coliseo con la gente legítima.
- Nunca se ven el código, el celular, el correo ni el nombre.
- Entrar a un grupo sigue pidiendo la aprobación del moderador, que comprueba el celular en el panel ("Verificar una solicitud").

## Reporte

Con el formato de la skill `ciic-desarrollo`: huella del ZIP, `aplicar.py`, tester local, ataque local, PRUEBA (`instalar`, tester, ataque), PRODUCCIÓN (respaldos, `instalar` antes y después, commit, página publicada, tester de lectura), la hora de cierre y de apertura, y las entradas de la bitácora (por fecha y hora). Sin datos de personas ni claves.
