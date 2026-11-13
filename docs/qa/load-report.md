# Carga: cuántos usuarios concurrentes aguanta el campus (UPS-060)

Corridas del 12 de noviembre de 2026, con `perf/locustfile.py` y `perf/run_local.sh` (commit `f2f100a` y los
ajustes del mismo PR). Cada escalón es **una sola corrida** de 60 s de ventana medida; no hay repeticiones, así
que la variación entre corridas no se conoce.

## Conclusión

Con 0.1 CPU y 512 MB de RAM (el plan free de Render) y Postgres 16 local, el campus sostiene **alrededor de 10
usuarios concurrentes** sin errores y con p95 de 1000 ms. El punto de quiebre está **entre 10 y 20 usuarios**: a
20 el p95 ya es 1900 ms. En la rampa pedida (10, 25, 50, 100, 200) el primer escalón que incumple es 25.

Esta cifra **no es de Render + Neon**. La prueba corrió en la máquina local, con la app y Postgres en contenedores
de Docker. No midió la red hacia Render ni Neon, ni el arranque en frío de Render. La prueba contra staging no se
corrió: requiere autorización humana. Producción no se tocó.

Usuario concurrente aquí significa un usuario virtual con sesión abierta que hace una petición cada 1 a 5 s. Diez
usuarios equivalen a unas 3.4 peticiones por segundo.

## Cómo se midió

- **App:** imagen `api` del `Dockerfile` (Python 3.12, uvicorn con un proceso), con `--cpus 0.1 --memory 512m`.
  Arranca con alembic y el seed. Modo `ENV=prod` con secretos generados por corrida.
- **Base:** `postgres:16-alpine` en contenedor propio, sin límite de CPU ni RAM, en una red de Docker aparte.
- **Generador de carga:** Locust 2.47.0 con `uvx`, en modo headless, en el mismo equipo Windows 11 que Docker. No
  está aislado: comparte CPU con la VM de Docker. No se midió la CPU del equipo.
- **Entorno de carga** (solo en los contenedores de la prueba):
  - `RATELIMIT_ENABLED=false`. Todos los usuarios salen de la misma IP, y el límite de 5 logins por minuto por IP
    habría tirado casi todos los logins. Por eso los límites AUTH-02 y COM-10 **no están incluidos** en la capacidad.
  - `REQUIRE_PASSWORD_CHANGE=false`. Las cuentas del seed tienen contraseña provisional.
  - `COOKIE_SECURE=false`. Locust corre sobre http y no envía cookies `Secure`.
- **Mezcla:** 95 % alumnos (cuenta `alumno.demo`) y 5 % admins de academia (`admin.ia`). Un alumno pide inicio,
  academia, clase (a veces la marca vista), muro con hasta tres páginas, publica o reacciona, calendario, y renueva
  sesión. Los pesos están en `perf/locustfile.py`.
- **Ventana medida:** cada usuario hace login y carga su contexto antes de la ventana. La ventana de 60 s empieza
  cuando el último usuario ya entró. La ola de login se reporta aparte, con sus fallos. Cada login fallido cuenta
  como error en la tasa de errores.
- **Criterio:** falla si la tasa de errores pasa de 1 % o el p95 de la ventana pasa de 1500 ms. El script sale con 1.

## Resultados por escalón

| Usuarios | Ola de login (todos entran) | Sin login | Peticiones en ventana | Peticiones/s | p50 (ms) | p95 (ms) | Tasa de error | Veredicto |
|---|---|---|---|---|---|---|---|---|
| 10 | 57.7 s | 0 | 205 | 3.4 | 17 | 1000 | 0.00 % | OK |
| 20 (Verify) | 116.7 s | 0 | 405 | 6.8 | 290 | 1900 | 0.00 % | FALLA (p95) |
| 25 | 93.6 s | 0 | 395 | 6.6 | 800 | 4000 | 0.00 % | FALLA (p95) |
| 50 | 196.2 s | 31 | 341 | 5.7 | 300 | 3100 | 7.87 % | FALLA |
| 100 | 124.1 s | 100 | 0 | - | - | - | 100 % | FALLA (ningún login) |
| 200 | 205.3 s | 185 | 323 | 5.4 | 60 | 1900 | 35.50 % | FALLA |

