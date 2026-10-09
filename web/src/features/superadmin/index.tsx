// Flow step 6 (UPS-009): superadmin panel — academies (with their channel), users, campus home page and the
// site brand (UPS-041, SiteBrandTab.tsx).
import { ArrowSquareOut, Info, Key, Plus, Power, UserPlus } from "@phosphor-icons/react";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useSearchParams, type RouteObject } from "react-router";

import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { SelectField, TextArea, TextField, fieldErrors } from "@/components/Field";
import { FormMessage } from "@/components/FormMessage";
import { Modal } from "@/components/Overlay";
import { PageSkeleton } from "@/components/Skeleton";
import { ErrorState, Notice } from "@/components/States";
import { api, ApiError, errorMessage } from "@/lib/api";
import { RequireRole, useAuth } from "@/lib/auth";
import { Wordmark } from "@/lib/brand";
import { AcademyTheme, meetsAA, safeAssetPath } from "@/lib/theme";
import type { AcademyOut, HomeContentOut, Page, PasswordResetOut, Role, UserAdminOut } from "@/lib/types";
import { CampusLayout } from "@/layouts";

import { SiteBrandTab } from "./SiteBrandTab";

export const order = 60;

type Tab = "academias" | "usuarios" | "inicio" | "marca";

const ROLE_LABEL: Record<Role, string> = {
  superadmin: "Superadmin",
  academy_admin: "Admin de club",
  member: "Miembro",
};

function useAcademies() {
  const [academies, setAcademies] = useState<AcademyOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(
    () =>
      api<Page<AcademyOut>>("/admin/academies", { query: { limit: 50 } })
        .then((page) => {
          setAcademies(page.items);
          setError(null);
        })
        .catch((err) => setError(errorMessage(err))),
    [],
  );
  useEffect(() => {
    void load();
  }, [load]);
  return { academies, error, reload: load };
}

/** Editing a field clears its error and the form's message (one message at a time, web/DESIGN.md). */
function clearOnEdit(
  event: FormEvent<HTMLFormElement>,
  setErrors: (update: (errors: Record<string, string>) => Record<string, string>) => void,
  setError: (error: string | null) => void,
) {
  const name = (event.target as HTMLInputElement).name;
  setError(null);
  if (name) setErrors((errors) => (name in errors ? Object.fromEntries(Object.entries(errors).filter(([key]) => key !== name)) : errors));
}

// ── Academies ────────────────────────────────────────────────

function NewAcademyForm({ onCreated, onClose }: { onCreated: (a: AcademyOut) => void; onClose: () => void }) {
  const [colors, setColors] = useState({ color_primary: "#00BF63", color_secondary: "#04944F", color_accent: "#F28034" });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const logo = form.get("logo") as File | null;
    setBusy(true);
    setError(null);
    setErrors({});
    try {
      let academy = await api<AcademyOut>("/admin/academies", {
        method: "POST",
        json: {
          slug: String(form.get("slug")).trim().toLowerCase(),
          name: String(form.get("name")).trim(),
          short_description: String(form.get("short_description")).trim(),
          ...colors,
        },
      });
      if (logo && logo.size > 0) {
        const upload = new FormData();
        upload.append("file", logo);
        academy = await api<AcademyOut>(`/academies/${academy.id}/logo`, { method: "POST", form: upload });
      }
      onCreated(academy);
      onClose();
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) setErrors(fieldErrors(err.details));
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} onChange={(e) => clearOnEdit(e, setErrors, setError)} className="grid gap-4" noValidate>
      <TextField label="Nombre" name="name" required maxLength={80} placeholder="UpiixRobótica" reserve error={errors.name} />
      <TextField
        label="Identificador (slug)"
        name="slug"
        required
        pattern="^[a-z0-9]+(-[a-z0-9]+)*$"
        placeholder="upiixrobotica"
        hint="Minúsculas, números y guiones. Será la URL /a/… y el canal #… de la comunidad."
        error={errors.slug}
      />
      <TextField label="Descripción corta" name="short_description" maxLength={200} reserve error={errors.short_description} />
      <div className="grid gap-3 sm:grid-cols-3">
        {(["color_primary", "color_secondary", "color_accent"] as const).map((key) => (
          <label key={key} className="grid gap-1 text-sm font-semibold">
            {key === "color_primary" ? "Primario" : key === "color_secondary" ? "Secundario" : "Acento"}
            <input
              type="color"
              value={colors[key]}
              onChange={(e) => setColors({ ...colors, [key]: e.target.value.toUpperCase() })}
              className="h-11 w-full cursor-pointer rounded-xl border border-line bg-surface p-1"
            />
          </label>
        ))}
      </div>
      {!meetsAA(colors.color_primary) && <Notice tone="alert">El color primario no alcanza contraste AA con su texto.</Notice>}
      <label className="grid gap-1 text-sm font-semibold">
        Logo (opcional)
        <input type="file" name="logo" accept="image/png,image/jpeg,image/webp,image/svg+xml" className="text-sm font-normal" />
      </label>
      <div className="grid gap-2">
        <FormMessage message={error} lines={{ base: 2, sm: 1 }} />
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" loading={busy}>
            Crear club
          </Button>
        </div>
      </div>
    </form>
  );
}

