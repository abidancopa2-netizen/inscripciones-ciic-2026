#!/usr/bin/env python3
"""
════════════════════════════════════════════════════════════════════════
  GALERÍAS DE PANTALLAS · para el diseño de autor · contrato v5.5
  Abre index.html y panel.html en modo demo con un navegador automático,
  lleva cada pantalla a cada uno de sus estados (espera, error, cerrado,
  confirmación, ventanas, avisos…) y guarda una copia exacta de su HTML.

  Salida (en docs/diseno/):
    index.html                    portada
    pantallas-participante.html   todos los estados de la página del participante (390 px y 1024 px)
    pantallas-panel.html          todos los estados del panel (1280 px y algunos a 390 px)

  Cada estado va en su propio marco y usa ../base.css: edita base.css,
  recarga la galería y ves el cambio en todas las pantallas a la vez.
  Si cambias la ESTRUCTURA del HTML de las páginas, vuelve a correr esto:
      pip install playwright && python -m playwright install chromium
      python local/generar_galeria.py
════════════════════════════════════════════════════════════════════════
"""
import asyncio
import html
from pathlib import Path

from playwright.async_api import async_playwright

RAIZ = Path(__file__).resolve().parent.parent
DOCS = RAIZ / 'docs'
SALIDA = DOCS / 'diseno'
URL = DOCS.as_uri() + '/'
QR = ('data:image/svg+xml;utf8,' + html.escape('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 29 29"><rect width="29" height="29" fill="#fff"/>'
      '<path d="M1 1h7v7H1zM21 1h7v7h-7zM1 21h7v7H1zM3 3v3h3V3zM23 3v3h3V3zM3 23v3h3v-3zM10 2h2v2h-2zM13 4h2v3h-2zM10 9h3v2h-3zM15 10h4v2h-4zM20 12h3v2h-3z'
      'M9 14h2v4H9zM13 15h3v3h-3zM17 17h4v2h-4zM23 16h4v3h-4zM10 21h3v3h-3zM15 22h2v5h-2zM19 21h3v2h-3zM22 25h5v2h-5z" fill="#111"/></svg>'))

# Lo que se quita de cada copia: scripts y la cinta del modo demo (no forma parte del diseño).
COPIAR = """() => {
  // lo escrito por el usuario vive en propiedades, no en atributos: se pasa a atributos para que la copia lo muestre
  document.querySelectorAll('input').forEach((i) => { if (i.type === 'checkbox' || i.type === 'radio') i.toggleAttribute('checked', i.checked); else if (i.type !== 'file') i.setAttribute('value', i.value); });
  document.querySelectorAll('textarea').forEach((t) => { t.textContent = t.value; });
  document.querySelectorAll('select').forEach((s) => [...s.options].forEach((o) => o.toggleAttribute('selected', o.selected)));
  const b = document.body.cloneNode(true);
  b.querySelectorAll('script, [data-demo]').forEach((x) => x.remove());
  b.querySelectorAll('dialog[open]').forEach((d) => d.setAttribute('data-congelado', ''));
  const d = document.querySelector('dialog[open]'), extra = d ? d.offsetHeight + 90 : 0;
  const av = document.getElementById('avisos'), extraAv = av && av.children.length ? av.offsetHeight + 30 : 0;
  const fondo = Math.max(...[...document.body.children].filter((e) => e.offsetParent !== null || e.tagName === 'MAIN').map((e) => e.getBoundingClientRect().bottom + scrollY));
  return { html: b.innerHTML, alto: Math.ceil(fondo) + 24 + extra + extraAv };
}"""
UUID = "crypto.randomUUID()"


async def api(pg, accion, extra=''):
    return await pg.evaluate("window.CIIC_DEMO.api(Object.assign({action:'%s', solicitud:%s}, %s), {sesion:'u-tu'})" % (accion, UUID, extra or '{}'))


def mensaje(caja, tipo, estilo, texto):
    return "document.getElementById('%s').innerHTML = %r" % (caja, '<div class="mensaje" data-tipo="%s" data-estilo="%s" role="alert">%s</div>' % (tipo, estilo, html.escape(texto)))


