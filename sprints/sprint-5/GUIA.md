# Sprint 5 · Guía del equipo y del ensayo con 10 personas

👤 = lo haces tú (propietario) · 🤖 = lo hace Claude Code · 👥 = el equipo o los voluntarios.

Todo esto ocurre en **PRUEBA**, con la base ficticia. Las cuentas de PRUEBA no sirven en PRODUCCIÓN: allí el equipo se invita de nuevo en el Sprint 6 (parte D).

## A · Antes de empezar (🤖)

1. Aplicar el Sprint 5 según su `LEEME.md`: local, PRUEBA, commit y push.
2. Confirmar en el panel publicado que se ven el tema nuevo y el aviso de privacidad final, sin `[corchetes]`.

## B · Invitar al equipo en PRUEBA (👤, 15 minutos)

Equipo: tú como propietario, **2 admin** y **4 operadores**.

| Rol | Qué puede hacer |
|---|---|
| Operador | Buscar por documento o celular, ver participantes y listas, marcar "en el grupo", exportar listas, verificar solicitudes para entrar a un grupo y reenviar una confirmación perdida (procedimientos 1 y 2, en la parte C) |
| Admin | Lo del operador, más: anular, inscribir o cambiar a mano, ampliar cupos con su llave, crear y editar actividades, agregar al padrón, cerrar las inscripciones |
| Propietario (solo tú) | Todo: abrir, etapas, horarios (mismo día y margen), equipo, respaldo, importar, vaciar y pasar a producción |

1. 👤 En Supabase, proyecto **PRUEBA** → Authentication → Users → **Invite user**. Una invitación por persona, con **su** correo. No compartas cuentas: la bitácora registra quién hizo cada cosa.
2. 👥 Cada persona abre el correo **una sola vez**: el enlace sirve una vez. Crea su contraseña (12 caracteres o más) y registra el código QR en Google Authenticator o Microsoft Authenticator. Verá "Tu cuenta aún no tiene rol": es lo esperado.
3. 👥 Desde ahí, siempre entra por `https://abidancopa2-netizen.github.io/inscripciones-ciic-2026/panel.html` con correo, contraseña y el código de 6 dígitos. Si reabre el correo, el panel le explica que el enlace ya se usó.
4. 👤 En el panel → Sistema → Equipo, asigna el rol de cada persona.
5. 👥 Cada uno vuelve a entrar y comprueba que ve las pestañas de su rol.

Si alguien pierde el teléfono con el autenticador: 👤 desactívalo en Sistema → Equipo, bórralo en Supabase (Authentication → Users) e invítalo de nuevo.

## C · Ensayo con 10 personas (45 minutos, el 10/11)

**Objetivo:** que el equipo practique su parte, y ver la página con gente real en sus teléfonos y redes, no con el tester.

**Quiénes:** tú y el equipo en el panel (en computadora), y **10 voluntarios** como participantes, con su propio celular y sus datos móviles o wifi.

**Documentos para los voluntarios** (son del padrón ficticio, no de personas reales):

| Voluntario | Documento | Etapa | Qué debe pasar |
|---|---|---|---|
| 1 | `32003385` | 1 | Elige el taller del grupo de ensayo, pulsa "Unirme al grupo" y pide entrar. Luego reenvía el enlace del grupo al voluntario 9 |
| 2 | `29445705` | 1 | Elige el taller del grupo de ensayo, pulsa "Unirme al grupo" y pide entrar |
| 3 | `30224031` | 1 | Inscripción normal |
| 4 | `79496093` | 1 | Elige la actividad que el propietario dejó con cupo 3: le debe tocar "lleno" y elegir otra |
| 5 | `34252300` | 1 | Después de inscribirse, vuelve a escribir su documento: debe decir que ya está inscrito. Luego escribe al WhatsApp de contacto y pide "las actividades del documento 32003385" (el del voluntario 1): no debe recibir nada |
| 6 | `49216024` | 1 | Pone el teléfono en modo avión justo después de pulsar "Confirmar" y lo quita a los 5 s: no debe quedar inscrito dos veces |
| 7 | `004893139` | 2 | Inscripción de etapa 2 (sin visitas) |
| 8 | `PA5566778` | 2 | Pasaporte. Elige el taller del grupo de ensayo y, en la confirmación, cierra la página sin captura y sin unirse. Luego escribe al WhatsApp de contacto: "perdí mi confirmación" |
| 9 | `56307322` | 3 | Etapa 3, no habilitada: la página debe explicarlo. Luego usa el enlace que le reenvió el voluntario 1 y pide entrar al grupo: lo deben rechazar |
| 10 | `99999999` | — | No está en el padrón: la página debe explicarlo |

Para los datos de la pantalla 2, cada voluntario usa **su** nombre o uno inventado y un correo de prueba. Los voluntarios **1, 2, 5 y 8** escriben su celular real, porque prueban WhatsApp; los demás pueden inventarlo. Todo se borra al final con "Vaciar". Los enlaces de grupo de PRUEBA son ficticios, salvo el del grupo de ensayo.

