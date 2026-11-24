export { default } from 'next-auth/middleware'

// Public routes: landing, login, first-run setup, email verification, password reset,
// SSO callbacks, API routes (the BFF under /api/rl checks the session cookie itself) and
// static assets. Everything else requires a NextAuth session.
export const config = {
  matcher: [
    '/((?!$|login|setup|verify-email|forgot-password|reset-password|auth/oidc|auth/oauth2|api|_next/static|_next/image|favicon.ico).*)',
  ],
}
