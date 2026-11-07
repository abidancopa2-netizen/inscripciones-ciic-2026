# Guía para el diseño de autor · contrato v5.5

`index.html` (participante) y `panel.html` (organización) ya cumplen el contrato v5.5. Puedes rediseñarlos por completo, siempre que conserves lo que lista esta guía. Si lo conservas, el tester de navegador y el backend seguirán funcionando con tu diseño.

## 1 · Cómo trabajar sin Supabase (modo demo)

**Lo más rápido:** la carpeta `demo/` trae `demo-participante.html` y `demo-panel.html`, cada uno con todo adentro. Se abren con doble clic. Su selector **"Ver estado"** fuerza los estados que no aparecen solos: fila de espera, sin conexión, cuenta regresiva, cerrado, error del sistema, alerta de saturación, integridad rota, ventana de advertencia, inicio de sesión real y código de verificación. Son copias armadas de `docs/`: cuando cambies el diseño en `docs/`, vuelve a armarlas con `python local/armar_demos.py`.


1. En `config.js`, deja `MODO: 'demo'`.
2. Abre `index.html` y `panel.html` en el **mismo navegador**. Funcionan con doble clic, aunque es mejor servirlos: en la carpeta `docs/` corre `python -m http.server 8000` y abre `http://localhost:8000/`.
3. La página y el panel comparten la misma base de prueba, guardada en el navegador: lo que inscribes en la página aparece en el panel, y lo que cierras en el panel lo ve la página.
4. La cinta amarilla de arriba (`data-demo`) solo existe en modo demo. Trae los documentos de prueba, el botón para cambiar de cuenta y el de reiniciar datos. No la diseñes: desaparece en modo real.
5. Para conectar la base real: `MODO: 'real'`, y pega `API_URL` y `ANON_KEY`.

El modo demo usa `demo/demo-api.js`, que responde exactamente como la base de datos según el contrato. Si el diseño funciona en demo, funcionará con Supabase.

## 2 · Qué puedes cambiar y qué no

| Puedes cambiar libremente | No cambies |
|---|---|
| `base.css` completo, o reemplazarlo por el tuyo | Los `id` de la sección 3 |
| Textos visibles, títulos, colores, tipografías, logos, imágenes | Los atributos `data-*` de la sección 4 |
| El orden visual (con CSS), animaciones, íconos | Que cada pantalla sea un `<section data-pantalla="N">` y cada panel un `<section data-panel="…">` |
| Agregar elementos decorativos | El bloque `<script>` de cada página (si lo reescribes, debe respetar las secciones 13 y 14 de la documentación) |
| Frameworks de CSS | Construir HTML con `innerHTML` a partir de datos: el script usa `textContent` a propósito, para que nadie inyecte código con su nombre o su correo |

## 2.1 · Tema CIDEIC (Sprint 5)

El diseño de autor vive aparte, en `docs/tema/`, y se puede cambiar o quitar sin tocar el contrato:

| Archivo | Qué es |
|---|---|
| `tema/participante.css`, `tema/panel.css` | Variables de color (oscuro y claro), escena, tipografía, tarjetas y botones. Se cargan **después** de `base.css` |
| `tema/participante.js`, `tema/panel.js` | Modo "inicio" (escena o portada), interruptor claro/oscuro (guarda `cideic_tema`), pie con enlace de WhatsApp y, en el panel, tarjetas plegables de Operación (guarda `cideic_plegadas`). Solo cambian clases y `data-tema` |
| `tema/img/*.webp` | Cielo, paisaje (nítido y difuso), logo de la portada y marca de la cabecera, cada uno en oscuro y claro (unos 220 KB en total) |
| `tema/fuentes/` | Saira (licencia OFL): `saira.css`, `saira-latin.woff2`, `saira-latin-ext.woff2` y `OFL.txt`. La crea `sprints/sprint-5.1/fuente.py` (baja una vez la misma fuente que pedía el tema); no va en los manifiestos |

En el HTML el tema solo agrega: la clase `t-participante` o `t-panel` en `<html>`, un script corto en `<head>` (fija el modo antes de pintar, para que no destelle), la hoja de la fuente Saira (`tema/fuentes/saira.css`; desde el Sprint 5.1 está alojada aquí y no se pide a Google), la escena o portada decorativa (`aria-hidden`), la marca de la cabecera y el interruptor. No cambia ningún id ni `data-*`.

Para retocarlo, edita `docs/tema/` y vuelve a armar las demos (`python local/armar_demos.py`): las demos llevan el tema en línea, con las imágenes como `data:`. Para cambiar una imagen, reemplaza el archivo con el mismo nombre.

