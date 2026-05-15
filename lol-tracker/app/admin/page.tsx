'use client'
import { useState, useEffect, useCallback } from 'react'

interface Player { id: number; nick: string }
interface Season { id: number; name: string; active: boolean }
interface Match {
  id: number
  winnerTeam: number
  createdAt: string
  players: { team: number; player: { nick: string } }[]
}

export default function AdminPage() {
  const [password, setPassword] = useState('')
  const [authed, setAuthed] = useState(false)
  const [authError, setAuthError] = useState('')

  const [players, setPlayers] = useState<Player[]>([])
  const [seasons, setSeasons] = useState<Season[]>([])
  const [matches, setMatches] = useState<Match[]>([])
  const [activeSeason, setActiveSeason] = useState<Season | null>(null)

  const [newNick, setNewNick] = useState('')
  const [newSeasonName, setNewSeasonName] = useState('')

  const [team1, setTeam1] = useState<number[]>([])
  const [team2, setTeam2] = useState<number[]>([])
  const [winner, setWinner] = useState<1 | 2>(1)

  const [msg, setMsg] = useState('')
  const [loading, setLoading] = useState(false)

  const headers = { 'Content-Type': 'application/json', Authorization: `Bearer ${password}` }

  useEffect(() => {
    const saved = localStorage.getItem('x5_admin_pwd')
    if (!saved) return
    setPassword(saved)
    fetch('/api/seasons', { headers: { Authorization: `Bearer ${saved}` } }).then((res) => {
      if (res.ok) { setAuthed(true); loadData() }
    })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const flash = (text: string) => {
    setMsg(text)
    setTimeout(() => setMsg(''), 3000)
  }

  const loadData = useCallback(async () => {
    const [p, s] = await Promise.all([
      fetch('/api/players').then((r) => r.json()),
      fetch('/api/seasons').then((r) => r.json()),
    ])
    setPlayers(p)
    setSeasons(s)
    const active = s.find((x: Season) => x.active) ?? null
    setActiveSeason(active)
    if (active) {
      const m = await fetch(`/api/matches?seasonId=${active.id}`).then((r) => r.json())
      setMatches(m)
    }
  }, [])

  const handleLogin = async () => {
    setAuthError('')
    const res = await fetch('/api/seasons', {
      headers: { Authorization: `Bearer ${password}` },
    })
    if (res.ok) {
      localStorage.setItem('x5_admin_pwd', password)
      setAuthed(true)
      loadData()
    } else {
      setAuthError('Senha incorreta')
    }
  }

  const addPlayer = async () => {
    if (!newNick.trim()) return
    setLoading(true)
    const res = await fetch('/api/players', {
      method: 'POST',
      headers,
      body: JSON.stringify({ nick: newNick }),
    })
    setLoading(false)
    if (res.ok) {
      setNewNick('')
      flash('Jogador adicionado!')
      loadData()
    } else {
      const d = await res.json()
      flash(d.error ?? 'Erro')
    }
  }

  const removePlayer = async (id: number) => {
    if (!confirm('Remover jogador?')) return
    await fetch(`/api/players/${id}`, { method: 'DELETE', headers })
    flash('Jogador removido')
    loadData()
  }

  const createSeason = async () => {
    if (!newSeasonName.trim()) return
    setLoading(true)
    const res = await fetch('/api/seasons', {
      method: 'POST',
      headers,
      body: JSON.stringify({ name: newSeasonName }),
    })
    setLoading(false)
    if (res.ok) {
      setNewSeasonName('')
      flash('Season criada!')
      loadData()
    } else {
      const d = await res.json()
      flash(d.error ?? 'Erro')
    }
  }

  const activateSeason = async (id: number) => {
    await fetch(`/api/seasons/${id}/activate`, { method: 'POST', headers })
    flash('Season ativada!')
    loadData()
  }

  const togglePlayerTeam = (id: number, targetTeam: 1 | 2) => {
    const inT1 = team1.includes(id)
    const inT2 = team2.includes(id)

    if (targetTeam === 1) {
      setTeam2((prev) => prev.filter((x) => x !== id))
      setTeam1((prev) => (inT1 ? prev.filter((x) => x !== id) : [...prev, id]))
    } else {
      setTeam1((prev) => prev.filter((x) => x !== id))
      setTeam2((prev) => (inT2 ? prev.filter((x) => x !== id) : [...prev, id]))
    }
  }

  const registerMatch = async () => {
    if (!activeSeason) return flash('Nenhuma season ativa')
    if (team1.length === 0 && team2.length === 0) return flash('Selecione os jogadores')
    setLoading(true)
    const res = await fetch('/api/matches', {
      method: 'POST',
      headers,
      body: JSON.stringify({
        seasonId: activeSeason.id,
        winnerTeam: winner,
        team1PlayerIds: team1,
        team2PlayerIds: team2,
      }),
    })
    setLoading(false)
    if (res.ok) {
      setTeam1([])
      setTeam2([])
      setWinner(1)
      flash('Partida registrada!')
      loadData()
    } else {
      const d = await res.json()
      flash(d.error ?? 'Erro')
    }
  }

  const deleteMatch = async (id: number) => {
    if (!confirm('Desfazer essa partida?')) return
    await fetch(`/api/matches/${id}`, { method: 'DELETE', headers })
    flash('Partida removida')
    loadData()
  }

  const seedSeason3 = async () => {
    if (!confirm('Importar dados da Season 3 da planilha?')) return
    setLoading(true)
    const res = await fetch('/api/seed', { method: 'POST', headers })
    setLoading(false)
    const d = await res.json()
    if (res.ok) {
      flash('Season 3 importada!')
      loadData()
    } else {
      flash(d.error ?? 'Erro')
    }
  }

  if (!authed) {
    return (
      <div className="max-w-xs mx-auto mt-20 flex flex-col gap-4">
        <h1 className="text-xl font-bold text-amber-400 text-center tracking-wider">ADMIN</h1>
        <input
          type="password"
          placeholder="Senha admin"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleLogin()}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-amber-400"
        />
        {authError && <p className="text-red-400 text-xs">{authError}</p>}
        <button
          onClick={handleLogin}
          className="bg-amber-400 text-gray-950 font-bold py-2 rounded text-sm hover:bg-amber-300 transition-colors"
        >
          Entrar
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-amber-400 tracking-wider">PAINEL ADMIN</h1>
        <button
          onClick={() => { localStorage.removeItem('x5_admin_pwd'); setAuthed(false); setPassword('') }}
          className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
        >
          Sair
        </button>
        {msg && (
          <span className="text-xs bg-green-900 text-green-300 px-3 py-1.5 rounded">{msg}</span>
        )}
      </div>

      {/* Seasons */}
      <section className="bg-gray-900 rounded-lg border border-gray-800 p-5">
        <h2 className="text-sm font-bold tracking-widest text-gray-400 mb-4 uppercase">Seasons</h2>
        <div className="flex gap-2 mb-4">
          <input
            value={newSeasonName}
            onChange={(e) => setNewSeasonName(e.target.value)}
            placeholder="Nome da season (ex: Season 4)"
            className="flex-1 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-amber-400"
          />
          <button
            onClick={createSeason}
            disabled={loading}
            className="bg-amber-400 text-gray-950 font-bold px-4 py-2 rounded text-sm hover:bg-amber-300 disabled:opacity-50 transition-colors"
          >
            Criar
          </button>
        </div>
        <div className="space-y-2">
          {seasons.map((s) => (
            <div key={s.id} className="flex items-center justify-between">
              <span className={`text-sm ${s.active ? 'text-amber-400 font-bold' : 'text-gray-400'}`}>
                {s.name} {s.active && '(ativa)'}
              </span>
              {!s.active && (
                <button
                  onClick={() => activateSeason(s.id)}
                  className="text-xs text-gray-400 border border-gray-700 rounded px-2 py-1 hover:border-amber-400 hover:text-amber-400 transition-colors"
                >
                  Ativar
                </button>
              )}
            </div>
          ))}
        </div>
        <button
          onClick={seedSeason3}
          className="mt-4 text-xs text-gray-500 border border-gray-700 rounded px-3 py-1.5 hover:border-gray-500 hover:text-gray-300 transition-colors"
        >
          Importar Season 3 (planilha)
        </button>
      </section>

      {/* Register Match */}
      <section className="bg-gray-900 rounded-lg border border-gray-800 p-5">
        <h2 className="text-sm font-bold tracking-widest text-gray-400 mb-1 uppercase">
          Registrar Partida
        </h2>
        {activeSeason ? (
          <p className="text-xs text-gray-500 mb-4">Season: {activeSeason.name}</p>
        ) : (
          <p className="text-xs text-red-400 mb-4">Nenhuma season ativa</p>
        )}

        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <p className="text-xs font-bold text-blue-400 mb-2 tracking-wider">TIME AZUL</p>
            <div className="space-y-1 max-h-64 overflow-y-auto">
              {players.map((p) => (
                <button
                  key={p.id}
                  onClick={() => togglePlayerTeam(p.id, 1)}
                  className={`w-full text-left px-3 py-1.5 rounded text-sm transition-colors ${
                    team1.includes(p.id)
                      ? 'bg-blue-600 text-white'
                      : team2.includes(p.id)
                        ? 'opacity-30 bg-gray-800 text-gray-500 cursor-not-allowed'
                        : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                  }`}
                >
                  {p.nick}
                </button>
              ))}
            </div>
          </div>
          <div>
            <p className="text-xs font-bold text-red-400 mb-2 tracking-wider">TIME VERMELHO</p>
            <div className="space-y-1 max-h-64 overflow-y-auto">
              {players.map((p) => (
                <button
                  key={p.id}
                  onClick={() => togglePlayerTeam(p.id, 2)}
                  className={`w-full text-left px-3 py-1.5 rounded text-sm transition-colors ${
                    team2.includes(p.id)
                      ? 'bg-red-600 text-white'
                      : team1.includes(p.id)
                        ? 'opacity-30 bg-gray-800 text-gray-500 cursor-not-allowed'
                        : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                  }`}
                >
                  {p.nick}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4 mb-4">
          <span className="text-sm text-gray-400">Vencedor:</span>
          <button
            onClick={() => setWinner(1)}
            className={`px-4 py-1.5 rounded text-sm font-bold transition-colors ${
              winner === 1 ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            Time Azul
          </button>
          <button
            onClick={() => setWinner(2)}
            className={`px-4 py-1.5 rounded text-sm font-bold transition-colors ${
              winner === 2 ? 'bg-red-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            Time Vermelho
          </button>
        </div>

        <button
          onClick={registerMatch}
          disabled={loading || !activeSeason}
          className="bg-amber-400 text-gray-950 font-bold px-6 py-2 rounded text-sm hover:bg-amber-300 disabled:opacity-50 transition-colors"
        >
          Registrar Resultado
        </button>
      </section>

      {/* Add Player */}
      <section className="bg-gray-900 rounded-lg border border-gray-800 p-5">
        <h2 className="text-sm font-bold tracking-widest text-gray-400 mb-4 uppercase">
          Jogadores
        </h2>
        <div className="flex gap-2 mb-4">
          <input
            value={newNick}
            onChange={(e) => setNewNick(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && addPlayer()}
            placeholder="Nick do jogador"
            className="flex-1 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-amber-400"
          />
          <button
            onClick={addPlayer}
            disabled={loading}
            className="bg-amber-400 text-gray-950 font-bold px-4 py-2 rounded text-sm hover:bg-amber-300 disabled:opacity-50 transition-colors"
          >
            Adicionar
          </button>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {players.map((p) => (
            <div
              key={p.id}
              className="flex items-center justify-between bg-gray-800 rounded px-3 py-1.5"
            >
              <span className="text-sm text-gray-300">{p.nick}</span>
              <button
                onClick={() => removePlayer(p.id)}
                className="text-gray-600 hover:text-red-400 ml-2 text-xs transition-colors"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      </section>

      {/* Recent Matches */}
      <section className="bg-gray-900 rounded-lg border border-gray-800 p-5">
        <h2 className="text-sm font-bold tracking-widest text-gray-400 mb-4 uppercase">
          Partidas Recentes
        </h2>
        {matches.length === 0 ? (
          <p className="text-gray-600 text-sm">Nenhuma partida registrada.</p>
        ) : (
          <div className="space-y-2">
            {matches.map((m) => {
              const t1 = m.players.filter((p) => p.team === 1).map((p) => p.player.nick)
              const t2 = m.players.filter((p) => p.team === 2).map((p) => p.player.nick)
              return (
                <div
                  key={m.id}
                  className="flex items-start justify-between gap-4 bg-gray-800 rounded px-3 py-2"
                >
                  <div className="text-xs flex-1">
                    <div className="flex gap-3 flex-wrap">
                      <span className={m.winnerTeam === 1 ? 'text-blue-400 font-bold' : 'text-gray-500'}>
                        Azul: {t1.join(', ') || '—'}
                      </span>
                      <span className="text-gray-600">vs</span>
                      <span className={m.winnerTeam === 2 ? 'text-red-400 font-bold' : 'text-gray-500'}>
                        Verm: {t2.join(', ') || '—'}
                      </span>
                    </div>
                    <p className="text-gray-600 mt-0.5">
                      {new Date(m.createdAt).toLocaleString('pt-BR')}
                    </p>
                  </div>
                  <button
                    onClick={() => deleteMatch(m.id)}
                    className="text-gray-600 hover:text-red-400 text-xs shrink-0 transition-colors"
                  >
                    Desfazer
                  </button>
                </div>
              )
            })}
          </div>
        )}
      </section>
    </div>
  )
}
