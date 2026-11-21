// Email channel UI (spec 003). The "Correos" tab of the superadmin panel; UPS-079 reuses the pieces for clubs.
import { useEffect, useState } from "react";
import type { RouteObject } from "react-router";

import { PageSkeleton } from "@/components/Skeleton";
import { ErrorState } from "@/components/States";
import { api, errorMessage } from "@/lib/api";
import type { AcademyOut, MailStatus, Page } from "@/lib/types";

import type { AcademyChoice } from "./AudiencePicker";
import { BajaPage } from "./BajaPage";
import { Composer } from "./Composer";
import { History } from "./History";

export { AudiencePicker, toAudience, EMPTY_AUDIENCE } from "./AudiencePicker";
export { Composer } from "./Composer";
export { History } from "./History";

export function MailTab() {
  const [status, setStatus] = useState<MailStatus | null>(null);
  const [academies, setAcademies] = useState<AcademyChoice[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    Promise.all([api<MailStatus>("/mail/status"), api<Page<AcademyOut>>("/admin/academies", { query: { limit: 50 } })])
      .then(([s, a]) => {
        setStatus(s);
        setAcademies(a.items.map(({ id, name }) => ({ id, name })));
        setError(null);
      })
      .catch((err) => setError(errorMessage(err)));
  }, [attempt, reloadKey]);

  if (error && !status) return <ErrorState message={error} onRetry={() => setAttempt((n) => n + 1)} />;
  if (!status) return <PageSkeleton />;
  return (
    <div className="grid gap-8">
      <Composer status={status} academies={academies} onSent={() => setReloadKey((n) => n + 1)} />
      <History academies={academies} reloadKey={reloadKey} />
    </div>
  );
}

/** The club panel's "Correos" tab: mail to the admin's own club (or to people of it) and that club's history. */
export function ClubMailTab({ academy }: { academy: AcademyChoice }) {
  const [status, setStatus] = useState<MailStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [attempt, setAttempt] = useState(0);
  const academies = [academy];

  useEffect(() => {
    api<MailStatus>("/mail/status")
      .then((s) => {
        setStatus(s);
        setError(null);
      })
      .catch((err) => setError(errorMessage(err)));
  }, [attempt, reloadKey]);

  if (error && !status) return <ErrorState message={error} onRetry={() => setAttempt((n) => n + 1)} />;
  if (!status) return <PageSkeleton />;
  return (
    <div className="grid gap-8">
      <Composer status={status} academies={academies} kinds={["academy", "individual"]} ownClub onSent={() => setReloadKey((n) => n + 1)} />
      <History academies={academies} reloadKey={reloadKey} ownClub />
    </div>
  );
}

export const routes: RouteObject[] = [
  { path: "/baja", element: <BajaPage /> },
];
