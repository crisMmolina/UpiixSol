// Mi cuenta → Seguridad: password and email. Every message has a reserved line, so the tab never grows
// per error (audit auth.md 9), and disabled buttons say why (auth.md 8).
import { useId, useState, type FormEvent } from "react";

import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { TextField } from "@/components/Field";
import { FormMessage } from "@/components/FormMessage";
import { Stagger, StaggerItem } from "@/components/Motion";
import { api, setAccessToken } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { EmailChangeIn, PasswordChangeIn, TokenOut, UserMe } from "@/lib/types";

import { statusFor, useFormRequest, type SetStatus, type Status } from "./status";

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function PasswordForm({ status, setStatus }: { status: Status; setStatus: SetStatus }) {
  const { reload } = useAuth();
  const empty: PasswordChangeIn = { current_password: "", new_password: "", confirm_password: "" };
  const [draft, setDraft] = useState(empty);
  const request = useFormRequest("password", ["current_password", "new_password", "confirm_password"], setStatus);
  const helpId = useId();
  const mismatch = draft.confirm_password !== "" && draft.confirm_password !== draft.new_password;
  const blocked = !draft.current_password
    ? "Escribe tu contraseña actual."
    : draft.new_password.length < 8
      ? "La nueva contraseña necesita 8 caracteres o más."
      : !draft.confirm_password
        ? "Confirma la nueva contraseña."
        : mismatch
          ? "Corrige el campo marcado."
          : null;
  const own = statusFor(status, "password");

  function change(field: keyof PasswordChangeIn, value: string) {
    setDraft({ ...draft, [field]: value });
    request.edited(field);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (blocked) return;
    void request.run(async () => {
      // The API revokes every session and returns a fresh one for this device.
      const session = await api<TokenOut>("/account/password", { method: "POST", json: draft });
      setAccessToken(session.access_token);
      await reload();
      setDraft(empty);
      return "Contraseña actualizada. Cerramos tus otras sesiones.";
    });
  }

  return (
    <Card className="p-6">
      <form className="grid gap-2" onSubmit={submit} noValidate>
        <h2 className="mb-2 text-xl">Contraseña</h2>
        <TextField
          label="Contraseña actual"
          type="password"
          autoComplete="current-password"
          required
          reserve
          value={draft.current_password}
          error={request.errors.current_password}
          onChange={(e) => change("current_password", e.target.value)}
        />
        <TextField
          label="Nueva contraseña"
          type="password"
          autoComplete="new-password"
          hint="Mínimo 8 caracteres."
          minLength={8}
          maxLength={128}
          required
          value={draft.new_password}
          error={request.errors.new_password}
          onChange={(e) => change("new_password", e.target.value)}
        />
        <TextField
          label="Confirma la nueva contraseña"
          type="password"
          autoComplete="new-password"
          required
          reserve
          value={draft.confirm_password}
          error={mismatch ? "Las contraseñas no coinciden." : request.errors.confirm_password}
          onChange={(e) => change("confirm_password", e.target.value)}
        />
        <div className="mt-2 grid gap-2">
          <div>
            <Button type="submit" loading={request.busy} disabled={Boolean(blocked)} aria-describedby={helpId}>
              Cambiar contraseña
            </Button>
          </div>
          <FormMessage id={helpId} lines={2} message={own?.text} tone={own?.tone} hint={blocked} />
        </div>
      </form>
    </Card>
  );
}

function EmailForm({ user, status, setStatus }: { user: UserMe; status: Status; setStatus: SetStatus }) {
  const { reload } = useAuth();
  const empty: EmailChangeIn = { new_email: "", current_password: "" };
  const [draft, setDraft] = useState(empty);
  const request = useFormRequest("email", ["new_email", "current_password"], setStatus);
  const helpId = useId();
  const blocked = !draft.new_email.trim()
    ? "Escribe el nuevo correo."
    : !draft.current_password
      ? "Escribe tu contraseña actual para confirmar."
      : null;
  const own = statusFor(status, "email");

  function change(field: keyof EmailChangeIn, value: string) {
    setDraft({ ...draft, [field]: value });
    request.edited(field);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (blocked) return;
    const newEmail = draft.new_email.trim();
    if (!EMAIL.test(newEmail)) return request.reject({ new_email: "Escribe un correo válido, como nombre@dominio.com." });
    void request.run(async () => {
      await api<UserMe>("/account/email", { method: "POST", json: { ...draft, new_email: newEmail } });
      await reload();
      setDraft(empty);
      return "Correo actualizado. Úsalo al iniciar sesión.";
    });
  }

  return (
    <Card className="p-6">
      <form className="grid gap-2" onSubmit={submit} noValidate>
        <div className="mb-2">
          <h2 className="text-xl">Correo</h2>
          <p className="text-sm text-muted">
            Actual: <span className="font-semibold text-ink break-all">{user.email}</span>
          </p>
        </div>
        <TextField
          label="Nuevo correo"
          type="email"
          autoComplete="email"
          required
          reserve
          value={draft.new_email}
          error={request.errors.new_email}
          onChange={(e) => change("new_email", e.target.value)}
        />
        <TextField
          label="Contraseña actual"
          type="password"
          autoComplete="current-password"
          required
          reserve
          value={draft.current_password}
          error={request.errors.current_password}
          onChange={(e) => change("current_password", e.target.value)}
        />
        <div className="mt-2 grid gap-2">
          <div>
            <Button type="submit" loading={request.busy} disabled={Boolean(blocked)} aria-describedby={helpId}>
              Cambiar correo
            </Button>
          </div>
          <FormMessage id={helpId} lines={2} message={own?.text} tone={own?.tone} hint={blocked} />
        </div>
      </form>
    </Card>
  );
}

export function SecurityTab({ user, play }: { user: UserMe; play: boolean }) {
  // Shared by both forms: changing the email replaces the password's message and vice versa.
  const [status, setStatus] = useState<Status>(null);
  return (
    <Stagger className="grid max-w-2xl gap-6" play={play}>
      <StaggerItem>
        <PasswordForm status={status} setStatus={setStatus} />
      </StaggerItem>
      <StaggerItem>
        <EmailForm user={user} status={status} setStatus={setStatus} />
      </StaggerItem>
    </Stagger>
  );
}
