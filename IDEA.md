# IDEA · UpiixSol Campus

> **No es un challenge ni un hackathon.** Es una **plataforma real** para el club de alumnos que tendrá **tráfico recurrente** (uso diario durante el semestre), desarrollada como **proyecto escolar** con fecha límite **jueves 8 de octubre de 2026**. Se construye lo más robusta posible dentro de ese plazo: primero que funcione bien y sea segura, luego lo vistoso. Tags: **[Decided]** · **[Recommended]** · **[To validate]**.
> Donde este documento dice "demo", léase "flujo de aceptación": es el recorrido que debe funcionar de punta a punta en la entrega y en producción.
> Every pitch number comes from §10 with a source. §4 → vertical tasks · §6 → contract · §7 → spikes · §8 → acceptance.
> Idioma de este documento y de la UI: español (México).

## 0. Name and brand (fixed at T0)
- Name: **UpiixSol Campus** · repo/domain: `upiixsol-campus` · tagline: **"Tu club, tus academias, un solo campus"**. [Decided]
- Renaming after T−50% needs a human `uak decision`.

### 0.1 Identidad visual (assets que se entregan junto con este archivo)
Los logos son archivos reales que el humano adjunta al kit. **No redibujarlos ni recrearlos en SVG**; usarlos tal cual desde `assets/brand/`. [Decided]

| Archivo esperado | Contenido | Uso |
|---|---|---|
| `assets/brand/upiixsol/wordmark.png` | Wordmark "upiixSol" (upiix verde, x verde oscuro, Sol naranja) + paleta | Header del campus, login, favicon recortado |
| `assets/brand/upiixsol/mascot.png` | Ajolote con penacho naranja/rojo y texto "upiixSol" | Bienvenida de la página principal, login, estados vacíos |
| `assets/brand/upiixia/wordmark.png` | Wordmark "upiixIA" (upiix verde, x verde oscuro, IA verde claro) + paleta | Header dentro de la academia UpiixIA |
| `assets/brand/upiixia/mascot.png` | Ajolote todo en verdes con penacho de hojas | Bienvenida de la academia UpiixIA [Decided] |
| `docs/ref/player-reference.png` | Captura de un reproductor de curso de otra plataforma | **Solo referencia de layout** (sidebar + video + descripción). No copiar marca, colores ni textos. |

Paletas:

| Marca | Primario | Secundario | Acento | Acento 2 |
|---|---|---|---|---|
| UpiixSol | `#00BF63` | `#04944F` | `#F28034` [Decided — ignorar el `#FFDE59` rotulado en la imagen de paleta, es un error] | `#B4422F` (rojo terracota de las plumas; para estados activos/hover del naranja, badges, avisos y detalles) [Decided] |
| UpiixIA | `#00BF63` | `#04944F` | `#7ED957` | — |

- **Tema claro por defecto** [Decided]: fondos claros (blanco o crema cálido ≈ `#FBF8EF`, como el fondo de la mascota de UpiixSol), texto oscuro (≈ `#1F2A24`), tarjetas blancas con borde/sombra suave. Los colores de marca se usan en botones, enlaces, encabezados, barras de progreso y acentos, no como fondo de páginas completas. El reproductor de clases también va en claro (solo el recuadro del video es oscuro). Modo oscuro: fuera de alcance v1.
- Contraste: el texto sobre `#00BF63` y `#F28034` debe ser blanco en negrita o usar el tono oscuro (`#04944F` / `#B4422F`) para cumplir legibilidad; validar con un checker WCAG AA.

- Tipografía: redondeada y gruesa, similar al wordmark (p. ej. *Fredoka* o *Baloo 2* de Google Fonts para títulos; *Inter* para cuerpo). [Recommended]
- El tema de cada academia se aplica con variables CSS (`--academy-primary`, `--academy-secondary`, `--academy-accent`, `--academy-accent-2` opcional, `--academy-logo`) cargadas desde la BD, siempre sobre la base de tema claro. El campus raíz usa la paleta UpiixSol. [Decided]

