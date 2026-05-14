import { prisma } from '@/lib/prisma'
import { isAdmin } from '@/lib/auth'

export async function POST(request: Request, { params }: { params: Promise<{ id: string }> }) {
  if (!isAdmin(request)) return Response.json({ error: 'Unauthorized' }, { status: 401 })

  const { id } = await params
  await prisma.season.updateMany({ data: { active: false } })
  const season = await prisma.season.update({ where: { id: Number(id) }, data: { active: true } })

  return Response.json(season)
}
