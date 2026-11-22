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

// Security headers for every dashboard page (review P-16).
const SECURITY_HEADERS = [
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'X-Frame-Options', value: 'DENY' },
  { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
  { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=(), payment=()' },
  { key: 'Cross-Origin-Opener-Policy', value: 'same-origin' },
  {
    key: 'Content-Security-Policy',
    value: [
      "default-src 'self'",
      "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
      "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
      "font-src 'self' data: https://fonts.gstatic.com",
      "img-src 'self' data: blob: https:",
      "connect-src 'self' http: https: ws: wss:",
      "frame-ancestors 'none'",
      "base-uri 'self'",
      "form-action 'self'",
    ].join('; '),
  },
]

const nextConfig = {
  output: 'standalone',
  async headers() {
    return [{ source: '/:path*', headers: SECURITY_HEADERS }]
  },
  async redirects() {
    return Object.entries(LEGACY_ROUTES).map(([source, destination]) => ({
      source,
      destination,
      permanent: true,
    }))
  },
}

export default nextConfig
