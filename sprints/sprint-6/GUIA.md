# Sprint 6 · Guía de la apertura (Etapa 1)

👤 = lo haces tú (propietario) · 🤖 = lo hace Claude Code · 👥 = el equipo.

**Fechas:**

| Qué | Cuándo |
|---|---|
| Ensayo con 10 personas (en PRUEBA) | Martes 10/11. Mejor en la mañana (por ejemplo, de 10:00 a 11:30): deja la tarde para corregir lo que encuentre antes del congelamiento |
| Apertura de la Etapa 1 (en PRODUCCIÓN) | **Miércoles 11/11 a las 20:00**, con el dominio propio o sin él |
| Congreso | Del 16 al 21/11 (viicideic.space) |
| Borrado de los datos (90 días) | A más tardar el viernes 19/02/2027 (doc §19.8) |

**Congelamiento** (doc §20.1 y la skill `sql-ciic-inscripciones`): desde 24 horas antes de abrir, es decir, **desde el martes 10/11 a las 20:00**, no se corre SQL en PRODUCCIÓN hasta el fin del congreso. Todo lo operativo se hace desde el panel. Este sprint lo respeta así:

| Desde | Hasta | SQL en PRODUCCIÓN | Páginas y `config.js` | Panel y Supabase (sin SQL) |
|---|---|---|---|---|
| Hoy | **10/11 · 20:00** | Todo lo de este sprint va el **09/11**: migraciones 10 a 12 con `instalar.py` y tu `asignar_propietario` | Sí, con pruebas. `config.js` a PRODUCCIÓN después del ensayo (parte 4) | Sí |
| 10/11 · 20:00 | 11/11 · 12:00 (Pasar a producción) | **Congelado.** Solo la excepción de §20.1, para algo crítico del ensayo (parte 4.1) | Solo para corregir un problema del ensayo, o para terminar la Fase 2 si se atrasó. Siempre con el tester en local y en PRUEBA, y el de lectura después | **Sí:** cuentas y roles, carga del padrón, actividades y enlaces, revisión, prueba de humo, respaldos y Pasar a producción |
| 11/11 · 12:00 | 21/11 (fin del congreso) | Congelado (excepción de §20.1) | Congelado (misma excepción) | Sí |

La carga de los datos reales desde el panel **no rompe el congelamiento**: §20.1 la pone entre lo que se hace sin SQL. Los ajustes del panel de Supabase (correo, URLs, invitaciones) tampoco son SQL, pero se dejan listos el 09/11.

## 1 · Correos de Supabase: hazlo primero (👤, 09/11, 30 minutos)

**Sin este paso, las invitaciones al equipo no llegan.** Sin un servidor de correo propio, Supabase solo envía a los correos de los miembros de su organización (los demás reciben "Email address not authorized"), y como mucho 2 por hora. Hazlo en **PRUEBA** (para el equipo del ensayo) y en **PRODUCCIÓN**.

1. En la cuenta de Gmail **logisticacideic@gmail.com**: Cuenta de Google → Seguridad → activa la **verificación en 2 pasos**. Luego, en **Contraseñas de aplicaciones**, crea una llamada "Supabase CIDEIC". Gmail te da 16 letras: guárdalas en tu gestor de contraseñas. Nunca en el chat ni en el repositorio.
2. Supabase (en cada proyecto) → Authentication → Emails → **SMTP Settings** → Enable custom SMTP. Llena:
   - Sender email: `logisticacideic@gmail.com`
   - Sender name: `VII CIDEIC`
   - Host: `smtp.gmail.com`
   - Port: `465`
   - Username: `logisticacideic@gmail.com`
   - Password: las 16 letras
   - Guarda.
3. Authentication → **Rate Limits** → "emails sent": **30 por hora**.
4. Prueba: en el panel de ese proyecto, "¿Olvidaste tu contraseña?" con tu correo. El mensaje debe llegar desde logisticacideic@gmail.com.

