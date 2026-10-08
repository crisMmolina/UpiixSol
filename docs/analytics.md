# Analítica de uso (UPS-037)

Registramos **qué hacen y qué usan** los alumnos en una sola tabla de la base de datos, `activity_events`,
pensada para que después se construya un dashboard encima y para que el flujo pueda moverse a un
almacén de datos (warehouse) sin cambiar a quien lo produce.

- Código: `app/models/analytics.py`, `app/services/analytics.py`, `app/routers/analytics.py`,
  el middleware de `app/main.py` y el tracker web `web/src/lib/analytics.ts`.
- Interruptor: `ANALYTICS_ENABLED=false` apaga todo (servidor y endpoint). Sin definir, está encendido en
  `dev`/`prod` y apagado con `ENV=test`, para que el resto de las pruebas no escriba en la base local;
  `app/tests/test_analytics.py` lo enciende.

## Cómo se capturan los eventos

### Servidor (sin tocar los routers de otras tareas)

`request_context` en `app/main.py` llama a `analytics.capture(request, response)` en cada petición:

1. Si la respuesta no es 2xx, o la analítica está apagada, no hace nada.
2. Busca la plantilla de la ruta que respondió (`request.scope["route"].path`) y el método en la tabla
   `SERVER_EVENTS`. Si no está, no hace nada.
3. Toma `user_id` de `request.state.user_id` (lo pone la dependencia de auth) y los parámetros de la ruta.
4. Agrega una `BackgroundTask` a la respuesta: **la escritura ocurre después de enviar la respuesta**,
   en el thread pool, con su propia sesión corta (`session_factory`, por defecto `app.db.SessionLocal`).
   Ahí resuelve el club (`academy_id`) del sujeto (lección → módulo → ruta → club, post → canal → club…).
5. Cualquier excepción, al programar o al escribir, se registra en el logger `app.analytics` y se descarta:
   la petición nunca se rompe ni se hace más lenta por la analítica.

Login y registro no pasan por la dependencia de auth: el usuario se obtiene del hash de la cookie de
refresh que la misma respuesta acaba de crear (`refresh_tokens.token_hash`), también en segundo plano.

### Cliente web

`POST /api/analytics/events` (202 `{accepted}`), solo con sesión iniciada (`current_user`):

```json
{
  "session_id": "3f1c…",
  "events": [
    {"name": "page.view", "path": "/a/:slug/clases/:lessonId", "academy_slug": "upiixia"},
    {"name": "video.play", "subject_type": "lesson", "subject_id": 12, "properties": {"position_s": 42}}
  ]
}
```

- Máximo 50 eventos por lote; `properties` plano (texto, número, booleano o null), máximo 2 KB por evento y
  sin claves personales (`email`, `boleta`, `name`, `full_name`, `nickname`, `phone`, `password`, `token`,
  `query`). Nombre fuera de la lista → 422. Campos desconocidos → 422.
- `occurred_at` opcional; se recorta a ahora ± 5 min (los relojes de los clientes mienten). Sin zona = UTC.
- `path` es la **plantilla** de la ruta del front, nunca la URL con ids. Se guarda en `properties.path`.
- `academy_slug` se convierte a `academy_id` (slug desconocido → `NULL`).
- Límite: 30 lotes por minuto por usuario (slowapi, mismo limitador que el resto).

`web/src/lib/analytics.ts` exporta `track(name, data)`:

- Encola y envía en lotes cada ~10 s o al llegar a 20 eventos, y una vez más cuando la pestaña se oculta
  (`visibilitychange` → hidden, y `pagehide`).
- **Autenticación al ocultar la página:** `navigator.sendBeacon` no puede mandar el header
  `Authorization`, y la cookie de refresh solo viaja a `/api/auth`, así que un beacon llegaría anónimo
  (401). En su lugar se usa `fetch` con `keepalive: true` a través de `api()`, que pone el access token
  que vive en memoria (y renueva una vez si hay 401). `keepalive` sobrevive al cierre de la página igual
  que un beacon; su límite de 64 KB por petición cabe de sobra en un lote típico. No se abre otra vía de
  autenticación (por ejemplo, cookie para `/api/analytics`) para no ampliar la superficie de CSRF.
