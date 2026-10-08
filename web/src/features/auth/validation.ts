// Client checks for /login (same rules as app/schemas/users.py) and the rate-limit message.

import { ApiError, errorMessage } from "@/lib/api";

export type Errors = Record<string, string>;

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function checkEmail(value: string, errors: Errors): void {
  if (!value) errors.email = "Escribe tu correo.";
  else if (!EMAIL.test(value)) errors.email = "Escribe un correo válido.";
}

export function validateLogin(email: string, password: string): Errors {
  const errors: Errors = {};
  checkEmail(email, errors);
  if (!password) errors.password = "Escribe tu contraseña.";
  return errors;
}

export function validateRegister(data: { full_name: string; boleta: string; email: string; password: string; accept: boolean }): Errors {
  const errors: Errors = {};
  if (!data.full_name) errors.full_name = "Escribe tu nombre completo.";
  else if (data.full_name.length < 3) errors.full_name = "Usa al menos 3 caracteres.";
  if (!data.boleta) errors.boleta = "Escribe tu número de boleta.";
  else if (!/^\d{10}$/.test(data.boleta)) errors.boleta = "La boleta debe tener 10 dígitos.";
  checkEmail(data.email, errors);
  if (!data.password) errors.password = "Escribe una contraseña.";
  else if (data.password.length < 8) errors.password = "Usa al menos 8 caracteres.";
  if (!data.accept) errors.accept_privacy = "Debes aceptar el aviso de privacidad.";
  return errors;
}

const UNITS: Record<string, [string, string]> = {
  second: ["un segundo", "segundos"],
  minute: ["un minuto", "minutos"],
  hour: ["una hora", "horas"],
  day: ["un día", "días"],
};

/** How long to wait, from the limiter's details (`{"limit": "5 per 1 minute"}`); the API sends no
 *  Retry-After header and the per-account limit sends no details, so the default is the 1-minute window. */
export function waitTime(details: unknown): string {
  const limit = (details as { limit?: unknown } | null)?.limit;
  const match = typeof limit === "string" ? limit.match(/per (\d+) (second|minute|hour|day)/) : null;
  if (!match) return "un minuto";
  const [one, many] = UNITS[match[2]];
  return match[1] === "1" ? one : `${match[1]} ${many}`;
}

/** Form-level text for a failed login/register. Short on purpose: it must fit the reserved lines
 *  (2 on phones, 1 from 640 px) of its FormMessage. */
export function formError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 429) return `Demasiados intentos. Espera ${waitTime(error.details)}.`;
    if (error.code === "account_exists") return "Ese correo o esa boleta ya tienen cuenta.";
    if (error.status === 422) return "Revisa los campos marcados.";
    if (error.code === "invalid_credentials") return errorMessage(error);
    if (error.code === "http_error" || error.status >= 500) return "No pudimos conectar. Intenta de nuevo.";
    return errorMessage(error);
  }
  return "No pudimos conectar. Intenta de nuevo.";
}
