export function calcPoints(wins: number, losses: number): number {
  return wins * 3 - losses * 2
}

export function calcWinRate(wins: number, losses: number): number {
  const total = wins + losses
  if (total === 0) return 50
  return (wins / total) * 100
}

export interface TierInfo {
  name: string
  bgClass: string
  textClass: string
}

export function getTier(winRate: number): TierInfo {
  if (winRate >= 65) return { name: 'O MELHOR', bgClass: 'bg-amber-400', textClass: 'text-amber-950' }
  if (winRate >= 55) return { name: 'BOM TRABALHO', bgClass: 'bg-green-300', textClass: 'text-green-950' }
  if (winRate >= 47) return { name: 'FEZ O BASICO', bgClass: 'bg-green-500', textClass: 'text-white' }
  if (winRate >= 41) return { name: 'EMPENA LOBBY', bgClass: 'bg-orange-100', textClass: 'text-orange-950' }
  return { name: 'SANGRIA', bgClass: 'bg-red-500', textClass: 'text-white' }
}

export interface PlayerBalance {
  id: number
  nick: string
  winRate: number
}

export function balanceTeams(players: PlayerBalance[]): {
  team1: PlayerBalance[]
  team2: PlayerBalance[]
  diff: number
} {
  if (players.length < 2) return { team1: players, team2: [], diff: 0 }

  const n = players.length
  const half = Math.floor(n / 2)

  if (n <= 12) {
    let bestDiff = Infinity
    let bestTeam1: PlayerBalance[] = []
    let bestTeam2: PlayerBalance[] = []
    for (const team1 of combinations(players, half)) {
      const ids = new Set(team1.map((p) => p.id))
      const team2 = players.filter((p) => !ids.has(p.id))
      const avg1 = team1.reduce((s, p) => s + p.winRate, 0) / team1.length
      const avg2 = team2.reduce((s, p) => s + p.winRate, 0) / team2.length
      const diff = Math.abs(avg1 - avg2)
      if (diff < bestDiff) { bestDiff = diff; bestTeam1 = team1; bestTeam2 = team2 }
    }
    return { team1: bestTeam1, team2: bestTeam2, diff: bestDiff }
  }

  const sorted = [...players].sort((a, b) => b.winRate - a.winRate)
  const team1: PlayerBalance[] = []
  const team2: PlayerBalance[] = []
  for (const player of sorted) {
    const sum1 = team1.reduce((s, p) => s + p.winRate, 0)
    const sum2 = team2.reduce((s, p) => s + p.winRate, 0)
    if (team1.length < half && (team2.length >= half || sum1 <= sum2)) team1.push(player)
    else team2.push(player)
  }
  const avg1 = team1.reduce((s, p) => s + p.winRate, 0) / (team1.length || 1)
  const avg2 = team2.reduce((s, p) => s + p.winRate, 0) / (team2.length || 1)
  return { team1, team2, diff: Math.abs(avg1 - avg2) }
}

function combinations<T>(arr: T[], k: number): T[][] {
  if (k === 0) return [[]]
  if (arr.length === 0 || k > arr.length) return []
  const [first, ...rest] = arr
  return [...combinations(rest, k - 1).map((c) => [first, ...c]), ...combinations(rest, k)]
}

// ── Badge system ─────────────────────────────────────────────────────────────

export const BADGE_DEFS: Record<string, { emoji: string; label: string; desc: string }> = {
  EXTERMINADOR: { emoji: '⚔️',  label: 'Exterminador', desc: 'Mais kills' },
  SUICIDA:      { emoji: '💀',  label: 'Suicida',       desc: 'Mais mortes' },
  ASSISTENTE:   { emoji: '🤝',  label: 'Assistente',    desc: 'Mais assistências' },
  CURANDEIRO:   { emoji: '💚',  label: 'Curandeiro',    desc: 'Mais cura' },
  DESTRUIDOR:   { emoji: '💥',  label: 'Destruidor',    desc: 'Mais dano' },
  SENTINELA:    { emoji: '👁️', label: 'Sentinela',     desc: 'Mais visão' },
  AVARENTO:     { emoji: '💰',  label: 'Avarento',      desc: 'Mais ouro' },
  FORMIGUINHA:  { emoji: '🐜',  label: 'Formiguinha',   desc: 'Mais CS' },
}

export interface MatchPlayerForBadge {
  playerId: number
  kills:       number | null
  deaths:      number | null
  assists:     number | null
  healing:     number | null
  damage:      number | null
  visionScore: number | null
  gold:        number | null
  cs:          number | null
}

export function computeBadges(players: MatchPlayerForBadge[]): Map<number, string[]> {
  const result = new Map<number, string[]>()
  players.forEach((p) => result.set(p.playerId, []))

  if (!players.some((p) => p.kills !== null)) return result

  const award = (
    key: keyof MatchPlayerForBadge,
    badge: string,
    mode: 'max' | 'min',
    threshold = 0,
  ) => {
    const vals = players
      .map((p) => ({ id: p.playerId, val: p[key] as number | null }))
      .filter((x): x is { id: number; val: number } => x.val !== null)
    if (vals.length === 0) return
    const extreme = mode === 'max' ? Math.max(...vals.map((v) => v.val)) : Math.min(...vals.map((v) => v.val))
    if (mode === 'max' && extreme < threshold) return
    vals.filter((v) => v.val === extreme).forEach((v) => result.get(v.id)?.push(badge))
  }

  award('kills',       'EXTERMINADOR', 'max', 1)
  award('deaths',      'SUICIDA',      'max', 1)
  award('assists',     'ASSISTENTE',   'max', 1)
  award('healing',     'CURANDEIRO',   'max', 500)
  award('damage',      'DESTRUIDOR',   'max', 1)
  award('visionScore', 'SENTINELA',    'max', 1)
  award('gold',        'AVARENTO',     'max', 1)
  award('cs',          'FORMIGUINHA',  'max', 1)

  return result
}
