import { prisma } from '@/lib/prisma'

interface PlayerPayload {
  nick: string
  team: number
  champion?: string
  kills?: number
  deaths?: number
  assists?: number
  gold?: number
  damage?: number
  healing?: number
  wardsPlaced?: number
  wardsKilled?: number
  cs?: number
  visionScore?: number
}

export async function POST(request: Request) {
  const body = await request.json()
  const { token, winnerTeam, duration, players, gameId } = body as {
    token: string
    winnerTeam: number
    duration?: number
    gameId?: string
    players: PlayerPayload[]
  }

  if (token !== process.env.ADMIN_PASSWORD) {
    return Response.json({ error: 'Unauthorized' }, { status: 401 })
  }

  if (![1, 2].includes(winnerTeam) || !Array.isArray(players) || players.length === 0) {
    return Response.json({ error: 'Dados inválidos' }, { status: 400 })
  }

  // Deduplicate by LCU game ID — multiple agents may submit the same match
  if (gameId) {
    const existing = await prisma.match.findUnique({ where: { lcuGameId: gameId } })
    if (existing) return Response.json({ matchId: existing.id, duplicate: true }, { status: 200 })
  }

  const season = await prisma.season.findFirst({ where: { active: true } })
  if (!season) return Response.json({ error: 'Nenhuma season ativa' }, { status: 400 })

  // Match nicks case-insensitively
  const allPlayers = await prisma.player.findMany()
  const nickMap = new Map(allPlayers.map((p) => [p.nick.toLowerCase(), p]))

  const resolved: (PlayerPayload & { playerId: number })[] = []
  const notFound: string[] = []
  for (const p of players) {
    const dbPlayer = nickMap.get(p.nick.toLowerCase())
    if (dbPlayer) resolved.push({ ...p, playerId: dbPlayer.id })
    else notFound.push(p.nick)
  }

  if (resolved.length === 0) {
    return Response.json({ error: 'Nenhum jogador encontrado no banco', notFound }, { status: 400 })
  }

  const match = await prisma.$transaction(async (tx) => {
    const m = await tx.match.create({
      data: {
        seasonId:  season.id,
        winnerTeam,
        duration:  duration ?? null,
        source:    'lcu',
        lcuGameId: gameId ?? null,
        players: {
          create: resolved.map((p) => ({
            playerId:    p.playerId,
            team:        p.team,
            champion:    p.champion    ?? null,
            kills:       p.kills       ?? null,
            deaths:      p.deaths      ?? null,
            assists:     p.assists     ?? null,
            gold:        p.gold        ?? null,
            damage:      p.damage      ?? null,
            healing:     p.healing     ?? null,
            wardsPlaced: p.wardsPlaced ?? null,
            wardsKilled: p.wardsKilled ?? null,
            cs:          p.cs          ?? null,
            visionScore: p.visionScore ?? null,
          })),
        },
      },
    })

    for (const p of resolved) {
      const won = p.team === winnerTeam
      await tx.playerStat.upsert({
        where: { playerId_seasonId: { playerId: p.playerId, seasonId: season.id } },
        create: { playerId: p.playerId, seasonId: season.id, wins: won ? 1 : 0, losses: won ? 0 : 1 },
        update: {
          wins:   won ? { increment: 1 } : undefined,
          losses: won ? undefined : { increment: 1 },
        },
      })
    }

    return m
  })

  return Response.json({ matchId: match.id, notFound }, { status: 201 })
}
