// Resource cards filterable by type, with "Cargar más". When `canManage` is true it also creates,
// edits and deletes (the API enforces the same academy scope). Used by /a/:slug/recursos and the
// "Recursos" tab of the academy panel.
import {
  ArrowSquareOut,
  FileText,
  LinkSimple,
  Package,
  PencilSimple,
  PlayCircle,
  Plus,
  Trash,
  type Icon,
} from "@phosphor-icons/react";
import { useCallback, useEffect, useState, type FormEvent } from "react";

import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { SelectField, TextArea, TextField, fieldErrors } from "@/components/Field";
import { Markdown } from "@/components/Markdown";
import { Modal } from "@/components/Overlay";
import { CardSkeleton } from "@/components/Skeleton";
import { EmptyState, ErrorState } from "@/components/States";
import { api, ApiError, errorMessage } from "@/lib/api";
import type { Page, ResourceOut, ResourceType } from "@/lib/types";

const TYPES: { id: ResourceType; label: string; plural: string; icon: Icon }[] = [
  { id: "document", label: "Documento", plural: "Documentos", icon: FileText },
  { id: "link", label: "Link", plural: "Links", icon: LinkSimple },
  { id: "video", label: "Video", plural: "Videos", icon: PlayCircle },
  { id: "other", label: "Otro", plural: "Otros", icon: Package },
];
const typeInfo = (type: ResourceType) => TYPES.find((t) => t.id === type) ?? TYPES[3];
const PAGE_SIZE = 12;

export function ResourceBoard({ slug, academyId, canManage, mascotUrl }: {
  slug: string;
  /** Needed for writes; null while unknown (management stays hidden). */
  academyId: number | null;
  canManage: boolean;
  mascotUrl?: string | null;
}) {
  const [filter, setFilter] = useState<ResourceType | null>(null);
  const [items, setItems] = useState<ResourceOut[] | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [dialog, setDialog] = useState<{ kind: "form"; resource?: ResourceOut } | { kind: "delete"; resource: ResourceOut } | null>(null);

  const fetchPage = useCallback(
    (after: string | null) =>
      api<Page<ResourceOut>>(`/academies/${slug}/resources`, {
        query: { type: filter, cursor: after, limit: PAGE_SIZE },
      }),
    [slug, filter],
  );

  const [version, setVersion] = useState(0);
  const load = () => setVersion((v) => v + 1);

  useEffect(() => {
    let alive = true; // a slower response for a previous filter never overwrites the current one
    fetchPage(null)
      .then((page) => {
        if (!alive) return;
        setItems(page.items);
        setCursor(page.next_cursor ?? null);
        setError(null);
      })
      .catch((err) => alive && setError(errorMessage(err)));
    return () => {
      alive = false;
    };
  }, [fetchPage, version]);

  function changeFilter(next: ResourceType | null) {
    setFilter(next);
    setItems(null);
    setError(null);
  }

  function retry() {
    setItems(null);
    setError(null);
    load();
  }

  async function loadMore() {
    setLoadingMore(true);
    try {
      const page = await fetchPage(cursor);
      setItems((prev) => [...(prev ?? []), ...page.items]);
      setCursor(page.next_cursor ?? null);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoadingMore(false);
    }
  }

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        {/* One row on phones that scrolls sideways inside itself instead of wrapping into two. `w-0 min-w-full`
            keeps the row from widening its grid ancestors (the academy panel) to the chips' full width. */}
        <div role="group" aria-label="Filtrar por tipo" className="flex w-0 min-w-full gap-2 overflow-x-auto pb-1 sm:w-auto sm:min-w-0 sm:flex-wrap">
          {[{ id: null, plural: "Todos" }, ...TYPES].map(({ id, plural }) => (
            <button
              key={plural}
              type="button"
              aria-pressed={filter === id}
              onClick={() => changeFilter(id)}
              // Active state matches the active item of the main navigation.
              className={`min-h-11 shrink-0 rounded-full border px-4 text-sm font-semibold text-ink transition ${
                filter === id ? "border-primary/40 bg-primary/15" : "border-line bg-surface hover:border-secondary"
              }`}
            >
              {plural}
            </button>
          ))}
        </div>
        {canManage && academyId !== null && (
          <Button icon={<Plus weight="bold" />} onClick={() => setDialog({ kind: "form" })}>
            Agregar recurso
          </Button>
        )}
      </div>

      {error ? (
        <ErrorState message={error} onRetry={retry} />
      ) : items === null ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          title={filter ? `No hay ${typeInfo(filter).plural.toLowerCase()} todavía` : "Aún no hay recursos"}
          description={canManage ? undefined : "Vuelve pronto: el equipo del club los irá subiendo."}
          action={
            canManage && academyId !== null ? (
              <Button icon={<Plus weight="bold" />} onClick={() => setDialog({ kind: "form" })}>
                Agregar el primero
              </Button>
            ) : undefined
          }
          mascotUrl={mascotUrl}
        />
      ) : (
        <>
          <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((resource) => (
              <li key={resource.id}>
                <ResourceCard
                  resource={resource}
                  canManage={canManage}
                  onEdit={() => setDialog({ kind: "form", resource })}
                  onDelete={() => setDialog({ kind: "delete", resource })}
                />
              </li>
            ))}
          </ul>
          {cursor && (
            <div className="mt-6 text-center">
              <Button variant="secondary" loading={loadingMore} onClick={() => void loadMore()}>
                Cargar más
              </Button>
            </div>
          )}
        </>
      )}

      {dialog?.kind === "form" && academyId !== null && (
        <Modal open onClose={() => setDialog(null)} title={dialog.resource ? "Editar recurso" : "Nuevo recurso"}>
          <ResourceForm academyId={academyId} resource={dialog.resource} onClose={() => setDialog(null)} onSaved={load} />
        </Modal>
      )}
      {dialog?.kind === "delete" && (
        <Modal open onClose={() => setDialog(null)} title="Eliminar recurso">
          <DeletePrompt resource={dialog.resource} onClose={() => setDialog(null)} onDeleted={load} />
        </Modal>
      )}
    </div>
  );
}


