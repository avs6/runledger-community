type RunLedgerLogoProps = {
  markSize?: number
  showWordmark?: boolean
  className?: string
  wordmarkClassName?: string
  taglineClassName?: string
}

export function RunLedgerMark({ size = 36 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="runledger-mark-bg" x1="8" y1="4" x2="58" y2="60" gradientUnits="userSpaceOnUse">
          <stop stopColor="#0F766E" />
          <stop offset="0.52" stopColor="#155E75" />
          <stop offset="1" stopColor="#111827" />
        </linearGradient>
        <linearGradient id="runledger-mark-line" x1="15" y1="45" x2="50" y2="17" gradientUnits="userSpaceOnUse">
          <stop stopColor="#A7F3D0" />
          <stop offset="1" stopColor="#67E8F9" />
        </linearGradient>
      </defs>
      <rect x="4" y="4" width="56" height="56" rx="16" fill="url(#runledger-mark-bg)" />
      <rect x="4.5" y="4.5" width="55" height="55" rx="15.5" stroke="white" strokeOpacity="0.12" />
      <path
        d="M17 42.5L28.25 32.25L37 36.5L49 22"
        stroke="url(#runledger-mark-line)"
        strokeWidth="4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M17 47V37" stroke="white" strokeOpacity="0.9" strokeWidth="4" strokeLinecap="round" />
      <path d="M29 47V28" stroke="white" strokeOpacity="0.9" strokeWidth="4" strokeLinecap="round" />
      <path d="M41 47V32" stroke="white" strokeOpacity="0.65" strokeWidth="4" strokeLinecap="round" />
      <circle cx="49" cy="22" r="3.25" fill="#CCFBF1" />
    </svg>
  )
}

export default function RunLedgerLogo({
  markSize = 36,
  showWordmark = true,
  className = '',
  wordmarkClassName = 'text-sm text-slate-950 dark:text-white',
  taglineClassName = 'text-teal-700 dark:text-teal-300',
}: RunLedgerLogoProps) {
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <RunLedgerMark size={markSize} />
      {showWordmark && (
        <div>
          <div className={`font-semibold leading-none tracking-tight ${wordmarkClassName}`}>RunLedger</div>
          <div className={`mt-1 text-[9px] font-bold uppercase leading-none tracking-[0.2em] ${taglineClassName}`}>
            AI Ops Ledger
          </div>
        </div>
      )}
    </div>
  )
}
