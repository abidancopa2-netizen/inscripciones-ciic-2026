# Sprint 3 · Guía paso a paso: de tu computadora a Supabase y GitHub

Al terminar tendrás:
- **dos proyectos en Supabase**: PRUEBA, con la base ficticia, donde corre el tester; y PRODUCCIÓN, solo con el esquema, donde entrarán los datos reales;
- **la página y el panel publicados** en GitHub Pages, apuntando por ahora a PRUEBA;
- **los flujos de GitHub en verde**: el tester y "Mantener Supabase activo";
- **tu cuenta de propietario** entrando al panel publicado con contraseña y código del celular.

Todo es gratis. Tiempo aproximado: tu parte, 45 minutos; la de Claude Code, la que tarden las pruebas.

| Marca | Quién |
|---|---|
| 👤 | Tú, en el navegador |
| 🤖 | Claude Code, en la carpeta del proyecto (tú solo le das la instrucción) |

---

## Fase A · Local (🤖, antes de tocar nada en internet)

🤖 Pídele: **"Aplica y prueba el sprint 3 en local según sprints/sprint-3/LEEME.md."**

Esperado: 302 de 302 con navegador. Si falla algo, el reporte viene aquí antes de seguir.

---

## Fase B · Cuentas y proyectos (👤)

**B1. GitHub.** Si no tienes cuenta, créala en github.com. Activa la verificación en dos pasos (Settings → Password and authentication) y **guarda los códigos de recuperación fuera del celular**.

**B2. Supabase.** Entra a supabase.com (puedes usar "Continue with GitHub"). Activa la verificación en dos pasos de tu cuenta de Supabase y guarda sus códigos de recuperación.

**B3. Proyecto de PRUEBA.** "New project":
- Nombre: `ciic-prueba`.
- Contraseña de la base: usa "Generate a password" y **guárdala en tu gestor de contraseñas**. No la escribas en el chat ni en ningún archivo del proyecto. Debe tener **solo letras y números**: si la generada trae símbolos (`@ : / # ? % $` y otros), genera otra o cámbiala luego en Project Settings → Database → Reset database password. Los símbolos rompen la cadena de conexión (habría que codificarlos) y el `$` se expande al cargarla.
- Región: **South America (São Paulo)**, la más cercana a Perú.
- Plan: Free.

**B4. Proyecto de PRODUCCIÓN.** Igual que B3, con el nombre `ciic-produccion` y **otra** contraseña.

**B5. Anota de cada proyecto**, en tu gestor de contraseñas o en una nota privada:

| Dato | Dónde está | ¿Es secreto? |
|---|---|---|
| Identificador (ref) | En la dirección del proyecto: `https://<ref>.supabase.co` | No |
| Project URL | Botón **Connect** (arriba) o Project Settings → API | No |
| Clave pública | Project Settings → API Keys: la `anon` (empieza con `eyJ`) o la `publishable` (`sb_publishable_…`) | No: va en la página |
| Cadena de conexión | Botón **Connect** → **Session pooler** → la línea `postgresql://postgres.<ref>:[YOUR-PASSWORD]@…pooler.supabase.com:5432/postgres`, con tu contraseña en lugar de `[YOUR-PASSWORD]` | **SÍ**: da acceso total a la base |

Nunca uses la clave `service_role` ni la `secret`: no hacen falta en ningún paso.

**B6. Acceso del panel, en los DOS proyectos.** En Authentication:
- **Sign In / Providers → Email:** activado. **"Allow new users to sign up": desactivado** (solo entra quien invites). "Confirm email": activado.
- **Multi-Factor:** TOTP activado (suele venir así).
- **URL Configuration:** lo completas en la Fase D7, cuando exista la dirección de la página.

---

## Fase C · Instalar en Supabase (🤖 con tus datos)

**C1. Darle las cadenas secretas a Claude Code sin escribirlas en el chat.** En la carpeta del proyecto, crea con el Bloc de notas un archivo llamado `.env.local` con este contenido (una línea por dato; **comillas simples**, y una línea en blanco al final):

