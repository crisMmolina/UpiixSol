# Auditoría · área clubes

Cuentas usadas: superadmin2 (creó el club AUD-Robots sin logo: primario #1E40AF, secundario #B91C1C, acento #FACC15) y admin.ia (pestaña Identidad). Capturas y scripts en `audit/clubs/`. Medición con Playwright, escritorio 1280x800 y celular 390x844. Resultados crudos: `audit/clubs/results_su.json`, `audit/clubs/results_ia.json`.

1. [bug] [alta] /a/aud-robots, /clubes, /, /admin (tarjetas) — Los colores del club sin logo no se aplican en ninguna parte excepto en el selector. La cabecera "Bienvenida al club", los enlaces "Entrar", la tira superior de las tarjetas y la navegación siguen en verde campus. Causa: `web/src/index.css:24-29` declara `--color-primary: var(--academy-primary)` dentro de `@theme`, y eso se resuelve en `:root`, así que los hijos heredan #00bf63 aunque `AcademyTheme` cambie `--academy-primary`. Medido en /a/aud-robots: `--academy-primary` = #1E40AF, pero `--color-primary` en `:root` = #00bf63. Ningún elemento de home, /clubes ni /a/aud-robots usa rgb(30,64,175), rgb(185,28,28) o rgb(250,204,21) (results_su.json, contadores AUD = {}). Reproducir: login superadmin2 → /a/aud-robots. Evidencia: `13_club_aud-robots_d.png`, `11_clubes_d.png`. Para UpiixIA la prueba no es concluyente, porque sus colores coinciden con los del campus.

2. [bug] [alta] /panel/academia/upiixia?tab=identidad (admin.ia) — La vista previa en vivo no reacciona al color primario. Al cambiar el primario en el formulario a #1E40AF (sin guardar), la variable `--academy-primary` del preview sí cambia a #1E40AF, pero el botón y la barra de progreso siguen en rgb(0,191,99) porque `--color-primary` queda en #00bf63. El admin ve un preview que no coincide con lo que guardará. Misma causa que el hallazgo 1. Código: `web/src/features/academy-admin/index.tsx` (IdentityTab, aside "Vista previa", ~líneas 262-285). Evidencia: `results_ia.json` (preview_after_primary_change), `21_ia_identidad_preview_cambiado_d.png`. Se descartó el cambio después de medir.

3. [ux] [media] /clubes y /admin — Club sin logo: el nombre se muestra como texto de fuente display en la cabecera de la tarjeta y otra vez como título h3 debajo, así que aparece duplicado. Además, la tarjeta sin descripción (AUD X) deja un hueco vacío. Código: `web/src/features/home/index.tsx` (AcademyCard, ~líneas 73-100). Evidencia: `11_clubes_d.png`, `03_admin_tras_crear.png`. Los clubes con logo (UpiixIA) no tienen este problema.

4. [ux] [media] Selector de club (barra superior, en campus y en club) — El fallback sin logo muestra las dos primeras letras del nombre (`club.name.slice(0,2)`, `web/src/layouts/ClubSwitcher.tsx`). Los tres clubes AUD muestran "AU" y no se distinguen por el ícono; solo el nombre al lado permite diferenciarlos. Es el único lugar donde AUD-Robots sí muestra su color (cuadro azul). Evidencia: `14_selector_en_club_aud_d.png`.

5. [ux] [baja] Selector de club, escritorio y celular — El botón del selector mide 36x36 px (clase `size-9`, `ClubSwitcher.tsx`), por debajo del mínimo táctil de 44 px que sí usan los ítems del menú (min-h-11). Medido: `switcher_btn_box_d` y `switcher_btn_box_m` = 36x36.

6. [ux] [baja] /a/aud-robots (celular) — Sin verificar: en la captura de página completa (`13_club_aud-robots_m.png`) la barra de navegación inferior fija aparece a media altura. Probablemente es un artefacto de full_page con elementos fijos; confirmar con captura de viewport.

7. [layout] [baja] Carga inicial de / , /clubes y /a/:slug — Sin verificar la causa: en varias capturas la pantalla estaba en blanco (`10_home_campus_d.png`) o en skeleton de tarjetas (`11_clubes_d.png`, `13_club_*` en la primera corrida) tras `networkidle`. Al cargar la sesión, la petición POST /api/auth/refresh tardó unos 2.76 s. Repetir con espera a un elemento concreto antes de dar por bueno.

8. [bug] [baja] /a/upiixia — Sin verificar: al entrar a un club, GET /api/academies/upiixia y GET /api/academies/upiixia/home se disparan dos veces cada uno (log de red en la sesión de superadmin2). Puede ser el doble efecto en desarrollo; no se revisó el build.

Resumen de lo medido sin hallazgos: sin scroll horizontal en 1280 ni en 390 px (home, /clubes, /a/aud-robots, /a/upiixia, identidad). Pestaña Identidad sin errores de consola fuera de los 401 de refresh anónimo. Cambiar de pestaña en Identidad no mostró saltos de layout medibles (la diferencia de posición del panel se debía al scroll, no a un salto).

No probado: permisos de admin.ia sobre el club de otro (ruta directa /panel/academia/aud-robots) y pruebas con alumno.demo; ambos quedan fuera de esta corrida.

Nota de método: el login de la API limita a 5 intentos por minuto por IP y por correo (`app/ratelimit.py`). Varias corridas seguidas devolvieron 429 "Demasiados intentos", así que las sesiones se guardaron en `audit/clubs/state_*.json`.
