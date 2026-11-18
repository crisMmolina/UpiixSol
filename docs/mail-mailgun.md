# Correo con Mailgun · guía de puesta en marcha (UPS-080)

Guía para activar el correo de UpiixSol (spec 003) en producción. **Todos los pasos en Mailgun, en el DNS y en el panel de Render los hace una persona** (victor); ningún agente toca esos paneles ni ve las llaves. Contexto: [ADR 0002](adr/0002-correo-mailgun.md), [plan §Rollout](specs/003-correo/plan.md), [spike](spikes/mailgun.md).

- Dominio de envío: `mg.upiixsol.com` (subdominio, para no mezclar la reputación con `upiixsol.com`).
- Remitente: `UpiixSol <avisos@mg.upiixsol.com>`.
- Estado actual: el dominio ya está **verificado** en Mailgun. Las secciones 1 y 2 quedan como referencia para repetirlo o auditarlo.

> **Regla:** las llaves (`MAILGUN_API_KEY`, `MAILGUN_WEBHOOK_SIGNING_KEY`) viven solo en el panel de Render (y en tu `.env` local, que no se sube). Nunca en el repo, en un chat, en un issue ni en capturas.

## 1. Dominio en Mailgun
1. En Mailgun: **Sending → Domains → Add new domain** con el nombre `mg.upiixsol.com`.
2. Región: la que elijas al crearlo (**US** o **EU**) no se puede cambiar después. Si es EU, usa `MAILGUN_API_BASE=https://api.eu.mailgun.net` (§3).
3. Mailgun muestra los registros a crear. Copia los valores desde su pantalla; **no los pegues en este repo**.

## 2. Registros DNS
Se agregan en el proveedor DNS de `upiixsol.com`. Los valores exactos los da Mailgun.

| Tipo | Nombre | Para qué |
|---|---|---|
| TXT | `mg` | SPF (`v=spf1 include:mailgun.org ~all` según indique Mailgun) |
| TXT | `<selector>._domainkey.mg` | DKIM (firma de los correos) |
| MX | `mg` (dos registros) | Recepción de rebotes y respuestas a ese subdominio |
| CNAME | `email.mg` | **Opcional**, solo para seguimiento de clics. Déjalo sin crear: la app envía con seguimiento apagado |
| TXT | `_dmarc` (en la raíz `upiixsol.com`) | DMARC. Empieza con `v=DMARC1; p=none; rua=mailto:<buzón del club>` y endurece a `quarantine` cuando los reportes salgan limpios |

No toques los registros que ya existan en la raíz (el sitio apunta a Render).

**Cómo comprobar que están bien**
1. En Mailgun, **Domain settings → DNS records → Verify DNS settings**: SPF, DKIM y MX en verde. La propagación puede tardar de minutos a 48 h.
2. Opcional, desde la terminal: `dig TXT mg.upiixsol.com +short` y `dig MX mg.upiixsol.com +short`.

## 3. Variables en Render
Se cargan en **Render → servicio `upiixsol` → Environment**, **todas de una vez** y con un solo deploy. `render.yaml` ya las declara; las llaves llevan `sync: false`, así que Render te pide el valor.

| Variable | Valor |
|---|---|
| `MAIL_ENABLED` | `true` (empieza en `false` hasta tener todo lo demás) |
| `MAIL_BACKEND` | `mailgun` |
| `MAILGUN_DOMAIN` | `mg.upiixsol.com` |
| `MAILGUN_API_BASE` | `https://api.mailgun.net` (US) o `https://api.eu.mailgun.net` (EU) |
| `MAILGUN_API_KEY` | **Sending key** del dominio (Mailgun → Domain settings → Sending keys). No uses la llave privada de la cuenta |
| `MAILGUN_WEBHOOK_SIGNING_KEY` | **HTTP webhook signing key** (Mailgun → Webhooks; es distinta de la API key) |
| `MAILGUN_TEST_MODE` | `true` para las primeras pruebas; `false` al salir de pruebas |
| `MAIL_FROM` | `UpiixSol <avisos@mg.upiixsol.com>` |
| `PUBLIC_BASE_URL` | `https://www.upiixsol.com` (con él se arman los enlaces de `/baja`) |

Opcionales: `MAIL_MONTHLY_LIMIT` (por defecto 3000 destinatarios por periodo de facturación, el tope del plan Free de Mailgun), `MAIL_PERIOD_START_DAY` (1–28, por defecto 1: día del mes, en UTC, en que inicia tu periodo; míralo en Mailgun → Billing). Mailgun también cuenta los envíos hechos fuera de la app (pruebas con curl, otras herramientas): deja un margen, porque el contador de la app solo ve lo que la app envió. Un `MAIL_DAILY_LIMIT` viejo en el entorno se ignora. También: `MAIL_REPLY_TO`, `MAIL_BLOCKED_DOMAINS`.

**Qué falla al arrancar** (con `ENV=prod`, la API no levanta y el deploy se queda en rojo; el log muestra el `ValueError`):
- `MAIL_ENABLED=true` y `MAILGUN_API_BASE` o `PUBLIC_BASE_URL` sin `https://`.
- `MAIL_ENABLED=true` con `MAIL_BACKEND=mailgun` y falta alguna de `MAILGUN_API_KEY`, `MAILGUN_DOMAIN` (debe estar definida explícitamente, no basta el valor por defecto) o `MAILGUN_WEBHOOK_SIGNING_KEY`. El mensaje dice cuáles.

