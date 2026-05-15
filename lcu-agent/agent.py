"""
X5 Tracker — LCU Agent
Abre e já funciona: detecta o fim de partidas customizadas e envia para veted.site.
"""

import json
import time
import base64
import os
import sys
import requests
import urllib3
from pathlib import Path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SERVER_URL  = "https://veted.site"
AGENT_TOKEN = "x5lcu2026"
POLL_INTERVAL = 5  # segundos


def find_lockfile() -> Path | None:
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Riot Games" / "League of Legends" / "lockfile",
        Path("C:/Riot Games/League of Legends/lockfile"),
        Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "Riot Games" / "League of Legends" / "lockfile",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def parse_lockfile(path: Path) -> dict:
    parts = path.read_text(encoding="utf-8").strip().split(":")
    return {"port": parts[2], "password": parts[3]}


def make_session(port: str, password: str) -> requests.Session:
    token = base64.b64encode(f"riot:{password}".encode()).decode()
    s = requests.Session()
    s.verify = False
    s.headers["Authorization"] = f"Basic {token}"
    s.headers["Accept"] = "application/json"
    s.base_url = f"https://127.0.0.1:{port}"
    return s


def lcu_get(session: requests.Session, path: str):
    try:
        r = session.get(f"{session.base_url}{path}", timeout=3)
        if r.ok:
            return r.json()
    except Exception:
        pass
    return None


def get_phase(session: requests.Session) -> str | None:
    data = lcu_get(session, "/lol-gameflow/v1/gameflow-phase")
    return data if isinstance(data, str) else None


def get_eog_stats(session: requests.Session) -> dict | None:
    return lcu_get(session, "/lol-end-of-game/v1/eog-stats-block")


def parse_eog(eog: dict) -> dict | None:
    if eog.get("gameType") != "CUSTOM_GAME":
        print(f"  Ignorando — tipo: {eog.get('gameType')}")
        return None

    game_id  = str(eog.get("gameId", ""))
    duration = eog.get("gameLength")

    winner_team = None
    players = []

    for team_data in eog.get("teams", []):
        team_num = 1 if team_data.get("teamId", 100) == 100 else 2
        if team_data.get("win", "").lower() == "win":
            winner_team = team_num

        for p in team_data.get("players", []):
            stats = p.get("stats", {})
            cs = stats.get("minionsKilled", 0) + stats.get("neutralMinionsKilled", 0)
            players.append({
                "nick":        p.get("summonerName", ""),
                "team":        team_num,
                "champion":    p.get("championName"),
                "kills":       stats.get("championsKilled", 0),
                "deaths":      stats.get("numDeaths", 0),
                "assists":     stats.get("assists", 0),
                "gold":        stats.get("goldEarned", 0),
                "damage":      stats.get("totalDamageDealtToChampions", 0),
                "healing":     stats.get("totalHeal", 0),
                "wardsPlaced": stats.get("wardsPlaced", 0),
                "wardsKilled": stats.get("wardsKilled", 0),
                "cs":          cs,
                "visionScore": stats.get("visionScore", 0),
            })

    if winner_team is None or not players:
        print("  Não foi possível determinar vencedor.")
        return None

    return {"gameId": game_id, "winnerTeam": winner_team, "duration": duration, "players": players}


def submit_match(payload: dict) -> bool:
    url = SERVER_URL.rstrip("/") + "/api/match/submit"
    try:
        r = requests.post(url, json={**payload, "token": AGENT_TOKEN}, timeout=10)
        data = r.json()
        if r.ok:
            if data.get("duplicate"):
                print(f"  ℹ️  Já registrada por outro agente (id={data.get('matchId')})")
            else:
                print(f"  ✅ Partida registrada! id={data.get('matchId')}")
            if data.get("notFound"):
                print(f"  ⚠️  Nicks não encontrados: {data['notFound']}")
            return True
        print(f"  ❌ Erro: {data.get('error', r.text)}")
    except Exception as e:
        print(f"  ❌ Falha ao enviar: {e}")
    return False


def main():
    print("=" * 45)
    print(" X5 Tracker — Agente LCU")
    print(f" Servidor: {SERVER_URL}")
    print("=" * 45)
    print("Aguardando o cliente do LoL...\n")

    session    = None
    last_phase = None
    eog_sent   = False

    while True:
        lockfile = find_lockfile()

        if lockfile is None:
            if session is not None:
                print("  Cliente fechado. Aguardando...")
                session    = None
                last_phase = None
                eog_sent   = False
            time.sleep(POLL_INTERVAL)
            continue

        if session is None:
            try:
                lf      = parse_lockfile(lockfile)
                session = make_session(lf["port"], lf["password"])
                print("  ✅ Cliente do LoL detectado!\n")
            except Exception as e:
                print(f"  Erro ao conectar: {e}")
                time.sleep(POLL_INTERVAL)
                continue

        phase = get_phase(session)

        if phase != last_phase:
            print(f"  Fase: {phase}")
            last_phase = phase
            if phase != "EndOfGame":
                eog_sent = False

        if phase == "EndOfGame" and not eog_sent:
            print("  Partida encerrada — coletando stats...")
            time.sleep(2)

            eog = get_eog_stats(session)
            if eog:
                payload = parse_eog(eog)
                if payload:
                    print(f"  Enviando para {SERVER_URL}...")
                    if submit_match(payload):
                        eog_sent = True
                    else:
                        print("  Tentando novamente em 10s...")
                        time.sleep(10)
                else:
                    eog_sent = True
            else:
                print("  Stats ainda não disponíveis, aguardando...")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAgente encerrado.")
        sys.exit(0)
