"""
actualizar_2627_v3.py - VERSION COMPLETA JORNADA A JORNADA
Baja: resultado + minuto gol + goleador + asistencia + pases + paradas + tiros 1P/2P/Total
Plan PRO 7500/dia - Incremental: solo pide stats de partidos NUEVOS
"""
import os, time, requests, pandas as pd, json
from datetime import datetime

try:
    import streamlit as st
    API_KEY = st.secrets.get("API_KEY", "9ad18f235fecc18540aa98b959b8f1c7")
except:
    API_KEY = os.environ.get("API_FOOTBALL_KEY", "9ad18f235fecc18540aa98b959b8f1c7")

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
SEASON = 2026

MAPA_TU_LIGA = {
    "Bundesliga": 78, "2. Bundesliga": 79, "Bundesliga - Femenina": 87,
    "Saudi Professional League": 307, "Primera División": 140, "Ligue 1": 61,
    "2. Liga": 207, "Premier League": 39, "Jupiler Pro League": 144,
    "Challenger Pro League": 145, "Copa": 143, "Superliga Femenina": 148,
    "Serie A Betano": 283, "Brasileirao Serie B": 85, "Superliga": 119,
    "League One": 41, "Cyprus League": 318, "K League 1": 292, "K League 2": 293,
    "UAE League": 301, "Presidents Cup": 302, "Premiership": 179, "Nike liga": 332,
    "LaLiga EA Sports": 140, "LaLiga Hypermotion": 141,
    "Primera Federación - Grupo 1": 435, "Primera Federación - Grupo 2": 436,
    "Supercopa": 556, "Liga F": 148, "Ligue 2": 62, "NB I.": 271,
    "Super League": 172, "Championship": 40, "President Cup": 302,
    "WSL": 44, "Ligat ha'Al": 383, "Serie A": 135, "Serie B": 136,
    "J1 League": 98, "J2 League": 99, "Super Liga": 286, "Botola Pro": 200,
    "Eliteserien": 103, "Eredivisie": 88, "Copa de Primera": 250,
    "Liga Portugal": 94, "Liga Portugal 2": 95, "Taça de Portugal": 139,
    "Thai League 1": 290, "Thai League 2": 291, "Süper Lig": 203, "1. Lig": 204,
    "V.League 1": 340,
}

def api_get(endpoint, params, req):
    if req[0] >= 7400:
        print(f"LIMITE 7400 alcanzado, parando. {req[0]}")
        return None
    time.sleep(0.30)  # 200/min seguro
    for intento in range(3):
        try:
            r = requests.get(f"{BASE_URL}/{endpoint}", headers=HEADERS, params=params, timeout=25)
            if r.status_code == 429:
                print("429 esperando 65s")
                time.sleep(65)
                continue
            r.raise_for_status()
            req[0] += 1
            print(f"  {endpoint} {params} -> {req[0]} usado, quedan {r.headers.get('x-ratelimit-requests-remaining')}")
            return r.json()
        except Exception as e:
            print(f"Error {endpoint} {params} intento {intento}: {e}")
            time.sleep(5)
    return None

def parse_stats(stats_response):
    """Convierte statistics API a dict HS,HST,HF,HC,HY,HR, Passes, Saves etc"""
    out = {}
    try:
        for team_stat in stats_response.get("response", []):
            team = team_stat["team"]["name"]
            is_home = team_stat["team"]["id"] == team_stat.get("team_home_id") or True # simplificado
            # La API no da home/away facil aqui, lo parseamos por posicion
            stats = {s["type"]: s["value"] for s in team_stat["statistics"]}
            # Mapeo
            # Ej: 'Total Shots', 'Shots on Goal', 'Fouls', 'Corner Kicks', 'Yellow Cards', 'Red Cards', 'Ball Possession', 'Total passes', 'Goalkeeper Saves'
            # Guardamos crudo
            out[team] = stats
        return out
    except Exception as e:
        print(f"parse_stats error {e}")
        return {}