## 3 · Ids que usa el script

**index.html (28):** `acepta` `apellidos` `banner` `btn-aviso` `btn-confirmar` `btn-imprimir` `btn-inicio` `btn-verificar` `btn-volver` `celular` `comprobante` `correo` `demo-cinta` `dias` `dlg-aviso` `dlg-aviso-ok` `dlg-aviso-texto` `doc` `evento` `form-datos` `form-doc` `msg-1` `msg-2` `msg-verif` `nombres` `pais` `pie` `t2`

**panel.html (134):** `a-doc` `a-etapa` `alta-totp` `archivo-actividades` `archivo-padron` `avisos` `btn-alta` `btn-buscar` `btn-cancelar-act` `btn-entrar` `btn-importar` `btn-importar-act` `btn-inscribir` `btn-limites` `btn-margen` `btn-nueva` `btn-olvide` `btn-paso` `btn-produccion` `btn-respaldo` `btn-salir` `btn-vaciar` `btn-wa` `caja-cupo` `clave` `clave-prueba` `codigo6` `como-rol` `correo` `cruces` `csv-ins` `csv-pad` `cuentas-demo` `demo-cinta` `est-botones` `est-txt` `estado-sis` `evento` `f-cupo` `f-desc` `f-estado` `f-etapa` `f-fecha` `f-fin` `f-grupo` `f-inicio` `f-lugar` `f-modo` `f-nombre` `f-q` `f-tipo` `form-act` `form-codigo` `form-login` `form-nueva` `form-prueba` `i-a1` `i-a2` `i-apellidos` `i-cel` `i-correo` `i-doc` `i-nombres` `i-ok` `incidencias` `informe-actividades` `informe-padron` `integridad` `l-act` `l-aviso` `l-buscar` `l-copiar` `l-csv` `l-csv-todas` `l-etapa` `l-q` `l-res` `l-tabla` `l-todos` `l-vcf` `lim-disp` `lim-red` `lista-acts` `llave-prod` `llave-vaciar` `m-caja` `m-cancelar` `m-entrada` `m-lbl` `m-ok` `m-tit` `m-txt` `margen` `modal` `modo-prueba` `msg-codigo` `msg-login` `msg-nueva` `nota-visitas` `nueva-clave` `p-res` `pag-ant` `pag-sig` `pag-txt` `paso` `paso-clave` `paso-demo` `paso-prueba` `q` `qr` `redes-lista` `redes-nota` `repetidos` `res-buscar` `secreto` `sesion` `sw-dos` `sw-mismo` `t-codigo` `t-form-act` `tabla-acts` `tabla-equipo` `tabla-part` `tarjeta-redes` `totales` `ultimo-respaldo` `ultimos` `vista-actividades` `vista-app` `vista-login` `vista-padron` `wa-act` `wa-cel` `wa-res`

Además, el script crea estos ids dentro de contenedores: `btn-abrir`, `btn-cerrar`, `min-aviso`, `btn-recontar` (en `est-botones` e `integridad`).

## 4 · Atributos y estados para diseñar

