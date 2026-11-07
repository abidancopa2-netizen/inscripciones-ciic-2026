# Sprint 5.1 · Correcciones antes del ensayo: aviso, redes en el panel y fuente local

Probado en el entorno de diseño (PostgreSQL 16, con navegador): **383 de 383**, con 1 omitida (la página publicada, que solo se prueba contra GitHub Pages). Lo corrí desde cero, y también actualizando una base del Sprint 5 con datos a la migración 10. El Sprint 5.1 agrega 19 pruebas: el bloque AL, 2 niveles nuevos y 2 pruebas de navegador.

**Migración 10** (versión `5.5-s5.1`). En este sprint va **solo a PRUEBA**. A PRODUCCIÓN se instala en el Sprint 6, si el ensayo sale bien, y hasta entonces ahí no se toca nada.

## Qué trae

| Parte | Qué hace |
|---|---|
| `supabase/10_sprint5_redes.sql` | **(1)** Los intentos fallidos (IP de la red e identificador del navegador) se borran en cuanto termina su ventana de 10 min. Lo hace la consulta `estado`, que las páginas repiten cada 20 s, de a una por vez y con `SKIP LOCKED`: nunca espera ni hace esperar a nadie. **(2)** Las acciones `panel_redes` (admin) y `panel_liberar_red` (propietario, queda en la bitácora). La IP sale de la base enmascarada (`190.234.•.•`) y con un id opaco: la completa nunca sale. **(3)** El límite por red queda en **300** si seguía en 30. **(4)** El mensaje de error del correo dice "correo electrónico" |
| Panel | En Operación, la tarjeta **"Redes con intentos fallidos"** (admin y propietario): muestra IP enmascarada, fallos, % del límite, minutos para que se reinicie y estado (normal, cerca o frenada). La franja de arriba avisa al 80 % y cuando una red se frena. "Liberar red" y los límites (red y dispositivo) los cambia el propietario y valen de inmediato. En la demo, "Ver estado… → Redes cerca y frenada" muestra cómo se ve |
| `sprints/sprint-5.1/fuente.py` | Baja **una vez** la fuente Saira, la misma que pedía el tema, y la deja en `docs/tema/fuentes/`. `index.html` y `panel.html` ya no llaman a Google. La licencia OFL permite alojarla, y `OFL.txt` va junto a la fuente |
| `sprints/sprint-5.1/configurar.py` | Corrige el aviso en tu `config.js`: la IP solo durante el límite de intentos, GitHub Pages y "correo electrónico". El nombre y el contacto quedan igual. Funciona igual que en el Sprint 5: muestra una vista previa, guarda tu archivo y no toca `MODO`, `API_URL`, `ANON_KEY` ni `SUPABASE_JS` |
| "Correo electrónico" | En el aviso, en la etiqueta y el mensaje de la página y del panel, y en la base |
| "Mantener Supabase activo" | Corre cada hora, en vez de dos veces al día. Así, aunque nadie use la página, los intentos no quedan más de una hora |
| Revisión independiente | Una revisión aparte de la migración encontró que borrar dentro de `contar_llamada` podía hacer esperar a un `verificar` detrás de una llamada larga. Se movió a `estado`, con `SKIP LOCKED`. También se aclaró en el panel que "Liberar red" no libera a un celular que llegó a su propio límite |
| Tester | **(1)** Bloque **AL**: niveles, una red cerca, frenada y liberada, la IP enmascarada, la bitácora y el borrado de ventanas terminadas. **(2)** Desde una PC pasan a **AVISO**, si la base no dio ningún error: T ("las otras 90 reciben lleno") y W ("talleres con cupo de sobra"), cuando lo que falta son personas sin conexión; y AE, que ahora se mide por el tiempo en la base. **(3)** En el navegador: todos los archivos propios cargan y nada llama a Google |
| `sprints/sprint-5/GUIA.md` | Prueba de la red de la UCSM en el campus (con su tabla), correo para TI, caso de freno por red en el ensayo, hora de apertura, quién vigila qué, plan de contingencia y texto de difusión |
| Documentación | R-25 (retención y ventana fija), R-46 nueva, acciones nuevas, aviso 11.3, decisiones del 07/11, `PLAN.md`, `CLAUDE.md` y `LEEME-DISENO` |

## Respuestas al reporte del Sprint 5

