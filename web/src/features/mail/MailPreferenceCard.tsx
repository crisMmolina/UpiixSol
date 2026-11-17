// Mi cuenta → "Recibir correos del club": the switch behind PUT /api/mail/preferences (spec 003 §Opt-out).
import { useEffect, useId, useState } from "react";

import { Card } from "@/components/Card";
import { FormMessage } from "@/components/FormMessage";
import { api, errorMessage } from "@/lib/api";
import type { MailPreferences } from "@/lib/types";

export function MailPreferenceCard() {
  const [receive, setReceive] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<{ text: string; tone: "error" | "success" } | null>(null);
  const descId = useId();

  useEffect(() => {
    let live = true;
    api<MailPreferences>("/mail/preferences")
      .then((prefs) => live && setReceive(prefs.receive_club_email))
      .catch((err) => live && setNote({ text: errorMessage(err), tone: "error" }));
    return () => {
      live = false;
    };
  }, []);

  async function toggle() {
    if (receive === null || busy) return;
    const next = !receive;
    setBusy(true);
    setNote(null);
    try {
      const saved = await api<MailPreferences>("/mail/preferences", { method: "PUT", json: { receive_club_email: next } });
      setReceive(saved.receive_club_email);
      setNote({ text: saved.receive_club_email ? "Volverás a recibir correos del club." : "Ya no recibirás correos del club.", tone: "success" });
    } catch (err) {
      setNote({ text: errorMessage(err), tone: "error" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="grid gap-3 p-6">
      <div className="flex items-start justify-between gap-4">
        <div className="grid gap-1">
          <h2 className="text-xl">Correos del club</h2>
          <p id={descId} className="text-sm text-muted">
            Los avisos de tus clubes llegan a tu correo. Si los apagas, solo recibirás los correos de tu cuenta, como cambiar la contraseña.
          </p>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={receive ?? false}
          aria-label="Recibir correos del club"
          aria-describedby={descId}
          disabled={receive === null || busy}
          onClick={() => void toggle()}
          className="group relative -my-2 grid min-h-11 min-w-14 shrink-0 place-items-center disabled:opacity-60"
        >
          <span className={`h-7 w-12 rounded-full border border-line transition-colors motion-reduce:transition-none group-focus-visible:outline-3 ${receive ? "bg-primary" : "bg-line"}`} />
          <span
            aria-hidden
            className={`absolute left-1/2 size-5 -translate-x-[1.35rem] rounded-full bg-surface shadow-soft transition-transform motion-reduce:transition-none ${receive ? "translate-x-[0.35rem]" : ""}`}
          />
        </button>
      </div>
      <FormMessage message={note?.text} tone={note?.tone} lines={{ base: 2, sm: 1 }} />
    </Card>
  );
}
