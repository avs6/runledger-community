'use client'

import { useEffect, useState, type ReactNode } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  Activity,
  BarChart2,
  Beaker,
  Bell,
  Building2,
  ChevronDown,
  Database,
  FileText,
  FlaskConical,
  Key,
  Landmark,
  LayoutDashboard,
  LayoutGrid,
  LayoutList,
  MessageSquare,
  Network,
  Plug,
  Radio,
  Route,
  ScrollText,
  Settings,
  Settings2,
  Shield,
  ShieldCheck,
  TableProperties,
  TrendingUp,
  Users,
  Wallet,
  Wrench,
} from 'lucide-react'
import RunLedgerLogo from '@/components/brand/RunLedgerLogo'
import { useRole } from '@/components/rbac/useRole'

const STORAGE_KEY = 'runledger.sidebar.sections'

const defaultSections = {
  workspace: true,
  improve: true,
  controlPlane: true,
  finance: true,
  governance: false,
  administration: true,
} as const

type SectionKey = keyof typeof defaultSections

const workspaceNav = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/request-flow', label: 'Request Flow', icon: Route },
  { href: '/runs', label: 'Runs', icon: LayoutList },
  { href: '/sessions', label: 'Sessions', icon: MessageSquare },
  { href: '/analytics', label: 'Analytics', icon: BarChart2 },
  { href: '/monitoring', label: 'Monitoring', icon: Activity },
] as const

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

  function NavLink({ href, label, icon: Icon, badge }: { href: string; label: string; icon: React.ElementType; badge?: string }) {
    const active = isActive(href)
    return (
      <Link
        href={href}
        className={`group relative flex items-center gap-2.5 rounded-xl px-2.5 py-2 text-sm font-medium transition-all duration-150 ${
          active
            ? 'bg-teal-500/10 text-teal-900 shadow-sm dark:bg-teal-400/10 dark:text-teal-50'
            : 'text-slate-500 hover:bg-slate-100 hover:text-slate-950 dark:text-slate-400 dark:hover:bg-white/[0.045] dark:hover:text-slate-100'
        }`}
      >
        {active && (
          <span className="absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-full bg-teal-400" />
        )}
        <Icon className={`h-4 w-4 shrink-0 ${active ? 'text-teal-600 dark:text-teal-300' : 'text-slate-500 group-hover:text-slate-700 dark:group-hover:text-slate-300'}`} />
        <span className="truncate">{label}</span>
        {badge && (
          <span className="ml-auto rounded-full bg-teal-500/15 px-1.5 py-0.5 text-[9px] font-bold text-teal-700 dark:text-teal-300">
            {badge}
          </span>
        )}
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
          className="mb-1 flex w-full items-center justify-between rounded-lg px-2.5 py-1 text-[9px] font-bold uppercase tracking-[0.2em] text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700 dark:text-slate-600 dark:hover:bg-white/[0.045] dark:hover:text-slate-400"
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
    <aside className="flex h-full w-60 flex-col border-r border-slate-200/80 bg-white/90 px-3 py-4 backdrop-blur-xl dark:border-white/[0.05] dark:bg-[#07111F]/95">
      <div className="mb-5 px-2">
        <RunLedgerLogo markSize={30} />
      </div>

      <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto">
        <Section id="workspace" label="Workspace">
          {workspaceNav.map(({ href, label, icon }) => (
            <NavLink key={href} href={href} label={label} icon={icon} />
          ))}
          {(isOrgAdmin || isPlatformAdmin) && (
            <NavLink href="/organization/dashboard" label="Global Dashboard" icon={LayoutGrid} badge="ORG" />
          )}
        </Section>

        <Section id="improve" label="Improve">
          <NavLink href="/prompts" label="Prompts" icon={FileText} />
          <NavLink href="/evaluation" label="Evaluations" icon={FlaskConical} />
          <NavLink href="/experiments" label="Experiments" icon={Beaker} />
          <NavLink href="/datasets" label="Datasets" icon={TableProperties} />
        </Section>

        {canAccessApiKeys && (
          <Section id="controlPlane" label="Control Plane">
            {canAccessOrgControl && (
              <>
                <NavLink href="/gateway" label="Model Gateway" icon={Network} />
                <NavLink href="/provider-profiles" label="Provider Profiles" icon={Database} />
              </>
            )}
            <NavLink href="/api-keys" label="API Keys" icon={Key} />
            {canAccessOrgControl && (
              <>
                <NavLink href="/integrations" label="Integrations" icon={Settings2} />
                <NavLink href="/mcp" label="MCP Servers" icon={Plug} />
                <NavLink href="/data-capture" label="Data Capture" icon={Shield} />
                <NavLink href="/otlp" label="OTLP Ingest" icon={Radio} />
                <NavLink href="/alert-rules" label="Alert Rules" icon={Bell} />
                <NavLink href="/tool-registry" label="Tool Registry" icon={Wrench} />
              </>
            )}
          </Section>
        )}

        {canAccessFinance && (
          <Section id="finance" label="Finance">
            <NavLink href="/budgets" label="Budgets" icon={Wallet} />
            <NavLink href="/outcomes" label="Outcomes & ROI" icon={TrendingUp} />
          </Section>
        )}

        {isWorkspaceAdmin && (
          <Section id="governance" label="Governance">
            <NavLink href="/approvals" label="Approvals" icon={ShieldCheck} />
            <NavLink href="/audit" label="Audit Log" icon={ScrollText} />
          </Section>
        )}
      </nav>

      <div className="mt-4 border-t border-slate-200/70 pt-4 dark:border-white/[0.05]">
        <Section id="administration" label="Admin">
          {isPlatformAdmin && <NavLink href="/organizations" label="Organizations" icon={Landmark} />}
          {canAccessOrgControl && (
            <>
              <NavLink href="/organization" label="Organization Profile" icon={Building2} />
              <NavLink href="/users" label="Users" icon={Users} />
              <NavLink href="/workspace" label="Workspaces" icon={LayoutGrid} />
            </>
          )}
          {canAccessSettings && <NavLink href="/settings" label="Platform Settings" icon={Settings} />}
        </Section>
      </div>
    </aside>
  )
}