| Del reporte | Qué hace esta entrega |
|---|---|
| El aviso decía "IP por unos minutos", pero `intentos` podía guardarla días | Opción (a) del propietario: la migración 10 la borra al terminar la ventana, y "Mantener activo" cada hora cubre las horas sin visitas. El aviso ahora dice que se usan solo para el límite de intentos, que dura 10 minutos, y que después se borran automáticamente |
| Google Fonts recibía la IP de cada participante | La fuente queda en `docs/tema/fuentes/`. El aviso nombra GitHub Pages y que los proveedores registran IPs en sus registros técnicos. jsDelivr sigue solo en el panel, con SRI |
| "Correo institucional" en el aviso y en el mensaje | Ahora dice "correo electrónico" en todas partes (no se restringe el dominio, §24) |
| E y AE fallan desde la PC por conexión | La "E" del reporte es el bloque T ("Las otras 90 reciben lleno"). T, W ("talleres con cupo de sobra") y AE quedan como AVISO desde una PC si la base no dio ningún error. AE se mide por el tiempo en la base. En GitHub y en local todo sigue contando como FALLA |
| Logo en móvil: solo el símbolo | Ya muestra "CIDEIC" a 390 px, sin desbordar. La captura se tomó durante la animación de entrada (unos 2 s): primero aparece el símbolo, después la línea y la palabra. No cambia nada |
| Imagen con `src` vacío en el panel | Es el QR del alta del código (`#qr`, dentro de `#alta-totp`, oculto). No tiene `src` hasta que Supabase entrega el QR al registrar el autenticador, y no hace ningún pedido. No cambia nada |
| 3 FALLAS por corrida desde la PC (SSLEOFError) | La base nunca respondió "ocupado" y GitHub dio 0 reintentos. Desde la PC, corre W con `--personas-w 300` (ya mediste que 300 conexiones a la vez dan 0 errores): mide lo mismo sin saturar tu red |

## Cómo aplicarlo y probarlo

**1 · En local (🤖)**

```bash
python sprints/sprint-5.1/aplicar.py                              # copia los archivos y vuelve a armar las demos
python sprints/sprint-5.1/fuente.py                               # baja Saira una vez → docs/tema/fuentes/ (anota sus huellas)
python supabase/instalar.py --dsn "dbname=ciic" --verificar       # debe decir "Pendientes: 10_sprint5_redes.sql"
python supabase/instalar.py --dsn "dbname=ciic"
python sprints/sprint-5.1/configurar.py                           # vista previa del aviso; no escribe
```

👤 La vista previa termina con la **huella del texto del aviso: debe ser `11590a4931c3`**, la que el propietario aprobó en la conversación de diseño. Si coincide y el propietario lo confirma:

```bash
python sprints/sprint-5.1/configurar.py --aplicar                 # escribe config.js (guarda el anterior) y vuelve a armar las demos
```

Después reinicia el servidor local y corre el tester con `--web`: debe dar 383 de 383.

`config.js` sigue apuntando a PRUEBA. **Anota su huella nueva**: es la base de la entrega de la apertura.

**2 · En PRUEBA (🤖)**

1. `instalar.py --dsn "$DSN_PRUEBA" --confirmar "$REF_PRUEBA" --verificar` → "Pendientes: 10_sprint5_redes.sql". Luego, el mismo comando sin `--verificar`.
2. Commit y push: lo de la entrega, `docs/tema/fuentes/` (4 archivos), `docs/config.js` y `.github/workflows/mantener-activo.yml`. Si la app bloquea el push, dale el comando al propietario.
3. Cuando GitHub Pages publique, corre el tester contra PRUEBA desde la PC, con `--dsn`, `--web` (la página publicada) y **`--personas-w 300`**.
   - En el bloque AL, la red de tu PC se frena unos segundos en PRUEBA y se libera sola.
   - Si una carga falla solo por conexión, sale como AVISO: anota cuántos hubo.
4. GitHub → "Tester del sistema" (completo, 150, W 1000). Es la referencia. Ahí, la parte de la red del bloque AL se omite, porque la IP de salida de GitHub puede cambiar entre llamadas.
5. 👤 En el teléfono y en la computadora, revisa:
   - la letra, que debe verse igual que antes;
   - el aviso nuevo, desde el enlace de la pantalla 2;
   - en el panel, Operación → "Redes con intentos fallidos" (sin redes, dirá "Ninguna red con muchos intentos fallidos").

**3 · Red de la UCSM y ensayo (👤 y 👥, con `sprints/sprint-5/GUIA.md`, parte C)**

- Primero, el correo a TI y la prueba en el campus, con su tabla de resultados.
- Después, el ensayo del 10/11, que ahora trae el caso de freno por red.

**4 · En PRODUCCIÓN:** nada en este sprint.

## Qué esperar

| Medida | Entorno de diseño | En Supabase (para el reporte) |
|---|---|---|
| Versión | `5.5-s5.1` (10 migraciones) | PRUEBA en `5.5-s5.1`; PRODUCCIÓN sigue en `5.5-s4.1` |
| Tester local | 383 de 383, 1 omitida | — |
| Límite por red | 300 | 300 en PRUEBA (si estaba en 30) |
| Página publicada | — | Sin llamadas a Google, todos sus archivos cargan, aviso sin `[corchetes]` |
| GitHub | — | En verde. La parte de la red del bloque AL sale omitida |

## Si algo sale mal

- `instalar.py` aplica la migración 10 en una sola transacción: si falla, la base queda como estaba.
- `python sprints/sprint-5.1/configurar.py --revertir` devuelve solo tu `config.js`.
- `python sprints/sprint-5.1/aplicar.py --revertir` restaura los archivos del proyecto, también `config.js`. La fuente no está en el manifiesto: si reviertes, borra `docs/tema/fuentes/`.
- El reporte va a la conversación de diseño con el formato de la skill. Incluye la huella nueva de `config.js`, las huellas de la fuente y los AVISOS desde la PC.