### El día anterior: el grupo de WhatsApp de ensayo (👤, 10 minutos)

1. En WhatsApp, crea el grupo "Ensayo CIDEIC" con los 2 admin y los 4 operadores.
2. Info del grupo → Ajustes del grupo → **Aprobar nuevos participantes** → activado. Según la versión de WhatsApp, puede decir "aprobar miembros". Sin esto, quien tenga el enlace entra directo y no hay nada que verificar.
3. Haz **administradores del grupo** a los 6 (Info del grupo → toca a la persona → Designar como admin. del grupo). Solo los administradores ven y aprueban las solicitudes.
4. Info del grupo → Invitar al grupo mediante enlace → copia el enlace.
5. Panel de PRUEBA → Actividades → **Editar** en un taller visible → Entrega: "Enlace en la confirmación" → pega el enlace → Guardar. Anota su código (por ejemplo, `T05`) y díselo a los voluntarios 1, 2 y 8.

### Procedimiento 1 · Solicitud para entrar a un grupo (operadores)

Solo sirve si el grupo tiene **Aprobar nuevos participantes** activado.

1. En WhatsApp: Info del grupo → solicitudes pendientes. Cada solicitud muestra el número de quien pide entrar.
2. Panel → Actividades → **Verificar una solicitud de WhatsApp**: eliges la actividad del grupo y escribes ese número.
3. Si sale inscrito, apruebas y lo marcas "en el grupo" en Listas. Si sale "No hay nadie inscrito…", rechazas.
4. Si la solicitud no muestra el número, no apruebes: recházala y pídele que escriba al WhatsApp de contacto.

### Procedimiento 2 · Alguien perdió su confirmación (quien atiende el WhatsApp de contacto)

La página no vuelve a mostrar una confirmación: con solo un documento, cualquiera vería la de otra persona (R-31). Por eso la reenvía el equipo, y solo a la persona inscrita. El WhatsApp de contacto es el tuyo: atiendes tú, o le pasas a un operador **el número desde el que escriben** y el documento que dan.

1. Pídele su documento.
2. Panel → Participantes → **Buscar** con los **9 últimos dígitos del número desde el que escribe**, no con el documento que te dio.
3. Sigue solo si aparece una inscripción **CONFIRMADO** cuyo celular es ese número y cuyo documento es el que te dio (la búsqueda también encuentra documentos con esos dígitos: mira los dos). Si no aparece o algo no coincide, no le des nada: ni actividades, ni enlaces, ni si ese documento está inscrito. Pídele que escriba desde el celular con el que se inscribió.
4. Con los códigos de sus actividades (por ejemplo, `V03 + T07`), busca en la pestaña Actividades el nombre, la fecha, la hora y el lugar, y respóndele con eso.
5. Para cada grupo:
   - Si en Listas ya figura "✔ en el grupo", díselo.
   - Si la entrega es por enlace, mándale el enlace. Lo copias en WhatsApp (Info del grupo → Invitar al grupo mediante enlace), porque eres administrador del grupo. Cuando lo use, pedirá entrar y se aprueba con el procedimiento 1.
   - Si la entrega es a mano, dile que lo agregarán con ese número.
6. Si ya no tiene el número con el que se inscribió, pasa el caso a un admin, que no le da nada por WhatsApp. El admin le escribe desde logisticacideic@gmail.com **solo al correo registrado**, sin decirle cuál es. Si responde desde ese correo, el admin puede cambiarle el número: **Anular y liberar cupos** y enseguida **Inscribir desde el panel** con el número nuevo y las mismas actividades. Si alguna se llenó en ese momento, el panel ofrece ampliar.

### Guion

| Hora | Quién | Qué |
|---|---|---|
| −15 min | 👤 | Sistema → **Respaldo** (descárgalo). Operación → **Cerrar ahora**. Etapas: 1 y 2. En Actividades, deja **una visita con cupo 3**, para el voluntario 4, y comprueba que el taller del ensayo tiene el enlace del grupo. Decide quién atiende el WhatsApp de contacto. |
| −5 min | 👥 | Los voluntarios abren `https://abidancopa2-netizen.github.io/inscripciones-ciic-2026/` y ven "inscripciones cerradas". El equipo entra al panel. |
| 0 | 👤 | Operación → **Abrir**. Cuenta regresiva en voz alta: los 10 escriben su documento **a la vez**. |
| 0–10 min | 👥 | Cada voluntario completa su caso (tabla de arriba) y hace una captura del comprobante. |
| 10–25 min | 👥 equipo | **Operadores 1 y 2:** las 3 solicitudes del grupo de ensayo, con el procedimiento 1: aprobar a los voluntarios 1 y 2, y rechazar al 9. **Operador 3:** con el procedimiento 2, reenviar la confirmación al voluntario 8 y no darle nada al voluntario 5. **Operador 4:** buscar a 3 voluntarios por documento y por celular; abrir la lista de una actividad, marcar a 2 como "en el grupo" y exportar el CSV. **Admin 1:** anular la inscripción del voluntario 3. **Admin 2:** agregar al padrón el documento del voluntario 10 (`99999999`, etapa 1); inscribirlo a mano en la actividad llena, con la ampliación y su llave; luego cambiarle una de sus actividades. Avísale: su comprobante cambia. |
| 25 min | 👤 | Operación → **Avisar y cerrar** con 2 minutos. Un voluntario intenta inscribirse durante el aviso y después del cierre. |
| 30 min | 👤 | Sistema → **Respaldo**. 🤖 Claude Code lo verifica: `python supabase/restaurar.py <archivo> --verificar`, y `--solo-faltantes --simular` contra PRUEBA (no debería volver nada). |
| 30–45 min | todos | Ronda de comentarios: qué confundió, qué tardó, qué faltó. Anótalo (plantilla abajo). |

