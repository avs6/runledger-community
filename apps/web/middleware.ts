export { default } from 'next-auth/middleware'

// Public routes: landing, login, email verification, password reset, SSO callbacks,
// API routes and static assets. Everything else requires a NextAuth session.
export const config = {
  matcher: [
    '/((?!$|login|verify-email|forgot-password|reset-password|auth/oidc|auth/oauth2|api|_next/static|_next/image|favicon.ico).*)',
  ],
}
