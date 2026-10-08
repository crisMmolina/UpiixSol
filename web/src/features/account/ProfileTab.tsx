// Mi cuenta → Perfil: photo and public data.
import { useId, useState, type FormEvent } from "react";

import { Avatar } from "@/components/Avatar";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { TextField } from "@/components/Field";
import { FormMessage } from "@/components/FormMessage";
import { Stagger, StaggerItem } from "@/components/Motion";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { UserMe } from "@/lib/types";

import { statusFor, useFormRequest, type Errors, type Status } from "./status";

// Same limits as app/media.py (avatar: 2 MB, PNG/JPG/WebP): checked before uploading anything.
const AVATAR_TYPES = ["image/png", "image/jpeg", "image/webp"];
const AVATAR_MAX_BYTES = 2 * 1024 * 1024;

function checkProfile(nickname: string, fullName: string): Errors {
  const errors: Errors = {};
  if (!nickname) errors.nickname = "Escribe tu apodo.";
  else if (nickname.length < 2) errors.nickname = "Usa al menos 2 caracteres.";
  if (!fullName) errors.full_name = "Escribe tu nombre completo.";
  else if (fullName.length < 3) errors.full_name = "Usa al menos 3 caracteres.";
  return errors;
}

export function ProfileTab({ user, play }: { user: UserMe; play: boolean }) {
  const { reload } = useAuth();
  const [draft, setDraft] = useState({ nickname: user.nickname, full_name: user.full_name });
  const [status, setStatus] = useState<Status>(null);
  const profile = useFormRequest("profile", ["nickname", "full_name"], setStatus);
  const avatar = useFormRequest("avatar", [], setStatus);
  const saveHelpId = useId();
  const dirty = draft.nickname !== user.nickname || draft.full_name !== user.full_name;

  function save(event: FormEvent) {
    event.preventDefault();
    const data = { nickname: draft.nickname.trim(), full_name: draft.full_name.trim() };
    const local = checkProfile(data.nickname, data.full_name);
    if (Object.keys(local).length) return profile.reject(local);
    void profile.run(async () => {
      await api<UserMe>("/account/profile", { method: "PATCH", json: data });
      await reload();
      return "Perfil actualizado.";
    });
  }

  function upload(file: File | undefined) {
    if (!file) return;
    if (!AVATAR_TYPES.includes(file.type)) {
      setStatus({ source: "avatar", tone: "error", text: "Usa una imagen PNG, JPG o WebP." });
      return;
    }
    if (file.size > AVATAR_MAX_BYTES) {
      setStatus({ source: "avatar", tone: "error", text: "La imagen supera 2 MB. Elige una más ligera." });
      return;
    }
    const form = new FormData();
    form.append("file", file);
    void avatar.run(async () => {
      await api<UserMe>("/account/avatar", { method: "POST", form });
      await reload();
      return "Foto actualizada.";
    });
  }

  const avatarStatus = statusFor(status, "avatar");
  const profileStatus = statusFor(status, "profile");

  return (
    <Stagger className="grid gap-6 lg:grid-cols-[18rem_1fr]" play={play}>
      <StaggerItem>
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
          <FormMessage
            lines={2}
            className="w-full justify-items-center text-center"
            message={avatarStatus?.text}
            tone={avatarStatus?.tone}
            hint="PNG, JPG o WebP · máx. 2 MB"
          />
        </Card>
      </StaggerItem>

      <StaggerItem>
        <Card className="p-6">
          <form className="grid gap-2" onSubmit={save} noValidate>
            <h2 className="mb-2 text-xl">Datos del perfil</h2>
            <TextField
              label="Apodo"
              hint="Es lo único que se muestra en la comunidad."
              value={draft.nickname}
              minLength={2}
              maxLength={40}
              required
              error={profile.errors.nickname}
              onChange={(e) => {
                setDraft({ ...draft, nickname: e.target.value });
                profile.edited("nickname");
              }}
            />
            <TextField
              label="Nombre completo"
              value={draft.full_name}
              minLength={3}
              maxLength={120}
              required
              reserve
              autoComplete="name"
              error={profile.errors.full_name}
              onChange={(e) => {
                setDraft({ ...draft, full_name: e.target.value });
                profile.edited("full_name");
              }}
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
            <div className="mt-2 grid gap-2">
              <div>
                <Button type="submit" loading={profile.busy} disabled={!dirty} aria-describedby={saveHelpId}>
                  Guardar perfil
                </Button>
              </div>
              <FormMessage
                id={saveHelpId}
                lines={2}
                message={profileStatus?.text}
                tone={profileStatus?.tone}
                hint={dirty ? null : "Cambia tu apodo o tu nombre para poder guardar."}
              />
            </div>
          </form>
        </Card>
      </StaggerItem>
    </Stagger>
  );
}
