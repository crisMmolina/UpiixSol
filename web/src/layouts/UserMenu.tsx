import { CaretDown, GearSix, SignOut, UserCircle } from "@phosphor-icons/react";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router";

import { Avatar } from "@/components/Avatar";
import { ButtonLink } from "@/components/Button";
import { homeFor, useAuth } from "@/lib/auth";

export function UserMenu() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (event: MouseEvent | KeyboardEvent) => {
      if (event instanceof KeyboardEvent ? event.key === "Escape" : !ref.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [open]);

  if (!user) {
    return (
      <ButtonLink to="/login" size="sm">
        Entrar
      </ButtonLink>
    );
  }

  const item = "flex min-h-11 items-center gap-2 rounded-xl px-3 text-sm font-medium text-ink no-underline transition hover:bg-subtle";
  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        className="flex min-h-11 items-center gap-2 rounded-full pl-1 pr-2 transition hover:bg-line/60"
      >
        <Avatar user={user} size="sm" />
        <span className="hidden max-w-32 truncate text-sm font-semibold sm:inline">{user.nickname}</span>
        <CaretDown size={14} weight="bold" aria-hidden />
      </button>
      {open && (
        <div role="menu" className="animate-enter absolute right-0 z-40 mt-2 w-56 rounded-2xl border border-line bg-surface p-1.5 shadow-lift">
          <Link role="menuitem" to="/cuenta" className={item} onClick={() => setOpen(false)}>
            <UserCircle size={20} aria-hidden /> Mi cuenta
          </Link>
          {user.role !== "member" && (
            <Link role="menuitem" to={homeFor(user)} className={item} onClick={() => setOpen(false)}>
              <GearSix size={20} aria-hidden /> {user.role === "superadmin" ? "Panel de superadmin" : "Panel de mi club"}
            </Link>
          )}
          <button
            role="menuitem"
            type="button"
            className={`${item} w-full text-left`}
            onClick={async () => {
              setOpen(false);
              await logout();
              navigate("/login", { replace: true });
            }}
          >
            <SignOut size={20} aria-hidden /> Cerrar sesión
          </button>
        </div>
      )}
    </div>
  );
}
