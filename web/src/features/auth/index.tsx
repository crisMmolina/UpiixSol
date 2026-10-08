// Flow step 1 (UPS-005): single login for every role + member self-registration.
import { SignIn, UserPlus } from "@phosphor-icons/react";
import { useState, type FormEvent } from "react";
import { Navigate, useNavigate, useSearchParams, type RouteObject } from "react-router";

import { Button } from "@/components/Button";
import { TextField, fieldErrors } from "@/components/Field";
import { PageSkeleton } from "@/components/Skeleton";
import { ApiError, errorMessage } from "@/lib/api";
import { homeFor, useAuth } from "@/lib/auth";
import { AcademyTheme, CAMPUS_BRANDING } from "@/lib/theme";
import type { UserMe } from "@/lib/types";

export const order = 10;

type Tab = "login" | "register";

/** Only same-origin app paths; rejects //host, /\host and absolute URLs (open redirect). */
export function safeNext(next: string | null): string | null {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.startsWith("/\\")) return null;
  return next;
}

function useDestination() {
  const [params] = useSearchParams();
  const next = safeNext(params.get("next"));
  return (user: UserMe) => next ?? homeFor(user);
}

function LoginForm({ onDone }: { onDone: (user: UserMe) => void }) {
  const { login } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      onDone(await login({ email: String(form.get("email")), password: String(form.get("password")) }));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="grid gap-4" noValidate>
      <TextField label="Correo" name="email" type="email" autoComplete="email" required inputMode="email" />
      <TextField label="Contraseña" name="password" type="password" autoComplete="current-password" required />
      {error && (
        <p role="alert" className="rounded-xl bg-accent-2/10 px-3 py-2 text-sm font-semibold text-accent-2">
          {error}
        </p>
      )}
      <Button type="submit" size="lg" loading={busy} icon={<SignIn weight="bold" />}>
        Entrar
      </Button>
      <p className="text-center text-xs text-muted">
        ¿Olvidaste tu contraseña? Pide a la mesa directiva del club que la restablezca.
      </p>
    </form>
  );
}

function RegisterForm({ onDone }: { onDone: (user: UserMe) => void }) {
  const { register } = useAuth();
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const local: Record<string, string> = {};
    const boleta = String(form.get("boleta")).trim();
    if (!/^\d{10}$/.test(boleta)) local.boleta = "La boleta debe tener 10 dígitos.";
    if (String(form.get("password")).length < 8) local.password = "Usa al menos 8 caracteres.";
    if (!form.get("accept_privacy")) local.accept_privacy = "Debes aceptar el aviso de privacidad.";
    setErrors(local);
    setError(null);
    if (Object.keys(local).length) return;

    setBusy(true);
    try {
      onDone(
        await register({
          full_name: String(form.get("full_name")).trim(),
          boleta,
          email: String(form.get("email")).trim(),
          password: String(form.get("password")),
          accept_privacy: true,
        }),
      );
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) setErrors(fieldErrors(err.details));
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="grid gap-4" noValidate>
      <TextField label="Nombre completo" name="full_name" autoComplete="name" required minLength={3} error={errors.full_name} />
      <TextField
        label="Número de boleta"
        name="boleta"
        inputMode="numeric"
        maxLength={10}
        required
        hint="10 dígitos, como aparece en tu credencial del IPN."
        error={errors.boleta}
      />
      <TextField label="Correo" name="email" type="email" autoComplete="email" required error={errors.email} />
      <TextField
        label="Contraseña"
        name="password"
        type="password"
        autoComplete="new-password"
        required
        minLength={8}
        hint="Mínimo 8 caracteres."
        error={errors.password}
      />
      <label className="flex items-start gap-2 text-sm">
        <input type="checkbox" name="accept_privacy" className="mt-1 size-4 accent-[var(--academy-secondary)]" />
        <span>
          Acepto el <strong>aviso de privacidad</strong>: mi boleta y mi correo solo los ven la mesa directiva y yo; en la
          comunidad solo se muestran mi apodo y mi foto.
        </span>
      </label>
      {errors.accept_privacy && <p className="text-xs font-semibold text-accent-2">{errors.accept_privacy}</p>}
      {error && (
        <p role="alert" className="rounded-xl bg-accent-2/10 px-3 py-2 text-sm font-semibold text-accent-2">
          {error}
        </p>
      )}
      <Button type="submit" size="lg" loading={busy} icon={<UserPlus weight="bold" />}>
        Crear cuenta
      </Button>
    </form>
  );
}

function LoginPage() {
  const { status, user } = useAuth();
  const [params, setParams] = useSearchParams();
  const destination = useDestination();
  const navigate = useNavigate();
  const tab: Tab = params.get("tab") === "registro" ? "register" : "login";

  if (status === "loading") return <PageSkeleton />;
  if (user) return <Navigate to={destination(user)} replace />;

  const onDone = (signedIn: UserMe) => navigate(destination(signedIn), { replace: true });
  const selectTab = (next: Tab) => {
    const updated = new URLSearchParams(params);
    if (next === "register") updated.set("tab", "registro");
    else updated.delete("tab");
    setParams(updated, { replace: true });
  };
  const tabClass = (active: boolean) =>
    `min-h-11 flex-1 rounded-full text-sm font-semibold transition ${
      active ? "bg-surface text-ink shadow-soft" : "text-muted hover:text-ink"
    }`;

  return (
    <AcademyTheme branding={CAMPUS_BRANDING} className="min-h-dvh bg-bg">
      <main className="mx-auto grid min-h-dvh max-w-5xl items-center gap-8 px-4 py-10 sm:px-8 lg:grid-cols-2">
        <section className="flex flex-col items-center text-center lg:items-start lg:text-left">
          <img src="/brand/upiixsol/wordmark.png" alt="UpiixSol" className="h-12 w-auto sm:h-14" />
          <h1 className="mt-6 text-3xl sm:text-4xl">Tus clubs en un solo campus</h1>
          <p className="mt-3 max-w-md text-muted">
            Retoma tus clases donde te quedaste y conversa con tu comunidad.
          </p>
          <img
            src="/brand/upiixsol/mascot.png"
            alt="Ajolote de UpiixSol"
            className="mt-6 hidden w-full max-w-xs sm:block"
          />
        </section>

        <section className="rounded-card border border-line bg-surface p-5 shadow-soft sm:p-8">
          <div role="tablist" aria-label="Acceso" className="mb-6 flex gap-1 rounded-full bg-bg p-1">
            <button
              role="tab"
              type="button"
              aria-selected={tab === "login"}
              className={tabClass(tab === "login")}
              onClick={() => selectTab("login")}
            >
              Entrar
            </button>
            <button
              role="tab"
              type="button"
              aria-selected={tab === "register"}
              className={tabClass(tab === "register")}
              onClick={() => selectTab("register")}
            >
              Crear cuenta
            </button>
          </div>
          <div role="tabpanel">
            {tab === "login" ? <LoginForm onDone={onDone} /> : <RegisterForm onDone={onDone} />}
          </div>
        </section>
      </main>
    </AcademyTheme>
  );
}

export const routes: RouteObject[] = [{ path: "/login", element: <LoginPage /> }];
