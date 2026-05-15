import { prisma } from '@/lib/prisma'
import { computeBadges, BADGE_DEFS } from '@/lib/utils'
import Link from 'next/link'

export const dynamic = 'force-dynamic'

function fmtDuration(secs: number | null) {
  if (!secs) return null
  const m = Math.floor(secs / 60)
  const s = secs % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

export default async function HistoryPage() {
  const season = await prisma.season.findFirst({ where: { active: true } })

  if (!season) {
    return (
      <div className="text-center py-20">
        <p className="text-gray-400 mb-4">Nenhuma season ativa.</p>
        <Link href="/admin" className="text-amber-400 underline">Criar season no painel admin</Link>
      </div>
    )
  }

  const matches = await prisma.match.findMany({
    where: { seasonId: season.id },
    include: {
      players: {
        include: { player: { select: { id: true, nick: true } } },
      },
    },
    orderBy: { createdAt: 'desc' },
    take: 50,
  })

  const hasStats = (m: typeof matches[0]) => m.players.some((p) => p.kills !== null)

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-widest text-amber-400">HISTÓRICO</h1>
        <p className="text-xs text-gray-500 mt-0.5">{season.name} · {matches.length} partidas</p>
      </div>

      {matches.length === 0 && (
        <p className="text-center text-gray-500 py-10">Nenhuma partida registrada.</p>
      )}

      <div className="space-y-4">
        {matches.map((m) => {
          const team1 = m.players.filter((p) => p.team === 1)
          const team2 = m.players.filter((p) => p.team === 2)
          const withStats = hasStats(m)
          const badgeMap = withStats
            ? computeBadges(m.players.map((p) => ({ playerId: p.id, kills: p.kills, deaths: p.deaths, assists: p.assists, healing: p.healing, damage: p.damage, visionScore: p.visionScore, gold: p.gold, cs: p.cs })))
            : new Map()

          return (
            <div key={m.id} className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
              {/* Header */}
              <div className="flex items-center justify-between px-4 py-2 bg-gray-800/60 text-xs text-gray-400">
                <div className="flex items-center gap-3">
                  <span>{new Date(m.createdAt).toLocaleString('pt-BR')}</span>
                  {m.duration && <span>{fmtDuration(m.duration)}</span>}
                  {m.source === 'lcu' && (
                    <span className="bg-indigo-900 text-indigo-300 px-1.5 py-0.5 rounded text-[10px] font-bold tracking-wider">AUTO</span>
                  )}
                </div>
                <span className={`font-bold tracking-wider ${m.winnerTeam === 1 ? 'text-blue-400' : 'text-red-400'}`}>
                  {m.winnerTeam === 1 ? 'Time Azul venceu' : 'Time Vermelho venceu'}
                </span>
              </div>

              {/* Teams */}
              {withStats ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs border-collapse">
                    <thead>
                      <tr className="text-gray-500 uppercase tracking-widest">
                        <th className="px-3 py-2 text-left">Jogador</th>
                        <th className="px-2 py-2 text-center">Campeão</th>
                        <th className="px-2 py-2 text-center">K/D/A</th>
                        <th className="px-2 py-2 text-center">Dano</th>
                        <th className="px-2 py-2 text-center">Cura</th>
                        <th className="px-2 py-2 text-center">Ouro</th>
                        <th className="px-2 py-2 text-center">CS</th>
                        <th className="px-2 py-2 text-center">Visão</th>
                        <th className="px-3 py-2 text-left">Badges</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[...team1, ...team2].map((p, idx) => {
                        const isTeam1 = p.team === 1
                        const won = p.team === m.winnerTeam
                        const badges = badgeMap.get(p.id) ?? []
                        const separator = idx === team1.length - 1
                        return (
                          <tr
                            key={p.id}
                            className={`border-t border-gray-800 ${separator ? 'border-b-2 border-b-gray-700' : ''} hover:bg-gray-800/40 transition-colors`}
                          >
                            <td className="px-3 py-2">
                              <Link
                                href={`/players/${p.player.id}`}
                                className={`font-semibold hover:underline ${isTeam1 ? 'text-blue-300' : 'text-red-300'}`}
                              >
                                {p.player.nick}
                              </Link>
                              {won && <span className="ml-1 text-amber-400 text-[10px]">✓</span>}
                            </td>
                            <td className="px-2 py-2 text-center text-gray-400">{p.champion ?? '—'}</td>
                            <td className="px-2 py-2 text-center font-mono">
                              <span className="text-green-400">{p.kills ?? '—'}</span>
                              <span className="text-gray-600">/</span>
                              <span className="text-red-400">{p.deaths ?? '—'}</span>
                              <span className="text-gray-600">/</span>
                              <span className="text-blue-400">{p.assists ?? '—'}</span>
                            </td>
                            <td className="px-2 py-2 text-center text-gray-300">{p.damage?.toLocaleString('pt-BR') ?? '—'}</td>
                            <td className="px-2 py-2 text-center text-gray-300">{p.healing?.toLocaleString('pt-BR') ?? '—'}</td>
                            <td className="px-2 py-2 text-center text-gray-300">{p.gold?.toLocaleString('pt-BR') ?? '—'}</td>
                            <td className="px-2 py-2 text-center text-gray-300">{p.cs ?? '—'}</td>
                            <td className="px-2 py-2 text-center text-gray-300">{p.visionScore ?? '—'}</td>
                            <td className="px-3 py-2">
                              <div className="flex gap-1 flex-wrap">
                                {badges.map((b) => {
                                  const def = BADGE_DEFS[b]
                                  return def ? (
                                    <span
                                      key={b}
                                      title={def.desc}
                                      className="text-sm cursor-default"
                                    >
                                      {def.emoji}
                                    </span>
                                  ) : null
                                })}
                              </div>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="px-4 py-3 flex gap-6 text-sm">
                  <div>
                    <span className={`text-xs font-bold tracking-wider ${m.winnerTeam === 1 ? 'text-blue-400' : 'text-gray-500'} mr-2`}>AZUL</span>
                    {team1.map((p) => (
                      <Link key={p.id} href={`/players/${p.player.id}`} className="mr-2 hover:text-amber-400 transition-colors">{p.player.nick}</Link>
                    ))}
                  </div>
                  <span className="text-gray-600 self-center">vs</span>
                  <div>
                    <span className={`text-xs font-bold tracking-wider ${m.winnerTeam === 2 ? 'text-red-400' : 'text-gray-500'} mr-2`}>VERM</span>
                    {team2.map((p) => (
                      <Link key={p.id} href={`/players/${p.player.id}`} className="mr-2 hover:text-amber-400 transition-colors">{p.player.nick}</Link>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
