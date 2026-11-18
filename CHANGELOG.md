# Changelog

Formato: [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) · versiones semver cortadas por humanos.

## [Unreleased]
### Added
- Esqueleto FastAPI + Vite/React: health/ready, errores JSON uniformes, cabeceras de seguridad, rate limiting, Alembic y CI (UPS-001).
- Modelo de datos (19 tablas), esquemas de la API, semilla demo idempotente y sistema de diseño (UPS-002).
- Parser de URLs de YouTube y embed `youtube-nocookie` (UPS-003).
- Base del front: sesión con renovación segura, tema por academia con contraste AA y componentes accesibles (UPS-004).
- Login único, registro de miembros con boleta y sesión con rotación de refresh token (UPS-005).
- Página principal del campus y bienvenida de cada academia con re-tematización y "Continuar donde te quedaste" (UPS-006).
- Reproductor de cursos con ruta, módulos plegables, progreso y "Marcar como completada" (UPS-007).
- Panel de academia: identidad (logo, mascota, colores), contenido con reordenamiento e inscritos por boleta (UPS-008).
- Panel de superadmin: academias (con su canal), usuarios, restablecer contraseña y página principal (UPS-009).
- Matriz de permisos verificada por endpoint y rol, en `docs/permissions-matrix.md` (UPS-010).
- Comunidad tipo Discord: Feed, General y canal por academia, posts con imagen, comentarios y moderación (UPS-011).
- Eventos y calendario (mes y lista), globales o por academia (UPS-013).
- Flujo de aceptación end-to-end de 6 pasos con Playwright en escritorio y celular (UPS-016).
- El superadmin hace admin de un club a un miembro y lo regresa a miembro desde la pestaña Usuarios, con insignia de rol y confirmación que nombra a la persona y al club; el cambio aplica en la siguiente petición y queda en el registro sin datos personales (UPS-093).
- Foto en los eventos: quien administra el evento la sube, la cambia o la quita desde el formulario (ahora también para editar) y se ve en el calendario, en la página del club y en la principal; si la foto falla, el evento se conserva y el formulario lo avisa (UPS-094).
- Logos y mascotas con fondo transparente: al subirlos, la casilla «Quitar el fondo blanco» (marcada por defecto) vuelve transparente solo el blanco conectado al borde y deja el blanco encerrado en el dibujo; se ve en una muestra clara y una oscura, y «Quitar fondo blanco al logo actual» arregla el que ya está subido. Disponible en el panel del club y en Marca del sitio (UPS-095).

### Fixed
- Comunidad ya no se desplaza de lado en celular (UPS-011).
- Fechas sin zona horaria en eventos se interpretan como UTC en lugar de dar error 500 (UPS-013).

### Security
- Límite de 6 MB por petición (413), moderación solo sobre contenido visible y sin sondeo en pestañas ocultas (UPS-011).
- Altas simultáneas duplicadas responden 409, búsqueda con comodines literales y reset de contraseña sin caché (UPS-009).
