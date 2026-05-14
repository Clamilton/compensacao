import { prisma } from '@/lib/prisma'
import { calcWinRate, balanceTeams } from '@/lib/utils'

export async function POST(request: Request) {
  const { playerIds, seasonId } = await request.json()

  if (!Array.isArray(playerIds) || playerIds.length < 2) {
    return Response.json({ error: 'Selecione pelo menos 2 jogadores' }, { status: 400 })
  }

  const stats = await prisma.playerStat.findMany({
    where: { playerId: { in: playerIds }, seasonId },
    include: { player: { select: { id: true, nick: true } } },
  })

  // Build map: playerId -> winRate (players without stats = 50%)
  const statsMap = new Map(stats.map((s) => [s.playerId, calcWinRate(s.wins, s.losses)]))

  const players = await prisma.player.findMany({
    where: { id: { in: playerIds }, active: true },
    select: { id: true, nick: true },
  })

  const withRates = players.map((p) => ({
    id: p.id,
    nick: p.nick,
    winRate: statsMap.get(p.id) ?? 50,
  }))

  const result = balanceTeams(withRates)
  return Response.json(result)
}
