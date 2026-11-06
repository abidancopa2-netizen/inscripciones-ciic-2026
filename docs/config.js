/*  ─────────────────────────────────────────────────────────────────────
 *  CONFIGURACIÓN · lo único que editas en la página y en el panel.
 *  MODO: 'real' → funciona sin Supabase, con datos de prueba en este navegador (para diseñar).
 *        'real' → usa Supabase: pega API_URL y ANON_KEY.
 *  Supabase → tu proyecto → Project Settings → API (o el botón "Connect"):
 *    API_URL  = la "Project URL", por ejemplo https://abcdefghijkl.supabase.co
 *    ANON_KEY = la clave pública "anon" (eyJ…) o "publishable" (sb_publishable_…).
 *    Es pública por diseño. NUNCA pegues la service_role ni la secret.
 *  ───────────────────────────────────────────────────────────────────── */
window.CIIC_CONFIG = {
  MODO: 'demo',
  API_URL: 'https://hbnrhrmndadciornanbx.supabase.co',
  ANON_KEY: 'sb_publishable_it4qsCUK2UeX5Q5sU5WVzw_mOnF-gBW',
  NOMBRE_EVENTO: 'Congreso Internacional de Ingeniería Civil 2026',
  CONTACTO: '',   // opcional: correo o WhatsApp de informes, p. ej. 'visitas@congreso.pe'
  // Texto completo del aviso de privacidad (sección 11.3 de la documentación). Completa los corchetes.
  AVISO_PRIVACIDAD:
    'Aviso de privacidad · Inscripción a visitas técnicas y talleres del [nombre del congreso]\n\n' +
    '[Nombre de la universidad u organización], con RUC [número] y domicilio en [dirección], es responsable de los datos personales que registras en este formulario: ' +
    'documento de identidad, nombres, apellidos, correo institucional y número de celular.\n\n' +
    'Usamos tus datos para: (1) gestionar tu inscripción a visitas técnicas y talleres; (2) coordinar contigo por WhatsApp los detalles de tus actividades; ' +
    '(3) registrar tu asistencia; y (4) enviarte por correo información del evento.\n\n' +
    'Solo el equipo organizador accede a tus datos, con cuentas individuales; los encargados de cada visita o taller reciben únicamente la lista de su actividad. ' +
    'No los vendemos ni los compartimos con terceros para otros fines. Los conservaremos hasta 90 días después del congreso y luego los eliminaremos.\n\n' +
    'Puedes ejercer tus derechos de acceso, rectificación, cancelación y oposición escribiendo a [correo de contacto]. Este aviso se rige por la Ley N.º 29733 y su reglamento.',
  // Modo real: versión fija de supabase-js y su hash de integridad SRI (sección 18). Verificado el 04/11/2026 en jsDelivr y unpkg.
  // Archivo real del paquete (no el .min.js que jsDelivr genera al vuelo) y su huella: si el CDN lo cambia, el navegador no lo ejecuta.
  SUPABASE_JS: 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.45.4/dist/umd/supabase.js',
  SUPABASE_JS_SRI: 'sha384-0w2KAL2YHP6wKOkUDzkCDGgVvfmHnj02DHeQ6XcHOgTfFsGyonKOpShMH1x6nk9o',
};
