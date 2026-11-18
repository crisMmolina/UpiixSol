// Reply-To (spec 004 §Reply-To): where replies go. Prefilled from the server's MAIL_REPLY_TO, editable, validated.
import { TextField } from "@/components/Field";

const EMAIL = /^[^\s@<>",;]+@[^\s@<>",;]+\.[^\s@<>",;]+$/;

/** An empty value is fine (the server falls back to its default); otherwise it must be one email. */
export function replyToError(value: string): string | undefined {
  return value.trim() && !EMAIL.test(value.trim()) ? "Escribe un correo válido." : undefined;
}

export function ReplyToField({ value, onChange }: { value: string; onChange: (next: string) => void }) {
  return (
    <TextField
      label="Responder a"
      type="email"
      inputMode="email"
      value={value}
      maxLength={254}
      error={replyToError(value)}
      hint="Las respuestas de quien reciba el correo llegan aquí."
      onChange={(e) => onChange(e.target.value.replace(/\s+/g, ""))}
    />
  );
}
