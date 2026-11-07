/*  ─────────────────────────────────────────────────────────────────────
 *  CONFIGURACIÓN · lo único que editas en la página y en el panel.
 *  MODO: 'demo' → funciona sin Supabase, con datos de prueba en este navegador (para diseñar).
 *        'real' → usa Supabase: pega API_URL y ANON_KEY.
 *  Supabase → tu proyecto → Project Settings → API (o el botón "Connect"):
 *    API_URL  = la "Project URL", por ejemplo https://abcdefghijkl.supabase.co
 *    ANON_KEY = la clave pública "anon" (eyJ…) o "publishable" (sb_publishable_…).
 *    Es pública por diseño. NUNCA pegues la service_role ni la secret.
 *  ───────────────────────────────────────────────────────────────────── */
window.CIIC_CONFIG = {
  MODO: 'real',
  API_URL: 'https://hbnrhrmndadciornanbx.supabase.co',
  ANON_KEY: 'sb_publishable_it4qsCUK2UeX5Q5sU5WVzw_mOnF-gBW',
  NOMBRE_EVENTO: "VII Congreso Internacional de Estudiantes de Ingeniería Civil · CIDEIC",
  CONTACTO: "+51 927 457 291 (WhatsApp)",   // opcional: correo o WhatsApp de informes, p. ej. 'visitas@congreso.pe'
  // Texto completo del aviso de privacidad (sección 11.3 de la documentación). Completa los corchetes.
  AVISO_PRIVACIDAD:
    "Aviso de privacidad · Inscripción a visitas técnicas y talleres del VII Congreso Internacional de Estudiantes de Ingeniería Civil (CIDEIC)\n\n" +
    "Responsable. La Universidad Católica de Santa María (UCSM), con RUC 20141637941 y domicilio en Urb. San José s/n, Umacollo, Arequipa, es responsable del tratamiento de los datos personales que registras en este formulario. Se guardan en el banco de datos de inscripciones del congreso, a cargo de la UCSM.\n\n" +
    "Qué datos y para qué. Registramos tu documento de identidad, nombres, apellidos, correo institucional, país, número de celular y las actividades que eliges. Los usamos para: (1) gestionar tu inscripción a visitas técnicas y talleres; (2) coordinar contigo por WhatsApp los detalles de tus actividades; (3) registrar tu asistencia; y (4) enviarte por correo solo avisos importantes sobre tu inscripción (cambios de fecha, hora o lugar, o cancelación de una actividad), cuando no podamos comunicarlo por WhatsApp. Todos los datos del formulario son obligatorios: sin ellos no podemos inscribirte. Para proteger el formulario de abusos guardamos por unos minutos datos técnicos de tu conexión, como la dirección IP. No tomamos decisiones automatizadas ni elaboramos perfiles: los cupos se asignan por orden de inscripción.\n\n" +
    "Quién accede. Solo el equipo organizador, con cuentas individuales; los encargados de cada visita o taller reciben únicamente la lista de su actividad. No vendemos tus datos ni los compartimos con terceros para otros fines. Si te unes al grupo de WhatsApp de tu actividad, sus demás integrantes verán tu número.\n\n" +
    "Dónde se guardan. En los servidores de Supabase (Supabase, Inc.), el proveedor de la plataforma, ubicados fuera del Perú. Supabase solo los guarda por encargo nuestro; es una transferencia internacional (flujo transfronterizo) de datos.\n\n" +
    "Cuánto tiempo. Hasta 90 días después del congreso; luego los eliminamos.\n\n" +
    "Tus derechos. Puedes ejercer tus derechos de información, acceso, rectificación, cancelación, oposición y portabilidad (recibir tus datos en un formato estructurado, de uso común y lectura mecánica) escribiendo a logisticacideic@gmail.com. Si consideras que no atendimos tu solicitud, puedes acudir a la Autoridad Nacional de Protección de Datos Personales del Ministerio de Justicia y Derechos Humanos. Este aviso se rige por la Ley N.º 29733, Ley de Protección de Datos Personales, y su reglamento, aprobado por el Decreto Supremo N.º 016-2024-JUS.",
  // Modo real: versión fija de supabase-js y su hash de integridad SRI (sección 18). Verificado el 04/11/2026 en jsDelivr y unpkg.
  // Archivo real del paquete (no el .min.js que jsDelivr genera al vuelo) y su huella: si el CDN lo cambia, el navegador no lo ejecuta.
  SUPABASE_JS: 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.45.4/dist/umd/supabase.js',
  SUPABASE_JS_SRI: 'sha384-0w2KAL2YHP6wKOkUDzkCDGgVvfmHnj02DHeQ6XcHOgTfFsGyonKOpShMH1x6nk9o',
};
