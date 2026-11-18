# Auditoría · área auth (/login, registro, cerrar sesión, /cuenta, redirecciones)

Medido con Playwright (Chromium) contra una instancia local de desarrollo. Escritorio 1280x800 y celular 390x844. Scripts, JSON y capturas en `audit/auth/`. Cuentas de prueba creadas con prefijo AUD- (`aud.pw.1490667@upiixsol.dev`, `aud.auth.1490128@upiixsol.dev`, etc.). No se tocaron cuentas sembradas ni contraseñas sembradas (una pasada de login con alumno.demo fue solo de lectura y no se repitió).

1. [layout] [alta] /login, pestañas Entrar / Crear cuenta — Al cambiar de pestaña la tarjeta cambia de altura y se recentra verticalmente: sale de y=193 con h=413 (Entrar) y entra en y=68 con h=664 (Crear cuenta). Salta ~125 px hacia arriba; en celular 389 px (y=381) → 660 px (y=279). — Cómo reproducir: abrir /login, clic en "Crear cuenta". — Evidencia: t1_login.json (`vuelta_login_card`, `tab_registro_card`), código features/auth/index.tsx:170-171 (`main` con `min-h-dvh grid items-center`), la tarjeta no tiene altura reservada.

2. [layout] [media] /login (Entrar y Crear cuenta) — Al aparecer un error la tarjeta crece y se desplaza: Entrar sin error h=413 y=193 → con "Correo o contraseña incorrectos." h=465 y=167 (+52 px, sube 26 px). Registro: h=664 y=68 → con errores locales h=696 y=52 (+32); con correo duplicado (409) h=736 y=40 (+72). Celular: 389 → 441 px. Los mensajes no tienen animación de entrada (features/auth/index.tsx:53-57 y :136-140, sin clases `animate-*`). — Cómo reproducir: en Entrar enviar credenciales malas; en Crear cuenta enviar el formulario vacío. — Evidencia: t1_login.json (`login_mal_card`, `reg_vacio_card`), t2_flows.json (`registro_correo_duplicado.card`), capturas `desktop_login_error.png`, `desktop_registro_errores.png`.

3. [bug] [alta] /cuenta?tab=perfil, campo Apodo — Con un apodo de 1 carácter el servidor responde 422 y el campo muestra el mensaje técnico en inglés del validador: "String should have at least 2 characters"; además aparece el genérico "Revisa los datos enviados." Ni el texto ni el mensaje están en español. Se conserva el botón "Guardar perfil" habilitado (dirty) sin validar minLength en cliente. — Cómo reproducir: /cuenta, borrar el apodo y escribir "A", clic en "Guardar perfil". — Evidencia: t2_flows.json `perfil.apodo_field_text`, `apodo_aria_invalid`; HTTP 422 PATCH /api/account/profile. Origen: el texto llega tal cual desde `fieldErrors(error.details)` (lib/api.ts, features/account/index.tsx:46). Ver también la altura: tabpanel 395 → 447 px al mostrar el error (`perfil.tabpanel_con_error`).

4. [ux] [media] /cuenta?tab=seguridad — Mensajes de estado obsoletos que se acumulan: tras cambiar la contraseña con éxito y luego cambiar el correo, ambos mensajes quedan visibles a la vez ("Contraseña actualizada. Cerramos tus sesiones…" y "Correo actualizado…"). Igual con errores: "La contraseña actual no es correcta." sigue visible mientras el formulario de correo muestra "Ese correo ya está registrado.". En Perfil, "Perfil actualizado." queda visible junto a "La imagen supera 2 MB." al subir una foto grande. — Cómo reproducir: cambiar contraseña (éxito), luego cambiar correo (éxito). — Evidencia: t4_pw.json `email_ok_alerts`; t2_flows.json `seguridad.email_duplicado_alerts`, `perfil.avatar_grande_alerts`. Origen: `useFormRequest` por formulario (features/account/index.tsx:34-54) y `StatusMessage` por formulario sin limpiar el otro (líneas 211-228, 163-171).

5. [ux] [media] /login?tab=registro — Validación local incompleta: al enviar vacío solo se marcan boleta, contraseña y aviso de privacidad; "Nombre completo" (minLength 3) y "Correo" no se validan en cliente (el formulario tiene `noValidate`), así que el usuario ve errores de esos campos solo después de corregir lo demás. La llamada al servidor no se hace si hay errores locales (sin 422 extra). — Cómo reproducir: Crear cuenta → Crear cuenta sin llenar nada. — Evidencia: t1_login.json `reg_vacio_errors` = ["", "La boleta debe tener 10 dígitos.", "", "Usa al menos 8 caracteres.", "Debes aceptar el aviso de privacidad."]. Código features/auth/index.tsx:77-84, :106.

