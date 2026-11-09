# Sprint 5 · Guía del equipo, del ensayo con 10 personas y de la apertura

👤 = lo haces tú (propietario) · 🤖 = lo hace Claude Code · 👥 = el equipo o los voluntarios.

Todo esto ocurre en **PRUEBA**, con la base ficticia. Las cuentas de PRUEBA no sirven en PRODUCCIÓN: allí el equipo se invita de nuevo en el Sprint 6 (parte D).

## A · Antes de empezar (🤖)

1. Aplicar el Sprint 5 y el 5.1 según sus `LEEME.md`: local, PRUEBA, commit y push.
2. Confirmar en el panel publicado que se ven el tema nuevo, la tarjeta "Redes con intentos fallidos" y el aviso de privacidad final, sin `[corchetes]`.

## B · Invitar al equipo en PRUEBA (👤, 15 minutos)

Equipo: tú como propietario, **2 admin** y **4 operadores** en el ensayo. **Para la apertura (08/11): 2 admin y 18 operadores** (21 personas con el propietario); el reparto está en la parte D.

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

### Antes del ensayo: prueba de la red de la UCSM (👤, en el campus, 30 minutos)

**Para qué:** saber antes de la apertura si el Wi-Fi y el firewall de la UCSM dejan pasar el sistema, y si un pabellón entero sale a internet con una sola IP. Es en **PRUEBA** y **sin pruebas de carga**: esas, solo con permiso de TI (el correo para TI está más abajo).

**Necesitas:** 2 celulares (al menos uno con datos móviles), una laptop si puedes (para ver el certificado) y tu cuenta del panel.

En el pabellón de la facultad (y en otro, si quieres comparar), conectado al Wi-Fi de la UCSM:

