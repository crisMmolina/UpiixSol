# Pruebas del campus · checklist de aceptación

Lista de pruebas manuales y automáticas para dar el campus por bueno antes de la entrega.
Cada prueba tiene un ID, pasos y resultado esperado. Marca `[x]` cuando pase y anota el bug si falla.

**Cuentas de prueba (seed):** `superadmin`, un `academy_admin` de UpiixSol, un `academy_admin` de UpiixIA, un `member` sin club y un `member` inscrito. La contraseña sale de `SEED_DEFAULT_PASSWORD` en `.env` (no se escribe aquí).
**Entornos:** local (`docker compose up` o `uv run` + `npm --prefix web run dev`), staging en Render + Neon.
**Dispositivos:** escritorio 1440 px, tablet 768 px y móvil 375 px. Chrome y Firefox, y Safari iOS si se puede.

Leyenda de la columna **Auto**: ✅ ya cubierta por un test (`app/tests` o `e2e/`), 🟡 cubierta en parte y ❌ manual o sin test.

---

## 0. Puerta automática (antes de cualquier prueba manual)

| ID | Prueba | Esperado |
|---|---|---|
| P0-01 | `uv run ruff check app` | 0 errores |
| P0-02 | `uv run pytest -q --cov=app` | Todo en verde y la cobertura no baja del piso de CI |
| P0-03 | `npm --prefix web run lint && npm --prefix web run build` | Sin errores ni warnings de tipos |
| P0-04 | `uv run pytest -q e2e/` (Playwright) | Todo en verde |
| P0-05 | `bash .uak/bin/smoke` | Sale con 0 |
| P0-06 | `alembic upgrade head && alembic downgrade base && alembic upgrade head` en SQLite **y** en Postgres 16 | Las migraciones 0001 a 0006 suben y bajan limpias |
| P0-07 | Instalación limpia con `docker compose up` desde cero (sin volúmenes) | La app levanta, corre el seed y `/api/ready` responde ok |

## 1. Autenticación y sesión

| ID | Pasos | Esperado | Auto |
|---|---|---|---|
| AUTH-01 | Login con cada rol del seed | Entra y cae en su pantalla de inicio correcta | 🟡 |
| AUTH-02 | Login con contraseña mala 5 o más veces seguidas | Error genérico (sin decir si el usuario existe) y después 429 por rate limit | 🟡 |
| AUTH-03 | Esperar a que caduque el access token o borrarlo y navegar | El refresh renueva la sesión en silencio | 🟡 |
| AUTH-04 | Logout y luego botón "atrás" del navegador | No muestra datos privados y pide login | ❌ |
| AUTH-05 | Reusar un refresh token después del logout | 401 (el token quedó revocado) | 🟡 |
| AUTH-06 | Abrir `/admin`, `/panel/academia` o `/cuenta` sin sesión | Redirige a `/login` y regresa a la ruta original después del login | ❌ |
| AUTH-07 | Recargar (F5) en cualquier ruta interna estando logueado | Sigue logueado y sin pantalla en blanco | ❌ |

## 2. Roles y matriz de permisos (`docs/permissions-matrix.md`)

Probar **por API** (curl o tests), no solo ocultando botones en la UI.

| ID | Pasos | Esperado | Auto |
|---|---|---|---|
| ROL-01 | Un `member` llama a cada endpoint de `/admin/*` y del panel de academia | 403 en todos | 🟡 |
| ROL-02 | El admin de UpiixSol edita rutas, recursos, eventos, branding o inscripciones de UpiixIA (por `academy_id`) | 403 | ✅ |
| ROL-03 | El admin de academia entra a `/admin` (superadmin) | La UI no lo deja y la API da 403 | 🟡 |
| ROL-04 | El superadmin hace todo lo anterior en cualquier academia | 200 | 🟡 |
| ROL-05 | Recorrer cada fila de la matriz §2.1 de IDEA.md con los 3 roles | Cada celda coincide con lo implementado | ❌ |
| ROL-06 | Revisar las respuestas públicas (`PublicUser`, autores de posts y comentarios) | Nunca incluyen email ni boleta | 🟡 |
| ROL-07 | Cambiar el rol de un usuario desde el superadmin con la sesión de ese usuario abierta | El nuevo alcance aplica al refrescar el token, sin quedar con permisos viejos | ❌ |

## 3. Inicio del campus, clubes y theming

