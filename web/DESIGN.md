# DESIGN · UpiixSol Campus (v2)

> Única dirección visual del proyecto (owner: UPS-021). Tokens en `web/src/index.css`. v2 nace del feedback del 2026-10-08 y de un campus de cursos de referencia: menos ruido visual, app (no sitio web), blanco puro.

**Design read:** campus de aprendizaje para estudiantes del club, lenguaje limpio de app de cursos, poco ruido y color con intención. Dials (skill `design-taste-frontend`): VARIANCE 5 · MOTION 4 · DENSITY 4.

## Terminología
- La palabra visible es **Club / Clubes**. Nunca "Academia" en textos de UI o mensajes del API. Los nombres internos (`/a/:slug`, `academy_id`, `--academy-*`) se quedan.

## Tema claro (por defecto)
| Token | Valor | Uso | Contraste |
|---|---|---|---|
| `--color-bg` | `#FFFFFF` | Panel de contenido (blanco puro) | |
| `--color-subtle` | `#F5F6F7` | Riel lateral, barra superior, fondos de chips | |
| `--color-surface` | `#FFFFFF` | Tarjetas, menús, paneles | |
| `--color-ink` | `#16181D` | Texto principal | 17.76:1 sobre blanco |
| `--color-muted` | `#5E6470` | Texto secundario | 5.94:1 blanco · 5.49:1 subtle |
| `--color-line` | `#E6E8EB` | Bordes y separadores | |
| `--color-link` | `#037A41` | Enlaces y texto verde | 5.43:1 blanco · 5.02:1 subtle |

Un solo gris (frío, neutral). Nada de beige.

## Tema oscuro (vista de curso)
`[data-theme="dark"]` en el contenedor redefine los mismos tokens; los componentes no cambian.

| Token | Valor | Contraste |
|---|---|---|
| bg / surface / subtle | `#121417` / `#1B1E22` / `#16191C` | |
| ink | `#E8EAED` | 13.88:1 sobre surface |
| muted | `#9BA3AD` | 6.56:1 sobre surface |
| line | `#2B3036` | |
| link | `#3DD68C` | 8.92:1 sobre surface (`#037A41` no pasa en oscuro) |

## Color de cada club
`--academy-primary/secondary/accent/accent-2` vienen de la BD (`AcademyTheme`). Texto sobre el primario = `--academy-on-primary` calculado (oscuro sobre `#00BF63`, 7.3:1). El color de marca se usa con intención: botón primario, barras de progreso, portadas de rutas y el ícono activo; no como fondo de páginas.

## Estructura de la app
- **Escritorio:** riel de íconos a la izquierda (`5.5rem`, ícono en cuadro de 40 px con la etiqueta debajo), barra superior delgada (logo, selector de club, campana, menú de usuario) sobre `subtle`, y el contenido en un panel blanco con esquina superior izquierda redondeada.
- **Teléfono:** barra superior + barra inferior de pestañas (máx. 5; la quinta es "Más" si hay más secciones).
- **Club:** el riel cambia a las secciones del club (Inicio, Rutas, Recursos, Comunidad, Eventos) con **Campus** fijo arriba para volver; el selector de club (⇅ junto al logo) salta entre clubes y el campus.
- **Sin footer.** Es una app.

## Notificaciones
`useNotifications().notify({...})`. El aviso aparece como **una tarjeta compacta encima de la barra superior** (solo el más reciente: título + acción en una línea; el texto completo queda en la campana) y se va solo (6 s). En escritorio va centrado en la barra (26 rem); en teléfono va del borde izquierdo hasta antes de la campana y el menú de usuario, que siguen al alcance. Nunca tapa la página ni sus acciones (`layouts/Notifications.tsx`). La campana muestra el número sin leer y abre un panel lateral derecho con todas. La contraseña provisional vive aquí (una vez por sesión como tarjeta, siempre en la campana).

## Tipografía
- Títulos: **Fredoka** 600 (marca, redondeada). Cuerpo y UI: **Inter Variable** 400/500/600. Números con `tabular-nums`.
- Tamaños contenidos: `h1` 1.875rem móvil / 2.25rem escritorio; jerarquía con peso y color, no con tamaño.