| Atributo o selector | Dónde | Valores | Qué representa |
|---|---|---|---|
| `[data-pantalla]` + `hidden` | Página | 1, 2, 3 | Pantalla visible: documento, elección, confirmación |
| `.mensaje[data-estilo]` | Ambas | `exito`, `aviso`, `info`, `error` | Color del mensaje |
| `.mensaje[data-tipo]` | Ambas | Tipo de respuesta de la API (sección 6) | Para estilos finos por caso |
| `.banner[data-tipo]` | Página | `aviso` (cuenta regresiva), `sin_conexion` | Franja superior |
| `.opcion[data-actividad]` | Página | ID de la actividad | Botón de cada actividad |
| `.opcion[aria-pressed="true"]` | Página | — | Elegida |
| `.opcion:disabled` | Página | — | Bloqueada; el motivo va en `.quedan` ("Llena", "Solo Etapa 1", "Se cruza con VIS05") |
| `.opcion[data-tipo-actividad]`, `.etiqueta[data-tipo]` | Página | `VISITA`, `TALLER` | Tipo de actividad |
| `[data-grupo]` | Página, confirmación | `enlace`, `manual`, `pendiente` | Cómo entra al grupo de WhatsApp |
| `.franja[data-estado]` | Panel | `abierto`, `cerrado` | Estado del sistema |
| `.franja[data-alerta]` | Panel | `si`, `no` | Saturación sostenida |
| `[data-tab]`, `[aria-selected]` | Panel | `operacion`, `participantes`, `actividades`, `listas`, `sistema` | Pestañas |
| `[data-panel]` | Panel | Igual que `data-tab` | Contenido de cada pestaña |
| `[data-nivel]` | Panel | 2, 3 | Se oculta a roles menores (1 operador, 2 admin, 3 propietario) |
| `.chip[aria-pressed]` | Panel | `true`, `false` | Etapas habilitadas (`data-ins`, `data-vis`) |
| `.interruptor[aria-checked]` | Panel | `true`, `false` | Interruptores |
| `.estado[data-v]` | Panel | `CONFIRMADO`, `ANULADO`, `SIN_INSCRIBIR`, `ok`, `mal`, `aviso`, `neutro` | Etiquetas de estado |
| `.act[data-publicada]` | Panel | `true`, `false` | Actividad visible u oculta |
| `.barra span[data-llena]` | Panel | `true`, `false` | Barra de ocupación |
| `[data-mas]`, `[data-menos]`, `[data-cupo]`, `[data-ver]`, `[data-editar]`, `[data-cruce]`, `[data-grupo]`, `[data-en-grupo]` | Panel | IDs | Botones generados por el script; el tester los usa |
| `[data-paso]` | Panel, Sistema | 1 a 5 | Pasos de "De la base de prueba a la real" |
| `[data-demo]` | Ambas | — | Solo modo demo; no forma parte del diseño |

## 5 · Formatos admitidos

| Dato | Formato | Ejemplos válidos | Qué hace el sistema |
|---|---|---|---|
| Documento | 6 a 12 letras y números, con al menos un número | `45678912`, `001234567`, `PA5566778`, `12345678K` | Quita espacios, puntos y guiones; pasa a mayúsculas; si es solo números y tiene menos de 8, completa con ceros a la izquierda (`4123456` → `04123456`) |
| Etapa | 1, 2 o 3 | `1`, `Etapa 2`, `E3` (en la importación) | Una sola etapa por documento; no se cambia |
| Nombres | 2 a 60 caracteres | `María Fernanda` | Quita espacios repetidos y caracteres de control; guarda el texto original |
| Apellidos | 2 a 60 caracteres | `Quispe Rojas` | Igual que nombres |
| Correo institucional | Formato de correo | `maria.quispe@uni.edu.pe` | Obligatorio; se guarda en minúsculas; no se le envía nada |
| Celular (Perú) | 9 dígitos que empiezan con 9 | `987654321`, `987 654 321`, `+51 987 654 321` | Se guarda como `+51987654321` |
| Celular (otros países) | 6 a 14 dígitos sin el código | `912345678` con país CL | Se guarda con su código: `+56912345678` |
| Países | PE, CL, CO, EC, BO, AR, MX, BR, VE, PY, UY, ES, US | — | Selector de la página |
| Actividades | Exactamente 2 IDs | `["VIS01","TAL05"]` | Una visita como máximo; un día cada una salvo "mismo día" |
| Fecha de actividad | `dd/mm/aaaa` | `12/11/2026` | Panel, catálogo |
| Hora | `hh:mm` de 24 h | `08:30`, `15:00` | Fin posterior al inicio |
| Enlace de grupo | Empieza con `https://chat.whatsapp.com/` | — | Vacío = "aún no hay grupo" |
| Información de la actividad | Hasta 400 caracteres | — | Se muestra en la elección y en la confirmación |
| Cupo inicial | 1 a 1000 | — | Al crear la actividad |
| Paso de cupo · margen · refresco | 1 a 100 · 0 a 240 min · 10 a 120 s | — | Panel |
| CSV del padrón (importar) | Dos columnas: documento y etapa; separador coma, punto y coma o tabulación; con o sin encabezado; UTF-8 con o sin BOM; hasta 10 000 filas | `DNI;Etapa` / `71.234.568;Etapa 2` | Normaliza igual que el documento; informa agregados, existentes, conflictos de etapa e inválidos |

| CSV de actividades (importar) | Encabezado obligatorio: `id;tipo;nombre;lugar;fecha;inicio;fin;cupo;descripcion;entrega;enlace;visible` (columnas en cualquier orden; obligatorias: tipo, nombre, fecha, inicio, fin, cupo); hasta 500 filas | `;TALLER;Topografía con drones;Aula 204;12/11/2026;15:00;18:00;110;;ENLACE;;NO` | Valida cada fila como al crear; las que ya existen no se modifican; nacen ocultas salvo `visible = SI` |

