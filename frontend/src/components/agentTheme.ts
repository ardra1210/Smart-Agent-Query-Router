// Visual identity per agent. Unknown agents (newly registered ones) get a neutral default.

interface AgentTheme {
  initials: string
  avatar: string
  bar: string
  chip: string
}

const THEMES: Record<string, AgentTheme> = {
  GitHubAgent: {
    initials: 'GH',
    avatar: 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900',
    bar: 'bg-zinc-800 dark:bg-zinc-200',
    chip: 'bg-zinc-100 text-zinc-700 ring-zinc-300 dark:bg-zinc-800 dark:text-zinc-200 dark:ring-zinc-700',
  },
  LinearAgent: {
    initials: 'LN',
    avatar: 'bg-indigo-600 text-white',
    bar: 'bg-indigo-500',
    chip: 'bg-indigo-50 text-indigo-700 ring-indigo-200 dark:bg-indigo-950 dark:text-indigo-300 dark:ring-indigo-800',
  },
}

const DEFAULT_THEME: AgentTheme = {
  initials: '',
  avatar: 'bg-teal-600 text-white',
  bar: 'bg-teal-500',
  chip: 'bg-teal-50 text-teal-700 ring-teal-200 dark:bg-teal-950 dark:text-teal-300 dark:ring-teal-800',
}

export function agentTheme(name: string): AgentTheme {
  return THEMES[name] ?? { ...DEFAULT_THEME, initials: name.slice(0, 2).toUpperCase() }
}
