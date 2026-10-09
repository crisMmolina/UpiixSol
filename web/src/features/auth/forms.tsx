// /login forms. Every message has a reserved line (FormMessage / `reserve`), so errors never resize the card.
import { SignIn, UserPlus } from "@phosphor-icons/react";
import { useId, useState, type FormEvent } from "react";

import { Button } from "@/components/Button";
import { TextField, fieldErrors } from "@/components/Field";
import { FormMessage } from "@/components/FormMessage";
import { Stagger, StaggerItem } from "@/components/Motion";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { UserMe } from "@/lib/types";

import { formError, validateLogin, validateRegister, type Errors } from "./validation";

type FormProps = {
  onDone: (user: UserMe) => void;
  /** Stagger the fields in (after a tab switch, not on first paint). */
  play: boolean;
};

/** Field-level state shared by both forms: local checks first, then the API's answer. */
function useAuthForm() {
  const [errors, setErrors] = useState<Errors>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  /** Returns false (and focuses the first wrong field) when the local checks fail. */
  function check(form: HTMLFormElement, local: Errors): boolean {
    setErrors(local);
    setError(null);
    const first = Object.keys(local)[0];
    if (!first) return true;
    form.querySelector<HTMLElement>(`[name="${first}"]`)?.focus();
    return false;
  }

  async function send(request: () => Promise<void>) {
    setBusy(true);
    try {
      await request();
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) setErrors(fieldErrors(err.details));
      setError(formError(err));
    } finally {
      setBusy(false);
    }
  }

  /** Typing in a field clears its own error (the form-level one stays until the next submit). */
  function onInput(event: FormEvent<HTMLFormElement>) {
    const name = (event.target as HTMLInputElement).name;
    if (name && errors[name]) setErrors(({ [name]: _cleared, ...rest }) => rest);
  }

  return { errors, error, busy, check, send, onInput };
}

export function LoginForm({ onDone, play }: FormProps) {
  const { login } = useAuth();
  const { errors, error, busy, check, send, onInput } = useAuthForm();

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") ?? "").trim();
    const password = String(form.get("password") ?? "");
    if (!check(event.currentTarget, validateLogin(email, password))) return;
    void send(async () => onDone(await login({ email, password })));
  }

  return (
    <form onSubmit={submit} onInput={onInput} noValidate>
      <Stagger className="grid gap-2" play={play}>
        <StaggerItem>
          <TextField label="Correo" name="email" type="email" autoComplete="email" inputMode="email" required reserve error={errors.email} />
        </StaggerItem>
        <StaggerItem>
          <TextField label="Contraseña" name="password" type="password" autoComplete="current-password" required reserve error={errors.password} />
        </StaggerItem>
        <StaggerItem className="grid gap-2 pt-1">
          <Button type="submit" size="lg" loading={busy} icon={<SignIn weight="bold" />}>
            Entrar
          </Button>
          <FormMessage message={error} lines={{ base: 2, sm: 1 }} className="justify-items-center text-center" />
        </StaggerItem>
        <StaggerItem>
          <p className="text-center text-xs text-muted">¿Olvidaste tu contraseña? Pide a la mesa directiva del club que la restablezca.</p>
        </StaggerItem>
      </Stagger>
    </form>
  );
}

export function RegisterForm({ onDone, play }: FormProps) {
  const { register } = useAuth();
  const { errors, error, busy, check, send, onInput } = useAuthForm();
  const privacyId = useId();

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const data = {
      full_name: String(form.get("full_name") ?? "").trim(),
      boleta: String(form.get("boleta") ?? "").trim(),
      email: String(form.get("email") ?? "").trim(),
      password: String(form.get("password") ?? ""),
      accept: Boolean(form.get("accept_privacy")),
    };
    if (!check(event.currentTarget, validateRegister(data))) return;
    const { accept: _accept, ...fields } = data;
    void send(async () => onDone(await register({ ...fields, accept_privacy: true })));
  }

  return (
    <form onSubmit={submit} onInput={onInput} noValidate>
      <Stagger className="grid gap-2" play={play}>
        <StaggerItem>
          <TextField label="Nombre completo" name="full_name" autoComplete="name" required minLength={3} reserve error={errors.full_name} />
        </StaggerItem>
        <StaggerItem>
          <TextField
            label="Número de boleta"
            name="boleta"
            inputMode="numeric"
            maxLength={10}
            required
            hint="10 dígitos, como aparece en tu credencial del IPN."
            error={errors.boleta}
          />
        </StaggerItem>
        <StaggerItem>
          <TextField label="Correo" name="email" type="email" autoComplete="email" inputMode="email" required reserve error={errors.email} />
        </StaggerItem>
        <StaggerItem>
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
        </StaggerItem>
        <StaggerItem className="grid gap-1.5">
          <label className="flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              name="accept_privacy"
              aria-invalid={Boolean(errors.accept_privacy) || undefined}
              aria-describedby={errors.accept_privacy ? privacyId : undefined}
              className="mt-1 size-4 accent-[var(--academy-secondary)]"
            />
            <span>
              Acepto el <strong>aviso de privacidad</strong>: mi boleta y mi correo solo los ven la mesa directiva y yo; en la
              comunidad solo se muestran mi apodo y mi foto. Registramos cómo se usa la plataforma (páginas y acciones)
              para mejorarla.
            </span>
          </label>
          <FormMessage id={privacyId} size="xs" live={false} message={errors.accept_privacy} />
        </StaggerItem>
        <StaggerItem className="grid gap-2 pt-1">
          <Button type="submit" size="lg" loading={busy} icon={<UserPlus weight="bold" />}>
            Crear cuenta
          </Button>
          <FormMessage message={error} lines={{ base: 2, sm: 1 }} className="justify-items-center text-center" />
        </StaggerItem>
      </Stagger>
    </form>
  );
}
