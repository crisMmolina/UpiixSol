// "Marca del sitio" (UPS-041): the campus name, wordmark colors, logo and mascot, with a live preview of the
// top bar and the login screen. Name and colors are saved with the button; images apply as soon as they upload.
// Every change goes through applySite (lib/brand.tsx), which re-renders the whole app with the new brand.
import { CheckCircle, DownloadSimple, ImageSquare, Trash, UploadSimple, Warning } from "@phosphor-icons/react";
import { useEffect, useState, type ChangeEvent, type FormEvent } from "react";

import { Button, buttonClasses } from "@/components/Button";
import { Card } from "@/components/Card";
import { TextField, fieldErrors } from "@/components/Field";
import { FormMessage } from "@/components/FormMessage";
import { api, ApiError, errorMessage } from "@/lib/api";
import { applySite, BUILT_IN_SITE, LOGO_HEIGHT, reloadSite, useSite, Wordmark, type Site, type SiteSettings } from "@/lib/brand";
import { AcademyTheme, contrastRatio, readableTextOn } from "@/lib/theme";
import type { AcademyBranding } from "@/lib/types";

type Draft = Pick<SiteSettings, "name" | "color_primary" | "color_secondary" | "color_accent">;
type ImageKind = "logo" | "mascot";
type Message = { tone: "success" | "error"; text: string; where: "form" | "images" };

const HEX = /^#[0-9A-F]{6}$/;
const COLOR_FIELDS: { key: Exclude<keyof Draft, "name">; label: string }[] = [
  { key: "color_primary", label: "Primario" },
  { key: "color_secondary", label: "Secundario" },
  { key: "color_accent", label: "Acento" },
];
const IMAGE = {
  logo: {
    label: "Logo",
    builtIn: BUILT_IN_SITE.logo_url ?? "/brand/upiixsol/wordmark.png",
    uploaded: "Logo actualizado en todo el campus.",
    removed: "Logo quitado: el campus muestra el nombre con sus tres colores.",
    confirm: "¿Quitar el logo? En su lugar se mostrará el nombre con los tres colores.",
  },
  mascot: {
    label: "Mascota",
    builtIn: "/brand/upiixsol/mascot.png",
    uploaded: "Mascota actualizada en todo el campus.",
    removed: "Mascota quitada: ya no se muestra en el campus.",
    confirm: "¿Quitar la mascota? Dejará de mostrarse en el campus.",
  },
} as const;

// A brand change remounts every route (App.tsx), this tab included: the result message and any unsaved
// name/color edits are handed to the new instance through here.
type Handoff = { message: Message; draft: Draft | null } | null;
let handoff: Handoff = null;
const handOff = (value: Handoff) => {
  handoff = value;
};

function draftOf(site: Readonly<Site>): Draft {
  return {
    name: site.name,
    color_primary: site.colors.primary,
    color_secondary: site.colors.secondary,
    color_accent: site.colors.accent,
  };
}

function validate(draft: Draft): Record<string, string> {
  const errors: Record<string, string> = {};
  const name = draft.name.trim();
  if (name.length < 2 || name.length > 40) errors.name = "Escribe de 2 a 40 caracteres.";
  for (const { key } of COLOR_FIELDS) if (!HEX.test(draft[key])) errors[key] = "Usa el formato #RRGGBB.";
  return errors;
}

