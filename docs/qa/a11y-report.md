# Reporte QA móvil y accesibilidad (UPS-057)

Fuente: `docs/PRUEBAS-CAMPUS.md` §12 (MOB-01…04) y §13 (A11Y-01…05). Pruebas: `e2e/test_qa_mobile_a11y.py`.
Entorno: Windows 11, Chromium de Playwright, app compilada (`npm --prefix web run build`) y base SQLite sembrada
en cada servidor. Anchos: 375×812 (teléfono), 812×375 (horizontal), 1440×900 (escritorio).
Capturas de referencia en `e2e/artifacts/` (`ups057-*.png`, no se versionan).

Reproducir: `npm --prefix web run build && uv run pytest -q e2e/test_qa_mobile_a11y.py`

## Resultado por criterio

| ID | Resultado | Evidencia |
|---|---|---|
| MOB-01 | Pasa | 375 px en visitante, miembro, admin de club y superadmin: sin scroll horizontal, objetivos ≥ 44 px, sin texto cortado (auditoría de `test_mobile.py`). |
| MOB-02 | Parcial | Menú de cuenta y ClubSwitcher: abren, cierran con Esc y devuelven el foco al disparador (pasa). Modal "Nuevo evento": el foco cicla dentro (pasa). Cajón "Más": **falla**, ver B1. |
| MOB-03 | Pasa | Player: sin scroll de página. Tablas de admin de club y superadmin: dentro de un contenedor con `overflow-x`. |
| MOB-04 | Pasa | Horizontal 812×375 en login, inicio, academia, Player y admin: sin roturas ni scroll. |
| A11Y-01 | **Bloqueado** | axe-core no está instalado (no hay en `web/node_modules`, ni en `web/package.json`). Los 14 casos de la prueba (7 pantallas × 375 y 1440) fallan a propósito hasta que exista la dependencia. No hay resultado de axe: no se ha corrido. Pedido enviado al humano (`uak msg`, UPS-001 dueño de `web/package.json`). |
| A11Y-02 | Pasa (con límite) | Login completo solo con teclado (Tab, escribir, Enter) y foco visible en cada parada de Tab de inicio y Player. Límite: los `iframe` del Player no se miden desde fuera (ver B2). |
| A11Y-03 | Pasa en pares renderizados; paleta cruda **no cumple** (ver B3) | Pares reales medidos en la página: `--theme-ink`, `--theme-muted`, `--theme-link` y `--theme-danger` sobre `--theme-bg` (≥ 4.5:1), y `--academy-on-primary` sobre `--academy-primary` en la academia. |
| A11Y-04 | Pasa | Cajón "Más": sin `prefers-reduced-motion` anima 220 ms (Web Animations); con la preferencia, 0 ms de animación y la CSS queda en 0.00001 s. |
| A11Y-05 | **Pendiente humano** | NVDA no se ejecutó. Ver la sección siguiente. |

## Bugs encontrados (no corregidos en UPS-057; piden tarea nueva)

- **B1 · Cajón "Más" no atrapa el foco (MOB-02).** `web/src/components/Overlay.tsx` abre los cajones con `showModal()`. En Chromium, al pasar Tab desde el último control del cajón el foco sale al cuerpo del documento (la interfaz del navegador) y no vuelve al inicio del diálogo. Reproducción: `/a/upiixia` a 375 px con `alumno.demo@upiixsol.dev`, abrir "Más" y pulsar Tab tres veces. El modal "Nuevo evento" sí cicla. Hace falta un centinela de foco o un ciclo explícito en el cajón. Verificar también en Firefox y Safari.
- **B2 · Foco de los `iframe` del Player (A11Y-02, no confirmado).** El anillo de foco de un `iframe` lo pinta su contenido (de otro origen), así que no se puede medir desde la prueba. Revisar a mano, con el reproductor enfocado por teclado.
- **B3 · Paleta cruda sin AA como texto sobre blanco (A11Y-03).** Cálculo WCAG 2.x, sobre `#FFFFFF`:

  | Color | Sobre blanco | Sobre `#16181D` (texto oscuro) | Uso permitido |
  |---|---|---|---|
  | `#00BF63` | 2.43:1 | 7.30:1 | Relleno con texto oscuro. No es texto. |
  | `#04944F` | 3.92:1 | 4.53:1 | Texto grande (3:1) sobre blanco. Texto normal solo con texto oscuro. |
  | `#F28034` | 2.65:1 | 6.69:1 | Relleno con texto oscuro. No es texto. |
  | `#B4422F` | 5.58:1 | 3.18:1 | Texto normal sobre blanco. |

  La UI ya usa tokens de texto que sí cumplen (`--theme-link` `#037a41`, `--theme-muted`, `--theme-danger`) y `DESIGN.md` pide texto oscuro sobre el primario. El criterio literal "la paleta pasa AA" no se cumple para las marcas como texto. Decisión de producto: documentarlo como regla o ajustar la paleta.
- **B4 · Falta axe-core (A11Y-01).** Dependencia en `web/package.json` (UPS-001). Sin ella no hay auditoría automática.

## A11Y-05 · NVDA (pendiente, no realizado)

No se ejecutó lector de pantalla. Revisar a mano con NVDA y Chrome en `/login` y en `/a/upiixia/clases/1`:

- [ ] Campos de login con nombre accesible ("Boleta o correo", "Contraseña") y error anunciado.
- [ ] Botón "Entrar" anunciado como botón.
- [ ] Player: encabezado de nivel 1 de la clase, controles del video con nombre, lista de módulos como navegación o lista.
- [ ] Fecha y responsable: ____________ · Resultado: ____________

## Límites de este reporte

- Solo Chromium (Playwright). Firefox y Safari no se probaron.
- No se midió Lighthouse; el criterio pedía axe.
- Los cocientes de contraste son cálculos de la fórmula WCAG 2.x sobre los colores que devuelve el navegador.
