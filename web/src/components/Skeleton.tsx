// Loading placeholders shaped like the final content (DESIGN.md: every data view has a skeleton).

export function Skeleton({ className = "" }: { className?: string }) {
  return <div aria-hidden className={`skeleton rounded-lg ${className}`} />;
}

/** Lines of text; the last one is shorter, like a real paragraph. */
export function SkeletonText({ lines = 3, className = "" }: { lines?: number; className?: string }) {
  return (
    <div aria-hidden className={`grid gap-2 ${className}`}>
      {Array.from({ length: lines }, (_, i) => (
        <Skeleton key={i} className={`h-3.5 ${i === lines - 1 ? "w-2/3" : "w-full"}`} />
      ))}
    </div>
  );
}

export function SkeletonAvatar({ className = "size-10" }: { className?: string }) {
  return <Skeleton className={`shrink-0 rounded-full ${className}`} />;
}

/** Card with an optional media block on top (route covers, club cards, blog posts). */
export function CardSkeleton({ media = false, className = "" }: { media?: boolean; className?: string }) {
  return (
    <div aria-hidden className={`overflow-hidden rounded-card border border-line bg-surface ${className}`}>
      {media && <Skeleton className="aspect-[16/9] w-full rounded-none" />}
      <div className="p-5">
        <Skeleton className="mb-3 h-5 w-1/2" />
        <SkeletonText lines={2} />
      </div>
    </div>
  );
}

/** List of rows with avatar + two lines (posts, events, users). */
export function ListSkeleton({ rows = 4, className = "" }: { rows?: number; className?: string }) {
  return (
    <div aria-hidden className={`grid gap-3 ${className}`}>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex items-center gap-3 rounded-card border border-line bg-surface p-4">
          <SkeletonAvatar />
          <div className="grid flex-1 gap-2">
            <Skeleton className="h-3.5 w-1/3" />
            <Skeleton className="h-3.5 w-3/4" />
          </div>
        </div>
      ))}
    </div>
  );
}

/** Grid of cards (catalogs). */
export function GridSkeleton({ count = 6, media = true, className = "" }: { count?: number; media?: boolean; className?: string }) {
  return (
    <div aria-hidden className={`grid gap-5 sm:grid-cols-2 xl:grid-cols-3 ${className}`}>
      {Array.from({ length: count }, (_, i) => (
        <CardSkeleton key={i} media={media} />
      ))}
    </div>
  );
}

/** Full-page placeholder while the session or a page loads. */
export function PageSkeleton() {
  return (
    <div role="status" aria-label="Cargando" className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-8">
      <Skeleton className="mb-2 h-9 w-72" />
      <Skeleton className="mb-8 h-4 w-96 max-w-full" />
      <GridSkeleton count={3} />
    </div>
  );
}