| ID | Pasos | Esperado | Auto |
|---|---|---|---|
| HOME-01 | Abrir `/` (inicio UpiixSol) | Hero, clubes, eventos próximos y marca del sitio editable | 🟡 |
| HOME-02 | Abrir `/clubes` y `/academias` | Se listan todas las academias activas con su logo y su color | 🟡 |
| HOME-03 | Entrar a `/a/:slug` de UpiixSol y de UpiixIA | Cada una usa su propia paleta, logo y mascota | ✅ |
| HOME-04 | Cambiar de club con el ClubSwitcher | El tema cambia sin recargar y sin parpadeo del tema anterior | 🟡 |
| HOME-05 | Academia sin logo | Se ve el wordmark de texto con la misma altura que un logo | ✅ |
| HOME-06 | Abrir un slug que no existe (`/a/no-existe`) | Pantalla 404 amable, sin crash | ❌ |
| HOME-07 | "Unirme al club" y "Salir del club" como member | Cambia el estado de inscripción y lo que puede hacer en comunidad | 🟡 |
| HOME-08 | Medir el layout shift al cargar el inicio y la academia | Sin saltos visibles (test_layout_stability) | ✅ |

## 4. Aprendizaje: rutas, módulos, clases y progreso

| ID | Pasos | Esperado | Auto |
|---|---|---|---|
| LRN-01 | Abrir `/a/:slug/rutas`, luego una ruta, un módulo y una clase | La navegación es completa y el orden respeta el que puso el admin | 🟡 |
| LRN-02 | Reproducir una clase de YouTube en el Player | El video carga y se ve la miniatura | ❌ |
| LRN-03 | Marcar una clase como completada, **recargar** | El % de la ruta sube y se mantiene tras recargar (criterio de aceptación Alto) | ✅ |
| LRN-04 | Desmarcar la clase completada | El % baja | 🟡 |
| LRN-05 | Completar todas las clases de una ruta | Queda al 100 % y se ve como terminada | ❌ |
| LRN-06 | Navegación anterior/siguiente en el Player | Salta bien entre clases y entre módulos | ❌ |
| LRN-07 | Clase con texto o markdown con `<script>` o un `onerror` | Se sanitiza y no se ejecuta nada | 🟡 |
| LRN-08 | Visitante sin sesión intenta completar una clase | Le pide login y no se guarda nada | ❌ |

## 5. Panel de academia (`/panel/academia/:slug`)

| ID | Pasos | Esperado | Auto |
|---|---|---|---|
| ADM-01 | Crear, editar y borrar ruta, módulo y clase | Funciona, y el borrado pide confirmación | ✅ |
| ADM-02 | Reordenar rutas, módulos y clases (flechas o arrastre) | El orden persiste al recargar y se ve igual en el lado del alumno | 🟡 |
| ADM-03 | Editar el branding (colores, logo, mascota) | Se ve en vivo en `/a/:slug` | ✅ |
| ADM-04 | Elegir colores con mal contraste | Advierte o bloquea por WCAG AA | ❌ |
| ADM-05 | Gestionar inscripciones (agregar o quitar miembros) | La lista se actualiza y el miembro gana o pierde acceso | 🟡 |
| ADM-06 | Editar el inicio de la academia (`PUT /home`) | Los cambios se ven en el inicio del club | 🟡 |
| ADM-07 | Subir recursos (archivo y enlace), editarlos y borrarlos | Aparecen en `/a/:slug/recursos` y se pueden descargar | 🟡 |
| ADM-08 | Crear, editar y borrar eventos | Aparecen en `/a/:slug/eventos` y en `/calendario` | 🟡 |
| ADM-09 | Ver las analíticas de la academia | Los números cuadran con los datos del seed | ❌ |

## 6. Superadmin (`/admin`)

| ID | Pasos | Esperado | Auto |
|---|---|---|---|
| SUP-01 | Crear una academia nueva con su tema y canal **sin tocar código** | Aparece en clubes, con su paleta y su canal en comunidad (criterio Alto) | ✅ |
| SUP-02 | Crear un usuario, cambiarle el rol o la academia y resetearle la contraseña | Funciona y la contraseña temporal no se muestra en logs | 🟡 |
| SUP-03 | Desactivar o editar una academia | Deja de verse o se actualiza en todas partes | 🟡 |
| SUP-04 | Editar la marca del sitio (SiteBrandTab: nombre, logo, mascota, colores) | Login, inicio y header usan la marca nueva **sin redeploy** | ✅ |
| SUP-05 | Quitar el logo o la mascota del sitio | Vuelve al wordmark o al valor por defecto, sin imagen rota | 🟡 |
| SUP-06 | Paginación de usuarios con más de 50 registros | El cursor funciona, sin duplicados ni saltos | 🟡 |

## 7. Comunidad y moderación

