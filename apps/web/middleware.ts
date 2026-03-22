export { default } from 'next-auth/middleware'

export const config = {
  matcher: ['/((?!login|signup|verify-email|api|_next/static|_next/image|favicon.ico).*)'],
}