class Galeria:
    def __init__(self, titulo):
        self.titulo, self.estados = titulo, []

    async def copiar(self, pg, grupo, nombre, nota, ancho):
        await pg.wait_for_timeout(250)
        c = await pg.evaluate(COPIAR)
        self.estados.append((grupo, nombre, nota, ancho, c['html'], c['alto']))
        print('  ·', grupo, '·', nombre)

    def escribir(self, archivo, intro):
        marcos, indice, grupo_actual = [], [], None
        for k, (grupo, nombre, nota, ancho, cuerpo, alto) in enumerate(self.estados):
            if grupo != grupo_actual:
                marcos.append('<h2 class="g-grupo" id="g%d">%s</h2>' % (k, html.escape(grupo)))
                indice.append('<li><a href="#g%d">%s</a></li>' % (k, html.escape(grupo)))
                grupo_actual = grupo
            doc = ('<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
                   '<link rel="stylesheet" href="../base.css"><style>'
                   'dialog[data-congelado]{position:relative;display:block;margin:28px auto;inset:auto}'
                   'body:has(dialog[data-congelado])::before{content:"";position:fixed;inset:0;background:rgba(10,15,25,.45)}'
                   '.avisos{position:static;margin:12px auto;max-width:420px}</style></head><body>' + cuerpo + '</body></html>')
            marcos.append('<figure class="g-estado" id="e%d"><figcaption><b>%s</b><span>%s</span><em>%d px</em></figcaption>'
                          '<div class="g-marco" style="width:%dpx"><iframe title="%s" loading="lazy" width="%d" height="%d" srcdoc="%s"></iframe></div></figure>' % (
                              k, html.escape(nombre), html.escape(nota), ancho, ancho, html.escape(nombre), ancho, min(alto + 4, 2600), html.escape(doc, quote=True)))
        pagina = '''<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s · galería de pantallas</title>
<style>
  body { margin: 0; font: 15px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; background: #e9ecf2; color: #1b2333; }
  .g-cabeza { padding: 22px 28px; background: #1b2333; color: #fff; }
  .g-cabeza h1 { margin: 0 0 6px; font-size: 1.4rem; }
  .g-cabeza p { margin: 4px 0; max-width: 980px; opacity: .85; }
  .g-cabeza a { color: #9cc0ff; }
  .g-indice { display: flex; flex-wrap: wrap; gap: 6px 18px; list-style: none; padding: 0; margin: 12px 0 0; }
  main { padding: 10px 28px 60px; }
  .g-grupo { margin: 34px 0 8px; font-size: 1.15rem; border-bottom: 2px solid #c6ccd8; padding-bottom: 6px; }
  .g-fila { display: flex; flex-wrap: wrap; gap: 22px; align-items: flex-start; }
  .g-estado { margin: 0; }
  .g-estado figcaption { display: flex; flex-direction: column; max-width: 390px; margin-bottom: 6px; font-size: .85rem; }
  .g-estado figcaption span { color: #4b5567; } .g-estado figcaption em { color: #7b8597; font-style: normal; font-size: .75rem; }
  .g-marco { border: 1px solid #c6ccd8; border-radius: 10px; overflow: hidden; background: #fff; box-shadow: 0 2px 10px rgba(20,30,50,.08); max-width: calc(100vw - 60px); overflow-x: auto; }
  .g-marco iframe { display: block; border: 0; }
</style></head><body>
<header class="g-cabeza"><h1>%s · galería de pantallas</h1>%s<ol class="g-indice">%s</ol></header>
<main>%s</main>
</body></html>''' % (html.escape(self.titulo), html.escape(self.titulo), intro, ''.join(indice), self._en_filas(marcos))
        (SALIDA / archivo).write_text(pagina, encoding='utf-8')

    @staticmethod
    def _en_filas(marcos):
        out, fila = [], []
        for m in marcos:
            if m.startswith('<h2'):
                if fila:
                    out.append('<div class="g-fila">' + ''.join(fila) + '</div>'); fila = []
                out.append(m)
            else:
                fila.append(m)
        if fila:
            out.append('<div class="g-fila">' + ''.join(fila) + '</div>')
        return '\n'.join(out)


