import { prisma } from '@/lib/prisma'
import { calcPoints, calcWinRate, getTier } from '@/lib/utils'
import Link from 'next/link'

export const dynamic = 'force-dynamic'

export default async function Home() {
  const season = await prisma.season.findFirst({ where: { active: true } })

  if (!season) {
    return (
      <div className="text-center py-20">
        <p className="text-gray-400 mb-4">Nenhuma season ativa.</p>
        <Link href="/admin" className="text-amber-400 underline">
          Criar season no painel admin
        </Link>
      </div>
    )
  }

  const stats = await prisma.playerStat.findMany({
    where: { seasonId: season.id },
    include: { player: { select: { id: true, nick: true } } },
  })

  const rows = stats
    .map((s) => ({
      id: s.player.id,
      nick: s.player.nick,
      wins: s.wins,
      losses: s.losses,
      games: s.wins + s.losses,
      winRate: calcWinRate(s.wins, s.losses),
      points: calcPoints(s.wins, s.losses),
    }))
    .sort((a, b) => b.points - a.points || b.winRate - a.winRate || a.nick.localeCompare(b.nick))

  const total = rows.length

  // Groups for the merged RANK column
  const tierGroups: {
    name: string
    bgClass: string
    textClass: string
    span: number
    startRow: number
  }[] = []

  rows.forEach((_, i) => {
    const tier = getTier(i + 1, total)
    const last = tierGroups[tierGroups.length - 1]
    if (!last || last.name !== tier.name) {
      tierGroups.push({ ...tier, span: 1, startRow: i })
    } else {
      last.span++
    }
  })

  return (
    <div>
      <div className="mb-6 flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-widest text-amber-400">
            X5 — {season.name.toUpperCase()}
          </h1>
          <p className="text-xs text-gray-500 mt-0.5">
            {total} jogadores · Fórmula: V×3 − D×2
          </p>
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg border border-gray-800">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="bg-gray-800 text-xs tracking-widest uppercase text-gray-400">
              <th className="px-3 py-3 text-center w-10">TOP</th>
              <th className="px-4 py-3 text-left">NICK</th>
              <th className="px-3 py-3 text-center">JOGOS</th>
              <th className="px-3 py-3 text-center">VITÓRIAS</th>
              <th className="px-3 py-3 text-center">DERROTAS</th>
              <th className="px-3 py-3 text-center">WIN RATE</th>
              <th className="px-3 py-3 text-center">PONTOS</th>
              <th className="px-3 py-3 text-center w-32">RANK</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => {
              const groupEntry = tierGroups.find((g) => g.startRow === i)
              return (
                <tr
                  key={row.id}
                  className="border-t border-gray-800 hover:bg-gray-800/50 transition-colors"
                >
                  <td className="px-3 py-2.5 text-center text-gray-500 font-mono text-xs">
                    {i + 1}
                  </td>
                  <td className="px-4 py-2.5 font-semibold tracking-wide">
                    {i === 0 && <span className="mr-1.5 text-amber-400">👑</span>}
                    {row.nick}
                  </td>
                  <td className="px-3 py-2.5 text-center text-gray-400">{row.games}</td>
                  <td className="px-3 py-2.5 text-center text-green-400 font-medium">
                    {row.wins}
                  </td>
                  <td className="px-3 py-2.5 text-center text-red-400 font-medium">
                    {row.losses}
                  </td>
                  <td className="px-3 py-2.5 text-center text-gray-300 font-mono">
                    {row.winRate.toFixed(2)}%
                  </td>
                  <td
                    className={`px-3 py-2.5 text-center font-bold font-mono ${
                      row.points > 0
                        ? 'text-green-300'
                        : row.points < 0
                          ? 'text-red-400'
                          : 'text-gray-400'
                    }`}
                  >
                    {row.points}
                  </td>
                  {groupEntry && (
                    <td
                      rowSpan={groupEntry.span}
                      className={`px-2 py-2 text-center text-xs font-bold tracking-wider align-middle border-l border-gray-800 ${groupEntry.bgClass} ${groupEntry.textClass}`}
                    >
                      {groupEntry.name}
                    </td>
                  )}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {total === 0 && (
        <p className="text-center text-gray-500 py-10">
          Nenhum jogador nesta season.{' '}
          <Link href="/admin" className="text-amber-400 underline">
            Adicionar jogadores
          </Link>
        </p>
      )}
    </div>
  )
}
