'use client'

import { useSession } from 'next-auth/react'

export type TenantRole = 'org_admin' | 'org_manager' | 'org_member' | 'org_billing_admin' | 'org_auditor' | null
export type WorkspaceRole = 'workspace_admin' | 'workspace_editor' | 'workspace_contributor' | 'member' | 'viewer' | null

export interface RoleContext {
  isPlatformAdmin: boolean
  tenantRole: TenantRole
  workspaceRole: WorkspaceRole
  /** True if user can manage org-level settings (org_admin only) */
  isOrgAdmin: boolean
  /** True if user has org_admin or org_manager role */
  isOrgElevated: boolean
  /** True if user can manage workspace settings */
  isWorkspaceAdmin: boolean
  /** True if user can manage org-only control-plane settings and pages */
  canManageOrgSettings: boolean
  /** True if user can manage platform-only settings and actions */
  canManagePlatformSettings: boolean
  /** True if user can write/create data (not viewer) */
  canWrite: boolean
  /** True if user can view settings tabs */
  canAccessSettings: boolean
}

export function useRole(): RoleContext {
  const { data: session } = useSession()
  const s = session as Record<string, unknown> | null

  const isPlatformAdmin = (s?.isPlatformAdmin as boolean) ?? false
  const tenantRole = (s?.tenantRole as TenantRole) ?? null
  const workspaceRole = (s?.workspaceRole as WorkspaceRole) ?? null

  const isOrgAdmin = isPlatformAdmin || tenantRole === 'org_admin'
  const isOrgElevated = isPlatformAdmin || tenantRole === 'org_admin' || tenantRole === 'org_manager'
  const isWorkspaceAdmin = isOrgElevated || workspaceRole === 'workspace_admin'
  const canManageOrgSettings = isOrgAdmin || isPlatformAdmin
  const canManagePlatformSettings = isPlatformAdmin
  const canWrite = workspaceRole !== 'viewer' || isOrgElevated
  const canAccessSettings = canManagePlatformSettings

  return {
    isPlatformAdmin,
    tenantRole,
    workspaceRole,
    isOrgAdmin,
    isOrgElevated,
    isWorkspaceAdmin,
    canManageOrgSettings,
    canManagePlatformSettings,
    canWrite,
    canAccessSettings,
  }
}
