# Sprint 6.1 · Recuperar la contraseña con el autenticador, y la configuración a la vista

**Reemitido el 08/11:** reemplaza al 6.1 anterior (sha256 `15e3627d…`). Si ese ya estaba aplicado, este se aplica encima sin conflictos: `aplicar.py` lo reconoce y lo marca "incorpora".

Entrega chica, **sin SQL**: la base sigue en `5.5-s6`. No toca `docs/config.js`.

**Cuándo:** después de las migraciones 10 a 12 en PRODUCCIÓN (Fase 1 del Sprint 6), **antes de invitar al equipo en PRUEBA** y antes del congelamiento (10/11, 20:00).

## Qué trae

| Archivo | Cambio |
|---|---|
| `docs/panel.html` | Con el autenticador activo, el enlace de "¿Olvidaste tu contraseña?" pide **primero el código de 6 dígitos** (la sesión pasa a nivel `aal2`) y **después** la contraseña nueva. Luego entra al panel sin pedir el código otra vez. Antes, Supabase respondía "AAL2 session is required to update email or password when MFA is enabled" (#42). La invitación (cuenta sin autenticador) sigue igual: contraseña y después el QR |
| `tester/tester.py` | El Auth simulado se porta como Supabase: exige `aal2` para cambiar la contraseña de una cuenta con factor, y guarda la sesión con una clave por proyecto, como supabase-js 2.45.4. **3 pruebas nuevas**, solo en local: recuperación con autenticador, invitación, y la sesión de PRUEBA que no se usa cuando `config.js` pasa a PRODUCCIÓN |
| `supabase/instalar.py` | **#44:** `--verificar` y el final de la instalación muestran una línea "Configuración": de dónde sale la IP real, el límite por red, el límite por dispositivo, la ventana, el modo y si está abierta. Solo lee: no cambia cómo instala |
| `.claude/skills/ciic-desarrollo/SKILL.md` | La bitácora se cita por fecha y hora (no se numera); las incidencias, por su número |
| `sprints/sprint-6/GUIA.md` | Parte 1: el correo de Supabase sale de la cuenta Gmail del propietario, y cómo cambiarlo. Parte 3: red de la UCSM probada, correo a TI descartado. Parte 4, paso 5: sesiones al pasar a PRODUCCIÓN. **Parte 4.2 nueva:** contraseña o celular perdidos, sin SQL. Parte 5.1: "Permitir 2 talleres aunque queden visitas" encendido. Parte 10: lo adelantado al fin de semana |
| `sprints/PLAN.md` | Sprint 6.1 |
| `documentacion/…-documentacion.md` | Revisión 13: 12.5, 12.6, 19.8 y 24 |

## Pasos (🤖 Claude Code, unos 25 minutos)

Cada paso va en la bitácora de `local-privado/INCIDENCIAS.md`, con fecha y hora.

1. Comprueba el sha256 de `sprint-6.1.zip` con el que te dio el propietario. Si no coincide, detente.
2. Descomprímelo en la raíz: queda en `sprints/sprint-6.1/` (reemplaza la carpeta del 6.1 anterior, si estaba).
3. `git status`: el Sprint 6 ya está en un commit (`500b111`). `docs/config.js` sigue en `fa8884d5a6f7`.
4. `python sprints/sprint-6.1/aplicar.py --verificar` → **7 archivos, sin conflictos**: "cambia" en todos si el 6.1 anterior no estaba aplicado; si estaba, 2 "igual" (panel y tester), 3 "incorpora" (GUIA, PLAN y doc) y 2 "cambia" (`instalar.py` y la skill). Si se detiene, **no uses `--forzar`**: copia el mensaje al reporte.
5. `python sprints/sprint-6.1/aplicar.py`. Rearma las demos.
6. Base local: `python supabase/instalar.py --dsn "$DSN" --verificar` → "Pendientes: ninguna" y la línea nueva "Configuración: …". Luego el tester local con `--web`, como en la Fase 1: **390 de 390, 1 omitida**. Las 3 nuevas, en la sección del navegador:
   - "Panel: recuperar la contraseña con autenticador pide primero el código y después la contraseña (Sprint 6.1)"
   - "Panel: la invitación crea la contraseña y después muestra el QR del autenticador (como antes)"
   - "Panel: con la sesión guardada de otro proyecto (PRUEBA), pide entrar de nuevo al pasar a PRODUCCIÓN"
7. Commit y push: los 7 archivos, las demos y `sprints/sprint-6.1/` (sin `archivos/` ni `anteriores/`, que Git ignora). Si la app bloquea el push, dale el comando al propietario.
8. Tester de GitHub (PRUEBA): 306/306 como en la Fase 1. Las 3 pruebas nuevas solo corren en local; en GitHub siguen dentro de la omitida "Panel: inicio de sesión con una cuenta sin rol (Auth simulado)".
9. **Lectura de las 2 bases con el `instalar.py` nuevo** (solo `--verificar`, que no cambia nada; PRODUCCIÓN solo con la autorización del propietario en esta sesión). Copia al reporte la línea "Configuración" de cada una:
   - PRUEBA: la IP real que se fijó en el Sprint 3 (se espera `cf-connecting-ip`) · límite por red 300 · por dispositivo 4 · ventana 10 min.
   - PRODUCCIÓN: IP real desde `cf-connecting-ip` · límite por red 300 · por dispositivo 4 · ventana 10 min · **cerrada**. Si dice "auto (pendiente)" o un límite distinto, avísale al propietario antes del congelamiento.

## Prueba real en PRUEBA (👤 propietario, 5 minutos, después del push)

El tester usa un Auth simulado. La prueba con el Supabase de verdad la haces tú, en el panel publicado (todavía apunta a PRUEBA):

1. Espera a que GitHub Pages publique (Actions → "pages build and deployment" en verde) y abre el panel en una ventana privada.
2. Escribe tu correo y pulsa "¿Olvidaste tu contraseña?". Abre el enlace del correo (revisa Spam).
3. Debe mostrar **"Primero, tu código de verificación"**. Escribe el código de tu app (la entrada de PRUEBA).
4. Debe mostrar "Crea tu contraseña". Escribe una nueva de 12 caracteres o más y guarda.
5. Debe entrar al panel y mostrar "Contraseña guardada.", sin pedir el código otra vez.
6. Anótalo en la bitácora. Si algo no coincide, copia el texto exacto del mensaje y tráelo a la conversación de diseño.

Recién entonces, invita al equipo en PRUEBA.

## Qué esperar

| Paso | Resultado |
|---|---|
| `aplicar.py --verificar` | 7 archivos, sin conflictos |
| `instalar.py --verificar` (local) | Pendientes: ninguna · línea "Configuración" |
| Tester local con `--web` | **390/390**, 1 omitida (la página publicada) |
| Tester de GitHub (PRUEBA) | 306/306, como en la Fase 1 |
| "Configuración" de PRUEBA y PRODUCCIÓN | 300 por red · 4 por dispositivo · 10 min · IP real fijada (no "auto"); PRODUCCIÓN desde `cf-connecting-ip` y cerrada |
| Prueba real en PRUEBA | Código → contraseña nueva → entra, con "Contraseña guardada." |
| `docs/config.js` | Sin cambios: `fa8884d5a6f7` |

## Si hay que volver atrás

`python sprints/sprint-6.1/aplicar.py --revertir`, el tester local, commit y push. Todo vuelve al Sprint 6: la recuperación con autenticador vuelve a fallar, y `--verificar` deja de mostrar la configuración. La base no cambia.

## Reporte

Con el formato de la skill `ciic-desarrollo`: huella del ZIP, `aplicar.py`, tester local (cifras y las 3 pruebas nuevas), tester de GitHub, la línea "Configuración" de cada base, el resultado de la prueba real del propietario y las entradas de la bitácora. Sin datos de personas ni claves.