**Plan B, si Gmail no deja:** Authentication → Users → Add user → **Create new user**, con el correo de la persona, una contraseña temporal y "Auto Confirm User". Dásela en persona, nunca por chat. Con ella entra al panel y registra su código. Sin correo propio no funciona "¿Olvidaste tu contraseña?", así que esa contraseña se queda hasta después del congreso.

## 2 · Ajustes de Auth (👤, 09/11, 10 minutos, en los dos proyectos)

| Dónde | Qué |
|---|---|
| Authentication → Sign In / Providers → Email | **"Allow new users to sign up": apagado.** Las cuentas solo entran por invitación. La prueba de ataque lo revisa |
| Authentication → URL Configuration | **Site URL:** `https://abidancopa2-netizen.github.io/inscripciones-ciic-2026/panel.html`. **Redirect URLs:** esa misma y, si usarás el dominio (parte 6), `https://inscripciones.viicideic.space/panel.html` |
| Authentication → Multi-Factor | TOTP habilitado (ya estaba desde el Sprint 3) |

## 3 · Fase 1 · lunes 09/11 · PRUEBA, prueba de ataque y PRODUCCIÓN

En este orden:

1. 👤 **Tu autenticador de PRUEBA, registrado de nuevo** (parte 7). Va primero porque cierra el incidente, y porque necesitas entrar al panel de PRUEBA para abrirlo en el paso 4 y para el ensayo.
2. 👤 Correo propio y ajustes de Auth (partes 1 y 2).
3. 🤖 Local y PRUEBA, según `sprints/sprint-6/LEEME.md`: migraciones 11 y 12, panel y tester (unas 2 horas).
4. 🤖 **Prueba de ataque en PRUEBA** (LEEME, Fase 1, paso 2.5), con PRUEBA abierta por ti. Va después de la migración 11 (la comprueba) y antes del ensayo: deja PRUEBA limpia, y si encuentra algo queda tiempo para corregir.
5. 🤖 Con tu autorización en esa sesión, y solo si la prueba de ataque salió en verde: **migraciones 10 a 12 en PRODUCCIÓN**. PRODUCCIÓN sigue cerrada, y `config.js` sigue en PRUEBA.
6. 👤 Tu cuenta de propietario en PRODUCCIÓN (parte 4, paso 4, subpasos 1 y 2): la única sentencia SQL tuya en PRODUCCIÓN.

Ese mismo día, 👤: el correo a TI, la prueba de red en el campus, el grupo de WhatsApp de ensayo y el equipo en PRUEBA (guía del Sprint 5, partes B y C).

## 4 · Fase 2 · martes 10/11, después del ensayo · `config.js` a PRODUCCIÓN y cuentas

Empieza cuando el ensayo terminó y PRUEBA quedó como estaba. Los pasos 1 a 3 cambian `config.js`: **termínalos antes de las 20:00**. Si el ensayo se atrasa y no alcanza, se pueden terminar el 11/11 antes de las 09:00 (no son SQL). No más tarde: la carga necesita el panel ya en PRODUCCIÓN.

1. 👤 Copia en `.env.local` los datos de PRODUCCIÓN (Supabase PRODUCCIÓN → Project Settings → API Keys):
   ```
   PRODUCCION_API_URL=https://<ref>.supabase.co
   PRODUCCION_ANON_KEY=<la clave anon o publishable>
   ```
   Nunca en el chat.
2. 🤖 `python sprints/sprint-6/configurar.py`: comprueba que esa API responde, que está en `5.5-s6` y que está **cerrada**, y muestra el cambio. Luego `--aplicar`, commit y push.
3. 🤖 Cuando GitHub Pages publique: `python tester/tester.py --modo lectura --api <PRODUCCIÓN> --anon <PRODUCCIÓN> --web <página publicada>`. Sin inyectar nada, comprueba con el tráfico real del navegador que la página y el panel publicados llaman **solo** a PRODUCCIÓN, que el panel no ofrece "Entrar con la clave de prueba" y que la base está en `5.5-s6`. Desde aquí, la página publicada dice "inscripciones cerradas".
4. 👤 **Tu cuenta en PRODUCCIÓN.** Los pasos 1 y 2 se adelantan al **09/11**: así la única sentencia SQL queda lejos del congelamiento.
   1. Supabase **PRODUCCIÓN** → Authentication → Users → Add user → **Create new user**: tu correo, una contraseña nueva (distinta de la de PRUEBA) y "Auto Confirm User".
   2. En el SQL Editor de **PRODUCCIÓN**, corre esto. Debe responder "TU_CORREO es el propietario.":
      ```sql
      select privado.asignar_propietario('TU_CORREO');
      ```
   3. Después del paso 3 de esta parte (con el panel publicado ya en PRODUCCIÓN), entra con tu correo y esa contraseña. Registra el QR en tu autenticador como una entrada **nueva**, "CIDEIC PRODUCCIÓN", distinta de la de PRUEBA.
