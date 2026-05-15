import { prisma } from '@/lib/prisma'
import { calcPoints, calcWinRate, getTier, computeBadges, BADGE_DEFS } from '@/lib/utils'
import Link from 'next/link'
import { notFound } from 'next/navigation'

export const dynamic = 'force-dynamic'

export default async function PlayerPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const playerId = Number(id)

  const player = await prisma.player.findUnique({
    where: { id: playerId },
    include: {
      stats: { include: { season: true }, orderBy: { season: { createdAt: 'desc' } } },
      matchPlayers: {
        include: {
          match: {
            include: {
              players: {
                include: { player: { select: { id: true, nick: true } } },
              },
            },
          },
        },
        orderBy: { match: { createdAt: 'desc' } },
        take: 20,
      },
    },
  })

  if (!player) notFound()

  const activeStat = player.stats.find((s) => s.season.active)
  const winRate = activeStat ? calcWinRate(activeStat.wins, activeStat.losses) : 50
  const tier = getTier(winRate)

  // Aggregate stats from LCU matches
  const lcuMatches = player.matchPlayers.filter((mp) => mp.kills !== null)
  const agg = lcuMatches.reduce(
    (acc, mp) => ({
      kills:       acc.kills       + (mp.kills       ?? 0),
      deaths:      acc.deaths      + (mp.deaths      ?? 0),
      assists:     acc.assists     + (mp.assists      ?? 0),
      damage:      acc.damage      + (mp.damage       ?? 0),
      healing:     acc.healing     + (mp.healing      ?? 0),
      gold:        acc.gold        + (mp.gold         ?? 0),
      cs:          acc.cs          + (mp.cs           ?? 0),
      visionScore: acc.visionScore + (mp.visionScore  ?? 0),
    }),
    { kills: 0, deaths: 0, assists: 0, damage: 0, healing: 0, gold: 0, cs: 0, visionScore: 0 },
  )
  const n = lcuMatches.length || 1
  const avg = {
    kills:       (agg.kills       / n).toFixed(1),
    deaths:      (agg.deaths      / n).toFixed(1),
    assists:     (agg.assists     / n).toFixed(1),
    damage:      Math.round(agg.damage       / n).toLocaleString('pt-BR'),
    healing:     Math.round(agg.healing      / n).toLocaleString('pt-BR'),
    gold:        Math.round(agg.gold         / n).toLocaleString('pt-BR'),
    cs:          (agg.cs          / n).toFixed(1),
    visionScore: (agg.visionScore / n).toFixed(1),
  }

  // Badge tally across all LCU matches
  const badgeTally = new Map<string, number>()
  for (const mp of player.matchPlayers) {
    const allMpInMatch = mp.match.players
    const badges = computeBadges(
      allMpInMatch.map((x) => ({
        playerId:    x.id,
        kills:       x.kills,
        deaths:      x.deaths,
        assists:     x.assists,
        healing:     x.healing,
        damage:      x.damage,
        visionScore: x.visionScore,
        gold:        x.gold,
        cs:          x.cs,
      })),
    )
    const myBadges = badges.get(mp.id) ?? []
    myBadges.forEach((b) => badgeTally.set(b, (badgeTally.get(b) ?? 0) + 1))
  }
  const sortedBadges = [...badgeTally.entries()].sort((a, b) => b[1] - a[1])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <Link href="/" className="text-xs text-gray-500 hover:text-gray-300 transition-colors">← Placar</Link>
          <h1 className="text-3xl font-bold tracking-widest mt-1">{player.nick}</h1>
          {activeStat && (
            <p className="text-gray-400 text-sm mt-1">
              {activeStat.wins}V {activeStat.losses}D · {winRate.toFixed(1)}% WR · {calcPoints(activeStat.wins, activeStat.losses)} pts
            </p>
          )}
        </div>
        <span className={`px-4 py-2 rounded text-sm font-bold tracking-wider ${tier.bgClass} ${tier.textClass}`}>
          {tier.name}
        </span>
      </div>

      {/* Seasons */}
      <section className="bg-gray-900 rounded-lg border border-gray-800 p-5">
        <h2 className="text-xs font-bold tracking-widest text-gray-400 mb-4 uppercase">Seasons</h2>
        <div className="space-y-2">
          {player.stats.map((s) => {
            const wr = calcWinRate(s.wins, s.losses)
            return (
              <div key={s.id} className="flex items-center justify-between text-sm">
                <span className={s.season.active ? 'text-amber-400 font-semibold' : 'text-gray-400'}>
                  {s.season.name}
                </span>
                <span className="text-gray-300 font-mono">
                  {s.wins}V {s.losses}D · {wr.toFixed(1)}% · {calcPoints(s.wins, s.losses)}pts
                </span>
              </div>
            )
          })}
          {player.stats.length === 0 && <p className="text-gray-600 text-sm">Sem dados de season.</p>}
        </div>
      </section>

      {/* LCU Stats */}
      {lcuMatches.length > 0 && (
        <section className="bg-gray-900 rounded-lg border border-gray-800 p-5">
          <h2 className="text-xs font-bold tracking-widest text-gray-400 mb-4 uppercase">
            Médias por Partida ({lcuMatches.length} com stats)
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              { label: 'K/D/A', value: `${avg.kills}/${avg.deaths}/${avg.assists}` },
              { label: 'Dano', value: avg.damage },
              { label: 'Cura', value: avg.healing },
              { label: 'Ouro', value: avg.gold },
              { label: 'CS', value: avg.cs },
              { label: 'Visão', value: avg.visionScore },
            ].map((stat) => (
              <div key={stat.label} className="bg-gray-800 rounded p-3 text-center">
                <p className="text-xs text-gray-500 mb-1 uppercase tracking-wider">{stat.label}</p>
                <p className="text-lg font-bold font-mono text-gray-100">{stat.value}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Badges */}
      {sortedBadges.length > 0 && (
        <section className="bg-gray-900 rounded-lg border border-gray-800 p-5">
          <h2 className="text-xs font-bold tracking-widest text-gray-400 mb-4 uppercase">Badges Conquistados</h2>
          <div className="flex flex-wrap gap-3">
            {sortedBadges.map(([badge, count]) => {
              const def = BADGE_DEFS[badge]
              if (!def) return null
              return (
                <div key={badge} className="flex items-center gap-2 bg-gray-800 rounded-lg px-3 py-2">
                  <span className="text-xl">{def.emoji}</span>
                  <div>
                    <p className="text-xs font-bold text-gray-200">{def.label}</p>
                    <p className="text-[10px] text-gray-500">{def.desc} · {count}×</p>
                  </div>
                </div>
              )
            })}
          </div>
        </section>
      )}

      {/* Recent Matches */}
      <section className="bg-gray-900 rounded-lg border border-gray-800 p-5">
        <h2 className="text-xs font-bold tracking-widest text-gray-400 mb-4 uppercase">Partidas Recentes</h2>
        {player.matchPlayers.length === 0 ? (
          <p className="text-gray-600 text-sm">Nenhuma partida registrada.</p>
        ) : (
          <div className="space-y-2">
            {player.matchPlayers.map((mp) => {
              const won = mp.team === mp.match.winnerTeam
              const allies = mp.match.players
                .filter((p) => p.team === mp.team && p.player.id !== playerId)
                .map((p) => p.player.nick)
              const badges = mp.kills !== null
                ? computeBadges(mp.match.players.map((x) => ({ playerId: x.id, kills: x.kills, deaths: x.deaths, assists: x.assists, healing: x.healing, damage: x.damage, visionScore: x.visionScore, gold: x.gold, cs: x.cs })))
                : new Map()
              const myBadges = badges.get(mp.id) ?? []
              return (
                <div
                  key={mp.id}
                  className={`flex items-center justify-between gap-4 rounded px-3 py-2 text-xs border-l-2 ${
                    won ? 'border-green-500 bg-green-900/10' : 'border-red-500 bg-red-900/10'
                  }`}
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`font-bold ${won ? 'text-green-400' : 'text-red-400'}`}>
                        {won ? 'Vitória' : 'Derrota'}
                      </span>
                      {mp.champion && <span className="text-gray-400">{mp.champion}</span>}
                      {mp.kills !== null && (
                        <span className="font-mono text-gray-300">
                          {mp.kills}/{mp.deaths}/{mp.assists}
                        </span>
                      )}
                    </div>
                    <p className="text-gray-600 mt-0.5">
                      {new Date(mp.match.createdAt).toLocaleString('pt-BR')}
                      {allies.length > 0 && ` · com ${allies.slice(0, 3).join(', ')}${allies.length > 3 ? '…' : ''}`}
                    </p>
                  </div>
                  <div className="flex gap-1">
                    {myBadges.map((b) => {
                      const def = BADGE_DEFS[b]
                      return def ? <span key={b} title={def.desc} className="text-base">{def.emoji}</span> : null
                    })}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </section>
    </div>
  )
}
