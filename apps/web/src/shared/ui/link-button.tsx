import { buttonVariants } from '@heroui/react'
import { Link, type LinkProps } from '@tanstack/react-router'
import type { ReactNode } from 'react'
import { twMerge } from 'tailwind-merge'

interface LinkButtonProps extends Pick<LinkProps, 'to' | 'params'> {
  children: ReactNode
  className?: string
  size?: 'sm' | 'md' | 'lg'
  variant?: 'primary' | 'outline' | 'ghost' | 'secondary' | 'tertiary'
}

export function LinkButton({
  children,
  className,
  params,
  size = 'sm',
  to,
  variant = 'primary',
}: LinkButtonProps) {
  return (
    <Link
      className={twMerge(buttonVariants({ size, variant }), className)}
      params={params}
      to={to}
    >
      {children}
    </Link>
  )
}
