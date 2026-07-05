
import re
import unicodedata
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt  # type: ignore
import os
from functools import lru_cache
import json
from datetime import datetime
import subprocess
import sys
import time
import streamlit.components.v1 as components  # <-- ESTA ES LA LÍNEA NUEVA

st.set_page_config(
    page_title="Filtro Jornada", 
    layout="wide",
    initial_sidebar_state="expanded"  # <-- ESTO FUERZA EL SIDEBAR ABIERTO
)

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

/* PEGA ESTO AQUÍ - FIX SCROLL EXPANDER */
div[data-testid="stExpander"] div[data-testid="stExpanderDetails"] {
    max-height: none !important;
    overflow: visible !important;
}

div[data-testid="stExpander"]:has(> details > summary:contains("Filtros de partidos")) div[data-testid="stExpanderDetails"] {
    max-height: 80vh !important;
    overflow-y: auto !important;
    padding-right: 10px;
}

</style>
""", unsafe_allow_html=True)


# --- LIMPIEZA FORZADA DE CACHE VIEJO --- (ahora con botón)

def normaliza(nombre: str) -> str:
    # quita acentos, pasa a mayúsculas, limpia espacios
    n = unicodedata.normalize('NFKD', str(nombre))
    n = n.encode('ASCII', 'ignore').decode('ASCII')
    n = n.upper().strip()
    n = re.sub(r'\s+', ' ', n)
    return n
@lru_cache(maxsize=2048)
def abreviar_equipo(nombre):
    n = normaliza(nombre)

    # --- PARCHE DURO: Atlético de Madrid SIEMPRE ATM ---
    if 'ATLETICO' in n or n.startswith('ATLETI') or n in ('ATH MADRID','ATH. MADRID','AT MADRID','ATM'):
        return 'ATM'

    # --- PARCHE DURO: Athletic Club SIEMPRE ATH ---
    if 'ATHLETIC' in n or 'BILBAO' in n:
        return 'ATH'

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
        # España
        'ATLETICO MADRID': 'ATM', 'ATLETICO DE MADRID': 'ATM',
        'ATHLETIC BILBAO': 'ATH', 'ATHLETIC CLUB': 'ATH',
        'REAL MADRID': 'RMA', 'BARCELONA': 'FCB', 'FC BARCELONA': 'FCB',
        'BETIS': 'BET', 'REAL BETIS': 'BET', 'BETIS SEVILLA': 'BET',
        'SEVILLA': 'SEV', 'VALENCIA': 'VAL', 'VILLARREAL': 'VIL',
        'REAL SOCIEDAD': 'RSO', 'CELTA': 'CEL', 'CELTA VIGO': 'CEL',
        'OSASUNA': 'OSA', 'GETAFE': 'GET', 'ALAVES': 'ALA',
        'GIRONA': 'GIR', 'LAS PALMAS': 'LPA', 'MALLORCA': 'MAL',
        'RAYO VALLECANO': 'RAY', 'ESPANYOL': 'ESP', 'LEGANES': 'LEG',
        'VALLADOLID': 'VLL', 'LEVANTE': 'LEV', 'LEVANTE UD': 'LEV',
        'ELCHE': 'ELC', 'ELCHE CF': 'ELC',
        'REAL OVIEDO': 'OVI', 'OVIEDO': 'OVI',
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
    return (n.split()[0][:3]).upper()


#####################jornadas conteo
def jornadas_conteo(jornadas, df_ref=None, equipo=None, rival=None):
    from collections import Counter
    if df_ref is None or equipo is None:
        c = Counter(jornadas)
        return " | ".join([f"J{int(j)} - {c[j]}#" if c[j]>1 else f"J{int(j)}" for j in sorted(c)])

    df_eq = df_ref[(df_ref['HomeTeam']==equipo) | (df_ref['AwayTeam']==equipo)].copy()
    if df_eq.empty:
        return ""

    is_home = df_eq['HomeTeam']==equipo
    df_eq['res'] = np.where(
    (is_home & (df_eq['FTHG']>df_eq['FTAG'])) | (~is_home & (df_eq['FTAG']>df_eq['FTHG'])),
    'win',
    np.where(
        (is_home & (df_eq['FTHG']<df_eq['FTAG'])) | (~is_home & (df_eq['FTAG']<df_eq['FTHG'])),
        'loss',
        'draw'
    )
)

    partes = []
    for (season, j), g in df_eq.groupby(['Season','Jornada'], sort=True):
        if (g['res']=='win').all():
            color = '#0f8105'
        elif (g['res']=='loss').all():
            color = '#f31818'
        else:
            color = '#0A2342'

        es_local = (g['HomeTeam']==equipo).iloc[0]
        sufijo = 'c' if es_local else 'f'
        txt = f"J{int(j)}{sufijo}"

        # CAMBIO: añadir. si hay AM en algún partido de esa jornada
        if ((g['FTHG'] > 0) & (g['FTAG'] > 0)).any():
            txt += '●'

        if len(g) > 1:
            txt += f" - {len(g)}#"

        es_h2h = False
        if rival:
            es_h2h = (((g['HomeTeam']==equipo) & (g['AwayTeam']==rival)) |
                      ((g['HomeTeam']==rival) & (g['AwayTeam']==equipo))).any()

        partidos_html = []
        for _, r in g.iterrows():
            partido_completo = formatear_partido(r, equipo, None, "")
            partidos_html.append(f"<div style='margin-bottom:6px'>{partido_completo}</div>")

        viñeta = "".join(partidos_html)

        estilos = []
        if color: estilos.append(f"color:{color};font-weight:700")
        if es_h2h: estilos.append("text-decoration:underline;text-decoration-thickness:2px")

        jx_html = f"""<details style="display:inline-block">
            <summary style="{';'.join(estilos)};cursor:pointer;list-style:none;display:inline">{txt}</summary>
            <div style="position:absolute;z-index:999;background:#FFFFFF;border:2px solid #000;padding:6px;margin-top:2px;box-shadow:2px 2px 6px rgba(0,0,0.3);max-width:280px">{viñeta}</div>
        </details>"""

        partes.append(jx_html)
    return " | ".join(partes)







st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
with st.expander("⚙ Opciones avanzadas"):
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🧪 Borrar cache", use_container_width=True):
            for f in ['ligas_2122_a_2526.parquet', 'ligas_2122_a_2526.parquet.lock']:
                if os.path.exists(f):
                    os.remove(f)
            st.cache_data.clear()
            st.rerun()

    with col_b:
        if st.button("🔄 Actualizar 25/26", type="primary", use_container_width=True):
            with st.spinner("Descargando jornadas nuevas..."):
                try:
                    result = subprocess.run(
                        [sys.executable, "actualizar_ligas.py"], 
                        capture_output=True, 
                        text=True, 
                        timeout=180
                    )
                    st.code(result.stdout)
                    if result.returncode == 0:
                        st.cache_data.clear()
                        for f in ['ligas_2122_a_2526.parquet', 'ligas_2122_a_2526.parquet.lock']:
                            if os.path.exists(f):
                                os.remove(f)
                        st.success("✅ Actualizado")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Falló")
                        st.code(result.stderr)
                except Exception as e:
                    st.error(f"Error: {e}")
# --- FIN BOTONES ---

# --- INICIALIZAR SESSION STATE ---
if 'rango_cuotas' not in st.session_state: 
    st.session_state.rango_cuotas = (1.5, 10.0)
if 'rango_minutos' not in st.session_state: 
    st.session_state.rango_minutos = (0, 120)
if 'pct_marcador' not in st.session_state: 
    st.session_state.pct_marcador = 0


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
    import os, re
    # 1. Carga base
    if os.path.exists('ligas_2122_a_2526.parquet'):
        df = pd.read_parquet('ligas_2122_a_2526.parquet')
    else:
        df = pd.read_csv('ligas_2122_a_2526.csv', low_memory=False)

    # 2. ¿Necesitamos el parche de LaLiga 24/25?
    tiene_laliga_2425 = ((df['League'] == 'LaLiga') & (df['Season'] == '2024/2025')).any()

    if not tiene_laliga_2425:
        df2 = None
        if os.path.exists('laliga_2425_partidos.parquet'):
            df2 = pd.read_parquet('laliga_2425_partidos.parquet')
        elif os.path.exists('laliga_2425_partidos.csv'):
            df2 = pd.read_csv('laliga_2425_partidos.csv', low_memory=False)

        if df2 is not None and not df2.empty:
            df = pd.concat([
                df[~((df['League']=='LaLiga') & (df['Season']=='2024/2025'))],
                df2
            ], ignore_index=True)

    # 3. Resto igual (limpieza)
    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
    df = df[df['Date'].notna()]

    df['__tiene_cuota'] = df['B365H'].astype(str).str.strip().ne('') & df['B365H'].notna()
    df = df.sort_values('__tiene_cuota', ascending=False)
    df = df.drop_duplicates(subset=['Date','HomeTeam','AwayTeam','League'], keep='first')
    df = df.drop(columns='__tiene_cuota')

    for col in ['League','Season','HomeTeam','AwayTeam']:
        df[col] = df[col].astype(str).str.strip().str.replace('"','').str.replace("'",'')
    for col in ['HomeTeam','AwayTeam']:
        df[col] = df[col].apply(normaliza)

    mapa_unifica = {
    'HERACLES ALMELO':'HERACLES','SC HERACLES ALMELO':'HERACLES','SC HERACLES':'HERACLES',
    'FC GRONINGEN':'GRONINGEN','PEC ZWOLLE':'ZWOLLE','FC ZWOLLE':'ZWOLLE',
    'FC VOLENDAM':'VOLENDAM','SC TELSTAR':'TELSTAR','AFC AJAX':'AJAX','AJAX AMSTERDAM':'AJAX',
    'AZ ALKMAAR':'AZ','PSV EINDHOVEN':'PSV','FC TWENTE':'TWENTE','FC TWENTE ENSCHEDE':'TWENTE',
    'FC UTRECHT':'UTRECHT','SC HEERENVEEN':'HEERENVEEN','SBV EXCELSIOR':'EXCELSIOR','EXCELSIOR ROTTERDAM':'EXCELSIOR',
    'ATLETICO DE MADRID':'ATLETICO MADRID',
    'ATH MADRID':'ATLETICO MADRID', 'ATH. MADRID':'ATLETICO MADRID', 'AT MADRID':'ATLETICO MADRID',
    'ATHLETIC CLUB':'ATHLETIC BILBAO',
    'VALLECANO':'RAYO VALLECANO','RAYO VALLECANO MADRID':'RAYO VALLECANO',
    'DEPORTIVO ALAVES':'ALAVES','LEVANTE UD':'LEVANTE',
    'ELCHE CF':'ELCHE', 'REAL OVIEDO':'OVIEDO',
}
    df['HomeTeam'] = df['HomeTeam'].replace(mapa_unifica)
    df['AwayTeam'] = df['AwayTeam'].replace(mapa_unifica)

    df = df.sort_values('Date')
    df['pair'] = df.apply(lambda r: tuple(sorted([r['HomeTeam'], r['AwayTeam']])), axis=1)
    df = df.sort_values('Date').groupby(['Season','League','pair'], as_index=False).head(2)
    df = df.drop(columns='pair')
    def norm_season(s):
        s = str(s)
        if re.match(r'^\d{4}/\d{4}$', s): return s
        if re.match(r'^\d{4}$', s): return f"20{s[:2]}/20{s[2:]}"
        return s
    df['Season'] = df['Season'].apply(norm_season)
    df = df[df['League'].notna() & (df['League']!='nan')]

    cols_num = ['FTHG','FTAG','HTHG','HTAG','HS','AS','HST','AST','HF','AF','HC','AC','HY','AY','HR','AR']
    for col in cols_num:
        df[col] = pd.to_numeric(df.get(col,0), errors='coerce').fillna(0)
    if 'FTR' not in df.columns:
        df['FTR'] = np.where(df['FTHG']>df['FTAG'],'H',np.where(df['FTHG']<df['FTAG'],'A','D'))
    for col in ['B365H','B365D','B365A']:
        df[col] = pd.to_numeric(df.get(col,np.nan), errors='coerce')
    
    ##########LOGICA: COLUMNAS CALCULADAS GOLES/STATS
    
    df['GolesTotales'] = df['FTHG']+df['FTAG']
    df['GolesHT'] = df['HTHG']+df['HTAG']
    df['HomeAbbr'] = df['HomeTeam'].apply(abreviar_equipo)
    df['AwayAbbr'] = df['AwayTeam'].apply(abreviar_equipo)
    df['Goles2T'] = df['GolesTotales']-df['GolesHT']
    df['corneTot'] = df['HC']+df['AC']
    df['TargAmTot'] = df['HY']+df['AY']
    df['tirosTot'] = df['HS']+df['AS']
    df['tirosPuertaTot'] = df['HST']+df['AST']
    df['faltasTot'] = df['HF']+df['AF']
    df['TargRojTot'] = df['HR']+df['AR']
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
    
    if 'asistente' not in df_g.columns:
        df_g['asistente'] = ''
    if 'tipo' not in df_g.columns:
        df_g['tipo'] = ''
    if 'equipo' not in df_g.columns:
        df_g['equipo'] = ''
    

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
     
##########LOGICA: GOLES POR MINUTO/JUGADOR
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
###################def formatear_partido


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

    NAVY = "#0A2342"
    style_base = f"color:{NAVY}; font-weight:600; font-size:9px; font-style:normal!important"
    style_ganador = f"color:{NAVY}; font-weight:900; font-size:9px; font-style:normal!important"
    style_subrayado = "text-decoration:underline; text-decoration-thickness:2px; font-style:normal!important"

    ht_res = ht_disp if hthg > htag else at_disp if hthg < htag else 'E'
    ft_res = ht_disp if hg_num > ag_num else at_disp if hg_num < ag_num else 'E'
    
    # Color del top_line según equipo_filtro
    color_res = "#444"
    eq_norm = normaliza(equipo_filtro) if equipo_filtro and equipo_filtro!= "Ninguno" else None
    if eq_norm:
        won = (eq_norm == ht and hg_num > ag_num) or (eq_norm == at and ag_num > hg_num)
        lost = (eq_norm == ht and hg_num < ag_num) or (eq_norm == at and ag_num < hg_num)
        color_res = "#0f8105" if won else "#f31818" if lost else "#f89007"

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

    # Colores por parte desde la perspectiva del equipo filtrado
    if eq_norm == ht:  # Waregem es local
        color_ht = "#0f8105" if hthg > htag else "#f31818" if hthg < htag else "#f89007"
        color_st = "#0f8105" if h2tg > a2tg else "#f31818" if h2tg < a2tg else "#f89007"
        color_ft = "#0f8105" if hg_num > ag_num else "#f31818" if hg_num < ag_num else "#f89007"
    elif eq_norm == at:  # Waregem es visitante
        color_ht = "#0f8105" if htag > hthg else "#f31818" if htag < hthg else "#f89007"
        color_st = "#0f8105" if a2tg > h2tg else "#f31818" if a2tg < h2tg else "#f89007"
        color_ft = "#0f8105" if ag_num > hg_num else "#f31818" if ag_num < hg_num else "#f89007"
    else:  # Sin filtro, desde perspectiva del local
        color_ht = "#0f8105" if hthg > htag else "#f31818" if hthg < htag else "#f89007"
        color_st = "#0f8105" if h2tg > a2tg else "#f31818" if h2tg < a2tg else "#f89007"
        color_ft = "#0f8105" if hg_num > ag_num else "#f31818" if hg_num < ag_num else "#f89007"
    
    ht_style = "font-weight:900" if hg_num > ag_num else "font-weight:600"
    at_style = "font-weight:900" if ag_num > hg_num else "font-weight:600"
    if eq_norm == ht:
        ht_style += ";text-decoration:underline;text-decoration-thickness:2px"
    if eq_norm == at:
        at_style += ";text-decoration:underline;text-decoration-thickness:2px"
    ##########lineas cartas partidos
    h1, a1 = hthg, htag
    h2, a2 = h2tg, a2tg
    ht_line = f"<div style='font-size:11px;color:{color_ht}'>1ªP: <span style='{ht_style}'>{ht_disp}</span> {h1}-{a1} <span style='{at_style}'>{at_disp}</span></div>"
    st_line = f"<div style='font-size:8px;color:{color_st}'>2ªP: <span style='{ht_style}'>{ht_disp}</span> {h2}-{a2} <span style='{at_style}'>{at_disp}</span></div>"
    ft_line = f"<div style='font-size:11px;color:{color_ft};font-weight:900'>FINAL: <span style='{ht_style}'>{ht_disp}</span> {hg_num}-{ag_num} <span style='{at_style}'>{at_disp}</span></div>"
    pos_line = f"<div style='font-size:9px'>{hpos_txt} vs {apos_txt}</div>"
    pts_line = f"<div style='font-size:9px'>{hpts_txt}-pts {apts_txt}</div>"
    perf_line = f"<div style='font-size:9px'>Perf:{home_perf_txt}-{away_perf_txt}</div>"

    def wrap(v, win, fil):
        s = style_ganador if win else style_base
        if fil: s += f"; {style_subrayado}"
        return f"<span style='{s}'>{v}</span>"

    h1_g = f"1p:{wrap(f'{hthg}G', hg_num>ag_num, eq_norm==ht)}"
    a1_g = f"1p:{wrap(f'{htag}G', ag_num>hg_num, eq_norm==at)}"
    h2_g = f"2p:{wrap(f'{h2tg}G', hg_num>ag_num, eq_norm==ht)}"
    a2_g = f"2p:{wrap(f'{a2tg}G', ag_num>hg_num, eq_norm==at)}"
    sh = wrap(f"{hs}T {hst}TP {hf}F {hc}C {hy}A {hr}R", hg_num>ag_num, eq_norm==ht)
    sa = wrap(f"{as_}T {ast}TP {af}F {ac}C {ay}A {ar}R", ag_num>hg_num, eq_norm==at)

    stats_html = f"<div style='font-size:7.5px'>{h1_g}</div><div style='font-size:7.5px'>{a1_g}</div><div style='font-size:7.5px'>{h2_g}</div><div style='font-size:7.5px'>{a2_g}</div><div style='font-size:7px'>{sh}</div><div style='font-size:7px'>{sa}</div>"

    goles_html = f"<div style='font-size:9px;color:{NAVY}'>{goles_txt}</div>" if goles_txt else ""
    return f'<div translate="no" lang="zxx" style="border-bottom:2px solid #000; padding-bottom:4px; margin-bottom:6px">{top_line}{date_line}{odds_html}{ht_line}{st_line}{ft_line}{pos_line}{pts_line}{perf_line}{stats_html}{goles_html}</div>'
####def formatear_h2h_compacto

def formatear_h2h_compacto(row, equipo_ref=None):
    NAVY = "#0A2342"
    league = str(row.get('League',''))[:3].upper()
    fecha = row['Date'].strftime('%d/%m/%y') if pd.notna(row['Date']) else ''
    jorn = f"J{int(row['Jornada'])}"
    try:
        h_od = float(row['B365H']); d_od = float(row['B365D']); a_od = float(row['B365A']); ftr = row.get('FTR','')
        s_win = "font-weight:900; color:#000"; s_norm = "color:#555"
        odds = f"<span style='{s_win if ftr=='H' else s_norm}'>{h_od:.2f}</span> <span style='{s_win if ftr=='D' else s_norm}'>{d_od:.2f}</span> <span style='{s_win if ftr=='A' else s_norm}'>{a_od:.2f}</span>"
    except:
        odds = ""

    ht = row.get('HomeAbbr', abreviar_equipo(row['HomeTeam'])); at = row.get('AwayAbbr', abreviar_equipo(row['AwayTeam']))
    hg, ag = int(row['FTHG']), int(row['FTAG'])
    h1, a1 = int(row['HTHG']), int(row['HTAG'])
    h2, a2 = hg - h1, ag - a1
    
    eq_norm = normaliza(equipo_ref) if equipo_ref else None
    is_h = eq_norm == row['HomeTeam']
    is_a = eq_norm == row['AwayTeam']

    def nv(t,b=False,u=False):
        return f"<span style='font-weight:{900 if b else 600}{';text-decoration:underline;text-decoration-thickness:2px' if u else ''}'>{t}</span>"

    if eq_norm:
        won = (is_h and hg > ag) or (is_a and ag > hg)
        lost = (is_h and hg < ag) or (is_a and ag < hg)
        color_linea = "#0f8105" if won else "#f31818" if lost else "#f89007"
        color_ht = "#0f8105" if h1 > a1 else "#f31818" if h1 < a1 else "#f89007"
        color_st = "#0f8105" if h2 > a2 else "#f31818" if h2 < a2 else "#f89007"
    else:
        color_linea = "#0A2342"
    
    ht_line = f"<span style='color:{color_linea}'>1ªP: {nv(ht,h1>a1,is_h)} {nv(h1,h1>a1,is_h)}-{nv(a1,a1>h1,is_a)} {nv(at,a1>h1,is_a)}</span>"
    st_line = f"<span style='color:{color_linea}'>2ªP: {nv(ht,h2>a2,is_h)} {nv(h2,h2>a2,is_h)}-{nv(a2,a2>h2,is_a)} {nv(at,a2>h2,is_a)}</span>"
    ft_line = f"<span style='color:{color_linea};font-weight:900'>FINAL: {nv(ht,hg>ag,is_h)} {nv(hg,hg>ag,is_h)}-{nv(ag,ag>hg,is_a)} {nv(at,ag>hg,is_a)}</span>"
    
    pos = f"{nv(str(int(row['HomePosPrev']))+'º',False,is_h)} <span style='color:#000'>vs</span> {nv(str(int(row['AwayPosPrev']))+'º',False,is_a)}"
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

    lineas = [
        f"{league} {res}",
        f"{fecha} |{jorn}|",
        odds,
        ht_line,
        st_line,
        ft_line,
        pos,
        pts,
        f"<span style='color:#000'>Perf:</span>{nv(round(float(row.get('HomePerf',0)),1),hg>ag,is_h)}-{nv(round(float(row.get('AwayPerf',0)),1),ag>hg,is_a)}",
        f"1p:{nv(str(int(row['HTHG']))+'G',False,is_h)}",
        f"1p:{nv(str(int(row['HTAG']))+'G',False,is_a)}",
        f"2p:{nv(str(hg-int(row['HTHG']))+'G',False,is_h)}",
        f"2p:{nv(str(ag-int(row['HTAG']))+'G',False,is_a)}",
        nv(f"{int(row['HS'])}T {int(row['HST'])}TP {int(row['HF'])}F {int(row['HC'])}C {int(row['HY'])}A {int(row['HR'])}R",hg>ag,is_h),
        nv(f"{int(row['AS'])}T {int(row['AST'])}TP {int(row['AF'])}F {int(row['AC'])}C {int(row['AY'])}A {int(row['AR'])}R",ag>hg,is_a)
    ]

    return f"<div style='font-family:monospace; font-size:11px; line-height:1.15; padding:3px 2px; border-bottom:1px solid #ddd; white-space:nowrap'>{ '<br>'.join(lineas) }</div>"
####def def calcular_htft

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
    h_badge = badge_equipo(row.get('HomeAbbr', abreviar_equipo(ht)), hy, hr, hc, hthg, h2tg, equipo_filtro == ht)
    a_badge = badge_equipo(row.get('AwayAbbr', abreviar_equipo(at)), ay, ar, ac, htag, a2tg, equipo_filtro == at)
    if h_badge and a_badge: return f"<div style='text-align:left; line-height:1.8'>{h_badge}<br>{a_badge}</div>"
    elif h_badge: return f"<div style='text-align:left'>{h_badge}</div>"
    elif a_badge: return f"<div style='text-align:left'>{a_badge}</div>"
    return ""


################################# FIN RESULTADO_HT_FT#################################

@st.cache_data
def calcular_estado_jornada(df):
    df = df.sort_values(['League','Season','Date']).copy()
##########bloque para que las jornadas vallan de 1 en 1
# 1) Jornada - 1 jornada = todos los equipos juegan una vez
    for (l, s), g in df.groupby(['League','Season'], sort=False):
        g = g.sort_values('Date')
        teams = pd.unique(g[['HomeTeam','AwayTeam']].values.ravel())
        per_jor = max(1, len(teams) // 2)
        # asigna jornada secuencial: 0-9 → J1, 10-19 → J2, etc.
        jornadas = (np.arange(len(g)) // per_jor) + 1
        df.loc[g.index, 'Jornada'] = jornadas
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

##########LOGICA: CALCULO RACHAS G/E/P

@st.cache_data
def _rachas(df_base, cond, loc, x_max=None):
    df = df_base[['Date','Season','Jornada','HomeTeam','AwayTeam','FTR']].copy()
    df = df.sort_values('Date')

    # vista por equipo, vectorizada
    h = df.assign(Equipo=df['HomeTeam'], Res=df['FTR'].map({'H':'G','A':'P','D':'E'}), Loc='Local')
    a = df.assign(Equipo=df['AwayTeam'], Res=df['FTR'].map({'A':'G','H':'P','D':'E'}), Loc='Visitante')
    d = pd.concat([h[['Date','Season','Jornada','Equipo','Res','Loc']],
        a[['Date','Season','Jornada','Equipo','Res','Loc']]], ignore_index=True)

    if loc!= 'Todo':
        d = d[d['Loc']==loc]

    d = d.sort_values(['Equipo','Date'])
    mapa = {"G":{'G'},"P":{'P'},"E":{'E'},"G/E":{'G','E'},"E/P":{'E','P'},"G/P":{'G','P'}}
    cs = {'G','P','E'} if cond=="Todo" else mapa[cond]
    d['ok'] = d['Res'].isin(cs)

    out = []
    for eq, g in d.groupby('Equipo', sort=False):
        g = g.copy()
        g['new_season'] = g['Season']!= g['Season'].shift()
        g['run'] = (g['ok']!= g['ok'].shift()) | g['new_season']
        g['run_id'] = g['run'].cumsum()

        rachas_ok = g[g['ok']].groupby('run_id')
        lens = rachas_ok.size().tolist()
        max_seg = max(lens) if lens else 0
        total_ok = g['ok'].sum()
        pct = round(100*total_ok/len(g),1) if len(g) else 0
        ult5 = ''.join(g['Res'].tail(5).tolist())

        if x_max:
            runs_x = [r for _, r in rachas_ok if len(r) >= x_max]
            count_x = len(runs_x)
            jornadas_x = [f"J{int(r['Jornada'].iloc[0])}-J{int(r['Jornada'].iloc[-1])} ({len(r)})" for r in runs_x]
            jornadas_str = ' | '.join(jornadas_x) if jornadas_x else "-"
            texto = f"{eq} | {len(g)}PJ | {max_seg} max | {count_x}# | {pct}% | {ult5} ↳ {jornadas_str}"
            out.append({'Equipo':texto,'PJ':len(g),'Max':max_seg,'CountX':count_x,'%':pct})
        else:
            jornadas_ok = [f"J{int(r['Jornada'].iloc[0])}-J{int(r['Jornada'].iloc[-1])}" for _, r in rachas_ok]
            jornadas_str = ', '.join(jornadas_ok)
            texto = f"{eq} | {len(g)}PJ | {max_seg} max | {pct}% | {ult5} ↳ {jornadas_str}"
            out.append({'Equipo':texto,'PJ':len(g),'Max':max_seg,'%':pct})

    return pd.DataFrame(out)


############fin filtro racchas

    


def limpiar_filtros():
    st.session_state.marcador_filtro = "Todos"
    st.session_state.pct_marcador = 0
    st.session_state.columna_filtro = "Ninguno"
    st.session_state.operador_filtro = "="
    st.session_state.valor_filtro = "Ninguno"
    st.session_state.columna_filtro2 = "Ninguno"
    st.session_state.operador_filtro2 = "="
    st.session_state.valor_filtro2 = "Ninguno"
    st.session_state.alcance_filtro2 = "Todo"
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

######"Filtros de partidos"
with st.expander("Filtros de partidos", expanded=False):
    col1, col2, col3, col4 = st.columns(4)

    ligas_disponibles = sorted(df['League'].unique())
    temporadas_disponibles = sorted(df['Season'].unique())

    st.caption(f"Ligas detectadas: {', '.join(ligas_disponibles)}")

    liga_sel = col1.multiselect("Liga", ligas_disponibles, default=[ligas_disponibles[0]] if ligas_disponibles else [],
        format_func=lambda x: '\u2060'.join(x))
    temp_sel = col2.multiselect("Temporada", temporadas_disponibles, default=[temporadas_disponibles[-1]] if temporadas_disponibles else [])
    modo_vista = "Jornadas"

    df_fil = df[df['League'].isin(liga_sel) & df['Season'].isin(temp_sel)]

    if df_fil.empty:
        st.stop()

    @st.cache_data
    def calcular_estado_jornada_rapido(df, temporadas, ligas):
        df_fil = df[df['League'].isin(ligas) & df['Season'].isin(temporadas)]
        return calcular_estado_jornada(df_fil)

    with st.spinner('Calculando clasificación...'):
        df_base, df_clas_base = calcular_estado_jornada_rapido(df, temp_sel, liga_sel)

    df_rachas_full = df_base.copy()
    df_final = df_base.copy()
    df_clasificacion = df_clas_base.copy()
    
    jornadas = sorted(df_final['Jornada'].unique())  # <-- ESTA LÍNEA FALTABA
    

    if len(jornadas) > 0:
        min_j, max_j = int(min(jornadas)), int(max(jornadas))
        col_j1, col_j2 = st.columns(2)
        j_desde = col_j1.number_input("Jornada De", min_value=min_j, max_value=max_j, value=min_j, key='j_desde', step=1)
        j_hasta = col_j2.number_input("Jornada A", min_value=min_j, max_value=max_j, value=max_j, key='j_hasta', step=1)
        # Validamos que De <= A
        if j_desde > j_hasta:
            st.warning("Jornada 'De' no puede ser mayor que 'A'")
            j_desde = j_hasta
        rango_jornadas = (int(j_desde), int(j_hasta))
    else:
        rango_jornadas = (0, 0)

        # --- RANGO CUOTAS CON CAJITAS ---
    col_c1, col_c2 = st.columns(2)
    cuota_desde = col_c1.number_input(
        "Cuota De",
        min_value=1.0,
        max_value=40.0,
        value=st.session_state.rango_cuotas[0],
        step=0.05,
        key='cuota_desde'
    )
    cuota_hasta = col_c2.number_input(
        "Cuota A",
        min_value=1.0,
        max_value=40.0,
        value=st.session_state.rango_cuotas[1],
        step=0.05,
        key='cuota_hasta'
    )

    if cuota_desde > cuota_hasta:
        st.warning("Cuota 'De' no puede ser mayor que 'A'")
        cuota_desde = cuota_hasta

    rango_cuotas = (float(cuota_desde), float(cuota_hasta))
    st.session_state.rango_cuotas = rango_cuotas
    # --- FIN RANGO CUOTAS ---
    rango_minutos = st.slider("Minutos", 0, 120, st.session_state.rango_minutos, 1, key='rango_minutos')

if len(jornadas) > 0:
    df_final = df_final[(df_final['Jornada'] >= rango_jornadas[0]) & (df_final['Jornada'] <= rango_jornadas[1])]
    df_clasificacion = df_clasificacion[(df_clasificacion['Jornada'] >= rango_jornadas[0]) & (df_clasificacion['Jornada'] <= rango_jornadas[1])]

    df_base_h2h = df_final.copy()

    todos_eventos = {}
    for liga in liga_sel:
        for temp in temp_sel:
            todos_eventos.update(cargar_eventos(liga, temp))

    if 'marcador_filtro' not in st.session_state: st.session_state.marcador_filtro = "Todos"
    if 'pct_marcador' not in st.session_state: st.session_state.pct_marcador = 0
    if 'columna_filtro' not in st.session_state: st.session_state.columna_filtro = "Ninguno"
    if 'operador_filtro' not in st.session_state: st.session_state.operador_filtro = "="
    if 'valor_filtro' not in st.session_state: st.session_state.valor_filtro = "Ninguno"
    if 'columna_filtro2' not in st.session_state: st.session_state.columna_filtro2 = "Ninguno"
    if 'operador_filtro2' not in st.session_state: st.session_state.operador_filtro2 = "="
    if 'valor_filtro2' not in st.session_state: st.session_state.valor_filtro2 = "Ninguno"
    if 'alcance_filtro2' not in st.session_state: st.session_state.alcance_filtro2 = "Todo"
    if 'equipo_filtro' not in st.session_state: st.session_state.equipo_filtro = "Ninguno"
    if 'resultado_filtro' not in st.session_state: st.session_state.resultado_filtro = "Ninguno"
    if 'ambos_marcan' not in st.session_state: st.session_state.ambos_marcan = "Todos"
    if 'condicion_filtro' not in st.session_state: st.session_state.condicion_filtro = "Todo"
    if 'htft_filtro' not in st.session_state: st.session_state.htft_filtro = "Todo"
    if 'jugador_filtro' not in st.session_state: st.session_state.jugador_filtro = "TODOS"
    if 'cuota_tipo' not in st.session_state: st.session_state.cuota_tipo = "Todo"
    if 'parte_gol' not in st.session_state: st.session_state.parte_gol = "Todo"
    if 'alcance_filtro' not in st.session_state: st.session_state.alcance_filtro = "Todo"
    if 'equipo2_filtro' not in st.session_state: st.session_state.equipo2_filtro = "Ninguno"
    if 'margen_filtro' not in st.session_state: st.session_state.margen_filtro = "Todo"
    if 'htft_parcial' not in st.session_state: st.session_state.htft_parcial = "Ninguno"

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
    opciones_col = [
        "Ninguno",
        "_GOL_",
        "GolesTotales", "GolesHT", "Goles2T", "FTHG", "FTAG", "HTHG", "HTAG",
        "_TARJ_",
        "TargAmTot", "TargRojTot", "HY", "AY", "HR", "AR",
        "_TIR_",
        "tirosTot", "tirosPuertaTot", "HS", "AS", "HST", "AST",
        "_CORN_",
        "corneTot", "HC", "AC",
        "_FALT_",
        "faltasTot", "HF", "AF",
        "_CLASF_",
        "HomePtsPrev", "AwayPtsPrev", "HomePosPrev", "AwayPosPrev", "HomePerf", "AwayPerf"
    ]
    equipos_disponibles = sorted(pd.unique(df_final[['HomeTeam','AwayTeam']].values.ravel()))

    opciones_1x2 = ["Ninguno","Gana","Pierde","Empata","Gana/Empata","Gana/Pierde","Empata/Pierde"]
    mapa_1x2 = {"Ninguno":"-", "Gana":"G", "Pierde":"P", "Empata":"E", "Gana/Empata":"GE", "Gana/Pierde":"GP", "Empata/Pierde":"EP"}
    ABREV_MARGEN = {"Todo":"—","Empate":"E","Gana 1":"G1","Gana 2":"G2","Gana 3+":"G3+","Pierde 1":"P1","Pierde 2":"P2","Pierde 3+":"P3+","Gana ≥2":"G2+","Pierde ≥2":"P2+"}
############filtros avanzados    
    with st.expander("🎛️ Filtros avanzados", expanded=False):
    
        f1 = st.columns(4)
        equipo_filtro = f1[0].selectbox("Eq1", ["Ninguno"] + equipos_disponibles, key='equipo_filtro')
        equipo2_filtro = f1[1].selectbox("Eq2", ["Ninguno"] + equipos_disponibles, key='equipo2_filtro')
        columna_filtro = f1[2].selectbox("Col1", opciones_col, format_func=lambda x: ABREV_COL.get(x, x), key='columna_filtro')
        columna_filtro2 = f1[3].selectbox("Col2", opciones_col, format_func=lambda x: ABREV_COL.get(x, x), key='columna_filtro2')

        f2 = st.columns(4)
        operador_filtro = f2[0].selectbox("Op1", ["=", ">", ">=", "<", "<="], key='operador_filtro')
        operador_filtro2 = f2[1].selectbox("Op2", ["=", ">", ">=", "<", "<="], key='operador_filtro2')
        valor_filtro = f2[2].selectbox("Vlr1", ["Ninguno"] + [i/2 for i in range(81)], key='valor_filtro')
        valor_filtro2 = f2[3].selectbox("Vlr2", ["Ninguno"] + [i/2 for i in range(81)], key='valor_filtro2')

        ##########LOGICA: SELECTOR FAV/CONTRA1 AMPLIADO A 30
        f3 = st.columns(4)
        alcance_filtro = f3[0].selectbox("Fav/Cntr1", ["Todo","AF","C"] + [f"AF{i}" for i in range(31)] + [f"C{i}" for i in range(31)], key='alcance_filtro', help="Todo=total | AF=a favor | C=en contra")
        ##########LOGICA: SELECTOR FAV/CONTRA2 AMPLIADO A 30
        alcance_filtro2 = f3[1].selectbox("Fav/Cntr2", ["Todo","AF","C"] + [f"AF{i}" for i in range(31)] + [f"C{i}" for i in range(31)], key='alcance_filtro2')
        condicion_filtro = f3[2].selectbox("L/V", ["Todo", "Local", "Visitante"], key='condicion_filtro')
        htft_filtro = f3[3].selectbox("R=HT/FT", ["Todo","G/G","G/E","G/P","E/G","E/E","E/P","P/G","P/E","P/P","RE","FAIL"], key='htft_filtro')

        f4 = st.columns(4)
        resultado_filtro = f4[0].selectbox("1x2", opciones_1x2, format_func=lambda x: mapa_1x2[x], key='resultado_filtro')
        ambos_marcan = f4[1].selectbox("AM", ["Todos","Si1P","Si2P","No1P","No2P","Si","No"], key='ambos_marcan')
        cuota_tipo = f4[2].selectbox("R1x2", ["Ninguno","Todo","1","X","2"], key='cuota_tipo')
        margen_filtro = f4[3].selectbox("Margen", list(ABREV_MARGEN.keys()), format_func=lambda x: ABREV_MARGEN.get(x, x), key='margen_filtro')

        f4 = st.columns(4) # 4 columnas porque luego usas f4[0] hasta f4[3]
        marcadores_unicos = sorted(
            (df_final['FTHG'].astype(int).astype(str) + '-' + df_final['FTAG'].astype(int).astype(str)).unique(),
            key=lambda s: (int(s.split('-')[0]), int(s.split('-')[1]))
        )
        f5 = st.columns(3)
        marcador_filtro = f5[0].selectbox("Marcador", ["Todos"] + marcadores_unicos, key='marcador_filtro')
        f5[1].caption("% mínimo")
        htft_parcial = st.selectbox(
        "HT/FT parcial",
        ["Ninguno", "X/G", "X/E", "X/P", "G/X", "E/X", "P/X"],
        key='htft_parcial',
        help="X/G=da igual 1ª/gana | G/X=gana 1ª/da igual"
    )
        pct_marcador = f5[1].number_input(" ", min_value=0, max_value=100, value=st.session_state.pct_marcador, step=5, key='pct_marcador', label_visibility="collapsed")
        f5[2].empty()

        parte_gol = st.selectbox("Parte", ["Todo","1T","2T"], key='parte_gol')

        from collections import defaultdict, Counter
        player_teams = defaultdict(Counter)
        for (ht, at, fecha), evs in todos_eventos.items():
            for ev in evs:
                if ev.get('missed') or not ev.get('player'):
                    continue
                team = ev.get('team')
                if team:
                    player_teams[ev['player']][team] += 1
        player_to_team = {p: max(cnts.items(), key=lambda x: x[1])[0] for p, cnts in player_teams.items()} if player_teams else {}
        lista_jug = sorted([p for p,t in player_to_team.items() if t==equipo_filtro]) if equipo_filtro!="Ninguno" else sorted(player_to_team.keys())

        jugador_filtro = st.selectbox("Jugador", ["TODOS"] + lista_jug, key='jugador_filtro')

        st.button("Limpiar", on_click=limpiar_filtros, use_container_width=False)
    
       # --- RESUMEN DE FILTROS ACTIVOS ---
   
    # --- RESUMEN DE FILTROS ACTIVOS ---
    filtros_activos = []

    if equipo_filtro!= "Ninguno": filtros_activos.append(f"Eq1:{equipo_filtro}")
    if equipo2_filtro!= "Ninguno": filtros_activos.append(f"Eq2:{equipo2_filtro}")
    if condicion_filtro!= "Todo": filtros_activos.append(f"L/V:{condicion_filtro}")
    if resultado_filtro!= "Ninguno": filtros_activos.append(f"1x2:{mapa_1x2[resultado_filtro]}")
    if ambos_marcan!= "Todos": filtros_activos.append(f"AM:{ambos_marcan}")
    if htft_filtro!= "Todo": filtros_activos.append(f"HT/FT:{htft_filtro}")
    if margen_filtro!= "Todo": filtros_activos.append(f"Margen:{ABREV_MARGEN[margen_filtro]}")
    if htft_parcial!= "Ninguno": filtros_activos.append(f"HT/FT:{htft_parcial}")
    if marcador_filtro!= "Todos": filtros_activos.append(f"Marc:{marcador_filtro}")
    if pct_marcador > 0: filtros_activos.append(f"Min%:{pct_marcador}%")
    if cuota_tipo not in ["Ninguno","Todo"]: filtros_activos.append(f"R1x2:{cuota_tipo}")
    if not (rango_cuotas[0]==1.0 and rango_cuotas[1]==40.0): filtros_activos.append(f"Cuotas:{rango_cuotas[0]}-{rango_cuotas[1]}")
    if parte_gol!= "Todo": filtros_activos.append(f"Parte:{parte_gol}")
    if jugador_filtro!= "TODOS": filtros_activos.append(f"Jug:{jugador_filtro}")
    if not (rango_minutos[0]==0 and rango_minutos[1]>=120): filtros_activos.append(f"Min:{rango_minutos[0]}-{rango_minutos[1]}")

    # Col1
    if columna_filtro!= "Ninguno" and valor_filtro!= "Ninguno":
        txt_col1 = f"{ABREV_COL.get(columna_filtro, columna_filtro)}{operador_filtro}{valor_filtro}"
        if alcance_filtro!= "Todo": txt_col1 = f"{alcance_filtro}:{txt_col1}"
        filtros_activos.append(txt_col1)

    # Col2
    if columna_filtro2!= "Ninguno" and valor_filtro2!= "Ninguno":
        txt_col2 = f"{ABREV_COL.get(columna_filtro2, columna_filtro2)}{operador_filtro2}{valor_filtro2}"
        if alcance_filtro2!= "Todo": txt_col2 = f"{alcance_filtro2}:{txt_col2}"
        filtros_activos.append(txt_col2)

    # Jornada
# Jornada
    if len(jornadas) > 0 and (rango_jornadas[0]!=min_j or rango_jornadas[1]!=max_j):
        filtros_activos.append(f"J:{rango_jornadas[0]}-{rango_jornadas[1]}")

    if filtros_activos:
        st.info("**Filtros:** " + " | ".join(filtros_activos))
    else:
        st.caption("**Filtros:** Ninguno")
   
   # === FILTRO X/X HT/FT PARCIAL ===
if htft_parcial!= "Ninguno" and equipo_filtro!= "Ninguno" and equipo2_filtro == "Ninguno":
    es_local = df_final['HomeTeam'] == equipo_filtro

    ht_gana = np.where(es_local, df_final['HTHG'] > df_final['HTAG'], df_final['HTAG'] > df_final['HTHG'])
    ht_pierde = np.where(es_local, df_final['HTHG'] < df_final['HTAG'], df_final['HTAG'] < df_final['HTHG'])
    ht_empata = ~(ht_gana | ht_pierde)

    ft_gana = np.where(es_local, df_final['FTHG'] > df_final['FTAG'], df_final['FTAG'] > df_final['FTHG'])
    ft_pierde = np.where(es_local, df_final['FTHG'] < df_final['FTAG'], df_final['FTAG'] < df_final['FTHG'])
    ft_empata = ~(ft_gana | ft_pierde)

    if htft_parcial == "X/G":
        df_final = df_final[ft_gana]
    elif htft_parcial == "X/E":
        df_final = df_final[ft_empata]
    elif htft_parcial == "X/P":
        df_final = df_final[ft_pierde]
    elif htft_parcial == "G/X":
        df_final = df_final[ht_gana]
    elif htft_parcial == "E/X":
        df_final = df_final[ht_empata]
    elif htft_parcial == "P/X":
        df_final = df_final[ht_pierde]
# === FIN FILTRO X/X HT/FT PARCIAL ===
   
    # --- FIN RESUMEN FILTROS ---

   ##########fin desplegable
    # === FIN FILTRO GOLES ===

    # === FIN FILTRO GOLES ===

    # === FILTRO EQUIPOS BASE ===
    if equipo_filtro!= "Ninguno" and equipo2_filtro!= "Ninguno":
        df_final = df_final[((df_final['HomeTeam']==equipo_filtro) | (df_final['AwayTeam']==equipo_filtro)) | ((df_final['HomeTeam']==equipo2_filtro) | (df_final['AwayTeam']==equipo2_filtro))]
    elif equipo_filtro!= "Ninguno":
        df_final = df_final[(df_final['HomeTeam']==equipo_filtro) | (df_final['AwayTeam']==equipo_filtro)]
    elif equipo2_filtro!= "Ninguno":
        df_final = df_final[(df_final['HomeTeam']==equipo2_filtro) | (df_final['AwayTeam']==equipo2_filtro)]

    # === FILTRO LOCAL/VISITANTE ===
    if condicion_filtro != "Todo" and (equipo_filtro != "Ninguno" or equipo2_filtro != "Ninguno") and not (equipo_filtro != "Ninguno" and equipo2_filtro != "Ninguno"):
        eq = equipo_filtro if equipo_filtro != "Ninguno" else equipo2_filtro
        if condicion_filtro == "Local":
            df_final = df_final[df_final['HomeTeam'] == eq]
        elif condicion_filtro == "Visitante":
            df_final = df_final[df_final['AwayTeam'] == eq]

##########LOGICA: FILTRO 1X2 GANA/PIERDE/EMPATA
    # === FILTROS 1X2 / AM / HTFT / CUOTAS / MARGEN / MARCADOR ===
    if resultado_filtro!= "Ninguno" and equipo_filtro!= "Ninguno" and equipo2_filtro=="Ninguno":
        if resultado_filtro == "Gana":
            df_final = df_final[((df_final['HomeTeam']==equipo_filtro) & (df_final['FTR']=='H')) | ((df_final['AwayTeam']==equipo_filtro) & (df_final['FTR']=='A'))]
        elif resultado_filtro == "Pierde":
            df_final = df_final[((df_final['HomeTeam']==equipo_filtro) & (df_final['FTR']=='A')) | ((df_final['AwayTeam']==equipo_filtro) & (df_final['FTR']=='H'))]
        elif resultado_filtro == "Empata":
            df_final = df_final[df_final['FTR']=='D']
        elif resultado_filtro == "Gana/Empata":
            df_final = df_final[~(((df_final['HomeTeam']==equipo_filtro) & (df_final['FTR']=='A')) | ((df_final['AwayTeam']==equipo_filtro) & (df_final['FTR']=='H')))]
        elif resultado_filtro == "Gana/Pierde":
            df_final = df_final[df_final['FTR']!='D']
        elif resultado_filtro == "Empata/Pierde":
            df_final = df_final[~(((df_final['HomeTeam']==equipo_filtro) & (df_final['FTR']=='H')) | ((df_final['AwayTeam']==equipo_filtro) & (df_final['FTR']=='A')))]


##########LOGICA: FILTRO AMBOS MARCAN


    if ambos_marcan!= "Todos":
        # Forzar numérico por si acaso
        for col in ['FTHG','FTAG','HTHG','HTAG']:
            df_final[col] = pd.to_numeric(df_final[col], errors='coerce').fillna(0)

        if ambos_marcan == "Si":
            if parte_gol == "1T":
                df_final = df_final[(df_final['HTHG'] > 0) & (df_final['HTAG'] > 0)]
            elif parte_gol == "2T":
                df_final = df_final[((df_final['FTHG'] - df_final['HTHG']) > 0) & ((df_final['FTAG'] - df_final['HTAG']) > 0)]
            else:
                df_final = df_final[(df_final['FTHG'] > 0) & (df_final['FTAG'] > 0)]

        elif ambos_marcan == "No":
            if parte_gol == "1T":
                df_final = df_final[~((df_final['HTHG'] > 0) & (df_final['HTAG'] > 0))]
            elif parte_gol == "2T":
                df_final = df_final[~(((df_final['FTHG'] - df_final['HTHG']) > 0) & ((df_final['FTAG'] - df_final['HTAG']) > 0))]
            else:
                df_final = df_final[~((df_final['FTHG'] > 0) & (df_final['FTAG'] > 0))]

        elif ambos_marcan == "Si1P":
            df_final = df_final[(df_final['HTHG'] > 0) & (df_final['HTAG'] > 0)]
        elif ambos_marcan == "No1P":
            df_final = df_final[~((df_final['HTHG'] > 0) & (df_final['HTAG'] > 0))]
        elif ambos_marcan == "Si2P":
            df_final = df_final[((df_final['FTHG'] - df_final['HTHG']) > 0) & ((df_final['FTAG'] - df_final['HTAG']) > 0)]
        elif ambos_marcan == "No2P":
            df_final = df_final[~(((df_final['FTHG'] - df_final['HTHG']) > 0) & ((df_final['FTAG'] - df_final['HTAG']) > 0))]
    
    # HT/FT relativo al Eq1
    ##########LOGICA: FILTRO HT/FT GANA/PIERDE/REMONTA
    
    if htft_filtro != "Todo" and equipo_filtro != "Ninguno" and equipo2_filtro == "Ninguno":
        es_local = df_final['HomeTeam'] == equipo_filtro
        
        ht_gana = np.where(es_local, df_final['HTHG'] > df_final['HTAG'], df_final['HTAG'] > df_final['HTHG'])
        ht_pierde = np.where(es_local, df_final['HTHG'] < df_final['HTAG'], df_final['HTAG'] < df_final['HTHG'])
        ht_res = np.where(ht_gana, 'G', np.where(ht_pierde, 'P', 'E'))
        
        ft_gana = np.where(es_local, df_final['FTHG'] > df_final['FTAG'], df_final['FTAG'] > df_final['FTHG'])
        ft_pierde = np.where(es_local, df_final['FTHG'] < df_final['FTAG'], df_final['FTAG'] < df_final['FTHG'])
        ft_res = np.where(ft_gana, 'G', np.where(ft_pierde, 'P', 'E'))
        
        combo = ht_res + '/' + ft_res
        
        if htft_filtro == "RE":  # Remonta
            df_final = df_final[(ht_res != 'G') & (ft_res == 'G')]
        elif htft_filtro == "FAIL":  # Se deja remontar
            df_final = df_final[((ht_res == 'G') & (ft_res != 'G')) | ((ht_res == 'E') & (ft_res == 'P'))]
        else:
            df_final = df_final[combo == htft_filtro]
        # HT/FT relativo al Eq1
        es_local = df_final['HomeTeam'] == equipo_filtro
        
        ht_gana = np.where(es_local, df_final['HTHG'] > df_final['HTAG'], df_final['HTAG'] > df_final['HTHG'])
        ht_pierde = np.where(es_local, df_final['HTHG'] < df_final['HTAG'], df_final['HTAG'] < df_final['HTHG'])
        ht_res = np.where(ht_gana, 'G', np.where(ht_pierde, 'P', 'E'))
        
        ft_gana = np.where(es_local, df_final['FTHG'] > df_final['FTAG'], df_final['FTAG'] > df_final['FTHG'])
        ft_pierde = np.where(es_local, df_final['FTHG'] < df_final['FTAG'], df_final['FTAG'] < df_final['FTHG'])
        ft_res = np.where(ft_gana, 'G', np.where(ft_pierde, 'P', 'E'))
        
        combo = ht_res + '/' + ft_res
        
        if htft_filtro == "RE":  # Remonta: no iba ganando y acaba ganando
            df_final = df_final[(ht_res != 'G') & (ft_res == 'G')]
        elif htft_filtro == "FAIL":  # Se deja remontar: iba ganando o empatando y acaba perdiendo
            df_final = df_final[((ht_res == 'G') & (ft_res != 'G')) | ((ht_res == 'E') & (ft_res == 'P'))]
        else:
            df_final = df_final[combo == htft_filtro]

    if cuota_tipo not in ["Ninguno","Todo"]:
        if cuota_tipo == "1":
            df_final = df_final[df_final['FTR'] == 'H']
            col = "B365H"
        elif cuota_tipo == "X":
            df_final = df_final[df_final['FTR'] == 'D']
            col = "B365D"
        elif cuota_tipo == "2":
            df_final = df_final[df_final['FTR'] == 'A']
            col = "B365A"
        else:
            col = None
        # mantiene tu filtro de rango de cuotas
        if col:
            df_final = df_final[(df_final[col] >= rango_cuotas[0]) & (df_final[col] <= rango_cuotas[1])]

##########LOGICA: FILTRO MARGEN VICTORIA/DERROTA

    if margen_filtro!= "Todo" and equipo_filtro!= "Ninguno" and equipo2_filtro=="Ninguno":
        es_loc = df_final['HomeTeam']==equipo_filtro
        dif = np.where(es_loc, df_final['FTHG']-df_final['FTAG'], df_final['FTAG']-df_final['FTHG'])
        if margen_filtro == "Empate": df_final = df_final[dif==0]
        elif margen_filtro == "Gana 1": df_final = df_final[dif==1]
        elif margen_filtro == "Gana 2": df_final = df_final[dif==2]
        elif margen_filtro == "Gana 3+": df_final = df_final[dif>=3]
        elif margen_filtro == "Pierde 1": df_final = df_final[dif==-1]
        elif margen_filtro == "Pierde 2": df_final = df_final[dif==-2]
        elif margen_filtro == "Pierde 3+": df_final = df_final[dif<=-3]
        elif margen_filtro == "Gana ≥2": df_final = df_final[dif>=2]
        elif margen_filtro == "Pierde ≥2": df_final = df_final[dif<=-2]

    if marcador_filtro!= "Todos":
        gl, gv = map(int, marcador_filtro.split('-'))
        df_final = df_final[(df_final['FTHG']==gl) & (df_final['FTAG']==gv)]

        
        ##########LOGICA: GOLES A FAVOR/CONTRA POR PARTE
        
    # === FIX: FILTRO F/C + PARTE ===
    if equipo_filtro != "Ninguno" and equipo2_filtro == "Ninguno" and alcance_filtro in ["AF", "C"] and parte_gol != "Todo":
        es_local = df_final['HomeTeam'] == equipo_filtro
        
        if parte_gol == "1T":
            goles_favor = np.where(es_local, df_final['HTHG'], df_final['HTAG'])
            goles_contra = np.where(es_local, df_final['HTAG'], df_final['HTHG'])
        else:  # 2T
            goles_favor = np.where(es_local, df_final['FTHG'] - df_final['HTHG'], df_final['FTAG'] - df_final['HTAG'])
            goles_contra = np.where(es_local, df_final['FTAG'] - df_final['HTAG'], df_final['FTHG'] - df_final['HTHG'])
        
        if alcance_filtro == "AF":
            df_final = df_final[goles_favor > 0]
        else:  # C
            df_final = df_final[goles_contra > 0]
    # === FIN FIX ===


##########LOGICA: FILTRO RAPIDO GOLES AF0/C1/C2
        # === FILTRO F/C CON ATAJOS (respeta Parte) ===
    ##########LOGICA: FILTRO RAPIDO GOLES AF0-AF30/C0-C30
    if equipo_filtro!= "Ninguno" and equipo2_filtro=="Ninguno" and (alcance_filtro.startswith("AF") or alcance_filtro.startswith("C")) and alcance_filtro not in ["Todo","AF","C"]:  
        es_local = df_final['HomeTeam'] == equipo_filtro
        valor_atajo = int(alcance_filtro[2:]) # coge AF30 -> 30, C12 -> 12

        if parte_gol == "1T":
            goles_favor = np.where(es_local, df_final['HTHG'], df_final['HTAG'])
            goles_contra = np.where(es_local, df_final['HTAG'], df_final['HTHG'])
        elif parte_gol == "2T":
            goles_favor = np.where(es_local, df_final['FTHG'] - df_final['HTHG'], df_final['FTAG'] - df_final['HTAG'])
            goles_contra = np.where(es_local, df_final['FTAG'] - df_final['HTAG'], df_final['FTHG'] - df_final['HTHG'])
        else:
            goles_favor = np.where(es_local, df_final['FTHG'], df_final['FTAG'])
            goles_contra = np.where(es_local, df_final['FTAG'], df_final['FTHG'])

        if alcance_filtro.startswith("AF"):
            df_final = df_final[goles_favor == valor_atajo]
        else:
            df_final = df_final[goles_contra == valor_atajo]

##########LOGICA: FILTRO COLUMNA1 + FAV/CONTRA + PARTE
    # === FILTRO COLUMNA CON AF / C (respeta Parte) ===
    if columna_filtro in columnas_numericas and valor_filtro != "Ninguno":
        col_usar = columna_filtro

        if equipo_filtro != "Ninguno" and equipo2_filtro == "Ninguno" and alcance_filtro in ["AF","C"]:
            es_local = df_final['HomeTeam'] == equipo_filtro

            if alcance_filtro == "AF":
                # === GOLES ===
                if columna_filtro in ['GolesTotales','FTHG','FTAG']:
                    if parte_gol == "1T":
                        df_final['_val'] = np.where(es_local, df_final['HTHG'], df_final['HTAG'])
                    elif parte_gol == "2T":
                        df_final['_val'] = np.where(es_local, df_final['FTHG']-df_final['HTHG'], df_final['FTAG']-df_final['HTAG'])
                    else:
                        df_final['_val'] = np.where(es_local, df_final['FTHG'], df_final['FTAG'])
                elif columna_filtro == 'GolesHT':
                    df_final['_val'] = np.where(es_local, df_final['HTHG'], df_final['HTAG'])
                elif columna_filtro == 'Goles2T':
                    df_final['_val'] = np.where(es_local, df_final['FTHG']-df_final['HTHG'], df_final['FTAG']-df_final['HTAG'])
                # === CORNERS TOTALES -> CORNERS DEL EQUIPO ===
                elif columna_filtro == 'corneTot':
                    df_final['_val'] = np.where(es_local, df_final['HC'], df_final['AC'])
                # === TIROS TOTALES -> TIROS DEL EQUIPO ===
                elif columna_filtro == 'tirosTot':
                    df_final['_val'] = np.where(es_local, df_final['HS'], df_final['AS'])
                # === TIROS PUERTA TOTALES -> TIROS PUERTA DEL EQUIPO ===
                elif columna_filtro == 'tirosPuertaTot':
                    df_final['_val'] = np.where(es_local, df_final['HST'], df_final['AST'])
                # === FALTAS TOTALES -> FALTAS DEL EQUIPO ===
                elif columna_filtro == 'faltasTot':
                    df_final['_val'] = np.where(es_local, df_final['HF'], df_final['AF'])
                # === TARJETAS AM TOTALES -> TARJETAS AM DEL EQUIPO ===
                elif columna_filtro == 'TargAmTot':
                    df_final['_val'] = np.where(es_local, df_final['HY'], df_final['AY'])
                # === TARJETAS ROJ TOTALES -> TARJETAS ROJ DEL EQUIPO ===
                elif columna_filtro == 'TargRojTot':
                    df_final['_val'] = np.where(es_local, df_final['HR'], df_final['AR'])
                # === STATS L/V NORMALES ===
                else:
                    mapa = {'HS':'AS','AS':'HS','HST':'AST','AST':'HST','HF':'AF','AF':'HF','HC':'AC','AC':'HC',
                            'HY':'AY','AY':'HY','HR':'AR','AR':'HR','HomePtsPrev':'AwayPtsPrev','AwayPtsPrev':'HomePtsPrev',
                            'HomePosPrev':'AwayPosPrev','AwayPosPrev':'HomePosPrev','HomePerf':'AwayPerf','AwayPerf':'HomePerf'}
                    if columna_filtro in ['HC','HS','HST','HF','HY','HR']:
                        df_final['_val'] = np.where(es_local, df_final[columna_filtro], df_final[mapa[columna_filtro]])
                    else:
                        df_final['_val'] = np.where(es_local, df_final[mapa[columna_filtro]], df_final[columna_filtro])
                col_usar = '_val'

            elif alcance_filtro == "C":
                # === GOLES EN CONTRA ===
                if columna_filtro in ['GolesTotales','FTHG','FTAG']:
                    if parte_gol == "1T":
                        df_final['_val'] = np.where(es_local, df_final['HTAG'], df_final['HTHG'])
                    elif parte_gol == "2T":
                        df_final['_val'] = np.where(es_local, df_final['FTAG']-df_final['HTAG'], df_final['FTHG']-df_final['HTHG'])
                    else:
                        df_final['_val'] = np.where(es_local, df_final['FTAG'], df_final['FTHG'])
                elif columna_filtro == 'GolesHT':
                    df_final['_val'] = np.where(es_local, df_final['HTAG'], df_final['HTHG'])
                elif columna_filtro == 'Goles2T':
                    df_final['_val'] = np.where(es_local, df_final['FTAG']-df_final['HTAG'], df_final['FTHG']-df_final['HTHG'])
                # === CORNERS TOTALES -> CORNERS EN CONTRA ===
                elif columna_filtro == 'corneTot':
                    df_final['_val'] = np.where(es_local, df_final['AC'], df_final['HC'])
                # === TIROS TOTALES -> TIROS EN CONTRA ===
                elif columna_filtro == 'tirosTot':
                    df_final['_val'] = np.where(es_local, df_final['AS'], df_final['HS'])
                # === TIROS PUERTA TOTALES -> TIROS PUERTA EN CONTRA ===
                elif columna_filtro == 'tirosPuertaTot':
                    df_final['_val'] = np.where(es_local, df_final['AST'], df_final['HST'])
                # === FALTAS TOTALES -> FALTAS EN CONTRA ===
                elif columna_filtro == 'faltasTot':
                    df_final['_val'] = np.where(es_local, df_final['AF'], df_final['HF'])
                # === TARJETAS AM TOTALES -> TARJETAS AM EN CONTRA ===
                elif columna_filtro == 'TargAmTot':
                    df_final['_val'] = np.where(es_local, df_final['AY'], df_final['HY'])
                # === TARJETAS ROJ TOTALES -> TARJETAS ROJ EN CONTRA ===
                elif columna_filtro == 'TargRojTot':
                    df_final['_val'] = np.where(es_local, df_final['AR'], df_final['HR'])
                # === STATS L/V NORMALES ===
                else:
                    mapa = {'HS':'AS','AS':'HS','HST':'AST','AST':'HST','HF':'AF','AF':'HF','HC':'AC','AC':'HC',
                            'HY':'AY','AY':'HY','HR':'AR','AR':'HR','HomePtsPrev':'AwayPtsPrev','AwayPtsPrev':'HomePtsPrev',
                            'HomePosPrev':'AwayPosPrev','AwayPosPrev':'HomePosPrev','HomePerf':'AwayPerf','AwayPerf':'HomePerf'}
                    if columna_filtro in ['HC','HS','HST','HF','HY','HR']:
                        df_final['_val'] = np.where(es_local, df_final[mapa[columna_filtro]], df_final[columna_filtro])
                    else:
                        df_final['_val'] = np.where(es_local, df_final[columna_filtro], df_final[mapa[columna_filtro]])
                col_usar = '_val'

        val = float(valor_filtro)
        if operador_filtro == "=": df_final = df_final[df_final[col_usar] == val]
        elif operador_filtro == ">": df_final = df_final[df_final[col_usar] > val]
        elif operador_filtro == ">=": df_final = df_final[df_final[col_usar] >= val]
        elif operador_filtro == "<": df_final = df_final[df_final[col_usar] < val]
        elif operador_filtro == "<=": df_final = df_final[df_final[col_usar] <= val]

        if '_val' in df_final.columns:
            df_final = df_final.drop(columns=['_val'])

##########LOGICA: FILTRO COLUMNA2 + FAV/CONTRA + PARTE
    # === FILTRO COLUMNA 2 CON AF / C (respeta Parte) ===
    if columna_filtro2 in columnas_numericas and valor_filtro2 != "Ninguno":
        col_usar2 = columna_filtro2

        if equipo_filtro != "Ninguno" and equipo2_filtro == "Ninguno" and alcance_filtro2 in ["AF","C"]:
            es_local = df_final['HomeTeam'] == equipo_filtro

            if alcance_filtro2 == "AF":
                if columna_filtro2 in ['GolesTotales','FTHG','FTAG']:
                    if parte_gol == "1T":
                        df_final['_val2'] = np.where(es_local, df_final['HTHG'], df_final['HTAG'])
                    elif parte_gol == "2T":
                        df_final['_val2'] = np.where(es_local, df_final['FTHG']-df_final['HTHG'], df_final['FTAG']-df_final['HTAG'])
                    else:
                        df_final['_val2'] = np.where(es_local, df_final['FTHG'], df_final['FTAG'])
                elif columna_filtro2 == 'GolesHT':
                    df_final['_val2'] = np.where(es_local, df_final['HTHG'], df_final['HTAG'])
                elif columna_filtro2 == 'Goles2T':
                    df_final['_val2'] = np.where(es_local, df_final['FTHG']-df_final['HTHG'], df_final['FTAG']-df_final['HTAG'])
                else:
                    mapa = {'HS':'AS','AS':'HS','HST':'AST','AST':'HST','HF':'AF','AF':'HF','HC':'AC','AC':'HC','HY':'AY','AY':'HY','HR':'AR','AR':'HR','HomePtsPrev':'AwayPtsPrev','AwayPtsPrev':'HomePtsPrev','HomePosPrev':'AwayPosPrev','AwayPosPrev':'HomePosPrev','HomePerf':'AwayPerf','AwayPerf':'HomePerf'}
                    col_away = mapa.get(columna_filtro2, columna_filtro2)
                    df_final['_val2'] = np.where(es_local, df_final[columna_filtro2], df_final[col_away])
                col_usar2 = '_val2'

            elif alcance_filtro2 == "C":
                if columna_filtro2 in ['GolesTotales','FTHG','FTAG']:
                    if parte_gol == "1T":
                        df_final['_val2'] = np.where(es_local, df_final['HTAG'], df_final['HTHG'])
                    elif parte_gol == "2T":
                        df_final['_val2'] = np.where(es_local, df_final['FTAG']-df_final['HTAG'], df_final['FTHG']-df_final['HTHG'])
                    else:
                        df_final['_val2'] = np.where(es_local, df_final['FTAG'], df_final['FTHG'])
                elif columna_filtro2 == 'GolesHT':
                    df_final['_val2'] = np.where(es_local, df_final['HTAG'], df_final['HTHG'])
                elif columna_filtro2 == 'Goles2T':
                    df_final['_val2'] = np.where(es_local, df_final['FTAG']-df_final['HTAG'], df_final['FTHG']-df_final['HTHG'])
                else:
                    mapa = {'HS':'AS','AS':'HS','HST':'AST','AST':'HST','HF':'AF','AF':'HF','HC':'AC','AC':'HC','HY':'AY','AY':'HY','HR':'AR','AR':'HR','HomePtsPrev':'AwayPtsPrev','AwayPtsPrev':'HomePtsPrev','HomePosPrev':'AwayPosPrev','AwayPosPrev':'HomePosPrev','HomePerf':'AwayPerf','AwayPerf':'HomePerf'}
                    col_away = mapa.get(columna_filtro2, columna_filtro2)
                    df_final['_val2'] = np.where(es_local, df_final[col_away], df_final[columna_filtro2])
                col_usar2 = '_val2'

        val2 = float(valor_filtro2)
        if operador_filtro2 == "=": df_final = df_final[df_final[col_usar2] == val2]
        elif operador_filtro2 == ">": df_final = df_final[df_final[col_usar2] > val2]
        elif operador_filtro2 == ">=": df_final = df_final[df_final[col_usar2] >= val2]
        elif operador_filtro2 == "<": df_final = df_final[df_final[col_usar2] < val2]
        elif operador_filtro2 == "<=": df_final = df_final[df_final[col_usar2] <= val2]

        if '_val2' in df_final.columns:
            df_final = df_final.drop(columns=['_val2'])

    # === FILTRO POR PARTE - solo si NO hay filtro de goles activo Y hay equipo ===
    if parte_gol!= "Todo" and equipo_filtro!= "Ninguno" and equipo2_filtro=="Ninguno":
        if parte_gol == "1T":
            df_final = df_final[((df_final['HomeTeam']==equipo_filtro)&(df_final['HTHG']>0))|((df_final['AwayTeam']==equipo_filtro)&(df_final['HTAG']>0))]
        elif parte_gol == "2T":
            df_final = df_final[((df_final['HomeTeam']==equipo_filtro)&((df_final['FTHG']-df_final['HTHG'])>0))|((df_final['AwayTeam']==equipo_filtro)&((df_final['FTAG']-df_final['HTAG'])>0))]
    # si no hay equipo, NO filtramos por parte (para que se vean todos los partidos)
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
       # --- CONTADOR GLOBAL POR JORNADA (independiente de equipos) ---
    if len(df_final) > 0:
        conteo_j = df_final['Jornada'].value_counts().reset_index()
        conteo_j.columns = ['Jornada', 'Veces']
        # ordenar por jornada de la última a la primera
        conteo_j = conteo_j.sort_values('Jornada', ascending=False)
        
        with st.expander(f"📊 Repeticiones por jornada ({len(conteo_j)} jornadas)", expanded=False):
            for _, row in conteo_j.iterrows():
                st.markdown(f"<div style='font-size:11px;padding:2px 0;font-family:monospace'>J{int(row['Jornada'])} - {int(row['Veces'])}#</div>", unsafe_allow_html=True)
    
    # --- RESUMEN CON % QUE RESPETA Eq1/Eq2 ---
    with st.expander(f"📊 Filtro actual ≥{pct_marcador}%", expanded=False):
        if len(df_final) > 0:
            base = df_base_h2h.copy()

            # 1) Muestra Eq1 y/o Eq2 si están elegidos
            equipos_mostrar = []
            if equipo_filtro!= "Ninguno":
                equipos_mostrar.append(equipo_filtro)
            if equipo2_filtro!= "Ninguno" and equipo2_filtro not in equipos_mostrar:
                equipos_mostrar.append(equipo2_filtro)
            if not equipos_mostrar:
                equipos_mostrar = pd.unique(base[['HomeTeam','AwayTeam']].values.ravel())

            datos = []

            if marcador_filtro!= "Todos":
                gl, gv = map(int, marcador_filtro.split('-'))
                titulo = f"{marcador_filtro}"
                for eq in equipos_mostrar:
                    part = base[(base['HomeTeam']==eq) | (base['AwayTeam']==eq)]
                    tot = len(part)
                    if tot == 0: continue
                    hits = len(part[(part['FTHG']==gl) & (part['FTAG']==gv)])
                    pct = hits / tot * 100
                    if pct >= pct_marcador:
                        df_jors = part[(part['FTHG']==gl) & (part['FTAG']==gv)]
                        rival = None
                        if len(equipos_mostrar) == 2:
                            rival = equipos_mostrar[1] if eq == equipos_mostrar[0] else equipos_mostrar[0] 
                        jors = jornadas_conteo(df_jors['Jornada'], df_jors, eq, rival)
                        html = f"<div style='font-size:11px;line-height:1.3;margin:2px 0'><b>{eq.title()}:</b> {hits}# {pct:.1f}% — {jors}</div>"
                        datos.append((pct, hits, eq, html))
            else:
                titulo = "Filtro actual"
                for eq in equipos_mostrar:
                    part_tot = base[(base['HomeTeam']==eq) | (base['AwayTeam']==eq)]
                    part_ok = df_final[(df_final['HomeTeam']==eq) | (df_final['AwayTeam']==eq)]
                    tot = len(part_tot)
                    hits = len(part_ok)
                    pct = hits / tot * 100 if tot else 0
                    if pct >= pct_marcador:
                        rival = None
                        if len(equipos_mostrar) == 2:
                            rival = equipos_mostrar[1] if eq == equipos_mostrar[0] else equipos_mostrar[0]
                        jors = jornadas_conteo(part_ok['Jornada'], part_ok, eq, rival)
                        html = f"<div style='font-size:11px;line-height:1.3;margin:2px 0'><b>{eq.title()}:</b> {hits}# {pct:.1f}% — {jors}</div>"
                        datos.append((pct, hits, eq, html))

            # ORDENAR DE MAYOR A MENOR POR % Y LUEGO POR # ACIERTOS
            datos.sort(key=lambda x: (-x[0], -x[1], x[2]))
            lineas = [d[3] for d in datos]

            if lineas:
                st.markdown(f"<div style='background:#f8f9fa;padding:8px 10px;border-left:3px solid #0A2342;margin:6px 0 10px 0'><b>{titulo} ≥{pct_marcador}% ({len(lineas)} equipos)</b><br>" + "".join(lineas) + "</div>", unsafe_allow_html=True)
            elif pct_marcador > 0:
                st.warning(f"Ningún equipo llega al {pct_marcador}%")
        else:
            st.info("No hay partidos con los filtros actuales")
        if equipo_filtro!= "Ninguno" and len(df_final) > 0:
            total = len(df_final)
            gana = len(df_final[((df_final['HomeTeam'] == equipo_filtro) & (df_final['FTR'] == 'H')) |
                                ((df_final['AwayTeam'] == equipo_filtro) & (df_final['FTR'] == 'A'))])
            empata = len(df_final[df_final['FTR'] == 'D'])
            pierde = len(df_final[((df_final['HomeTeam'] == equipo_filtro) & (df_final['FTR'] == 'A')) |
                                ((df_final['AwayTeam'] == equipo_filtro) & (df_final['FTR'] == 'H'))])

            gana_empata = gana + empata
            pierde_empata = pierde + empata

        

    

    columnas_mostrar = [
        'partidos', ""
    ]

    columnas_mostrar = [col for col in columnas_mostrar if col in df_final.columns]
    
    

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
    with st.expander("📋 Partidos", expanded=False, key="exp_partidos"):
        if equipo_filtro != "Ninguno" and equipo2_filtro != "Ninguno":
            df1 = df_final[(df_final['HomeTeam']==equipo_filtro) | (df_final['AwayTeam']==equipo_filtro)].sort_values(['Jornada','Date'], ascending=False).head(150)
            df2 = df_final[(df_final['HomeTeam']==equipo2_filtro) | (df_final['AwayTeam']==equipo2_filtro)].sort_values(['Jornada','Date'], ascending=False).head(150)
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

            elif modo_vista == "Clasificación":
                

                if df_clasificacion.empty:
                    st.warning("No hay datos para ese rango de jornadas")
                else:
                    # Solo la última jornada del rango filtrado
                    j_ultima = int(df_clasificacion['Jornada'].max())
                    temp = temp_sel[-1] if temp_sel else df_clasificacion['Season'].iloc[0]
                    liga = liga_sel[0] if liga_sel else df_clasificacion['League'].iloc[0]

                    tabla = df_clasificacion[
                        (df_clasificacion['Season'] == temp) &
                        (df_clasificacion['League'] == liga) &
                        (df_clasificacion['Jornada'] == j_ultima)
                    ].sort_values('Pos').copy()

                    if tabla.empty:
                        st.warning("No hay datos de clasificación para esa liga/temporada/jornada")
                    else:
                        tabla['Equipo'] = tabla['Equipo'].str.title()

                        st.subheader(f"{liga} {temp} — Jornada {j_ultima}")

                        def color_pg_pe_pp(val, col):
                            if col == 'PG': return 'color:#0f8105; font-weight:700'
                            if col == 'PE': return 'color:#b45309; font-weight:700'
                            if col == 'PP': return 'color:#dc2626; font-weight:700'
                            return ''

                        styled = tabla[['Pos','Equipo','PJ','PG','PE','PP','GF','GC','DG','Pts']].style.map(
                            lambda v: color_pg_pe_pp(v, 'PG'), subset=['PG']
                        ).map(
                            lambda v: color_pg_pe_pp(v, 'PE'), subset=['PE']
                        ).map(
                            lambda v: color_pg_pe_pp(v, 'PP'), subset=['PP']
                        )

                        st.dataframe(
                            styled,
                            hide_index=True,
                            use_container_width=True,
                            height=600
                        )



################## modo clasificacion fin ############
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


            ############fin expander rachas

with st.expander("🔍 Buscador de Equipos", expanded=False):
    st.markdown("""
    <style>
    /* Ancho completo para selects en este expander */
    div[data-testid="stExpander"] [data-testid="stSelectbox"] {
        width: 100% !important;
    }
    div[data-testid="stExpander"] [data-testid="stSelectbox"] > div {
        width: 100% !important;
        min-width: unset !important;
    }
    div[data-testid="stExpander"] [data-testid="stSelectbox"] > div > div {
        width: 100% !important;
        min-width: 100% !important;
    }
    /* Evita que las columnas compriman el contenido en móvil */
    div[data-testid="stExpander"] [data-testid="stHorizontalBlock"] > div {
        min-width: 45% !important;
        flex-shrink: 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.caption("Busca equipos que cumplan condiciones en cualquier liga/temporada")

    df_busca = df.copy()

    col_liga, col_temp = st.columns(2)
    ligas_busca = col_liga.multiselect("Ligas", sorted(df_busca['League'].unique()), default=[], key="be2_ligas_v2")
    temps_busca = col_temp.multiselect("Temps", sorted(df_busca['Season'].unique()), default=[], key="be2_temps_v2")

    if ligas_busca: df_busca = df_busca[df_busca['League'].isin(ligas_busca)]
    if temps_busca: df_busca = df_busca[df_busca['Season'].isin(temps_busca)]

    if df_busca.empty:
        st.warning("Selecciona liga/temporada")
        st.stop()

    df_be, _ = calcular_estado_jornada(df_busca)

    # --- NIVEL 2: JORNADA DE/A en misma línea ---
    st.markdown("**Jornadas**")
    jmin, jmax = int(df_be['Jornada'].min()), int(df_be['Jornada'].max())
    col_j1, col_j2 = st.columns(2)
    j_desde_be = col_j1.number_input("De", min_value=jmin, max_value=jmax, value=jmin, step=1, key='be2_j_desde', label_visibility="collapsed")
    j_hasta_be = col_j2.number_input("A", min_value=jmin, max_value=jmax, value=jmax, step=1, key='be2_j_hasta', label_visibility="collapsed")
    if j_desde_be > j_hasta_be:
        st.warning("'De' no puede ser mayor que 'A'")
        j_desde_be = j_hasta_be
    j_rango = (int(j_desde_be), int(j_hasta_be))

    # --- NIVEL 3: MODO en línea completa ---
    modo_busca = st.radio("Modo búsqueda", ["Últimos X partidos", "% en rango jornadas"], horizontal=True, key="be2_modo")

    # --- NIVEL 4: CAJITA DINÁMICA según modo ---
    if modo_busca == "Últimos X partidos":
        ultimos_x = st.number_input("Últimos", 1, 38, 5, key="be2_ultimos")
        pct_min_rango = None
    else:
        pct_min_rango = st.number_input("% mín", 0, 100, 50, 5, key="be2_pct_min")
        ultimos_x = None

    

    # --- RESTO IGUAL: Fav/Cntr1, AM, Vlr1, Parte ---
    colc1, colc2, colc3, colc4 = st.columns(4)
    fav_c1 = colc1.selectbox("Fav/Cntr1", ["Todo","AF","C"], key="be2_favc1", help="AF=a favor del equipo | C=en contra")
    am_busca = colc2.selectbox("AM", ["Todos","Si","No"], key="be2_am")
    vlr1_busca = colc3.selectbox("Vlr1", ["Ninguno"] + [i/2 for i in range(21)], key="be2_vlr1")
    parte_busca = colc4.selectbox("Parte", ["Todo","1T","2T"], key="be2_parte")

    # --- Col1, Op1, L/V, Minutos ---
    columnas_numericas_be = ['FTHG','FTAG','HTHG','HTAG','HS','AS','HST','AST','HF','AF','HC','AC','HY','AY','HR','AR','GolesTotales','GolesHT','Goles2T','corneTot','TargAmTot','tirosTot','tirosPuertaTot','faltasTot','TargRojTot']
    ABREV_COL_BE = {
        'FTHG': 'GL','FTAG': 'GV','HTHG': 'G1L','HTAG': 'G1V',
        'HS': 'TL','AS': 'TV','HST': 'TPL','AST': 'TPV',
        'HF': 'FL','AF': 'FV','HC': 'CL','AC': 'CV',
        'HY': 'AL','AY': 'AV','HR': 'RL','AR': 'RV',
        'GolesTotales': 'GT','GolesHT': 'G1T','Goles2T': 'G2T',
        'corneTot': 'CT','TargAmTot': 'TAM',
        'tirosTot': 'TT','tirosPuertaTot': 'TPT','faltasTot': 'FT','TargRojTot': 'TRT',
        'Ninguno': '—',
    }
    colc5, colc6 = st.columns(2)
    col1_busca = colc5.selectbox("Col1", ["Ninguno"] + columnas_numericas_be, format_func=lambda x: ABREV_COL_BE.get(x, x), key="be2_col1")
    op1_busca = colc6.selectbox("Op1", ["=", ">", ">=", "<", "<="], key="be2_op1")

    colc7, colc8 = st.columns(2)
    lv_busca = colc7.selectbox("L/V", ["Todo","Local","Visitante"], key="be2_lv")
    st.caption("Minutos por parte")
    col_1t, col_2t, col_ext = st.columns(3)
    min_1t = col_1t.number_input("1ªT", min_value=0, max_value=60, value=45, step=1, key="be2_min_1t")
    min_2t = col_2t.number_input("2ªT", min_value=0, max_value=60, value=45, step=1, key="be2_min_2t")
    min_ext = col_ext.number_input("+", min_value=0, max_value=30, value=10, step=1, key="be2_min_ext", help="Añadido/Prórroga")

    if st.button("🔎 Buscar equipos", type="primary", use_container_width=True, key="be2_buscar"):
        equipos = pd.unique(df_be[['HomeTeam','AwayTeam']].values.ravel())
        resultados = []

        for eq in equipos:
            df_eq = df_be[(df_be['HomeTeam']==eq) | (df_be['AwayTeam']==eq)].copy()
            if df_eq.empty: continue

            if lv_busca == "Local":
                df_eq = df_eq[df_eq['HomeTeam']==eq]
            elif lv_busca == "Visitante":
                df_eq = df_eq[df_eq['AwayTeam']==eq]
            if df_eq.empty: continue

            df_eq = df_eq[(df_eq['Jornada']>=j_rango[0]) & (df_eq['Jornada']<=j_rango[1])]

            if modo_busca == "Últimos X partidos":
                df_eq = df_eq.sort_values('Date').tail(ultimos_x)

            if df_eq.empty: continue

            total = len(df_eq)
            es_local = df_eq['HomeTeam']==eq

            if parte_busca == "1T":
                gf = np.where(es_local, df_eq['HTHG'], df_eq['HTAG'])
                gc = np.where(es_local, df_eq['HTAG'], df_eq['HTHG'])
            elif parte_busca == "2T":
                gf = np.where(es_local, df_eq['FTHG']-df_eq['HTHG'], df_eq['FTAG']-df_eq['HTAG'])
                gc = np.where(es_local, df_eq['FTAG']-df_eq['HTAG'], df_eq['FTHG']-df_eq['HTHG'])
            else:
                gf = np.where(es_local, df_eq['FTHG'], df_eq['FTAG'])
                gc = np.where(es_local, df_eq['FTAG'], df_eq['FTHG'])

            cumple = np.ones(len(df_eq), dtype=bool)

            if vlr1_busca!= "Ninguno":
                if fav_c1 == "AF":
                    cumple = cumple & (gf > float(vlr1_busca))
                elif fav_c1 == "C":
                    cumple = cumple & (gc > float(vlr1_busca))
                else:
                    cumple = cumple & ((gf + gc) > float(vlr1_busca))

            if col1_busca!= "Ninguno" and vlr1_busca != "Ninguno":
                mapa_col = {'HS':'AS','AS':'HS','HST':'AST','AST':'HST','HF':'AF','AF':'HF','HC':'AC','AC':'HC',
                            'HY':'AY','AY':'HY','HR':'AR','AR':'HR','FTHG':'FTAG','FTAG':'FTHG','HTHG':'HTAG','HTAG':'HTHG'}
                if fav_c1 == "AF":
                    val_col = np.where(es_local, df_eq[col1_busca], df_eq.get(mapa_col.get(col1_busca, col1_busca), df_eq[col1_busca]))
                elif fav_c1 == "C":
                    val_col = np.where(es_local, df_eq.get(mapa_col.get(col1_busca, col1_busca), 0), df_eq.get(col1_busca, 0))
                else:
                    val_col = df_eq[col1_busca]

                val = float(vlr1_busca)
                if op1_busca == "=": cumple = cumple & (val_col == val)
                elif op1_busca == ">": cumple = cumple & (val_col > val)
                elif op1_busca == ">=": cumple = cumple & (val_col >= val)
                elif op1_busca == "<": cumple = cumple & (val_col < val)
                elif op1_busca == "<=": cumple = cumple & (val_col <= val)

            if am_busca == "Si":
                cumple = cumple & (gf > 0) & (gc > 0)
            elif am_busca == "No":
                cumple = cumple & ~((gf > 0) & (gc > 0))

            hits = cumple.sum()
            pct = hits / total * 100 if total else 0

            if modo_busca == "% en rango jornadas" and pct < pct_min_rango:
                continue

            if hits > 0:
                gana = ((es_local) & (df_eq['FTHG']>df_eq['FTAG'])) | ((~es_local) & (df_eq['FTAG']>df_eq['FTHG']))
                pierde = ((es_local) & (df_eq['FTHG']<df_eq['FTAG'])) | ((~es_local) & (df_eq['FTAG']<df_eq['FTHG']))

                df_cumple = df_eq[cumple].copy()
                partes_jors = []
                for (season, j), g in df_cumple.groupby(['Season','Jornada'], sort=True):
                    gana_j = ((g['HomeTeam']==eq) & (g['FTHG']>g['FTAG'])).any() or ((g['AwayTeam']==eq) & (g['FTAG']>g['FTHG'])).any()
                    pierde_j = ((g['HomeTeam']==eq) & (g['FTHG']<g['FTAG'])).any() or ((g['AwayTeam']==eq) & (g['FTAG']<g['FTHG'])).any()
                    color = '#0f8105' if gana_j else '#f31818' if pierde_j else '#0A2342'
                    es_loc_j = (g['HomeTeam']==eq).iloc[0]
                    sufijo = 'c' if es_loc_j else 'f'
                    gf_j = g['FTHG'].iloc[0] if es_loc_j else g['FTAG'].iloc[0]
                    gc_j = g['FTAG'].iloc[0] if es_loc_j else g['FTHG'].iloc[0]
                    am = "●" if (gf_j > 0 and gc_j > 0) else ""
                    txt = f"J{int(j)}{sufijo}{am}"
                    if len(g) > 1: txt += f" - {len(g)}#"
                    partidos_html = []
                    for _, r in g.iterrows():
                        partidos_html.append(formatear_h2h_compacto(r, eq))
                    viñeta = "".join(partidos_html)
                    carta = f"""<details style="display:inline-block;margin-right:1px"><summary style="color:{color};font-weight:700;cursor:pointer;display:inline;list-style:none">{txt}</summary><div style="position:absolute;z-index:999;background:#FFFFFF;border:2px solid #000;padding:6px;margin-top:2px;box-shadow:2px 2px 6px rgba(0,0,0,0.3);max-width:320px">{viñeta}</div></details>"""
                    partes_jors.append(carta)

                jors_txt = "".join(partes_jors)
                resultados.append({
                    'Equipo': eq, 'Liga': df_eq.iloc[0]['League'], 'PJ': total, 'Cumple': hits, '%': round(pct,1),
                    'G': gana.sum(), 'E': (total - gana.sum() - pierde.sum()), 'P': pierde.sum(), 'Jornadas': jors_txt
                })

        if resultados:
            df_res = pd.DataFrame(resultados).sort_values(['%','Cumple'], ascending=False)
            st.success(f"Encontrados {len(df_res)} equipos")
            lineas_html = []
            for _, r in df_res.iterrows():
                linea = f"""<div style='font-size:11px; font-family:monospace; line-height:1.4; padding:2px 0; border-bottom:1px solid #eee; white-space:nowrap; overflow:hidden; text-overflow:ellipsis'>
                    <span style='color:#555; font-weight:700'>{r['Liga'][:3].upper()}</span> |
                    <span style='font-weight:900; color:#0A2342'>{r['Equipo']}</span> |
                    <span style='color:#0f8105; font-weight:700'>{r['%']}%</span> |
                    {r['Jornadas']}
                </div>"""
                lineas_html.append(linea)
            st.markdown(f"<div style='background:#fff; border:1px solid #ddd; max-height:500px; overflow-y:auto; padding:4px'>{''.join(lineas_html)}</div>", unsafe_allow_html=True)
        else:
            st.warning("Ningún equipo cumple esas condiciones")


# --- RESUMEN JORNADAS + % G/E/P CORREGIDO ---
def resumen_jornadas_visual(df_partidos, df_clas, liga, season, j_desde, j_hasta, condicion_lv="Todo", filtro_res="Todo"):
    df_liga = df_partidos[(df_partidos['League']==liga) & (df_partidos['Season']==season) &
                          (df_partidos['Jornada']>=j_desde) & (df_partidos['Jornada']<=j_hasta)].copy()
    if df_liga.empty: return []

    ult_j = df_liga['Jornada'].max()
    clas_ult = df_clas[(df_clas['League']==liga) & (df_clas['Season']==season) & (df_clas['Jornada']==ult_j)]
    if not clas_ult.empty:
        orden_equipos = clas_ult.sort_values('Pos')['Equipo'].tolist()
    else:
        orden_equipos = sorted(pd.unique(df_liga[['HomeTeam','AwayTeam']].values.ravel()))

    lineas = []
    for equipo in orden_equipos:
        df_eq_base = df_liga[(df_liga['HomeTeam']==equipo) | (df_liga['AwayTeam']==equipo)].copy()
        if df_eq_base.empty: continue

        if condicion_lv == "Local":
            df_eq_base = df_eq_base[df_eq_base['HomeTeam']==equipo]
        elif condicion_lv == "Visitante":
            df_eq_base = df_eq_base[df_eq_base['AwayTeam']==equipo]
        if df_eq_base.empty: continue

        es_local = df_eq_base['HomeTeam']==equipo
        gana_base = (es_local & (df_eq_base['FTHG']>df_eq_base['FTAG'])) | (~es_local & (df_eq_base['FTAG']>df_eq_base['FTHG']))
        pierde_base = (es_local & (df_eq_base['FTHG']<df_eq_base['FTAG'])) | (~es_local & (df_eq_base['FTAG']<df_eq_base['FTHG']))
        empata_base = ~(gana_base | pierde_base)

        total_pj = len(df_eq_base)
        n_g = gana_base.sum(); n_e = empata_base.sum(); n_p = pierde_base.sum()
        p_g = round(n_g/total_pj*100) if total_pj else 0
        p_e = round(n_e/total_pj*100) if total_pj else 0
        p_p = round(n_p/total_pj*100) if total_pj else 0

        pj_casa = es_local.sum()
        pj_fuera = (~es_local).sum()
        p_fx = round((~es_local & gana_base).sum()/pj_fuera*100) if pj_fuera else 0
        p_cx = round((es_local & gana_base).sum()/pj_casa*100) if pj_casa else 0
        p_fpx = round((~es_local & pierde_base).sum()/pj_fuera*100) if pj_fuera else 0
        p_cpx = round((es_local & pierde_base).sum()/pj_casa*100) if pj_casa else 0
        p_fex = round((~es_local & empata_base).sum()/pj_fuera*100) if pj_fuera else 0
        p_cex = round((es_local & empata_base).sum()/pj_casa*100) if pj_casa else 0

        df_eq_filtro = df_eq_base.copy()
        if filtro_res!= "Todo":
            if filtro_res == "G":
                df_eq_filtro = df_eq_filtro[gana_base]
            elif filtro_res == "E":
                df_eq_filtro = df_eq_filtro[empata_base]
            elif filtro_res == "P":
                df_eq_filtro = df_eq_filtro[pierde_base]
            elif filtro_res == "GE":
                df_eq_filtro = df_eq_filtro[gana_base | empata_base]
            elif filtro_res == "PE":
                df_eq_filtro = df_eq_filtro[pierde_base | empata_base]
            elif filtro_res == "GP":
                df_eq_filtro = df_eq_filtro[gana_base | pierde_base]

        if df_eq_filtro.empty: continue

        df_eq_filtro['res'] = np.where(gana_base[df_eq_filtro.index], 'win', np.where(pierde_base[df_eq_filtro.index], 'loss', 'draw'))
        df_eq_filtro['color'] = np.where(gana_base[df_eq_filtro.index], '#0f8105', np.where(pierde_base[df_eq_filtro.index], '#f31818', '#0A2342'))

        partes = []
        for (season, j), g in df_eq_filtro.groupby(['Season','Jornada'], sort=True):
            color = g['color'].iloc[0]
            es_loc_j = (g['HomeTeam']==equipo).iloc[0]
            sufijo = 'c' if es_loc_j else 'f'
            txt = f"J{int(j)}{sufijo}"

            # CAMBIO: añadir. si hay AM en algún partido de esa jornada
            if ((g['FTHG'] > 0) & (g['FTAG'] > 0)).any():
                txt += '●'

            if len(g) > 1:
                txt += f" - {len(g)}#"

            # --- CAMBIO CLAVE: partido entero en vez de solo resultado ---
            partidos_html = []
            for _, r in g.iterrows():
                partidos_html.append(formatear_h2h_compacto(r, equipo))
            resultado = "".join(partidos_html)
            # --- FIN CAMBIO ---

            partes.append(f"<details style='display:inline-block;margin-right:1px'><summary style='color:{color};font-weight:700;cursor:pointer;display:inline;list-style:none'>{txt}</summary><div style='background:#FFFFFF;border:2px solid #000;padding:4px;margin-top:2px;box-shadow:2px 2px 6px rgba(0,0,0,0.3);max-width:320px'>{resultado}</div></details>")

        # CAMBIO: nombre en mayúsculas, línea 2 G/P/E con f: y c:, línea 3 jornadas
        linea = f"""<div style='font-size:11px;line-height:1.4;margin:6px 0;padding-bottom:4px;border-bottom:1px solid #eee'>
        <b>{equipo.upper()}</b><br>
        <span style='color:#0f8105;font-weight:700'>G:{p_g}% #{n_g}</span> c:{p_cx}% f:{p_fx}% | <span style='color:#f31818;font-weight:700'>P:{p_p}% #{n_p}</span> c:{p_cpx}% f:{p_fpx}% | <span style='color:#0A2342;font-weight:700'>E:{p_e}% #{n_e}</span> c:{p_cex}% f:{p_fex}%<br>
        {"|".join(partes)}
        </div>"""
        lineas.append(linea)
    return lineas

######"clasif".
with st.expander("📅Clasif.", expanded=False):
    # --- FILTROS SOLO PARA ESTE BLOQUE ---
    col_cl1, col_cl2 = st.columns(2)

    ligas_clasif = col_cl1.multiselect(
        "Liga",
        sorted(df_base['League'].unique()),
        default=[liga_sel[0]] if liga_sel else [],
        key="clasif_ligas_local"
    )
    temps_clasif = col_cl2.multiselect(
        "Temporada",
        sorted(df_base['Season'].unique()),
        default=[temp_sel[-1]] if temp_sel else [],
        key="clasif_temps_local"
    )

    # DataFrame filtrado SOLO para este bloque
    df_base_clasif = df_base[df_base['League'].isin(ligas_clasif) & df_base['Season'].isin(temps_clasif)]
    df_clas_base_clasif = df_clas_base[df_clas_base['League'].isin(ligas_clasif) & df_clas_base['Season'].isin(temps_clasif)]

    

    if len(df_base_clasif) > 0:
        col_lv, col_res = st.columns([1, 1])
        condicion_lv = col_lv.selectbox(
            "L/V",
            ["Todo", "Local", "Visitante"],
            key="clasf_lv_local"
        )
        filtro_res = col_res.selectbox(
            "Res",
            ["Todo", "G", "E", "P", "GE", "PE", "GP"],
            key="clasf_res_local"
        )

        # --- CAJITAS % ---
        col_pct1, col_pct2 = st.columns(2)
        pct_min = col_pct1.number_input(
            "% Mín",
            min_value=0,
            max_value=100,
            value=0,
            step=1,
            key="clasf_pct_min_local"
        )
        pct_max = col_pct2.number_input(
            "% Máx",
            min_value=0,
            max_value=100,
            value=100,
            step=1,
            key="clasf_pct_max_local"
        )
        if pct_min > pct_max:
            st.warning("% Mín no puede ser mayor que % Máx")
            pct_min = pct_max

        # --- CAJITAS LIBRES PARA JORNADAS ---
        col_j1, col_j2 = st.columns(2)

        if len(df_base) > 0 and 'Jornada' in df_base.columns:
            j_min_default = int(df_base['Jornada'].min())
            j_max_default = int(df_base['Jornada'].max())
        else:
            j_min_default = 1
            j_max_default = 38

        j_desde = col_j1.number_input(
            "Jornada De",
            min_value=1,
            max_value=46,
            value=j_min_default,
            step=1,
            key='clasf_j_desde_local'
        )
        j_hasta = col_j2.number_input(
            "Jornada A",
            min_value=1,
            max_value=46,
            value=j_max_default,
            step=1,
            key='clasf_j_hasta_local'
        )
        if j_desde > j_hasta:
            st.warning("Jornada 'De' no puede ser mayor que 'A'")
            j_desde = j_hasta

        # --- GENERAR RESULTADOS CON DF_BASE_CLASIF ---
        for liga in ligas_clasif:
            for temp in temps_clasif:
                lineas = resumen_jornadas_visual(
                    df_base_clasif, df_clas_base_clasif, liga, temp,
                    j_desde, j_hasta, condicion_lv, filtro_res
                )

                # Filtrar por %
                if pct_min > 0 or pct_max < 100:
                    lineas_filtradas = []
                    for linea in lineas:
                        pct_match = None
                        if filtro_res == "G":
                            m = re.search(r'G:(\d+)%', linea)
                            if m: pct_match = int(m.group(1))
                        elif filtro_res == "E":
                            m = re.search(r'E:(\d+)%', linea)
                            if m: pct_match = int(m.group(1))
                        elif filtro_res == "P":
                            m = re.search(r'P:(\d+)%', linea)
                            if m: pct_match = int(m.group(1))
                        else:
                            m = re.search(r'G:(\d+)%', linea)
                            if m: pct_match = int(m.group(1))

                        if pct_match is not None and pct_min <= pct_match <= pct_max:
                            lineas_filtradas.append(linea)
                    lineas = lineas_filtradas

                if lineas:
                    st.markdown(
                        f"<div style='background:#f8f9fa;padding:8px 10px;border-left:3px solid #0A2342;margin:6px 0 10px 0;font-size:11px'>"
                        f"<b style='font-size:11px'>Filtro J{j_desde}-J{j_hasta} {condicion_lv} {filtro_res} %:{pct_min}-{pct_max} ({len(lineas)} equipos)</b><br>"
                        + "<br>".join(lineas) + "</div>",
                        unsafe_allow_html=True
                    )
                else:
                    st.info(f"No hay datos en J{j_desde}-J{j_hasta} con esos filtros para {liga} {temp}")
    else:
        st.markdown("<div style='font-size:11px'>Selecciona Liga y Temporada para ver el resumen</div>", unsafe_allow_html=True)


#################generador de apuesta
with st.expander("🎯 Creador Apuestas", expanded=False):
    st.caption("Predicción universal - misma tarjeta")

    col_l, col_t = st.columns(2)
    ca_liga = col_l.selectbox("Liga", sorted(df['League'].unique()), key="ca_liga")
    ca_temp = col_t.selectbox("Temporada", sorted(df[df['League']==ca_liga]['Season'].unique(), reverse=True), key="ca_temp")

    df_creador_base = df[(df['League']==ca_liga) & (df['Season']==ca_temp)].copy()
    df_creador, _ = calcular_estado_jornada(df_creador_base)

    jmin_all = int(df_creador['Jornada'].min()); jmax_all = int(df_creador['Jornada'].max())
    j1, j2 = st.slider("Jornadas a analizar", jmin_all, jmax_all, (jmin_all, jmax_all), key="ca_jornadas")

    equipos = sorted(pd.unique(df_creador[['HomeTeam','AwayTeam']].values.ravel()))
    col_eq1, col_eq2 = st.columns(2)
    eq1 = col_eq1.selectbox("Eq1 (local)", [""] + equipos, key="ca_eq1")
    eq2 = col_eq2.selectbox("Eq2 (visitante)", [""] + [e for e in equipos if e != eq1], key="ca_eq2")

    if st.button("Generar partido", key="ca_gen", use_container_width=True) and eq1 and eq2:
        df_r = df_creador[(df_creador['Jornada']>=j1) & (df_creador['Jornada']<=j2)].copy()
        m1 = df_r[(df_r['HomeTeam']==eq1)|(df_r['AwayTeam']==eq1)].sort_values('Date').tail(20)
        m2 = df_r[(df_r['HomeTeam']==eq2)|(df_r['AwayTeam']==eq2)].sort_values('Date').tail(20)

        if len(m1)<4 or len(m2)<4:
            st.warning("Necesitas mínimo 4 partidos en el rango")
            st.stop()

        # --- CALIBRACIÓN LIGA ---
        lg_home = df_r['FTHG'].mean(); lg_away = df_r['FTAG'].mean()
        lg_g = (lg_home + lg_away)/2 or 1.3
        home_adv = lg_home / max(lg_away, 0.1)

        def fuerza(eq, df_eq):
            w = np.exp(np.linspace(-0.5,0,len(df_eq))); w/=w.sum()
            loc = df_eq['HomeTeam']==eq
            gf = np.average(np.where(loc, df_eq['FTHG'], df_eq['FTAG']), weights=w)
            gc = np.average(np.where(loc, df_eq['FTAG'], df_eq['FTHG']), weights=w)
            htg = np.average(np.where(loc, df_eq['HTHG'], df_eq['HTAG']), weights=w)
            perf = np.clip(np.average(np.where(loc, df_eq['HomePerf'], df_eq['AwayPerf']), weights=w), 0.8, 1.8)
            pos = np.average(np.where(loc, df_eq['HomePosPrev'], df_eq['AwayPosPrev']), weights=w)
            hs = np.average(np.where(loc, df_eq['HS'], df_eq['AS']), weights=w)
            hst = np.average(np.where(loc, df_eq['HST'], df_eq['AST']), weights=w)
            hf = np.average(np.where(loc, df_eq['HF'], df_eq['AF']), weights=w)
            hc = np.average(np.where(loc, df_eq['HC'], df_eq['AC']), weights=w)
            hy = np.average(np.where(loc, df_eq['HY'], df_eq['AY']), weights=w)
            hr = np.average(np.where(loc, df_eq['HR'], df_eq['AR']), weights=w)

            atk = np.clip((gf/lg_g) * (0.7 + 0.3*perf/1.3), 0.65, 1.5)
            defe = np.clip((gc/lg_g) * (1.2 - 0.2*perf/1.3), 0.7, 1.4)

            # --- PEDIGREE HISTÓRICO (FIX) ---
            hist = 1.0
            temps = sorted(df['Season'].unique())
            if ca_temp in temps:
                idx = temps.index(ca_temp)
                prev_temps = temps[max(0, idx-3):idx]
                pos_hist = []
                for t in prev_temps:
                    df_t_base = df[(df['League']==ca_liga) & (df['Season']==t)]
                    if df_t_base.empty: continue
                    df_t, _ = calcular_estado_jornada(df_t_base)  # cacheado
                    ult_j = df_t['Jornada'].max()
                    r = df_t[(df_t['Jornada']==ult_j) & ((df_t['HomeTeam']==eq)|(df_t['AwayTeam']==eq))]
                    if not r.empty:
                        row = r.iloc[-1]
                        p = row['HomePosPrev'] if row['HomeTeam']==eq else row['AwayPosPrev']
                        pos_hist.append(p)
                if pos_hist:
                    avg_pos = np.mean(pos_hist)
                    hist = float(np.clip(1.18 - (avg_pos-1)*0.018, 0.88, 1.15))

            atk = np.clip(atk * hist, 0.6, 1.6)
            defe = np.clip(defe * (2 - hist), 0.65, 1.5)

            return {'atk':atk,'def':defe,'p1':htg/max(gf,0.1),'perf':perf,'pos':pos,
                    'hs':hs,'hst':hst,'hf':hf,'hc':hc,'hy':hy,'hr':hr}

        f1, f2 = fuerza(eq1,m1), fuerza(eq2,m2)
        pos_fact = np.clip(1 + (f2['pos']-f1['pos'])*0.01, 0.9, 1.1)

        # contexto
        pts1 = m1.iloc[-1]['HomePtsPrev'] if m1.iloc[-1]['HomeTeam']==eq1 else m1.iloc[-1]['AwayPtsPrev']
        pts2 = m2.iloc[-1]['HomePtsPrev'] if m2.iloc[-1]['HomeTeam']==eq2 else m2.iloc[-1]['AwayPtsPrev']
        jor_actual = (j1+j2)//2
        n_eq = df_r['HomeTeam'].nunique()
        peso_h, peso_a = 1.0, 1.0

        # últimos 8 jornadas
        if jor_actual > jmax_all - 8:
            peso_h *= 1.07; peso_a *= 1.07

        # ... (tu lógica de descenso, derbi, venganza, hundido, vida o muerte se mantiene igual) ...
        # [Pega aquí tus bloques de rivalidad/venganza/hundido sin cambios]

        lam_h = np.clip(lg_g * f1['atk'] * f2['def'] * home_adv * pos_fact * peso_h, 0.4, 2.8)
        lam_a = np.clip(lg_g * f2['atk'] * f1['def'] / home_adv / pos_fact * peso_a, 0.4, 2.6)

        g1, g2 = int(round(lam_h)), int(round(lam_a))
        h1 = int(round(lam_h * f1['p1'])); a1 = int(round(lam_a * f2['p1']))
        h2, a2 = max(0,g1-h1), max(0,g2-a1)

        ab1, ab2 = abreviar_equipo(eq1), abreviar_equipo(eq2)
        ht_res = ab1 if h1>a1 else ab2 if a1>h1 else 'E'
        ft_res = ab1 if g1>g2 else ab2 if g2>g1 else 'E'

        html = f"""
        <div style='font-family:monospace; font-size:11px; line-height:1.15; padding:6px; background:#fff; border:2px solid #000'>
        <b>{ca_liga} {ca_temp} | J{j1}-{j2}</b><br>
        {ht_res}/{ft_res}<br>
        {ab1} {g1}-{g2} {ab2}<br>
        Perf:{f1['perf']:.1f}-{f2['perf']:.1f}<br>
        1p:{h1}G | 1p:{a1}G<br>
        2p:{h2}G | 2p:{a2}G<br>
        {int(f1['hs'])}T {int(f1['hst'])}TP {int(f1['hf'])}F {int(f1['hc'])}C {int(f1['hy'])}A {int(f1['hr'])}R<br>
        {int(f2['hs'])}T {int(f2['hst'])}TP {int(f2['hf'])}F {int(f2['hc'])}C {int(f2['hy'])}A {int(f2['hr'])}R
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)
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
    with st.expander("🗓️ Agenda Apuestas", expanded=False):
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

            # === DASHBOARD EDGE ===
            with st.expander("📊 Ver dónde tengo edge", expanded=False):
                df_analisis = df_ag[df_ag['resultado']!= 'Pendiente'].copy()
                
                # FILTROS DINÁMICOS
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
                        st.dataframe(liga_stats.sort_values('ROI%', ascending=False), hide_index=True, use_container_width=True, column_config={"liga":"Liga","Ap":"Ap","W":"✅","L":"❌","Win%":"%W","ROI%":"ROI","Benef":"€"})
                    with tab2:
                        tipo_stats = df_analisis.groupby('tipo').agg(Ap=('id','count'),W=('resultado', lambda x: (x=='Ganada').sum()),Benef=('beneficio','sum'),Stake=('stake','sum')).reset_index()
                        tipo_stats['ROI%'] = (tipo_stats['Benef']/tipo_stats['Stake']*100).round(1)
                        st.dataframe(tipo_stats.sort_values('ROI%', ascending=False), hide_index=True, use_container_width=True)
                    with tab3:
                        df_analisis['equipo'] = df_analisis['partido'].str.split(' vs ').str[0]
                        equipo_stats = df_analisis.groupby('equipo').agg(Ap=('id','count'),W=('resultado', lambda x: (x=='Ganada').sum()),Benef=('beneficio','sum')).reset_index()
                        equipo_stats = equipo_stats[equipo_stats['Ap']>=2]
                        equipo_stats['Win%'] = (equipo_stats['W']/equipo_stats['Ap']*100).round(0).astype(int)
                        st.dataframe(equipo_stats.sort_values('Benef', ascending=False).head(10), hide_index=True, use_container_width=True, column_config={"equipo":"Equipo","Ap":"Ap","W":"✅","Win%":"%W","Benef":"€"})
                else:
                    st.info("Cierra apuestas para ver stats")

            # LISTA RÁPIDA CON BORRADO INSTANTÁNEO
                        
            for ap in sorted(apuestas, key=lambda x: x['id'], reverse=True)[:50]:
                col1,col2,col3,col4 = st.columns([1.3,4.5,2.2,0.6])
                col1.caption(f"{ap['fecha']}")
                col2.write(f"**{ap['partido']}** {ap['marcador']} · **{ap.get('detalle','')}** · min {ap.get('minuto',0)}' · {ap.get('tipo','')}")
                col3.write(f"{ap['stake']}€ @ {ap['cuota']} → **{ap['resultado']}**")
                if col4.button("🗑️", key=f"del_{ap['id']}"):
                    # Borrado rápido sin rerun completo
                    agenda_data["apuestas"] = [a for a in apuestas if a['id']!= ap['id']]
                    guardar_agenda(agenda_data)

            # CERRAR APUESTAS - FUERA DEL BUCLE
            pend = [a for a in apuestas if a['resultado']=='Pendiente']
            if pend:
                opciones = {a['id']: f"{a['fecha']} | {a['partido']} ({a['marcador']}) - {a['stake']}€ @ {a['cuota']}" for a in pend}
                sel_id = st.selectbox("Cerrar apuesta", options=list(opciones.keys()),
                                     format_func=lambda x: opciones[x], key="sel_cerrar")

                col_r1, col_r2 = st.columns([1,2])
                res = col_r1.radio("Resultado", ["Ganada","Perdida","Nula"], horizontal=True, key="res_radio")

                if col_r2.button("💾 Guardar resultado", use_container_width=True, key="btn_guardar"):
                    for a in apuestas:
                        if a['id'] == sel_id:
                            a['resultado'] = res
                            if res == "Ganada":
                                a['beneficio'] = round((a['cuota']-1) * a['stake'], 2)
                            elif res == "Perdida":
                                a['beneficio'] = -a['stake']
                            else:
                                a['beneficio'] = 0
                            break
                    agenda_data["apuestas"] = apuestas
                    guardar_agenda(agenda_data)
            else:
                st.info("No hay pendientes")

# LLAMAR AL FRAGMENTO
mostrar_agenda()


################# filtro resumen
with st.expander("📋 Resumen", expanded=False):
    col_izq, col_der = st.columns(2)

    ligas_res = sorted(df['League'].unique())
    temps_res = sorted(df['Season'].unique())

    # FILA 1: Liga1 Liga2 - con multiselect
    liga1_res = col_izq.multiselect("Liga", ligas_res, default=[liga_sel[0]] if liga_sel else [], key="res_liga1")
    liga2_res = col_der.multiselect("Liga2", ligas_res, key="res_liga2")

    # FILA 2: Temp1 Temp2 - con multiselect
    temp1_res = col_izq.multiselect("Temporada", temps_res, default=[temp_sel[-1]] if temp_sel else [], key="res_temp1")
    temp2_res = col_der.multiselect("Temp2", temps_res, key="res_temp2")

    # FILA 3: Equipo1 Equipo2
    df_res_base1 = df[df['League'].isin(liga1_res) & df['Season'].isin(temp1_res)] if liga1_res and temp1_res else pd.DataFrame()
    equipos_res1 = sorted(pd.unique(df_res_base1[['HomeTeam','AwayTeam']].values.ravel())) if not df_res_base1.empty else []
    equipo_res = col_izq.selectbox("Equipo", [""] + equipos_res1, key="res_equipo1")

    equipos_res2 = []
    if liga2_res and temp2_res:
        df_res_base2 = df[df['League'].isin(liga2_res) & df['Season'].isin(temp2_res)]
        equipos_res2 = sorted(pd.unique(df_res_base2[['HomeTeam','AwayTeam']].values.ravel()))
    equipo2_res = col_der.selectbox("Equipo2", [""] + equipos_res2, key="res_equipo2")

    def calcular_stats_equipo(df_res_base, equipo_res, temps_res):
        if not equipo_res or df_res_base.empty:
            return None

        df_res, df_clas_res = calcular_estado_jornada(df_res_base)
        df_eq_total = df_res[(df_res['HomeTeam']==equipo_res) | (df_res['AwayTeam']==equipo_res)].copy()

        if df_eq_total.empty:
            return None

        lista_stats = []
        temps_ordenadas = sorted(temps_res, reverse=True)

        for temp in temps_ordenadas:
            df_eq = df_eq_total[df_eq_total['Season']==temp].copy()
            if df_eq.empty:
                continue

            total = len(df_eq)
            es_local = df_eq['HomeTeam']==equipo_res

            gana = ((es_local) & (df_eq['FTHG']>df_eq['FTAG'])) | ((~es_local) & (df_eq['FTAG']>df_eq['FTHG']))
            pierde = ((es_local) & (df_eq['FTHG']<df_eq['FTAG'])) | ((~es_local) & (df_eq['FTAG']<df_eq['FTHG']))
            empata = ~(gana | pierde)

            n_g, n_e, n_p = gana.sum(), empata.sum(), pierde.sum()
            pct_g, pct_e, pct_p = round(n_g/total*100), round(n_e/total*100), round(n_p/total*100)

            gf = np.where(es_local, df_eq['FTHG'], df_eq['FTAG'])
            gc = np.where(es_local, df_eq['FTAG'], df_eq['FTHG'])
            gf_tot, gc_tot = gf.sum(), gc.sum()
            gf_avg, gc_avg = round(gf.mean(),2), round(gc.mean(),2)

            hs = np.where(es_local, df_eq['HS'], df_eq['AS'])
            hst = np.where(es_local, df_eq['HST'], df_eq['AST'])
            hf = np.where(es_local, df_eq['HF'], df_eq['AF'])
            hc = np.where(es_local, df_eq['HC'], df_eq['AC'])
            hy = np.where(es_local, df_eq['HY'], df_eq['AY'])
            hr = np.where(es_local, df_eq['HR'], df_eq['AR'])

            am = ((gf > 0) & (gc > 0)).sum()
            over25 = (gf + gc > 2.5).sum()

            racha_actual = 0
            mejor_racha = 0
            for res in np.where(gana, 'G', np.where(pierde, 'P', 'E')):
                if res == 'G':
                    racha_actual += 1
                    mejor_racha = max(mejor_racha, racha_actual)
                else:
                    racha_actual = 0

            df_clas_temp = df_clas_res[(df_clas_res['Equipo']==equipo_res) & (df_clas_res['Season']==temp)]
            if not df_clas_temp.empty:
                ult_j = df_clas_temp['Jornada'].max()
                fila_final = df_clas_temp[df_clas_temp['Jornada']==ult_j].iloc[0]
                pos_final = int(fila_final['Pos'])
                pts_final = int(fila_final['Pts'])
            else:
                pos_final = 0
                pts_final = 0

            ult5 = ''.join(['G' if g else 'P' if p else 'E' for g,p in zip(gana.tail(5), pierde.tail(5))])
            jors_html = jornadas_conteo(df_eq['Jornada'], df_eq, equipo_res, None)

            lista_stats.append({
                'temp': temp, 'total': total, 'n_g': n_g, 'n_e': n_e, 'n_p': n_p,
                'pct_g': pct_g, 'pct_e': pct_e, 'pct_p': pct_p,
                'gf_tot': gf_tot, 'gc_tot': gc_tot, 'gf_avg': gf_avg, 'gc_avg': gc_avg,
                'am': am, 'over25': over25, 'hs': hs.mean(), 'hst': hst.mean(),
                'hf': hf.mean(), 'hc': hc.mean(), 'hy': hy.mean(), 'hr': hr.mean(),
                'mejor_racha': mejor_racha, 'ult5': ult5, 'pos_final': pos_final,
                'pts_final': pts_final, 'jors_html': jors_html, 'equipo': equipo_res
            })

        return lista_stats, df_clas_res, df_eq_total

    if st.button("🔍 Buscar resumen", type="primary", use_container_width=True, key="btn_resumen"):
        if not equipo_res:
            st.warning("Selecciona al menos Equipo")
        else:
            # Equipo 1 - ya son listas, no hace falta convertir
            stats1 = calcular_stats_equipo(df_res_base1, equipo_res, temp1_res)

            # Equipo 2 si existe
            stats2 = None
            if equipo2_res and liga2_res and temp2_res:
                df_res_base2 = df[df['League'].isin(liga2_res) & df['Season'].isin(temp2_res)]
                stats2 = calcular_stats_equipo(df_res_base2, equipo2_res, temp2_res)

            if not stats1:
                st.warning(f"{equipo_res} no tiene partidos en esa selección")
            else:
                lista_stats1, df_clas_res1, df_eq_total1 = stats1

                # === MINI RESUMEN EQ1 ===
                if lista_stats1:
                    filas = []
                    for s in lista_stats1: # Recorro todas las temps seleccionadas
                        df_temp = df_eq_total1[(df_eq_total1['Season']==s['temp'])].copy()
                        if df_temp.empty:
                            continue
                        es_local = df_temp['HomeTeam']==equipo_res
                        gana = ((es_local) & (df_temp['FTHG']>df_temp['FTAG'])) | ((~es_local) & (df_temp['FTAG']>df_temp['FTHG']))
                        pierde = ((es_local) & (df_temp['FTHG']<df_temp['FTAG'])) | ((~es_local) & (df_temp['FTAG']<df_temp['FTHG']))
                        empata = ~(gana | pierde)

                        g = int(gana.sum())
                        e = int(empata.sum())
                        p = int(pierde.sum())
                        pts = g*3 + e

                        dft = df_clas_res1[(df_clas_res1['Equipo']==equipo_res) & (df_clas_res1['Season']==s['temp'])]
                        if not dft.empty:
                            ult_jornada = dft.sort_values('Jornada').iloc[-1]
                            pos = int(ult_jornada['Pos'])
                        else:
                            pos = 0

                        linea = f"<div style='font-size:10px; font-family:monospace; line-height:1.2'><b>{equipo_res.title()}</b> {s['temp']}: <b>{pos}º</b> {pts}pts | <span style='color:#15803d'>{g}G</span> <span style='color:#000000'>{e}E</span> <span style='color:#b91c1c'>{p}P</span></div>"
                        filas.append(linea)

                    st.caption(f"Resumen {equipo_res}")
                    st.markdown("\n".join(filas), unsafe_allow_html=True)

                # === MINI RESUMEN EQ2 SI EXISTE ===
                if stats2:
                    lista_stats2, df_clas_res2, df_eq_total2 = stats2
                    filas2 = []
                    for s in lista_stats2:
                        df_temp = df_eq_total2[(df_eq_total2['Season']==s['temp'])].copy()
                        if df_temp.empty:
                            continue
                        es_local = df_temp['HomeTeam']==equipo2_res
                        gana = ((es_local) & (df_temp['FTHG']>df_temp['FTAG'])) | ((~es_local) & (df_temp['FTAG']>df_temp['FTHG']))
                        pierde = ((es_local) & (df_temp['FTHG']<df_temp['FTAG'])) | ((~es_local) & (df_temp['FTAG']<df_temp['FTHG']))
                        empata = ~(gana | pierde)

                        g = int(gana.sum())
                        e = int(empata.sum())
                        p = int(pierde.sum())
                        pts = g*3 + e

                        dft = df_clas_res2[(df_clas_res2['Equipo']==equipo2_res) & (df_clas_res2['Season']==s['temp'])]
                        if not dft.empty:
                            ult_jornada = dft.sort_values('Jornada').iloc[-1]
                            pos = int(ult_jornada['Pos'])
                        else:
                            pos = 0

                        linea = f"<div style='font-size:10px; font-family:monospace; line-height:1.2'><b>{equipo2_res.title()}</b> {s['temp']}: <b>{pos}º</b> {pts}pts | <span style='color:#15803d'>{g}G</span> <span style='color:#000000'>{e}E</span> <span style='color:#b91c1c'>{p}P</span></div>"
                        filas2.append(linea)

                    st.caption(f"Resumen {equipo2_res}")
                    st.markdown("\n".join(filas2), unsafe_allow_html=True)

                                # === GRÁFICA PEQUEÑA ===
                import matplotlib.pyplot as plt
                import matplotlib.colors as mcolors
                
                df_graf1 = df_clas_res1[(df_clas_res1['Equipo']==equipo_res) & (df_clas_res1['Season'].isin(temp1_res))]

                fig = plt.figure(figsize=(3, 1), dpi=100)
                ax = fig.add_subplot(111)
                
                leyendas = []

                # Equipo 1 - todas las temps
                for temp in temp1_res:
                    d = df_graf1[df_graf1['Season']==temp].sort_values('Jornada')
                    if not d.empty:
                        line, = ax.plot(d['Jornada'], d['Pts'], linewidth=2)
                        color_hex = mcolors.to_hex(line.get_color()) # Convierto C0 -> #1f77b4
                        leyendas.append(f"<span style='color:{color_hex}; font-size:16px'>●</span> {equipo_res} {temp}")

                # Equipo 2 si existe
                if stats2:
                    df_graf2 = df_clas_res2[(df_clas_res2['Equipo']==equipo2_res) & (df_clas_res2['Season'].isin(temp2_res))]
                    for temp in temp2_res:
                        d = df_graf2[df_graf2['Season']==temp].sort_values('Jornada')
                        if not d.empty:
                            line, = ax.plot(d['Jornada'], d['Pts'], linewidth=2, linestyle='--')
                            color_hex = mcolors.to_hex(line.get_color())
                            leyendas.append(f"<span style='color:{color_hex}; font-size:16px'>●</span> {equipo2_res} {temp}")

                ax.set_xticks(range(0, 39, 10))
                ax.tick_params(labelsize=6)
                plt.tight_layout(pad=0.1)
                st.pyplot(fig, use_container_width=False)
                plt.close()
                
                                # Leyenda en texto debajo de la gráfica
                if leyendas:
                    st.markdown("<div style='font-size:10px; line-height:1.3'>" + "<br>".join(leyendas) + "</div>", unsafe_allow_html=True)
                # === TARJETAS DETALLADAS EQ1 ===
                for i, s in enumerate(lista_stats1):
                    st.markdown(f"""
                    <div style='background:#f8f9fa;padding:8px 10px;border-left:4px solid #0A2342;margin:6px 0;font-family:monospace;font-size:10px;line-height:1.4'>
                    <b style='font-size:12px'>{s['equipo'].title()} | {s['temp']}</b><br>
                    <b>{s['total']}PJ</b> → <span style='color:#0f8105;font-weight:900'>{s['n_g']}G {s['pct_g']}%</span> |
                    <span style='color:#b45309;font-weight:900'>{s['n_e']}E {s['pct_e']}%</span> |
                    <span style='color:#dc2626;font-weight:900'>{s['n_p']}P {s['pct_p']}%</span><br>
                    <b>Goles:</b> {s['gf_tot']}GF {s['gc_tot']}GC | Prom: {s['gf_avg']}-{s['gc_avg']} | AM:{s['am']}/{s['total']} ({round(s['am']/s['total']*100)}%) | Over2.5:{s['over25']}/{s['total']} ({round(s['over25']/s['total']*100)}%)<br>
                    <b>Stats:</b> {s['hs']:.1f}T {s['hst']:.1f}TP {s['hf']:.1f}F {s['hc']:.1f}C {s['hy']:.1f}A {s['hr']:.1f}R<br>
                    <b>Racha:</b> Mejor {s['mejor_racha']}G | Últ5: {s['ult5']}<br>
                    <b>Pos final:</b> {s['pos_final']}º | <b>Pts final:</b> {s['pts_final']}<br>
                    <b>Jornadas:</b> {s['jors_html']}
                    </div>
                    """, unsafe_allow_html=True)

                # === TARJETAS DETALLADAS EQ2 SI EXISTE ===
                if stats2:
                    lista_stats2, _, _ = stats2
                    for i, s in enumerate(lista_stats2):
                        st.markdown(f"""
                        <div style='background:#e0f2fe;padding:10px 12px;border-left:4px solid #0369a1;margin:8px 0;font-family:monospace;font-size:12px;line-height:1.6'>
                        <b style='font-size:14px'>{s['equipo'].title()} | {s['temp']}</b><br>
                        <b>{s['total']}PJ</b> → <span style='color:#0f8105;font-weight:900'>{s['n_g']}G {s['pct_g']}%</span> |
                        <span style='color:#b45309;font-weight:900'>{s['n_e']}E {s['pct_e']}%</span> |
                        <span style='color:#dc2626;font-weight:900'>{s['n_p']}P {s['pct_p']}%</span><br>
                        <b>Goles:</b> {s['gf_tot']}GF {s['gc_tot']}GC | Prom: {s['gf_avg']}-{s['gc_avg']} | AM:{s['am']}/{s['total']} ({round(s['am']/s['total']*100)}%) | Over2.5:{s['over25']}/{s['total']} ({round(s['over25']/s['total']*100)}%)<br>
                        <b>Stats:</b> {s['hs']:.1f}T {s['hst']:.1f}TP {s['hf']:.1f}F {s['hc']:.1f}C {s['hy']:.1f}A {s['hr']:.1f}R<br>
                        <b>Racha:</b> Mejor {s['mejor_racha']}G | Últ5: {s['ult5']}<br>
                        <b>Pos final:</b> {s['pos_final']}º | <b>Pts final:</b> {s['pts_final']}<br>
                        <b>Jornadas:</b> {s['jors_html']}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        ##############
