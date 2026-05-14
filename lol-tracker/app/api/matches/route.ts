import { prisma } from '@/lib/prisma'
import { isAdmin } from '@/lib/auth'

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const seasonId = Number(searchParams.get('seasonId'))

  const matches = await prisma.match.findMany({
    where: seasonId ? { seasonId } : undefined,
    include: {
      players: { include: { player: true } },
    },
    orderBy: { createdAt: 'desc' },
    take: 20,
  })
  return Response.json(matches)
}

export async function POST(request: Request) {
  if (!isAdmin(request)) return Response.json({ error: 'Unauthorized' }, { status: 401 })

  const { seasonId, winnerTeam, team1PlayerIds, team2PlayerIds } = await request.json()

  if (!seasonId || ![1, 2].includes(winnerTeam)) {
    return Response.json({ error: 'Dados inválidos' }, { status: 400 })
  }

  const t1: number[] = team1PlayerIds ?? []
  const t2: number[] = team2PlayerIds ?? []

  if (t1.length === 0 && t2.length === 0) {
    return Response.json({ error: 'Times vazios' }, { status: 400 })
  }

  const match = await prisma.$transaction(async (tx) => {
    const m = await tx.match.create({
      data: {
        seasonId,
        winnerTeam,
        players: {
          create: [
            ...t1.map((id) => ({ playerId: id, team: 1 })),
            ...t2.map((id) => ({ playerId: id, team: 2 })),
          ],
        },
      },
    })

    // Update stats for each player
    const allPlayers = [...t1.map((id) => ({ id, team: 1 })), ...t2.map((id) => ({ id, team: 2 }))]
    for (const { id, team } of allPlayers) {
      const won = team === winnerTeam
      await tx.playerStat.upsert({
        where: { playerId_seasonId: { playerId: id, seasonId } },
        create: {
          playerId: id,
          seasonId,
          wins: won ? 1 : 0,
          losses: won ? 0 : 1,
        },
        update: {
          wins: won ? { increment: 1 } : undefined,
          losses: won ? undefined : { increment: 1 },
        },
      })
    }

    return m
  })

  return Response.json(match, { status: 201 })
}