| ID | Pasos | Esperado | Auto |
|---|---|---|---|
| COM-01 | Ver los canales Feed, General y uno por academia | Aparecen los tres tipos (criterio Medio) | ✅ |
| COM-02 | Un member inscrito publica en el canal de su club | Se publica | ✅ |
| COM-03 | Un member **no** inscrito publica en el canal de otro club | 403, y la UI le ofrece "Unirme al club" | 🟡 |
| COM-04 | Publicar en General sin estar en ningún club | Se publica | 🟡 |
| COM-05 | Post con imagen, comentarios y borrar mis propios posts | Funciona | 🟡 |
| COM-06 | El admin o el superadmin oculta un post o comentario | Desaparece para los members y el autor ya no puede borrarlo (auditoría) | ✅ |
| COM-07 | Ver una imagen oculta (`hidden-image`) como member y como moderador | El member recibe 403 y el moderador la ve | 🟡 |
| COM-08 | Scroll infinito en un canal con muchos posts | Pagina con cursor y sin duplicados | 🟡 |
| COM-09 | Post con HTML o JS malicioso | Se sanitiza con nh3 y DOMPurify | 🟡 |
| COM-10 | Spam de posts (muchos seguidos) | Rate limit con 429 | ❌ |

## 8. Reacciones

| ID | Pasos | Esperado | Auto |
|---|---|---|---|
| REA-01 | Reaccionar y quitar la reacción en un post | El contador sube y baja, y persiste al recargar | 🟡 |
| REA-02 | Doble clic rápido en la reacción | No se duplica (la operación es idempotente) | ❌ |
| REA-03 | `GET /reactions/mine` | Marca mis reacciones como activas | 🟡 |

## 9. Recursos, eventos y calendario

| ID | Pasos | Esperado | Auto |
|---|---|---|---|
| RES-01 | Descargar un recurso como member | Descarga bien, con el nombre y el tipo correctos | ❌ |
| RES-02 | Subir un archivo prohibido (`.exe`, `.html` o uno de más de 10 MB) | Se rechaza con un mensaje claro | 🟡 |
| EVT-01 | Ver `/calendario` con eventos de varios clubes | Aparecen en la fecha y hora correctas (zona America/Mexico_City) | ❌ |
| EVT-02 | Evento pasado frente a evento próximo | El inicio solo muestra los próximos | 🟡 |

## 10. Cuenta (`/cuenta`)

| ID | Pasos | Esperado | Auto |
|---|---|---|---|
| ACC-01 | Editar el nickname y el avatar | Se ve en el header y en mis posts | 🟡 |
| ACC-02 | Cambiar el correo (pide la contraseña actual) | Funciona. Con una contraseña mala da error, y un correo duplicado da 409 | 🟡 |
| ACC-03 | Cambiar la contraseña y luego entrar con la nueva | Las otras sesiones (refresh tokens) quedan invalidadas | 🟡 |
| ACC-04 | Subir un avatar que no es imagen o es muy pesado | Se rechaza, y Pillow re-encodea la imagen | 🟡 |

## 11. Blog y galería

| ID | Pasos | Esperado | Auto |
|---|---|---|---|
| BLG-01 | Crear, editar y borrar una entrada de blog con portada | Se ve en `/blog` y en `/blog/:slug` | 🟡 |
| BLG-02 | Crear, editar y borrar un proyecto de galería con portada | Se ve en `/galeria` y en `/galeria/:slug` | 🟡 |
| BLG-03 | Abrir un slug inexistente de blog o galería | 404 amable | ❌ |
| BLG-04 | El editor rico produce contenido con scripts | Se sanitiza | 🟡 |

## 12. Móvil y responsive

| ID | Pasos | Esperado | Auto |
|---|---|---|---|
| MOB-01 | Recorrer todas las rutas de arriba a 375 px | Sin scroll horizontal, sin texto cortado y con objetivos táctiles de 44 px o más | 🟡 |
| MOB-02 | Usar el menú, el ClubSwitcher y los modales en móvil | Abren y cierran, y atrapan el foco | ❌ |
| MOB-03 | Usar el Player y el panel admin en móvil | Son usables (tablas con scroll interno, no de página) | ❌ |
| MOB-04 | Orientación horizontal en el teléfono | Sin roturas | ❌ |

## 13. Accesibilidad y contraste

