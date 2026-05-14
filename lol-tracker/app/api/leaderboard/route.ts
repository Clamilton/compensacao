import { prisma } from '@/lib/prisma'
import { calcPoints, calcWinRate } from '@/lib/utils'

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const seasonIdParam = searchParams.get('seasonId')

  let season
  if (seasonIdParam) {
    season = await prisma.season.findUnique({ where: { id: Number(seasonIdParam) } })
  } else {
    season = await prisma.season.findFirst({ where: { active: true } })
  }

  if (!season) return Response.json({ season: null, rows: [] })

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

  return Response.json({ season, rows })
}
