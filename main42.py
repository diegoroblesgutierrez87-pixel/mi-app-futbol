import re
import unicodedata
import streamlit as st
import pandas as pd
import numpy as np
import os
import json
from datetime import datetime

def normaliza(nombre: str) -> str:
    # quita acentos, pasa a mayúsculas, limpia espacios
    n = unicodedata.normalize('NFKD', str(nombre))
    n = n.encode('ASCII', 'ignore').decode('ASCII')
    n = n.upper().strip()
    n = re.sub(r'\s+', ' ', n)
    return n

def abreviar_equipo(nombre):
    n = normaliza(nombre)
    mapa = {
        # Holanda
        'HERACLES ALMELO': 'HER', 'HERACLES': 'HER',
        'GRONINGEN': 'GRO', 'FC GRONINGEN': 'GRO',
        'TELSTAR': 'TEL', 'PEC ZWOLLE': 'ZWO', 'ZWOLLE': 'ZWO',
        'VOLENDAM': 'VOL', 'FC VOLENDAM': 'VOL',
        'AJAX': 'AJA', 'AFC AJAX': 'AJA', 'AZ ALKMAAR': 'AZ',
        'FEYENOORD': 'FEY', 'PSV EINDHOVEN': 'PSV', 'PSV': 'PSV',
        'TWENTE': 'TWE', 'FC TWENTE': 'TWE', 'UTRECHT': 'UTR',
        'HEERENVEEN': 'HEE', 'EXCELSIOR': 'EXC',
        # España - COMPLETO
        'ATLETICO MADRID': 'ATM', 'ATLETICO DE MADRID': 'ATM',
        'ATHLETIC BILBAO': 'ATH', 'ATHLETIC CLUB': 'ATH',
        'REAL MADRID': 'RMA', 'BARCELONA': 'FCB', 'FC BARCELONA': 'FCB',
        'BETIS': 'BET', 'REAL BETIS': 'BET', 'BETIS SEVILLA': 'BET',
        'SEVILLA': 'SEV', 'VALENCIA': 'VAL', 'VILLARREAL': 'VIL',
        'REAL SOCIEDAD': 'RSO', 'CELTA': 'CEL', 'CELTA VIGO': 'CEL',
        'OSASUNA': 'OSA', 'GETAFE': 'GET', 'ALAVES': 'ALA',
        'GIRONA': 'GIR', 'LAS PALMAS': 'LPA', 'MALLORCA': 'MAL',
        'RAYO VALLECANO': 'RAY', 'ESPANYOL': 'ESP', 'LEGANES': 'LEG',
        'VALLADOLID': 'VLL',
        # Inglaterra
        'MANCHESTER UNITED': 'MUN', 'MANCHESTER CITY': 'MCI',
        'ARSENAL': 'ARS', 'CHELSEA': 'CHE', 'LIVERPOOL': 'LIV',
        'TOTTENHAM': 'TOT',
        # Otros
        'PARIS SAINT GERMAIN': 'PSG', 'BAYERN MUNICH': 'BAY', 'BAYERN MUNCHEN': 'BAY',
    }
    if n in mapa:
        return mapa[n]
    for pref in ['FC ', 'AFC ', 'SC ', 'AC ', 'AS ', 'CF ', 'REAL ', 'CLUB ', 'DE ', 'LA ', 'UD ', 'SD ']:
        if n.startswith(pref):
            n = n[len(pref):]
    p = n.split()
    return (p[0][:3]).upper()

st.set_page_config(page_title="Filtro Jornada", layout="wide")
import streamlit.components.v1 as components

# anti-traductor
components.html("""<script>
const doc = window.parent.document;
doc.documentElement.setAttribute('translate','no');
</script>""", height=0)

