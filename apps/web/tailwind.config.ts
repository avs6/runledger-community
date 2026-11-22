import type { Config } from "tailwindcss";

const config: Config = {
    darkMode: ["class"],
    content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
  	extend: {
  		fontFamily: {
  			sans: ['var(--font-sans)', '"Segoe UI"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
  			display: ['var(--font-display)', 'ui-sans-serif', 'system-ui', 'sans-serif'],
  		},
  		borderRadius: {
  			lg: 'var(--radius)',
  			md: 'calc(var(--radius) - 2px)',
  			sm: 'calc(var(--radius) - 4px)'
  		},
  		colors: {
  			background: 'hsl(var(--background))',
  			foreground: 'hsl(var(--foreground))',
  			card: {
  				DEFAULT: 'hsl(var(--card))',
  				foreground: 'hsl(var(--card-foreground))'
  			},
  			popover: {
  				DEFAULT: 'hsl(var(--popover))',
  				foreground: 'hsl(var(--popover-foreground))'
  			},
  			primary: {
  				DEFAULT: 'hsl(var(--primary))',
  				foreground: 'hsl(var(--primary-foreground))'
  			},
  			secondary: {
  				DEFAULT: 'hsl(var(--secondary))',
  				foreground: 'hsl(var(--secondary-foreground))'
  			},
  			muted: {
  				DEFAULT: 'hsl(var(--muted))',
  				foreground: 'hsl(var(--muted-foreground))'
  			},
  			accent: {
  				DEFAULT: 'hsl(var(--accent))',
  				foreground: 'hsl(var(--accent-foreground))'
  			},
  			destructive: {
  				DEFAULT: 'hsl(var(--destructive))',
  				foreground: 'hsl(var(--destructive-foreground))'
  			},
  			border: 'hsl(var(--border))',
  			input: 'hsl(var(--input))',
  			ring: 'hsl(var(--ring))',
  			// Semantic tokens backed by the CSS variables in app/globals.css (light + dark).
  			// Use these instead of raw hex or ad-hoc palette colours (review Wave 0.4).
  			status: {
  				success: 'hsl(var(--status-success))',
  				warning: 'hsl(var(--status-warning))',
  				error: 'hsl(var(--status-error))',
  				info: 'hsl(var(--status-info))',
  				neutral: 'hsl(var(--status-neutral))'
  			},
  			severity: {
  				low: 'hsl(var(--severity-low))',
  				medium: 'hsl(var(--severity-medium))',
  				high: 'hsl(var(--severity-high))',
  				critical: 'hsl(var(--severity-critical))'
  			},
  			scope: {
  				platform: 'hsl(var(--scope-platform))',
  				organization: 'hsl(var(--scope-organization))',
  				workspace: 'hsl(var(--scope-workspace))',
  				'access-group': 'hsl(var(--scope-access-group))',
  				'api-key': 'hsl(var(--scope-api-key))'
  			},
  			runtime: {
  				active: 'hsl(var(--runtime-active))',
  				degraded: 'hsl(var(--runtime-degraded))',
  				down: 'hsl(var(--runtime-down))',
  				maintenance: 'hsl(var(--runtime-maintenance))'
  			},
  			chart: {
  				'1': 'hsl(var(--chart-1))',
  				'2': 'hsl(var(--chart-2))',
  				'3': 'hsl(var(--chart-3))',
  				'4': 'hsl(var(--chart-4))',
  				'5': 'hsl(var(--chart-5))'
  			}
  		}
  	}
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