## 1. One line
Para **los miembros de un club estudiantil del IPN (UPIIZ)**, que hoy **tienen su material repartido entre grupos de WhatsApp, Drive y Discord sin seguimiento de avance [To validate: número]**, **UpiixSol Campus** les permite **entrar a cualquier academia del club, retomar la clase donde se quedaron y conversar con su comunidad en un solo lugar**, a diferencia de **la mezcla actual de Drive + YouTube + Discord**.

Por qué no usar algo existente: los LMS genéricos (Moodle, Classroom) no tienen identidad por academia ni comunidad tipo red social, y Discord no tiene rutas de aprendizaje ni progreso. Aquí: multi-academia con tema propio, 3 roles con alcance estricto y comunidad por canales integrada, todo en un solo login.

## 2. Users
| Persona | Moment | Need | Flow step |
|---|---|---|---|
| **Superadmin** (mesa directiva del club, 4 cuentas) | Inicio de semestre / alta de una nueva academia | Crear academias, asignar sus admins, gestionar eventos, galería, blog, página principal y usuarios | 6 |
| **Admin de academia** (líder de UpiixIA) | Prepara el contenido de la semana | Editar solo su academia: identidad, rutas → módulos → clases, recursos, eventos de su academia | 5 |
| **Miembro / alumno** (estudiante con boleta) | Entre clases, en el celular o la laptop | Registrarse solo, explorar academias, ver clases, retomar donde se quedó, publicar en la comunidad | 1–4 |

### 2.1 Roles y permisos [Decided]
| Acción | Superadmin | Admin de academia | Miembro |
|---|---|---|---|
| Alta/baja/edición de academias | ✅ | ❌ | ❌ |
| Logo y colores de una academia | ✅ todas | ✅ solo la suya | ❌ |
| Alta de admins de academia | ✅ (panel especial) | ❌ | ❌ |
| Alta/baja de miembros y asignarlos a academias | ✅ | ✅ inscribir a su academia [Recommended] | ❌ |
| Rutas, módulos, clases, recursos | ✅ todas | ✅ solo la suya | 👁 ver |
| Eventos | ✅ globales y de academia | ✅ solo de su academia [Recommended] | 👁 ver |
| Página principal, galería de proyectos, blog | ✅ | ❌ | 👁 ver · proponer proyecto [To validate] |
| Comunidad: publicar/comentar/reaccionar | ✅ | ✅ | ✅ |
| Moderar (ocultar/borrar posts) | ✅ todo | ✅ canal de su academia | ❌ |
| Editar su propio perfil (foto, nickname, nombre) | ✅ | ✅ | ✅ |
| Cambiar su correo y contraseña | ✅ | ✅ | ✅ |

- Un admin de academia está asignado a **una** academia (`users.academy_id`). [Decided]
- Todas las academias activas son visibles para cualquier miembro autenticado; la "inscripción" marca *Mis academias* y habilita el progreso. [Recommended]
- Los permisos se validan **en el backend** por endpoint; ocultar botones en el front no basta. [Decided]

### 2.2 Autenticación [Decided]
- **Un solo login** para los 3 roles (correo + contraseña); tras entrar, se redirige según rol.
- **Registro libre** solo para miembros: nombre completo, número de boleta, correo, contraseña. Boleta: 10 dígitos, única [To validate: formato exacto de boleta IPN].
- Las cuentas de admin de academia **solo** las crea el superadmin desde su panel.
- Contraseñas con hash (bcrypt/argon2), nunca en texto plano en BD ni en el repo.

### 2.3 Cuentas sembradas (seed) [Decided]
Se usa el dominio `upiixsol.dev` porque varios validadores de email rechazan `.local`/`.test`. Son provisionales, no reciben correo.

