// Helpers shared by the community screens (UPS-035 split of index.tsx).
import type { ChannelOut, UserMe } from "@/lib/types";

/** GET /api/channels also says whether the caller may post there (club channels: members and admins). */
export type CommunityChannel = ChannelOut & { can_post?: boolean };

const relative = new Intl.RelativeTimeFormat("es-MX", { numeric: "auto" });

export function timeAgo(iso: string): string {
  const minutes = Math.round((new Date(iso).getTime() - Date.now()) / 60_000);
  if (Math.abs(minutes) < 60) return relative.format(minutes, "minute");
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 24) return relative.format(hours, "hour");
  return relative.format(Math.round(hours / 24), "day");
}

export function canModerate(user: UserMe | null, channel: ChannelOut | undefined): boolean {
  if (!user || !channel) return false;
  if (user.role === "superadmin") return true;
  return user.role === "academy_admin" && channel.academy_id !== null && channel.academy_id === user.academy_id;
}

/** Long words, pasted URLs and the like wrap instead of widening the page (no horizontal scroll at 390 px). */
export const WRAP = "min-w-0 [overflow-wrap:anywhere]";
