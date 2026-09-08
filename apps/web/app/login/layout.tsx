import { ThemeProvider } from '@/components/providers/ThemeProvider'

export default function LoginLayout({ children }: { children: React.ReactNode }) {
  return <ThemeProvider>{children}</ThemeProvider>
}
