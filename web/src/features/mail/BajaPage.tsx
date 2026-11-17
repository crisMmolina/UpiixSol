// Public /baja?t=… (spec 003 §Opt-out): one button. The server answers the same for a known, unknown or missing token.
import { CheckCircle } from "@phosphor-icons/react";
import { useState } from "react";
import { Link, useSearchParams } from "react-router";

import { Button } from "@/components/Button";
import { FormMessage } from "@/components/FormMessage";
import { api, errorMessage } from "@/lib/api";
import { LOGO_HEIGHT, useSite, Wordmark } from "@/lib/brand";
import { AcademyTheme, CAMPUS_BRANDING } from "@/lib/theme";

export function BajaPage() {
  const site = useSite();
  const [search] = useSearchParams();
  const token = search.get("t");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function unsubscribe() {
    setBusy(true);
    setError(null);
    try {
      await api("/mail/unsubscribe", { method: "POST", query: token ? { t: token } : undefined, json: {} });
      setDone(true);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AcademyTheme branding={CAMPUS_BRANDING}>
      <main className="mx-auto grid max-w-md gap-6 px-4 pt-10 pb-12 sm:pt-16">
        {site.logoUrl ? (
          <img src={site.logoUrl} alt={site.name} {...site.logoSize} className={`mx-auto h-(--logo-h) w-auto ${LOGO_HEIGHT.login}`} />
        ) : (
          <Wordmark
            name={site.name}
            colors={{ color_primary: site.colors.primary, color_secondary: site.colors.secondary, color_accent: site.colors.accent }}
            className={`mx-auto block max-w-full break-words ${LOGO_HEIGHT.login}`}
          />
        )}
        <section aria-label="Darse de baja" className="grid gap-4 rounded-card border border-line bg-surface p-5 shadow-soft sm:p-8">
          {done ? (
            <>
              <CheckCircle size={40} weight="fill" aria-hidden className="text-link" />
              <h1 className="text-2xl sm:text-3xl" role="status">
                Listo, ya no recibirás correos del club
              </h1>
              <p className="text-muted">Los avisos importantes de tu cuenta, como cambiar tu contraseña, seguirán llegando. Si cambias de opinión, vuelve a activarlos en Mi cuenta.</p>
              <Link to="/cuenta" className="inline-flex min-h-11 items-center font-semibold text-link underline">
                Ir a Mi cuenta
              </Link>
            </>
          ) : (
            <>
              <h1 className="text-2xl sm:text-3xl">Darte de baja de los correos del club</h1>
              <p className="text-muted">Dejaremos de enviar avisos de clubes a este correo. Puedes volver a activarlos cuando quieras en Mi cuenta.</p>
              <div>
                <Button onClick={() => void unsubscribe()} loading={busy}>
                  Darme de baja
                </Button>
              </div>
              <FormMessage message={error} lines={2} />
            </>
          )}
        </section>
      </main>
    </AcademyTheme>
  );
}
