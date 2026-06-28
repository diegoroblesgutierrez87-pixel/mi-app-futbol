import re
import unicodedata
import streamlit as st
import pandas as pd
import numpy as np

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
st.markdown("""
<style>
[data-testid="stDeployButton"],[data-testid="stToolbar"],#MainMenu,footer{display:none!important}
.block-container{padding:.5rem!important}
div[data-testid="stHorizontalBlock"]{display:flex!important;flex-wrap:nowrap!important;overflow-x:auto!important;gap:6px!important;padding-bottom:6px!important}
div[data-testid="stHorizontalBlock"]>div{flex:0 0 auto!important;min-width:82px!important}
[data-testid="stWidgetLabel"] p{font-size:10px!important;margin:0!important;white-space:nowrap}
table{border-collapse:collapse;width:100%;font-size:9px;font-family:'Source Code Pro',monospace;table-layout:fixed;margin:0}
thead{display:none}
td{padding:3px 5px!important;border-bottom:2px solid #000!important;border-left:1px solid #d1d5db;border-right:1px solid #d1d5db;vertical-align:middle;line-height:1.15}
tr:nth-child(even){background:#f9fafb}tr:hover{background:#e5e7eb}
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
    for col in ['B365H','B365D','B365A']:
        if col not in df.columns: df[col] = ''

    df['GolesTotales'] = df['FTHG'] + df['FTAG']
    df['GolesHT'] = df['HTHG'] + df['HTAG']
    df['Goles2T'] = df['GolesTotales'] - df['GolesHT']
    df['corneTot'] = df['HC'] + df['AC']
    df['TargAmTot'] = df['HY'] + df['AY']
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
    key = (normaliza(row['HomeTeam']), normaliza(row['AwayTeam']), row['Date'].strftime('%Y-%m-%d'))
    evs = eventos_dict.get(key, [])
    if not evs:
        return ""

    hg = int(row['FTHG']); ag = int(row['FTAG'])
    ganador = normaliza(row['HomeTeam']) if hg > ag else normaliza(row['AwayTeam']) if ag > hg else None
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
    ht_disp = abreviar_equipo(ht)
    at_disp = abreviar_equipo(at)
    league = row.get('League','')
    fecha = row['Date'].strftime('%d/%m/%y') if pd.notna(row['Date']) else ''
    jornada = f"J{int(row['Jornada'])}" if pd.notna(row.get('Jornada')) else ''
    hg_num, ag_num = int(row['FTHG']), int(row['FTAG'])
    hpts, apts = int(row['HomePtsPrev']), int(row['AwayPtsPrev'])
    hpos, apos = int(row['HomePosPrev']), int(row['AwayPosPrev'])
    hy, ay = int(row['HY']), int(row['AY'])
    hr, ar = int(row['HR']), int(row['AR'])
    hc, ac = int(row['HC']), int(row['AC'])
    hs, as_ = int(row['HS']), int(row['AS'])
    hst, ast = int(row['HST']), int(row['AST'])
    hf, af = int(row['HF']), int(row['AF'])
    hthg, htag = int(row['HTHG']), int(row['HTAG'])
    h2tg = hg_num - hthg
    a2tg = ag_num - htag

    tot_a = hy + ay
    tot_r = hr + ar
    tot_c = hc + ac
    tot_g = hg_num + ag_num
    tot_s = hs + as_
    tot_f = hf + af

    def color_stat(valor, tipo, es_local=True):
        if valor == 0:
            return ""
        txt = f"{valor}{tipo}"
        return f"<span style='color:#000000; font-weight:600; font-style:normal!important; margin:0 3px; display:inline-block'>{txt}</span>"

    totales_partes = [color_stat(tot_a,'A',True),color_stat(tot_r,'R',True),color_stat(tot_c,'C',True),color_stat(tot_g,'G',True),color_stat(tot_f,'F',True),color_stat(tot_s,'S',True)]
    
    # Resultado HT/FT
    # Resultado HT/FT - siempre con abreviatura (E/VAL, ALA/BET...)
    ht_res = abreviar_equipo(ht) if hthg > htag else abreviar_equipo(at) if hthg < htag else 'E'
    ft_res = abreviar_equipo(ht) if hg_num > ag_num else abreviar_equipo(at) if hg_num < ag_num else 'E'
    if equipo_filtro and equipo_filtro != "Ninguno":
        if equipo_filtro == ht:
            won = hg_num > ag_num; lost = hg_num < ag_num
        elif equipo_filtro == at:
            won = ag_num > hg_num; lost = ag_num < hg_num
        else:
            won = lost = False
        color_res = "#0f8105ff" if won else "#f31818" if lost else "#f89007ff"
    else:
        color_res = "#444"
    
    cuota_h = row.get('B365H', ''); cuota_d = row.get('B365D', ''); cuota_a = row.get('B365A', '')
    cuotas_html = ""
    if cuota_h and cuota_d and cuota_a:
        try:
            ftr = row.get('FTR', '')
            style_cuota_ganadora = "font-weight:900; color:#000; font-style:normal!important;"
            style_cuota_normal = "font-weight:600; color:#6b7280; font-style:normal!important;"
            h_txt = f"{float(cuota_h):.2f}"; d_txt = f"{float(cuota_d):.2f}"; a_txt = f"{float(cuota_a):.2f}"
            if cuota_tipo == "1" and ftr == 'H': h_txt = f"[{h_txt}]"
            elif cuota_tipo == "X" and ftr == 'D': d_txt = f"[{d_txt}]"
            elif cuota_tipo == "2" and ftr == 'A': a_txt = f"[{a_txt}]"
            h_style = style_cuota_ganadora if ftr == 'H' else style_cuota_normal
            d_style = style_cuota_ganadora if ftr == 'D' else style_cuota_normal
            a_style = style_cuota_ganadora if ftr == 'A' else style_cuota_normal
            
            re_fail_txt = ""
            if equipo_filtro and equipo_filtro != "Ninguno":
                if equipo_filtro == row['HomeTeam']: htgf, htgc = hthg, htag; gf, gc = hg_num, ag_num
                elif equipo_filtro == row['AwayTeam']: htgf, htgc = htag, hthg; gf, gc = ag_num, hg_num
                else: htgf = htgc = gf = gc = 0
                if htgf <= htgc and gf > gc: re_fail_txt = "<span style='font-weight:900; color:#0f8105ff; margin-left:12px; font-style:normal!important'>RE</span>"
                elif htgf > htgc and gf <= gc: re_fail_txt = "<span style='font-weight:900; color:#f31818; margin-left:12px; font-style:normal!important'>FAIL</span>"
            cuotas_html = f"<div style='font-size:9px; margin-bottom:2px; font-style:normal!important'>{league} | <span style='{h_style}'>{h_txt}</span>&nbsp;&nbsp;<span style='{d_style}'>{d_txt}</span>&nbsp;&nbsp;<span style='{a_style}'>{a_txt}</span>{re_fail_txt}</div>"
        except:
            cuotas_html = ""
    
    style_ganador = "color:#000000; font-weight:900; font-size:9px; font-style:normal!important"
    style_subrayado = "text-decoration:underline; text-decoration-thickness:2px; font-style:normal!important"
    ht_txt, at_txt = ht_disp, at_disp
    hg_txt, ag_txt = str(hg_num), str(ag_num)
    hpts_txt, apts_txt = str(hpts), str(apts)
    hpos_txt, apos_txt = f"{hpos}º", f"{apos}º"

    if hg_num > ag_num:
        ht_txt = f"<span style='{style_ganador}'>{ht_disp}</span>"; hg_txt = f"<span style='{style_ganador}'>{hg_num}</span>"; hpts_txt = f"<span style='{style_ganador}'>{hpts}</span>"; hpos_txt = f"<span style='{style_ganador}'>{hpos}º</span>"
    elif ag_num > hg_num:
        at_txt = f"<span style='{style_ganador}'>{at_disp}</span>"; ag_txt = f"<span style='{style_ganador}'>{ag_num}</span>"; apts_txt = f"<span style='{style_ganador}'>{apts}</span>"; apos_txt = f"<span style='{style_ganador}'>{apos}º</span>"

    if equipo_filtro and equipo_filtro != "Ninguno":
        if equipo_filtro == row['HomeTeam']:
            if hg_num > ag_num: ht_txt = f"<span style='{style_ganador}; {style_subrayado}'>{ht_disp}</span>"; hpts_txt = f"<span style='{style_ganador}; {style_subrayado}'>{hpts}</span>"; hpos_txt = f"<span style='{style_ganador}; {style_subrayado}'>{hpos}º</span>"
            else: ht_txt = f"<span style='{style_subrayado}'>{ht_disp}</span>"; hpts_txt = f"<span style='{style_subrayado}'>{hpts}</span>"; hpos_txt = f"<span style='{style_subrayado}'>{hpos}º</span>"
        elif equipo_filtro == row['AwayTeam']:
            if ag_num > hg_num: at_txt = f"<span style='{style_ganador}; {style_subrayado}'>{at_disp}</span>"; apts_txt = f"<span style='{style_ganador}; {style_subrayado}'>{apts}</span>"; apos_txt = f"<span style='{style_ganador}; {style_subrayado}'>{apos}º</span>"
            else: at_txt = f"<span style='{style_subrayado}'>{at_disp}</span>"; apts_txt = f"<span style='{style_subrayado}'>{apts}</span>"; apos_txt = f"<span style='{style_subrayado}'>{apos}º</span>"

    linea1 = f"<div style='font-style:normal!important; font-size:9px'>{fecha} | {jornada} | {ht_txt} {hg_txt}-{ag_txt} {at_txt}</div>"
    linea2 = f"<div style='font-style:normal!important; font-size:9px'>| {hpts_txt}-{apts_txt} pts | {hpos_txt} vs {apos_txt}</div>"
    res_line = f"<div style='font-size:9px; margin-top:1px; font-weight:700; color:{color_res}; font-style:normal!important'>{ht_res}/{ft_res}</div>"
    
    es_local_ganador = hg_num > ag_num; es_visit_ganador = ag_num > hg_num; es_local_filtrado = equipo_filtro == row['HomeTeam']; es_visit_filtrado = equipo_filtro == row['AwayTeam']
    
    h1t_home_styles = []; h1t_away_styles = []
    if es_local_filtrado: h1t_home_styles.append("text-decoration:underline; text-decoration-thickness:2px")
    if es_local_ganador: h1t_home_styles.append("font-weight:900")
    if es_visit_filtrado: h1t_away_styles.append("text-decoration:underline; text-decoration-thickness:2px")
    if es_visit_ganador: h1t_away_styles.append("font-weight:900")
    
    h1t_home = f"<span style=\"{';'.join(h1t_home_styles)}\">1p: {hthg}G</span>" if h1t_home_styles else f"1p: {hthg}G"
    h1t_away = f"<span style=\"{';'.join(h1t_away_styles)}\">1p: {htag}G</span>" if h1t_away_styles else f"1p: {htag}G"
    
    style_h2_home = []; style_h2_away = []
    if es_local_filtrado: style_h2_home.append("text-decoration:underline; text-decoration-thickness:2px")
    if es_local_ganador: style_h2_home.append("font-weight:900")
    if es_visit_filtrado: style_h2_away.append("text-decoration:underline; text-decoration-thickness:2px")
    if es_visit_ganador: style_h2_away.append("font-weight:900")
    h2t_home = f"<span style=\"{';'.join(style_h2_home)}\">2p: {h2tg}G</span>" if style_h2_home else f"2p: {h2tg}G"
    h2t_away = f"<span style=\"{';'.join(style_h2_away)}\">2p: {a2tg}G</span>" if style_h2_away else f"2p: {a2tg}G"
    
    stats_home_styles = []; stats_away_styles = []
    if es_local_filtrado: stats_home_styles.append("text-decoration:underline; text-decoration-thickness:2px")
    if es_local_ganador: stats_home_styles.append("font-weight:900")
    if es_visit_filtrado: stats_away_styles.append("text-decoration:underline; text-decoration-thickness:2px")
    if es_visit_ganador: stats_away_styles.append("font-weight:900")
    
    stats_home_txt = f"{hs}T {hst}TP {hf}F {hc}C {hy}A {hr}R"
    stats_away_txt = f"{as_}T {ast}TP {af}F {ac}C {ay}A {ar}R"
    
    stats_home = f"<span style=\"{';'.join(stats_home_styles)}\">{stats_home_txt}</span>" if stats_home_styles else stats_home_txt
    stats_away = f"<span style=\"{';'.join(stats_away_styles)}\">{stats_away_txt}</span>" if stats_away_styles else stats_away_txt
    
    linea_stats = f"<div style='margin-top:2px; line-height:1.2; font-size:7.5px'>{h1t_home}</div>"
    linea_stats += f"<div style='line-height:1.2; font-size:7.5px'>{h1t_away}</div>"
    linea_stats += f"<div style='line-height:1.2; font-size:7.5px; color:#555'>{h2t_home}</div>"
    linea_stats += f"<div style='line-height:1.2; font-size:7.5px; color:#555'>{h2t_away}</div>"
    linea_stats += f"<div style='line-height:1.2; font-size:7px; color:#222; margin-top:1px'>{stats_home}</div>"
    linea_stats += f"<div style='line-height:1.2; font-size:7px; color:#222'>{stats_away}</div>"
    
    totales_final = ""
    if any([tot_a, tot_r, tot_c, tot_g, tot_f, tot_s]):
        totales_final = f"<div style='font-size:8px; margin-top:3px'><span style='font-weight:700; color:#111;'>TOT:</span> {''.join([p for p in totales_partes if p])}</div>"
    
    goles_html = f"<div style='margin-top:3px; line-height:1.2; font-size:9px; color:#333'>{goles_txt}</div>" if goles_txt else ""
    return f'<div translate="no">{cuotas_html}{linea1}{linea2}{res_line}{linea_stats}{totales_final}{goles_html}</div>'
def formatear_h2h_compacto(row, equipo_ref=None):
    league = str(row.get('League',''))[:3].upper()
    fecha = row['Date'].strftime('%d/%m/%y') if pd.notna(row['Date']) else ''
    jorn = f"J{int(row['Jornada'])}"

    # cuotas con la ganadora en negrita
    try:
        h_od = float(row['B365H']); d_od = float(row['B365D']); a_od = float(row['B365A'])
        ftr = row.get('FTR','')
        s_win = "font-weight:900; color:#000"
        s_norm = "color:#555"
        odds = f"<span style='{s_win if ftr=='H' else s_norm}'>{h_od:.2f}</span> <span style='{s_win if ftr=='D' else s_norm}'>{d_od:.2f}</span> <span style='{s_win if ftr=='A' else s_norm}'>{a_od:.2f}</span>"
    except:
        odds = ""

    ht_raw = abreviar_equipo(row['HomeTeam'])
    at_raw = abreviar_equipo(row['AwayTeam'])
    hg, ag = int(row['FTHG']), int(row['FTAG'])
    h1h, h1a = int(row['HTHG']), int(row['HTAG'])
    h2h, h2a = hg - h1h, ag - h1a

    is_home = equipo_ref and normaliza(equipo_ref)==normaliza(row['HomeTeam'])
    is_away = equipo_ref and normaliza(equipo_ref)==normaliza(row['AwayTeam'])

    # equipos y marcador (negrita ganador + subrayado si es el equipo de la columna)
    ht_disp = f"<b>{ht_raw}</b>" if hg > ag else ht_raw
    at_disp = f"<b>{at_raw}</b>" if ag > hg else at_raw
    hg_disp = f"<b>{hg}</b>" if hg > ag else str(hg)
    ag_disp = f"<b>{ag}</b>" if ag > hg else str(ag)
    if is_home: ht_disp = f"<u>{ht_disp}</u>"
    if is_away: at_disp = f"<u>{at_disp}</u>"
    teams = f"{ht_disp} {hg_disp}-{ag_disp} {at_disp}"

    hpos, apos = int(row['HomePosPrev']), int(row['AwayPosPrev'])
    hpts, apts = int(row['HomePtsPrev']), int(row['AwayPtsPrev'])
    pos = f"<u>{hpos}º</u> vs {apos}º" if is_home else f"{hpos}º vs <u>{apos}º</u>" if is_away else f"{hpos}º vs {apos}º"
    pts = f"<u>{hpts}</u>-{apts} pts" if is_home else f"{hpts}-<u>{apts}</u> pts" if is_away else f"{hpts}-{apts} pts"

    # HT/FT en color según el equipo de la columna
    ht_res = ht_raw if h1h > h1a else at_raw if h1h < h1a else 'E'
    ft_res = ht_raw if hg > ag else at_raw if hg < ag else 'E'
    if is_home: won = hg > ag; lost = hg < ag
    elif is_away: won = ag > hg; lost = ag < hg
    else: won = lost = False
    color = "#0f8105ff" if won else "#f31818" if lost else "#f89007ff"
    res = f"<span style='color:{color}; font-weight:700'>{ht_res}/{ft_res}</span>"

    # 1p 2p
    h1t_h = f"1p:{h1h}G"; h1t_a = f"1p:{h1a}G"
    h2t_h = f"2p:{h2h}G"; h2t_a = f"2p:{h2a}G"
    if is_home: h1t_h = f"<u>{h1t_h}</u>"; h2t_h = f"<u>{h2t_h}</u>"
    if is_away: h1t_a = f"<u>{h1t_a}</u>"; h2t_a = f"<u>{h2t_a}</u>"

    hs, hst, hf, hc, hy, hr = [int(row[x]) for x in ['HS','HST','HF','HC','HY','HR']]
    as_, ast, af, ac, ay, ar = [int(row[x]) for x in ['AS','AST','AF','AC','AY','AR']]
    stat_h = f"{hs}T {hst}TP {hf}F {hc}C {hy}A {hr}R"
    stat_a = f"{as_}T {ast}TP {af}F {ac}C {ay}A {ar}R"
    if is_home: stat_h = f"<u>{stat_h}</u>"
    if is_away: stat_a = f"<u>{stat_a}</u>"

    tot_a = hy+ay; tot_c = hc+ac; tot_g = hg+ag; tot_f = hf+af; tot_s = hs+as_; tot_r = hr+ar
    tot = ''.join([f"{v}{k}" for v,k in [(tot_a,'A'),(tot_c,'C'),(tot_g,'G'),(tot_f,'F'),(tot_s,'S'),(tot_r,'R')] if v>0])
#######visualizacion de h2h
    lineas = [
    f"{league} {res}",
    f"{fecha} |{jorn}|",
    odds,
    teams,
    pos,
    pts,
    h1t_h,
    h1t_a,
    h2t_h,
    h2t_a,
    stat_h,
    stat_a,
    f"TOT:{tot}"
]
   
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

    # ResHtFt vectorizado
    abbr_map = {t: abreviar_equipo(t) for t in pd.unique(df[['HomeTeam','AwayTeam']].values.ravel())}
    ht_res = np.where(df['HTHG'] > df['HTAG'], df['HomeTeam'].map(abbr_map),
             np.where(df['HTHG'] < df['HTAG'], df['AwayTeam'].map(abbr_map), 'E'))
    ft_res = np.where(df['FTHG'] > df['FTAG'], df['HomeTeam'].map(abbr_map),
             np.where(df['FTHG'] < df['FTAG'], df['AwayTeam'].map(abbr_map), 'E'))
    df['ResHtFt'] = ht_res + '/' + ft_res

    return df, df_clasificacion

   

@st.cache_data
def _rachas(df_base, cond, loc):
    df = df_base.copy()
    if 'Jornada' not in df.columns:
        df['Jornada'] = 0
    h = df[['Date','Jornada','HomeTeam','AwayTeam','FTR']].copy()
    h['Equipo'] = h['HomeTeam']
    h['Res'] = h['FTR'].map({'H':'G','A':'P','D':'E'})
    h['Loc'] = 'Local'
    a = df[['Date','Jornada','HomeTeam','AwayTeam','FTR']].copy()
    a['Equipo'] = a['AwayTeam']
    a['Res'] = a['FTR'].map({'A':'G','H':'P','D':'E'})
    a['Loc'] = 'Visitante'
    d = pd.concat([h, a], ignore_index=True)
    if loc in ['Local','Visitante']:
        d = d[d['Loc'] == loc]
    d = d.sort_values(['Equipo','Date'])
    mapa = {"Gana": {'G'}, "Pierde": {'P'}, "Empata": {'E'}, "Gana/Empata": {'G','E'}, "Empata/Pierde": {'E','P'}, "Gana/Pierde": {'G','P'}}
    cs = mapa[cond]
    out = []
    for eq, g in d.groupby('Equipo'):
        s = g['Res'].tolist()
        js = g['Jornada'].tolist()
        seg = 0
        for r in reversed(s):
            if r in cs: seg += 1
            else: break
        total = sum(1 for r in s if r in cs)
        pct = round(100 * total / len(s), 1) if s else 0
        jornadas_ok = sorted(set(int(j) for r, j in zip(s, js) if r in cs))
        jornadas_str = ', '.join(f"J{j}" for j in jornadas_ok)
        ult5 = ''.join(s[-5:])
        texto = f"{eq} | {len(s)}J | {seg} seg | {pct}% | {ult5}\n↳ {jornadas_str}"
        out.append({'Equipo': texto, 'PJ': len(s), 'Seguidos': seg, '%': pct})
    return pd.DataFrame(out)


    


def limpiar_filtros():
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
df = cargar_csv()



col1, col2, col3, col4 = st.columns(4)

ligas_disponibles = sorted(df['League'].unique())
temporadas_disponibles = sorted(df['Season'].unique())

st.caption(f"Ligas detectadas: {', '.join(ligas_disponibles)}")

liga_sel = col1.multiselect("Liga", ligas_disponibles, default=[], 
    format_func=lambda x: '\u2060'.join(x))  # rompe la palabra I2 para el traductor
temp_sel = col2.multiselect("Temporada", temporadas_disponibles, default=[])

if not liga_sel or not temp_sel:
  
    st.stop()

modo_vista = col4.selectbox("Modo vista", ["Jornadas", "Clasificación"])

df_fil = df[df['League'].isin(liga_sel) & df['Season'].isin(temp_sel)]

if df_fil.empty:
    st.stop()

with st.spinner('Calculando clasificación...'):
    df_final, df_clasificacion = calcular_estado_jornada(df_fil)

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
###columna numerica
    columnas_numericas = ['FTHG','FTAG','HTHG','HTAG','HS','AS','HST','AST','HF','AF','HC','AC','HY','AY','HR','AR','GolesTotales','GolesHT','Goles2T','corneTot','TargAmTot','HomePtsPrev','AwayPtsPrev','HomePosPrev','AwayPosPrev']
    equipos_disponibles = sorted(pd.unique(df_final[['HomeTeam','AwayTeam']].values.ravel()))

    # FILA 1 - Eq1 Eq2 Col. Vlr L/V
    r1c1, r1c2, r1c3, r1c4, r1c5, r1c6 = st.columns([1.1, 1.1, 1, 0.5, 0.7, 0.8])
    equipo_filtro = r1c1.selectbox("Eq1", ["Ninguno"] + equipos_disponibles, key='equipo_filtro')
    equipo2_filtro = r1c2.selectbox("Eq2", ["Ninguno"] + equipos_disponibles, key='equipo2_filtro')
    columna_filtro = r1c3.selectbox("Col.", ["Ninguno"] + columnas_numericas, key='columna_filtro')
    operador_filtro = r1c4.selectbox("Op", ["=", ">", ">=", "<", "<="], key='operador_filtro')
    valor_filtro = r1c5.selectbox("Vlr", ["Ninguno"] + [i/2 for i in range(81)], key='valor_filtro')
    condicion_filtro = r1c6.selectbox("L/V", ["Todo", "Local", "Visitante"], key='condicion_filtro')

    # FILA 2 - Fav/Contr HT/FT 1x2 AM @
    r2c1, r2c2, r2c3, r2c4, r2c5 = st.columns(5)
    alcance_filtro = r2c1.selectbox("Fav/Contr", ["Todo","A favor","En contra"], key='alcance_filtro', help="Todo=total | A favor=lo que hace | En contra=lo que recibe")
    htft_filtro = r2c2.selectbox("HT/FT", ["Todo","G/G","G/E","G/P","E/G","E/E","E/P","P/G","P/E","P/P","RE","FAIL"], key='htft_filtro')
    opciones_1x2 = ["Ninguno","Gana","Pierde","Empata","Gana/Empata","Gana/Pierde","Empata/Pierde"]
    mapa_1x2 = {"Ninguno":"-", "Gana":"G", "Pierde":"P", "Empata":"E", "Gana/Empata":"GE", "Gana/Pierde":"GP", "Empata/Pierde":"EP"}
    resultado_filtro = r2c3.selectbox("1x2", opciones_1x2, format_func=lambda x: mapa_1x2[x], key='resultado_filtro')
    ambos_marcan = r2c4.selectbox("AM", ["Todos","Sí","No"], key='ambos_marcan')
    cuota_tipo = r2c5.selectbox("@", ["Ninguno","Todo","1","X","2"], key='cuota_tipo')


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
    if columna_filtro!= "Ninguno" and valor_filtro!= "Ninguno":
        def valor_equipo(row, col, equipo):
            es_local = row['HomeTeam'] == equipo
            if alcance_filtro == "A favor":
                mapa = {
                    'FTHG': row['FTHG'] if es_local else row['FTAG'],
                    'FTAG': row['FTAG'] if es_local else row['FTHG'],
                    'HTHG': row['HTHG'] if es_local else row['HTAG'],
                    'HTAG': row['HTAG'] if es_local else row['HTHG'],
                    'HS': row['HS'] if es_local else row['AS'],
                    'AS': row['AS'] if es_local else row['HS'],
                    'HST': row['HST'] if es_local else row['AST'],
                    'AST': row['AST'] if es_local else row['HST'],
                    'HF': row['HF'] if es_local else row['AF'],
                    'AF': row['AF'] if es_local else row['HF'],
                    'HC': row['HC'] if es_local else row['AC'],
                    'AC': row['AC'] if es_local else row['HC'],
                    'HY': row['HY'] if es_local else row['AY'],
                    'AY': row['AY'] if es_local else row['HY'],
                    'HR': row['HR'] if es_local else row['AR'],
                    'AR': row['AR'] if es_local else row['HR'],
                    'GolesTotales': row['FTHG'] if es_local else row['FTAG'],
                    'GolesHT': row['HTHG'] if es_local else row['HTAG'],
                    'Goles2T': (row['FTHG']-row['HTHG']) if es_local else (row['FTAG']-row['HTAG']),
                    'corneTot': row['HC'] if es_local else row['AC'],
                    'TargAmTot': row['HY'] if es_local else row['AY'],
                }
            else: # En contra
                mapa = {
                    'FTHG': row['FTAG'] if es_local else row['FTHG'],
                    'FTAG': row['FTHG'] if es_local else row['FTAG'],
                    'HTHG': row['HTAG'] if es_local else row['HTHG'],
                    'HTAG': row['HTHG'] if es_local else row['HTAG'],
                    'HS': row['AS'] if es_local else row['HS'],
                    'AS': row['HS'] if es_local else row['AS'],
                    'HST': row['AST'] if es_local else row['HST'],
                    'AST': row['HST'] if es_local else row['AST'],
                    'HF': row['AF'] if es_local else row['HF'],
                    'AF': row['HF'] if es_local else row['AF'],
                    'HC': row['AC'] if es_local else row['HC'],
                    'AC': row['HC'] if es_local else row['AC'],
                    'HY': row['AY'] if es_local else row['HY'],
                    'AY': row['HY'] if es_local else row['AY'],
                    'HR': row['AR'] if es_local else row['HR'],
                    'AR': row['HR'] if es_local else row['AR'],
                    'GolesTotales': row['FTAG'] if es_local else row['FTHG'],
                    'GolesHT': row['HTAG'] if es_local else row['HTHG'],
                    'Goles2T': (row['FTAG']-row['HTAG']) if es_local else (row['FTHG']-row['HTHG']),
                    'corneTot': row['AC'] if es_local else row['HC'],
                    'TargAmTot': row['AY'] if es_local else row['HY'],
                }
            return mapa.get(col, row[col])

        if equipo_filtro!= "Ninguno" and alcance_filtro!= "Todo":
            df_final['_val'] = df_final.apply(lambda r: valor_equipo(r, columna_filtro, equipo_filtro), axis=1)
            col_usar = '_val'
        else:
            col_usar = columna_filtro

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



    # === APLICAR FILTRO DE CUOTAS B365 ===
    if cuota_tipo!= "Ninguno": # Ninguno = filtro desactivado
        if cuota_tipo == "Todo":
            # Mostrar partidos donde CUALQUIERA de las tres cuotas esté entre min y max
            cols_cuotas = ['B365H', 'B365D', 'B365A']
            for col_cuota in cols_cuotas:
                if col_cuota in df_final.columns:
                    df_final[col_cuota] = pd.to_numeric(df_final[col_cuota], errors='coerce')

            for col in ['B365H','B365D','B365A']:
                df_final[col] = pd.to_numeric(df_final[col], errors='coerce')
            mask = (
                ((df_final['B365H'] >= rango_cuotas[0]) & (df_final['B365H'] <= rango_cuotas[1])) |
                ((df_final['B365D'] >= rango_cuotas[0]) & (df_final['B365D'] <= rango_cuotas[1])) |
                ((df_final['B365A'] >= rango_cuotas[0]) & (df_final['B365A'] <= rango_cuotas[1]))
            )
            df_final = df_final[mask]

        else:
            # Filtro específico 1, X o 2: entre min y max + que haya ganado
            col_cuota = {'1': 'B365H', 'X': 'B365D', '2': 'B365A'}[cuota_tipo]
            ftr_esperado = {'1': 'H', 'X': 'D', '2': 'A'}[cuota_tipo]

            if col_cuota in df_final.columns:
                df_final[col_cuota] = pd.to_numeric(df_final[col_cuota], errors='coerce')
                df_final = df_final[df_final[col_cuota].notna()]

                df_final = df_final[
                    (df_final[col_cuota] >= rango_cuotas[0]) &
                    (df_final[col_cuota] <= rango_cuotas[1])
                ]

                df_final = df_final[df_final['FTR'] == ftr_esperado]
    # === FIN FILTRO CUOTAS ===
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
    if parte_gol!= "Todo" and equipo_filtro!= "Ninguno":
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

        st.markdown(f"""
        <div style='background-color:#f3f4f6; padding:12px; border-radius:8px; margin:10px 0; font-size:14px'>
            <b>{equipo_filtro} ({condicion_filtro}):</b><br>
            Gana: <b>{gana} / {total}</b> |
            Empata: <b>{empata} / {total}</b> |
            Pierde: <b>{pierde} / {total}</b> |
            Gana/Empata: <b>{gana_empata} / {total}</b> |
            Pierde/Empata: <b>{pierde_empata} / {total}</b>
        </div>
        """, unsafe_allow_html=True)

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

            html1 = ''.join(formatear_h2h_compacto(r, equipo_filtro) for _, r in df1.iterrows())
            html2 = ''.join(formatear_h2h_compacto(r, equipo2_filtro) for _, r in df2.iterrows())

            h2h_html = f"""
            <div style="display:flex; flex-direction:row; width:100%;">
             <div style="width:50%; padding-right:2px; box-sizing:border-box;">
              <div style="font-weight:700; font-size:11px; text-align:center; margin-bottom:2px;">{equipo_filtro} ({len(df1)})</div>
              <div style="height:700px; overflow-y:auto; overflow-x:hidden; border-right:1px solid #ddd;">{html1}</div>
             </div>
             <div style="width:50%; padding-left:2px; box-sizing:border-box;">
              <div style="font-weight:700; font-size:11px; text-align:center; margin-bottom:2px;">{equipo2_filtro} ({len(df2)})</div>
              <div style="height:700px; overflow-y:auto; overflow-x:hidden;">{html2}</div>
             </div>
            </div>
            """
            st.markdown(h2h_html, unsafe_allow_html=True)
        else:
            df_mostrar = df_final.sort_values(['Jornada','Date'], ascending=[False, False]).reset_index(drop=True)
            MAX_FILAS = 150
            if len(df_mostrar) > MAX_FILAS:
                st.warning(f"Mostrando {MAX_FILAS} de {len(df_mostrar)} partidos")
                df_mostrar = df_mostrar.head(MAX_FILAS)
            if len(df_mostrar) > 0:
                df_mostrar['partidos'] = df_mostrar.apply(lambda row: formatear_partido(row, equipo_filtro, cuota_tipo, row.get('Goles','')), axis=1)
            st.caption(f"Mostrando {len(df_mostrar)} partidos")
            html_table = df_mostrar[['partidos']].to_html(escape=False, index=False, classes='dataframe')
            st.markdown(f'<div style="height:700px; overflow-y:auto;">{html_table}</div>', unsafe_allow_html=True)

    with st.expander("ℹ Info jornadas", key="exp_info"):
        for liga in liga_sel:
            for temp in temp_sel:
                subset = df_fil[(df_fil['League']==liga) & (df_fil['Season']==temp)]
                if not subset.empty:
                    equipos = pd.unique(subset[['HomeTeam','AwayTeam']].values.ravel())
                    n_equipos = len(equipos)
                    st.write(f"**{liga} {temp}**: {n_equipos} equipos → {n_equipos//2} partidos por jornada")

    with st.expander("🔥 Filtro Rachas", expanded=False, key="exp_rachas"):
        c1, c2, c3, c4 = st.columns([1.2, 1.3, 0.9, 1.0])
        tipo = c1.selectbox("Tipo", ["Seguidos", "%"], key="r_tipo")
        cond = c2.selectbox("Condición", ["Gana","Pierde","Empata","Gana/Empata","Empata/Pierde","Gana/Pierde"], key="r_cond")
        donde = c4.selectbox("Dónde", ["Todo","Local","Visitante"], key="r_donde")
        if tipo == "Seguidos":
            x = c3.number_input("X seguidos", 1, 20, 3, key="r_x")
        else:
            pct_min = c3.slider("% mínimo", 0, 100, 50, key="r_pct")
        src = df_final.copy()
        if not src.empty:
            t = _rachas(src, cond, donde)
            if tipo == "Seguidos":
                res = t[t['Seguidos'] >= x].sort_values(['Seguidos','%'], ascending=False)
            else:
                res = t[t['%'] >= pct_min].sort_values(['%','Seguidos'], ascending=False)
            st.dataframe(
                res[['Equipo']],
                use_container_width=True,
                hide_index=True,
                height=500,
                key="tabla_rachas_estable",
                column_config={"Equipo": st.column_config.TextColumn("Resumen / Jornadas")}
            )