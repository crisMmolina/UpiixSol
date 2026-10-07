import type { PublicUser } from "@/lib/types";

const sizes = { sm: "size-8 text-xs", md: "size-10 text-sm", lg: "size-16 text-lg" };

/** Community identity: avatar + nickname only (never email or boleta). */
export function Avatar({ user, size = "md" }: { user: Pick<PublicUser, "nickname" | "avatar_url">; size?: keyof typeof sizes }) {
  if (user.avatar_url) {
    return <img src={user.avatar_url} alt="" className={`${sizes[size]} shrink-0 rounded-full object-cover ring-2 ring-surface`} loading="lazy" />;
  }
  return (
    <span aria-hidden className={`${sizes[size]} grid shrink-0 place-items-center rounded-full bg-primary/20 font-display font-semibold text-ink`}>
      {user.nickname.slice(0, 2).toUpperCase()}
    </span>
  );
}
