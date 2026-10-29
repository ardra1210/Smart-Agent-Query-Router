import type { QueryResult } from '../types'
import { agentTheme } from './agentTheme'

interface Props {
  result: QueryResult
  labels: Record<string, string>
}

function summarize({ decision }: QueryResult, labels: Record<string, string>): string {
  const agent = decision.agent ? (labels[decision.agent] ?? decision.agent) : ''
  if (decision.escalated) {
    const prefix = 'Keyword routing was unsure, so the question was escalated to Claude'
    if (decision.status === 'routed') return `${prefix}, which picked ${agent}`
    if (decision.status === 'clarify') return `${prefix}, which also found it ambiguous`
    return `${prefix}, which found no agent that can answer it`
  }
  if (decision.status === 'routed')
    return `Routed to ${agent} with ${Math.round(decision.confidence * 100)}% of the keyword evidence`
  if (decision.status === 'clarify') return 'Scores were too close to call, so the router asked instead of guessing'
  return 'No agent had enough evidence to answer, so the router declined'
}

export function RoutingTrace({ result, labels }: Props) {
  const { decision, response, latency_ms } = result
  const entries = Object.entries(decision.scores).sort((a, b) => b[1] - a[1])
  const maxScore = Math.max(1, ...entries.map(([, score]) => score))
  const summary = summarize(result, labels)

  return (
    <details className="group mt-3 rounded-lg border border-zinc-200 bg-zinc-50/60 text-sm dark:border-zinc-800 dark:bg-zinc-900/40">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-2 text-zinc-500 select-none hover:text-zinc-800 dark:text-zinc-400 dark:hover:text-zinc-200">
        <svg className="size-3.5 transition-transform group-open:rotate-90" viewBox="0 0 16 16" fill="currentColor">
          <path d="M6 3.5 10.5 8 6 12.5" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" />
        </svg>
        <span className="font-medium">Why this answer?</span>
        <span className="ml-auto font-mono text-xs">{latency_ms.toFixed(2)} ms</span>
      </summary>

      <div className="space-y-4 border-t border-zinc-200 px-3 py-3 dark:border-zinc-800">
        <p className="text-zinc-700 dark:text-zinc-300">{summary}.</p>
        {decision.reason && (
          <blockquote className="border-l-2 border-indigo-300 pl-3 text-zinc-600 italic dark:border-indigo-700 dark:text-zinc-400">
            {decision.reason}
          </blockquote>
        )}

        <div className="space-y-2">
          <h4 className="text-xs font-semibold tracking-wide text-zinc-500 uppercase">Agent scores</h4>
          {entries.map(([name, score]) => {
            const signals = decision.signals[name] ?? []
            const chosen = name === decision.agent
            return (
              <div key={name}>
                <div className="flex items-center justify-between text-xs">
                  <span className={chosen ? 'font-semibold' : 'text-zinc-500 dark:text-zinc-400'}>
                    {labels[name] ?? name}
                    {chosen && <span className="ml-1.5 text-emerald-600 dark:text-emerald-400">✓ chosen</span>}
                  </span>
                  <span className="font-mono text-zinc-500">{score.toFixed(1)}</span>
                </div>
                <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-800">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${agentTheme(name).bar} ${chosen || decision.status !== 'routed' ? '' : 'opacity-40'}`}
                    style={{ width: `${(score / maxScore) * 100}%` }}
                  />
                </div>
                {signals.length > 0 && (
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    {signals.map((signal) => (
                      <code
                        key={signal}
                        className="rounded bg-white px-1.5 py-0.5 text-xs text-zinc-600 ring-1 ring-zinc-200 dark:bg-zinc-900 dark:text-zinc-300 dark:ring-zinc-700"
                      >
                        {signal}
                      </code>
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </div>

        <dl className="grid grid-cols-3 gap-2 text-xs">
          <Fact label="Strategy" value={decision.escalated ? `keyword → ${decision.strategy}` : decision.strategy} />
          <Fact label="Decision" value={decision.status} />
          <Fact label="Capability" value={response?.capability.replace(/_/g, ' ') ?? '—'} />
        </dl>
      </div>
    </details>
  )
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-white px-2 py-1.5 ring-1 ring-zinc-200 dark:bg-zinc-900 dark:ring-zinc-800">
      <dt className="text-zinc-500">{label}</dt>
      <dd className="mt-0.5 font-medium text-zinc-800 dark:text-zinc-200">{value}</dd>
    </div>
  )
}
