import requests
import json
import time
import os
import pandas as pd
from datetime import datetime

API_KEY = "22ed42b619cb4a6959314ab3c93d9cb1"
headers = {'x-apisports-key': API_KEY}

LEAGUE = 140 # LaLiga EA Sports
SEASON = 2024 # 2024/25
OUTPUT_JSON = "laliga_2425_COMPLETA.json"
OUTPUT_PARTIDOS = "laliga_2425_partidos.csv"
OUTPUT_GOLES = "laliga_2425_goles.csv"
PROGRESS = "progreso_2425.json"

MAX_CALLS_MIN = 10
MAX_CALLS_DIA = 100
SLEEP = 60 / MAX_CALLS_MIN # 6 segundos

# ---------- control de llamadas ----------
def cargar_progreso():
    hoy = datetime.now().strftime('%Y-%m-%d')
    if os.path.exists(PROGRESS):
        with open(PROGRESS, 'r', encoding='utf-8') as f:
            p = json.load(f)
        # resetea contador si es nuevo día
        if p.get('fecha')!= hoy:
            p['calls_hoy'] = 0
            p['fecha'] = hoy
        return p
    return {"partidos": [], "fixtures_hechos": [], "calls_hoy": 0, "fecha": hoy, "ultima_call": 0}

def guardar_progreso(p):
    with open(PROGRESS, 'w', encoding='utf-8') as f:
        json.dump(p, f)

progreso = cargar_progreso()
partidos_guardados = progreso['partidos']
fixtures_hechos = set(progreso['fixtures_hechos'])

def api_get(url, params):
    # control diario
    if progreso['calls_hoy'] >= MAX_CALLS_DIA:
        raise Exception("Límite diario alcanzado")

    # control por minuto
    ahora = time.time()
    espera = SLEEP - (ahora - progreso.get('ultima_call', 0))
    if espera > 0:
        time.sleep(espera)

    r = requests.get(url, headers=headers, params=params)
    progreso['calls_hoy'] += 1
    progreso['ultima_call'] = time.time()
    guardar_progreso(progreso)

    data = r.json()
    return data.get('response', [])

print(f"Reanudando... {len(partidos_guardados)}/380 | llamadas hoy: {progreso['calls_hoy']}/{MAX_CALLS_DIA}")

# ---------- 1. fixtures ----------
try:
    fixtures = api_get("https://v3.football.api-sports.io/fixtures", {'league': LEAGUE, 'season': SEASON})
except Exception as e:
    print(e); exit()