def main():
    print(f"=== V3 COMPLETA {datetime.now()} ===")
    req = [0]

    # Cargar existentes
    df_partidos_old = pd.read_csv("partidos_2627_actual.csv", low_memory=False) if os.path.exists("partidos_2627_actual.csv") else pd.DataFrame()
    df_goles_old = pd.read_csv("goles_2627_actual.csv", low_memory=False) if os.path.exists("goles_2627_actual.csv") else pd.DataFrame()

    # Set de partidos ya con stats completos (para no repetir)
    partidos_con_stats = set()
    if not df_partidos_old.empty:
        # Consideramos que tiene stats si HS !=0
        if "HS" in df_partidos_old.columns:
            con_stats = df_partidos_old[df_partidos_old["HS"].fillna(0) != 0]
            partidos_con_stats = set(zip(con_stats["Date"].astype(str), con_stats["HomeTeam"], con_stats["AwayTeam"]))

    nuevos_partidos = []
    nuevos_goles = []

    for nombre_csv, id_liga in MAPA_TU_LIGA.items():
        print(f"\n>>> LIGA {nombre_csv} id={id_liga}")
        data_fixtures = api_get("fixtures", {"league": id_liga, "season": SEASON}, req)
        if not data_fixtures:
            continue
        for fx in data_fixtures.get("response", []):
            f = fx["fixture"]
            if f["status"]["short"] not in ["FT","AET","PEN"]:
                continue
            fixture_id = f["id"]
            date_str = f["date"][:10]
            home = fx["teams"]["home"]["name"].upper()
            away = fx["teams"]["away"]["name"].upper()
            key = (pd.to_datetime(date_str).strftime("%d/%m/%Y"), home, away)

            # Si ya lo tenemos con stats, solo asegúrate que está en lista, no vuelvas a pedir events
            ya_tiene_stats = key in partidos_con_stats

            # --- RESULTADO BASICO ---
            ft_h = fx["goals"]["home"] or 0
            ft_a = fx["goals"]["away"] or 0
            ht_h = fx["score"]["halftime"]["home"] or 0
            ht_a = fx["score"]["halftime"]["away"] or 0
            ftr = "H" if ft_h > ft_a else "A" if ft_a > ft_h else "D"

            # Base row, se enriquecerá con stats si hace falta
            row = {
                "Date": pd.to_datetime(date_str).strftime("%d/%m/%Y"),
                "League": nombre_csv,
                "Season": "2026/2027",
                "HomeTeam": home,
                "AwayTeam": away,
                "FTHG": ft_h, "FTAG": ft_a, "HTHG": ht_h, "HTAG": ht_a, "FTR": ftr,
                "B365H":0,"B365D":0,"B365A":0,
                "HS":0,"AS":0,"HST":0,"AST":0,"HF":0,"AF":0,"HC":0,"AC":0,"HY":0,"AY":0,"HR":0,"AR":0,
                "HomePasses":0,"AwayPasses":0,"HomeSaves":0,"AwaySaves":0
            }

            # Si ya tiene stats, no pidas nada mas
            if ya_tiene_stats:
                # Mantener el existente si ya lo teniamos
                continue

            # --- EVENTS: minuto, goleador, asistencia ---
            data_events = api_get("fixtures/events", {"fixture": fixture_id}, req)
            if data_events:
                for ev in data_events.get("response", []):
                    if ev["type"] == "Goal":
                        minuto = ev["time"]["elapsed"] or 0
                        extra = ev["time"]["extra"] or 0
                        if extra: minuto_str = f"{minuto}+{extra}"
                        else: minuto_str = str(minuto)
                        # 1P/2P/Total ya lo sabes por minuto
                        parte = "1P" if (ev["time"]["elapsed"] or 0) <=45 else "2P"
                        nuevos_goles.append({
                            "Date": row["Date"],
                            "League": nombre_csv,
                            "Season": "2026/2027",
                            "HomeTeam": home,
                            "AwayTeam": away,
                            "minuto": ev["time"]["elapsed"],
                            "minuto_str": minuto_str,
                            "parte": parte,
                            "goleador": ev["player"]["name"],
                            "asistente": ev["assist"]["name"] if ev["assist"]["name"] else "",
                            "equipo": ev["team"]["name"].upper(),
                            "tipo": ev["detail"],  # Normal Goal, Penalty, Own Goal
                            "fixture_id": fixture_id
                        })

            # --- STATISTICS: pases, paradas, tiros, faltas, corners, tarjetas ---
            data_stats = api_get("fixtures/statistics", {"fixture": fixture_id}, req)
            if data_stats:
                try:
                    resp = data_stats.get("response", [])
                    if len(resp) >=2:
                        # resp[0] = home, resp[1]= away (orden API)
                        for idx, team_data in enumerate(resp):
                            stats_dict = {s["type"]: s["value"] for s in team_data["statistics"] if s["value"] is not None}
                            is_home_team = idx==0
                            if is_home_team:
                                row["HS"] = stats_dict.get("Total Shots", 0) or 0
                                row["HST"] = stats_dict.get("Shots on Goal", 0) or 0
                                row["HF"] = stats_dict.get("Fouls", 0) or 0
                                row["HC"] = stats_dict.get("Corner Kicks", 0) or 0
                                row["HY"] = stats_dict.get("Yellow Cards", 0) or 0
                                row["HR"] = stats_dict.get("Red Cards", 0) or 0
                                row["HomePasses"] = stats_dict.get("Total passes", 0) or stats_dict.get("Total Passes", 0) or 0
                                row["HomeSaves"] = stats_dict.get("Goalkeeper Saves", 0) or 0
                            else:
                                row["AS"] = stats_dict.get("Total Shots", 0) or 0
                                row["AST"] = stats_dict.get("Shots on Goal", 0) or 0
                                row["AF"] = stats_dict.get("Fouls", 0) or 0
                                row["AC"] = stats_dict.get("Corner Kicks", 0) or 0
                                row["AY"] = stats_dict.get("Yellow Cards", 0) or 0
                                row["AR"] = stats_dict.get("Red Cards", 0) or 0
                                row["AwayPasses"] = stats_dict.get("Total passes", 0) or stats_dict.get("Total Passes", 0) or 0
                                row["AwaySaves"] = stats_dict.get("Goalkeeper Saves", 0) or 0
                except Exception as e:
                    print(f"Stats parse error fixture {fixture_id}: {e}")

            nuevos_partidos.append(row)

            # Si te acercas al limite, guarda y para
            if req[0] >= 7300:
                print("Casi limite, guardando y saliendo")
                break
        if req[0] >= 7300:
            break

    # Guardar
    if nuevos_partidos:
        df_new = pd.DataFrame(nuevos_partidos)
        df_all = pd.concat([df_partidos_old, df_new], ignore_index=True).drop_duplicates(subset=["Date","HomeTeam","AwayTeam","League"], keep="last")
        df_all.to_csv("partidos_2627_actual.csv", index=False)
        print(f"Guardado partidos_2627_actual.csv {len(df_all)} (+{len(df_new)} nuevos)")
    else:
        print("Sin partidos nuevos con stats")

    if nuevos_goles:
        df_goles_new = pd.DataFrame(nuevos_goles)
        df_goles_all = pd.concat([df_goles_old, df_goles_new], ignore_index=True).drop_duplicates(subset=["Date","HomeTeam","AwayTeam","goleador","minuto"], keep="last")
        df_goles_all.to_csv("goles_2627_actual.csv", index=False)
        print(f"Guardado goles_2627_actual.csv {len(df_goles_all)} goles (+{len(nuevos_goles)} nuevos)")
        # Para que tu cargar_eventos lo lea, también guarda copia como laliga_2425_goles.csv compatible si quieres
        # df_goles_all.to_csv("laliga_2425_goles.csv", index=False)

    print(f"FIN V3 - Total peticiones usadas: {req[0]} / 7500")

if __name__ == "__main__":
    main()
