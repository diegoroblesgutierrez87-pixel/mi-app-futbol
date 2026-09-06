
import streamlit as st
st.set_page_config(page_title="Filtro Jornada", layout="wide", initial_sidebar_state="collapsed")
import re, unicodedata, os, pathlib, json, pandas as pd, numpy as np
from functools import lru_cache
from datetime import datetime
import time, streamlit.components.v1 as components

try:
    _BASE_DIR = pathlib.Path(__file__).parent.resolve()
except:
    _BASE_DIR = pathlib.Path.cwd().resolve()

def normaliza(nombre: str) -> str:
    n = unicodedata.normalize('NFKD', str(nombre)).encode('ASCII','ignore').decode('ASCII')
    n = n.upper().strip()
    n = re.sub(r'\s+', ' ', n)
    n = n.replace("REAL SOCIEDAD B", "REAL SOCIEDAD II").replace("CELTA DE VIGO B", "CELTA DE VIGO II")
    return n

@lru_cache(maxsize=2048)
def abreviar_equipo(nombre):
    n = normaliza(nombre)
    if 'ATLETICO' in n or n.startswith('ATLETI'): return 'ATM'
    if 'ATHLETIC' in n or 'BILBAO' in n: return 'ATH'
    mapa = {'REAL MADRID':'RMA','BARCELONA':'FCB','FC BARCELONA':'FCB','BETIS':'BET','SEVILLA':'SEV','VALENCIA':'VAL','VILLARREAL':'VIL','REAL SOCIEDAD':'RSO','CELTA':'CEL','OSASUNA':'OSA','GETAFE':'GET','ALAVES':'ALA','GIRONA':'GIR','LAS PALMAS':'LPA','MALLORCA':'MAL','RAYO VALLECANO':'RAY','ESPANYOL':'ESP','LEGANES':'LEG','VALLADOLID':'VLL','LEVANTE':'LEV','ELCHE':'ELC','OVIEDO':'OVI','HERACLES ALMELO':'HER','GRONINGEN':'GRO','TELSTAR':'TEL','PEC ZWOLLE':'ZWO','VOLENDAM':'VOL'}
    if n in mapa: return mapa[n]
    for pref in ['FC ','AFC ','SC ','AC ','AS ','CF ','REAL ','CLUB ']:
        if n.startswith(pref): n=n[len(pref):]
    return (n.split()[0][:3]).upper()

@st.cache_data(show_spinner=False)
def cargar_todo(_cache_buster=0):
    import pathlib
    try:
        BASE = pathlib.Path(__file__).parent.resolve()
    except:
        BASE = pathlib.Path.cwd().resolve()
    f = BASE / "Ligas-PRECALCULADO.csv"
    if not f.exists():
        f = BASE / "ligas_PRECALCULADO.csv"
    if not f.exists():
        f = BASE / "ligas_PRECALCULADO.csv"
    df = pd.read_csv(f, on_bad_lines='skip', engine='c', low_memory=False)
    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
    df = df[df['Date'].notna()]
    # merge goles
    try:
        fg = BASE / "Goles-Precalculado.csv"
        if not fg.exists():
            fg = BASE / "goles_precalculado.csv"
        if fg.exists() and fg.stat().st_size>100:
            df_g = pd.read_csv(fg, dtype=str, engine='c', on_bad_lines='skip')
            if 'fixture_id' in df_g.columns and 'fixture_id' in df.columns:
                df_g['fixture_id'] = df_g['fixture_id'].astype(str).str.split('.').str[0].str.strip()
                df['fixture_id'] = df['fixture_id'].astype(str).str.split('.').str[0].str.strip()
                cols = [c for c in ['Goles_Todo_HTML','Goles_1P_HTML','Goles_2P_HTML','Goles_Todo_TXT'] if c in df_g.columns]
                if cols:
                    df = df.merge(df_g[['fixture_id']+cols], on='fixture_id', how='left')
                    for c in cols:
                        df[c]=df[c].fillna('')
    except Exception as e:
        pass
    if 'HomeAbbr' not in df.columns:
        df['HomeAbbr']=df['HomeTeam'].astype(str).str[:3].str.upper()
    if 'AwayAbbr' not in df.columns:
        df['AwayAbbr']=df['AwayTeam'].astype(str).str[:3].str.upper()
    # stats derivados minimos
    if 'GolesTotales' not in df.columns:
        df['GolesTotales']=df['FTHG']+df['FTAG']
    return df.copy()

@st.cache_data(show_spinner=False)
def cargar_eventos(league=None, season=None):
    return {}

def buscar_goles_partido(row, eventos_dict, min_min=0, max_min=120, parte="Todo", equipo_filtro=None):
    try:
        if parte=="Todo":
            v=str(row.get('Goles_Todo_HTML','')).strip()
            if v and len(v)>3: return v
        if parte=="1T":
            v=str(row.get('Goles_1P_HTML','')).strip()
            if v and len(v)>2: return v
        if parte=="2T":
            v=str(row.get('Goles_2P_HTML','')).strip()
            if v and len(v)>2: return v
        v=str(row.get('Goles_Todo_TXT','')).strip()
        if v: return v
    except:
        pass
    return ""

