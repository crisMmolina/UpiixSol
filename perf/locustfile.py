"""Carga de concurrencia del campus (UPS-060). Ejecutar con `bash perf/run_local.sh USERS DURATION`.

Mezcla de uso: 95 % alumnos y 5 % admins de academia. Cada usuario virtual entra una vez (login), carga su
inicio, la academia, una clase y el muro de la comunidad con scroll infinito, publica o reacciona, mira el
calendario y renueva la sesión (refresh). Solo usa las cuentas del seed (app/seed.py): `alumno.demo` para
alumnos y `admin.ia` para el admin de UpiixIA. Por eso todos los alumnos virtuales comparten una cuenta:
es un límite de la prueba, y está escrito en docs/qa/load-report.md.

Las pruebas de límite (AUTH-02, COM-10) no cuentan como capacidad: run_local.sh arranca la app con
RATELIMIT_ENABLED=false (entorno de carga, dicho en el reporte).

Arranque sincronizado: los usuarios entran y hacen login; la ventana medida empieza cuando el último ya entró,
y dura LOAD_DURATION. El login cuesta CPU de hash (argon2): se reporta aparte (tiempo de entrada y fallos), y
sus fallos cuentan en el error rate. Así el p95 mide la operación del campus, no el arranque.

Sale con código 1 si el error rate pasa de 1 % o el p95 de la ventana medida pasa de 1500 ms.
"""

import os
import random
import re
import time
from datetime import UTC, datetime, timedelta

import gevent
from gevent.event import Event
from locust import HttpUser, between, events, task
from locust.exception import StopUser

ACADEMY = "upiixia"
STUDENT_KEY = "2026000001"  # boleta de alumno.demo (LoginIn acepta boleta o correo)
ADMIN_KEY = "admin.ia@upiixsol.dev"
PASSWORD = os.environ.get("LOAD_SEED_PASSWORD", "")
FETCH = {"X-Requested-With": "fetch"}  # CSRF guard de los endpoints con cookie (require_fetch_header)
MAX_ERROR_RATIO = 0.01
MAX_P95_MS = 1500
REQUEST_TIMEOUT = 30  # ventana medida
SETUP_TIMEOUT = 120  # arranque: 20 logins a la vez tardan ~50 s en un 0.1 CPU; cortar antes los haría fallar
LOAD_USERS = int(os.environ.get("LOAD_USERS", "1"))
_GATE = Event()
_SETUP = {"t0": time.monotonic(), "arrived": 0, "login_failed": 0, "opened_at": None}


def _duration_seconds(text: str) -> int:
    """`60s`, `2m` o `90` (segundos)."""
    match = re.fullmatch(r"(\d+)([sm]?)", text.strip())
    if not match:
        raise ValueError(f"LOAD_DURATION no válido: {text!r} (ej. 60s o 2m)")
    return int(match.group(1)) * (60 if match.group(2) == "m" else 1)


RUN_SECONDS = _duration_seconds(os.environ.get("LOAD_DURATION", "60s"))


def _open_measurement(environment) -> None:
    """Último usuario en entrar: descarta las estadísticas del arranque y cronometra la ventana medida."""
    environment.stats.reset_all()
    _SETUP["opened_at"] = time.monotonic()
    print(
        f"UPS-060 arranque: {_SETUP['arrived']} usuarios entraron en "
        f"{_SETUP['opened_at'] - _SETUP['t0']:.1f} s; {_SETUP['login_failed']} sin login; "
        f"ventana medida: {RUN_SECONDS} s"
    )
    gevent.spawn_later(RUN_SECONDS, environment.runner.quit)
    _GATE.set()


