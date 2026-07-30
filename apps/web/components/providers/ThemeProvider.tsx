'use client'

import { ThemeProvider as NextThemesProvider } from 'next-themes'

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  return (
    <NextThemesProvider attribute="class" defaultTheme="light" storageKey="runledger-theme-v3" enableSystem={false}>
      {children}
    </NextThemesProvider>
  )
}
