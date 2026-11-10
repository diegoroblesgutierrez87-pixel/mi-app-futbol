import streamlit as st
import pandas as pd
import pathlib
import re
import unicodedata
import numpy as np
import matplotlib.pyplot as plt
import io, base64

st.set_page_config(page_title="Lite Rapido + Local", layout="wide")
# --- FIX SCROLL MOVIL - ANTI-REFRESH ARRIBA SIN BLOQUEAR SCROLL ---
st.markdown("""
<style>
html, body {
    overscroll-behavior: none!important;
    overscroll-behavior-y: none!important;
    -webkit-overflow-scrolling: touch;
    touch-action: pan-y!important;
    overflow-y: auto!important;
    height: auto!important;
}
[data-testid="stAppViewContainer"] {
    overscroll-behavior: contain!important;
    overscroll-behavior-y: contain!important;
    overflow-y: auto!important;
}
[data-testid="stHeader"] {
    overscroll-behavior: none!important;
}
div[data-testid="stExpanderDetails"] {
    max-height: none!important;
    overflow: visible!important;
    -webkit-overflow-scrolling: auto!important;
    touch-action: auto!important;
    overscroll-behavior: auto!important;
}
iframe {
    touch-action: auto!important;
    overscroll-behavior: auto!important;
}
#btn-top-float {
    position: fixed!important;
    bottom: 20px!important;
    right: 20px!important;
    z-index: 999999!important;
    background: #0A2342!important;
    color: white!important;
    border: none!important;
    border-radius: 50%!important;
    width: 56px!important;
    height: 56px!important;
    font-size: 26px!important;
    font-weight: 900!important;
    cursor: pointer!important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4)!important;
    display: none;
}
#btn-top-float:hover { background: #0f8105!important; }
#top-ancla { position: absolute; top: 0; }
</style>
<div id="top-ancla"></div>
<button id="btn-top-float" onclick="window.scrollTo({top:0, behavior:'smooth'})">↑</button>
<script>
// ANTI REFRESH - SOLO SI ESTAS ARRIBA DEL TODO Y NO ESTAS DENTRO DE EXPANDER
let startY = 0;
document.addEventListener('touchstart', e => {
    startY = e.touches[0].clientY;
}, {passive: true});
document.addEventListener('touchmove', e => {
    const inside = e.target.closest('[data-testid="stExpanderDetails"], [data-testid="stExpander"], iframe');
    if (inside) return;
    const curY = e.touches[0].clientY;
    const diff = curY - startY;
    // solo bloquea si estas en top 0 y tiras hacia abajo > 20px
    if (window.scrollY <= 5 && diff > 20) {
        e.preventDefault();
    }
}, {passive: false});
window.addEventListener('scroll', function() {
    const btn = document.getElementById('btn-top-float');
    if (btn) btn.style.display = window.scrollY > 400 ? 'block' : 'none';
});
</script>
""", unsafe_allow_html=True)
########
# --- UTILS ---
MAPA_NORMALIZACION = {
    "Pusamania Borneo": "PUSAMANIA BORNEO",
    "Dewa United": "DEWA UNITED",
    "Persebaya Surabaya": "PERSEBAYA SURABAYA",
    "Persita": "PERSITA",
    "PSS Sleman": "PSS SLEMAN",
    "Bali United": "BALI UNITED",
    "Persija": "PERSIJA",
    "PSIM Yogyakarta": "PSIM YOGYAKARTA",
    "PSM Makassar": "PSM MAKASSAR",
    "Garudayaksa": "GARUDAYAKSA",
    "Persepam Madura Utd": "PERSEPAM MADURA UTD",
    "Arema FC": "AREMA FC",
    "Persijap": "PERSIJAP",
    "Bhayangkara FC": "BHAYANGKARA FC",
    "Persik Kediri": "PERSIK KEDIRI",
    "Persib Bandung": "PERSIB BANDUNG",
    "KUCHING FA": "Kuching FA",
    "JOHOR DARUL TAKZIM FC": "Johor Darul Takzim FC",
    "KELANTAN RED WARRIOR FC": "Kelantan Red Warrior FC",
    "KUALA LUMPUR FA": "Kuala Lumpur FA",
    "IMIGRESEN": "Imigresen",
    "PENANG": "Penang",
    "SELANGOR": "Selangor",
    "SABAH FA": "Sabah FA",
    "TERENGGANU": "Terengganu",
    "MELAKA": "Melaka",
    "DPMM FC BRUNEI": "DPMM FC Brunei",
    "NEGERI SEMBILAN": "Negeri Sembilan",
    "CASTELLON": "CASTELLÓN",
    "SPVGG GREUTHER FURTH": "SPVGG GREUTHER FÜRTH",
    "1. FC NURNBERG": "1. FC NÜRNBERG",
    "BAYERN MUNCHEN": "BAYERN MÜNCHEN",
    "RAAL LA LOUVIERE": "RAAL LA LOUVIÈRE",
    "VFL OSNABRUCK": "VFL OSNABRÜCK",
    "MUGLASPOR": "MUĞLASPOR",
    "Real Madrid II": "REAL MADRID II",
    "Teruel": "TERUEL",
}
_MAPA_UPPER = {k.upper(): v for k, v in MAPA_NORMALIZACION.items()}

from functools import lru_cache
@lru_cache(maxsize=20000)
def normaliza(s):
    if pd.isna(s): return ""
    raw = str(s).strip()
    if raw in MAPA_NORMALIZACION:
        return MAPA_NORMALIZACION[raw]
    up = raw.upper()
    if up in _MAPA_UPPER:
        return _MAPA_UPPER[up]
    return up

def normaliza_fuzzy(s):
    n = normaliza(s)
    n = re.sub(r'\(.*?\)', '', n)
    n = re.sub(r'^\d+\.?\s*', '', n)
    for pref in ['FC ','CF ','SC ','SV ','REAL ','CLUB ','DEPORTIVO ','CLUB ATLETICO ','AL-','AL ']:
        if n.startswith(pref):
            n = n[len(pref):].strip()
    return n.strip()

@st.cache_data(show_spinner=False, max_entries=500)
def plot_momentum_base64_cached(fixture_id, titulo, n_points):
    # usa globals para no pasar dataframes gigantes al cache
    mom_data = momentum_by_id.get(fixture_id, [])
    if not mom_data:
        # busca por teams key que es "HOME___AWAY"
        for k,v in momentum_by_teams.items():
            if fixture_id in k:
                mom_data = v
                break
    if not mom_data:
        return ""
    try:
        mins = [int(m.get('minute',0)) for m in mom_data][::2] # cada 2 min = mitad de barras = 2x rapido
        vals = [float(m.get('momentumValue',0)) for m in mom_data][::2]
        fig, ax = plt.subplots(figsize=(5,1.6), dpi=100) # mas pequeño = 3x rapido
        colors = ['#e74c3c' if v>=0 else '#3498db' for v in vals]
        ax.bar(mins, vals, color=colors, width=1.2, alpha=0.9)
        ax.axhline(0, color='black', linewidth=0.6)
        ax.set_xlim(-1, 100)
        ax.set_title(titulo, fontsize=8, fontweight='bold')
        ax.tick_params(labelsize=5)
        ax.set_xticks([])
        fig.tight_layout(pad=0.3)
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        b64 = base64.b64encode(buf.read()).decode()
        return f"<img src='data:image/png;base64,{b64}' style='width:100%;max-width:380px;margin:4px 0;border:1px solid #ddd'/>"
    except:
        return ""

def plot_momentum_base64(mom_data, goles_list, titulo=""):
    # wrapper compat para que no pete nada de lo que ya tienes
    if not mom_data:
        return ""
    try:
        fid = str(goles_list[0].get('fixture_id','')) if goles_list else titulo
        return plot_momentum_base64_cached(titulo, titulo, len(mom_data))
    except:
        return plot_momentum_base64_cached(titulo, titulo, len(mom_data))

def abreviar_equipo(nombre):
    n = normaliza(nombre)
    if not n or n == "NAN": return "XXX"
    if 'KAISERSLAUTERN' in n: return 'KAI'
    if 'DARMSTADT' in n: return 'DAR'
    if 'ATLETICO' in n: return 'ATM'
    if 'BILBAO' in n or 'ATHLETIC' in n: return 'ATH'
    if 'QADISIYAH' in n: return 'QAD'
    if 'DIRIYAH' in n: return 'DIR'
    # quita "1. ", "2. " del inicio
    n = re.sub(r'^\d+\.?\s*', '', n)
    # quita prefijos feos
    for pref in ['FC ','REAL ','CLUB ','DEPORTIVO ','CLUB ATLETICO ','SV ','CF ','SC ','AL ']:
        if n.startswith(pref):
            n = n[len(pref):].strip()
    if n.startswith('AL-'):
        n = n[3:].strip()
    parts = n.split()
    if not parts: return "XXX"
    # si quedó "FC KAISERSLAUTERN", usa la 2da palabra
    if parts[0] in ['FC','CF','SC','SV'] and len(parts) > 1:
        return parts[1][:3].upper()
    if '-' in parts[0]:
        return parts[0].split('-')[-1][:3].upper()
    return parts[0][:3].upper()

def get_base():
    # 1 - si hay parquet nuevo en el repo, usa repo
    for p in [pathlib.Path(__file__).parent.resolve(), pathlib.Path(".").resolve()]:
        if (p / "base_partidos.parquet").exists():
            return p
    # 2 - si no, busca csv
    for p in [pathlib.Path("/mnt/data"), pathlib.Path(__file__).parent.resolve(), pathlib.Path(".").resolve()]:
        if (p / "europa_actual.csv").exists():
            return p
    return pathlib.Path("/mnt/data")

BASE = get_base()

@st.cache_data(show_spinner=False)
def cargar_todo_lite():
    f_parquet = BASE / "base_partidos.parquet"
    f_pkl = BASE / "base_partidos.pkl"
    if f_parquet.exists():
        df = pd.read_parquet(f_parquet)
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
    elif f_pkl.exists():
        df = pd.read_pickle(f_pkl)
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
    else:
        files = ["europa_actual.csv","din1_suec1_26_27.csv","asia_actual_j1j2k1k2csl1.csv","arabia_actual.csv","sudamerica_actual.csv","asia_4ligas_con_israel_2026.csv"]
        dfs=[]
        for fn in files:
            fp = BASE / fn
            if fp.exists() and fp.stat().st_size > 100:
                d = pd.read_csv(fp, on_bad_lines='skip', engine='c')
                if 'Date' in d.columns:
                    d['Date'] = pd.to_datetime(d['Date'], dayfirst=True, errors='coerce')
                dfs.append(d)
        df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    # Nations League: CSV aparte - dentro del loader, antes del cache
    try:
        _pn = BASE / "uefa_nations_league_2627.csv"
        _ya_n = bool((df['League'].astype(str) == 'UEFA Nations League').any()) if 'League' in df.columns and not df.empty else False
        if _pn.exists() and not _ya_n:
            _dn = pd.read_csv(_pn, on_bad_lines='skip')
            _dn['Date'] = pd.to_datetime(_dn['Date'], dayfirst=True, errors='coerce')
            df = pd.concat([df, _dn], ignore_index=True)
    except:
        pass
    if 'Season' in df.columns:
        df['Season'] = df['Season'].astype(str)
    if 'fixture_id' in df.columns and not df.empty:
        df = df.sort_values('Date').drop_duplicates(subset=['fixture_id'], keep='last')

    # FIX DEFINITIVO - SIEMPRE RECALCULA JORNADA POR EQUIPO, AUNQUE EL PARQUET TRAIGA JORNADA VIEJA
    if not df.empty:
        df = df.sort_values(['League','Season','Date']).copy()
        df['Jornada'] = 0
        for (l,s), g in df.groupby(['League','Season'], sort=False):
            teams = pd.unique(pd.concat([g['HomeTeam'], g['AwayTeam']]).dropna())
            for team in teams:
                mask = (g['HomeTeam'] == team) | (g['AwayTeam'] == team)
                sub = g[mask].sort_values('Date')
                if sub.empty:
                    continue
                idxs = sub.index.to_numpy()
                df.loc[idxs, 'Jornada'] = range(1, len(idxs)+1)

    if 'HomeAbbr' not in df.columns and 'HomeTeam' in df.columns:
        df['HomeAbbr'] = df['HomeTeam'].apply(abreviar_equipo)
        df['AwayAbbr'] = df['AwayTeam'].apply(abreviar_equipo)
    return df

@st.cache_data(show_spinner=False)
def cargar_goles_lite():
    f_parquet = BASE / "base_goles.parquet"
    f_pkl = BASE / "base_goles.pkl"
    if f_parquet.exists():
        dg_all = pd.read_parquet(f_parquet)
    elif f_pkl.exists():
        dg_all = pd.read_pickle(f_pkl)
    else:
        files = ["goles_actual.csv","goles_arabia_actual.csv","goles_sudamerica_actual.csv","goles_asia_4ligas_con_israel_2026.csv"]
        dfs=[]
        for fn in files:
            f = BASE / fn
            if f.exists() and f.stat().st_size > 100:
                dfs.append(pd.read_csv(f, dtype=str, on_bad_lines='skip', engine='c'))
        dg_all = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    # Nations League goles: CSV aparte - dentro del loader, antes del cache
    try:
        _pg = BASE / "uefa_nations_league_2627_goles.csv"
        if _pg.exists():
            _dg_n = pd.read_csv(_pg, dtype=str, on_bad_lines='skip')
            if not dg_all.empty and 'fixture_id' in dg_all.columns:
                _ex = set(dg_all['fixture_id'].astype(str).str.split('.').str[0])
                _dg_n = _dg_n[~_dg_n['fixture_id'].astype(str).str.split('.').str[0].isin(_ex)]
            if not _dg_n.empty:
                dg_all = pd.concat([dg_all, _dg_n], ignore_index=True)
    except:
        pass
    ev = {}
    if dg_all.empty:
        return ev
        return ev
    try:
        for fid, g in dg_all.groupby('fixture_id'):
            fid_c = str(fid).split('.')[0]
            lista = []
            for _, r in g.iterrows():
                try:
                    m = int(float(str(r.get('minuto','0')).split('+')[0] or 0))
                    team = normaliza(r.get('equipo',''))
                    if not team: continue
                    gol = str(r.get('goleador','')).strip()
                    asi = str(r.get('asistente','')).strip()
                    if gol.lower() == 'nan': gol = ""
                    if asi.lower() == 'nan': asi = ""
                    abbr = abreviar_equipo(team)
                    tipo = str(r.get('tipo','Normal Goal')).strip()
                    lista.append({"m": m, "team": team, "gol": gol, "asi": asi, "abbr": abbr, "tipo": tipo})
                except: continue
            if lista:
                ev[fid_c] = sorted(lista, key=lambda x: x['m'])
    except: pass
    return ev

@st.cache_data(show_spinner=False)
def cargar_momentum_lite():
    f_parquet = BASE / "base_momentum.parquet"
    f_pkl = BASE / "base_momentum.pkl"
    dm = None
    if f_parquet.exists():
        dm = pd.read_parquet(f_parquet)
    elif f_pkl.exists():
        dm = pd.read_pickle(f_pkl)
    else:
        return {}, {}
    mom_by_id = {}
    mom_by_teams = {}
    try:
        for fid, g in dm.groupby('fixture_id'):
            fid_c = str(fid).split('.')[0]
            g_sorted = g.sort_values('minute')
            recs = g_sorted.to_dict('records')
            mom_by_id[fid_c] = recs
            if not g_sorted.empty:
                h_raw = str(g_sorted.iloc[0].get('home',''))
                a_raw = str(g_sorted.iloc[0].get('away',''))
                hn = normaliza_fuzzy(h_raw)
                an = normaliza_fuzzy(a_raw)
                if hn and an:
                    mom_by_teams[(hn, an)] = recs
                    mom_by_teams[(an, hn)] = recs
    except:
        pass
    return mom_by_id, mom_by_teams

df = cargar_todo_lite()
eventos = cargar_goles_lite()
momentum_by_id, momentum_by_teams = cargar_momentum_lite()
if df.empty:
    st.error("No CSVs encontrados en /mnt/data")
    st.stop()

# --- UI ---
if 'show_partidos' not in st.session_state:
    st.session_state.show_partidos = False
#########################

####################


######################################

####################


######################################

####################


######################################

####################


######################################

####################


######################################

####################


######################################

######################################

####################


######################################

####################


######################################

####################


######################################

####################


######################################

######################################

####################


######################################

####################


######################################

####################


######################################

####################


######################################

####################


######################################

####################


##############
@st.cache_data(show_spinner=False)
def cargar_clasificacion_main():
    import pathlib
    for p in [pathlib.Path("/mnt/data/Base-Clasificacion-Jornada.csv"), pathlib.Path(__file__).parent.resolve()/ "Base-Clasificacion-Jornada.csv"]:
        if p.exists():
            try:
                return pd.read_csv(p, on_bad_lines='skip')
            except:
                pass
    return pd.DataFrame()
df_clas_main = cargar_clasificacion_main()
clas_dict_main = {}
clas_max_j_main = {}
if not df_clas_main.empty:
    for _, rc in df_clas_main.iterrows():
        try:
            k = (normaliza(rc.get('League','')), int(rc.get('jornada_int',0)), normaliza(rc.get('Team','')))
            clas_dict_main[k] = rc
            ln = normaliza(rc.get('League',''))
            clas_max_j_main[ln] = max(clas_max_j_main.get(ln,0), int(rc.get('jornada_int',0)))
        except:
            pass
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
##############################################################################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
##############################################################################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
##############################################################################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################

filtros = st.expander("FILTROS", expanded=False)
with filtros:
    if st.button("Ocultar partidos" if st.session_state.show_partidos else "Mostrar partidos", key="toggle_partidos", use_container_width=True):
        st.session_state.show_partidos = not st.session_state.show_partidos
        st.rerun()

ligas = sorted(df['League'].dropna().unique()) if 'League' in df.columns else []
c1,c2,c3,c4d = filtros.columns(4)
with c1: liga_sel = st.selectbox("Liga", ["Todas"] + ligas)
df_f = df if liga_sel == "Todas" else df[df['League'] == liga_sel]
# FIX TEMPORADA NUEVA J1/J2 - solo J-League empieza 07/08/2026 (K League NO)
if not df_f.empty and 'Date' in df_f.columns:
    try:
        mask_new = df_f['League'].astype(str).str.contains('J1 League|J2 League', case=False, na=False)
        if mask_new.any():
            df_f = df_f[~mask_new | (df_f['Date'] >= pd.to_datetime('2026-08-07'))].copy()
    except:
        pass

# --- FILTRO FECHA POR LIGA ---
if not df_f.empty and 'Date' in df_f.columns:
    try:
        fechas_unicas = sorted(df_f['Date'].dropna().dt.date.unique(), reverse=True)
        fechas_str = ["Todas"] + [d.strftime("%d/%m/%Y") for d in fechas_unicas]
    except:
        fechas_unicas = []
        fechas_str = ["Todas"]
else:
    fechas_unicas = []
    fechas_str = ["Todas"]

with c4d:
    fecha_sel_str = st.selectbox("Desde fecha", fechas_str, key="fecha_desde")

if fecha_sel_str != "Todas" and fechas_unicas:
    try:
        fecha_sel_date = pd.to_datetime(fecha_sel_str, dayfirst=True).date()
        mask_fecha = df_f['Date'].dt.date >= fecha_sel_date
        df_f = df_f[mask_fecha]
    except:
        pass

# Equipo lista - BASE YA NORMALIZADA V5
if not df_f.empty:
    equipos = sorted(pd.concat([df_f['HomeTeam'], df_f['AwayTeam']]).dropna().astype(str).str.upper().unique().tolist())
else:
    equipos = []

with c2: eq1 = st.selectbox("Equipo 1", ["Ninguno"] + equipos, key="eq1_main")
with c3: eq1_loc = st.selectbox("Eq1 Condición", ["Todos","Local","Visitante"], key="eq1loc")

# --- NUEVO: COINCIDIR FECHAS -> AUTO EQUIPO 2 (FUTURO) ---
@st.cache_data(show_spinner=False)
def _cargar_cal_completo():
    import pathlib
    for p in [pathlib.Path("/mnt/data/calendario_completo_2026_2027.csv"), pathlib.Path("calendario_completo_2026_2027.csv"), pathlib.Path(__file__).parent / "calendario_completo_2026_2027.csv"]:
        if p.exists():
            try:
                _dfc = pd.read_csv(p, on_bad_lines='skip')
                _dfc['Date'] = pd.to_datetime(_dfc['Date'], dayfirst=True, errors='coerce')
                return _dfc
            except:
                pass
    return pd.DataFrame()

_df_cal = _cargar_cal_completo()
if not _df_cal.empty and 'Date' in _df_cal.columns:
    try:
        fechas_cal_unicas = sorted(_df_cal['Date'].dropna().dt.date.unique())
        fechas_cal_str = [d.strftime("%d/%m/%Y") for d in fechas_cal_unicas]
    except:
        fechas_cal_str = fechas_str
else:
    fechas_cal_str = fechas_str

# Coincidir fechas (futuro) quitado

c4,c5 = filtros.columns(2)
with c4:
    lista_eq2 = [e for e in equipos if e.upper() != str(eq1).upper()]
    default_idx = 0
    eq2 = st.selectbox("Equipo 2", ["Ninguno"] + lista_eq2, index=default_idx, key="eq2_main")
with c5: eq2_loc = st.selectbox("Eq2 Condición", ["Todos","Local","Visitante"], key="eq2loc")

# --- BUSCADOR POR % ---
c6,c7,c8 = filtros.columns([2,1,1])
with c6:
    filtro_tipo = st.selectbox("Filtro %", ["Ninguno","Ambos SI","Ambos NO","Over 2.5","Under 2.5","Corners Over 9.5","Corners Under 9.5","Amarillas Over 4.5","Amarillas Under 4.5","Tiros Puerta Over 8.5","Tiros Puerta Under 8.5","Tiros Totales Over 24.5","Tiros Totales Under 24.5","Faltas Over 24.5","Faltas Under 24.5","Gana","Pierde","Empata","GanaEmpata","GanaPierde","PierdeEmpata"], key="filtro_tipo")
with c7:
    filtro_pct = st.number_input("% mínimo", min_value=0, max_value=100, value=60, step=5, key="filtro_pct")
with c8:
    modo_stats = st.selectbox("Detalle stats", ["ON","OFF"], key="modo_stats")

c9,c_min1,c_min2 = filtros.columns([1,1,1])
with c9:
    modo_jugadores = st.selectbox("JUGADORES", ["ON","OFF"], key="jugadores")
with c_min1:
    min_desde_raw = st.text_input("MIN DESDE", key="min_desde", placeholder="-")
with c_min2:
    min_hasta_raw = st.text_input("MIN HASTA", key="min_hasta", placeholder="-")

def parse_min(v):
    try:
        if v is None or str(v).strip() in ["", "-", "–", "—"]:
            return None
        return int(str(v).strip().replace("'", ""))
    except:
        return None

MIN_DESDE = parse_min(min_desde_raw)
MIN_HASTA = parse_min(min_hasta_raw)

# --- FILTRO VECTORIZADO - BASE YA NORMALIZADA V5 ---
def filtrar_equipo(dframe, equipo, condicion):
    if equipo == "Ninguno" or dframe.empty:
        return dframe.iloc[0:0] if equipo!= "Ninguno" else dframe
    n_eq = str(equipo).strip().upper()
    if 'HomeNorm' not in dframe.columns:
        dframe = dframe.copy()
        dframe['HomeNorm'] = dframe['HomeTeam'].astype(str).str.upper()
        dframe['AwayNorm'] = dframe['AwayTeam'].astype(str).str.upper()
    if condicion == "Local":
        return dframe[dframe['HomeNorm']==n_eq]
    if condicion == "Visitante":
        return dframe[dframe['AwayNorm']==n_eq]
    return dframe[(dframe['HomeNorm']==n_eq) | (dframe['AwayNorm']==n_eq)]

if eq1!= "Ninguno" and eq2!= "Ninguno":
    df_eq1 = filtrar_equipo(df_f, eq1, eq1_loc)
    df_eq2 = filtrar_equipo(df_f, eq2, eq2_loc)
    modo_doble = True
elif eq1!= "Ninguno":
    df_mostrar = filtrar_equipo(df_f, eq1, eq1_loc)
    modo_doble = False
elif eq2!= "Ninguno":
    df_mostrar = filtrar_equipo(df_f, eq2, eq2_loc)
    modo_doble = False
else:
    df_mostrar = df_f
    modo_doble = False

# --- MINI RESUMEN FILTROS - para ver si filtra bien ---
try:
    _n_base = len(df_f)
    _n_out = (len(df_eq1) + len(df_eq2)) if modo_doble else len(df_mostrar)
    _min_txt = f"{min_desde_raw or '-'} -> {min_hasta_raw or '-'}"
    _filtro_txt = f"{filtro_tipo} >= {filtro_pct}%" if filtro_tipo != "Ninguno" else "Ninguno"
    st.markdown(
        f"<div style='font-family:monospace;font-size:10px;color:#000;font-weight:900;background:#f0f0f0;border:1px solid #0A2342;border-radius:6px;padding:6px 8px;margin:8px 0;white-space:pre-wrap;word-break:break-word'>"
        f"FILTROS | Liga={liga_sel} | Desde fecha={fecha_sel_str} | "
        f"Eq1={eq1} ({eq1_loc}) | Eq2={eq2} ({eq2_loc}) | "
        f"Filtro%={_filtro_txt} | Stats={modo_stats} | Jugadores={modo_jugadores} | MIN={_min_txt} | "
        f"Partidos={_n_out}/{_n_base}</div>",
        unsafe_allow_html=True,
    )
except:
    pass

def fmt_rapido(r, eq_refs_norm, current_eq_norm, current_eq_orig):
    j = int(r.get('Jornada',0) or 0)
    h = str(r.get('HomeTeam','')); a = str(r.get('AwayTeam',''))
    hab = h.strip()
    aab = a.strip()
    try: hg = int(float(r.get('FTHG',0) or 0)); ag = int(float(r.get('FTAG',0) or 0))
    except: hg = 0; ag = 0
    try: hthg = int(float(r.get('HTHG',0) or 0)); htag = int(float(r.get('HTAG',0) or 0))
    except: hthg = 0; htag = 0

    col = "#0A2342"
    if eq_refs_norm:
        hn = normaliza(h); an = normaliza(a)
        for ern in eq_refs_norm:
            if ern == hn and hg > ag: col = "#0f8105"
            if ern == an and ag > hg: col = "#0f8105"
            if ern == hn and hg < ag: col = "#f31818"
            if ern == an and ag < hg: col = "#f31818"
            if ern == hn and hg == ag: col = "#8B4513"
            if ern == an and hg == ag: col = "#8B4513"
    else:
        if hg == ag:
            col = "#8B4513"

    mins_1t = []
    mins_2t = []
    marc_h, marc_a = 0, 0
    try:
        fid = str(r.get('fixture_id','')).split('.')[0]
        home_abbr_fix = str(r.get('HomeAbbr','')).strip().upper()
        for ev in eventos.get(fid, []):
            m = ev['m']; team = ev['team']
            gol = ev.get('gol',''); asi = ev.get('asi','')
            h_norm = normaliza(r.get('HomeTeam','')); a_norm = normaliza(r.get('AwayTeam',''))
            if team == h_norm:
                abbr = r.get('HomeAbbr') or abreviar_equipo(r.get('HomeTeam',''))
            elif team == a_norm:
                abbr = r.get('AwayAbbr') or abreviar_equipo(r.get('AwayTeam',''))
            else:
                abbr = ev.get('abbr') or abreviar_equipo(team)
            if not abbr or abbr == "XXX":
                abbr = "A."
            tipo_ev = ev.get('tipo','Normal Goal')
            es_fallado = 'Missed' in tipo_ev
            es_propia = 'Own Goal' in tipo_ev

            if not es_fallado:
                if es_propia:
                    # gol en propia: cuenta para el rival
                    if team == h_norm:
                        marc_a += 1
                    else:
                        marc_h += 1
                else:
                    if team == h_norm:
                        marc_h += 1
                    else:
                        marc_a += 1
            # PARCHE REAL MADRID: si goles no cuadran con final, no muestres marcador progresivo
            total_real = hg + ag
            total_ev = len([e for e in eventos.get(fid, []) if 'Missed' not in e.get('tipo','')])
            if total_ev != total_real:
                alterador = ""
            else:
                alterador = f" {marc_h}-{marc_a}"
            if es_fallado:
                alterador = (alterador + " [PEN FALLADO]") if alterador else " [PEN FALLADO]"

            # --- NO filtrar goles aquí, el filtro de partido se hace fuera ---

            es_mio = any(ern in team or team in ern for ern in eq_refs_norm) if eq_refs_norm else False
            mj = globals().get('modo_jugadores', 'OFF')
            def abrev(n):
                s = str(n).strip()
                if not s or s.lower() == 'nan': return ""
                p = s.split()
                if len(p) == 1: return p[0]
                return f"{p[0][0]}. {p[-1]}"
            gol_raw = str(gol).strip()
            asi_raw = str(asi).strip()
            if gol_raw.lower() == 'nan': gol_raw = ""
            if asi_raw.lower() == 'nan': asi_raw = ""
            gol_ab = abrev(gol_raw).upper()
            asi_ab = abrev(asi_raw).lower()

            # si no hay goleador, no intentes pintar "" ()
            if mj == "ON" and gol_raw and gol_ab:
                txt_extra = f' "{gol_ab}" ({asi_ab})({abbr}){alterador}' if asi_ab else f' "{gol_ab}" ({abbr}){alterador}'
            else:
                txt_extra = f'({abbr}){alterador}'

            if not txt_extra.strip():
                txt_extra = f'({abbr}){alterador}'

            is_local = (team == h_norm)
            es_mio = any(ern in team or team in ern for ern in eq_refs_norm) if eq_refs_norm else False
            filtro_activo = (MIN_DESDE is not None or MIN_HASTA is not None)
            en_rango = (MIN_DESDE is None or m >= MIN_DESDE) and (MIN_HASTA is None or m <= MIN_HASTA)
            # ahora color del gol = color del resultado si es mi equipo, resto BLANCO para verse
            color_gol = col if es_mio else "#000000"
            deco = ""
            if filtro_activo and en_rango:
                bold = "font-weight:900;"
                gris = "background:#D3D3D3; border-radius:3px; padding:1px 4px;"
            else:
                bold = ""
                gris = ""
            extra_style = f"{deco} {bold}"
            if mj == "ON" and gol_ab:
                extra_jug = f' "{gol_ab}"' + (f' ({asi_ab})' if asi_ab else '')
            else:
                extra_jug = ""
            min_txt = f"<span style='font-size:12px; {bold} {gris}'>{m}'</span>"
            bolita = "⚽"
            if is_local:
                html_gol = f"<div style='text-align:left; color:{color_gol}; {extra_style} margin:0; padding:0; line-height:1.0; font-size:11px'>{min_txt} {alterador.strip()}{extra_jug} {bolita}</div>"
            else:
                html_gol = f"<div style='text-align:right; color:{color_gol}; {extra_style} margin:0; padding:0; line-height:1.0; font-size:11px'>{bolita} {min_txt} {alterador.strip()}{extra_jug}</div>"
            if m <= 45:
                mins_1t.append(html_gol)
            else:
                mins_2t.append(html_gol)
    except: pass

    if not mins_1t and not mins_2t:
        ms = re.findall(r"(\d+)'", str(r.get('Goles_Todo_HTML','') or ''))
        for x in ms:
            try:
                m_int = int(x)
                if m_int <= 45:
                    mins_1t.append(f"<span style='color:#fff'>{x}'</span>")
                else:
                    mins_2t.append(f"<span style='color:#fff'>{x}'</span>")
            except:
                mins_1t.append(f"<span style='color:#fff'>{x}'</span>")

    # separador 1T/2T linea continua gris flojita ancho completo
    sep_1t = "<div style='display:flex;align-items:center;gap:8px;margin:6px 0'><div style='flex:1;height:1px;background:#D3D3D3'></div><span style='color:#A9A9A9;font-weight:900;font-size:9px;white-space:nowrap'>1T</span><div style='flex:1;height:1px;background:#D3D3D3'></div></div>"
    sep_2t = "<div style='display:flex;align-items:center;gap:8px;margin:6px 0'><div style='flex:1;height:1px;background:#D3D3D3'></div><span style='color:#A9A9A9;font-weight:900;font-size:9px;white-space:nowrap'>2T</span><div style='flex:1;height:1px;background:#D3D3D3'></div></div>"
    if mins_1t and mins_2t:
        txt_mins = sep_1t + "".join(mins_1t) + sep_2t + "".join(mins_2t)
    elif mins_1t:
        txt_mins = sep_1t + "".join(mins_1t)
    elif mins_2t:
        txt_mins = sep_2t + "".join(mins_2t)
    else:
        txt_mins = "-"

    # --- MOMENTUM DESACTIVADO TOTAL - CERO GRAFICAS ---
    mom_html = ""

    # Si hay filtro MIN y no hay goles en ese rango, no renderizar - DESACTIVADO para no limitar
    pass

    # FIX L/V - ahora sí usa el equipo del bloque
    loc_tag = ""
    if current_eq_orig:
        if r.get('HomeTeam','') == current_eq_orig: loc_tag = " (L)"
        elif r.get('AwayTeam','') == current_eq_orig: loc_tag = " (V)"

    # extra stats - ON muestra todo diferenciado con color / OFF normal
    extra = ""
    try:
        def _iv(v):
            try:
                if v is None or pd.isna(v): return None
                return int(float(v))
            except: return None

        if 'modo_stats' in locals() or 'modo_stats' in globals():
            ms = modo_stats
        else:
            ms = "OFF"

        # --- ROJAS AUTO DESACTIVADO ---

        if ms == "ON":
            hy = _iv(r.get('HY')); ay = _iv(r.get('AY'))
            hr = _iv(r.get('HR')); ar = _iv(r.get('AR'))
            hc = _iv(r.get('HC')); ac = _iv(r.get('AC'))
            hst = _iv(r.get('HST')); ast = _iv(r.get('AST'))
            hs = _iv(r.get('HS')); _as = _iv(r.get('AS'))
            hf = _iv(r.get('HF')); af = _iv(r.get('AF'))
            hsv = _iv(r.get('HomeSaves')); asv = _iv(r.get('AwaySaves'))

            hp = _iv(r.get('HomePasses')); ap = _iv(r.get('AwayPasses'))
            hpos = _iv(r.get('HomePos')); apos = _iv(r.get('AwayPos'))

            if (hy is not None or ay is not None) and ((hy or 0) + (ay or 0) > 0):
                extra += f" <span style='color:#b8860b'>Amarillas Local {hy if hy is not None else '-'} - Visitante {ay if ay is not None else '-'}</span><br>"
            if (hr is not None or ar is not None) and ((hr or 0) + (ar or 0) > 0):
                extra += f" <span style='color:#FF0000'>Rojas Local {hr if hr is not None else '-'} - Visitante {ar if ar is not None else '-'}</span><br>"
            if (hc is not None or ac is not None) and ((hc or 0) + (ac or 0) > 0):
                extra += f" <span style='color:#1E90FF'>Corners Local {hc if hc is not None else '-'} - Visitante {ac if ac is not None else '-'}</span><br>"
            if (hst is not None or ast is not None) and ((hst or 0) + (ast or 0) > 0):
                extra += f" <span style='color:#0066cc'>Tiros Puerta Local {hst if hst is not None else '-'} - Visitante {ast if ast is not None else '-'}</span><br>"
            if (hs is not None or _as is not None) and ((hs or 0) + (_as or 0) > 0):
                extra += f" <span style='color:#004080'>Tiros Totales Local {hs if hs is not None else '-'} - Visitante {_as if _as is not None else '-'}</span><br>"
            if (hf is not None or af is not None) and ((hf or 0) + (af or 0) > 0):
                extra += f" <span style='color:#666'>Faltas Local {hf if hf is not None else '-'} - Visitante {af if af is not None else '-'}</span><br>"
            if (hsv is not None or asv is not None) and ((hsv or 0) + (asv or 0) > 0):
                extra += f" <span style='color:#008080'>Paradas Local {hsv if hsv is not None else '-'} - Visitante {asv if asv is not None else '-'}</span><br>"
            if (hp is not None or ap is not None) and ((hp or 0) + (ap or 0) > 0):
                extra += f" <span style='color:#2E8B57'>Pases Local {hp if hp is not None else '-'} - Visitante {ap if ap is not None else '-'}</span><br>"
            if (hpos is not None or apos is not None) and ((hpos or 0) + (apos or 0) > 0):
                extra += f" <span style='color:#8B4513'>Posesion Local {hpos if hpos is not None else '-'}% - Visitante {apos if apos is not None else '-'}%</span><br>"
        else:
            # OFF - comportamiento original tuyo
            if "Corners" in filtro_tipo:
                hc = r.get('HC'); ac = r.get('AC')
                if hc is not None and ac is not None and pd.notna(hc) and pd.notna(ac):
                    tot_c = int(float(hc)+float(ac))
                    extra += f" <span style='color:#555'>[{tot_c}c]</span>"
            if "Amarillas" in filtro_tipo:
                hy = r.get('HY'); ay = r.get('AY')
                if hy is not None and ay is not None and pd.notna(hy) and pd.notna(ay):
                    tot_y = int(float(hy)+float(ay))
                    extra += f" <span style='color:#b8860b'>[{tot_y}y]</span>"
            if "Tiros Puerta" in filtro_tipo:
                hst = r.get('HST'); ast = r.get('AST')
                if hst is not None and ast is not None and pd.notna(hst) and pd.notna(ast):
                    tot_sot = int(float(hst)+float(ast))
                    extra += f" <span style='color:#0066cc'>[{tot_sot}tp]</span>"
            if "Tiros Totales" in filtro_tipo:
                hs = r.get('HS'); _as = r.get('AS')
                if hs is not None and _as is not None and pd.notna(hs) and pd.notna(_as):
                    tot_s = int(float(hs)+float(_as))
                    extra += f" <span style='color:#0066cc'>[{tot_s}t]</span>"
            if "Faltas" in filtro_tipo:
                hf = r.get('HF'); af = r.get('AF')
                if hf is not None and af is not None and pd.notna(hf) and pd.notna(af):
                    tot_f = int(float(hf)+float(af))
                    extra += f" <span style='color:#888'>[{tot_f}f]</span>"
    except: pass

    # G/E/P del equipo seleccionado: 1P / FINAL
    def res_eq(gf, gc):
        if gf > gc: return "G"
        if gf == gc: return "E"
        return "P"

    es_local = current_eq_orig and r.get('HomeTeam','') == current_eq_orig
    es_visit = current_eq_orig and r.get('AwayTeam','') == current_eq_orig

    if es_local:
        r1 = res_eq(hthg, htag)
        rF = res_eq(hg, ag)
        btts_txt = f"{r1}/{rF}"
    elif es_visit:
        r1 = res_eq(htag, hthg)
        rF = res_eq(ag, hg)
        btts_txt = f"{r1}/{rF}"
    else:
        btts = hg > 0 and ag > 0
        btts_txt = "G/G" if btts else "NG/NG"

    col_j = "#0A2342"
    # --- CLASIFICACION ---
    clas_html = ""
    try:
        lg_norm = normaliza(r.get('League',''))
        j_act = int(j)
        j_max = clas_max_j_main.get(lg_norm, j_act)
        def _get_main(jn, team_norm):
            return clas_dict_main.get((lg_norm, jn, team_norm))
        rh_act = _get_main(j_max, normaliza(h))
        ra_act = _get_main(j_max, normaliza(a))
        if rh_act is not None and ra_act is not None:
            txt_actual_main = f"({int(rh_act.get('Pts',0))}pts){int(rh_act.get('Pos',0))}º vs {int(ra_act.get('Pos',0))}º({int(ra_act.get('Pts',0))}pts) actual"
            clas_html = f"<div style='text-align:center;margin:3px 0;'><span style='background:#E8E8E8;color:#000;padding:1px 6px;border-radius:3px;font-size:10px;font-weight:900;'>{txt_actual_main}</span></div>"
    except:
        clas_html = ""
    # --- TODA LA LINEA COLOREADA + SUBRAYADO EQUIPO FILTRO ---
    h_norm_chk = normaliza(h)
    a_norm_chk = normaliza(a)
    col_line = col_j
    h_html = h
    a_html = a
    if current_eq_norm:
        col_line = col
        if h_norm_chk == current_eq_norm:
            h_html = f"<span style='background:#a0a0a0;color:#000;padding:2px 8px;border-radius:3px;font-weight:900'>{h}</span>"
        elif a_norm_chk == current_eq_norm:
            a_html = f"<span style='background:#a0a0a0;color:#000;padding:2px 8px;border-radius:3px;font-weight:900'>{a}</span>"
    return f"<div style='font-family:monospace;font-size:11px;padding:6px 4px;border-bottom:2px solid #ccc;line-height:1.2;max-width:380px;margin:0 auto;background:#ffffff;color:#000'><div style='text-align:left;color:{col_line};font-weight:900'><span style='background:{col};color:#fff;padding:1px 5px;border-radius:3px;font-weight:900;margin-right:4px'>{btts_txt}</span> |Jornada {j}| {h_html} vs {a_html}</div>{clas_html}<div style='text-align:center;font-weight:900;word-break:break-word'>{extra}</div><div style='text-align:center;font-weight:900;margin-top:4px'><span style='background:#E8E8E8;color:#000;padding:2px 10px;border-radius:3px;border:1px solid #0A2342'>Final {hg}-{ag}</span></div><div style='text-align:center;color:#666;font-weight:700;font-size:10px;margin-top:2px'>[1ª parte {hthg}-{htag}]</div><div style='color:#000;white-space:normal;word-break:break-word;line-height:1.1;margin-top:3px'>{txt_mins}</div>{mom_html}</div>"