- `session_id`: un id aleatorio por pestaña en `sessionStorage` (en memoria si no hay storage).
- No hace nada sin sesión (`setAnalyticsUser(null)` vacía la cola), nunca lanza, nunca bloquea la UI y se
  apaga hasta recargar tras un 4xx (lote inválido, 429…). Un 401 o `password_change_required` solo
  descartan el lote.
- `web/src/App.tsx` registra `page.view` en cada navegación con la plantilla de la ruta
  (`/a/:slug/rutas/:routeId`) y el slug del club cuando la ruta está bajo `/a/:slug`, desde un componente
  `<PageViews>` que envuelve todas las rutas.

## Catálogo de eventos

### Servidor (`source = 'server'`)

| Evento | Ruta (plantilla) | Sujeto | `properties` |
|---|---|---|---|
| `auth.login` | `POST /api/auth/login` | — | — |
| `auth.registered` | `POST /api/auth/register` | — | — |
| `club.viewed` | `GET /api/academies/{slug}/home` | `academy` | — |
| `club.joined` | `POST /api/academies/{slug}/enroll` | `academy` | — |
| `club.left` | `DELETE /api/academies/{slug}/enroll` | `academy` | — |
| `route.viewed` | `GET /api/routes/{route_id}` | `route` | — |
| `lesson.viewed` | `GET /api/lessons/{lesson_id}` | `lesson` | — |
| `lesson.completed` | `POST /api/lessons/{lesson_id}/complete` | `lesson` | — |
| `lesson.uncompleted` | `DELETE /api/lessons/{lesson_id}/complete` | `lesson` | — |
| `post.created` | `POST /api/channels/{channel_id}/posts` | `channel` | — |
| `comment.created` | `POST /api/posts/{post_id}/comments` | `post` | — |
| `reaction.added` | `PUT /api/posts/{post_id}/reactions/{kind}` | `post` | `kind` |
| `reaction.removed` | `DELETE /api/posts/{post_id}/reactions/{kind}` | `post` | `kind` |

No hay una ruta GET por recurso ni por archivo (los archivos se sirven desde `/media` sin sesión), así que
la apertura de recursos se registra desde el cliente (`resource.opened`). Si más adelante se agrega
`GET /api/resources/{resource_id}/open` (redirección), basta con sumarla a `SERVER_EVENTS`.

### Web (`source = 'web'`)

| Evento | Cuándo | Sujeto sugerido | `properties` sugeridas |
|---|---|---|---|
| `page.view` | cada navegación (automático) | — | `path` (plantilla) |
| `video.play` | el reproductor arranca | `lesson` | `position_s` |
| `video.pause` | pausa | `lesson` | `position_s` |
| `video.ended` | el video termina | `lesson` | `duration_s` |
| `video.progress` | hitos 25/50/75 % | `lesson` | `percent` |
| `search.performed` | búsqueda en el reproductor o listados | — | `scope`, `query_length`, `results` (nunca el texto) |
| `resource.opened` | clic en un recurso | `resource` | `type` |
| `link.opened` | clic en un enlace de una clase | `lesson` | `position` |

Puntos de llamada sugeridos (archivos de otras tareas; solo hay que importar `track`):

- `web/src/features/learning/` (reproductor, UPS-038): `video.play/pause/ended/progress` desde los
  eventos del IFrame Player de YouTube, `link.opened` en los enlaces de la clase y `search.performed`
  en el buscador de clases.
- `web/src/features/resources/`: `resource.opened` al abrir la tarjeta (`subject_id` = id del recurso,
  `academy_slug` = slug del club, `properties.type`).
- Buscadores de comunidad, galería o blog: `search.performed` con `query_length` y `results`.

Agregar un evento web nuevo = sumarlo a `WEB_EVENTS` (backend) y a `WebEventName` (front) y a esta tabla.

## Esquema

`activity_events` (migración `0005`, solo se inserta; la app nunca actualiza ni borra filas):

