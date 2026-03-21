'use client'

import { useRole } from './useRole'
import type { RoleContext } from './useRole'

interface RoleGuardProps {
  children: React.ReactNode
  fallback?: React.ReactNode
  check: (role: RoleContext) => boolean
}

export function RoleGuard({ children, fallback = null, check }: RoleGuardProps) {
  const role = useRole()
  if (!check(role)) return <>{fallback}</>
  return <>{children}</>
}
