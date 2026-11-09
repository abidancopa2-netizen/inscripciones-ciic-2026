# Sprint 6.3 · Prueba del 0 en el tester y revisión del CSV del padrón

**Se aplica después de la Fase 2** (PRODUCCIÓN en modo producción) y **antes del congelamiento** (10/11, 20:00). Si no alcanza el tiempo, se deja para después del congreso: no toca nada que vean los participantes.

Entrega chica: **solo el tester y textos**. Sin página, **sin SQL** (la base sigue en `5.5-s6`) y **sin `docs/config.js`** (sigue en `fa8884d5a6f7`). **Nada en PRODUCCIÓN.**

## Qué trae

| Archivo | Cambio |
|---|---|
| `tester/tester.py` | #47. La prueba "enviado como número pierde el 0 y la base lo recupera" usaba el **primer** documento de la muestra de la Etapa 1. Al reimportar el padrón de PRUEBA, ese primero pasó a ser un carné de 9 dígitos que empieza en "00". Como número llega con 7 dígitos y el contrato solo rellena hasta 8 (DNI), así que no puede coincidir. Ahora la prueba toma un **DNI de 8 dígitos que empiece en 0** de la misma muestra. Si no hay ninguno, la prueba se **omite** con su motivo, en vez de fallar. La base y la página no cambian: la página siempre envía el documento como texto |
| `sprints/sprint-6/GUIA.md` | Parte 5.1, paso 0 nuevo: revisión del CSV en Excel antes de importar (columna `documento` como Texto, largos con `LARGO`, duplicados y etapas). Paso 2: cuadrar "N filas leídas" y la suma del informe con las filas del archivo. "Importar padrón" rellena a 8 **sin avisar**, así que un carné que perdió su 0 no aparece en el informe |
| `sprints/PLAN.md` | Sprint 6.3 |

**Probado en el entorno de diseño** (PostgreSQL 16, con navegador):
- Tester desde cero con `--web`: **390/390, 1 omitida** (la página publicada).
- Reproduje la #47 poniendo un carné `00…` de 9 dígitos como primero de la Etapa 1. Así, la prueba anterior da `no_encontrado`. La nueva toma un DNI `0…` de 8 dígitos y pasa. El mismo carné enviado como texto se encuentra.

## Pasos (🤖 Claude Code, unos 10 minutos)

Cada paso va en la bitácora de `local-privado/INCIDENCIAS.md`, con fecha y hora.

1. Comprueba el sha256 de `sprint-6.3.zip` con el que te dio el propietario. Si no coincide, detente.
2. Confirma que la Fase 2 terminó (el propietario te lo dice). Si no, detente: este sprint va después.
3. Descomprímelo en la raíz: queda en `sprints/sprint-6.3/`.
4. `git status`: el 6.2 ya está en un commit (`292a946`). `docs/config.js` en `fa8884d5a6f7`.
5. `python sprints/sprint-6.3/aplicar.py --verificar` → **3 archivos "cambia", 0 nuevos, sin conflictos**. La base esperada de `tester/tester.py` es `4853ea1c54f8`. Si se detiene, **no uses `--forzar`**: copia el mensaje al reporte.
6. `python sprints/sprint-6.3/aplicar.py`. Rearma las demos (no cambian).
7. Base local: `python supabase/instalar.py --dsn "$DSN" --verificar` → "Pendientes: ninguna". Tester local con `--web`: **390/390, 1 omitida**.
8. Commit y push: los 3 archivos y `sprints/sprint-6.3/` (sin `archivos/` ni `anteriores/`). Si la app bloquea el push, dale el comando al propietario.
9. Tester de GitHub (PRUEBA): **306/306**. Si la muestra de PRUEBA no trae ningún DNI de 8 dígitos que empiece en 0, sale **305/305 con esa prueba omitida**, y también está bien. Ninguna de las dos es un fallo.

## Qué esperar

| Paso | Resultado |
|---|---|
| `aplicar.py --verificar` | 3 cambian · 0 nuevos · sin conflictos |
| `instalar.py --verificar` (local) | Pendientes: ninguna · `5.5-s6` |
| Tester local con `--web` | **390/390**, 1 omitida |
| Tester de GitHub (PRUEBA) | **306/306** (o 305/305 con la prueba del 0 omitida) |
| `docs/config.js` | Sin cambios: `fa8884d5a6f7` |

## Si hay que volver atrás

`python sprints/sprint-6.3/aplicar.py --revertir`, el tester local, commit y push. La base y la página no cambian.

## Reporte

Con el formato de la skill `ciic-desarrollo`: huella del ZIP, `aplicar.py`, tester local, tester de GitHub, commit y entradas de la bitácora (por fecha y hora). Sin datos de personas ni claves.