# CSS LIMPIO - sin divs que rompan
# CSS LIMPIO - fondo blanco papel
st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"],
[data-testid="stHeader"], [data-testid="stToolbar"],
section[data-testid="stSidebar"] > div:first-child,
.block-container {
    background-color: #FFFFFF!important;
    color-scheme: light!important;
}
html, body { background: #FFFFFF!important; }

[data-testid="stDeployButton"],[data-testid="stToolbar"],#MainMenu,footer{display:none!important}
.block-container{padding:.5rem!important; background:#FFFFFF!important}

/* --- FILTROS 4x4 en móvil --- */
div[data-testid="stHorizontalBlock"]{
    display:flex!important;
    flex-wrap:wrap!important;
    gap:6px!important;
    padding-bottom:6px!important;
    overflow-x:hidden!important;
}
div[data-testid="stHorizontalBlock"]>div{
    flex:1 1 22%!important;
    min-width:80px!important;
    max-width:24%!important;
}
@media (min-width:769px){
  div[data-testid="stHorizontalBlock"]{
    flex-wrap:nowrap!important;
    overflow-x:auto!important;
  }
  div[data-testid="stHorizontalBlock"]>div{
    flex:0 0 auto!important;
    max-width:none!important;
  }
}

[data-testid="stWidgetLabel"] p{font-size:10px!important;margin:0!important;white-space:nowrap}
table{border-collapse:collapse;width:100%;font-size:9px;font-family:'Source Code Pro',monospace;table-layout:fixed;margin:0; background:#FFFFFF}
thead{display:none}
td{padding:3px 5px!important;border-bottom:2px solid #000!important;border-left:1px solid #d1d5db;border-right:1px solid #d1d5db;vertical-align:middle;line-height:1.15; background:#FFFFFF}
tr:nth-child(even){background:#FFFFFF}tr:hover{background:#f5f5f5}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def cargar_csv():
    import os
    import re
    # LEE PARQUET SI EXISTE, SI NO CSV (primera vez)
    if os.path.exists('ligas_2122_a_2526.parquet'):
        df = pd.read_parquet('ligas_2122_a_2526.parquet')
    else:
        df = pd.read_csv('ligas_2122_a_2526.csv', low_memory=False)

    if os.path.exists('laliga_2425_partidos.parquet'):
        df2 = pd.read_parquet('laliga_2425_partidos.parquet')
        df = pd.concat([df, df2], ignore_index=True)
    elif os.path.exists('laliga_2425_partidos.csv'):
        df2 = pd.read_csv('laliga_2425_partidos.csv', low_memory=False)
        df = pd.concat([df, df2], ignore_index=True)

    # 1) Fecha primero
    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
    df = df[df['Date'].notna()]

    # 2) Prioriza filas con cuota
    df['__tiene_cuota'] = df['B365H'].astype(str).str.strip().ne('') & df['B365H'].notna()
    df = df.sort_values('__tiene_cuota', ascending=False)
    df = df.drop_duplicates(subset=['Date','HomeTeam','AwayTeam','League'], keep='first')
    df = df.drop(columns='__tiene_cuota')

    for col in ['League', 'Season', 'HomeTeam', 'AwayTeam']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.replace('"', '').str.replace("'", "")

    # Normaliza espacios
    # después de leer df
    for col in ['HomeTeam','AwayTeam']:
        df[col] = df[col].astype(str).apply(normaliza)

    mapa_unifica = {
        'HERACLES ALMELO': 'HERACLES',
        'SC HERACLES ALMELO': 'HERACLES',
        'SC HERACLES': 'HERACLES',
        'FC GRONINGEN': 'GRONINGEN',
        'PEC ZWOLLE': 'ZWOLLE',
        'FC ZWOLLE': 'ZWOLLE',
        'FC VOLENDAM': 'VOLENDAM',
        'SC TELSTAR': 'TELSTAR',
        'AFC AJAX': 'AJAX',
        'AJAX AMSTERDAM': 'AJAX',
        'AZ ALKMAAR': 'AZ',
        'PSV EINDHOVEN': 'PSV',
        'FC TWENTE': 'TWENTE',
        'FC TWENTE ENSCHEDE': 'TWENTE',
        'FC UTRECHT': 'UTRECHT',
        'SC HEERENVEEN': 'HEERENVEEN',
        'SBV EXCELSIOR': 'EXCELSIOR',
        'VALLECANO': 'RAYO VALLECANO', # <--- AÑADE ESTA
        'RAYO VALLECANO MADRID': 'RAYO VALLECANO', # por si acaso
        'EXCELSIOR ROTTERDAM': 'EXCELSIOR',
        'ATLETICO DE MADRID': 'ATLETICO MADRID',
        'ATHLETIC CLUB': 'ATHLETIC BILBAO',
    }
    df['HomeTeam'] = df['HomeTeam'].replace(mapa_unifica)
    df['AwayTeam'] = df['AwayTeam'].replace(mapa_unifica)

    def norm_season(s):
        s = str(s)
        if re.match(r'^\d{4}/\d{4}$', s): return s
        if re.match(r'^\d{4}$', s): return f"20{s[:2]}/20{s[2:]}"
        return s
    df['Season'] = df['Season'].apply(norm_season)

    df = df[df['League'].notna() & (df['League']!='nan')]

    cols_num = ['FTHG','FTAG','HTHG','HTAG','HS','AS','HST','AST','HF','AF','HC','AC','HY','AY','HR','AR']
    for col in cols_num:
        df[col] = pd.to_numeric(df.get(col, 0), errors='coerce').fillna(0)

    if 'FTR' not in df.columns:
        df['FTR'] = np.where(df['FTHG'] > df['FTAG'], 'H', np.where(df['FTHG'] < df['FTAG'], 'A', 'D'))
    ############################################
    for col in ['B365H','B365D','B365A']:
        if col not in df.columns:
            df[col] = np.nan
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df['GolesTotales'] = df['FTHG'] + df['FTAG']
    df['GolesHT'] = df['HTHG'] + df['HTAG']

    # --- NUEVO: abreviaturas precacheadas ---
    df['HomeAbbr'] = df['HomeTeam'].apply(abreviar_equipo)
    df['AwayAbbr'] = df['AwayTeam'].apply(abreviar_equipo)
    ##################################################
    df['Goles2T'] = df['GolesTotales'] - df['GolesHT']
    df['corneTot'] = df['HC'] + df['AC']
    df['TargAmTot'] = df['HY'] + df['AY']
    df['tirosTot'] = df['HS'] + df['AS']
    df['tirosPuertaTot'] = df['HST'] + df['AST']
    df['faltasTot'] = df['HF'] + df['AF']
    df['TargRojTot'] = df['HR'] + df['AR']
    return df.copy()
@st.cache_data
def cargar_eventos(league, season):
    import os
    if os.path.exists('laliga_2425_goles.parquet'):
        df_g = pd.read_parquet('laliga_2425_goles.parquet')
    elif os.path.exists('laliga_2425_goles.csv'):
        df_g = pd.read_csv('laliga_2425_goles.csv', low_memory=False)
    else:
        return {}

    # --- MAPEO INTELIGENTE DE COLUMNAS ---
    cols = {c.lower(): c for c in df_g.columns}
    def get(col_options):
        for opt in col_options:
            if opt.lower() in cols: return cols[opt.lower()]
        return None

    col_date = get(['Date','Fecha','fecha'])
    col_home = get(['HomeTeam','Local','Equipo_Local','local'])
    col_away = get(['AwayTeam','Visitante','Equipo_Visitante','visitante'])
    col_min = get(['minuto','Minuto','minute','Minute'])
    col_gol = get(['goleador','Goleador','jugador','Jugador','player'])
    col_ast = get(['asistente','Asistente','assist'])
    col_tipo = get(['tipo','Tipo','type'])
    col_eq = get(['equipo','Equipo','team'])

    # renombra a estándar
    rename_map = {}
    if col_date: rename_map[col_date] = 'Date'
    if col_home: rename_map[col_home] = 'HomeTeam'
    if col_away: rename_map[col_away] = 'AwayTeam'
    if col_min: rename_map[col_min] = 'minuto'
    if col_gol: rename_map[col_gol] = 'goleador'
    if col_ast: rename_map[col_ast] = 'asistente'
    if col_tipo: rename_map[col_tipo] = 'tipo'
    if col_eq: rename_map[col_eq] = 'equipo'
    df_g = df_g.rename(columns=rename_map)

    # si faltan columnas clave, salimos
    for req in ['Date','HomeTeam','AwayTeam','minuto','goleador']:
        if req not in df_g.columns:
            st.error(f"Tu CSV no tiene columna '{req}'. Columnas encontradas: {list(df_g.columns)}")
            return {}

    # normaliza nombres equipos
    for col in ['HomeTeam','AwayTeam','equipo']:
        if col in df_g.columns:
            df_g[col] = df_g[col].apply(normaliza)

    # filtro opcional
    if 'League' in df_g.columns and 'Season' in df_g.columns:
        df_g = df_g[(df_g['League']==league) & (df_g['Season']==season)]

    df_g['Date'] = pd.to_datetime(df_g['Date'], dayfirst=True, errors='coerce')
    df_g = df_g.dropna(subset=['Date'])
    df_g['Date'] = df_g['Date'].dt.strftime('%Y-%m-%d')



    eventos_dict = {}
    for (ht, at, fecha), grupo in df_g.groupby(['HomeTeam','AwayTeam','Date']):
        evs = []
        for _, r in grupo.sort_values('minuto').iterrows():
            tipo = str(r.get('tipo','')).lower()
            evs.append({
                "minute": int(r['minuto']),
                "player": str(r['goleador']),
                "assist": str(r.get('asistente','')) if pd.notna(r.get('asistente')) else "",
                "extra": None,
                "penalty": 'pen' in tipo,
                "missed": 'penx' in tipo or tipo == 'x',
                "team": normaliza(str(r.get('equipo','')))
            })
        key = (ht, at, fecha) # ht y at ya están normalizados
        eventos_dict[key] = evs
    return eventos_dict
     

def buscar_goles_partido(row, eventos_dict, min_min=0, max_min=120, parte="Todo", equipo_filtro=None):
    if pd.isna(row['Date']):
        return ""
    key = (row['HomeTeam'], row['AwayTeam'], row['Date'].strftime('%Y-%m-%d'))
    evs = eventos_dict.get(key, [])
    if not evs:
        return ""

    hg = int(row['FTHG']); ag = int(row['FTAG'])
    ganador = row['HomeTeam'] if hg > ag else row['AwayTeam'] if ag > hg else None
    filtro_norm = normaliza(equipo_filtro) if equipo_filtro and equipo_filtro!= "Ninguno" else None

    txt = []
    for ev in evs:
        minuto = ev.get('minute', 0)
        if parte == "1T" and minuto > 45: continue
        if parte == "2T" and minuto <= 45: continue
        if not (min_min <= minuto <= max_min): continue

        team = ev.get('team','')
        if filtro_norm and team!= filtro_norm:
            continue

        if ev.get('penalty'):
            minuto_txt = f"{minuto}'(penX)" if ev.get('missed') else f"{minuto}'(pen)"
        else:
            minuto_txt = f"{minuto}'"

        gol_text = f"{minuto_txt} {ev.get('player','')}"
        if ev.get('assist') and not ev.get('missed'):
            gol_text += f" ({ev['assist']})"

        estilos = []
        if filtro_norm and team == filtro_norm:
            estilos.append("text-decoration:underline; text-decoration-thickness:2px")
        if ganador and team == ganador:
            estilos.append("font-weight:900")
        txt.append(f"<span style=\"{';'.join(estilos)}\">{gol_text}</span>" if estilos else gol_text)

    return " | ".join(txt)
###################formatear partido, visualizacion practicamente todo
def formatear_partido(row, equipo_filtro=None, cuota_tipo=None, goles_txt=""):
    ht, at = row['HomeTeam'], row['AwayTeam']
    ht_disp = row.get('HomeAbbr', abreviar_equipo(ht))
    at_disp = row.get('AwayAbbr', abreviar_equipo(at))
    league = row.get('League','')
    fecha = row['Date'].strftime('%d/%m/%y') if pd.notna(row['Date']) else ''
    jornada = f"J{int(row['Jornada'])}" if pd.notna(row.get('Jornada')) else ''
    hg_num, ag_num = int(row['FTHG']), int(row['FTAG'])
    hpts, apts = int(row['HomePtsPrev']), int(row['AwayPtsPrev'])
    hpos, apos = int(row['HomePosPrev']), int(row['AwayPosPrev'])
    hy, ay = int(row['HY']), int(row['AY']); hr, ar = int(row['HR']), int(row['AR'])
    hc, ac = int(row['HC']), int(row['AC']); hs, as_ = int(row['HS']), int(row['AS'])
    hst, ast = int(row['HST']), int(row['AST']); hf, af = int(row['HF']), int(row['AF'])
    hthg, htag = int(row['HTHG']), int(row['HTAG'])
    h2tg = hg_num - hthg; a2tg = ag_num - htag

    tot_a = hy + ay; tot_r = hr + ar; tot_c = hc + ac
    tot_g = hg_num + ag_num; tot_s = hs + as_; tot_f = hf + af

    NAVY = "#0A2342"
    style_base = f"color:{NAVY}; font-weight:600; font-size:9px; font-style:normal!important"
    style_ganador = f"color:{NAVY}; font-weight:900; font-size:9px; font-style:normal!important"
    style_subrayado = "text-decoration:underline; text-decoration-thickness:2px; font-style:normal!important"

    def color_stat(valor, tipo):
        if valor == 0: return ""
        return f"<span style='color:{NAVY}; font-weight:600; margin:0 3px; display:inline-block'>{valor}{tipo}</span>"
    totales_partes = [color_stat(tot_a,'A'),color_stat(tot_r,'R'),color_stat(tot_c,'C'),color_stat(tot_g,'G'),color_stat(tot_f,'F'),color_stat(tot_s,'S')]

    ht_res = ht_disp if hthg > htag else at_disp if hthg < htag else 'E'
    ft_res = ht_disp if hg_num > ag_num else at_disp if hg_num < ag_num else 'E'
    color_res = "#444"
    eq_norm = normaliza(equipo_filtro) if equipo_filtro and equipo_filtro != "Ninguno" else None
    if eq_norm:
        won = (eq_norm == ht and hg_num > ag_num) or (eq_norm == at and ag_num > hg_num)
        lost = (eq_norm == ht and hg_num < ag_num) or (eq_norm == at and ag_num < hg_num)
        color_res = "#0f8105" if won else "#f31818" if lost else "#f89007"

    # CUOTAS COMO ESTABAN
    cuota_h = row.get('B365H'); cuota_d = row.get('B365D'); cuota_a = row.get('B365A')
    league_short = str(league)[:3].upper()
    home_perf = round(float(row.get('HomePerf',0)),1); away_perf = round(float(row.get('AwayPerf',0)),1)

    hg_txt = f"<span style='{style_base}'>{hg_num}</span>"; ag_txt = f"<span style='{style_base}'>{ag_num}</span>"
    hpts_txt = f"<span style='{style_base}'>{hpts}</span>"; apts_txt = f"<span style='{style_base}'>{apts}</span>"
    hpos_txt = f"<span style='{style_base}'>{hpos}º</span>"; apos_txt = f"<span style='{style_base}'>{apos}º</span>"
    ht_txt = ht_disp; at_txt = at_disp
    home_perf_txt = f"<span style='{style_base}'>{home_perf:.1f}</span>"
    away_perf_txt = f"<span style='{style_base}'>{away_perf:.1f}</span>"

    if hg_num > ag_num:
        ht_txt = f"<span style='{style_ganador}'>{ht_disp}</span>"; hg_txt = f"<span style='{style_ganador}'>{hg_num}</span>"
        hpts_txt = f"<span style='{style_ganador}'>{hpts}</span>"; hpos_txt = f"<span style='{style_ganador}'>{hpos}º</span>"
        home_perf_txt = f"<span style='{style_ganador}'>{home_perf:.1f}</span>"
    elif ag_num > hg_num:
        at_txt = f"<span style='{style_ganador}'>{at_disp}</span>"; ag_txt = f"<span style='{style_ganador}'>{ag_num}</span>"
        apts_txt = f"<span style='{style_ganador}'>{apts}</span>"; apos_txt = f"<span style='{style_ganador}'>{apos}º</span>"
        away_perf_txt = f"<span style='{style_ganador}'>{away_perf:.1f}</span>"

    if eq_norm == ht:
        sty = f"{style_ganador if hg_num>ag_num else style_base}; {style_subrayado}"
        ht_txt = f"<span style='{sty}'>{ht_disp}</span>"; hg_txt = f"<span style='{sty}'>{hg_num}</span>"
        hpts_txt = f"<span style='{sty}'>{hpts}</span>"; hpos_txt = f"<span style='{sty}'>{hpos}º</span>"
        home_perf_txt = f"<span style='{sty}'>{home_perf:.1f}</span>"
    if eq_norm == at:
        sty = f"{style_ganador if ag_num>hg_num else style_base}; {style_subrayado}"
        at_txt = f"<span style='{sty}'>{at_disp}</span>"; ag_txt = f"<span style='{sty}'>{ag_num}</span>"
        apts_txt = f"<span style='{sty}'>{apts}</span>"; apos_txt = f"<span style='{sty}'>{apos}º</span>"
        away_perf_txt = f"<span style='{sty}'>{away_perf:.1f}</span>"

    # --- ESTRUCTURA EXACTA COMO LA FOTO ---
    top_line = f"<div style='font-size:9px'>{league_short} <span style='color:{color_res};font-weight:700'>{ht_res}/{ft_res}</span></div>"
    
    jornada_html = f"<span style='color:#0A2342;font-weight:700'>{jornada}</span>" if jornada else ""
    date_line = f"<div style='font-size:9px'>{fecha} |{jornada_html}|</div>"

    odds_html = ""
    if pd.notna(cuota_h) and pd.notna(cuota_d) and pd.notna(cuota_a):
        try:
            ftr = row.get('FTR', '')
            h_o = f"{float(cuota_h):.2f}"; d_o = f"{float(cuota_d):.2f}"; a_o = f"{float(cuota_a):.2f}"
            h_s = "font-weight:900; color:#000" if ftr == 'H' else "font-weight:600; color:#555"
            d_s = "font-weight:900; color:#000" if ftr == 'D' else "font-weight:600; color:#555"
            a_s = "font-weight:900; color:#000" if ftr == 'A' else "font-weight:600; color:#555"
            odds_html = f"<div style='font-size:9px'><span style='{h_s}'>{h_o}</span> <span style='{d_s}'>{d_o}</span> <span style='{a_s}'>{a_o}</span></div>"
        except: pass

    teams_line = f"<div style='font-size:9px'>{ht_txt} {hg_txt}-{ag_txt} {at_txt}</div>"
    pos_line = f"<div style='font-size:9px'>{hpos_txt} vs {apos_txt}</div>"
    pts_line = f"<div style='font-size:9px'>{hpts_txt}-pts {apts_txt}</div>"
    perf_line = f"<div style='font-size:9px'>Perf:{home_perf_txt}-{away_perf_txt}</div>"

    def wrap(v, win, fil): 
        s = style_ganador if win else style_base
        if fil: s += f"; {style_subrayado}"
        return f"<span style='{s}'>{v}</span>"

    h1 = f"1p:{wrap(f'{hthg}G', hg_num>ag_num, eq_norm==ht)}"
    a1 = f"1p:{wrap(f'{htag}G', ag_num>hg_num, eq_norm==at)}"
    h2 = f"2p:{wrap(f'{h2tg}G', hg_num>ag_num, eq_norm==ht)}"
    a2 = f"2p:{wrap(f'{a2tg}G', ag_num>hg_num, eq_norm==at)}"
    sh = wrap(f"{hs}T {hst}TP {hf}F {hc}C {hy}A {hr}R", hg_num>ag_num, eq_norm==ht)
    sa = wrap(f"{as_}T {ast}TP {af}F {ac}C {ay}A {ar}R", ag_num>hg_num, eq_norm==at)

    stats_html = f"<div style='font-size:7.5px'>{h1}</div><div style='font-size:7.5px'>{a1}</div><div style='font-size:7.5px'>{h2}</div><div style='font-size:7.5px'>{a2}</div><div style='font-size:7px'>{sh}</div><div style='font-size:7px'>{sa}</div>"
    
    goles_html = f"<div style='font-size:9px;color:{NAVY}'>{goles_txt}</div>" if goles_txt else ""
    return f'<div translate="no" style="border-bottom:2px solid #000; padding-bottom:4px; margin-bottom:6px">{top_line}{date_line}{odds_html}{teams_line}{pos_line}{pts_line}{perf_line}{stats_html}{goles_html}</div>'
####fin cuotas como estan
def formatear_h2h_compacto(row, equipo_ref=None):
    NAVY = "#0A2342"
    league = str(row.get('League',''))[:3].upper()
    fecha = row['Date'].strftime('%d/%m/%y') if pd.notna(row['Date']) else ''
    jorn = f"J{int(row['Jornada'])}"
    try:
        h_od = float(row['B365H']); d_od = float(row['B365D']); a_od = float(row['B365A']); ftr = row.get('FTR','')
        s_win = "font-weight:900; color:#000"; s_norm = "color:#555"
        odds = f"<span style='{s_win if ftr=='H' else s_norm}'>{h_od:.2f}</span> <span style='{s_win if ftr=='D' else s_norm}'>{d_od:.2f}</span> <span style='{s_win if ftr=='A' else s_norm}'>{a_od:.2f}</span>"
    except: odds = ""
    
    ht = row.get('HomeAbbr', abreviar_equipo(row['HomeTeam'])); at = row.get('AwayAbbr', abreviar_equipo(row['AwayTeam']))
    hg, ag = int(row['FTHG']), int(row['FTAG'])
    ###el R/R
    eq_norm = normaliza(equipo_ref) if equipo_ref else None
    is_h = eq_norm == row['HomeTeam']
    is_a = eq_norm == row['AwayTeam']
    
    def nv(t,b=False,u=False): 
        return f"<span style='color:{NAVY};font-weight:{900 if b else 600}{';text-decoration:underline;text-decoration-thickness:2px' if u else ''}'>{t}</span>"
    
    teams = f"{nv(ht,hg>ag,is_h)} {nv(hg,hg>ag,is_h)}-{nv(ag,ag>hg,is_a)} {nv(at,ag>hg,is_a)}"
    pos = f"{nv(f'{int(row['HomePosPrev'])}º',False,is_h)} <span style='color:#000'>vs</span> {nv(f'{int(row['AwayPosPrev'])}º',False,is_a)}"
    pts = f"{nv(int(row['HomePtsPrev']),False,is_h)}-<span style='color:#000'>pts</span> {nv(int(row['AwayPtsPrev']),False,is_a)}"
    
    ht_res = ht if int(row['HTHG'])>int(row['HTAG']) else at if int(row['HTHG'])<int(row['HTAG']) else 'E'
    ft_res = ht if hg>ag else at if ag>hg else 'E'
    if eq_norm:
        won = (is_h and hg > ag) or (is_a and ag > hg)
        lost = (is_h and hg < ag) or (is_a and ag < hg)
        color = "#0f8105" if won else "#f31818" if lost else "#f89007"
    else:
        color = "#444"
    res = f"<span style='color:{color};font-weight:700'>{ht_res}/{ft_res}</span>"
    ## R/R
    lineas = [
        f"{league} {res}",
        f"{fecha} |{jorn}|",
        odds,
        teams,
        pos,
        pts,
        f"<span style='color:#000'>Perf:</span>{nv(round(float(row.get('HomePerf',0)),1),hg>ag,is_h)}-{nv(round(float(row.get('AwayPerf',0)),1),ag>hg,is_a)}",
        f"1p:{nv(f'{int(row['HTHG'])}G',False,is_h)}",
        f"1p:{nv(f'{int(row['HTAG'])}G',False,is_a)}",
        f"2p:{nv(f'{hg-int(row['HTHG'])}G',False,is_h)}",
        f"2p:{nv(f'{ag-int(row['HTAG'])}G',False,is_a)}",
        nv(f"{int(row['HS'])}T {int(row['HST'])}TP {int(row['HF'])}F {int(row['HC'])}C {int(row['HY'])}A {int(row['HR'])}R",hg>ag,is_h),
        nv(f"{int(row['AS'])}T {int(row['AST'])}TP {int(row['AF'])}F {int(row['AC'])}C {int(row['AY'])}A {int(row['AR'])}R",ag>hg,is_a)
    ]
    
    # AQUÍ ESTÁ LA SEPARACIÓN QUE FALTABA
    return f"<div style='font-family:monospace; font-size:11px; line-height:1.15; padding:3px 2px; border-bottom:1px solid #ddd; white-space:nowrap'>{ '<br>'.join(lineas) }</div>"
###################FIN FORMATEAR_PARTIDO#################
def calcular_htft(row, equipo):
    if equipo == row['HomeTeam']:
        gf, gc = row['FTHG'], row['FTAG']
        htgf, htgc = row['HTHG'], row['HTAG']
    elif equipo == row['AwayTeam']:
        gf, gc = row['FTAG'], row['FTHG']
        htgf, htgc = row['HTAG'], row['HTHG']
    else:
        return None

    if htgf > htgc:
        res_ht = 'G'
    elif htgf < htgc:
        res_ht = 'P'
    else:
        res_ht = 'E'

    if gf > gc:
        res_ft = 'G'
    elif gf < gc:
        res_ft = 'P'
    else:
        res_ft = 'E'

    return f"{res_ht}/{res_ft}"

def crear_columna_tarjetas_corners(row, equipo_filtro=None):
    ht, at = row['HomeTeam'], row['AwayTeam']
    hy, ay = int(row['HY']), int(row['AY']); hr, ar = int(row['HR']), int(row['AR']); hc, ac = int(row['HC']), int(row['AC'])
    hthg, htag = int(row['HTHG']), int(row['HTAG']); fthg, ftag = int(row['FTHG']), int(row['FTAG'])
    h2tg = fthg - hthg; a2tg = ftag - htag
    style_subrayado = "text-decoration:underline; text-decoration-thickness:2px"
    def balon_con_numero(parte, goles):
        if goles == 0: return ""
        return f"<span style='display:inline-flex; align-items:center; margin-right:6px'><span style='margin-right:3px; font-size:9px; color:#555; font-weight:600'>{parte}</span><span style='display:inline-flex; align-items:center; justify-content:center; width:20px; height:20px; background:#000; color:#fff; border-radius:50%; font-size:11px; font-weight:900; border:2px solid #000'>{goles}</span></span>"
    def badge_equipo(eq, amarillas, rojas, corners, gol_ht, gol_2t, subrayar=False):
        badges = []
        if amarillas > 0: badges.append(f"<span style='display:inline-block; background:#fbbf24; color:#000; font-weight:700; font-size:11px; padding:0px 4px; border-radius:2px; margin:0 2px; min-width:14px; text-align:center; line-height:1.4'>{amarillas}</span>")
        if rojas > 0: badges.append(f"<span style='display:inline-block; background:#dc2626; color:#fff; font-weight:700; font-size:11px; padding:0px 4px; border-radius:2px; margin:0 2px; min-width:14px; text-align:center; line-height:1.4'>{rojas}</span>")
        if corners > 0: badges.append(f"<span style='margin-left:4px; margin-right:4px; font-size:11px; font-weight:600'>{corners} ⛳</span>")
        badges.append(balon_con_numero('1P', gol_ht)); badges.append(balon_con_numero('2P', gol_2t))
        badges = [b for b in badges if b]
        if badges:
            nombre_eq = f"<span style='{style_subrayado}'>{eq}</span>" if subrayar else f"<b>{eq}</b>"
            return f"<span style='font-size:11px'>{nombre_eq}: {' '.join(badges)}</span>"
        return ""
    h_badge = badge_equipo(abreviar_equipo(ht), hy, hr, hc, hthg, h2tg, equipo_filtro == ht)
    a_badge = badge_equipo(abreviar_equipo(at), ay, ar, ac, htag, a2tg, equipo_filtro == at)
    if h_badge and a_badge: return f"<div style='text-align:left; line-height:1.8'>{h_badge}<br>{a_badge}</div>"
    elif h_badge: return f"<div style='text-align:left'>{h_badge}</div>"
    elif a_badge: return f"<div style='text-align:left'>{a_badge}</div>"
    return ""
###############################FIN CREAR_COLUMNA_TARJETAS_CORNERS###############################
def resultado_ht_ft(row):
    if row['HTHG'] > row['HTAG']: res_ht = abreviar_equipo(row['HomeTeam'])
    elif row['HTHG'] < row['HTAG']: res_ht = abreviar_equipo(row['AwayTeam'])
    else: res_ht = 'E'
    if row['FTHG'] > row['FTAG']: res_ft = abreviar_equipo(row['HomeTeam'])
    elif row['FTHG'] < row['FTAG']: res_ft = abreviar_equipo(row['AwayTeam'])
    else: res_ft = 'E'
    return f"{res_ht}/{res_ft}"

################################# FIN RESULTADO_HT_FT#################################

@st.cache_data
def calcular_estado_jornada(df):
    df = df.sort_values(['League','Season','Date']).copy()

    # 1) Jornada
    for (l, s), g in df.groupby(['League','Season'], sort=False):
        equipos = pd.unique(g[['HomeTeam','AwayTeam']].values.ravel())
        ppj = max(len(equipos)//2, 1)
        df.loc[g.index, 'Jornada'] = (np.arange(len(g)) // ppj) + 1
    df['Jornada'] = df['Jornada'].astype(int)

    # 2) Puntos del partido
    df['HPts'] = np.where(df['FTR']=='H', 3, np.where(df['FTR']=='D', 1, 0))
    df['APts'] = np.where(df['FTR']=='A', 3, np.where(df['FTR']=='D', 1, 0))

    # 3) Puntos previos
    df['HomePtsPrev'] = df.groupby(['League','Season','HomeTeam'])['HPts']\
                        .transform(lambda x: x.cumsum().shift(fill_value=0))
    df['AwayPtsPrev'] = df.groupby(['League','Season','AwayTeam'])['APts']\
                        .transform(lambda x: x.cumsum().shift(fill_value=0))

    # 4) Posiciones previas con numpy
    home_pos = pd.Series(0, index=df.index, dtype=int)
    away_pos = pd.Series(0, index=df.index, dtype=int)
    tablas = []

    for (l, s), g in df.groupby(['League','Season'], sort=False):
        g = g.sort_values(['Jornada','Date'])
        teams = pd.unique(g[['HomeTeam','AwayTeam']].values.ravel())
        idx_map = {t:i for i, t in enumerate(teams)}
        n = len(teams)

        pts = np.zeros(n, dtype=int)
        gf = np.zeros(n, dtype=int)
        gc = np.zeros(n, dtype=int)
        pj = np.zeros(n, dtype=int)
        pg = np.zeros(n, dtype=int)
        pe = np.zeros(n, dtype=int)
        pp = np.zeros(n, dtype=int)

        last_jor = None

        for row in g.itertuples():
            hi = idx_map[row.HomeTeam]
            ai = idx_map[row.AwayTeam]

            if last_jor is not None and row.Jornada!= last_jor:
                snap = pd.DataFrame({
                    'Equipo': teams, 'Pts': pts, 'PJ': pj, 'PG': pg,
                    'PE': pe, 'PP': pp, 'GF': gf, 'GC': gc, 'DG': gf-gc
                })
                snap['Pos'] = snap['Pts'].rank(method='min', ascending=False).astype(int)
                snap = snap.sort_values(['Pts','DG','GF'], ascending=False)
                snap['Jornada'] = last_jor
                snap['League'] = l
                snap['Season'] = s
                tablas.append(snap)

            dg = gf - gc
            order = np.lexsort((-gf, -dg, -pts))
            ranks = np.empty(n, dtype=int)
            ranks[order] = np.arange(1, n+1)

            home_pos.at[row.Index] = ranks[hi]
            away_pos.at[row.Index] = ranks[ai]

            pj[hi] += 1; pj[ai] += 1
            gf[hi] += row.FTHG; gc[hi] += row.FTAG
            gf[ai] += row.FTAG; gc[ai] += row.FTHG

            if row.FTR == 'H':
                pts[hi] += 3; pg[hi] += 1; pp[ai] += 1
            elif row.FTR == 'A':
                pts[ai] += 3; pg[ai] += 1; pp[hi] += 1
            else:
                pts[hi] += 1; pts[ai] += 1; pe[hi] += 1; pe[ai] += 1

            last_jor = row.Jornada

        if last_jor is not None:
            snap = pd.DataFrame({
                'Equipo': teams, 'Pts': pts, 'PJ': pj, 'PG': pg,
                'PE': pe, 'PP': pp, 'GF': gf, 'GC': gc, 'DG': gf-gc
            })
            snap['Pos'] = snap['Pts'].rank(method='min', ascending=False).astype(int)
            snap = snap.sort_values(['Pts','DG','GF'], ascending=False)
            snap['Jornada'] = last_jor
            snap['League'] = l
            snap['Season'] = s
            tablas.append(snap)

    df['HomePosPrev'] = home_pos
    df['AwayPosPrev'] = away_pos
    df_clasificacion = pd.concat(tablas, ignore_index=True) if tablas else pd.DataFrame()

    # ResHtFt vectorizado - usa abreviaturas ya calculadas
    if 'HomeAbbr' in df.columns and 'AwayAbbr' in df.columns:
        abbr_map = {}
        abbr_map.update(dict(zip(df['HomeTeam'], df['HomeAbbr'])))
        abbr_map.update(dict(zip(df['AwayTeam'], df['AwayAbbr'])))
    else:
        abbr_map = {t: abreviar_equipo(t) for t in pd.unique(df[['HomeTeam','AwayTeam']].values.ravel())}
    ht_res = np.where(df['HTHG'] > df['HTAG'], df['HomeTeam'].map(abbr_map),
             np.where(df['HTHG'] < df['HTAG'], df['AwayTeam'].map(abbr_map), 'E'))
    ft_res = np.where(df['FTHG'] > df['FTAG'], df['HomeTeam'].map(abbr_map),
             np.where(df['FTHG'] < df['FTAG'], df['AwayTeam'].map(abbr_map), 'E'))
    df['ResHtFt'] = ht_res + '/' + ft_res

    # PUNTAJE RENDIMIENTO
    df['RivalProHome'] = df['AwayPosPrev'] <= 6
    df['RivalProAway'] = df['HomePosPrev'] <= 6
    df['HomePerf'] = np.where(df['FTR']=='H',1.5,np.where(df['FTR']=='D',0.5,0)) + 0.15*df['HST'] - 0.05*df['AST'] + 0.05*df['HC'] - 0.02*df['AC'] - 0.10*df['HY'] - 0.25*df['HR'] + 0.5*df['RivalProHome']*(df['FTR']=='H')
    df['AwayPerf'] = np.where(df['FTR']=='A',1.5,np.where(df['FTR']=='D',0.5,0)) + 0.15*df['AST'] - 0.05*df['HST'] + 0.05*df['AC'] - 0.02*df['HC'] - 0.10*df['AY'] - 0.25*df['AR'] + 0.5*df['RivalProAway']*(df['FTR']=='A')

    return df, df_clasificacion

   



#############filtro rachas



@st.cache_data
def _rachas(df_base, cond, loc, x_max=None):
    df = df_base.copy().sort_values('Date')

    # añadimos Jornada para poder mostrarla
    h = df[['Date','Season','Jornada','HomeTeam','AwayTeam','FTR']].copy()
    h['Equipo'] = h['HomeTeam']
    h['Res'] = h['FTR'].map({'H':'G','A':'P','D':'E'})
    h['Loc'] = 'Local'

    a = df[['Date','Season','Jornada','HomeTeam','AwayTeam','FTR']].copy()
    a['Equipo'] = a['AwayTeam']
    a['Res'] = a['FTR'].map({'A':'G','H':'P','D':'E'})
    a['Loc'] = 'Visitante'

    d = pd.concat([h, a], ignore_index=True)
    if loc in ['Local','Visitante']:
        d = d[d['Loc'] == loc]
    d = d.sort_values(['Equipo','Date'])

    mapa = {"G": {'G'}, "P": {'P'}, "E": {'E'}, "G/E": {'G','E'}, "E/P": {'E','P'}, "G/P": {'G','P'}}
    cs = {'G','P','E'} if cond == "Todo" else mapa[cond]

    out = []
    for eq, g in d.groupby('Equipo'):
        rachas = []; actual = []; temp_ant = None
        for _, r in g.iterrows():
            if temp_ant and r['Season']!= temp_ant:
                if actual: rachas.append(actual); actual = []
            temp_ant = r['Season']
            if r['Res'] in cs:
                actual.append(r)
            else:
                if actual: rachas.append(actual); actual = []
        if actual: rachas.append(actual)

        lens = [len(x) for x in rachas]
        max_seg = max(lens) if lens else 0
        total_ok = sum(1 for r in g['Res'] if r in cs)
        pct = round(100 * total_ok / len(g), 1) if len(g) else 0
        ult5 = ''.join(g['Res'].tail(5).tolist())

        if x_max:
            runs_x = [r for r in rachas if len(r) >= x_max]
            count_x = len(runs_x)
            # AQUÍ EL CAMBIO: JX-JY (x)
            jornadas_x = []
            for r in runs_x:
                ini = int(r[0]['Jornada']); fin = int(r[-1]['Jornada'])
                jornadas_x.append(f"J{ini}-J{fin} ({len(r)})")
            jornadas_str = ' | '.join(jornadas_x) if jornadas_x else "-"

            texto = f"{eq} | {len(g)}PJ | {max_seg} max | {count_x}# | {pct}% | {ult5} ↳ {jornadas_str}"
            out.append({'Equipo': texto, 'PJ': len(g), 'Max': max_seg, 'CountX': count_x, '%': pct})
        else:
            jornadas_ok = []
            for r in rachas:
                ini = int(r[0]['Jornada']); fin = int(r[-1]['Jornada'])
                jornadas_ok.append(f"J{ini}-J{fin}")
            jornadas_str = ', '.join(jornadas_ok)
            texto = f"{eq} | {len(g)}PJ | {max_seg} max | {pct}% | {ult5} ↳ {jornadas_str}"
            out.append({'Equipo': texto, 'PJ': len(g), 'Max': max_seg, '%': pct})

    return pd.DataFrame(out)


############fin filtro racchas

    


def limpiar_filtros():
    st.session_state.marcador_filtro = "Todos"
    st.session_state.columna_filtro = "Ninguno"
    st.session_state.operador_filtro = "="
    st.session_state.valor_filtro = "Ninguno"
    st.session_state.equipo_filtro = "Ninguno"
    st.session_state.resultado_filtro = "Ninguno"
    st.session_state.ambos_marcan = "Todos"
    st.session_state.equipo_clasificacion = "Ninguno"
    st.session_state.equipos_grafica = []
    st.session_state.condicion_filtro = "Todo"
    st.session_state.htft_filtro = "Todo"
    st.session_state.cuota_tipo = "Todo"
    st.session_state.cuota_operador = "Mayor o igual"
    st.session_state.rango_cuotas = (1.5, 10.0)
    st.session_state.jugador_filtro = "TODOS"
    st.session_state.rango_minutos = (0, 120)
    st.session_state.parte_gol = "Todo"
    st.session_state.alcance_filtro = "Todo"
    st.session_state.equipo2_filtro = "Ninguno"
    st.session_state.margen_filtro = "Todo"


df = cargar_csv()

# === AGENDA APUESTAS - HABITACIÓN NUEVA ===
AGENDA_FILE = 'agenda_apuestas.json'

def cargar_agenda():
    if os.path.exists(AGENDA_FILE):
        try:
            with open(AGENDA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return {"banca_inicial": 1000.0, "apuestas": data}
                return data
        except:
            return {"banca_inicial": 1000.0, "apuestas": []}
    return {"banca_inicial": 1000.0, "apuestas": []}

def guardar_agenda(data):
    with open(AGENDA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@st.fragment
def mostrar_agenda():
    with st.expander("🗓 Agenda Apuestas", expanded=False):
        agenda_data = cargar_agenda()
        banca_inicial = st.number_input("💰 Banca inicial €", 0.0, 1000000.0,
                                       float(agenda_data.get("banca_inicial", 1000)), 10.0,
                                       key="banca_ini_frag")
        agenda_data["banca_inicial"] = banca_inicial
        apuestas = agenda_data.get("apuestas", [])

        tab_live, tab_comb, tab_pre = st.tabs(["LIVE", "COMBINADA", "PREPARTIDO"])

        def form_apuesta(tipo_agenda):
            with st.form(f"form_{tipo_agenda}", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                equipos = sorted(pd.unique(df[['HomeTeam','AwayTeam']].values.ravel()))
                eq1 = c1.selectbox("Local", [""] + equipos, key=f"eq1_{tipo_agenda}")
                eq2 = c2.selectbox("Visitante", [""] + equipos, key=f"eq2_{tipo_agenda}")

                liga = ""
                if eq1 and eq2:
                    m = df[((df['HomeTeam']==eq1)&(df['AwayTeam']==eq2))|((df['HomeTeam']==eq2)&(df['AwayTeam']==eq1))]
                    if not m.empty:
                        liga = m.sort_values('Date', ascending=False).iloc[0]['League']
                ligas = [""] + sorted(df['League'].unique())
                liga = c3.selectbox("Liga", ligas, index=ligas.index(liga) if liga in ligas else 0, key=f"liga_{tipo_agenda}")

                c4, c5, c6 = st.columns(3)
                cuota = c4.number_input("Cuota", 1.01, 100.0, 1.90, 0.01, key=f"cuota_{tipo_agenda}")
                stake = c5.number_input("Stake", 0.0, 10000.0, 10.0, 0.5, key=f"stake_{tipo_agenda}")
                minuto = c6.number_input("Min", 0, 120, 0, key=f"min_{tipo_agenda}")

                c7, c8 = st.columns([1,2])
                tipo_apuesta = c7.selectbox("Tipo", ["Over","Under","Hándicap","1X2","BTTS","Corners","Otro"], key=f"tap_{tipo_agenda}")
                detalle = c8.text_input("Detalle (ej: 0.5 1ª)", "", key=f"det_{tipo_agenda}")
                marcador = st.text_input("Marcador", "0-0", key=f"marc_{tipo_agenda}")

                if st.form_submit_button("💾 Guardar PENDIENTE"):
                    if eq1 and eq2:
                        apuestas.append({
                            "id": int(datetime.now().timestamp()*1000),
                            "fecha": datetime.now().strftime("%d/%m %H:%M"),
                            "tipo": tipo_agenda,
                            "partido": f"{eq1} vs {eq2}",
                            "liga": liga,
                            "tipo_apuesta": tipo_apuesta,
                            "cuota": cuota,
                            "stake": stake,
                            "marcador": marcador,
                            "detalle": detalle,
                            "minuto": minuto,
                            "resultado": "Pendiente",
                            "beneficio": 0
                        })
                        agenda_data["apuestas"] = apuestas
                        guardar_agenda(agenda_data)

        with tab_live: form_apuesta("LIVE")
        with tab_comb: form_apuesta("COMBINADA")
        with tab_pre: form_apuesta("PREPARTIDO")

        if apuestas:
            df_ag = pd.DataFrame(apuestas)
            banca_actual = banca_inicial + df_ag['beneficio'].sum()

            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Banca", f"{banca_actual:.0f}€", f"{df_ag['beneficio'].sum():+.0f}€")
            c2.metric("Pend", len(df_ag[df_ag['resultado']=='Pendiente']))
            c3.metric("Ganadas", len(df_ag[df_ag['resultado']=='Ganada']))
            c4.metric("ROI", f"{df_ag['beneficio'].sum()/df_ag['stake'].sum()*100:.1f}%" if df_ag['stake'].sum()>0 else "0%")

            with st.expander("📊 Ver dónde tengo edge", expanded=False):
                df_analisis = df_ag[df_ag['resultado']!= 'Pendiente'].copy()
                f1,f2,f3,f4 = st.columns(4)
                ligas_f = f1.multiselect("Liga", df_analisis['liga'].dropna().unique())
                tipos_f = f2.multiselect("Tipo", df_analisis.get('tipo_apuesta', pd.Series()).dropna().unique())
                res_f = f3.multiselect("Resultado", ["Ganada","Perdida"], default=["Ganada","Perdida"])
                txt_f = f4.text_input("Detalle contiene", placeholder="over, 1ª, corner")
                if ligas_f: df_analisis = df_analisis[df_analisis['liga'].isin(ligas_f)]
                if tipos_f: df_analisis = df_analisis[df_analisis['tipo_apuesta'].isin(tipos_f)]
                if res_f: df_analisis = df_analisis[df_analisis['resultado'].isin(res_f)]
                if txt_f: df_analisis = df_analisis[df_analisis['detalle'].str.contains(txt_f, case=False, na=False)]
                if not df_analisis.empty:
                    tab1, tab2, tab3 = st.tabs(["Por Liga", "Por Tipo", "Por Equipo"])
                    with tab1:
                        liga_stats = df_analisis.groupby('liga').agg(Ap=('id','count'),W=('resultado', lambda x: (x=='Ganada').sum()),L=('resultado', lambda x: (x=='Perdida').sum()),Stake=('stake','sum'),Benef=('beneficio','sum')).reset_index()
                        liga_stats['Win%'] = (liga_stats['W']/liga_stats['Ap']*100).round(0).astype(int)
                        liga_stats['ROI%'] = (liga_stats['Benef']/liga_stats['Stake']*100).round(1)
                        st.dataframe(liga_stats.sort_values('ROI%', ascending=False), hide_index=True, use_container_width=True)
                    with tab2:
                        tipo_stats = df_analisis.groupby('tipo').agg(Ap=('id','count'),W=('resultado', lambda x: (x=='Ganada').sum()),Benef=('beneficio','sum'),Stake=('stake','sum')).reset_index()
                        tipo_stats['ROI%'] = (tipo_stats['Benef']/tipo_stats['Stake']*100).round(1)
                        st.dataframe(tipo_stats.sort_values('ROI%', ascending=False), hide_index=True, use_container_width=True)
                    with tab3:
                        df_analisis['equipo'] = df_analisis['partido'].str.split(' vs ').str[0]
                        equipo_stats = df_analisis.groupby('equipo').agg(Ap=('id','count'),W=('resultado', lambda x: (x=='Ganada').sum()),Benef=('beneficio','sum')).reset_index()
                        equipo_stats = equipo_stats[equipo_stats['Ap']>=2]
                        equipo_stats['Win%'] = (equipo_stats['W']/equipo_stats['Ap']*100).round(0).astype(int)
                        st.dataframe(equipo_stats.sort_values('Benef', ascending=False).head(10), hide_index=True, use_container_width=True)

            for ap in sorted(apuestas, key=lambda x: x['id'], reverse=True)[:50]:
                col1,col2,col3,col4 = st.columns([1.3,4.5,2.2,0.6])
                col1.caption(f"{ap['fecha']}")
                col2.write(f"**{ap['partido']}** {ap['marcador']} · **{ap.get('detalle','')}** · min {ap.get('minuto',0)}' · {ap.get('tipo','')}")
                col3.write(f"{ap['stake']}€ @ {ap['cuota']} → **{ap['resultado']}**")
                if col4.button("🗑", key=f"del_{ap['id']}"):
                    agenda_data["apuestas"] = [a for a in apuestas if a['id']!= ap['id']]
                    guardar_agenda(agenda_data)

            pend = [a for a in apuestas if a['resultado']=='Pendiente']
            if pend:
                st.divider()
                opciones = {a['id']: f"{a['fecha']} | {a['partido']} ({a['marcador']}) - {a['stake']}€ @ {a['cuota']}" for a in pend}
                sel_id = st.selectbox("Cerrar apuesta", options=list(opciones.keys()), format_func=lambda x: opciones[x], key="sel_cerrar")
                col_r1, col_r2 = st.columns([1,2])
                res = col_r1.radio("Resultado", ["Ganada","Perdida","Nula"], horizontal=True, key="res_radio")
                if col_r2.button("💾 Guardar resultado", use_container_width=True, key="btn_guardar"):
                    for a in apuestas:
                        if a['id'] == sel_id:
                            a['resultado'] = res
                            a['beneficio'] = round((a['cuota']-1)*a['stake'],2) if res=="Ganada" else -a['stake'] if res=="Perdida" else 0
                            break
                    agenda_data["apuestas"] = apuestas
                    guardar_agenda(agenda_data)

mostrar_agenda()

col1, col2, col3, col4 = st.columns(4)

ligas_disponibles = sorted(df['League'].unique())
temporadas_disponibles = sorted(df['Season'].unique())

st.caption(f"Ligas detectadas: {', '.join(ligas_disponibles)}")

liga_sel = col1.multiselect("Liga", ligas_disponibles, default=[], 
    format_func=lambda x: '\u2060'.join(x))  # rompe la palabra I2 para el traductor
temp_sel = col2.multiselect("Temporada", temporadas_disponibles, default=[])

if not liga_sel or not temp_sel:
    st.info("👆 Selecciona Liga y Temporada para ver partidos")
    st.stop()

modo_vista = col4.selectbox("Modo vista", ["Jornadas", "Clasificación"])

df_fil = df[df['League'].isin(liga_sel) & df['Season'].isin(temp_sel)]

if df_fil.empty:
    st.stop()

with st.spinner('Calculando clasificación...'):
    df_final, df_clasificacion = calcular_estado_jornada(df_fil)
    df_rachas_full = df_final.copy()   # <-- para el dashboard de rachas, con todas las jornadas

jornadas = sorted(df_final['Jornada'].unique())
jornada_sel = col3.multiselect("J", jornadas, format_func=lambda x: f"J{x}")

if len(jornadas) > 0:
    min_j, max_j = int(min(jornadas)), int(max(jornadas))
    rango_jornadas = st.slider("Rango de jornadas", min_value=min_j, max_value=max_j, value=(min_j, max_j))

    if not jornada_sel:
        df_final = df_final[(df_final['Jornada'] >= rango_jornadas[0]) & (df_final['Jornada'] <= rango_jornadas[1])]
        df_clasificacion = df_clasificacion[(df_clasificacion['Jornada'] >= rango_jornadas[0]) & (df_clasificacion['Jornada'] <= rango_jornadas[1])]
    else:
        df_final = df_final[df_final['Jornada'].isin(jornada_sel)]
        df_clasificacion = df_clasificacion[df_clasificacion['Jornada'].isin(jornada_sel)]



df_base_h2h = df_final.copy() # <-- AHORA SIEMPRE EXISTE
st.divider()

# --- CARGA EVENTOS PARA FILTRO JUGADOR ---
todos_eventos = {}
for liga in liga_sel:
    for temp in temp_sel:
        todos_eventos.update(cargar_eventos(liga, temp))

############# los desplegables
if modo_vista == "Jornadas":
    # --- inicializaciones (las dejas igual) ---
    if 'marcador_filtro' not in st.session_state: st.session_state.marcador_filtro = "Todos"
    if 'columna_filtro' not in st.session_state: st.session_state.columna_filtro = "Ninguno"
    if 'operador_filtro' not in st.session_state: st.session_state.operador_filtro = "="
    if 'valor_filtro' not in st.session_state: st.session_state.valor_filtro = "Ninguno"
    if 'equipo_filtro' not in st.session_state: st.session_state.equipo_filtro = "Ninguno"
    if 'resultado_filtro' not in st.session_state: st.session_state.resultado_filtro = "Ninguno"
    if 'ambos_marcan' not in st.session_state: st.session_state.ambos_marcan = "Todos"
    if 'condicion_filtro' not in st.session_state: st.session_state.condicion_filtro = "Todo"
    if 'htft_filtro' not in st.session_state: st.session_state.htft_filtro = "Todo"
    if 'jugador_filtro' not in st.session_state: st.session_state.jugador_filtro = "TODOS"
    if 'cuota_tipo' not in st.session_state: st.session_state.cuota_tipo = "Todo"
    if 'rango_cuotas' not in st.session_state: st.session_state.rango_cuotas = (1.5, 10.0)
    if 'rango_minutos' not in st.session_state: st.session_state.rango_minutos = (0, 120)
    if 'parte_gol' not in st.session_state: st.session_state.parte_gol = "Todo"
    if 'alcance_filtro' not in st.session_state: st.session_state.alcance_filtro = "Todo"
    if 'equipo2_filtro' not in st.session_state: st.session_state.equipo2_filtro = "Ninguno"  
    if 'margen_filtro' not in st.session_state: st.session_state.margen_filtro = "Todo" 
###columna numerica
    columnas_numericas = ['FTHG','FTAG','HTHG','HTAG','HS','AS','HST','AST','HF','AF','HC','AC','HY','AY','HR','AR','GolesTotales','GolesHT','Goles2T','corneTot','TargAmTot','tirosTot','tirosPuertaTot','faltasTot','TargRojTot','HomePtsPrev','AwayPtsPrev','HomePosPrev','AwayPosPrev','HomePerf','AwayPerf']
    ABREV_COL = {
        'FTHG': 'GL','FTAG': 'GV','HTHG': 'G1L','HTAG': 'G1V',
        'HS': 'TL','AS': 'TV','HST': 'TPL','AST': 'TPV',
        'HF': 'FL','AF': 'FV','HC': 'CL','AC': 'CV',
        'HY': 'AL','AY': 'AV','HR': 'RL','AR': 'RV',
        'GolesTotales': 'GT','GolesHT': 'GHT','Goles2T': 'G2T',
        'corneTot': 'CT','TargAmTot': 'TAM',
        'tirosTot': 'TT','tirosPuertaTot': 'TPT','faltasTot': 'FT','TargRojTot': 'TRT',
        'HomePtsPrev': 'PtL','AwayPtsPrev': 'PtV',
        'HomePosPrev': 'PosL','AwayPosPrev': 'PosV',
        'HomePerf': 'PfL','AwayPerf': 'PfV',
        'Ninguno': '—',
    }
    
    equipos_disponibles = sorted(pd.unique(df_final[['HomeTeam','AwayTeam']].values.ravel()))

    # FILA 1 - Eq1 Eq2 Col. Vlr L/V
# FILA 1 - 4 filtros
    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
    equipo_filtro = r1c1.selectbox("Eq1", ["Ninguno"] + equipos_disponibles, key='equipo_filtro')
    equipo2_filtro = r1c2.selectbox("Eq2", ["Ninguno"] + equipos_disponibles, key='equipo2_filtro')
    columna_filtro = r1c3.selectbox("Col.", ["Ninguno"] + columnas_numericas, format_func=lambda x: ABREV_COL.get(x, x), key='columna_filtro')
    operador_filtro = r1c4.selectbox("Op", ["=", ">", ">=", "<", "<="], key='operador_filtro')

    # FILA 2 - 4 filtros
    r2c1, r2c2, r2c3, r2c4 = st.columns(4)
    valor_filtro = r2c1.selectbox("Vlr", ["Ninguno"] + [i/2 for i in range(81)], key='valor_filtro')
    condicion_filtro = r2c2.selectbox("L/V", ["Todo", "Local", "Visitante"], key='condicion_filtro')
    alcance_filtro = r2c3.selectbox("F/C", ["Todo","AF","C","AF0","AF1","AF2","AF3","AF4","C0","C1","C2","C3","C4"], key='alcance_filtro', help="Todo=total | AF=a favor | C=en contra | AF0=0 goles | C0=0 encajados")
    htft_filtro = r2c4.selectbox("HT/FT", ["Todo","G/G","G/E","G/P","E/G","E/E","E/P","P/G","P/E","P/P","RE","FAIL"], key='htft_filtro')

    # FILA 3 - 4 filtros
    r3c1, r3c2, r3c3, r3c4 = st.columns(4)
    opciones_1x2 = ["Ninguno","Gana","Pierde","Empata","Gana/Empata","Gana/Pierde","Empata/Pierde"]
    mapa_1x2 = {"Ninguno":"-", "Gana":"G", "Pierde":"P", "Empata":"E", "Gana/Empata":"GE", "Gana/Pierde":"GP", "Empata/Pierde":"EP"}
    resultado_filtro = r3c1.selectbox("1x2", opciones_1x2, format_func=lambda x: mapa_1x2[x], key='resultado_filtro')
    ambos_marcan = r3c2.selectbox("AM", ["Todos","Sí","No"], key='ambos_marcan')
    cuota_tipo = r3c3.selectbox("R1x2", ["Ninguno","Todo","1","X","2"], key='cuota_tipo')
    ABREV_MARGEN = {"Todo":"—","Empate":"E","Gana 1":"G1","Gana 2":"G2","Gana 3+":"G3+","Pierde 1":"P1","Pierde 2":"P2","Pierde 3+":"P3+","Gana ≥2":"G2+","Pierde ≥2":"P2+"}
    margen_filtro = r3c4.selectbox("Margen", ["Todo","Empate","Gana 1","Gana 2","Gana 3+","Pierde 1","Pierde 2","Pierde 3+","Gana ≥2","Pierde ≥2"], format_func=lambda x: ABREV_MARGEN.get(x, x), key='margen_filtro')
        # --- NUEVO: Marcador exacto ---
    r3c1, r3c2 = st.columns([1, 4])
    # creamos la lista de marcadores únicos de los partidos YA filtrados por liga/temp/jornada
    marcadores_unicos = sorted(
        (df_final['FTHG'].astype(int).astype(str) + '-' + df_final['FTAG'].astype(int).astype(str)).unique(),
        key=lambda s: (int(s.split('-')[0]), int(s.split('-')[1]))
    )
    marcador_filtro = r3c1.selectbox("Marcador", ["Todos"] + marcadores_unicos, key='marcador_filtro')

    # --- lista de jugadores (esto faltaba) ---
    from collections import defaultdict, Counter
    player_teams = defaultdict(Counter)
    for (ht, at, fecha), evs in todos_eventos.items():
        for ev in evs:
            if ev.get('missed') or not ev.get('player'): continue
            team = ev.get('team')
            if team:
                player_teams[ev['player']][team] += 1
    player_to_team = {p: max(cnts.items(), key=lambda x: x[1])[0] for p, cnts in player_teams.items()} if player_teams else {}
    lista_jug = sorted([p for p,t in player_to_team.items() if t==equipo_filtro]) if equipo_filtro!="Ninguno" else sorted(player_to_team.keys())
    # FILA 3 - resto igual
    rango_cuotas = st.slider("Rango cuotas", 1.0, 40.0, st.session_state.rango_cuotas, 0.05, key='rango_cuotas')
    jugador_filtro = st.selectbox("Jugador", ["TODOS"] + lista_jug, key='jugador_filtro')
    
    st.button("Limpiar", on_click=limpiar_filtros, use_container_width=False)

    # FILA 4 - minutos
    rango_minutos = st.slider("Minutos", 0, 120, st.session_state.rango_minutos, 1, key='rango_minutos')
    parte_gol = st.selectbox("Parte", ["Todo","1T","2T"], key='parte_gol')
   
    # === FIN FILTRO GOLES ===

#     # === FIN FILTRO GOLES ===

    # === FILTRO F/C CON ATAJOS (respeta Parte) ===
    if equipo_filtro != "Ninguno" and alcance_filtro in ["AF0","AF1","AF2","AF3","AF4","C0","C1","C2","C3","C4"]:
        es_local = df_final['HomeTeam'] == equipo_filtro
        valor_atajo = int(alcance_filtro[-1])  # ya está arreglado

        if parte_gol == "1T":
            goles_favor = np.where(es_local, df_final['HTHG'], df_final['HTAG'])
            goles_contra = np.where(es_local, df_final['HTAG'], df_final['HTHG'])
        elif parte_gol == "2T":
            goles_favor = np.where(es_local, df_final['FTHG'] - df_final['HTHG'], df_final['FTAG'] - df_final['HTAG'])
            goles_contra = np.where(es_local, df_final['FTAG'] - df_final['HTAG'], df_final['FTHG'] - df_final['HTHG'])
        else:  # Todo = FT
            goles_favor = np.where(es_local, df_final['FTHG'], df_final['FTAG'])
            goles_contra = np.where(es_local, df_final['FTAG'], df_final['FTHG'])

        if alcance_filtro.startswith("AF"):
            df_final = df_final[goles_favor == valor_atajo]
        else:
            df_final = df_final[goles_contra == valor_atajo]

    # === FILTRO COLUMNA CON AF / C ===
    if columna_filtro != "Ninguno" and valor_filtro != "Ninguno":
        col_usar = columna_filtro

        if equipo_filtro != "Ninguno" and alcance_filtro in ["AF","C"]:
            es_local = df_final['HomeTeam'] == equipo_filtro

            if alcance_filtro == "AF":
                if columna_filtro == 'GolesTotales':
                    df_final['_val'] = np.where(es_local, df_final['FTHG'], df_final['FTAG'])
                elif columna_filtro == 'GolesHT':
                    df_final['_val'] = np.where(es_local, df_final['HTHG'], df_final['HTAG'])
                elif columna_filtro == 'Goles2T':
                    df_final['_val'] = np.where(es_local, df_final['FTHG'] - df_final['HTHG'], df_final['FTAG'] - df_final['HTAG'])
                else:
                    mapa = {'FTHG':'FTAG','FTAG':'FTHG','HTHG':'HTAG','HTAG':'HTHG','HS':'AS','AS':'HS','HST':'AST','AST':'HST','HF':'AF','AF':'HF','HC':'AC','AC':'HC','HY':'AY','AY':'HY','HR':'AR','AR':'HR','HomePtsPrev':'AwayPtsPrev','AwayPtsPrev':'HomePtsPrev','HomePosPrev':'AwayPosPrev','AwayPosPrev':'HomePosPrev','HomePerf':'AwayPerf','AwayPerf':'HomePerf'}
                    col_away = mapa.get(columna_filtro, columna_filtro)
                    df_final['_val'] = np.where(es_local, df_final[columna_filtro], df_final[col_away])
                col_usar = '_val'

            elif alcance_filtro == "C":
                if columna_filtro == 'GolesTotales':
                    df_final['_val'] = np.where(es_local, df_final['FTAG'], df_final['FTHG'])
                elif columna_filtro == 'GolesHT':
                    df_final['_val'] = np.where(es_local, df_final['HTAG'], df_final['HTHG'])
                elif columna_filtro == 'Goles2T':
                    df_final['_val'] = np.where(es_local, df_final['FTAG'] - df_final['HTAG'], df_final['FTHG'] - df_final['HTHG'])
                else:
                    mapa = {'FTHG':'FTAG','FTAG':'FTHG','HTHG':'HTAG','HTAG':'HTHG','HS':'AS','AS':'HS','HST':'AST','AST':'HST','HF':'AF','AF':'HF','HC':'AC','AC':'HC','HY':'AY','AY':'HY','HR':'AR','AR':'HR','HomePtsPrev':'AwayPtsPrev','AwayPtsPrev':'HomePtsPrev','HomePosPrev':'AwayPosPrev','AwayPosPrev':'HomePosPrev','HomePerf':'AwayPerf','AwayPerf':'HomePerf'}
                    col_away = mapa.get(columna_filtro, columna_filtro)
                    df_final['_val'] = np.where(es_local, df_final[col_away], df_final[columna_filtro])
                col_usar = '_val'

        if operador_filtro == "=":
            df_final = df_final[df_final[col_usar] == valor_filtro]
        elif operador_filtro == ">":
            df_final = df_final[df_final[col_usar] > valor_filtro]
        elif operador_filtro == ">=":
            df_final = df_final[df_final[col_usar] >= valor_filtro]
        elif operador_filtro == "<":
            df_final = df_final[df_final[col_usar] < valor_filtro]
        elif operador_filtro == "<=":
            df_final = df_final[df_final[col_usar] <= valor_filtro]

        if '_val' in df_final.columns:
            df_final = df_final.drop(columns=['_val'])
                # === FILTRO MARCADOR EXACTO ===
    if marcador_filtro != "Todos":
        gol_local, gol_visit = map(int, marcador_filtro.split('-'))
        df_final = df_final[(df_final['FTHG'] == gol_local) & (df_final['FTAG'] == gol_visit)]
    #################hasta aqui
#################hasta aqui 
    if equipo_filtro!= "Ninguno":
        if condicion_filtro == "Local":
            df_final = df_final[df_final['HomeTeam'] == equipo_filtro]
        elif condicion_filtro == "Visitante":
            df_final = df_final[df_final['AwayTeam'] == equipo_filtro]
        else:
            df_final = df_final[(df_final['HomeTeam'] == equipo_filtro) | (df_final['AwayTeam'] == equipo_filtro)]

    if equipo_filtro!= "Ninguno" and htft_filtro!= "Todo":
        def check_htft(row):
            if equipo_filtro == row['HomeTeam']:
                gf, gc = row['FTHG'], row['FTAG']
                htgf, htgc = row['HTHG'], row['HTAG']
            elif equipo_filtro == row['AwayTeam']:
                gf, gc = row['FTAG'], row['FTHG']
                htgf, htgc = row['HTAG'], row['HTHG']
            else:
                return False
            if htft_filtro == "RE":
                return htgf <= htgc and gf > gc
            elif htft_filtro == "FAIL":
                return htgf > htgc and gf <= gc
            else:
                res_ht = 'G' if htgf > htgc else 'P' if htgf < htgc else 'E'
                res_ft = 'G' if gf > gc else 'P' if gf < gc else 'E'
                return f"{res_ht}/{res_ft}" == htft_filtro
        df_final = df_final[df_final.apply(check_htft, axis=1)]
            
#####################################################RE FAIL
    if equipo_filtro!= "Ninguno" and resultado_filtro!= "Ninguno":
        df_eq = df_final.copy()
        if resultado_filtro == "Gana":
            df_final = df_eq[((df_eq['HomeTeam'] == equipo_filtro) & (df_eq['FTR'] == 'H')) |
                             ((df_eq['AwayTeam'] == equipo_filtro) & (df_eq['FTR'] == 'A'))]
        elif resultado_filtro == "Pierde":
            df_final = df_eq[((df_eq['HomeTeam'] == equipo_filtro) & (df_eq['FTR'] == 'A')) |
                             ((df_eq['AwayTeam'] == equipo_filtro) & (df_eq['FTR'] == 'H'))]
        elif resultado_filtro == "Empata":
            df_final = df_eq[df_eq['FTR'] == 'D']
        elif resultado_filtro == "Gana/Empata":
            df_final = df_eq[((df_eq['HomeTeam'] == equipo_filtro) & (df_eq['FTR'].isin(['H','D']))) |
                             ((df_eq['AwayTeam'] == equipo_filtro) & (df_eq['FTR'].isin(['A','D'])))]
        elif resultado_filtro == "Gana/Pierde":
            df_final = df_eq[((df_eq['HomeTeam'] == equipo_filtro) & (df_eq['FTR'].isin(['H','A']))) |
                             ((df_eq['AwayTeam'] == equipo_filtro) & (df_eq['FTR'].isin(['A','H'])))]
        elif resultado_filtro == "Empata/Pierde":
            df_final = df_eq[((df_eq['HomeTeam'] == equipo_filtro) & (df_eq['FTR'].isin(['D','A']))) |
                         ((df_eq['AwayTeam'] == equipo_filtro) & (df_eq['FTR'].isin(['D','H'])))]

    # === FILTRO MARGEN ===
    if margen_filtro!= "Todo" and equipo_filtro!= "Ninguno":
        def check_margen(row):
            if row['HomeTeam'] == equipo_filtro:
                dif = int(row['FTHG']) - int(row['FTAG'])
            elif row['AwayTeam'] == equipo_filtro:
                dif = int(row['FTAG']) - int(row['FTHG'])
            else:
                return False
            if margen_filtro == "Empate": return dif == 0
            if margen_filtro == "Gana 1": return dif == 1
            if margen_filtro == "Gana 2": return dif == 2
            if margen_filtro == "Gana 3+": return dif >= 3
            if margen_filtro == "Pierde 1": return dif == -1
            if margen_filtro == "Pierde 2": return dif == -2
            if margen_filtro == "Pierde 3+": return dif <= -3
            if margen_filtro == "Gana ≥2": return dif >= 2
            if margen_filtro == "Pierde ≥2": return dif <= -2
            return True
        df_final = df_final[df_final.apply(check_margen, axis=1)]



    # === APLICAR FILTRO DE CUOTAS B365 ===
    if cuota_tipo!= "Ninguno":
        if cuota_tipo == "Todo":
            mask = (
                ((df_final['B365H'] >= rango_cuotas[0]) & (df_final['B365H'] <= rango_cuotas[1])) |
                ((df_final['B365D'] >= rango_cuotas[0]) & (df_final['B365D'] <= rango_cuotas[1])) |
                ((df_final['B365A'] >= rango_cuotas[0]) & (df_final['B365A'] <= rango_cuotas[1]))
            )
            df_final = df_final[mask]
        else:
            col_cuota = {'1': 'B365H', 'X': 'B365D', '2': 'B365A'}[cuota_tipo]
            ftr_esperado = {'1': 'H', 'X': 'D', '2': 'A'}[cuota_tipo]
            df_final = df_final[
                (df_final[col_cuota] >= rango_cuotas[0]) &
                (df_final[col_cuota] <= rango_cuotas[1]) &
                (df_final['FTR'] == ftr_esperado)
            ]
    # === FIN FILTRO CUOTAS ===

    # FILTRO AMBOS MARCAN - ESTE TE FALTABA
    if ambos_marcan == "Sí":
        df_final = df_final[(df_final['FTHG'] > 0) & (df_final['FTAG'] > 0)]
    elif ambos_marcan == "No":
        df_final = df_final[(df_final['FTHG'] == 0) | (df_final['FTAG'] == 0)]

    # ESTO VA DESPUÉS DE TODOS LOS FILTROS
    df_final = df_final.reset_index(drop=True)

    ###################################################################
    # 1) FILTRO POR PARTE - FUNCIONA PARA TODAS LAS LIGAS/TEMPORADAS
    if parte_gol != "Todo" and equipo_filtro != "Ninguno" and alcance_filtro not in ["AF0","AF1","AF2","AF3","AF4","C0","C1","C2","C3","C4"]:
        if parte_gol == "1T":
            df_final = df_final[
                ((df_final['HomeTeam'] == equipo_filtro) & (df_final['HTHG'] > 0)) |
                ((df_final['AwayTeam'] == equipo_filtro) & (df_final['HTAG'] > 0))
            ]
            
        elif parte_gol == "2T":
            df_final = df_final[
                ((df_final['HomeTeam'] == equipo_filtro) & ((df_final['FTHG'] - df_final['HTHG']) > 0)) |
                ((df_final['AwayTeam'] == equipo_filtro) & ((df_final['FTAG'] - df_final['HTAG']) > 0))
            ]
    elif parte_gol!= "Todo" and equipo_filtro == "Ninguno":
        if parte_gol == "1T":
            df_final = df_final[(df_final['HTHG'] + df_final['HTAG']) > 0]
        elif parte_gol == "2T":
            df_final = df_final[((df_final['FTHG']-df_final['HTHG']) + (df_final['FTAG']-df_final['HTAG'])) > 0]

    # 2) GOLES DETALLADOS (solo para mostrar)
    df_final['Goles'] = ''
    if todos_eventos and not df_final.empty:
        df_final['Goles'] = df_final.apply(
            lambda r: buscar_goles_partido(r, todos_eventos, rango_minutos[0], rango_minutos[1], parte_gol, equipo_filtro),
            axis=1
        )
        if not (rango_minutos[0] == 0 and rango_minutos[1] >= 120):
            df_final = df_final[df_final['Goles'].str.len() > 0]

    # --- FILTRO JUGADOR ---
    if jugador_filtro!= "TODOS":
        df_final = df_final[df_final['Goles'].str.contains(jugador_filtro, case=False, na=False)]
######################################################################################
    if len(df_final) > 0:
        df_final['partidos'] = ''
        df_final['Tarjetas/Corners/goles'] = ''
    else:
        df_final['partidos'] = pd.Series(dtype='object')
        df_final['Tarjetas/Corners/goles'] = pd.Series(dtype='object')

    st.caption(f"Mostrando {len(df_final)} partidos")

    if equipo_filtro!= "Ninguno" and len(df_final) > 0:
        total = len(df_final)
        gana = len(df_final[((df_final['HomeTeam'] == equipo_filtro) & (df_final['FTR'] == 'H')) |
                            ((df_final['AwayTeam'] == equipo_filtro) & (df_final['FTR'] == 'A'))])
        empata = len(df_final[df_final['FTR'] == 'D'])
        pierde = len(df_final[((df_final['HomeTeam'] == equipo_filtro) & (df_final['FTR'] == 'A')) |
                              ((df_final['AwayTeam'] == equipo_filtro) & (df_final['FTR'] == 'H'))])

        gana_empata = gana + empata
        pierde_empata = pierde + empata

        

    st.divider()

    columnas_mostrar = [
        'partidos', 
    ]

    columnas_mostrar = [col for col in columnas_mostrar if col in df_final.columns]
    
    st.divider()

    # --- CSS para las tablas ---

    
    def render_tabla_equipo(df_input, equipo_ref):
        df_tmp = df_input.copy()
        if todos_eventos and not df_tmp.empty:
            df_tmp['Goles'] = df_tmp.apply(
                lambda r: buscar_goles_partido(r, todos_eventos, rango_minutos[0], rango_minutos[1], parte_gol, equipo_ref),
                axis=1
            )
        else:
            df_tmp['Goles'] = ''
        if jugador_filtro!= "TODOS":
            df_tmp = df_tmp[df_tmp['Goles'].str.contains(jugador_filtro, case=False, na=False)]
        if len(df_tmp) > 0:
            df_tmp['partidos'] = df_tmp.apply(lambda row: formatear_partido(row, equipo_ref, cuota_tipo, row.get('Goles','')), axis=1)
        df_tmp = df_tmp.sort_values(['Jornada','Date'], ascending=[False, False]).head(150)
        return df_tmp[['partidos']].to_html(escape=False, index=False, classes='dataframe')

    # --- Partidos plegables ---
    # --- Partidos plegables ---
    with st.expander("📋 Partidos", expanded=True, key="exp_partidos"):
        if equipo_filtro != "Ninguno" and equipo2_filtro != "Ninguno":
            df1 = df_base_h2h[(df_base_h2h['HomeTeam']==equipo_filtro) | (df_base_h2h['AwayTeam']==equipo_filtro)].sort_values(['Jornada','Date'], ascending=False).head(150)
            df2 = df_base_h2h[(df_base_h2h['HomeTeam']==equipo2_filtro) | (df_base_h2h['AwayTeam']==equipo2_filtro)].sort_values(['Jornada','Date'], ascending=False).head(150)

            html1 = "".join([formatear_h2h_compacto(r, equipo_filtro) for _, r in df1.iterrows()])
            html2 = "".join([formatear_h2h_compacto(r, equipo2_filtro) for _, r in df2.iterrows()])
            h2h_html = f'''
            <div style="max-height:700px; overflow-y:auto; border:1px solid #ddd;">
              <div style="display:grid; grid-template-columns:1fr 1fr; gap:0; position:sticky; top:0; background:#fff; z-index:5; border-bottom:2px solid #000;">
                <div style="font-weight:700; font-size:11px; text-align:center; padding:4px">{equipo_filtro} ({len(df1)})</div>
                <div style="font-weight:700; font-size:11px; text-align:center; padding:4px">{equipo2_filtro} ({len(df2)})</div>
              </div>
              <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; padding:6px;">
                <div>{html1}</div>
                <div>{html2}</div>
              </div>
            </div>
            '''
            st.markdown(h2h_html, unsafe_allow_html=True)
        ############ver 2 partidos en 2 columnas a la vez
        else:
            df_mostrar = df_final.sort_values(['Jornada','Date'], ascending=[False, False]).reset_index(drop=True)
            MAX_FILAS = 150
            if len(df_mostrar) > MAX_FILAS:
                st.warning(f"Mostrando {MAX_FILAS} de {len(df_mostrar)} partidos")
                df_mostrar = df_mostrar.head(MAX_FILAS)
            st.caption(f"Mostrando {len(df_mostrar)} partidos")
            partidos_html = []
            if len(df_mostrar) > 0:
                for _, r in df_mostrar.iterrows():
                    partidos_html.append(formatear_partido(r, equipo_filtro if equipo_filtro != "Ninguno" else None, cuota_tipo, r.get('Goles','')))
            left_html = "".join(partidos_html[0::2])
            right_html = "".join(partidos_html[1::2])
            grid_html = f'''
            <div style="max-height:700px; overflow-y:auto; border:1px solid #ddd;">
              <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; padding:6px;">
                <div>{left_html}</div>
                <div>{right_html}</div>
              </div>
            </div>
            '''
            st.markdown(grid_html, unsafe_allow_html=True)
###########################################################
    with st.expander("ℹ Info jornadas", key="exp_info"):
        for liga in liga_sel:
            for temp in temp_sel:
                subset = df_fil[(df_fil['League']==liga) & (df_fil['Season']==temp)]
                if not subset.empty:
                    equipos = pd.unique(subset[['HomeTeam','AwayTeam']].values.ravel())
                    n_equipos = len(equipos)
                    st.write(f"**{liga} {temp}**: {n_equipos} equipos → {n_equipos//2} partidos por jornada")

########filtro rachas La UI (donde eliges Tipo, Condición, Dónde)
with st.expander("🔥 Filtro Rachas", expanded=False, key="exp_rachas"):
    c1, c2, c3, c4 = st.columns([1.2, 1.3, 0.9, 1.0])
    tipo = c1.selectbox("Tipo", ["Máximos", "%"], key="r_tipo")
    cond = c2.selectbox("R1x2", ["Todo","G","P","E","G/E","E/P","G/P"], key="r_cond")
    donde = c4.selectbox("Dónde", ["Todo","Local","Visitante"], key="r_donde")

    if tipo == "Máximos":
        x = c3.number_input("X max", 1, 20, 3, key="r_x")
    else:
        pct_min = c3.slider("% mínimo", 0, 100, 50, key="r_pct")

    # rango de jornadas SOLO para rachas
    jmin = int(df_rachas_full['Jornada'].min())
    jmax = int(df_rachas_full['Jornada'].max())
    rj1, rj2 = st.slider("Jornadas", jmin, jmax, (jmin, jmax), key="r_jornadas")

    src = df_rachas_full[(df_rachas_full['Jornada'] >= rj1) & (df_rachas_full['Jornada'] <= rj2)].copy()

    if not src.empty:
        if tipo == "Máximos":
            t = _rachas(src, cond, donde, x_max=x)
            res = t[t['CountX'] > 0].sort_values(['CountX','Max'], ascending=False)
        else:
            t = _rachas(src, cond, donde)
            res = t[t['%'] >= pct_min].sort_values(['%','Max'], ascending=False)

        st.caption(f"Rachas calculadas en J{rj1} a J{rj2} — {len(res)} equipos")
        st.dataframe(
            res[['Equipo']],
            use_container_width=True,
            hide_index=True,
            height=500,
            key="tabla_rachas_estable",
            column_config={"Equipo": st.column_config.TextColumn("Resumen / Jornadas")}
        )
            ############fin
 ##################################################################
 ################################################################           
