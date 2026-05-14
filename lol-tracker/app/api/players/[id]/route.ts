import { prisma } from '@/lib/prisma'
import { isAdmin } from '@/lib/auth'

export async function DELETE(request: Request, { params }: { params: Promise<{ id: string }> }) {
  if (!isAdmin(request)) return Response.json({ error: 'Unauthorized' }, { status: 401 })

  const { id } = await params
  await prisma.player.update({ where: { id: Number(id) }, data: { active: false } })
  return Response.json({ ok: true })
}
