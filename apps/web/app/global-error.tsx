'use client'

/** Last-resort boundary when the root layout itself fails. */
export default function GlobalError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: 'system-ui, sans-serif', padding: 40, textAlign: 'center' }}>
        <h1 style={{ fontSize: 18 }}>RunLedger couldn&apos;t load</h1>
        <p style={{ color: '#64748b', fontSize: 14 }}>An unexpected error stopped the app. Try reloading.</p>
        <button type="button" onClick={reset} style={{ marginTop: 16, padding: '8px 16px', borderRadius: 8 }}>
          Reload
        </button>
      </body>
    </html>
  )
}
