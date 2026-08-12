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
  Bot,
  Building2,
  ChevronDown,
  Cpu,
  Database,
  FolderLock,
  FileText,
  FlaskConical,
  GitBranch,
  GraduationCap,
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
  ShieldAlert,
  ShieldCheck,
  TableProperties,
  TrendingUp,
  Trophy,
  Users,
  Wallet,
  FileCheck,
  Play,
  Wrench,
  Gauge,
  Layers,
  FileSpreadsheet,
  Server,
  Puzzle,
  Store,
  FolderKanban,
  UsersRound,
} from 'lucide-react'
import RunLedgerLogo from '@/components/brand/RunLedgerLogo'
import { useRole } from '@/components/rbac/useRole'

const STORAGE_KEY = 'runledger.sidebar.sections'

const defaultSections = {
  observe: true,
  build: true,
  gateway: true,
  governance: true,
  finance: true,
  organization: true,
  platform: true,
} as const

type SectionKey = keyof typeof defaultSections

const observeNav = [
  { href: '/dashboard', label: 'Workspace Dashboard', icon: LayoutDashboard },
  { href: '/runs', label: 'Runs', icon: LayoutList },
  { href: '/sessions', label: 'Sessions', icon: MessageSquare },
  { href: '/request-flow', label: 'Request Flow', icon: Route },
  { href: '/request-explorer', label: 'Request Explorer', icon: Search },
  { href: '/analytics', label: 'Analytics', icon: BarChart2 },
  { href: '/engineering', label: 'Engineering', icon: Wrench },
  { href: '/model-usage', label: 'Model Usage', icon: Cpu },
  { href: '/monitoring', label: 'Monitoring', icon: Activity },
  { href: '/evaluations', label: 'Quality Scores', icon: GraduationCap },
  { href: '/outcomes', label: 'Outcomes & ROI', icon: TrendingUp },
] as const

const buildNav = [
  { href: '/agents', label: 'Agents', icon: Bot },
  { href: '/workflows', label: 'Workflows', icon: GitBranch },
  { href: '/playground', label: 'Playground', icon: Play },
  { href: '/prompts', label: 'Prompts', icon: FileText },
  { href: '/evaluation', label: 'Evaluations Studio', icon: FlaskConical },
  { href: '/datasets', label: 'Datasets', icon: TableProperties },
  { href: '/experiments', label: 'Experiments', icon: Beaker },
  { href: '/replay', label: 'Replay Lab', icon: Beaker },
  { href: '/optimization-opportunities', label: 'Optimization Opportunities', icon: Lightbulb },
  { href: '/optimization-simulator', label: 'Optimization Simulator', icon: FlaskConical },
  { href: '/model-scorecards', label: 'Model Scorecards', icon: Trophy },
  { href: '/runbooks', label: 'Runbooks', icon: BookOpen },
  { href: '/vector-stores', label: 'Vector Stores', icon: Database },
] as const

