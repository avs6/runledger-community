/** @type {import('next').NextConfig} */

// Old or never-built paths that earlier builds and docs linked to. Each maps to the
// page that exists now, so bookmarks and external links keep working.
const LEGACY_ROUTES = {
  '/telemetry': '/monitoring/telemetry',
  '/admin/organizations': '/organizations',
  '/admin/settings': '/settings',
  '/alerts': '/alert-rules',
  '/analytics/engineering': '/engineering',
  '/analytics/model-usage': '/model-usage',
  '/analytics/monitoring': '/monitoring',
  '/analytics/outcomes': '/outcomes',
  '/analytics/runs': '/runs',
  '/audit-log': '/audit',
  '/billing-periods': '/billing',
  '/budget-notifications': '/budgets',
  '/cache-config': '/gateway?tab=cache',
  '/governance': '/governance-pack',
  '/model-gateway': '/gateway',
  '/monitoring/sessions': '/sessions',
  '/optimization': '/optimization-opportunities',
  '/providers': '/provider-profiles',
  '/retention': '/settings?tab=retention',
  '/routes': '/gateway?tab=routes',
  '/scorecards': '/model-scorecards',
  '/tools': '/tool-registry',
  '/workspaces': '/workspace',
}

const nextConfig = {
  output: 'standalone',
  async redirects() {
    return Object.entries(LEGACY_ROUTES).map(([source, destination]) => ({
      source,
      destination,
      permanent: true,
    }))
  },
}

export default nextConfig