```
DSN_PRUEBA='postgresql://postgres.<ref_prueba>:<contraseña>@aws-0-sa-east-1.pooler.supabase.com:5432/postgres'
DSN_PRODUCCION='postgresql://postgres.<ref_prod>:<contraseña>@aws-0-sa-east-1.pooler.supabase.com:5432/postgres'
REF_PRUEBA='<ref_prueba>'
REF_PRODUCCION='<ref_prod>'
URL_PRUEBA='https://<ref_prueba>.supabase.co'
ANON_PRUEBA='<clave pública de prueba>'
URL_PRODUCCION='https://<ref_prod>.supabase.co'
ANON_PRODUCCION='<clave pública de producción>'
```

Copia la cadena tal como la muestra Supabase en "Session pooler" (el servidor `aws-…pooler.supabase.com` puede ser otro) y reemplaza solo `[YOUR-PASSWORD]`.

`.gitignore` ya excluye `.env.*`: nunca se sube a GitHub. Claude Code tiene prohibido leerlo con su visor; lo carga en la terminal sin mostrarlo.

**C2.** 🤖 Pídele: **"Sigue la Fase C de sprints/sprint-3/GUIA.md."** Claude Code hará:

| Paso | Qué hace | Esperado |
|---|---|---|
| C2 | Instala en PRUEBA: `instalar.py --dsn "$DSN_PRUEBA" --confirmar "$REF_PRUEBA" --datos local/datos_prueba.sql` (primero con `--verificar`, que no cambia nada). Aplica las migraciones pendientes en una sola transacción: si algo falla, no queda nada a medias. Si PRUEBA ya estaba instalada, aplica solo lo nuevo | La versión más reciente (hoy **5.5-s3.2**), padrón 3201, actividades 28, integridad OK |
| C3 | Crea la clave del tester en PRUEBA (`select privado.crear_clave_admin();`) y la guarda como `ADMIN_KEY` en `.env.local`, sin mostrarla | — |
| C4 | Corre el tester contra PRUEBA, **sin `--local` y sin `--web`**, con `--dsn "$DSN_PRUEBA"` | Todo en verde salvo **"ip_cabecera ya no es auto"**, que falla a propósito hasta C5. Las pruebas de IP falsa pasan: si llega `cf-connecting-ip`, la red no cambia; y una `CF-Connecting-IP` falsa la rechaza el proxy de Supabase (HTTP 403), lo que también cuenta como seguro |
| C5 | **IP real (bloqueante).** Lee la línea "cabeceras" del bloque R · IP y fija `config.ip_cabecera` con la tabla de abajo; vuelve a correr el tester | Las 3 pruebas de IP en verde: la IP falsa no cambia la red, `ip_cabecera` ya no es `auto`, y la red es tu IP pública. Para saber tu IP pública, el tester consulta `api.ipify.org` (un servicio externo que solo recibe la IP de quien consulta, la tuya o la de GitHub; ningún dato del sistema) |
| C6 | Solo con C4 y C5 en verde en PRUEBA: instala en PRODUCCIÓN **sin datos** (`instalar.py --dsn "$DSN_PRODUCCION" --confirmar "$REF_PRODUCCION"`, primero con `--verificar`) y le pone el mismo `ip_cabecera`. **No** crea clave del tester en producción | La misma versión que PRUEBA (hoy 5.5-s3.2), padrón 0, actividades 0 |
| C7 | Anota las mediciones de Supabase: importar 10 000 filas (total y en la base) y el p95 de la carga de 150 | Van en el reporte |

**Cómo elegir `ip_cabecera` en C5** (lo hace Claude Code con lo que muestra el tester):

| Si la línea "cabeceras" muestra… | Valor |
|---|---|
| `cf-connecting-ip` con tu IP pública | `cf-connecting-ip` (lo observado en PRUEBA el 05/11: llega `cf-connecting-ip` con tu IP; `x-forwarded-for` antepone lo que mande el cliente; `x-real-ip` no llega) |
| No hay `cf-connecting-ip`, pero sí `x-real-ip` con tu IP pública | `x-real-ip` |
| Solo `x-forwarded-for`, y tu IP pública es el **último** valor | `xff-ultimo` |
| Nada de lo anterior coincide con tu IP pública | No se elige: el reporte va a la conversación de diseño |

```sql
update public.config set ip_cabecera = '<valor>' where id = 1;     -- en los dos proyectos
```

---

## Fase D · GitHub (🤖 con tu inicio de sesión)

**D1.** 👤 Instala GitHub CLI: en PowerShell, `winget install GitHub.cli`. Luego, en la terminal de Claude Code, `gh auth login`: elige GitHub.com, HTTPS y "Login with a web browser", y completa el código en el navegador.