| Rol | Correo | Contraseña |
|---|---|---|
| Superadmin 1 | `superadmin1@upiixsol.dev` | `admin123` |
| Superadmin 2 | `superadmin2@upiixsol.dev` | `admin123` |
| Superadmin 3 | `superadmin3@upiixsol.dev` | `admin123` |
| Superadmin 4 | `superadmin4@upiixsol.dev` | `admin123` |
| Admin de academia UpiixIA (demo) [Recommended] | `admin.ia@upiixsol.dev` | `admin123` |
| Miembro demo [Recommended] | `alumno.demo@upiixsol.dev` | `admin123` |

- El seed lee la contraseña inicial de `SEED_DEFAULT_PASSWORD` (default `admin123`) y la guarda con hash.
- Las cuentas sembradas llevan `must_change_password = true`; tras el login se muestra un aviso para cambiar correo y contraseña (obligatorio desde UPS-020; `REQUIRE_PASSWORD_CHANGE=false` lo vuelve no bloqueante para una demo). [Decided by @crisMmolina]
- Pantalla **Mi cuenta → Seguridad**: cambiar correo (pide contraseña actual) y cambiar contraseña (actual + nueva + confirmación). [Decided]

## 3. Demo case
Academia **UpiixIA** (la primera dada de alta en el seed) con la ruta **"Fundamentos de IA con Python"**: 2 módulos, 4 clases con videos públicos de YouTube, 3 recursos (un PDF, un link, un video), 2 eventos próximos y un canal de comunidad con 5 posts sembrados. El miembro demo tiene 2 de 4 clases completadas (50 %), así "Continuar donde te quedaste" tiene algo que mostrar. Se elige porque recorre los tres roles y es el caso real con el que arrancará el club. [To validate: elegir los videos reales con el admin de UpiixIA]

## 4. Demo flow (6 steps or fewer, 3 min or less; each step = one vertical task)
| # | User does | Sees on screen | API | Prio |
|---|---|---|---|---|
| 1 | Miembro se registra con nombre, boleta, correo y contraseña (o entra con la cuenta demo) | Login único con pestaña "Crear cuenta"; al entrar, la página principal de UpiixSol con mascota, bienvenida y tarjetas de academias | `POST /api/auth/register` · `POST /api/auth/login` | P0 |
| 2 | Recorre la página principal y da clic en la tarjeta de UpiixIA | **Wow:** el campus se re-tematiza al instante con el logo y los verdes de UpiixIA, y la bienvenida de la academia muestra "Continuar: Clase 3 · 50 %", últimos mensajes de su comunidad y próximos eventos | `GET /api/home` · `GET /api/academies/{slug}/home` | P0 |
| 3 | Da clic en "Continuar" | Reproductor estilo curso: sidebar con ruta, barra de % completado, módulos plegables con `x/y` clases, clase actual resaltada; video de YouTube embebido, descripción y links de recursos debajo; botones Anterior/Siguiente y "Marcar como completada" → la barra sube a 75 % | `GET /api/routes/{id}` · `GET /api/lessons/{id}` · `POST /api/lessons/{id}/complete` | P0 |
| 4 | Va a Comunidad → canal #upiixia y publica un hallazgo con imagen | Layout tipo Discord: columna de canales (Feed, General, uno por academia), el post aparece arriba y también en Feed | `GET /api/channels` · `POST /api/channels/{id}/posts` | P0 |
| 5 | Admin de UpiixIA entra, agrega un módulo y una clase (URL de YouTube, descripción, 2 links) y cambia el color de acento | Panel de academia: la clase nueva aparece en el sidebar del reproductor y el tema cambia en vivo | `POST /api/academies/{id}/routes/{rid}/modules` · `POST /api/modules/{id}/lessons` · `PATCH /api/academies/{id}/branding` | P0 |
| 6 | Superadmin da de alta la academia "UpiixRobótica" con logo y color, le crea su admin y publica un evento global | La academia nueva aparece en la página principal, su canal se crea solo en Comunidad y el evento sale en el calendario | `POST /api/admin/academies` · `POST /api/admin/users` · `POST /api/events` | P0 |

