import { Card } from '@heroui/react'
import type { ReactNode } from 'react'

export function PageSectionCard({
  children,
  className = '',
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <Card className={`border border-hairline bg-canvas ${className}`.trim()}>
      <div className="grid gap-4 p-[18px]">
        {children}
      </div>
    </Card>
  )
}
