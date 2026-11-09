# Sprint 6.2 · Correo institucional en la página, y el equipo de 21

**Reemitido el 08/11:** reemplaza al 6.2 anterior (77 303 bytes, `3578738e…`). Si ese ya estaba aplicado, este se aplica encima sin conflictos ("igual" o "incorpora").

Pedido del ensayo del 08/11. Entrega chica, **sin SQL** (la base sigue en `5.5-s6`) y **sin `docs/config.js`** (sigue en `fa8884d5a6f7`). El aviso de privacidad no cambia (huella del texto `11590a4931c3`). **Nada en PRODUCCIÓN.**

## Qué trae

| Archivo | Cambio |
|---|---|
| `docs/index.html` | Pantalla 2: el campo del correo se titula **"Correo institucional"** y su ejemplo pasa a `nombre.apellido@estudiante.ucsm.edu.pe`. **La validación no cambia:** se acepta cualquier correo con formato válido (los extranjeros y los de otras universidades usan el suyo; decisión del 07/11). `x@y` sigue sin pasar y `x@y.com` pasa |
| `documentacion/…-documentacion.md` | Revisión 14: D15 y R-25 (la barrera real es el límite por red, #46), 2 filas de §24 (correo y aviso) y el Security Advisor de Supabase como riesgo revisado y aceptado |
| `sprints/sprint-5/GUIA.md` | Parte D: reparto para 2 admin y 18 operadores (coordinadores por bloque, 7 parejas de grupos de WhatsApp, 2 en el WhatsApp de contacto) y la regla "solo los admin exportan" |
| `sprints/sprint-6/GUIA.md` | Parte 2: Rate Limits de Auth en 100 cada 5 min por IP. Parte 4: invitaciones por tandas (30 correos por hora) y compromiso de confidencialidad antes de invitar a PRODUCCIÓN |
| `sprints/PLAN.md` | Sprint 6.2 |

Las demos (`demo/`) las rearma `aplicar.py`. El tester no cambia: sigue en 390 pruebas en local.

## Pasos (🤖 Claude Code, unos 15 minutos)

Cada paso va en la bitácora de `local-privado/INCIDENCIAS.md`, con fecha y hora.

1. Comprueba el sha256 de `sprint-6.2.zip` con el que te dio el propietario. Si no coincide, detente.
2. Descomprímelo en la raíz: queda en `sprints/sprint-6.2/`.
3. `git status`: el 6.1 ya está en un commit (`ece0fb1`). `docs/config.js` en `fa8884d5a6f7`.
4. `python sprints/sprint-6.2/aplicar.py --verificar` → **5 archivos "cambia", 0 nuevos, sin conflictos** (si el 6.2 anterior ya estaba aplicado: `docs/index.html` "igual" y los otros 4 "incorpora" o "cambia"). La base esperada de `docs/index.html` es `bcbdb67ce7ef`. Si se detiene, **no uses `--forzar`**: copia el mensaje al reporte.
5. `python sprints/sprint-6.2/aplicar.py`. Rearma las demos.
6. Base local: `python supabase/instalar.py --dsn "$DSN" --verificar` → "Pendientes: ninguna". Tester local con `--web`: **390/390, 1 omitida** (la página publicada).
7. Commit y push: los 5 archivos, las demos y `sprints/sprint-6.2/` (sin `archivos/` ni `anteriores/`). Si la app bloquea el push, dale el comando al propietario.
8. Tester de GitHub (PRUEBA): **306/306**, como en el 6.1.
9. Cuando GitHub Pages publique (Actions → "pages build and deployment" en verde), avísale al propietario para que vea el cambio en la página de PRUEBA.

## Qué ve el propietario en la página publicada (todavía apunta a PRUEBA)

En una ventana privada, pantalla 2: el título "Correo institucional" y, dentro del campo vacío, el ejemplo `nombre.apellido@estudiante.ucsm.edu.pe`. Si PRUEBA está cerrada, la pantalla 2 no se alcanza: basta con verlo en la demo `demo/demo-participante.html` o abrir PRUEBA un momento desde el panel y cerrarla después.

## Qué esperar

| Paso | Resultado |
|---|---|
| `aplicar.py --verificar` | 5 cambian · 0 nuevos · sin conflictos |
| `instalar.py --verificar` (local) | Pendientes: ninguna · `5.5-s6` |
| Tester local con `--web` | **390/390**, 1 omitida |
| Tester de GitHub (PRUEBA) | **306/306** |
| `docs/config.js` | Sin cambios: `fa8884d5a6f7` |

## Si hay que volver atrás

`python sprints/sprint-6.2/aplicar.py --revertir`, el tester local, commit y push. La página vuelve a decir "Correo electrónico". La base no cambia.

## Reporte

Con el formato de la skill `ciic-desarrollo`: huella del ZIP, `aplicar.py`, tester local, tester de GitHub, commit y entradas de la bitácora (por fecha y hora). Sin datos de personas ni claves.
