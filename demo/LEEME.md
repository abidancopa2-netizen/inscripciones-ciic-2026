# Demos autónomas

Dos archivos que funcionan con doble clic, sin servidor ni Supabase, con la base ficticia adentro:

- `demo-participante.html`: la página que ve quien se inscribe (3 pantallas).
- `demo-panel.html`: el panel de organización (5 pestañas, 3 niveles de rol).

Ábrelos en el mismo navegador: comparten los datos (lo que inscribes en uno aparece en el otro).

La cinta amarilla de arriba es solo de la demo. Su selector **"Ver estado"** fuerza en pantalla los estados que normalmente no aparecen solos: fila de espera, sin conexión, cuenta regresiva, cerrado, error del sistema, alerta de saturación, integridad rota, ventana de advertencia, inicio de sesión real y código de verificación.

Estos archivos son una **copia armada** de `docs/index.html`, `docs/panel.html`, `docs/base.css` y `docs/config.js`. Para diseñar, edita los de `docs/` (ver `docs/LEEME-DISENO.md`) y vuelve a armar las demos con `python local/armar_demos.py`.
