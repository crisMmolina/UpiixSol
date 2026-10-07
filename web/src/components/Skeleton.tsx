export function Skeleton({ className = "" }: { className?: string }) {
  return <div aria-hidden className={`animate-pulse rounded-xl bg-line/70 ${className}`} />;
}

export function CardSkeleton() {
  return (
    <div className="rounded-card border border-line bg-surface p-5 shadow-soft">
      <Skeleton className="mb-4 h-8 w-32" />
      <Skeleton className="mb-2 h-4 w-full" />
      <Skeleton className="h-4 w-2/3" />
    </div>
  );
}

/** Full-page placeholder while the session or a page loads. */
export function PageSkeleton() {
  return (
    <div role="status" aria-label="Cargando" className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-8">
      <Skeleton className="mb-6 h-10 w-64" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <CardSkeleton />
        <CardSkeleton />
        <CardSkeleton />
      </div>
    </div>
  );
}
