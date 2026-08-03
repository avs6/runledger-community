'use client'

import { useEffect, useState, type ReactNode } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  Activity,
  BarChart2,
  Beaker,
  Bell,
  BookOpen,
  Building2,
  ChevronDown,
  Cpu,
  Database,
  FileText,
  FlaskConical,
  Key,
  Landmark,
  LayoutDashboard,
  LayoutGrid,
  LayoutList,
  Lightbulb,
  MessageSquare,
  Network,
  PiggyBank,
  Plug,
  Radio,
  Receipt,
  Rocket,
  Route,
  ScrollText,
  Search,
  Settings,
  Settings2,
  Shield,
  ShieldCheck,
  TableProperties,
  TrendingUp,
  Trophy,
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
  organization: true,
  platform: true,
} as const

type SectionKey = keyof typeof defaultSections

const workspaceNav = [
  { href: '/dashboard', label: 'Workspace Dashboard', icon: LayoutDashboard },
  { href: '/request-flow', label: 'Request Flow', icon: Route },
  { href: '/request-explorer', label: 'Request Explorer', icon: Search },
  { href: '/engineering', label: 'Engineering', icon: Wrench },
  { href: '/runs', label: 'Runs', icon: LayoutList },
  { href: '/sessions', label: 'Sessions', icon: MessageSquare },
  { href: '/analytics', label: 'Analytics', icon: BarChart2 },
  { href: '/model-usage', label: 'Model Usage', icon: Cpu },
  { href: '/monitoring', label: 'Monitoring', icon: Activity },
  { href: '/runbooks', label: 'Runbooks', icon: BookOpen },
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
    if (href === '/organization') return pathname === '/organization'
    return pathname === href || pathname.startsWith(`${href}/`)
  }

  function NavLink({ href, label, icon: Icon, badge }: { href: string; label: string; icon: React.ElementType; badge?: string }) {
    const active = isActive(href)
    return (
      <Link
        href={href}
        className={`group relative flex items-center gap-2.5 rounded-xl px-2.5 py-2 text-[13px] font-medium tracking-[-0.01em] transition-all duration-150 ${
          active
            ? 'bg-blue-100 text-slate-950 shadow-sm ring-1 ring-blue-200 dark:bg-blue-200 dark:text-slate-950 dark:ring-blue-300'
            : 'text-slate-600 hover:bg-blue-50 hover:text-slate-950 dark:text-slate-600 dark:hover:bg-blue-100 dark:hover:text-slate-950'
        }`}
      >
        {active && (
          <span className="absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-full bg-blue-500" />
        )}
        <Icon className={`h-4 w-4 shrink-0 ${active ? 'text-blue-700' : 'text-slate-500 group-hover:text-slate-700 dark:group-hover:text-slate-700'}`} />
        <span className="truncate">{label}</span>
        {badge && (
          <span className="ml-auto rounded-full bg-blue-100 px-1.5 py-0.5 text-[9px] font-bold text-blue-700 dark:bg-blue-200 dark:text-blue-800">
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
          className="mb-1 flex w-full items-center justify-between rounded-lg px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.19em] text-slate-500 transition-colors hover:bg-blue-50 hover:text-slate-700 dark:text-slate-500 dark:hover:bg-blue-100 dark:hover:text-slate-700"
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
    <aside className="flex h-full w-60 flex-col border-r border-slate-200 bg-[#eef3f8]/95 px-3 py-4 backdrop-blur-xl dark:border-slate-300 dark:bg-[#dbe5ef]/95">
      <div className="mb-5 px-2">
        <RunLedgerLogo markSize={30} />
      </div>

      <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto">
        <Section id="workspace" label="Workspace">
          {workspaceNav.map(({ href, label, icon }) => (
            <NavLink key={href} href={href} label={label} icon={icon} />
          ))}
        </Section>

        <Section id="improve" label="Improve">
          <NavLink href="/optimization-opportunities" label="Optimization Opportunities" icon={Lightbulb} />
          <NavLink href="/optimization-simulator" label="Optimization Simulator" icon={FlaskConical} />
          <NavLink href="/model-scorecards" label="Model Scorecards" icon={Trophy} />
          <NavLink href="/prompts" label="Prompts" icon={FileText} />
          <NavLink href="/evaluation" label="Evaluations" icon={FlaskConical} />
          <NavLink href="/experiments" label="Experiments" icon={Beaker} />
          <NavLink href="/datasets" label="Datasets" icon={TableProperties} />
          <NavLink href="/replay" label="Replay Lab" icon={Beaker} />
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
            <NavLink href="/cost-savings" label="Cost & Savings" icon={PiggyBank} />
            <NavLink href="/budgets" label="Budgets" icon={Wallet} />
            <NavLink href="/outcomes" label="Outcomes & ROI" icon={TrendingUp} />
            <NavLink href="/chargeback" label="Chargeback" icon={Receipt} />
          </Section>
        )}

        {isWorkspaceAdmin && (
          <Section id="governance" label="Governance">
            <NavLink href="/approvals" label="Approvals" icon={ShieldCheck} />
            <NavLink href="/audit" label="Audit Log" icon={ScrollText} />
            <NavLink href="/policy-dry-run" label="Policy Dry Run" icon={Shield} />
          </Section>
        )}
      </nav>

      <div className="mt-4 border-t border-slate-200/80 pt-4 dark:border-white/[0.06]">
        {canAccessOrgControl && (
          <Section id="organization" label="Organization">
            <NavLink href="/organization/dashboard" label="Org Dashboard" icon={LayoutDashboard} />
            <NavLink href="/organization" label="Profile" icon={Building2} />
            <NavLink href="/users" label="Users" icon={Users} />
            <NavLink href="/workspace" label="Workspaces" icon={LayoutGrid} />
          </Section>
        )}
        {isPlatformAdmin && (
          <Section id="platform" label="Platform">
            <NavLink href="/global-dashboard" label="Global Dashboard" icon={Landmark} />
            <NavLink href="/organizations" label="All Organizations" icon={Landmark} />
            <NavLink href="/onboarding" label="Getting Started" icon={Rocket} />
            {canAccessSettings && <NavLink href="/settings" label="Settings" icon={Settings} />}
          </Section>
        )}
      </div>
    </aside>
  )
}
