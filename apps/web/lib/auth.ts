import type { AuthOptions } from 'next-auth'
import CredentialsProvider from 'next-auth/providers/credentials'

// authorize() runs server-side only — use the internal Docker network URL when set
const API_URL = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export const authOptions: AuthOptions = {
  providers: [
    CredentialsProvider({
      name: 'credentials',
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
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
            }),
          })

          if (!res.ok) return null

          const data = await res.json()
          return {
            id: data.workspace_id,
            email: data.email,
            name: data.workspace_name,
            // Store in token — accessed via jwt callback
            apiKey: data.api_key,
            workspaceId: data.workspace_id,
            workspaceName: data.workspace_name,
          }
        } catch {
          return null
        }
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.apiKey = (user as { apiKey?: string }).apiKey
        token.workspaceId = (user as { workspaceId?: string }).workspaceId
        token.workspaceName = (user as { workspaceName?: string }).workspaceName
      }
      return token
    },
    async session({ session, token }) {
      session.apiKey = token.apiKey as string
      session.workspaceId = token.workspaceId as string
      session.workspaceName = token.workspaceName as string
      return session
    },
  },
  pages: {
    signIn: '/login',
  },
  session: {
    strategy: 'jwt',
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },
}

// Extend next-auth types
declare module 'next-auth' {
  interface Session {
    apiKey: string
    workspaceId: string
    workspaceName: string
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    apiKey?: string
    workspaceId?: string
    workspaceName?: string
  }
}
