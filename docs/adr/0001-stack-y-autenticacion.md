# ADR 0001 · Stack, database and authentication
- Status: proposed · Date: 2026-10-06 · Decider: @crisMmolina

## Context
A real platform with recurring traffic, delivered on Thursday 8 Oct 2026, with 3 roles and multiple academies. The kit's stack is FastAPI + React.

## Decision
- Backend: Python 3.12, FastAPI, SQLAlchemy 2 (sync), Alembic, Pydantic v2, uv.
- DB: PostgreSQL 16 in production and CI; SQLite for local dev and fast tests.
- Auth: email + password, **argon2id** hashing (`argon2-cffi`), 15-min access JWT (`pyjwt`, HS256, secret from env), 7-day refresh in an `HttpOnly; Secure; SameSite=Lax` cookie, rotated on every use and stored as a hash in the DB (revocable).
- Rate limiting: `slowapi` in memory (one process in v1). If we scale to more than one worker, move it to Redis.
- Sanitization: `nh3`. Images: `Pillow` (real type, size, resize).
- Frontend: React 19 + Vite + TS + Tailwind v4 + react-router; fonts Fredoka (headings) and Inter (body) through `@fontsource`.

## Alternatives
- Sessions in the DB with a cookie only: simpler, but the IDEA asks for JWT + refresh; refresh rotation gives us revocation anyway.
- Async SQLAlchemy: more complexity and not needed at the expected traffic.
- bcrypt: valid, but OWASP prefers argon2id.

## Consequences
Easy: tests with TestClient and SQLite, deployment with compose. Hard: in-memory rate limiting does not scale horizontally (documented). Reversible: the hash algorithm can migrate on next login (`argon2` `needs_rehash`).
