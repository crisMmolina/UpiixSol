# DECISIONS

Coordination decisions on the claims branch.
Why: a reversible option after 15 min keeps work moving.
- 1791337653 | UPS-003 | stdlib only, nocookie embed, no server fetch | Why: no key, no SSRF, works pre-setup
- 1791338714 | UPS-001 | deps installed by human (guard); TS6 no baseUrl | Why: marathon guard; TS5101
- 1791339381 | deadline decision/UPS-001-1791338062/1791338962 | REVERSIBLE_AND_LOG | Option: Install dependency set approved by @crisMmolina in chat (backend: fastapi, uvicorn[standard], sqlalchemy>=2, alembic, psycopg[binary], pydantic-settings, pydantic[email], argon2-cffi, pyjwt, slowapi, python-multipart, pillow, nh3, httpx; dev: pytest, pytest-cov, ruff, playwright; web: react-router, tailwindcss, @tailwindcss/vite, motion, @phosphor-icons/react, @fontsource/fredoka, @fontsource-variable/inter, dompurify, marked); Why: UPS-001 setup; all MIT/BSD/Apache, maintained; audit after install; no money, accounts, publishing or scope expansion.
- 1791340307 | UPS-002 | position instead of order; SVG allowlist; & stays escaped | Why: reserved word; review findings
- 1791351367 | UPS-012 | Gestión en /a/:slug/recursos (dentro de Paths); link desde el panel pedido a claude-a | Why: academy-admin/index.tsx es de UPS-008
- 1791352226 | UPS-012 | No merge propio: marathon/PROJECT principio 2 = merge humano CODEOWNER | Why: Aprobación #81 era de 89af2b1
- 1791352323 | UPS-014 | must_change_password stays a non-blocking banner (spec); new session issued on password change | Why: IDEA §2.3 + acceptance
- 1791352408 | deadline decision/UPS-013-1791351460/1791352360 | REVERSIBLE_AND_LOG | Option: UTCDatetime type in app/schemas/common.py used by EventIn (owner UPS-002, already integrated, same author); Why: reject #70: naive vs aware compare gives 500; no money, accounts, publishing or scope expansion.
- 1791353499 | UPS-015 | real_ip desde gateway edge 172.31.0.1 + HTTP_BIND loopback obligatorio; red backend internal | Why: Terminador TLS del host llega via docker-proxy: sin real_ip todos comparten llave de rate limit
- 1791355489 | UPS-018 | mine en endpoint aparte y batch en el cliente: no tocar schemas (UPS-002) ni posts_out | Why: PostOut no tiene 'mine' y ya trae conteos
- 1791355506 | deadline decision/UPS-014-1791354509/1791355409 | REVERSIBLE_AND_LOG | Option: Regenerate docs/permissions-matrix.md (owner UPS-010, integrated, same author) in the UPS-014 PR; Why: UPS-010 contract: a new write endpoint requires regenerating the doc; test_docs_are_up_to_date; no money, accounts, publishing or scope expansion.
- 1791356122 | UPS-019 | HTML5 DnD nativo sin dependencia; rutas siguen solo con flechas (criterio pide módulos y clases) | Why: Paso siguiente del backlog: evaluar sin dependencia nueva
- 1791357617 | UPS-017 | Tags normalizados sin acentos (filtro JSON texto); parámetro blog_id para no chocar con post_id en la matriz | Why: Revisión de seguridad: tags acentuados no filtraban; ids enormes daban 500
- 1791382058 | UPS-012 | front-end only; no API/security changes | Why: Joahan asked to apply the UX/UI skills
- 1791382066 | UPS-017 | front-end only; no API/security changes | Why: Joahan asked to apply the UX/UI skills
- 1791382074 | UPS-019 | front-end only; no API/security changes | Why: Joahan asked to apply the UX/UI skills
- 1791385392 | UPS-018 | front-end only; API unchanged | Why: Joahan asked to apply the UX/UI skills
- 1791440527 | deadline lease/UPS-015/1791439899 | REQUIRES_RECOVERY | Claim kept; read the summary and use release --expired --read-summary. No work is deleted.
- 1791441047 | UPS-026 | day cell = absolute button over cell | Why: keyboard/44px
- 1791441054 | deadline lease/UPS-014/1791440918 | REQUIRES_RECOVERY | Claim kept; read the summary and use release --expired --read-summary. No work is deleted.
- 1791441077 | UPS-023 | enrollment becomes implicit: clicking a route tile fires idempotent POST /enroll | Why: no other feature depends on enrollment; keeps membership data