@st.cache_data(show_spinner=False)
def get_equipos_cached(ligas_tuple):
    src = df[df['League'].isin(ligas_tuple)] if ligas_tuple else df
    eqs = pd.unique(src[['HomeTeam','AwayTeam']].values.ravel())
    return sorted([str(x) for x in eqs if str(x).lower()!='nan'])

def racha_comprimida_html(df_team, equipo):
    if df_team.empty: return ""
    df_team = df_team.drop_duplicates(subset=['Date','HomeTeam','AwayTeam']).sort_values('Date')
    is_home = df_team['HomeTeam'].values == equipo
    hg = df_team['FTHG'].to_numpy(dtype=int); ag = df_team['FTAG'].to_numpy(dtype=int)
    res = np.where(is_home, np.where(hg>ag,'G',np.where(hg<ag,'P','E')), np.where(ag>hg,'G',np.where(ag<hg,'P','E')))
    if len(res)==0: return ""
    import itertools
    comp=[(len(list(g)),k) for k,g in itertools.groupby(res)]
    sep="<span style='color:#bbb;font-size:11px;margin:0 3px'>|</span>"
    parts=[]
    for c,l in comp:
        col="#0f8105" if l=='G' else "#f31818" if l=='P' else "#0A2342"
        parts.append(f"<span style='color:{col};font-weight:700;font-size:11px'>{c}{l}</span>")
    return f"<span style='display:inline-flex;flex-wrap:wrap;gap:2px'>{sep.join(parts)}</span>"

def racha_ambos_marcan_html(df_team):
    if df_team.empty: return ""
    df_team = df_team.drop_duplicates(subset=['Date','HomeTeam','AwayTeam']).sort_values('Date')
    hg=df_team['FTHG'].to_numpy(dtype=int); ag=df_team['FTAG'].to_numpy(dtype=int)
    res=np.where((hg>0)&(ag>0),'si','no')
    import itertools
    comp=[f"{len(list(g))}{k}" for k,g in itertools.groupby(res)]
    sep="<span style='color:#bbb;font-size:11px;margin:0 3px'>|</span>"
    inner=[f"<span style='font-size:11px;font-weight:700;color:#000'>{x}</span>" for x in comp]
    return f"<span>{sep.join(inner)}</span>"

@st.cache_data(show_spinner=False)
def get_df_base_calculado(_df, ligas_tuple, temps_tuple):
    import pathlib
    df_fil = _df[_df['League'].isin(ligas_tuple) & _df['Season'].isin(temps_tuple)].copy()
    df_fil = df_fil.sort_values(['League','Season','Date'])
    try:
        BASE = pathlib.Path(__file__).parent.resolve()
    except:
        BASE = pathlib.Path.cwd().resolve()
    for name in ["Clasificacion-PRECALCULADO.csv","clasificacion_PRECALCULADO.csv","Clasificacion-PF.csv"]:
        p=BASE/name
        if p.exists():
            df_clas=pd.read_csv(p, on_bad_lines='skip', engine='c')
            df_clas=df_clas[df_clas['League'].isin(ligas_tuple) & df_clas['Season'].isin(temps_tuple)]
            return df_fil, df_clas
    return df_fil, pd.DataFrame()

# CARGA
try:
    _BASE_TMP = pathlib.Path(__file__).parent.resolve()
    _buster=0
    for _pp in [_BASE_TMP/"Ligas-PRECALCULADO.csv", _BASE_TMP/"Goles-Precalculado.csv"]:
        if _pp.exists(): _buster+=int(_pp.stat().st_mtime)+int(_pp.stat().st_size)
except:
    _buster=0

df=cargar_todo(_cache_buster=_buster)
df_original=df.copy()
if df.empty:
    st.error("DF vacio - sube Ligas-PRECALCULADO.csv y Goles-Precalculado.csv")
    st.stop()

st.title("Filtro Jornada - PRECALCULADO OK")
ligas_disponibles=sorted(df['League'].dropna().unique())
temps_disponibles=sorted(df['Season'].dropna().unique())
liga_sel=st.multiselect("Liga", ligas_disponibles, default=[ligas_disponibles[0]] if ligas_disponibles else [], key="filtro_liga_main")
temp_sel=st.multiselect("Temporada", temps_disponibles, default=[temps_disponibles[-1]] if temps_disponibles else [], key="filtro_temp_main")

if not liga_sel or not temp_sel:
    st.warning("Selecciona liga y temporada")
    st.stop()

df_base, df_clas_base = get_df_base_calculado(df, tuple(liga_sel), tuple(temp_sel))
st.success(f"Cargado {len(df_base)} partidos | {len(df_clas_base)} clasif")
st.dataframe(df_base.head(100), use_container_width=True)