| Columna | Tipo | Notas |
|---|---|---|
| `id` | `BIGINT` PK (INTEGER en SQLite) | autoincremental |
| `occurred_at` | `TIMESTAMPTZ` (UTC) | servidor: hora de la respuesta; web: hora del cliente recortada |
| `user_id` | `INTEGER` NULL, FK `users` `ON DELETE SET NULL` | |
| `academy_id` | `INTEGER` NULL, FK `academies` `ON DELETE SET NULL` | club del evento |
| `name` | `VARCHAR(40)` | de la lista de arriba |
| `subject_type` | `VARCHAR(20)` NULL | `lesson`, `route`, `academy`, `post`, `channel`, `resource`… |
| `subject_id` | `INTEGER` NULL | id del sujeto |
| `properties` | `JSON` | pequeño, sin datos personales |
| `session_id` | `VARCHAR(64)` NULL | id de pestaña (solo web) |
| `source` | `VARCHAR(10)` | `server` o `web` (CHECK) |

Índices: `(occurred_at)`, `(name, occurred_at)`, `(user_id, occurred_at)`, `(academy_id, occurred_at)`.
Toda consulta del dashboard debe acotar `occurred_at` para aprovecharlos.

## Consultas de ejemplo para el dashboard (PostgreSQL)

Horas en hora de Ciudad de México; en SQLite cambiar `date_trunc` por `date(occurred_at)` /
`strftime('%Y-%W', occurred_at)`.

**Usuarios activos por día (últimos 30 días)**

```sql
SELECT date_trunc('day', occurred_at AT TIME ZONE 'America/Mexico_City') AS dia,
       count(DISTINCT user_id) AS usuarios_activos
FROM activity_events
WHERE occurred_at >= now() - interval '30 days' AND user_id IS NOT NULL
GROUP BY 1 ORDER BY 1;
```

**Embudo de avance por ruta: vio la ruta → vio una clase → completó una → completó todas**

```sql
WITH lecciones AS (
  SELECT l.id AS lesson_id, m.route_id
  FROM lessons l JOIN modules m ON m.id = l.module_id
  WHERE l.is_published
), total AS (
  SELECT route_id, count(*) AS n FROM lecciones GROUP BY route_id
), ev AS (
  SELECT e.user_id, e.name, coalesce(lx.route_id, CASE WHEN e.subject_type = 'route' THEN e.subject_id END) AS route_id,
         e.subject_id
  FROM activity_events e
  LEFT JOIN lecciones lx ON e.subject_type = 'lesson' AND lx.lesson_id = e.subject_id
  WHERE e.occurred_at >= now() - interval '90 days'
    AND e.name IN ('route.viewed', 'lesson.viewed', 'lesson.completed')
), completas AS (
  SELECT ev.route_id, ev.user_id
  FROM ev JOIN total t ON t.route_id = ev.route_id
  WHERE ev.name = 'lesson.completed'
  GROUP BY ev.route_id, ev.user_id, t.n
  HAVING count(DISTINCT ev.subject_id) = t.n
)
SELECT r.title,
       count(DISTINCT ev.user_id) FILTER (WHERE ev.name = 'route.viewed')     AS vieron_ruta,
       count(DISTINCT ev.user_id) FILTER (WHERE ev.name = 'lesson.viewed')    AS vieron_clase,
       count(DISTINCT ev.user_id) FILTER (WHERE ev.name = 'lesson.completed') AS completaron_una,
       (SELECT count(*) FROM completas c WHERE c.route_id = r.id)             AS completaron_todas
FROM learning_routes r LEFT JOIN ev ON ev.route_id = r.id
GROUP BY r.id, r.title ORDER BY vieron_ruta DESC;
```

(Las desmarcadas, `lesson.uncompleted`, no restan aquí; para el estado actual usar `lesson_progress`.)

**Recursos más abiertos (últimos 30 días)**

```sql
SELECT r.id, r.title, a.name AS club, count(*) AS aperturas, count(DISTINCT e.user_id) AS usuarios
FROM activity_events e
JOIN resources r ON r.id = e.subject_id
JOIN academies a ON a.id = r.academy_id
WHERE e.name = 'resource.opened' AND e.subject_type = 'resource'
  AND e.occurred_at >= now() - interval '30 days'
GROUP BY r.id, r.title, a.name ORDER BY aperturas DESC LIMIT 20;
```

