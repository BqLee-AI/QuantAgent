import type { ReactNode } from 'react'

interface SectionHeaderProps {
  eyebrow: string
  title: string
  description: string
  action?: ReactNode
}

export function SectionHeader({
  eyebrow,
  title,
  description,
  action,
}: SectionHeaderProps) {
  return (
    <header className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
      <div className="grid gap-1.5">
        <p className="m-0 text-[12px] font-extrabold uppercase tracking-[0.04em] text-muted">
          {eyebrow}
        </p>
        <h2 className="m-0 wrap-anywhere text-title-md font-bold text-ink">
          {title}
        </h2>
        <p className="m-0 max-w-[62ch] text-body-sm text-muted">
          {description}
        </p>
      </div>
      {action}
    </header>
  )
}