function ResourceCard({ resource, canManage, onEdit, onDelete }: {
  resource: ResourceOut;
  canManage: boolean;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const info = typeInfo(resource.type);
  const TypeIcon = info.icon;
  const href = resource.url ?? resource.file_url;
  return (
    <Card className="flex h-full flex-col gap-3 p-5">
      <div className="flex min-h-7 items-center justify-between gap-2">
        <Badge tone="primary" icon={<TypeIcon weight="bold" aria-hidden />}>
          {info.label}
        </Badge>
        {canManage && (
          // Negative margins keep the 44 px targets without pushing the title down.
          <div className="-my-2 -mr-2 flex">
            <button type="button" aria-label={`Editar ${resource.title}`} title="Editar" onClick={onEdit}
              className="grid size-11 place-items-center rounded-full hover:bg-line/60">
              <PencilSimple weight="bold" />
            </button>
            <button type="button" aria-label={`Eliminar ${resource.title}`} title="Eliminar" onClick={onDelete}
              className="grid size-11 place-items-center rounded-full text-accent-2 hover:bg-line/60">
              <Trash weight="bold" />
            </button>
          </div>
        )}
      </div>
      <h2 className="text-xl">{resource.title}</h2>
      {resource.description && <Markdown source={resource.description} className="text-sm text-muted" />}
      {href && (
        <a href={href} target="_blank" rel="noopener noreferrer" className="mt-auto inline-flex items-center gap-1 font-semibold">
          {resource.url ? "Abrir" : "Ver archivo"} <ArrowSquareOut weight="bold" aria-hidden />
          <span className="sr-only">(se abre en otra pestaña)</span>
        </a>
      )}
    </Card>
  );
}

function ResourceForm({ academyId, resource, onClose, onSaved }: {
  academyId: number;
  resource?: ResourceOut;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const file = form.get("file");
    const hasFile = file instanceof File && file.size > 0;
    const fields = {
      type: String(form.get("type")),
      title: String(form.get("title")).trim(),
      description: String(form.get("description")),
      url: String(form.get("url")).trim(),
    };
    setBusy(true);
    setError(null);
    setErrors({});
    try {
      if (resource) {
        await api(`/resources/${resource.id}`, { method: "PATCH", json: { ...fields, url: fields.url || null } });
        if (hasFile) {
          const upload = new FormData();
          upload.append("file", file);
          await api(`/resources/${resource.id}/file`, { method: "POST", form: upload });
        }
      } else {
        const body = new FormData();
        for (const [key, value] of Object.entries(fields)) body.append(key, value);
        if (hasFile) body.append("file", file);
        await api(`/academies/${academyId}/resources`, { method: "POST", form: body });
      }
      onSaved();
      onClose();
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) setErrors(fieldErrors(err.details));
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="grid gap-4" noValidate>
      <SelectField label="Tipo" name="type" defaultValue={resource?.type ?? "document"} error={errors.type}>
        {TYPES.map((t) => (
          <option key={t.id} value={t.id}>
            {t.label}
          </option>
        ))}
      </SelectField>
      <TextField label="Título" name="title" defaultValue={resource?.title} required maxLength={120} error={errors.title} />
      <TextArea label="Descripción (markdown)" name="description" defaultValue={resource?.description} rows={3} error={errors.description} />
      <TextField
        label="Link"
        name="url"
        type="url"
        defaultValue={resource?.url ?? ""}
        placeholder="https://…"
        hint="Un link http(s), un archivo o ambos."
        error={errors.url}
      />
      <TextField
        label={resource?.file_url ? "Reemplazar archivo" : "Archivo (opcional)"}
        name="file"
        type="file"
        accept="image/png,image/jpeg,image/webp"
        hint="Imagen PNG, JPG o WebP de hasta 5 MB."
      />
      {error && (
        <p role="alert" className="rounded-xl bg-accent-2/10 px-3 py-2 text-sm font-semibold text-accent-2">
          {error}
        </p>
      )}
      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose}>
          Cancelar
        </Button>
        <Button type="submit" loading={busy}>
          {resource ? "Guardar cambios" : "Agregar recurso"}
        </Button>
      </div>
    </form>
  );
}

function DeletePrompt({ resource, onClose, onDeleted }: { resource: ResourceOut; onClose: () => void; onDeleted: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function remove() {
    setBusy(true);
    try {
      await api(`/resources/${resource.id}`, { method: "DELETE" });
      onDeleted();
      onClose();
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-4">
      <p>
        ¿Eliminar <strong>{resource.title}</strong>? Los miembros dejarán de verlo y no se puede deshacer.
      </p>
      {error && (
        <p role="alert" className="rounded-xl bg-accent-2/10 px-3 py-2 text-sm font-semibold text-accent-2">
          {error}
        </p>
      )}
      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose}>
          Cancelar
        </Button>
        <Button variant="danger" loading={busy} onClick={() => void remove()}>
          Eliminar
        </Button>
      </div>
    </div>
  );
}
