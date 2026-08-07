export function TabSkeleton() {
  return (
    <div className="space-y-4 px-4 pb-6 pt-5" aria-busy="true" aria-label="불러오는 중">
      <div className="h-6 w-32 animate-pulse rounded-md bg-muted" />
      <div className="flex flex-col items-center gap-3 rounded-2xl bg-card p-6 shadow-sm">
        <div className="h-36 w-36 animate-pulse rounded-full bg-muted" />
        <div className="h-4 w-40 animate-pulse rounded bg-muted" />
      </div>
      <div className="space-y-3">
        {[0, 1, 2].map((i) => (
          <div key={i} className="rounded-2xl bg-card p-4 shadow-sm">
            <div className="mb-3 h-4 w-24 animate-pulse rounded bg-muted" />
            <div className="h-3 w-full animate-pulse rounded-full bg-muted" />
          </div>
        ))}
      </div>
      <div className="grid grid-cols-3 gap-3">
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="h-20 animate-pulse rounded-2xl bg-muted" />
        ))}
      </div>
    </div>
  )
}
