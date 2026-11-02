# update_patrones_0_0_80_90.py
# Actualiza Partidos-0-0-Hasta80-Gol80-90.csv cada jornada
# Lee base_partidos.csv (+ resto si existe) y base_goles.csv (+ resto si existe)
# Genera columna Total_Jornada para resumen [x/total] leyendo solo 1 CSV

import pandas as pd, pathlib, re

def parse_minuto(s):
    m = re.match(r'(\d+)', str(s))
    return int(m.group(1)) if m else None

def load_csvs():
    # partidos: base + resto
    dfs_p = []
    for fp in [pathlib.Path("base_partidos.csv"), pathlib.Path("/mnt/data/base_partidos.csv"),
               pathlib.Path("base_partidos_resto_CORREGIDO.csv"), pathlib.Path("/mnt/data/base_partidos_resto_CORREGIDO.csv")]:
        if fp.exists():
            try:
                dfs_p.append(pd.read_csv(fp, on_bad_lines='skip'))
            except:
                pass
    if not dfs_p:
        raise FileNotFoundError("No encuentro base_partidos.csv")
    df_p = pd.concat(dfs_p, ignore_index=True)
    df_p['fid_str'] = df_p['fixture_id'].astype(str).str.split('.').str[0]
    df_p = df_p.drop_duplicates(subset=['fid_str'], keep='first')

    # goles: base + resto
    dfs_g = []
    for fp in [pathlib.Path("base_goles.csv"), pathlib.Path("/mnt/data/base_goles.csv"),
               pathlib.Path("base_goles_resto_CORREGIDO.csv"), pathlib.Path("/mnt/data/base_goles_resto_CORREGIDO.csv")]:
        if fp.exists():
            try:
                dfs_g.append(pd.read_csv(fp, on_bad_lines='skip'))
            except:
                pass
    if not dfs_g:
        raise FileNotFoundError("No encuentro base_goles.csv")
    df_g = pd.concat(dfs_g, ignore_index=True)
    df_g['fid_str'] = df_g['fixture_id'].astype(str).str.split('.').str[0]
    # no dedup goles, hay varios por partido

    return df_p, df_g

def main():
    df_p, df_g = load_csvs()
    print(f"Partidos cargados: {len(df_p)} | Goles cargados: {len(df_g)}")

    # parse fechas y minutos
    df_p['Date_dt'] = pd.to_datetime(df_p['Date'], dayfirst=True, errors='coerce')
    df_g['min_parsed'] = df_g['minuto'].apply(parse_minuto)

    # fids con gol <80 y 80-90
    early = set(df_g[df_g['min_parsed'] < 80]['fid_str'].unique())
    late_df = df_g[(df_g['min_parsed'] >= 80) & (df_g['min_parsed'] <= 90)].copy()
    late = set(late_df['fid_str'].unique())
    candidatos = late - early
    print(f"Early <80: {len(early)} | Late 80-90: {len(late)} | Candidatos 0-0 hasta 80 + gol 80-90: {len(candidatos)}")

    # totales por liga+jornada para Total_Jornada
    df_p['League'] = df_p['League'].astype(str).str.strip()
    df_p['jornada_num'] = df_p['jornada_num'].astype(str).str.strip().str.upper()
    df_p['jornada_num'] = df_p['jornada_num'].apply(lambda x: f"J{x.replace('J','')}" if x.replace('J','').isdigit() else x)
    totales = df_p.groupby(['League','jornada_num']).size().to_dict()

    def get_total(league, j_liga):
        j = str(j_liga).strip().upper()
        if j == '' or j == 'NAN':
            return 0
        if not j.startswith('J'):
            j = f"J{j}"
        return totales.get((str(league).strip(), j), 0)

    registros = []
    for fid in candidatos:
        goles_tarde = late_df[late_df['fid_str'] == fid].sort_values('min_parsed')
        part = df_p[df_p['fid_str'] == fid]
        if part.empty:
            continue
        part = part.iloc[0]
        j_liga = part.get('jornada_num','')
        # jornada_home/away como int si es posible
        def j_int(v):
            s=str(v).replace('J','').strip()
            return int(s) if s.isdigit() else s
        jh = j_int(part.get('jornada_home',''))
        ja = j_int(part.get('jornada_away',''))
        registros.append({
            'fid': fid,
            'League': part['League'],
            'Season': part['Season'],
            'Date': part['Date_dt'].strftime('%Y-%m-%d') if pd.notna(part['Date_dt']) else '',
            'Home': part['HomeTeam'],
            'Away': part['AwayTeam'],
            'FTHG': int(part['FTHG']) if pd.notna(part['FTHG']) else '',
            'FTAG': int(part['FTAG']) if pd.notna(part['FTAG']) else '',
            'Jornada_Home': jh,
            'Jornada_Away': ja,
            'Jornada_Liga': j_liga,
            'Total_Jornada': get_total(part['League'], j_liga),
            'mins': goles_tarde['min_parsed'].tolist(),
            'gols_80_90': goles_tarde['min_parsed'].tolist(),
            'gols_80_90_plus': goles_tarde['minuto'].tolist(),
        })

    df_final = pd.DataFrame(registros)
    if df_final.empty:
        print("Vacio, no hay partidos")
        return
    df_final['Date_dt'] = pd.to_datetime(df_final['Date'], errors='coerce')
    df_final = df_final.sort_values('Date_dt').drop(columns=['Date_dt'])

    cols = ['fid','League','Season','Date','Home','Away','FTHG','FTAG','Jornada_Home','Jornada_Away','Jornada_Liga','Total_Jornada','mins','gols_80_90','gols_80_90_plus']
    df_final = df_final[cols]

    out = pathlib.Path("Partidos-0-0-Hasta80-Gol80-90.csv")
    out2 = pathlib.Path("/mnt/data/Partidos-0-0-Hasta80-Gol80-90.csv")
    df_final.to_csv(out, index=False)
    try:
        df_final.to_csv(out2, index=False)
    except:
        pass

    print(f"Guardado {out} filas {len(df_final)} con Total_Jornada")
    # verificacion 2 Bundesliga
    check = df_final[df_final['League']=='2 BUNDESLIGA']
    if not check.empty:
        print(check[['fid','Jornada_Liga','Total_Jornada','mins']].to_string(index=False))

if __name__ == "__main__":
    main()
