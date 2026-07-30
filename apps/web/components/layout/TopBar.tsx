'use client'

import { useSession, signOut } from 'next-auth/react'
import { Moon, Sun, LogOut, User, ChevronDown, Shield, LayoutGrid, Check, Building2 } from 'lucide-react'
import { useTheme } from 'next-themes'
import { useState, useEffect, useRef, useCallback } from 'react'
import { createPortal } from 'react-dom'
import { usePathname } from 'next/navigation'
import { useRole } from '@/components/rbac/useRole'

interface Workspace {
  id: string
  name: string
}

function roleBadge(role: string | null, isPlatformAdmin: boolean) {
  if (isPlatformAdmin) return { label: 'Platform Admin', cls: 'bg-blue-100 text-blue-800 dark:bg-blue-200 dark:text-blue-800' }
  if (role === 'org_admin') return { label: 'Org Admin', cls: 'bg-blue-100 text-blue-800 dark:bg-blue-200 dark:text-blue-800' }
  if (role === 'workspace_admin') return { label: 'WS Admin', cls: 'bg-blue-100 text-blue-700 dark:bg-blue-200 dark:text-blue-800' }
  if (role === 'member') return { label: 'Member', cls: 'bg-slate-100 text-slate-600 dark:bg-slate-200 dark:text-slate-700' }
  if (role === 'viewer') return { label: 'Viewer', cls: 'bg-slate-100 text-slate-500 dark:bg-slate-200 dark:text-slate-600' }
  return null
}

