# update_patrones_0_0_80_90.py
# Genera Partidos-0-0-Hasta80-Gol80-90.csv desde base_partidos.csv + base_goles.csv
import pandas as pd, pathlib, re

def parse_minuto(s):
    m = re.match(r'(\d+)', str(s))
    return int(m.group(1)) if m else None

def cargar():
    bp = None
    bg = None
    for p in [pathlib.Path("base_partidos.csv"), pathlib.Path("/mnt/data/base_partidos.csv")]:
        if p.exists():
            bp = p
            break
    for p in [pathlib.Path("base_goles.csv"), pathlib.Path("/mnt/data/base_goles.csv")]:
        if p.exists():
            bg = p
            break
    if not bp or not bg:
        raise FileNotFoundError("No encuentro base_partidos.csv / base_goles.csv")
    print(f"Leyendo {bp} y {bg}")
    df_p = pd.read_csv(bp, on_bad_lines='skip')
    df_g = pd.read_csv(bg, on_bad_lines='skip')
    return df_p, df_g

def main():
    df_p, df_g = cargar()
    df_p['fid_str'] = df_p['fixture_id'].astype(str).str.split('.').str[0]
    df_p['Date'] = pd.to_datetime(df_p['Date'], dayfirst=True, errors='coerce')
    df_g['fid_str'] = df_g['fixture_id'].astype(str).str.split('.').str[0]
    df_g['min_parsed'] = df_g['minuto'].apply(parse_minuto)

    # fids con gol <80 y >=80
    early = set(df_g[df_g['min_parsed'] < 80]['fid_str'].unique())
    late_df = df_g[(df_g['min_parsed'] >= 80) & (df_g['min_parsed'] <= 90)].copy()
    late = set(late_df['fid_str'].unique())
    candidatos = late - early

    print(f"Early: {len(early)} Late: {len(late)} Candidatos 0-0 hasta 80 + gol 80-90: {len(candidatos)}")

    registros = []
    for fid in candidatos:
        goles_tarde = late_df[late_df['fid_str']==fid].sort_values('min_parsed')
        part = df_p[df_p['fid_str']==fid]
        if part.empty:
            continue
        part = part.iloc[0]
        registros.append({
            'fid': fid,
            'League': part['League'],
            'Season': part['Season'],
            'Date': part['Date'].strftime('%Y-%m-%d') if pd.notna(part['Date']) else '',
            'Home': part['HomeTeam'],
            'Away': part['AwayTeam'],
            'FTHG': int(part['FTHG']) if pd.notna(part['FTHG']) else '',
            'FTAG': int(part['FTAG']) if pd.notna(part['FTAG']) else '',
            'Jornada_Home': int(str(part.get('jornada_home','')).replace('J','')) if str(part.get('jornada_home','')).replace('J','').isdigit() else str(part.get('jornada_home','')).replace('J',''),
            'Jornada_Away': int(str(part.get('jornada_away','')).replace('J','')) if str(part.get('jornada_away','')).replace('J','').isdigit() else str(part.get('jornada_away','')).replace('J',''),
            'Jornada_Liga': part.get('jornada_num',''),
            'mins': goles_tarde['min_parsed'].tolist(),
            'gols_80_90': goles_tarde['min_parsed'].tolist(),
            'gols_80_90_plus': goles_tarde['minuto'].tolist(),
        })

    df_final = pd.DataFrame(registros)
    if df_final.empty:
        print("Vacio")
        return
    df_final['Date_dt'] = pd.to_datetime(df_final['Date'], errors='coerce')
    df_final = df_final.sort_values('Date_dt').drop(columns=['Date_dt'])

    # normaliza Jornada_Liga a Jx
    def norm_jl(x):
        s=str(x).strip()
        if s=='':
            return ''
        if s.upper().startswith('J'):
            return s.upper()
        if s.isdigit():
            return f"J{s}"
        return s
    df_final['Jornada_Liga'] = df_final['Jornada_Liga'].apply(norm_jl)

    # columnas finales
    cols = ['fid','League','Season','Date','Home','Away','FTHG','FTAG','Jornada_Home','Jornada_Away','Jornada_Liga','mins','gols_80_90','gols_80_90_plus']
    df_final = df_final[cols]

    out = pathlib.Path("Partidos-0-0-Hasta80-Gol80-90.csv")
    out2 = pathlib.Path("/mnt/data/Partidos-0-0-Hasta80-Gol80-90.csv")
    df_final.to_csv(out, index=False)
    try:
        df_final.to_csv(out2, index=False)
    except:
        pass
    print(f"Guardado {out} filas {len(df_final)}")
    print(df_final[df_final['League']=='2 BUNDESLIGA'].to_string())

if __name__ == "__main__":
    main()
