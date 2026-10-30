import type { QueryResult } from '../types'
import { agentTheme } from './agentTheme'
import { RoutingTrace } from './RoutingTrace'
import { StatusBadge } from './StatusBadge'

interface Props {
  result: QueryResult
  labels: Record<string, string>
  onClarify: (query: string) => void
}

export function AssistantMessage({ result, labels, onClarify }: Props) {
  const { decision } = result
  const agent = decision.agent
  const theme = agent ? agentTheme(agent) : null
  const multi = decision.status === 'multi'

  return (
    <div className="flex gap-3">
      <div
        className={`flex size-8 shrink-0 items-center justify-center rounded-lg text-xs font-bold ${
          theme ? theme.avatar : 'bg-zinc-200 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400'
        }`}
      >
        {theme ? theme.initials : multi ? '⇉' : '?'}
      </div>

      <div className="min-w-0 flex-1">
        <AgentHeading result={result} labels={labels} />
        <div className="rounded-2xl rounded-tl-sm border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
          {multi ? (
            <>
              <p>{result.message}</p>
              <div className="mt-3 space-y-4">
                {result.parts.map((part) => (
                  <section key={part.query} className="relative pl-4">
                    <span
                      className={`absolute inset-y-0 left-0 w-0.5 rounded-full ${part.decision.agent ? agentTheme(part.decision.agent).bar : 'bg-zinc-300'}`}
                    />
                    <p className="mb-1 text-xs text-zinc-500">“{part.query}”</p>
                    <AgentHeading result={part} labels={labels} />
                    <AnswerBody result={part} labels={labels} onClarify={onClarify} />
                  </section>
                ))}
              </div>
            </>
          ) : (
            <AnswerBody result={result} labels={labels} onClarify={onClarify} />
          )}
        </div>
      </div>
    </div>
  )
}

function AgentHeading({ result, labels }: Pick<Props, 'result' | 'labels'>) {
  const { decision, response } = result
  const agent = decision.agent
  const name = agent ? (labels[agent] ?? agent) : decision.status === 'multi' ? 'Multiple agents' : 'Router'
  return (
    <div className="mb-1 flex items-center gap-2 text-sm">
      <span className="font-semibold">{name}</span>
      {response && agent && (
        <span className={`rounded-full px-2 py-0.5 text-xs ring-1 ring-inset ${agentTheme(agent).chip}`}>
          {response.capability.replace(/_/g, ' ')}
        </span>
      )}
    </div>
  )
}

function AnswerBody({ result, labels, onClarify }: Props) {
  const { decision, response } = result
  return (
    <>
      <p className={decision.status === 'fallback' ? 'text-zinc-500 dark:text-zinc-400' : ''}>{result.message}</p>

      {response && response.items.length > 0 && (
        <ul className="mt-3 divide-y divide-zinc-100 overflow-hidden rounded-lg border border-zinc-200 dark:divide-zinc-800 dark:border-zinc-800">
          {response.items.map((item) => (
            <li key={item.id} className="flex items-start gap-3 px-3 py-2.5 hover:bg-zinc-50 dark:hover:bg-zinc-800/50">
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{item.title}</p>
                <p className="mt-0.5 truncate text-xs text-zinc-500 dark:text-zinc-400">
                  <span className="font-mono">{item.id}</span>
                  {item.subtitle && <> · {item.subtitle}</>}
                </p>
              </div>
              {item.status && <StatusBadge status={item.status} />}
            </li>
          ))}
        </ul>
      )}

      {decision.status === 'clarify' && (
        <div className="mt-3 flex flex-wrap gap-2">
          {decision.candidates.map((name) => {
            const label = labels[name] ?? name
            return (
              <button
                key={name}
                onClick={() => onClarify(`${result.query.trim().replace(/[?.!]+$/, '')} in ${label}`)}
                className={`rounded-lg px-3 py-1.5 text-sm font-medium ring-1 ring-inset transition hover:brightness-95 ${agentTheme(name).chip}`}
              >
                {label}
              </button>
            )
          })}
        </div>
      )}

      <RoutingTrace result={result} labels={labels} />
    </>
  )
}