1. **Red:** si hay más de una red Wi-Fi (estudiantes, invitados, eduroam), prueba cada una. Si aparece una página para iniciar sesión en el Wi-Fi (portal cautivo), anótalo: la gente tendrá que pasarla antes de abrir la inscripción.
2. **Página:** abre `https://abidancopa2-netizen.github.io/inscripciones-ciic-2026/`. Debe cargar completa: paisaje, logo CIDEIC, letra Saira y el botón de modo.
3. **Verificar:** escribe `32003385` (documento ficticio de PRUEBA) y pulsa Verificar. Debe pasar a la pantalla 2 (no confirmes). Anota cuántos segundos tardó, y repite con datos móviles para comparar.
4. **Panel:** abre `https://abidancopa2-netizen.github.io/inscripciones-ciic-2026/panel.html` y entra con correo, contraseña y código. Debe abrir Operación: así se prueban Supabase Auth y jsDelivr.
5. **WhatsApp:** abre el enlace del grupo de ensayo. Debe abrir WhatsApp.
6. **Certificado (inspección SSL):** en la laptop, con Chrome, en la página: ícono a la izquierda de la dirección → "La conexión es segura" → "El certificado es válido" → **Emitido por**. Repite abriendo la dirección `API_URL` de `config.js` (termina en `.supabase.co`): mostrará un error en texto, es normal; lo que importa es el certificado. Si dice una autoridad pública (por ejemplo Google Trust Services, Let's Encrypt, DigiCert o Sectigo), no hay inspección. Si dice Fortinet, FortiGate, Sophos, Palo Alto, Cisco o el nombre de la UCSM, el firewall inspecciona el tráfico: anótalo y pregúntale a TI.
7. **IP pública:** en cada celular, busca "cuál es mi IP" en Google. Anota solo los 2 primeros números, y compara de palabra si los 2 celulares tienen la misma IP completa.
8. **Freno por red:** en el panel, Operación → Redes con intentos fallidos → Límites: **Red = 5** → Guardar.
   - Cada celular escribe 3 documentos que no existen (`11111111`, `22222222`, `33333333`).
   - Con 4 fallos, la red aparece "cerca del límite" y la franja avisa. Con 5, aparece "frenada". Compara la IP enmascarada (`190.234.•.•`) con los 2 números que anotaste.
   - Desde el Wi-Fi, `32003385` debe dar "Hay demasiados intentos fallidos desde tu red". Con datos móviles, debe pasar.
   - Pulsa **Liberar red**: `32003385` vuelve a pasar desde el Wi-Fi.
   - Si los celulares no comparten IP, ninguno llega a 5 y no se frena: eso también es un resultado.
   - **Al terminar: Red = 300 → Guardar.**

| Pabellón | Red Wi-Fi | IP (2 primeros números) | Portal | Carga la página | Verifica DNI (s, Wi-Fi / datos) | Entra al panel | Certificado emitido por | Comparten IP | Se frena con 5 |
|---|---|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |  |  |

**Correo para TI de la UCSM** (envíalo antes de la prueba; completa lo que está entre corchetes):

```
Asunto: VII CIDEIC · Consulta sobre la red de la UCSM para la inscripción en línea

Estimado equipo de TI:

Soy [nombre], de la organización del VII Congreso Internacional de Estudiantes de Ingeniería
Civil (CIDEIC). El [día] a las [hora] abriremos en línea la inscripción a las visitas técnicas
y talleres del congreso. Esperamos que muchos estudiantes se inscriban a la vez desde el
campus, sobre todo desde el pabellón de [facultad], con el Wi-Fi de la universidad.

El sistema usa estos servicios, todos por HTTPS (puerto 443):
- abidancopa2-netizen.github.io: la página de inscripción (GitHub Pages)
- *.supabase.co: la base de datos y el inicio de sesión del equipo (detrás de Cloudflare)
- cdn.jsdelivr.net: una librería que usa solo el panel del equipo organizador
- chat.whatsapp.com: los enlaces a los grupos de cada actividad

Quisiéramos confirmar con ustedes:
1. ¿El Wi-Fi de estudiantes permite el acceso a esos dominios?
2. Entendemos que cada pabellón sale a internet con una sola IP pública. ¿Es así? ¿Hay
   límites de conexiones o de tráfico por usuario, por IP o hacia un mismo destino que
   puedan afectar a cientos de personas a la vez durante unos minutos?
3. ¿El firewall inspecciona el tráfico cifrado (SSL/TLS)? Si es así, ¿podrían exceptuar
   esos dominios durante la inscripción?
4. ¿El Wi-Fi tiene una página de inicio de sesión (portal) que los estudiantes deban pasar?
5. ¿Podemos hacer una prueba corta de carga desde el campus, coordinada con ustedes? Por
   ejemplo, unos 30 celulares a la vez durante 5 minutos, en el horario que nos indiquen.
6. ¿Hay algún mantenimiento previsto para el [día]? ¿A quién podemos llamar durante la
   apertura si notamos problemas de red?

El tráfico de cada persona es liviano: unas pocas consultas pequeñas en pocos minutos.
Si lo necesitan, les enviamos más detalles técnicos.

Muchas gracias,
[nombre] · [cargo en la organización] · [teléfono de contacto]
```

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
2. Panel → Operación → **Buscar, cambiar o anular**, con los **9 últimos dígitos del número desde el que escribe**, no con el documento que te dio.
3. Sigue solo si aparece una inscripción **CONFIRMADO** cuyo celular es ese número y cuyo documento es el que te dio (la búsqueda también encuentra documentos con esos dígitos: mira los dos). Si no aparece o algo no coincide, no le des nada: ni actividades, ni enlaces, ni si ese documento está inscrito. Pídele que escriba desde el celular con el que se inscribió.
4. Pulsa **Copiar mensaje** en su inscripción: te pide confirmar el celular y el documento, y copia un mensaje con sus actividades (nombre, fecha, hora y lugar) y sus grupos. Pégalo en su chat de WhatsApp. (Sin ese botón: con los códigos de sus actividades, busca en la pestaña Actividades el nombre, la fecha, la hora y el lugar.)
5. El mensaje ya trae cada grupo: el enlace (al usarlo, pedirá entrar y se aprueba con el procedimiento 1) o "te agregaremos con tu número". Si en Listas ya figura "✔ en el grupo", puedes decírselo.
6. Si ya no tiene el número con el que se inscribió, pasa el caso a un admin, que no le da nada por WhatsApp. El admin le escribe desde logisticacideic@gmail.com **solo al correo registrado**, sin decirle cuál es. Si responde desde ese correo, el admin puede cambiarle el número: **Anular y liberar cupos** y enseguida **Inscribir desde el panel** con el número nuevo y las mismas actividades. Si alguna se llenó en ese momento, el panel ofrece ampliar.

### Guion

| Hora | Quién | Qué |
|---|---|---|
| −15 min | 👤 | Sistema → **Respaldo** (descárgalo). Operación → **Cerrar ahora**. Etapas: 1 y 2. En Actividades, deja **una visita con cupo 3**, para el voluntario 4, y comprueba que el taller del ensayo tiene el enlace del grupo. Decide quién atiende el WhatsApp de contacto. |
| −5 min | 👥 | Los voluntarios abren `https://abidancopa2-netizen.github.io/inscripciones-ciic-2026/` y ven "inscripciones cerradas". El equipo entra al panel. |
| 0 | 👤 | Operación → **Abrir**. Cuenta regresiva en voz alta: los 10 escriben su documento **a la vez**. |
| 0–10 min | 👥 | Cada voluntario completa su caso (tabla de arriba) y hace una captura del comprobante. |
| 10–25 min | 👥 equipo | **Operadores 1 y 2:** las 3 solicitudes del grupo de ensayo, con el procedimiento 1: aprobar a los voluntarios 1 y 2, y rechazar al 9. **Operador 3:** con el procedimiento 2, reenviar la confirmación al voluntario 8 y no darle nada al voluntario 5. **Operador 4:** buscar a 3 voluntarios por documento y por celular; abrir la lista de una actividad, marcar a 2 como "en el grupo" y exportar el CSV. **Admin 1:** anular la inscripción del voluntario 3. **Admin 2:** agregar al padrón el documento del voluntario 10 (`99999999`, etapa 1); inscribirlo a mano en la actividad llena, con la ampliación y su llave; luego cambiarle una de sus actividades. Avísale: su comprobante cambia. |
| 20–25 min | 👤 y 3 voluntarios en el Wi-Fi de la UCSM, mismo pabellón | **Freno por red** (las inscripciones siguen abiertas: si están cerradas, los documentos que no existen no cuentan).<br>1. Operación → Redes con intentos fallidos → Límites: **Red = 5** → Guardar.<br>2. Cada uno escribe 2 documentos que no existen (`11111111`, `22222222`). Si ya hubo fallos en esta ventana de 10 min, se frena antes.<br>3. El equipo ve "cerca del límite" y luego "frenada", en la tarjeta y en la franja.<br>4. Desde ese Wi-Fi, un documento válido da "demasiados intentos fallidos desde tu red"; con datos móviles, pasa.<br>5. Prueben las 2 salidas: **Liberar red** y, otra vez frenada, subir el límite. Al final: **Red = 300**. |
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
7. 👤 Comprueba que el límite por red quedó en **300** (Operación → Redes con intentos fallidos → Límites).

### Qué anotar (para la conversación de diseño)

```
ENSAYO · 10/11/2026 · 10 voluntarios · equipo: 1 propietario, 2 admin, 4 operadores
Casos 1–10: <bien / qué pasó>
Equipo: <qué hizo cada rol y si encontró todo>
WhatsApp: <solicitudes de 1, 2 y 9 bien atendidas; minutos para reenviar la confirmación del 8; qué recibió el 5>
Red UCSM: <tabla de la prueba previa; en el ensayo, si se frenó con 5, si el aviso se vio y si liberar o subir el límite lo resolvió>
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

1. 🤖 Migración 10 en PRODUCCIÓN (`instalar.py`, primero `--verificar`), si el ensayo salió bien. Deja el límite por red en 300. Luego `config.js` pasa a apuntar a PRODUCCIÓN (sigue cerrada).
2. 👤 Tu cuenta de propietario en PRODUCCIÓN.
3. 👤 Invitar al equipo en PRODUCCIÓN.
4. 👤 Sistema → Respaldo → Importar padrón → Importar actividades. El informe dice qué filas no entraron y por qué: corriges el CSV y lo vuelves a importar (lo que ya entró no se duplica).
5. 👤 Revisar actividades, cupos y enlaces → Respaldo → **Pasar a producción** → Respaldo.
6. 🤖 Tester en modo lectura → congelamiento → 👤 **Abrir** a la hora anunciada.

### Hora de apertura

- **Fuera del horario de clases**, por ejemplo a las 20:00 de un día sin evaluaciones. Así nadie queda en desventaja por estar en clase o en laboratorio. Además, la gente se reparte entre su casa y sus datos móviles, en lugar de concentrarse en la IP de un pabellón.
- Anúnciala con 24 horas de anticipación y recuérdala 1 hora antes. Ese día, el equipo debe estar disponible desde 30 minutos antes hasta 1 hora después.
- **Por etapas, solo si hay una prioridad que respetar.** Por ejemplo, si la Etapa 1 tiene prioridad en las visitas, abre la Etapa 1 a las 20:00 y agrega la Etapa 2 a las 20:30, desde Operación → Etapas que pueden inscribirse. Agregar una etapa se puede con las inscripciones abiertas. Si no hay una prioridad que respetar, conviene una sola apertura: es más simple y más justa. La carga no lo exige, porque en las pruebas 1000 personas a la vez se inscribieron en unos 20 s.

### Quién vigila qué durante la apertura

| Quién | Qué vigila o hace |
|---|---|
| Propietario | Operación: abrir, cerrar, límites y "Liberar red". Decide ante cualquier señal del plan de contingencia |
| Admin 1 | La franja de arriba, "Redes con intentos fallidos", llamadas y pico en 10 s, Incidencias e Integridad. Avisa al propietario |
| Admin 2 | Inscripciones a mano, cambios y cupos (con su llave) |
| Operadores 1 y 2 · **coordinadores** | Uno por bloque (por ejemplo, visitas y talleres). Reparten los grupos entre las parejas, cubren a quien se desconecte, juntan los casos raros y los pasan al admin 2. Si ven muchas solicitudes de gente no inscrita, avisan al admin 1 |
| Operadores 3 a 16 · **7 parejas de grupos** | Cada pareja atiende sus grupos de WhatsApp: solicitudes con el procedimiento 1 (aprobar a los inscritos, rechazar a los demás) y la marca "en el grupo" en Listas. **2 por grupo** mientras alcance; si hay más grupos que parejas, cada pareja lleva varios grupos del mismo bloque. Anoten en una tabla compartida (sin datos de personas) qué grupos lleva cada pareja |
| Operadores 17 y 18 · **WhatsApp de contacto** | Dudas y confirmaciones perdidas (procedimiento 2, con "Copiar mensaje"). Como el número es el tuyo, vincúlalo en sus computadoras con WhatsApp Web (Dispositivos vinculados) solo durante la apertura, o pásales tú los casos. Lo que no puedan resolver, al admin 2 |
| **Exportar listas** | Regla del equipo (08/11): **solo los admin exportan**. El panel deja exportar a los operadores, pero cada exportación queda en la bitácora con quién y cuándo; revisa esas entradas al cerrar el día |
| Canal de avisos masivos | **Uno solo, anunciado de antemano** (por ejemplo, el canal o la comunidad de WhatsApp del CIDEIC y los delegados de cada ciclo), a cargo de una persona que no sea el propietario. La página también avisa sola: muestra "cerradas" y la cuenta regresiva de "Avisar y cerrar" |

### Plan de contingencia

| Señal | Qué significa | Qué hacer | Quién |
|---|---|---|---|
| Franja **"⚠ RED CERCA DEL LÍMITE"** (80 %) | Muchos documentos mal escritos o fuera del padrón desde una misma red. Casi seguro, un pabellón de la UCSM | Mirar la tarjeta. Si es una red de la UCSM, **subir el límite por red** (por ejemplo, de 300 a 500) antes de que se frene. Vale de inmediato | Admin 1 avisa · propietario sube |
| Franja **"⛔ RED FRENADA"** | Esa red no puede verificar documentos hasta que termine su ventana; la tarjeta dice en cuántos minutos | **Liberar red** y subir el límite. Por el canal: "Si te sale *demasiados intentos fallidos desde tu red*, cambia a tus datos móviles" | Propietario · canal |
| Franja **"⚠ SATURACIÓN SOSTENIDA"** | Más de 2000 llamadas por cada 10 s durante 30 s: mucha demanda, no un error | No cerrar por reflejo: la página pone a la gente "en la fila" y reintenta sola. Vigilar Incidencias, Integridad y que las inscripciones sigan subiendo. Si aparecen incidencias seguidas o se rompe la integridad: **Avisar y cerrar** (2 min) y seguir la fila "grupo afuera" | Admin 1 vigila · propietario decide |
| Muchos "no carga" o "Sin conexión" por WhatsApp, pero **sin alarma** y con pocas llamadas en el panel | Las llamadas no llegan a Supabase: probablemente el Wi-Fi, el firewall o el portal de la UCSM | Probar desde un celular con datos móviles. Si así funciona, avisar por el canal "usa tus datos móviles" y llamar al contacto de TI. Si es general y dura más de 10 minutos, seguir la fila siguiente | Operadores 3 y 4 detectan · propietario decide |
| **Un grupo grande quedó afuera** de forma injusta (una red frenada o caída en los primeros minutos) | Los cupos se llenaron sin ellos | **Avisar y cerrar** (o Cerrar ahora). Los inscritos conservan su lugar; quien estaba eligiendo vuelve al inicio. Arreglar la causa (liberar red, subir el límite, TI), anunciar la nueva hora con el texto de abajo y reabrir a esa hora. Si las visitas se llenaron mientras tanto, los admins pueden ampliar cupos con su llave | Propietario · admins · canal |
| **Alguien no logra inscribirse** (un caso suelto, con captura del error) | Una falla individual | Un admin lo inscribe desde el panel: Operación → Inscribir desde el panel. Antes, se comprueba su número (procedimiento 2, pasos 1 y 2) y se le pide que lea y acepte el aviso de privacidad en la página. Después se le envía su confirmación (procedimiento 2, pasos 4 y 5) | Operador recibe · admin inscribe |

Reintentar después de un "Sin conexión" **no duplica** la inscripción. Mientras la persona no recargue, la página reenvía el mismo pedido (R-32), y si el primero ya había entrado, recibe su confirmación. Si recarga y vuelve a intentar, ve "Este documento ya está inscrito" y se le reenvía con el procedimiento 2. La base no permite dos inscripciones del mismo documento.

**Aviso para el caso "grupo grande afuera"** (completa los corchetes):

```
📢 CIDEIC · Inscripciones: hubo un problema de conexión en [la red de la universidad / el pabellón X]
y muchos no pudieron entrar. Para que sea justo, cerramos las inscripciones unos minutos.
Reabrimos hoy a las [hh:mm], en el mismo enlace. Si ya te inscribiste, tu lugar está guardado:
no tienes que hacer nada.
```

### Texto de difusión

```
📲 *Inscripciones CIDEIC · visitas técnicas y talleres*
🗓️ Abren el [día] a las [hh:mm] en: https://abidancopa2-netizen.github.io/inscripciones-ciic-2026/

• Ten a la mano tu DNI, carnet de extranjería o pasaporte.
• Puedes usar el Wi-Fi de la universidad o tus datos móviles. Si la página no carga o te dice
  "demasiados intentos fallidos desde tu red", cambia a tus datos móviles y vuelve a intentarlo.
• Si ves "Sin conexión" o "Estás en la fila", no recargues: la página reintenta sola y no te
  inscribe dos veces.
• Al terminar, entra a tus grupos de WhatsApp o toma una captura: la confirmación se muestra
  una sola vez.

¿Dudas o perdiste tu confirmación? Escríbenos al WhatsApp +51 927 457 291, desde el número con
el que te inscribiste.
```
