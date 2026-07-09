'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard, LayoutList, MessageSquare,
  FlaskConical, Activity, Wallet, Settings,
  Building2, Users, LayoutGrid, Network, Wrench, Database, BarChart2, FileText, TrendingUp, ShieldCheck, ScrollText, Beaker, TableProperties,
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
        className={`group relative flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm font-medium transition-all duration-150 ${
          active
            ? 'bg-violet-500/10 text-violet-200 shadow-sm dark:bg-violet-500/10 dark:text-violet-200'
            : 'text-slate-400 hover:bg-white/[0.04] hover:text-slate-200 dark:text-slate-400 dark:hover:bg-white/[0.04] dark:hover:text-slate-200'
        }`}
      >
        {active && (
          <span className="absolute left-0 top-1/2 -translate-y-1/2 h-4 w-0.5 rounded-full bg-violet-400" />
        )}
        <Icon className={`h-4 w-4 shrink-0 ${active ? 'text-violet-400' : 'text-slate-500 group-hover:text-slate-300'}`} />
        {label}
      </Link>
    )
  }

  function SectionLabel({ label }: { label: string }) {
    return (
      <div className="mt-4 mb-1 px-2.5">
        <span className="text-[9px] font-bold uppercase tracking-[0.18em] text-slate-600 dark:text-slate-600">
          {label}
        </span>
      </div>
    )
  }

  // Build the bottom admin items based on role — no duplicates
  const bottomItems: { href: string; label: string; icon: React.ElementType }[] = []

  if (isOrgAdmin || isPlatformAdmin) {
    bottomItems.push({ href: '/organization', label: 'Organization', icon: Building2 })
  }

  if (isWorkspaceAdmin || isOrgAdmin || isPlatformAdmin) {
    bottomItems.push({ href: '/users', label: 'Users', icon: Users })
  }

  bottomItems.push({ href: '/workspace', label: 'Workspace', icon: LayoutGrid })

  return (
    <aside className="flex h-full w-60 flex-col border-r border-white/[0.05] bg-white/80 px-3 py-4 backdrop-blur-xl dark:border-white/[0.05] dark:bg-[#070A17]/90">
      {/* Logo */}
      <div className="mb-5 px-2">
        <div className="flex items-center gap-2.5">
          <svg width="28" height="28" viewBox="0 0 56 56" fill="none" xmlns="http://www.w3.org/2000/svg" className="shrink-0">
            <defs>
              <linearGradient id="sb-grad" x1="0" y1="0" x2="56" y2="56" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stopColor="#7C3AED" />
                <stop offset="100%" stopColor="#6366F1" />
              </linearGradient>
            </defs>
            <rect width="56" height="56" rx="14" fill="url(#sb-grad)" />
            <rect x="9" y="33" width="9" height="13" rx="2" fill="white" fillOpacity="0.55" />
            <rect x="23" y="22" width="9" height="24" rx="2" fill="white" />
            <rect x="37" y="13" width="9" height="33" rx="2" fill="white" fillOpacity="0.85" />
            <polyline points="13.5,33 27.5,22 41.5,13" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
          </svg>
          <div>
            <div className="text-sm font-semibold tracking-tight text-slate-900 dark:text-white leading-none" style={{ fontFamily: 'var(--font-display, inherit)' }}>
              RunLedger
            </div>
            <div className="mt-0.5 text-[9px] font-semibold uppercase tracking-[0.18em] text-violet-500 dark:text-violet-400 leading-none">
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
            className={`group relative flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm font-medium transition-all duration-150 ${
              pathname.startsWith('/organization/dashboard')
                ? 'bg-violet-500/10 text-violet-200'
                : 'text-slate-400 hover:bg-white/[0.04] hover:text-slate-200'
            }`}
          >
            {pathname.startsWith('/organization/dashboard') && (
              <span className="absolute left-0 top-1/2 -translate-y-1/2 h-4 w-0.5 rounded-full bg-violet-400" />
            )}
            <LayoutGrid className={`h-4 w-4 shrink-0 ${pathname.startsWith('/organization/dashboard') ? 'text-violet-400' : 'text-slate-500 group-hover:text-slate-300'}`} />
            Global Dashboard
            <span className="ml-auto rounded-full bg-violet-500/15 px-1.5 py-0.5 text-[9px] font-bold text-violet-400 dark:bg-violet-500/15 dark:text-violet-400">
              ORG
            </span>
          </Link>
        )}

        {/* ── Intelligence ── */}
        <SectionLabel label="Intelligence" />
        <NavLink href="/analytics" label="Analytics" icon={BarChart2} />
        <NavLink href="/evaluation" label="Evaluation" icon={FlaskConical} />
        <NavLink href="/experiments" label="Experiments" icon={Beaker} />
        <NavLink href="/datasets" label="Datasets" icon={TableProperties} />
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
            <NavLink href="/budgets" label="Budgets" icon={Wallet} />
            <NavLink href="/outcomes" label="Outcomes & ROI" icon={TrendingUp} />
          </>
        )}

        {/* ── Governance ── */}
        <SectionLabel label="Governance" />
        <NavLink href="/approvals" label="Approvals" icon={ShieldCheck} />
        {isWorkspaceAdmin && (
          <NavLink href="/audit" label="Audit Log" icon={ScrollText} />
        )}
      </nav>

      {/* Bottom section — org/user/workspace management + settings */}
      <div className="mt-4 pt-4 border-t border-white/[0.05]">
        <div className="flex flex-col gap-0.5">
          {bottomItems.map(({ href, label, icon: Icon }) => (
            <NavLink key={href} href={href} label={label} icon={Icon} />
          ))}
          <NavLink href="/settings" label="Settings" icon={Settings} />
        </div>
      </div>
    </aside>
  )
}