eq_refs_orig = [e for e in [eq1, eq2] if e!= "Ninguno"]
eq_refs_norm = [normaliza(e) for e in eq_refs_orig]

html = ""

# mensaje ocultos borrado

# MODO FILTRO POR % - PRIORITARIO
if st.session_state.show_partidos and filtro_tipo!= "Ninguno":
    def get_val(r, keys):
        for k in keys:
            if k in r and pd.notna(r.get(k)):
                try: return float(r.get(k))
                except: pass
        return None
    def cumple(r, team_norm=None):
        try: hg = int(float(r.get('FTHG',0) or 0)); ag = int(float(r.get('FTAG',0) or 0))
        except: hg=0; ag=0
        hc = get_val(r, ['HC']) or 0; ac = get_val(r, ['AC']) or 0
        tot_c = get_val(r, ['Corners','TotalCorners'])
        if tot_c is None: tot_c = hc + ac
        hy = get_val(r, ['HY']) or 0; ay = get_val(r, ['AY']) or 0
        tot_y = get_val(r, ['YellowCards'])
        if tot_y is None: tot_y = hy + ay
        hst = get_val(r, ['HST']) or 0; ast = get_val(r, ['AST']) or 0
        tot_sot = get_val(r, ['SOT'])
        if tot_sot is None: tot_sot = hst + ast
        hs = get_val(r, ['HS']) or 0; _as = get_val(r, ['AS']) or 0
        tot_s = get_val(r, ['Shots'])
        if tot_s is None: tot_s = hs + _as
        hf = get_val(r, ['HF']) or 0; af = get_val(r, ['AF']) or 0
        tot_f = get_val(r, ['Fouls'])
        if tot_f is None: tot_f = hf + af
        if filtro_tipo == "Ambos SI": return hg>0 and ag>0
        if filtro_tipo == "Ambos NO": return not (hg>0 and ag>0)
        if filtro_tipo == "Over 2.5": return (hg+ag) > 2.5
        if filtro_tipo == "Under 2.5": return (hg+ag) < 2.5
        if filtro_tipo == "Corners Over 9.5": return tot_c > 9.5
        if filtro_tipo == "Corners Under 9.5": return tot_c < 9.5 and tot_c>0
        if filtro_tipo == "Amarillas Over 4.5": return tot_y > 4.5
        if filtro_tipo == "Amarillas Under 4.5": return tot_y <= 4.5
        if filtro_tipo == "Tiros Puerta Over 8.5": return tot_sot > 8.5
        if filtro_tipo == "Tiros Puerta Under 8.5": return tot_sot < 8.5 and tot_sot>0
        if filtro_tipo == "Tiros Totales Over 24.5": return tot_s > 24.5
        if filtro_tipo == "Tiros Totales Under 24.5": return tot_s < 24.5 and tot_s>0
        if filtro_tipo == "Faltas Over 24.5": return tot_f > 24.5
        if filtro_tipo == "Faltas Under 24.5": return tot_f < 24.5 and tot_f>0
        # --- NUEVOS: resultado relativo al equipo ---
        if team_norm is not None:
            hn = normaliza(r.get('HomeTeam','')); an = normaliza(r.get('AwayTeam',''))
            if team_norm == hn: gf, gc = hg, ag
            elif team_norm == an: gf, gc = ag, hg
            else: return False
            if filtro_tipo == "Gana": return gf > gc
            if filtro_tipo == "Pierde": return gf < gc
            if filtro_tipo == "Empata": return gf == gc
            if filtro_tipo == "GanaEmpata": return gf >= gc
            if filtro_tipo == "GanaPierde": return gf != gc
            if filtro_tipo == "PierdeEmpata": return gf <= gc
        return False

    columnas = set(df_f.columns)
    hay_datos = True
    if "Corners" in filtro_tipo and not ({"HC","AC","Corners"}.intersection(columnas)):
        st.warning(f"⚠️ {liga_sel} no tiene corners"); hay_datos=False
    if "Amarillas" in filtro_tipo and not ({"HY","AY"}.intersection(columnas)):
        st.warning(f"⚠️ {liga_sel} no tiene amarillas"); hay_datos=False

    if hay_datos:
        equipos_con_loc = []
        if eq1!= "Ninguno":
            equipos_con_loc.append((eq1, eq1_loc))
        if eq2!= "Ninguno":
            equipos_con_loc.append((eq2, eq2_loc))

        if equipos_con_loc:
            equipos_a_chequear = equipos_con_loc
        else:
            base_eq = equipos if liga_sel!="Todas" else sorted(pd.unique(pd.concat([df['HomeTeam'], df['AwayTeam']]).dropna()).tolist())
            equipos_a_chequear = [(t, "Todos") for t in base_eq]

        calificados = []
        for team, loc_cond in equipos_a_chequear:
            d_team = filtrar_equipo(df_f, team, loc_cond)
            if len(d_team) < 1:
                continue
            # para filtros de stats, excluye partidos sin dato para no penalizar %
            if "Corners" in filtro_tipo:
                d_team_valid = d_team[(pd.to_numeric(d_team['HC'], errors='coerce').fillna(0) + pd.to_numeric(d_team['AC'], errors='coerce').fillna(0)) > 0]
            elif "Amarillas" in filtro_tipo:
                d_team_valid = d_team[(pd.to_numeric(d_team['HY'], errors='coerce').fillna(0) + pd.to_numeric(d_team['AY'], errors='coerce').fillna(0)) > 0]
            elif "Tiros Puerta" in filtro_tipo:
                d_team_valid = d_team[(pd.to_numeric(d_team['HST'], errors='coerce').fillna(0) + pd.to_numeric(d_team['AST'], errors='coerce').fillna(0)) > 0]
            elif "Tiros Totales" in filtro_tipo:
                d_team_valid = d_team[(pd.to_numeric(d_team['HS'], errors='coerce').fillna(0) + pd.to_numeric(d_team['AS'], errors='coerce').fillna(0)) > 0]
            elif "Faltas" in filtro_tipo:
                d_team_valid = d_team[(pd.to_numeric(d_team['HF'], errors='coerce').fillna(0) + pd.to_numeric(d_team['AF'], errors='coerce').fillna(0)) > 0]
            else:
                d_team_valid = d_team
            if len(d_team_valid) < 1:
                continue
            c_ok = 0
            jornadas_ok = []
            t_norm = normaliza(team)
            for _, rr in d_team_valid.iterrows():
                if cumple(rr.to_dict(), t_norm):
                    c_ok+=1
                    try: jornadas_ok.append(int(float(rr.get('Jornada',0))))
                    except: pass
            pct = (c_ok / len(d_team_valid) * 100) if len(d_team_valid)>0 else 0
            if pct >= filtro_pct:
                calificados.append((team, loc_cond, pct, len(d_team_valid), c_ok, sorted(set(jornadas_ok))))

        calificados = sorted(calificados, key=lambda x: x[2], reverse=True)

    if not calificados:
        st.info(f"Ningún equipo cumple {filtro_tipo} >= {filtro_pct}%")
    else:
        # --- HEADER RESUMEN POR LIGA ---
        from collections import defaultdict
        resumen = defaultdict(list)
        for team, loc_cond, pct, total, ok, jors_list in calificados:
            try:
                liga_r = df_f[(df_f['HomeTeam']==team)|(df_f['AwayTeam']==team)]['League'].mode().iloc[0]
            except:
                liga_r = liga_sel
            resumen[liga_r].append((team, pct, ok, total, jors_list))
        header_html = "<div style='font-family:monospace;background:#fff;color:#000;padding:8px;border-radius:6px;margin:6px 0;font-size:11px;border:1px solid #000'>"
        for liga_name in sorted(resumen.keys()):
            header_html += f"<div style='font-weight:900;margin-top:6px;color:#000;text-decoration:underline'>{liga_name}:</div>"
            for team_r, pct_r, ok_r, tot_r, jors_r in sorted(resumen[liga_name], key=lambda x: x[1], reverse=True):
                def _j_btts(jj):
                    try:
                        _d = df_f[pd.to_numeric(df_f['Jornada'], errors='coerce') == jj]
                        _d = _d[(_d['HomeTeam'].astype(str).str.upper() == str(team_r).upper()) | (_d['AwayTeam'].astype(str).str.upper() == str(team_r).upper())]
                        for _, _rr in _d.iterrows():
                            if int(float(_rr.get('FTHG', 0) or 0)) > 0 and int(float(_rr.get('FTAG', 0) or 0)) > 0:
                                return f"J{jj}*"
                    except:
                        pass
                    return f"J{jj}"
                j_str = ", ".join([_j_btts(j) for j in jors_r]) if jors_r else ""
                header_html += f"<div style='margin-left:10px;color:#000'>{team_r} {ok_r}/{tot_r} -> {j_str} {pct_r:.0f}%</div>"
        header_html += "</div>"
        html_partidos = ""
        for team, loc_cond, pct, total, ok, jors in calificados:
            d_team_full = filtrar_equipo(df_f, team, loc_cond)
            d_team_cumple = d_team_full[d_team_full.apply(lambda rr: cumple(rr.to_dict(), normaliza(team)), axis=1)]
            d_team_cumple = d_team_cumple.sort_values(['Jornada','Date'], ascending=[False, False]).head(20)
            try:
                liga_team = df_f[(df_f['HomeTeam']==team)|(df_f['AwayTeam']==team)]['League'].mode().iloc[0]
            except:
                liga_team = liga_sel
            color_pct = "#0f8105" if pct>=70 else "#0A2342"
            # FONDO BEIGE PARA FILTRO
            html_partidos += f"<div style='font-family:monospace;font-weight:900;background:{color_pct};color:#fff;padding:4px 6px;margin:8px 0 2px 0'>{team} {loc_cond} - {liga_team} | {filtro_tipo} {pct:.0f}% ({ok}/{total})</div>"
            for _, r in d_team_cumple.iterrows():
                # fmt_rapido normal devuelve fondo #111, lo convertimos a beige
                _html_tmp = fmt_rapido(r.to_dict(), [normaliza(team)], normaliza(team), team)
                _html_tmp = _html_tmp.replace("background:#111", "background:#F5E6C8").replace("background:#111111", "background:#F5E6C8").replace("color:#fff", "color:#000").replace("color:#bbb", "color:#444")
                # mantiene el color del equipo filtrado pero fondo beige
                _html_tmp = _html_tmp.replace("border-bottom:2px solid #333", "border-bottom:2px solid #D2C4A3")
                html_partidos += _html_tmp.replace("<div style='font-family:monospace;font-size:11px;padding:6px 4px;border-bottom:2px solid #333;line-height:1.2;max-width:380px;margin:0 auto;background:#111;color:#fff'", "<div style='font-family:monospace;font-size:11px;padding:6px 4px;border-bottom:2px solid #D2C4A3;line-height:1.2;max-width:380px;margin:0 auto;background:#F5E6C8;color:#000'")
        html = header_html + html_partidos
        # --- FIX COPIAR FILTRO - SOLO PARTIDOS ---
        if html_partidos:
            import streamlit.components.v1 as components
            bloque_copy_filtro = f"""
            <div>
                <button onclick="copyFiltro()" id="btnCopyFiltro" style="position:sticky;top:0;z-index:99999;width:100%;background:#0f8105;color:white;border:none;border-radius:6px;padding:12px;font-weight:900;cursor:pointer;margin-bottom:8px;">📋 COPIAR PARTIDOS ({len(calificados)} equipos)</button>
                {header_html}
                <div id="targetFiltro">{html_partidos}</div>
            </div>
            <script>
            function copyFiltro(){{
                var txt = document.getElementById('targetFiltro').innerText;
                navigator.clipboard.writeText(txt).then(()=>{{
                    var b = document.getElementById('btnCopyFiltro');
                    b.innerText = '✓ COPIADO';
                    b.style.background = '#0A2342';
                    setTimeout(()=>{{ b.innerText=' COPIAR FILTRO ({len(calificados)} equipos)'; b.style.background='#0f8105'; }},1200);
                }});
            }}
            </script>
            """
            components.html(bloque_copy_filtro, height=900, scrolling=True)

