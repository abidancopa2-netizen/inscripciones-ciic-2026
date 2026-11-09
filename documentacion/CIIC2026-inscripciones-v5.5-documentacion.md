# Sistema de inscripciones CIIC 2026 · v5.5 · Documentación técnica completa

Fecha: 08-11-2026 · Revisión 14 (Sprint 6.2) · Contrato **v5.5 final**. Acompaña a la lámina **INS-07 · Contrato v5.3** (los cambios de la v5.4 y la v5.5 están solo en este documento) y al paquete `inscripciones-ciic-v5.5` (páginas en v5.5, base construida en v5.1 que los sprints llevan a v5.5).

Este documento describe cada pieza del sistema: qué es, qué hace, qué datos recibe y entrega, y qué reglas cumple. Es la referencia para programar, probar, operar y auditar. Los HTML, el SQL y el tester se construyen contra él, por sprints (sección 23).

La revisión 14 (Sprint 6.2) cambia el título y el ejemplo del correo en la página ("Correo institucional", sin cambiar la validación), corrige D15 y R-25 (la barrera real es el límite por red, #46), actualiza 2 filas de §24 y agrega el Security Advisor como riesgo revisado y aceptado (§24). La revisión 13 (Sprint 6.1) agrega la recuperación de contraseña con autenticador y la sesión guardada de otro proyecto (12.5), la contraseña o el celular perdidos sin SQL (12.6), la revocación de la contraseña de aplicación del correo de Supabase (19.8), la decisión de permitir 2 talleres aunque queden visitas (24) y la configuración que muestra `instalar.py --verificar`; no cambia el contrato ni la base. La revisión 12 (Sprint 6) agrega la apertura: fechas reales (congreso del 16 al 21/11, Etapa 1 abre el 11/11, borrado a más tardar el 19/02/2027), `config.js` hacia PRODUCCIÓN sin la clave de prueba en el panel (R-37), textos sin caracteres invisibles (R-47, migración 11), limpieza de intentos con pg_cron cada 5 minutos (R-25, migración 12), congelamiento desde el 10/11 a las 20:00 (20.1), panel que no se deja enmarcar, "Copiar mensaje" y la prueba de ataque (22). La revisión 11 (Sprint 5.1) agrega las redes con intentos fallidos en el panel (R-46), la limpieza de intentos al terminar su ventana (R-25), la fuente alojada en `docs/tema/fuentes/` y el aviso de privacidad corregido (11.3). La revisión 10 (Sprint 5) agrega el aviso de privacidad final (11.3), el tema CIDEIC aparte del contrato (`docs/tema/`, ver `docs/LEEME-DISENO.md` §2.1) y las decisiones del 06/11 (24). La revisión 9 (Sprint 4.1) agrega el ensayo de "Pasar a producción" y "Vaciar" por la API real (21.3) y el respaldo guardado tal como lo da la base (19.3, 19.5). La revisión 8 documenta cómo quedaron construidos, en el Sprint 4, el tráfico (15.14), el respaldo y la restauración (19.3 a 19.5, 21.3) y el inicio de sesión del panel con un enlace ya usado (12.5); no cambia el contrato. La revisión 7 agrega, sin cambiar nada de lo anterior, las decisiones D23 a D25: vaciar los datos de prueba e importar actividades desde el panel, para pasar de la base ficticia a la real sin SQL (sección 19.7), y la base ficticia generada (sección 21.2). La revisión 6 cerró el contrato con las decisiones D15 a D22 (sección 2): la segunda auditoría (sección 3.2), el plan gratuito sin copias automáticas con un respaldo manual desde el panel (sección 19), la protección contra borrados y cambios masivos, las reglas para cambiar el SQL, también para asistentes de IA (sección 20), y las herramientas del panel para no tener que tocar SQL durante el congreso.

Las marcas **[v5.2]**, **[v5.3]**, **[v5.4]** y **[v5.5]** indican en qué versión del contrato cambió cada punto respecto de lo construido en la v5.1. Lo que no tiene marca ya funciona así en el código construido.

---

## Índice

1. Visión general
2. Contrato v5.5 y decisiones
3. Diagnóstico de las auditorías
4. Componentes
5. Reglas (R-01 a R-45)
6. Cerrar y depurar
7. Horarios y cruces
8. Límite de intentos del DNI
9. Soporte y cambio de inscripción
10. Grupos de WhatsApp
11. Datos personales y aviso de privacidad
12. Equipo: cuentas, claves y roles
13. Frontend del participante: contrato de datos
14. Paneles de organización: definición para el frontend
15. Modelo de datos
16. API: acciones
17. Tipos de respuesta
18. Seguridad, emergencias y riesgos aceptados
19. Respaldo, recuperación y retención
20. Reglas para cambiar el SQL (personas e IA)
21. Tecnologías y despliegue
22. Pruebas y aceptación
23. Sprints
24. Decisiones abiertas
25. Ventana al sistema de asistencia
26. Glosario

---

## 1. Visión general

El sistema inscribe a cada asistente del congreso en una combinación de 2 actividades: una visita técnica y un taller, o dos talleres. El asistente entra solo con su documento. La organización controla el proceso desde tres paneles, con cuentas individuales y roles.

Tres principios ordenan todo el diseño:

| Principio | Qué significa | Dónde se aplica |
|---|---|---|
| **Sin datos por DNI** [v5.2] | Con solo un documento nunca se devuelve nada de una inscripción existente: solo "ya inscrito". | Verificar, inscribir |
| **Una sola puerta** | Toda lectura y escritura pasa por la función `public.api(p)`. Las tablas están cerradas a la clave pública. | Base de datos |
| **Agregar en vivo, quitar cerrado** | Los cambios que agregan opciones se aplican con el sistema abierto. Los que quitan opciones exigen cerrar las inscripciones. | Todas las acciones del panel |
| **La ronda ordena el tiempo** | Cada cierre sube un contador llamado ronda: el número de edición del sistema. Una página que verificó en una ronda anterior no puede confirmar: vuelve al inicio. | Verificar, inscribir, página |

---

## 2. Contrato v5.5 y decisiones

| # | Decisión | Definición | Efecto en el contrato |
|---|---|---|---|
| D1 | Qué ve quien conoce un DNI inscrito | Solo "ya inscrito". No hay comprobantes. La confirmación se muestra una sola vez, sin código | `duplicado` sin datos; `registrado` sin `codigo` |
| D2 [v5.3] | Etapa por persona | **Una sola y fija.** `documento` es la clave del padrón; ninguna acción cambia la etapa. Si se cargó mal: quitar (sin inscripción, con el sistema cerrado) y volver a agregar | `panel_padron_agregar` → `ya_existe` si el documento existe |
| D3 | Refresco | Una sola llamada: `estado` con `conActividades: true` | Campo nuevo |
| D4 | Idempotencia | `solicitud` en toda escritura; el panel envía el cupo final | `solicitud`, `repetida`, `solicitud_repetida`; sin `delta` |
| D5 | Errores | Número de incidencia; detalle privado para el admin | `error_servidor` con `incidencia`; `panel_incidencias` |
| D6 [v5.3] | Privacidad | Aviso y casilla obligatoria. El aviso dice además que los encargados de cada actividad reciben la lista de sus participantes | `aceptaPrivacidad` |
| D7 | Contadores | Trigger desde `inscripcion_actividades`; integridad visible | `panel_resumen.integridad` |
| D8 | Clave del tester en producción | Se borra sola al pasar a PRODUCCION | — |
| D9 | Propietario | Único: el creador, designado por SQL e inamovible desde el panel | `panel_equipo_rol` sin "propietario" |
| D10 [v5.3] | Saturación | Ventanas de 10 s. Alerta solo si **3 ventanas seguidas** pasan el umbral (2000 llamadas por ventana). Una ráfaga de apertura no alerta | `panel_resumen.trafico` |
| D11 [v5.3] | Datos | **Padrón mínimo**: documento y etapa (más un campo libre opcional que no valida nada). Los datos de la persona salen del formulario: nombres, apellidos, **correo institucional obligatorio** y WhatsApp | `correo` obligatorio; padrón sin nombres |
| D12 [v5.3] | Listas por actividad | Participantes de cada visita o taller ordenados por apellidos con DNI, nombres, apellidos, correo, celular y etapa; marca de "en el grupo" guardada en la base; copiar números; .vcf; CSV por actividad, por etapa y de todas, descargable desde el nivel 1 | `panel_lista`, `panel_grupo_marcar`, `panel_exportar` |
| D13 [v5.3] | Roles por nivel | Nivel 1 consulta (operador) · nivel 2 modificaciones (admin) · nivel 3 habilitan el sistema (propietario). Cerrar en emergencia es nivel 2; abrir, nivel 3 | `sin_permiso` con `nivel` |
| D14 [v5.3] | Emergencias | Por gravedad y sin pausar el proyecto (sección 18.2) | — |

| D15 [v5.4] | Suplantación | Riesgo aceptado: no hay segundo dato. **La barrera real es el límite por red** (300 documentos fallidos cada 10 minutos por la IP que pone Cloudflare, que no se puede falsear). El de 4 por dispositivo frena con un mensaje claro a quien se equivoca, pero se reinicia con una ventana de incógnito u otro navegador [Sprint 6.2, #46]. Si después existe un código de entrada por persona, se agrega como segundo dato | — |
| D16 [v5.4] | Correo | Obligatorio y de cualquier dominio [Sprint 5.1]. Sirve para conciliar, para identificar impostores y, solo si WhatsApp no alcanza, para avisar cambios o cancelaciones de una actividad (finalidad 4 del aviso). El dato clave de contacto es el celular | `correo` también en `panel_inscribir` |
| D17 [v5.4] | Plan gratuito | Sin plan de pago. Sin copias automáticas: respaldo manual desde el panel, cada hora el día de apertura (RPO 1 h) y restauración en menos de 2 h (RTO) | `panel_respaldo`, `restaurar.py` |
| D18 [v5.4] | Congelamiento | Desde 24 h antes de abrir hasta el fin del congreso (incluida la semana de exámenes) no se corre SQL en producción: todo por el panel | — |
| D19 [v5.4] | Protección masiva | La base bloquea `DELETE`, `UPDATE` y `TRUNCATE` que afecten más de 10 filas de las tablas críticas, salvo permiso explícito en esa transacción | Trigger por sentencia |
| D20 [v5.4] | Retención | 90 días después del congreso; al día 90 se borra el proyecto de Supabase, los respaldos y los CSV | — |
| D21 [v5.4] | Cloudflare, cifrado de campos, permisos por actividad | Cloudflare solo si las pruebas de destrucción lo piden. Sin cifrado de campos. El operador conserva listas y CSV | — |
| D22 [v5.4] | Operar sin SQL | El panel suma: importar padrón (CSV con documento y etapa), pasar a producción, recontar inscritos y respaldo | `panel_padron_importar`, `panel_preparar_produccion`, `panel_sincronizar` |
| D23 [v5.5] | Vaciar datos de prueba | Desde el panel, en modo PRUEBA y con el sistema cerrado: borra padrón, actividades, inscripciones y bitácora de prueba; conserva configuración y equipo | `panel_vaciar_prueba` |
| D24 [v5.5] | Importar actividades | El catálogo se carga desde un CSV en el panel; las que ya existen no se modifican | `panel_actividades_importar` |
| D25 [v5.5] | Base ficticia | Un generador produce siempre la misma base inventada: 3201 personas en el padrón, 28 actividades, 700 inscripciones y 20 anuladas, para la demo, la base local y los CSV de importación | — |

Siguen abiertas, sin tocar el contrato: combinar el mismo día, el margen de traslado y desde cuándo avisar ampliaciones (sección 24).

## 3. Diagnóstico de las auditorías

### 3.1 Primera auditoría

Una auditoría externa revisó la revisión 1 de este documento y la lámina INS-05, sin ver el SQL. Cada hallazgo se contrastó con el código v5.1 construido:

| Hallazgo de la auditoría | Contra el código v5.1 | Decisión v5.2 | Sprint |
|---|---|---|---|
| El DNI entrega el comprobante | Confirmado: devolvía código, actividades y enlaces | D1 | 1 |
| Detalle de errores | Peor de lo supuesto: el mensaje de PostgreSQL llegaba también a la página pública | D5 | 1 |
| IP del límite por red | Confirmado: se tomaba el primer valor de `x-forwarded-for`, que el cliente puede escribir | Cabecera del proxy de Supabase, confirmada en el proyecto real | 1 y 3 |
| Reintentos e idempotencia | Confirmado: el panel reintentaba escrituras y "+5" podía sumar dos veces | D4 | 2 |
| Contadores desincronizados | Parcial: todas las rutas de la API están bien; una edición a mano no | D7 | 2 |
| CSV y fórmulas | Parcial: se limpiaba al guardar (alterando el dato), no al exportar | Neutralizar en la exportación; guardar el dato original | 2 |
| Permisos de PostgreSQL | Implementado (revoke, esquema privado, `search_path` fijo); faltaba demostrarlo | Bloque de pruebas de privilegios | 1 |
| Rol verificado en el servidor | Implementado y probado | Sin cambios | — |
| Desactivar cuenta con sesión abierta | Implementado: se relee en cada llamada | Sin cambios | — |
| Último propietario | De hecho garantizado | D9 | 1 |
| Función monolítica; validación repetida | Ya era un despachador con una sola función de combinación | Sin cambios | — |
| El simulador como única verdad | Desactualizado: el SQL real pasó 163 pruebas | Las pruebas siguen contra el SQL | — |
| Padrón en varias etapas | Decisión pendiente | D2: una sola etapa, fija | 2 |
| Limitar todas las acciones públicas en la base | Descartado: cada lectura se volvería una escritura | D10 y D3 | 4 |
| Retroceso exponencial | Matizado | Exponencial con azar para fallos de red; corto para `ocupado` | 4 |
| Privacidad | Faltaba | D6 | 4 |
| Respaldos y restauración | Faltaba | Copia completa y simulacro (sección 18.3) | 4 |
| (No lo vio la auditoría) Script de Supabase desde una CDN | Sin verificación de integridad | Hash de integridad y política de contenido | 1 |

Durante la construcción de la lámina INS-07, el simulador encontró además que sus propios datos de prueba tenían contadores sin inscripciones reales: el indicador de integridad lo marcó al instante. Es lo que debe hacer en producción.

### 3.2 Segunda auditoría [v5.4]

Revisó la revisión 5, la lámina INS-07 y el flujo `mantener-activo.yml`, sin el SQL ni las páginas reales. Cada punto se contrastó con lo construido:

| Hallazgo | Contra lo construido | Decisión v5.4 |
|---|---|---|
| R-01 contradecía a D1 (duplicado con comprobante) | Confirmado | R-01 corregida: solo "ya inscrito" |
| `panel_inscribir` sin correo | Confirmado | Correo obligatorio también en el panel |
| Exportaciones sin rastro | Confirmado | Cada CSV y .vcf queda en la bitácora (R-39) |
| Idempotencia sin ámbito | Válido para el diseño | Clave = solicitud + acción + quien llama; formato UUID; vence a las 24 h (R-32) |
| Cambios de rol sin valor anterior | Confirmado | Bitácora con "antes → después" (R-30) |
| Flujo de mantener activo | Confirmado: imprimía la respuesta y usaba una acción sin fijar | Sin acciones de terceros; valida HTTP 200 y JSON con `jq`; no imprime la respuesta (21.1) |
| Retención, RPO, RTO y procedimientos de recuperación sin definir | Confirmado | Sección 19 |
| `innerHTML` y escape en el frontend | Ya resuelto en las páginas reales (todo con `textContent`); el simulador escapaba comillas dobles, no simples | Escapar también comillas simples en el simulador |
| `SECURITY DEFINER`, `search_path`, permisos | Ya implementado | Prueba automática de privilegios (bloque R) |
| `api()` monolítica | Ya es un despachador | Dividir `02_api.sql` en archivos por módulo al tocarlo (sección 20) |
| OTP al correo institucional | Discrepancia: el correo lo escribe la misma persona; un impostor recibiría su propio código | Descartado (D15, D16) |
| WAF o proxy con límite por IP | Correcto, pero no cabe en el plazo | Solo si las pruebas de destrucción lo piden (D21) |
| Cifrado de campos | Rompería la búsqueda por DNI y celular | Descartado (D21) |
| Permisos por actividad; separar la exportación masiva | Decisión ya tomada | Se mantiene; se registra cada descarga (D21, R-39) |
| La secuencia del tráfico como cuello de botella | `nextval` no bloquea filas ni participa en transacciones | Se mide en la prueba de 1000 |
| Pipeline completo (ramas, linters, aprobaciones) | Sobrecosto para un solo desarrollador en el plazo | Lo esencial en la sección 20 |

## 4. Componentes

| Componente | Qué es | Función | Dónde vive |
|---|---|---|---|
| Página de inscripción | HTML, CSS y JS con tu diseño | Las tres pantallas del participante: documento, elección y datos, comprobante | GitHub Pages |
| Panel de organización | HTML, CSS y JS con tu diseño, con cuatro pestañas | Operación, participantes, actividades y Equipo | GitHub Pages |
| `config.js` | Archivo de configuración de las páginas | Guarda `API_URL` y `ANON_KEY`; nada más | GitHub Pages |
| Supabase Auth | Servicio de cuentas | Invitación, inicio de sesión del equipo con correo, contraseña y código TOTP, recuperación | Supabase |
| `public.api(p)` | Función PL/pgSQL | Recibe cada pedido, revisa permisos y reglas, y responde JSON | Supabase (PostgreSQL) |
| Funciones `privado.*` | Funciones PL/pgSQL internas | Lógica de cada acción; no se publican | Supabase (PostgreSQL) |
| Tablas | PostgreSQL | La fuente de verdad (sección 15) | Supabase (PostgreSQL) |
| `excel_a_sql.py` | Script de Python | Convierte tu hoja de cálculo en SQL para cargar padrón y actividades | Tu computadora |
| Tester | Python con Playwright | Prueba reglas, navegador, carga y avalancha | GitHub Actions |
| Servidor local | Python con PostgreSQL local | Prueba todo sin cuenta de Supabase | Tu computadora |
| Simulador | JavaScript dentro de la lámina | Recorre las reglas con datos de prueba antes de programar | Lámina INS-06 |
| Grupos de WhatsApp | Un grupo por actividad, con "Aprobar nuevos participantes" | Coordinación con los inscritos | WhatsApp |

---

## 5. Reglas

Cada regla indica qué dice, por qué existe, dónde se valida, qué responde si no se cumple, quién la cambia y si el cambio se puede hacer con el sistema abierto.

### R-01 · Una inscripción confirmada por documento
- **Qué dice:** un documento tiene como máximo una inscripción en estado CONFIRMADO. Vale para la página y para el panel.
- **Por qué:** evita que una persona ocupe cuatro cupos.
- **Dónde:** índice único parcial `un_confirmado_por_documento` en `inscripciones`.
- **Si falla:** [v5.4] `duplicado` con un único mensaje, "Este documento ya está inscrito"; nunca código, actividades ni enlaces (R-31).
- **Quién la cambia:** nadie (fija).

### R-02 · Combinación de 2 actividades
- **Qué dice:** exactamente 2 actividades distintas; máximo 1 visita. Válidas: 1 visita + 1 taller, o 2 talleres.
- **Por qué:** es el formato del congreso.
- **Dónde:** `api()`, con los máximos de `tipos_actividad` (VISITA 1, TALLER 2) y `config` (total 2).
- **Si falla:** `combinacion_invalida` con `motivo: "cantidad"` o `"dos_visitas"`.
- **Quién la cambia:** fija en el código de la regla; los máximos por tipo se pueden ajustar en SQL.

### R-03 · Horarios
- **Qué dice:** con `mismo_dia = false` (por defecto), las 2 actividades deben ser de días distintos. Con `mismo_dia = true`, pueden ser el mismo día si no se cruzan: entre el fin de una y el inicio de la otra debe haber al menos `margen_min` minutos. Un par puede autorizarse aunque se cruce, en `cruces_permitidos`.
- **Por qué:** una persona no puede estar en dos lugares a la vez, y necesita tiempo de traslado.
- **Dónde:** `api()`; la página lo anticipa marcando "Se cruza con …".
- **Si falla:** `combinacion_invalida` con `motivo: "mismo_dia"` o `"cruce"`.
- **Quién la cambia:** admin, Panel 3. Permitir el mismo día, bajar el margen o permitir un par: abierto. Volver a una por día, subir el margen o bloquear un par: cerrado.

### R-04 · Todo o nada
- **Qué dice:** las 2 actividades se guardan juntas en una transacción o no se guarda ninguna.
- **Dónde:** transacción de `registrar`, `panel_inscribir` y `panel_cambiar`.
- **Quién la cambia:** nadie.

### R-05 · Sin sobrecupo
- **Qué dice:** `inscritos` nunca supera `cupo`, aunque cientos confirmen a la vez.
- **Dónde:** `CHECK (inscritos between 0 and cupo)` y bloqueo `FOR UPDATE` de las filas de las actividades elegidas, siempre en orden de ID.
- **Si falla:** `lleno` con `actividadId`.
- **Quién la cambia:** el cupo, Panel 1.

### R-06 · Etapas que pueden inscribirse
- **Qué dice:** solo pasan la pantalla 1 los documentos de una etapa incluida en `config.etapas`.
- **Si falla:** `etapa_no_habilitada` con la etapa de la persona.
- **Quién la cambia:** operador, Panel 1. Agregar etapa: abierto. Quitar: cerrado.

### R-07 · Etapas que pueden elegir visitas
- **Qué dice:** solo las etapas en `config.etapas_visita` pueden elegir visitas. Por defecto, la Etapa 1. Las demás etapas habilitadas se inscriben en 2 talleres. Una etapa con visitas pero sin inscripción no tiene efecto. Las visitas se reparten por orden de llegada.
- **Reemplaza a:** "talleres siguen las etapas" de la v4, que decía lo mismo de forma indirecta.
- **Dónde:** `verificar` devuelve `puedeVisita`; `registrar` lo vuelve a revisar.
- **Si falla:** `visita_no_habilitada`.
- **Quién la cambia:** operador, Panel 1. Agregar: abierto. Quitar: cerrado.

### R-08 · Exigir visita mientras queden
- **Qué dice:** con `dos_talleres = false`, quien puede elegir visitas debe incluir una mientras alguna visita visible tenga cupo.
- **Si falla:** `combinacion_invalida` con `motivo: "falta_visita"`.
- **Quién la cambia:** operador, Panel 1. Permitir 2 talleres: abierto. Exigir visita: cerrado.

### R-09 · Cerrar y depurar
- **Qué dice:** botón "Cerrar ahora" con ventana de confirmación. Cerrar espera a las inscripciones en curso, pone `abierto = false` y sube `ronda` en 1. Con el sistema cerrado, toda confirmación recibe `cerrado`. Al reabrir, una confirmación con una ronda anterior recibe `recargar`.
- **Detalle:** sección 6.
- **Quién la cambia:** operador, Panel 1.

### R-10 · Quitar opciones exige cerrar
- **Qué dice:** con el sistema abierto, la base rechaza con `requiere_cierre` todo cambio que quite opciones: reducir cupo, ocultar actividad, quitar etapa de inscripción o de visitas, exigir visita, volver a una actividad por día, subir el margen, bloquear un cruce, quitar del padrón y editar el horario de una actividad visible.
- **Por qué:** quien está eligiendo no debe encontrar que su opción desapareció entre una pantalla y otra.
- **Quién la cambia:** nadie (fija).

### R-11 · Bajar cupo por debajo de los inscritos
- **Qué dice:** no falla. Responde `advertencia` y ofrece dejar el cupo igual a los inscritos (la actividad queda llena). Nunca anula a nadie.
- **Requiere:** sistema cerrado (es una reducción).
- **Quién la cambia:** operador, Panel 1.

### R-12 · Documento
- **Qué dice:** 6 a 12 letras o números, con al menos un número. Se normaliza: mayúsculas, sin espacios, puntos ni guiones; un DNI numérico de menos de 8 dígitos se completa con ceros a la izquierda.
- **Si falla:** `formato`, cuenta como intento fallido.

### R-13 · Celular
- **Qué dice:** obligatorio, con código de país. Perú: 9 dígitos que empiezan con 9. Otros países: 6 a 14 dígitos. Se guarda como `+51987654321`. [v5.3] El **correo institucional** también es obligatorio, con formato válido.
- **Si falla:** `celular_invalido`.

### R-14 · Consentimiento
- **Qué dice:** [v5.2] `aceptaPrivacidad` y `aceptaWhatsapp` deben ser `true`. La página los marca con una sola casilla que cubre el aviso de privacidad y el contacto por WhatsApp. También desde el panel. Se guarda `aviso_version`.
- **Dónde:** `api()` y `CHECK (acepta_whatsapp and acepta_privacidad)`.
- **Si falla:** `sin_consentimiento`.

### R-15 · Celular repetido
- **Qué dice:** se permite (hermanos, padres), pero el Panel 1 lo lista para revisar.

### R-16 · Enlace del grupo
- **Qué dice:** [v5.2] el enlace de WhatsApp solo aparece en la confirmación, una sola vez, a quien se acaba de inscribir en esa actividad. Nunca por DNI ni en la lista pública.

### R-17 · Quitar una actividad
- **Qué dice:** solo si está oculta y sin inscritos.
- **Si falla:** `esta_visible` o `tiene_inscritos`.

### R-18 · Datos fijos de una actividad
- **Qué dice:** con inscritos, tipo, fecha, inicio y fin no cambian. Sin inscritos: libres si está oculta; si está visible, solo con el sistema cerrado. Nombre, lugar, información y enlace se editan siempre.
- **Por qué:** cambiar el horario de una actividad con inscritos obligaría a revisar cruces y avisar a cada persona, y podría invalidar combinaciones ya confirmadas.
- **Si cambia de verdad:** crear otra actividad y mover a cada persona con "Cambiar inscripción" (R-21).
- **Si falla:** `tiene_inscritos` o `requiere_cierre`.

### R-19 · Paso de cupo
- **Qué dice:** los botones de cupo del Panel 1 suman o restan `paso_cupo` (1 a 100, por defecto 5). [v5.2] Calculan y envían el cupo final, nunca el incremento.

### R-20 · Inscribir desde el panel
- **Qué dice:** un admin inscribe a una persona del padrón en la combinación que elija. Ignora abierto, etapas, etapas de visita y ronda. Respeta R-01, R-02, R-03, R-13 (incluido el correo institucional [v5.4]), R-14 y el padrón. Si una actividad está llena, responde `advertencia`; al confirmar con la llave (el ID), amplía su cupo en 1.
- **Registro:** `origen = 'PANEL'`, `registrado_por` y entrada en la bitácora.
- **Sistema:** abierto o cerrado.

### R-21 · Cambiar inscripción
- **Qué dice:** un admin cambia las actividades de una inscripción confirmada en una sola transacción. Conserva su código interno (solo lo ve el panel). Mismas reglas que R-20.
- **Detalle:** sección 9.

### R-22 · Padrón de último momento
- **Qué dice:** [v5.3] un admin agrega un documento con su etapa, nada más. La etapa es fija: si el documento ya existe, `ya_existe` con su etapa. Para corregir un error: quitar (R-23) y volver a agregar. Queda con `origen = 'PANEL'`.

### R-23 · Quitar del padrón
- **Qué dice:** solo sin inscripción confirmada y con el sistema cerrado. [v5.2] Se identifica solo por documento.

### R-24 · Crear actividades
- **Qué dice:** se crean en el Panel 3 con su cupo inicial y nacen ocultas. Se muestran desde el Panel 1.

### R-25 · Límite de intentos
- **Qué dice:** 4 documentos fallidos por dispositivo en 10 minutos; 300 por red en 10 minutos [Sprint 5.1; antes 30]. Un acierto reinicia el contador del dispositivo. La ventana es fija, alineada al reloj (hh:00, hh:10…): al empezar la siguiente, el contador vuelve a 0. Los límites se cambian desde Operación → Redes con intentos fallidos (propietario) y valen de inmediato.
- **Retención [Sprint 5.1]:** las filas de `intentos` (IP de la red e identificador del navegador) se borran en cuanto termina su ventana. Lo hace la consulta `estado` (`privado.limpiar_intentos`), que las páginas abiertas repiten cada 20 s, de a una por vez y con `SKIP LOCKED`: nunca espera ni hace esperar a verificar o registrar. Sin visitas, la base misma llama a `privado.limpiar_intentos()` cada 5 minutos con pg_cron [Sprint 6, migración 12]: una fila dura a lo más su ventana más 5 minutos. Antes lo cubría la consulta horaria de "Mantener Supabase activo", pero GitHub atrasa o se salta ese horario (incidencia #40). Si una base no tiene pg_cron (la local), la limpieza sigue con `estado` y "Mantener activo". Nunca entran en el respaldo.
- **Detalle:** sección 8.

### R-26 · Roles por nivel [v5.3]
- **Qué dice:** cada acción tiene un nivel y cada rol llega hasta uno. Operador: nivel 1. Admin: niveles 1 y 2. Propietario: los tres.
- **Nivel 1 · consulta:** ver el resumen y los totales, buscar, ver participantes, listas por actividad, **descargar sus CSV y .vcf** (solo leen: el operador ya ve esos datos en pantalla), verificar solicitudes de WhatsApp, marcar quién está en el grupo.
- **Nivel 2 · modificaciones:** cupos, mostrar u ocultar, crear, editar y quitar actividades, cruces, inscribir, cambiar, anular, padrón, incidencias, paso de cupo, y **cerrar** (ahora o con aviso), para que cualquier admin pueda frenar en una emergencia.
- **Nivel 3 · habilitan el sistema:** **abrir**, etapas de inscripción y de visitas, permitir 2 talleres, mismo día y margen, refresco, límites de intentos, umbral de saturación, Equipo.
- **Dónde:** `api()` revisa el nivel antes de cada acción; `panel_config` lo decide por campo.
- **Si falla:** `sin_permiso` con `nivel`.

### R-27 · Avisar y cerrar
- **Qué dice:** el operador puede programar el cierre en 1, 2, 5 o 10 minutos. `estado.cierraEn` lleva los segundos que faltan y cada página muestra una cuenta regresiva. Al llegar la hora, la primera llamada a `api()` aplica el cierre (como R-09). Se puede cancelar el aviso o cerrar antes.
- **Por qué:** quien está a punto de confirmar no pierde su elección sin aviso.
- **Dónde:** `config.cierre_en` y `privado.aplicar_cierre_programado()` al inicio de `api()`.
- **Sistema:** abierto.

### R-28 · Refresco inmediato de la página
- **Qué dice:** la página consulta `estado` cada `refresco` segundos, al volver la conexión (evento `online`) y al volver a la pestaña (evento `visibilitychange`). Sin conexión, no envía nada y lo dice.
- **Por qué:** una página que estuvo sin internet o en segundo plano debe adaptarse al sistema actual antes de que la persona siga eligiendo.
- **Dónde:** página.

### R-29 · Entrega del grupo de WhatsApp
- **Qué dice:** cada actividad tiene `grupo_modo`: ENLACE (el comprobante muestra el enlace) o MANUAL (el comprobante dice "te agregaremos"). Las solicitudes de ingreso se verifican por celular contra los inscritos de esa actividad.
- **Detalle:** sección 10.
- **Quién la cambia:** admin, Panel 3. Verificar solicitudes: operador.

### R-30 · Equipo
- **Qué dice:** las cuentas se crean por invitación, con el registro abierto desactivado. Una cuenta sin rol o desactivada no puede hacer nada. [v5.2] El propietario es único (índice único en `organizadores`), se asigna solo por SQL y el panel no puede modificarlo ni desactivarlo. Desde el panel solo se asignan operador y admin. [v5.4] Cada cambio de rol o de estado de una cuenta queda en la bitácora con el valor anterior y el nuevo.
- **Detalle:** sección 12.
- **Quién la cambia:** propietario, pestaña Sistema → Equipo.

---

### R-31 · Sin comprobantes [v5.2]
- **Qué dice:** con solo el DNI nunca se devuelve código, actividades ni enlaces de una inscripción existente. `verificar` y `registrar` responden `duplicado` con un único mensaje.
- **Por qué:** cualquiera que conozca un DNI podría ver la inscripción de otra persona.
- **Dónde:** `api()`.

### R-32 · Idempotencia [v5.2]
- **Qué dice:** cada escritura (inscribir y toda acción del panel que cambie algo) lleva `solicitud`. La base guarda su huella y su respuesta. El mismo reenvío con los mismos datos recibe la misma respuesta con `repetida: true` y no repite el cambio. La misma `solicitud` con otros datos recibe `solicitud_repetida`.
- **Dónde:** `privado.solicitudes`, dentro de la misma transacción del cambio.
- **Ámbito [v5.4]:** la clave es solicitud + acción + quien llama (la cuenta en el panel; el documento en la página). La `solicitud` debe ser un UUID; otro formato responde `valor_invalido`. Vence a las 24 h. Así nadie puede ocupar ni chocar con la solicitud de otra persona.
- **Por qué:** si se pierde la respuesta, reintentar no debe inscribir dos veces ni sumar un cupo dos veces.

### R-33 · Contadores por trigger [v5.2]
- **Qué dice:** `actividades.inscritos` lo mueve un trigger: al insertar o borrar filas de `inscripcion_actividades` y al cambiar el estado de una inscripción. Ninguna función lo suma a mano. `panel_resumen` compara cada contador con sus inscripciones confirmadas y muestra la integridad.
- **Por qué:** cubre también las ediciones a mano en el editor de tablas de Supabase.

### R-34 · Alerta de saturación [v5.3]
- **Qué dice:** cada llamada suma 1 a una secuencia (`nextval`, sin escribir filas). Cada 10 segundos se guarda una foto del contador: las llamadas de esa ventana son la diferencia entre dos fotos. Si **3 ventanas seguidas** (30 s) pasan `config.umbral_ventana` (2000 por defecto), el panel muestra la alerta y la bitácora la registra. No bloquea a nadie.
- **Por qué así:** que 500 o 1000 personas entren en el mismo segundo es normal en la apertura y no debe alarmar: es una ráfaga de una ventana. Un ataque se reconoce porque se sostiene. Un promedio por minuto escondería las ráfagas y tardaría en ver un ataque.
- **Cálculo:** 500 personas refrescando cada 20 s hacen unas 250 llamadas por ventana; 1000, unas 500. La apertura puede llegar a 1000–3000 en una sola ventana. El umbral de 2000 sostenido 30 s está muy por encima de lo legítimo sostenido.
- **En las pruebas:** el tester baja el umbral para comprobar que la alerta se enciende, y lo restaura.
- **Limpieza [v5.4]:** solo se guardan los últimos 2 días de fotos.

### R-35 · Padrón mínimo [v5.3]
- **Qué dice:** el padrón valida solo con documento y etapa. Un campo libre opcional (`datos`) guarda lo que entregue la universidad sin usarse para validar. Los datos de la persona (nombres, apellidos, correo institucional, celular) salen del formulario.

### R-36 · Incidencias [v5.2]
- **Qué dice:** un error interno responde `error_servidor` con un número de incidencia. El detalle técnico se guarda en `privado.incidencias`, sin datos personales, y lo ve el admin en el Panel 1.

### R-37 · Producción sin clave de prueba [v5.2]
- **Qué dice:** un trigger en `config` borra `ADMIN_KEY` cuando el modo pasa a PRODUCCION. Volver a PRUEBA no la recupera: hay que crear otra.
- **En el panel [Sprint 6]:** con `PANEL_PRUEBA: false` en `config.js` (lo pone `sprints/sprint-6/configurar.py` al apuntar a PRODUCCIÓN), el panel publicado no muestra "Entrar con la clave de prueba", aunque la base siga en modo PRUEBA hasta "Pasar a producción". El tester en modo lectura lo comprueba en la página publicada, sin inyectar nada.

### R-47 · Textos limpios [Sprint 6]
- **Qué dice:** nombres, apellidos, correo y los textos de actividades y padrón se guardan sin caracteres de control ni invisibles o de dirección (U+200B…U+200F, U+202A…U+202E, U+2060…U+2064, U+2066…U+2069, U+FEFF), con los espacios juntados y sin `=`, `+`, `-` ni `@` al inicio. Hasta 60 caracteres en nombres y apellidos.
- **Por qué:** la prueba de ataque del Sprint 6 guardó un apellido con U+202E, que muestra el texto al revés en el panel y en el CSV.
- **Dónde:** `privado.texto_limpio` (migración 11).

### R-38 · Listas por actividad [v5.3]
- **Qué dice:** por visita o taller (o de todas) y por etapa (o todas), los participantes confirmados ordenados por apellidos y nombres, con DNI, correo, celular, etapa, código interno, origen y estado de grupo. Se buscan por número, DNI o nombre. Cada persona y actividad tiene una marca "en el grupo" (`en_grupo`), con quién la puso y cuándo. El botón la guarda en la base en una transacción con `solicitud` (repetir el clic por una respuesta perdida no la cambia dos veces) y la pantalla se vuelve a leer de la base, así que lo que ves es lo que quedó guardado.
- **Por qué:** aprobar solicitudes y agregar a mano a los grupos de WhatsApp desde una lista, no a ciegas.
- **Nivel:** 1.

### R-39 · CSV de las listas [v5.3]
- **Qué dice:** una fila por persona y actividad, con actividad, nombre de la actividad, fecha, horario, DNI, apellidos, nombres, correo, celular, etapa, código, origen y "en el grupo". Por actividad, por etapa o de todas. Las celdas que empiezan con `=`, `+`, `-`, `@`, tabulación o salto se neutralizan al exportar.
- **Para quién:** los encargados de cada visita o taller, que arman con él sus bases de asistencia o de solicitudes. Cada encargado recibe solo la lista de su actividad.
- **Nivel:** 1. Descargar no modifica nada y el operador ya ve esos datos en Listas.
- **Registro [v5.4]:** cada descarga (CSV o .vcf) queda en la bitácora: quién, filtros de actividad y etapa, cuántas filas y cuándo.

### R-40 · Protección contra operaciones masivas [v5.4]
- **Qué dice:** un trigger por sentencia en `padron`, `actividades`, `cruces_permitidos`, `inscripciones`, `inscripcion_actividades` y `organizadores` bloquea todo `DELETE` o `UPDATE` que afecte más de `config.limite_masivo` filas (10 por defecto), y todo `TRUNCATE`. Solo pasan si en esa misma transacción se declaró `set local ciic.masivo = 'confirmado'`.
- **Por qué:** el error más probable es humano: un `DELETE` o `UPDATE` sin `where` en el SQL Editor. Con la protección, un `delete from inscripciones;` responde un error claro y no borra nada.
- **Las funciones del sistema** que tocan muchas filas a propósito (recontar, preparar producción, limpiar pruebas, restaurar) declaran el permiso ellas mismas.
- **Si falla:** `ERROR: operación masiva bloqueada (N filas en inscripciones)…`, con la instrucción de hacer un respaldo antes.
- **Límite honesto:** no protege contra `DROP TABLE` ni contra borrar el proyecto: para eso están el congelamiento y el respaldo (secciones 19 y 20).

### R-41 · Respaldo desde el panel [v5.4]
- **Qué dice:** el propietario descarga con un clic un archivo `respaldo-ciic-AAAAMMDD-HHMM.json` con todas las tablas de datos, la versión del esquema, el conteo de filas por tabla y una huella SHA-256 del contenido. Queda en la bitácora.
- **Restaurar:** `supabase/restaurar.py` convierte el archivo en SQL para el SQL Editor: completo (base nueva) o solo lo que falta (filas borradas por error). Detalle en la sección 19.
- **Nivel:** 3.

### R-42 · Importar padrón desde el panel [v5.4]
- **Qué dice:** el propietario sube un CSV con dos columnas, documento y etapa (hasta 10 000 filas). La base agrega los nuevos y responde un informe: agregados, ya existían con la misma etapa, conflictos (ya existían con otra etapa: no se cambian, R-22) e inválidos. Repetir la misma importación no duplica nada.
- **Por qué:** cargar o ampliar el padrón sin tocar SQL.
- **Lotes [Sprint 2.1]:** el panel envía el archivo en lotes de hasta 2000 filas, con su progreso. Cada lote es una operación independiente (atómica dentro del lote) y deja su entrada en la bitácora con su número ("lote 2/5"). Si un lote falla, los anteriores quedan; reimportar el mismo archivo es seguro: lo ya agregado cuenta como "ya existía".
- **Nivel:** 3.

### R-43 · Pasar a producción desde el panel [v5.4]
- **Qué dice:** con el sistema cerrado, en modo PRUEBA y escribiendo la llave `PRODUCCION`, el propietario vacía lo de prueba (inscripciones y sus actividades, bitácora, intentos, solicitudes, tráfico e incidencias), recuenta los contadores y pasa el modo a PRODUCCION (R-37 borra la clave del tester). No toca el padrón ni las actividades, salvo los documentos del tester (`ZQX…`, que ninguna persona real tiene) [Sprint 4].
- **Por qué:** era el paso con SQL más peligroso de la lista de apertura.
- **Nivel:** 3. Queda en la bitácora como primera entrada de producción.

### R-44 · Vaciar datos de prueba [v5.5]
- **Qué dice:** con la base en modo PRUEBA, el sistema cerrado y la llave `VACIAR`, el propietario borra el padrón, las actividades, los cruces permitidos, las inscripciones y sus actividades, la bitácora, los intentos, las solicitudes, el tráfico y las incidencias. Conserva la configuración, los tipos de actividad y el equipo. Declara el permiso de R-40 en su transacción.
- **Por qué:** pasar de la base ficticia a la real sin SQL (sección 19.7).
- **En Supabase [Sprint 3.2]:** sus 8 borrados llevan `where true`, porque Supabase carga `safeupdate` en las conexiones de la API y rechaza todo `DELETE` o `UPDATE` sin `WHERE` (error 21000). Hallado contra PRUEBA, en la Fase C del Sprint 3.
- **Si falla:** `modo_produccion` (ya en producción), `requiere_cierre` (abierto), `valor_invalido` (llave incorrecta).
- **Nivel:** 3. Queda como primera entrada de la bitácora nueva, con lo que se borró.

### R-45 · Importar actividades [v5.5]
- **Qué dice:** el propietario sube un CSV con encabezado (sección 14.6), hasta 500 actividades. Cada fila se valida como en `panel_crear` (tipo, nombre, fecha, horas, cupo, entrega y enlace). Con `id` existente: no se modifica y se informa. Sin `id`: se asigna el siguiente (`VIS…`, `TAL…`). Nacen ocultas salvo `visible = SI`.
- **Si falla:** el informe lista cada fila inválida con su motivo; las válidas se agregan igual.
- **Nivel:** 3.

### R-46 · Redes con intentos fallidos [Sprint 5.1]
- **Qué dice:** el panel (Operación) muestra a admin y propietario las redes de la ventana actual con 50 fallos o más, o con el 80 % del límite si el límite es bajo (con 5, desde 4). Por red: la IP enmascarada (`190.234.•.•`, IPv6 `2800:200:•`), los fallos, el % del límite, los minutos para que se reinicie y el estado: normal, cerca (80 %) o frenada (el límite). La franja de arriba avisa cuando una red está cerca o frenada. El propietario puede **Liberar red**: su contador vuelve a 0 y queda en la bitácora con la IP enmascarada.
- **Privacidad:** la IP completa nunca sale de la base. Cada red viaja con un id opaco (HMAC con una sal guardada en `privado.sal`) que solo sirve para liberarla.
- **Acciones:** `panel_redes` (nivel 2) y `panel_liberar_red` (nivel 3, con `solicitud`). `panel_resumen` trae el mismo resumen (`redes`) para admin y propietario.

## 6. Cerrar y depurar

### 6.1 Dos formas de cerrar (Panel 1)

[v5.3] Cerrar (ahora o con aviso) es nivel 2: cualquier admin puede frenar en una emergencia. Abrir es nivel 3: solo el propietario.

| Botón | Qué hace |
|---|---|
| **Cerrar ahora** | Ventana de confirmación con un botón. Cierra en el acto. |
| **Avisar y cerrar** | Eliges 1, 2, 5 o 10 minutos. Las páginas muestran la cuenta regresiva. Al llegar la hora se cierra sola. Mientras corre: **Cerrar ahora** o **Cancelar aviso**. |
| **Abrir** | Ventana de confirmación. Abre con la ronda vigente. |

Abrir y cerrar son manuales: no hay apertura programada.

### 6.2 Secuencia del cierre

| Paso | Qué pasa | Detalle técnico |
|---|---|---|
| 1 | El organizador confirma "Cerrar ahora" (o llega la hora del aviso) | `panel_config {abierto:false}` responde `advertencia`; se reenvía con `confirmar:true`. Con aviso, la primera llamada después de `cierre_en` lo aplica |
| 2 | La base espera a las inscripciones en curso | El cierre toma `SELECT … FROM config FOR UPDATE`. Cada `registrar` tiene `FOR SHARE` sobre la misma fila mientras dura su transacción (milisegundos) |
| 3 | Cierra y sube la ronda | `UPDATE config SET abierto = false, ronda = ronda + 1, cierre_en = null` |
| 4 | Lo que llegue después | `cerrado` |
| 5 | Páginas con internet | En su siguiente refresco: "Las inscripciones se cerraron antes de que confirmaras. Tu elección no se guardó." |
| 6 | El organizador hace sus cambios | Las acciones que quitan opciones ya no responden `requiere_cierre` |
| 7 | Abre | `panel_config {abierto:true}` |
| 8 | Páginas de antes del cierre | Al confirmar o al refrescar: `recargar`, vuelven a la pantalla 1 |

### 6.3 La ronda, en simple

Es el número de edición del sistema. Cada cierre lo sube en uno. La página de cada persona recuerda con qué número verificó y lo envía al confirmar. Si ya no coincide, la base responde `recargar` y la persona verifica de nuevo con las reglas vigentes. El organizador no hace nada con ella: funciona sola.

### 6.4 Qué ve la persona

| Situación | Qué pasa |
|---|---|
| Pantalla 1, con internet | En su siguiente refresco: "Inscripciones cerradas"; se actualiza sola cuando abras |
| Pantalla 2, con internet, con aviso | Cuenta regresiva: "Las inscripciones se cierran en 1:40. Confirma tu elección antes." |
| Pantalla 2, con internet, al cerrar | Vuelve al inicio: "tu elección no se guardó" |
| Confirmó en el mismo instante del cierre | Si su inscripción ya se estaba guardando, termina y queda inscrita. Si llegó después, `cerrado`. Nunca a medias |
| Sin internet durante el cierre | Su página no se entera. Si pulsa Confirmar: "Sin conexión, tu elección no se ha enviado" |
| Vuelve el internet o vuelve a la pestaña | Refresco inmediato (R-28): si sigue cerrado, pantalla de cerrado; si ya reabriste, vuelta al inicio |

### 6.5 ¿Necesito cerrar para este cambio?

Regla: si el cambio **agrega** opciones, se hace abierto. Si **quita** opciones, hay que cerrar primero, porque alguien podría estar eligiendo justo eso. Con el sistema abierto, la base responde `requiere_cierre`.

| Panel | Acción | ¿Cerrar primero? |
|---|---|---|
| 1 | Ampliar cupo | No |
| 1 | Reducir cupo | Sí |
| 1 | Mostrar actividad | No |
| 1 | Ocultar actividad | Sí |
| 1 | Habilitar etapa de inscripción o de visitas | No |
| 1 | Deshabilitar etapa de inscripción o de visitas | Sí |
| 1 | Permitir 2 talleres aunque queden visitas | No |
| 1 | Exigir visita mientras queden | Sí |
| 1 | Buscar, inscribir, cambiar inscripción, anular | No |
| 2 | Agregar al padrón | No |
| 2 | Quitar del padrón | Sí |
| 3 | Crear actividad (nace oculta) | No |
| 3 | Editar nombre, lugar, información, enlace o entrega del grupo | No |
| 3 | Editar horario de una actividad visible sin inscritos | Sí |
| 3 | Editar horario de una actividad con inscritos | Nunca |
| 3 | Permitir mismo día, bajar margen, permitir un cruce | No |
| 3 | Volver a uno por día, subir margen, bloquear un cruce | Sí |
| 3 | Quitar actividad (oculta y sin inscritos) | No |
| 3 | Verificar solicitudes de WhatsApp | No |
| Equipo | Roles y cuentas | No |

Anular libera cupos (agrega opciones), por eso se permite abierto.

### 6.6 Sin bucles ni carreras

La página solo reintenta con `ocupado` o sin red; `cerrado`, `recargar` y `demasiados_intentos` detienen los reintentos. El bloqueo compartido de `registrar` y el exclusivo del cierre ponen ambos en orden: ninguna inscripción entra después del cierre.

## 7. Horarios y cruces

### 7.1 Regla de cruce

Dos actividades `a` y `b` del mismo día se cruzan si no se cumple ninguna de estas dos condiciones:

```
a.fin + margen_min <= b.inicio
b.fin + margen_min <= a.inicio
```

Actividades de días distintos nunca se cruzan. Dos visitas tampoco se evalúan, porque R-02 ya impide combinarlas.

### 7.2 Configuración (Panel 3)

| Control | Campo | Valores | Efecto |
|---|---|---|---|
| Combinar el mismo día | `config.mismo_dia` | sí / no (no por defecto) | No: días distintos. Sí: mismo día sin cruce |
| Margen entre actividades | `config.margen_min` | 0 a 240 (30 por defecto) | Minutos mínimos de traslado |
| Cruces de horario | `cruces_permitidos` | pares (a, b) | Lista calculada; "Permitir" autoriza el par, "Bloquear" lo quita |

### 7.3 Ejemplos con los datos de prueba

| Par | Horarios | Margen 30 | Resultado |
|---|---|---|---|
| VIS05 + TAL01 (jueves) | 14:00–17:00 / 15:00–18:00 | se solapan | Se cruzan |
| VIS08 + TAL05 (viernes) | 07:00–14:00 / 15:00–18:00 | 60 min de traslado | No se cruzan |
| TAL01 + TAL02 (jueves) | 15:00–18:00 / 15:00–18:00 | mismo horario | Se cruzan |
| VIS01 (jueves) + TAL05 (viernes) | días distintos | — | No se cruzan |

### 7.4 Comportamiento

- La página marca "Se cruza con VIS05" en las opciones incompatibles con la ya elegida.
- La base vuelve a revisar al confirmar.
- `panel_crear` y `panel_editar` devuelven `cruces` con los IDs con los que se cruza la actividad.
- `panel_inscribir` y `panel_cambiar` respetan los cruces; para una excepción, el admin permite el par en el Panel 3.

---

## 8. Límite de intentos del DNI

### 8.1 Objetivo

Impedir que alguien pruebe documentos al azar para descubrir quién compró entrada, sin bloquear a quien se equivoca al escribir. Decidido [Sprint 6.2, #46]: **la barrera real es el límite por red** (300 cada 10 minutos, por `cf-connecting-ip`), alto porque en Perú muchos usuarios comparten la misma IP (el Wi-Fi de la UCSM sale con una por pabellón). El de 4 por dispositivo es un freno amable para quien se equivoca: vive en el navegador y se reinicia con una ventana de incógnito, otro navegador o un script; el ataque lo comprueba ("Cambiar de dispositivo en cada intento no sirve: la red se frena"). Hacerlo resistente exigiría identificar el navegador por sus características, lo que contradice el aviso de privacidad.

### 8.2 Algoritmo

| Paso | Detalle |
|---|---|
| Identificar el dispositivo | La página crea un identificador al azar (`crypto.randomUUID()`) la primera vez, lo guarda en `localStorage` y lo envía como `dispositivo`. Si no se puede guardar, crea uno por visita |
| Identificar la red | [Sprint 1] La base lee la IP según `config.ip_cabecera`. Mientras no se confirme, vale `auto`: `cf-connecting-ip`, si no `x-real-ip`, si no el primer valor de `x-forwarded-for`. En el Sprint 3, la acción `admin_cabeceras` muestra qué cabeceras pone el proxy de Supabase y se fija la correcta (`cf-connecting-ip`, `x-real-ip`, `xff-primero` o `xff-ultimo`). El primer valor de `x-forwarded-for` lo puede escribir el cliente; el último, sin confirmarlo, podría ser un proxy interno y juntar a todos en una sola red, que el límite por red bloquearía entera. Por eso no se elige a ciegas |
| Antes de verificar | Si el dispositivo tiene 4 fallos o la red 30 en la ventana actual: `demasiados_intentos` |
| Qué cuenta como fallo | `formato` y `no_encontrado`. No cuentan `cerrado` ni `etapa_no_habilitada` (el documento existe) |
| Al fallar | Suma 1 al dispositivo y a la red; responde `intentosRestantes` |
| Al acertar | `ok` o `duplicado`: el contador del dispositivo vuelve a 0. El de la red no cambia |
| Ventana | 10 minutos fijos (`date_trunc` a bloques de 10 min). Las filas viejas se borran solas |

### 8.3 Tabla `intentos`

| Columna | Tipo | Función |
|---|---|---|
| `clave` | text | `disp:<identificador>` o `red:<ip>` |
| `ventana` | timestamptz | Inicio del bloque de 10 minutos |
| `fallos` | int | Fallos en esa ventana |

Clave primaria: (`clave`, `ventana`). Se actualiza con `INSERT … ON CONFLICT DO UPDATE SET fallos = fallos + 1`.

### 8.4 Por qué dos contadores

| Si solo hubiera… | Problema |
|---|---|
| Contador por dispositivo | Un atacante borra el identificador y empieza de nuevo |
| Contador por red con límite 4 | Los operadores móviles en Perú ponen a muchos usuarios detrás de una misma IP. El error de una persona bloquearía a cientos. Por eso la red tiene un límite alto (30) |

### 8.5 Límites honestos

Alguien con muchas redes distintas podría seguir probando, despacio. La protección de fondo es que ninguna respuesta pública revela nombre, correo ni celular. Si una persona legítima queda frenada, soporte la inscribe desde el panel (R-20), que no tiene límite.

### 8.6 Valores ajustables

| Campo de `config` | Por defecto | Función |
|---|---|---|
| `limite_dispositivo` | 4 | Fallos por dispositivo antes de frenar |
| `limite_red` | 30 | Fallos por red antes de frenar |
| `ventana_min` | 10 | Duración de la ventana y del frenado |

---

## 9. Soporte y cambio de inscripción

### 9.1 Flujo

| Paso | Quién | Acción |
|---|---|---|
| 1 | Participante | Escribe a soporte pidiendo cambiar su visita o taller |
| 2 | Admin | Panel 1 → Buscar por documento o celular |
| 3 | Admin | "Cambiar inscripción": elige las 2 actividades nuevas |
| 4 | Base | Valida y cambia en una sola transacción |
| 5 | Admin | Si una nueva está llena: ventana de advertencia, escribe su ID como llave, se amplía en 1 |
| 6 | Participante | Su código es el mismo; vuelve a verificar su documento en la página para ver el comprobante nuevo |

No hace falta cerrar el sistema: el cambio no quita opciones a nadie más.

### 9.2 Transacción de `panel_cambiar`

1. Busca la inscripción confirmada por código.
2. Valida la combinación nueva con R-02 y R-03 (ignora etapas, abierto y ronda).
3. Bloquea con `FOR UPDATE`, en orden de ID, todas las actividades viejas y nuevas.
4. Para cada actividad nueva que la persona no tenía: si está llena y no vino `ampliarCupo`, responde `advertencia` y no escribe nada; si vino, pone `cupo = inscritos + 1`.
5. Borra de `inscripcion_actividades` las que salen y agrega las que entran.
6. Resta 1 a `inscritos` de las que salen y suma 1 a las que entran.
7. Anota `modificado_por` y `modificado_en` en la inscripción, y el cambio en la bitácora.

Como todo ocurre en la misma transacción, nadie puede tomar el cupo liberado en medio del cambio.

---

## 10. Grupos de WhatsApp

### 10.1 El problema

Un enlace de invitación se puede reenviar, y eso no se puede impedir. Lo que sí se puede es que el enlace solo no alcance para entrar.

### 10.2 Cuatro capas

| # | Capa | Cómo | Dónde |
|---|---|---|---|
| 1 | Aprobar nuevos participantes | En cada grupo: Ajustes del grupo → Aprobar nuevos participantes → Activado. Quien use el enlace solo puede pedir entrar; los administradores aprueban o rechazan en Participantes pendientes | WhatsApp |
| 2 | Lista de la actividad [v5.3] | Panel 3 → Listas: eliges la actividad y ves a todos sus inscritos con su número. Para una solicitud, buscas el número: si aparece, apruebas y marcas "en el grupo"; si no, rechazas | Panel 3 · `panel_lista`, `panel_grupo_marcar` |
| 3 | Entrega a mano | Por actividad, `grupo_modo = MANUAL`: la confirmación no muestra enlace y dice con qué número se le agregará. En Listas están los números por agregar para copiarlos o bajarlos en .vcf | Panel 3 · Listas |
| 4 | Enlace visible una sola vez y restablecible | R-16 y R-31: aparece solo en la confirmación; nunca por DNI. Si se filtra: en WhatsApp "Restablecer enlace" y pegar el nuevo en el Panel 3 (sin cerrar) | Base · Panel 3 |

### 10.3 `panel_verificar_celular`

| Entrada | Regla |
|---|---|
| `id` | Actividad del grupo |
| `celular` | Como aparece en la solicitud; se comparan los últimos 9 dígitos |

| Salida | Significado |
|---|---|
| `inscrito: true`, `nombre`, `codigo` | Aprobar |
| `inscrito: false` | Rechazar |

### 10.4 Lo que ve el participante

| `grupoModo` | `grupo` | Comprobante |
|---|---|---|
| ENLACE | enlace | Botón "Unirme al grupo" y "Un administrador aprobará tu ingreso" |
| ENLACE | `null` | "Aún no hay grupo: te escribiremos por WhatsApp" |
| MANUAL | `null` siempre | [v5.3] "La organización te agregará al grupo con tu número +51 987 654 321. Si no es correcto, escríbenos." |

### 10.5 Confirmación perdida [Sprint 5]

La página no vuelve a mostrar una confirmación (R-31). La reenvía el equipo por WhatsApp, después de comprobar que quien escribe es la persona inscrita: se busca en el panel por el **número desde el que escribe**, no por el documento que dice. Si no coincide, no se le da nada; si ya no tiene ese número, un admin lo atiende por el correo con el que se inscribió. Paso a paso, en `sprints/sprint-5/GUIA.md` (parte C, procedimientos).

Para que "Verificar una solicitud" sirva, cada grupo debe tener activado **Aprobar nuevos participantes** y quienes aprueban deben ser administradores del grupo y tener cuenta en el panel.

## 11. Datos personales y aviso de privacidad

### 11.1 Qué es privado

No es solo el celular: todo dato que identifica a una persona es un dato personal según la Ley N.º 29733 de Protección de Datos Personales. En este sistema: documento, nombres, apellidos, celular y correo. Como la base se reutilizará para registrar asistencia y, solo si WhatsApp no alcanza, avisar por correo cambios o cancelaciones de una actividad, esas finalidades deben avisarse desde la inscripción. [Sprint 5] No se envía información general por correo: la comunicación va por los grupos de WhatsApp.

### 11.2 Qué debe decir el aviso

| Punto | Contenido |
|---|---|
| Responsable | Quién recoge los datos (universidad u organización), con RUC, dirección y contacto |
| Datos | Documento y etapa (padrón); nombres, apellidos, correo electrónico y celular (formulario) |
| Finalidades | Inscripción a visitas y talleres; coordinación por WhatsApp; registro de asistencia; información del evento por correo |
| Quién accede | El equipo organizador, con cuenta individual y rol; los encargados de cada visita o taller reciben solo la lista de su actividad |
| Conservación | [v5.4] 90 días después del congreso; después se elimina el proyecto con todos sus datos, los respaldos y los CSV (sección 19.8) |
| Derechos | Acceso, rectificación, cancelación y oposición, con el canal para pedirlos |

### 11.3 Aviso de privacidad [final, Sprint 5.1]

Lo escribe en `config.js` el script `sprints/sprint-5.1/configurar.py` (huella del texto `11590a4931c3`). El Sprint 5.1 corrigió tres frases que no coincidían con el sistema: la IP se guardaba más que "unos minutos" (ahora solo se usa para el límite de 10 minutos y se borra al terminar su ventana, R-25), la fuente venía de Google Fonts (ahora está en `docs/tema/fuentes/`) y se mencionan GitHub Pages y los registros técnicos de los proveedores; y "correo institucional" pasó a "correo electrónico" (no se restringe el dominio, 24). Contenido según el deber de información del reglamento (Decreto Supremo N.º 016-2024-JUS, art. 6.1): responsable con RUC y domicilio, banco de datos, finalidades, datos obligatorios y consecuencia de no darlos, destinatarios, transferencia internacional (Supabase, fuera del Perú), ausencia de decisiones automatizadas, plazo de conservación y cómo ejercer los derechos, **incluida la portabilidad** (art. 76, como parte del derecho de acceso), más la vía ante la Autoridad Nacional.

> **Aviso de privacidad · Inscripción a visitas técnicas y talleres del VII Congreso Internacional de Estudiantes de Ingeniería Civil (CIDEIC)**
>
> **Responsable.** La Universidad Católica de Santa María (UCSM), con RUC 20141637941 y domicilio en Urb. San José s/n, Umacollo, Arequipa, es responsable del tratamiento de los datos personales que registras en este formulario. Se guardan en el banco de datos de inscripciones del congreso, a cargo de la UCSM.
>
> **Qué datos y para qué.** Registramos tu documento de identidad, nombres, apellidos, correo electrónico, país, número de celular y las actividades que eliges. Los usamos para: (1) gestionar tu inscripción a visitas técnicas y talleres; (2) coordinar contigo por WhatsApp los detalles de tus actividades; (3) registrar tu asistencia; y (4) enviarte por correo solo avisos importantes sobre tu inscripción (cambios de fecha, hora o lugar, o cancelación de una actividad), cuando no podamos comunicarlo por WhatsApp. Todos los datos del formulario son obligatorios: sin ellos no podemos inscribirte. Para proteger el formulario de abusos, cuando un intento de verificación falla guardamos la dirección IP de tu conexión y un identificador al azar que la página crea en tu navegador; los usamos solo para el límite de intentos, que dura 10 minutos, y después se borran automáticamente. No tomamos decisiones automatizadas ni elaboramos perfiles: los cupos se asignan por orden de inscripción.
>
> **Quién accede.** Solo el equipo organizador, con cuentas individuales; los encargados de cada visita o taller reciben únicamente la lista de su actividad. No vendemos tus datos ni los compartimos con terceros para otros fines. Si te unes al grupo de WhatsApp de tu actividad, sus demás integrantes verán tu número.
>
> **Dónde se guardan.** En los servidores de Supabase (Supabase, Inc.), el proveedor de la plataforma, ubicados fuera del Perú. Supabase solo los guarda por encargo nuestro; es una transferencia internacional (flujo transfronterizo) de datos. Esta página se publica en GitHub Pages (GitHub, Inc., de Estados Unidos), que no recibe los datos del formulario. Como todo servicio web, GitHub y Supabase registran la dirección IP de cada conexión en sus registros técnicos, por el tiempo que fijan sus propias políticas.
>
> **Cuánto tiempo.** Hasta 90 días después del congreso; luego los eliminamos.
>
> **Tus derechos.** Puedes ejercer tus derechos de información, acceso, rectificación, cancelación, oposición y portabilidad (recibir tus datos en un formato estructurado, de uso común y lectura mecánica) escribiendo a logisticacideic@gmail.com. Si consideras que no atendimos tu solicitud, puedes acudir a la Autoridad Nacional de Protección de Datos Personales del Ministerio de Justicia y Derechos Humanos. Este aviso se rige por la Ley N.º 29733, Ley de Protección de Datos Personales, y su reglamento, aprobado por el Decreto Supremo N.º 016-2024-JUS.

Para confirmar con quien vea lo legal en la UCSM (no cambian el sistema): si el banco de datos está inscrito en el Registro Nacional de Protección de Datos Personales (y con qué nombre), si la UCSM tiene un oficial de datos personales cuyo contacto deba figurar, y que el flujo transfronterizo se comunique a la Autoridad (art. 21.2). La finalidad 4 quedó acotada a avisos de cambios o cancelaciones cuando WhatsApp no alcanza (decisión del propietario, Sprint 5): se mantiene porque el formulario pide el correo, y un dato que se pide necesita una finalidad avisada. Plazos para responder (art. 69, días hábiles): información 8, acceso 20, rectificación, cancelación y oposición 10. Una solicitud de acceso o portabilidad se atiende con `panel_buscar` y el CSV de participantes.

El texto final es la **versión 1** del aviso en PRODUCCIÓN (nadie se inscribió allí con el borrador). Desde la apertura, cada vez que cambie el texto, sube `config.aviso_version`.

### 11.4 Cómo aparece en la página

Una sola casilla obligatoria antes de confirmar:

> ☐ Leí el **aviso de privacidad** y acepto que la organización use mis datos para esta inscripción y me contacte por WhatsApp para coordinar mis actividades.

"Aviso de privacidad" abre el texto completo. La página envía `aceptaPrivacidad: true` y `aceptaWhatsapp: true`; la base guarda ambos y `aviso_version`.

### 11.5 Qué ve cada rol

| Rol | Datos personales |
|---|---|
| Participante | Ninguno de otras personas; ni siquiera los suyos después de confirmar |
| Operador | Búsqueda por documento o celular, la lista de participantes, las listas por actividad y sus CSV |
| Admin | Lo mismo que el operador; además modifica datos |
| Encargado de actividad (sin cuenta) | Solo el CSV de su actividad, que le entrega un admin |
| Propietario | Lo anterior, más las cuentas del equipo |
| Respaldos | Solo el propietario; guardados cifrados y fuera del equipo personal |

## 12. Equipo: cuentas, claves y roles

### 12.1 Roles

| Rol | Puede |
|---|---|
| propietario | [v5.3] Nivel 3. Tú, el creador; único e inamovible desde el panel. Habilita el sistema y administra Equipo: asigna roles, activa y desactiva cuentas. Se asigna solo por SQL |
| admin | [v5.3] Nivel 2: modifica datos (cupos, catálogo, inscripciones, padrón) y puede cerrar |
| operador | [v5.3] Nivel 1: consulta (resumen, búsqueda, participantes, listas y sus CSV) y marca quién está en el grupo |
| sin rol | Nada |

### 12.2 Crear una cuenta

| Paso | Quién | Qué |
|---|---|---|
| 1 | Propietario | Supabase → Authentication → Users → Invite user, con el correo |
| 2 | Invitado | Recibe el correo, entra al enlace y crea su contraseña |
| 3 | Invitado | Primer ingreso al panel: escanea el QR con una app de códigos (Google Authenticator, Microsoft Authenticator) e ingresa un código para confirmar |
| 4 | Propietario | Pestaña Sistema → Equipo [v5.4]: la cuenta aparece sin rol; le asigna operador o admin |
| 5 | Invitado | Desde ahí, cada ingreso pide correo, contraseña y código de 6 dígitos |

Nadie conoce la contraseña de otra persona, ni el propietario.

### 12.3 La primera cuenta de propietario

1. Te invitas en Supabase y completas los pasos 2 y 3.
2. En el SQL Editor:

```sql
select privado.asignar_propietario('tu@correo.com');
```

Es la única vez que se usa SQL para cuentas. [v5.2] El propietario es único: la base no acepta un segundo (índice único) y `asignar_propietario` falla si ya hay otro. [Sprint 1] Si algún día cambia (por ejemplo, porque perdiste el acceso), el dueño del proyecto de Supabase corre en el SQL Editor `select privado.cambiar_propietario('nuevo@correo.com');`: pasa el rol en una sola operación y el anterior queda como admin.

### 12.4 Configuración de Supabase Auth

| Ajuste | Valor |
|---|---|
| Registro abierto (cualquiera puede crearse cuenta) | Desactivado |
| Proveedor | Correo y contraseña |
| MFA | TOTP activado |
| URL del sitio y de redirección | La del panel en GitHub Pages (para invitaciones y recuperación) |

### 12.5 Inicio de sesión del panel

| Paso | Llamada de Supabase |
|---|---|
| Correo y contraseña | `auth.signInWithPassword` |
| ¿Tiene factor TOTP? No: mostrar QR | `auth.mfa.enroll({factorType: 'totp'})` y luego verificar |
| Sí: pedir el código | `auth.mfa.challenge` y `auth.mfa.verify` |
| Sesión lista | El token tiene nivel `aal2`; `api()` exige `aal2` para toda acción `panel_*` |
| Olvidé mi contraseña | `auth.resetPasswordForEmail` |
| Enlace de recuperación con autenticador [Sprint 6.1] | Con un factor TOTP verificado, Supabase exige nivel `aal2` para cambiar la contraseña ("AAL2 session is required…"). El panel pide **primero** el código (`auth.mfa.challenge` y `auth.mfa.verify`) y después `auth.updateUser`; luego entra sin pedir el código otra vez. La invitación (sin factor) sigue igual: contraseña y después el QR |
| Sesión guardada de otro proyecto [Sprint 6.1] | supabase-js guarda la sesión con una clave por proyecto (`sb-<ref>-auth-token`) y el panel no la cambia: al pasar `config.js` de PRUEBA a PRODUCCIÓN, la sesión de PRUEBA no se usa y el panel pide entrar de nuevo |
| La cuenta no puede entrar (sin rol, desactivada) [Sprint 4] | El aviso de la base ("Tu cuenta aún no tiene rol…") se muestra en el paso de inicio de sesión, siempre visible, también justo después del código |
| Enlace del correo ya usado o vencido [Sprint 4] | Supabase vuelve con `#error=access_denied&error_code=otp_expired`. El panel quita ese `#error` de la dirección **antes** de iniciar supabase-js (que, si lo ve, descarta la sesión guardada) y avisa: el enlace sirve una sola vez; se entra con correo y contraseña |
| Base en PRODUCCION [Sprint 4] | El botón "Entrar con la clave de prueba" se oculta: esa clave ya no existe (R-37) |

### 12.6 Situaciones

| Situación | Qué hacer |
|---|---|
| Olvidó la contraseña | "¿Olvidaste tu contraseña?" en el panel → enlace del correo → código de 6 dígitos → contraseña nueva [Sprint 6.1]. No necesita al propietario: todo cambio de contraseña pasa por el autenticador |
| Perdió el celular | El propietario, sin SQL: Supabase → Authentication → Users → la persona → Danger zone → **Remove MFA factors**. Al entrar, registra uno nuevo. Si además olvidó la contraseña: en la misma ficha, "Send password recovery". Vale durante el congelamiento (no es SQL) |
| Celular robado o cuenta expuesta | Primero Equipo → Desactivar (corta el acceso al panel en ese momento), porque quitar el factor no cierra sus sesiones; luego Remove MFA factors; al registrar su QR nuevo, Activar |
| Deja el equipo | Equipo → Desactivar. Pierde todo acceso; su historial queda en la bitácora |
| Cuenta sin rol | No ve nada hasta que el propietario le asigne uno |

### 12.7 Acciones de Equipo (pestaña Sistema [v5.4])

| Acción | Campos | Regla |
|---|---|---|
| `panel_equipo` | — | Lista: correo, nombre, rol, TOTP registrado, activa. Solo propietario |
| `panel_equipo_rol` | `usuario`, `rol` (`null`, operador o admin) | [v5.2] No asigna "propietario" ni modifica al propietario |
| `panel_equipo_activo` | `usuario`, `activo` | [v5.2] No desactiva al propietario |

[v5.4] Cada cambio queda en la bitácora con el valor anterior y el nuevo: "carla@… · rol: sin rol → operador".

### 12.8 Opcional: invitar desde el panel

Invitar sin entrar a Supabase requiere una Edge Function con la clave de servicio, que verifique que quien la llama es propietario y luego invite el correo. Es opcional; lo recomendado es invitar desde Supabase.

## 13. Frontend del participante: contrato de datos

### 13.1 Llamada

```
POST {API_URL}/rest/v1/rpc/api
Content-Type: application/json
apikey: {ANON_KEY}
Authorization: Bearer {ANON_KEY}      ← solo si la clave empieza con "eyJ"

{"p": {"action": "verificar", "dni": "04567812", "dispositivo": "d-7f3a9c2e"}}
```

Toda respuesta es JSON con `ok`, `tipo` y `mensaje`. Si no trae `tipo` ni `ok`, es un error de red o de Supabase: se reintenta.

### 13.2 Campos que envía la página

| Campo | Tipo | Acciones | Regla | Ejemplo |
|---|---|---|---|---|
| `action` | texto | todas | `estado`, `actividades`, `verificar`, `registrar` | `"registrar"` |
| `dni` | texto | verificar, registrar | Verificar: lo escrito. Registrar: el `doc` devuelto por verificar. Nunca número | `"04567812"` |
| `dispositivo` | texto | verificar, registrar | Identificador guardado en `localStorage` | `"d-7f3a9c2e"` |
| `nombres` [v5.2] | texto | registrar | 2 a 60 caracteres | `"María"` |
| `apellidos` [v5.2] | texto | registrar | 2 a 60 caracteres | `"Quispe Rojas"` |
| `correo` [v5.3] | texto | registrar | **Obligatorio**: correo electrónico con formato válido, de cualquier dominio [Sprint 5.1] | `"maria.quispe@uni.edu.pe"` |
| `pais` | texto | registrar | PE, CL, CO, EC, BO, AR, MX, BR, VE, PY, UY, ES, US | `"PE"` |
| `celular` | texto | registrar | Solo el número, sin código de país | `"987654321"` |
| `aceptaPrivacidad` [v5.2] | booleano | registrar | `true` (sección 11) | `true` |
| `aceptaWhatsapp` | booleano | registrar | `true`; la misma casilla que la privacidad | `true` |
| `solicitud` [v5.2] | texto | registrar | Identificador al azar de cada intento de confirmar. Al reintentar por falta de respuesta, el mismo | `"s-4f9a2c71"` |
| `conActividades` [v5.2] | booleano | estado | `true` en la pantalla 2: el refresco trae las actividades | `true` |
| `actividades` | lista de texto | registrar | Exactamente 2 IDs | `["VIS01","TAL05"]` |
| `ronda` | número | registrar | La devuelta por verificar | `3` |

### 13.3 Campos que recibe la página

| Respuesta | Campos |
|---|---|
| `estado` (`tipo: "estado"`) | `abierto`, `ronda`, `cierraEn` (segundos que faltan o `null`), `etapas`, `etapasVisita`, `mismoDia`, `margenMin`, `dosTalleres`, `refresco`, `modo`, `version`, `hora` |
| `actividades` (`tipo: "actividades"`) | `actividades` (lista pública) |
| `verificar` con `ok: true` | `doc`, `etapa`, `puedeVisita`, `ronda`, `mensaje`, `actividades` |
| Cada actividad | `id`, `tipo`, `nombre`, `lugar`, `fecha` (dd/mm/aaaa), `inicio`, `fin` (hh:mm), `descripcion`, `capacidad`, `inscritos`, `disponibles`, `lleno`, `cruzaCon` (IDs con los que no se puede combinar el mismo día; vacío con "una por día") |
| `registrado` [v5.2] | `doc`, `etapa`, `celular` [v5.3] (el que escribió, para "te agregaremos con tu número"), `actividades` (cada una con `grupoModo` y `grupo`), `mensaje`, `repetida` si es la respuesta guardada de un reenvío. Sin `codigo` |
| `duplicado` [v5.2] | Solo `mensaje`: "Este documento ya está inscrito." Ningún dato |
| `error_servidor` [v5.2] | `incidencia` (número para soporte) y mensaje genérico |
| `solicitud_repetida` [v5.2] | La misma `solicitud` con otros datos: generar una nueva y reenviar |
| `formato`, `no_encontrado` | `intentosRestantes` |
| `demasiados_intentos` | `motivo` (`dispositivo` o `red`), `esperaMinutos` |
| `combinacion_invalida` | `motivo`: `cantidad`, `dos_visitas`, `mismo_dia`, `cruce`, `falta_visita` |
| `lleno` | `actividadId`, `actividades` |
| `recargar` | `ronda` |

### 13.4 Pantallas y estados

| Pantalla | Estado | Disparador | Qué se muestra |
|---|---|---|---|
| Todas | Aviso de cierre | `estado.cierraEn` no es `null` | Franja: "Las inscripciones se cierran en m:ss. Confirma tu elección antes." |
| Todas | Sin conexión | Evento `offline` o fallo de red | Franja: "Sin conexión" |
| 1 · Documento | Lista | Carga | Campo de documento y botón Verificar |
| 1 | Verificando | Clic | Botón ocupado |
| 1 | Error de formato | `formato` | Mensaje e intentos restantes |
| 1 | No encontrado | `no_encontrado` | Mensaje e intentos restantes |
| 1 | Frenado | `demasiados_intentos` | Mensaje con minutos; campo deshabilitado |
| 1 | Cerrado | `cerrado` o `estado.abierto = false` | Aviso; se actualiza sola |
| 1 | Etapa no habilitada | `etapa_no_habilitada` | Aviso informativo |
| 1 | Recargar | `recargar` o cambio de ronda | Aviso; documento ya escrito |
| 2 · Elección | Lista | `ok` | Actividades por día con disponibles |
| 2 | Opción elegida | Clic | Opción marcada |
| 2 | Opción bloqueada | Cálculo local con `lleno`, `puedeVisita` y `cruzaCon` | Motivo: "Llena", "Solo Etapa 1", "Se cruza con VIS05" |
| 2 | Cambio de visita | Elegir segunda visita | Aviso: se quitó la anterior |
| 2 | Datos | — | Nombre, correo, país, celular, consentimiento |
| 2 | Confirmando | Clic | Botón ocupado |
| 2 | En la fila | `ocupado` repetido | "Estás en la fila, no recargues" |
| 2 | Cerrado mientras elegía | `estado.abierto = false` o `cerrado` | Pantalla 1: "Tu elección no se guardó" |
| 2 | Sin conexión al confirmar | Sin red | "Tu elección no se ha enviado"; se mantiene la selección |
| 2 | Regla rota | `combinacion_invalida`, `lleno`, `visita_no_habilitada`… | Mensaje; quitar la elección en conflicto |
| 1 | Ya inscrito [v5.2] | `duplicado` | Solo el aviso "este documento ya está inscrito", sin datos |
| 3 · Confirmación [v5.2] | Confirmado | `registrado` | Una sola vez, sin código: actividades, información, botones de grupo y el aviso "entra ahora a tus grupos o toma una captura" |
| 3 | Con enlace | `grupoModo = ENLACE` y `grupo` | Botón "Unirme al grupo" y "Un administrador aprobará tu ingreso" |
| 3 | Entrega a mano | `grupoModo = MANUAL` | [v5.3] "La organización te agregará al grupo con tu número {celular}. Si no es correcto, escríbenos." |
| 3 | Sin grupo aún | `grupoModo = ENLACE` y `grupo = null` | "Te escribiremos por WhatsApp" |

### 13.5 Comportamientos obligatorios

| Comportamiento | Detalle |
|---|---|
| Decidir por `tipo` y `motivo` | Nunca leyendo el texto de `mensaje` |
| Pintar con `textContent` | Todo dato que viene de personas: nombres, lugares, descripciones |
| Refresco | Cada `refresco` segundos con la pestaña visible, al volver la conexión (`online`) y al volver a la pestaña (`visibilitychange`): `estado` y `actividades`. Si `abierto = false`: pantalla de cerrado. Si la ronda cambió: pantalla 1. Recalcular `puedeVisita = etapasVisita.includes(etapa)` |
| Reintentos [v5.2] | Con `ocupado`: cada 0,5 a 2 s al azar. Sin respuesta: espera creciente 0,5, 1, 2, 4 y 8 s, con azar. Hasta 3 minutos. Siempre con la misma `solicitud` |
| DNI como texto | En el `input` y en el JSON |
| Validar antes de enviar | Formato del documento y del celular en la página, para no gastar intentos |

### 13.6 Cuándo refrescar

```js
setInterval(refrescar, estado.refresco * 1000);               // con la pestaña visible
window.addEventListener('online', refrescar);                  // volvió internet
document.addEventListener('visibilitychange', () => { if (!document.hidden) refrescar(); });
// refrescar(): pide estado con conActividades (en la pantalla 2); si !abierto → pantalla de cerrado;
// si ronda cambió → pantalla 1 ("recargar"); recalcula puedeVisita; pinta cierraEn
```

### 13.7 Ejemplo completo

```json
// verificar
{"p": {"action": "verificar", "dni": "04567812", "dispositivo": "d-7f3a9c2e"}}
// respuesta
{"ok": true, "tipo": "ok", "doc": "04567812", "etapa": 1, "puedeVisita": true, "ronda": 3,
 "mensaje": "Documento verificado · Etapa 1.", "actividades": [{"id": "VIS01", "tipo": "VISITA", "...": "..."}]}

// registrar
{"p": {"action": "registrar", "dni": "04567812", "nombres": "María", "apellidos": "Quispe Rojas", "correo": "",
       "pais": "PE", "celular": "987654321", "aceptaPrivacidad": true, "aceptaWhatsapp": true,
       "actividades": ["VIS01", "TAL05"], "ronda": 3, "dispositivo": "d-7f3a9c2e", "solicitud": "s-4f9a2c71"}}
// respuesta
{"ok": true, "tipo": "registrado", "doc": "04567812", "etapa": 1,
 "actividades": [{"id": "VIS01", "grupo": "https://chat.whatsapp.com/…", "...": "..."}, {"id": "TAL05", "...": "..."}],
 "mensaje": "Inscripción confirmada."}

// ya inscrito (verificar o registrar)
{"ok": false, "tipo": "duplicado", "mensaje": "Este documento ya está inscrito. Si necesitas ayuda, escríbenos."}
```

---

## 14. Paneles de organización: definición para el frontend

Recomendación: una sola página con cuatro pestañas (Operación, Participantes, Actividades, Equipo) y un solo inicio de sesión. [v5.2] Equipo solo existe para el propietario. Las escrituras llevan `solicitud` y solo se reintentan con la misma.

### 14.1 Elementos comunes

| Elemento | Función | Datos |
|---|---|---|
| Inicio de sesión | Correo, contraseña y código TOTP de 6 dígitos; QR la primera vez; "¿Olvidaste tu contraseña?" | Supabase Auth (sección 12.5) |
| Entrar con la clave de prueba | Solo en modo PRUEBA: la clave del tester y el rol con el que se quiere ver el panel. Sirve para probar sin cuentas | `key`, `comoRol` |
| Llamadas | Mismo `POST /rest/v1/rpc/api`, con `Authorization: Bearer {token de sesión}` en lugar de la clave anon | — |
| Cabecera | Nombre, rol, Salir, versión | `panel_resumen.sesion` |
| Franja de estado | Siempre visible. Abierto: "ABIERTO · ronda N" (verde), con la cuenta regresiva si hay aviso. Cerrado: "CERRADO · ronda N · puedes quitar opciones" (ámbar) | `config.abierto`, `config.ronda`, `config.cierraEn` |
| Ventana de advertencia | Se abre con `advertencia`. Título, mensaje, Cancelar, acción. Si la acción amplía cupos, pide escribir el ID de la actividad | `mensaje`, `accion`, `ids` |
| Avisos | `requiere_cierre`, `sin_permiso` y demás rechazos, sin reintentar. Éxitos breves | `tipo`, `mensaje` |
| Refresco | `panel_resumen` cada 20 s con la pestaña visible | — |

Llaves de la ventana de advertencia:

| Acción | Llave |
|---|---|
| Cerrar ahora, abrir | Sin llave: botón de confirmación |
| Inscribir o cambiar con ampliación | El ID de cada actividad llena, separados por espacio |
| Bajar cupo bajo inscritos, agregar a otra etapa, anular | Sin llave: botón de confirmación |

### 14.2 Panel 1 · Operación

| Bloque | Muestra | Acción | API | Rol | Sistema |
|---|---|---|---|---|---|
| Estado | Abiertas, cerradas o cuenta regresiva; ronda | Cerrar ahora | `panel_config {abierto:false, confirmar}` | admin (2) | — |
| Estado | | Avisar y cerrar en 1, 2, 5 o 10 min | `panel_config {avisarCierreMin}` | admin (2) | abierto |
| Estado | | Cancelar aviso | `panel_config {cancelarAviso:true}` | admin (2) | — |
| Estado | | Abrir | `panel_config {abierto:true}` | propietario (3) | — |
| Etapas de inscripción | Botones 1, 2, 3 | Habilitar / deshabilitar | `panel_config {etapas}` | propietario (3) | agregar: abierto · quitar: cerrado |
| Etapas de visitas | Botones 1, 2, 3 y aviso de etapas sin inscripción | Habilitar / deshabilitar | `panel_config {etapasVisita}` | propietario (3) | agregar: abierto · quitar: cerrado |
| Regla R-08 | Interruptor | Encender / apagar | `panel_config {dosTalleres}` | propietario (3) | encender: abierto · apagar: cerrado |
| Paso de cupo | Número | Guardar | `panel_config {pasoCupo}` | admin (2) | abierto |
| Totales | Inscritos, por etapa, visitas ocupadas/cupo, DNI fallidos, frenados, llamadas en la última ventana de 10 s y pico [v5.3] | — | `panel_resumen.totales`, `trafico` | operador | — |
| Integridad [v5.2] | OK, o qué actividades tienen el contador distinto de sus inscripciones | Recontar inscritos [v5.4] (nivel 2, `panel_sincronizar`); si vuelve a descuadrar, avisar a soporte técnico | `panel_resumen.integridad` | operador | — |
| Alerta de saturación [v5.3] | Franja roja cuando 3 ventanas seguidas pasan el umbral | Procedimiento de emergencia (sección 18.2) | `panel_resumen.trafico` | operador | — |
| Incidencias [v5.2] | Número, hora, acción y detalle técnico | — | `panel_incidencias` | admin | — |
| Actividades | ID, nombre, barra, inscritos/cupo, "ampliada desde N", llena, oculta | +paso [v5.2] | `panel_actividad {cupo: cupo + paso, solicitud}` | admin (2) | abierto |
| Actividades | | −paso, Cupo… | `panel_actividad {cupo, confirmar, solicitud}` | admin (2) | cerrado |
| Actividades | | Mostrar / Ocultar | `panel_actividad {publicada}` | operador | mostrar: abierto · ocultar: cerrado |
| Buscar | Código, nombre, celular, actividades, estado, origen | Buscar | `panel_buscar {q}` | operador | — |
| Buscar | | Cambiar inscripción | `panel_cambiar {codigo, actividades, ampliarCupo}` | admin | — |
| Buscar | | Anular | `panel_anular {codigo}` | admin | — |
| Inscribir | Documento, nombres, apellidos, correo electrónico [v5.4], actividad 1 y 2, celular, consentimiento (privacidad y WhatsApp) | Inscribir | `panel_inscribir {…, solicitud}` | admin | — |
| Celulares repetidos | Celular y personas | Ir a buscar | `panel_resumen.repetidos` | operador | — |

### 14.3 Panel 2 · Participantes

| Bloque | Muestra | Acción | API | Rol | Sistema |
|---|---|---|---|---|---|
| Resumen | En padrón, inscritos, sin inscribir, agregados en el panel | — | `panel_participantes` | operador | — |
| Filtros | Etapa, estado, búsqueda | Filtrar, paginar de 50 en 50 | `panel_participantes {etapa, estado, q, pagina}` | operador | — |
| Lista | Documento, nombre, etapa, estado, código, actividades, origen | Inscribir (lleva al Panel 1 con el documento) | — | admin | — |
| Lista | | Quitar | `panel_padron_quitar {documento}` | admin | cerrado |
| Alta [v5.3] | Documento y etapa | Agregar; si ya existe, `ya_existe` (etapa fija) | `panel_padron_agregar {documento, etapa}` | admin (2) | abierto |
| Descarga | — | CSV del padrón con estado o de inscripciones | `panel_registros {formato}` | admin | — |

### 14.4 Panel 3 · Actividades y horarios

| Bloque | Muestra | Acción | API | Rol | Sistema |
|---|---|---|---|---|---|
| Horarios | Interruptor "combinar el mismo día" | Encender / apagar | `panel_horarios {mismoDia}` | propietario (3) | encender: abierto · apagar: cerrado |
| Horarios | Margen en minutos | Guardar | `panel_horarios {margenMin}` | propietario (3) | bajar: abierto · subir: cerrado |
| Cruces | Pares con día y horas; permitido o bloqueado | Permitir / Bloquear | `panel_cruce {a, b, permitido}` | admin | permitir: abierto · bloquear: cerrado |
| Solicitudes de WhatsApp | Actividad, celular de la solicitud, resultado | Verificar | `panel_verificar_celular {id, celular}` | operador | — |
| Catálogo | ID, nombre, lugar, día y hora, inscritos/cupo, cupo inicial, enlace, visible | Editar | `panel_editar {…}` | admin | según R-18 |
| Catálogo | | Quitar | `panel_quitar {id}` | admin | oculta y sin inscritos |
| Catálogo | | Ver la lista de la actividad | Abre Listas filtrado | operador (1) | — |
| Formulario | Tipo, nombre, lugar, fecha, inicio, fin, cupo inicial (al crear), información, entrega del grupo (ENLACE o MANUAL), enlace | Guardar | `panel_crear` / `panel_editar` | admin | — |

### 14.5 Panel 3 · Listas por actividad [v5.3]

| Bloque | Muestra | Acción | API | Nivel |
|---|---|---|---|---|
| Lista | Por actividad o de todas, y por etapa: #, actividad, apellidos, nombres, DNI, correo, celular, etapa, estado de grupo; ordenada por apellidos | Filtrar · buscar por número, DNI o nombre | `panel_lista {id, etapa, q}` | 1 |
| Grupo de WhatsApp | Inscritos, en el grupo, por agregar | Marcar agregado (uno o todos) · copiar números por agregar · .vcf | `panel_grupo_marcar {id, codigos, agregado, solicitud}` | 1 |
| Exportar | — | CSV de la lista (con su filtro de actividad y etapa) · CSV de todas | `panel_exportar {id, etapa}` | 1 |

Respuesta de `panel_lista`:

```json
{"ok": true, "tipo": "panel", "total": 18, "pendientes": 17,
 "filas": [{"actividad": "VIS01", "apellidos": "Navarro Mamani", "nombres": "Miguel", "doc": "78695681",
            "correo": "miguel.navarro@uni.edu.pe", "celular": "+51987112233", "etapa": 1, "codigo": "CIIC-7K4Q2",
            "origen": "WEB", "enGrupo": true}]}
```

### 14.6 Formatos de importación [v5.5]

**Padrón** (`panel_padron_importar`): dos columnas, documento y etapa; separador coma, punto y coma o tabulación; con o sin encabezado (se reconoce por palabras como "documento", "dni" o "etapa"); UTF-8 con o sin BOM; hasta 10 000 filas por llamada (el panel lo envía en lotes de 2000; R-42). La etapa admite `1`, `Etapa 1` o `E1`.

**Actividades** (`panel_actividades_importar`): encabezado obligatorio; columnas en cualquier orden, reconocidas por su nombre:

| Columna | Obligatoria | Formato |
|---|---|---|
| `id` | No | Letras, números, guion o guion bajo, hasta 20; vacía = se asigna |
| `tipo` | Sí | `VISITA` o `TALLER` |
| `nombre` | Sí | 3 a 120 caracteres |
| `lugar` | No | Hasta 120 caracteres |
| `fecha` | Sí | `dd/mm/aaaa` |
| `inicio`, `fin` | Sí | `hh:mm`, fin posterior al inicio |
| `cupo` | Sí | 1 a 1000 |
| `descripcion` | No | Hasta 400 caracteres |
| `entrega` | No | `ENLACE` (por defecto) o `MANUAL` |
| `enlace` | No | Empieza con `https://chat.whatsapp.com/` |
| `visible` | No | `SI` o `NO` (por defecto `NO`) |

### 14.7 Sistema (solo propietario) [v5.4]

La pestaña Equipo pasa a llamarse **Sistema** y reúne todo lo del nivel 3 que no es operación diaria. No existe para nadie más.

| Bloque | Muestra | Acción | API | Rol |
|---|---|---|---|---|
| Cuentas | Correo, nombre, rol (sin rol, operador o admin; el propietario se muestra fijo), TOTP, activa | Guardar rol · Desactivar · Activar, nunca sobre el propietario | `panel_equipo`, `panel_equipo_rol`, `panel_equipo_activo` | propietario |
| Ayuda | Cómo invitar en Supabase; qué hacer si alguien pierde contraseña o celular | — | — | propietario |
| Respaldo | Último respaldo descargado: fecha, quién, tamaño | Descargar respaldo | `panel_respaldo` | propietario |
| Importar padrón | Selector de archivo CSV (documento, etapa) y vista previa de las primeras filas | Importar · informe de agregados, existentes, conflictos e inválidos | `panel_padron_importar` | propietario |
| Vaciar datos de prueba [v5.5] | Paso 2 de "De la base de prueba a la real" | Vaciar (llave VACIAR; solo PRUEBA y cerrado) | `panel_vaciar_prueba` | propietario |
| Importar actividades [v5.5] | Selector de archivo CSV y vista previa | Importar · informe de agregadas, existentes e inválidas | `panel_actividades_importar` | propietario |
| Pasar a producción | Estado: modo, abierto o cerrado, inscripciones de prueba | Pasar a producción (con la llave PRODUCCION; solo cerrado) | `panel_preparar_produccion` | propietario |

[v5.5] La pestaña muestra estos bloques como pasos numerados: 1 Respaldo · 2 Vaciar datos de prueba · 3 Importar padrón · 4 Importar actividades · 5 Pasar a producción (sección 19.7).

### 14.8 Respuesta de `panel_resumen`

```json
{
  "ok": true, "tipo": "panel", "version": "5.1", "hora": "2026-11-12 08:14:07",
  "sesion": {"nombre": "Ana Rojas", "rol": "admin"},
  "config": {"abierto": true, "ronda": 3, "cierraEn": null, "umbralVentana": 2000, "avisoVersion": 1, "etapas": [1, 2], "etapasVisita": [1], "dosTalleres": true,
             "mismoDia": false, "margenMin": 30, "pasoCupo": 5, "refresco": 20, "modo": "PRODUCCION"},
  "totales": {"inscritos": 412, "anulados": 6, "porEtapa": {"1": 160, "2": 190, "3": 62},
              "padron": {"1": 180, "2": 180, "3": 140}, "visitas": {"ocupados": 198, "cupo": 215},
              "fallos10min": 3, "frenados": 0},
  "actividades": [{"id": "VIS01", "tipo": "VISITA", "nombre": "…", "lugar": "…", "fecha": "12/11/2026",
                   "inicio": "08:00", "fin": "12:00", "descripcion": "…", "capacidad": 20, "cupoInicial": 20,
                   "inscritos": 18, "disponibles": 2, "lleno": false, "publicada": true,
                   "grupoModo": "ENLACE", "grupo": "https://chat.whatsapp.com/…", "cruces": []}],
  "cruces": [{"a": "TAL01", "b": "VIS05", "fecha": "12/11/2026", "permitido": false}],
  "integridad": {"ok": true, "descuadres": []},
  "trafico": {"ventana10s": 240, "pico10s": 1830, "alerta": false},
  "repetidos": [{"celular": "+51987654321", "personas": [{"codigo": "…", "doc": "…", "nombre": "…"}]}],
  "ultimos": [{"fecha": "…", "codigo": "…", "doc": "…", "nombre": "…", "etapa": 1, "actividades": ["VIS01", "TAL05"], "origen": "WEB"}]
}
```

### 14.9 Lineamientos de diseño profesional

| Lineamiento | Por qué |
|---|---|
| Franja de estado siempre visible | El organizador debe saber en todo momento si está abierto o cerrado |
| Estado con palabra y color, nunca solo color | Accesibilidad y lectura rápida |
| Confirmación antes de lo que no se deshace | Cerrar, anular, ampliar, quitar |
| Acciones que exigen cierre atenuadas con "requiere cerrar" mientras está abierto | Anticipa el rechazo; la base igual decide |
| Tablas con desplazamiento propio | En celular, la página nunca se desplaza de lado |
| Teclado y lector de pantalla | Botones reales, etiquetas en campos, foco visible |
| Mismo vocabulario que la base | "Cerrar y depurar", "Cambiar inscripción", "Mostrar", "Ocultar" |

---

## 15. Modelo de datos

Una sola base, abierta a crecer: lo que llene el formulario, lo que entregue la universidad y lo que necesiten después la asistencia o los correos. El padrón y las inscripciones se cruzan por documento.

### 15.1 `config` (una fila)

| Columna | Tipo | Por defecto | Función |
|---|---|---|---|
| `id` | int | 1 | Fuerza una sola fila (`CHECK id = 1`) |
| `abierto` | boolean | false | Inscripciones abiertas |
| `ronda` | int | 1 | Sube en cada cierre (R-09) |
| `umbral_ventana` [v5.3] | int | 2000 | Llamadas por ventana de 10 s que, sostenidas 3 ventanas, encienden la alerta (R-34) |
| `aviso_version` [v5.2] | int | 1 | Versión vigente del aviso de privacidad |
| `limite_masivo` [v5.4] | int | 10 | Filas por sentencia sobre las que R-40 bloquea |
| `ip_cabecera` [Sprint 1] | text | `auto` | De qué cabecera sale la IP del límite por red (§8); se fija en el Sprint 3 |
| `cierre_en` | timestamptz | null | Hora del cierre avisado (R-27) |
| `etapas` | smallint[] | {} | Etapas que pueden inscribirse (R-06) |
| `etapas_visita` | smallint[] | {1} | Etapas que pueden elegir visitas (R-07) |
| `dos_talleres` | boolean | true | Permitir 2 talleres aunque queden visitas (R-08) |
| `mismo_dia` | boolean | false | Combinar el mismo día (R-03) |
| `margen_min` | int | 30 | Minutos de traslado (0 a 240) |
| `paso_cupo` | int | 5 | Paso de los botones de cupo (1 a 100) |
| `refresco` | int | 20 | Segundos entre refrescos de la página (10 a 120) |
| `total_por_persona` | int | 2 | Actividades por inscripción (R-02) |
| `limite_dispositivo` | int | 4 | R-25 |
| `limite_red` | int | 300 [Sprint 5.1] | R-25 |
| `ventana_min` | int | 10 | R-25 |
| `modo` | text | PRUEBA | PRUEBA o PRODUCCION (el tester solo actúa en PRUEBA) |

### 15.2 `padron`

| Columna | Tipo | Función |
|---|---|---|
| `documento` | text | [v5.3] **Clave primaria**: una sola etapa, que no se actualiza (D2). Normalizado (R-12) |
| `etapa` | smallint | 1, 2 o 3 |
| `datos` | jsonb | [v5.3] Opcional: lo que entregue la universidad; no se usa para validar |
| `fecha_compra` | text | Referencial |
| `origen` | text | CARGA (desde la hoja) o PANEL (último momento) |
| `creado_por` | uuid | Cuenta que lo agregó (si fue desde el panel) |
| `creado_en` | timestamptz | Cuándo |

Clave primaria [v5.2]: `documento`.

### 15.3 `tipos_actividad`

| Columna | Tipo | Función |
|---|---|---|
| `codigo` | text | VISITA, TALLER; mañana otros |
| `nombre` | text | Nombre para mostrar |
| `max_por_persona` | int | VISITA 1, TALLER 2 |
| `requiere_etapa_visita` | boolean | true para VISITA: aplica R-07 |

### 15.4 `actividades`

| Columna | Tipo | Función |
|---|---|---|
| `id` | text | VIS01, TAL05… (el panel arma los nuevos) |
| `tipo` | text | Referencia a `tipos_actividad` |
| `nombre`, `lugar` | text | Datos visibles |
| `fecha` | date | Día |
| `inicio`, `fin` | time | Horario |
| `cupo` | int | Cupo actual |
| `cupo_inicial` | int | Cupo con que se creó; para "ampliada desde N" |
| `inscritos` | int | Contador; solo lo mueven las funciones. `CHECK (inscritos between 0 and cupo)` |
| `publicada` | boolean | Visible en la página |
| `descripcion` | text | Información para el participante (hasta 400 caracteres) |
| `grupo_modo` | text | ENLACE o MANUAL (R-29) |
| `grupo_whatsapp` | text | Enlace del grupo; vacío = pendiente |
| `orden` | bigint | Orden de presentación |
| `creado_por`, `creado_en` | uuid, timestamptz | Auditoría |

### 15.5 `cruces_permitidos`

| Columna | Tipo | Función |
|---|---|---|
| `a`, `b` | text | IDs de las actividades, con `a < b` |
| `permitido_por` | uuid | Cuenta que lo autorizó |
| `creado_en` | timestamptz | Cuándo |

### 15.6 `inscripciones`

| Columna | Tipo | Función |
|---|---|---|
| `codigo` | text | Clave primaria; CIIC-XXXXX |
| `documento` | text | Normalizado |
| `nombres`, `apellidos` [v5.2] | text | Lo que escribió la persona |
| `correo` | text | [v5.3] Obligatorio: correo electrónico (cualquier dominio) |
| `etapa` | smallint | Etapa con la que entró |
| `celular`, `pais` | text | `+51987654321`, PE |
| `acepta_whatsapp`, `acepta_privacidad` [v5.2] | boolean | `CHECK` ambos verdaderos |
| `aviso_version` [v5.2] | int | Versión del aviso que aceptó |
| `estado` | text | CONFIRMADO o ANULADO |
| `origen` | text | WEB o PANEL |
| `ronda` | int | Ronda en la que se confirmó |
| `registrado_por` | uuid | Cuenta, si vino del panel |
| `modificado_por`, `modificado_en` | uuid, timestamptz | Último cambio de inscripción |
| `creado_en` | timestamptz | Cuándo |

Índice único parcial: `documento` donde `estado = 'CONFIRMADO'` (R-01). Índice por `celular`.

### 15.7 `inscripcion_actividades`

| Columna | Tipo | Función |
|---|---|---|
| `codigo` | text | Referencia a `inscripciones` |
| `actividad_id` | text | Referencia a `actividades` |
| `en_grupo` [v5.3] | boolean | Si ya está en el grupo de WhatsApp de esa actividad |
| `en_grupo_por`, `en_grupo_en` [v5.3] | uuid, timestamptz | Quién lo marcó y cuándo |

Clave primaria: (`codigo`, `actividad_id`). [v5.2] Su trigger mueve `actividades.inscritos` (R-33). Reemplaza a las columnas fijas `actividad1` y `actividad2` de la v5.0. Permite marcar asistencia por actividad y, en el futuro, inscripciones con más de 2 actividades.

### 15.8 `asistencias` (reservada para el Panel 4)

| Columna | Tipo | Función |
|---|---|---|
| `codigo`, `actividad_id` | text | Referencia a `inscripcion_actividades` |
| `marcado_en` | timestamptz | Hora de llegada |
| `marcado_por` | uuid | Cuenta del equipo que marcó |
| `metodo` | text | DNI, QR o MANUAL |
| `observacion` | text | Nota opcional |

Se crea vacía en la v5.1 para que el modelo no cambie cuando llegue el Panel 4.

### 15.9 `organizadores`

| Columna | Tipo | Función |
|---|---|---|
| `user_id` | uuid | Cuenta de Supabase Auth |
| `nombre` | text | Para la bitácora y la cabecera |
| `rol` | text | propietario, admin, operador o vacío (sin rol). [v5.2] Índice único parcial: un solo propietario |
| `activo` | boolean | Desactivar sin borrar |

### 15.10 `intentos`

Ver sección 8.3.

### 15.11 `bitacora`

| Columna | Tipo | Función |
|---|---|---|
| `id` | bigint | Autonumérico |
| `creado_en` | timestamptz | Cuándo |
| `user_id` | uuid | Cuenta |
| `nombre` | text | Nombre de la cuenta en ese momento |
| `antes`, `despues` [v5.4] | jsonb | Valor anterior y nuevo en cambios de rol, de cuenta y de configuración |
| `accion` | text | Configuración, Cierre y depuración, Aviso de cierre, Cierre programado, Apertura, Equipo, Actividad X, Anulación, Inscripción desde el panel, Cambio de inscripción, Padrón, Horarios, Cruce |
| `detalle` | text | Qué cambió, de qué valor a qué valor |

### 15.12 `privado.solicitudes` [v5.2]

| Columna | Tipo | Función |
|---|---|---|
| `actor` [v5.4] | text | Quien llama: `uid:<cuenta>` en el panel, `doc:<documento>` en la página |
| `accion` | text | Acción |
| `id` | text | La `solicitud` (UUID) que mandó la página o el panel |
| `huella` | text | SHA-256 del pedido sin `solicitud` ni `dispositivo` |
| `respuesta` | jsonb | Respuesta que se devolvió |
| `creado_en` | timestamptz | Se borran después de 24 h |

Clave primaria [v5.4]: (`actor`, `accion`, `id`).

### 15.13 `privado.incidencias` [v5.2]

| Columna | Tipo | Función |
|---|---|---|
| `id` | bigint | Número que ve la persona (`INC-0001`) |
| `creado_en` | timestamptz | Cuándo |
| `accion` | text | Acción que falló |
| `sqlstate`, `mensaje` | text | Código y texto del error; sin datos personales |

### 15.14 Tráfico [v5.2]

[v5.3] Secuencia `privado.llamadas` (suma 1 por llamada, sin escribir filas) y tabla `privado.trafico (ventana, total)`, con una foto del contador cada 10 segundos, tomada por la primera llamada de cada ventana. Las llamadas de una ventana son la diferencia entre dos fotos. Al tomar cada foto se evalúa la alerta (R-34). [v5.4] Se borran las fotos de más de 2 días.

[Sprint 4, migración 08] Columnas: `ventana` (epoch / 10), `total` (valor de la secuencia en la primera llamada), `llamadas` (se llena al abrir la ventana siguiente) y `alerta`. Solo la llamada que toma la foto escribe, y nunca espera a otra: una sola llave para toda la base (`pg_try_advisory_xact_lock(2026, 0)`); si otra llamada está tomando una foto, sigue de largo y la toma una llamada siguiente. Un fallo al contar nunca impide atender la llamada. Las peticiones que no llegan a `api()` (JSON inválido, rechazadas por PostgREST) no se cuentan. La alerta se enciende con 3 ventanas completas seguidas sobre el umbral y se apaga con 3 seguidas por debajo; al encenderse deja una entrada "Alerta de saturación" en la bitácora. `panel_resumen.trafico` = `{ventana10s, pico10s, alerta, umbral}`. "Vaciar datos de prueba" y "Pasar a producción" vacían el tráfico.

### 15.15 Triggers [v5.2]

| Trigger | Sobre | Hace |
|---|---|---|
| Contadores | `inscripcion_actividades` (insertar, borrar) e `inscripciones` (cambio de estado, borrado) | Suma o resta en `actividades.inscritos` |
| Producción | `config` (modo pasa a PRODUCCION) | Borra la `ADMIN_KEY` |
| Protección masiva [v5.4] | `padron`, `actividades`, `cruces_permitidos`, `inscripciones`, `inscripcion_actividades`, `organizadores` (por sentencia, con tablas de transición) | Bloquea `DELETE` y `UPDATE` de más de `limite_masivo` filas y todo `TRUNCATE`, salvo `ciic.masivo = confirmado` (R-40) |

### 15.16 Seguridad del esquema

Todas las tablas con RLS encendido y sin políticas. Sin permisos para `anon` ni `authenticated`. Las funciones internas en el esquema `privado`, que la API no publica. Solo `public.api(jsonb)` tiene `grant execute` a `anon` y `authenticated`.

---

## 16. API: acciones

Formato del pedido: `{"p": {"action": "...", ...}}`. [v5.2] Toda escritura revisa primero `solicitud` (R-32). Para las acciones `panel_*`, la base exige una sesión de nivel `aal2`, identifica la cuenta con `auth.uid()` y busca su rol y si está activa en `organizadores`. Antes de cualquier acción, `api()` aplica el cierre avisado si ya llegó su hora (R-27).

| Acción | Rol | Campos | Valida | Respuestas |
|---|---|---|---|---|
| `estado` | público | `conActividades` [v5.2] | — | `estado` (con `actividades` si se pidió) |
| `actividades` | público | — | — | lista pública |
| `verificar` | público | `dni`, `dispositivo` | R-12, R-25, R-01, R-09, R-06, R-07 | `ok`, `duplicado`, `formato`, `no_encontrado`, `cerrado`, `etapa_no_habilitada`, `demasiados_intentos` |
| `registrar` | público | ver 13.2 (nombres, apellidos, aceptaPrivacidad y solicitud [v5.2]) | R-02 a R-09, R-12 a R-14, R-25 | `registrado`, `duplicado`, `recargar`, `cerrado`, `lleno`, `combinacion_invalida`, `visita_no_habilitada`, `no_disponible`, `datos_invalidos`, `celular_invalido`, `sin_consentimiento`, `ocupado` |
| `panel_resumen` | operador | — | sesión | `panel` (9.5) |
| `panel_config` | por campo [v5.3]: cerrar, avisar, cancelar y `pasoCupo` admin; abrir, etapas, `dosTalleres`, `refresco`, límites y `umbral` propietario || `abierto`, `confirmar`, `avisarCierreMin`, `cancelarAviso`, `limiteDispositivo`, `limiteRed`, `etapas`, `etapasVisita`, `dosTalleres`, `pasoCupo`, `refresco` | R-09, R-10, R-19 | `panel`, `advertencia`, `requiere_cierre`, `valor_invalido` |
| `panel_actividad` | operador | `id`, `cupo` (final; `delta` eliminado [v5.2]), `publicada`, `confirmar`, `solicitud` | R-10, R-11 | `panel`, `advertencia`, `requiere_cierre`, `cupo_invalido` |
| `panel_buscar` | operador | `q` | — | `panel` con `registros` |
| `panel_anular` | admin | `codigo` | — | `panel`, `no_encontrado` |
| `panel_inscribir` | admin | `dni`, `nombres`, `apellidos`, `correo` [v5.4], `celular`, `pais`, `aceptaPrivacidad`, `aceptaWhatsapp`, `actividades`, `ampliarCupo`, `solicitud` | R-20 | `registrado`, `advertencia`, `duplicado`, `no_encontrado`, `combinacion_invalida` |
| `panel_cambiar` | admin | `codigo`, `actividades`, `ampliarCupo` | R-21 | `panel`, `advertencia`, `sin_cambios`, `combinacion_invalida` |
| `panel_participantes` | operador | `etapa`, `estado`, `q`, `pagina` | — | `panel` con `filas` y `total` |
| `panel_padron_agregar` | admin | `documento`, `etapa`, `datos` (opcional) [v5.3] | R-12, R-22 | `panel`, `ya_existe` (con `etapa`), `formato` |
| `panel_padron_quitar` | admin | `documento` | R-10, R-23 | `panel`, `requiere_cierre`, `tiene_inscripcion` |
| `panel_crear` | admin | `tipo`, `nombre`, `lugar`, `fecha`, `inicio`, `fin`, `cupo`, `descripcion`, `grupo` | R-24 | `panel` con `actividad` y `cruces` |
| `panel_editar` | admin | `id` y los mismos campos sin `cupo` | R-18 | `panel`, `tiene_inscritos`, `requiere_cierre`, `enlace_invalido` |
| `panel_quitar` | admin | `id` | R-17 | `panel`, `esta_visible`, `tiene_inscritos` |
| `panel_horarios` | propietario [v5.3] | `mismoDia`, `margenMin` | R-03, R-10 | `panel` con `cruces`, `requiere_cierre` |
| `panel_cruce` | admin | `a`, `b`, `permitido` | R-03, R-10 | `panel`, `requiere_cierre` |
| `panel_verificar_celular` | operador | `id`, `celular` | R-29 | `panel` con `inscrito`, `nombre`, `codigo` |
| `panel_equipo` | propietario | — | R-30 | `panel` con `cuentas` |
| `panel_equipo_rol` | propietario | `usuario`, `rol` (operador o admin), `nombre` | R-30 | `panel`, `no_permitido` |
| `panel_lista` [v5.3] | operador | `id` (vacío: todas), `etapa` (vacío: todas), `q` | R-38 | `panel` con `total`, `pendientes`, `filas` |
| `panel_grupo_marcar` [v5.3] | operador | `id`, `codigos`, `agregado`, `solicitud` | R-38 | `panel` con `marcados` |
| `panel_exportar` [v5.3] | operador | `id` (vacío: todas), `etapa` (vacío: todas) | R-39 | `panel` con `encabezados` y `filas` |
| `panel_incidencias` [v5.2] | admin | — | R-36 | `panel` con `incidencias` |
| `panel_equipo_activo` | propietario | `usuario`, `activo` | R-30 | `panel`, `no_permitido` |
| `panel_registros` | admin | `formato`: `inscripciones`, `padron` o `actividad` (con `id`: nombre, celular y código) | — | `panel` con `encabezados` y `filas` |
| `panel_sincronizar` | admin | `solicitud` | R-33 | Recuenta inscritos; botón "Recontar" del Panel 1 [v5.4] |
| `panel_respaldo` [v5.4] | propietario | — | R-41 | `panel` con `formato` (`ciic-respaldo-1`), `version`, `generadoEn`, `generadoPor`, `filas` y `huellas` por tabla, `huella` total y `tablas` |
| `panel_padron_importar` [v5.4] | propietario | `filas` (documento y etapa, hasta 10 000), `lote` (opcional, "2/5"), `solicitud` | R-42 | `panel` con `agregados`, `existentes`, `conflictos` y `invalidos` (hasta 200 cada uno), `totalConflictos`, `totalInvalidos` y `duracionMs` (tiempo en la base) |
| `panel_vaciar_prueba` [v5.5] | propietario | `llave` ("VACIAR"), `solicitud` | R-44 | `panel` con `eliminados` (padrón, actividades, inscripciones); `modo_produccion`, `requiere_cierre`, `valor_invalido` |
| `panel_actividades_importar` [v5.5] | propietario | `filas` (hasta 500), `solicitud` | R-45 | `panel` con `agregadas`, `existentes`, `invalidas` |
| `panel_preparar_produccion` [v5.4] | propietario | `llave` ("PRODUCCION"), `solicitud` | R-43 | `panel`, `requiere_cierre`, `modo_produccion`, `valor_invalido` |
| `panel_redes` [Sprint 5.1] | admin | — | R-46 | `panel` con `limite`, `ventanaMin`, `desde`, `reiniciaEnSeg`, `cerca`, `frenadas` y `redes` (`id`, `red` enmascarada, `fallos`, `pct`, `estado`) |
| `panel_liberar_red` [Sprint 5.1] | propietario | `id` (de `panel_redes`), `solicitud` | R-46 | `panel` con `liberada` y `fallos`, más el resumen de redes; `no_encontrado` si ya no tiene fallos en la ventana |
| `admin_ping`, `admin_muestra`, `admin_limpiar` | tester | `key`; limpiar acepta `docs`, `padron` e `intentos` | modo PRUEBA | Diagnóstico · documentos sin inscribir · borra solo lo del tester |
| `admin_cabeceras` [v5.2] | tester | `key` | modo PRUEBA | Las cabeceras que llegan (`cabeceras`, `cf-connecting-ip`, `x-real-ip`, `x-forwarded-for`), `ipCabecera` y la `red` resuelta |
| `admin_error` [Sprint 1] | tester | `key` | modo PRUEBA | Provoca un error interno a propósito para probar las incidencias (R-36) |
| `admin_sembrar` [v5.2] | tester | `key`, `n` | modo PRUEBA | Crea un padrón sintético para la prueba de 1000 personas; `admin_limpiar` lo borra |
| Cualquier `panel_*` con `key` | tester | `key`, `comoRol` (propietario, admin, operador); `avisarCierreSeg` solo para el tester | modo PRUEBA | Permite probar el panel y los roles sin cuentas |

---

## 17. Tipos de respuesta

| Tipo | Cuándo | Campos extra | Qué hace la pantalla |
|---|---|---|---|
| `ok` | Documento verificado | ver 8.3 | Pantalla 2 |
| `registrado` | Inscripción guardada | ver 8.3 | Pantalla 3 |
| `panel` | Acción del panel correcta | según la acción | Actualiza |
| `duplicado` | Ya tiene inscripción | Ninguno [v5.2] | Pantalla 1: aviso "ya inscrito" |
| `formato` | Documento mal escrito | `intentosRestantes` | Mensaje |
| `no_encontrado` | Fuera del padrón (o código inexistente en el panel) | `intentosRestantes` | Mensaje |
| `demasiados_intentos` | R-25 | `motivo`, `esperaMinutos` | Mensaje; no reintentar |
| `cerrado` | Sistema cerrado | — | Pantalla de cerrado |
| `recargar` | Ronda vieja | `ronda` | Pantalla 1 |
| `etapa_no_habilitada` | R-06 | `etapa` | Aviso |
| `visita_no_habilitada` | R-07 | — | Aviso; quitar la visita |
| `combinacion_invalida` | R-02, R-03, R-08 | `motivo` | Mensaje; quitar la elección en conflicto |
| `lleno` | Se llenó en ese instante | `actividadId`, `actividades` | Quitar esa elección |
| `no_disponible` | Se ocultó en ese instante | `actividades` | Repintar |
| `datos_invalidos`, `celular_invalido`, `sin_consentimiento` | Formulario | — | Mensaje junto al campo |
| `ocupado` | Bloqueo de más de 2 s o tiempo agotado | `motivo` [Sprint 3]: el SQLSTATE (57014 tiempo agotado, 55P03 bloqueo, 40P01 interbloqueo, 40001 serialización) | Reintentar al azar; si es una escritura, con la misma solicitud |
| `advertencia` | Decisión con consecuencias; no se escribió nada | `accion`, `minimo`, `ids` | Ventana; reenviar con `confirmar` o `ampliarCupo` |
| `requiere_cierre` | R-10 con el sistema abierto | — | Aviso |
| `sin_sesion` | Panel sin sesión ni clave | — | Pantalla de inicio de sesión |
| `falta_codigo` | Sesión sin código TOTP verificado (`aal1`) | — | Pedir el código |
| `no_autorizado` | Clave de prueba incorrecta (espera 1,5 s) | — | Aviso |
| `modo_produccion` | Clave de prueba con la base en PRODUCCION | — | Aviso |
| `sin_permiso` | Nivel insuficiente, cuenta sin rol o desactivada | `nivel` [v5.3] | Aviso: "requiere rol admin o superior" (2) o "es del propietario" (3); describe el rol que falta, no lo que hace la acción |
| `no_permitido` | Quitarse el propio rol de propietario o desactivarse | — | Aviso |
| `sin_conexion` | Lo genera la página, no la base: no hay internet | — | "No se ha enviado"; refrescar al volver |
| `tiene_inscritos`, `tiene_inscripcion`, `esta_visible`, `ya_existe`, `sin_cambios`, `cupo_invalido`, `valor_invalido`, `enlace_invalido`, `actividad_invalida` | Reglas del panel | — | Aviso |
| `error_servidor` | Error inesperado | `incidencia` [v5.2]; nunca el detalle | Mensaje genérico y el número |
| `solicitud_repetida` [v5.2] | Misma `solicitud` con otros datos | — | Nueva solicitud y reenviar |
| (campo) `repetida` [v5.2] | La respuesta es la guardada de un reenvío | — | Tratarla como la original |

---

[v5.4] Fuera de la API, en el SQL Editor, R-40 responde `ERROR: operación masiva bloqueada`. La API nunca lo recibe: sus funciones declaran el permiso cuando corresponde.

## 18. Seguridad, emergencias y riesgos aceptados

| Riesgo | Control | Dónde |
|---|---|---|
| Leer o borrar tablas con la clave pública | RLS sin políticas, sin permisos para `anon`; solo `api()` | Esquema |
| Inyección SQL | JSON y parámetros de funciones; nunca SQL armado con texto | `api()` |
| Probar DNIs al azar | R-25; respuestas sin datos personales | `intentos` |
| Inscribir a otra persona con su DNI | Riesgo aceptado; celular guardado, repetidos, anulación y cambio por soporte | Panel 1 |
| Robo del acceso al panel | Cuentas individuales con TOTP, rol por cuenta, sesión que vence, desactivación individual | Supabase Auth |
| Abuso de la inscripción privilegiada | Solo admin, llave para ampliar, origen y autor, "ampliada desde N" | Panel 1 |
| Cambios con reglas viejas | Ronda y bloqueo de `config` | Sección 5 |
| XSS por nombres | `textContent`; limpieza de caracteres de control | Frontends y base |
| Fórmulas en el CSV | Se quitan `= + - @` al inicio de cada texto | Base |
| Saturación | Bloqueo de 2 filas por milisegundos, límite de 3 s por consulta, reintentos al azar, refresco pausado con la pestaña oculta | Base y página |
| Filtración de `service_role` | Nunca en páginas ni repositorio; rotarla si se filtra | Tú |
| Tester en producción | Solo en modo PRUEBA; su clave se puede borrar | Base |
| Pérdida de datos | CSV completo cada día de inscripciones y antes de cada cierre con cambios | Panel 2 |
| Enlace de grupo reenviado | Aprobar nuevos participantes, verificación por celular, entrega a mano, restablecer enlace (sección 10) | WhatsApp · Panel 3 |
| Cuentas creadas por extraños | Registro abierto desactivado; solo invitados; sin rol no ven nada | Supabase Auth |
| Ex integrante del equipo | Desactivar en Equipo | Panel |
| Sesión robada sin código | `api()` exige nivel `aal2` (contraseña + código) | Base |
| Ver la inscripción de otro con su DNI [v5.2] | No hay comprobantes: solo "ya inscrito" (R-31) | `api()` |
| Fuga de información en errores [v5.2] | Número de incidencia; detalle privado y sin datos personales (R-36) | `api()` |
| Evadir el límite por red con una cabecera falsa [v5.2] | IP de la cabecera del proxy de Supabase, no del primer valor del cliente | `privado.red()` |
| Script de inicio de sesión alterado en la CDN [v5.2] | Versión fija con hash de integridad (`integrity`) y política de contenido (`Content-Security-Policy`) | HTML |
| Saturación o ataque [v5.3] | Alerta solo si el ritmo se sostiene 30 s (R-34) y procedimiento por gravedad, sin pausar (18.2) | Panel 1 |
| CSV con datos personales fuera del sistema [v5.3] | Lo descarga el equipo con cuenta (desde nivel 1), que ya ve esos datos en Listas; cada encargado recibe solo su actividad; el aviso de privacidad lo dice | Tú |
| Clave del tester en producción [v5.2] | Se borra sola al pasar a PRODUCCION (R-37) | Base |
| Datos personales (Ley N.º 29733) | Consentimiento explícito, uso solo para coordinar, nada personal en respuestas públicas ni en el repositorio | Todo |

---

### 18.2 Procedimiento ante un ataque, por gravedad [v5.3]

La prioridad es que los datos sigan en orden y el sistema siga rápido. **No se pausa el proyecto**: en los planes de pago de Supabase no se puede pausar, y en el gratuito pausar apaga todo para todos hasta que se reanude desde el panel de Supabase.

| Gravedad | Cómo se ve | Qué hacer | Nivel |
|---|---|---|---|
| Menor | Alerta roja, pero las inscripciones avanzan y la página responde | Solo mirar. La base absorbe la carga y el límite de intentos frena a quien prueba DNIs. Para aliviarla, subir el refresco a 60 s: las páginas consultan la mitad | 3 (refresco) |
| Moderada | La página se pone lenta o las inscripciones se detienen | **Cerrar ahora**: las respuestas de "cerrado" cuestan casi nada y los datos quedan intactos. Avisar por los canales oficiales. Cuando baje, el propietario abre; la ronda hace que las páginas viejas verifiquen de nuevo | 2 cierra · 3 abre |
| Grave | Nada responde durante varios minutos | Mantener cerrado y escribir al soporte de Supabase. Cambiar la clave pública es el último recurso: obliga a publicar un `config.js` nuevo y deja sin servicio a las páginas abiertas hasta que se recarguen | 3 |

[v5.4] El proyecto está en el plan gratuito: la pausa por inactividad se evita con el flujo de la sección 21.1, y las copias se hacen a mano (sección 19).

### 18.3 Riesgos aceptados [v5.4]

| Riesgo | Por qué se acepta | Qué lo mitiga |
|---|---|---|
| Suplantación con un DNI conocido | No hay segundo dato disponible (D15) | Límite de 4 intentos; correo y celular registrados identifican al impostor; soporte corrige con "Cambiar inscripción" o anulando |
| Sin WAF ni límite por IP antes de la base | No cabe en el plazo (D21) | Padrón, límite de intentos, índice único, alerta y "Cerrar ahora"; Cloudflare si las pruebas lo piden |
| Sin cifrado de campos | Rompería las búsquedas (D21) | Tablas cerradas (RLS y `revoke`); cifrado en tránsito y en reposo de la plataforma |
| El operador descarga listas y CSV | Ya ve esos datos (D21) | Cada descarga queda en la bitácora (R-39) |
| Sin copias automáticas (plan gratuito) | Sin presupuesto (D17) | Respaldo manual desde el panel, cada hora el día de apertura (sección 19) |
| Sin protección automática contra `DROP TABLE` o borrar el proyecto | La base no puede impedirlo desde dentro | Congelamiento, reglas para cambiar el SQL y respaldo previo (sección 20) |

## 19. Respaldo, recuperación y retención [v5.4]

### 19.1 Por qué importa en el plan gratuito

Si Supabase se cae, los datos siguen ahí y vuelven con el servicio: eso es una caída, no una pérdida. Los datos se **pierden** cuando se dañan o se borran: un `DELETE` o `UPDATE` sin condición, un SQL con errores, borrar el proyecto por equivocación. El plan gratuito no incluye copias automáticas, así que sin respaldos manuales un error así se lleva todo.

| Término | Qué mide | Valor acordado |
|---|---|---|
| **RPO** | Cuántos datos puedes perder: el tiempo entre el último respaldo y el desastre | **1 hora** el día de apertura; 24 horas los demás días |
| **RTO** | Cuánto tiempo puede estar el sistema fuera de servicio mientras se restaura | **2 horas** |

Ejemplo: respaldo a las 10:00, error a las 11:30. Al restaurar, se pierde lo que pasó entre 10:00 y 11:30: esas personas vieron su confirmación pero ya no están en la base. Por eso, el día de apertura, el respaldo es cada hora.

### 19.2 Las tres defensas

| Defensa | Qué evita |
|---|---|
| Congelamiento y panel (sección 20) | Que alguien toque el SQL de producción durante el evento |
| Protección masiva (R-40) | Que un `DELETE` o `UPDATE` sin condición borre o pise muchas filas |
| Respaldo desde el panel (R-41) | Que un error que pase las otras dos defensas se lleve los datos |

### 19.3 Respaldo desde el panel

- **Dónde:** pestaña Sistema → Respaldo → Descargar respaldo. Solo el propietario.
- **Qué contiene:** `config`, `tipos_actividad`, `padron`, `actividades`, `cruces_permitidos`, `inscripciones`, `inscripcion_actividades`, `organizadores`, `bitacora` e `incidencias`; la versión del esquema; la fecha; quién lo generó; el conteo de filas por tabla; y una huella SHA-256 del contenido para detectar archivos dañados.
- **Qué no contiene:** las cuentas de Supabase Auth (contraseñas y códigos), que no se pueden exportar, ni las tablas temporales (intentos, solicitudes, tráfico).
- **Tamaño:** pocos MB, incluso con miles de inscripciones (medido: la base completa de un congreso grande ocupa unos 24 MB).
- **Dónde guardarlo:** en una carpeta de tu computadora o en una memoria USB. Nunca en GitHub, en chats ni en correos: tiene datos personales.
- **Cómo se guarda [Sprint 4.1]:** el panel guarda el texto tal como lo entrega la base, sin volver a escribirlo en el navegador (que cambiaría un `1.50` por `1.5` o un entero de más de 15 dígitos, y la huella dejaría de coincidir).

### 19.4 Calendario de respaldos

| Momento | Respaldo |
|---|---|
| Antes de pasar a producción | Sí: el padrón y las actividades listos |
| Justo antes de abrir | Sí |
| Día de apertura | **Cada hora** mientras esté abierto (RPO 1 h) |
| Otros días con inscripciones | Al cierre de cada día |
| Antes de cualquier cambio de SQL | Siempre (sección 20) |
| Al terminar el congreso | Respaldo final y CSV de todas las listas |

Como respaldo adicional, el CSV de todas las listas (nivel 1) te dice quién se inscribió en qué aunque todo lo demás falle. No es restaurable automáticamente, pero sí legible.

### 19.5 Restaurar paso a paso (RTO 2 horas)

| Paso | Qué hacer | Tiempo aprox. |
|---|---|---|
| 1 | Si la base todavía responde: **Cerrar ahora** desde el panel | 1 min |
| 2 | Elegir el respaldo más reciente y comprobar su huella: `python supabase/restaurar.py respaldo.json --verificar` | 5 min |
| 3a | **Pérdida parcial** (filas borradas o pisadas por error, proyecto sano): `python supabase/restaurar.py respaldo.json --solo-faltantes --salida restaurar.sql` y pegarlo en el SQL Editor (o aplicarlo directo con `--dsn "$DSN_PRODUCCION" --confirmar "$REF_PRODUCCION"`, mejor si el archivo es grande). Inserta solo lo que falta, no pisa lo que existe; correrlo dos veces no duplica nada | 15 min |
| 3b | **Pérdida total** (proyecto inutilizable): en el plan gratuito caben 2 proyectos activos, así que se borra o pausa el de prueba y se crea uno nuevo; se instala con `python supabase/instalar.py --dsn … --confirmar …` (sin `--datos`); luego `restaurar.py respaldo.json --completo` (con `--salida` para el SQL Editor o con `--dsn`). Exige una base vacía; deja las inscripciones cerradas y la ronda +1 | 45 min |
| 4 | Solo en 3b: invitar de nuevo al equipo, darte el rol de propietario por SQL (sección 12.3) y asignar roles; pegar la nueva `API_URL` y `ANON_KEY` en `config.js` y publicar | 30 min |
| 5 | Panel: comprobar la integridad y recontar si hace falta; tester en modo lectura | 15 min |
| 6 | **Abrir.** La ronda hace que las páginas viejas verifiquen de nuevo. Avisar por los canales oficiales a quienes se inscribieron después del respaldo | 10 min |

`restaurar.py` verifica la huella y la versión del esquema, inserta las tablas en el orden de sus referencias, declara `ciic.masivo` en su transacción, y al final recuenta los contadores y muestra el conteo por tabla para compararlo con el respaldo.

[Sprint 4] Cómo quedó:

- **Huella:** SHA-256 del texto que PostgreSQL da a cada tabla en jsonb (nativo y rápido: 1,1 s para una base de 25 MB), por tabla y total. `restaurar.py` la reproduce desde el archivo aunque se haya vuelto a escribir con otros espacios, y lee los decimales tal cual (`1.50` sigue siendo `1.50`) [Sprint 4.1]. Detecta un archivo dañado o modificado sin recalcularla; no es una firma. Un respaldo guardado con el panel del Sprint 4 que tuviera decimales en `datos` no pasaría la verificación: para esa emergencia, `--aceptar-huella-distinta` restaura si las filas de cada tabla cuadran (siempre con `--simular` primero).
- **Antes de cambiar nada**, el SQL exige las inscripciones cerradas (y bloquea `config` para que nadie abra mientras tanto) y un esquema igual o más nuevo que el del respaldo. Con `--solo-faltantes`, el mismo modo que el respaldo: un respaldo de PRUEBA no entra en una base en PRODUCCION. Con `--completo`, una base sin padrón, actividades, cruces ni inscripciones.
- **`--simular`** hace todo y lo deshace: muestra qué volvería, sin tocar la bitácora ni los contadores de ids. Se usa siempre primero. **`--tablas`** limita qué tablas se devuelven.
- **`--solo-faltantes` devuelve filas borradas, no repara filas modificadas** (las que existen no se tocan). Una inscripción vuelve entera, con sus actividades, solo si ya no existe: a una inscripción que existe nunca se le agregan actividades, aunque se haya cambiado después del respaldo. Las actividades que vuelven, vuelven **ocultas** y el informe las lista para revisarlas. También vuelve lo que se quitó a propósito después del respaldo (una persona del padrón, una actividad): por eso conviene `--simular` y, si hace falta, `--tablas`.
- **`--completo`** respeta los valores del respaldo también en `tipos_actividad`, conserva las actividades de inscripciones anuladas aunque la actividad ya no exista, y si la base nueva ya tenía alguna entrada de bitácora (por ejemplo, `asignar_propietario`), la del respaldo con el mismo número entra con un número nuevo.
- Las cuentas del equipo solo se restauran si su usuario existe en Supabase Auth; en un proyecto nuevo se invitan de nuevo (paso 4). Los contadores de ids solo avanzan. Deja una entrada "Restaurar respaldo" en la bitácora.
- El SQL generado tiene datos personales: `restaurar*.sql` está en `.gitignore` y no es una migración (no se nombra `NN_…sql`).

### 19.6 Procedimientos ante fallos

| Situación | Qué hacer |
|---|---|
| Supabase caído | Nada que restaurar: los datos vuelven con el servicio. Avisar por los canales oficiales; el flujo de 21.1 te avisa por correo si no responde |
| Página lenta o ataque | Sección 18.2 |
| Datos borrados o pisados por error | Borrados: paso 3a de 19.5 con el último respaldo (primero `--simular`). Pisados (modificados): se corrigen desde el panel con el respaldo como referencia; `--solo-faltantes` no pisa lo que existe |
| Doble clic o respuesta perdida | Nada: la idempotencia lo resuelve (R-32) |
| Clave pública (`ANON_KEY`) visible | No es un incidente: es pública por diseño |
| Clave secreta (`service_role` o `secret`) expuesta | Rotarla de inmediato en Supabase, revisar la bitácora y los registros del proyecto; nunca debe estar en las páginas ni en el repositorio |
| Alguien del equipo pierde su contraseña o su celular | Sección 12.6 |
| Pérdida de acceso a tu cuenta de Supabase o de GitHub | Prevenir: verificación en dos pasos en ambas cuentas y sus códigos de recuperación guardados fuera del celular. Si el propietario del panel pierde su cuenta: `select privado.cambiar_propietario('nuevo@correo.com');` en el SQL Editor (§12.3) |
| Página publicada con errores | En GitHub, revertir el último cambio; GitHub Pages publica la versión anterior en minutos |
| SQL aplicado con errores | Si el sistema sigue sano: migración correctiva nueva. Si dañó datos: paso 3a o 3b de 19.5 con el respaldo tomado antes de aplicarlo |
| Proyecto pausado | Reanudarlo desde el panel de Supabase; revisar por qué falló el flujo de 21.1 |

### 19.7 De la base de prueba a la real [v5.5]

Todo desde la pestaña Sistema, con las inscripciones cerradas y la base en modo PRUEBA:

| Paso | Qué | Resultado |
|---|---|---|
| 1 | **Respaldo** de la base ficticia | Por si hay que volver atrás |
| 2 | **Vaciar datos de prueba** (llave `VACIAR`) | Base vacía; configuración y equipo intactos |
| 3 | **Importar padrón** real (CSV documento;etapa) | Informe: agregados, conflictos, inválidos |
| 4 | **Importar actividades** reales (CSV con encabezado) o crearlas en Actividades | Catálogo cargado y oculto, salvo `visible = SI` |
| 5 | Revisar: mostrar las actividades, enlaces de grupos, etapas; una inscripción de prueba con un documento real de alguien del equipo | Todo como debe quedar |
| 6 | **Respaldo** | La base real antes de producción |
| 7 | **Pasar a producción** (llave `PRODUCCION`) | Borra las inscripciones de prueba del paso 5 y la clave del tester |
| 8 | **Respaldo** y abrir cuando corresponda | Empieza el congelamiento (sección 20.1) |

Si algo sale mal entre los pasos 2 y 7, se restaura el respaldo del paso 1 con `restaurar.py` (sección 19.5).

### 19.8 Retención: 90 días

| Momento | Qué hacer |
|---|---|
| Al terminar el congreso | Respaldo final, CSV de todas las listas y CSV por actividad para cada encargado |
| Durante los 90 días | La base sigue activa para asistencia y consultas; el flujo de 21.1 evita la pausa |
| Al terminar el congreso, o antes si el correo de Supabase ya pasó a la cuenta de envío [Sprint 6.1] | Revocar la contraseña de aplicación "Supabase CIDEIC" de la cuenta Gmail personal del propietario que envía el correo de Supabase (Cuenta de Google → Seguridad → Contraseñas de aplicaciones), y quitar ese SMTP o pasarlo a la cuenta de envío |
| Día 90: **a más tardar el 19/02/2027** (el congreso termina el 21/11/2026, según viicideic.space) | Borrar el proyecto de Supabase (Project Settings → General → Delete project), borrar los respaldos y CSV propios, y pedir a cada encargado que borre los suyos. Anotar la fecha |

Si algún uso futuro necesita los datos más allá de los 90 días, primero se cambia el aviso de privacidad y se sube `aviso_version`.

## 20. Reglas para cambiar el SQL (personas e IA) [v5.4]

El día a día se opera desde el panel. El SQL de producción solo cambia con una migración revisada, probada y respaldada. Estas reglas valen igual para una persona que para un asistente de IA; la skill `skill-sql-ciic/SKILL.md` las contiene listas para cargar en el asistente.

### 20.1 Congelamiento

Desde 24 horas antes de abrir hasta el fin del congreso, incluida la semana de exámenes: **no se corre SQL en producción**. Todo lo operativo tiene botón en el panel:

| Necesidad | Dónde, sin SQL |
|---|---|
| Agregar personas al padrón | Panel 2 (una) o Sistema → Importar padrón (muchas) |
| Cupos, mostrar u ocultar, crear o editar actividades | Paneles 1 y 3 |
| Inscribir, cambiar, anular | Panel 1 |
| Abrir, cerrar, etapas, reglas | Panel 1 |
| Recontar inscritos | Panel 1 → Integridad |
| Respaldo | Sistema → Respaldo |
| Vaciar la base ficticia y cargar la real | Sistema → pasos 1 a 5 (sección 19.7) |
| Vaciar las inscripciones de prueba y pasar a producción | Sistema → Pasar a producción |
| Roles del equipo | Sistema → Equipo |

**Excepción** (solo si algo crítico no se puede resolver desde el panel): respaldo → probar en el proyecto de prueba con el tester completo → cerrar inscripciones → respaldo → aplicar → tester en modo lectura → abrir. Todo anotado en la bitácora del proyecto.

**En la apertura del 11/11 a las 20:00 [Sprint 6]:** el congelamiento empieza el 10/11 a las 20:00. Todo el SQL de PRODUCCIÓN del Sprint 6 va el 09/11 (migraciones 10 a 12 y `asignar_propietario`). Entre el 10/11 a las 20:00 y Pasar a producción (11/11, 12:00), además del panel, solo se cambian las páginas para corregir lo que encontró el ensayo, con el tester en local y en PRUEBA. Desde Pasar a producción, solo el panel. Qué hacer con cada tipo de problema: `sprints/sprint-6/GUIA.md`, parte 4.1.

### 20.2 Reglas

1. **Nunca `DELETE` ni `UPDATE` sin `where`.** Antes de cada uno, correr el mismo `where` con `select count(*)` y comprobar el número. R-40 bloquea los que pasen de 10 filas: si salta, se revisa el `where`; no se desactiva la protección.
2. **Respaldo antes de todo cambio** en producción (sección 19.3).
3. **Primero en el proyecto de prueba**, con el tester completo en verde. Nunca se prueba en producción.
4. **Migraciones numeradas y nunca editadas** después de aplicarse: `03_…sql`, `04_…sql`. Si una migración tuvo un error, se corrige con otra nueva.
5. **Cada migración se puede volver a correr**: `create or replace`, `create … if not exists`, `alter … add column if not exists`, y todo dentro de `begin; … commit;`.
6. **Nada destructivo sin plan**: `drop`, `truncate` y borrados masivos solo con respaldo previo, `set local ciic.masivo = 'confirmado'` dentro de la transacción y la confirmación explícita del propietario.
7. **Funciones nuevas en el esquema `privado`**, con `revoke` para `public`, `anon` y `authenticated`. La única puerta pública es `public.api(jsonb)`.
8. **`security definer` solo con `set search_path` fijo** y nombres de tabla con su esquema (`public.inscripciones`).
9. **Sin SQL dinámico armado con texto del usuario.** Todo dato entra como parámetro desde el JSON.
10. **Toda acción nueva del panel** declara su nivel (R-26), deja entrada en la bitácora, usa `solicitud` si escribe (R-32) y tiene pruebas en el tester (bloques R y AB como mínimo).
11. **El contrato no cambia en silencio**: campos, tipos de respuesta o niveles nuevos suben la versión del contrato y actualizan este documento.
12. **Nada de datos personales** en migraciones, issues, chats con asistentes de IA ni capturas: para probar, datos ficticios.
13. **`02_api.sql` por módulos** al tocarlo: `api.sql` (puerta), `registro.sql`, `actividades.sql`, `participantes.sql`, `equipo.sql`, `seguridad.sql`, `auditoria.sql`, en ese orden de instalación.
14. **Fuera del horario de inscripción** y con el sistema cerrado si el cambio toca reglas.
15. **Dentro de una función, ningún `DELETE` ni `UPDATE` sin `WHERE`** [Sprint 3.2]: Supabase los rechaza por la API (`safeupdate`, error 21000). Para todas las filas a propósito: `where true`. El tester lo vigila.
16. **Producción solo con `instalar.py`** (primero `--verificar`, con `--confirmar <ref>`) o con las sentencias de una línea de la guía (`ip_cabecera`, `asignar_propietario`), cuando el propietario lo pide y fuera del congelamiento.

### 20.3 Plantilla de migración

```sql
-- 03_descripcion_corta.sql · fecha · autor · qué cambia y por qué
-- Requisitos: respaldo de producción tomado; tester completo en verde en el proyecto de prueba.
begin;

-- 1. Comprobación previa: abortar si el estado no es el esperado
do $$ begin
  if (select modo from public.config where id = 1) = 'PRODUCCION'
     and (select abierto from public.config where id = 1) then
    raise exception 'Cierra las inscripciones antes de aplicar esta migración.';
  end if;
end $$;

-- 2. Cambios que se pueden volver a correr
alter table public.inscripciones add column if not exists ejemplo text;
create or replace function privado.ejemplo(b jsonb) returns jsonb language plpgsql stable as $$
begin
  return jsonb_build_object('ok', true);
end $$;
revoke all on function privado.ejemplo(jsonb) from public, anon, authenticated;

-- 3. Operación masiva, solo si es imprescindible
-- set local ciic.masivo = 'confirmado';
-- update public.… set … where …;   -- antes: select count(*) … where … (mismo where)

-- 4. Comprobación posterior: abortar si algo no cuadra
do $$ begin
  if exists (select 1 from public.actividades a
             where a.inscritos <> (select count(*) from public.inscripcion_actividades ia
                                   join public.inscripciones i using (codigo)
                                   where ia.actividad_id = a.id and i.estado = 'CONFIRMADO')) then
    raise exception 'Integridad rota después de la migración: se revierte.';
  end if;
end $$;

commit;
```

### 20.4 Revisión antes de aplicar

| Pregunta | Debe ser |
|---|---|
| ¿Hay respaldo de producción de hoy? | Sí |
| ¿Pasó el tester completo en el proyecto de prueba? | Sí |
| ¿Algún `delete` o `update` sin `where`? | No |
| ¿Toda función nueva tiene `revoke` y, si es `security definer`, `search_path` fijo? | Sí |
| ¿Se puede volver a correr sin dañar nada? | Sí |
| ¿Cambia el contrato? | Si sí: versión nueva y documento actualizado |
| ¿Estamos dentro del congelamiento? | No (o es la excepción de 20.1) |
| ¿El sistema está cerrado si toca reglas? | Sí |

### 20.5 Skill para asistentes de IA

El archivo `skill-sql-ciic/SKILL.md` resume estas reglas para que un asistente de IA las siga al proponer o revisar SQL: se niega a escribir `delete` o `update` sin `where`, exige respaldo y prueba previa, usa la plantilla de 20.3, revisa con la tabla de 20.4 y advierte cuando un cambio toca el contrato o cae dentro del congelamiento. En Claude se instala como skill; en otros asistentes se pega como instrucciones del proyecto.

## 21. Tecnologías y despliegue

| Capa | Tecnología | Función |
|---|---|---|
| Frontends | HTML, CSS, JavaScript; framework libre | Página y paneles con tu diseño |
| Hosting de frontends | GitHub Pages | Publica los archivos estáticos |
| Base de datos | PostgreSQL 15+ en Supabase | Datos, transacciones, bloqueos, restricciones |
| Lógica | PL/pgSQL | Reglas dentro de la base |
| API | PostgREST (Supabase) | Expone `api()` |
| Cuentas | Supabase Auth con TOTP; supabase-js en versión fija con hash de integridad [v5.2] | Equipo de organización |
| Carga de datos | Python + openpyxl | Hoja → SQL |
| Pruebas | Python + Playwright + GitHub Actions | Tester automático |
| Pruebas locales | PostgreSQL local + `servidor_local.py` | Sin cuenta de Supabase |

Despliegue recomendado:

| Elemento | Recomendación |
|---|---|
| Proyectos | Dos en Supabase: prueba y producción, con el mismo SQL |
| SQL | `01_esquema.sql` una vez; cada cambio como archivo numerado (`03_v51.sql`…) que se puede volver a correr sin perder datos |
| Claves en las páginas | Solo `API_URL` y `ANON_KEY` |
| Plan gratuito [v5.4] | Dos proyectos activos (prueba y producción); sin copias automáticas (sección 19); pausa tras 7 días de poca actividad (21.1); 500 MB de base (se usa alrededor del 5 %) y 5 GB de transferencia al mes |

---

### 21.1 Evitar la pausa automática [v5.4]

| Opción | Qué hace | Cuándo |
|---|---|---|
| Flujo "Mantener Supabase activo" | `.github/workflows/mantener-activo.yml` hace cada hora [Sprint 5.1] una consulta real a la base (`estado`). El horario de GitHub es de mejor esfuerzo: se atrasa horas o se salta (incidencia #40). Para la pausa de 7 días alcanza; para borrar los intentos ya no se depende de él (pg_cron, R-25). Lee `config.js` publicado en GitHub Pages (o la variable de repositorio `CONFIG_URL`), no usa acciones de terceros, valida HTTP 200 y que el JSON diga `tipo: estado` (con `jq`), oculta la clave en el registro y no imprime la respuesta. Si falla tres veces, GitHub te avisa por correo | Desde que crees el proyecto, siempre |
| Plan de pago | Los proyectos de pago nunca se pausan | No se usa: sin presupuesto (D17) |
| Entrar al proyecto | Supabase avisa por correo una semana antes de pausar; entrar al panel del proyecto genera actividad | Respaldo manual |

Notas: GitHub desactiva los flujos programados de un repositorio público sin actividad durante 60 días; antes del congreso no aplica, y después basta con reactivarlo en Actions. Un proyecto pausado se reanuda desde el panel de Supabase con sus datos, pero mientras está pausado nadie puede usarlo.

### 21.2 Base ficticia [v5.5]

`local/generar_datos.py` produce siempre la misma base inventada (semilla fija): nombres, documentos, correos y celulares ficticios.

| Archivo | Contenido | Para qué |
|---|---|---|
| `docs/demo/datos-demo.js` | Estado completo del modo demo | Diseñar y probar las páginas sin Supabase |
| `local/datos_prueba.sql` | Padrón (3201: 1801 de Etapa 1, 1000 de Etapa 2, 400 de Etapa 3) y 28 actividades (14 por día, 2 ocultas), sin inscripciones | Base local y del proyecto de prueba; es la que usa el tester |
| `local/inscripciones_prueba.sql` | 700 inscripciones confirmadas y 20 anuladas, después de la anterior | Explorar el panel con datos (opcional) |
| `local/padron_prueba.csv` | El padrón de carga en formato de importación: 3200 filas (el padrón tiene 3201: la persona número 3201 es el ejemplo de alta de último momento, con origen PANEL) | Probar el paso 3 de 19.7 |
| `local/padron_importar_ejemplo.csv` | 200 documentos nuevos y casos difíciles (puntos, sin cero, conflicto, inválido, BOM) | Probar "Importar padrón" |
| `local/actividades_prueba.csv` | Las 28 actividades en formato de importación | Probar el paso 4 de 19.7 |

Casos que incluye: DNI con cero inicial y sin él, carnet de extranjería, pasaporte, RUT con letra, ya inscritos, Etapa 3 sin habilitar, tres actividades llenas (VIS03, VIS04, VIS08), dos con entrega a mano (VIS11, VIS15), una sin enlace (TAL10), dos ocultas (VIS13, VIS16), un cruce permitido (VIS05 × TAL06), tres pares de celulares repetidos, celulares de Chile, inscritos desde el panel, la mitad marcados en su grupo, seis cuentas del equipo (una sin rol, una desactivada) y una bitácora de ejemplo.

[Sprint 2] El esquema v5.5 es el predeterminado: `python local/generar_datos.py`. Para una base anterior al Sprint 2: `--esquema v51`.

**Demos autónomas.** `local/armar_demos.py` arma `demo/demo-participante.html` y `demo/demo-panel.html`: cada página en un solo archivo, con estilos, configuración, datos ficticios y backend de demostración adentro, más un selector de estados para diseñar (espera, sin conexión, cuenta regresiva, cerrado, error, saturación, integridad rota, advertencia, inicio de sesión y código). Se abren con doble clic y comparten datos si están en la misma carpeta.

### 21.3 Proyectos y publicación [Sprint 3]

| Pieza | Decisión |
|---|---|
| Proyectos de Supabase | Dos, en el plan gratuito (el máximo): **PRUEBA**, con la base ficticia, donde corre el tester; y **PRODUCCIÓN**, con el esquema y luego los datos reales por el panel (§19.7). Región São Paulo |
| Instalación | `supabase/instalar.py` [Sprint 3.1]: registro de migraciones (`privado.migraciones`); aplica **solo lo pendiente**, todo en **una transacción** (si algo falla no queda nada a medias); en una base sin registro, deduce lo aplicado de `privado.version()`; avisa si un archivo ya aplicado cambió. No toca nada si la base está en PRODUCCION abierta. En una base remota exige `--confirmar <ref>` antes de conectarse. Solo carga datos ficticios en una base de PRUEBA con padrón, actividades e inscripciones vacíos. Una migración es un archivo `supabase/NN_*.sql` con el encabezado "CIIC 2026 · … · NN ·": lo que genera `excel_a_sql.py` nunca se ejecuta |
| Página publicada | GitHub Pages desde `/docs`. Hasta la apertura, `docs/config.js` apunta a PRUEBA; en la apertura (Sprint 6) pasa a PRODUCCIÓN |
| Tester en GitHub | Prueba siempre PRUEBA: variables `PRUEBA_API_URL`, `PRUEBA_ANON_KEY` y secreto `ADMIN_KEY`. A la página publicada le inyecta la configuración de PRUEBA, aunque `config.js` apunte a producción |
| Mantener activo | Consulta los dos proyectos (cada uno se pausa por separado): el de `config.js` y los de las variables `PRUEBA_*` y `PRODUCCION_*`, sin repetir. Si falta alguna variable, falla y GitHub avisa por correo |
| Cadena de suministro | Las acciones de GitHub se fijan por SHA de commit (checkout v6.1.0, setup-python v6.3.0, upload-artifact v6.0.0) y las dependencias del tester por versión exacta, todas con dos semanas o más de publicadas |
| `safeupdate` [Sprint 3.2] | Supabase rechaza `DELETE` y `UPDATE` sin `WHERE` por la API. Ninguna función los lleva (migración 07); el tester lo vigila con un escáner de todas las funciones, y el servidor local carga `safeupdate` cuando está instalado, para que el defecto aparezca también en local |
| IP observada en PRUEBA [Sprint 3.2] | Llega `cf-connecting-ip` con la IP real; `x-forwarded-for` antepone lo que mande el cliente; `x-real-ip` no llega; una `CF-Connecting-IP` enviada por el cliente la rechaza el proxy (HTTP 403). `ip_cabecera = 'cf-connecting-ip'` |
| Terceros | En modo Supabase, el tester consulta `api.ipify.org` para saber la IP pública de quien lo corre (prueba de IP, §8). Ese servicio solo recibe esa IP; ningún dato del sistema |
| Secretos | Las cadenas de conexión y la clave del tester viven en `.env.local` (excluido por `.gitignore`, prohibido al visor de Claude Code) y en los secretos de GitHub. Nunca en el repositorio ni en el chat |
| Documentos del tester | Formato `ZQX` + 7 dígitos, que ninguna persona real tiene. `admin_limpiar` solo borra del padrón documentos con ese formato (migración 05) |
| Respaldo y restauración [Sprint 4] | `panel_respaldo` (migración 08) y `supabase/restaurar.py` (§19.5). Medido en local: con la base ficticia y 720 inscripciones, 1,2 MB en 0,2 s; con una base de 25 MB (43 000 en el padrón, 20 000 entradas de bitácora), 16 MB en 1,1 s. Restauración completa de la base ficticia en 0,4 s |
| Ensayo por la API real [Sprint 4.1] | `admin_ensayo` (migración 09, solo con la clave del tester y en modo PRUEBA): ejecuta "Pasar a producción" o "Vaciar datos de prueba" **por la API**, con el rol, `safeupdate`, los disparadores y R-40 de Supabase, mide cómo quedó la base y lo deshace todo en la misma llamada. El tester lo corre siempre (bloque AF), también desde GitHub. En PRODUCCIÓN no hay clave del tester: no hace nada |
| Carga y saturación [Sprint 4] | Bloque W: 1000 personas sintéticas (`ZQX`, importadas con `panel_padron_importar`, que reemplaza al `admin_sembrar` del plan) navegan y confirman a la vez; luego el tester baja el umbral a 100 para ver la ráfaga sin alerta y la alerta sostenida, y lo restaura |

La guía paso a paso está en `sprints/sprint-3/GUIA.md`.

## 22. Pruebas y aceptación

El tester (`tester/tester.py`) prueba el sistema real instalado. En modo completo inscribe personas del padrón de prueba y al final borra solo lo suyo y deja configuración, cupos y actividades como estaban (la ronda queda más alta).

| Bloque | Comprueba |
|---|---|
| A · Conexión | `estado` completo, actividades de 2 días, lista pública sin enlace, panel sin sesión y con clave falsa |
| B · Documentos | Formatos inválidos con intentos restantes, inexistente, normalización (espacios, puntos, guiones, cero inicial) |
| C · Etapas y visitas | Etapa no habilitada, etapa sin visitas, habilitar en vivo, quitar exige cierre |
| D · Combinaciones y datos | Cantidad, dos visitas, mismo día, oculta, nombre, correo, celular, consentimiento, fórmula en el nombre, duplicado |
| E · Cupos | 18 personas por 15 cupos: 15 exactas; todo o nada; mismo DNI 4 veces a la vez |
| F · Panel | +paso en vivo, −paso y ocultar exigen cierre, cerrar sube la ronda, bajar bajo inscritos con advertencia, buscar, anular, CSV |
| H · Cierre y ronda | Cerrado, página vieja (`recargar`), cierre en medio de 20 inscripciones simultáneas, aviso con cuenta regresiva y cierre automático |
| I · Horarios y cruces | Cruce, par permitido, mismo día sin cruce, restringir exige cierre, el panel respeta horarios |
| J · Intentos | 3, 2, 1, 0 y frenado; acierto reinicia; límite por red (local) |
| K · Soporte | Cambiar inscripción con advertencia y llave, contadores exactos, mismo código; inscribir desde el panel ignora etapas |
| L · WhatsApp | `grupoModo`, entrega a mano sin enlace, verificar celular inscrito y no inscrito, enlace inválido |
| M · Roles | Lo que puede y no puede el operador; admin sin Equipo |
| N · Padrón y catálogo | Alta de último momento, otra etapa, quitar exige cierre, crear oculta, horario fijo con inscritos, quitar visible |
| O · Equipo | Sin código, sin rol, asignar rol, no quitarse el rol propio ni desactivarse, cuenta desactivada (local con `--dsn`) |
| P · Navegador | Página: verificar, elegir, confirmar, comprobante, cerrado mientras elige, intentos, celular. Panel: clave de prueba, +paso, −paso con aviso, cuatro pestañas |
| Q · Carga | 150 personas verifican y confirman a la vez: sin errores, sin sobrecupo, nadie dos veces, 95 % bajo 60 s |

Resultado en local (PostgreSQL 16, dos corridas seguidas): **163 de 163**; carga de 150 con 95 % en 2,0 s, sin reintentos.

[Sprint 4, en Supabase] W con 1000 personas desde GitHub: 18 s en total, de principio a fin p50 13,5 s y p95 15,9 s, confirmar p95 3,9 s, 0 reintentos, sin sobrecupo ni dobles; pico de 2342 llamadas en una ventana, sin alerta (no fueron 3 seguidas). Desde una PC con Windows la carga de 1000 midió la PC (límite de archivos y conexiones TLS), no el sistema: la referencia es la de GitHub. [Sprint 4.1] El tester reutiliza conexiones, amplía el límite de archivos en Windows y reparte la llegada de W en 3 s.

[Sprint 4] Resultado en el entorno de diseño (PostgreSQL 16, con navegador, desde cero y sobre una base 5.5-s3.2 puesta al día): **355 de 355**, 1 omitida (la página publicada, que solo se prueba contra GitHub Pages). W con 1000 personas (seis corridas): de principio a fin p50 2,2 a 8,7 s y p95 3,8 a 10,3 s; confirmar p50 0,5 a 1,6 s y p95 1,1 a 3,0 s; 0 reintentos.

Durante la construcción de las láminas, el simulador detectó cinco fallas, ya corregidas: la página no recalculaba el permiso de visitas; los datos de prueba dejaban sin probar los cruces; el mensaje del cuarto intento no avisaba el límite; tras un cierre programado, un segundo repintado borraba el mensaje "tu elección no se guardó"; y la actividad de ejemplo con entrega a mano estaba llena. Al construir el backend apareció una sexta: la página no podía saber qué cruces permitiste, y por eso se agregó `cruzaCon`.

### 22.2 Bloques nuevos de la v5.2

| Bloque | Comprueba | Crítico |
|---|---|---|
| R · Privilegios | Como anónimo: leer `padron` e `inscripciones` por la API REST, llamar funciones de `privado`, ejecutar acciones de panel. Todo rechazado. Una prueba por rol en cada acción | Sí |
| S · Sin comprobantes | `duplicado` sin código, actividades ni enlaces; `registrado` sin código | Sí |
| T · Carreras | 100 personas por los últimos 10 cupos; dos cambios simultáneos de la misma inscripción; anulación mientras otros toman los cupos; reducir cupo mientras otros confirman | Sí |
| U · Idempotencia | Reenviar la misma solicitud tras perder la respuesta: misma respuesta, ningún cambio doble; misma solicitud con otros datos → `solicitud_repetida` | Sí |
| V · Integridad | Tras cada bloque, cada contador igual a sus inscripciones; inserción a mano mantiene la integridad | Sí |
| W · 1000 personas | 1000 usuarios virtuales mezclando navegación y confirmación: cero sobrecupos, nadie dos veces, P50 y P95 medidos. [v5.3] Ráfaga de una ventana: sin alerta. Con el umbral bajado por el tester y el ritmo sostenido 3 ventanas: alerta | Sí |
| AA · Listas y CSV [v5.3] | Listas ordenadas por apellidos con todos los campos y filtro por etapa; marcar en el grupo queda en la base y se relee; el reenvío de la misma solicitud no lo cambia dos veces; CSV como operador, por actividad, por etapa y de todas, con las columnas de R-39 y fórmulas neutralizadas | Sí |
| AB · Niveles de rol [v5.3] | Cada acción con cada rol: operador solo nivel 1, admin hasta 2, propietario los 3; cerrar como admin sí, abrir como admin no | Sí |
| AC · Padrón mínimo [v5.3] | Alta solo con documento y etapa; documento repetido → `ya_existe`; ninguna acción cambia la etapa; correo obligatorio en el formulario | Sí |
| X · Incidencias | Un error interno devuelve solo el número; el detalle aparece para el admin | No |
| Y · Restauración [v5.4] | Respaldo del panel → `restaurar.py --completo` en una base nueva → conteos y huella iguales; `--solo-faltantes` después de borrar filas a propósito → vuelven sin duplicar | Sí |
| Z · Privacidad y equipo | Sin casilla no se inscribe; se guarda `aviso_version`; nadie asigna "propietario" por el panel; la clave del tester desaparece en PRODUCCION | Sí |

Nada se abre al público sin los bloques críticos en verde contra el proyecto real.

### 22.3 Bloques nuevos de la v5.4

| Bloque | Comprueba | Crítico |
|---|---|---|
| AD · Operaciones masivas | `delete from inscripciones;` y `update padron set etapa = 1;` sin permiso → bloqueados sin cambiar nada; con `ciic.masivo` en la transacción → pasan; `truncate` bloqueado; ninguna acción de la API se ve afectada | Sí |
| AE · Importar padrón | Nuevos agregados; repetidos con la misma etapa; conflictos de etapa sin cambiar nada; inválidos informados; repetir la importación no duplica | Sí |
| AF · Pasar a producción | Rechazado abierto, sin la llave o en PRODUCCION; vacía solo lo de prueba; padrón y actividades intactos; la clave del tester desaparece | Sí |
| AG · Bitácora | Cada CSV y .vcf registrado con filtros y filas; cambios de rol con antes y después | Sí |
| AH · Correo en el panel | `panel_inscribir` sin correo → `datos_invalidos` | Sí |
| AJ · Vaciar datos de prueba [v5.5] | Rechazado abierto, sin llave, como admin o en PRODUCCION; vacía todo lo de prueba; configuración y equipo intactos | Sí |
| AK · Importar actividades [v5.5] | Las 28 del CSV de prueba se agregan; repetidas sin cambios; filas inválidas con motivo; después de vaciar e importar, la base vuelve a inscribir | Sí |
| AI · Idempotencia con ámbito | La misma `solicitud` de otra cuenta o de otro documento no choca; una `solicitud` que no es UUID → `valor_invalido` | Sí |
| AL · Redes con intentos fallidos [Sprint 5.1] | Niveles; una red cerca, frenada y liberada; IP enmascarada; bitácora; borrado de ventanas terminadas | Sí |
| Lectura · página publicada [Sprint 6] | Sin inyectar nada: la página y el panel publicados llaman solo al proyecto de `--api`, el panel no ofrece la clave de prueba y la base tiene las migraciones 10 y 11 (`5.5-s6`) | Sí, en la apertura |

### 22.4 Prueba de ataque [Sprint 6]

`tester/ataque.py`, solo contra PRUEBA (se niega en modo PRODUCCION o si `config.js` ya apunta a PRODUCCIÓN). Ataca con la ANON_KEY publicada; la clave del tester solo prepara y limpia. Unos 3 a 5 minutos:

| # | Ataque | Resiste si |
|---|---|---|
| 1 | Leer o escribir tablas por PostgREST, llamar funciones de `privado`, GraphQL, crear una cuenta | No hay filas ni escritura; GraphQL no muestra tablas; "Allow new users to sign up" apagado |
| 2 | Enumerar documentos cambiando de dispositivo; falsear la IP con cabeceras; dispositivos raros | La red se frena cerca del límite; ninguna respuesta trae datos personales; las cabeceras falsas no la sacan del freno |
| 3 | Documentos raros (tipos, 5000 caracteres, Unicode, inyección SQL o HTML, carácter nulo) | Respuesta controlada en menos de 3 s, sin error interno |
| 4 | Inscribir de más: el mismo documento 20 veces a la vez, 3 actividades, repetidas, inexistentes, 2 visitas, sin aviso, ronda vieja, sin solicitud o reusada, etapa no habilitada, fuera del padrón | Una sola inscripción y ninguna fuera de las reglas |
| 5 | Campos raros: HTML, fórmulas, caracteres invisibles y de dirección, 5000 letras, celular o correo inválidos | Se guarda como texto limpio y recortado (R-47) |
| 6 | Panel sin sesión, rol pedido en el cuerpo, adivinar la clave del tester, tokens falsificados (sin firma, otra clave, service_role, vencido), sesión sin código, rol menor | Todo rechazado; la clave falsa cuesta 1,5 s por intento |
| 7 | Verificar celular y exportar sin sesión; un operador que prueba celulares | Rechazado sin sesión; con sesión es un riesgo aceptado (el operador ya ve su lista) y queda en la bitácora |
| 8 | Enmarcar el panel en otro sitio (clickjacking) | El panel no se muestra dentro de un marco de otro origen |

## 23. Sprints

Con el congreso del 16 al 21 de noviembre (la Etapa 1 abre el 11/11), cada sprint dura un día. [Sprint 6] Hasta el Sprint 5.1 este documento decía "congreso el 12/11": la fecha real es la de viicideic.space. La v5.1 construida (163 de 163 pruebas) es la base: no se empieza de cero.

| Sprint | Fecha | Contenido | Cierra cuando |
|---|---|---|---|
| 0 | 04/11 | Contrato v5.2 congelado: lámina INS-07 y esta revisión 3 | Tu aprobación |
| 1 | 05/11 | Seguridad: D1, D5, D8, D9, D13 (niveles de rol), D19 (protección masiva); IP del proxy; hash de integridad del script; prueba de privilegios; bitácora con antes y después | Bloques R, S, Z, AB, AD y AG en verde |
| 2 | 06/11 | Integridad y datos: D2 (etapa fija), D4 con ámbito, D7, D11 (padrón mínimo, correo obligatorio, también en el panel), D12 (listas, marca de grupo, CSV con registro), importar padrón; vaciar datos de prueba e importar actividades (R-44, R-45); generador con `--esquema v55` | Bloques T, U, V, AA, AC, AE, AH, AI, AJ y AK en verde; los 163 anteriores también |
| 3 | 07/11 | Proyecto real: Supabase de prueba y de producción, Auth con código, cuenta del propietario, datos reales cargados desde el panel con los pasos de la sección 19.7, tester desde GitHub, flujo "Mantener Supabase activo", confirmar la cabecera de IP | Tester completo en verde contra Supabase; flujo de mantener activo en verde |
| 4 | 08/11 | Carga y operación: D3, D6, D10 (ventanas sostenidas), D14, D17 (respaldo y `restaurar.py`), pasar a producción, retroceso exponencial; 1000 personas; simulacro de restauración | Bloques W, X, Y y AF en verde; P95 anotado |
| 5 | 09/11 y 10/11 | Diseño de autor sobre `base.css`; equipo invitado con sus roles; ensayo con diez personas, cierre en medio y un cambio por soporte | Tester de navegador en verde y ensayo sin incidencias |
| 6 | 09/11 a 11/11 | Fase 1 (09/11): migraciones 11 y 12, panel y prueba de ataque en PRUEBA; migraciones 10 a 12 y la cuenta del propietario en PRODUCCIÓN. Fase 2 (10/11, después del ensayo y antes del congelamiento de las 20:00): `config.js` → PRODUCCIÓN y cuentas. Fase 3 (11/11): datos reales, respaldo, Pasar a producción, respaldo, tester en lectura y apertura de la Etapa 1 a las 20:00 (`sprints/sprint-6/GUIA.md`) | Tester en modo lectura en verde |

Estado al 07/11: sprints 1 a 4 cerrados. Sprint 5 y 5.1 aplicados en PRUEBA (5.5-s5.1; local 383/383, PC 350/350 sin avisos, GitHub 302/302). Sprint 6 entregado: migraciones 11 y 12, `config.js` hacia PRODUCCIÓN con comprobación, prueba de ataque, "Copiar mensaje" y guía de la apertura. PRODUCCIÓN sigue en 5.5-s4.1, vacía y cerrada: recibe las migraciones 10 a 12 en la Fase 1 del Sprint 6 (09/11), antes del congelamiento (10/11, 20:00).

## 24. Decisiones abiertas

Las decisiones del contrato están en la sección 2. Quedan abiertas, sin afectar el contrato:

| Decisión | Estado | Nota |
|---|---|---|
| Actividades por persona | **Decidida (06/11)** | Siempre 2 |
| Combinar el mismo día durante el congreso | **Decidida (06/11)** | Apagado por defecto; el propietario puede encenderlo desde Actividades → horarios |
| Margen de traslado | **Decidida (06/11)** | 30 minutos, ajustable por el propietario desde el mismo lugar (solo cuenta con el mismo día encendido) |
| Permitir 2 talleres aunque queden visitas | **Decidida (08/11): encendido en PRODUCCIÓN** | Las visitas son un privilegio, no una obligación: quien puede elegir visitas también puede llevar 2 talleres. Se enciende desde Operación al cargar los datos; "Pasar a producción" no cambia la configuración |
| Aviso de ampliaciones | **Recomendación: no construirlo** | Solo admin y propietario cambian cupos, cada cambio queda en la bitácora y el panel ya muestra "ampliada desde N" en cada actividad. Con 3 personas que pueden ampliar, una alerta automática agrega poco |
| Límites de intentos | **Decidida (07/11)** | 4 por dispositivo y 300 por red, en ventanas fijas de 10 minutos; el propietario los cambia desde Operación → Redes con intentos fallidos. Con el Wi-Fi de la UCSM (una IP por pabellón), la tarjeta avisa al 80 % para subirlo antes de que se frene |
| Umbral de saturación | **Decidida (06/11)** | 2000 llamadas por ventana de 10 s, sostenidas 3 ventanas; sin campo en el panel. Medido: pico de 2342 en una ventana con 1000 personas, sin alerta |
| Dominio del correo | **Decidida (07/11): no restringir** | El congreso es internacional y de estudiantes de varias universidades: restringir a un dominio (`@ucsm.edu.pe`) dejaría fuera a los demás. La página pide "Correo institucional" con el ejemplo `nombre.apellido@estudiante.ucsm.edu.pe` [Sprint 6.2], pero acepta cualquier correo con formato válido (los extranjeros y los de otras universidades usan el suyo) |
| Texto final del aviso de privacidad | **Listo (07/11, Sprint 5.1)** | Sección 11.3, con portabilidad, flujo transfronterizo, la IP usada solo para el límite de 10 minutos y borrada al terminar su ventana, y GitHub Pages; confirmar con lo legal de la UCSM los puntos que ahí se listan |
| Security Advisor de Supabase (PRODUCCIÓN, 08/11) | **Revisado y aceptado; no se cambia nada** [Sprint 6.2] | 0 errores. "RLS Enabled No Policy" (17): intencional, las tablas solo se alcanzan por `public.api` (ataque: tablas 12/12). "Function Search Path Mutable" (128): no explotables; la única función SECURITY DEFINER es `public.api`, con `search_path` fijo, y las de `privado` son INVOKER, sin permisos para `anon` ni `authenticated`; cambiarlas antes de abrir sería riesgo sin beneficio. "Public / Signed-In Users Can Execute SECURITY DEFINER Function" sobre `public.api`: es la única puerta y revisa rol, cuenta activa y `aal2` (ataque: panel 9/9). "Leaked Password Protection Disabled": solo en el plan Pro; mitigado con TOTP obligatorio, registro apagado y `aal2`. Se puso el largo mínimo de contraseña en 12 en Auth |
| Código de entrada como segundo dato | Abierta | Hoy no existe (D15); si aparece, se agrega al padrón |
| Invitar desde el panel (Edge Function) | Opcional | Hoy se invita desde Supabase |

## 25. Ventana al sistema de asistencia

El Panel 4 se construirá después. El modelo de la v5.1 ya lo admite sin cambios de estructura:

| Pieza | Cómo encaja |
|---|---|
| `inscripcion_actividades` | Una fila por persona y actividad: es lo que se marca como asistido |
| `asistencias` | Tabla reservada (sección 15.8) |
| Código del comprobante | Puede mostrarse como QR en la pantalla 3 para marcar llegada |
| `tipos_actividad` | Conferencias, cursos u otros tipos entran como filas nuevas con su máximo por persona |
| Roles | Se puede agregar un rol "puerta" que solo marque asistencia |
| Bitácora | Registra quién marcó cada llegada |

Lo que el Panel 4 deberá definir en su propia lámina: dónde se marca (puerta de cada actividad o punto central), con qué (DNI, QR o ambos), qué pasa con quien no está inscrito en esa actividad, si las inasistencias liberan cupo para la siguiente actividad y qué reportes necesita la organización (asistencia por actividad, certificados).

---

## 26. Glosario

| Término | Significado |
|---|---|
| Actividad | Visita técnica o taller con día, horario y cupo |
| Advertencia | Respuesta que no escribe nada y pide confirmar una decisión con consecuencias |
| Anular | Pasar una inscripción a ANULADO y liberar sus cupos |
| Cambiar inscripción | Reemplazar las actividades de una inscripción en un paso, conservando el código |
| Congelamiento | Periodo en que no se corre SQL en producción; todo se hace desde el panel [v5.4] |
| Operación masiva | `DELETE` o `UPDATE` de más de 10 filas, o `TRUNCATE`: R-40 la bloquea salvo permiso explícito [v5.4] |
| Avisar y cerrar | Programar el cierre con cuenta regresiva en las páginas |
| Cerrar y depurar | Cerrar las inscripciones esperando a las que están en curso y subir la ronda |
| Entrega del grupo | ENLACE (botón en el comprobante) o MANUAL (la organización agrega a la persona) |
| Cruce | Dos actividades del mismo día sin el margen de traslado entre ellas |
| Dispositivo | Identificador al azar que la página guarda en el navegador |
| Etapa | Etapa de venta de la entrada: 1, 2 o 3 |
| Confirmación | Pantalla que se muestra una sola vez al inscribirse, con los botones de grupo; no se puede volver a pedir [v5.2] |
| Incidencia | Número que identifica un error interno; el detalle lo ve el admin [v5.2] |
| Integridad | Que cada contador de inscritos coincida con sus inscripciones confirmadas [v5.2] |
| Lista por actividad | Participantes de una visita o taller con todos sus datos, ordenados por apellidos [v5.3] |
| Nivel | Importancia de una acción: 1 consulta, 2 modificaciones, 3 habilitan el sistema [v5.3] |
| Ventana | 10 segundos de tráfico; la alerta exige 3 seguidas sobre el umbral [v5.3] |
| Llave | ID de la actividad que el organizador escribe para confirmar una ampliación de cupo |
| Propietario | Rol que administra el equipo; normalmente tú |
| Base ficticia | Datos inventados para diseñar y probar; se reemplazan por los reales desde el panel (sección 19.7) [v5.5] |
| Respaldo | Archivo JSON con todas las tablas de datos, descargado desde el panel [v5.4] |
| RPO | Cuántos datos se pueden perder: el tiempo entre el último respaldo y un desastre [v5.4] |
| RTO | Cuánto tiempo puede estar el sistema fuera de servicio mientras se restaura [v5.4] |
| Margen | Minutos mínimos entre dos actividades del mismo día |
| Origen | WEB (página) o PANEL (equipo), en inscripciones y padrón |
| Padrón | Lista de documentos con entrada, por etapa |
| Red | Dirección IP desde la que llega el pedido |
| Solicitud | Identificador al azar de cada escritura; su reenvío recibe la misma respuesta [v5.2] |
| Ronda | Contador que sube en cada cierre; invalida las páginas abiertas antes |
| Requiere cierre | Respuesta a un cambio que quita opciones con el sistema abierto |
