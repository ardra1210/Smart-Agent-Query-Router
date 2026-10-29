const TONES = {
  bad: 'bg-red-50 text-red-700 ring-red-200 dark:bg-red-950/60 dark:text-red-300 dark:ring-red-900',
  warn: 'bg-amber-50 text-amber-700 ring-amber-200 dark:bg-amber-950/60 dark:text-amber-300 dark:ring-amber-900',
  good: 'bg-emerald-50 text-emerald-700 ring-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:ring-emerald-900',
  neutral: 'bg-zinc-100 text-zinc-600 ring-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:ring-zinc-700',
}

const RULES: [RegExp, keyof typeof TONES][] = [
  [/fail|blocked|urgent/i, 'bad'],
  [/pending|progress|risk|triage/i, 'warn'],
  [/pass|success|done|merged|on track|open/i, 'good'],
]

export function StatusBadge({ status }: { status: string }) {
  const tone = RULES.find(([pattern]) => pattern.test(status))?.[1] ?? 'neutral'
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${TONES[tone]}`}
    >
      {status.replace(/_/g, ' ')}
    </span>
  )
}