function AcademiesTab() {
  const { academies, error, reload } = useAcademies();
  const [creating, setCreating] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  async function toggle(academy: AcademyOut) {
    const verb = academy.is_active ? "desactivar" : "activar";
    if (!window.confirm(`¿Seguro que quieres ${verb} ${academy.name}? Su contenido e historial se conservan.`)) return;
    try {
      await api(`/admin/academies/${academy.id}`, { method: "PATCH", json: { is_active: !academy.is_active } });
      await reload();
    } catch (err) {
      setNotice(errorMessage(err));
    }
  }

  if (error) return <ErrorState message={error} onRetry={() => void reload()} />;
  if (!academies) return <PageSkeleton />;

  return (
    <div className="grid gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-muted">Al crear un club se crea también su canal en la comunidad.</p>
        <Button icon={<Plus weight="bold" />} onClick={() => setCreating(true)}>
          Nuevo club
        </Button>
      </div>
      {notice && <Notice tone="accent">{notice}</Notice>}
      <div className="grid gap-4 md:grid-cols-2">
        {academies.map((academy) => {
          const logo = safeAssetPath(academy.logo_url);
          return (
            <AcademyTheme key={academy.id} branding={academy}>
              <Card stripe className={`grid gap-3 p-5 ${academy.is_active ? "" : "opacity-70"}`}>
                <div className="flex items-start justify-between gap-2">
                  {logo ? (
                    <img src={logo} alt="" className="h-9 w-auto" />
                  ) : (
                    <Wordmark name={academy.name} colors={academy} className="block min-w-0 truncate text-2xl" />
                  )}
                  <Badge tone={academy.is_active ? "primary" : "alert"}>{academy.is_active ? "Activo" : "Inactivo"}</Badge>
                </div>
                <p className="text-sm">
                  <strong>{academy.name}</strong> · <span className="text-muted">/a/{academy.slug}</span>
                </p>
                <p className="text-sm text-muted">{academy.short_description || "Sin descripción."}</p>
                <div className="flex flex-wrap gap-2">
                  <Link to={`/panel/academia/${academy.slug}`} className="inline-flex min-h-9 items-center gap-1 rounded-full border-2 border-secondary px-3 text-sm font-semibold no-underline">
                    Contenido e identidad <ArrowSquareOut weight="bold" aria-hidden />
                  </Link>
                  <Button size="sm" variant={academy.is_active ? "ghost" : "secondary"} icon={<Power weight="bold" />} onClick={() => void toggle(academy)}>
                    {academy.is_active ? "Desactivar" : "Activar"}
                  </Button>
                </div>
              </Card>
            </AcademyTheme>
          );
        })}
      </div>
      <Modal open={creating} onClose={() => setCreating(false)} title="Nuevo club">
        {creating && (
          <NewAcademyForm
            onClose={() => setCreating(false)}
            onCreated={(academy) => {
              setNotice(`${academy.name} creado con su canal #${academy.slug}. Ya aparece en la página principal.`);
              void reload();
            }}
          />
        )}
      </Modal>
    </div>
  );
}