| ID | Pasos | Esperado | Auto |
|---|---|---|---|
| A11Y-01 | Pasar axe o Lighthouse en el inicio, la academia, el Player, la comunidad, la cuenta y el admin | 0 violaciones serias y Accessibility de 90 o más | ❌ |
| A11Y-02 | Navegar solo con teclado (Tab, Enter y Esc) | Todo es alcanzable y el foco siempre es visible | 🟡 |
| A11Y-03 | Contraste de las paletas UpiixSol (#00BF63, #04944F, #F28034, #B4422F) y UpiixIA sobre fondo claro | Texto con AA (4.5:1) o texto grande con 3:1 | ❌ |
| A11Y-04 | Activar `prefers-reduced-motion` | No hay animaciones grandes | 🟡 |
| A11Y-05 | Lector de pantalla (NVDA) en el login y en el Player | Etiquetas y roles correctos | ❌ |

## 14. Seguridad

| ID | Pasos | Esperado | Auto |
|---|---|---|---|
| SEC-01 | Mandar un JSON con campos extra a un endpoint | 422 (`extra="forbid"`) | ✅ |
| SEC-02 | Probar IDOR: cambiar IDs en la URL o el body para tocar datos de otro usuario o academia | 403 o 404 | 🟡 |
| SEC-03 | Subir un archivo con extensión falsa (un `.png` que en realidad es HTML o SVG con script) | Se rechaza o se re-encodea, y nunca se sirve como `text/html` | 🟡 |
| SEC-04 | Revisar los headers de producción (CORS solo a los orígenes de `CORS_ORIGINS`, cookies `Secure`/`HttpOnly` si aplica) | Correctos | ❌ |
| SEC-05 | Hacer `git grep` de secretos y revisar que `.env.example` no tenga valores reales | Limpio | ❌ |
| SEC-06 | Revisar que las contraseñas en la BD estén en argon2id | Ningún texto plano | ✅ |
| SEC-07 | Revisar que los errores 500 no filtren stack traces al cliente | Solo JSON uniforme | 🟡 |

## 15. Deploy (Render + Neon), según `docs/deploy-render.md`

| ID | Pasos | Esperado | Auto |
|---|---|---|---|
| DEP-01 | Deploy limpio en staging | Las migraciones corren solas, `/api/health` y `/api/ready` responden ok | ❌ |
| DEP-02 | Cold start de Render (servicio dormido) | El primer request carga en menos de 60 s sin error en la UI | ❌ |
| DEP-03 | Las imágenes subidas sobreviven a un redeploy | El `MEDIA_DIR` es persistente (disco o almacenamiento externo) | ❌ |
| DEP-04 | Deep links en producción (`/a/x/clases/1` al recargar) | Sirven el SPA, no un 404 | ❌ |
| DEP-05 | Backup y restore de Neon según `docs/runbook.md` | Funciona | ❌ |

## 16. Flujo completo de punta a punta (demo)

Corre este flujo de una sola vez, en móvil y en escritorio:
1. El superadmin crea la academia "Club Demo" con su tema y crea a su admin.
2. El admin de Club Demo crea una ruta con 1 módulo y 2 clases, sube un recurso y crea un evento.
3. Un member se registra o entra, se une a Club Demo y completa 1 clase. Al recargar ve 50 %.
4. El member publica en el canal de Club Demo y otro usuario reacciona y comenta.
5. El admin oculta el comentario. El member ya no lo ve.
6. El admin de UpiixSol intenta editar Club Demo y recibe 403.
7. El superadmin cambia la marca del sitio y el login la refleja sin redeploy.

**Esperado:** todo sin errores en la consola ni 500 en la red. ✅ (`e2e/test_flow.py`, en parte)

---

## Propuesta de tareas para el kit (pendiente de tu revisión)

| Tarea | Cubre | Prioridad |
|---|---|---|
| QA de permisos: test de la matriz completa por API | ROL-01…07, SEC-02 | P0 |
| QA de aprendizaje y Player: e2e de progreso, navegación y 100 % | LRN-01…08 | P0 |
| QA de auth y sesión: e2e de refresh, logout, redirect y rate limit | AUTH-01…07 | P0 |
| QA de comunidad, moderación y reacciones: e2e y límites | COM-01…10, REA-01…03 | P1 |
| QA del panel admin y el superadmin: e2e de CRUD, orden, inscripciones y analíticas | ADM-01…09, SUP-01…06 | P1 |
| QA de recursos, eventos, cuenta, blog y galería | RES, EVT, ACC, BLG | P1 |
| QA móvil y accesibilidad: axe en e2e, contraste de paletas y teclado | MOB-01…04, A11Y-01…05 | P1 |
| QA de seguridad y uploads | SEC-01…07, RES-02, ACC-04 | P0 |
| QA de deploy en staging: checklist Render + Neon | DEP-01…05, P0-06/07 | P0 |

Cada tarea sería de tipo `bug` o `integration`, con sus `Paths` en `app/tests/test_qa_*.py` o `e2e/test_qa_*.py` y un `Verify` exacto. Los bugs que salgan se abren como tareas nuevas o `uak followup`.
