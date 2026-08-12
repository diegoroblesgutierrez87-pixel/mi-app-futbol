"""
actualizar_2627.py - Actualizador 26/27 separado
Lee ligas_2122_a_2526.* y crea/actualiza partidos_2627_actual.csv
Respeta: 300 req/min y 7500 req/dia
Usa st.secrets["API_KEY"] si existe, si no variable API_KEY
"""
import os
import time
import requests
import pandas as pd
from datetime import datetime

try:
    import streamlit as st
    API_KEY = st.secrets.get("API_KEY", "9ad18f235fecc18540aa98b959b8f1c7")
except:
    API_KEY = os.environ.get("API_FOOTBALL_KEY", "9ad18f235fecc18540aa98b959b8f1c7")

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

# 20 LIGAS PRINCIPALES - IDs API-Football (ajusta si usas otros nombres)
# LaLiga=140, Premier=39, Bundesliga=78, Serie A=135, Ligue1=61
LIGAS_MAP = {
    # Nombre en tu CSV : {id, nombre api}
    "LaLiga": {"id": 140, "api_name": "La Liga"},
    "Premier League": {"id": 39, "api_name": "Premier League"},
    "Bundesliga": {"id": 78, "api_name": "Bundesliga"},
    "Serie A": {"id": 135, "api_name": "Serie A"},
    "Ligue 1": {"id": 61, "api_name": "Ligue 1"},
    "Eredivisie": {"id": 88, "api_name": "Eredivisie"},
    "Primeira Liga": {"id": 94, "api_name": "Primeira Liga"},
    "Jupiler Pro League": {"id": 144, "api_name": "Jupiler Pro League"},
    "Super Lig": {"id": 203, "api_name": "Super Lig"},
    "LaLiga2": {"id": 141, "api_name": "La Liga 2"},
    "Championship": {"id": 40, "api_name": "Championship"},
    "Bundesliga 2": {"id": 79, "api_name": "2. Bundesliga"},
    "Serie B": {"id": 136, "api_name": "Serie B"},
    "Ligue 2": {"id": 62, "api_name": "Ligue 2"},
    "Eredivisie2": {"id": 88, "api_name": "Eredivisie"}, # placeholder
    "Scottish Premiership": {"id": 179, "api_name": "Premiership"},
    "Super League": {"id": 172, "api_name": "Super League"},
    "Ekstraklasa": {"id": 106, "api_name": "Ekstraklasa"},
    "Eliteserien": {"id": 103, "api_name": "Eliteserien"},
    "Allsvenskan": {"id": 113, "api_name": "Allsvenskan"},
}

SEASON = 2026 # Temporada 2026/2027 en API-Football es 2026

def api_get(endpoint, params, req_count):
    if req_count[0] >= 7400:
        print(f"STOP limite diario casi alcanzado {req_count[0]}/7500")
        return None
    # 300/min -> 0.25s por req = 240/min seguro
    time.sleep(0.25)
    try:
        r = requests.get(f"{BASE_URL}/{endpoint}", headers=HEADERS, params=params, timeout=20)
        # control rate limit headers
        remaining = r.headers.get("x-ratelimit-requests-remaining")
        if remaining:
            print(f"Remaining: {remaining}")
        if r.status_code == 429:
            print("429 rate limit, esperando 60s")
            time.sleep(60)
            return api_get(endpoint, params, req_count)
        r.raise_for_status()
        req_count[0] += 1
        return r.json()
    except Exception as e:
        print(f"Error API {endpoint} {params}: {e}")
        return None

def fixtures_to_row(fixture, league_name_csv):
    """Convierte fixture API a fila compatible con tu CSV"""
    try:
        f = fixture["fixture"]
        l = fixture["league"]
        teams = fixture["teams"]
        goals = fixture["goals"]
        score = fixture["score"]

        date = f["date"][:10] # YYYY-MM-DD -> tu app lo pasa a datetime con dayfirst
        ht = score["halftime"]["home"] or 0
        at = score["halftime"]["away"] or 0
        ft_h = goals["home"]
        ft_a = goals["away"]

        # Solo guardamos finalizados
        if f["status"]["short"] not in ["FT","AET","PEN"]:
            if ft_h is None or ft_a is None:
                return None

        ftr = "H" if ft_h > ft_a else "A" if ft_a > ft_h else "D" if ft_h is not None else ""

        return {
            "Date": pd.to_datetime(date).strftime("%d/%m/%Y"),
            "League": league_name_csv,
            "Season": "2026/2027",
            "HomeTeam": teams["home"]["name"].upper(),
            "AwayTeam": teams["away"]["name"].upper(),
            "FTHG": ft_h or 0,
            "FTAG": ft_a or 0,
            "HTHG": ht,
            "HTAG": at,
            "FTR": ftr,
            "B365H": 0, "B365D": 0, "B365A": 0,
            "HS": 0, "AS": 0, "HST": 0, "AST": 0, "HF": 0, "AF": 0,
            "HC": 0, "AC": 0, "HY": 0, "AY": 0, "HR": 0, "AR": 0,
        }
    except Exception as e:
        print(f"Error parse fixture: {e}")
        return None

def main():
    print(f"=== Actualizador 26/27 {datetime.now()} Season {SEASON} ===")
    req_count = [0]

    # Cargar existente si hay
    if os.path.exists("partidos_2627_actual.csv"):
        df_existing = pd.read_csv("partidos_2627_actual.csv", low_memory=False)
        print(f"Existente: {len(df_existing)} partidos 26/27")
    else:
        df_existing = pd.DataFrame()

    all_new = []

    # Detectar que ligas pedir: solo las que estan en tu CSV base y en el MAP
    try:
        if os.path.exists("ligas_2122_a_2526.csv"):
            df_base = pd.read_csv("ligas_2122_a_2526.csv", usecols=["League"], low_memory=False)
            ligas_en_base = df_base["League"].unique().tolist()
        else:
            ligas_en_base = list(LIGAS_MAP.keys())
    except:
        ligas_en_base = list(LIGAS_MAP.keys())

    ligas_a_actualizar = [l for l in ligas_en_base if l in LIGAS_MAP][:20] # 20 para no pasar limite
    print(f"Ligas a actualizar: {ligas_a_actualizar} -> {len(ligas_a_actualizar)} req")

    for liga_csv in ligas_a_actualizar:
        cfg = LIGAS_MAP[liga_csv]
        print(f"\n-> {liga_csv} id={cfg['id']}")
        data = api_get("fixtures", {"league": cfg["id"], "season": SEASON}, req_count)
        if not data:
            continue
        fixtures = data.get("response", [])
        print(f"   {len(fixtures)} fixtures recibidos")
        for fx in fixtures:
            row = fixtures_to_row(fx, liga_csv)
            if row:
                all_new.append(row)

    if not all_new:
        print("Nada nuevo")
        return

    df_new = pd.DataFrame(all_new)
    print(f"Nuevos: {len(df_new)}")

    # Merge con existente evitando duplicados
    if not df_existing.empty:
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        df_combined = df_combined.drop_duplicates(subset=["Date","HomeTeam","AwayTeam","League"], keep="last")
    else:
        df_combined = df_new

    df_combined.to_csv("partidos_2627_actual.csv", index=False)
    print(f"Guardado partidos_2627_actual.csv: {len(df_combined)} filas - Peticiones usadas: {req_count[0]}")
    print("OK")

if __name__ == "__main__":
    main()
