# Auditoría · área admin (superadmin /admin, admin de club /panel/academia, permisos)

Entorno: http://100.93.23.54:8301 · código: /home/joahan/Proyectos/UpiixSol-wt/main-tools (solo lectura).
Capturas y logs: audit/admin/
Datos AUD creados: club `aud-club-prueba` (id 2) y `aud-x-club`; usuarios aud-admin-ia, aud-miembro (boleta 2099000001, contraseña reseteada), aud-admin-otro, aud-miembro2, aud-x@, aud-ui-admin, aud-ui-miembro; route/módulo/clase/recurso/eventos/posts/proyecto/blog con prefijo "AUD-".

## Hallazgos

1. [bug] [media] /admin (miembro y admin.ia), /panel/academia y /panel/academia/:slug (miembro), /admin (anónimo) — La guarda RequireRole redirige con Navigate a homeFor(user) (web/src/lib/auth.tsx:122), pero la URL del navegador se queda en la ruta pedida y se pinta el contenido del destino. Miembro en /admin ve "¡Hola, alumno.demo!" con URL /admin; admin.ia en /admin ve el panel de UpiixIA con URL /admin; anónimo en /admin ve la home pública con URL /admin (no /login?next=). Cómo reproducir: iniciar sesión como alumno.demo y abrir /admin; comprobar page.url. Evidencia: miem__admin.png, adm__admin.png, ui_miem.log. Causa exacta sin verificar. Una vez vi /admin en blanco con admin.ia (primera corrida), no reproducido después: sin verificar.

2. [ux] [media] /panel/academia/aud-club-prueba (admin.ia, club ajeno) — El encabezado muestra "AUD Club Prueba", pestañas y "Ver como miembro"; el contenido es un error "No tienes permiso para hacer esto." con botón "Reintentar" (que vuelve a fallar) y el texto "¿Algo no se ve bien? Revisa la vista de miembro en Rutas." (web/src/features/academy-admin/index.tsx:832). Debería redirigir a su club o mostrar "no administras este club". Evidencia: adm__panel_academia_aud-club-prueba.png; HTTP 403 GET /api/academies/2/content (x2).

3. [layout] [media] /panel/academia/upiixia, 1280x800 — El toast persistente "Cambia tu contraseña provisional" (cuenta admin.ia con must_change_password=true) tapa el botón "Ver como miembro": toast aprox. x 913–1264, y 80–250; botón aprox. x 1024–1229, y 113–157. Cómo reproducir: login admin.ia, abrir /panel/academia/upiixia. Evidencia: admin_desk_contenido.png. Sin verificar: si el toast se cierra solo.

4. [layout] [baja] /admin?tab=usuarios, modal "Nuevo usuario", 1280x800 — Al aparecer el error 409 "Ya existe un usuario con ese correo o esa boleta.", el modal cambia de y=92 a y=66 y de alto 616 a 668 px (+52 px; sube 26 px por centrado vertical). Cómo reproducir: Nuevo usuario, correo superadmin2@upiixsol.dev, Crear usuario. Evidencia: ui_sup_users.log, sup_modal_duplicado.png.

5. [ux] [baja] /admin?tab=usuarios — En la fila del propio superadmin sólo aparece "Restablecer"; no hay "Desactivar" ni explicación (protección de auto-desactivación). Evidencia: sup_modal_duplicado.png (fondo). Sin verificar si hay tooltip.

6. [ux] [baja] /admin?tab=usuarios y API POST /api/admin/users — El apodo por defecto es el primer nombre en minúsculas (app/services/auth.py:47-51), así que todos los usuarios AUD quedaron con apodo "aud" (ids 7, 8, 9, 10 y los creados desde la UI). No hay control de duplicados de apodo en la respuesta. Sin verificar si la BD lo permite a nivel de constraint (aparentemente sí).

7. [permisos] [baja] docs/permissions-matrix.md — La matriz sólo cubre escrituras. Las lecturas GET /api/academies/{id}/content y /api/academies/{id}/enrollments no están en la matriz. El control de alcance sí funciona (ver sección de permisos), pero no hay test que lo fije. Las respuestas de enrollments incluyen correo y boleta de cada inscrito para el admin del club.

8. [ux] [baja] Cualquier visita anónima — La consola registra "Failed to load resource: 401" en POST /api/auth/refresh (intento de restaurar sesión sin cookie). Es ruido de consola, no se ve en pantalla. Sin verificar si es esperado por diseño.

