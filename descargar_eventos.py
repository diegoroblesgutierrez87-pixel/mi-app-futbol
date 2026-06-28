import requests
import json
import time

API_KEY = "22ed42b619cb4a6959314ab3c93d9cb1"  # ← Mete tu key de api-football.com
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {'x-apisports-key': API_KEY}

LEAGUES = {
    'SP1': 140,  # La Liga
    'E0': 39,    # Premier League
    'D1': 78,    # Bundesliga
    'F1': 61,    # Ligue 1
    'I1': 135,   # Serie A
}

def get_fixtures(league_id, season):
    url = f"{BASE_URL}/fixtures"
    params = {'league': league_id, 'season': season}
    r = requests.get(url, headers=HEADERS, params=params)
    r.raise_for_status()
    return r.json()['response']

def get_events(fixture_id):
    url = f"{BASE_URL}/fixtures/events"
    params = {'fixture': fixture_id}
    r = requests.get(url, headers=HEADERS, params=params)
    r.raise_for_status()
    return r.json()['response']

def descargar_liga_completa(league_code, season):
    if league_code not in LEAGUES:
        print(f"Liga {league_code} no mapeada")
        return []
    
    league_id = LEAGUES[league_code]
    print(f"\n=== Descargando {league_code} {season} ===")
    
    fixtures = get_fixtures(league_id, season)
    finished = [f for f in fixtures if f['fixture']['status']['short'] == 'FT']
    print(f"Partidos finalizados: {len(finished)}")
    
    if len(finished) == 0:
        print("No hay partidos finalizados aún")
        return []
    
    all_matches = []
    for i, fix in enumerate(finished):
        fid = fix['fixture']['id']
        events_raw = get_events(fid)
        
        events = []
        for ev in events_raw:
            if ev['type'] == 'Goal' and ev['detail'] != 'Missed Penalty':
                events.append({
                    "minute": ev['time']['elapsed'],
                    "extra": ev['time']['extra'],
                    "type": "Goal",
                    "team": "home" if ev['team']['id'] == fix['teams']['home']['id'] else "away",
                    "player": ev['player']['name'],
                    "assist": ev['assist']['name'] if ev.get('assist') else None,
                    "detail": ev['detail']
                })
        
        match_data = {
            "fixture_id": fid,
            "league": league_code,
            "season": season,
            "date": fix['fixture']['date'][:10],
            "home_team": fix['teams']['home']['name'],
            "away_team": fix['teams']['away']['name'],
            "home_goals": fix['goals']['home'],
            "away_goals": fix['goals']['away'],
            "events": events
        }
        all_matches.append(match_data)
        
        print(f"{i+1}/{len(finished)}: {match_data['home_team']} {match_data['home_goals']}-{match_data['away_goals']} {match_data['away_team']}")
        time.sleep(0.4)  # Rate limit de la API
    
    filename = f'eventos_{league_code}_{season}.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(all_matches, f, ensure_ascii=False, indent=2)
    
    print(f"Guardado: {filename} con {len(all_matches)} partidos")
    return all_matches

if __name__ == "__main__":
    descargar_liga_completa('SP1', 2024) 
    # descargar_liga_completa('E0', 2025)  # Descomenta si quieres Premier