elif st.session_state.show_partidos:
    # MODO NORMAL (tu logica original intacta)
    if modo_doble:
        for eq_orig, df_eq in [(eq1, df_eq1), (eq2, df_eq2)]:
            cond = eq1_loc if eq_orig == eq1 else eq2_loc
            # FIX MIN en modo doble
            try:
                if MIN_DESDE is not None or MIN_HASTA is not None:
                    fids_v = set()
                    for fid_c, evs_c in eventos.items():
                        for ev_c in evs_c:
                            mm_c = ev_c.get('m', -1)
                            if MIN_DESDE is not None and mm_c < MIN_DESDE: continue
                            if MIN_HASTA is not None and mm_c > MIN_HASTA: continue
                            fids_v.add(str(fid_c))
                            break
                    df_eq = df_eq[df_eq['fixture_id'].astype(str).str.split('.').str[0].isin(fids_v)]
            except:
                pass
            # FIX J10 ARRIBA = respeta Jornada base
            if not df_eq.empty:
                df_eq = df_eq.sort_values('Jornada', ascending=False)
            df_eq = df_eq.head(30) if not df_eq.empty else df_eq
            html += f"<div style='font-family:monospace;font-weight:900;background:#0A2342;color:#fff;padding:4px 6px;margin:8px 0 2px 0;text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:4px'>{eq_orig} {cond} | {len(df_eq)}</div>"
            eq_norm_single = normaliza(eq_orig)
            for _, r in df_eq.iterrows():
                html += fmt_rapido(r.to_dict(), [eq_norm_single], eq_norm_single, eq_orig)
    else:
        # Pre-filtro por MIN para que el contador sea real
        df_filtrada_min = df_mostrar.copy()
        try:
            if MIN_DESDE is not None or MIN_HASTA is not None:
                fids_validos = set()
                for fid_check, evs_check in eventos.items():
                    for ev_c in evs_check:
                        if 'Missed' in ev_c.get('tipo',''): continue
                        mm_c = ev_c.get('m', -1)
                        if MIN_DESDE is not None and mm_c < MIN_DESDE: continue
                        if MIN_HASTA is not None and mm_c > MIN_HASTA: continue
                        fids_validos.add(str(fid_check))
                        break
                df_filtrada_min = df_mostrar[df_mostrar['fixture_id'].astype(str).str.split('.').str[0].isin(fids_validos)]
        except:
            pass

        # FIX J10 CADIZ ARRIBA - respeta Jornada base, no recalcula
        if not df_filtrada_min.empty:
            df_mostrar = df_filtrada_min.sort_values('Jornada', ascending=False)
        else:
            df_mostrar = df_filtrada_min
        if eq_refs_orig:
            cond_txt = eq1_loc if eq1!= "Ninguno" else eq2_loc
            html += f"<div style='font-family:monospace;font-weight:900;background:#0A2342;color:#fff;padding:4px 6px;margin:6px 0 2px 0;text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:4px'>{eq_refs_orig[0]} {cond_txt} | {len(df_mostrar)}</div>"
        for _, r in df_mostrar.iterrows():
            # --- FILTRO POR MINUTO A NIVEL PARTIDO ---
            try:
                if MIN_DESDE is not None or MIN_HASTA is not None:
                    fid_f = str(r.get('fixture_id','')).split('.')[0]
                    evs = eventos.get(fid_f, [])
                    tiene = False
                    for ev in evs:
                        mm = ev.get('m', -1)
                        if MIN_DESDE is not None and mm < MIN_DESDE: continue
                        if MIN_HASTA is not None and mm > MIN_HASTA: continue
                        tiene = True
                        break
                    if not tiene:
                        continue
            except:
                pass

            curr_norm = eq_refs_norm[0] if eq_refs_norm else ""
            curr_orig = eq_refs_orig[0] if eq_refs_orig else ""
            html += fmt_rapido(r.to_dict(), eq_refs_norm, curr_norm, curr_orig)

    if (modo_doble and (not df_eq1.empty or not df_eq2.empty)) or (not modo_doble and not df_mostrar.empty):
        import streamlit.components.v1 as components
        import html as _html
        safe_html = _html.escape(html)
        # FIX HUECO GIGANTE BLANCO - FILTROS
        h_dinamica = min(5000, max(600, len(html)//10))
        total_partidos_btn = (len(df_eq1) + len(df_eq2)) if modo_doble else len(df_mostrar)
        bloque_copy = f"""
        <div>
            <button onclick="copyPartidos()" id="btnCopyPartidos" style="position:sticky;top:0;z-index:99999;width:100%;background:#0A2342;color:white;border:none;border-radius:6px;padding:12px;font-weight:900;cursor:pointer;margin-bottom:8px;">📋 COPIAR PARTIDOS ({total_partidos_btn} partidos)</button>
            <div id="targetPartidos">{html}</div>
        </div>
        <script>
        function copyPartidos(){{
            var txt = document.getElementById('targetPartidos').innerText;
            navigator.clipboard.writeText(txt).then(()=>{{
                var b = document.getElementById('btnCopyPartidos');
                b.innerText = '✓ COPIADO';
                b.style.background = '#0f8105';
                setTimeout(()=>{{ b.innerText='📋 COPIAR PARTIDOS ({total_partidos_btn} partidos)'; b.style.background='#0A2342'; }},1500);
            }});
        }}
        </script>
        """
        components.html(bloque_copy, height=h_dinamica, scrolling=True)
    else:
        st.info("Selecciona equipo")

# caption base borrado

if st.button("Ocultar partidos 2" if st.session_state.show_partidos else "Mostrar partidos 2", key="toggle_partidos_2", use_container_width=True):
    st.session_state.show_partidos = not st.session_state.show_partidos
    st.rerun()
    #######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
##############################################################################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
##########################################
##########################################
######################################
###############
############################
####################################################################
##########################################
######################################
###############
############################
####################################################################
##########################################
######################################
###############
############################
####################################################################
##########################################
######################################
###############
############################
####################################################################
##########################################
######################################
###############
############################
####################################################################
##########################################
######################################
###############
############################
####################################################################
##########################################
######################################
###############
############################
##########################
##############################
#############################
########################
##########################################
with st.expander("MOMENTUM LIVE - PEGAR URL Y COPIAR", expanded=False):
    import requests, re, json, html
    import streamlit.components.v1 as components

    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36"

    def get_momentum_from_url(url):
        url = url.strip()
        eid = None
        m_mid = re.search(r'[?&]mid=([A-Za-z0-9]{6,12})', url, re.I)
        if m_mid:
            eid = m_mid.group(1)
        else:
            m = re.search(r'/partido/futbol/[^/]+/([A-Za-z0-9]{8,12})/', url)
            if m:
                eid = m.group(1)
        if not eid:
            return None, "No encuentro ?mid= en la URL. Pega la URL completa: ...?mid=ML4DjdZa"
        # FIX REAL HOME/AWAY - no fiarse de la URL
        home = "Local"
        away = "Visitante"
        try:
            r_html = requests.get(url, headers={"User-Agent": UA, "Referer":"https://www.flashscore.es/"}, timeout=8)
            htxt = r_html.text
            mh = re.search(r'duelParticipant__home[^>]*>.*?duelParticipant__name[^>]*>([^<]+)</', htxt, re.S)
            ma = re.search(r'duelParticipant__away[^>]*>.*?duelParticipant__name[^>]*>([^<]+)</', htxt, re.S)
            if mh and ma:
                home = re.sub(r'<.*?>','', mh.group(1)).strip().title()
                away = re.sub(r'<.*?>','', ma.group(1)).strip().title()
            else:
                mt2 = re.search(r'<meta property="og:title" content="([^"]+?)\s*-\s*([^"]+?)\s*\|', htxt)
                if mt2:
                    home = mt2.group(1).strip().title()
                    away = mt2.group(2).strip().title()
        except:
            pass
        if home == "Local":
            mt = re.search(r'/partido/futbol/([^/]+)/([^/]+)/', url)
            if mt:
                def clean(s):
                    s = re.sub(r'-[A-Za-z0-9]{6,8}$','',s)
                    return s.replace('-',' ').title().strip()
                away = clean(mt.group(1))
                home = clean(mt.group(2))
        try:
            import time as _tt
            api = f"https://13.ds.lsapp.eu/pq_graphql?_hash=mmts&eventId={eid}&providerId=7&_t={int(_tt.time())}"
            r = requests.get(api, headers={"User-Agent": UA, "Referer":"https://www.flashscore.es/", "Cache-Control":"no-cache", "Pragma":"no-cache"}, timeout=12)
            if r.status_code!=200:
                return None, f"Error {r.status_code} - Flashscore bloquea Streamlit Cloud. Ejecuta la app en local y si funcionara"
            data = r.json()
            root = data.get("data",{}).get("findMatchMomentumStatsByMatchId",{})
            entries = root.get("momentum",{}).get("entries",[])
            if not entries:
                return None, "Sin momentum aun - partido no empezado"
            vals = [round(float(e.get("momentumValue",0)),3) for e in entries]
            # FIX REAL HOME: el local de verdad es el primer slug de la URL
            def clean_slug(s):
                s = re.sub(r'-[A-Za-z0-9]{6,}$','',s).replace('-',' ').title().strip()
                return s
            m_url = re.search(r'/partido/futbol/([^/]+)/([^/]+)/', url)
            if m_url:
                real_home_url = clean_slug(m_url.group(1))
                real_away_url = clean_slug(m_url.group(2))
            else:
                real_home_url, real_away_url = home, away

            # si la API dice que el home es España pero en la URL el primero es Croacia, invierte todo
            api_home = (root.get("homeParticipant",{}).get("name") or home or "").lower()
            if real_home_url.lower() not in api_home and real_away_url.lower() in api_home:
                # esta al reves -> invierte momentum
                vals = [-v for v in vals]
                home, away = real_home_url, real_away_url
            else:
                home, away = real_home_url, real_away_url

            return {"eid":eid, "vals":vals, "home":home.title(), "away":away.title()}, None
        except Exception as e:
            return None, str(e)

    if st.button("🧹 LIMPIAR MOMENTUMS", key="v6_clear"):
        for i in range(15):
            if f"v6_url_{i}" in st.session_state:
                del st.session_state[f"v6_url_{i}"]
        st.rerun()
    st.caption("URL con ?mid= - 15 huecos para directo")
    urls = []
    for i in range(15):
        u = st.text_input(f"P{i+1}", value="https://www.flashscore.es/partido/futbol/cd-tenerife-IHv6nz80/cordoba-cf-CWuejruc/?mid=ML4DjdZa" if i==0 else "", key=f"v6_url_{i}", placeholder=f"Partido {i+1} ?mid=")
        urls.append(u)

    auto = st.checkbox("🔄 Auto-actualizar cada 60s", value=False, key="v6_auto")
    btn = st.button("⚡ GENERAR 15 MOMENTUMS", key="v6_btn", use_container_width=True)

    if btn or auto:
        todo = []
        for idx, url in enumerate(urls):
            if not url.strip():
                continue
            with st.spinner(f"P{idx+1}..."):
                res, err = get_momentum_from_url(url)
                if err:
                    st.error(f"P{idx+1} {err}")
                else:
                    vals = res["vals"]
                    eid = res["eid"]
                    reducido = {"id":eid,"home":res.get("home","local"),"away":res.get("away","visit"),"momentum":vals,"count":len(vals)}
                    todo.append(reducido)
                    j_str = json.dumps(reducido, separators=(',',':'))
                    j_esc = html.escape(j_str)
                    st.success(f"P{idx+1} OK {eid} {len(vals)} mins")
                    copy_html = f"""
                    <div style="font-family:monospace">
                        <textarea id="json_{idx}" style="width:100%;height:60px;font-size:10px;font-family:monospace;border:1px solid #ccc;border-radius:6px;padding:4px">{j_esc}</textarea>
                        <button onclick="navigator.clipboard.writeText(document.getElementById('json_{idx}').value).then(()=>{{document.getElementById('msg_{idx}').innerText='✅ P{idx+1} COPIADO'}})" 
                        style="width:100%;background:#0A2342;color:white;border:none;border-radius:6px;padding:8px;font-weight:900;cursor:pointer;margin-top:4px">📋 COPIAR P{idx+1}</button>
                        <div id="msg_{idx}" style="font-weight:900;color:#0f8105;text-align:center;font-size:11px"></div>
                    </div>
                    """
                    components.html(copy_html, height=110)
        if todo:
            mega = html.escape(json.dumps(todo, separators=(',',':')))
            mega_html = f"""
            <textarea id="mega" style="width:100%;height:90px;font-size:10px;font-family:monospace;border:2px solid #0A2342;border-radius:6px;padding:6px">{mega}</textarea>
            <button onclick="navigator.clipboard.writeText(document.getElementById('mega').value).then(()=>{{document.getElementById('mega_msg').innerText='✅ MEGA 15 COPIADO'}})" 
            style="width:100%;background:#0f8105;color:white;border:none;border-radius:6px;padding:10px;font-weight:900;cursor:pointer;margin-top:6px">📋 COPIAR LOS {len(todo)} JUNTOS PARA IA</button>
            <div id="mega_msg" style="font-weight:900;color:#0f8105;text-align:center"></div>
            """
            components.html(mega_html, height=160)
################

###################################################################
################################################################### CLONADO FIX3 - DOBLE
# 
###################################################################
################################################################### CLONADO FIX3 - DOBLE
# 
###################################################################
################################################################### CLONADO FIX3 - DOBLE
# 
###################################################################
################################################################### CLONADO FIX3 - DOBLE
# 
###################################################################
################################################################### CLONADO FIX3 - DOBLE
# 
################################################################################################################################## CLONADO FIX3 - DOBLE
# 
###################################################################
################################################################### CLONADO FIX3 - DOBLE
# 
###################################################################
################################################################### CLONADO FIX3 - DOBLE
# 
###################################################################
################################################################### CLONADO FIX3 - DOBLE
# 
###################################################################
################################################################### CLONADO FIX3 - DOBLE
# 
################################################################################################################################## CLONADO FIX3 - DOBLE
# 
###################################################################
################################################################### CLONADO FIX3 - DOBLE
# 
###################################################################
################################################################### CLONADO FIX3 - DOBLE
# 
###################################################################
################################################################### CLONADO FIX3 - DOBLE
# 
###################################################################
################################################################### CLONADO FIX3 - DOBLE
# 
################################################################################################################################## CLONADO FIX3 - DOBLE
# 
###################################################################
################################################################### CLONADO FIX3 - DOBLE
# 
###################################################################
################################################################### CLONADO FIX3 - DOBLE
# 
###################################################################
################################################################### CLONADO FIX3 - DOBLE
# 
###################################################################
################################################################### CLONADO FIX3 - DOBLE
# 
################################################################################################################################## CLONADO FIX3 - DOBLE
# 
###################################################################
################################################################### CLONADO FIX3 - DOBLE
# 
###################################################################
################################################################### CLONADO FIX3 - DOBLE
# 
###################################################################
################################################################### CLONADO FIX3 - DOBLE
# 
###################################################################
################################################################### CLONADO FIX3 - DOBLE
# 
###################################################################
## ================= BLOQUE PATRONES V1 - 0-0 HASTA 80' GOL 80-90' =================
# TAG: [PATRONES-0-0-80-90-V1]
with st.expander("BLOQUE PATRONES - 0-0 HASTA 80' + GOL 80-90'", expanded=False):
    import pathlib
    def cargar_patrones_0_0_80_90(tipo):
        mapa = {"0-0 FINALES":"0-0_FINAL","HT 0-0 + OVER":"HT0-0_FT_OVER","0-0 HASTA 80+ GOL 80-90":"0-0_HASTA80_GOL80-90","1 GOL HT + OVER 1.5 FT":"1GOL_HT_OVER15","1.5 HT + OVER 2.5 FT":"15HT_OVER25FT","0-0 HT + 1 GOL FT":"HT00_FT1","GOL 80' HASTA FINAL":"GOL80_FINAL"}
        patron_buscado = mapa.get(tipo, "0-0_HASTA80_GOL80-90")
        for p in [pathlib.Path(__file__).parent.resolve() / "patrones_0_0_COMBINADO.parquet", pathlib.Path("patrones_0_0_COMBINADO.parquet"), pathlib.Path(__file__).parent.resolve() / "patrones_0_0_COMBINADO.csv", pathlib.Path("patrones_0_0_COMBINADO.csv"), pathlib.Path(f"/mnt/data/patrones_0_0_COMBINADO.parquet"), pathlib.Path(f"/mnt/data/patrones_0_0_COMBINADO.csv"), pathlib.Path(f"/mnt/data/patrones_0_0_COMBINADO.pkl")]:
            if p.exists():
                try:
                    if p.suffix == ".parquet":
                        df_all = pd.read_parquet(p)
                    elif p.suffix == ".pkl":
                        df_all = pd.read_pickle(p)
                    else:
                        df_all = pd.read_csv(p, on_bad_lines='skip')
                    df_all['Date'] = pd.to_datetime(df_all['Date'], errors='coerce')
                    mask_tn = df_all['Home'].astype(str).str.contains('ES SAHEL|ES METLAOUI|ES ZARZIS|ES HAMMAM|CA BIZERTIN|AS MARSA|CLUB AFRICAIN|PROGRES SAKIET|CS HAMMAM|US BEN GUERDANE|OLYMPIQUE BEJA|US MONASTIRIENNE|STADE TUNISIEN|CS SFAXIEN|JEUNESSE SPORTIVE OMRANE|ES TUNIS', na=False) | df_all['Away'].astype(str).str.contains('ES SAHEL|ES METLAOUI|ES ZARZIS|ES HAMMAM|CA BIZERTIN|AS MARSA|CLUB AFRICAIN|PROGRES SAKIET|CS HAMMAM|US BEN GUERDANE|OLYMPIQUE BEJA|US MONASTIRIENNE|STADE TUNISIEN|CS SFAXIEN|JEUNESSE SPORTIVE OMRANE|ES TUNIS', na=False)
                    df_all.loc[mask_tn, 'League'] = 'LIGA 1 TUNEZ'
                    # === MERGE CLASIFICACION REAL - DICCIONARIO (no falla) ===
                    try:
                        import pathlib as _pl
                        p_clas = _pl.Path(__file__).parent.resolve() / "Base-Clasificacion-Jornada.csv"
                        if not p_clas.exists():
                            p_clas = _pl.Path("Base-Clasificacion-Jornada.csv")
                        if p_clas.exists():
                            df_clas = pd.read_csv(p_clas, encoding='utf-8-sig')
                            # diccionario (LIGA, JORNADA, EQUIPO) -> Pos
                            dic_pos = {}
                            for _, cc in df_clas.iterrows():
                                k = (str(cc['League']).upper().strip(), str(cc['jornada_num']).upper().strip(), str(cc['Team']).upper().strip())
                                dic_pos[k] = cc['Pos']
                            def get_pos(liga, jornada, equipo):
                                return dic_pos.get((str(liga).upper().strip(), str(jornada).upper().strip(), str(equipo).upper().strip()), "")
                            df_all['Pos_Home'] = df_all.apply(lambda x: get_pos(x['League'], x['Jornada_Liga'], x['Home']), axis=1)
                            df_all['Pos_Away'] = df_all.apply(lambda x: get_pos(x['League'], x['Jornada_Liga'], x['Away']), axis=1)
                    except Exception as e:
                        pass
                    if patron_buscado == "GOL80_FINAL":
                        if 'PATRON' in df_all.columns and (df_all['PATRON'] == "GOL80_FINAL").any():
                            df = df_all[df_all['PATRON'] == "GOL80_FINAL"].copy()
                        else:
                            df = df_all.copy()
                    elif 'PATRON' in df_all.columns:
                        df = df_all[df_all['PATRON'] == patron_buscado].copy()
                    else:
                        df = df_all.copy()
                    if 'fid' in df.columns:
                        df = df.drop_duplicates(subset=['fid'])
                    return df
                except:
                    pass
        return pd.DataFrame()

    tipo_pat = st.selectbox("TIPO PATRON", ["0-0 HASTA 80+ GOL 80-90", "0-0 FINALES", "HT 0-0 + OVER", "1 GOL HT + OVER 1.5 FT", "1.5 HT + OVER 2.5 FT", "0-0 HT + 1 GOL FT", "GOL 80' HASTA FINAL"], key="tipo_pat_0_0")
    mostrar_00 = st.selectbox("MOSTRAR 0-0", ["SI", "NO"], key="mostrar_00_pat")
    # nuevo desplegable solo para HT 0-0
    over_pat = "TODOS"
    if tipo_pat == "HT 0-0 + OVER":
        over_pat = st.selectbox("OVER 2DA PARTE", ["OVER 1.5", "OVER 2.5"], key="over_ht_pat")
    df_pat = cargar_patrones_0_0_80_90(tipo_pat)
    if df_pat.empty:
        st.warning("No encuentro Partidos-0-0-Hasta80-Gol80-90.csv en la carpeta del app.py")
    else:
        txt_tipo = "0-0 FINALES" if tipo_pat == "0-0 FINALES" else "0-0 hasta 80' + gol 80-90'"
        st.caption(f"Total patrones: {len(df_pat)} partidos {txt_tipo}")

        c_p1, c_p2, c_p3 = st.columns([1,1,1])
        with c_p1:
            ligas_all = sorted(df_pat['League'].dropna().unique().tolist())
            liga_pat_sel = st.multiselect("LIGA PATRONES", ["TODAS"] + ligas_all, default=["TODAS"], key="liga_patrones_0_0")
            if not liga_pat_sel:
                liga_pat_sel = ["TODAS"]
        df_l = df_pat if "TODAS" in liga_pat_sel else df_pat[df_pat['League'].isin(liga_pat_sel)]
        with c_p2:
            equipos_all = sorted(pd.concat([df_l['Home'], df_l['Away']]).dropna().unique().tolist())
            eq_pat_sel = st.multiselect("EQUIPO PATRONES", ["TODOS"] + equipos_all, default=["TODOS"], key="eq_patrones_0_0")
            if not eq_pat_sel:
                eq_pat_sel = ["TODOS"]
        with c_p3:
            fecha_pat = st.selectbox("DESDE", ["Todas"] + sorted(df_l['Date'].dt.date.astype(str).unique().tolist(), reverse=True)[:30], key="fecha_pat_0_0")

        res_pat = "-"
        if tipo_pat == "0-0 HASTA 80+ GOL 80-90" and "TODOS" not in eq_pat_sel:
            res_pat = st.selectbox("GOL ENTRE 80-90 SI EQUIPO VA", ["-","EMPATA","GANA","PIERDE"], key="res_pat_0_0")

        df_f = df_l.copy()
        if tipo_pat == "0-0 HASTA 80+ GOL 80-90" and "TODOS" not in eq_pat_sel and res_pat != "-":
            def _cumple_res(r):
                for eq in eq_pat_sel:
                    if r['Home']==eq:
                        if res_pat=="GANA" and r['FTHG']>r['FTAG']: return True
                        if res_pat=="PIERDE" and r['FTHG']<r['FTAG']: return True
                        if res_pat=="EMPATA" and r['FTHG']==r['FTAG']: return True
                    if r['Away']==eq:
                        if res_pat=="GANA" and r['FTAG']>r['FTHG']: return True
                        if res_pat=="PIERDE" and r['FTAG']<r['FTHG']: return True
                        if res_pat=="EMPATA" and r['FTHG']==r['FTAG']: return True
                return False
            df_f = df_f[df_f.apply(_cumple_res, axis=1)]
        # filtro OVER para HT 0-0 - FIX HT real 0-0
        def _es_ht00(row):
            try:
                import ast
                g2 = ast.literal_eval(str(row.get('gols_2t','[]')))
                gt = ast.literal_eval(str(row.get('gols_todos','[]')))
                gt_int = [int(str(x).strip().replace("'", "")) for x in gt]
                g2_int = [int(str(x).strip().replace("'", "")) for x in g2]
                return len(g2_int)==len(gt_int) and len(gt_int)>0 and not any(m<=45 for m in gt_int)
            except:
                return False
        if tipo_pat == "HT 0-0 + OVER":
            df_f['Total_Goles'] = pd.to_numeric(df_f['FTHG'], errors='coerce') + pd.to_numeric(df_f['FTAG'], errors='coerce')
            df_f = df_f[df_f.apply(_es_ht00, axis=1)]
            if over_pat == "OVER 1.5":
                df_f = df_f[df_f['Total_Goles'] > 1.5]
            elif over_pat == "OVER 2.5":
                df_f = df_f[df_f['Total_Goles'] > 2.5]
        if tipo_pat == "0-0 HT + 1 GOL FT":
            df_f['Total_Goles'] = pd.to_numeric(df_f['FTHG'], errors='coerce') + pd.to_numeric(df_f['FTAG'], errors='coerce')
            df_f = df_f[df_f.apply(_es_ht00, axis=1)]
            df_f = df_f[df_f['Total_Goles'] == 1]
        if tipo_pat == "1 GOL HT + OVER 1.5 FT":
            # ya filtrado arriba, asegura 1 HT y >1.5 FT
            pass
        # GOL 80' HASTA FINAL - sea cual sea el resultado previo
        if tipo_pat == "GOL 80' HASTA FINAL":
            def _tiene_gol80(row):
                try:
                    import ast
                    gt = ast.literal_eval(str(row.get('gols_todos','[]')))
                    gt_int = [int(float(str(x).replace("'", "").strip())) for x in gt if str(x).strip()!='']
                    return any(m >= 80 for m in gt_int)
                except:
                    return False
            df_f = df_f[df_f.apply(_tiene_gol80, axis=1)]
        # MOSTRAR 0-0
        if mostrar_00 == "NO":
            df_f = df_f[~((df_f['FTHG'] == 0) & (df_f['FTAG'] == 0))]
        if "TODOS" not in eq_pat_sel:
            df_f = df_f[(df_f['Home'].isin(eq_pat_sel)) | (df_f['Away'].isin(eq_pat_sel))]
        if fecha_pat != "Todas":
            try:
                fd = pd.to_datetime(fecha_pat).date()
                df_f = df_f[df_f['Date'].dt.date >= fd]
            except:
                pass

        # RESUMEN DE FILTROS SELECCIONADOS - multi
        liga_txt = ",".join(liga_pat_sel[:3]) + (f"+{len(liga_pat_sel)-3}" if len(liga_pat_sel)>3 else "") if "TODAS" not in liga_pat_sel else "TODAS"
        eq_txt = ",".join(eq_pat_sel[:3]) + (f"+{len(eq_pat_sel)-3}" if len(eq_pat_sel)>3 else "") if "TODOS" not in eq_pat_sel else "TODOS"
        st.markdown(f"<div style='font-family:monospace;font-size:11px;background:#0A2342;color:#fff;padding:6px 8px;border-radius:4px;margin-top:4px'>RESUMEN: TIPO={tipo_pat} | MOSTRAR 0-0={mostrar_00} | LIGA={liga_txt} | EQUIPO={eq_txt} | DESDE={fecha_pat} -> {len(df_f)}/{len(df_pat)} partidos</div>", unsafe_allow_html=True)

        # --- RESUMEN EQUIPOS POR LIGA + RESUMEN POR LIGA Y JORNADA ---
        resumen_eq_html = ""
        for liga2, df_liga2 in df_f.groupby('League'):
            if "TODAS" not in liga_pat_sel and liga2 not in liga_pat_sel:
                continue
            conteo = {}
            for _, rr in df_liga2.iterrows():
                j = str(rr.get('Jornada_Liga','')).replace('J','')
                for eq in [rr['Home'], rr['Away']]:
                    if "TODOS" not in eq_pat_sel and eq not in eq_pat_sel:
                        continue
                    if eq not in conteo:
                        conteo[eq] = []
                    if j not in conteo[eq]:
                        conteo[eq].append(j)
            if conteo:
                resumen_eq_html += f"<div style='background:#0A2342;color:#fff;padding:6px 8px;margin-top:10px;font-weight:900;font-family:monospace'>LIGA: {liga2}</div>"
                for eq, jornadas in sorted(conteo.items(), key=lambda x: (-len(x[1]), x[0])):
                    js = " ".join([f"J{j}" for j in sorted(jornadas, key=lambda x: int(x) if x.isdigit() else 999)])
                    resumen_eq_html += f"<div style='font-family:monospace;font-size:11px;padding:2px 8px;background:#e8ffe8;border-bottom:1px solid #ccc'><b>{eq}</b>: {js} ({len(jornadas)})</div>"

        resumen_html = resumen_eq_html
        def j_num(x):
            s=str(x).replace('J','')
            return int(s) if s.isdigit() else 999
        # totales reales por liga/jornada desde el propio CSV si tiene Total_Jornada
        for liga, df_liga in df_f.groupby('League'):
            resumen_html += f"<div style='background:#0A2342;color:#fff;padding:6px 8px;margin-top:10px;font-weight:900;font-family:monospace'>LIGA: {liga}</div>"
            for j_liga, df_j in sorted(df_liga.groupby('Jornada_Liga'), key=lambda x: j_num(x[0])):
                # total real - FIX: si Total_Jornada viene inflado por Túnez, corrige por tamaño real de liga
                if 'Total_Jornada' in df_j.columns:
                    total_j_raw = int(pd.to_numeric(df_j['Total_Jornada'], errors='coerce').max())
                    if liga in ['2 LIGA AUSTRIA 2DA','LIGA 1 TUNEZ']:
                        total_j = 8
                    else:
                        total_j = total_j_raw if total_j_raw >= len(df_j) else len(df_j)
                        if total_j < 10:
                            total_j = 10
                else:
                    total_j = len(df_j)
                
                resumen_html += f"<div style='background:#e8e8e8;padding:4px 8px;font-family:monospace;font-weight:900;border:1px solid #000'>Jornada {str(j_liga).replace('J','')}: [{len(df_j)}/{total_j}]</div>"
                for _, r in df_j.sort_values('Date').iterrows():
                    if tipo_pat == "HT 0-0 + OVER":
                        mins = r.get('gols_2t','') or r.get('gols_todos','')
                    elif tipo_pat in ["1 GOL HT + OVER 1.5 FT", "1.5 HT + OVER 2.5 FT", "0-0 HT + 1 GOL FT"]:
                        mins = r.get('gols_todos','') or r.get('mins','') or r.get('gols_2t','') or r.get('gols_80_90','')
                    elif tipo_pat == "GOL 80' HASTA FINAL":
                        mins = r.get('gols_todos','') or r.get('gols_80_90','')
                    else:
                        mins = r.get('gols_80_90','') or r.get('gols_todos','')
                    try:
                        import ast
                        mlist = ast.literal_eval(str(mins)) if isinstance(mins, str) and mins.startswith('[') else [mins]
                        mlist_int = [int(float(str(m).replace('[','').replace(']','').replace("'", "").strip())) for m in mlist if str(m).strip()!='']
                        if tipo_pat in ["0-0 HASTA 80+ GOL 80-90", "GOL 80' HASTA FINAL"]:
                            mlist_int = [m for m in mlist_int if m>=80]
                        elif tipo_pat == "HT 0-0 + OVER":
                            mlist_int = [m for m in mlist_int if m>45]
                        total_real = int(r.get('FTHG',0)) + int(r.get('FTAG',0))
                        if len(mlist_int) != total_real:
                            mlist_int = mlist_int[:total_real]
                        # --- NUEVO: split HT | 2T y negrita local si existe gols_home ---
                        try:
                            gh = ast.literal_eval(str(r.get('gols_home','[]')))
                            gh = [int(float(x)) for x in gh]
                            gt_all = ast.literal_eval(str(r.get('gols_todos','[]')))
                            gt_all = [int(float(x)) for x in gt_all]
                        except:
                            gh = []
                            gt_all = []
                        def fmt(m):
                            es_home = m in gh
                            if "TODOS" not in eq_pat_sel:
                                home_sel = r['Home'] in eq_pat_sel
                                away_sel = r['Away'] in eq_pat_sel
                                if home_sel or away_sel:
                                    # si es gol del equipo seleccionado -> verde, rival -> rojo
                                    if es_home:
                                        if home_sel:
                                            return f"<span style='background:#00E676;color:#000;font-weight:900;padding:0 4px;border-radius:3px'>{m}'</span>"
                                        else:
                                            return f"<span style='background:#FF8A80;color:#000;font-weight:900;padding:0 4px;border-radius:3px'>{m}'</span>"
                                    else:
                                        if away_sel:
                                            return f"<span style='background:#00E676;color:#000;font-weight:900;padding:0 4px;border-radius:3px'>{m}'</span>"
                                        else:
                                            return f"<span style='background:#FF8A80;color:#000;font-weight:900;padding:0 4px;border-radius:3px'>{m}'</span>"
                            if es_home:
                                return f"<span style='color:#000;font-weight:900;'>{m}'</span>"
                            else:
                                return f"<span style='color:#666'>{m}'</span>"
                        ht = [m for m in mlist_int if m <= 45]
                        st2 = [m for m in mlist_int if m > 45]
                        if ht and st2:
                            mtxt = ",".join([fmt(x) for x in ht]) + " | " + ",".join([fmt(x) for x in st2])
                        else:
                            mtxt = ",".join([fmt(x) for x in mlist_int])
                    except:
                        mtxt = str(mins)
                    def _pos_real(v):
                        if pd.isna(v) or v=='' or str(v).upper()=='NAN':
                            return ""
                        s=str(v).replace('º','').strip()
                        return f"<span style='color:#9C27B0;font-weight:900'>{s}º</span> " if s.isdigit() else ""
                    ph = _pos_real(r.get('Pos_Home','')) if 'Pos_Home' in r else ""
                    pa = _pos_real(r.get('Pos_Away','')) if 'Pos_Away' in r else ""
                    if tipo_pat == "0-0 FINALES":
                        linea_res = f"{ph}{r['Home']} {r['FTHG']}-{r['FTAG']} {r['Away']} {pa}"
                    else:
                        if tipo_pat == "1 GOL HT + OVER 1.5 FT" and not mtxt:
                            try:
                                ht_h = int(r.get('HTHG',1)); ht_a = int(r.get('HTAG',0))
                                linea_res = f"{ph}{r['Home']} {r['FTHG']}-{r['FTAG']} {r['Away']} {pa}[HT {ht_h}-{ht_a}]"
                            except:
                                linea_res = f"{ph}{r['Home']} {r['FTHG']}-{r['FTAG']} {r['Away']} {pa}"
                        else:
                            linea_res = f"{ph}{r['Home']} {r['FTHG']}-{r['FTAG']} {r['Away']} {pa}[{mtxt}]" if mtxt else f"{ph}{r['Home']} {r['FTHG']}-{r['FTAG']} {r['Away']} {pa}"
                            if not mtxt:
                                linea_res = f"{ph}{r['Home']} {r['FTHG']}-{r['FTAG']} {r['Away']} {pa}"
                    resumen_html += f"<div style='font-family:monospace;font-size:11px;padding:2px 8px;border-bottom:1px solid #ddd'>{linea_res}</div>"

        st.markdown(f"<div style='font-family:monospace;font-size:10px;background:#f0f0f0;border:1px solid #000;padding:6px'>LIGA={liga_txt} EQUIPO={eq_txt} -> {len(df_f)}/{len(df_pat)} partidos</div>", unsafe_allow_html=True)
        import streamlit.components.v1 as components
        import html as _html2
        # texto plano del resumen para copiar - multi + equipos repiten
        resumen_bar = f"RESUMEN: TIPO={tipo_pat} | MOSTRAR 0-0={mostrar_00} | LIGA={','.join(liga_pat_sel)} | EQUIPO={','.join(eq_pat_sel)} | DESDE={fecha_pat} | VA={res_pat} -> {len(df_f)}/{len(df_pat)} partidos"
        # genera texto de equipos que repiten para copiar
        resumen_eq_txt = ""
        for liga2, df_liga2 in df_f.groupby('League'):
            if "TODAS" not in liga_pat_sel and liga2 not in liga_pat_sel:
                continue
            conteo2 = {}
            for _, rr in df_liga2.iterrows():
                j = str(rr.get('Jornada_Liga','')).replace('J','')
                for eq in [rr['Home'], rr['Away']]:
                    if "TODOS" not in eq_pat_sel and eq not in eq_pat_sel:
                        continue
                    if eq not in conteo2:
                        conteo2[eq] = []
                    if j not in conteo2[eq]:
                        conteo2[eq].append(j)
            if conteo2:
                resumen_eq_txt += f"LIGA: {liga2}\n"
                for eq, jornadas in sorted(conteo2.items(), key=lambda x: (-len(x[1]), x[0])):
                    js = " ".join([f"J{j}" for j in sorted(jornadas, key=lambda x: int(x) if x.isdigit() else 999)])
                    resumen_eq_txt += f"{eq}: {js} ({len(jornadas)})\n"
                resumen_eq_txt += "\n"
        resumen_txt = resumen_bar + "\n\n" + resumen_eq_txt + "\n"
        for liga, df_liga in df_f.groupby('League'):
            resumen_txt += f"LIGA: {liga}\n"
            for j_liga, df_j in sorted(df_liga.groupby('Jornada_Liga'), key=lambda x: j_num(x[0])):
                total_j_raw = int(pd.to_numeric(df_j['Total_Jornada'], errors='coerce').max()) if 'Total_Jornada' in df_j.columns else len(df_j)
                if liga in ['2 LIGA AUSTRIA 2DA','LIGA 1 TUNEZ'] and total_j_raw > 10:
                    total_j = 8
                else:
                    total_j = total_j_raw
                resumen_txt += f"Jornada {str(j_liga).replace('J','')}: [{len(df_j)}/{total_j}]\n"
                for _, r in df_j.sort_values('Date').iterrows():
                    if tipo_pat == "HT 0-0 + OVER":
                        mins = r.get('gols_2t','') or r.get('gols_todos','')
                    elif tipo_pat in ["1 GOL HT + OVER 1.5 FT", "1.5 HT + OVER 2.5 FT"]:
                        mins = r.get('gols_todos','') or r.get('mins','') or r.get('gols_2t','') or r.get('gols_80_90','')
                    elif tipo_pat == "GOL 80' HASTA FINAL":
                        mins = r.get('gols_todos','') or r.get('gols_80_90','')
                    else:
                        mins = r.get('gols_80_90','') or r.get('gols_todos','')
                    try:
                        import ast
                        mlist = ast.literal_eval(str(mins)) if isinstance(mins, str) and mins.startswith('[') else [mins]
                        mlist_int = [int(float(str(m).replace('[','').replace(']','').replace("'", "").strip())) for m in mlist if str(m).strip()!='']
                        if tipo_pat in ["0-0 HASTA 80+ GOL 80-90", "GOL 80' HASTA FINAL"]:
                            mlist_int = [m for m in mlist_int if m>=80]
                        elif tipo_pat == "HT 0-0 + OVER":
                            mlist_int = [m for m in mlist_int if m>45]
                        else:
                            mlist_int = mlist_int
                        total_real = int(r.get('FTHG',0)) + int(r.get('FTAG',0))
                        if len(mlist_int) != total_real:
                            mlist_int = mlist_int[:total_real]
                        mtxt = ",".join([f"{m}'" for m in mlist_int])
                    except:
                        mtxt = str(mins)
                    if tipo_pat == "0-0 FINALES" or not mtxt:
                        resumen_txt += f"{r['Home']} {r['FTHG']}-{r['FTAG']} {r['Away']}\n"
                    else:
                        resumen_txt += f"{r['Home']} {r['FTHG']}-{r['FTAG']} {r['Away']} [{mtxt}]\n"
        components.html(f"""
        <div style='max-height:500px;overflow-y:auto;background:#fff;border:1px solid #000;padding:6px;font-family:monospace;font-size:11px'>{resumen_html}</div>
        <textarea id='txt_resumen' style='position:absolute;left:-9999px'>{_html2.escape(resumen_txt)}</textarea>
        <button onclick="navigator.clipboard.writeText(document.getElementById('txt_resumen').value).then(()=>{{let b=document.getElementById('btn_resumen'); b.innerText='✓ COPIADO RESUMEN';}})" id='btn_resumen' style='width:100%;background:#0A2342;color:white;border:none;border-radius:6px;padding:10px;font-weight:900;margin-top:6px'>📋 COPIAR RESUMEN ({len(df_f)})</button>
        """, height=500, scrolling=True)

        if 'ver_lista_pat' not in st.session_state:
            st.session_state.ver_lista_pat = True
        if st.button("👁️ OCULTAR/MOSTRAR LISTA DETALLADA", key="toggle_lista_pat"):
            st.session_state.ver_lista_pat = not st.session_state.ver_lista_pat

        html_pat = ""
        if not st.session_state.ver_lista_pat:
            st.caption("Lista detallada oculta")
        else:
            for _, r in df_f.sort_values('Date', ascending=False).head(200).iterrows():
                try:
                    fecha = r['Date'].strftime("%d/%m/%Y") if pd.notna(r['Date']) else ""
                    mins = r.get('gols_80_90','')
                    jl_raw = r.get('Jornada_Liga','')
                    j_label = jl_raw
                    html_pat += f"<div style='font-family:monospace;font-size:11px;padding:4px;border-bottom:1px solid #ddd'><span style='background:#0A2342;color:#fff;padding:1px 6px;border-radius:3px;font-weight:900;margin-right:6px'>{j_label}</span><b>{fecha}</b> | {r['League'][:18]} | {r['Home']} {r['FTHG']}-{r['FTAG']} {r['Away']} | GOL {mins}</div>"
                except:
                    pass

        import html as _html
        if not st.session_state.ver_lista_pat:
            html_pat = ""
        components.html(f"""
        <div style='font-family:monospace;max-height:600px;overflow-y:auto;background:#fff;border:1px solid #000;padding:6px'>{html_pat}</div>
        <textarea id='txt_pat' style='position:absolute;left:-9999px'>{_html.escape(df_f.to_string())}</textarea>
        <button onclick="navigator.clipboard.writeText(document.getElementById('txt_pat').value).then(()=>{{let b=document.getElementById('btn_pat'); b.innerText='✓ COPIADO';}})" id='btn_pat' style='width:100%;background:#0A2342;color:white;border:none;border-radius:6px;padding:10px;font-weight:900;margin-top:8px'>📋 COPIAR PATRONES ({len(df_f)})</button>
        """, height=700, scrolling=True)
# ================= FIN BLOQUE PATRONES V1 =================
###################################################################
################################################################### CLONADO FIX3 - DOBLE
###################################################################
################################################################### CLONADO FIX3 - DOBLE
###################################################################
################################################################### CLONADO FIX3 - DOBLE
###################################################################
################################################################### CLONADO FIX3 - DOBLE
###################################################################
################################################################### CLONADO FIX3 - DOBLE
###################################################################
################################################################### CLONADO FIX3 - DOBLE
###################
################################################################### CLONADO
##################
################################################################### CLONADOF
##################
################################################################### CLONADO##################
################################################################### CLONADO
##################
################################################################### CLONADO################################################################# CLONADO FIX3 - DOBLE
###################################################################
################################################################### CLONADO FIX3 - DOBLE
###################################################################
################################################################### CLONADO FIX3 - DOBLE
###################
################################################################### CLONADO
##################
################################################################### CLONADOF
##################
################################################################### CLONADO##################
################################################################### CLONADO
##################
################################################################### CLONADO################################################################# CLONADO FIX3 - DOBLE
###################################################################
################################################################### CLONADO FIX3 - DOBLE
###################################################################
################################################################### CLONADO FIX3 - DOBLE
###################
################################################################### CLONADO
##################
################################################################### CLONADOF
##################
################################################################### CLONADO##################
################################################################### CLONADO
##################
################################################################### CLONADO################################################################# CLONADO FIX3 - DOBLE
###################################################################
################################################################### CLONADO FIX3 - DOBLE
###################################################################
################################################################### CLONADO FIX3 - DOBLE
###################
################################################################### CLONADO
##################
################################################################### CLONADOF
##################
################################################################### CLONADO##################
################################################################### CLONADO
##################
################################################################### CLONADO################################################################# CLONADO FIX3 - DOBLE
###################################################################
################################################################### CLONADO FIX3 - DOBLE
###################################################################
################################################################### CLONADO FIX3 - DOBLE
###################
################################################################### CLONADO
##################
################################################################### CLONADOF
##################
################################################################### CLONADO##################
################################################################### CLONADO
##################
################################################################### CLONADO################################################################# CLONADO FIX3 - DOBLE
###################################################################
################################################################### CLONADO FIX3 - DOBLE
###################################################################
################################################################### CLONADO FIX3 - DOBLE
###################
################################################################### CLONADO
##################
################################################################### CLONADOF
##################
################################################################### CLONADO##################
################################################################### CLONADO
##################
################################################################### CLONADO################################################################# CLONADO FIX3 - DOBLE
###################################################################
################################################################### CLONADO FIX3 - DOBLE
###################################################################
################################################################### CLONADO FIX3 - DOBLE
###################
################################################################### CLONADO
##################
################################################################### CLONADOF
##################
################################################################### CLONADO##################
################################################################### CLONADO
##################
################################################################### CLONADO################################################################# CLONADO FIX3 - DOBLE
###################################################################
################################################################### CLONADO FIX3 - DOBLE
###################################################################
################################################################### CLONADO FIX3 - DOBLE
###################
################################################################### CLONADO
##################
################################################################### CLONADOF
##################
################################################################### CLONADO##################
################################################################### CLONADO
##################
################################################################### CLONADO################################################################# CLONADO FIX3 - DOBLE
###################################################################
################################################################### CLONADO FIX3 - DOBLE
###################################################################
################################################################### CLONADO FIX3 - DOBLE
###################
################################################################### CLONADO
##################
################################################################### CLONADOF
##################
################################################################### CLONADO##################
################################################################### CLONADO
##################
################################################################### CLONADO################################################################# CLONADO FIX3 - DOBLE
###################################################################
################################################################### CLONADO FIX3 - DOBLE
###################################################################
################################################################### CLONADO FIX3 - DOBLE
###################
################################################################### CLONADO
##################
################################################################### CLONADOF
##################
################################################################### CLONADO##################
################################################################### CLONADO
##################
################################################################### CLONADO
################################################################# CLONADO
##################
################################################################### CLONADO
with st.expander("PREDICCION - PARTIDOS FUTUROS + HISTORIAL FIX 2", expanded=False):
    import pathlib

    @st.cache_data(show_spinner=False)
    def cargar_futuro_fix2():
        # tu calendario real que está en github
        candidatos = [
            pathlib.Path("/mnt/data/calendario_completo_2026_2027.csv"),
            pathlib.Path(__file__).parent.resolve() / "calendario_completo_2026_2027.csv",
            pathlib.Path(".").resolve() / "calendario_completo_2026_2027.csv",
            pathlib.Path("/mnt/data/Calendario-Futuro-Ligas-Tu-Csv-LIMPIO.csv"),
        ]
        p = None
        for c in candidatos:
            if c.exists():
                p = c
                break
        if not p:
            return pd.DataFrame()
        df_fut = pd.read_csv(p, on_bad_lines='skip')
        # normaliza columnas para que tu resto del bloque siga funcionando
        # tu csv nuevo trae 'League' no 'League_CSV'
        if 'League_CSV' not in df_fut.columns and 'League' in df_fut.columns:
            df_fut['League_CSV'] = df_fut['League']
        df_fut['Date'] = pd.to_datetime(df_fut['Date'], errors='coerce')
        return df_fut

    df_futuro_fix2 = cargar_futuro_fix2()
############

    import json, time
    FILE_PERSIST_PRED_FIX2 = pathlib.Path(__file__).parent.resolve() / ".persist_pred_48h_fix2.json"
    TTL_48H = 48 * 3600
    def _load_persist_48h_fix2():
        if not FILE_PERSIST_PRED_FIX2.exists():
            return {}
        try:
            if time.time() - FILE_PERSIST_PRED_FIX2.stat().st_mtime > TTL_48H:
                FILE_PERSIST_PRED_FIX2.unlink(missing_ok=True)
                return {}
            with open(FILE_PERSIST_PRED_FIX2, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    def _save_persist_48h_fix2():
        try:
            data = {
                "ligas_pred_fix2": st.session_state.get("ligas_pred_fix2", []),
                "fecha_pred_fix2": st.session_state.get("fecha_pred_fix2", "Todas"),
                "min_desde_pred_fix2": st.session_state.get("min_desde_pred_fix2", ""),
                "min_hasta_pred_fix2": st.session_state.get("min_hasta_pred_fix2", ""),
                "partidos_pred_sel_fix2": st.session_state.get("partidos_pred_sel_fix2", []),
                "eq_manual_1_fix2": st.session_state.get("eq_manual_1_fix2", []),
                "eq_manual_2_fix2": st.session_state.get("eq_manual_2_fix2", []),
                "cond_loc_pred_fix2": st.session_state.get("cond_loc_pred_fix2", "Local en casa / Visitante fuera"),
                "filtro_ht_ft_unico_2026_v9_fix2": st.session_state.get("filtro_ht_ft_unico_2026_v9_fix2", []),
                "ver_goleadores_fix2": st.session_state.get("ver_goleadores_fix2", "OFF"),
                "ambos_marcan_fix2": st.session_state.get("ambos_marcan_fix2", "-"),
            }
            with open(FILE_PERSIST_PRED_FIX2, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except:
            pass

    _persist_fix2 = _load_persist_48h_fix2()
    if "ligas_pred_fix2" not in st.session_state:
        st.session_state.ligas_pred_fix2 = _persist_fix2.get("ligas_pred_fix2") or st.query_params.get_all("ligas_pred_fix2")
    if "fecha_pred_fix2" not in st.session_state:
        st.session_state.fecha_pred_fix2 = _persist_fix2.get("fecha_pred_fix2") or st.query_params.get("fecha_pred_fix2", "Todas")
    if "min_desde_pred_fix2" not in st.session_state:
        st.session_state.min_desde_pred_fix2 = _persist_fix2.get("min_desde_pred_fix2") or st.query_params.get("min_desde_pred_fix2", "")
    if "min_hasta_pred_fix2" not in st.session_state:
        st.session_state.min_hasta_pred_fix2 = _persist_fix2.get("min_hasta_pred_fix2") or st.query_params.get("min_hasta_pred_fix2", "")
    if "partidos_pred_sel_fix2" not in st.session_state:
        st.session_state.partidos_pred_sel_fix2 = _persist_fix2.get("partidos_pred_sel_fix2") or st.query_params.get_all("partidos_pred_sel_fix2")
    if "eq_manual_1_fix2" not in st.session_state:
        st.session_state.eq_manual_1_fix2 = _persist_fix2.get("eq_manual_1_fix2") or st.query_params.get_all("eq_manual_1_fix2")
    if "eq_manual_2_fix2" not in st.session_state:
        st.session_state.eq_manual_2_fix2 = _persist_fix2.get("eq_manual_2_fix2") or st.query_params.get_all("eq_manual_2_fix2")
    if "cond_loc_pred_fix2" not in st.session_state:
        st.session_state.cond_loc_pred_fix2 = _persist_fix2.get("cond_loc_pred_fix2") or st.query_params.get("cond_loc_pred_fix2", "Local en casa / Visitante fuera")
    if "filtro_ht_ft_unico_2026_v9_fix2" not in st.session_state:
        st.session_state.filtro_ht_ft_unico_2026_v9_fix2 = _persist_fix2.get("filtro_ht_ft_unico_2026_v9_fix2") or st.query_params.get_all("filtro_ht_ft_unico_2026_v9_fix2")
    if "ambos_marcan_fix2" not in st.session_state:
        st.session_state.ambos_marcan_fix2 = _persist_fix2.get("ambos_marcan_fix2") or st.query_params.get("ambos_marcan_fix2", "-")

    if st.button(" LIMPIAR TODO EL BLOQUE PREDICCION FIX2", key="btn_limpiar_pred_fix2", use_container_width=True):
        for k in ["ligas_pred_fix2","fecha_pred_fix2","min_desde_pred_fix2","min_hasta_pred_fix2","partidos_pred_sel_fix2","eq_manual_1_fix2","eq_manual_2_fix2","filtro_ht_ft_unico_2026_v9_fix2","cond_loc_pred_fix2"]:
            if k in st.session_state:
                del st.session_state[k]
        for k in ["ligas_pred_fix2","fecha_pred_fix2","min_desde_pred_fix2","min_hasta_pred_fix2"]:
            if k in st.query_params:
                del st.query_params[k]
        try:
            FILE_PERSIST_PRED_FIX2.unlink(missing_ok=True)
        except:
            pass
        st.rerun()

    _save_persist_48h_fix2()

    @st.cache_data(show_spinner=False)
    def cargar_base_europa_fix2_v2():
        def _find_first(names):
            for name in names:
                for base in [pathlib.Path(name), pathlib.Path(__file__).parent.resolve()/name, pathlib.Path("/mnt/data")/name]:
                    if base.exists():
                        return base
            return None
        def _load_concat_partidos(file_list):
            dfs=[]
            for name in file_list:
                for base in [pathlib.Path(name), pathlib.Path(__file__).parent.resolve()/name, pathlib.Path("/mnt/data")/name]:
                    if base.exists():
                        try:
                            if str(base).endswith('.parquet'):
                                dfs.append(pd.read_parquet(base))
                            else:
                                dfs.append(pd.read_csv(base, on_bad_lines='skip'))
                        except:
                            pass
                        break
            if not dfs:
                return pd.DataFrame()
            df_all = pd.concat(dfs, ignore_index=True)
            if 'fixture_id' in df_all.columns:
                df_all = df_all.drop_duplicates(subset=['fixture_id'], keep='last')
            return df_all

        def _load_concat_goles(file_list):
            dfs=[]
            for name in file_list:
                for base in [pathlib.Path(name), pathlib.Path(__file__).parent.resolve()/name, pathlib.Path("/mnt/data")/name]:
                    if base.exists():
                        try:
                            if str(base).endswith('.parquet'):
                                dfs.append(pd.read_parquet(base))
                            else:
                                dfs.append(pd.read_csv(base, on_bad_lines='skip'))
                        except:
                            pass
                        break
            if not dfs:
                return pd.DataFrame()
            df_all = pd.concat(dfs, ignore_index=True)
            # NO borrar por fixture_id solo - perderias minutos
            if 'fixture_id' in df_all.columns:
                cols = [c for c in ['fixture_id','minuto','minute','m','equipo','team_id'] if c in df_all.columns]
                if len(cols) >=2:
                    df_all = df_all.drop_duplicates(subset=cols, keep='last')
                else:
                    df_all = df_all.drop_duplicates(subset=['fixture_id'], keep='last')
            return df_all

        # PARTIDOS: europa + resto + Nations League
        df_e = _load_concat_partidos(["base_partidos_europa.parquet", "base_partidos_resto.parquet", "base_partidos_resto_CORREGIDO.csv", "base_partidos.csv", "uefa_nations_league_2627.csv"])
        if not df_e.empty:
            df_e['HomeNorm'] = df_e['HomeTeam'].astype(str).str.upper().str.strip()
            df_e['AwayNorm'] = df_e['AwayTeam'].astype(str).str.upper().str.strip()
            def _parse_fecha_base_fix2(s):
                try:
                    d = pd.to_datetime(s, dayfirst=True, errors='coerce')
                    if pd.isna(d):
                        d = pd.to_datetime(s, errors='coerce')
                    return d
                except:
                    return pd.NaT
            df_e['Date'] = df_e['Date'].apply(_parse_fecha_base_fix2)
            df_e = df_e.sort_values(['League','Season','Date']).copy()
            # USA TU jornada_num DEL CSV/PARQUET - NO RECALCULA
            if 'jornada_num' in df_e.columns:
                df_e['Jornada'] = df_e['jornada_num'].astype(str).str.extract(r'(\d+)').astype(float).fillna(0).astype(int)
            else:
                df_e['Jornada'] = 0
                for (l_name, s_name), g_s in df_e.groupby(['League','Season'], sort=False):
                    g_s = g_s.sort_values('Date')
                    idxs = g_s.index.to_numpy()
                    n_teams = len(pd.unique(pd.concat([g_s['HomeTeam'], g_s['AwayTeam']]).dropna()))
                    ppj = max(n_teams // 2, 1)
                    df_e.loc[idxs, 'Jornada'] = (np.arange(len(idxs)) // ppj) + 1

        # GOLES: europa + resto + Nations League
        df_g = _load_concat_goles(["base_goles_europa.parquet", "base_goles_resto.parquet", "base_goles_resto_CORREGIDO.csv", "base_goles.csv", "base_goles_resto.csv", "base_goles_europa.csv", "uefa_nations_league_2627_goles.csv"])
        ev = {}
        ###########BLOQUE GOLES FIX 2 GOLEADOR ASISTENTE
        if not df_g.empty:
            def _parse_min_fix2(v):
                try:
                    s=str(v).strip().replace("'", "")
                    if "+" in s:
                        a,b=s.split("+",1)
                        return int(a)+int(b)
                    return int(float(s))
                except:
                    return 0
            df_g['fid_str'] = df_g['fixture_id'].astype(str).str.split('.').str[0]
            df_g['m'] = df_g.get('minuto', 0).apply(_parse_min_fix2)
            for fid, sub in df_g.groupby('fid_str'):
                ev[fid] = [{'m': int(r.get('m', 0)), 'team': normaliza(r.get('equipo','')), 'tipo': str(r.get('tipo','')), 'goleador': str(r.get('goleador','')), 'asistente': str(r.get('asistente',''))} for _, r in sub.iterrows()]
        return df_e, ev

    df_europa_fix2, eventos_europa_fix2 = cargar_base_europa_fix2_v2()

    @st.cache_data(show_spinner=False)
    def cargar_clasificacion_fix2():
        for p in [pathlib.Path("/mnt/data/Base-Clasificacion-Jornada.csv"), pathlib.Path(__file__).parent.resolve()/ "Base-Clasificacion-Jornada.csv"]:
            if p.exists():
                try:
                    return pd.read_csv(p, on_bad_lines='skip')
                except:
                    pass
        return pd.DataFrame()
    df_clas_fix2 = cargar_clasificacion_fix2()
    clas_dict_fix2 = {}
    clas_max_j_fix2 = {}
    if not df_clas_fix2.empty:
        for _, rc in df_clas_fix2.iterrows():
            try:
                k = (normaliza(rc.get('League','')), int(rc.get('jornada_int',0)), normaliza(rc.get('Team','')))
                clas_dict_fix2[k] = rc
                ln = normaliza(rc.get('League',''))
                clas_max_j_fix2[ln] = max(clas_max_j_fix2.get(ln,0), int(rc.get('jornada_int',0)))
            except:
                pass

    df_fix2 = df_europa_fix2
    eventos_fix2 = eventos_europa_fix2

    if "show_partidos_fix2" not in st.session_state:
        st.session_state.show_partidos_fix2 = False
    if st.button("👁️ MOSTRAR / OCULTAR PARTIDOS FIX2", key="btn_toggle_partidos_fix2", use_container_width=True):
        st.session_state.show_partidos_fix2 = not st.session_state.show_partidos_fix2

    ligas_fut_all_fix2 = sorted(df_futuro_fix2['League_CSV'].dropna().unique().tolist())
    keywords_eu = ["Eliteserien","Eredivisie","Bundesliga","LaLiga","Premier","Serie A","Ligue","Pro League","First League Bulgaria","Super Lig","Ekstraklasa","Primeira Liga","K League","K LEAGUE","J1 League","J2 League","CSL","Chinese Super League","A-League","MLS","Brasileirao","Liga MX"]
    if not df_europa_fix2.empty and 'League' in df_europa_fix2.columns:
        ligas_europa_set_fix2 = set(df_europa_fix2['League'].dropna().astype(str).tolist())
        ligas_por_europa = [l for l in ligas_fut_all_fix2 if any(normaliza(l) == normaliza(le) or normaliza(l) in normaliza(le) or normaliza(le) in normaliza(l) for le in ligas_europa_set_fix2)]
        ligas_por_key = [l for l in ligas_fut_all_fix2 if any(k.lower() in l.lower() for k in keywords_eu)]
        ligas_fut_fix2 = sorted(list(set(ligas_por_europa + ligas_por_key)))
        if not ligas_fut_fix2:
            ligas_fut_fix2 = sorted(list(set(ligas_por_key)))
    else:
        ligas_fut_fix2 = [l for l in ligas_fut_all_fix2 if any(k.lower() in l.lower() for k in keywords_eu)]
        if not ligas_fut_fix2:
            ligas_fut_fix2 = ligas_fut_all_fix2

    c_lp4_fix2 = st.columns([1])[0]
    with c_lp4_fix2:
        ver_goleadores_fix2 = st.selectbox("GOLEADOR+ASIST", ["ON","OFF"], index=0 if st.session_state.get("ver_goleadores_fix2","ON")=="ON" else 1, key="ver_goleadores_fix2")
        cond_loc_pred_fix2 = "TODOS"
        res_1p_tipo_fix2 = st.selectbox("Resultado 1ªP", ["TODOS","EMPATE","GANA","PIERDE","EMPATEGANA","EMPATEPIERDE","GANAPIERDE"], index=0, key="res_1p_tipo_pred_fix2")
        res_ft_tipo_fix2 = st.selectbox("Resultado FINAL FIX2", ["TODOS","GANA","EMPATA","PIERDE","GANAEMPATA","GANAPIERDE","EMPATAPIERDE"], index=0, key="res_ft_tipo_fix2")
        opciones_res_fix2 = [f"{a}-{b}_1ªP" for a in range(5) for b in range(5)] + [f"{a}-{b}_2ªP" for a in range(5) for b in range(5)]
        resultados_pred_sel_fix2 = st.multiselect("Resultado 1ªP / 2ªP", opciones_res_fix2, default=[], key="filtro_ht_ft_unico_2026_v9_fix2", placeholder="Ej: 0-0_1ªP")
        # AMBOS MARCAN movido debajo de Overs
        res_live_tipo_fix2 = "TODOS"
        min_live_raw_fix2 = ""

    # --- NUEVO DESPLEGABLE LIGAS PARA FILTRAR EQUIPOS ---
    ligas_hist_fix2 = ["TODAS"] + sorted(df_fix2['League'].dropna().astype(str).unique().tolist()) if not df_fix2.empty and 'League' in df_fix2.columns else ["TODAS"]
    liga_hist_sel_fix2 = st.selectbox("LIGA HISTORIAL FIX2", ligas_hist_fix2, index=0, key="liga_hist_fix2")
    if liga_hist_sel_fix2 != "TODAS":
        df_liga_filt = df_fix2[df_fix2['League'].astype(str) == liga_hist_sel_fix2]
        lista_hist_equipos_fix2 = sorted(pd.concat([df_liga_filt['HomeTeam'], df_liga_filt['AwayTeam']]).dropna().astype(str).unique().tolist())
    else:
        lista_hist_equipos_fix2 = sorted(pd.concat([df_fix2['HomeTeam'], df_fix2['AwayTeam']]).dropna().astype(str).unique().tolist())

    # MIN DESDE/HASTA - MISMA LINEA IZQ/DCHA PEQUEÑO CENTRADO - FIX MOVIL REAL
    c_min_a_fix2, c_min_b_fix2 = st.columns([1,1], gap="small")
    with c_min_a_fix2:
        min_desde_pred_raw_fix2 = st.text_input("MIN DESDE FIX2", key="min_desde_pred_fix2", placeholder="-")
    with c_min_b_fix2:
        min_hasta_pred_raw_fix2 = st.text_input("MIN HASTA FIX2", key="min_hasta_pred_fix2", placeholder="-")

    import streamlit.components.v1 as components
    components.html("""
    <script>
    (function(){
      const doc = window.parent.document;
      function fixMin(){
        const a = doc.querySelector('input[aria-label="MIN DESDE FIX2"]');
        if(!a) return;
        const hb = a.closest('div[data-testid="stHorizontalBlock"]');
        if(!hb) return;
        hb.style.setProperty('display','flex','important');
        hb.style.setProperty('flex-direction','row','important');
        hb.style.setProperty('flex-wrap','nowrap','important');
        hb.style.setProperty('justify-content','center','important');
        hb.style.setProperty('align-items','center','important');
        hb.style.setProperty('gap','10px','important');
        hb.style.setProperty('max-width','230px','important');
        hb.style.setProperty('width','230px','important');
        hb.style.setProperty('margin','0 auto','important');
        hb.querySelectorAll(':scope > div[data-testid="column"]').forEach(col=>{
          col.style.setProperty('flex','0 0 105px','important');
          col.style.setProperty('min-width','105px','important');
          col.style.setProperty('max-width','105px','important');
          col.style.setProperty('width','105px','important');
        });
        // aprieta el input interno para que no ocupe 100vw
        hb.querySelectorAll('input[aria-label="MIN DESDE FIX2"], input[aria-label="MIN HASTA FIX2"]').forEach(inp=>{
          inp.style.setProperty('max-width','105px','important');
          inp.style.setProperty('width','105px','important');
          const wrap = inp.closest('div[data-testid="stTextInput"]');
          if(wrap){
            wrap.style.setProperty('max-width','105px','important');
            wrap.style.setProperty('width','105px','important');
            wrap.style.setProperty('margin','0 auto','important');
          }
        });
      }
      setTimeout(fixMin, 200);
      setTimeout(fixMin, 800);
      setInterval(fixMin, 1200);
    })();
    </script>
    """, height=0)

    equipos_manuales_2_fix2 = []
    # EQUIPOS MANUALES 2 QUITADO - solo uso el 1
    equipos_manuales_1_fix2 = st.multiselect("Equipos manuales 1 FIX2", lista_hist_equipos_fix2, default=[], key="eq_manual_1_fix2", placeholder="Ej: Cartagena, Burgos...")
    goles_parte_fix2 = st.selectbox("GOLES PARTE", ["Todo","1ªParte","2ªParte"], index=0, key="goles_parte_fix2")
    overs_sel_fix2 = st.multiselect("Overs / Unders por parte", ["1P >0.5","1P >1.5","1P >2.5","2P >0.5","2P >1.5","2P >2.5"], default=[], key="overs_unders_pred_fix2", placeholder="Ej: 1P >0.5")
    ambos_marcan_fix2 = st.selectbox("AMBOS MARCAN", ["-","SI","NO"], index=["-","SI","NO"].index(st.session_state.get("ambos_marcan_fix2","-")), key="ambos_marcan_fix2")

    ligas_pred_sel_fix2 = []
    fecha_pred_sel_fix2 = "Todas"
    df_base_pred_fix2 = df_futuro_fix2

    def _parse_min_pred_fix2(v):
        try:
            if v is None or str(v).strip() in ["", "-", "–", "—"]: return None
            return int(str(v).strip().replace("'", ""))
        except: return None
    MIN_DESDE_PRED_FIX2 = _parse_min_pred_fix2(min_desde_pred_raw_fix2)
    MIN_HASTA_PRED_FIX2 = _parse_min_pred_fix2(min_hasta_pred_raw_fix2)
    MIN_LIVE_FIX2 = _parse_min_pred_fix2(min_live_raw_fix2)

    if fecha_pred_sel_fix2!= "Todas":
        try:
            f_date_fix2 = pd.to_datetime(fecha_pred_sel_fix2, dayfirst=True).date()
            df_base_pred_fix2 = df_base_pred_fix2[df_base_pred_fix2['Date'].dt.date >= f_date_fix2]
        except: pass

    df_base_pred_fix2 = df_base_pred_fix2.sort_values('Date').head(1000)

    opciones_partidos_fix2 = []
    for _, r in df_base_pred_fix2.iterrows():
        try:
            fecha_s = r['Date'].strftime("%d/%m")
            liga_s = str(r['League_CSV'])[:15]
            h = str(r['HomeTeam']).strip()
            a = str(r['AwayTeam']).strip()
            fid = str(r.get('fixture_id',''))
            opciones_partidos_fix2.append(f"{fecha_s} | {liga_s} | {h} vs {a} | {fid}")
        except: continue

    partidos_sel_fix2 = []
    # DESPLEGABLE PARTIDO FUTURO QUITADO - solo uso manual

    partidos_pred_copy_fix2 = []
    tiene_manuales_fix2 = (len(equipos_manuales_1_fix2) > 0 or len(equipos_manuales_2_fix2) > 0)

    if not partidos_sel_fix2 and not tiene_manuales_fix2:
        pass
    else:
        partidos_pred_copy_fix2 = []
        lista_resumen_fix2 = []
        partidos_a_iterar_fix2 = partidos_sel_fix2 if partidos_sel_fix2 else ["MANUAL | Manual | Manual vs Manual | 0"]

        for partido_str_fix2 in partidos_a_iterar_fix2:
            try:
                partes_fix2 = partido_str_fix2.split("|")
                teams_part_fix2 = partes_fix2[2].strip() if len(partes_fix2)>=3 else ""
                if " vs " in teams_part_fix2:
                    h_fut_fix2, a_fut_fix2 = [x.strip() for x in teams_part_fix2.split(" vs ")]
                else:
                    continue
            except:
                continue

            # calcula 2/5 y 1/9 para el futuro antes de pintar
            def _cnt_fut_fix2(nom):
                _up = nom.upper().strip()
                _df = df_fix2[(df_fix2['HomeNorm'] == _up) | (df_fix2['AwayNorm'] == _up)] if 'HomeNorm' in df_fix2.columns else df_fix2[(df_fix2['HomeTeam'].astype(str).str.upper().str.strip() == _up) | (df_fix2['AwayTeam'].astype(str).str.upper().str.strip() == _up)]
                _tot = len(_df)
                _df_f = _df.copy()
                if resultados_pred_sel_fix2:
                    sel_fix2 = resultados_pred_sel_fix2
                    set_1p = set(); set_2p = set()
                    for s in sel_fix2:
                        if "_1ªP" in s:
                            try: _x,_y = s.replace("_1ªP","").split("-"); set_1p.add((int(_x),int(_y)))
                            except: pass
                        if "_2ªP" in s:
                            try: _x,_y = s.replace("_2ªP","").split("-"); set_2p.add((int(_x),int(_y)))
                            except: pass
                    if set_1p or set_2p:
                        def _cumple(rr):
                            try:
                                hg_ = int(float(rr.get('FTHG',0) or 0)); ag_ = int(float(rr.get('FTAG',0) or 0))
                                hthg_ = int(float(rr.get('HTHG',0) or 0)); htag_ = int(float(rr.get('HTAG',0) or 0))
                            except: return False
                            if set_1p and (hthg_, htag_) in set_1p: return True
                            if set_2p and (hg_, ag_) in set_2p: return True
                            return False
                        _df_f = _df_f[_df_f.apply(_cumple, axis=1)]
                # MIN DESDE / HASTA - cuenta solo partidos con gol en ese rango
                if MIN_DESDE_PRED_FIX2 is not None or MIN_HASTA_PRED_FIX2 is not None:
                    def _tiene_min_f(rr):
                        fid = str(rr.get('fixture_id','')).split('.')[0]
                        evs = eventos_fix2.get(fid, [])
                        if not evs:
                            try:
                                import pathlib as _pb2
                                _gb2 = _pb2.Path("/mnt/data/base_goles.csv")
                                if _gb2.exists():
                                    _dfgb2 = pd.read_csv(_gb2, on_bad_lines='skip')
                                    _dfgb2['fid_str'] = _dfgb2['fixture_id'].astype(str).str.split('.').str[0]
                                    _sub2 = _dfgb2[_dfgb2['fid_str']==fid]
                                    for _, _rg2 in _sub2.iterrows():
                                        try:
                                            _ms2 = str(_rg2.get('minuto','0')).replace("'", "")
                                            _mm2 = int(_ms2.split('+')[0].split('.')[0]) if _ms2 else 0
                                        except:
                                            _mm2 = 0
                                        if 'Missed' in str(_rg2.get('tipo','')): continue
                                        if MIN_DESDE_PRED_FIX2 is not None and _mm2 < MIN_DESDE_PRED_FIX2: continue
                                        if MIN_HASTA_PRED_FIX2 is not None and _mm2 > MIN_HASTA_PRED_FIX2: continue
                                        return True
                                    return False
                            except:
                                pass
                        for ev in evs:
                            if 'Missed' in ev.get('tipo',''): continue
                            mm = ev.get('m',-1)
                            if MIN_DESDE_PRED_FIX2 is not None and mm < MIN_DESDE_PRED_FIX2: continue
                            if MIN_HASTA_PRED_FIX2 is not None and mm > MIN_HASTA_PRED_FIX2: continue
                            return True
                        return False
                    _df_f = _df_f[_df_f.apply(_tiene_min_f, axis=1)]
                return len(_df_f), _tot
            f_h_filt, f_h_tot = _cnt_fut_fix2(h_fut_fix2)
            f_a_filt, f_a_tot = _cnt_fut_fix2(a_fut_fix2)
            st.markdown(f"<div style='font-family:monospace;font-weight:900;background:#FFFFFF;color:#000;padding:6px 8px;margin:12px 0 4px 0;font-size:12px;border:1px solid #000'>🔮 FUTURO FIX2: {h_fut_fix2} {f_h_filt}/{f_h_tot} vs {a_fut_fix2} {f_a_filt}/{f_a_tot} | {partes_fix2[0].strip()}</div>", unsafe_allow_html=True)

            if "MANUAL" in partido_str_fix2:
                equipos_a_mostrar_fix2 = []
                if equipos_manuales_1_fix2: equipos_a_mostrar_fix2.extend(equipos_manuales_1_fix2)
                if equipos_manuales_2_fix2: equipos_a_mostrar_fix2.extend(equipos_manuales_2_fix2)
            else:
                equipos_a_mostrar_fix2 = [h_fut_fix2, a_fut_fix2]
                if equipos_manuales_1_fix2: equipos_a_mostrar_fix2.extend(equipos_manuales_1_fix2)
                if equipos_manuales_2_fix2: equipos_a_mostrar_fix2.extend(equipos_manuales_2_fix2)

            for nombre_eq_fix2 in equipos_a_mostrar_fix2:
                norm_eq_fix2 = normaliza(nombre_eq_fix2)
                eq_up_fix2 = nombre_eq_fix2.upper().strip()
                df_team_fix2 = df_fix2[(df_fix2['HomeNorm'] == eq_up_fix2) | (df_fix2['AwayNorm'] == eq_up_fix2)] if 'HomeNorm' in df_fix2.columns else df_fix2[(df_fix2['HomeTeam'].astype(str).str.upper().str.strip() == eq_up_fix2) | (df_fix2['AwayTeam'].astype(str).str.upper().str.strip() == eq_up_fix2)]

                if cond_loc_pred_fix2 == "equipo local solamente partidos de local" and nombre_eq_fix2 == h_fut_fix2:
                    df_team_fix2 = df_team_fix2[df_team_fix2['HomeNorm'] == eq_up_fix2] if 'HomeNorm' in df_team_fix2.columns else df_team_fix2[df_team_fix2['HomeTeam'].astype(str).str.upper().str.strip() == eq_up_fix2]
                elif cond_loc_pred_fix2 == "equipo visitante solamente sus partidos de visitante" and nombre_eq_fix2 == a_fut_fix2:
                    df_team_fix2 = df_team_fix2[df_team_fix2['AwayTeam'].astype(str).str.upper().str.strip() == eq_up_fix2]
                elif cond_loc_pred_fix2 == "Local en casa / Visitante fuera":
                    if nombre_eq_fix2 == h_fut_fix2:
                        df_team_fix2 = df_team_fix2[df_team_fix2['HomeTeam'].astype(str).str.upper().str.strip() == eq_up_fix2]
                    elif nombre_eq_fix2 == a_fut_fix2:
                        df_team_fix2 = df_team_fix2[df_team_fix2['AwayTeam'].astype(str).str.upper().str.strip() == eq_up_fix2]

                # BASE TOTAL SIN FILTROS - Para testigo JX ante cualquier filtro
                df_team_base_total_fix2 = df_team_fix2.copy()
                try:
                    df_team_base_total_fix2['Date_parsed_tmp'] = pd.to_datetime(df_team_base_total_fix2['Date'], dayfirst=True, errors='coerce')
                    df_team_base_total_fix2 = df_team_base_total_fix2.sort_values('Date_parsed_tmp').reset_index(drop=True)
                    df_team_base_total_fix2['J_EQ'] = range(1, len(df_team_base_total_fix2)+1)
                    df_team_fix2['J_EQ'] = df_team_base_total_fix2['J_EQ'].values
                    df_team_base_pred_fix2 = df_team_base_total_fix2.copy()
                except:
                    df_team_base_total_fix2['J_EQ'] = range(1, len(df_team_base_total_fix2)+1)
                    df_team_fix2['J_EQ'] = df_team_base_total_fix2['J_EQ'].values
                    df_team_base_pred_fix2 = df_team_base_total_fix2.copy()

                # Esta es la base que usaremos para sacar las 15 jornadas - SIN filtros de desplegables
                df_team_base_pred_fix2 = df_team_base_total_fix2.copy()
                if resultados_pred_sel_fix2: # [TAG-FIX2-SET-UNICO-NO-TOCAR-FIX3] - [TAG-FIX2-SET-FINAL]
                    sel_fix2 = resultados_pred_sel_fix2
                    set_1p_fix2 = set(); set_2p_fix2 = set()
                    for s in sel_fix2:
                        if "_1ªP" in s:
                            try: _x,_y = s.replace("_1ªP","").split("-"); set_1p_fix2.add((int(_x),int(_y))) # 
                            except: pass
                        if "_2ªP" in s:
                            try: _x,_y = s.replace("_2ªP","").split("-"); set_2p_fix2.add((int(_x),int(_y))) # 
                            except: pass
                    if set_1p_fix2 or set_2p_fix2:
                        def _cumple_res_pred_fix2(rr):
                            try:
                                hg_ = int(float(rr.get('FTHG',0) or 0)); ag_ = int(float(rr.get('FTAG',0) or 0))
                                hthg_ = int(float(rr.get('HTHG',0) or 0)); htag_ = int(float(rr.get('HTAG',0) or 0))
                            except: return False
                            if set_1p_fix2 and (hthg_, htag_) in set_1p_fix2: return True
                            if set_2p_fix2 and (hg_, ag_) in set_2p_fix2: return True
                            return False
                        df_team_fix2 = df_team_fix2[df_team_fix2.apply(_cumple_res_pred_fix2, axis=1)]

                if overs_sel_fix2:
                    def _cumple_overs_pred_fix2(rr):
                        try:
                            hg_ = int(float(rr.get('FTHG',0) or 0)); ag_ = int(float(rr.get('FTAG',0) or 0))
                            hthg_ = int(float(rr.get('HTHG',0) or 0)); htag_ = int(float(rr.get('HTAG',0) or 0))
                            if hthg_==0 and htag_==0:
                                try:
                                    fid = str(rr.get('fixture_id','')).split('.')[0]
                                    c1=0; c2=0
                                    for ev in eventos_fix2.get(fid, []):
                                        if ev.get('m',999)<=45 and 'Missed' not in ev.get('tipo',''):
                                            if normaliza(ev.get('team','')) == normaliza(str(rr.get('HomeTeam',''))):
                                                c1+=1
                                            else:
                                                c2+=1
                                    if c1+c2>0:
                                        hthg_=c1; htag_=c2
                                except:
                                    pass
                        except:
                            return False
                        g1 = hthg_ + htag_
                        g2 = (hg_ + ag_) - g1
                        if g2 < 0: g2 = 0
                        for o in overs_sel_fix2:
                            if o == "1P >0.5" and not (g1 > 0.5): return False
                            if o == "1P >1.5" and not (g1 > 1.5): return False
                            if o == "1P >2.5" and not (g1 > 2.5): return False
                            if o == "2P >0.5" and not (g2 > 0.5): return False
                            if o == "2P >1.5" and not (g2 > 1.5): return False
                            if o == "2P >2.5" and not (g2 > 2.5): return False
                        return True
                    df_team_fix2 = df_team_fix2[df_team_fix2.apply(_cumple_overs_pred_fix2, axis=1)]

                if ambos_marcan_fix2 != "-":
                    def _cumple_btts_fix2(rr):
                        try:
                            hg_ = int(float(rr.get('FTHG',0) or 0)); ag_ = int(float(rr.get('FTAG',0) or 0))
                        except:
                            return False
                        btts = (hg_ > 0 and ag_ > 0)
                        return btts if ambos_marcan_fix2 == "SI" else not btts
                    df_team_fix2 = df_team_fix2[df_team_fix2.apply(_cumple_btts_fix2, axis=1)]

                if res_1p_tipo_fix2!= "TODOS":
                    def _cumple_1p_tipo_fix2(rr):
                        try:
                            hthg_ = int(float(rr.get('HTHG',0) or 0)); htag_ = int(float(rr.get('HTAG',0) or 0))
                        except: return False
                        hn_ = normaliza(rr.get('HomeTeam','')); an_ = normaliza(rr.get('AwayTeam',''))
                        if norm_eq_fix2 == hn_:
                            r_ = "GANA" if hthg_ > htag_ else "EMPATE" if hthg_ == htag_ else "PIERDE"
                        elif norm_eq_fix2 == an_:
                            r_ = "GANA" if htag_ > hthg_ else "EMPATE" if htag_ == hthg_ else "PIERDE"
                        else:
                            return False
                        if res_1p_tipo_fix2 == "EMPATE": return r_ == "EMPATE"
                        if res_1p_tipo_fix2 == "GANA": return r_ == "GANA"
                        if res_1p_tipo_fix2 == "PIERDE": return r_ == "PIERDE"
                        if res_1p_tipo_fix2 == "EMPATEGANA": return r_ in ("EMPATE","GANA")
                        if res_1p_tipo_fix2 == "EMPATEPIERDE": return r_ in ("EMPATE","PIERDE")
                        if res_1p_tipo_fix2 == "GANAPIERDE": return r_ in ("GANA","PIERDE")
                        return True
                    df_team_fix2 = df_team_fix2[df_team_fix2.apply(_cumple_1p_tipo_fix2, axis=1)]

                if res_ft_tipo_fix2 != "TODOS":
                    def _cumple_ft_tipo_fix2(rr):
                        try:
                            hg_ = int(float(rr.get('FTHG',0) or 0)); ag_ = int(float(rr.get('FTAG',0) or 0))
                        except: return False
                        hn_ = normaliza(rr.get('HomeTeam','')); an_ = normaliza(rr.get('AwayTeam',''))
                        if norm_eq_fix2 == hn_:
                            r_ = "GANA" if hg_ > ag_ else "EMPATA" if hg_ == ag_ else "PIERDE"
                        elif norm_eq_fix2 == an_:
                            r_ = "GANA" if ag_ > hg_ else "EMPATA" if ag_ == hg_ else "PIERDE"
                        else:
                            return False
                        if res_ft_tipo_fix2 == "GANA": return r_ == "GANA"
                        if res_ft_tipo_fix2 == "EMPATA": return r_ == "EMPATA"
                        if res_ft_tipo_fix2 == "PIERDE": return r_ == "PIERDE"
                        if res_ft_tipo_fix2 == "GANAEMPATA": return r_ in ("GANA","EMPATA")
                        if res_ft_tipo_fix2 == "GANAPIERDE": return r_ in ("GANA","PIERDE")
                        if res_ft_tipo_fix2 == "EMPATAPIERDE": return r_ in ("EMPATA","PIERDE")
                        return True
                    df_team_fix2 = df_team_fix2[df_team_fix2.apply(_cumple_ft_tipo_fix2, axis=1)]

                # --- EDGE LIVE: RESULTADO EN MINUTO X - FIX HT + 2ª PARTE ---
                if res_live_tipo_fix2!= "TODOS" and MIN_LIVE_FIX2 is not None:
                    def _strip_acc_l(s):
                        try:
                            return ''.join(c for c in unicodedata.normalize('NFKD', str(s)) if not unicodedata.combining(c))
                        except:
                            return str(s)
                    def _cumple_live_fix2(rr):
                        fid = str(rr.get('fixture_id','')).split('.')[0]
                        hn_ = normaliza(rr.get('HomeTeam','')); an_ = normaliza(rr.get('AwayTeam',''))
                        hn_c = _strip_acc_l(hn_); an_c = _strip_acc_l(an_)
                        norm_eq_c = _strip_acc_l(norm_eq_fix2)
                        try:
                            hg_ft = int(float(rr.get('FTHG',0) or 0)); ag_ft = int(float(rr.get('FTAG',0) or 0))
                            hthg = int(float(rr.get('HTHG',0) or 0)); htag = int(float(rr.get('HTAG',0) or 0))
                        except:
                            hg_ft=0; ag_ft=0; hthg=0; htag=0
                        evs = eventos_fix2.get(fid, [])
                        # cuenta goles 2ª parte hasta MIN
                        sh_total = (hg_ft - hthg) + (ag_ft - htag)
                        if sh_total <0: sh_total=0
                        sh_up_to = 0
                        hg_live = 0; ag_live = 0; cnt_match=0
                        for ev in evs:
                            m = ev.get('m',0)
                            if m <= 45 or m > MIN_LIVE_FIX2: 
                                if m <= MIN_LIVE_FIX2:
                                    # 1ª parte
                                    team_ev = _strip_acc_l(ev.get('team',''))
                                    tipo = ev.get('tipo','')
                                    if 'Missed' in tipo: continue
                                    if 'Own Goal' in tipo:
                                        if team_ev == hn_c: hg_live+=1; cnt_match+=1
                                        elif team_ev == an_c: ag_live+=1; cnt_match+=1
                                    else:
                                        if team_ev == hn_c: hg_live+=1; cnt_match+=1
                                        elif team_ev == an_c: ag_live+=1; cnt_match+=1
                                continue
                            # 2ª parte hasta MIN
                            sh_up_to += 1
                            team_ev = _strip_acc_l(ev.get('team',''))
                            tipo = ev.get('tipo','')
                            if 'Missed' in tipo: continue
                            # FIX OWN GOAL LIVE
                            es_local_raw_live = _equipo_es_local(team_ev, hn, an) if '_equipo_es_local' in locals() else (team_ev == hn_c)
                            is_home_live = es_local_raw_live
                            if is_home_live: hg_live+=1; cnt_match+=1
                            else: ag_live+=1; cnt_match+=1
                        # LOGICA HT
                        if MIN_LIVE_FIX2 <= 45:
                            # solo 1ª parte
                            if cnt_match==0:
                                hg_live = hthg if hthg+htag>0 else 0
                                ag_live = htag if hthg+htag>0 else 0
                        else:
                            # >45
                            if sh_up_to == 0:
                                hg_live = hthg; ag_live = htag
                            elif sh_up_to == sh_total and sh_total>0:
                                hg_live = hg_ft; ag_live = ag_ft
                            else:
                                # si hay goles parciales 2ª parte pero no tenemos match, usa HT + lo contado
                                if cnt_match==0 and sh_up_to>0:
                                    # no podemos saber equipo, fallback a FT si ya paso todo
                                    hg_live = hg_ft if sh_up_to==sh_total else hthg
                                    ag_live = ag_ft if sh_up_to==sh_total else htag
                        if norm_eq_c == hn_c:
                            r_ = "GANA" if hg_live > ag_live else "EMPATE" if hg_live == ag_live else "PIERDE"
                        elif norm_eq_c == an_c:
                            r_ = "GANA" if ag_live > hg_live else "EMPATE" if ag_live == hg_live else "PIERDE"
                        else:
                            return False
                        if res_live_tipo_fix2 == "EMPATE": return r_ == "EMPATE"
                        if res_live_tipo_fix2 == "GANA": return r_ == "GANA"
                        if res_live_tipo_fix2 == "PIERDE": return r_ == "PIERDE"
                        if res_live_tipo_fix2 == "EMPATEGANA": return r_ in ("EMPATE","GANA")
                        if res_live_tipo_fix2 == "EMPATEPIERDE": return r_ in ("EMPATE","PIERDE")
                        if res_live_tipo_fix2 == "GANAPIERDE": return r_ in ("GANA","PIERDE")
                        return True
                    df_team_fix2 = df_team_fix2[df_team_fix2.apply(_cumple_live_fix2, axis=1)]

                if df_team_fix2.empty:
                    # FIX BAYERN MÜNCHEN / ARSENAL - si parquet no trae equipo, usa base_partidos.csv
                    try:
                        import pathlib as _p
                        _pp = _p.Path("/mnt/data/base_partidos.csv")
                        _gp = _p.Path("/mnt/data/base_goles.csv")
                        if _pp.exists():
                            _df_csv = pd.read_csv(_pp, on_bad_lines='skip')
                            _df_csv['Date'] = pd.to_datetime(_df_csv['Date'], dayfirst=True, errors='coerce')
                            _norm = normaliza(nombre_eq_fix2)
                            _up = nombre_eq_fix2.upper().strip()
                            _df_try = _df_csv[(_df_csv['HomeTeam'].astype(str).str.upper().str.strip() == _up) | (_df_csv['AwayTeam'].astype(str).str.upper().str.strip() == _up)]
                            if not _df_try.empty:
                                _df_try = _df_try.copy()
                                _df_try['Jornada'] = _df_try.get('jornada_num','').astype(str).str.extract(r'(\d+)').astype(float).fillna(0).astype(int)
                                _df_try['fixture_id'] = _df_try.get('fixture_id', _df_try.index)
                                df_team_fix2 = _df_try
                                df_team_base_total_fix2 = _df_try.copy()
                                df_team_base_pred_fix2 = _df_try.copy()
                                # carga eventos de base_goles.csv para que filtre 25-45
                                if _gp.exists():
                                    try:
                                        _df_g = pd.read_csv(_gp, on_bad_lines='skip')
                                        _df_g['fid_str'] = _df_g['fixture_id'].astype(str).str.split('.').str[0]
                                        _df_g['m'] = pd.to_numeric(_df_g.get('minuto', 0), errors='coerce').fillna(0).astype(int)
                                        for fid, sub in _df_g.groupby('fid_str'):
                                            if fid not in eventos_fix2:
                                                eventos_fix2[fid] = [{'m': int(r.get('m', 0)), 'team': normaliza(r.get('equipo','')), 'tipo': str(r.get('tipo','')), 'goleador': str(r.get('goleador','')), 'asistente': str(r.get('asistente',''))} for _, r in sub.iterrows()]
                                    except:
                                        pass
                            else:
                                st.caption(f"{nombre_eq_fix2} - sin historial en base actual FIX2")
                                continue
                        else:
                            st.caption(f"{nombre_eq_fix2} - sin historial en base actual FIX2")
                            continue
                    except:
                        st.caption(f"{nombre_eq_fix2} - sin historial en base actual FIX2")
                        continue

                total_fix2 = len(df_team_base_total_fix2) if 'df_team_base_total_fix2' in locals() else len(df_team_fix2)
                # filt con MIN incluido
                if MIN_DESDE_PRED_FIX2 is not None or MIN_HASTA_PRED_FIX2 is not None:
                    def _tiene_min_eq(rr):
                        fid = str(rr.get('fixture_id','')).split('.')[0]
                        evs = eventos_fix2.get(fid, [])
                        if not evs:
                            try:
                                import pathlib as _pb
                                _gb = _pb.Path("/mnt/data/base_goles.csv")
                                if _gb.exists():
                                    _dfgb = pd.read_csv(_gb, on_bad_lines='skip')
                                    _dfgb['fid_str'] = _dfgb['fixture_id'].astype(str).str.split('.').str[0]
                                    _sub = _dfgb[_dfgb['fid_str']==fid]
                                    for _, _rg in _sub.iterrows():
                                        try:
                                            _ms = str(_rg.get('minuto','0')).replace("'", "")
                                            _mm = int(_ms.split('+')[0].split('.')[0]) if _ms else 0
                                        except:
                                            _mm = 0
                                        if 'Missed' in str(_rg.get('tipo','')): continue
                                        if MIN_DESDE_PRED_FIX2 is not None and _mm < MIN_DESDE_PRED_FIX2: continue
                                        if MIN_HASTA_PRED_FIX2 is not None and _mm > MIN_HASTA_PRED_FIX2: continue
                                        return True
                                    return False
                            except:
                                pass
                        for ev in evs:
                            if 'Missed' in ev.get('tipo',''): continue
                            mm = ev.get('m',-1)
                            if MIN_DESDE_PRED_FIX2 is not None and mm < MIN_DESDE_PRED_FIX2: continue
                            if MIN_HASTA_PRED_FIX2 is not None and mm > MIN_HASTA_PRED_FIX2: continue
                            return True
                        return False
                    df_filtrada_real_fix2 = df_team_fix2[df_team_fix2.apply(_tiene_min_eq, axis=1)] if not df_team_fix2.empty else df_team_fix2
                    filt_fix2 = len(df_filtrada_real_fix2)
                else:
                    df_filtrada_real_fix2 = df_team_fix2
                    filt_fix2 = len(df_team_fix2)

                # DESGLOSE LOCAL/VISITANTE FIX CON NORMALIZA - 100% = J_EQ
                try:
                    _mask_local_total = df_team_base_total_fix2['HomeTeam'].apply(lambda x: normaliza(str(x))==norm_eq_fix2)
                    local_total = int(_mask_local_total.sum())
                    visitante_total = total_fix2 - local_total
                    _mask_local_filt = df_filtrada_real_fix2['HomeTeam'].apply(lambda x: normaliza(str(x))==norm_eq_fix2) if not df_filtrada_real_fix2.empty else _mask_local_total[:0]
                    local_filt = int(_mask_local_filt.sum())
                    visitante_filt = filt_fix2 - local_filt
                    desglose = f" [L:{local_filt}/{local_total} V:{visitante_filt}/{visitante_total}]"
                except:
                    desglose = ""

                cabecera_txt = f"{nombre_eq_fix2.upper()} {filt_fix2}/{total_fix2} FIX2{desglose}"
                st.markdown(f"<div style='font-family:monospace;font-weight:900;background:#FFFFFF;color:#000;padding:2px 6px;margin:6px 0 2px 0;font-size:10px;border:1px solid #000'>{cabecera_txt}</div>", unsafe_allow_html=True)
                partidos_pred_copy_fix2.append(cabecera_txt)
                # --- GENERA RESUMEN L/V CON JORNADAS + RESULTADO FILTRADO CORREGIDO: 1P MUESTRA HT ---
                try:
                    def _es_filtro_1p():
                        try:
                            # Overs 1P
                            for o in (overs_sel_fix2 if 'overs_sel_fix2' in locals() else []):
                                if "1P" in str(o):
                                    return True
                            # Resultado 1ªP 0-0_1ªP etc
                            for r in (resultados_pred_sel_fix2 if 'resultados_pred_sel_fix2' in locals() else []):
                                if "_1ªP" in str(r):
                                    return True
                            # MIN DESDE/HASTA <=45
                            if MIN_DESDE_PRED_FIX2 is not None and MIN_DESDE_PRED_FIX2 <= 45:
                                return True
                            if MIN_HASTA_PRED_FIX2 is not None and MIN_HASTA_PRED_FIX2 <= 45:
                                return True
                            # Si Tipo Resultado 1P != TODOS, es filtro de 1P
                            if 'res_1p_tipo_fix2' in locals() and res_1p_tipo_fix2 != "TODOS":
                                return True
                        except:
                            pass
                        return False

                    def _es_filtro_2p():
                        try:
                            for o in (overs_sel_fix2 if 'overs_sel_fix2' in locals() else []):
                                if "2P" in str(o):
                                    return True
                            for r in (resultados_pred_sel_fix2 if 'resultados_pred_sel_fix2' in locals() else []):
                                if "_2ªP" in str(r):
                                    return True
                            if MIN_DESDE_PRED_FIX2 is not None and MIN_DESDE_PRED_FIX2 > 45:
                                return True
                        except:
                            pass
                        return False

                    es_filtro_1p_activo = _es_filtro_1p()
                    es_filtro_2p_activo = _es_filtro_2p() and not es_filtro_1p_activo

                    lista_loc_detalle = []
                    lista_vis_detalle = []

                    for _, rr in df_filtrada_real_fix2.iterrows():
                        try:
                            jn = int(rr.get('Jornada', 0))
                        except:
                            continue
                        es_loc = str(rr.get('HomeTeam','')).upper().strip() == eq_up_fix2
                        try:
                            hg = int(float(rr.get('FTHG',0) or 0)); ag = int(float(rr.get('FTAG',0) or 0))
                            hthg = int(float(rr.get('HTHG',0) or 0)); htag = int(float(rr.get('HTAG',0) or 0))
                        except:
                            hg=0; ag=0; hthg=0; htag=0

                        # LOGICA CORREGIDA: 1P>0.5=HT real, 2P>0.5=2P real
                        _is_1p = any("1P" in str(o) for o in (overs_sel_fix2 if 'overs_sel_fix2' in locals() else [])) or any("_1ªP" in str(r) for r in (resultados_pred_sel_fix2 if 'resultados_pred_sel_fix2' in locals() else []))
                        _is_2p = any("2P" in str(o) for o in (overs_sel_fix2 if 'overs_sel_fix2' in locals() else [])) or any("_2ªP" in str(r) for r in (resultados_pred_sel_fix2 if 'resultados_pred_sel_fix2' in locals() else []))
                        if _is_1p:
                            g_home = hthg
                            g_away = htag
                        elif _is_2p:
                            g_home = hg - hthg
                            g_away = ag - htag
                            if g_home < 0: g_home = 0
                            if g_away < 0: g_away = 0
                        else:
                            g_home = hg
                            g_away = ag

                        if es_loc:
                            g_fav = g_home
                            g_riv = g_away
                        else:
                            g_fav = g_away
                            g_riv = g_home

                        # Colores: fav VERDE #00c800, rival ROJO #ff2a2a, 0 negro
                        c_fav = "#00c800" if g_fav>0 else "#000000"
                        c_riv = "#ff2a2a" if g_riv>0 else "#000000"
                        fav_txt = f"<span style='color:{c_fav};font-weight:900'>{g_fav}</span>"
                        riv_txt = f"<span style='color:{c_riv};font-weight:900'>{g_riv}</span>"

                        if es_loc:
                            detalle = f"J{jn}({fav_txt}-{riv_txt})"
                            lista_loc_detalle.append((jn, detalle))
                        else:
                            detalle = f"J{jn}({riv_txt}-{fav_txt})"
                            lista_vis_detalle.append((jn, detalle))

                    # --- RESUMEN 3 LINEAS + RESULTADO + MINUTOS VERDE/ROJO + HUECOS _ ---
                    lista_loc_plain = []
                    lista_vis_plain = []
                    # dict filtrados por jornada para lookup rapido - USA J_EQ
                    filt_por_j = {}
                    for _, rr in df_filtrada_real_fix2.iterrows():
                        try:
                            jn = int(rr.get('J_EQ', rr.get('Jornada',0)))
                            hg = int(float(rr.get('FTHG',0) or 0))
                            ag = int(float(rr.get('FTAG',0) or 0))
                            es_loc = str(rr.get('HomeTeam','')).upper().strip() == eq_up_fix2
                            fid_r = str(rr.get('fixture_id','')).split('.')[0]
                            # --- rival + clasificacion FUZZY ---
                            opp_team = str(rr.get('AwayTeam','')).strip() if es_loc else str(rr.get('HomeTeam','')).strip()
                            opp_norm = normaliza(opp_team)
                            self_team = nombre_eq_fix2.strip()
                            self_norm = norm_eq_fix2
                            lg_norm_r = normaliza(rr.get('League',''))
                            def _get_clas_fuzzy(lg_n, team_n, j_list):
                                for jc in j_list:
                                    rec = clas_dict_fix2.get((lg_n, jc, team_n))
                                    if rec is not None:
                                        return rec
                                for (l_, n_, j_), rec_ in clas_dict_fix2.items():
                                    if l_ != lg_n: continue
                                    if j_ not in j_list: continue
                                    if team_n in n_ or n_ in team_n:
                                        return rec_
                                for (l_, n_, j_), rec_ in clas_dict_fix2.items():
                                    if l_ != lg_n: continue
                                    if team_n in n_ or n_ in team_n:
                                        return rec_
                                return None
                            try:
                                j_max_liga = clas_max_j_fix2.get(lg_norm_r, 0)
                                j_cands = [j_max_liga] if j_max_liga else [9999]
                                r_self = _get_clas_fuzzy(lg_norm_r, self_norm, j_cands)
                                r_opp = _get_clas_fuzzy(lg_norm_r, opp_norm, j_cands)
                                # POS AL LADO DEL NOMBRE: 13ºTEAM
                                def _pos_celeste(rec):
                                    return f"<span style='color:#00BFFF;font-size:9px;font-weight:900'>{int(rec.get('Pos',0))}º</span>" if rec is not None else ""
                                pos_self_html = _pos_celeste(r_self)
                                pos_opp_html = _pos_celeste(r_opp)
                                pts_self_html = ""
                                pts_opp_html = ""
                                if r_opp is not None:
                                    if es_loc:
                                        rival_txt = f" <span style='font-size:9px;font-weight:400'>{pos_self_html}<span style='color:#fff;font-weight:900'>{self_team}</span>{pts_self_html} <span style='color:#888'>vs</span> {pos_opp_html}<span style='color:#888'>{opp_team}</span>{pts_opp_html}</span>"
                                    else:
                                        rival_txt = f" <span style='font-size:9px;font-weight:400'>{pos_opp_html}<span style='color:#888'>{opp_team}</span>{pts_opp_html} <span style='color:#888'>vs</span> {pos_self_html}<span style='color:#fff;font-weight:900'>{self_team}</span>{pts_self_html}</span>"
                                else:
                                    if es_loc:
                                        rival_txt = f" <span style='font-size:9px;font-weight:400'>{pos_self_html}<span style='color:#fff;font-weight:900'>{self_team}</span> <span style='color:#888'>vs {opp_team}</span></span>"
                                    else:
                                        rival_txt = f" <span style='font-size:9px;font-weight:400'><span style='color:#888'>{opp_team} vs </span>{pos_self_html}<span style='color:#fff;font-weight:900'>{self_team}</span></span>"
                            except:
                                rival_txt = f" <span style='font-size:9px;font-weight:400'><span style='color:#888'>{opp_team} vs </span><span style='color:#fff;font-weight:900'>{self_team}</span></span>" if not es_loc else f" <span style='font-size:9px;font-weight:400'><span style='color:#fff;font-weight:900'>{self_team}</span><span style='color:#888'> vs {opp_team}</span></span>"

                            if es_loc:
                                _ch = "#00c800" if hg>0 else "#888"
                                _ca = "#ff2a2a" if ag>0 else "#888"
                                res_txt = f"[<span style='color:{_ch};font-weight:900'>{hg}</span>-<span style='color:{_ca};font-weight:900'>{ag}</span>]"
                                letra = "G" if hg>ag else "E" if hg==ag else "P"
                            else:
                                _ch = "#ff2a2a" if hg>0 else "#888"
                                _ca = "#00c800" if ag>0 else "#888"
                                res_txt = f"[<span style='color:{_ch};font-weight:900'>{hg}</span>-<span style='color:{_ca};font-weight:900'>{ag}</span>]"
                                letra = "G" if ag>hg else "E" if ag==hg else "P"
                            if letra == "G":
                                badge = "<span style='background:#00c800;color:#fff;padding:0 4px;border-radius:3px;font-size:9px;font-weight:900'>G</span>"
                            elif letra == "E":
                                badge = "<span style='background:#ffcc00;color:#000;padding:0 4px;border-radius:3px;font-size:9px;font-weight:900'>E</span>"
                            else:
                                badge = "<span style='background:#ff2a2a;color:#fff;padding:0 4px;border-radius:3px;font-size:9px;font-weight:900'>P</span>"
                                    # --- FILTRO GOLES PARTE PARA RESUMEN + HT REAL FIX ---
                            goles_parte_f = st.session_state.get("goles_parte_fix2", "Todo")
                            mins_1p = []
                            mins_2p = []
                            hthg_calc = 0
                            htag_calc = 0
                            for ev in sorted(eventos_fix2.get(fid_r, []), key=lambda x: x.get('m',0)):
                                if 'Missed' in ev.get('tipo',''): continue
                                mm = ev.get('m',-1)
                                # para HT calc cuenta todo <=45 sin filtro MIN
                                if mm <= 45:
                                    try:
                                        t = normaliza(ev.get('team',''))
                                        hn_tmp = normaliza(str(rr.get('HomeTeam','')))
                                        if t == hn_tmp:
                                            hthg_calc += 1
                                        else:
                                            htag_calc += 1
                                    except:
                                        pass
                                if MIN_DESDE_PRED_FIX2 is not None and mm < MIN_DESDE_PRED_FIX2: continue
                                if MIN_HASTA_PRED_FIX2 is not None and mm > MIN_HASTA_PRED_FIX2: continue
                                es_mio = (normaliza(ev.get('team','')) == norm_eq_fix2)
                                col = "#00c800" if es_mio else "#ff2a2a"
                                tag = f"<span style='color:{col};font-weight:900'>{mm}'</span>"
                                if mm <= 45:
                                    mins_1p.append(tag)
                                else:
                                    mins_2p.append(tag)
                            # HT real - si parquet trae 0-0 lo recalcula de goles
                            try:
                                _hthg_parq = int(float(rr.get('HTHG',0) or 0))
                                _htag_parq = int(float(rr.get('HTAG',0) or 0))
                            except:
                                _hthg_parq = 0; _htag_parq = 0
                            if _hthg_parq == 0 and _htag_parq == 0 and (hthg_calc+htag_calc)>0:
                                _hthg_fix = hthg_calc
                                _htag_fix = htag_calc
                            else:
                                _hthg_fix = _hthg_parq
                                _htag_fix = _htag_parq
                            if es_loc:
                                _c1 = "#D0D0D0" if _hthg_fix>0 else "#888"
                                _c2 = "#888"
                                _ht_txt = f"<span style='color:#888'>[</span><span style='color:{_c1};font-weight:900'>{_hthg_fix}</span><span style='color:#888'>-</span><span style='color:{_c2};font-weight:900'>{_htag_fix}</span><span style='color:#888'>]</span>"
                            else:
                                _c1 = "#888"
                                _c2 = "#D0D0D0" if _htag_fix>0 else "#888"
                                _ht_txt = f"<span style='color:#888'>[</span><span style='color:{_c1};font-weight:900'>{_hthg_fix}</span><span style='color:#888'>-</span><span style='color:{_c2};font-weight:900'>{_htag_fix}</span><span style='color:#888'>]</span>"
                            # HT GRIS SIEMPRE VISIBLE + FINAL COLOREADO SIEMPRE
                            if goles_parte_f == "1ªParte":
                                mins_txt = " ".join(mins_1p) if mins_1p else ""
                            elif goles_parte_f == "2ªParte":
                                mins_txt = " ".join(mins_2p) if mins_2p else ""
                            else:
                                if mins_1p and mins_2p:
                                    mins_txt = " ".join(mins_1p) + " <span style='color:#888'>|</span> " + " ".join(mins_2p)
                                elif mins_1p:
                                    mins_txt = " ".join(mins_1p)
                                elif mins_2p:
                                    mins_txt = " ".join(mins_2p)
                                else:
                                    mins_txt = ""
                            # res_txt ya es el FINAL coloreado, siempre se muestra
                            inner = f"<span style='font-size:9px'><span style='font-size:11px;font-weight:900'>{res_txt} {_ht_txt}</span>{rival_txt}</span><br><span style='display:inline-block;margin:2px 0 0 18px;font-size:11px;font-weight:900'>{mins_txt}</span>"
                            filt_por_j[jn] = (inner, es_loc, badge)
                            continue
                            
##########
                        except:
                            continue
                    # recorre TODAS las jornadas base para meter _ - FIX CON J_EQ
                    try:
                        jornadas_base = sorted(pd.to_numeric(df_team_base_total_fix2['J_EQ'], errors='coerce').dropna().unique().astype(int).tolist(), reverse=True)
                    except:
                        jornadas_base = sorted(filt_por_j.keys(), reverse=True)
                    for jn in jornadas_base:
                        j_tag = f"<span style='color:#A020F0;font-weight:900'>J{jn}</span>"
                        if jn in filt_por_j:
                            try:
                                inner, es_loc, badge = filt_por_j[jn]
                            except:
                                inner, es_loc = filt_por_j[jn]
                                badge = ""
                            if es_loc:
                                lista_loc_plain.append(f"<div style='margin:4px 0;padding:5px 6px;background:#000;border:1px solid #555;border-radius:6px'>{badge} {j_tag} {inner}</div>")
                            else:
                                lista_vis_plain.append(f"<div style='margin:4px 0;padding:5px 6px;background:#000;border:1px solid #555;border-radius:6px'>{badge} {j_tag} {inner}</div>")
                        else:
                            # HUECO - [E]J9([1-1][0-1]) + EQUIPO vs EQUIPO + PUNTOS - VERDE FILTRADO ROJO RIVAL 0 GRIS
                            try:
                                if 'J_EQ' in df_team_base_total_fix2.columns:
                                    _df_b = df_team_base_total_fix2[df_team_base_total_fix2['J_EQ']==jn]
                                    r_base = _df_b.iloc[0] if not _df_b.empty else df_team_base_total_fix2[df_team_base_total_fix2['Jornada']==jn].iloc[0]
                                else:
                                    r_base = df_team_base_total_fix2[df_team_base_total_fix2['Jornada']==jn].iloc[0]
                                es_loc_base = normaliza(str(r_base.get('HomeTeam',''))) == norm_eq_fix2
                                _h0 = str(r_base.get('HomeTeam','')).strip()
                                _a0 = str(r_base.get('AwayTeam','')).strip()
                                _lg0 = normaliza(r_base.get('League',''))
                                _j0_antes = int(jn) - 1
                                try:
                                    _hg = int(float(r_base.get('FTHG',0) or 0)); _ag = int(float(r_base.get('FTAG',0) or 0))
                                    _hthg = int(float(r_base.get('HTHG',0) or 0)); _htag = int(float(r_base.get('HTAG',0) or 0))
                                except:
                                    _hg=0; _ag=0; _hthg=0; _htag=0
                                if _hthg==0 and _htag==0:
                                    try:
                                        _fid_tmp = str(r_base.get('fixture_id','')).split('.')[0]
                                        _c1=0; _c2=0
                                        for _ev in eventos_fix2.get(_fid_tmp, []):
                                            if _ev.get('m',999) <=45 and 'Missed' not in _ev.get('tipo',''):
                                                _t = normaliza(_ev.get('team',''))
                                                if _t == normaliza(_h0):
                                                    _c1+=1
                                                else:
                                                    _c2+=1
                                        if _c1+_c2>0:
                                            _hthg=_c1; _htag=_c2
                                    except:
                                        pass
                                if es_loc_base:
                                    _letra = "G" if _hg>_ag else "E" if _hg==_ag else "P"
                                else:
                                    _letra = "G" if _ag>_hg else "E" if _ag==_hg else "P"
                                if _letra=="G":
                                    _badge = "<span style='background:#00c800;color:#fff;padding:0 4px;border-radius:3px;font-size:9px;font-weight:900'>G</span>"
                                elif _letra=="E":
                                    _badge = "<span style='background:#ffcc00;color:#000;padding:0 4px;border-radius:3px;font-size:9px;font-weight:900'>E</span>"
                                else:
                                    _badge = "<span style='background:#ff2a2a;color:#fff;padding:0 4px;border-radius:3px;font-size:9px;font-weight:900'>P</span>"
                                # COLORES FT - verde filtrado / rojo rival / 0 gris | HT - blanco filtrado / gris rival
                                if es_loc_base:
                                    _hg_c = f"<span style='color:#00c800;font-weight:900'>{_hg}</span>" if _hg>0 else f"<span style='color:#888;font-weight:900'>{_hg}</span>"
                                    _ag_c = f"<span style='color:#ff2a2a;font-weight:900'>{_ag}</span>" if _ag>0 else f"<span style='color:#888;font-weight:900'>{_ag}</span>"
                                    _hthg_c = f"<span style='color:#FFFFFF;font-weight:900'>{_hthg}</span>" if _hthg>0 else f"<span style='color:#888;font-weight:900'>{_hthg}</span>"
                                    _htag_c = f"<span style='color:#888;font-weight:900'>{_htag}</span>"
                                else:
                                    _hg_c = f"<span style='color:#ff2a2a;font-weight:900'>{_hg}</span>" if _hg>0 else f"<span style='color:#888;font-weight:900'>{_hg}</span>"
                                    _ag_c = f"<span style='color:#00c800;font-weight:900'>{_ag}</span>" if _ag>0 else f"<span style='color:#888;font-weight:900'>{_ag}</span>"
                                    _hthg_c = f"<span style='color:#888;font-weight:900'>{_hthg}</span>"
                                    _htag_c = f"<span style='color:#FFFFFF;font-weight:900'>{_htag}</span>" if _htag>0 else f"<span style='color:#888;font-weight:900'>{_htag}</span>"
                                def _get_res_hueco(j_, team_n):
                                    rec = clas_dict_fix2.get((_lg0, j_, team_n))
                                    if rec is not None:
                                        return rec
                                    for (l_, jj_, n_), rc_ in clas_dict_fix2.items():
                                        if l_ != _lg0: continue
                                        if jj_ != j_: continue
                                        if team_n in n_ or n_ in team_n:
                                            return rc_
                                    return None
                                rh = _get_res_hueco(_j0_antes, normaliza(_h0)) if _j0_antes>=1 else None
                                ra = _get_res_hueco(_j0_antes, normaliza(_a0)) if _j0_antes>=1 else None
                                if rh is None:
                                    rh = _get_res_hueco(clas_max_j_fix2.get(_lg0, int(jn)), normaliza(_h0))
                                if ra is None:
                                    ra = _get_res_hueco(clas_max_j_fix2.get(_lg0, int(jn)), normaliza(_a0))
                                if rh is not None and ra is not None:
                                    vs_txt = f" <span style='color:#888;font-size:9px;font-weight:400'>{_h0} {int(rh.get('Pos',0))}º vs {_a0} {int(ra.get('Pos',0))}º</span>"
                                else:
                                    vs_txt = f" <span style='color:#888;font-size:9px;font-weight:400'>{_h0} vs {_a0}</span>"
                                _txt = f"<div style='margin:4px 0;padding:5px 6px;background:#000;border:1px solid #555;border-radius:6px'>{_badge} {j_tag} <span style='font-size:9px'>[{_hg_c}-{_ag_c}] [{_hthg_c}-{_htag_c}]{vs_txt}</span></div>"
                            except:
                                es_loc_base = True
                                _txt = f"{j_tag}(<span style='color:#888;font-weight:900'>_</span>)"
                            if es_loc_base:
                                lista_loc_plain.append(_txt)
                            else:
                                lista_vis_plain.append(_txt)
                    j_loc_plain_txt = "".join(lista_loc_plain) if lista_loc_plain else "-"
                    j_vis_plain_txt = "".join(lista_vis_plain) if lista_vis_plain else "-"
                    try:
                        last_j_fix2 = int(pd.to_numeric(df_team_base_total_fix2['Jornada'], errors='coerce').max())
                    except:
                        last_j_fix2 = 0
                    # --- CLASIFICACION PROPIA 8º/20(14pts) ---
                    try:
                        _lg_norm_self = normaliza(df_team_base_total_fix2['League'].iloc[0]) if 'League' in df_team_base_total_fix2.columns and not df_team_base_total_fix2.empty else normaliza("")
                        _j_max_self = clas_max_j_fix2.get(_lg_norm_self, last_j_fix2)
                        _rec_self = clas_dict_fix2.get((_lg_norm_self, _j_max_self, norm_eq_fix2))
                        if _rec_self is None:
                            for (l_, j_, n_), rec_ in clas_dict_fix2.items():
                                if l_ != _lg_norm_self: continue
                                if j_ != _j_max_self: continue
                                if norm_eq_fix2 in n_ or n_ in norm_eq_fix2:
                                    _rec_self = rec_; break
                        if _rec_self is not None:
                            _pos_self = int(_rec_self.get('Pos',0)); _pts_self = int(_rec_self.get('Pts',0))
                            _tot_teams = len([k for k in clas_dict_fix2.keys() if k[0]==_lg_norm_self and k[1]==_j_max_self])
                            _clas_txt = f" <span style='color:#888;font-size:10px;font-weight:400'>{_pos_self}º/{_tot_teams}</span>"
                        else:
                            _clas_txt = ""
                    except:
                        _clas_txt = ""
                    linea_res = f"{nombre_eq_fix2.upper()}: {filt_fix2}/{total_fix2} <span style='color:#A020F0;font-weight:900'>_Jornada {last_j_fix2}</span>{_clas_txt}<br><br>L:{local_filt}/{local_total}<br>{j_loc_plain_txt}<br>V:{visitante_filt}/{visitante_total}<br>{j_vis_plain_txt}"
                    linea_res = linea_res.replace(" vs ", " <span style='color:#888'>vs</span> ")
                    lista_resumen_fix2.append(linea_res)
                except Exception as e:
                    try:
                        j_loc = []
                        j_vis = []
                        for _, rr in df_filtrada_real_fix2.iterrows():
                            jn = int(rr.get('Jornada', 0))
                            es_loc = str(rr.get('HomeTeam','')).upper().strip() == eq_up_fix2
                            if es_loc:
                                j_loc.append(f"J{jn}")
                            else:
                                j_vis.append(f"J{jn}")
                        j_loc_txt = ", ".join(sorted(j_loc, key=lambda x: int(x[1:]) if x[1:].isdigit() else 999)) if j_loc else "-"
                        j_vis_txt = ", ".join(sorted(j_vis, key=lambda x: int(x[1:]) if x[1:].isdigit() else 999)) if j_vis else "-"
                        linea_res = f"{nombre_eq_fix2.upper()}: {filt_fix2}/{total_fix2} | L:{local_filt}/{local_total} [{j_loc_txt}] | V:{visitante_filt}/{visitante_total} [{j_vis_txt}]"
                        lista_resumen_fix2.append(linea_res)
                    except:
                        pass
#########
                # FIX DEFINITIVO - Usa J_EQ no Jornada de liga
                if not df_team_base_pred_fix2.empty and 'J_EQ' in df_team_base_pred_fix2.columns:
                    df_team_base_pred_fix2 = df_team_base_pred_fix2.sort_values('J_EQ')
                    if not df_team_fix2.empty and 'J_EQ' in df_team_fix2.columns:
                        df_team_fix2 = df_team_fix2.sort_values('J_EQ')
                    max_j = int(pd.to_numeric(df_team_base_pred_fix2['J_EQ'], errors='coerce').max())
                    jornadas_fix2 = list(range(max_j, max(0, max_j-15), -1))
                else:
                    max_j = int(pd.to_numeric(df_team_base_pred_fix2['Jornada'], errors='coerce').max()) if not df_team_base_pred_fix2.empty else 0
                    jornadas_fix2 = list(range(max_j, max(0, max_j-15), -1))
                for j_fix2 in jornadas_fix2:
                    if 'J_EQ' in df_team_fix2.columns and 'J_EQ' in df_team_base_pred_fix2.columns:
                        d_j_ok_fix2 = df_team_fix2[df_team_fix2['J_EQ']==j_fix2]
                    else:
                        d_j_ok_fix2 = df_team_fix2[df_team_fix2['Jornada']==j_fix2].sort_values('Date', ascending=False) if not df_team_fix2.empty and 'Jornada' in df_team_fix2.columns else pd.DataFrame()
                    es_hueco_fix2 = d_j_ok_fix2.empty
                    # Para MIN DESDE/HASTA: si la jornada existe pero ningún partido tiene eventos en ese rango, también es hueco
                    if not es_hueco_fix2 and (MIN_DESDE_PRED_FIX2 is not None or MIN_HASTA_PRED_FIX2 is not None):
                        _tiene_algun_evento_jornada = False
                        for _, _rr_tmp in d_j_ok_fix2.iterrows():
                            _fid_tmp = str(_rr_tmp.get('fixture_id','')).split('.')[0]
                            _evs_tmp = eventos_fix2.get(_fid_tmp, [])
                            if not _evs_tmp:
                                try:
                                    import pathlib as _pb3
                                    _gb3 = _pb3.Path("/mnt/data/base_goles.csv")
                                    if _gb3.exists():
                                        _dfgb3 = pd.read_csv(_gb3, on_bad_lines='skip')
                                        _dfgb3['fid_str'] = _dfgb3['fixture_id'].astype(str).str.split('.').str[0]
                                        _sub3 = _dfgb3[_dfgb3['fid_str']==_fid_tmp]
                                        for _, _rg3 in _sub3.iterrows():
                                            try:
                                                _ms3 = str(_rg3.get('minuto','0')).replace("'", "")
                                                _mm3 = int(_ms3.split('+')[0].split('.')[0]) if _ms3 else 0
                                            except:
                                                _mm3 = 0
                                            if 'Missed' in str(_rg3.get('tipo','')): continue
                                            if MIN_DESDE_PRED_FIX2 is not None and _mm3 < MIN_DESDE_PRED_FIX2: continue
                                            if MIN_HASTA_PRED_FIX2 is not None and _mm3 > MIN_HASTA_PRED_FIX2: continue
                                            _tiene_algun_evento_jornada = True
                                            break
                                        if _tiene_algun_evento_jornada: break
                                        continue
                                except:
                                    pass
                            for _ev_tmp in _evs_tmp:
                                if 'Missed' in _ev_tmp.get('tipo',''): continue
                                _mm_tmp = _ev_tmp.get('m', -1)
                                if MIN_DESDE_PRED_FIX2 is not None and _mm_tmp < MIN_DESDE_PRED_FIX2: continue
                                if MIN_HASTA_PRED_FIX2 is not None and _mm_tmp > MIN_HASTA_PRED_FIX2: continue
                                _tiene_algun_evento_jornada = True
                                break
                            if _tiene_algun_evento_jornada: break
                        if not _tiene_algun_evento_jornada:
                            es_hueco_fix2 = True
                    if es_hueco_fix2:
                        try:
                            _base_j = df_team_base_pred_fix2[df_team_base_pred_fix2['Jornada']==j_fix2]
                            if not _base_j.empty:
                                _r0 = _base_j.iloc[0]
                                _h0 = str(_r0.get('HomeTeam','')).strip()
                                _a0 = str(_r0.get('AwayTeam','')).strip()
                                _lg0 = normaliza(_r0.get('League',''))
                                _j0_antes = int(j_fix2) - 1
                                try:
                                    _hg0 = int(float(_r0.get('FTHG',0) or 0)); _ag0 = int(float(_r0.get('FTAG',0) or 0))
                                    _hthg0 = int(float(_r0.get('HTHG',0) or 0)); _htag0 = int(float(_r0.get('HTAG',0) or 0))
                                except:
                                    _hg0=0; _ag0=0; _hthg0=0; _htag0=0
                                if _hthg0==0 and _htag0==0:
                                    try:
                                        _fid_tmp = str(_r0.get('fixture_id','')).split('.')[0]
                                        _c1=0; _c2=0
                                        for _ev in eventos_fix2.get(_fid_tmp, []):
                                            if _ev.get('m',999) <=45 and 'Missed' not in _ev.get('tipo',''):
                                                _t = normaliza(_ev.get('team',''))
                                                if _t == normaliza(_h0):
                                                    _c1+=1
                                                else:
                                                    _c2+=1
                                        if _c1+_c2>0:
                                            _hthg0=_c1; _htag0=_c2
                                    except:
                                        pass
                                _es_loc_hueco = (normaliza(_h0) == norm_eq_fix2)
                                if _es_loc_hueco:
                                    _letra0 = "G" if _hg0>_ag0 else "E" if _hg0==_ag0 else "P"
                                    _hg0_c = f"<span style='color:#00c800;font-weight:900'>{_hg0}</span>" if _hg0>0 else f"<span style='color:#888;font-weight:900'>{_hg0}</span>"
                                    _ag0_c = f"<span style='color:#ff2a2a;font-weight:900'>{_ag0}</span>" if _ag0>0 else f"<span style='color:#888;font-weight:900'>{_ag0}</span>"
                                    _hthg0_c = f"<span style='color:#FFFFFF;font-weight:900'>{_hthg0}</span>" if _hthg0>0 else f"<span style='color:#888;font-weight:900'>{_hthg0}</span>"
                                    _htag0_c = f"<span style='color:#888;font-weight:900'>{_htag0}</span>"
                                else:
                                    _letra0 = "G" if _ag0>_hg0 else "E" if _ag0==_hg0 else "P"
                                    _hg0_c = f"<span style='color:#ff2a2a;font-weight:900'>{_hg0}</span>" if _hg0>0 else f"<span style='color:#888;font-weight:900'>{_hg0}</span>"
                                    _ag0_c = f"<span style='color:#00c800;font-weight:900'>{_ag0}</span>" if _ag0>0 else f"<span style='color:#888;font-weight:900'>{_ag0}</span>"
                                    _hthg0_c = f"<span style='color:#888;font-weight:900'>{_hthg0}</span>"
                                    _htag0_c = f"<span style='color:#FFFFFF;font-weight:900'>{_htag0}</span>" if _htag0>0 else f"<span style='color:#888;font-weight:900'>{_htag0}</span>"
                                if _letra0=="G":
                                    _badge0 = "<span style='background:#00c800;color:#fff;padding:0 4px;border-radius:3px;font-size:9px;font-weight:900'>G</span>"
                                elif _letra0=="E":
                                    _badge0 = "<span style='background:#ffcc00;color:#000;padding:0 4px;border-radius:3px;font-size:9px;font-weight:900'>E</span>"
                                else:
                                    _badge0 = "<span style='background:#ff2a2a;color:#fff;padding:0 4px;border-radius:3px;font-size:9px;font-weight:900'>P</span>"
                                def _get_hueco(j_, team_n):
                                    rec = clas_dict_fix2.get((_lg0, j_, team_n))
                                    if rec is not None:
                                        return rec
                                    for (l_, jj_, n_), rc_ in clas_dict_fix2.items():
                                        if l_ != _lg0: continue
                                        if jj_ != j_: continue
                                        if team_n in n_ or n_ in team_n:
                                            return rc_
                                    return None
                                rh = _get_hueco(_j0_antes, normaliza(_h0)) if _j0_antes>=1 else None
                                ra = _get_hueco(_j0_antes, normaliza(_a0)) if _j0_antes>=1 else None
                                if rh is None:
                                    rh = _get_hueco(clas_max_j_fix2.get(_lg0, int(j_fix2)), normaliza(_h0))
                                if ra is None:
                                    ra = _get_hueco(clas_max_j_fix2.get(_lg0, int(j_fix2)), normaliza(_a0))
                                if rh is not None and ra is not None:
                                    txt_hueco = f"{_badge0})J{int(j_fix2)}([{_hg0_c}-{_ag0_c}] [{_hthg0_c}-{_htag0_c}]) <span style='color:#00BFFF;font-weight:900'>{int(rh.get('Pos',0))}º</span>{_h0} <span style='color:#888'>({int(rh.get('Pts',0))}pts)</span> vs <span style='color:#00BFFF;font-weight:900'>{int(ra.get('Pos',0))}º</span>{_a0} <span style='color:#888'>({int(ra.get('Pts',0))}pts)</span>"
                                else:
                                    txt_hueco = f"{_badge0})J{int(j_fix2)}([{_hg0_c}-{_ag0_c}] [{_hthg0_c}-{_htag0_c}]) {_h0} vs {_a0}"
                            else:
                                txt_hueco = f"J{int(j_fix2)} sin datos"
                        except:
                            txt_hueco = f"J{int(j_fix2)} sin datos"
                        partidos_pred_copy_fix2.append(f"{txt_hueco} (NO CUMPLE)")
                        st.markdown(f"<div style='font-family:monospace; text-align:center; padding:5px; max-width:480px; margin:2px auto; background:#0a0a0a; border-radius:6px; border:1px dashed #555;'><div style='color:#888; font-weight:700; font-size:11px;'>{txt_hueco}</div></div><div style='height:2.5px;background:#333;margin:4px auto 10px auto; max-width:480px;'></div>", unsafe_allow_html=True)
                        continue
                    d_j_fix2 = d_j_ok_fix2
                    html_lineas_fix2 = ""
                    for _, r in d_j_fix2.iterrows():
                        fid = str(r.get('fixture_id','')).split('.')[0]
                        if MIN_DESDE_PRED_FIX2 is not None or MIN_HASTA_PRED_FIX2 is not None:
                            _tiene = False
                            for _ev in eventos_fix2.get(fid, []):
                                if 'Missed' in _ev.get('tipo',''): continue
                                _mm = _ev.get('m', -1)
                                if MIN_DESDE_PRED_FIX2 is not None and _mm < MIN_DESDE_PRED_FIX2: continue
                                if MIN_HASTA_PRED_FIX2 is not None and _mm > MIN_HASTA_PRED_FIX2: continue
                                _tiene = True
                                break
                            if not _tiene:
                                continue
                        h = str(r.get('HomeTeam','')).strip(); a = str(r.get('AwayTeam','')).strip()
                        try: hg = int(float(r.get('FTHG',0))); ag = int(float(r.get('FTAG',0)))
                        except: hg=0; ag=0
                        h_norm_r = normaliza(h); a_norm_r = normaliza(a)
                        if norm_eq_fix2 == h_norm_r: col_main = "#0f8105" if hg>ag else "#f31818" if hg<ag else "#DAA520"
                        elif norm_eq_fix2 == a_norm_r: col_main = "#0f8105" if ag>hg else "#f31818" if ag<hg else "#DAA520"
                        else: col_main = "#000"
                        hn = h_norm_r; an = a_norm_r
                        try: hthg = int(float(r.get('HTHG',0) or 0)); htag = int(float(r.get('HTAG',0) or 0))
                        except: hthg=0; htag=0

                        # --- COLOR HT ---
                        try:
                            _nf_clean_fix2 = str(norm_eq_fix2).upper().strip()
                            _h_clean_fix2 = str(h_norm_r).upper().strip()
                            _a_clean_fix2 = str(a_norm_r).upper().strip()
                            _is_home_fix2 = _nf_clean_fix2 == _h_clean_fix2
                            _is_away_fix2 = _nf_clean_fix2 == _a_clean_fix2
                        except:
                            _is_home_fix2 = (norm_eq_fix2 == hn)
                            _is_away_fix2 = (norm_eq_fix2 == an)
                        if _is_home_fix2:
                            if hthg > htag: col_ht = "#0f8105"
                            elif hthg < htag: col_ht = "#f31818"
                            else: col_ht = "#DAA520"
                        elif _is_away_fix2:
                            if htag > hthg: col_ht = "#0f8105"
                            elif htag < hthg: col_ht = "#f31818"
                            else: col_ht = "#DAA520"
                        else:
                            col_ht = "#0A2342"

                        # --- G/E/P ---
                        def res_eq_pred_fix2(gf, gc): return "G" if gf>gc else "E" if gf==gc else "P"
                        if norm_eq_fix2 == hn: r1 = res_eq_pred_fix2(hthg, htag); rF = res_eq_pred_fix2(hg, ag)
                        elif norm_eq_fix2 == an: r1 = res_eq_pred_fix2(htag, hthg); rF = res_eq_pred_fix2(ag, hg)
                        else: r1="E"; rF="E"
                        estado = f"{r1}/{rF}"

                        # --- NOMBRES con pastilla blanca para seleccionado (mismo siempre) ---
                        EMOJI_SEL = "⚽"
                        EMOJI_RIVAL = "⚽"
                        if norm_eq_fix2 == h_norm_r:
                            h_txt = f"<span style='background:#FFFFFF;color:#000;padding:2px 8px;border-radius:5px;font-weight:900;'>{h}</span>"
                            a_txt = f"<span style='color:#aaaaaa;font-weight:700'>{a}</span>"
                            emoji_home = EMOJI_SEL
                            emoji_away = EMOJI_RIVAL
                        elif norm_eq_fix2 == a_norm_r:
                            h_txt = f"<span style='color:#aaaaaa;font-weight:700'>{h}</span>"
                            a_txt = f"<span style='background:#FFFFFF;color:#000;padding:2px 8px;border-radius:5px;font-weight:900;'>{a}</span>"
                            emoji_home = EMOJI_RIVAL
                            emoji_away = EMOJI_SEL
                        else:
                            h_txt = f"<span style='color:#ffffff'>{h}</span>"
                            a_txt = f"<span style='color:#ffffff'>{a}</span>"
                            emoji_home = EMOJI_RIVAL
                            emoji_away = EMOJI_SEL

                        # --- FT / HT con colores verde fav / rojo rival ---
                        if norm_eq_fix2 == h_norm_r:
                            hg_c = f"<span style='color:#00c800;font-weight:900'>{hg}</span>" if hg>0 else f"<span style='color:#888;font-weight:900'>{hg}</span>"
                            ag_c = f"<span style='color:#ff2a2a;font-weight:900'>{ag}</span>" if ag>0 else f"<span style='color:#888;font-weight:900'>{ag}</span>"
                            ft_txt = f"[{hg_c}-{ag_c}]"
                        elif norm_eq_fix2 == a_norm_r:
                            hg_c = f"<span style='color:#ff2a2a;font-weight:900'>{hg}</span>" if hg>0 else f"<span style='color:#888;font-weight:900'>{hg}</span>"
                            ag_c = f"<span style='color:#00c800;font-weight:900'>{ag}</span>" if ag>0 else f"<span style='color:#888;font-weight:900'>{ag}</span>"
                            ft_txt = f"[{hg_c}-{ag_c}]"
                        else:
                            ft_txt = f"[{hg}-{ag}]"
                        ht_inner = f"{hthg}-{htag}"
                        ht_str = f"[{ht_inner}]"
                        ht_html_badge = f"<span style='color:#fff;font-weight:900;background:{col_ht};border-radius:3px;padding:0 4px 2px 4px;margin:0 3px'>{ht_str}</span>"

                        # --- GOLES AGRUPADOS FIX OWN GOAL 2-0 -> 3-0 ---
                        filtro_act = (MIN_DESDE_PRED_FIX2 is not None or MIN_HASTA_PRED_FIX2 is not None)
                        evs_sorted_fix2 = sorted(eventos_fix2.get(fid, []), key=lambda x: x['m'])

                        def _equipo_es_local(team_str, home_norm, away_norm):
                            try:
                                t = normaliza(team_str)
                                h = normaliza(home_norm)
                                a = normaliza(away_norm)
                                if t == h: return True
                                if t == a: return False
                                if h and (h in t or t in h): return True
                                if a and (a in t or t in a): return False
                            except:
                                pass
                            tu = str(team_str).upper().strip()
                            hu = str(home_norm).upper().strip()
                            au = str(away_norm).upper().strip()
                            if tu == hu or hu in tu or tu in hu: return True
                            if tu == au or au in tu or tu in au: return False
                            return False

                        def _agrupa_fix2_con_score(evs, sh=0, sa=0):
                            grupos=[]; last=None; cur=[]; h=sh; a=sa; lh=sh; la=sa
                            for ev in evs:
                                if 'Missed' in ev.get('tipo',''): continue
                                m=ev.get('m',-1); team_ev=str(ev.get('team','')).strip(); tipo=str(ev.get('tipo',''))
                                es_local_raw = _equipo_es_local(team_ev, hn, an)
                                is_home = es_local_raw
                                if is_home: h+=1
                                else: a+=1
                                if last is not None and is_home != last and cur:
                                    grupos.append((cur, lh, la)); cur=[]
                                cur.append(m); last=is_home; lh=h; la=a
                            if cur: grupos.append((cur, lh, la))
                            return grupos

                        def _agrupa_fix2_con_score_sub(evs, sh=0, sa=0):
                            grupos=[]; h=sh; a=sa
                            for ev in evs:
                                m=ev.get('m',-1); team_ev=str(ev.get('team','')).strip(); tipo=str(ev.get('tipo',''))
                                es_local_raw = _equipo_es_local(team_ev, hn, an)
                                is_home_scoring = es_local_raw
                                if 'Own Goal' in tipo:
                                    is_home_scoring = not es_local_raw
                                if 'Missed Penalty' in tipo:
                                    grupos.append(([(m, tipo)], h, a, is_home_scoring)); continue
                                if is_home_scoring: h+=1
                                else: a+=1
                                grupos.append(([(m, tipo)], h, a, is_home_scoring))
                            return grupos

                        evs_1p_fix2 = [e for e in evs_sorted_fix2 if e.get('m',0) <= 45]
                        evs_2p_fix2 = [e for e in evs_sorted_fix2 if e.get('m',0) > 45]
                        g1_data = _agrupa_fix2_con_score(evs_1p_fix2, 0, 0)
                        if g1_data: g1_data[-1] = (g1_data[-1][0], hthg, htag)
                        g2_data = _agrupa_fix2_con_score(evs_2p_fix2, hthg, htag)
                        if g2_data: g2_data[-1] = (g2_data[-1][0], hg, ag)

                        try:
                            _fecha_dt_fix2 = pd.to_datetime(r.get('Date'), dayfirst=True, errors='coerce')
                            _fecha_str_fix2 = _fecha_dt_fix2.strftime("%d/%m/%Y") if pd.notna(_fecha_dt_fix2) else ""
                        except:
                            _fecha_str_fix2 = ""

                        g1_data = _agrupa_fix2_con_score_sub(evs_1p_fix2, 0, 0)
                        g2_data = _agrupa_fix2_con_score_sub(evs_2p_fix2, hthg, htag)

                        def _fmt_mins(min_tipo_list):
                            out=[]
                            for mm, tp in min_tipo_list:
                                if 'Own Goal' in tp: out.append(f"(pp) {mm}'")
                                elif 'Missed Penalty' in tp: out.append(f"(x) {mm}'")
                                elif 'Penalty' in tp: out.append(f"(p) {mm}'")
                                else: out.append(f"{mm}'")
                            return "  ".join(out)
                        goles_parte_fix2 = st.session_state.get("goles_parte_fix2", "Todo")
                        mostrar_1p = goles_parte_fix2 in ("Todo","1ªParte")
                        mostrar_2p = goles_parte_fix2 in ("Todo","2ªParte")
                        filtro_act_fix2 = (MIN_DESDE_PRED_FIX2 is not None or MIN_HASTA_PRED_FIX2 is not None)
                        es_local_j = (norm_eq_fix2 == h_norm_r)
                        ###########FONDO LOCAL VISITANTE
                        bg_j = "#131314C4" if es_local_j else "#133562cc"
                        # --- CUOTAS EN LINEA J | P/P ---
                        try:
                            def _get_odd_j(rw, keys):
                                for k in keys:
                                    if k in rw and pd.notna(rw.get(k)):
                                        try:
                                            v=float(rw.get(k))
                                            if v>1: return v
                                        except: pass
                                return None
                            _oh = _get_odd_j(r, ['odd_home','B365H','1','Odd_H','HomeOdd'])
                            _od = _get_odd_j(r, ['odd_draw','B365D','X','Odd_D','DrawOdd'])
                            _oa = _get_odd_j(r, ['odd_away','B365A','2','Odd_A','AwayOdd'])
                            if _oh or _od or _oa:
                                _gan = 'H' if hg>ag else 'A' if ag>hg else 'D'
                                def _fmt_j(v, is_win):
                                    if v is None: return "<span style='color:#666'>-</span>"
                                    sz = "12px" if is_win else "10px"
                                    bg = "#fff" if is_win else "transparent"
                                    col = "#000" if is_win else "#aaa"
                                    wt = "900" if is_win else "700"
                                    br = "1px solid #000" if is_win else "none"
                                    return f"<span style='font-size:{sz}; background:{bg}; color:{col}; font-weight:{wt}; padding:1px 4px; border-radius:3px; border:{br};'>{v:.2f}</span>"
                                _cuotas_j = f" | {_fmt_j(_oh, _gan=='H')} {_fmt_j(_od, _gan=='D')} {_fmt_j(_oa, _gan=='A')}"
                            else:
                                _cuotas_j = ""
                        except:
                            _cuotas_j = ""
                        html = f"<div style='font-family:monospace; text-align:center; padding:6px 4px 4px 4px; max-width:480px; margin:0 auto; line-height:1.2; background:{bg_j}; border-radius:8px; border:2.5px solid #FFFFFF;'>"
                        html += f"<div style='font-weight:900; color:#fff; font-size:10px; line-height:1.1; margin:0 0 3px 0;'>J{int(j_fix2)} | <span style='background:{col_main};color:#fff;padding:3px 8px;border-radius:4px;font-size:14px;'>{estado}</span> <span style='color:#aaa;'>({_fecha_str_fix2})</span>{_cuotas_j}</div>"
                        # --- CLASIFICACION ENCIMA DE EQUIPO VS EQUIPO ---
                        try:
                            lg_norm = normaliza(r.get('League',''))
                            j_act = int(j_fix2)
                            j_antes = j_act - 1
                            j_max = clas_max_j_fix2.get(lg_norm, j_act)
                            def _get(j, team_norm):
                                return clas_dict_fix2.get((lg_norm, j, team_norm))
                            rh_antes = _get(j_antes, h_norm_r) if j_antes>=1 else None
                            ra_antes = _get(j_antes, a_norm_r) if j_antes>=1 else None
                            rh_act = _get(j_max, h_norm_r)
                            ra_act = _get(j_max, a_norm_r)
                            txt_actual = ""
                            txt_antes = ""
                            if rh_act is not None and ra_act is not None:
                                txt_actual = f"({int(rh_act.get('Pts',0))}pts){int(rh_act.get('Pos',0))}º vs {int(ra_act.get('Pos',0))}º({int(ra_act.get('Pts',0))}pts) actual"
                            if rh_antes is not None and ra_antes is not None:
                                txt_antes = f"({int(rh_antes.get('Pts',0))}pts){int(rh_antes.get('Pos',0))}º vs {int(ra_antes.get('Pos',0))}º({int(ra_antes.get('Pts',0))}pts) antes"
                            if txt_actual:
                                html += f"<div style='font-size:10px; color:#fff; text-align:center; margin:2px 0 4px 0;'><span style='background:#000; padding:1px 5px; border-radius:3px;'>{txt_actual}</span></div>"
                        except:
                            pass
                        html += f"<div style='font-weight:900; font-size:19px; line-height:1.35; margin:0; text-align:center; display:flex; justify-content:center; align-items:center; gap:8px; flex-wrap:wrap;'>{h_txt} {ft_txt} {a_txt}</div>"
                        ####
                        if norm_eq_fix2 == h_norm_r:
                            hthg_c = f"<span style='color:#FFFFFF;font-weight:900'>{hthg}</span>" if hthg>0 else f"<span style='color:#888;font-weight:900'>{hthg}</span>"
                            htag_c = f"<span style='color:#888;font-weight:900'>{htag}</span>"
                            ht_colored = f"{hthg_c}-{htag_c}"
                        elif norm_eq_fix2 == a_norm_r:
                            hthg_c = f"<span style='color:#888;font-weight:900'>{hthg}</span>"
                            htag_c = f"<span style='color:#FFFFFF;font-weight:900'>{htag}</span>" if htag>0 else f"<span style='color:#888;font-weight:900'>{htag}</span>"
                            ht_colored = f"{hthg_c}-{htag_c}"
                        else:
                            ht_colored = f"{hthg}-{htag}"
                        html += f"<div style='margin-top:3px; font-size:12px; color:#fff; line-height:1.2;'>(1ª parte {ht_colored})</div>"
                        if mostrar_1p:
                            if not g1_data:
                                html += f"<div style='font-size:10px; color:#888; text-align:center;'>—</div>"
                            else:
                                for mins_tipo, sh, sa, is_home in g1_data:
                                    for mm, tp in mins_tipo:
                                        if 'Own Goal' in tp: base = f"(pp) {mm}'"
                                        elif 'Missed Penalty' in tp: base = f"(x) {mm}'"
                                        elif 'Penalty' in tp: base = f"(p) {mm}'"
                                        else: base = f"{mm}'"
                                        emoji_gol = EMOJI_SEL if (is_home and hn==norm_eq_fix2) or (not is_home and an==norm_eq_fix2) else EMOJI_RIVAL
                                        es_fav_min = (is_home and hn==norm_eq_fix2) or (not is_home and an==norm_eq_fix2)
                                        color_min = "#00ff00" if es_fav_min else "#ff4444"
                                        txt_min = f"{base}"
                                        en_rango = (MIN_DESDE_PRED_FIX2 is None or mm >= MIN_DESDE_PRED_FIX2) and (MIN_HASTA_PRED_FIX2 is None or mm <= MIN_HASTA_PRED_FIX2)
                                        if '(x)' not in base:
                                            if filtro_act_fix2 and en_rango:
                                                txt_min = f"<span style='font-weight:900; color:{color_min}; background:#444; border-radius:3px; padding:1px 4px;'>{txt_min}</span>"
                                            else:
                                                txt_min = f"<span style='font-weight:900; color:{color_min};'>{txt_min}</span>"
                                        is_missed = 'Missed' in tp
                                        if is_missed: continue
                                        # --- MARCADOR VERDE FAVORABLE / ROJO RIVAL ---
                                        es_fav = (is_home and hn==norm_eq_fix2) or (not is_home and an==norm_eq_fix2)
                                        if es_fav:
                                            score_txt = f"<span style='color:#00ff00;font-weight:900'>{sh}</span><span style='color:#fff'>-{sa}</span>" if is_home else f"<span style='color:#fff'>{sh}-</span><span style='color:#00ff00;font-weight:900'>{sa}</span>"
                                        else:
                                            score_txt = f"<span style='color:#ff4444;font-weight:900'>{sh}</span><span style='color:#fff'>-{sa}</span>" if is_home else f"<span style='color:#fff'>{sh}-</span><span style='color:#ff4444;font-weight:900'>{sa}</span>"
                                        # NUEVO - busca goleador de ese minuto
                                        fid_tmp = str(r.get('fixture_id','')).split('.')[0] if 'r' in locals() else fid
                                        gol_info = ""
                                        for ev_tmp in eventos_fix2.get(fid_tmp, []):
                                            if ev_tmp.get('m', -1) == mm:
                                                g = ev_tmp.get('goleador','').strip()
                                                a_s = ev_tmp.get('asistente','').strip()
                                                if g and g.lower() not in ["nan",""]:
                                                    if a_s and a_s.lower() not in ["nan",""]:
                                                        gol_info = f"<div style='font-size:13px;color:#fff;margin-top:2px;font-weight:700'>{g} <span style='color:#bbb'>(ast: {a_s})</span></div>"
                                                    else:
                                                        gol_info = f"<div style='font-size:13px;color:#fff;margin-top:2px;font-weight:700'>{g}</div>"
                                                break
                                        if is_home:
                                            html += f"<div style='text-align:center; line-height:1.3; margin:4px 0;'><span style='display:inline-block; width:340px; max-width:92vw; text-align:left; font-size:14px; color:#fff; font-weight:700; transform:translateX(-20px); word-break:break-word; white-space:normal;'>{txt_min} {score_txt} {emoji_gol}{gol_info}</span></div>"
                                        else:
                                            html += f"<div style='text-align:center; line-height:1.3; margin:4px 0;'><span style='display:inline-block; width:340px; max-width:92vw; text-align:right; font-size:14px; color:#fff; font-weight:700; transform:translateX(20px); word-break:break-word; white-space:normal;'>{emoji_gol} {score_txt} {txt_min}{gol_info}</span></div>"
                        if mostrar_2p:
                            html += f"<div style='margin:6px auto 4px auto; font-size:9px; letter-spacing:2px; color:#aaa; text-align:center; line-height:1;'>___________________2ª________________</div>"
                            if not g2_data:
                                html += f"<div style='font-size:10px; color:#888; text-align:center;'>—</div>"
                            else:
                                for mins_tipo, sh, sa, is_home in g2_data:
                                    for mm, tp in mins_tipo:
                                        if 'Missed' in tp: continue
                                        if 'Own Goal' in tp: base = f"(pp) {mm}'"
                                        elif 'Missed Penalty' in tp: base = f"(x) {mm}'"
                                        elif 'Penalty' in tp: base = f"(p) {mm}'"
                                        else: base = f"{mm}'"
                                        emoji_gol = EMOJI_SEL if (is_home and hn==norm_eq_fix2) or (not is_home and an==norm_eq_fix2) else EMOJI_RIVAL
                                        es_fav_min2 = (is_home and hn==norm_eq_fix2) or (not is_home and an==norm_eq_fix2)
                                        color_min2 = "#00ff00" if es_fav_min2 else "#ff4444"
                                        txt_min = f"{base}"
                                        if filtro_act_fix2 and (MIN_DESDE_PRED_FIX2 is None or mm >= MIN_DESDE_PRED_FIX2) and (MIN_HASTA_PRED_FIX2 is None or mm <= MIN_HASTA_PRED_FIX2):
                                            txt_min = f"<span style='font-weight:900; color:{color_min2}; background:#444; border-radius:3px; padding:1px 4px;'>{txt_min}</span>"
                                        else:
                                            txt_min = f"<span style='font-weight:900; color:{color_min2};'>{txt_min}</span>"
                                        gol_txt = ""
                                        for evb in eventos_fix2.get(fid, []):
                                            if evb.get('m', -1) == mm:
                                                g = evb.get('goleador','').strip()
                                                a_s = evb.get('asistente','').strip()
                                                if g.lower() not in ["","nan","none"]:
                                                    gol_txt = g if not a_s or a_s.lower() in ["","nan","none"] else f"{g} ({a_s})"
                                                break
                                        if st.session_state.get("ver_goleadores_fix2","ON") == "OFF":
                                            gol_html = ""
                                        else:
                                            gol_html = f"<div style='font-size:13px;color:#fff;margin-top:2px;font-weight:700'>{gol_txt}</div>" if gol_txt else ""
                                        if is_home:
                                            es_fav2 = (is_home and hn==norm_eq_fix2) or (not is_home and an==norm_eq_fix2)
                                            if es_fav2:
                                                score_2p = f"<span style='color:#00ff00;font-weight:900'>{sh}</span><span style='color:#fff'>-{sa}</span>" if is_home else f"<span style='color:#fff'>{sh}-</span><span style='color:#00ff00;font-weight:900'>{sa}</span>"
                                            else:
                                                score_2p = f"<span style='color:#ff4444;font-weight:900'>{sh}</span><span style='color:#fff'>-{sa}</span>" if is_home else f"<span style='color:#fff'>{sh}-</span><span style='color:#ff4444;font-weight:900'>{sa}</span>"
                                            html += f"<div style='text-align:center; line-height:1.3; margin:2px 0;'><span style='display:inline-block; width:360px; max-width:92vw; text-align:left; font-size:14px; color:#fff; font-weight:700; transform:translateX(-20px); word-break:break-word; white-space:normal; line-height:1.2;'>{txt_min} {score_2p} {emoji_gol}{gol_html}</span></div>"
                                        else:
                                            es_fav2_r = (is_home and hn==norm_eq_fix2) or (not is_home and an==norm_eq_fix2)
                                            if es_fav2_r:
                                                score_2p_r = f"<span style='color:#fff'>{sh}-</span><span style='color:#00ff00;font-weight:900'>{sa}</span>"
                                            else:
                                                score_2p_r = f"<span style='color:#fff'>{sh}-</span><span style='color:#ff4444;font-weight:900'>{sa}</span>"
                                            html += f"<div style='text-align:center; line-height:1.3; margin:2px 0;'><span style='display:inline-block; width:220px; text-align:right; font-size:14px; color:#fff; font-weight:700; transform:translateX(85px);'>{emoji_gol} {score_2p_r} {txt_min}{gol_html}</span></div>"
                        html += f"</div><div style='height:2.5px;background:#0A2342;margin:4px auto 10px auto; max-width:480px;'></div>"

                        html_lineas_fix2 += html
                        m1 = []; m2 = []
                        for evc in sorted(eventos_fix2.get(fid, []), key=lambda x: x['m']):
                            if MIN_DESDE_PRED_FIX2 is not None and evc.get('m',-1) < MIN_DESDE_PRED_FIX2: continue
                            if MIN_HASTA_PRED_FIX2 is not None and evc.get('m',-1) > MIN_HASTA_PRED_FIX2: continue
                            if 'Missed' in evc.get('tipo',''): continue
                            mm = evc.get('m',0)
                            if mm <= 45: m1.append(f"{mm}'")
                            else: m2.append(f"{mm}'")
                        goles_parte_copy = st.session_state.get("goles_parte_fix2", "Todo")
                        if goles_parte_copy == "1ªParte":
                            m2 = []
                        elif goles_parte_copy == "2ªParte":
                            m1 = []
                        if m1 and m2: mins_txt = " ".join(m1) + f"{ht_str} " + " ".join(m2)
                        elif m1: mins_txt = " ".join(m1) + f"{ht_str}"
                        elif m2: mins_txt = f"{ht_str} " + " ".join(m2)
                        else: mins_txt = f"{ht_str}"
                        ht_clean = f"[{hthg}-{htag}]"
                        ft_clean = f"{hg}-{ag}"
                        if m1 and m2: mins_txt_clean = " ".join(m1) + f"{ht_clean} " + " ".join(m2)
                        elif m1: mins_txt_clean = " ".join(m1) + f"{ht_clean}"
                        elif m2: mins_txt_clean = f"{ht_clean} " + " ".join(m2)
                        else: mins_txt_clean = f"{ht_clean}"
                        # NUEVO ORDEN: [E)]J10([2-2] CLASIFICACION) mins
                        # saca el texto limpio del rival sin html para el copy
                        try:
                            _rival_copy = f" {h} vs {a}"
                            # si tienes clasificacion, usala
                            if 'rival_txt' in locals() or 'vs_txt' in locals():
                                import re
                                # vs_txt ya lo tienes arriba para huecos, para no huecos usa rival_txt limpio
                                _rv_clean = re.sub(r'<[^>]+>', '', rival_txt).strip() if 'rival_txt' in locals() else f" {h} vs {a}"
                                partidos_pred_copy_fix2.append(f"{badge}J{int(j_fix2)}({ft_clean} {_rv_clean}) {mins_txt_clean}")
                            else:
                                partidos_pred_copy_fix2.append(f"J{int(j_fix2)}({ft_clean} {_rival_copy}) {mins_txt_clean} {estado}")
                        except:
                            partidos_pred_copy_fix2.append(f"J{int(j_fix2)}({ft_clean} {h} vs {a}) {mins_txt_clean} {estado}")

                    if st.session_state.get("show_partidos_fix2", False):
                        st.markdown(f"<div style='line-height:1.15;white-space:normal;word-break:break-word;margin:0 0 2px 0;padding:0'>{html_lineas_fix2}</div>", unsafe_allow_html=True)

    if True: # FIX BOTON SIEMPRE VISIBLE AUNQUE NO CONCUERDE
        import html as _html
        # cabecera filtros - TODO lo de los desplegables
        try:
            _ligas_txt = ", ".join(ligas_pred_sel_fix2) if ligas_pred_sel_fix2 else "TODAS"
            _fecha_txt = fecha_pred_sel_fix2
            _goles_parte_txt = st.session_state.get("goles_parte_fix2", "Todo")
            _cond_loc_txt = cond_loc_pred_fix2
            _res_1p_tipo_txt = res_1p_tipo_fix2
            _res_ht_ft_txt = ", ".join(resultados_pred_sel_fix2) if resultados_pred_sel_fix2 else "TODOS"
            _overs_txt = ", ".join(overs_sel_fix2) if overs_sel_fix2 else "TODOS"
            _live_txt = f"{res_live_tipo_fix2} MIN:{min_live_raw_fix2 or '-'}"
            _min_desde_txt = min_desde_pred_raw_fix2 or "-"
            _min_hasta_txt = min_hasta_pred_raw_fix2 or "-"
            _eq_man1_txt = f"{equipos_manuales_1_fix2}" if equipos_manuales_1_fix2 else "-"
            _eq_man2_txt = f"{equipos_manuales_2_fix2}" if equipos_manuales_2_fix2 else "-"
            _partidos_fut_txt = f"{len(partidos_sel_fix2)}: {partidos_sel_fix2[:2]}" if partidos_sel_fix2 else "MANUAL"
            filtros_txt_fix2 = (
                f"FILTROS FIX2 | PARTIDOS FUT={_partidos_fut_txt} | Ligas=[{_ligas_txt}] | Fecha={_fecha_txt} | "
                f"GOLES_PARTE={_goles_parte_txt} | Filtro={_cond_loc_txt} | "
                f"1P_TIPO={_res_1p_tipo_txt} | 1P/2P_RES=[{_res_ht_ft_txt}] | Overs=[{_overs_txt}] | "
                f"BTTS=[{ambos_marcan_fix2}] | LIVE={_live_txt} | MIN_DESDE={_min_desde_txt} HASTA={_min_hasta_txt} | "
                f"MANUAL1={_eq_man1_txt} | MANUAL2={_eq_man2_txt} | EQUIPOS_MOSTRADOS={equipos_a_mostrar_fix2}"
            )
        except Exception as e:
            filtros_txt_fix2 = f"FILTROS FIX2: {ligas_pred_sel_fix2} {fecha_pred_sel_fix2} {cond_loc_pred_fix2} | ERR:{e}"
        # TEXTO VISIBLE EN PANTALLA PARA VER FILTROS PUESTOS
        st.markdown(f"<div style='font-family:monospace; font-size:9px; color:#000; font-weight:900; background:#f0f0f0; border:1px solid #0A2342; border-radius:6px; padding:6px 8px; margin:8px 0; white-space:pre-wrap; word-break:break-word;'>{filtros_txt_fix2}</div>", unsafe_allow_html=True)
        # --- CABECERA FINAL VISUAL ORDENADA ---
        try:
            if lista_resumen_fix2:
                resumen_html = "".join([f"<div style='border:2px solid #FFFFFF; border-radius:10px; padding:10px; margin:14px 0; background:#000; box-shadow:0 0 6px #000;'>{r}</div>" for r in lista_resumen_fix2])
                st.markdown(f"<div style='font-family:monospace; font-size:10px; color:#e8e8e8; font-weight:900; background:#000; border:1px solid #333; border-radius:8px; padding:10px; margin:12px 0; line-height:1.6;'>🔎 RESUMEN FINAL FIX2<br><br>{resumen_html}</div>", unsafe_allow_html=True)
        except:
            pass
        try:
            import re as _re_fix2
            def _strip_html_fix2(s):
                s = s.replace('</div>', '\n').replace('<br>', '\n').replace('<br/>','\n').replace('<br />','\n')
                return _re_fix2.sub(r'<[^>]+>', '', s).replace('&nbsp;',' ').strip()
            resumen_copy_html = "\n".join(lista_resumen_fix2) if lista_resumen_fix2 else ""
            resumen_copy_clean = _strip_html_fix2(resumen_copy_html)
            partidos_clean = [_strip_html_fix2(x) for x in (partidos_pred_copy_fix2 or ["SIN DATOS FIX2 - filtros no coinciden"])[:300]]
            if resumen_copy_clean:
                texto_final_fix2 = filtros_txt_fix2 + "\n" + "\n".join(partidos_clean) + "\n\n--- RESUMEN FINAL ---\n" + resumen_copy_clean
            else:
                texto_final_fix2 = filtros_txt_fix2 + "\n" + "\n".join(partidos_clean)
        except:
            texto_final_fix2 = filtros_txt_fix2 + "\n" + "\n".join(partidos_pred_copy_fix2[:300])
        safe_txt_fix2 = _html.escape(texto_final_fix2)
        import streamlit.components.v1 as components
        components.html(f"""
        <textarea id="txt_pred_fix2" style="position:absolute;left:-9999px;top:-9999px;">{safe_txt_fix2}</textarea>
        <button onclick="navigator.clipboard.writeText(document.getElementById('txt_pred_fix2').value).then(()=>{{let b=document.getElementById('btn_pred_copy_fix2'); b.innerText='✓ COPIADO'; b.style.background='#0f8105'; setTimeout(()=>{{b.innerText=' COPIAR PREDICCION FIX2'; b.style.background='#0A2342'}},1200)}})"
        id="btn_pred_copy_fix2"
        style="width:100%;background:#0A2342;color:white;border:none;border-radius:6px;padding:12px;font-weight:900;cursor:pointer;">
         COPIAR PREDICCION FIX2 ({len(partidos_sel_fix2)} partidos futuros)
        </button>
        """, height=55, scrolling=False)

##################
################################################################### CLONADO
##################
##################
################################################################### CLONADO########################################################
################################################################### CLONADO FIX3 - DOBLE
###################
################################################################### CLONADO
##################
################################################################### CLONADOF
##################
################################################################### CLONADO##################
################################################################### CLONADO
##########################################################################
################################################################### CLONADO FIX3 - DOBLE
###################
################################################################### CLONADO
##################
################################################################### CLONADOF
##################
################################################################### CLONADO##################
################################################################### CLONADO
##########################################################################
################################################################### CLONADO FIX3 - DOBLE
###################
################################################################### CLONADO
##################
################################################################### CLONADOF
##################
################################################################### CLONADO##################
################################################################### CLONADO
##########################################################################
################################################################### CLONADO FIX3 - DOBLE
###################
################################################################### CLONADO
##################
################################################################### CLONADOF
##################
################################################################### CLONADO##################
################################################################### CLONADO
##########################################################################
################################################################### CLONADO FIX3 - DOBLE
###################
################################################################### CLONADO
##################
################################################################### CLONADOF
##################
################################################################### CLONADO##################
################################################################### CLONADO
##########################################################################
################################################################### CLONADO FIX3 - DOBLE
###################
################################################################### CLONADO
##################
################################################################### CLONADOF
##################
################################################################### CLONADO##################
################################################################### CLONADO
##################
##################
with st.expander("JORNADAS - HISTORIAL COMPLETO L/V", expanded=False):
    @st.cache_data(show_spinner=False)
    def cargar_base_jornadas():
        dfs=[]
        for name in ["base_partidos_europa.parquet", "base_partidos_resto.parquet"]:
            for base in [pathlib.Path(name), pathlib.Path(__file__).parent.resolve()/name, pathlib.Path("/mnt/data")/name]:
                if base.exists():
                    try: dfs.append(pd.read_parquet(base))
                    except: pass
                    break
        # Nations League: tu script la guarda en CSV aparte, si no lo sumas aqui nunca aparece
        for name in ["uefa_nations_league_2627.csv"]:
            for base in [pathlib.Path(name), pathlib.Path(__file__).parent.resolve()/name, pathlib.Path("/mnt/data")/name]:
                if base.exists():
                    try: dfs.append(pd.read_csv(base, on_bad_lines='skip'))
                    except: pass
                    break
        df_p = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
        if not df_p.empty and 'fixture_id' in df_p.columns:
            df_p = df_p.drop_duplicates(subset=['fixture_id'], keep='last')
        dfs_g=[]
        for name in ["base_goles_europa.parquet", "base_goles_resto.parquet"]:
            for base in [pathlib.Path(name), pathlib.Path(__file__).parent.resolve()/name, pathlib.Path("/mnt/data")/name]:
                if base.exists():
                    try: dfs_g.append(pd.read_parquet(base))
                    except: pass
                    break
        for name in ["uefa_nations_league_2627_goles.csv"]:
            for base in [pathlib.Path(name), pathlib.Path(__file__).parent.resolve()/name, pathlib.Path("/mnt/data")/name]:
                if base.exists():
                    try: dfs_g.append(pd.read_csv(base, on_bad_lines='skip'))
                    except: pass
                    break
        df_g = pd.concat(dfs_g, ignore_index=True) if dfs_g else pd.DataFrame()
        ev={}
        if not df_g.empty:
            df_g['fid_str']=df_g['fixture_id'].astype(str).str.split('.').str[0]
            # femenino viene como "45'" / "45'+2'" -> to_numeric lo deja en 0. Usa min_num si hay, si no extrae el numero.
            def _parse_m(row):
                try:
                    if 'min_num' in row and pd.notna(row.get('min_num')):
                        return int(float(row.get('min_num')))
                except:
                    pass
                try:
                    m = re.search(r'\d+', str(row.get('minuto', '')))
                    return int(m.group(0)) if m else 0
                except:
                    return 0
            df_g['m'] = df_g.apply(_parse_m, axis=1).astype(int)
            for fid, sub in df_g.groupby('fid_str'):
                ev[fid]=[{'m':int(r.get('m',0)), 'team':normaliza(r.get('equipo','')), 'tipo':str(r.get('tipo',''))} for _, r in sub.iterrows()]
        return df_p, ev

    df_jorn, ev_jorn = cargar_base_jornadas()
    @st.cache_data(show_spinner=False)
    def cargar_clas_jorn():
        for p in [pathlib.Path("/mnt/data/Base-Clasificacion-Jornada.csv"), pathlib.Path(__file__).parent.resolve()/ "Base-Clasificacion-Jornada.csv"]:
            if p.exists():
                try: return pd.read_csv(p, on_bad_lines='skip')
                except: pass
        return pd.DataFrame()
    df_clas_j = cargar_clas_jorn()
    clas_dict_j={}; clas_max_j={}
    if not df_clas_j.empty:
        for _, rc in df_clas_j.iterrows():
            try:
                k=(normaliza(rc.get('League','')), int(rc.get('jornada_int',0)), normaliza(rc.get('Team','')))
                clas_dict_j[k]=rc
                ln=normaliza(rc.get('League',''))
                clas_max_j[ln]=max(clas_max_j.get(ln,0), int(rc.get('jornada_int',0)))
            except: pass
    if df_jorn.empty:
        st.caption("Sin base")
    else:
        ligas_j = ["TODAS"] + sorted(df_jorn['League'].dropna().astype(str).unique().tolist())
        liga_j_sel = st.selectbox("LIGA JORNADAS", ligas_j, key="liga_jornadas_sel")
        df_l = df_jorn if liga_j_sel=="TODAS" else df_jorn[df_jorn['League'].astype(str)==liga_j_sel]
        equipos_j = sorted(pd.concat([df_l['HomeTeam'], df_l['AwayTeam']]).dropna().astype(str).unique().tolist())
        eqs_j = st.multiselect("EQUIPOS JORNADAS", equipos_j, default=[], key="eq_jornadas", placeholder="Elige 1 o varios")
        goles_parte2 = st.selectbox("GOLES PARTE2", ["Todo","1ªParte","2ªParte"], index=0, key="goles_parte2")
        ambos_marcan_fix3 = st.selectbox("AMBOS MARCAN FIX3", ["-","SI","NO"], index=0, key="ambos_marcan_fix3")

        # MIN DESDE/HASTA FIX3 - PEQUEÑO CENTRADO MOVIL
        c_min_a_fix3, c_min_b_fix3 = st.columns([1,1], gap="small")
        with c_min_a_fix3:
            min_desde_raw_fix3 = st.text_input("MIN DESDE FIX3", key="min_desde_fix3", placeholder="-")
        with c_min_b_fix3:
            min_hasta_raw_fix3 = st.text_input("MIN HASTA FIX3", key="min_hasta_fix3", placeholder="-")

        import streamlit.components.v1 as components
        components.html("""
        <script>
        (function(){
          const doc = window.parent.document;
          function fixMin3(){
            const a = doc.querySelector('input[aria-label="MIN DESDE FIX3"]');
            if(!a) return;
            const hb = a.closest('div[data-testid="stHorizontalBlock"]');
            if(!hb) return;
            hb.style.setProperty('display','flex','important');
            hb.style.setProperty('flex-direction','row','important');
            hb.style.setProperty('flex-wrap','nowrap','important');
            hb.style.setProperty('justify-content','center','important');
            hb.style.setProperty('gap','10px','important');
            hb.style.setProperty('max-width','230px','important');
            hb.style.setProperty('width','230px','important');
            hb.style.setProperty('margin','0 auto','important');
            hb.querySelectorAll(':scope > div[data-testid="column"]').forEach(col=>{
              col.style.setProperty('flex','0 0 105px','important');
              col.style.setProperty('max-width','105px','important');
              col.style.setProperty('width','105px','important');
            });
            hb.querySelectorAll('input[aria-label="MIN DESDE FIX3"], input[aria-label="MIN HASTA FIX3"]').forEach(inp=>{
              const wrap = inp.closest('div[data-testid="stTextInput"]');
              if(wrap){
                wrap.style.setProperty('max-width','105px','important');
                wrap.style.setProperty('width','105px','important');
              }
            });
          }
          setTimeout(fixMin3, 200);
          setTimeout(fixMin3, 800);
          setInterval(fixMin3, 1200);
        })();
        </script>
        """, height=0)

        def _parse_min_fix3(v):
            try:
                if v is None or str(v).strip() in ["", "-", "–", "—"]: return None
                return int(str(v).strip().replace("'", ""))
            except: return None
        MIN_DESDE_FIX3 = _parse_min_fix3(min_desde_raw_fix3)
        MIN_HASTA_FIX3 = _parse_min_fix3(min_hasta_raw_fix3)

        # --- RESUMEN FILTROS FIX3 VISIBLE ---
        try:
            _f3_liga = liga_j_sel
            _f3_eq = ", ".join(eqs_j) if eqs_j else "-"
            _f3_goles = goles_parte2
            _f3_md = min_desde_raw_fix3 or "-"
            _f3_mh = min_hasta_raw_fix3 or "-"
            _resumen_fix3 = f"FILTROS FIX3 | LIGA=[{_f3_liga}] | EQUIPOS=[{_f3_eq}] | GOLES_PARTE={_f3_goles} | BTTS={ambos_marcan_fix3} | MIN_DESDE={_f3_md} HASTA={_f3_mh}"
            st.markdown(f"<div style='font-family:monospace;font-size:9px;color:#000;font-weight:900;background:#f0f0f0;border:1px solid #0A2342;border-radius:6px;padding:6px 8px;margin:8px 0;white-space:pre-wrap;word-break:break-word;'>{_resumen_fix3}</div>", unsafe_allow_html=True)
        except:
            pass

        if not eqs_j:
            st.caption("Selecciona equipo(s)")
        else:
            # SOPORTE MULTI-EQUIPO - muestra los 2/3/4 seleccionados
            bloques_html=[]

        # SOPORTE MULTI-EQUIPO - muestra los 2/3/4 seleccionados
        bloques_html=[]
        for eq_j in eqs_j:
            norm_j = normaliza(eq_j); up_j = eq_j.upper().strip()
            df_team = df_l[(df_l['HomeTeam'].astype(str).str.upper().str.strip()==up_j) | (df_l['AwayTeam'].astype(str).str.upper().str.strip()==up_j)].copy()
            df_team['Date']=pd.to_datetime(df_team['Date'], dayfirst=True, errors='coerce')
            df_team=df_team.sort_values('Date').reset_index(drop=True)
            df_team['J_EQ']=range(1, len(df_team)+1)

            total=len(df_team)
            loc_total=int((df_team['HomeTeam'].astype(str).str.upper().str.strip()==up_j).sum())
            vis_total=total-loc_total

            total_por_j={}
            filt_cnt=0
            for _, rr in df_team.iterrows():
                try:
                    jn=int(rr.get('J_EQ',0)); hg=int(float(rr.get('FTHG',0) or 0)); ag=int(float(rr.get('FTAG',0) or 0))
                    es_loc=str(rr.get('HomeTeam','')).upper().strip()==up_j
                    fid=str(rr.get('fixture_id','')).split('.')[0]
                    h_team=str(rr.get('HomeTeam','')).strip(); a_team=str(rr.get('AwayTeam','')).strip()
                    lg_norm=normaliza(rr.get('League',''))
                    try:
                        j_max=clas_max_j.get(lg_norm, 0); j_cand=[j_max] if j_max else [9999]
                        def _get_clas_fuzzy(team_norm, lg_norm):
                            for jc in j_cand:
                                rec=clas_dict_j.get((lg_norm, jc, team_norm))
                                if rec is not None: return rec
                            for (l_, j_, n_), rec_ in clas_dict_j.items():
                                if l_!=lg_norm: continue
                                if j_ not in j_cand: continue
                                if team_norm in n_ or n_ in team_norm: return rec_
                            for (l_, j_, n_), rec_ in clas_dict_j.items():
                                if l_!=lg_norm: continue
                                if team_norm in n_ or n_ in team_norm: return rec_
                            return None
                        r_h=_get_clas_fuzzy(normaliza(h_team), lg_norm)
                        r_a=_get_clas_fuzzy(normaliza(a_team), lg_norm)
                        if r_h is not None:
                            pos_h_html=f"<span style='color:#00BFFF;font-size:9px;font-weight:900'>{int(r_h.get('Pos',0))}º</span>"
                            pts_h_html=f"<span style='color:#888;font-size:9px;font-weight:400'>({int(r_h.get('Pts',0))}pts)</span>"
                        else:
                            pos_h_html=""; pts_h_html=""
                        if r_a is not None:
                            pos_a_html=f"<span style='color:#00BFFF;font-size:9px;font-weight:900'>{int(r_a.get('Pos',0))}º</span>"
                            pts_a_html=f"<span style='color:#888;font-size:9px;font-weight:400'>({int(r_a.get('Pts',0))}pts)</span>"
                        else:
                            pos_a_html=""; pts_a_html=""
                        pts_txt=""
                        pos_txt=pts_txt
                    except:
                        pos_h_html=""; pos_a_html=""; pts_txt=""; pos_txt=""
                    try:
                        hthg=int(float(rr.get('HTHG',0) or 0)); htag=int(float(rr.get('HTAG',0) or 0))
                    except:
                        hthg=0; htag=0
                    if hthg==0 and htag==0:
                        try:
                            c1=0; c2=0
                            for ev in ev_jorn.get(fid, []):
                                if ev.get('m',999)<=45 and 'Missed' not in ev.get('tipo',''):
                                    t=normaliza(ev.get('team',''))
                                    if t==normaliza(h_team):
                                        c1+=1
                                    else:
                                        c2+=1
                            if c1+c2>0:
                                hthg=c1; htag=c2
                        except:
                            pass
                    if es_loc:
                        _col_hthg = "#D0D0D0" if hthg>0 else "#888"
                        _col_htag = "#888"
                        if htag==0:
                            _col_htag = "#888"
                        ht_gris = f"<span style='color:#888'>[</span><span style='color:{_col_hthg};font-weight:900'>{hthg}</span><span style='color:#888'>-</span><span style='color:{_col_htag};font-weight:900'>{htag}</span><span style='color:#888'>]</span>"
                    else:
                        _col_hthg = "#888"
                        _col_htag = "#D0D0D0" if htag>0 else "#888"
                        ht_gris = f"<span style='color:#888'>[</span><span style='color:{_col_hthg};font-weight:900'>{hthg}</span><span style='color:#888'>-</span><span style='color:{_col_htag};font-weight:900'>{htag}</span><span style='color:#888'>]</span>"
                    if es_loc:
                        h_txt=f"{pos_h_html}<span style='color:#FFFFFF;font-weight:900;'>{h_team}</span>"
                        a_txt=f"<span style='color:#888888;font-weight:700'>{a_team}</span>{pos_a_html}"
                        _c_h = "#00c800" if hg>0 else "#888"
                        _c_a = "#ff2a2a" if ag>0 else "#888"
                        res_txt=f"[<span style='color:{_c_h};font-weight:900'>{hg}</span>-<span style='color:{_c_a};font-weight:900'>{ag}</span>] {ht_gris}"
                        teams_txt=f"{h_txt} <span style='color:#888'>vs</span> {a_txt}"
                        letra="G" if hg>ag else "E" if hg==ag else "P"
                    else:
                        h_txt=f"{pos_h_html}<span style='color:#888888;font-weight:700'>{h_team}</span>"
                        a_txt=f"<span style='color:#FFFFFF;font-weight:900;'>{a_team}</span>{pos_a_html}"
                        _c_h = "#ff2a2a" if hg>0 else "#888"
                        _c_a = "#00c800" if ag>0 else "#888"
                        res_txt=f"[<span style='color:{_c_h};font-weight:900'>{hg}</span>-<span style='color:{_c_a};font-weight:900'>{ag}</span>] {ht_gris}"
                        teams_txt=f"{h_txt} <span style='color:#888'>vs</span> {a_txt}"
                        letra="G" if ag>hg else "E" if ag==hg else "P"
                    badge="<span style='background:#00c800;color:#fff;padding:0 4px;border-radius:3px;font-size:9px;font-weight:900'>G</span>" if letra=="G" else "<span style='background:#ffcc00;color:#000;padding:0 4px;border-radius:3px;font-size:9px;font-weight:900'>E</span>" if letra=="E" else "<span style='background:#ff2a2a;color:#fff;padding:0 4px;border-radius:3px;font-size:9px;font-weight:900'>P</span>"
                    # --- FILTRO BTTS SI/NO ---
                    btts = (hg > 0 and ag > 0)
                    if ambos_marcan_fix3 == "SI":
                        btts_pasa = btts
                    elif ambos_marcan_fix3 == "NO":
                        btts_pasa = not btts
                    else:
                        btts_pasa = True

                    tiene_en_rango = btts_pasa
                    if btts_pasa and (MIN_DESDE_FIX3 is not None or MIN_HASTA_FIX3 is not None):
                        tiene_en_rango = False
                        for ev in ev_jorn.get(fid, []):
                            if 'Missed' in ev.get('tipo',''): continue
                            mm=ev.get('m',-1)
                            if MIN_DESDE_FIX3 is not None and mm < MIN_DESDE_FIX3: continue
                            if MIN_HASTA_FIX3 is not None and mm > MIN_HASTA_FIX3: continue
                            tiene_en_rango = True
                            break
                    if tiene_en_rango:
                        filt_cnt+=1
                    mins_1p=[]; mins_2p=[]
                    for ev in sorted(ev_jorn.get(fid, []), key=lambda x: x.get('m',0)):
                        if 'Missed' in ev.get('tipo',''): continue
                        mm=ev.get('m',-1)
                        if MIN_DESDE_FIX3 is not None and mm < MIN_DESDE_FIX3: continue
                        if MIN_HASTA_FIX3 is not None and mm > MIN_HASTA_FIX3: continue
                        if not tiene_en_rango: continue
                        es_mio=(ev.get('team','')==norm_j); col="#00c800" if es_mio else "#ff2a2a"
                        tag=f"<span style='color:{col};font-weight:900'>{mm}'</span>"
                        if mm<=45: mins_1p.append(tag)
                        else: mins_2p.append(tag)
                    if not tiene_en_rango:
                        mins_txt=""
                    else:
                        if goles_parte2=="1ªParte": mins_txt=" ".join(mins_1p) if mins_1p else ""
                        elif goles_parte2=="2ªParte": mins_txt=" ".join(mins_2p) if mins_2p else ""
                        else: 
                            if mins_1p and mins_2p: mins_txt=" ".join(mins_1p)+" <span style='color:#888;font-weight:900'>|</span> "+" ".join(mins_2p)
                            elif mins_1p: mins_txt=" ".join(mins_1p)
                            elif mins_2p: mins_txt=" ".join(mins_2p)
                            else: mins_txt=""
                    if tiene_en_rango:
                        inner=f"<span><span style='font-size:11px;font-weight:900'>{res_txt}</span> ({teams_txt}{pos_txt})</span><br><span style='display:inline-block;margin:2px 0 0 18px;font-size:11px;font-weight:900'>{mins_txt}</span>"
                    else:
                        _teams_gris = teams_txt.replace("#FFFFFF", "#888888").replace("#00BFFF", "#888")
                        inner=f"<span><span style='font-size:11px;font-weight:900'>{res_txt}</span> ({_teams_gris}{pos_txt})</span><br><span style='display:inline-block;margin:2px 0 0 18px'></span>"
                    total_por_j[jn]=(inner, es_loc, badge)
                except: continue
            jornadas_ord=sorted(total_por_j.keys(), reverse=True)
            todo_list=[]
            for jn in jornadas_ord:
                j_tag=f"<span style='color:#A020F0;font-weight:900'>J{jn}</span>"
                try:
                    inner, es_loc, badge = total_por_j[jn]
                except:
                    inner, es_loc = total_por_j[jn]
                    badge = ""
                todo_list.append(f"<div style='margin:4px 0;padding:5px 6px;background:#000;border:1px solid #555;border-radius:6px'>{badge} {j_tag} {inner}</div>")
            todo_txt="".join(todo_list) if todo_list else "-"
            filt_show = filt_cnt if (MIN_DESDE_FIX3 is not None or MIN_HASTA_FIX3 is not None or ambos_marcan_fix3 != "-") else total
            linea_res2=f"{eq_j.upper()}: {filt_show}/{total}<br><br>{todo_txt}"
            bloques_html.append(linea_res2)
        for bloque in bloques_html:
            st.markdown(f"<div style='border:2px solid #0A2342; border-radius:10px; padding:10px; margin:14px 0; background:#000; box-shadow:0 0 6px #000; font-family:monospace; font-size:10px; color:#e8e8e8; line-height:1.6;'>{bloque}</div>", unsafe_allow_html=True)

        # --- BOTON COPIAR FIX3: resumen + resultados ---
        if True:
            import html as _html_fix3, re as _re_fix3
            try:
                _resumen_copy = _resumen_fix3
            except:
                _resumen_copy = f"FILTROS FIX3 | LIGA={liga_j_sel} | EQUIPOS={eqs_j} | GOLES_PARTE={goles_parte2} | MIN {min_desde_raw_fix3}-{min_hasta_raw_fix3}"
            def _strip_fix3(s):
                s = s.replace('</div>', '\n').replace('<br>', '\n').replace('<br/>','\n').replace('<br />','\n')
                return _re_fix3.sub(r'<[^>]+>', '', s).replace('&nbsp;',' ').strip()
            _bloques_clean = "\n\n".join([_strip_fix3(b) for b in bloques_html]) if bloques_html else "SIN DATOS FIX3"
            _texto_final_fix3 = _resumen_copy + "\n\n" + _bloques_clean
            _safe_fix3 = _html_fix3.escape(_texto_final_fix3)
            import streamlit.components.v1 as components
            components.html(f"""
            <textarea id="txt_fix3" style="position:absolute;left:-9999px;top:-9999px;">{_safe_fix3}</textarea>
            <button onclick="navigator.clipboard.writeText(document.getElementById('txt_fix3').value).then(()=>{{let b=document.getElementById('btn_fix3_copy'); b.innerText='✓ COPIADO FIX3'; b.style.background='#0f8105'; setTimeout(()=>{{b.innerText=' COPIAR JORNADAS FIX3'; b.style.background='#A020F0'}},1200)}})"
            id="btn_fix3_copy"
            style="width:100%;background:#A020F0;color:white;border:none;border-radius:6px;padding:12px;font-weight:900;cursor:pointer;margin-top:10px;">
             COPIAR JORNADAS FIX3
            </button>
            """, height=55, scrolling=False)
#
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO#################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO#################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO#################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO#################
################################################################### CLONADO
####################################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO#################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO#################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO#################
################################################################### CLONADO
####################################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO#################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO#################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO#################
################################################################### CLONADO
####################################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO#################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO#################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO#################
################################################################### CLONADO
####################################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO#################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO#################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO#################
################################################################### CLONADO
####################################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO#################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO#################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO#################
################################################################### CLONADO
####################################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO#################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO#################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO#################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO#################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO#################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
##################
################################################################### CLONADO
#
###############
###############
###############
###############
###############
###############
###########################################################################
###############
###############
###############
###############
###############
###############
###############
###############
###############
###########################################################################
###############
###############
###############
###############
###############
###############
########
# 
# 
# 

# ================= BLOQUE AGENDA APUESTA V2 - CON BANCA =================
# TAG: [AGENDA-APUESTA-V2-BANCA]
with st.expander("BLOQUE AGENDA APUESTA - BANCA", expanded=False):
    import pathlib, datetime
    import pandas as pd

    # --- FUENTE UNICA: CSV DEL REPO ---
    path_apuestas = pathlib.Path(__file__).parent.resolve() / "apuestas_asentadas.csv"
    path_agenda = pathlib.Path(__file__).parent.resolve() / "agenda_apuestas.csv"  # solo para tus PENDIENTES a mano
    path_banca = pathlib.Path(__file__).parent.resolve() / "banca_config.csv"

    def _leer_agenda():
        # Lee apuestas_asentadas.csv del repo y lo convierte al formato que ya usa el bloque
        # + lo que tengas a mano en agenda_apuestas.csv (PENDIENTE)
        _rows = []
        if path_apuestas.exists():
            try:
                _raw = pd.read_csv(path_apuestas)
                _raw = _raw[~_raw['ID_Apuesta'].astype(str).str.contains('RESUMEN', na=False)]
                for _, _r in _raw.iterrows():
                    _part = str(_r.get('Partidos_Marcador', '') or '')
                    _tipo = str(_r.get('Tipo', '')).strip().lower()
                    _multi = _tipo != "simple"
                    if _multi:
                        _liga = "Combinadas"
                        _first = _part.split(' | ')[0] if ' | ' in _part else _part
                        _first = _first.split(' (')[0].strip()
                        _first = _first.rsplit(' ', 1)[0].strip() if ' vs ' in _first and ' ' in _first else _first
                        _e1 = _first.split(' vs ')[0].strip() if ' vs ' in _first else ""
                        _e2 = _first.split(' vs ')[1].strip() if ' vs ' in _first else ""
                    else:
                        _p = _part.split(' | ')[0] if ' | ' in _part else _part
                        _e1 = _p.split(' vs ')[0].strip() if ' vs ' in _p else ""
                        _e2 = _p.split(' vs ')[1].strip() if ' vs ' in _p else ""
                        # liga desde base_partidos.csv - mapa incrustado, sin leer archivo
                        _liga = "Ligas random"
                        try:
                            if not hasattr(_leer_agenda, "_map_bp"):
                                import re as _re_bp, unicodedata as _ud_bp
                                def _norm_bp(s):
                                    s = str(s or "").upper()
                                    s = ''.join(c for c in _ud_bp.normalize('NFD', s) if _ud_bp.category(c) != 'Mn')
                                    s = _re_bp.sub(r'[^A-Z0-9 ]', ' ', s)
                                    return _re_bp.sub(r'\s+', ' ', s).strip()
                                _leer_agenda._norm_bp = _norm_bp
                                _leer_agenda._map_bp = {
                                    "ALAVES": "【entity-LALIGA EA SPORTS¦canonical_name=LALIGA EA SPORTS】", "ALBACETE": "LALIGA HYPERMOTION", "ALGECIRAS": "PRIMERA FEDERACION GRUPO 2",
                                    "ARGES PITESTI": "LIGA I RUMANIA", "AROUCA": "【entity-LIGA PORTUGAL¦canonical_name=LIGA PORTUGAL】", "ASTON VILLA": "【entity-PREMIER LEAGUE¦canonical_name=PREMIER LEAGUE】",
                                    "ATROMITOS": "SUPER LEAGUE GRECIA", "BENFICA": "【entity-LIGA PORTUGAL¦canonical_name=LIGA PORTUGAL】", "BHAYANGKARA FC": "LIGA 1 INDONESIA",
                                    "BOURNEMOUTH": "【entity-PREMIER LEAGUE¦canonical_name=PREMIER LEAGUE】", "BURGOS": "LALIGA HYPERMOTION", "CAGLIARI": "SERIE A ITALIA",
                                    "CD CORIA": "PRIMERA FEDERACION GRUPO 1", "CERRO PORTENO": "PRIMERA DIVISION PARAGUAY", "CHELSEA": "【entity-PREMIER LEAGUE¦canonical_name=PREMIER LEAGUE】",
                                    "COLO COLO": "PRIMERA DIVISION CHILE", "DEPORTIVO RECOLETA": "PRIMERA DIVISION PARAGUAY", "ESPANYOL": "【entity-LALIGA EA SPORTS¦canonical_name=LALIGA EA SPORTS】",
                                    "EVERTON DE VINA": "PRIMERA DIVISION CHILE", "EXCELSIOR": "EREDIVISIE", "FAMALICAO": "【entity-LIGA PORTUGAL¦canonical_name=LIGA PORTUGAL】",
                                    "【entity-FIORENTINA¦canonical_name=Fiorentina】": "SERIE A ITALIA", "FRANCS BORAINS": "CHALLENGER PRO LEAGUE BELGICA 2DA", "FROSINONE": "SERIE A ITALIA",
                                    "FULHAM": "【entity-PREMIER LEAGUE¦canonical_name=PREMIER LEAGUE】", "GIMHAE CITY": "K LEAGUE 2", "GO AHEAD EAGLES": "EREDIVISIE",
                                    "GORNIK ZABRZE": "EKSTRAKLASA", "GRAZER AK": "BUNDESLIGA AUSTRIA", "IPSWICH": "【entity-PREMIER LEAGUE¦canonical_name=PREMIER LEAGUE】",
                                    "JEONBUK MOTORS": "K LEAGUE 1", "JEONNAM DRAGONS": "K LEAGUE 2", "JUVENTUD TORREMOLINOS": "PRIMERA FEDERACION GRUPO 2",
                                    "【entity-JUVENTUS¦canonical_name=Juventus】": "SERIE A ITALIA", "KORONA KIELCE": "EKSTRAKLASA", "LECCE": "SERIE A ITALIA",
                                    "LEEDS": "【entity-PREMIER LEAGUE¦canonical_name=PREMIER LEAGUE】", "LEGANES": "LALIGA HYPERMOTION", "LUDOGORETS": "FIRST LEAGUE BULGARIA",
                                    "MARSEILLE": "LIGUE 1", "MIRANDES": "PRIMERA FEDERACION GRUPO 1", "NEWCASTLE": "PREMIER LEAGUE",
                                    "NUBLENSE": "PRIMERA DIVISION CHILE", "OFI": "SUPER LEAGUE GRECIA", "PAJU CITIZEN": "K LEAGUE 2",
                                    "PANATHINAIKOS": "SUPER LEAGUE GRECIA", "PAOK": "SUPER LEAGUE GRECIA", "PRESTON": "CHAMPIONSHIP",
                                    "PSIM YOGYAKARTA": "LIGA 1 INDONESIA", "PSM MAKASSAR": "LIGA 1 INDONESIA", "PSS SLEMAN": "LIGA 1 INDONESIA",
                                    "RADOMIAK RADOM": "EKSTRAKLASA", "RAYO VALLECANO": "LALIGA EA SPORTS", "REAL MADRID": "LALIGA EA SPORTS",
                                    "REAL MURCIA": "PRIMERA FEDERACION GRUPO 2", "REAL SOCIEDAD": "LALIGA EA SPORTS", "SEOUL E LAND FC": "K LEAGUE 2",
                                    "SEVILLA": "LALIGA EA SPORTS", "SOUTHAMPTON": "CHAMPIONSHIP", "SPORTING GIJON": "LALIGA HYPERMOTION",
                                    "SPORTING HASSELT": "CHALLENGER PRO LEAGUE BELGICA 2DA", "SUNDERLAND": "PREMIER LEAGUE", "TORINO": "SERIE A ITALIA",
                                    "TOTTENHAM": "PREMIER LEAGUE", "UD OURENSE": "PRIMERA FEDERACION GRUPO 1", "UNIVERSIDAD DE CHILE": "PRIMERA DIVISION CHILE",
                                    "UTA ARAD": "LIGA I RUMANIA", "VALLADOLID": "LALIGA HYPERMOTION", "WIECZYSTA KRAKOW": "EKSTRAKLASA",
                                    "WSG WATTENS": "BUNDESLIGA AUSTRIA", "AL JABALAIN": "SAUDI FIRST DIVISION LEAGUE",
                                }
                            _l1 = _leer_agenda._map_bp.get(_leer_agenda._norm_bp(_e1))
                            _l2 = _leer_agenda._map_bp.get(_leer_agenda._norm_bp(_e2))
                            if _l1 and _l1 == _l2:
                                _liga = _l1
                            elif _l1:
                                _liga = _l1
                            elif _l2:
                                _liga = _l2
                        except Exception:
                            pass
                    _res = str(_r.get('Resultado', '')).upper()
                    _res = "GANADA" if _res == "GANADA" else "PERDIDA" if _res == "PERDIDA" else "NULA"
                    _f = pd.to_datetime(_r.get('Realizada'), errors='coerce')
                    _rows.append({
                        "Fecha": _f.strftime("%d/%m/%Y %H:%M") if pd.notna(_f) else str(_r.get('Realizada', '')),
                        "Liga": _liga, "Equipo1": _e1, "Equipo2": _e2, "Minuto": 0,
                        "Cuota": float(pd.to_numeric(_r.get('Cuota_Total'), errors='coerce') or 0) if str(_r.get('Cuota_Total', '')).strip() not in ["", "nan"] else 0.0,
                        "Importe": float(_r.get('Cantidad_Apostada_EUR', 0) or 0),
                        "Resultado": _res, "Beneficio": float(_r.get('Beneficio_EUR', 0) or 0), "Banca": 0,
                        "Apuesta": f"{_r.get('Selecciones', '')} | {_part} | ID:{_r.get('ID_Apuesta', '')}",
                        "ID_Apuesta": str(_r.get('ID_Apuesta', '')),
                    })
            except Exception:
                pass
        _df = pd.DataFrame(_rows)
        # + tus pendientes a mano, si los hay
        if path_agenda.exists():
            try:
                _man = pd.read_csv(path_agenda)
                if not _man.empty:
                    _df = pd.concat([_df, _man], ignore_index=True) if not _df.empty else _man
            except Exception:
                pass
        if not _df.empty:
            _df['_ord'] = pd.to_datetime(_df['Fecha'], format="%d/%m/%Y %H:%M", errors='coerce')
            _df = _df.sort_values('_ord').drop(columns=['_ord']).reset_index(drop=True)
            # recalcula Banca en orden
            _run = float(banca_inicial_default); _b = []
            for _, _rr in _df.iterrows():
                if _rr['Resultado'] == "PENDIENTE":
                    _b.append(round(_run, 2))
                else:
                    _run += float(_rr['Beneficio']); _b.append(round(_run, 2))
            _df['Banca'] = _b
        return _df

    def _norm_liga(x):
        s = str(x or "").strip().upper()
        if s in ["LIGA 1 INDON", "LIGA 1 INDON."]: s = "LIGA 1 INDONESIA"
        if s == "SERIE A": s = "SERIE A ITALIA"
        return s

    # --- CARGA CONFIG BANCA ---
    banca_inicial_default = 346.0
    if path_banca.exists():
        try:
            df_bc = pd.read_csv(path_banca)
            banca_inicial_default = float(df_bc['banca_inicial'].iloc[-1])
        except:
            pass
    
    ligas_base = []
    equipos_base = []
    try:
        for p in [pathlib.Path(__file__).parent.resolve() / "Base-Clasificacion-Jornada.csv", pathlib.Path("Base-Clasificacion-Jornada.csv")]:
            if p.exists():
                df_tmp = pd.read_csv(p, encoding='utf-8-sig')
                ligas_base = sorted(df_tmp['League'].dropna().unique().tolist())
                equipos_base = sorted(df_tmp['Team'].dropna().unique().tolist())
                break
    except:
        pass
    if not ligas_base:
        ligas_base = ["2 BUNDESLIGA","LIGA 1 TUNEZ","2 LIGA AUSTRIA 2DA","PRIMERA DIVISION"]
    for _lm in ["2ª Singapur","Ligas random","Combinadas"]:
        if _lm not in ligas_base:
            ligas_base.append(_lm)
    if not equipos_base:
        equipos_base = ["1 FC NURNBERG","1 FC KAISERSLAUTERN"]

    # --- BANCA ACTUAL CALCULADA ---
    banca_actual = banca_inicial_default
    beneficio_total = 0
    if path_apuestas.exists() or path_agenda.exists():
        try:
            df_tmp_ag = _leer_agenda()
            if 'Beneficio' in df_tmp_ag.columns:
                beneficio_total = pd.to_numeric(df_tmp_ag['Beneficio'], errors='coerce').fillna(0).sum()
                banca_actual = banca_inicial_default + beneficio_total
            elif 'Resultado' in df_tmp_ag.columns:
                # migra vieja
                pass
        except:
            pass

    c_bank1, c_bank2, c_bank3 = st.columns(3)
    with c_bank1:
        banca_inicial = st.number_input("BANCA INICIAL", min_value=1.0, value=float(banca_inicial_default), step=10.0, key="banca_inicial_v2")
        if st.button("💾 GUARDAR BANCA INICIAL", key="save_banca"):
            pd.DataFrame([{"banca_inicial": banca_inicial, "fecha": datetime.datetime.now().strftime("%d/%m/%Y")}]).to_csv(path_banca, index=False)
            st.success(f"Banca inicial guardada: {banca_inicial}"); st.rerun()
    with c_bank2:
        st.metric("BANCA ACTUAL", f"{banca_actual:.2f}€", f"{beneficio_total:+.2f}€")
    with c_bank3:
        st.metric("BENEFICIO", f"{beneficio_total:.2f}€")

    # --- FORM APUESTA ---
    c1, c2, c3 = st.columns(3)
    with c1:
        liga_ap = st.selectbox("LIGA", ligas_base, key="liga_agenda_v2")
    if liga_ap == "Combinadas":
        liga_manual_ap = st.text_input("LIGA A MANO", value="", key="liga_combi_v2", placeholder="Ej: COMBINADA CHAMPIONS + LIGA")
        liga_ap = liga_manual_ap.strip() if liga_manual_ap.strip() else "Combinadas"
        eq_combi_txt = st.text_area("EQUIPOS COMBINADA (1 por línea)", placeholder="QPR\nSTURM GRAZ\nNURNBERG", key="eq_combi_v2", height=70)
        _eqs_combi = [x.strip() for x in eq_combi_txt.splitlines() if x.strip()]
        eq1_ap = " + ".join(_eqs_combi) if _eqs_combi else ""
        eq2_ap = ""
    else:
        with c2:
            if liga_ap in ["2ª Singapur","Ligas random"]:
                eq1_ap = st.text_input("EQUIPO 1 (LOCAL)", value="", key="eq1_manual_v2")
            else:
                eq1_ap = st.selectbox("EQUIPO 1 (LOCAL)", equipos_base, key="eq1_agenda_v2")
        with c3:
            if liga_ap in ["2ª Singapur","Ligas random"]:
                eq2_ap = st.text_input("EQUIPO 2 (VISITANTE)", value="", key="eq2_manual_v2")
            else:
                eq2_ap = st.selectbox("EQUIPO 2 (VISITANTE)", equipos_base, key="eq2_agenda_v2")

    c4, c5, c6, c7 = st.columns(4)
    with c4:
        minuto_ap = st.number_input("MINUTO", min_value=0, max_value=120, value=80, key="min_agenda_v2")
    with c5:
        cuota_ap = st.number_input("CUOTA", min_value=1.01, max_value=100.0, value=2.10, step=0.05, format="%.2f", key="cuota_agenda_v2")
    with c6:
        importe_ap = st.number_input("IMPORTE €", min_value=0.5, max_value=10000.0, value=10.0, step=1.0, key="importe_agenda_v2")
    with c7:
        resultado_ap = st.selectbox("RESULTADO", ["PENDIENTE","GANADA","PERDIDA","NULA"], key="res_agenda_v2")

    texto_ap = st.text_area("QUE METI", placeholder="Ej: GOL 80-90 QPR, OVER 1.5...", key="texto_agenda_v2", height=70)

    # calculo preview
    if resultado_ap == "GANADA":
        benef_preview = importe_ap * cuota_ap - importe_ap
    elif resultado_ap == "PERDIDA":
        benef_preview = -importe_ap
    else:
        benef_preview = 0.0
    # --- ALARMA PRE-GUARDAR: EDGE / PLANO / ROJO ---
    try:
        _hist = _leer_agenda() if path_agenda.exists() else pd.DataFrame()
        def _veredicto(sub, nombre):
            if sub.empty or len(sub) < 2:
                return f"⚪ {nombre}: SIN DATOS ({len(sub)} apuestas)"
            ben = pd.to_numeric(sub['Beneficio'], errors='coerce').fillna(0).sum()
            gw = (sub['Resultado']=="GANADA").sum()
            if ben > 2: return f"🟢 {nombre}: TIENES EDGE | {gw}/{len(sub)} | {ben:+.0f}€"
            if ben >= -2: return f"🟡 {nombre}: AQUÍ PLANO | {gw}/{len(sub)} | {ben:+.0f}€"
            return f"🔴 {nombre}: AQUÍ SUELE SER ROJO | {gw}/{len(sub)} | {ben:+.0f}€"
        _h = _hist[_hist['Resultado'].isin(['GANADA','PERDIDA'])].copy() if not _hist.empty else pd.DataFrame()
        if not _h.empty:
            _h['Liga_N'] = _h['Liga'].apply(_norm_liga)
            _liga_n = _norm_liga(liga_ap)
            _v_liga = _veredicto(_h[_h['Liga_N']==_liga_n], f"LIGA {_liga_n or '-'}")
            _v_min = _veredicto(_h[(pd.to_numeric(_h['Minuto'], errors='coerce')>=minuto_ap-5) & (pd.to_numeric(_h['Minuto'], errors='coerce')<=minuto_ap+5)], f"MINUTO ~{minuto_ap}'")
            _v_cuota = _veredicto(_h[(pd.to_numeric(_h['Cuota'], errors='coerce')>=cuota_ap-0.5) & (pd.to_numeric(_h['Cuota'], errors='coerce')<=cuota_ap+0.5)], f"CUOTA ~@{cuota_ap:.2f}")
            _rojos = sum(["🔴" in x for x in [_v_liga, _v_min, _v_cuota]])
            _verdes = sum(["🟢" in x for x in [_v_liga, _v_min, _v_cuota]])
            if _rojos >= 2: _titulo = "🔴 NO LO METAS - 2 o más en rojo"; _bg = "#3d0a0a"
            elif _verdes >= 2: _titulo = "🟢 TIENES EDGE - dale"; _bg = "#0a3d24"
            elif _rojos == 1: _titulo = "🟡 CUIDADO - 1 en rojo"; _bg = "#3d320a"
            else: _titulo = "🟡 SIN EDGE CLARO"; _bg = "#222"
            st.markdown(f"<div style='background:{_bg};color:#fff;font-family:monospace;font-size:11px;font-weight:900;padding:8px;border-radius:6px;line-height:1.8'>{_titulo}<br>{_v_liga}<br>{_v_min}<br>{_v_cuota}</div>", unsafe_allow_html=True)
    except Exception as _e:
        pass

    if st.button("💾 GUARDAR APUESTA CON BANCA", key="guardar_agenda_v2"):
        if resultado_ap == "GANADA":
            beneficio = importe_ap * cuota_ap - importe_ap
        elif resultado_ap == "PERDIDA":
            beneficio = -importe_ap
        else:
            beneficio = 0.0
        
        nueva_banca = banca_actual + beneficio if resultado_ap != "PENDIENTE" else banca_actual

        liga_ap = _norm_liga(liga_ap)
        nueva = {
            "Fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Liga": liga_ap,
            "Equipo1": eq1_ap,
            "Equipo2": eq2_ap,
            "Minuto": minuto_ap,
            "Cuota": cuota_ap,
            "Importe": importe_ap,
            "Resultado": resultado_ap,
            "Beneficio": round(beneficio,2),
            "Banca": round(nueva_banca,2),
            "Apuesta": texto_ap
        }
        df_new = pd.DataFrame([nueva])
        if path_agenda.exists():
            df_old = _leer_agenda()
            # migrar columnas viejas si faltan
            for col in ["Importe","Resultado","Beneficio","Banca"]:
                if col not in df_old.columns:
                    df_old[col] = 0 if col!="Resultado" else "PENDIENTE"
            df_all = pd.concat([df_old, df_new], ignore_index=True)
        else:
            df_all = df_new
        
        # RECALCULA TODA LA BANCA EN ORDEN PARA NO DESFASE
        df_all['Beneficio'] = pd.to_numeric(df_all['Beneficio'], errors='coerce').fillna(0)
        banca_run = banca_inicial
        bancas = []
        for _, r in df_all.iterrows():
            if r['Resultado'] == "PENDIENTE":
                bancas.append(round(banca_run,2))
            else:
                banca_run += float(r['Beneficio'])
                bancas.append(round(banca_run,2))
        df_all['Banca'] = bancas
        
        df_all.to_csv(path_agenda, index=False, encoding='utf-8-sig')
        st.success(f"Guardada: {eq1_ap} vs {eq2_ap} {resultado_ap} {beneficio:+.2f}€ | Banca {banca_run:.2f}€")
        st.rerun()

    # --- EDITAR RESULTADO RAPIDO ---
    if path_apuestas.exists() or path_agenda.exists():
        df_ag = _leer_agenda()
        if not df_ag.empty:
            # stats
            tot = len(df_ag)
            gan = len(df_ag[df_ag['Resultado']=="GANADA"]) if 'Resultado' in df_ag.columns else 0
            per = len(df_ag[df_ag['Resultado']=="PERDIDA"]) if 'Resultado' in df_ag.columns else 0
            pen = len(df_ag[df_ag['Resultado']=="PENDIENTE"]) if 'Resultado' in df_ag.columns else 0
            stake_tot = pd.to_numeric(df_ag['Importe'], errors='coerce').fillna(0).sum() if 'Importe' in df_ag.columns else 0
            # --- DONDE GANO / DONDE FALLO ---
            try:
                _a = df_ag.copy()
                _a['Importe'] = pd.to_numeric(_a['Importe'], errors='coerce').fillna(0)
                _a['Beneficio'] = pd.to_numeric(_a['Beneficio'], errors='coerce').fillna(0)
                _a['Minuto'] = pd.to_numeric(_a['Minuto'], errors='coerce').fillna(0)
                _a['Cuota'] = pd.to_numeric(_a['Cuota'], errors='coerce').fillna(0)
                _a = _a[_a['Resultado'].isin(['GANADA','PERDIDA'])]
                _a['Liga'] = _a['Liga'].apply(_norm_liga)
                def _resumen_grupo(d, col):
                    rows=[]
                    for k, g in d.groupby(col):
                        n=len(g); gw=(g['Resultado']=='GANADA').sum(); ben=g['Beneficio'].sum(); stak=g['Importe'].sum()
                        roi=(ben/stak*100) if stak else 0
                        if ben > 2: _c="#00E676"; _bg="#0a3d24"; _tag="🟢 GANO"; _ord=0
                        elif ben >= -2: _c="#FFD600"; _bg="#3d320a"; _tag="🟡 PLANO"; _ord=1
                        else: _c="#FF5252"; _bg="#3d0a0a"; _tag="🔴 PIERDO"; _ord=2
                        _line=f"<span style='background:{_bg};color:{_c};font-weight:900;padding:1px 5px;border-radius:4px'>{_tag}</span> {k}: {gw}/{n} ({gw/n*100:.0f}%) | <b style='color:{_c}'>{ben:+.0f}€ | ROI {roi:+.0f}%</b>"
                        rows.append((_ord, -ben, _line))
                    rows.sort()
                    return "<br>".join([r[2] for r in rows]) if rows else "-"
                _a['MIN_RANGO'] = pd.cut(_a['Minuto'], [-1,60,75,85,90,200], labels=["0-60'","60-75'","75-85'","85-90'","90'+"])
                _a['CUOTA_RANGO'] = pd.cut(_a['Cuota'], [0,2,3,4,100], labels=["@1-2","@2-3","@3-4","@4+"])
                _liga_txt = _resumen_grupo(_a, 'Liga')
                _min_txt = _resumen_grupo(_a, 'MIN_RANGO')
                _cuota_txt = _resumen_grupo(_a, 'CUOTA_RANGO')
                st.markdown(f"<div style='font-family:monospace;font-size:10px;background:#111;color:#fff;padding:8px;border:1px solid #333;border-radius:6px;line-height:1.7'><b style='color:#00E676'>POR LIGA:</b><br>{_liga_txt}<br><br><b style='color:#FFD600'>POR MINUTO:</b><br>{_min_txt}<br><br><b style='color:#00BFFF'>POR CUOTA:</b><br>{_cuota_txt}</div>", unsafe_allow_html=True)
            except Exception as _e:
                st.caption(f"Sin stats: {_e}")
            
            # tabla editable - cambia PENDIENTE a GANADA/PERDIDA y recalcula banca
            for i, r in df_ag.tail(30).sort_index(ascending=False).iterrows():
                col = "#0f8105" if r.get('Resultado')=="GANADA" else "#f31818" if r.get('Resultado')=="PERDIDA" else "#666"
                benef = r.get('Beneficio',0); banca_r = r.get('Banca', banca_actual)
                _liga_s = str(r.get('Liga','') or '')[:12]
                _e1_s = str(r.get('Equipo1','') or '')[:10]
                _e2_s = str(r.get('Equipo2','') or '')[:10]
                st.markdown(f"<div style='background:#1a1a1a;color:#fff;font-family:monospace;font-size:11px;font-weight:900;padding:6px;border-radius:6px 6px 0 0'>[<span style='color:{col}'>{r.get('Resultado','-')}</span>] ID:{i} {r.get('Fecha','')} | {_liga_s} | {_e1_s} vs {_e2_s} | {r.get('Minuto','')}' | @{r.get('Cuota','')} x {r.get('Importe',0)}€ = {benef:+.2f}€ | Banca {banca_r}€</div>", unsafe_allow_html=True)
                with st.expander("✏️ EDITAR ESTA APUESTA", expanded=False):
                    c_e1, c_e2 = st.columns(2)
                    with c_e1:
                        n_liga = st.text_input("LIGA", value=str(r.get('Liga','')), key=f"e_liga_{i}")
                        n_eq1 = st.text_input("EQUIPO 1", value=str(r.get('Equipo1','')), key=f"e_eq1_{i}")
                        n_min = st.number_input("MINUTO", min_value=0, max_value=120, value=int(float(r.get('Minuto',80))), key=f"e_min_{i}")
                        n_imp = st.number_input("IMPORTE €", min_value=0.5, value=float(r.get('Importe',10)), key=f"e_imp_{i}")
                    with c_e2:
                        n_eq2 = st.text_input("EQUIPO 2", value=str(r.get('Equipo2','')), key=f"e_eq2_{i}")
                        n_cuota = st.number_input("CUOTA", min_value=1.01, value=max(1.01, float(pd.to_numeric(r.get('Cuota', 2.1), errors='coerce') or 2.1)), step=0.05, key=f"e_cuota_{i}")
                        n_res = st.selectbox("RESULTADO", ["GANADA","PERDIDA","NULA","PENDIENTE"], index=["GANADA","PERDIDA","NULA","PENDIENTE"].index(r.get('Resultado','PENDIENTE')) if r.get('Resultado') in ["GANADA","PERDIDA","NULA","PENDIENTE"] else 3, key=f"e_res_{i}")
                    n_txt = st.text_input("QUE METI", value=str(r.get('Apuesta','')), key=f"e_txt_{i}")
                    c_g, c_b = st.columns(2)
                    with c_g:
                        if st.button("💾 GUARDAR CAMBIOS", key=f"save_e_{i}", use_container_width=True):
                            df_ag.loc[i,'Liga']=_norm_liga(n_liga); df_ag.loc[i,'Equipo1']=n_eq1; df_ag.loc[i,'Equipo2']=n_eq2; df_ag.loc[i,'Minuto']=n_min; df_ag.loc[i,'Cuota']=n_cuota; df_ag.loc[i,'Importe']=n_imp; df_ag.loc[i,'Resultado']=n_res; df_ag.loc[i,'Apuesta']=n_txt
                            df_ag.loc[i,'Beneficio']=round(n_imp*n_cuota-n_imp,2) if n_res=="GANADA" else round(-n_imp,2) if n_res=="PERDIDA" else 0.0
                            banca_run=banca_inicial; bancas=[]
                            for _, rr in df_ag.iterrows():
                                if rr['Resultado']=="PENDIENTE": bancas.append(round(banca_run,2))
                                else: banca_run+=float(rr['Beneficio']); bancas.append(round(banca_run,2))
                            df_ag['Banca']=bancas; df_ag.to_csv(path_agenda, index=False, encoding='utf-8-sig'); st.rerun()
                    with c_b:
                        if st.button("🗑 BORRAR ESTA", key=f"del_e_{i}", use_container_width=True):
                            df_ag = df_ag.drop(index=i); banca_run=banca_inicial; bancas=[]
                            for _, rr in df_ag.iterrows():
                                if rr['Resultado']=="PENDIENTE": bancas.append(round(banca_run,2))
                                else: banca_run+=float(rr['Beneficio']); bancas.append(round(banca_run,2))
                            df_ag['Banca']=bancas; df_ag.to_csv(path_agenda, index=False, encoding='utf-8-sig'); st.rerun()
            
            c_edit1, c_edit2, c_edit3 = st.columns([1,1,1])
            with c_edit1:
                idx_edit = st.number_input("ID a editar (fila)", min_value=0, max_value=len(df_ag)-1, value=int(len(df_ag)-1), key="idx_edit_banca")
            with c_edit2:
                nuevo_res = st.selectbox("Nuevo resultado", ["GANADA","PERDIDA","NULA","PENDIENTE"], key="nuevo_res_banca")
            with c_edit3:
                if st.button("✏️ ACTUALIZAR RESULTADO", key="upd_banca"):
                    df_ag.loc[idx_edit, 'Resultado'] = nuevo_res
                    imp = float(df_ag.loc[idx_edit, 'Importe'])
                    cuo = float(df_ag.loc[idx_edit, 'Cuota'])
                    if nuevo_res == "GANADA":
                        df_ag.loc[idx_edit, 'Beneficio'] = round(imp*cuo - imp,2)
                    elif nuevo_res == "PERDIDA":
                        df_ag.loc[idx_edit, 'Beneficio'] = round(-imp,2)
                    else:
                        df_ag.loc[idx_edit, 'Beneficio'] = 0.0
                    # recalcular banca corrida
                    banca_run = banca_inicial
                    bancas = []
                    for _, rr in df_ag.iterrows():
                        if rr['Resultado'] == "PENDIENTE":
                            bancas.append(round(banca_run,2))
                        else:
                            banca_run += float(rr['Beneficio'])
                            bancas.append(round(banca_run,2))
                    df_ag['Banca'] = bancas
                    df_ag.to_csv(path_agenda, index=False, encoding='utf-8-sig')
                    st.success(f"Actualizado ID {idx_edit} -> {nuevo_res} | Banca {banca_run:.2f}"); st.rerun()

            # --- COPIAR ACERTADAS / FALLADAS ---
            try:
                _gan = df_ag[df_ag['Resultado']=="GANADA"]
                _per = df_ag[df_ag['Resultado']=="PERDIDA"]
                _txt_gan = "\n".join([f"✅ GANADA | {r['Fecha']} | {_norm_liga(r['Liga'])} | {r['Equipo1']} vs {r['Equipo2']} | {r['Minuto']}' | @{r['Cuota']} x {r.get('Importe',0)}€ = {r.get('Beneficio',0):+.2f}€ | {r['Apuesta']}" for _, r in _gan.iterrows()]) or "Sin acertadas"
                _txt_per = "\n".join([f"❌ FALLADA | {r['Fecha']} | {_norm_liga(r['Liga'])} | {r['Equipo1']} vs {r['Equipo2']} | {r['Minuto']}' | @{r['Cuota']} x {r.get('Importe',0)}€ = {r.get('Beneficio',0):+.2f}€ | {r['Apuesta']}" for _, r in _per.iterrows()]) or "Sin falladas"
                import html as _html_ag, streamlit.components.v1 as _comp_ag
                _txt_todo = f"ACERTADAS ({len(_gan)}):\n{_txt_gan}\n\nFALLADAS ({len(_per)}):\n{_txt_per}"
                _comp_ag.html(f"""
                <textarea id="txt_gan_ag" style="position:absolute;left:-9999px;">{_html_ag.escape(_txt_gan)}</textarea>
                <textarea id="txt_per_ag" style="position:absolute;left:-9999px;">{_html_ag.escape(_txt_per)}</textarea>
                <textarea id="txt_todo_ag" style="position:absolute;left:-9999px;">{_html_ag.escape(_txt_todo)}</textarea>
                <div style="display:flex;gap:6px">
                <button onclick="navigator.clipboard.writeText(document.getElementById('txt_gan_ag').value).then(()=>{{this.innerText='✓ COPIADO'}})" style="flex:1;background:#0f8105;color:#fff;border:none;border-radius:6px;padding:10px;font-weight:900;cursor:pointer;">📋 COPIAR ACERTADAS ({len(_gan)})</button>
                <button onclick="navigator.clipboard.writeText(document.getElementById('txt_per_ag').value).then(()=>{{this.innerText='✓ COPIADO'}})" style="flex:1;background:#f31818;color:#fff;border:none;border-radius:6px;padding:10px;font-weight:900;cursor:pointer;">📋 COPIAR FALLADAS ({len(_per)})</button>
                <button onclick="navigator.clipboard.writeText(document.getElementById('txt_todo_ag').value).then(()=>{{this.innerText='✓ COPIADO'}})" style="flex:1;background:#0A2342;color:#fff;border:none;border-radius:6px;padding:10px;font-weight:900;cursor:pointer;">📋 COPIAR TODO</button>
                </div>
                """, height=45)
            except:
                pass

            if st.button("🗑 BORRAR TODO + RESET BANCA", key="borrar_agenda_v2"):
                path_agenda.unlink(missing_ok=True)
                st.warning("Agenda borrada - Banca vuelve a inicial")
                st.rerun()
# ================= FIN BLOQUE AGENDA V2 =================
###############
###############
###########################################################################
###############
###############
###############
###############
###############
###############
###############
###############
###############
###########################################################################
###############
###############
###############
###############
###############
###############
###############
###############
###############



with st.expander("JUGADORES - GOLES Y ASISTENCIAS", expanded=False):
    import pathlib, json

    @st.cache_data(show_spinner=False)
    def cargar_base_jugadores_fix():
        def _find_file(name):
            for b in [pathlib.Path(name), pathlib.Path(__file__).parent.resolve()/name, pathlib.Path("/mnt/data")/name]:
                if b.exists():
                    return b
            return None
        def _load_parquet_concat(namelist):
            dfs=[]
            for nm in namelist:
                p=_find_file(nm)
                if p:
                    try:
                        dfs.append(pd.read_parquet(p))
                    except:
                        pass
            if not dfs:
                return pd.DataFrame()
            df_all=pd.concat(dfs, ignore_index=True)
            return df_all
        def _load_csv(name):
            p=_find_file(name)
            if not p:
                return pd.DataFrame()
            try:
                return pd.read_csv(p, on_bad_lines='skip')
            except:
                return pd.DataFrame()

        # PRIMERO PARQUET, SI NO HAY PARQUET ENTONCES CSV
        df_p = _load_parquet_concat(["base_partidos_europa.parquet","base_partidos_resto.parquet"])
        if df_p.empty:
            df_p = _load_csv("base_partidos.csv")
        df_g = _load_parquet_concat(["base_goles_europa.parquet","base_goles_resto.parquet"])
        # fusiona CSV para recuperar filas que faltan en parquet (ej: J3 【entity-Felix¦canonical_name=FELIX NMECHA】 80')
        _df_g_csv = _load_csv("base_goles.csv")
        if not _df_g_csv.empty:
            if df_g.empty:
                df_g = _df_g_csv
            else:
                _cols = list(dict.fromkeys(list(df_g.columns) + list(_df_g_csv.columns)))
                df_g = pd.concat([df_g.reindex(columns=_cols), _df_g_csv.reindex(columns=_cols)], ignore_index=True)
                _dedup = [c for c in ['fixture_id','goleador','minuto','tipo'] if c in df_g.columns]
                if _dedup:
                    df_g = df_g.drop_duplicates(subset=_dedup, keep='first')
        if not df_p.empty and 'fixture_id' in df_p.columns:
            df_p = df_p.drop_duplicates(subset=['fixture_id'], keep='last')

        if not df_p.empty:
            df_p['Date'] = pd.to_datetime(df_p['Date'], dayfirst=True, errors='coerce')
            df_p = df_p.sort_values(['League','Season','Date']).copy()
            df_p['Jornada'] = 0
            for (l,s), g in df_p.groupby(['League','Season'], sort=False):
                g=g.sort_values('Date')
                idxs=g.index.to_numpy()
                n=len(pd.unique(pd.concat([g['HomeTeam'], g['AwayTeam']]).dropna()))
                ppj=max(n//2,1)
                df_p.loc[idxs,'Jornada']=(np.arange(len(idxs))//ppj)+1

        # goles dict por fixture
        ev = {}
        if not df_g.empty:
            df_g['fid'] = df_g['fixture_id'].astype(str).str.split('.').str[0]
            _col_min = 'minuto' if 'minuto' in df_g.columns else ('min' if 'min' in df_g.columns else 'minuto')
            df_g['min_n'] = pd.to_numeric(df_g.get(_col_min,0), errors='coerce').fillna(0).astype(int)
            for fid, sub in df_g.groupby('fid'):
                lst=[]
                for _, r in sub.iterrows():
                    gol=str(r.get('goleador', r.get('scorer',''))).strip().lower()
                    asi=str(r.get('asistente', r.get('assist',''))).strip().lower()
                    if gol in ['m. beier','m beier']: gol='maximilian beier'
                    if asi in ['m. beier','m beier']: asi='maximilian beier'
                    if gol in ['s. guirassy','s guirassy']: gol='serhou guirassy'
                    if asi in ['s. guirassy','s guirassy']: asi='serhou guirassy'
                    if gol in ['d. mokwa ntusu','d mokwa ntusu','d. mokwa','d mokwa']: gol='david mokwa'
                    if asi in ['d. mokwa ntusu','d mokwa ntusu','d. mokwa','d mokwa']: asi='david mokwa'
                    if gol in ['l. petkov','l petkov']: gol='lukas petkov'
                    if asi in ['l. petkov','l petkov']: asi='lukas petkov'
                    if gol in ['f. nino','f nino']: gol='fernando nino rodriguez'
                    if asi in ['f. nino','f nino']: asi='fernando nino rodriguez'
                    if gol in ['l. cepeda','l cepeda']: gol='lucas cepeda'
                    if asi in ['l. cepeda','l cepeda']: asi='lucas cepeda'
                    if gol in ['h. mochizuki','h mochizuki']: gol='henry heroki mochizuki'
                    if asi in ['h. mochizuki','h mochizuki']: asi='henry heroki mochizuki'
                    if gol in ['t. akimoto','t akimoto']: gol='takahiro akimoto'
                    if asi in ['t. akimoto','t akimoto']: asi='takahiro akimoto'
                    if gol in ['t. yengi','t yengi']: gol='tete yengi'
                    if asi in ['t. yengi','t yengi']: asi='tete yengi'
                    if gol.lower() in ['','nan','none']: gol=""
                    if asi.lower() in ['','nan','none']: asi=""
                    lst.append({
                        'm': int(r.get('min_n',0)),
                        'team': normaliza(r.get('equipo', r.get('team', r.get('Team','')))),
                        'gol': gol,
                        'asi': asi,
                        'tipo': str(r.get('tipo',''))
                    })
                ev[fid]=lst
        return df_p, ev, df_g

    df_p_jug, ev_jug, df_g_jug = cargar_base_jugadores_fix()

    if df_p_jug.empty:
        st.warning("No hay base_partidos_europa/resto")
    else:
        # --- DESPLEGABLE EQUIPOS ---
        ligas_jug = ["TODAS"] + sorted(df_p_jug['League'].dropna().unique().tolist())
        c_liga_j, c_eq_j = st.columns([1,2])
        with c_liga_j:
            liga_sel_jug = st.selectbox("LIGA JUGADORES", ligas_jug, key="liga_jug_v1")
        df_liga_jug = df_p_jug if liga_sel_jug=="TODAS" else df_p_jug[df_p_jug['League']==liga_sel_jug]

        equipos_jug = sorted(pd.concat([df_liga_jug['HomeTeam'], df_liga_jug['AwayTeam']]).dropna().astype(str).unique().tolist())
        with c_eq_j:
            equipo_sel_jug = st.selectbox("EQUIPO", ["-"]+equipos_jug, key="equipo_jug_v1")

        if equipo_sel_jug != "-":
            norm_eq_jug = normaliza(equipo_sel_jug)
            up_eq_jug = equipo_sel_jug.upper().strip()

            df_team_jug = df_liga_jug[(df_liga_jug['HomeTeam'].astype(str).str.upper().str.strip()==up_eq_jug) | (df_liga_jug['AwayTeam'].astype(str).str.upper().str.strip()==up_eq_jug)]
            if df_team_jug.empty:
                df_team_jug = df_liga_jug[(df_liga_jug['HomeTeam'].apply(lambda x: normaliza(x)==norm_eq_jug)) | (df_liga_jug['AwayTeam'].apply(lambda x: normaliza(x)==norm_eq_jug))]

            df_team_jug = df_team_jug.sort_values('Date')
            df_team_jug['Jornada'] = range(1, len(df_team_jug)+1)

            # mapa jornada -> fixture_id + rivales
            jornada_map = {}
            for _, r in df_team_jug.iterrows():
                j=int(r.get('Jornada',0))
                fid=str(r.get('fixture_id','')).split('.')[0]
                jornada_map[j] = fid

            max_j = len(df_team_jug)

            # recolecta jugadores del equipo
            jugadores = {}
            for fid in jornada_map.values():
                for e in ev_jug.get(fid, []):
                    if 'Missed' in e.get('tipo',''): continue
                    if 'Own Goal' in e.get('tipo',''): continue
                    if e['team'] != norm_eq_jug:
                        continue
                    if e['gol']:
                        jugadores.setdefault(e['gol'], {})
                    if e['asi']:
                        jugadores.setdefault(e['asi'], {})

            if not jugadores:
                st.info(f"{equipo_sel_jug} sin goleadores/asistentes registrados")
            else:
                # para cada jugador construye J1..Jmax
                for nombre_jug in sorted(jugadores.keys()):
                    # por jornada busca eventos
                    tokens = []
                    tokens_copy = []  # para copiar limpio
                    for j in range(1, max_j+1):
                        fid = jornada_map.get(j)
                        if not fid:
                            tokens.append(f"<span style='background:#eee;color:#888;padding:1px 4px;border-radius:3px'>J{j}_</span>")
                            tokens_copy.append(f"J{j}_")
                            continue
                        evs = ev_jug.get(fid, [])
                        hits=[]
                        for e in evs:
                            if e['team'] != norm_eq_jug: continue
                            if 'Missed' in e.get('tipo',''): continue
                            if 'Own Goal' in e.get('tipo',''): continue
                            m=e['m']
                            if e['gol'] == nombre_jug:
                                hits.append(f"GOL_{m}'")
                            if e['asi'] == nombre_jug:
                                hits.append(f"ASIST_{m}'")
                        if not hits:
                            tokens.append(f"<span style='background:#eee;color:#888;padding:1px 4px;border-radius:3px;margin-right:2px'>J{j}_</span>")
                            tokens_copy.append(f"J{j}_")
                        else:
                            inner = "_".join(hits)
                            # verde gol, azul asist
                            if "GOL" in inner:
                                col="#0f8105"
                            else:
                                col="#1E90FF"
                            tokens.append(f"<span style='background:{col};color:#fff;padding:1px 5px;border-radius:3px;margin-right:2px;font-weight:900'>J{j}_{inner}</span>")
                            tokens_copy.append(f"J{j}_{inner}")

                    # resumen X/Y para cabecera - cuenta cada GOL/ASIST, no cada token
                    goles_tot = sum(t.count("GOL") for t in tokens_copy)
                    asis_tot = sum(t.count("ASIST") for t in tokens_copy)
                    # conteo jornadas con algo
                    nj_con = sum(1 for t in tokens_copy if "GOL" in t or "ASIST" in t)

                    html_jug = f"<div style='font-family:monospace;background:#fff;border:1px solid #000;border-radius:8px;padding:8px;margin:8px 0'><div style='font-weight:900;font-size:12px;background:#000;color:#fff;padding:3px 6px;border-radius:4px;display:inline-block'>{nombre_jug.upper()} | G:{goles_tot} A:{asis_tot} | {nj_con}/{max_j}</div><div style='margin-top:6px;line-height:1.9;white-space:normal;word-break:break-word'>{' '.join(tokens)}</div></div>"
                    st.markdown(html_jug, unsafe_allow_html=True)

                # --- BLOQUE COPIAR ---
                import html as _html
                txt_copy = ""
                for nombre_jug in sorted(jugadores.keys()):
                    line=[]
                    for j in range(1, max_j+1):
                        fid=jornada_map.get(j)
                        if not fid:
                            line.append(f"J{j}_")
                            continue
                        hits=[]
                        for e in ev_jug.get(fid, []):
                            if e['team'] != norm_eq_jug: continue
                            if 'Missed' in e.get('tipo',''): continue
                            if 'Own Goal' in e.get('tipo',''): continue
                            if e['gol']==nombre_jug: hits.append(f"GOL_{e['m']}'")
                            if e['asi']==nombre_jug: hits.append(f"ASIST_{e['m']}'")
                        if not hits:
                            line.append(f"J{j}_")
                        else:
                            line.append(f"J{j}_{'_'.join(hits)}")
                    txt_copy += f"{nombre_jug.upper()}: {', '.join(line)}\n"

                safe = _html.escape(txt_copy)
                import streamlit.components.v1 as components
                components.html(f"""
                <textarea id="txt_jug" style="position:absolute;left:-9999px">{safe}</textarea>
                <button onclick="navigator.clipboard.writeText(document.getElementById('txt_jug').value).then(()=>{{let b=document.getElementById('btn_jug'); b.innerText='✓ COPIADO'; b.style.background='#0f8105'}})"
                id="btn_jug" style="width:100%;background:#0A2342;color:white;border:none;border-radius:6px;padding:10px;font-weight:900">📋 COPIAR JUGADORES {equipo_sel_jug} ({len(jugadores)})</button>
                """, height=55)
          
          
          ##################################################### ##################################################### ##################################################### #####################################################