5. 👤 **El equipo en PRODUCCIÓN** (10/11 por la tarde o la noche, o el 11/11 en la mañana): invita a los 6 (2 admin y 4 operadores) **después del paso 3**, porque el enlace de la invitación abre el panel publicado. Cada uno abre su enlace una vez, crea su contraseña y registra una entrada nueva "CIDEIC PRODUCCIÓN". Tú les asignas el rol en Sistema → Equipo, y cada uno comprueba que ve sus pestañas. Esto es desde el panel: se puede hacer durante el congelamiento.

### 4.1 · Si el ensayo encuentra un problema

Anótalo en la bitácora de `INCIDENCIAS.md` y tráelo a la conversación de diseño. Se resuelve según lo que sea:

| Qué encontró | Ejemplos | Qué se hace | Hasta cuándo |
|---|---|---|---|
| Un dato o una regla | Un enlace, un cupo, el texto de una actividad, un límite, el mismo día, un rol | Se corrige en el panel. En PRODUCCIÓN, se carga bien desde el principio | Siempre |
| Un ajuste de Supabase | Un correo que no llega, una URL de redirección, el registro abierto | En el panel de Supabase, en los dos proyectos | Antes de invitar al equipo |
| La página o el panel (sin SQL) | Un botón que no responde, un texto confuso, algo que se ve mal en un celular | La conversación de diseño entrega un `sprint-6.x`. 🤖 Lo prueba con el tester en local y en PRUEBA, hace el push y corre el tester de lectura | **11/11 · 11:00** |
| La base, y es crítico | No deja inscribir, los cupos cuentan mal, muestra un dato que no debe | **Excepción de §20.1** (PRODUCCIÓN sigue cerrada): migración nueva → tester completo en PRUEBA → respaldo de PRODUCCIÓN → `instalar.py` → respaldo → tester de lectura. Solo con tu autorización en esa sesión, y todo en la bitácora | **11/11 · 11:00** |
| La base, y no es crítico | Algo incómodo que tiene un camino en el panel | No se toca: se usa el camino del panel y queda anotado para después del congreso | — |
| La red de la UCSM | El Wi-Fi de un pabellón se frena | Límite por red desde la tarjeta Redes. El texto de difusión ya dice "cambia a tus datos móviles" | Siempre |

**El 11/11 a las 11:30 decides si se sigue** (antes de Pasar a producción y de la difusión):

- **Si todo está en verde, o lo pendiente tiene camino en el panel:** se sigue con la hora de las 20:00.
- **Si queda algo crítico sin resolver:** no pases a producción y no difundas. La apertura se corre al día siguiente a la misma hora, y lo anuncias por el mismo canal. Hasta la difusión, moverla cuesta poco.

## 5 · Fase 3 · miércoles 11/11 · datos reales, Pasar a producción y apertura

### 5.1 Carga (👤, mañana, 1 a 2 horas)

Los archivos están en tu carpeta, fuera del repositorio. No pasan por el chat. Si el padrón ya está listo, puedes adelantar los pasos 2 a 4 al 10/11 por la noche: el 11/11 solo reimportas lo nuevo, y lo que ya entró no se duplica.

