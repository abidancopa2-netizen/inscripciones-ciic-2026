# Sprint 5 · Tema CIDEIC, aviso de privacidad final, equipo y ensayo

Probado en el entorno de diseño (PostgreSQL 16, con navegador): **364 de 364**, 1 omitida (la página publicada, que solo se prueba contra GitHub Pages). Lo corrí desde cero y sobre una copia del estado 4.1 con esta entrega aplicada.

**No hay migración.** La base sigue en `5.5-s4.1` en los dos proyectos. **PRODUCCIÓN no se toca** en este sprint.

## Qué trae

| Parte | Qué hace |
|---|---|
| **Tema CIDEIC** en `docs/tema/` | El CSS y los scripts del tema de tus dos demos (participante v3.1 y panel v1.2), más 14 imágenes `.webp` (unos 220 KB). `index.html` y `panel.html` solo **agregan** líneas: el enlace al CSS, la escena, el logo, el botón de modo y el script. No cambia ningún id ni `data-*`, y la lógica de las páginas es la del 4.1. `local/armar_demos.py` mete el tema dentro de las demos de un solo archivo |
| `sprints/sprint-5/configurar.py` | Pone en **tu** `docs/config.js` el nombre del congreso, el contacto de WhatsApp y el aviso de privacidad final. No va en el manifiesto porque ese archivo es tuyo. Solo cambia esos tres valores: si fuera a tocar `MODO`, `API_URL`, `ANON_KEY`, `SUPABASE_JS` o su SRI, se detiene sin escribir. Sin `--aplicar`, solo muestra el cambio y el texto del aviso |
| Tester | Rampa en Q y avisos por fallas de conexión desde la PC (tabla de abajo) |
| `sprints/sprint-5/GUIA.md` | **B:** cómo invitar al equipo. **C:** el ensayo con 10 personas, con guion, el grupo de WhatsApp de ensayo y dos procedimientos: verificar una solicitud para entrar a un grupo y reenviar una confirmación perdida. **D:** qué datos reales preparar para la apertura |
| Documentación | §11.3 con el aviso final y lo que conviene confirmar con la UCSM; §24 con las decisiones; `LEEME-DISENO` §2.1 (cómo está armado el tema); `PLAN.md`; `CLAUDE.md` |

## Respuestas al reporte del 4.1

| Del reporte | Qué hace esta entrega |
|---|---|
| Desde la PC, 1 falla de TLS en Q (329/330), que no se repitió | **(1)** Las personas de Q llegan repartidas en 1 s (`--rampa-q`), igual que en W. **(2)** Contra Supabase **desde una PC**, dos casos pasan de FALLA a **OMITE con "AVISO"**: el tiempo de Q o W que se pasa **solo** por errores de conexión del equipo, y hasta un 2 % de personas sin conexión después de 3 min de reintentos, siempre que **ninguna** haya recibido "ocupado" ni otro error de la base. En GitHub y en local todo sigue contando como FALLA: GitHub es la medición de referencia |
| Umbral de la alerta | Se queda en **2000**, sin campo en el panel (decisión del propietario) |
| ¿El panel v1.2 cubre lo agregado en s4 y s4.1? | Sí. Sistema muestra con el tema el respaldo, vaciar, importar y pasar a producción. El botón de respaldo sigue bajando un archivo que `restaurar.py --verificar` da por íntegro, y las tarjetas plegables no molestan al tester (364/364) |
| `CONTACTO` y `NOMBRE_EVENTO` | Los pone `configurar.py`. El nombre queda "VII Congreso Internacional de Estudiantes de Ingeniería Civil · CIDEIC", igual que el logo. Probé que entra sin desbordar en 390 px, en los dos modos |

## Cómo aplicarlo y probarlo

**1 · En local (🤖)**

```bash
python sprints/sprint-5/aplicar.py                               # copia los archivos y vuelve a armar las demos con el tema
python supabase/instalar.py --dsn "dbname=ciic" --verificar     # debe decir "Pendientes: ninguna" (5.5-s4.1)
python sprints/sprint-5/configurar.py                            # muestra el cambio y el texto del aviso; no escribe
```

👤 El propietario ya aprobó el texto del aviso en la conversación de diseño. La vista previa termina con la **huella del texto del aviso: debe ser `934770277ce4`**. Si coincide y el propietario lo confirma:

```bash
python sprints/sprint-5/configurar.py --aplicar     # escribe config.js, guarda el anterior y vuelve a armar las demos
```

Luego reinicia el servidor local y corre el tester con `--web`, como en el 4.1. Debe dar 364 de 364.

`config.js` sigue apuntando a PRUEBA. Solo cambian el nombre, el contacto y el aviso. **Anota su huella nueva en el reporte**: será la `base` de la próxima entrega que lo toque, la de la apertura.

**2 · En PRUEBA (🤖)**

1. `instalar.py --dsn "$DSN_PRUEBA" --confirmar "$REF_PRUEBA" --verificar` → "Pendientes: ninguna". No hace falta instalar nada.
2. Commit y push: `docs/index.html`, `docs/panel.html`, `docs/tema/` (4 archivos y 14 imágenes), `docs/config.js` y los demás archivos de la entrega. Si la app bloquea el push, dale el comando al propietario.
3. Cuando GitHub Pages publique (1 o 2 minutos), corre el tester contra PRUEBA desde la PC, con `--dsn` y con `--web` apuntando a la página publicada. Q y W van completos: si fallan conexiones de la PC, ahora aparecen como AVISO y no como FALLA. Anota cuántas hubo.
4. GitHub → "Tester del sistema" (completo, 150, W 1000). Es la medición de referencia.
5. 👤 Abre las dos páginas publicadas en tu teléfono y en la computadora: modo claro y oscuro, el aviso de privacidad (enlace en la pantalla 2) y el pie con el WhatsApp.

**3 · Equipo y ensayo (👤 y 👥, con `GUIA.md`)**

- **Parte B:** invitas tú en Supabase (PRUEBA): 2 admin y 4 operadores. Los correos del equipo no pasan por el chat ni por Claude Code.
- **Parte C:** ensayo con 10 personas, el 10/11. Al final, PRUEBA queda como estaba, y de paso ensayas la carga de datos de la apertura.
- El reporte del ensayo va a la conversación de diseño con la plantilla de la guía.

**4 · En PRODUCCIÓN:** nada en este sprint.

## Qué esperar

| Medida | Entorno de diseño | En Supabase (para el reporte) |
|---|---|---|
| Versión | `5.5-s4.1`, sin migración | Igual en los dos proyectos |
| Tester local | 364 de 364, 1 omitida | — |
| Página publicada | — | El tema en las dos páginas, `NOMBRE_EVENTO` nuevo y el aviso sin `[corchetes]` (el tester lo revisa en la página publicada) |
| Q y W desde la PC | — | En verde, o con AVISO si fallan conexiones del equipo. Ningún "ocupado" |
| GitHub | — | En verde, como en el 4.1 (294/294) |

## Si algo sale mal

- `python sprints/sprint-5/configurar.py --revertir` devuelve solo tu `config.js` como estaba. La copia queda en `sprints/sprint-5/anteriores/`, que no se sube a GitHub.
- `python sprints/sprint-5/aplicar.py --revertir` restaura todo: los archivos del proyecto y también `config.js`.
- No hay nada en la base que deshacer. El reporte va a la conversación de diseño con el formato de la skill.