Desde Excel, para el CSV: **Guardar como → CSV UTF-8 (delimitado por comas)**. Si Excel convirtió los DNI en números y les quitó el 0, no importa: la base lo recupera.

## 6 · Tipos de respuesta y qué muestra cada pantalla

| `tipo` | Pantalla | Qué hace el script |
|---|---|---|
| `ok` | Página 1 → 2 | Pasa a la elección |
| `duplicado` | Página 1 | Solo el aviso "ya está inscrito", sin datos |
| `formato`, `no_encontrado` | Página 1 | Mensaje con intentos restantes |
| `demasiados_intentos` | Página 1 | Mensaje y botón deshabilitado los minutos de espera |
| `etapa_no_habilitada`, `cerrado` | Página 1 | Aviso; se actualiza sola |
| `registrado` | Página 3 | Confirmación única, sin código |
| `lleno`, `no_disponible`, `combinacion_invalida`, `visita_no_habilitada` | Página 2 | Mensaje y lista actualizada |
| `datos_invalidos`, `celular_invalido`, `sin_consentimiento` | Página 2 | Mensaje junto al formulario |
| `recargar` | Página 1 | Vuelve al inicio con el documento puesto |
| `sin_conexion` | Ambas | Franja gris y mensaje; nada se envía |
| `error_servidor` | Ambas | Mensaje genérico y número de incidencia |
| `panel`, `advertencia`, `requiere_cierre`, `sin_permiso`, `ya_existe`… | Panel | Aviso flotante (`#avisos`) o ventana (`#modal`) |
| `sin_permiso`, `no_autorizado` al entrar | Panel, inicio de sesión | Mensaje en `#msg-login` (cuenta sin rol, desactivada); siempre en el paso visible [Sprint 4] |
| `enlace_usado` | Panel, inicio de sesión | Mensaje en `#msg-login` cuando se reabre un enlace de invitación ya usado o vencido [Sprint 4] |

## 7 · Datos de prueba

**Documentos** (botones en la cinta del modo demo):

| Documento | Caso |
|---|---|
| `04567812` | DNI que empieza con 0. Etapa 1: puede elegir visitas |
| `4123456` | El mismo caso sin el 0 inicial: la base lo completa |
| `12345678K` | Documento extranjero con letra |
| `78695681` | Ya inscrito: solo el aviso |
| `001234567` | Carnet de extranjería, Etapa 2: solo talleres |
| `PA5566778` | Pasaporte, Etapa 2 |
| `42048123` | Etapa 3: aún no habilitada |
| `99999999` | No está en el padrón: descuenta intentos (4 por dispositivo) |
| `12 3` | Formato inválido |

**Cuentas del panel:** Tú (propietario), Ana Rojas (admin), Luis Paz y Rosa Vílchez (operadores), Carla Díaz (sin rol: no entra) y Marco Salas (desactivado: no entra).

**Base ficticia** (generada por `local/generar_datos.py`, siempre igual):

| Dato | Cantidad y casos |
|---|---|
| Padrón | 3201 personas: 1801 de Etapa 1, 1000 de Etapa 2, 400 de Etapa 3; DNI, carnets, pasaportes y casos especiales |
| Actividades | 28: 14 por día (7 visitas y 6 talleres visibles, 1 oculta). VIS03, VIS04 y VIS08 llenas; VIS11 y VIS15 se entregan a mano; TAL10 sin enlace; VIS05 × TAL06 cruce permitido |
| Inscripciones | 700 confirmadas y 20 anuladas: nombres, correos institucionales y celulares inventados; la mitad marcados en su grupo; 39 hechas desde el panel; 3 pares de celulares repetidos; algunos celulares de Chile |
| Bitácora | Ejemplos de apertura, importaciones, respaldos, cambios y anulaciones |

Para probar las importaciones del panel (Sistema): `local/padron_prueba.csv`, `local/padron_importar_ejemplo.csv` (casos difíciles) y `local/actividades_prueba.csv`. El recorrido completo "de la base de prueba a la real" está en la documentación, sección 19.7.

## 8 · Antes de dar por terminado tu diseño

1. En modo demo, recorre los 9 documentos de prueba y completa una inscripción hasta la confirmación.
2. En el panel, entra con las cuatro cuentas y revisa que cada una vea lo que le corresponde.
3. Prueba en un celular o a 390 px de ancho: nada debe desplazarse hacia los lados.
4. Revisa con el teclado: todo se alcanza con Tab y tiene foco visible.
5. Corre el tester de navegador (en Claude Code): si pasa, tu diseño respeta el contrato.
