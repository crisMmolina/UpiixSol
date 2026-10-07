# DESIGN · UpiixSol Campus

> Única dirección visual del proyecto (owner: UPS-002). Fuente: `IDEA.md` §0.1. Provisional hasta que UPS-004 la aterrice en `web/src/index.css`; cambios por `uak msg UPS-002 --kind request`.

## Personalidad
Club estudiantil, cálido y cercano: **redondeado, grueso y alegre**, como el wordmark y el ajolote. Nada corporativo ni oscuro. Mucho aire, tarjetas suaves, acentos de color con intención (no fondos completos de marca).

## Tema (solo claro en v1)
| Token CSS | Valor | Uso |
|---|---|---|
| `--color-bg` | `#FBF8EF` | Fondo de página (crema cálido, igual al fondo de la mascota UpiixSol) |
| `--color-surface` | `#FFFFFF` | Tarjetas, paneles, sidebar del reproductor |
| `--color-text` | `#1F2A24` | Texto principal (13.98:1 sobre crema) |
| `--color-muted` | `#5B6B62` | Texto secundario, metadatos (5.31:1 sobre crema) |
| `--color-border` | `#E7E2D3` | Bordes de tarjetas y separadores |
| `--color-video` | `#111714` | Solo el recuadro del video (el reproductor sigue en claro) |

## Marca por academia (variables cargadas de la BD)
El campus raíz usa la paleta UpiixSol. Al entrar a `/a/{slug}`, `AcademyTheme` (UPS-004) sobrescribe estas variables con los colores de la academia (`GET /api/academies/{slug}` → `AcademyBranding`).

| Variable | UpiixSol (raíz) | UpiixIA | Uso |
|---|---|---|---|
| `--academy-primary` | `#00BF63` | `#00BF63` | Botón primario (fondo), barras de progreso, checks |
| `--academy-secondary` | `#04944F` | `#04944F` | Hover del primario, encabezados grandes, bordes activos |
| `--academy-accent` | `#F28034` | `#7ED957` | Badges, resaltados, ilustración |
| `--academy-accent-2` | `#B4422F` | — (cae a `--academy-secondary`) | Activo/hover del naranja, avisos, badges de alerta |
| `--academy-logo` | `/brand/upiixsol/wordmark.png` | `/brand/upiixia/wordmark.png` | Header |

`#FFDE59` **no** es color de marca (error en la imagen de paleta; IDEA §0.1).

## Contraste (WCAG AA, calculado el 2026-10-06)
| Combinación | Ratio | Veredicto | Regla |
|---|---|---|---|
| Blanco sobre `#00BF63` | 2.43 | ❌ | **Nunca** texto blanco sobre el verde primario |
| `#1F2A24` sobre `#00BF63` | 6.10 | ✅ | Texto de botón primario = oscuro, negritas |
| Blanco sobre `#04944F` | 3.92 | ⚠️ solo texto ≥ 18.66 px bold | Botones grandes / chips en negritas |
| `#1F2A24` sobre `#F28034` | 5.59 | ✅ | Texto sobre naranja = oscuro |
| Blanco sobre `#F28034` | 2.65 | ❌ | Prohibido |
| Blanco sobre `#B4422F` | 5.58 | ✅ | Badges/avisos terracota con texto blanco |
| `#1F2A24` sobre `#7ED957` | 8.45 | ✅ | Acento UpiixIA con texto oscuro |
| `#04944F` sobre crema | 3.69 | ⚠️ solo texto grande | Títulos grandes en verde |
| `#037A41` sobre crema / blanco | 5.12 / 5.43 | ✅ | **Enlaces y texto verde normal** (`--color-link`) |
| `#00BF63` / `#F28034` sobre crema | 2.29 / 2.50 | ❌ como texto | Solo iconos decorativos, barras, bordes |

Como los colores de cada academia vienen de la BD, `AcademyTheme` debe calcular el color de texto sobre `--academy-primary` (oscuro `#1F2A24` o blanco, el que dé ≥ 4.5:1) y exponerlo como `--academy-on-primary`. El panel de identidad (UPS-008/009) avisa si un color elegido no logra AA.

## Tipografía
- Títulos: **Fredoka** 600/700 (`@fontsource/fredoka`), redondeada como el wordmark. `h1` 2.25rem móvil / 3rem escritorio; `h2` 1.75rem; `h3` 1.25rem.
- Cuerpo y UI: **Inter Variable** (`@fontsource-variable/inter`) 400/500/600, 16 px base, `line-height` 1.6 en texto largo.
- Números (porcentajes, contadores): Inter con `font-variant-numeric: tabular-nums`.

## Forma, espacio y profundidad
- Radios: tarjetas `1.25rem`, botones `9999px` (píldora), inputs `0.75rem`, video `1rem`.
- Sombra única suave: `0 1px 2px rgb(31 42 36 / 6%), 0 8px 24px rgb(31 42 36 / 6%)`; hover de tarjeta sube 2 px.
- Espaciado en múltiplos de 4 px; contenedor máx. `72rem`, gutter `1rem` móvil / `2rem` escritorio.
- Iconos: `@phosphor-icons/react`, peso `bold` en navegación, `regular` en texto, 20–24 px.

## Componentes clave
- **Botón primario**: fondo `--academy-primary`, texto `--academy-on-primary` en negritas, hover `--academy-secondary`. Secundario: borde 2 px `--academy-secondary`, texto `--color-link`.
- **Tarjeta de academia**: superficie blanca, franja superior de 6 px con `--academy-primary`, logo de la academia, descripción corta, chip "Inscrito".
- **Barra de progreso**: pista `#E7E2D3`, relleno `--academy-primary`, porcentaje en texto oscuro al lado (no dentro de la barra).
- **Reproductor** (layout de `docs/ref/player-reference.png`, sin copiar su marca): sidebar blanco a la izquierda (título de ruta, barra + %, buscador, módulos plegables con `x/y` y check), área principal con video 16:9 en `--color-video`, botones Anterior / Siguiente / Marcar como completada, "Descripción" y "Recursos de la clase". En móvil el sidebar es un drawer.
- **Comunidad**: columna de canales (Feed, General, uno por academia con un punto de su color), posts en tarjetas, autor = avatar + nickname.
- **Estados**: cada vista de datos tiene skeleton (carga), vacío (con la mascota de la academia y una acción) y error (mensaje + reintentar).

## Mascotas y logos
- Usar los archivos de `web/public/brand/` tal cual (`IDEA.md` §0.1: no redibujar ni recrear en SVG).
- Las mascotas traen fondo propio (crema la de UpiixSol, verde muy claro la de UpiixIA): colocarlas sobre tarjetas o bloques del mismo tono, nunca sobre fondos que choquen.
- Wordmarks: altura 32 px en header móvil, 40 px escritorio; siempre con `alt` ("UpiixSol" / nombre de la academia).

## Movimiento
`motion/react` con transiciones cortas (150–250 ms, `ease-out`): cambio de tema de academia (cross-fade de colores 200 ms), aparición de tarjetas, check de "completada". Todo se desactiva con `prefers-reduced-motion: reduce`.

## Accesibilidad y responsive
- Foco visible: anillo 3 px `--academy-secondary` con `outline-offset: 2px`.
- Objetivos táctiles ≥ 44 px. Diseñar primero a 390 px; probar también a 1280 px.
- `lang="es-MX"`, textos de UI en español (México), fechas con `Intl.DateTimeFormat("es-MX")`.