async def pagina_nueva(nav, archivo, ancho, alto=900):
    ctx = await nav.new_context(viewport={'width': ancho, 'height': alto})
    pg = await ctx.new_page()
    await pg.goto(URL + archivo)
    await pg.wait_for_timeout(500)
    await pg.evaluate('window.CIIC_DEMO.reiniciar()')
    await pg.reload()
    await pg.wait_for_timeout(700)
    return ctx, pg


async def verificar(pg, doc):
    await pg.fill('#doc', doc)
    await pg.click('#btn-verificar')
    await pg.wait_for_timeout(700)


async def participante(nav):
    g = Galeria('Página del participante')
    for ancho in (390, 1024):
        etiqueta = 'celular' if ancho == 390 else 'computadora'
        ctx, pg = await pagina_nueva(nav, 'index.html', ancho)
        G1 = 'Pantalla 1 · documento (%s)' % etiqueta
        await g.copiar(pg, G1, 'Inicio', 'Lista para escribir', ancho)
        await pg.fill('#doc', '04567812')
        await pg.evaluate("const b=document.getElementById('btn-verificar'); b.disabled=true; b.textContent='Verificando…'")
        await g.copiar(pg, G1, 'Verificando', 'Espera corta: botón ocupado', ancho)
        await pg.evaluate(mensaje('msg-1', 'espera', 'aviso', 'Estás en la fila: hay mucha demanda. Seguimos intentando; no recargues la página.'))
        await g.copiar(pg, G1, 'En la fila', 'Espera larga: reintentos automáticos (tipo ocupado)', ancho)
        await pg.reload(); await pg.wait_for_timeout(600)
        await verificar(pg, '12 3'); await g.copiar(pg, G1, 'Formato inválido', 'tipo formato', ancho)
        await verificar(pg, '99999999'); await g.copiar(pg, G1, 'No está en el padrón', 'tipo no_encontrado · intentos restantes', ancho)
        for _ in range(4):
            await verificar(pg, '99999998')
        await g.copiar(pg, G1, 'Demasiados intentos', 'tipo demasiados_intentos · botón bloqueado', ancho)
        await pg.evaluate('window.CIIC_DEMO.reiniciar()'); await pg.reload(); await pg.wait_for_timeout(600)
        await verificar(pg, '78695681'); await g.copiar(pg, G1, 'Ya inscrito', 'tipo duplicado · sin datos', ancho)
        await verificar(pg, '42048123'); await g.copiar(pg, G1, 'Etapa no habilitada', 'tipo etapa_no_habilitada', ancho)
        await pg.evaluate(mensaje('msg-1', 'error_servidor', 'error', 'Ocurrió un error en el sistema. Intenta de nuevo en unos segundos. (Incidencia INC-0007)'))
        await g.copiar(pg, G1, 'Error del sistema', 'tipo error_servidor · con número de incidencia', ancho)
        await api(pg, 'panel_config', '{avisarCierreMin: 2}')
        await pg.evaluate('document.dispatchEvent(new Event("visibilitychange"))'); await pg.wait_for_timeout(1300)
        await g.copiar(pg, G1, 'Aviso de cierre', 'Franja con cuenta regresiva (cierraEn)', ancho)
        await api(pg, 'panel_config', '{abierto: false, confirmar: true}')
        await pg.evaluate('document.dispatchEvent(new Event("visibilitychange"))'); await pg.wait_for_timeout(900)
        await g.copiar(pg, G1, 'Inscripciones cerradas', 'tipo cerrado · se actualiza sola', ancho)
        await api(pg, 'panel_config', '{abierto: true}')
        await pg.evaluate('document.dispatchEvent(new Event("visibilitychange"))'); await pg.wait_for_timeout(700)
        await verificar(pg, '04567812')
        await api(pg, 'panel_config', '{abierto: false, confirmar: true}'); await api(pg, 'panel_config', '{abierto: true}')
        await pg.evaluate('document.dispatchEvent(new Event("visibilitychange"))'); await pg.wait_for_timeout(900)
        await g.copiar(pg, G1, 'El sistema se actualizó', 'tipo recargar · vuelve con el documento puesto', ancho)
        await ctx.set_offline(True); await pg.wait_for_timeout(1300)
        await pg.click('#btn-verificar'); await pg.wait_for_timeout(500)
        await g.copiar(pg, G1, 'Sin conexión', 'Franja gris · nada se envía', ancho)
        await ctx.set_offline(False); await ctx.close()

        ctx, pg = await pagina_nueva(nav, 'index.html', ancho, 1400)
        G2 = 'Pantalla 2 · elección y datos (%s)' % etiqueta
        await verificar(pg, '04567812'); await g.copiar(pg, G2, 'Elegir (Etapa 1)', 'Visitas y talleres; llenas bloqueadas', ancho)
        await pg.click('[data-actividad="VIS01"]'); await pg.click('[data-actividad="TAL07"]')
        for k, v in (('#nombres', 'Ana Lucía'), ('#apellidos', 'Torres Ríos'), ('#correo', 'ana.torres@uni.edu.pe'), ('#celular', '987 654 321')):
            await pg.fill(k, v)
        await pg.check('#acepta')
        await g.copiar(pg, G2, 'Dos elegidas y datos completos', 'aria-pressed="true"', ancho)
        await pg.fill('#correo', ''); await pg.click('#btn-confirmar'); await pg.wait_for_timeout(500)
        await g.copiar(pg, G2, 'Dato que falta', 'tipo datos_invalidos', ancho)
        await pg.fill('#correo', 'ana.torres@uni.edu.pe')
        await pg.evaluate(mensaje('msg-2', 'lleno', 'aviso', '"Planta de tratamiento de agua potable La Atarjea" se acaba de llenar. Elige otra combinación, por favor.'))
        await g.copiar(pg, G2, 'Se llenó al confirmar', 'tipo lleno · lista actualizada', ancho)
        await pg.evaluate("const b=document.getElementById('btn-confirmar'); b.disabled=true; b.textContent='Confirmando…'")
        await pg.evaluate(mensaje('msg-2', 'espera', 'aviso', 'Estás en la fila: hay mucha demanda. Seguimos intentando; no recargues ni cierres la página.'))
        await g.copiar(pg, G2, 'Confirmando · en la fila', 'Espera larga al confirmar', ancho)
        await pg.click('#btn-aviso'); await pg.wait_for_timeout(300)
        await g.copiar(pg, G2, 'Aviso de privacidad', 'Ventana (dialog) con el texto de config.js', ancho)
        await ctx.close()
        ctx, pg = await pagina_nueva(nav, 'index.html', ancho, 1400)
        await verificar(pg, '001234567'); await g.copiar(pg, G2, 'Etapa 2: solo talleres', 'Visitas bloqueadas: "Solo Etapa 1"', ancho)
        await pg.click('#btn-volver')
        await api(pg, 'panel_horarios', '{mismoDia: true}')
        await verificar(pg, '04567812'); await pg.click('[data-actividad="VIS05"]')
        await g.copiar(pg, G2, 'Mismo día con cruces', 'Aviso informativo y "Se cruza con VIS05"', ancho)
        await ctx.close()

        ctx, pg = await pagina_nueva(nav, 'index.html', ancho, 1200)
        G3 = 'Pantalla 3 · confirmación (%s)' % etiqueta
        async def inscribir(doc, a, b):
            await verificar(pg, doc); await pg.click('[data-actividad="%s"]' % a); await pg.click('[data-actividad="%s"]' % b)
            for k, v in (('#nombres', 'Lucía'), ('#apellidos', 'Quispe Rojas'), ('#correo', 'lucia.quispe@uni.edu.pe'), ('#celular', '912345678')):
                await pg.fill(k, v)
            await pg.check('#acepta'); await pg.click('#btn-confirmar'); await pg.wait_for_timeout(900)
        await inscribir('04567812', 'VIS01', 'TAL07')
        await g.copiar(pg, G3, 'Confirmada con enlaces', 'Se muestra una sola vez; sin código', ancho)
        await pg.click('#btn-inicio'); await pg.wait_for_timeout(300)
        await inscribir('4123456', 'TAL02', 'VIS11')
        await g.copiar(pg, G3, 'Entrega a mano', 'data-grupo="manual": muestra el número con el que se le agregará', ancho)
        await pg.click('#btn-inicio'); await pg.wait_for_timeout(300)
        await inscribir('12345678K', 'VIS02', 'TAL10')
        await g.copiar(pg, G3, 'Grupo aún sin enlace', 'data-grupo="pendiente"', ancho)
        await ctx.close()
    g.escribir('pantallas-participante.html', '<p>Cada marco es una copia exacta de <code>index.html</code> en un estado. Edita <code>../base.css</code> y recarga esta página: el cambio se ve en todas. <a href="index.html">Volver a la portada</a></p>')


