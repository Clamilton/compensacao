"""
X5 Tracker — LCU Agent
Monitora o cliente do LoL e envia resultados de partidas customizadas para o site.
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

CONFIG_FILE = Path(__file__).parent / "config.json"

DEFAULT_CONFIG = {
    "server_url": "https://veted.site",
    "admin_token": "",
    "poll_interval": 5,
}


def load_config() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return {**DEFAULT_CONFIG, **cfg}
    return DEFAULT_CONFIG.copy()


def save_config(cfg: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


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
    text = path.read_text(encoding="utf-8")
    parts = text.strip().split(":")
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
    if isinstance(data, str):
        return data
    return None


def get_eog_stats(session: requests.Session) -> dict | None:
    return lcu_get(session, "/lol-end-of-game/v1/eog-stats-block")


def parse_eog(eog: dict) -> dict | None:
    """Transforma o bloco EOG no formato esperado pela API do site."""
    game_type = eog.get("gameType", "")
    if game_type != "CUSTOM_GAME":
        print(f"  Ignorando — tipo de jogo: {game_type}")
        return None

    duration = eog.get("gameLength")  # segundos

    teams_raw = eog.get("teams", [])
    players = []

    for team_data in teams_raw:
        team_id = team_data.get("teamId", 100)
        team_num = 1 if team_id == 100 else 2
        won = team_data.get("win", "").lower() == "win"
        winner_team = team_num if won else (2 if team_num == 1 else 1)

        for p in team_data.get("players", []):
            stats = p.get("stats", {})
            cs = stats.get("minionsKilled", 0) + stats.get("neutralMinionsKilled", 0)
            players.append({
                "nick":        p.get("summonerName", ""),
                "team":        team_num,
                "champion":    p.get("championName", None),
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

    if not players:
        return None

    # winner_team foi sobrescrito na última iteração, mas precisamos definir certo
    winner_team = None
    for team_data in teams_raw:
        if team_data.get("win", "").lower() == "win":
            winner_team = 1 if team_data.get("teamId", 100) == 100 else 2
            break

    if winner_team is None:
        print("  Não foi possível determinar o time vencedor.")
        return None

    return {
        "winnerTeam": winner_team,
        "duration":   duration,
        "players":    players,
    }


def submit_match(cfg: dict, payload: dict) -> bool:
    url = cfg["server_url"].rstrip("/") + "/api/match/submit"
    body = {**payload, "token": cfg["admin_token"]}
    try:
        r = requests.post(url, json=body, timeout=10)
        data = r.json()
        if r.ok:
            print(f"  ✅ Partida registrada! matchId={data.get('matchId')}")
            if data.get("notFound"):
                print(f"  ⚠️  Jogadores não encontrados no banco: {data['notFound']}")
            return True
        else:
            print(f"  ❌ Erro da API: {data.get('error', r.text)}")
    except Exception as e:
        print(f"  ❌ Falha ao enviar: {e}")
    return False


def setup_wizard(cfg: dict) -> dict:
    print("=" * 50)
    print(" X5 Tracker — Configuração inicial")
    print("=" * 50)
    print()
    url = input(f"URL do site [{cfg['server_url']}]: ").strip()
    if url:
        cfg["server_url"] = url
    token = input("Senha admin: ").strip()
    if token:
        cfg["admin_token"] = token
    save_config(cfg)
    print("Configuração salva em config.json")
    print()
    return cfg


def main():
    cfg = load_config()

    if not cfg.get("admin_token"):
        cfg = setup_wizard(cfg)

    print("=" * 50)
    print(" X5 Tracker — LCU Agent")
    print(f" Servidor: {cfg['server_url']}")
    print("=" * 50)
    print()
    print("Aguardando o cliente do LoL...")

    session = None
    last_phase = None
    eog_sent = False

    while True:
        lockfile = find_lockfile()

        if lockfile is None:
            if session is not None:
                print("  Cliente fechado. Aguardando...")
                session = None
                last_phase = None
                eog_sent = False
            time.sleep(cfg["poll_interval"])
            continue

        if session is None:
            try:
                lf = parse_lockfile(lockfile)
                session = make_session(lf["port"], lf["password"])
                print("  ✅ Cliente do LoL detectado!")
            except Exception as e:
                print(f"  Erro ao conectar ao LCU: {e}")
                time.sleep(cfg["poll_interval"])
                continue

        phase = get_phase(session)

        if phase != last_phase:
            print(f"  Fase: {phase}")
            last_phase = phase
            if phase != "EndOfGame":
                eog_sent = False

        if phase == "EndOfGame" and not eog_sent:
            print("  Partida encerrada — coletando stats...")
            time.sleep(2)  # aguarda o servidor popular os dados

            eog = get_eog_stats(session)
            if eog:
                payload = parse_eog(eog)
                if payload:
                    print(f"  Enviando para {cfg['server_url']}...")
                    if submit_match(cfg, payload):
                        eog_sent = True
                    else:
                        print("  Tentando novamente em 10s...")
                        time.sleep(10)
                else:
                    eog_sent = True  # não é custom, marca como enviado para não repetir
            else:
                print("  EOG stats não disponíveis ainda, tentando novamente...")

        time.sleep(cfg["poll_interval"])


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAgente encerrado.")
        sys.exit(0)
