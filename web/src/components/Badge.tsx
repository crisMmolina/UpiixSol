import type { ReactNode } from "react";

type Tone = "neutral" | "primary" | "accent" | "alert" | "success";

const tones: Record<Tone, string> = {
  neutral: "bg-subtle text-ink ring-1 ring-line",
  primary: "bg-primary/15 text-ink ring-1 ring-primary/40",
  accent: "bg-accent text-on-accent",
  alert: "bg-accent-2 text-white", // #B4422F + white = 5.58:1
  success: "bg-primary/15 text-link",
};

export function Badge({ tone = "neutral", children, icon }: { tone?: Tone; children: ReactNode; icon?: ReactNode }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${tones[tone]}`}>
      {icon}
      {children}
    </span>
  );
}