async def panel(nav):
    g = Galeria('Panel de organización')
    A = 1280
    ctx, pg = await pagina_nueva(nav, 'panel.html', A)
    GL = 'Acceso'
    await g.copiar(pg, GL, 'Entrada en modo demo', 'Elegir cuenta de prueba (solo demo)', A)
    await pg.evaluate("for (const [id, v] of [['paso-demo', true], ['paso-clave', false], ['paso-prueba', false]]) document.getElementById(id).hidden = v")
    await g.copiar(pg, GL, 'Iniciar sesión', 'Correo y contraseña (modo real)', A)
    await pg.evaluate(mensaje('msg-login', 'no_autorizado', 'error', 'Correo o contraseña incorrectos.'))
    await g.copiar(pg, GL, 'Contraseña incorrecta', 'msg-login', A)
    await pg.evaluate("document.getElementById('msg-login').innerHTML=''; document.getElementById('form-prueba').hidden=false")
    await g.copiar(pg, GL, 'Clave de prueba', 'Solo con la base en modo PRUEBA', A)
    await pg.evaluate("document.getElementById('form-prueba').hidden=true; document.getElementById('paso-clave').hidden=true; document.getElementById('paso-codigo').hidden=false;"
                      "document.getElementById('alta-totp').hidden=false; document.getElementById('t-codigo').textContent='Registra tu app de verificación';"
                      "document.getElementById('qr').src=%r; document.getElementById('secreto').textContent='JBSW Y3DP EHPK 3PXP'" % QR)
    await g.copiar(pg, GL, 'Primera vez: registrar el código', 'QR de la app de verificación (TOTP)', A)
    await pg.evaluate("document.getElementById('alta-totp').hidden=true; document.getElementById('t-codigo').textContent='Código de verificación'")
    await g.copiar(pg, GL, 'Código de verificación', 'Cada inicio de sesión', A)
    await pg.evaluate("document.getElementById('paso-codigo').hidden=true; document.getElementById('paso-nueva').hidden=false")
    await g.copiar(pg, GL, 'Crear contraseña', 'Invitación o recuperación', A)
    await ctx.close()

    async def entrar(cuenta, alto=1600, ancho=A):
        c, p = await pagina_nueva(nav, 'panel.html', ancho, alto)
        await p.click('#cuentas-demo button:has-text("%s")' % cuenta); await p.wait_for_timeout(1000)
        return c, p
    GO = 'Operación'
    ctx, pg = await entrar('Tú')
    await g.copiar(pg, GO, 'Propietario · abierto', 'Vista completa', A)
    await api(pg, 'panel_config', '{avisarCierreMin: 5}')
    await pg.evaluate('document.dispatchEvent(new Event("visibilitychange"))'); await pg.wait_for_timeout(1200)
    await g.copiar(pg, GO, 'Aviso de cierre en curso', 'Cuenta regresiva en la franja y en el estado', A)
    await pg.evaluate("const f=document.getElementById('estado-sis'); f.dataset.alerta='si'; f.textContent='⚠ SATURACIÓN SOSTENIDA: más de 2000 llamadas por ventana de 10 s durante 30 s · ABIERTO · ronda 1';"
                      "document.getElementById('integridad').firstChild.dataset.estilo='error'; document.getElementById('integridad').firstChild.textContent='Integridad: descuadre en VIS04, TAL01.'")
    await g.copiar(pg, GO, 'Alerta de saturación e integridad rota', 'franja[data-alerta="si"] · mensaje de error', A)
    await api(pg, 'panel_config', '{abierto: false, confirmar: true}')
    await pg.evaluate('document.dispatchEvent(new Event("visibilitychange"))'); await pg.wait_for_timeout(1200)
    await g.copiar(pg, GO, 'Cerrado', 'franja[data-estado="cerrado"]', A)
    await api(pg, 'panel_config', '{abierto: true}')
    await pg.evaluate('document.dispatchEvent(new Event("visibilitychange"))'); await pg.wait_for_timeout(900)
    await pg.fill('#q', '78695681'); await pg.click('#btn-buscar'); await pg.wait_for_timeout(600)
    await pg.click('#res-buscar button:has-text("Cambiar inscripción")'); await pg.wait_for_timeout(300)
    await g.copiar(pg, GO, 'Buscar · cambiar inscripción', 'Resultado con el cambio desplegado', A)
    await pg.click('#btn-cerrar'); await pg.wait_for_timeout(500)
    await g.copiar(pg, GO, 'Ventana de advertencia', 'Cerrar ahora: confirmación', A)
    await pg.click('#m-cancelar')
    for k, v in (('#i-doc', '04567812'), ('#i-nombres', 'Ana'), ('#i-apellidos', 'Torres Ríos'), ('#i-correo', 'ana@uni.edu.pe'), ('#i-cel', '987654321')):
        await pg.fill(k, v)
    await pg.select_option('#i-a1', 'VIS03'); await pg.select_option('#i-a2', 'TAL07'); await pg.check('#i-ok')
    await pg.click('#btn-inscribir'); await pg.wait_for_timeout(700)
    await g.copiar(pg, GO, 'Ventana con llave', 'Ampliar cupo: escribir el ID para confirmar', A)
    await pg.click('#m-cancelar')
    await pg.evaluate("document.getElementById('avisos').innerHTML = %r" % (
        '<div class="mensaje" data-tipo="panel" data-estilo="exito" role="status">VIS01: cupo 30.</div>'
        '<div class="mensaje" data-tipo="requiere_cierre" data-estilo="aviso" role="status">Este cambio quita opciones a quien está eligiendo. Cierra las inscripciones, haz el cambio y vuelve a abrir.</div>'
        '<div class="mensaje" data-tipo="sin_permiso" data-estilo="error" role="status">Esta acción es del propietario.</div>'))
    await g.copiar(pg, GO, 'Avisos flotantes', 'Éxito, advertencia y error (#avisos)', A)
    GP = 'Participantes, actividades, listas y sistema'
    await pg.click('[data-tab="participantes"]'); await pg.wait_for_timeout(900)
    await g.copiar(pg, GP, 'Participantes', 'Padrón con estado, paginado de 50', A)
    await pg.click('[data-tab="actividades"]'); await pg.wait_for_timeout(500); await pg.click('#btn-nueva'); await pg.wait_for_timeout(300)
    await g.copiar(pg, GP, 'Actividades', 'Horarios, cruces, verificar solicitud, catálogo y formulario', A)
    await pg.click('[data-tab="listas"]'); await pg.wait_for_timeout(500); await pg.select_option('#l-act', 'VIS01'); await pg.wait_for_timeout(700)
    await g.copiar(pg, GP, 'Listas · VIS01', 'Ordenada por apellidos; marca de grupo', A)
    await pg.fill('#l-q', '999000111'); await pg.click('#l-buscar'); await pg.wait_for_timeout(600)
    await g.copiar(pg, GP, 'Listas · solicitud rechazada', 'Nadie con ese número', A)
    await pg.click('[data-tab="sistema"]'); await pg.wait_for_timeout(700)
    await pg.set_input_files('#archivo-padron', str(RAIZ / 'local/padron_importar_ejemplo.csv')); await pg.wait_for_timeout(400)
    await pg.click('#btn-importar'); await pg.wait_for_timeout(900)
    await pg.set_input_files('#archivo-actividades', str(RAIZ / 'local/actividades_prueba.csv')); await pg.wait_for_timeout(400)
    await g.copiar(pg, GP, 'Sistema', 'Equipo y los 5 pasos de la base de prueba a la real, con informe y vista previa', A)
    await ctx.close()
    GR = 'Otros roles'
    ctx, pg = await entrar('Luis')
    await g.copiar(pg, GR, 'Operador', 'Sin Sistema, sin botones de cupo ni cierre', A)
    await ctx.close()
    ctx, pg = await entrar('Ana')
    await g.copiar(pg, GR, 'Admin', 'Cierra y modifica; no abre ni toca etapas', A)
    await ctx.close()
    GM = 'En celular'
    ctx, pg = await entrar('Tú', 2400, 390)
    await g.copiar(pg, GM, 'Operación', 'Panel a 390 px', 390)
    await pg.click('[data-tab="listas"]'); await pg.wait_for_timeout(500); await pg.select_option('#l-act', 'VIS01'); await pg.wait_for_timeout(700)
    await g.copiar(pg, GM, 'Listas', 'La tabla se desplaza dentro de su caja', 390)
    await ctx.close()
    g.escribir('pantallas-panel.html', '<p>Cada marco es una copia exacta de <code>panel.html</code> en un estado. Edita <code>../base.css</code> y recarga esta página: el cambio se ve en todas. <a href="index.html">Volver a la portada</a></p>')