1. Sistema → **Respaldo**: el punto cero, con la base vacía.
2. Sistema → **Importar padrón** (CSV documento;etapa). Lee el informe: agregados, ya existentes, conflictos e inválidos. Si algo falló, corrige el CSV y vuelve a importarlo; lo que ya entró no se duplica.
3. Sistema → **Importar actividades**, con los enlaces de WhatsApp en la columna `enlace`. Lee el informe igual que el del padrón.
4. **Revisión entre 2 personas:**
   - **Cada actividad:** nombre, tipo, fecha (16 a 21/11), horario, lugar, cupo, entrega, enlace y que esté visible.
   - **En Operación:** inscriben **solo la Etapa 1** y la Etapa 1 puede elegir visitas; mismo día apagado y margen de 30 min (pestaña Actividades); límites 4 y 300 (tarjeta Redes).
   - **En Totales:** que el padrón de la Etapa 1 tenga la cifra esperada.
5. *(Opcional, antes de difundir el enlace)* **Prueba de humo real:**
   1. Operación → Abrir.
   2. 2 personas del equipo que estén en el padrón se inscriben con su DNI desde su celular, revisan la confirmación y el enlace de su grupo, y prueban "Copiar mensaje" en el panel.
   3. Cerrar ahora.

   "Pasar a producción" borra esas inscripciones.

### 5.2 Pasar a producción (👤 y 🤖, mediodía, 30 minutos)

1. Sistema → **Respaldo** con los datos cargados. 🤖 `python supabase/restaurar.py <archivo> --verificar`.
2. Sistema → **Pasar a producción**, con la llave `PRODUCCION`. Borra las inscripciones de prueba, la bitácora y los intentos. El padrón, las actividades y el equipo quedan, y el modo pasa a PRODUCCION.
3. Sistema → **Respaldo** otra vez, y 🤖 lo verifica.
4. 🤖 Tester en modo lectura con `--web`, como en la Fase 2: todo en verde.
5. Desde aquí y hasta el fin del congreso, solo el panel: ni código, ni `config.js`, ni SQL, salvo la excepción de §20.1.

### 5.3 Difusión y apertura

| Hora | Quién | Qué |
|---|---|---|
| 13:00 | 👤 | Publica el texto de difusión (parte 8) por el canal oficial, **solo si 5.2 terminó en verde**. Si no, espera: es mejor difundir tarde que anunciar una hora que no se cumple |
| 19:00 | 👤 | Recordatorio por el mismo canal |
| 19:30 | 👥 | Cada uno en su puesto (guía del Sprint 5, parte D: quién vigila qué). Prueba de humo: la página en un celular dice "cerradas" y el panel abre para todos |
| 20:00 | 👤 | Operación → **Abrir inscripciones** |
| 20:00–21:00 | 👥 | Vigilar con el plan de contingencia (guía del Sprint 5, parte D) |
| 21:00 y al cerrar el día | 👤 | Sistema → Respaldo. Guarda los archivos en tu carpeta, fuera del repositorio |

**Etapa 2:** cuando lo decidas, Operación → "Etapas que pueden inscribirse" → agrega la 2. Se puede hacer con las inscripciones abiertas, porque agrega opciones. Anúncialo por el mismo canal.

## 6 · Opcional · dominio `inscripciones.viicideic.space`

Solo si está **todo en verde antes del martes 10/11 a las 12:00**. Si no, se sigue con github.io (plan B). Después de difundir el enlace, no se cambia más.

1. 👤 **09/11 · DNS:** donde se administra viicideic.space, crea un registro **CNAME** con nombre `inscripciones`, valor `abidancopa2-netizen.github.io` y TTL 300. Si el DNS está en Cloudflare, ponlo en "DNS only" (nube gris), o GitHub no podrá emitir el certificado.
2. 👤 *(Recomendado, 09/11)* GitHub → tu perfil → Settings → Pages → **Add a domain** → `viicideic.space`. Agrega el registro TXT que te muestre y pulsa Verify. Así nadie más puede usar ese subdominio con GitHub Pages.
3. 👤 **10/11 en la mañana:**
   1. Repositorio → Settings → Pages → Custom domain: `inscripciones.viicideic.space` → Save. Espera a que diga "DNS check successful".
   2. GitHub agrega un archivo `docs/CNAME` con un commit. 🤖 Haz `git pull` antes del siguiente push.