export function SiteBrandTab() {
  const site = useSite();
  const [draft, setDraft] = useState<Draft>(() => handoff?.draft ?? draftOf(site));
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState<Message | null>(() => handoff?.message ?? null);
  const [busy, setBusy] = useState<"save" | ImageKind | null>(null);
  useEffect(() => {
    handOff(null);
  }, []);

  const saved = draftOf(site);
  const dirty = (Object.keys(saved) as (keyof Draft)[]).some((key) => draft[key] !== saved[key]);
  const images = { logo: site.logoUrl, mascot: site.hasMascot ? site.mascotUrl : null };

  /** The server answered with the new brand: show it everywhere and keep the result message. */
  function done(next: SiteSettings, text: string, where: Message["where"], keepDraft: boolean) {
    const result: Message = { tone: "success", text, where };
    handOff({ message: result, draft: keepDraft && dirty ? draft : null });
    setMessage(result);
    applySite(next);
    void reloadSite().catch(() => undefined); // refresh the browser's cached GET /api/site
  }

  function edit(change: Partial<Draft>) {
    setDraft((current) => ({ ...current, ...change }));
    setErrors((current) => Object.fromEntries(Object.entries(current).filter(([key]) => !(key in change))));
    if (message?.where === "form") setMessage(null);
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    const payload = { ...draft, name: draft.name.trim() };
    const invalid = validate(payload);
    setErrors(invalid);
    if (Object.keys(invalid).length) {
      setMessage({ tone: "error", text: "Revisa los campos marcados.", where: "form" });
      return;
    }
    setBusy("save");
    setMessage(null);
    try {
      const next = await api<SiteSettings>("/admin/site", { method: "PUT", json: payload });
      done(next, "Marca guardada. Ya se ve en todo el campus.", "form", false);
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) setErrors(fieldErrors(err.details));
      setMessage({ tone: "error", text: errorMessage(err), where: "form" });
    } finally {
      setBusy(null);
    }
  }

  async function upload(kind: ImageKind, event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = ""; // choosing the same file again still uploads it
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    setBusy(kind);
    setMessage(null);
    try {
      const next = await api<SiteSettings>(`/admin/site/${kind}`, { method: "POST", form });
      done(next, IMAGE[kind].uploaded, "images", true);
    } catch (err) {
      setMessage({ tone: "error", text: errorMessage(err), where: "images" });
    } finally {
      setBusy(null);
    }
  }

  async function remove(kind: ImageKind) {
    if (!window.confirm(IMAGE[kind].confirm)) return;
    setBusy(kind);
    setMessage(null);
    try {
      const next = await api<SiteSettings>(`/admin/site/${kind}`, { method: "DELETE" });
      done(next, IMAGE[kind].removed, "images", true);
    } catch (err) {
      setMessage({ tone: "error", text: errorMessage(err), where: "images" });
    } finally {
      setBusy(null);
    }
  }

  const preview: AcademyBranding = {
    slug: "campus",
    name: draft.name.trim() || site.name,
    logo_url: images.logo,
    mascot_url: images.mascot,
    color_primary: HEX.test(draft.color_primary) ? draft.color_primary : saved.color_primary,
    color_secondary: HEX.test(draft.color_secondary) ? draft.color_secondary : saved.color_secondary,
    color_accent: HEX.test(draft.color_accent) ? draft.color_accent : saved.color_accent,
    color_accent_2: site.colors.accent2,
  };
  const textOnPrimary = contrastRatio(readableTextOn(preview.color_primary), preview.color_primary);
  const formMessage = message?.where === "form" ? message : null;
  const imagesMessage = message?.where === "images" ? message : null;

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
      <div className="grid min-w-0 content-start gap-5">
        <form onSubmit={save} className="grid gap-5" noValidate aria-label="Nombre y colores">
          <Card className="grid gap-4 p-5">
            <h2 className="text-lg">Nombre</h2>
            <TextField
              label="Nombre del sitio"
              name="name"
              value={draft.name}
              maxLength={40}
              required
              onChange={(e) => edit({ name: e.target.value })}
              hint="De 2 a 40 caracteres. Se usa en la barra superior, el acceso y el título de la pestaña."
              error={errors.name}
            />
          </Card>

          <Card className="grid gap-4 p-5">
            <div>
              <h2 className="text-lg">Colores</h2>
              <p className="mt-1 text-sm text-muted">
                Sin logo, el nombre se dibuja así: hasta la primera «x» en primario, la «x» en secundario y el resto en
                acento. El primario también pinta botones y barras.
              </p>
            </div>
            <div className="grid gap-x-4 sm:grid-cols-3">
              {COLOR_FIELDS.map(({ key, label }) => (
                <div key={key} className="flex items-start gap-2">
                  <input
                    type="color"
                    aria-label={`${label}: selector`}
                    value={HEX.test(draft[key]) ? draft[key].toLowerCase() : "#ffffff"}
                    onChange={(e) => edit({ [key]: e.target.value.toUpperCase() })}
                    className="mt-6 h-11 w-12 shrink-0 cursor-pointer rounded-lg border border-line bg-surface p-1"
                  />
                  <div className="min-w-0 flex-1">
                    <TextField
                      label={label}
                      name={key}
                      value={draft[key]}
                      placeholder="#RRGGBB"
                      maxLength={7}
                      spellCheck={false}
                      onChange={(e) => edit({ [key]: e.target.value.trim().toUpperCase() })}
                      reserve
                      error={errors[key]}
                    />
                  </div>
                </div>
              ))}
            </div>
            {/* Always present (two lines kept on phones): the hint changes, the layout does not. */}
            <p className="flex min-h-10 items-start gap-1.5 text-sm sm:min-h-5" data-testid="contrast-hint">
              {textOnPrimary >= 4.5 ? (
                <>
                  <CheckCircle weight="bold" aria-hidden className="mt-0.5 shrink-0 text-link" />
                  <span className="text-muted">
                    Texto sobre el primario: {textOnPrimary.toFixed(2)}:1, cumple contraste AA.
                  </span>
                </>
              ) : (
                <>
                  <Warning weight="bold" aria-hidden className="mt-0.5 shrink-0 text-accent-2" />
                  <span className="font-semibold text-accent-2">
                    Texto sobre el primario: {textOnPrimary.toFixed(2)}:1, no alcanza AA (4.5:1). Usa un tono más claro u
                    oscuro.
                  </span>
                </>
              )}
            </p>
          </Card>

          <div className="grid gap-2">
            <FormMessage message={formMessage?.text} tone={formMessage?.tone} lines={{ base: 2, sm: 1 }} />
            <div className="flex flex-wrap gap-3">
              <Button type="submit" loading={busy === "save"} disabled={!dirty || (busy !== null && busy !== "save")}>
                Guardar marca
              </Button>
              <Button
                variant="ghost"
                disabled={!dirty || busy !== null}
                onClick={() => {
                  setDraft(saved);
                  setErrors({});
                  setMessage(null);
                }}
              >
                Descartar cambios
              </Button>
            </div>
          </div>
        </form>

        <Card className="grid gap-4 p-5" aria-label="Logo y mascota" role="group">
          <div>
            <h2 className="text-lg">Logo y mascota</h2>
            <p className="mt-1 text-sm text-muted">Se aplican al subirlos. PNG, JPG, WebP o SVG · máx. 2 MB.</p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            {(["logo", "mascot"] as const).map((kind) => {
              const current = images[kind];
              const { label, builtIn } = IMAGE[kind];
              return (
                <div key={kind} className="grid gap-3 rounded-2xl border border-line p-4" data-testid={`site-${kind}`}>
                  <span className="text-sm font-semibold">{label}</span>
                  <div className="grid h-24 place-items-center overflow-hidden rounded-xl bg-subtle px-3">
                    {current ? (
                      <img src={current} alt={`${label} actual`} className="max-h-20 max-w-full object-contain" />
                    ) : kind === "logo" ? (
                      <AcademyTheme branding={preview} className="min-w-0 max-w-full">
                        <Wordmark name={preview.name} colors={preview} className={`block truncate ${LOGO_HEIGHT.tile}`} />
                      </AcademyTheme>
                    ) : (
                      <span className="flex flex-col items-center gap-1 text-sm text-muted">
                        <ImageSquare size={28} aria-hidden />
                        Sin mascota
                      </span>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <label
                      className={`${buttonClasses("secondary", "sm")} cursor-pointer focus-within:outline-3 focus-within:outline-secondary ${
                        busy !== null ? "pointer-events-none opacity-60" : ""
                      }`}
                    >
                      {busy === kind ? (
                        <span className="size-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                      ) : (
                        <UploadSimple weight="bold" aria-hidden />
                      )}
                      {current ? "Cambiar" : "Subir"}
                      <input
                        type="file"
                        name={kind}
                        accept="image/png,image/jpeg,image/webp,image/svg+xml"
                        className="sr-only"
                        disabled={busy !== null}
                        aria-label={`Subir ${label.toLowerCase()}`}
                        onChange={(e) => void upload(kind, e)}
                      />
                    </label>
                    <Button
                      size="sm"
                      variant="ghost"
                      icon={<Trash weight="bold" />}
                      disabled={!current || busy !== null}
                      onClick={() => void remove(kind)}
                      aria-label={`Quitar ${label.toLowerCase()}`}
                    >
                      Quitar
                    </Button>
                  </div>
                  <a href={builtIn} download className="inline-flex items-center gap-1 text-xs font-semibold text-link">
                    <DownloadSimple weight="bold" aria-hidden /> Descargar el original de UpiixSol
                  </a>
                </div>
              );
            })}
          </div>
          <FormMessage message={imagesMessage?.text} tone={imagesMessage?.tone} lines={{ base: 2, sm: 1 }} />
        </Card>
      </div>

      <aside className="grid content-start gap-3 lg:sticky lg:top-24 lg:self-start" aria-label="Vista previa">
        <p className="text-sm font-semibold text-muted">Vista previa en vivo</p>
        <AcademyTheme branding={preview} className="grid gap-3">
          <div className="flex h-14 min-w-0 items-center rounded-2xl border border-line bg-subtle px-4" data-testid="preview-header">
            {images.logo ? (
              <img src={images.logo} alt={preview.name} className={`h-(--logo-h) w-auto ${LOGO_HEIGHT.header}`} />
            ) : (
              <Wordmark name={preview.name} colors={preview} className={`block min-w-0 truncate ${LOGO_HEIGHT.header}`} />
            )}
          </div>
          <Card className="grid justify-items-center gap-3 p-5 text-center" data-testid="preview-login">
            {images.logo ? (
              <img src={images.logo} alt={preview.name} className={`h-(--logo-h) w-auto max-w-full ${LOGO_HEIGHT.login}`} />
            ) : (
              <Wordmark name={preview.name} colors={preview} className={`block max-w-full break-words ${LOGO_HEIGHT.login}`} />
            )}
            <p className="font-display text-xl font-semibold">Tus clubs en un solo campus</p>
            <div className="grid h-24 place-items-center">
              {images.mascot ? (
                <img src={images.mascot} alt={`Mascota de ${preview.name}`} className="max-h-24 w-auto object-contain" />
              ) : (
                <span className="text-xs text-muted">Sin mascota</span>
              )}
            </div>
            <div className="grid w-full gap-2 rounded-xl border border-line p-3 text-left" aria-hidden>
              <span className="h-9 rounded-lg border border-line bg-bg" />
              <span className={`${buttonClasses("primary", "sm")} pointer-events-none`}>Entrar</span>
            </div>
          </Card>
        </AcademyTheme>
      </aside>
    </div>
  );
}