**D2 a D6.** 🤖 Pídele: **"Sigue la Fase D de sprints/sprint-3/GUIA.md."**

| Paso | Qué hace | Esperado |
|---|---|---|
| D2 | `git init`, revisa que `.env.local` y los resultados no entren (`git check-ignore -v .env.local`), primer commit y `gh repo create <nombre> --public --source . --push` | Repositorio creado; sin secretos |
| D3 | Activa GitHub Pages desde `main`, carpeta `/docs` (`gh api -X POST repos/{dueño}/{repo}/pages -f "source[branch]=main" -f "source[path]=/docs"`) | `https://<usuario>.github.io/<repo>/` responde |
| D4 | Pone en `docs/config.js` la URL y la clave pública de **PRUEBA**, `MODO: 'real'`; commit y push. **La página publicada apunta a PRUEBA hasta la apertura** (Sprint 6 la cambia a producción) | La página publicada verifica documentos de la base ficticia |
| D5 | Variables `PRUEBA_API_URL`, `PRUEBA_ANON_KEY`, `PRODUCCION_API_URL` y `PRODUCCION_ANON_KEY` (públicas), y el secreto `ADMIN_KEY` (`gh variable set …`; `gh secret set ADMIN_KEY` leyendo de `.env.local`, sin mostrarla) | "Mantener activo" falla y avisa si falta alguna: así ningún proyecto se pausa en silencio |
| D6 | Corre "Tester del sistema" (completo, 150) y "Mantener Supabase activo" con `gh workflow run`, y los sigue con `gh run watch` | Los dos en verde, con los dos proyectos consultados; el artefacto trae solo `reporte.md` y `resultados.json`, sin capturas. Las acciones de GitHub están fijadas por SHA y las dependencias por versión exacta |

**D7.** 👤 Vuelve a B6 → URL Configuration, en los dos proyectos: **Site URL** = `https://<usuario>.github.io/<repo>/panel.html`, y agrégala también en **Redirect URLs**.

---

## Fase E · Tu cuenta de propietario en PRUEBA (👤 + 🤖)

1. 👤 En el proyecto de PRUEBA: Authentication → Users → **Invite user** → tu correo.
2. 👤 Abre el correo: te lleva al panel publicado. Crea tu contraseña (12 caracteres o más) y registra el código QR en Google Authenticator o Microsoft Authenticator. Verás "Tu cuenta aún no tiene rol": es lo esperado.
3. 🤖 Pídele: **"Asígname como propietario en PRUEBA con mi correo <tu@correo>."** Correrá `select privado.asignar_propietario('<tu@correo>');`.
4. 👤 Recarga el panel: entras como propietario. Sistema → Equipo te muestra a ti.

El correo de Supabase gratuito envía pocos mensajes por hora: invita solo tu cuenta ahora; el equipo, en el Sprint 5. Tu cuenta en PRODUCCIÓN se crea en la apertura (Sprint 6), cuando la página pase a apuntar allí.

---

## Fase F · Aceptación y reporte (🤖)

| Comprobación | Esperado |
|---|---|
| Tester local (Fase A) | 302 de 302 |
| Tester contra PRUEBA desde tu equipo, con `--dsn` y `--web` (página publicada) | Todo en verde, incluidas las 3 pruebas de IP |
| Tester en GitHub Actions | Verde |
| Mantener Supabase activo | Verde, con los dos proyectos activos |
| Panel publicado | Entras con contraseña y código; ves el panel como propietario |
| PRODUCCIÓN | Versión 5.5-s3, vacía, con `ip_cabecera` fijado y sin clave del tester |
| Secretos | Ninguno en el repositorio (`git log -p` no contiene `postgresql://` ni la clave del tester) |

El reporte usa el formato de la skill `ciic-desarrollo` y suma: las cabeceras vistas y el `ip_cabecera` elegido, y las mediciones de C7.

## Qué no hacer

- No pegar la cadena de conexión, la contraseña de la base ni la clave del tester en el chat, en un commit o en un issue.
- No correr `local/supabase_local.sql` en Supabase (`instalar.py` no lo hace).
- No crear la clave del tester en PRODUCCIÓN.
- No cargar la base ficticia en PRODUCCIÓN (`instalar.py` solo la carga en una base de prueba vacía).