- Wow in one sentence: al entrar a una academia, todo el campus adopta su identidad y te devuelve a la clase exacta donde te quedaste. · seconds until the wow: ≤ 30 (con cuenta demo ya logueada).
- Plan B: los videos de YouTube pueden fallar sin red → cada clase demo tiene miniatura local y el reproductor muestra "Video no disponible sin conexión" sin romper el layout; se graba un video de respaldo de la demo completa.

## 5. Technical core
- Method: aplicación web multi-tenant ligera. Cada academia es un *tenant lógico* (`academy_id` en todas las tablas de contenido). RBAC con 3 roles + alcance por academia verificado en el backend. Progreso = `clases completadas / clases publicadas` de la ruta, calculado en el servidor. [Decided]
- No hay IA generativa en el núcleo. Ningún número mostrado (progreso, conteos, fechas) lo produce un LLM; todo sale de consultas a la BD. [Decided]
- Stack: **FastAPI + SQLAlchemy + Pydantic (`app/schemas/`)**, PostgreSQL (SQLite en desarrollo), frontend **React + Vite + Tailwind** con variables CSS por academia, subida de imágenes a almacenamiento local `media/` (S3-compatible después). [Recommended — el humano puede cambiarlo antes de T0]
- **Robustez para tráfico recurrente** [Decided salvo donde se indique]:
  - PostgreSQL en producción; migraciones con **Alembic** desde el primer commit (nada de `create_all` en prod).
  - Índices en todas las FK y en `users.email`, `users.boleta`, `academies.slug`, `posts(channel_id, created_at)`, `lesson_progress(user_id)`.
  - **Paginación por cursor** en feed, canales, comentarios, galería y listados de admin (máx. 50 por página). Ningún endpoint devuelve tablas completas.
  - Evitar N+1: cargar relaciones con `selectinload`/`joinedload` en rutas, módulos y posts.
  - Sesión con JWT de acceso corto (15 min) + refresh en cookie `httpOnly`, `Secure`, `SameSite=Lax`. [Recommended]
  - **Rate limiting** en login y registro (p. ej. 5 intentos/min por IP) y en publicar posts (p. ej. 10/min por usuario). [Recommended]
  - Validación de entrada con Pydantic en todo; sanitizar el markdown/HTML de posts y descripciones (evitar XSS); validar tipo real y tamaño de imágenes subidas.
  - CORS restringido al dominio del front; secretos solo por variables de entorno (`.env.example` en el repo, `.env` fuera).
  - Errores con formato JSON uniforme; logs estructurados; endpoint `GET /api/health`.
  - Imágenes servidas como estáticos con caché; redimensionar avatares y logos al subir. [Recommended]
  - Despliegue con **Docker Compose** (api + db + front estático/nginx) y respaldo diario de la BD con `pg_dump`. [Recommended]
  - Soft delete (`is_active`) para academias y usuarios: dar de baja no borra su historial.
- Honest validation: tests de permisos (matriz §2.1: cada rol × cada endpoint de escritura), test de que un admin de academia **no** puede editar otra academia, test de cálculo de progreso, test de registro con boleta duplicada. Se reporta el % de casos de la matriz cubiertos.