6. [ux] [media] /login — Límite de intentos por IP y por correo: 5/min para /api/auth/login (app/ratelimit.py:8, `LOGIN_LIMIT = "5/minute"`; límite adicional por correo en `hit_login_email`). Un inicio de sesión exitoso también cuenta y, al bloquearse, la UI solo dice "Demasiados intentos. Espera un momento." sin indicar cuánto esperar. En un campus con una sola IP pública (NAT) varios alumnos pueden bloquearse entre sí. — Cómo reproducir: 6 intentos seguidos con credenciales malas. — Evidencia: t5_pw2.json `limite_intentos` (el 6.º intento devuelve 429 y el mensaje), captura `mobile_login_429.png`. Impacto en campus NAT: sin verificar (depende de la red real).

7. [ux] [baja] /login, pestaña Entrar — Enviar el formulario vacío no valida en cliente: va al servidor (POST /api/auth/login → 422) y muestra un mensaje de error de API en lugar de "Escribe tu correo" / "Escribe tu contraseña". El texto exacto del mensaje no quedó capturado (sin verificar). — Evidencia: t1_login.json `login_vacio_alert` = 1; consola 422 en login. Código features/auth/index.tsx:35-47 y :50 (noValidate).

8. [ux] [baja] /cuenta?tab=seguridad — Botones deshabilitados sin explicación: "Cambiar contraseña" queda deshabilitado con contraseñas que no coinciden o con menos de 8 caracteres, y "Cambiar correo" si falta algún campo; no hay texto que diga por qué. Solo el caso de no coincidir muestra mensaje. — Evidencia: t2_flows.json `seguridad.mismatch_btn_disabled` = true, `pw_btn_disabled_inicial` = true; código features/account/index.tsx:266-270, :202.

9. [layout] [baja] /cuenta?tab=seguridad — Altura de la pestaña Seguridad crece en cada paso de error: 790 px (inicial) → 812 px (no coinciden, con mensaje) → 864 px (contraseña actual incorrecta) → 916 px (correo duplicado, con mensajes acumulados). El panel superior no se mueve, pero el contenido bajo la tarjeta se desplaza al hacer scroll. — Evidencia: t2_flows.json `seguridad.tabpanel`, `tabpanel_mismatch`, `tabpanel_pw_error`, `tabpanel_email_error`.

10. [ux] [baja] /cuenta — Foto de perfil: no hay validación de tamaño ni tipo en cliente (features/account/index.tsx:74-83, `accept` solo en el input). Un archivo de 3 MB se envía, el servidor responde 413 y el mensaje "La imagen supera 2 MB." sí aparece. Funciona, pero se gasta la subida y en consola queda un 413. — Evidencia: t2_flows.json `perfil.avatar_grande_alerts`; HTTP 413 POST /api/account/avatar.

11. [ux] [baja] /login, /cuenta — Ruido en consola: en cada carga sin sesión aparece "401 POST /api/auth/refresh" (esperado al no tener sesión, pero se ve como error en la consola del navegador). — Evidencia: t1_login.json y t2_flows.json `logs.console`.

## Verificado sin hallazgos

- Redirecciones sin sesión: /cuenta, /cuenta?tab=seguridad, /admin y /panel/academia llevan a `/login?next=<ruta>` (t2_flows.json `redirects_anonimo`).
- Miembro: /admin y /panel/academia redirigen a "/"; la API responde 403 a /api/admin/users, /api/admin/academies y /api/admin/home con token de miembro (t7_member.json).
- Cerrar sesión desde el menú de usuario: vuelve a /login y /cuenta pide sesión de nuevo (t7_member.json, t2_flows.json).
- Cambio de contraseña: contraseña actual incorrecta muestra "La contraseña actual no es correcta."; con éxito muestra el aviso de sesiones cerradas y limpia los campos (t4_pw.json). Tras el cambio, con la contraseña nueva se entra y con la vieja no (t5_pw2.json y t6 con credenciales nuevas, redirige a "/").
- Cambio de correo: correo ya registrado → 409 "Ese correo ya está registrado."; éxito → "Correo actualizado…" y el correo nuevo funciona para entrar (verificado en t5/t6).
- Alta de cuenta correcta (boleta 10 dígitos, aviso aceptado) lleva a "/" (t2_flows.json `registro_ok`).
- Sin scroll horizontal en celular 390 px en /login, registro, /cuenta Perfil y Seguridad (t1_login.json, t8_mobile.json: hscroll 0).
- Campo de contraseña de cambio: "Cambiar contraseña" se habilita solo con contraseñas iguales de 8+ caracteres (verificado).

## Sin verificar

- Texto exacto del error al enviar login vacío (punto 7).
- Mensajes de error de campo del correo con formato inválido ("Revisa los datos enviados." con 2 campos marcados aria-invalid); no se leyó el texto de cada campo.
- Aviso de contraseña provisional (`must_change_password`, Notice en /cuenta) y su redirección a Seguridad: no se probó porque no hay cuenta con contraseña provisional en las cuentas indicadas.
- Lectura de los datos de sesión tras recargar la página en /cuenta (no hubo fallo observado, solo no se comprobó con sesión expirada).
- Movimiento de la tarjeta de login al cambiar de pestaña con animación activa (medido con reduced_motion="reduce" por instrucción de medir posiciones).
- Limpieza de cuentas AUD- de prueba creadas durante la auditoría: no se borraron.