PORTADA = '''<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Diseño · galerías de pantallas</title>
<style>body{margin:0;font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:#e9ecf2;color:#1b2333}main{max-width:820px;margin:40px auto;padding:0 20px}
a.t{display:block;background:#fff;border:1px solid #c6ccd8;border-radius:12px;padding:18px 20px;margin:14px 0;color:inherit;text-decoration:none}a.t:hover{border-color:#1f4fbf}a.t b{font-size:1.1rem}
code{background:#fff;padding:1px 5px;border-radius:4px}</style></head><body><main>
<h1>Galerías de pantallas para el diseño de autor</h1>
<p>Cada pantalla, en cada uno de sus estados (espera, error, cerrado, confirmación, ventanas, avisos), copiada tal cual de las páginas reales. Todas usan <code>../base.css</code>: edita ese archivo y recarga para ver el cambio en todas a la vez.</p>
<a class="t" href="pantallas-participante.html"><b>Página del participante</b><br>Documento, elección y confirmación: inicio, verificando, en la fila, errores, intentos, cerrado, sin conexión, cuenta regresiva, llena, cruces, privacidad, confirmación. En celular y en computadora.</a>
<a class="t" href="pantallas-panel.html"><b>Panel de organización</b><br>Acceso (demo, contraseña, código, QR, nueva contraseña), Operación (abierto, aviso, alerta, cerrado, ventanas, avisos), Participantes, Actividades, Listas, Sistema, vistas por rol y en celular.</a>
<p>Para probar las interacciones de verdad, abre <a href="../index.html">../index.html</a> y <a href="../panel.html">../panel.html</a> en modo demo. Si cambias la estructura del HTML de las páginas, regenera las galerías con <code>python local/generar_galeria.py</code>.</p>
</main></body></html>'''


async def main():
    SALIDA.mkdir(exist_ok=True)
    (SALIDA / 'index.html').write_text(PORTADA, encoding='utf-8')
    async with async_playwright() as p:
        nav = await p.chromium.launch()
        print('Participante:'); await participante(nav)
        print('Panel:'); await panel(nav)
        await nav.close()
    print('Listo:', ', '.join(str(x.relative_to(RAIZ)) for x in sorted(SALIDA.glob('*.html'))))


if __name__ == '__main__':
    asyncio.run(main())
