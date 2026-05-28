import { Button } from '@heroui/react'
import { Link, type LinkProps } from '@tanstack/react-router'
import type { ReactNode } from 'react'

interface LinkButtonProps extends Pick<LinkProps, 'to' | 'params'> {
  children: ReactNode
  className?: string
  variant?: 'primary' | 'outline' | 'ghost' | 'secondary' | 'tertiary'
}

export function LinkButton({
  children,
  className,
  params,
  to,
  variant = 'primary',
}: LinkButtonProps) {
  return (
    <Link className="inline-flex" params={params} to={to}>
      <Button className={className} size="sm" variant={variant}>
        {children}
      </Button>
    </Link>
  )
}
