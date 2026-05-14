import { prisma } from '@/lib/prisma'
import { isAdmin } from '@/lib/auth'

export async function GET() {
  const seasons = await prisma.season.findMany({ orderBy: { id: 'desc' } })
  return Response.json(seasons)
}

export async function POST(request: Request) {
  if (!isAdmin(request)) return Response.json({ error: 'Unauthorized' }, { status: 401 })

  const { name } = await request.json()
  if (!name?.trim()) return Response.json({ error: 'Nome inválido' }, { status: 400 })

  // Deactivate all seasons, then create new active one
  await prisma.season.updateMany({ data: { active: false } })
  const season = await prisma.season.create({ data: { name: name.trim(), active: true } })

  return Response.json(season, { status: 201 })
}