for f in fixtures:
    fid = f['fixture']['id']
    if fid in fixtures_hechos:
        continue
    if progreso['calls_hoy'] >= MAX_CALLS_DIA -1: # dejamos margen para 2 calls
        break

    print(f"[{len(partidos_guardados)+1}/380] {f['teams']['home']['name']} vs {f['teams']['away']['name']}")

    try:
        eventos = api_get("https://v3.football.api-sports.io/fixtures/events", {'fixture': fid})
        stats = api_get("https://v3.football.api-sports.io/fixtures/statistics", {'fixture': fid})
    except Exception as e:
        print(" Pausa diaria"); break

    # goles con parte
    goles = []
    for e in eventos:
        if e['type'] == 'Goal':
            minuto = e['time']['elapsed']
            parte = '1T' if minuto <= 45 else '2T'
            goles.append({
                "minuto": minuto,
                "parte": parte,
                "goleador": e['player']['name'],
                "asistente": e['assist']['name'] if e['assist']['name'] else ""
            })

    # stats mapeadas a tu CSV
    def get_stat(team_name, stat_name):
        for t in stats:
            if t['team']['name'] == team_name:
                for s in t['statistics']:
                    if s['type'] == stat_name:
                        return s['value']
        return 0

    home = f['teams']['home']['name']
    away = f['teams']['away']['name']

    partido = {
        "Date": f['fixture']['date'][:10],
        "League": "SP1", # <-- CAMBIADO para que coincida con tu Streamlit
        "Season": "2425",
        "HomeTeam": home,
        "AwayTeam": away,
        "FTHG": f['goals']['home'] or 0,
        "FTAG": f['goals']['away'] or 0,
        "FTR": "H" if f['goals']['home'] > f['goals']['away'] else "A" if f['goals']['away'] > f['goals']['home'] else "D",
        "HTHG": f['score']['halftime']['home'] or 0,
        "HTAG": f['score']['halftime']['away'] or 0,
        "HS": get_stat(home, "Total Shots") or 0,
        "AS": get_stat(away, "Total Shots") or 0,
        "HST": get_stat(home, "Shots on Goal") or 0,
        "AST": get_stat(away, "Shots on Goal") or 0,
        "HF": get_stat(home, "Fouls") or 0,
        "AF": get_stat(away, "Fouls") or 0,
        "HC": get_stat(home, "Corner Kicks") or 0,
        "AC": get_stat(away, "Corner Kicks") or 0,
        "HY": get_stat(home, "Yellow Cards") or 0,
        "AY": get_stat(away, "Yellow Cards") or 0,
        "HR": get_stat(home, "Red Cards") or 0,
        "AR": get_stat(away, "Red Cards") or 0,
        "Poss_H": str(get_stat(home, "Ball Possession")).replace('%',''),
        "Poss_A": str(get_stat(away, "Ball Possession")).replace('%',''),
        "Passes_H": get_stat(home, "Total passes") or 0,
        "Passes_A": get_stat(away, "Total passes") or 0,
        "goles_detalle": goles
    }

    partidos_guardados.append(partido)
    fixtures_hechos.add(fid)
    progreso['partidos'] = partidos_guardados
    progreso['fixtures_hechos'] = list(fixtures_hechos)
    guardar_progreso(progreso)

# ---------- 2. Guardar JSON y CSV ----------
with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(partidos_guardados, f, ensure_ascii=False, indent=2)

# CSV partidos (compatible con tu app)
df_partidos = pd.DataFrame(partidos_guardados).drop(columns=['goles_detalle'])
df_partidos.to_csv(OUTPUT_PARTIDOS, index=False, encoding='utf-8')

# CSV goles (goleador, minuto, asistente, parte)
goles_rows = []
for p in partidos_guardados:
    for g in p['goles_detalle']:
        goles_rows.append({
            "Date": p['Date'],
            "HomeTeam": p['HomeTeam'],
            "AwayTeam": p['AwayTeam'],
            "minuto": g['minuto'],
            "parte": g['parte'],
            "goleador": g['goleador'],
            "asistente": g['asistente']
        })
pd.DataFrame(goles_rows).to_csv(OUTPUT_GOLES, index=False, encoding='utf-8')

# ---------- 3. AUTO para Streamlit (NUEVO, no borra nada) ----------
try:
    eventos_streamlit = []
    for p in partidos_guardados:
        eventos_streamlit.append({
            "home_team": p["HomeTeam"],
            "away_team": p["AwayTeam"],
            "date": p["Date"],
            "events": [
                {"minute": g["minuto"], "player": g["goleador"], "assist": g["asistente"], "extra": None}
                for g in p["goles_detalle"]
            ]
        })
    # tu función cargar_eventos_json busca eventos_{liga}_{año}.json donde año = int(season[:4])
    anio = int(partidos_guardados[0]["Season"][:4]) if partidos_guardados else 2425
    eventos_path = f"eventos_SP1_{anio}.json"
    with open(eventos_path, 'w', encoding='utf-8') as f:
        json.dump(eventos_streamlit, f, ensure_ascii=False, indent=2)
    print(f"→ {eventos_path} generado para Streamlit")
except Exception as e:
    print(f"Aviso Streamlit: {e}")

print(f"\nGuardado: {len(partidos_guardados)}/380 partidos")
print(f"→ {OUTPUT_PARTIDOS} y {OUTPUT_GOLES} actualizados")
if len(partidos_guardados) == 380:
    os.remove(PROGRESS)
    print("✅ Temporada completa")
else:
    print(f"Llamadas hoy: {progreso['calls_hoy']}/{MAX_CALLS_DIA}. Ejecuta mañana, reanudará solo.")