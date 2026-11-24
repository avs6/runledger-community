import type { AuthOptions } from 'next-auth'
import type { JWT } from 'next-auth/jwt'
import CredentialsProvider from 'next-auth/providers/credentials'
import { BFF_SESSION_KEY } from '@/lib/api/client'
// Registers the server-side session-key resolver used by apiFetch in server components.
import '@/lib/server-session'

// BFF (review P-06): the workspace session key is stored only in the encrypted,
// httpOnly NextAuth JWT cookie. The session object (what /api/auth/session returns and
// what server pages hand to client components) carries BFF_SESSION_KEY instead, browser
// calls go through /api/rl/*, and server code resolves the real key from the cookie.

const API_URL = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8201'

function buildUserFromApiResponse(data: Record<string, unknown>) {
  return {
    id: data.user_id as string,
    email: data.email as string,
    name: (data.full_name as string) || (data.email as string),
    apiKey: data.api_key as string,
    workspaceId: data.workspace_id as string,
    workspaceName: data.workspace_name as string,
    tenantId: data.tenant_id as string,
    tenantName: (data.tenant_name as string) || '',
    userId: data.user_id as string,
    fullName: data.full_name as string | null,
    isPlatformAdmin: (data.is_platform_admin as boolean) ?? false,
    tenantRole: (data.tenant_role as string | null) ?? null,
    workspaceRole: (data.workspace_role as string | null) ?? null,
    workspaceIds: (data.workspace_ids as string[]) ?? [],
    mustChangePassword: (data.must_change_password as boolean) ?? false,
  }
}

/** Turn a failed auth response into an Error whose message NextAuth hands back to
 *  signIn() as `result.error`, so the login page can show the real reason
 *  (unverified email, too many attempts, no workspace access, …). */
async function authError(res: Response): Promise<Error> {
  try {
    const body = await res.json()
    if (typeof body?.detail === 'string') return new Error(body.detail)
  } catch {
    /* fall through */
  }
  if (res.status === 429) return new Error('Too many failed sign-in attempts. Try again later.')
  return new Error('Invalid email or password')
}

/** Server-side session refresh: roles and workspace are always re-read from the API,
 *  never taken from client-supplied update() payloads. */
async function fetchSessionInfo(apiKey: string): Promise<Record<string, unknown> | null> {
  try {
    const res = await fetch(`${API_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${apiKey}` },
      cache: 'no-store',
    })
    if (!res.ok) return null
    return (await res.json()) as Record<string, unknown>
  } catch {
    return null
  }
}

function applySessionInfo(token: JWT, info: Record<string, unknown>) {
  token.workspaceId = info.workspace_id as string
  token.workspaceName = info.workspace_name as string
  token.tenantId = info.tenant_id as string
  token.tenantName = (info.tenant_name as string) ?? ''
  token.userId = info.user_id as string
  token.fullName = (info.full_name as string | null) ?? null
  token.isPlatformAdmin = (info.is_platform_admin as boolean) ?? false
  token.tenantRole = (info.tenant_role as string | null) ?? null
  token.workspaceRole = (info.workspace_role as string | null) ?? null
  token.workspaceIds = (info.workspace_ids as string[]) ?? []
  token.mustChangePassword = (info.must_change_password as boolean) ?? false
}

/** POST /auth/switch-workspace with the current key; the API revokes the old key. */
async function switchWorkspace(apiKey: string, workspaceId: string): Promise<{ apiKey: string } | { error: string }> {
  try {
    const res = await fetch(`${API_URL}/auth/switch-workspace`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ workspace_id: workspaceId }),
      cache: 'no-store',
    })
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      if (res.status === 401) return { error: 'session_expired' }
      return { error: typeof body?.detail === 'string' ? body.detail : 'Could not switch workspace' }
    }
    const data = (await res.json()) as { api_key?: string }
    return data.api_key ? { apiKey: data.api_key } : { error: 'Could not switch workspace' }
  } catch {
    return { error: 'Could not switch workspace' }
  }
}

const SESSION_MAX_AGE_SECONDS = 7 * 24 * 60 * 60

