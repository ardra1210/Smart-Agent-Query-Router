import { useState, type FormEvent } from 'react'

interface Props {
  disabled: boolean
  onSend: (query: string) => void
}

export function Composer({ disabled, onSend }: Props) {
  const [value, setValue] = useState('')

  function submit(event: FormEvent) {
    event.preventDefault()
    const query = value.trim()
    if (!query || disabled) return
    onSend(query)
    setValue('')
  }

  return (
    <form
      onSubmit={submit}
      className="flex items-center gap-2 rounded-2xl border border-zinc-300 bg-white p-1.5 pl-4 shadow-sm focus-within:border-indigo-400 focus-within:ring-4 focus-within:ring-indigo-500/10 dark:border-zinc-700 dark:bg-zinc-900"
    >
      <input
        autoFocus
        value={value}
        onChange={(e) => setValue(e.target.value)}
        maxLength={500}
        placeholder="Ask about pull requests, issues, sprints…"
        className="min-w-0 flex-1 bg-transparent py-2 outline-none placeholder:text-zinc-400"
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-40"
      >
        Send
      </button>
    </form>
  )
}