4. 👤 Cuando aparezca, marca **Enforce HTTPS**. El certificado tarda de minutos a una hora.
5. 👤 En Supabase (los dos proyectos) → URL Configuration, cambia la Site URL a `https://inscripciones.viicideic.space/panel.html` y deja las dos direcciones en Redirect URLs.
6. 🤖 Corre el tester con `--web https://inscripciones.viicideic.space/` y actualiza la variable `WEB_URL` del repositorio. "Mantener activo" sigue la redirección.
7. **A las 12:00 decides:**
   - Si la página y el panel abren con candado en tu celular, la difusión usa el dominio, y github.io redirige solo.
   - **Plan B:** Settings → Pages → **Remove** el dominio. github.io vuelve a funcionar en minutos (🤖 `git pull`: GitHub borra `docs/CNAME`), y la Site URL vuelve a github.io. El registro DNS puede quedar; no molesta.

## 7 · Incidente · el código TOTP de tu cuenta en PRUEBA quedó en una captura

**Cuándo:** el lunes 09/11, antes que todo lo demás (parte 3, paso 1).

Anótalo en `INCIDENCIAS.md` con la fecha, qué se vio y dónde, lo que hiciste y que PRODUCCIÓN no se ve afectada (otro proyecto, otra cuenta y otro código).

- **Si solo se vio el código de 6 dígitos:** venció a los 30 segundos y no sirve para entrar. Volver a registrar el autenticador es por precaución.
- **Si se vio el QR o el texto secreto** (algo como `JBSWY3…`): con eso cualquiera genera códigos. **Hay que registrarlo de nuevo.**

Para registrarlo de nuevo en PRUEBA (👤, 10 minutos):

1. Supabase **PRUEBA** → Authentication → Users → tu usuario → borra el factor de MFA (TOTP). Si tu panel de Supabase no muestra esa opción, corre en el SQL Editor de **PRUEBA**:
   ```sql
   delete from auth.mfa_factors where user_id = (select id from auth.users where email = 'TU_CORREO');
   ```
2. Para cerrar todas tus sesiones abiertas en PRUEBA (opcional, también en PRUEBA):
   ```sql
   delete from auth.sessions where user_id = (select id from auth.users where email = 'TU_CORREO');
   ```
3. Si la captura también mostraba tu contraseña, cámbiala con "¿Olvidaste tu contraseña?" (ya funciona, con el SMTP de la parte 1).
4. Entra al panel publicado con correo y contraseña. Como ya no tienes factor, el panel te muestra un QR nuevo: regístralo y borra la entrada vieja de tu app.
5. Para no repetirlo: no compartas capturas de las pantallas de inicio de sesión ni del código. Si hace falta mostrar algo, tapa esas partes.

## 8 · Texto de difusión final

Usa el enlace que quede (github.io, o el dominio si a las 12:00 del 10/11 estaba todo en verde) y la hora que decidas.

```
📲 *Inscripciones CIDEIC · visitas técnicas y talleres*
🗓️ Miércoles 11 de noviembre, 8:00 p. m. · Etapa 1
🔗 https://abidancopa2-netizen.github.io/inscripciones-ciic-2026/

• Abre para quienes tienen su entrada de la Etapa 1. La Etapa 2 se anunciará por este medio.
• Ten a la mano tu DNI, carnet de extranjería o pasaporte.
• Puedes usar el Wi-Fi de la universidad o tus datos móviles. Si la página no carga o te dice
  "demasiados intentos fallidos desde tu red", cambia a tus datos móviles y vuelve a intentarlo.
• Si ves "Sin conexión" o "Estás en la fila", no recargues: la página reintenta sola y no te
  inscribe dos veces.
• Al terminar, entra a tus grupos de WhatsApp o toma una captura: la confirmación se muestra
  una sola vez.

Las actividades son durante el congreso, del 16 al 21 de noviembre.
¿Dudas o perdiste tu confirmación? Escríbenos al WhatsApp +51 927 457 291, desde el número con
el que te inscribiste.
```

