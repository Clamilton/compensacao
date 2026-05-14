import { prisma } from '@/lib/prisma'

// Seed data from the spreadsheet (X5 - Season 3)
const PLAYERS_S3 = [
  { nick: 'GUI', wins: 35, losses: 16 },
  { nick: 'LUIZIM', wins: 29, losses: 18 },
  { nick: 'AMIRACLE', wins: 21, losses: 10 },
  { nick: 'LUCAS', wins: 17, losses: 8 },
  { nick: 'NEUNJ', wins: 35, losses: 36 },
  { nick: 'DEDELLAS', wins: 27, losses: 28 },
  { nick: 'DOM PEDRO', wins: 26, losses: 29 },
  { nick: 'BETA', wins: 18, losses: 18 },
  { nick: 'EVANDO', wins: 8, losses: 3 },
  { nick: 'MINIONLOL', wins: 13, losses: 12 },
  { nick: 'VITIMAGE', wins: 24, losses: 29 },
  { nick: 'PIABUG', wins: 9, losses: 7 },
  { nick: 'NICOLE', wins: 17, losses: 19 },
  { nick: 'DIGÃO', wins: 20, losses: 25 },
  { nick: 'FERDILANGO', wins: 17, losses: 21 },
  { nick: 'PEDRO DEBS', wins: 7, losses: 6 },
  { nick: 'SUB10', wins: 5, losses: 4 },
  { nick: 'ZAYON', wins: 4, losses: 3 },
  { nick: 'LIL', wins: 7, losses: 8 },
  { nick: 'HALIF', wins: 6, losses: 7 },
  { nick: 'ATARU', wins: 9, losses: 13 },
  { nick: 'HAGAN', wins: 15, losses: 22 },
  { nick: 'WINI', wins: 4, losses: 6 },
  { nick: 'ZEZAO', wins: 6, losses: 9 },
  { nick: 'CJ', wins: 2, losses: 3 },
  { nick: 'AILTIN NTC', wins: 7, losses: 11 },
  { nick: 'TESOCRUEL', wins: 8, losses: 14 },
]

export async function POST() {
  const existing = await prisma.season.findFirst({ where: { name: 'Season 3' } })
  if (existing) {
    return Response.json({ error: 'Season 3 já existe' }, { status: 409 })
  }

  await prisma.season.updateMany({ data: { active: false } })
  const season = await prisma.season.create({ data: { name: 'Season 3', active: true } })

  for (const p of PLAYERS_S3) {
    const player = await prisma.player.upsert({
      where: { nick: p.nick },
      create: { nick: p.nick },
      update: { active: true },
    })
    await prisma.playerStat.create({
      data: { playerId: player.id, seasonId: season.id, wins: p.wins, losses: p.losses },
    })
  }

  return Response.json({ ok: true, season })
}