9. [layout] [baja] /panel/academia/upiixia, cambio de pestañas — CLS acumulado de 0.021 en escritorio y 0.005 en móvil durante los cambios de pestaña. Dentro del umbral "bueno" (0.1), pero hay saltos. Sin verificar qué bloque se mueve. En /admin?tab=usuarios la altura del documento pasa de 800 a 1326 px al cargar la tabla (skeleton de 800 px); no hubo salto visible por encima del contenido.

10. [ux] [baja] Login (todas las pantallas) — Límite de 5 intentos por minuto por IP y por correo (app/ratelimit.py:17, hit_login_email). Los intentos rechazados también cuentan, así que reintentar seguido mantiene el bloqueo. Esto dificulta probar, pero es un comportamiento deliberado.

Sin hallazgos de overflow horizontal: scrollWidth == clientWidth en /admin (desktop y 390 px), /panel/academia/upiixia (desktop y 390 px) y en las pestañas probadas.

## Permisos: resultados de la API

Probes: unas 500 llamadas (80 casos x 5 identidades, más ~100 casos focalizados) (anónimo, alumno.demo, admin.ia club UpiixIA, aud-admin-otro club AUD, superadmin2). Resultados en sweep_results.json y sweep2.json.

- alumno.demo (miembro): 403 en todos los /api/admin/* (GET y escritura), en /api/academies/1/content, /enrollments (GET y POST/DELETE), branding, routes, modules, lessons, resources, events, hide de posts y comentarios, y DELETE de todos los objetos AUD. Anónimo: 401 en todo lo protegido.
- admin.ia (club 1): 403 en /api/admin/* (GET, POST /admin/users, PATCH /admin/academies, PUT /admin/home, POST /admin/academies). Sin poder de crear superadmins: AdminUserCreateIn sólo acepta academy_admin|member (422 con role=superadmin, y 403 en el endpoint para admin.ia).
- admin.ia sobre el club 2 (AUD): 403 en GET content, GET enrollments, POST enrollments, PATCH branding, POST routes, POST resources, POST/PATCH/DELETE eventos, POST hide de post del canal del club 2, POST /academies/2/routes/{route}/modules.
- admin.ia sobre eventos: 403 al crear evento global (academy_id null), al mover un evento propio al club 2, y al editar/borrar un evento del club 2.
- aud-admin-otro (club 2) sobre club 1: 403 en todos los casos anteriores (simétrico). Hide de post del canal club 1: 404 porque ya estaba oculto por admin.ia (no concluyente, pero el 403 de otros casos lo confirma).
- Mass assignment: PATCH /api/account/profile con role o academy_id → 422 "Extra inputs are not permitted"; PATCH /api/admin/users/{id} con role → 422; con academy_id en un miembro → 422.
- Superadmin: POST /api/admin/users con role superadmin → 422 (no existe ruta para crear superadmins).

## Matriz (docs/permissions-matrix.md) vs realidad

- Cobertura: los 56 endpoints de escritura de la matriz coinciden exactamente con los decoradores post/patch/put/delete del código (comparación scripteada, 0 faltantes y 0 sobrantes).
- Las celdas probadas coinciden con lo que dice la matriz: anónimo 401; miembro 403 en OWN/SUPER y 200 en ANY (enroll, reacciones, comentarios, cuenta); admin de otro club 403 en OWN; superadmin 200 en todo lo que la matriz marca ✅.
- Diferencias encontradas: ninguna en autorización. Hay dos huecos de cobertura: (a) las lecturas de contenido e inscritos (ver hallazgo 7); (b) no ejecuté el test app/tests/test_permissions_matrix.py, porque regenera docs/permissions-matrix.md. Sin verificar si pasa hoy.

## Notas de datos
- Restauré los apodos de alumno.demo, admin.ia y superadmin2 (los cambié por una prueba de PATCH /account/profile) y re-inscribí a alumno.demo en UpiixIA (la inscripción quedó con enrolled_at nuevo).
- Hay un club "AUD-Robots" en el selector de club que no creé yo (origen sin verificar).
- No probé: Clubes > "Nuevo club" y "Página principal" guardar desde UI; restablecer contraseña desde UI (sólo por API); la vista móvil de Clubes/Página principal en detalle.