export default function TopBar() {
  const { data: session, update } = useSession()
  const { resolvedTheme, setTheme } = useTheme()
  const pathname = usePathname()
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [wsMenuOpen, setWsMenuOpen] = useState(false)
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [switching, setSwitching] = useState(false)
  const [dropdownPos, setDropdownPos] = useState<{ top: number; left: number } | null>(null)
  const [mounted, setMounted] = useState(false)
  const wsButtonRef = useRef<HTMLButtonElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const { isPlatformAdmin, isOrgAdmin, tenantRole, workspaceRole } = useRole()

  const s = session as Record<string, unknown> | null
  const displayName = (s?.fullName as string) || (s?.email as string) || 'User'
  const workspaceName = (s?.workspaceName as string) || 'Workspace'
  const orgName = (s?.tenantName as string) || (s?.orgName as string) || ''
  const email = (s?.email as string) || ''
  const apiKey = (s?.apiKey as string) || ''
  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const badge = roleBadge(workspaceRole || tenantRole, isPlatformAdmin)

  // Mount flag for portal (SSR-safe)
  useEffect(() => { setMounted(true) }, [])

  // Close both menus when navigating to a different page
  useEffect(() => {
    setWsMenuOpen(false)
    setUserMenuOpen(false)
  }, [pathname])

  // Recalculate dropdown position from the button (not the container div)
  const openWsMenu = useCallback(() => {
    if (switching || !wsButtonRef.current) return
    const rect = wsButtonRef.current.getBoundingClientRect()
    // Clamp left so dropdown doesn't run off screen
    const left = Math.min(rect.left, window.innerWidth - 264)
    setDropdownPos({ top: rect.bottom + 4, left: Math.max(8, left) })
    setWsMenuOpen(true)
  }, [switching])

  // Close workspace menu on outside click (checks both button ref and dropdown ref)
  useEffect(() => {
    if (!wsMenuOpen) return
    function handleClick(e: MouseEvent) {
      const target = e.target as Node
      if (
        wsButtonRef.current?.contains(target) ||
        dropdownRef.current?.contains(target)
      ) return
      setWsMenuOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [wsMenuOpen])

  // Re-position dropdown on scroll/resize while open
  useEffect(() => {
    if (!wsMenuOpen) return
    function reposition() {
      if (!wsButtonRef.current) return
      const rect = wsButtonRef.current.getBoundingClientRect()
      const left = Math.min(rect.left, window.innerWidth - 264)
      setDropdownPos({ top: rect.bottom + 4, left: Math.max(8, left) })
    }
    window.addEventListener('scroll', reposition, true)
    window.addEventListener('resize', reposition)
    return () => {
      window.removeEventListener('scroll', reposition, true)
      window.removeEventListener('resize', reposition)
    }
  }, [wsMenuOpen])

  // Fetch workspaces when workspace menu opens
  useEffect(() => {
    if (!wsMenuOpen || !apiKey || workspaces.length > 0) return
    fetch(`${apiBase}/org/workspaces/my`, {
      headers: { Authorization: `Bearer ${apiKey}` },
    })
      .then((r) => r.ok ? r.json() : [])
      .then((data: Workspace[]) => setWorkspaces(data))
      .catch(() => {})
  }, [wsMenuOpen, apiKey, apiBase, workspaces.length])

  async function handleSwitchWorkspace(ws: Workspace) {
    if (ws.name === workspaceName) { setWsMenuOpen(false); return }
    setSwitching(true)
    setWsMenuOpen(false)
    try {
      const r = await fetch(`${apiBase}/auth/switch-workspace`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ workspace_id: ws.id }),
      })
      if (!r.ok) throw new Error('Switch failed')
      const data = await r.json()
      await update({
        apiKey: data.api_key,
        workspaceId: data.workspace_id,
        workspaceName: data.workspace_name,
        tenantId: data.tenant_id,
        tenantName: data.tenant_name,
        workspaceRole: data.workspace_role,
        tenantRole: data.tenant_role,
        workspaceIds: data.workspace_ids,
      })
      window.location.reload()
    } catch {
      signOut({ callbackUrl: '/login' })
    } finally {
      setSwitching(false)
    }
  }

  // Portal dropdown — rendered at document.body root so it escapes ALL stacking contexts
  const wsDropdown = mounted && wsMenuOpen && dropdownPos ? createPortal(
    <div
      ref={dropdownRef}
      className="fixed w-64 rounded-xl border border-slate-200 bg-[#f8fafc] py-1.5 shadow-xl dark:border-slate-300 dark:bg-[#edf3f9]"
      style={{ top: dropdownPos.top, left: dropdownPos.left, zIndex: 99999 }}
    >
      <div className="px-3 py-1.5 border-b border-slate-100 dark:border-slate-800">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-400">Switch Workspace</p>
      </div>
      {workspaces.length === 0 ? (
        <div className="px-3 py-3 text-xs text-slate-400">Loading workspaces…</div>
      ) : (
        workspaces.map((ws) => {
          const isCurrent = ws.name === workspaceName
          return (
            <button
              key={ws.id}
              onClick={() => handleSwitchWorkspace(ws)}
              className={`flex w-full items-center gap-2.5 px-3 py-2.5 text-sm transition-colors ${
                isCurrent
                  ? 'bg-blue-50 text-blue-800 dark:bg-blue-100 dark:text-blue-800'
                  : 'text-slate-700 hover:bg-slate-50 dark:text-slate-700 dark:hover:bg-blue-50'
              }`}
            >
              <div className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-xs font-bold text-white ${
                isCurrent ? 'bg-blue-600' : 'bg-gradient-to-br from-slate-400 to-slate-500'
              }`}>
                {ws.name.charAt(0).toUpperCase()}
              </div>
              <span className="flex-1 text-left font-medium truncate">{ws.name}</span>
              {isCurrent && <Check className="h-4 w-4 shrink-0 text-blue-600" />}
            </button>
          )
        })
      )}
      <div className="mx-3 border-t border-slate-100 dark:border-slate-800 mt-1 pt-1">
        {(isOrgAdmin || isPlatformAdmin) && (
          <a href="/workspace" className="flex w-full items-center gap-2 px-0 py-1.5 text-xs text-slate-500 transition-colors hover:text-blue-700 dark:text-slate-600 dark:hover:text-blue-700">
            <LayoutGrid className="h-3.5 w-3.5" /> Manage workspaces
          </a>
        )}
      </div>
    </div>,
    document.body
  ) : null

  return (
    <header className="relative z-30 flex h-14 items-center justify-between border-b border-slate-200 bg-[#f8fafc]/95 px-4 dark:border-slate-300 dark:bg-[#edf3f9]/95">
      {/* Left: org > workspace breadcrumb + switcher */}
      <div className="flex items-center gap-1.5">
        {orgName && (
          <>
            <div className="flex items-center gap-1.5">
              <Building2 className="h-3.5 w-3.5 text-slate-400" />
              <span className="text-xs font-medium tracking-[-0.01em] text-slate-500 dark:text-slate-400">{orgName}</span>
            </div>
            <span className="text-slate-300 dark:text-slate-600">/</span>
          </>
        )}

        {/* Workspace switcher button — ref is ONLY on the button itself */}
        <button
          ref={wsButtonRef}
          onClick={() => wsMenuOpen ? setWsMenuOpen(false) : openWsMenu()}
          disabled={switching}
          className="flex items-center gap-1.5 rounded-lg px-2 py-1 text-sm font-semibold tracking-[-0.015em] text-slate-700 transition-colors hover:bg-blue-50 dark:hover:bg-blue-100 disabled:opacity-60"
        >
          <LayoutGrid className={`h-3.5 w-3.5 ${switching ? 'animate-spin text-blue-500' : 'text-blue-700'}`} />
          <span>{workspaceName}</span>
          {!switching && <ChevronDown className={`h-3.5 w-3.5 text-slate-400 transition-transform ${wsMenuOpen ? 'rotate-180' : ''}`} />}
        </button>

        {badge && (
          <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${badge.cls}`}>
            {badge.label}
          </span>
        )}
      </div>

      {/* Workspace dropdown portal */}
      {wsDropdown}

      {/* Right: controls */}
      <div className="flex items-center gap-2">
        {/* Theme toggle */}
        <button
          onClick={() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')}
          className="rounded-lg p-2 text-slate-500 transition-colors hover:bg-blue-50 hover:text-slate-700 dark:text-slate-600 dark:hover:bg-blue-100 dark:hover:text-slate-800"
          aria-label="Toggle theme"
        >
          {resolvedTheme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </button>

        {/* User menu */}
        <div className="relative">
          <button
            onClick={() => setUserMenuOpen(!userMenuOpen)}
            className="flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-sm text-slate-700 transition-colors hover:bg-blue-50 dark:hover:bg-blue-100"
          >
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-200">
              {isPlatformAdmin
                ? <Shield className="h-3.5 w-3.5 text-blue-700" />
                : <User className="h-3.5 w-3.5 text-blue-700" />
              }
            </div>
            <span className="max-w-[120px] truncate font-semibold tracking-[-0.015em]">{displayName}</span>
            <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
          </button>

          {userMenuOpen && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setUserMenuOpen(false)} />
              <div className="absolute right-0 top-full z-50 mt-1 w-56 rounded-xl border border-slate-200 bg-[#f8fafc] py-1.5 shadow-lg dark:border-slate-300 dark:bg-[#edf3f9]">
                <div className="px-3 py-2 border-b border-slate-100 dark:border-slate-800">
                  <p className="text-xs font-semibold text-slate-900 dark:text-white truncate">{displayName}</p>
                  <p className="text-xs text-slate-500 dark:text-slate-400 truncate">{email}</p>
                  {badge && (
                    <span className={`mt-1 inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold ${badge.cls}`}>
                      {badge.label}
                    </span>
                  )}
                </div>
                <button
                  onClick={() => signOut({ callbackUrl: '/login' })}
                  className="flex w-full items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20 transition-colors"
                >
                  <LogOut className="h-4 w-4" />
                  Sign out
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
