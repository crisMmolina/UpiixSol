# Spec 006 · Combined recipients with a visible list, and who got each email
- Status: draft, decisions by victor 2026-11-20 · Owner: victor (git `rvvictor`) · PROJECT principles: 1, 2, 4, 5, 6
- Builds on spec 003 (audiences, quota, webhooks), spec 004 and spec 005 (step 3 "Destinatarios y envío", templates). Club scope rules of spec 003 are unchanged.

## Problem
victor (2026-11-20), team checklist:
- "Combinar secciones de Todo UPIIXSOL, CLUB, UN ROL, PERSONAS para poder, por ejemplo, enviar un correo a todo upiixsol y más aparte a personas externas o decidir a qué personas no … mostrar una lista con todas las personas y seleccionarlas con un checkbox … ya que actualmente no hay forma de saber a quién le estamos enviando correo."
- "Hay un contador de personas a las que les llegó el correo y a las que les rebotó, INDICAR cuáles fueron esas personas en ambos casos."
- "Hacer que cada correo enviado con una plantilla no predeterminada se guarde como una plantilla nueva" (handled in spec 005, UPS-104, see §Decisions).

Today a sender picks exactly one audience kind (all, a club, a role, or individual people and pasted addresses) and only sees a number. The history shows counts per status but not who is behind them, although every recipient row (name, address, status, reason) is kept for 365 days.

## Stories
- As a sender, I want to combine sources (Todo UpiixSol, a club, a role, people I pick, outside addresses) in one email, so that I do not send several copies.
- As a sender, I want to see the list of everyone who will get the email, with a checkbox per person, and uncheck whoever should not get it.
- As a sender, I want to open a sent email and see who received it, who bounced (and why), who failed and who marked it as spam.

## Acceptance criteria (EARS)
Combined recipients (step 3)
- The sender shall add one or more **sources**: "Todo UpiixSol" and "Un rol" (superadmin only), "Un club" (superadmin: any; club admin: only their club), "Personas" (search and check), "Correos de fuera" (paste). Each source shows as a removable chip with its count.
- The system shall show **one list** of the resulting people (union, each person once), each with a checkbox (checked = receives), name, nickname, address, and where they come from ("Club UpiixIA", "Rol: admin", "Agregado", "De fuera"). Adding a source checks its people automatically; unchecking a person excludes them even if a source includes them.
- The list shall be searchable (name, nickname, address), paged (≤ 50 per page, "Cargar más"), and show at the top "N recibirán · M quitados por ti · K no se pueden enviar"; people who cannot receive (inactive, unsubscribed, blocked domain) are listed apart with the reason and no checkbox.
- The count, the quota check and the list come from the same server resolution as the real send; what is sent is exactly the checked list at send time (sources are re-resolved, exclusions applied).
- Club scope: a club admin can only add their club, its enrollees and co-admins, and outside addresses (unchanged, 403 otherwise; scope from the DB, never the body).
- Visibility (victor 2026-11-20): every sender sees the address of each person **they may pick** (a superadmin: everyone; a club admin: their club). For typed outside addresses a club admin is never told whether that address unsubscribed before sending (spec 003 security review UPS-074 still holds).

Delivery detail (history)
- When a sender opens a sent email in the history, the system shall show its counts per status as today plus a list per status: **Entregados**, **Rebotados**, **Fallidos**, **Marcados como spam**, **En camino** (accepted, no final event yet), **Sin enviar** (pending); each row has name, address, time of the last event and, for bounces and failures, the reason in Spanish ("El buzón no existe", "El servidor lo rechazó", "Dirección suprimida por rebotes previos", …, raw code shown as a hint).
- The lists are searchable and paged (≤ 50); a club admin sees only their club's emails (as today, 404 otherwise).
- When the recipient rows were already purged (older than 365 days), the detail shall show the counts and "El detalle por persona se borra al año del envío".
- A sent email can be reused: "Usar de nuevo" loads its subject, preview text and blocks (never its recipients) in the composer.

## Non-functional
- Spanish (Mexico), WCAG AA, keyboard operable, 390 px usable (list rows stack; chips wrap), reduced motion.
- Lists and counts come from DB queries only. A list page answers in < 500 ms for 2,000 users on the CI Postgres.
- No new dependency.

## Out of scope
- Saved audiences / mailing lists, CSV import or export, per-person open/click tracking (Mailgun opens and clicks stay off), resending only to the bounced ones.

## Decisions
- [x] Combine sources and exclude people with checkboxes · victor 2026-11-20
- [x] Club admin scope unchanged (own club + outside addresses; "Todo UpiixSol" and "Un rol" only superadmin) · victor 2026-11-20
- [x] Addresses visible to every sender for the people in their scope (widens spec 003, where club admins saw names only) · victor 2026-11-20
- [x] Templates on send (spec 005 amendment, UPS-104): step 3 has "Guardar como plantilla" **checked by default** (name prefilled from the subject) when the content did not come unchanged from a template; and the gallery always has an "Enviados recientes" section with the sender's last sent emails to reuse · victor 2026-11-20
