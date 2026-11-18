# Spec 005 · Email composer redesign (edit on the email) and templates
- Status: draft, decisions by victor 2026-11-18 · Owner: victor (git `rvvictor`) · PROJECT principles: 1, 2, 4, 5, 6
- Builds on spec 004 (blocks, renderer, preview, sender, Reply-To) and spec 003 (audiences, quota). Does not change what is sent; it changes how it is built.

## Problem
victor (2026-11-18): "No me gusta nada como son, no se ve bien la UX/UI". Today the composer is one long form: subject, preview text, Reply-To, then a list of block forms moved with ↑/↓ arrows and a grid of seven "Agregar …" buttons, with the email preview off to the side. Building a common email (an announcement, an event invitation) takes many clicks and the editor looks nothing like the email that goes out. There are no templates for quick sends.

## Stories
- As a sender, I want to start from a ready template (Anuncio, Invitación a evento, Recordatorio, Nueva clase / boletín) or a blank email, so that a common email takes a minute.
- As a sender, I want to edit the email directly on a canvas that looks like the email (click a block to edit it, "+" between blocks to insert, drag to reorder), so that what I build is what I see.
- As a sender, I want to save the email I built as my own template, so that I reuse my club's formats.
- As a superadmin, I want UpiixSol templates every sender can use; as a club admin, I want my club's templates.

## Acceptance criteria (EARS)
Flow
- When a sender opens "Correos", the system shall show three steps: **1 · Plantilla** (gallery), **2 · Contenido** (canvas), **3 · Destinatarios y envío** (audience, "Enviado por", Reply-To, quota, "Revisar y enviar"). Back and next keep everything; the step is in the URL.
- While a sender edits, the system shall keep a local draft (this browser, this user) and offer to restore it; sending or discarding clears it.

Templates
- The gallery shall show built-in templates (Anuncio, Invitación a evento, Recordatorio, Nueva clase / boletín), the sender's saved templates (UpiixSol ones for everyone; their club's for a club admin) and "En blanco", each with a live thumbnail rendered by the same server renderer.
- Built-in templates live in code (versioned, Spanish placeholders like "Escribe aquí el título"), are not editable or deletable, and never contain real names, dates or addresses.
- When a sender picks a template, the system shall load its subject, preview text and blocks into the canvas; an event block in a template is a placeholder the sender completes (pick from the calendar or type).
- When a sender saves "Guardar como plantilla" (name ≤ 60, optional description ≤ 140), the system shall store subject, preview text and blocks (never the audience, sender or Reply-To); a superadmin saves to UpiixSol scope, a club admin to their own club (scope from the DB, never the body).
- A sender may rename or delete only templates in their scope; a club admin cannot touch UpiixSol or other clubs' templates (403); members and anonymous callers get 403 and 401.

Canvas (step 2)
- The canvas shall look like the email: same width, logo, "Enviado por", theme colors of the sender, fonts and spacing as the renderer, so the sender sees the layout while editing.
- Clicking a block selects it and edits it in place: headings, paragraphs and list items are typed directly on the canvas, with a small toolbar for **negritas**, *cursivas* and enlaces (stored in the existing inline format); buttons, events and images open a properties panel (side panel on desktop, bottom sheet on phones).
- A "+" between blocks and at the end opens an inserter with the seven block kinds (icon, name, one-line description); the new block is selected and focused.
- Blocks reorder by dragging (handle) and by keyboard (Alt+↑/↓ on the selected block), can be duplicated and deleted (with undo for 5 s).
- "Ver como llega" shows the exact server-rendered email (desktop 600 / phone 375), as the preview does today.
- The 30-block and one-event limits, the formatting rules and every validation of spec 004 still apply, with Spanish messages next to the block.

## Non-functional
- Spanish (Mexico), WCAG AA, keyboard operable (every action reachable without a mouse), reduced motion respected, 390 px usable (canvas full width, properties as bottom sheet).
- Canvas typing feels instant (no server round trip per keystroke); the exact preview refreshes debounced as today.
- No new frontend dependency for drag-and-drop (reuse `web/src/features/academy-admin/sortable.ts` or native pointer events); any other dependency goes through the dependency review.

## Out of scope
- A free HTML editor, scheduled sends, template sharing across clubs, template folders or tags, A/B tests.

## Open questions
- [x] Editing model: on the email (canvas), "+" inserter, drag to reorder · victor 2026-11-18
- [x] Templates: built-in + save your own · victor 2026-11-18
- [x] Built-ins: Anuncio, Invitación a evento, Recordatorio, Nueva clase / boletín · victor 2026-11-18
- [x] Scope: superadmin → UpiixSol templates for everyone; club admin → own club · victor 2026-11-18
