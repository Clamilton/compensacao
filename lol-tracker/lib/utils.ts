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

export function getTier(rank: number, total: number): TierInfo {
  if (rank === 1) {
    return { name: 'O MELHOR', bgClass: 'bg-amber-400', textClass: 'text-amber-950' }
  }
  const pct = rank / total
  if (pct <= 0.22) {
    return { name: 'BOM TRABALHO', bgClass: 'bg-green-300', textClass: 'text-green-950' }
  }
  if (pct <= 0.44) {
    return { name: 'FEZ O BASICO', bgClass: 'bg-green-500', textClass: 'text-white' }
  }
  if (pct <= 0.74) {
    return { name: 'EMPENA LOBBY', bgClass: 'bg-orange-100', textClass: 'text-orange-950' }
  }
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
  if (players.length < 2) {
    return { team1: players, team2: [], diff: 0 }
  }

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
      if (diff < bestDiff) {
        bestDiff = diff
        bestTeam1 = team1
        bestTeam2 = team2
      }
    }
    return { team1: bestTeam1, team2: bestTeam2, diff: bestDiff }
  }

  // Greedy for larger groups
  const sorted = [...players].sort((a, b) => b.winRate - a.winRate)
  const team1: PlayerBalance[] = []
  const team2: PlayerBalance[] = []
  for (const player of sorted) {
    const sum1 = team1.reduce((s, p) => s + p.winRate, 0)
    const sum2 = team2.reduce((s, p) => s + p.winRate, 0)
    if (team1.length < half && (team2.length >= half || sum1 <= sum2)) {
      team1.push(player)
    } else {
      team2.push(player)
    }
  }
  const avg1 = team1.reduce((s, p) => s + p.winRate, 0) / (team1.length || 1)
  const avg2 = team2.reduce((s, p) => s + p.winRate, 0) / (team2.length || 1)
  return { team1, team2, diff: Math.abs(avg1 - avg2) }
}

function combinations<T>(arr: T[], k: number): T[][] {
  if (k === 0) return [[]]
  if (arr.length === 0 || k > arr.length) return []
  const [first, ...rest] = arr
  return [
    ...combinations(rest, k - 1).map((c) => [first, ...c]),
    ...combinations(rest, k),
  ]
}
