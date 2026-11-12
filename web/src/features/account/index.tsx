// My account (UPS-014, IDEA §2.3): /cuenta with Perfil and Seguridad tabs.

import { useState } from "react";
import { useSearchParams, type RouteObject } from "react-router";

import { Notice } from "@/components/States";
import { RequireRole, useAuth } from "@/lib/auth";
import { CampusLayout } from "@/layouts";

import { ProfileTab } from "./ProfileTab";
import { SecurityTab } from "./SecurityTab";

export const order = 60;

type Tab = "perfil" | "seguridad";

// ── Page ─────────────────────────────────────────────────────

function AccountPage() {
  const { user } = useAuth();
  const [search, setSearch] = useSearchParams();
  // First paint shows the tab in place; switching tabs fades the new one in.
  const [switched, setSwitched] = useState(false);
  const tab: Tab = search.get("tab") === "seguridad" ? "seguridad" : "perfil";
  const selectTab = (next: Tab) => {
    if (next === tab) return;
    setSwitched(true);
    setSearch({ tab: next }, { replace: true });
  };
  if (!user) return null; // RequireRole renders the page only with a session
  const tabs: { id: Tab; label: string }[] = [
    { id: "perfil", label: "Perfil" },
    { id: "seguridad", label: "Seguridad" },
  ];

  return (
    <div className="grid gap-6">
      <h1 className="text-3xl sm:text-4xl">Mi cuenta</h1>
      {user.must_change_password && (
        <Notice
          action={
            // Same footprint on both tabs (on Seguridad an invisible twin), so the tab bar never jumps.
            tab === "perfil" ? (
              <button type="button" className="inline-flex min-h-11 items-center font-semibold underline" onClick={() => selectTab("seguridad")}>
                Ir a Seguridad →
              </button>
            ) : (
              <span aria-hidden className="invisible inline-flex min-h-11 items-center font-semibold">
                Ir a Seguridad →
              </span>
            )
          }
        >
          Estás usando una contraseña provisional. Cámbiala por una que solo tú conozcas.
        </Notice>
      )}
      <div role="tablist" aria-label="Secciones" className="flex w-full max-w-sm gap-1 rounded-full bg-line/50 p-1">
        {tabs.map(({ id, label }) => (
          <button
            key={id}
            role="tab"
            type="button"
            aria-selected={tab === id}
            onClick={() => selectTab(id)}
            className={`min-h-11 flex-1 rounded-full text-sm font-semibold ${tab === id ? "bg-surface text-ink shadow-soft" : "text-muted hover:text-ink"}`}
          >
            {label}
          </button>
        ))}
      </div>
      <section role="tabpanel">
        {tab === "perfil" ? (
          <ProfileTab key={user.id} user={user} play={switched} />
        ) : (
          <SecurityTab key={user.id} user={user} play={switched} />
        )}
      </section>
    </div>
  );
}

export const routes: RouteObject[] = [
  {
    element: (
      <RequireRole>
        <CampusLayout />
      </RequireRole>
    ),
    children: [{ path: "/cuenta", element: <AccountPage /> }],
  },
];
