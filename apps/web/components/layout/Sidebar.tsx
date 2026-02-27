import Link from 'next/link'
import { LayoutList, BarChart2, ShieldAlert } from 'lucide-react'

const nav = [
  { href: '/runs', label: 'Runs', icon: LayoutList },
  { href: '/analytics', label: 'Analytics', icon: BarChart2 },
  { href: '/budgets', label: 'Budgets', icon: ShieldAlert },
]

export default function Sidebar() {
  return (
    <aside className="flex h-full w-56 flex-col border-r border-gray-200 bg-white px-3 py-4">
      <div className="mb-6 px-2">
        <span className="text-lg font-semibold tracking-tight">RunLedger</span>
      </div>
      <nav className="flex flex-col gap-1">
        {nav.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className="flex items-center gap-2.5 rounded-md px-2 py-2 text-sm text-gray-700 hover:bg-gray-100"
          >
            <Icon className="h-4 w-4 text-gray-500" />
            {label}
          </Link>
        ))}
      </nav>
    </aside>
  )
}
