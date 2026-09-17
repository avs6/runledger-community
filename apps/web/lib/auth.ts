import type { AuthOptions } from 'next-auth'
import CredentialsProvider from 'next-auth/providers/credentials'

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
  }
}

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

          if (!res.ok) return null
          return buildUserFromApiResponse(await res.json())
        } catch {
          return null
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

          if (!res.ok) return null
          return buildUserFromApiResponse(await res.json())
        } catch {
          return null
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

          if (!res.ok) return null
          return buildUserFromApiResponse(await res.json())
        } catch {
          return null
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

          if (!res.ok) return null
          return buildUserFromApiResponse(await res.json())
        } catch {
          return null
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
      }
      // Support session update() for workspace switching
      if (trigger === 'update' && session) {
        const s = session as Record<string, unknown>
        if (s.apiKey) token.apiKey = s.apiKey as string
        if (s.workspaceId) token.workspaceId = s.workspaceId as string
        if (s.workspaceName) token.workspaceName = s.workspaceName as string
        if (s.tenantId) token.tenantId = s.tenantId as string
        if (s.tenantName !== undefined) token.tenantName = (s.tenantName as string) ?? ''
        if (s.workspaceRole !== undefined) token.workspaceRole = s.workspaceRole as string | null
        if (s.tenantRole !== undefined) token.tenantRole = s.tenantRole as string | null
        if (s.workspaceIds) token.workspaceIds = s.workspaceIds as string[]
      }
      return token
    },
    async session({ session, token }) {
      session.apiKey = token.apiKey as string
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
      return session
    },
  },
  pages: {
    signIn: '/login',
  },
  session: {
    strategy: 'jwt',
    maxAge: 30 * 24 * 60 * 60,
  },
}

declare module 'next-auth' {
  interface Session {
    apiKey: string
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
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    apiKey?: string
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
  }
}