// ── Users ────────────────────────────────────────────────────

function NewUserForm({ academies, onCreated, onClose }: { academies: AcademyOut[]; onCreated: (u: UserAdminOut) => void; onClose: () => void }) {
  const [role, setRole] = useState<"academy_admin" | "member">("academy_admin");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const boleta = String(form.get("boleta") ?? "").trim();
    setBusy(true);
    setError(null);
    setErrors({});
    try {
      const user = await api<UserAdminOut>("/admin/users", {
        method: "POST",
        json: {
          role,
          email: String(form.get("email")).trim(),
          full_name: String(form.get("full_name")).trim(),
          password: String(form.get("password")),
          boleta: boleta || null,
          academy_id: role === "academy_admin" ? Number(form.get("academy_id")) || null : null,
        },
      });
      onCreated(user);
      onClose();
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) setErrors(fieldErrors(err.details));
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} onChange={(e) => clearOnEdit(e, setErrors, setError)} className="grid gap-4" noValidate>
      <SelectField label="Rol" value={role} onChange={(e) => setRole(e.target.value as typeof role)}>
        <option value="academy_admin">Admin de club</option>
        <option value="member">Miembro</option>
      </SelectField>
      {role === "academy_admin" && (
        <SelectField label="Club" name="academy_id" required defaultValue={academies[0]?.id}>
          {academies.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </SelectField>
      )}
      <TextField label="Nombre completo" name="full_name" required reserve error={errors.full_name} />
      <TextField label="Correo" name="email" type="email" required reserve error={errors.email} />
      {role === "member" && <TextField label="Boleta (opcional)" name="boleta" inputMode="numeric" maxLength={10} reserve error={errors.boleta} />}
      <TextField
        label="Contraseña temporal"
        name="password"
        type="text"
        required
        minLength={8}
        autoComplete="off"
        hint="Compártela en persona; se le pedirá cambiarla al entrar."
        error={errors.password}
      />
      <div className="grid gap-2">
        <FormMessage message={error} lines={{ base: 2, sm: 1 }} />
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" loading={busy}>
            Crear usuario
          </Button>
        </div>
      </div>
    </form>
  );
}

