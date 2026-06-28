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


st.markdown("""
<style>
[data-testid="stDeployButton"] {display: none !important;}
[data-testid="stToolbar"] {display: none !important;}
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
.block-container {padding-top: 1rem;}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def cargar_csv():
    import os
    import re
    dfs = [pd.read_csv('ligas_2122_a_2526.csv', low_memory=False)]
    if os.path.exists('laliga_2425_partidos.csv'):
        dfs.append(pd.read_csv('laliga_2425_partidos.csv', low_memory=False))

    df = pd.concat(dfs, ignore_index=True)

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
    archivo_goles = 'laliga_2425_goles.csv'
    if not os.path.exists(archivo_goles):
        return {}

    df_g = pd.read_csv(archivo_goles, low_memory=False)

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
    totales_inline = ""
    if any([tot_a, tot_r, tot_c, tot_g, tot_f, tot_s]):
        totales_inline = f" <span style='color:#9ca3af; margin:0 8px'>|</span><span style='font-weight:700; color:#111; font-style:normal!important'>TOT:</span> {''.join([p for p in totales_partes if p])}"
    # Resultado HT/FT abreviado
    # Resultado HT/FT - si hay equipo filtrado, muestra G/P/E en color
    if equipo_filtro and equipo_filtro != "Ninguno":
        if equipo_filtro == ht: htgf, htgc = hthg, htag; gf, gc = hg_num, ag_num
        else: htgf, htgc = htag, hthg; gf, gc = ag_num, hg_num
        ht_res = 'G' if htgf > htgc else 'P' if htgf < htgc else 'E'
        ft_res = 'G' if gf > gc else 'P' if gf < gc else 'E'
        color_res = "#0f8105ff" if ft_res == 'G' else "#f31818" if ft_res == 'P' else "#f89007ff"
    else:
        ht_res = abreviar_equipo(ht) if hthg > htag else abreviar_equipo(at) if hthg < htag else 'E'
        ft_res = abreviar_equipo(ht) if hg_num > ag_num else abreviar_equipo(at) if hg_num < ag_num else 'E'
        color_res = "#444"
    res_inline = f" <span style='color:#9ca3af; margin:0 8px'>|</span><span style='font-weight:700; color:{color_res}; font-style:normal!important'>{ht_res}/{ft_res}</span>"
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
            ###############ajustar tamaño Línea de cuotas###################
            cuotas_html = f"<div style='font-size:9px; margin-bottom:2px; font-style:normal!important'>{league} | <span style='{h_style}'>{h_txt}</span>&nbsp;&nbsp;<span style='{d_style}'>{d_txt}</span>&nbsp;&nbsp;<span style='{a_style}'>{a_txt}</span>{re_fail_txt}{totales_inline}{res_inline}</div>"
        except:
            cuotas_html = ""
             ###############ajustar tamaño Línea del partido (equipos y marcador)###################
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

    linea_partido = f"<span style='font-style:normal!important'>{fecha} | {jornada} | {ht_txt} {hg_txt}-{ag_txt} {at_txt} | {hpts_txt}-{apts_txt} pts | {hpos_txt} vs {apos_txt}</span>"
    #
    es_local_ganador = hg_num > ag_num; es_visit_ganador = ag_num > hg_num; es_local_filtrado = equipo_filtro == row['HomeTeam']; es_visit_filtrado = equipo_filtro == row['AwayTeam']
    
    # h1t - SOLO GOLES (es lo único que tenemos por parte)
    h1t_home_styles = []
    h1t_away_styles = []
    if es_local_filtrado: h1t_home_styles.append("text-decoration:underline; text-decoration-thickness:2px")
    if es_local_ganador: h1t_home_styles.append("font-weight:900")
    if es_visit_filtrado: h1t_away_styles.append("text-decoration:underline; text-decoration-thickness:2px")
    if es_visit_ganador: h1t_away_styles.append("font-weight:900")
    
    h1t_home = f"<span style=\"{';'.join(h1t_home_styles)}\">h1t: {hthg}G</span>" if h1t_home_styles else f"h1t: {hthg}G"
    h1t_away = f"<span style=\"{';'.join(h1t_away_styles)}\">h1t: {htag}G</span>" if h1t_away_styles else f"h1t: {htag}G"
    linea_stats = f"<div style='margin-top:1px; line-height:1.1; font-size:7.5px; display:flex; gap:12px; white-space:nowrap'><span>{h1t_home}</span><span>{h1t_away}</span></div>"
    
    # h2t - SOLO GOLES
    style_h2_home = []
    style_h2_away = []
    if es_local_filtrado: style_h2_home.append("text-decoration:underline; text-decoration-thickness:2px")
    if es_local_ganador: style_h2_home.append("font-weight:900")
    if es_visit_filtrado: style_h2_away.append("text-decoration:underline; text-decoration-thickness:2px")
    if es_visit_ganador: style_h2_away.append("font-weight:900")
    h2t_home = f"<span style=\"{';'.join(style_h2_home)}\">h2t: {h2tg}G</span>" if style_h2_home else f"<span>h2t: {h2tg}G</span>"
    h2t_away = f"<span style=\"{';'.join(style_h2_away)}\">h2t: {a2tg}G</span>" if style_h2_away else f"<span>h2t: {a2tg}G</span>"
    linea_stats += f"<div style='line-height:1.1; font-size:7.5px; color:#555; display:flex; gap:12px; white-space:nowrap'>{h2t_home}{h2t_away}</div>"
    # stats totales por equipo (tiros, tiros puerta, faltas, corners, amarillas, rojas)
    stats_home_styles = []
    stats_away_styles = []
    if es_local_filtrado: stats_home_styles.append("text-decoration:underline; text-decoration-thickness:2px")
    if es_local_ganador: stats_home_styles.append("font-weight:900")
    if es_visit_filtrado: stats_away_styles.append("text-decoration:underline; text-decoration-thickness:2px")
    if es_visit_ganador: stats_away_styles.append("font-weight:900")
    
    stats_home_txt = f"{hs}T {hst}TP {hf}F {hc}C {hy}A {hr}R"
    stats_away_txt = f"{as_}T {ast}TP {af}F {ac}C {ay}A {ar}R"
    
    stats_home = f"<span style=\"{';'.join(stats_home_styles)}\">{stats_home_txt}</span>" if stats_home_styles else stats_home_txt
    stats_away = f"<span style=\"{';'.join(stats_away_styles)}\">{stats_away_txt}</span>" if stats_away_styles else stats_away_txt
    
    linea_stats += f"<div style='line-height:1.1; font-size:7px; color:#222; display:flex; gap:12px; white-space:nowrap; margin-top:1px'><span>{stats_home}</span><span>{stats_away}</span></div>"
    partido_html = linea_partido + linea_stats
    
    goles_html = f"<div style='margin-top:3px; line-height:1.2; font-size:9px; color:#333; white-space:normal'>{goles_txt}</div>" if goles_txt else ""
    return f'<div translate="no">{cuotas_html}{partido_html}{goles_html}</div>'

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
        badges.append(balon_con_numero('HT', gol_ht)); badges.append(balon_con_numero('2T', gol_2t))
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
    df = df.sort_values(['League','Season','Date']).reset_index(drop=True)

    df['Jornada'] = 0
    for (liga, temp), idx in df.groupby(['League','Season']).groups.items():
        grupo_liga = df.loc[idx].sort_values('Date').copy()
        equipos = pd.unique(grupo_liga[['HomeTeam','AwayTeam']].values.ravel())
        n_equipos = len(equipos)
        partidos_por_jornada = n_equipos // 2

        jornadas = []
        jornada_actual = 1
        contador = 0

        for i in range(len(grupo_liga)):
            jornadas.append(jornada_actual)
            contador += 1
            if contador >= partidos_por_jornada:
                jornada_actual += 1
                contador = 0

        df.loc[idx, 'Jornada'] = jornadas

    df['Jornada'] = df['Jornada'].astype(int)

    df['HPts'] = df['FTR'].apply(lambda x: 3 if x == 'H' else 1 if x == 'D' else 0)
    df['APts'] = df['FTR'].apply(lambda x: 3 if x == 'A' else 1 if x == 'D' else 0)

    datos = []
    tablas_por_jornada = []

    for (liga, temp), grupo in df.groupby(['League','Season']):
        equipos = pd.unique(grupo[['HomeTeam','AwayTeam']].values.ravel())
        tabla = {eq: {'Pts': 0, 'PJ': 0, 'PG': 0, 'PE': 0, 'PP': 0, 'GF': 0, 'GC': 0, 'DG': 0} for eq in equipos}

        grupo = grupo.sort_values(['Jornada','Date'])
        jornada_prev = None

        for idx, row in grupo.iterrows():
            h, a = row['HomeTeam'], row['AwayTeam']
            orden = sorted(tabla.items(), key=lambda x: (x[1]['Pts'], x[1]['DG'], x[1]['GF']), reverse=True)
            pos = {eq: i+1 for i, (eq, _) in enumerate(orden)}

            if jornada_prev is not None and row['Jornada']!= jornada_prev:
                tabla_j = pd.DataFrame.from_dict(tabla, orient='index')
                tabla_j['Equipo'] = tabla_j.index
                tabla_j['Pos'] = tabla_j['Pts'].rank(method='min', ascending=False).astype(int)
                tabla_j = tabla_j.sort_values(['Pts', 'DG', 'GF'], ascending=[False, False, False])
                tabla_j['Jornada'] = jornada_prev
                tabla_j['League'] = liga
                tabla_j['Season'] = temp
                tablas_por_jornada.append(tabla_j)

            datos.append({
                'idx': idx,
                'HomePtsPrev': tabla[h]['Pts'],
                'AwayPtsPrev': tabla[a]['Pts'],
                'HomePosPrev': pos[h],
                'AwayPosPrev': pos[a]
            })

            tabla[h]['PJ'] += 1
            tabla[a]['PJ'] += 1
            tabla[h]['GF'] += row['FTHG']
            tabla[h]['GC'] += row['FTAG']
            tabla[a]['GF'] += row['FTAG']
            tabla[a]['GC'] += row['FTHG']

            if row['FTR'] == 'H':
                tabla[h]['Pts'] += 3
                tabla[h]['PG'] += 1
                tabla[a]['PP'] += 1
            elif row['FTR'] == 'A':
                tabla[a]['Pts'] += 3
                tabla[a]['PG'] += 1
                tabla[h]['PP'] += 1
            else:
                tabla[h]['Pts'] += 1
                tabla[a]['Pts'] += 1
                tabla[h]['PE'] += 1
                tabla[a]['PE'] += 1

            tabla[h]['DG'] = tabla[h]['GF'] - tabla[h]['GC']
            tabla[a]['DG'] = tabla[a]['GF'] - tabla[a]['GC']
            jornada_prev = row['Jornada']

        tabla_j = pd.DataFrame.from_dict(tabla, orient='index')
        tabla_j['Equipo'] = tabla_j.index
        tabla_j['Pos'] = tabla_j['Pts'].rank(method='min', ascending=False).astype(int)
        tabla_j = tabla_j.sort_values(['Pts', 'DG', 'GF'], ascending=[False, False, False])
        tabla_j['Jornada'] = jornada_prev
        tabla_j['League'] = liga
        tabla_j['Season'] = temp
        tablas_por_jornada.append(tabla_j)

    if datos:
        df_temp = pd.DataFrame(datos).set_index('idx')
        df = df.join(df_temp)
    else:
        # si no hay datos (liga vacía), crea las columnas a 0
        df['HomePtsPrev'] = 0
        df['AwayPtsPrev'] = 0
        df['HomePosPrev'] = 0
        df['AwayPosPrev'] = 0

    df_clasificacion = pd.concat(tablas_por_jornada, ignore_index=True) if tablas_por_jornada else pd.DataFrame()

    
    df['ResHtFt'] = df.apply(resultado_ht_ft, axis=1)
#####funcion rachas
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

def render_tabla_equipo(df_input, equipo_ref, todos_eventos, rango_minutos, parte_gol, jugador_filtro, cuota_tipo):
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
    


def limpiar_filtros():
    st.session_state.columna_filtro = "Ninguno"
    st.session_state.operador_filtro = "Ninguno"
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

liga_sel = col1.multiselect("Liga", ligas_disponibles, default=ligas_disponibles)
temp_sel = col2.multiselect("Temporada", temporadas_disponibles, default=temporadas_disponibles)

if not liga_sel: 
    liga_sel = ligas_disponibles
if not temp_sel: 
    temp_sel = temporadas_disponibles

modo_vista = col4.selectbox("Modo vista", ["Jornadas", "Clasificación"])

df_fil = df[df['League'].isin(liga_sel) & df['Season'].isin(temp_sel)]

if df_fil.empty:
    st.stop()

with st.spinner('Calculando clasificación...'):
    df_final, df_clasificacion = calcular_estado_jornada(df_fil)

jornadas = sorted(df_final['Jornada'].unique())
jornada_sel = col3.multiselect("Jornada específica", jornadas, format_func=lambda x: f"Jornada {x}")

if len(jornadas) > 0:
    min_j, max_j = int(min(jornadas)), int(max(jornadas))
    rango_jornadas = col3.slider(
        "Rango de jornadas",
        min_value=min_j,
        max_value=max_j,
        value=(min_j, max_j),
        help="Selecciona desde qué jornada hasta qué jornada mostrar"
    )
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
    if 'operador_filtro' not in st.session_state: st.session_state.operador_filtro = "Ninguno"
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

    columnas_numericas = ['FTHG','FTAG','HTHG','HTAG','HS','AS','HST','AST','HF','AF','HC','AC','HY','AY','HR','AR','GolesTotales','GolesHT','Goles2T','corneTot','TargAmTot','HomePtsPrev','AwayPtsPrev','HomePosPrev','AwayPosPrev']
    equipos_disponibles = sorted(pd.unique(df_final[['HomeTeam','AwayTeam']].values.ravel()))

    # FILA 1 - 3 desplegables
    c1, c2, c3 = st.columns(3)
    columna_filtro = c1.selectbox("Columna", ["Ninguno"] + columnas_numericas, key='columna_filtro')
    operador_filtro = c2.selectbox("Op", ["Ninguno", "=", ">", ">=", "<", "<="], key='operador_filtro')
    valor_filtro = c3.selectbox("Valor", ["Ninguno"] + [i/2 for i in range(81)], key='valor_filtro')

    # FILA 2 - 3 desplegables
    c4, c4b, c5, c6 = st.columns(4)
    equipo_filtro = c4.selectbox("Equipo", ["Ninguno"] + equipos_disponibles, key='equipo_filtro')
    equipo2_filtro = c4b.selectbox("Equipo 2", ["Ninguno"] + equipos_disponibles, key='equipo2_filtro')
    condicion_filtro = c5.selectbox("Local/Vis", ["Todo", "Local", "Visitante"], key='condicion_filtro')
    alcance_filtro = c6.selectbox("Alcance", ["Todo","A favor","En contra"], key='alcance_filtro', help="Todo=total del partido | A favor=lo que hace tu equipo | En contra=lo que recibe")
    # FILA 3 - 3 desplegables
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

    c7, c8, c9 = st.columns(3)
    htft_filtro = c7.selectbox("HT/FT", ["Todo","G/G","G/E","G/P","E/G","E/E","E/P","P/G","P/E","P/P","RE","FAIL"], key='htft_filtro')
    resultado_filtro = c8.selectbox("Resultado", ["Ninguno","Gana","Pierde","Empata","Gana/Empata","Gana/Pierde","Empata/Pierde"], key='resultado_filtro')
    ambos_marcan = c9.selectbox("BTTS", ["Todos","Sí","No"], key='ambos_marcan')

    # FILA 4 - cuotas
    c10, c11, c12 = st.columns([1,2,1])
    cuota_tipo = c10.selectbox("Cuota", ["Ninguno","Todo","1","X","2"], key='cuota_tipo')
    rango_cuotas = c11.slider("Rango cuotas", 1.0, 40.0, st.session_state.rango_cuotas, 0.05, key='rango_cuotas')
    jugador_filtro = c12.selectbox("Jugador", ["TODOS"] + lista_jug, key='jugador_filtro')
    st.button("Limpiar", on_click=limpiar_filtros, use_container_width=False)

    # FILA 5 - minutos
    c13, c14 = st.columns([3,1])
    rango_minutos = c13.slider("Minutos", 0, 120, st.session_state.rango_minutos, 1, key='rango_minutos')
    parte_gol = c14.selectbox("Parte", ["Todo","1T","2T"], key='parte_gol')
   
    # === FIN FILTRO GOLES ===
    if columna_filtro!= "Ninguno" and operador_filtro!= "Ninguno" and valor_filtro!= "Ninguno":
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
        df_final['partidos'] = df_final.apply(lambda row: formatear_partido(row, equipo_filtro, cuota_tipo, row.get('Goles','')), axis=1)
        df_final['Tarjetas/Corners/goles'] = df_final.apply(lambda row: crear_columna_tarjetas_corners(row, equipo_filtro), axis=1)
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
    css = """
    <style>
    table {border-collapse:collapse; width:100%; font-size:9px; font-family:'Source Code Pro',monospace; table-layout:fixed; margin:0;}
    thead {display:none;}
    td {padding:3px 5px!important; border-bottom:2px solid #000!important; border-left:1px solid #d1d5db; border-right:1px solid #d1d5db; vertical-align:middle; line-height:1.15;}
    tr:nth-child(even){background:#f9fafb;} tr:hover{background:#e5e7eb;}
    [data-testid="stHorizontalBlock"]{gap:0.2rem!important;}
    [data-testid="column"]{padding:0 2px!important;}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
    
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
    with st.expander("📋 Partidos", expanded=True, key="exp_partidos"):
        if equipo_filtro!= "Ninguno" and equipo2_filtro!= "Ninguno":
            df1 = df_base_h2h[(df_base_h2h['HomeTeam']==equipo_filtro) | (df_base_h2h['AwayTeam']==equipo_filtro)]
            df2 = df_base_h2h[(df_base_h2h['HomeTeam']==equipo2_filtro) | (df_base_h2h['AwayTeam']==equipo2_filtro)]
            col_izq, col_der = st.columns(2, gap="small")
            with col_izq:
                st.caption(f"Mostrando {len(df1)} partidos de {equipo_filtro}")
                st.markdown(f'<div style="height:700px; overflow-y:auto;">{render_tabla_equipo(df1, equipo_filtro)}</div>', unsafe_allow_html=True)
            with col_der:
                st.caption(f"Mostrando {len(df2)} partidos de {equipo2_filtro}")
                st.markdown(f'<div style="height:700px; overflow-y:auto;">{render_tabla_equipo(df2, equipo2_filtro)}</div>', unsafe_allow_html=True)
        else:
            if len(df_final) > 0:
                df_final['partidos'] = df_final.apply(lambda row: formatear_partido(row, equipo_filtro, cuota_tipo, row.get('Goles','')), axis=1)
            df_mostrar = df_final.sort_values(['Jornada','Date'], ascending=[False, False]).reset_index(drop=True)
            MAX_FILAS = 150
            if len(df_mostrar) > MAX_FILAS:
                st.warning(f"Mostrando {MAX_FILAS} de {len(df_mostrar)} partidos")
                df_mostrar = df_mostrar.head(MAX_FILAS)
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

    # ==================== FILTRO RACHAS ====================
   

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
    