Con el dominio, cambia la línea 🔗 por `https://inscripciones.viicideic.space`.

## 9 · Qué anotar para la conversación de diseño

```
APERTURA · 11/11/2026 · Etapa 1
Fase 1 (09/11): <tester, ataque, migraciones en PRODUCCIÓN, limpieza programada activa en las dos bases>
Fase 2 (10/11): <huella de config.js, lectura publicada, cuentas listas>
Carga: <padrón y actividades: agregados / conflictos / inválidos>
Pasar a producción: <hora, respaldos verificados>
Apertura: <hora, inscritos en 15 min y en 1 h, redes cerca o frenadas, incidencias, casos de soporte>
```

Sin datos de personas reales: solo cifras.

## 10 · Cronograma

Para la apertura del 11/11 a las 20:00. La hora del ensayo es la recomendada: si cambia, corre la Fase 2 detrás de él.

**Lunes 09/11 · todo lo que se puede adelantar**

| Hora | 👤 Tú | 🤖 Claude Code |
|---|---|---|
| 08:30 | Autenticador de PRUEBA registrado de nuevo (parte 7, 10 min) | — |
| 09:00 | Correo propio y ajustes de Auth en los dos proyectos (partes 1 y 2). Datos de PRODUCCIÓN en `.env.local`. Si vas por el dominio: el CNAME y el TXT (parte 6) | — |
| 10:00 | — | Fase 1 en local y PRUEBA: migraciones 11 y 12, tester desde la PC y en GitHub (unas 2 h) |
| 12:00 | Abres PRUEBA desde el panel, y la cierras al terminar | Prueba de ataque en PRUEBA (30 min, con el reporte) |
| 12:30 | Autorizas PRODUCCIÓN | Migraciones 10 a 12 en PRODUCCIÓN y vista previa de `configurar.py` (15 min) |
| 13:00 | Tu cuenta en PRODUCCIÓN y `asignar_propietario` (parte 4) | — |
| 15:00 | Equipo en PRUEBA: invitaciones, códigos y roles (guía del Sprint 5, parte B) | — |
| 16:00 | Prueba de la red en el campus, y el correo a TI si falta | — |
| 18:00 | Grupo de WhatsApp del ensayo, y la confirmación de las 10 personas | Reporte de la Fase 1 |

**Martes 10/11 · ensayo y paso a PRODUCCIÓN**

| Hora | 👤 Tú | 🤖 Claude Code |
|---|---|---|
| 08:30 | Dominio en Pages, si vas por él (parte 6) | `git pull` y tester con el dominio |
| 10:00–11:30 | Ensayo en PRUEBA (guía del Sprint 5, parte C) | — |
| 12:00 | **Decisión del dominio.** Lo que encontró el ensayo, a la conversación de diseño (parte 4.1) | — |
| 12:00–16:00 | Correcciones, si hacen falta | Aplica y prueba lo que llegue |
| 16:00 | Apruebas la vista previa | Fase 2: `configurar.py --aplicar`, push y tester de lectura con `--web` (45 min) |
| 17:00 | Registras tu código en PRODUCCIÓN, invitas a los 6 y asignas los roles | — |
| **20:00** | **Empieza el congelamiento.** Si el padrón está listo, puedes cargarlo esta noche desde el panel | Nada en PRODUCCIÓN, salvo la excepción de §20.1 |

**Miércoles 11/11 · apertura**

| Hora | 👤 Tú | 🤖 Claude Code |
|---|---|---|
| 09:00 | Respaldo, importar padrón y actividades, cuentas pendientes del equipo (parte 5.1) | — |
| 10:30 | Revisión entre 2 personas y, si quieres, la prueba de humo | — |
| 11:30 | **Decides si se sigue** (parte 4.1) | — |
| 12:00 | Respaldo → Pasar a producción → respaldo (parte 5.2) | Verifica los respaldos y corre el tester de lectura |
| 13:00 | Difusión, solo si todo está en verde | — |
| 19:00 · 19:30 | Recordatorio · el equipo en sus puestos | — |
| **20:00** | **Abres** | — |
| 21:00 y al cerrar el día | Respaldo | — |