## 6. Data (contract in `app/schemas/`)
| Entity | Key fields | Source (license) |
|---|---|---|
| User | id, role (`superadmin`/`academy_admin`/`member`), email (único), password_hash, full_name, nickname, boleta (único, nullable para admins), avatar_url, academy_id (solo admin de academia), must_change_password, is_active, created_at | Registro / seed |
| Academy | id, slug, name, short_description, welcome_text, logo_url, mascot_url, color_primary, color_secondary, color_accent, color_accent_2 (nullable), is_active, order | Superadmin / admin de academia |
| Enrollment | user_id, academy_id, enrolled_at | Miembro / admin |
| LearningRoute | id, academy_id, title, description, cover_url, order, is_published | Admin de academia |
| Module | id, route_id, title, order | Admin de academia |
| Lesson | id, module_id, title, youtube_url, youtube_video_id (derivado), description (markdown), duration_min, order, is_published | Admin de academia |
| LessonLink | id, lesson_id, label, url | Admin de academia |
| LessonProgress | user_id, lesson_id, completed_at, last_viewed_at | Sistema |
| Resource | id, academy_id, type (`document`/`link`/`video`/`other`), title, description, url o file_url, thumbnail_url, created_at | Admin de academia |
| Event | id, academy_id (null = global), title, description, location o link, starts_at, ends_at, cover_url | Superadmin / admin de academia |
| Project (galería) | id, title, slug, summary, body (markdown), cover_url, authors, academy_id (opcional), tags, status (`draft`/`published`), published_at | Superadmin (miembros proponen [To validate]) |
| BlogPost | id, title, slug, body, cover_url, author_id, published_at | Superadmin |
| HomeContent | hero_title, hero_text, highlighted_academy_ids, featured_project_ids | Superadmin |
| Channel | id, type (`feed`/`general`/`academy`), academy_id (si aplica), name, slug | Sistema (el canal de academia se crea al dar de alta la academia) |
| Post | id, channel_id, author_id, body, image_url, link_url, created_at, is_hidden | Usuarios |
| Comment | id, post_id, author_id, body, created_at, is_hidden | Usuarios |
| Reaction | post_id, user_id, kind | Usuarios |

- El canal **Feed** no guarda posts propios: agrega los posts recientes de General + todas las academias. [Decided]
- Imágenes subidas: solo png/jpg/webp/svg, máx. 2 MB logos, 5 MB posts. [Recommended]

## 7. AI and external APIs (each = a 30-min spike + a recorded fallback)
| Use | Model/API [To validate] | Key owner | Fallback |
|---|---|---|---|
| Video de clases | YouTube embed (`youtube-nocookie.com/embed/{id}`), extrayendo el id de cualquier formato de URL (watch, youtu.be, shorts) | No requiere key | Miniatura local + mensaje "Video no disponible"; validar URL al guardar |
| Duración/miniatura automática del video | YouTube Data API v3 (opcional) | Superadmin | Duración capturada a mano por el admin; miniatura `img.youtube.com/vi/{id}/hqdefault.jpg` |
| Almacenamiento de imágenes | Disco local `media/` | — | Mismo |
| Correo (recuperar contraseña) | Fuera de alcance v1 | — | Superadmin restablece contraseñas desde su panel |

## 8. Rubric → evidence
No hay rúbrica de concurso; estos son los **criterios de aceptación** de la entrega. [Decided] Si el profesor da una rúbrica, se mapea aquí. [To validate]

| Criterio de aceptación | Peso | Step/artifact that proves it |
|---|---|---|
| Los 3 roles funcionan con un solo login y alcance correcto | Alto | Pasos 1, 5, 6 + tests de la matriz §2.1 en verde |
| Un admin de academia no puede tocar otra academia (backend) | Alto | Test de permisos dedicado |
| Flujo completo de aprendizaje con progreso persistente | Alto | Paso 3: completar clase, recargar, el % se mantiene |
| Multi-academia sin tocar código | Alto | Paso 6: academia nueva con su tema y canal |
| Comunidad con canales Feed / General / por academia | Medio | Paso 4 |
| Robustez: migraciones, paginación, rate limit, hash, validación | Medio | Checklist de §5 + `docker compose up` desde cero |
| Identidad visual UpiixSol / UpiixIA respetada y responsive | Medio | Pasos 2 y 3 en escritorio y móvil |