- "Sin login" son usuarios que no completaron el login en 120 s. Esos usuarios no entran a la ventana.
- Con 50, 100 y 200 usuarios la ventana tiene menos usuarios activos que el escalón nominal, así que sus p50 y
  p95 describen solo a quienes sí entraron.
- Las peticiones salen del CSV de Locust (en `<git-dir>/load-results`, fuera del árbol). El veredicto
  del script cuenta además los intentos de login, por eso puede diferir en unas pocas peticiones.
- RAM: en todas las corridas el contenedor llegó a 512 MiB (el tope) durante el arranque y la ola de login. En la ventana
  quedó en unos 76 a 80 MiB. `docker stats` incluye caché de página, así que no separa memoria anónima. En 100
  usuarios la memoria osciló entre unos 40 y 511 MiB. No hubo OOM-kill visible: el contenedor siguió vivo hasta el
  final de cada corrida. No se verificó con `docker inspect`.

### Endpoints más lentos (p95 de la ventana)

| Usuarios | Endpoint | p95 (ms) | Peticiones |
|---|---|---|---|
| 10 | `/api/home` | 2400 | 25 |
| 10 | `/api/lessons/[id]` | 2000 | 53 |
| 20 | `/api/academies/[slug]/home` | 3900 | 52 |
| 20 | `/api/home` | 3500 | 50 |
| 20 | `/api/auth/refresh` | 2400 | 23 |
| 25 | `/api/academies/[slug]/home` | 5900 | 51 |
| 25 | `/api/lessons/[id]` | 4200 | 84 |
| 25 | `/api/channels/[id]/posts` | 3800 | 77 |
| 50 | `/api/academies/[slug]/home` | 4600 | 52 |
| 50 | `/api/home` | 3400 | 49 |
| 200 | `/api/home` | 3400 | 37 |

Con 10 usuarios hay pocas peticiones por endpoint, así que sus percentiles altos cuentan con muy pocas muestras.

## Hallazgos (cuellos de botella, no corregidos aquí)

1. **El login domina el arranque.** En calibración con una versión previa del script, con un solo usuario el
   `POST /api/auth/login` tardó 2.65 s, mientras que `/api/home` tardó 16 ms de mediana. El hash argon2id
   (`app/security.py`, parámetros por defecto) reserva unos 64 MiB por intento. Con 0.1 CPU y 512 MB, la ola de
   login se vuelve el límite: 10 logins tardaron 58 s y con 100 usuarios ninguno entró en 120 s.
   Candidatos: parámetros de hash o concurrencia de hash, que decide el dueño con un ADR.
2. **Endpoints de inicio con p95 de 2.4 a 5.9 s desde 10 o 20 usuarios:** `/api/home`,
   `/api/academies/[slug]/home`, `/api/channels/[id]/posts` y `/api/lessons/[id]`. Sospecha: consultas repetidas o
   pesadas. **No medido:** no se perfilaron las consultas SQL.
3. **`/api/auth/refresh` con p95 de 2.4 s a 20 usuarios.** No se investigó la causa.
4. **Memoria al tope de 512 MiB** durante la ola de login. Con más concurrencia puede haber OOM. No verificado.
5. **Cuenta compartida.** Todos los alumnos virtuales usan `alumno.demo`, porque el seed solo trae un alumno. Eso
   no reproduce bien la contención por filas de usuarios distintos. Falta un seed de alumnos de prueba para carga.

## Límites de esta medición

- Una corrida por escalón, sin repetir. No hay intervalo de confianza.
- Postgres local en Docker: sin latencia de red ni de Neon.
- Sin Render: sin arranque en frío, sin proxy, sin el disco de Render.
- Locust corre en el mismo equipo y no está aislado.
- Los límites de tasa están apagados en la prueba (ver arriba).

## Cómo repetir

```bash
export UAK_PORT=8700          # el puerto del worktree
bash perf/run_local.sh 10 60s   # un escalón; sale con 1 si falla
```

Variables: `LOAD_CPUS` (0.1), `LOAD_MEM` (512m), `LOAD_SPAWN_RATE` (usuarios/5), `LOAD_OUT`.