export default function Sidebar() {
  const pathname = usePathname()
  const { isPlatformAdmin, isOrgElevated, isWorkspaceAdmin, canAccessSettings } = useRole()
  const canAccessFinance = isWorkspaceAdmin || isOrgElevated || isPlatformAdmin
  const canAccessOrgControl = isOrgElevated || isPlatformAdmin
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
    <aside className="flex h-full w-60 min-h-0 flex-col overflow-hidden border-r border-slate-200 bg-[#eef3f8]/95 px-3 py-4 backdrop-blur-xl dark:border-slate-300 dark:bg-[#dbe5ef]/95">
      <div className="mb-5 shrink-0 px-2">
        <RunLedgerLogo markSize={30} />
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto pr-1">
        <nav className="flex flex-col gap-0.5">
          <Section id="observe" label="Observe">
            {observeNav.map(({ href, label, icon }) => (
              <NavLink key={href} href={href} label={label} icon={icon} />
            ))}
          </Section>

          <Section id="build" label="Build & Improve">
            {buildNav.map(({ href, label, icon }) => (
              <NavLink key={href} href={href} label={label} icon={icon} />
            ))}
          </Section>

          {canAccessApiKeys && (
            <Section id="gateway" label="Gateway & Routing">
              {canAccessOrgControl && (
                <>
                  <NavLink href="/gateway" label="Model Gateway" icon={Network} />
                  <NavLink href="/provider-profiles" label="Provider Profiles" icon={Database} />
                </>
              )}
              <NavLink href="/guardrails" label="Guardrails" icon={ShieldAlert} />
              <NavLink href="/response-cache" label="Response Cache" icon={Database} />
              <NavLink href="/rate-limits" label="Rate Limits" icon={Gauge} />
            </Section>
          )}

          {canAccessApiKeys && (
            <Section id="governance" label="Safety & Governance">
              <NavLink href="/tool-registry" label="Tool Registry" icon={Wrench} />
              <NavLink href="/search-tools" label="Search Tools" icon={Search} />
              <NavLink href="/tool-policies" label="Tool Policies" icon={FolderLock} />
              <NavLink href="/mcp" label="MCP Servers" icon={Plug} />
              <NavLink href="/data-capture" label="Data Capture" icon={Shield} />
              <NavLink href="/security" label="Security" icon={ShieldAlert} />
              {isWorkspaceAdmin && <NavLink href="/approvals" label="Approvals" icon={ShieldCheck} />}
              {isWorkspaceAdmin && <NavLink href="/audit" label="Audit Log" icon={ScrollText} />}
              {isWorkspaceAdmin && <NavLink href="/policy-dry-run" label="Policy Dry Run" icon={Shield} />}
              {isWorkspaceAdmin && <NavLink href="/governance-pack" label="Audit Pack" icon={FileCheck} />}
              <NavLink href="/alert-rules" label="Alert Rules" icon={Bell} />
              <NavLink href="/tags" label="Tags" icon={BookOpen} />
            </Section>
          )}

          {canAccessFinance && (
            <Section id="finance" label="FinOps">
              <NavLink href="/cost-savings" label="Cost & Savings" icon={PiggyBank} />
              <NavLink href="/budgets" label="Budgets" icon={Wallet} />
              <NavLink href="/billing" label="Billing" icon={FileSpreadsheet} />
              {canAccessOrgControl && <NavLink href="/chargeback" label="Chargeback" icon={Receipt} />}
            </Section>
          )}
        </nav>
      </div>

      <div className="mt-auto shrink-0 border-t border-slate-200/80 pt-2 pr-1 max-h-[50vh] overflow-y-auto dark:border-white/[0.06]">
        {(canAccessApiKeys || canAccessOrgControl) && (
          <Section id="organization" label="Organization & Access">
            {canAccessOrgControl && <NavLink href="/organization/dashboard" label="Org Dashboard" icon={LayoutDashboard} />}
            {canAccessOrgControl && <NavLink href="/organization" label="Organization" icon={Building2} />}
            {canAccessOrgControl && <NavLink href="/users" label="Users" icon={Users} />}
            {canAccessOrgControl && <NavLink href="/workspace" label="Teams / Workspaces" icon={LayoutGrid} />}
            {canAccessOrgControl && <NavLink href="/projects" label="Projects" icon={FolderKanban} />}
            {canAccessOrgControl && <NavLink href="/team-models" label="Team Models" icon={UsersRound} />}
            {canAccessOrgControl && <NavLink href="/access-groups" label="Access Groups" icon={Layers} />}
            <NavLink href="/api-keys" label="API Keys" icon={Key} />
            {canAccessOrgControl && <NavLink href="/otlp" label="OTLP Ingest" icon={Radio} />}
            {canAccessOrgControl && <NavLink href="/mcp-registry" label="MCP Registry" icon={Server} />}
            {canAccessOrgControl && <NavLink href="/ai-hub" label="AI Hub" icon={Store} />}
            <NavLink href="/onboarding" label="Getting Started" icon={Rocket} />
            {canAccessOrgControl && <NavLink href="/integrations" label="Integrations" icon={Settings2} />}
          </Section>
        )}
        {canAccessOrgControl && (
          <Section id="platform" label="Platform">
            {isPlatformAdmin && <NavLink href="/global-dashboard" label="Global Dashboard" icon={Landmark} />}
            {isPlatformAdmin && <NavLink href="/organizations" label="All Organizations" icon={Landmark} />}
            {canAccessSettings && <NavLink href="/settings" label="Settings" icon={Settings} />}
          </Section>
        )}
      </div>
    </aside>
  )
}