### 8.1 Prioridades por el plazo (entrega jueves 8 oct 2026) [Decided]
1. **P0 — sin esto no hay entrega:** auth + roles + seed, CRUD de academias con identidad, rutas → módulos → clases + reproductor + progreso, inicio de UpiixSol e inicio de academia, panel superadmin de usuarios.
2. **P1:** comunidad (canales, posts, comentarios), recursos, eventos + calendario, perfil y cambio de correo/contraseña.
3. **P2 — solo si sobra tiempo:** galería de proyectos y blog con editor rico, reacciones, reordenar con arrastrar (antes: flechas subir/bajar), miniaturas automáticas de YouTube.
- Cada tarea vertical se cierra con su test y su migración; no se avanza a P1 con un P0 roto.

## 9. Scope
**Pantallas** [Decided]:
- *Públicas:* Login único con pestaña de registro de miembros.
- *Campus UpiixSol:* Inicio (bienvenida con mascota, tarjetas de academias, proyectos destacados, próximos eventos, actividad de la comunidad) · Academias · Galería de proyectos (listado tipo blog + detalle) · Blog · Calendario (vista mes + lista, filtro por academia) · Comunidad (Feed, General, un canal por academia) · Perfil.
- *Dentro de cada academia* (navegación propia, con su logo y colores): Inicio de la academia (bienvenida con logo y nombre, "Continuar donde te quedaste", progreso en mis rutas, recursos recientes, últimos mensajes de su canal, próximos eventos) · Rutas de aprendizaje (tarjetas de rutas → reproductor tipo curso) · Recursos (tarjetas filtrables por tipo: documento, link, video, otro) · Comunidad (atajo al canal de la academia) · Eventos (calendario filtrado).
- *Panel superadmin:* academias (CRUD + identidad), usuarios (crear admins de academia y miembros, asignar academia, activar/desactivar, restablecer contraseña), página principal, galería, blog, eventos, moderación.
- *Panel admin de academia:* identidad (logo, mascota, colores, texto de bienvenida), rutas → módulos → clases (reordenar con arrastrar), recursos, eventos de su academia, inscritos, moderación de su canal.
- *Mi cuenta:* foto de perfil, nickname, nombre completo, cambio de correo, cambio de contraseña.

**Reproductor de clase** (referencia de layout `docs/ref/player-reference.png`): sidebar izquierdo con título de la ruta, barra y % completado, buscador de clases, módulos plegables con check y contador `completadas/total`, clases con ícono de tipo y duración; área principal con título, video 16:9, controles Anterior/Siguiente/Marcar completada, y debajo "Descripción" y "Recursos de la clase". En móvil el sidebar se vuelve un drawer.

- Out: pagos, certificados, exámenes/calificaciones, chat en tiempo real (la comunidad se refresca al recargar o cada 30 s), mensajes directos, notificaciones por correo, app móvil nativa, recuperación de contraseña por correo.
- Simulated with `demo_data`: academia UpiixIA con 1 ruta, 2 módulos, 4 clases, 3 recursos, 2 eventos, 5 posts; 3 proyectos en la galería; 1 entrada de blog; cuentas de §2.3.
- UI language: español (México).
- Ethics/data: la boleta y el correo son datos personales: solo los ven el propio usuario y los superadmins; en la comunidad solo se muestra nickname y foto. Aviso de privacidad simple en el registro. Los admins pueden ocultar posts; queda registro de quién lo ocultó. Contraseñas con hash; las de seed se deben cambiar antes de producción.

## 10. Citable facts (verified on <fecha — pendiente>)
| Fact | Source URL |
|---|---|
| Parámetros y embed del reproductor de YouTube [To validate] | https://developers.google.com/youtube/iframe_api_reference |
| Modo de privacidad mejorada (`youtube-nocookie.com`) [To validate] | https://support.google.com/youtube/answer/171780 |
| Recomendaciones de hash de contraseñas (argon2/bcrypt) [To validate] | https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html |
| Dolor del club: material disperso / % de miembros que abandonan cursos [To validate — conseguir dato real con una encuesta al club] | — |
