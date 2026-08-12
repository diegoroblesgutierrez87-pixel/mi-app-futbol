"""
actualizar_2627.py - MAPA EXACTO USUARIO 26/27
Usa exactamente los nombres que tu CSV tiene
"""
import os, time, requests, pandas as pd
from datetime import datetime

try:
    import streamlit as st
    API_KEY = st.secrets.get("API_KEY", "9ad18f235fecc18540aa98b959b8f1c7")
except:
    API_KEY = os.environ.get("API_FOOTBALL_KEY", "9ad18f235fecc18540aa98b959b8f1c7")

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
SEASON = 2026

# TU LISTA EXACTA -> ID API-Football
# He quitado duplicados pero manteniendo tu nombre original como KEY
MAPA_TU_LIGA = {
    "Bundesliga": 78,
    "2. Bundesliga": 79,
    "Bundesliga - Femenina": 87,  # Frauen Bundesliga
    "Saudi Professional League": 307,
    "Primera División": 140,  # LaLiga EA Sports (tu Primera División)
    "Ligue 1": 61,
    "2. Liga": 207,  # Austria 2. Liga (si es Alemania 2. es 79, dime)
    "Premier League": 39,
    "Jupiler Pro League": 144,
    "Challenger Pro League": 145,
    "Copa": 143,  # Copa del Rey por defecto, cambia si es otra
    "Superliga Femenina": 148,  # Liga F antes Superliga Femenina
    "Serie A Betano": 283,  # Liga 1 Romania Betano (si es Brasil Betano es 71)
    "Brasileirao Serie B": 85,
    "Superliga": 119,  # Danesa por defecto, si es otra dime pais
    "League One": 41,
    "Cyprus League": 318,
    "K League 1": 292,
    "K League 2": 293,
    "UAE League": 301,
    "Presidents Cup": 302,  # UAE Presidents Cup
    "Premiership": 179,  # Scottish
    "Nike liga": 332,  # Eslovaca
    "LaLiga EA Sports": 140,
    "LaLiga Hypermotion": 141,
    "Primera Federación - Grupo 1": 435,
    "Primera Federación - Grupo 2": 436,
    "Supercopa": 556,  # Supercopa España
    "Liga F": 148,
    "Ligue 2": 62,
    "NB I.": 271,
    "Super League": 172,  # Suiza
    "Championship": 40,
    "President Cup": 302,
    "WSL": 44,  # Women Super League Inglaterra
    "Ligat ha'Al": 383,
    "Serie A": 135,
    "Serie B": 136,
    "J1 League": 98,
    "J2 League": 99,
    "Super Liga": 286,  # Serbia Super Liga
    "Botola Pro": 200,
    "Eliteserien": 103,
    "Eredivisie": 88,
    "Copa de Primera": 250,  # Paraguay
    "Liga Portugal": 94,
    "Liga Portugal 2": 95,
    "Taça de Portugal": 139,
    "Thai League 1": 290,
    "Thai League 2": 291,
    "Süper Lig": 203,
    "1. Lig": 204,
    "V.League 1": 340,
}

def api_get(params, req_count):
    if req_count[0] >= 7400:
        print("LIMITE DIARIO")
        return None
    time.sleep(0.25)
    try:
        r = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params=params, timeout=20)
        if r.status_code == 429:
            print("429 esperando 65s")
            time.sleep(65)
            return api_get(params, req_count)
        r.raise_for_status()
        req_count[0] += 1
        print(f"OK {params['league']} quedan {r.headers.get('x-ratelimit-requests-remaining')}")
        return r.json()
    except Exception as e:
        print(f"Error {params}: {e}")
        return None

def to_row(fx, nombre_csv):
    try:
        if fx["fixture"]["status"]["short"] not in ["FT","AET","PEN"]:
            return None
        ft_h = fx["goals"]["home"] or 0
        ft_a = fx["goals"]["away"] or 0
        ht_h = fx["score"]["halftime"]["home"] or 0
        ht_a = fx["score"]["halftime"]["away"] or 0
        date = fx["fixture"]["date"][:10]
        ftr = "H" if ft_h > ft_a else "A" if ft_a > ft_h else "D"
        return {
            "Date": pd.to_datetime(date).strftime("%d/%m/%Y"),
            "League": nombre_csv,
            "Season": "2026/2027",
            "HomeTeam": fx["teams"]["home"]["name"].upper(),
            "AwayTeam": fx["teams"]["away"]["name"].upper(),
            "FTHG": ft_h, "FTAG": ft_a, "HTHG": ht_h, "HTAG": ht_a, "FTR": ftr,
            "B365H":0,"B365D":0,"B365A":0,
            "HS":0,"AS":0,"HST":0,"AST":0,"HF":0,"AF":0,"HC":0,"AC":0,"HY":0,"AY":0,"HR":0,"AR":0
        }
    except:
        return None

def main():
    print(f"=== TODAS TUS LIGAS 26/27 {datetime.now()} ===")
    req = [0]
    if os.path.exists("partidos_2627_actual.csv"):
        df_old = pd.read_csv("partidos_2627_actual.csv", low_memory=False)
    else:
        df_old = pd.DataFrame()

    nuevos = []
    # Pide en orden de tu lista
    for nombre_csv, id_api in MAPA_TU_LIGA.items():
        print(f"-> {nombre_csv} [{id_api}]")
        data = api_get({"league": id_api, "season": SEASON}, req)
        if not data: continue
        for fx in data.get("response", []):
            r = to_row(fx, nombre_csv)
            if r: nuevos.append(r)

    if not nuevos:
        print("Sin finalizados aun - normal si no han empezado")
        if df_old.empty:
            pd.DataFrame(columns=["Date","League","Season","HomeTeam","AwayTeam","FTHG","FTAG","HTHG","HTAG","FTR"]).to_csv("partidos_2627_actual.csv", index=False)
        return

    df_new = pd.DataFrame(nuevos)
    df_all = pd.concat([df_old, df_new], ignore_index=True).drop_duplicates(subset=["Date","HomeTeam","AwayTeam","League"], keep="last")
    df_all.to_csv("partidos_2627_actual.csv", index=False)
    print(f"GUARDADO {len(df_all)} partidos - Peticiones {req[0]}")

if __name__ == "__main__":
    main()