## Forma y profundidad
- Radios: tarjetas `1rem`, campos `0.75rem`, botones píldora, video `1rem`.
- Tarjetas con borde fino y **sin sombra**; la sombra aparece solo al pasar el cursor en tarjetas clicables (sube 2 px).
- Botones: primario con color del club; secundario blanco con borde gris; fantasma sin borde. Presión `scale(0.98)`.

## Movimiento (sutil)
- Entrada de listas escalonada (`.enter` + `--i`, 40 ms por elemento, 260 ms).
- Tarjetas de aviso deslizan desde la derecha; menús aparecen con un fade corto; modales entran con fade + escala y los paneles laterales se deslizan (ver abajo).
- Skeleton con brillo suave. Todo se apaga con `prefers-reduced-motion`.

## Movimiento y estabilidad
Regla: **un mensaje nunca mueve el layout** y lo que aparece o cambia de tamaño **se anima**, nunca "salta". Todo en `@/components`.

| Primitiva | Cuándo | Uso |
|---|---|---|
| `TextField`/`TextArea`/`SelectField` con `reserve` | Campo que puede mostrar error y no tiene `hint` (con `hint` la línea ya existe: el error la reemplaza) | `<TextField label="Correo" reserve error={errors.email} />` |
| `FormMessage` | Error o resultado de un formulario, bajo el botón de enviar; también el "por qué" de un botón deshabilitado (`hint`) | `<FormMessage message={error} tone="error" hint={motivo} lines={1} />` |
| `AnimatedHeight` | Contenedor cuyo contenido cambia de alto (pestañas, pasos, cuerpo de un modal) | `<AnimatedHeight>{tab === "a" ? <A /> : <B />}</AnimatedHeight>` |
| `Stagger` + `StaggerItem` | Campos o tarjetas nuevos tras un cambio (no en la primera carga: `play={cambio}`) | `<Stagger play={switched}><StaggerItem>…</StaggerItem></Stagger>` |
| `Modal` / `Drawer` | Diálogos y paneles; ya animan entrada y salida | `<Modal open={abierto} onClose={…} title="…">` |

- **Espacio reservado:** `FormMessage` guarda `lines` líneas (1 por defecto; 2 donde el texto puede partirse en 390 px). Mensajes cortos en español que quepan en esa línea. Un mensaje nuevo **reemplaza** al anterior (un solo estado por pestaña o formulario), y escribir en el campo borra su error.
- **Anclar arriba:** pantallas cuyo alto cambia (login, modales) se anclan con padding fijo arriba, no se centran en vertical: así el borde superior nunca salta y lo que crece, crece hacia abajo.
- **Modales:** cuelgan a `max(1rem, 8dvh)` del borde superior. Para que se vea la salida, déjalos montados y cambia `open` (`{abierto && <Modal open …>}` cierra sin animación). Enfocan su primer campo solo en escritorio; los `Drawer` enfocan el botón Cerrar (en teléfono un campo abriría el teclado).
- **Duraciones y curva** (`DURATION`, `EASE_OUT`, `EASE_IN`): mensajes 160 ms · entrada de campos y overlays 220 ms · cambio de alto 260 ms · salida 160 ms · escalonado 40 ms. Entrar/crecer con `EASE_OUT` `cubic-bezier(.2,.8,.2,1)` (la misma de `.enter`), salir con `EASE_IN`. Solo `opacity`, `transform` y el alto del contenedor.
- **Movimiento reducido:** cada primitiva usa `useReducedMotion()`: con `prefers-reduced-motion` todo cambia al instante (sin desplazamientos), pero el espacio reservado sigue igual.
- **No usar** `AnimatedHeight` alrededor de menús flotantes (recorta su contenido) ni animar `top`/`margin`/`width`.

## Estados
Cada vista de datos tiene skeleton con la forma final (`SkeletonText`, `CardSkeleton`, `ListSkeleton`, `GridSkeleton`, `SkeletonAvatar`), vacío con la mascota del club y error con reintentar.

## Logos y mascotas
PNG con fondo transparente en `web/public/brand/` (fondo retirado y recortado el 2026-10-08), revisados sobre blanco y sobre oscuro. No redibujar ni recrear en SVG.

## Accesibilidad y responsive
Foco visible (3 px `--academy-secondary`), objetivos táctiles ≥ 44 px, primero 390 px y luego 1280 px, `lang="es-MX"`. Sin guiones largos en textos de UI.