class CampusUser(HttpUser):
    abstract = True
    wait_time = between(1, 5)
    key = STUDENT_KEY

    def on_start(self) -> None:
        # Una petición que no responde a tiempo cuenta como error. Sin tope, un usuario atorado no aparecería
        # en las estadísticas. El tope lo fija self.request_timeout: arranque, luego la ventana medida.
        request = self.client.request
        self.request_timeout = SETUP_TIMEOUT

        def bounded(method, url, **kwargs):
            kwargs.setdefault("timeout", self.request_timeout)
            return request(method, url, **kwargs)

        self.client.request = bounded
        self.lesson_ids: list[int] = []
        self.academy_id: int | None = None
        self.channel_id: int | None = None
        logged_in = self._login()
        if logged_in:
            self.academy_id = self._academy_id()
            channels = self.client.get("/api/channels", name="/api/channels")
            if channels.status_code == 200:
                self.channel_id = next((c["id"] for c in channels.json() if c["slug"] == ACADEMY), None)
            self._load_lessons()
        self._arrive(logged_in)
        if not logged_in:
            raise StopUser()

    def _arrive(self, logged_in: bool) -> None:
        _SETUP["arrived"] += 1
        if not logged_in:
            _SETUP["login_failed"] += 1
        if _SETUP["arrived"] >= LOAD_USERS:
            if _SETUP["opened_at"] is None:
                _open_measurement(self.environment)
        else:
            _GATE.wait()
        self.request_timeout = REQUEST_TIMEOUT

    def _login(self) -> bool:
        with self.client.post(
            "/api/auth/login",
            json={"identifier": self.key, "password": PASSWORD},
            headers=FETCH,
            name="/api/auth/login",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"login {response.status_code}")
                return False
            self.client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
            return True

    def _academy_id(self) -> int | None:
        response = self.client.get(f"/api/academies/{ACADEMY}", name="/api/academies/[slug]")
        return response.json().get("id") if response.status_code == 200 else None

    def _load_lessons(self) -> None:
        routes = self.client.get(f"/api/academies/{ACADEMY}/routes", name="/api/academies/[slug]/routes")
        items = routes.json().get("items", []) if routes.status_code == 200 else []
        if not items:
            return
        detail = self.client.get(f"/api/routes/{items[0]['id']}", name="/api/routes/[id]")
        if detail.status_code == 200:
            self.lesson_ids = [
                lesson["id"] for module in detail.json()["modules"] for lesson in module["lessons"]
            ]

    @task(3)
    def home(self) -> None:
        self.client.get("/api/home", name="/api/home")

    @task(3)
    def academy_page(self) -> None:
        self.client.get(f"/api/academies/{ACADEMY}/home", name="/api/academies/[slug]/home")

    @task(4)
    def player(self) -> None:
        if not self.lesson_ids:
            return
        lesson_id = random.choice(self.lesson_ids)
        self.client.get(f"/api/lessons/{lesson_id}", name="/api/lessons/[id]")
        if random.random() < 0.3:  # marca como vista una de cada tres veces que abre la clase
            self.client.post(
                f"/api/lessons/{lesson_id}/complete", name="/api/lessons/[id]/complete", headers=FETCH
            )

    @task(4)
    def community_feed(self) -> None:
        if self.channel_id is None:
            return
        cursor = None
        post_ids: list[int] = []
        for _ in range(random.randint(1, 3)):  # scroll infinito: hasta tres páginas
            params = {"limit": 20, **({"cursor": cursor} if cursor else {})}
            page = self.client.get(
                f"/api/channels/{self.channel_id}/posts",
                params=params,
                name="/api/channels/[id]/posts",
            )
            if page.status_code != 200:
                return
            body = page.json()
            post_ids += [post["id"] for post in body["items"]]
            cursor = body.get("next_cursor")
            if not cursor:
                break
        if post_ids and random.random() < 0.5:
            kind = random.choice(["like", "love", "fire", "idea", "clap"])
            post_id = random.choice(post_ids)
            self.client.put(
                f"/api/posts/{post_id}/reactions/{kind}", name="/api/posts/[id]/reactions/[kind]", headers=FETCH
            )

    @task(1)
    def post_message(self) -> None:
        if self.channel_id is None:
            return
        self.client.post(
            f"/api/channels/{self.channel_id}/posts",
            data={"body": f"Mensaje de carga {random.randint(1, 10**6)}"},
            name="/api/channels/[id]/posts (POST)",
            headers=FETCH,
        )

    @task(2)
    def calendar(self) -> None:
        now = datetime.now(UTC)
        self.client.get(
            "/api/events",
            params={"from": now.isoformat(), "to": (now + timedelta(days=30)).isoformat(), "limit": 50},
            name="/api/events",
        )

    @task(1)
    def refresh(self) -> None:
        with self.client.post(
            "/api/auth/refresh", headers=FETCH, name="/api/auth/refresh", catch_response=True
        ) as response:
            if response.status_code != 200:
                response.failure(f"refresh {response.status_code}")
                return
            self.client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"


class Student(CampusUser):
    abstract = False
    weight = 19  # 95 % de los usuarios virtuales
    key = STUDENT_KEY


class AcademyAdmin(CampusUser):
    abstract = False
    weight = 1  # 5 % de los usuarios virtuales
    key = ADMIN_KEY
    wait_time = between(3, 10)

    @task(2)
    def enrollments(self) -> None:
        if self.academy_id is None:
            return
        self.client.get(
            f"/api/academies/{self.academy_id}/enrollments",
            name="/api/academies/[id]/enrollments",
        )


@events.quitting.add_listener
def _check_thresholds(environment, **_kwargs) -> None:
    total = environment.stats.total
    if _SETUP["opened_at"] is None or total.num_requests == 0:
        print("UPS-060 FAIL: la ventana medida nunca abrió o no hubo peticiones")
        environment.process_exit_code = 1
        return
    # Un login fallido es un error del usuario: cuenta como intento y como error.
    attempts = total.num_requests + LOAD_USERS
    failures = total.num_failures + _SETUP["login_failed"]
    error_ratio = failures / attempts
    p95 = total.get_response_time_percentile(0.95)
    ok = error_ratio <= MAX_ERROR_RATIO and p95 <= MAX_P95_MS
    print(
        f"UPS-060 {'OK' if ok else 'FAIL'}: peticiones={attempts} errores={failures} "
        f"error_rate={error_ratio:.2%} p95={p95:.0f} ms (limites 1 %, {MAX_P95_MS} ms)"
    )
    if not ok:
        environment.process_exit_code = 1