Con `MAIL_ENABLED=false` nada de esto se exige y la pestaña «Correos» muestra «El correo está desactivado».

## 4. Webhook
1. Mailgun → **Sending → Webhooks → Add webhook** (en el dominio `mg.upiixsol.com`).
2. URL: `https://www.upiixsol.com/api/mail/webhooks/mailgun`
3. Eventos a activar: **Delivered**, **Permanent failure**, **Temporary failure** y **Spam complaints**. Mailgun también puede avisar de bajas (**Unsubscribes**), pero la app maneja sus propias bajas en `/baja`; no es necesario.
4. La app verifica la firma (HMAC-SHA256 con `MAILGUN_WEBHOOK_SIGNING_KEY`), que la marca de tiempo tenga menos de 5 minutos y que el token no se repita; si algo falla responde 403 y no cambia nada. Por eso la llave de firma debe estar cargada antes de activar el webhook.
5. Prueba: en Mailgun, **Send test webhook** a esa URL debe dar 200 (los eventos de un correo que la app no conoce se ignoran con 200).

## 5. Primer envío (plan §Rollout)
1. **Merge con `MAIL_ENABLED=false`** (valor por defecto): nada se envía.
2. Carga las variables de §3 con `MAILGUN_TEST_MODE=true` y `MAIL_ENABLED=true`. Espera a que el deploy quede en verde.
3. Entra a `/admin` → **Correos** → **Enviarme una prueba**. En modo de prueba Mailgun acepta el envío pero no entrega; revisa **Mailgun → Logs** y que la campaña aparezca en el historial.
4. Apaga el modo de prueba (`MAILGUN_TEST_MODE=false`) y repite **Enviarme una prueba**: debe llegar a tu buzón (revisa spam y los encabezados SPF/DKIM = pass).
5. Primera campaña real **a los superadmins** (audiencia «Un rol»).
6. Después **a un club** (pestaña Correos del club o «Un club»).
7. Por último **a todos** («Todo UpiixSol»).

**Criterio para avanzar:** entregados ≥ 95 % y ninguna queja en las dos primeras campañas. Vigila en Mailgun la tasa de rebotes; arriba de 5 % detén los envíos (§8).

## 6. Bajas (`/baja`)
Cada correo lleva un enlace a `https://www.upiixsol.com/baja?t=<token>` y los encabezados `List-Unsubscribe`. La persona abre `/baja`, confirma y queda en la lista de supresión (también puede cambiar la preferencia en **Mi cuenta**). Las bajas, los rebotes permanentes y las quejas se guardan en la base y se excluyen de envíos futuros. Para probarlo: envíate una prueba, abre el enlace, confirma y vuelve a enviarte: debes aparecer como excluido.

## 7. Encabezado de baja en lotes (`UNSUBSCRIBE_HEADER_IN_BATCH`)
No es una variable de Render: es una constante de código en `app/services/mailgun.py`, hoy en `False`. En lotes grandes Mailgun manda **un solo mensaje** para muchos destinatarios; mientras no se compruebe que `%recipient.unsubscribe_token%` se sustituye dentro del encabezado `List-Unsubscribe` por destinatario, la app no lo pone en lotes (spike §3, **sin verificar**).

Para verificarlo (≤ 5 min, con tu llave en `.env` local y solo en modo de prueba): sigue «How to verify later» del [spike §3](spikes/mailgun.md), compara el encabezado de dos destinatarios y anota el resultado en el spike. **Solo si los encabezados difieren y llevan sus tokens**, abre una tarea (`uak followup`) para cambiar la constante a `True`.

## 8. Retención mensual (UPS-081)
Una vez al mes, desde un shell con acceso a la base de producción (Render Shell del servicio):

```
python -m app.services.mail_retention --dry-run   # solo cuenta, no borra
python -m app.services.mail_retention             # borra destinatarios de campañas de más de 365 días
```

Conserva los conteos por estado en la campaña y las supresiones; imprime solo cifras. `--days N` cambia el plazo.

## 9. Rollback
Pon `MAIL_ENABLED=false` en Render y guarda: el servicio se reinicia y deja de enviar de inmediato, **sin redeploy de código**. La migración 0009 es aditiva y se queda. Si un envío quedó a medias, las filas `pending` se reanudan a mano con «Reanudar» cuando vuelvas a activarlo. Si sospechas que la llave se filtró: revócala en Mailgun, crea otra y cámbiala en Render.

## 10. Nota de incidente: nunca apuntes el `.env` local a producción
Nunca pongas la `DATABASE_URL` de Neon (producción) en tu `.env` local. Con ella, `alembic`, el seed, los scripts o los tests corren contra la base real y pueden migrar, sembrar o borrar datos de usuarios, además de enviar correo real a personas reales. Local usa SQLite o un Postgres de desarrollo. Para el paso del §7 y el §8 usa la llave en `.env` pero **la base local**; la retención de producción se corre solo desde el Shell de Render. Si ya pasó: cambia la contraseña de Neon, restaura el respaldo más reciente (runbook §5) y avisa al equipo.
