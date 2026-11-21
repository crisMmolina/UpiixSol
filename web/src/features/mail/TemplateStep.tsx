// Step 1 · Plantilla (spec 005 §Templates): built-in and saved templates with live thumbnails, "En blanco" and the
// sender's recent sent emails. One click loads the content into the composer; over unsaved work it asks first.
// `?reusar=<id>` (from the history) loads a sent email the same way.
import { useEffect, useRef, useState, type Dispatch } from "react";
import { useSearchParams } from "react-router";

import { Button } from "@/components/Button";
import { Modal } from "@/components/Overlay";
import { api, errorMessage } from "@/lib/api";
import type { Campaign, CampaignDetail, MailTemplate, Page } from "@/lib/types";

import { isDirty, loadContent, type ComposerAction, type ComposerState } from "./composerState";
import { NextButton, StepFooter, StepHeader } from "./ComposerSteps";
import { RecentSent, recentSent } from "./RecentSent";
import { TemplateNameDialog } from "./SaveTemplateDialog";
import { TemplateGallery } from "./TemplateGallery";

export function TemplateStep({ state, dispatch, ownClub, refreshKey, onNext }: { refreshKey: number; state: ComposerState; dispatch: Dispatch<ComposerAction>; ownClub: boolean; onNext: () => void }) {
  const [search, setSearch] = useSearchParams();
  const [templates, setTemplates] = useState<MailTemplate[]>([]);
  const [recent, setRecent] = useState<Campaign[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reuseError, setReuseError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [replacing, setReplacing] = useState<(() => void) | null>(null);
  const [renaming, setRenaming] = useState<MailTemplate | null>(null);
  const [deleting, setDeleting] = useState<MailTemplate | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const handled = useRef<string | null>(null);
  const dirtyRef = useRef(false);
  dirtyRef.current = isDirty(state);

  useEffect(() => {
    api<MailTemplate[]>("/mail/templates")
      .then((list) => {
        setTemplates(list);
        setLoadError(null);
      })
      .catch((err) => setLoadError(errorMessage(err)))
      .finally(() => setLoaded(true));
    api<Page<Campaign>>("/mail/campaigns", { query: { limit: 20 } })
      .then((page) => setRecent(recentSent(page.items)))
      .catch(() => setRecent([])); // the section only appears when there is something to show
  }, [refreshKey]);

  /** To step 2, dropping `reusar` from the URL in the same update. */
  function goContent() {
    setSearch((current) => {
      const merged = new URLSearchParams(current);
      merged.set("paso", "contenido");
      merged.delete("reusar");
      return merged;
    });
  }

  /** Loads content, asking first when there is unsaved work. */
  function load(patch: Partial<ComposerState>) {
    const apply = () => {
      dispatch({ type: "patch", patch });
      goContent();
    };
    if (dirtyRef.current) setReplacing(() => apply);
    else apply();
  }

  async function reuse(id: number) {
    setReuseError(null);
    setBusyId(id);
    try {
      const detail = await api<CampaignDetail>(`/mail/campaigns/${id}`);
      load(loadContent({ subject: detail.subject, preheader: detail.content.preheader, blocks: detail.content.blocks }, null));
    } catch {
      setReuseError("No pudimos cargar ese correo. Revisa que siga disponible e intenta de nuevo.");
      setSearch((current) => {
        const merged = new URLSearchParams(current);
        merged.delete("reusar");
        return merged;
      }, { replace: true });
    } finally {
      setBusyId(null);
    }
  }

  const reusar = search.get("reusar");
  useEffect(() => {
    if (!reusar || handled.current === reusar) return;
    handled.current = reusar;
    const id = Number(reusar);
    if (Number.isInteger(id) && id > 0) void reuse(id);
    else setReuseError("No pudimos cargar ese correo. Revisa que siga disponible e intenta de nuevo.");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reusar]);

  async function remove(template: MailTemplate) {
    setDeleteError(null);
    try {
      await api(`/mail/templates/${template.id}`, { method: "DELETE" });
      setTemplates((list) => list.filter((t) => t.id !== template.id));
      setDeleting(null);
    } catch (err) {
      setDeleteError(errorMessage(err));
    }
  }

  const selected = state.template === "blank" ? null : state.template.id;
  return (
    <div className="grid gap-7">
      <StepHeader title="¿Cómo quieres empezar?" lead="Elige una plantilla, usa de nuevo un correo que ya enviaste o empieza en blanco; en el siguiente paso cambias todo lo que quieras." />
      {reuseError && (
        <p role="alert" className="text-sm font-semibold text-danger">
          {reuseError}
        </p>
      )}
      {loadError && (
        <p role="alert" className="text-sm font-semibold text-danger">
          {`No pudimos cargar las plantillas: ${loadError}`}
        </p>
      )}
      <TemplateGallery
        templates={templates}
        loading={!loaded}
        blank={state.template === "blank"}
        selected={selected}
        ownClub={ownClub}
        onPick={(t) => load(loadContent(t, t.id))}
        onBlank={() => load({ ...loadContent({ subject: "", preheader: null, blocks: [] }, null) })}
        onRename={setRenaming}
        onDelete={(t) => {
          setDeleteError(null);
          setDeleting(t);
        }}
      />
      <RecentSent items={recent} busyId={busyId} onReuse={(c) => void reuse(c.id)} />
      <StepFooter>
        <NextButton onClick={onNext} />
      </StepFooter>

      <Modal open={replacing !== null} onClose={() => setReplacing(null)} title="¿Reemplazar tu correo?">
        <div className="grid gap-4">
          <p className="text-sm text-muted">Ya empezaste un correo. Si sigues, se reemplazan el asunto, el texto de vista previa y los bloques; los destinatarios se quedan como están.</p>
          <div className="flex flex-wrap justify-end gap-2">
            <Button variant="ghost" onClick={() => setReplacing(null)}>
              Cancelar
            </Button>
            <Button
              onClick={() => {
                replacing?.();
                setReplacing(null);
              }}
            >
              Reemplazar
            </Button>
          </div>
        </div>
      </Modal>

      <TemplateNameDialog
        open={renaming !== null}
        mode="rename"
        initial={renaming ? { name: renaming.name, description: renaming.description ?? "" } : undefined}
        onClose={() => setRenaming(null)}
        onSubmit={async (name, description) => {
          if (!renaming) return;
          const updated = await api<MailTemplate>(`/mail/templates/${renaming.id}`, { method: "PATCH", json: { name, ...(description ? { description } : {}) } });
          setTemplates((list) => list.map((t) => (t.id === updated.id ? updated : t)));
        }}
      />

      <Modal open={deleting !== null} onClose={() => setDeleting(null)} title="Eliminar plantilla">
        <div className="grid gap-4">
          <p className="text-sm">{`Vas a eliminar «${deleting?.name ?? ""}». Los correos que ya enviaste con ella no cambian.`}</p>
          {deleteError && (
            <p role="alert" className="text-sm font-semibold text-danger">
              {deleteError}
            </p>
          )}
          <div className="flex flex-wrap justify-end gap-2">
            <Button variant="ghost" onClick={() => setDeleting(null)}>
              Cancelar
            </Button>
            <Button variant="danger" onClick={() => deleting && void remove(deleting)}>
              Eliminar
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
