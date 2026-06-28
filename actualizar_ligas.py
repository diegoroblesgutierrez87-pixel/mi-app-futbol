import pandas as pd
import requests
import time
import os
from io import StringIO

# --- CONFIG ---
TEMPORADA_COD = '2526'
TEMPORADA_STR = '2025/2026'
LIGAS = ['B1','D1','D2','E0','E1','E2','E3','EC','F1','F2','G1','I1','I2','N1','P1','SC0','SC1','SC2','SC3','SP1','SP2','T1']

BASE_URL = "https://www.football-data.co.uk/mmz4281"
OUTPUT_FILE = "ligas_2122_a_2526.csv"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def descargar(liga):
    url = f"{BASE_URL}/{TEMPORADA_COD}/{liga}.csv"
    try:
        print(f"Descargando {liga}...", end=" ")
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code == 404:
            print("no existe aun")
            return None
        r.raise_for_status()
        
        txt = r.text
        if not txt.lstrip().startswith('Div'):
            for i, line in enumerate(txt.splitlines()):
                if line.startswith('Div,'):
                    txt = "\n".join(txt.splitlines()[i:])
                    break
        
        df = pd.read_csv(StringIO(txt))
        # Asignamos las columnas directamente al crear el df
        df = df.assign(League=liga, Season=TEMPORADA_STR)
        print(f"OK - {len(df)} partidos")
        return df
    except Exception as e:
        print(f"error: {e}")
        return None

# 1. Carga lo que ya tienes
if os.path.exists(OUTPUT_FILE):
    df_base = pd.read_csv(OUTPUT_FILE, low_memory=False)
    print(f"Base cargada: {len(df_base)} partidos")
else:
    df_base = pd.DataFrame()
    print("No hay base previa, se creara nueva")

actualizados = 0
lista_nuevos = []

for liga in LIGAS:
    df_nuevo = descargar(liga)
    time.sleep(0.6)
    
    if df_nuevo is None or df_nuevo.empty:
        continue
    
    lista_nuevos.append(df_nuevo)
    actualizados += 1

# 2. Elimina versiones viejas de 25/26 y concatena todo de golpe
if lista_nuevos:
    df_nuevos_total = pd.concat(lista_nuevos, ignore_index=True)
    
    if not df_base.empty:
        # Borra toda la 25/26 vieja
        df_base = df_base[df_base['Season'] != TEMPORADA_STR]
        # Une con las nuevas
        df_base = pd.concat([df_base, df_nuevos_total], ignore_index=True, sort=False)
    else:
        df_base = df_nuevos_total

# 3. Quita duplicados reales
if not df_base.empty:
    df_base = df_base.drop_duplicates(
        subset=['Date','HomeTeam','AwayTeam','League'], 
        keep='last'
    )
    
    # Reordena columnas
    cols_principales = ['League','Season']
    otras = [c for c in df_base.columns if c not in cols_principales]
    df_base = df_base[cols_principales + otras]
    
    # Guardamos CSV
    df_base.to_csv(OUTPUT_FILE, index=False)
    # Guardamos Parquet - ESTO LO LEE TU APP
    df_base.to_parquet('ligas_2122_a_2526.parquet', index=False)

print(f"\nGuardado en {OUTPUT_FILE}")
print(f"Guardado tambien en .parquet")
print(f"Ligas actualizadas hoy: {actualizados}/22")
if not df_base.empty:
    df_2526 = df_base[df_base['Season'] == TEMPORADA_STR]
    print(f"Total partidos 25/26: {len(df_2526)}")
    print(f"Ligas presentes 25/26: {sorted(df_2526['League'].unique())}")

print("Actualizacion completada")