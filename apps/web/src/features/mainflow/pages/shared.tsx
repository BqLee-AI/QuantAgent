export function PageHeader({
  kicker,
  title,
  description,
}: {
  kicker: string
  title: string
  description: string
}) {
  return (
    <section className="page-header">
      <p className="page-kicker">{kicker}</p>
      <h1 className="page-title">{title}</h1>
      <p className="page-description">{description}</p>
    </section>
  )
}

export function DetailFacts({ rows }: { rows: readonly string[] }) {
  return (
    <div className="grid gap-3">
      {rows.map((row) => (
        <p key={row} className="m-0 text-body-sm text-muted">
          {row}
        </p>
      ))}
    </div>
  )
}

export function InfoTag({ children }: { children: string }) {
  return (
    <span className="inline-flex min-h-[26px] items-center rounded-full bg-surface px-3 text-body-sm font-bold text-muted-strong">
      {children}
    </span>
  )
}
