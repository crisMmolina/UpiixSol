// Loading placeholders with the community's real shapes (UPS-035): the channel row/list, the channel
// heading, the composer (same textarea box, same reserved message line) and post cards, so nothing jumps
// when the data arrives, at 390 px or at 1280 px.
import { Card, Skeleton, SkeletonAvatar } from "@/components";

import { COMPOSER_TEXTAREA } from "./shared";

/** Feed, General and one club: a row of chips on phones, a list from `lg`. */
export function ChannelNavSkeleton() {
  return (
    <div aria-hidden className="flex gap-1 overflow-hidden pb-1 lg:grid">
      {["w-20", "w-24", "w-24"].map((width, i) => (
        <Skeleton key={i} className={`h-11 shrink-0 rounded-xl! lg:w-full ${width}`} />
      ))}
    </div>
  );
}

/** Heading (text-xl) + one line of description: the 48 px of the real block. */
export function ChannelHeadingSkeleton() {
  return (
    <div aria-hidden className="grid h-12 content-between py-1">
      <Skeleton className="h-5 w-32" />
      <Skeleton className="h-3.5 w-64 max-w-full" />
    </div>
  );
}

export function ComposerSkeleton() {
  return (
    <Card className="p-4">
      <div aria-hidden className="grid">
        <textarea rows={3} disabled tabIndex={-1} className={`skeleton pointer-events-none resize-none border-transparent ${COMPOSER_TEXTAREA}`} />
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Skeleton className="h-11 w-24 rounded-full!" />
          <Skeleton className="h-11 w-20 rounded-full!" />
          <Skeleton className="ml-auto h-3.5 w-12" />
          <Skeleton className="h-11 w-32 rounded-full!" />
        </div>
        {/* Same space as the composer's FormMessage (2 lines on phones, 1 from sm). */}
        <div className="mt-2 min-h-10 sm:min-h-5" />
      </div>
    </Card>
  );
}

export function PostSkeleton() {
  return (
    <div aria-hidden className="rounded-card border border-line bg-surface p-4">
      <div className="flex items-center gap-3">
        <SkeletonAvatar className="size-10 rounded-full!" />
        <div className="grid flex-1 gap-2">
          <Skeleton className="h-4 w-28" />
          <Skeleton className="h-3 w-36" />
        </div>
      </div>
      <div className="mt-3 grid gap-2.5 py-1">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-2/3" />
      </div>
      <div className="mt-3 flex h-11 items-center justify-between">
        <Skeleton className="h-11 w-14 rounded-full!" />
        <Skeleton className="h-4 w-28" />
      </div>
    </div>
  );
}

export function PostListSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div aria-hidden className="grid gap-4">
      {Array.from({ length: rows }, (_, i) => (
        <PostSkeleton key={i} />
      ))}
    </div>
  );
}

/** One comment: small avatar + a two-line bubble. */
export function CommentSkeleton() {
  return (
    <div aria-hidden className="flex gap-2">
      <SkeletonAvatar className="size-8 rounded-full!" />
      <Skeleton className="h-13 flex-1 rounded-2xl!" />
    </div>
  );
}