Revisen además en los teléfonos: el modo claro y oscuro, el texto del aviso de privacidad (enlace en la pantalla 2) y el pie con el WhatsApp de contacto.

### Después del ensayo: dejar PRUEBA como estaba, ensayando la carga de datos (👤, 10 minutos)

Esto ensaya además el paso de la apertura (§19.7), con los archivos de prueba del repositorio:

1. Sistema → **Respaldo**.
2. Sistema → **Vaciar datos de prueba** → escribe `VACIAR`. Conserva la configuración y el equipo.
3. Sistema → **Importar padrón** → `local/padron_prueba.csv` (3200 personas).
4. Sistema → **Importar actividades** → `local/actividades_prueba.csv` (28 actividades).
5. 🤖 Corre el tester contra PRUEBA: debe quedar en verde.
6. 👤 En WhatsApp, elimina el grupo de ensayo, o saca a los voluntarios y restablece su enlace.

### Qué anotar (para la conversación de diseño)

```
ENSAYO · 10/11/2026 · 10 voluntarios · equipo: 1 propietario, 2 admin, 4 operadores
Casos 1–10: <bien / qué pasó>
Equipo: <qué hizo cada rol y si encontró todo>
WhatsApp: <solicitudes de 1, 2 y 9 bien atendidas; minutos para reenviar la confirmación del 8; qué recibió el 5>
Tiempos: <cuánto tardó la gente de la pantalla 1 al comprobante>
Confusiones: <textos, botones, pasos>
Teléfonos: <modelos o navegadores con problemas>
Pedidos de cambio: <lista corta, por prioridad>
```

No incluyas datos de personas reales, solo los documentos de prueba de la tabla.

## D · Lo que viene en el Sprint 6 (apertura), para que prepares los datos

Datos reales que vas a necesitar:

| Dato | Formato | Cómo prepararlo |
|---|---|---|
| **Padrón** | CSV con 2 columnas: documento y etapa (1, 2 o 3); separador coma, punto y coma o tabulación; hasta 10 000 filas | Desde Excel: Guardar como → CSV UTF-8. Si Excel quitó los ceros de los DNI, no importa: la base los recupera |
| **Actividades** | CSV con encabezado `id;tipo;nombre;lugar;fecha;inicio;fin;cupo;descripcion;entrega;enlace;visible`; fecha `dd/mm/aaaa`, horas `hh:mm` | Mira `local/actividades_prueba.csv` como ejemplo. `visible` = SI para que se vean |
| **Enlaces de WhatsApp** | `https://chat.whatsapp.com/…`, uno por actividad, en la columna `enlace` | Crea un grupo por actividad, igual que el de ensayo: **Aprobar nuevos participantes** activado y el equipo como administradores del grupo. Los enlaces también se pueden pegar después, desde el panel (Actividades → Editar) |

**Cómo cargarlos sin pasarlos por el chat:**

- Los archivos se quedan **en tu computadora**, en una carpeta fuera del repositorio (por ejemplo, Documentos\CIDEIC-datos). Nunca en el chat, en GitHub ni en correos. `.gitignore` ya excluye los `.csv`, `.xlsx` y `respaldo-*.json`, pero fuera del repositorio no dependes de eso.
- Los cargas **tú desde el panel**, en el navegador. Los datos van directo de tu computadora a Supabase.

Orden de la apertura (detallado en la guía del Sprint 6):

1. 🤖 `config.js` pasa a apuntar a PRODUCCIÓN (sigue cerrada).
2. 👤 Tu cuenta de propietario en PRODUCCIÓN.
3. 👤 Invitar al equipo en PRODUCCIÓN.
4. 👤 Sistema → Respaldo → Importar padrón → Importar actividades. El informe dice qué filas no entraron y por qué: corriges el CSV y lo vuelves a importar (lo que ya entró no se duplica).
5. 👤 Revisar actividades, cupos y enlaces → Respaldo → **Pasar a producción** → Respaldo.
6. 🤖 Tester en modo lectura → congelamiento → 👤 **Abrir** a la hora anunciada.
