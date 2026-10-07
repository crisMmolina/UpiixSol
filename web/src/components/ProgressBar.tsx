export function ProgressBar({ percent, label, showValue = true, size = "md" }: {
  percent: number;
  label: string;
  showValue?: boolean;
  size?: "sm" | "md";
}) {
  const value = Math.max(0, Math.min(100, Math.round(percent)));
  return (
    <div className="flex items-center gap-3">
      <div
        role="progressbar"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={value}
        className={`w-full overflow-hidden rounded-full bg-line ${size === "sm" ? "h-1.5" : "h-2.5"}`}
      >
        <div className="h-full rounded-full bg-primary transition-[width] duration-500 ease-out" style={{ width: `${value}%` }} />
      </div>
      {/* DESIGN.md: the value sits next to the bar, in dark text (never inside the bar). */}
      {showValue && <span className="shrink-0 text-sm font-semibold tabular-nums text-ink">{value} %</span>}
    </div>
  );
}
