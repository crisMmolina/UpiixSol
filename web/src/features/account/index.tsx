// My account (UPS-014, IDEA §2.3): /cuenta with Perfil and Seguridad tabs.

import { useState, type FormEvent } from "react";
import { useSearchParams, type RouteObject } from "react-router";

import { Avatar } from "@/components/Avatar";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { TextField, fieldErrors } from "@/components/Field";
import { Notice } from "@/components/States";
import { api, ApiError, errorMessage, setAccessToken } from "@/lib/api";
import { RequireRole, useAuth } from "@/lib/auth";
import type { EmailChangeIn, PasswordChangeIn, ProfileUpdateIn, TokenOut, UserMe } from "@/lib/types";
import { CampusLayout } from "@/layouts";

export const order = 60;

type Tab = "perfil" | "seguridad";
type Message = { tone: "ok" | "error"; text: string } | null;

function StatusMessage({ message }: { message: Message }) {
  if (!message) return null;
  return (
    <p
      role="status"
      className={`rounded-xl px-3 py-2 text-sm font-semibold ${message.tone === "ok" ? "bg-primary/15 text-ink" : "bg-accent-2/10 text-accent-2"}`}
    >
      {message.text}
    </p>
  );
}

/** Runs a form request: field errors under each input, anything else as a message. */
function useFormRequest() {
  const [busy, setBusy] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState<Message>(null);

  async function run(request: () => Promise<string>) {
    setBusy(true);
    setErrors({});
    setMessage(null);
    try {
      setMessage({ tone: "ok", text: await request() });
    } catch (error) {
      const fields = error instanceof ApiError ? fieldErrors(error.details) : {};
      setErrors(fields);
      setMessage({ tone: "error", text: errorMessage(error) });
    } finally {
      setBusy(false);
    }
  }
  return { busy, errors, message, run };
}

// ── Perfil ───────────────────────────────────────────────────