export const authOptions: AuthOptions = {
  providers: [
    CredentialsProvider({
      id: 'credentials',
      name: 'credentials',
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
        workspaceId: { label: 'Workspace ID', type: 'text' },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null

        try {
          const res = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              email: credentials.email,
              password: credentials.password,
              workspace_id: credentials.workspaceId || null,
            }),
          })

          if (!res.ok) throw await authError(res)
          return buildUserFromApiResponse(await res.json())
        } catch (err) {
          if (err instanceof Error) throw err
          throw new Error('Sign-in service unavailable')
        }
      },
    }),
    CredentialsProvider({
      id: 'oidc-callback',
      name: 'OIDC',
      credentials: {
        code: { label: 'Authorization Code', type: 'text' },
        state: { label: 'State', type: 'text' },
        provider_id: { label: 'Provider ID', type: 'text' },
      },
      async authorize(credentials) {
        if (!credentials?.code || !credentials?.state || !credentials?.provider_id) return null

        try {
          const res = await fetch(`${API_URL}/auth/oidc/callback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              code: credentials.code,
              state: credentials.state,
              provider_id: credentials.provider_id,
            }),
          })

          if (!res.ok) throw await authError(res)
          return buildUserFromApiResponse(await res.json())
        } catch (err) {
          if (err instanceof Error) throw err
          throw new Error('Sign-in service unavailable')
        }
      },
    }),
    CredentialsProvider({
      id: 'oauth2-callback',
      name: 'OAuth2',
      credentials: {
        code: { label: 'Authorization Code', type: 'text' },
        state: { label: 'State', type: 'text' },
        provider_id: { label: 'Provider ID', type: 'text' },
      },
      async authorize(credentials) {
        if (!credentials?.code || !credentials?.state || !credentials?.provider_id) return null

        try {
          const res = await fetch(`${API_URL}/auth/oauth2/callback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              code: credentials.code,
              state: credentials.state,
              provider_id: credentials.provider_id,
            }),
          })

          if (!res.ok) throw await authError(res)
          return buildUserFromApiResponse(await res.json())
        } catch (err) {
          if (err instanceof Error) throw err
          throw new Error('Sign-in service unavailable')
        }
      },
    }),
    CredentialsProvider({
      id: 'ldap-login',
      name: 'LDAP',
      credentials: {
        username: { label: 'Username', type: 'text' },
        password: { label: 'Password', type: 'password' },
        provider_id: { label: 'Provider ID', type: 'text' },
      },
      async authorize(credentials) {
        if (!credentials?.username || !credentials?.password || !credentials?.provider_id) return null

        try {
          const res = await fetch(`${API_URL}/auth/ldap/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              username: credentials.username,
              password: credentials.password,
              provider_id: credentials.provider_id,
            }),
          })

          if (!res.ok) throw await authError(res)
          return buildUserFromApiResponse(await res.json())
        } catch (err) {
          if (err instanceof Error) throw err
          throw new Error('Sign-in service unavailable')
        }
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user, trigger, session }) {
      if (user) {
        const u = user as unknown as Record<string, unknown>
        token.apiKey = u.apiKey as string
        token.workspaceId = u.workspaceId as string
        token.workspaceName = u.workspaceName as string
        token.tenantId = u.tenantId as string
        token.tenantName = (u.tenantName as string) ?? ''
        token.userId = u.userId as string
        token.fullName = u.fullName as string | null
        token.isPlatformAdmin = u.isPlatformAdmin as boolean
        token.tenantRole = u.tenantRole as string | null
        token.workspaceRole = u.workspaceRole as string | null
        token.workspaceIds = u.workspaceIds as string[]
        token.mustChangePassword = (u.mustChangePassword as boolean) ?? false
      }
      // session update(), driven by the client:
      //   { switchWorkspaceId } → switch workspace here, server-side, with the current key;
      //                           the new key never leaves the server.
      //   { refresh: true }     → re-read roles after a password change or invite accept.
      // Roles and workspace are always re-read from GET /auth/me, never taken from the client.
      if (trigger === 'update' && session) {
        const s = session as Record<string, unknown>
        token.switchError = null
        if (typeof s.switchWorkspaceId === 'string' && token.apiKey) {
          const switched = await switchWorkspace(token.apiKey, s.switchWorkspaceId)
          if ('apiKey' in switched) token.apiKey = switched.apiKey
          else token.switchError = switched.error
        }
        if (token.apiKey && (s.switchWorkspaceId || s.refresh)) {
          const info = await fetchSessionInfo(token.apiKey)
          if (info) applySessionInfo(token, info)
        }
      }
      return token
    },
    async session({ session, token }) {
      // Never the real key: the browser only ever sees the placeholder.
      session.apiKey = token.apiKey ? BFF_SESSION_KEY : ''
      session.switchError = (token.switchError as string | null | undefined) ?? null
      session.workspaceId = token.workspaceId as string
      session.workspaceName = token.workspaceName as string
      session.tenantId = token.tenantId as string
      session.tenantName = (token.tenantName as string) ?? ''
      session.userId = token.userId as string
      session.fullName = (token.fullName as string | null) ?? null
      session.isPlatformAdmin = (token.isPlatformAdmin as boolean) ?? false
      session.tenantRole = (token.tenantRole as string | null) ?? null
      session.workspaceRole = (token.workspaceRole as string | null) ?? null
      session.workspaceIds = (token.workspaceIds as string[]) ?? []
      session.mustChangePassword = (token.mustChangePassword as boolean) ?? false
      return session
    },
  },
  events: {
    // Server logout revokes the session key, even if the browser never calls the API
    // itself (review P-06). Best effort: sign-out completes locally either way.
    async signOut({ token }) {
      const key = (token as JWT | null)?.apiKey
      if (!key) return
      try {
        await fetch(`${API_URL}/auth/logout`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${key}` },
          cache: 'no-store',
        })
      } catch {
        /* the daily purge job removes it after expiry */
      }
    },
  },
  pages: {
    signIn: '/login',
  },
  session: {
    strategy: 'jwt',
    // Matches the API's SESSION_TTL_DAYS (dashboard session keys expire with it).
    maxAge: SESSION_MAX_AGE_SECONDS,
  },
}

declare module 'next-auth' {
  interface Session {
    /** Always BFF_SESSION_KEY (or '' when signed out) — never the real session key. */
    apiKey: string
    /** Set when the last workspace switch failed ('session_expired' or a message). */
    switchError: string | null
    workspaceId: string
    workspaceName: string
    tenantId: string
    tenantName: string
    userId: string
    fullName: string | null
    isPlatformAdmin: boolean
    tenantRole: string | null
    workspaceRole: string | null
    workspaceIds: string[]
    mustChangePassword: boolean
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    apiKey?: string
    switchError?: string | null
    workspaceId?: string
    workspaceName?: string
    tenantId?: string
    tenantName?: string
    userId?: string
    fullName?: string | null
    isPlatformAdmin?: boolean
    tenantRole?: string | null
    workspaceRole?: string | null
    workspaceIds?: string[]
    mustChangePassword?: boolean
  }
}