function UsersTab() {
  const { user: me } = useAuth();
  const { academies } = useAcademies();
  const [filters, setFilters] = useState<{ role: string; q: string }>({ role: "", q: "" });
  const [items, setItems] = useState<UserAdminOut[] | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [reset, setReset] = useState<{ user: UserAdminOut; password: string } | null>(null);

  const load = useCallback(
    async (after: string | null) => {
      try {
        const page = await api<Page<UserAdminOut>>("/admin/users", {
          query: { cursor: after, limit: 50, role: filters.role, q: filters.q },
        });
        setItems((prev) => (after && prev ? [...prev, ...page.items] : page.items));
        setCursor(page.next_cursor);
        setError(null);
      } catch (err) {
        setError(errorMessage(err));
      }
    },
    [filters],
  );
  useEffect(() => {
    void load(null);
  }, [load]);

  const academyName = (id: number | null) => academies?.find((a) => a.id === id)?.name ?? "—";

  async function toggle(user: UserAdminOut) {
    if (!window.confirm(`¿${user.is_active ? "Desactivar" : "Activar"} la cuenta de ${user.full_name}?`)) return;
    try {
      await api(`/admin/users/${user.id}`, { method: "PATCH", json: { is_active: !user.is_active } });
      await load(null);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function resetPassword(user: UserAdminOut) {
    if (!window.confirm(`¿Restablecer la contraseña de ${user.full_name}? Se cerrarán sus sesiones.`)) return;
    try {
      const result = await api<PasswordResetOut>(`/admin/users/${user.id}/reset-password`, { method: "POST" });
      setReset({ user, password: result.temporary_password });
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <div className="grid gap-5">
      <form
        className="flex flex-wrap items-end gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          const form = new FormData(event.currentTarget);
          setFilters({ role: String(form.get("role")), q: String(form.get("q")).trim() });
        }}
      >
        <div className="min-w-48 flex-1">
          <TextField label="Buscar" name="q" placeholder="Nombre, correo, apodo o boleta" defaultValue={filters.q} />
        </div>
        <div className="w-48">
          <SelectField label="Rol" name="role" defaultValue={filters.role}>
            <option value="">Todos</option>
            <option value="superadmin">Superadmin</option>
            <option value="academy_admin">Admin de club</option>
            <option value="member">Miembro</option>
          </SelectField>
        </div>
        <Button type="submit" variant="secondary">
          Filtrar
        </Button>
        <Button icon={<UserPlus weight="bold" />} onClick={() => setCreating(true)} className="ml-auto">
          Nuevo usuario
        </Button>
      </form>
      {error && <Notice tone="alert">{error}</Notice>}
      {!items ? (
        <PageSkeleton />
      ) : (
        <Card className="overflow-x-auto">
          <table className="w-full min-w-[48rem] text-left text-sm">
            <thead className="border-b border-line text-muted">
              <tr>
                <th className="px-4 py-3 font-semibold">Nombre</th>
                <th className="px-4 py-3 font-semibold">Rol</th>
                <th className="px-4 py-3 font-semibold">Club</th>
                <th className="px-4 py-3 font-semibold">Boleta</th>
                <th className="px-4 py-3 font-semibold">Estado</th>
                <th className="px-4 py-3 font-semibold">
                  <span className="sr-only">Acciones</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((user) => (
                <tr key={user.id} className="border-b border-line last:border-0">
                  <td className="px-4 py-3">
                    <span className="font-semibold">{user.full_name}</span>
                    {user.id === me?.id && (
                      <span className="ml-2 align-middle">
                        <Badge tone="neutral">Tú</Badge>
                      </span>
                    )}
                    <span className="block text-xs text-muted">{user.email}</span>
                    {user.id === me?.id && (
                      <span className="mt-1 flex items-start gap-1 text-xs text-muted">
                        <Info size={14} weight="bold" aria-hidden className="mt-px shrink-0" />
                        No puedes desactivar tu propia cuenta; otro superadmin sí puede.
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">{ROLE_LABEL[user.role]}</td>
                  <td className="px-4 py-3">{user.role === "academy_admin" ? academyName(user.academy_id) : "—"}</td>
                  <td className="px-4 py-3 tabular-nums">{user.boleta ?? "—"}</td>
                  <td className="px-4 py-3">
                    <Badge tone={user.is_active ? "primary" : "alert"}>{user.is_active ? "Activo" : "Inactivo"}</Badge>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-1">
                      <Button size="sm" variant="ghost" icon={<Key weight="bold" />} onClick={() => void resetPassword(user)}>
                        Restablecer
                      </Button>
                      {user.id !== me?.id ? (
                        <Button size="sm" variant="ghost" icon={<Power weight="bold" />} onClick={() => void toggle(user)}>
                          {user.is_active ? "Desactivar" : "Activar"}
                        </Button>
                      ) : (
                        // Keeps "Restablecer" aligned with the other rows; the reason is under the name.
                        <Button size="sm" variant="ghost" icon={<Power weight="bold" />} className="invisible" aria-hidden tabIndex={-1}>
                          Desactivar
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-muted">
                    Sin resultados.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          {cursor && (
            <div className="p-4 text-center">
              <Button variant="secondary" onClick={() => void load(cursor)}>
                Ver más
              </Button>
            </div>
          )}
        </Card>
      )}
      <Modal open={creating} onClose={() => setCreating(false)} title="Nuevo usuario">
        {creating && academies && (
          <NewUserForm academies={academies.filter((a) => a.is_active)} onClose={() => setCreating(false)} onCreated={() => void load(null)} />
        )}
      </Modal>
      <Modal open={reset !== null} onClose={() => setReset(null)} title="Contraseña temporal">
        {reset && (
          <div className="grid gap-3">
            <p>
              Entrégale esta contraseña a <strong>{reset.user.full_name}</strong> en persona. Se le pedirá cambiarla al entrar.
            </p>
            <code className="select-all rounded-xl bg-line/60 px-3 py-2 text-lg font-semibold">{reset.password}</code>
            <p className="text-xs text-muted">No se volverá a mostrar.</p>
            <Button onClick={() => setReset(null)}>Listo</Button>
          </div>
        )}
      </Modal>
    </div>
  );
}

// ── Home page content ────────────────────────────────────────

function HomeTab() {
  const [content, setContent] = useState<HomeContentOut | null>(null);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<HomeContentOut>("/admin/home")
      .then(setContent)
      .catch((err) => setMessage({ ok: false, text: errorMessage(err) }));
  }, []);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!content) return;
    const form = new FormData(event.currentTarget);
    setBusy(true);
    try {
      const saved = await api<HomeContentOut>("/admin/home", {
        method: "PUT",
        json: { ...content, hero_title: String(form.get("hero_title")).trim(), hero_text: String(form.get("hero_text")) },
      });
      setContent(saved);
      setMessage({ ok: true, text: "Página principal actualizada." });
    } catch (err) {
      setMessage({ ok: false, text: errorMessage(err) });
    } finally {
      setBusy(false);
    }
  }

  if (!content) return message ? <ErrorState message={message.text} /> : <PageSkeleton />;
  return (
    <Card className="max-w-2xl p-5">
      <form onSubmit={save} onChange={() => setMessage(null)} className="grid gap-4">
        <TextField label="Título principal" name="hero_title" defaultValue={content.hero_title} required maxLength={120} />
        <TextArea label="Texto de bienvenida" name="hero_text" defaultValue={content.hero_text} rows={4} />
        <div className="grid gap-2">
          <FormMessage message={message?.text} tone={message?.ok ? "success" : "error"} lines={{ base: 2, sm: 1 }} />
          <Button type="submit" loading={busy} className="justify-self-start">
            Guardar
          </Button>
        </div>
      </form>
    </Card>
  );
}

// ── Page ─────────────────────────────────────────────────────

function SuperadminPage() {
  const [search, setSearch] = useSearchParams();
  const tab: Tab = (["academias", "usuarios", "inicio", "marca"] as const).find((t) => t === search.get("tab")) ?? "academias";
  const tabs: { id: Tab; label: string }[] = [
    { id: "academias", label: "Clubes" },
    { id: "usuarios", label: "Usuarios" },
    { id: "inicio", label: "Página principal" },
    { id: "marca", label: "Marca del sitio" },
  ];
  return (
    <div className="grid gap-6">
      <div>
        <p className="text-sm font-semibold text-link">Mesa directiva</p>
        <h1 className="text-3xl sm:text-4xl">Panel de superadmin</h1>
      </div>
      <div role="tablist" aria-label="Secciones" className="grid w-full max-w-2xl grid-cols-2 gap-1 rounded-3xl bg-line/50 p-1 sm:flex sm:rounded-full">
        {tabs.map(({ id, label }) => (
          <button
            key={id}
            role="tab"
            type="button"
            aria-selected={tab === id}
            onClick={() => setSearch({ tab: id }, { replace: true })}
            className={`min-h-11 flex-1 rounded-full px-3 text-sm font-semibold whitespace-nowrap ${tab === id ? "bg-surface text-ink shadow-soft" : "text-muted hover:text-ink"}`}
          >
            {label}
          </button>
        ))}
      </div>
      <section role="tabpanel">
        {tab === "academias" && <AcademiesTab />}
        {tab === "usuarios" && <UsersTab />}
        {tab === "inicio" && <HomeTab />}
        {tab === "marca" && <SiteBrandTab />}
      </section>
    </div>
  );
}

export const routes: RouteObject[] = [
  {
    element: (
      <RequireRole roles={["superadmin"]}>
        <CampusLayout />
      </RequireRole>
    ),
    children: [{ path: "/admin", element: <SuperadminPage /> }],
  },
];
