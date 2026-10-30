import { useEffect, useMemo, useRef, useState } from 'react'
import { fetchAgents, fetchHealth, sendQuery } from './api'
import { AssistantMessage } from './components/AssistantMessage'
import { Composer } from './components/Composer'
import { Sidebar } from './components/Sidebar'
import type { AgentInfo, ChatMessage, Health, QueryResult } from './types'

const EXAMPLES = [
  { query: 'Show my open pull requests', hint: 'GitHub' },
  { query: 'What issues are assigned to me?', hint: 'Linear' },
  { query: "What's the weather today?", hint: 'Out of scope' },
  { query: 'Show my issues', hint: 'Ambiguous' },
  { query: 'Which PRs need my review?', hint: 'GitHub' },
  { query: 'Is anything blocked in the current sprint?', hint: 'Linear' },
  { query: 'Show my open PRs and my Linear tickets', hint: 'Multi-part' },
  { query: 'What am I supposed to be working on?', hint: 'No keywords (needs Claude)' },
]

let nextId = 0
const newId = () => String(++nextId)

export default function App() {
  const [agents, setAgents] = useState<AgentInfo[]>([])
  const [online, setOnline] = useState<boolean | null>(null)
  const [health, setHealth] = useState<Health | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [pending, setPending] = useState(false)
  const [dark, setDark] = useState(() => document.documentElement.classList.contains('dark'))
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    Promise.all([fetchAgents(), fetchHealth()])
      .then(([list, status]) => {
        setAgents(list)
        setHealth(status)
        setOnline(true)
      })
      .catch(() => setOnline(false))
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, pending])

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    localStorage.setItem('theme', dark ? 'dark' : 'light')
  }, [dark])

  const labels = useMemo(() => Object.fromEntries(agents.map((a) => [a.name, a.label])), [agents])

  // Per-agent routed counts plus multi / clarify / fallback totals for the sidebar.
  const stats = useMemo(() => {
    const counts: Record<string, number> = {}
    const add = (key: string) => (counts[key] = (counts[key] ?? 0) + 1)
    const tally = ({ decision, parts }: QueryResult) => {
      add(decision.status === 'routed' && decision.agent ? decision.agent : decision.status)
      parts.forEach(tally)
    }
    for (const message of messages) if (message.role === 'assistant') tally(message.result)
    return counts
  }, [messages])

  async function ask(query: string) {
    setMessages((prev) => [...prev, { id: newId(), role: 'user', text: query }])
    setPending(true)
    try {
      const result = await sendQuery(query)
      setMessages((prev) => [...prev, { id: newId(), role: 'assistant', result }])
      setOnline(true)
    } catch {
      setOnline(false)
      setMessages((prev) => [
        ...prev,
        { id: newId(), role: 'error', text: 'Could not reach the backend. Is it running on port 8000?' },
      ])
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="flex h-full">
      <Sidebar agents={agents} stats={stats} online={online} health={health} />

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-3 border-b border-zinc-200 px-6 py-3 dark:border-zinc-800">
          <img src="/favicon.svg" alt="" className="size-7" />
          <div>
            <h1 className="text-sm font-semibold">Smart Agent Query Router</h1>
            <p className="text-xs text-zinc-500">Ask a question. The router picks the agent that can answer it.</p>
          </div>
          <div className="ml-auto flex items-center gap-1">
            {messages.length > 0 && (
              <button
                onClick={() => setMessages([])}
                className="rounded-lg px-3 py-1.5 text-sm text-zinc-500 hover:bg-zinc-100 hover:text-zinc-800 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
              >
                Clear
              </button>
            )}
            <button
              onClick={() => setDark((d) => !d)}
              aria-label="Toggle dark mode"
              className="rounded-lg p-2 text-zinc-500 hover:bg-zinc-100 hover:text-zinc-800 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
            >
              {dark ? '☀︎' : '☾'}
            </button>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-3xl space-y-6 px-6 py-8">
            {messages.length === 0 && (
              <div className="pt-10 text-center">
                <h2 className="text-2xl font-semibold tracking-tight">What do you want to know?</h2>
                <p className="mt-2 text-sm text-zinc-500">
                  Questions about GitHub or Linear are routed to the right agent. Anything else is politely declined.
                </p>
                <div className="mt-8 grid gap-2 text-left sm:grid-cols-2">
                  {EXAMPLES.map((example) => (
                    <button
                      key={example.query}
                      onClick={() => ask(example.query)}
                      disabled={pending}
                      className="rounded-xl border border-zinc-200 bg-white px-4 py-3 text-sm transition hover:border-indigo-300 hover:shadow-sm dark:border-zinc-800 dark:bg-zinc-900 dark:hover:border-indigo-700"
                    >
                      <span className="block">{example.query}</span>
                      <span className="mt-1 block text-xs text-zinc-400">{example.hint}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((message) => {
              if (message.role === 'user') {
                return (
                  <div key={message.id} className="flex justify-end">
                    <p className="max-w-[80%] rounded-2xl rounded-tr-sm bg-indigo-600 px-4 py-2.5 text-white">
                      {message.text}
                    </p>
                  </div>
                )
              }
              if (message.role === 'error') {
                return (
                  <p
                    key={message.id}
                    className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/50 dark:text-red-300"
                  >
                    {message.text}
                  </p>
                )
              }
              return <AssistantMessage key={message.id} result={message.result} labels={labels} onClarify={ask} />
            })}

            {pending && (
              <div className="flex items-center gap-2 text-sm text-zinc-400">
                <span className="size-2 animate-pulse rounded-full bg-indigo-500" />
                Routing…
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        </div>

        <div className="border-t border-zinc-200 px-6 py-4 dark:border-zinc-800">
          <div className="mx-auto max-w-3xl">
            <Composer disabled={pending} onSend={ask} />
          </div>
        </div>
      </main>
    </div>
  )
}
