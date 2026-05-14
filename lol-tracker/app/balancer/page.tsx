'use client'
import { useState, useEffect } from 'react'

interface Player {
  id: number
  nick: string
}

interface BalancedPlayer {
  id: number
  nick: string
  winRate: number
}

interface BalanceResult {
  team1: BalancedPlayer[]
  team2: BalancedPlayer[]
  diff: number
}

interface Season {
  id: number
  name: string
  active: boolean
}

export default function BalancerPage() {
  const [players, setPlayers] = useState<Player[]>([])
  const [seasons, setSeasons] = useState<Season[]>([])
  const [activeSeason, setActiveSeason] = useState<Season | null>(null)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [result, setResult] = useState<BalanceResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      fetch('/api/players').then((r) => r.json()),
      fetch('/api/seasons').then((r) => r.json()),
    ]).then(([p, s]: [Player[], Season[]]) => {
      setPlayers(p)
      setSeasons(s)
      setActiveSeason(s.find((x) => x.active) ?? null)
    })
  }, [])

  const toggle = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
    setResult(null)
  }

  const balance = async () => {
    if (selected.size < 2) return setError('Selecione pelo menos 2 jogadores')
    if (!activeSeason) return setError('Nenhuma season ativa')
    setError('')
    setLoading(true)
    const res = await fetch('/api/balance', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ playerIds: Array.from(selected), seasonId: activeSeason.id }),
    })
    setLoading(false)
    if (res.ok) {
      setResult(await res.json())
    } else {
      const d = await res.json()
      setError(d.error ?? 'Erro ao balancear')
    }
  }

  const selectAll = () => setSelected(new Set(players.map((p) => p.id)))
  const clearAll = () => {
    setSelected(new Set())
    setResult(null)
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-widest text-amber-400 mb-1">BALANCEADOR</h1>
        <p className="text-xs text-gray-500">
          Selecione os jogadores presentes para sugerir times equilibrados por win rate.
          {activeSeason && ` (${activeSeason.name})`}
        </p>
      </div>

      {/* Player Selection */}
      <div className="bg-gray-900 rounded-lg border border-gray-800 p-5">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs text-gray-400 font-semibold uppercase tracking-widest">
            Jogadores ({selected.size} selecionados)
          </span>
          <div className="flex gap-2">
            <button
              onClick={selectAll}
              className="text-xs text-gray-500 hover:text-gray-300 border border-gray-700 rounded px-2 py-1 transition-colors"
            >
              Todos
            </button>
            <button
              onClick={clearAll}
              className="text-xs text-gray-500 hover:text-gray-300 border border-gray-700 rounded px-2 py-1 transition-colors"
            >
              Limpar
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
          {players.map((p) => (
            <button
              key={p.id}
              onClick={() => toggle(p.id)}
              className={`px-3 py-2 rounded text-sm font-medium transition-colors text-left ${
                selected.has(p.id)
                  ? 'bg-amber-400 text-gray-950'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-200'
              }`}
            >
              {p.nick}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      <button
        onClick={balance}
        disabled={loading || selected.size < 2}
        className="w-full bg-amber-400 text-gray-950 font-bold py-3 rounded text-sm tracking-wider hover:bg-amber-300 disabled:opacity-50 transition-colors"
      >
        {loading ? 'Balanceando...' : 'BALANCEAR TIMES'}
      </button>

      {/* Result */}
      {result && (
        <div className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
          <div className="bg-gray-800 px-5 py-3 flex items-center justify-between">
            <span className="text-xs font-bold tracking-widest text-gray-400 uppercase">
              Times Sugeridos
            </span>
            <span className="text-xs text-gray-500">
              Diferença de WR: {result.diff.toFixed(1)}%
            </span>
          </div>
          <div className="grid grid-cols-2 divide-x divide-gray-800">
            <TeamColumn
              label="TIME AZUL"
              labelClass="text-blue-400"
              players={result.team1}
            />
            <TeamColumn
              label="TIME VERMELHO"
              labelClass="text-red-400"
              players={result.team2}
            />
          </div>
          <div className="px-5 py-3 border-t border-gray-800">
            <div className="grid grid-cols-2 text-xs text-gray-500">
              <div>
                WR médio:{' '}
                <span className="text-blue-400 font-mono">
                  {(result.team1.reduce((s, p) => s + p.winRate, 0) / (result.team1.length || 1)).toFixed(1)}%
                </span>
              </div>
              <div>
                WR médio:{' '}
                <span className="text-red-400 font-mono">
                  {(result.team2.reduce((s, p) => s + p.winRate, 0) / (result.team2.length || 1)).toFixed(1)}%
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function TeamColumn({
  label,
  labelClass,
  players,
}: {
  label: string
  labelClass: string
  players: BalancedPlayer[]
}) {
  return (
    <div className="p-4">
      <p className={`text-xs font-bold tracking-widest mb-3 ${labelClass}`}>{label}</p>
      <ul className="space-y-1.5">
        {players.map((p) => (
          <li key={p.id} className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-200">{p.nick}</span>
            <span className="text-xs font-mono text-gray-500">{p.winRate.toFixed(1)}%</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
