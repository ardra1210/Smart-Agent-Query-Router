import type { AgentInfo, Health } from '../types'
import { agentTheme } from './agentTheme'

interface Props {
  agents: AgentInfo[]
  stats: Record<string, number>
  online: boolean | null
  health: Health | null
}

const OUTCOMES = [
  { key: 'multi', label: 'Multi-part' },
  { key: 'clarify', label: 'Clarified' },
  { key: 'fallback', label: 'Declined' },
]

export function Sidebar({ agents, stats, online, health }: Props) {
  return (
    <aside className="hidden w-80 shrink-0 flex-col gap-6 overflow-y-auto border-r border-zinc-200 bg-white p-5 lg:flex dark:border-zinc-800 dark:bg-zinc-900/50">
      <section>
        <h2 className="mb-3 flex items-center justify-between text-xs font-semibold tracking-wide text-zinc-500 uppercase">
          Agents
          <span className="flex items-center gap-1.5 font-normal normal-case">
            <span
              className={`size-2 rounded-full ${online === null ? 'bg-zinc-400' : online ? 'bg-emerald-500' : 'bg-red-500'}`}
            />
            {online === null ? 'connecting' : online ? 'backend online' : 'backend offline'}
          </span>
        </h2>
        <div className="space-y-3">
          {agents.map((agent) => {
            const theme = agentTheme(agent.name)
            return (
              <div key={agent.name} className="rounded-xl border border-zinc-200 p-3 dark:border-zinc-800">
                <div className="flex items-center gap-2">
                  <span className={`flex size-6 items-center justify-center rounded-md text-[10px] font-bold ${theme.avatar}`}>
                    {theme.initials}
                  </span>
                  <span className="font-medium">{agent.label}</span>
                  <span className="ml-auto font-mono text-xs text-zinc-400">{stats[agent.name] ?? 0} routed</span>
                </div>
                <p className="mt-2 text-xs text-zinc-500 dark:text-zinc-400">{agent.description}</p>
                <ul className="mt-2 flex flex-wrap gap-1">
                  {agent.capabilities.map((cap) => (
                    <li
                      key={cap.name}
                      title={cap.description}
                      className="rounded bg-zinc-100 px-1.5 py-0.5 text-[11px] text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300"
                    >
                      {cap.name.replace(/_/g, ' ')}
                    </li>
                  ))}
                </ul>
              </div>
            )
          })}
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-xs font-semibold tracking-wide text-zinc-500 uppercase">Other outcomes</h2>
        <dl className="grid grid-cols-3 gap-2">
          {OUTCOMES.map(({ key, label }) => (
            <div key={key} className="rounded-xl border border-zinc-200 p-3 dark:border-zinc-800">
              <dt className="text-xs text-zinc-500">{label}</dt>
              <dd className="mt-1 font-mono text-xl font-semibold">{stats[key] ?? 0}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="mt-auto rounded-xl bg-zinc-50 p-3 text-xs text-zinc-500 dark:bg-zinc-900 dark:text-zinc-400">
        <p className="mb-1 font-medium text-zinc-700 dark:text-zinc-300">
          Routing: {health?.escalation ? 'keyword + Claude fallback' : 'keyword only'}
        </p>
        {health?.escalation
          ? 'Keyword matching decides first; questions it is unsure about are escalated to Claude.'
          : 'Deterministic keyword matching, no API key needed.'}{' '}
        Open <em>Why this answer?</em> under any reply to see how it was routed.
      </section>
    </aside>
  )
}
