// UPS-012: academy resources.
//   /a/:slug/recursos → cards filterable by type; superadmins and the academy's admin also
//                       create, edit and delete them here (same scope the API enforces).
import { useEffect, useState } from "react";
import type { RouteObject } from "react-router";

import { AcademyLayout, useAcademy } from "@/layouts";
import { api } from "@/lib/api";
import { RequireRole, useAuth } from "@/lib/auth";
import type { AcademyOut } from "@/lib/types";

import { ResourceBoard } from "./ResourceBoard";

/** The academy id (needed for writes) and whether the current user may manage this academy. */
function useManageScope(slug: string): { academyId: number | null; canManage: boolean } {
  const { user } = useAuth();
  const [academyId, setAcademyId] = useState<number | null>(null);
  const mayManage = user?.role === "superadmin" || user?.role === "academy_admin";

  useEffect(() => {
    if (!mayManage) return;
    let alive = true;
    api<AcademyOut>(`/academies/${slug}`)
      .then((academy) => alive && setAcademyId(academy.id))
      .catch(() => alive && setAcademyId(null)); // no management controls; browsing still works
    return () => {
      alive = false;
    };
  }, [slug, mayManage]);

  const canManage =
    academyId !== null && (user?.role === "superadmin" || (user?.role === "academy_admin" && user.academy_id === academyId));
  return { academyId, canManage };
}

function ResourcesPage() {
  const academy = useAcademy();
  const { academyId, canManage } = useManageScope(academy.slug);
  return (
    <div>
      <h1 className="mb-2 text-3xl sm:text-4xl">Recursos</h1>
      <p className="mb-6 text-muted">Documentos, links y videos que comparte {academy.name}.</p>
      <ResourceBoard slug={academy.slug} academyId={academyId} canManage={canManage} mascotUrl={academy.mascot_url} />
    </div>
  );
}

export const routes: RouteObject[] = [
  {
    path: "/a/:slug",
    element: (
      <RequireRole>
        <AcademyLayout />
      </RequireRole>
    ),
    children: [{ path: "recursos", element: <ResourcesPage /> }],
  },
];