**Posts por club por semana**

```sql
SELECT date_trunc('week', e.occurred_at AT TIME ZONE 'America/Mexico_City') AS semana,
       coalesce(a.name, 'General') AS club,
       count(*) AS posts
FROM activity_events e LEFT JOIN academies a ON a.id = e.academy_id
WHERE e.name = 'post.created' AND e.occurred_at >= now() - interval '12 weeks'
GROUP BY 1, 2 ORDER BY 1, 2;
```

**Usuarios activos por club (últimos 7 y 30 días)**

```sql
SELECT a.name AS club,
       count(DISTINCT e.user_id) FILTER (WHERE e.occurred_at >= now() - interval '7 days') AS activos_7d,
       count(DISTINCT e.user_id) AS activos_30d
FROM activity_events e JOIN academies a ON a.id = e.academy_id
WHERE e.occurred_at >= now() - interval '30 days' AND e.user_id IS NOT NULL
GROUP BY a.name ORDER BY activos_30d DESC;
```

## Retención y crecimiento

- Volumen esperado: decenas de eventos por alumno por sesión. Con cientos de alumnos, millones de filas
  al año: la tabla aguanta, pero conviene planearlo desde ya.
- **Particionar por mes** en PostgreSQL cuando pase de ~10 M filas: `PARTITION BY RANGE (occurred_at)`,
  una partición por mes (con `pg_partman` o un job mensual). Borrar o archivar un mes completo es un
  `DETACH PARTITION` instantáneo en lugar de un `DELETE` masivo.
- **Archivar**: conservar en línea 12–13 meses (comparación año contra año) y exportar lo anterior a
  archivos Parquet/CSV comprimidos en almacenamiento de objetos antes de borrar la partición.
- Para el dashboard, crear vistas materializadas diarias (DAU, posts por club) y refrescarlas por cron, en
  lugar de recorrer la tabla cruda en cada carga.
- Al borrar un usuario o un club, sus eventos se conservan con `user_id`/`academy_id` en `NULL`
  (anonimizados), así los totales históricos no cambian.

## Mover el flujo a un warehouse

Quien produce los eventos (middleware y endpoint) no cambia; solo cambia a dónde se copian:

1. **Exportación por rangos de `occurred_at`** (lo más simple): un job diario exporta el día anterior
   (`WHERE occurred_at >= :desde AND occurred_at < :hasta`, ordenado por `id`) a Parquet y lo carga en
   BigQuery/Snowflake/DuckDB. Como la tabla es append-only, `id` también sirve como cursor incremental
   (`id > :ultimo_id`). Dejar un margen de unos minutos por los eventos web recortados a ±5 min.
2. **CDC** (cuando se necesite casi tiempo real): replicación lógica de PostgreSQL (Debezium o el
   conector nativo del warehouse) sobre `activity_events`; al ser solo inserciones, el flujo es trivial.
3. Si el volumen crece mucho, `write_server_event` y `record_web_events` pueden publicar a una cola
   (Kafka, Pub/Sub, SQS) en lugar de insertar; el contrato del evento (nombre, sujeto, propiedades) es el
   mismo de esta tabla.

## Privacidad

- `properties` nunca lleva datos personales: ni nombre, ni correo, ni boleta, ni texto libre (por eso
  `search.performed` guarda la longitud de la búsqueda y no el texto). El backend rechaza las claves
  personales conocidas, pero el contrato es "solo ids, slugs, plantillas de ruta y contadores".
- Las rutas se guardan como plantillas (`/a/:slug/clases/:lessonId`), no como URLs con ids o parámetros.
- No se guardan IP ni user agent.
- **Aviso de privacidad:** el texto actual del registro (`web/src/features/auth/index.tsx`, otra tarea)
  solo habla de boleta y correo. Debe agregar algo como: *"Registramos de forma interna cómo usas el campus
  (páginas, clases vistas y completadas, publicaciones) para mejorarlo; no se comparte con terceros"*.
  Pendiente para el dueño de ese archivo.
- Acceso a la tabla: solo superadmins (vía dashboard futuro) y operación. Un admin de club solo debería ver
  agregados de su club.
