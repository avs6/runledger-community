'use client'

import { useEffect, useState, type ReactNode } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard, LayoutList, MessageSquare,
  FlaskConical, Activity, Wallet, Settings,
  Building2, Users, LayoutGrid, Network, Wrench, Database, BarChart2, FileText, TrendingUp, ShieldCheck, ScrollText, Beaker, TableProperties,
  Key, Bell, Plug, Shield, Radio, Settings2, Landmark, ChevronDown,
} from 'lucide-react'
import { useRole } from '@/components/rbac/useRole'

const coreNav = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/runs', label: 'Runs', icon: LayoutList },
  { href: '/sessions', label: 'Sessions', icon: MessageSquare },
] as const

const globalDashboardItem = { href: '/organization/dashboard', label: 'Global Dashboard', icon: LayoutGrid }
const STORAGE_KEY = 'runledger.sidebar.sections'

const defaultSections = {
  intelligence: true,
  gateway: true,
  controlPlane: true,
  finance: true,
  governance: false,
  administration: true,
} as const

type SectionKey = keyof typeof defaultSections

export default function Sidebar() {
  const pathname = usePathname()
  const { isPlatformAdmin, isOrgAdmin, isWorkspaceAdmin, canAccessSettings } = useRole()
  const canAccessFinance = isWorkspaceAdmin || isOrgAdmin || isPlatformAdmin
  const canAccessOrgControl = isOrgAdmin || isPlatformAdmin
  const canAccessApiKeys = isWorkspaceAdmin || canAccessOrgControl
  const [sections, setSections] = useState<Record<SectionKey, boolean>>(defaultSections)

  useEffect(() => {
    const saved = window.localStorage.getItem(STORAGE_KEY)
    if (!saved) return
    try {
      setSections({ ...defaultSections, ...JSON.parse(saved) })
    } catch {
      window.localStorage.removeItem(STORAGE_KEY)
    }
  }, [])

  function toggleSection(section: SectionKey) {
    setSections((prev) => {
      const next = { ...prev, [section]: !prev[section] }
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
      return next
    })
  }

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
            ? 'bg-teal-500/10 text-teal-800 shadow-sm dark:bg-teal-500/10 dark:text-teal-100'
            : 'text-slate-500 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-white/[0.04] dark:hover:text-slate-200'
        }`}
      >
        {active && (
          <span className="absolute left-0 top-1/2 -translate-y-1/2 h-4 w-0.5 rounded-full bg-teal-400" />
        )}
        <Icon className={`h-4 w-4 shrink-0 ${active ? 'text-teal-500 dark:text-teal-300' : 'text-slate-500 group-hover:text-slate-700 dark:group-hover:text-slate-300'}`} />
        {label}
      </Link>
    )
  }

  function Section({ id, label, children }: { id: SectionKey; label: string; children: ReactNode }) {
    const open = sections[id]
    return (
      <div className="mt-3">
        <button
          type="button"
          onClick={() => toggleSection(id)}
          className="mb-1 flex w-full items-center justify-between rounded-md px-2.5 py-1 text-[9px] font-bold uppercase tracking-[0.18em] text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700 dark:text-slate-600 dark:hover:bg-white/[0.04] dark:hover:text-slate-400"
          aria-expanded={open}
        >
          <span>{label}</span>
          <ChevronDown className={`h-3 w-3 transition-transform ${open ? '' : '-rotate-90'}`} />
        </button>
        {open && <div className="flex flex-col gap-0.5">{children}</div>}
      </div>
    )
  }

  return (
    <aside className="flex h-full w-60 flex-col border-r border-slate-200/80 bg-white/85 px-3 py-4 backdrop-blur-xl dark:border-white/[0.05] dark:bg-[#070D18]/92">
      {/* Logo */}
      <div className="mb-5 px-2">
        <div className="flex items-center gap-2.5">
          <svg width="28" height="28" viewBox="0 0 56 56" fill="none" xmlns="http://www.w3.org/2000/svg" className="shrink-0">
            <defs>
              <linearGradient id="sb-grad" x1="0" y1="0" x2="56" y2="56" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#0F766E" />
              <stop offset="100%" stopColor="#0891B2" />
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
            <div className="mt-0.5 text-[9px] font-semibold uppercase tracking-[0.18em] text-teal-600 dark:text-teal-300 leading-none">
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
                ? 'bg-teal-500/10 text-teal-800 dark:text-teal-100'
                : 'text-slate-500 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-white/[0.04] dark:hover:text-slate-200'
            }`}
          >
            {pathname.startsWith('/organization/dashboard') && (
              <span className="absolute left-0 top-1/2 -translate-y-1/2 h-4 w-0.5 rounded-full bg-teal-400" />
            )}
            <LayoutGrid className={`h-4 w-4 shrink-0 ${pathname.startsWith('/organization/dashboard') ? 'text-teal-500 dark:text-teal-300' : 'text-slate-500 group-hover:text-slate-700 dark:group-hover:text-slate-300'}`} />
            Global Dashboard
            <span className="ml-auto rounded-full bg-teal-500/15 px-1.5 py-0.5 text-[9px] font-bold text-teal-700 dark:bg-teal-500/15 dark:text-teal-300">
              ORG
            </span>
          </Link>
        )}

        {/* ── Intelligence ── */}
        <Section id="intelligence" label="Intelligence">
          <NavLink href="/analytics" label="Analytics" icon={BarChart2} />
          <NavLink href="/evaluation" label="Evaluation" icon={FlaskConical} />
          <NavLink href="/experiments" label="Experiments" icon={Beaker} />
          <NavLink href="/datasets" label="Datasets" icon={TableProperties} />
          <NavLink href="/monitoring" label="Monitoring" icon={Activity} />
          <NavLink href="/prompts" label="Prompts" icon={FileText} />
        </Section>

        {/* ── Gateway ── */}
        {canAccessOrgControl && (
          <>
            <Section id="gateway" label="Gateway">
              <NavLink href="/gateway" label="Model Gateway" icon={Network} />
              <NavLink href="/tool-registry" label="Tool Registry" icon={Wrench} />
              <NavLink href="/provider-profiles" label="Provider Profiles" icon={Database} />
            </Section>
          </>
        )}

        {/* ── Control Plane (org-admin+) ── */}
        {canAccessApiKeys && (
          <>
            <Section id="controlPlane" label="Control Plane">
              <NavLink href="/api-keys" label="API Keys" icon={Key} />
              {canAccessOrgControl && (
                <>
                  <NavLink href="/alert-rules" label="Alert Rules" icon={Bell} />
                  <NavLink href="/mcp" label="MCP" icon={Plug} />
                  <NavLink href="/integrations" label="Integrations" icon={Settings2} />
                  <NavLink href="/data-capture" label="Data Capture" icon={Shield} />
                  <NavLink href="/otlp" label="OTLP" icon={Radio} />
                </>
              )}
            </Section>
          </>
        )}

        {/* ── Finance ── */}
        {canAccessFinance && (
          <>
            <Section id="finance" label="Finance">
              <NavLink href="/budgets" label="Budgets" icon={Wallet} />
              <NavLink href="/outcomes" label="Outcomes & ROI" icon={TrendingUp} />
            </Section>
          </>
        )}

        {/* ── Governance ── */}
        {isWorkspaceAdmin && (
          <Section id="governance" label="Governance">
            <NavLink href="/approvals" label="Approvals" icon={ShieldCheck} />
            <NavLink href="/audit" label="Audit Log" icon={ScrollText} />
          </Section>
        )}
      </nav>

      {/* Bottom section — org/user/workspace management + settings */}
      <div className="mt-4 pt-4 border-t border-white/[0.05]">
        <Section id="administration" label="Administration">
          {isPlatformAdmin && <NavLink href="/organizations" label="Organizations" icon={Landmark} />}
          {canAccessOrgControl && (
            <>
              <NavLink href="/organization" label="Org Profile" icon={Building2} />
              <NavLink href="/users" label="Users" icon={Users} />
              <NavLink href="/workspace" label="Workspace" icon={LayoutGrid} />
            </>
          )}
          {canAccessSettings && <NavLink href="/settings" label="Settings" icon={Settings} />}
        </Section>
      </div>
    </aside>
  )
}
