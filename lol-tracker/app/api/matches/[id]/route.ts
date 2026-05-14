import { prisma } from '@/lib/prisma'
import { isAdmin } from '@/lib/auth'

export async function DELETE(request: Request, { params }: { params: Promise<{ id: string }> }) {
  if (!isAdmin(request)) return Response.json({ error: 'Unauthorized' }, { status: 401 })

  const { id } = await params
  const matchId = Number(id)

  const match = await prisma.match.findUnique({
    where: { id: matchId },
    include: { players: true },
  })

  if (!match) return Response.json({ error: 'Partida não encontrada' }, { status: 404 })

  await prisma.$transaction(async (tx) => {
    // Revert stats
    for (const mp of match.players) {
      const won = mp.team === match.winnerTeam
      await tx.playerStat.update({
        where: { playerId_seasonId: { playerId: mp.playerId, seasonId: match.seasonId } },
        data: {
          wins: won ? { decrement: 1 } : undefined,
          losses: won ? undefined : { decrement: 1 },
        },
      })
    }
    await tx.match.delete({ where: { id: matchId } })
  })

  return Response.json({ ok: true })
}
