'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard, LayoutList, MessageSquare,
  FlaskConical, Activity, Wallet, Settings,
  Building2, Users, LayoutGrid, Network, Wrench, Database, BarChart2, CreditCard, FileText,
} from 'lucide-react'
import { useRole } from '@/components/rbac/useRole'

const coreNav = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/runs', label: 'Runs', icon: LayoutList },
  { href: '/sessions', label: 'Sessions', icon: MessageSquare },
] as const

// Shown only to org_admin + platform_admin in the core nav section
const globalDashboardItem = { href: '/organization/dashboard', label: 'Global Dashboard', icon: LayoutGrid }

export default function Sidebar() {
  const pathname = usePathname()
  const { isPlatformAdmin, isOrgAdmin, isWorkspaceAdmin } = useRole()
  const canAccessFinance = isWorkspaceAdmin || isOrgAdmin || isPlatformAdmin

  const isActive = (href: string) => {
    if (href === '/dashboard') return pathname === '/dashboard' || pathname === '/'
    return pathname.startsWith(href)
  }

  function NavLink({ href, label, icon: Icon }: { href: string; label: string; icon: React.ElementType }) {
    const active = isActive(href)
    return (
      <Link
        href={href}
        className={`group flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition-all ${
          active
            ? 'bg-gradient-to-r from-teal-100 to-cyan-50 text-teal-800 shadow-sm dark:from-teal-900/60 dark:to-cyan-900/40 dark:text-teal-100'
            : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800/80 dark:hover:text-white'
        }`}
      >
        <Icon className={`h-4 w-4 shrink-0 ${active ? 'text-teal-700 dark:text-teal-200' : 'text-slate-500 dark:text-slate-400'}`} />
        {label}
      </Link>
    )
  }

  function SectionLabel({ label }: { label: string }) {
    return (
      <div className="mt-3 mb-0.5 px-2.5">
        <span className="text-[9px] font-bold uppercase tracking-[0.16em] text-slate-400 dark:text-slate-500">
          {label}
        </span>
      </div>
    )
  }

  // Build the bottom admin items based on role — no duplicates
  const bottomItems: { href: string; label: string; icon: React.ElementType }[] = []

  if (isPlatformAdmin) {
    bottomItems.push({ href: '/admin/tenants', label: 'Organization', icon: Building2 })
  } else if (isOrgAdmin) {
    bottomItems.push({ href: '/organization', label: 'Organization', icon: Building2 })
  }

  if (isPlatformAdmin) {
    bottomItems.push({ href: '/admin/users', label: 'Users', icon: Users })
  } else if (isWorkspaceAdmin) {
    bottomItems.push({ href: '/users', label: 'Users', icon: Users })
  }

  if (isPlatformAdmin) {
    bottomItems.push({ href: '/admin/workspaces', label: 'Workspaces', icon: LayoutGrid })
  } else {
    bottomItems.push({ href: '/workspace', label: 'Workspace', icon: LayoutGrid })
  }

  return (
    <aside className="flex h-full w-60 flex-col border-r border-slate-200/80 bg-white/70 px-3 py-4 backdrop-blur-md dark:border-slate-700/70 dark:bg-slate-900/70">
      {/* Logo */}
      <div className="mb-6 px-2">
        <div className="flex items-center gap-2.5">
          <svg width="28" height="28" viewBox="0 0 56 56" fill="none" xmlns="http://www.w3.org/2000/svg" className="shrink-0">
            <defs>
              <linearGradient id="sb-grad" x1="0" y1="0" x2="56" y2="56" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stopColor="#0f766e" />
                <stop offset="100%" stopColor="#0891b2" />
              </linearGradient>
            </defs>
            <rect width="56" height="56" rx="14" fill="url(#sb-grad)" />
            <rect x="9" y="33" width="9" height="13" rx="2" fill="white" fillOpacity="0.65" />
            <rect x="23" y="22" width="9" height="24" rx="2" fill="white" />
            <rect x="37" y="13" width="9" height="33" rx="2" fill="white" fillOpacity="0.88" />
            <polyline points="13.5,33 27.5,22 41.5,13" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
          </svg>
          <div>
            <div className="text-sm font-semibold tracking-tight text-slate-900 dark:text-white leading-none">
              RunLedger
            </div>
            <div className="mt-0.5 text-[9px] font-semibold uppercase tracking-[0.18em] text-teal-600 dark:text-teal-400 leading-none">
              Control Plane
            </div>
          </div>
        </div>
      </div>

      {/* Main nav */}
      <nav className="flex flex-col gap-0.5 flex-1 overflow-y-auto">
        {/* ── Observe ── */}
        {coreNav.map(({ href, label, icon: Icon }) => (
          <NavLink key={href} href={href} label={label} icon={Icon} />
        ))}
        {(isOrgAdmin || isPlatformAdmin) && (
          <Link
            href={globalDashboardItem.href}
            className={`group flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition-all ${
              pathname.startsWith('/organization/dashboard')
                ? 'bg-gradient-to-r from-violet-100 to-purple-50 text-violet-800 shadow-sm dark:from-violet-900/60 dark:to-purple-900/40 dark:text-violet-100'
                : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800/80 dark:hover:text-white'
            }`}
          >
            <LayoutGrid className={`h-4 w-4 shrink-0 ${pathname.startsWith('/organization/dashboard') ? 'text-violet-700 dark:text-violet-200' : 'text-slate-500 dark:text-slate-400'}`} />
            Global Dashboard
            <span className="ml-auto rounded-full bg-violet-100 px-1.5 py-0.5 text-[9px] font-bold text-violet-600 dark:bg-violet-900/50 dark:text-violet-400">
              ORG
            </span>
          </Link>
        )}

        {/* ── Intelligence ── */}
        <SectionLabel label="Intelligence" />
        <NavLink href="/analytics" label="Analytics" icon={BarChart2} />
        <NavLink href="/evaluation" label="Evaluation" icon={FlaskConical} />
        <NavLink href="/monitoring" label="Monitoring" icon={Activity} />
        <NavLink href="/prompts" label="Prompts" icon={FileText} />

        {/* ── Gateway ── */}
        <SectionLabel label="Gateway" />
        <NavLink href="/gateway" label="Model Gateway" icon={Network} />
        <NavLink href="/tool-registry" label="Tool Registry" icon={Wrench} />
        {(isOrgAdmin || isPlatformAdmin) && (
          <NavLink href="/provider-profiles" label="Provider Profiles" icon={Database} />
        )}

        {/* ── Finance ── */}
        {canAccessFinance && (
          <>
            <SectionLabel label="Finance" />
            <NavLink href="/finance" label="Finance" icon={Wallet} />
          </>
        )}
      </nav>

      {/* Bottom section — org/user/workspace management + settings */}
      <div className="mt-4 pt-4 border-t border-slate-200/80 dark:border-slate-700/70">
        <div className="flex flex-col gap-0.5">
          {bottomItems.map(({ href, label, icon: Icon }) => (
            <NavLink key={href} href={href} label={label} icon={Icon} />
          ))}
          {canAccessFinance && (
            <NavLink href="/billing/subscription" label="Subscription" icon={CreditCard} />
          )}
          <NavLink href="/settings" label="Settings" icon={Settings} />
        </div>
      </div>
    </aside>
  )
}
