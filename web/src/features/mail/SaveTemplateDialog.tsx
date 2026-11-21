// Naming a template: "Guardar como plantilla" (step 2) and "Renombrar plantilla" (gallery), plus the save that
// runs when an email is sent (spec 006 §Decisions).
import { useState } from "react";

import { Button } from "@/components/Button";
import { TextField } from "@/components/Field";
import { FormMessage } from "@/components/FormMessage";
import { Modal } from "@/components/Overlay";
import { api, ApiError, errorMessage } from "@/lib/api";
import type { Block, MailTemplate } from "@/lib/types";

import { MAX_TEMPLATE_DESCRIPTION, MAX_TEMPLATE_NAME, numberedName } from "./composerState";

export interface TemplateContent {
  subject: string;
  preheader?: string;
  blocks: Block[];
}

interface DialogProps {
  mode: "save" | "rename";
  /** "UpiixSol" or "tu club": where a new template is kept. */
  where?: string;
  initial?: { name: string; description: string };
  onClose: () => void;
  onSubmit: (name: string, description: string) => Promise<void>;
}

/** The form mounts when the dialog opens, so its fields start from `initial` with no effect racing the typing. */
function NameForm({ mode, where, initial, onClose, onSubmit }: DialogProps) {
  const [name, setName] = useState(initial?.name ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (!name.trim()) return setError("Escribe un nombre.");
    setBusy(true);
    try {
      await onSubmit(name.trim(), description.trim());
      setBusy(false);
      onClose();
    } catch (err) {
      setError(err instanceof ApiError && err.status === 409 ? "Ya tienes una plantilla con ese nombre." : err instanceof Error && !(err instanceof ApiError) ? err.message : errorMessage(err));
      setBusy(false);
    }
  }

  return (
    <form
      className="grid gap-4"
      onSubmit={(e) => {
        e.preventDefault();
        void submit();
      }}
    >
      {mode === "save" && <p className="text-sm text-muted">{`Se guardará en ${where ?? "UpiixSol"}. Guarda el asunto, el texto de vista previa y los bloques, nunca a los destinatarios.`}</p>}
      <TextField label="Nombre de la plantilla" value={name} maxLength={MAX_TEMPLATE_NAME} autoFocus onChange={(e) => setName(e.target.value.replace(/[\r\n]+/g, " "))} />
      <TextField label="Descripción (opcional)" value={description} maxLength={MAX_TEMPLATE_DESCRIPTION} onChange={(e) => setDescription(e.target.value.replace(/[\r\n]+/g, " "))} />
      <FormMessage message={error} />
      <div className="flex flex-wrap justify-end gap-2">
        <Button variant="ghost" onClick={onClose} disabled={busy}>
          Cancelar
        </Button>
        <Button type="submit" loading={busy}>
          Guardar
        </Button>
      </div>
    </form>
  );
}

/** One dialog for both: `save` creates (shows where it goes), `rename` edits name and description. */
export function TemplateNameDialog({ open, ...props }: DialogProps & { open: boolean }) {
  return (
    <Modal open={open} onClose={props.onClose} title={props.mode === "save" ? "Guardar como plantilla" : "Renombrar plantilla"}>
      {open && <NameForm {...props} />}
    </Modal>
  );
}

export async function createTemplate(name: string, description: string, content: TemplateContent): Promise<MailTemplate> {
  return api<MailTemplate>("/mail/templates", {
    method: "POST",
    json: { name, ...(description ? { description } : {}), subject: content.subject, ...(content.preheader ? { preheader: content.preheader } : {}), blocks: content.blocks },
  });
}

/** Save on send: after a successful send, never throwing. A 409 name clash retries as "<nombre> (2)"…; any other
 * failure comes back as a notice for the sender (the email is already on its way). Null = saved quietly. */
export async function saveAfterSend(name: string, content: TemplateContent): Promise<string | null> {
  for (let n = 1; n <= 5; n++) {
    const attempt = n === 1 ? name : numberedName(name, n);
    try {
      await createTemplate(attempt, "", content);
      return n === 1 ? `Guardamos «${attempt}» como plantilla.` : `Ya había una plantilla con ese nombre: la guardamos como «${attempt}».`;
    } catch (err) {
      if (!(err instanceof ApiError && err.status === 409)) return `El correo se envió, pero no pudimos guardar la plantilla: ${errorMessage(err)}`;
    }
  }
  return "El correo se envió, pero no pudimos guardar la plantilla: ya hay varias con ese nombre.";
}
