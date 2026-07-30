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
      viewBox="0 0 128 128"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="runledger-blade-a" x1="43" y1="8" x2="84" y2="104" gradientUnits="userSpaceOnUse">
          <stop stopColor="#93C5FD" />
          <stop offset="0.48" stopColor="#3B82F6" />
          <stop offset="1" stopColor="#1E5A94" />
        </linearGradient>
        <linearGradient id="runledger-blade-b" x1="45" y1="10" x2="86" y2="104" gradientUnits="userSpaceOnUse">
          <stop stopColor="#BFDBFE" />
          <stop offset="0.5" stopColor="#60A5FA" />
          <stop offset="1" stopColor="#2F6FA7" />
        </linearGradient>
        <filter id="runledger-mark-shadow" x="-20%" y="-20%" width="140%" height="140%" colorInterpolationFilters="sRGB">
          <feDropShadow dx="0" dy="6" stdDeviation="7" floodColor="#1E3A5F" floodOpacity="0.18" />
        </filter>
      </defs>
      <g filter="url(#runledger-mark-shadow)">
        <g transform="translate(64 64)">
          <path d="M-7 -54C15 -52 27 -38 24 -16C13 -20 2 -19 -8 -13C-18 -30 -16 -44 -7 -54Z" fill="url(#runledger-blade-a)" transform="rotate(0)" />
          <path d="M-7 -54C15 -52 27 -38 24 -16C13 -20 2 -19 -8 -13C-18 -30 -16 -44 -7 -54Z" fill="url(#runledger-blade-b)" transform="rotate(60)" />
          <path d="M-7 -54C15 -52 27 -38 24 -16C13 -20 2 -19 -8 -13C-18 -30 -16 -44 -7 -54Z" fill="url(#runledger-blade-a)" transform="rotate(120)" />
          <path d="M-7 -54C15 -52 27 -38 24 -16C13 -20 2 -19 -8 -13C-18 -30 -16 -44 -7 -54Z" fill="url(#runledger-blade-b)" transform="rotate(180)" />
          <path d="M-7 -54C15 -52 27 -38 24 -16C13 -20 2 -19 -8 -13C-18 -30 -16 -44 -7 -54Z" fill="url(#runledger-blade-a)" transform="rotate(240)" />
          <path d="M-7 -54C15 -52 27 -38 24 -16C13 -20 2 -19 -8 -13C-18 -30 -16 -44 -7 -54Z" fill="url(#runledger-blade-b)" transform="rotate(300)" />
        </g>
        <circle cx="64" cy="64" r="24" fill="#050A12" fillOpacity="0.9" />
        <text
          x="64"
          y="76"
          textAnchor="middle"
          fill="#F8FAFC"
          fontFamily="Sora, Segoe UI, Arial, sans-serif"
          fontSize="31"
          fontWeight="800"
          letterSpacing="-2"
          transform="rotate(7 64 64)"
        >
          RL
        </text>
      </g>
    </svg>
  )
}

export default function RunLedgerLogo({
  markSize = 36,
  showWordmark = true,
  className = '',
  wordmarkClassName = 'text-sm text-slate-950 dark:text-slate-950',
  taglineClassName = 'text-blue-700 dark:text-blue-700',
}: RunLedgerLogoProps) {
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <RunLedgerMark size={markSize} />
      {showWordmark && (
        <div>
          <div className={`font-display font-bold leading-none tracking-[-0.045em] ${wordmarkClassName}`}>RunLedger</div>
          <div className={`mt-1 text-[8px] font-semibold uppercase leading-none tracking-[0.18em] ${taglineClassName}`}>
            Intelligence, Accounted.
          </div>
        </div>
      )}
    </div>
  )
}
