import { prisma } from '@/lib/prisma'
import { isAdmin } from '@/lib/auth'

export async function GET() {
  const players = await prisma.player.findMany({
    where: { active: true },
    orderBy: { nick: 'asc' },
  })
  return Response.json(players)
}

export async function POST(request: Request) {
  if (!isAdmin(request)) return Response.json({ error: 'Unauthorized' }, { status: 401 })

  const { nick } = await request.json()
  if (!nick?.trim()) return Response.json({ error: 'Nick inválido' }, { status: 400 })

  const existing = await prisma.player.findUnique({ where: { nick: nick.trim().toUpperCase() } })
  if (existing) {
    if (!existing.active) {
      const updated = await prisma.player.update({
        where: { id: existing.id },
        data: { active: true },
      })
      return Response.json(updated, { status: 201 })
    }
    return Response.json({ error: 'Jogador já existe' }, { status: 409 })
  }

  const player = await prisma.player.create({ data: { nick: nick.trim().toUpperCase() } })
  return Response.json(player, { status: 201 })
}