function ProfileTab({ user }: { user: UserMe }) {
  const { reload } = useAuth();
  const [draft, setDraft] = useState<ProfileUpdateIn>({ nickname: user.nickname, full_name: user.full_name });
  const profile = useFormRequest();
  const avatar = useFormRequest();
  const dirty = draft.nickname !== user.nickname || draft.full_name !== user.full_name;

  function save(event: FormEvent) {
    event.preventDefault();
    void profile.run(async () => {
      await api<UserMe>("/account/profile", { method: "PATCH", json: draft });
      await reload();
      return "Perfil actualizado.";
    });
  }

  function upload(file: File | undefined) {
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    void avatar.run(async () => {
      await api<UserMe>("/account/avatar", { method: "POST", form });
      await reload();
      return "Foto actualizada.";
    });
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[18rem_1fr]">
      <Card className="flex flex-col items-center gap-4 p-6 text-center">
        <Avatar user={{ nickname: user.nickname, avatar_url: user.avatar_url }} size="lg" />
        <div>
          <p className="font-display text-lg font-semibold">{user.nickname}</p>
          <p className="text-sm text-muted">Así te ven en la comunidad</p>
        </div>
        <label className="cursor-pointer rounded-full border border-line px-4 py-2 text-sm font-semibold hover:bg-line/40 focus-within:ring-3 focus-within:ring-primary/25">
          {avatar.busy ? "Subiendo…" : "Cambiar foto"}
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            className="sr-only"
            disabled={avatar.busy}
            onChange={(e) => {
              upload(e.target.files?.[0]);
              e.target.value = "";
            }}
          />
        </label>
        <span className="text-xs text-muted">PNG, JPG o WebP · máx. 2 MB</span>
        <StatusMessage message={avatar.message} />
      </Card>

      <Card className="p-6">
        <form className="grid gap-4" onSubmit={save} noValidate>
          <h2 className="text-xl">Datos del perfil</h2>
          <TextField
            label="Apodo"
            hint="Es lo único que se muestra en la comunidad."
            value={draft.nickname ?? ""}
            minLength={2}
            maxLength={40}
            required
            error={profile.errors.nickname}
            onChange={(e) => setDraft({ ...draft, nickname: e.target.value })}
          />
          <TextField
            label="Nombre completo"
            value={draft.full_name ?? ""}
            minLength={3}
            maxLength={120}
            required
            autoComplete="name"
            error={profile.errors.full_name}
            onChange={(e) => setDraft({ ...draft, full_name: e.target.value })}
          />
          <dl className="grid gap-1 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-muted">Correo</dt>
              <dd className="font-semibold break-all">{user.email}</dd>
            </div>
            <div>
              <dt className="text-muted">Boleta</dt>
              <dd className="font-semibold tabular-nums">{user.boleta ?? "—"}</dd>
            </div>
          </dl>
          <StatusMessage message={profile.message} />
          <div>
            <Button type="submit" loading={profile.busy} disabled={!dirty}>
              Guardar perfil
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}

// ── Seguridad ────────────────────────────────────────────────

function EmailForm({ user }: { user: UserMe }) {
  const { reload } = useAuth();
  const empty: EmailChangeIn = { new_email: "", current_password: "" };
  const [draft, setDraft] = useState(empty);
  const request = useFormRequest();

  function submit(event: FormEvent) {
    event.preventDefault();
    void request.run(async () => {
      await api<UserMe>("/account/email", { method: "POST", json: draft });
      await reload();
      setDraft(empty);
      return "Correo actualizado. Úsalo la próxima vez que inicies sesión.";
    });
  }

  return (
    <Card className="p-6">
      <form className="grid gap-4" onSubmit={submit} noValidate>
        <div>
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
          value={draft.new_email}
          error={request.errors.new_email}
          onChange={(e) => setDraft({ ...draft, new_email: e.target.value })}
        />
        <TextField
          label="Contraseña actual"
          type="password"
          autoComplete="current-password"
          required
          value={draft.current_password}
          error={request.errors.current_password}
          onChange={(e) => setDraft({ ...draft, current_password: e.target.value })}
        />
        <StatusMessage message={request.message} />
        <div>
          <Button type="submit" loading={request.busy} disabled={!draft.new_email || !draft.current_password}>
            Cambiar correo
          </Button>
        </div>
      </form>
    </Card>
  );
}

function PasswordForm() {
  const { reload } = useAuth();
  const empty: PasswordChangeIn = { current_password: "", new_password: "", confirm_password: "" };
  const [draft, setDraft] = useState(empty);
  const request = useFormRequest();
  const mismatch = draft.confirm_password !== "" && draft.confirm_password !== draft.new_password;

  function submit(event: FormEvent) {
    event.preventDefault();
    void request.run(async () => {
      // The API revokes every session and returns a fresh one for this device.
      const session = await api<TokenOut>("/account/password", { method: "POST", json: draft });
      setAccessToken(session.access_token);
      await reload();
      setDraft(empty);
      return "Contraseña actualizada. Cerramos tus sesiones en otros dispositivos.";
    });
  }

  return (
    <Card className="p-6">
      <form className="grid gap-4" onSubmit={submit} noValidate>
        <h2 className="text-xl">Contraseña</h2>
        <TextField
          label="Contraseña actual"
          type="password"
          autoComplete="current-password"
          required
          value={draft.current_password}
          error={request.errors.current_password}
          onChange={(e) => setDraft({ ...draft, current_password: e.target.value })}
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
          onChange={(e) => setDraft({ ...draft, new_password: e.target.value })}
        />
        <TextField
          label="Confirma la nueva contraseña"
          type="password"
          autoComplete="new-password"
          required
          value={draft.confirm_password}
          error={mismatch ? "Las contraseñas no coinciden." : request.errors.confirm_password}
          onChange={(e) => setDraft({ ...draft, confirm_password: e.target.value })}
        />
        <StatusMessage message={request.message} />
        <div>
          <Button
            type="submit"
            loading={request.busy}
            disabled={!draft.current_password || draft.new_password.length < 8 || mismatch || !draft.confirm_password}
          >
            Cambiar contraseña
          </Button>
        </div>
      </form>
    </Card>
  );
}

// ── Page ─────────────────────────────────────────────────────

function AccountPage() {
  const { user } = useAuth();
  const [search, setSearch] = useSearchParams();
  const tab: Tab = search.get("tab") === "seguridad" ? "seguridad" : "perfil";
  if (!user) return null; // RequireRole renders the page only with a session
  const tabs: { id: Tab; label: string }[] = [
    { id: "perfil", label: "Perfil" },
    { id: "seguridad", label: "Seguridad" },
  ];

  return (
    <div className="grid gap-6">
      <h1 className="text-3xl sm:text-4xl">Mi cuenta</h1>
      {user.must_change_password && (
        <Notice
          action={
            tab === "perfil" ? (
              <button type="button" className="font-semibold underline" onClick={() => setSearch({ tab: "seguridad" }, { replace: true })}>
                Ir a Seguridad →
              </button>
            ) : undefined
          }
        >
          Estás usando una contraseña provisional. Cámbiala por una que solo tú conozcas.
        </Notice>
      )}
      <div role="tablist" aria-label="Secciones" className="flex w-full max-w-sm gap-1 rounded-full bg-line/50 p-1">
        {tabs.map(({ id, label }) => (
          <button
            key={id}
            role="tab"
            type="button"
            aria-selected={tab === id}
            onClick={() => setSearch({ tab: id }, { replace: true })}
            className={`min-h-11 flex-1 rounded-full text-sm font-semibold ${tab === id ? "bg-surface text-ink shadow-soft" : "text-muted hover:text-ink"}`}
          >
            {label}
          </button>
        ))}
      </div>
      <section role="tabpanel">
        {tab === "perfil" ? (
          <ProfileTab key={user.id} user={user} />
        ) : (
          <div className="grid max-w-2xl gap-6">
            <PasswordForm />
            <EmailForm user={user} />
          </div>
        )}
      </section>
    </div>
  );
}

export const routes: RouteObject[] = [
  {
    element: (
      <RequireRole>
        <CampusLayout />
      </RequireRole>
    ),
    children: [{ path: "/cuenta", element: <AccountPage /> }],
  },
];
