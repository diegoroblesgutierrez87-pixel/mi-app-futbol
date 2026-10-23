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

    ev = {}
    if dg_all.empty:
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

with c2: eq1 = st.selectbox("Equipo 1", ["Ninguno"] + equipos)
with c3: eq1_loc = st.selectbox("Eq1 Condición", ["Todos","Local","Visitante"], key="eq1loc")
c4,c5 = filtros.columns(2)
with c4: eq2 = st.selectbox("Equipo 2", ["Ninguno"] + [e for e in equipos if e.upper() != str(eq1).upper()])
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
            # ahora color del gol = color del resultado si es mi equipo, no subrayado
            color_gol = col if es_mio else "#000"
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
            if is_local:
                html_gol = f"<div style='text-align:left; color:{color_gol}; {extra_style} margin:0; padding:0; line-height:1.0; font-size:11px'>{min_txt} {alterador.strip()}{extra_jug}</div>"
            else:
                html_gol = f"<div style='text-align:right; color:{color_gol}; {extra_style} margin:0; padding:0; line-height:1.0; font-size:11px'>{min_txt} {alterador.strip()}{extra_jug}</div>"
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
                    mins_1t.append(f"<span style='color:#000'>{x}'</span>")
                else:
                    mins_2t.append(f"<span style='color:#000'>{x}'</span>")
            except:
                mins_1t.append(f"<span style='color:#000'>{x}'</span>")

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
    # --- TODA LA LINEA COLOREADA + SUBRAYADO EQUIPO FILTRO ---
    h_norm_chk = normaliza(h)
    a_norm_chk = normaliza(a)
    col_line = col_j
    h_html = h
    a_html = a
    if current_eq_norm:
        col_line = col
        if h_norm_chk == current_eq_norm:
            h_html = f"<span style='text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:3px'>{h}</span>"
        elif a_norm_chk == current_eq_norm:
            a_html = f"<span style='text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:3px'>{a}</span>"
    return f"<div style='font-family:monospace;font-size:11px;padding:6px 4px;border-bottom:2px solid #333;line-height:1.2;max-width:380px;margin:0 auto'><div style='text-align:left;color:{col_line};font-weight:900'>|Jornada {j}| {h_html} vs {a_html}</div><div style='text-align:center;font-weight:900;word-break:break-word'>{extra}</div><div style='text-align:center;font-weight:900;margin-top:4px'><span style='background:#0A2342;color:#fff;padding:2px 10px;border-radius:3px'>Final {hg}-{ag}</span></div><div style='text-align:center;color:#666;font-weight:700;font-size:10px;margin-top:2px'>[1ª parte {hthg}-{htag}]</div><div style='color:#000;white-space:normal;word-break:break-word;line-height:1.1;margin-top:3px'>{txt_mins}</div>{mom_html}</div>"

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
                j_str = ", ".join([f"J{j}" for j in jors_r]) if jors_r else ""
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
            html_partidos += f"<div style='font-family:monospace;font-weight:900;background:{color_pct};color:#fff;padding:4px 6px;margin:8px 0 2px 0'>{team} {loc_cond} - {liga_team} | {filtro_tipo} {pct:.0f}% ({ok}/{total})</div>"
            for _, r in d_team_cumple.iterrows():
                html_partidos += fmt_rapido(r.to_dict(), [normaliza(team)], normaliza(team), team)
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
###################################################################
################################################################### CLONADO FIX3 - DOBLE
# 
###################################################################
################################################################### CLONADO FIX3 - DOBLE100% INDEPENDIENTE
with st.expander("PREDICCION - PARTIDOS FUTUROS + HISTORIAL FIX 3", expanded=False):
    import pathlib, unicodedata

    @st.cache_data(show_spinner=False)
    def cargar_futuro_fix3():
        p = pathlib.Path("/mnt/data/Calendario-Futuro-Ligas-Tu-Csv-LIMPIO.csv")
        if not p.exists():
            for q in [pathlib.Path(__file__).parent.resolve(), pathlib.Path(".").resolve()]:
                if (q / "Calendario-Futuro-Ligas-Tu-Csv-LIMPIO.csv").exists():
                    p = q / "Calendario-Futuro-Ligas-Tu-Csv-LIMPIO.csv"
                    break
        if not p.exists():
            return pd.DataFrame()
        df_fut = pd.read_csv(p, on_bad_lines='skip')
        df_fut['Date'] = pd.to_datetime(df_fut['Date'], errors='coerce')
        return df_fut

    df_futuro_fix3 = cargar_futuro_fix3()
    if df_futuro_fix3.empty:
        st.warning("No encuentro Calendario-Futuro-Ligas-Tu-Csv-LIMPIO.csv en /mnt/data")
        st.stop()

    import json, time
    FILE_PERSIST_PRED_FIX3 = pathlib.Path(__file__).parent.resolve() / ".persist_pred_48h_fix3.json"
    TTL_48H = 48 * 3600
    def _load_persist_48h_fix3():
        if not FILE_PERSIST_PRED_FIX3.exists():
            return {}
        try:
            if time.time() - FILE_PERSIST_PRED_FIX3.stat().st_mtime > TTL_48H:
                FILE_PERSIST_PRED_FIX3.unlink(missing_ok=True)
                return {}
            with open(FILE_PERSIST_PRED_FIX3, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    def _save_persist_48h_fix3():
        try:
            data = {
                "ligas_pred_fix3": st.session_state.get("ligas_pred_fix3", []),
                "fecha_pred_fix3": st.session_state.get("fecha_pred_fix3", "Todas"),
                "min_desde_pred_fix3": st.session_state.get("min_desde_pred_fix3", ""),
                "min_hasta_pred_fix3": st.session_state.get("min_hasta_pred_fix3", ""),
                "partidos_pred_sel_fix3": st.session_state.get("partidos_pred_sel_fix3", []),
                "eq_manual_1_fix3": st.session_state.get("eq_manual_1_fix3", []),
                "eq_manual_2_fix3": st.session_state.get("eq_manual_2_fix3", []),
                "cond_manual_1_fix3": st.session_state.get("cond_manual_1_fix3", "TODOS"),
                "cond_manual_2_fix3": st.session_state.get("cond_manual_2_fix3", "TODOS"),
                "cond_loc_pred_fix3": st.session_state.get("cond_loc_pred_fix3", "Local en casa / Visitante fuera"),
                "filtro_ht_ft_unico_2026_v9_fix3": st.session_state.get("filtro_ht_ft_unico_2026_v9_fix3", []),
            }
            with open(FILE_PERSIST_PRED_FIX3, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except:
            pass

    _persist_fix3 = _load_persist_48h_fix3()
    if "ligas_pred_fix3" not in st.session_state:
        st.session_state.ligas_pred_fix3 = _persist_fix3.get("ligas_pred_fix3") or st.query_params.get_all("ligas_pred_fix3")
    if "fecha_pred_fix3" not in st.session_state:
        st.session_state.fecha_pred_fix3 = _persist_fix3.get("fecha_pred_fix3") or st.query_params.get("fecha_pred_fix3", "Todas")
    if "min_desde_pred_fix3" not in st.session_state:
        st.session_state.min_desde_pred_fix3 = _persist_fix3.get("min_desde_pred_fix3") or st.query_params.get("min_desde_pred_fix3", "")
    if "min_hasta_pred_fix3" not in st.session_state:
        st.session_state.min_hasta_pred_fix3 = _persist_fix3.get("min_hasta_pred_fix3") or st.query_params.get("min_hasta_pred_fix3", "")
    if "partidos_pred_sel_fix3" not in st.session_state:
        st.session_state.partidos_pred_sel_fix3 = _persist_fix3.get("partidos_pred_sel_fix3") or st.query_params.get_all("partidos_pred_sel_fix3")
    if "eq_manual_1_fix3" not in st.session_state:
        st.session_state.eq_manual_1_fix3 = _persist_fix3.get("eq_manual_1_fix3") or st.query_params.get_all("eq_manual_1_fix3")
    if "eq_manual_2_fix3" not in st.session_state:
        st.session_state.eq_manual_2_fix3 = _persist_fix3.get("eq_manual_2_fix3") or st.query_params.get_all("eq_manual_2_fix3")
    if "cond_manual_1_fix3" not in st.session_state:
        st.session_state.cond_manual_1_fix3 = _persist_fix3.get("cond_manual_1_fix3") or st.query_params.get("cond_manual_1_fix3", "TODOS")
    if "cond_manual_2_fix3" not in st.session_state:
        st.session_state.cond_manual_2_fix3 = _persist_fix3.get("cond_manual_2_fix3") or st.query_params.get("cond_manual_2_fix3", "TODOS")
    if "cond_loc_pred_fix3" not in st.session_state:
        st.session_state.cond_loc_pred_fix3 = _persist_fix3.get("cond_loc_pred_fix3") or st.query_params.get("cond_loc_pred_fix3", "Local en casa / Visitante fuera")
    if "filtro_ht_ft_unico_2026_v9_fix3" not in st.session_state:
        st.session_state.filtro_ht_ft_unico_2026_v9_fix3 = _persist_fix3.get("filtro_ht_ft_unico_2026_v9_fix3") or st.query_params.get_all("filtro_ht_ft_unico_2026_v9_fix3")

    if st.button(" LIMPIAR TODO EL BLOQUE PREDICCION FIX3", key="btn_limpiar_pred_fix3", use_container_width=True):
        for k in ["ligas_pred_fix3","fecha_pred_fix3","min_desde_pred_fix3","min_hasta_pred_fix3","partidos_pred_sel_fix3","eq_manual_1_fix3","eq_manual_2_fix3","cond_manual_1_fix3","cond_manual_2_fix3","filtro_ht_ft_unico_2026_v9_fix3","cond_loc_pred_fix3"]:
            if k in st.session_state:
                del st.session_state[k]
        try:
            FILE_PERSIST_PRED_FIX3.unlink(missing_ok=True)
        except:
            pass
        st.rerun()

    _save_persist_48h_fix3()

    @st.cache_data(show_spinner=False)
    def cargar_base_europa_fix3():
        p_par = pathlib.Path("base_partidos_europa.parquet")
        if not p_par.exists():
            p_par = pathlib.Path(__file__).parent.resolve() / "base_partidos_europa.parquet"
        g_par = pathlib.Path("base_goles_europa.parquet")
        if not g_par.exists():
            g_par = pathlib.Path(__file__).parent.resolve() / "base_goles_europa.parquet"
        df_e = pd.read_parquet(p_par) if p_par.exists() else pd.DataFrame()
        if not df_e.empty:
            def _parse_fecha_base(s):
                d = pd.to_datetime(s, dayfirst=True, errors='coerce')
                if pd.isna(d):
                    d = pd.to_datetime(s, errors='coerce')
                return d
            df_e['Date'] = df_e['Date'].apply(_parse_fecha_base)
            df_e = df_e.sort_values(['League','Season','Date']).copy()
            df_e['Jornada'] = 0
            for (l_name, s_name), g_s in df_e.groupby(['League','Season'], sort=False):
                g_s = g_s.sort_values('Date')
                idxs = g_s.index.to_numpy()
                n_teams = len(pd.unique(pd.concat([g_s['HomeTeam'], g_s['AwayTeam']]).dropna()))
                ppj = max(n_teams // 2, 1)
                df_e.loc[idxs, 'Jornada'] = (np.arange(len(idxs)) // ppj) + 1
        df_g = pd.read_parquet(g_par) if g_par.exists() else pd.DataFrame()
        ev = {}
        if not df_g.empty:
            df_g['fid_str'] = df_g['fixture_id'].astype(str).str.split('.').str[0]
            df_g['m'] = pd.to_numeric(df_g.get('minuto', 0), errors='coerce').fillna(0).astype(int)
            for fid, sub in df_g.groupby('fid_str'):
                ev[fid] = [{'m': int(r.get('m', 0)), 'team': normaliza(r.get('equipo','')), 'tipo': str(r.get('tipo',''))} for _, r in sub.iterrows()]
        return df_e, ev

    df_europa_fix3, eventos_europa_fix3 = cargar_base_europa_fix3()
    df_fix3 = df_europa_fix3
    eventos_fix3 = eventos_europa_fix3

    ligas_fut_all_fix3 = sorted(df_futuro_fix3['League_CSV'].dropna().unique().tolist())
    if not df_europa_fix3.empty and 'League' in df_europa_fix3.columns:
        ligas_europa_set_fix3 = set(df_europa_fix3['League'].dropna().astype(str).tolist())
        ligas_fut_fix3 = [l for l in ligas_fut_all_fix3 if any(normaliza(l) == normaliza(le) or normaliza(l) in normaliza(le) or normaliza(le) in normaliza(l) for le in ligas_europa_set_fix3)]
        if not ligas_fut_fix3:
            keywords_eu = ["Eliteserien","Eredivisie","Bundesliga","LaLiga","Premier","Serie A","Ligue","Pro League","First League Bulgaria","Super Lig","Ekstraklasa","Primeira Liga"]
            ligas_fut_fix3 = [l for l in ligas_fut_all_fix3 if any(k.lower() in l.lower() for k in keywords_eu)]
    else:
        ligas_fut_fix3 = ligas_fut_all_fix3

    c_lp1_fix3, c_lp2_fix3, c_lp3_fix3, c_lp4_fix3 = st.columns([2,1,1,1])
    with c_lp4_fix3:
        cond_loc_pred_fix3 = st.selectbox("Filtro FIX3", ["TODOS","equipo local solamente partidos de local","equipo visitante solamente sus partidos de visitante","Local en casa / Visitante fuera"], index=3, key="cond_loc_pred_fix3")
        res_1p_tipo_fix3 = st.selectbox("Resultado 1ªP FIX3", ["TODOS","EMPATE","GANA","PIERDE","EMPATEGANA","EMPATEPIERDE","GANAPIERDE"], index=0, key="res_1p_tipo_pred_fix3")
        opciones_res_fix3 = [f"{a}-{b}_1ªP" for a in range(5) for b in range(5)] + [f"{a}-{b}_2ªP" for a in range(5) for b in range(5)]
        resultados_pred_sel_fix3 = st.multiselect("Resultado 1ªP / 2ªP FIX3", opciones_res_fix3, default=[], key="filtro_ht_ft_unico_2026_v9_fix3", placeholder="Ej: 0-0_1ªP")
        overs_sel_fix3 = st.multiselect("Overs / Unders por parte FIX3", ["1P >0.5","1P >1.5","1P >2.5","2P >0.5","2P >1.5","2P >2.5"], default=[], key="overs_unders_pred_fix3", placeholder="Ej: 1P >0.5")

    lista_hist_equipos_fix3 = sorted(pd.concat([df_fix3['HomeTeam'], df_fix3['AwayTeam']]).dropna().astype(str).unique().tolist())

    pass

    c_man1_fix3, c_man2_fix3 = st.columns(2)
    with c_man1_fix3:
        equipos_manuales_1_fix3 = st.multiselect("Equipos manuales 1 FIX3", lista_hist_equipos_fix3, default=[], key="eq_manual_1_fix3", placeholder="Ej: Cartagena, Burgos...")
        cond_manual_1_fix3 = st.selectbox("Cond manual 1 FIX3", ["TODOS","solo local","solo visitante"], key="cond_manual_1_fix3")
    with c_man2_fix3:
        equipos_manuales_2_fix3 = st.multiselect("Equipos manuales 2 FIX3", lista_hist_equipos_fix3, default=[], key="eq_manual_2_fix3", placeholder="Ej: Antequera, Marbella...")
        cond_manual_2_fix3 = st.selectbox("Cond manual 2 FIX3", ["TODOS","solo local","solo visitante"], key="cond_manual_2_fix3")

    with c_lp1_fix3:
        ligas_pred_sel_fix3 = st.multiselect("Ligas futuras FIX3", ligas_fut_fix3, default=st.session_state.ligas_pred_fix3, key="ligas_pred_fix3", placeholder="Todas las ligas")
    with c_lp2_fix3:
        df_base_pred_fix3 = df_futuro_fix3 if not ligas_pred_sel_fix3 else df_futuro_fix3[df_futuro_fix3['League_CSV'].isin(ligas_pred_sel_fix3)]
        fechas_pred_fix3 = sorted(df_base_pred_fix3['Date'].dropna().dt.date.unique())
        fechas_pred_str_fix3 = ["Todas"] + [d.strftime("%d/%m/%Y") for d in fechas_pred_fix3]
        fecha_pred_sel_fix3 = st.selectbox("Fecha desde FIX3", fechas_pred_str_fix3, index=fechas_pred_str_fix3.index(st.session_state.fecha_pred_fix3) if st.session_state.fecha_pred_fix3 in fechas_pred_str_fix3 else 0, key="fecha_pred_fix3")
    with c_lp3_fix3:
        c_m1_fix3, c_m2_fix3 = st.columns(2)
        with c_m1_fix3:
            min_desde_pred_raw_fix3 = st.text_input("MIN DESDE FIX3", key="min_desde_pred_fix3", placeholder="-")
        with c_m2_fix3:
            min_hasta_pred_raw_fix3 = st.text_input("MIN HASTA FIX3", key="min_hasta_pred_fix3", placeholder="-")

    def _parse_min_pred_fix3(v):
        try:
            if v is None or str(v).strip() in ["", "-", "–", "—"]: return None
            return int(str(v).strip().replace("'", ""))
        except: return None
    MIN_DESDE_PRED_FIX3 = _parse_min_pred_fix3(min_desde_pred_raw_fix3)
    MIN_HASTA_PRED_FIX3 = _parse_min_pred_fix3(min_hasta_pred_raw_fix3)

    if fecha_pred_sel_fix3!= "Todas":
        try:
            f_date_fix3 = pd.to_datetime(fecha_pred_sel_fix3, dayfirst=True).date()
            df_base_pred_fix3 = df_base_pred_fix3[df_base_pred_fix3['Date'].dt.date >= f_date_fix3]
        except: pass

    df_base_pred_fix3 = df_base_pred_fix3.sort_values('Date').head(1000)
    opciones_partidos_fix3 = []
    for _, r in df_base_pred_fix3.iterrows():
        try:
            fecha_s = r['Date'].strftime("%d/%m")
            liga_s = str(r['League_CSV'])[:15]
            h = str(r['HomeTeam']).strip()
            a = str(r['AwayTeam']).strip()
            fid = str(r.get('fixture_id',''))
            opciones_partidos_fix3.append(f"{fecha_s} | {liga_s} | {h} vs {a} | {fid}")
        except: continue

    partidos_sel_fix3 = []
    if not opciones_partidos_fix3:
        st.info("No hay partidos futuros con ese filtro FIX3")
    else:
        partidos_sel_fix3 = st.multiselect("Elige partido futuro FIX3 (auto-carga equipos)", opciones_partidos_fix3, key="partidos_pred_sel_fix3", placeholder="Ej: Magdeburg vs Hannover")

    partidos_pred_copy_fix3 = []
    tiene_manuales_fix3 = (len(equipos_manuales_1_fix3) > 0 or len(equipos_manuales_2_fix3) > 0)

    if not partidos_sel_fix3 and not tiene_manuales_fix3:
        st.caption("Selecciona partido futuro o equipo manual FIX3")
    else:
        partidos_pred_copy_fix3 = []
        partidos_a_iterar_fix3 = partidos_sel_fix3 if partidos_sel_fix3 else ["MANUAL | Manual | Manual vs Manual | 0"]
        for partido_str_fix3 in partidos_a_iterar_fix3:
            try:
                partes_fix3 = partido_str_fix3.split("|")
                teams_part_fix3 = partes_fix3[2].strip() if len(partes_fix3)>=3 else ""
                if " vs " in teams_part_fix3:
                    h_fut_fix3, a_fut_fix3 = [x.strip() for x in teams_part_fix3.split(" vs ")]
                else:
                    continue
            except:
                continue
            st.markdown(f"<div style='font-family:monospace;font-weight:900;background:#0A2342;color:#fff;padding:6px 8px;margin:12px 0 4px 0;font-size:12px'>🔮 FUTURO FIX3: {h_fut_fix3} vs {a_fut_fix3} | {partes_fix3[0].strip()}</div>", unsafe_allow_html=True)
            if "MANUAL" in partido_str_fix3:
                equipos_a_mostrar_fix3 = []
                if equipos_manuales_1_fix3: equipos_a_mostrar_fix3.extend(equipos_manuales_1_fix3)
                if equipos_manuales_2_fix3: equipos_a_mostrar_fix3.extend(equipos_manuales_2_fix3)
            else:
                equipos_a_mostrar_fix3 = [h_fut_fix3, a_fut_fix3]
                if equipos_manuales_1_fix3: equipos_a_mostrar_fix3.extend(equipos_manuales_1_fix3)
                if equipos_manuales_2_fix3: equipos_a_mostrar_fix3.extend(equipos_manuales_2_fix3)
            for nombre_eq_fix3 in equipos_a_mostrar_fix3:
                norm_eq_fix3 = normaliza(nombre_eq_fix3)
                eq_up_fix3 = nombre_eq_fix3.upper().strip()
                eq_up_fix3 = nombre_eq_fix3.upper().strip()
                def _is_match_fix3(team_raw):
                    return str(team_raw).upper().strip() == eq_up_fix3
                df_team_fix3 = df_fix3[(df_fix3['HomeTeam'].astype(str).str.upper().str.strip() == eq_up_fix3) | (df_fix3['AwayTeam'].astype(str).str.upper().str.strip() == eq_up_fix3)]
                if cond_loc_pred_fix3 == "equipo local solamente partidos de local" and nombre_eq_fix3 == h_fut_fix3:
                    df_team_fix3 = df_team_fix3[df_team_fix3['HomeTeam'].apply(_is_match_fix3)]
                elif cond_loc_pred_fix3 == "equipo visitante solamente sus partidos de visitante" and nombre_eq_fix3 == a_fut_fix3:
                    df_team_fix3 = df_team_fix3[df_team_fix3['AwayTeam'].apply(_is_match_fix3)]
                elif cond_loc_pred_fix3 == "Local en casa / Visitante fuera":
                    if nombre_eq_fix3 == h_fut_fix3:
                        df_team_fix3 = df_team_fix3[df_team_fix3['HomeTeam'].apply(_is_match_fix3)]
                    elif nombre_eq_fix3 == a_fut_fix3:
                        df_team_fix3 = df_team_fix3[df_team_fix3['AwayTeam'].apply(_is_match_fix3)]
                if nombre_eq_fix3 in equipos_manuales_1_fix3:
                    if cond_manual_1_fix3 == "solo local":
                        df_team_fix3 = df_team_fix3[df_team_fix3['HomeTeam'].apply(_is_match_fix3)]
                    elif cond_manual_1_fix3 == "solo visitante":
                        df_team_fix3 = df_team_fix3[df_team_fix3['AwayTeam'].apply(_is_match_fix3)]
                if nombre_eq_fix3 in equipos_manuales_2_fix3:
                    if cond_manual_2_fix3 == "solo local":
                        df_team_fix3 = df_team_fix3[df_team_fix3['HomeTeam'].apply(_is_match_fix3)]
                    elif cond_manual_2_fix3 == "solo visitante":
                        df_team_fix3 = df_team_fix3[df_team_fix3['AwayTeam'].apply(_is_match_fix3)]
                df_team_base_pred_fix3 = df_team_fix3.copy()
                if resultados_pred_sel_fix3: # [TAG-FIX3-SET-FINAL-UNICO-NO-TOCAR-FIX2]
                    sel_fix3 = resultados_pred_sel_fix3
                    set_1p_fix3 = set(); set_2p_fix3 = set()
                    for s in sel_fix3:
                        if "_1ªP" in s:
                            try: _x,_y = s.replace("_1ªP","").split("-"); set_1p_fix3.add((int(_x),int(_y))) # 
                            except: pass
                        if "_2ªP" in s:
                            try: _x,_y = s.replace("_2ªP","").split("-"); set_2p_fix3.add((int(_x),int(_y))) # 
                            except: pass
                    if set_1p_fix3 or set_2p_fix3:
                        def _cumple_res_pred_fix3(rr):
                            try:
                                hg_ = int(float(rr.get('FTHG',0) or 0)); ag_ = int(float(rr.get('FTAG',0) or 0))
                                hthg_ = int(float(rr.get('HTHG',0) or 0)); htag_ = int(float(rr.get('HTAG',0) or 0))
                            except: return False
                            if set_1p_fix3 and (hthg_, htag_) in set_1p_fix3: return True
                            if set_2p_fix3 and (hg_, ag_) in set_2p_fix3: return True
                            return False
                        df_team_fix3 = df_team_fix3[df_team_fix3.apply(_cumple_res_pred_fix3, axis=1)]
                if overs_sel_fix3:
                    def _cumple_overs_pred_fix3(rr):
                        try:
                            hg_ = int(float(rr.get('FTHG',0) or 0)); ag_ = int(float(rr.get('FTAG',0) or 0))
                            hthg_ = int(float(rr.get('HTHG',0) or 0)); htag_ = int(float(rr.get('HTAG',0) or 0))
                        except: return False
                        g1 = hthg_ + htag_
                        g2 = (hg_ + ag_) - g1
                        if g2 < 0: g2 = 0
                        for o in overs_sel_fix3:
                            if o == "1P >0.5" and not (g1 > 0.5): return False
                            if o == "1P >1.5" and not (g1 > 1.5): return False
                            if o == "1P >2.5" and not (g1 > 2.5): return False
                            if o == "2P >0.5" and not (g2 > 0.5): return False
                            if o == "2P >1.5" and not (g2 > 1.5): return False
                            if o == "2P >2.5" and not (g2 > 2.5): return False
                        return True
                    df_team_fix3 = df_team_fix3[df_team_fix3.apply(_cumple_overs_pred_fix3, axis=1)]
                if res_1p_tipo_fix3!= "TODOS":
                    def _cumple_1p_tipo_fix3(rr):
                        try:
                            hthg_ = int(float(rr.get('HTHG',0) or 0)); htag_ = int(float(rr.get('HTAG',0) or 0))
                        except: return False
                        hn_ = normaliza(rr.get('HomeTeam','')); an_ = normaliza(rr.get('AwayTeam',''))
                        if norm_eq_fix3 == hn_:
                            r_ = "GANA" if hthg_ > htag_ else "EMPATE" if hthg_ == htag_ else "PIERDE"
                        elif norm_eq_fix3 == an_:
                            r_ = "GANA" if htag_ > hthg_ else "EMPATE" if htag_ == hthg_ else "PIERDE"
                        else:
                            return False
                        if res_1p_tipo_fix3 == "EMPATE": return r_ == "EMPATE"
                        if res_1p_tipo_fix3 == "GANA": return r_ == "GANA"
                        if res_1p_tipo_fix3 == "PIERDE": return r_ == "PIERDE"
                        if res_1p_tipo_fix3 == "EMPATEGANA": return r_ in ("EMPATE","GANA")
                        if res_1p_tipo_fix3 == "EMPATEPIERDE": return r_ in ("EMPATE","PIERDE")
                        if res_1p_tipo_fix3 == "GANAPIERDE": return r_ in ("GANA","PIERDE")
                        return True
                    df_team_fix3 = df_team_fix3[df_team_fix3.apply(_cumple_1p_tipo_fix3, axis=1)]
                if df_team_fix3.empty:
                    st.caption(f"{nombre_eq_fix3} - sin historial en base actual FIX3")
                    continue
                st.markdown(f"<div style='font-family:monospace;font-weight:900;background:#000;color:#fff;padding:2px 6px;margin:6px 0 2px 0;font-size:10px'>{nombre_eq_fix3.upper()} FIX3</div>", unsafe_allow_html=True)
                # FIX3 ORDEN POR FECHAS - FIX REAL - J1=SEVILLA 15/08, J8=GETAFE 19/10 ULTIMA - FIX FECHAS FUTURAS 09/12
                def _parse_fecha_fix3_robusto(s):
                    try:
                        d = pd.to_datetime(s, dayfirst=True, errors='coerce')
                        if pd.isna(d):
                            d = pd.to_datetime(s, errors='coerce')
                        return d
                    except:
                        return pd.NaT
                df_team_base_pred_fix3['Date_parsed'] = df_team_base_pred_fix3['Date'].apply(_parse_fecha_fix3_robusto)
                df_team_base_pred_fix3 = df_team_base_pred_fix3[df_team_base_pred_fix3['Date_parsed'] <= pd.to_datetime("2026-10-20")]
                df_team_base_pred_fix3['fid_num'] = pd.to_numeric(df_team_base_pred_fix3['fixture_id'], errors='coerce')
                df_team_base_pred_fix3 = df_team_base_pred_fix3.sort_values(['Date_parsed','fid_num'], ascending=[True, True])
                df_team_fix3['Date_parsed'] = df_team_fix3['Date'].apply(_parse_fecha_fix3_robusto) if not df_team_fix3.empty else df_team_fix3.get('Date')
                df_team_fix3 = df_team_fix3[df_team_fix3['Date_parsed'] <= pd.to_datetime("2026-10-20")]
                df_team_fix3['fid_num'] = pd.to_numeric(df_team_fix3['fixture_id'], errors='coerce') if not df_team_fix3.empty else 0
                df_team_fix3 = df_team_fix3.sort_values(['Date_parsed','fid_num'], ascending=[True, True]) if not df_team_fix3.empty else df_team_fix3
                # J1 = mas antigua, J8 = mas reciente GETAFE 1-1 RAYO
                df_team_base_pred_fix3['Jornada'] = range(1, len(df_team_base_pred_fix3)+1)
                if not df_team_fix3.empty:
                    df_team_fix3['Jornada'] = range(1, len(df_team_fix3)+1)
                # FIX ORDEN REAL POR FECHA DESCENDENTE - NO RECALCULAR JORNADA
                df_team_fix3 = df_team_fix3.sort_values('Date_parsed', ascending=False)
                jornadas_fix3 = sorted(df_team_fix3['Jornada'].dropna().unique(), reverse=True)[:15] if not df_team_fix3.empty else []
                for j_fix3 in jornadas_fix3:
                    d_j_ok_fix3 = df_team_fix3[df_team_fix3['Jornada']==j_fix3].sort_values('Date_parsed', ascending=False) if not df_team_fix3.empty and 'Jornada' in df_team_fix3.columns else pd.DataFrame()
                    if d_j_ok_fix3.empty and len(jornadas_fix3) == 1:
                        d_j_ok_fix3 = df_team_fix3.sort_values('Date_parsed', ascending=False).head(15)
                    es_hueco_fix3 = d_j_ok_fix3.empty
                    if es_hueco_fix3:
                        continue
                    d_j_fix3 = d_j_ok_fix3
                    html_lineas_fix3 = ""
                    for _, r in d_j_fix3.iterrows():
                        fid = str(r.get('fixture_id','')).split('.')[0]
                        if MIN_DESDE_PRED_FIX3 is not None or MIN_HASTA_PRED_FIX3 is not None:
                            _tiene = False
                            for _ev in eventos_fix3.get(fid, []):
                                if 'Missed' in _ev.get('tipo',''): continue
                                _mm = _ev.get('m', -1)
                                if MIN_DESDE_PRED_FIX3 is not None and _mm < MIN_DESDE_PRED_FIX3: continue
                                if MIN_HASTA_PRED_FIX3 is not None and _mm > MIN_HASTA_PRED_FIX3: continue
                                _tiene = True
                                break
                            if not _tiene:
                                continue
                        h = str(r.get('HomeTeam','')).strip(); a = str(r.get('AwayTeam','')).strip()
                        try: hg = int(float(r.get('FTHG',0))); ag = int(float(r.get('FTAG',0)))
                        except: hg=0; ag=0
                        h_norm_r = normaliza(h); a_norm_r = normaliza(a)
                        if norm_eq_fix3 == h_norm_r: col_main = "#0f8105" if hg>ag else "#f31818" if hg<ag else "#8B4513"
                        elif norm_eq_fix3 == a_norm_r: col_main = "#0f8105" if ag>hg else "#f31818" if ag<hg else "#8B4513"
                        else: col_main = "#000"
                        hn = h_norm_r; an = a_norm_r
                        try: hthg = int(float(r.get('HTHG',0) or 0)); htag = int(float(r.get('HTAG',0) or 0))
                        except: hthg=0; htag=0
                        ht_str = f"[{hthg}-{htag}]"
                        # --- COLOR HT SEGUN 1ªP DEL EQUIPO FILTRADO + SUBRAYADO GOLES FIX3 - [TAG-FIX3-HT-SUBRAYADO-FINAL-NO-TOCAR-FIX2] ---
                        try:
                            _nf_clean_fix3 = str(norm_eq_fix3).upper().strip()
                            _h_clean_fix3 = str(h_norm_r).upper().strip()
                            _a_clean_fix3 = str(a_norm_r).upper().strip()
                            _is_home_fix3 = _nf_clean_fix3 == _h_clean_fix3
                            _is_away_fix3 = _nf_clean_fix3 == _a_clean_fix3
                        except:
                            _is_home_fix3 = (norm_eq_fix3 == hn)
                            _is_away_fix3 = (norm_eq_fix3 == an)
                        if _is_home_fix3:
                            if hthg > htag: col_ht = "#0f8105"
                            elif hthg < htag: col_ht = "#f31818"
                            else: col_ht = "#8B4513"
                        elif _is_away_fix3:
                            if htag > hthg: col_ht = "#0f8105"
                            elif htag < hthg: col_ht = "#f31818"
                            else: col_ht = "#8B4513"
                        else:
                            col_ht = "#0A2342"
                        #  SUBRAYADO HT DENTRO DEL CUADRO DE COLOR
                        u_ht = "text-decoration:underline;text-decoration-thickness:2.5px;text-underline-offset:3px;" # 
                        if norm_eq_fix3 == hn: #  equipo es local -> subraya hthg
                            ht_inner = f"<span style='{u_ht}'>{hthg}</span>-{htag}"
                        elif norm_eq_fix3 == an: #  equipo es visitante -> subraya htag
                            ht_inner = f"{hthg}-<span style='{u_ht}'>{htag}</span>"
                        else:
                            ht_inner = f"{hthg}-{htag}"
                        ht_str = f"[{ht_inner}]"
                        ht_html = f"<span style='color:#fff;font-weight:900;background:{col_ht};border-radius:3px;padding:0 4px;margin:0 3px'>{ht_str}</span>"
                        # [TAG-FIX3-GOLES-V4-FIX-4-1-OK] - FIX3 ONLY - CALCULO CORREGIDO - NO TOCA FIX2
                        filtro_act = (MIN_DESDE_PRED_FIX3 is not None or MIN_HASTA_PRED_FIX3 is not None)
                        evs_sorted_fix3 = sorted(eventos_fix3.get(fid, []), key=lambda x: x['m'])
                        def _es_home_fix3(team_str):
                            t = str(team_str).upper().strip()
                            hn_u = str(hn).upper().strip()
                            an_u = str(an).upper().strip()
                            if t == hn_u or hn_u in t or t in hn_u:
                                return True
                            if t == an_u or an_u in t or t in an_u:
                                return False
                            if "BARCELONA" in t:
                                return True
                            return False
                        def _agrupa_fix3_con_score(evs, score_start_h=0, score_start_a=0):
                            grupos = []
                            last_is_home = None
                            cur_spans = []
                            h_goals = score_start_h
                            a_goals = score_start_a
                            last_h = h_goals
                            last_a = a_goals
                            for ev in evs:
                                if 'Missed' in ev.get('tipo',''): continue
                                m = ev.get('m',-1)
                                team_ev = str(ev.get('team','')).strip()
                                if 'Own Goal' in ev.get('tipo',''):
                                    is_home_goal = not _es_home_fix3(team_ev)
                                else:
                                    is_home_goal = _es_home_fix3(team_ev)
                                if is_home_goal:
                                    h_goals += 1
                                else:
                                    a_goals += 1
                                benef = hn if is_home_goal else an
                                es_mio = norm_eq_fix3 in benef
                                col_min = col_main if es_mio else "#000"
                                peso = "font-weight:900;" if es_mio else "font-weight:700;"
                                sub_min = "text-decoration:underline;text-decoration-thickness:2.5px;text-underline-offset:2px;" if es_mio else ""
                                en_rango = (MIN_DESDE_PRED_FIX3 is None or m >= MIN_DESDE_PRED_FIX3) and (MIN_HASTA_PRED_FIX3 is None or m <= MIN_HASTA_PRED_FIX3)
                                if filtro_act and en_rango:
                                    span = f"<span style='color:{col_min};{peso};{sub_min}background:#D3D3D3;border-radius:3px;padding:1px 4px;margin-right:4px'>{m}'</span>"
                                else:
                                    span = f"<span style='color:{col_min};{peso};{sub_min}margin-right:4px'>{m}'</span>"
                                if last_is_home is not None and is_home_goal != last_is_home and cur_spans:
                                    grupos.append(("".join(cur_spans), last_h, last_a, last_is_home))
                                    cur_spans = []
                                cur_spans.append(span)
                                last_is_home = is_home_goal
                                last_h = h_goals
                                last_a = a_goals
                            if cur_spans:
                                grupos.append(("".join(cur_spans), last_h, last_a, last_is_home))
                            return grupos, h_goals, a_goals
                        evs_1p = [e for e in evs_sorted_fix3 if e.get('m',0) <= 45]
                        evs_2p = [e for e in evs_sorted_fix3 if e.get('m',0) > 45]
                        g1_data, h_fin_1p_calc, a_fin_1p_calc = _agrupa_fix3_con_score(evs_1p, 0, 0)
                        g2_data, _, _ = _agrupa_fix3_con_score(evs_2p, h_fin_1p_calc, a_fin_1p_calc)
                        if g1_data:
                            last_html, _, _, last_is_home = g1_data[-1]
                            g1_data[-1] = (last_html, hthg, htag, last_is_home)
                        if g2_data:
                            last_html, _, _, last_is_home = g2_data[-1]
                            g2_data[-1] = (last_html, hg, ag, last_is_home)
                        def fmt_grupo(tupla):
                            html_spans, sh, sa, _ = tupla
                            score_txt = f"<span style='color:#333;font-weight:400;font-size:10px;margin-left:6px;opacity:0.9'>{sh}-{sa}</span>"
                            return html_spans + score_txt
                        g1 = [fmt_grupo(t) for t in g1_data]
                        g2 = [fmt_grupo(t) for t in g2_data]
                        max_rows = max(len(g1), len(g2), 1)
                        filas = ""
                        for ii in range(max_rows):
                            left = g1[ii] if ii < len(g1) else ""
                            right = g2[ii] if ii < len(g2) else ""
                            if ii == len(g1)-1 and g1:
                                left = f"{left} {ht_html}" if left else ht_html
                            if not g1 and ii == 0:
                                left = ht_html
                            filas += f"<div style='display:grid;grid-template-columns:1fr 14px 1fr;align-items:center;line-height:1.6'><div style='text-align:left'>{left}</div><div style='text-align:center;color:#000;font-weight:900'>|</div><div style='text-align:left'>{right}</div></div>"
                        mins_html = f"<div style='margin-top:2px'>{filas}</div>"
                        mins_1t = g1
                        mins_2t = g2
                        mins_1t_html = mins_html
                        mins_2t_html = ""
                        def res_eq_pred_fix3(gf, gc): return "G" if gf>gc else "E" if gf==gc else "P"
                        if norm_eq_fix3 == hn: r1 = res_eq_pred_fix3(hthg, htag); rF = res_eq_pred_fix3(hg, ag)
                        elif norm_eq_fix3 == an: r1 = res_eq_pred_fix3(htag, hthg); rF = res_eq_pred_fix3(ag, hg)
                        else: r1="E"; rF="E"
                        estado = f"{r1}/{rF}"
                        if norm_eq_fix3 == h_norm_r:
                            h_txt = f"<span style='text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:3px'>{h}</span>"; a_txt = a
                        elif norm_eq_fix3 == a_norm_r:
                            h_txt = h; a_txt = f"<span style='text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:3px'>{a}</span>"
                        else:
                            h_txt = h; a_txt = a
                        # --- SUBRAYADO GOLES FT Y HT EN NEGRO CON LOGICA 0 FIX3 - [TAG-FIX3-NEGRO-LOGICA-0-V5-NO-TOCAR-FIX2] ---
                        u_black = "border-bottom:3.5px solid #000;padding-bottom:0px;" # 
                        u_black_w = "border-bottom:3.5px solid #000;padding-bottom:0px;color:#fff;" # 
                        # LOGICA: si marca 0 y rival >0 no subraya, si 0-0 si subraya
                        if norm_eq_fix3 == hn: #  local
                            if hg == 0 and ag > 0: hg_disp = f"{hg}" #  0-1 FT no subraya
                            else: hg_disp = f"<span style='{u_black}'>{hg}</span>" # 
                            ag_disp = f"{ag}" # 
                            if hthg == 0 and htag > 0: hthg_disp = f"{hthg}" #  tu ejemplo 30'[0-1] no subraya
                            else: hthg_disp = f"<span style='{u_black_w}'>{hthg}</span>" # 
                            htag_disp = f"{htag}" # 
                            ft_txt = f"{hg_disp}-{ag_disp}" # 
                            ht_inner = f"{hthg_disp}-{htag_disp}" # 
                        elif norm_eq_fix3 == an: #  visitante
                            hg_disp = f"{hg}" # 
                            if ag == 0 and hg > 0: ag_disp = f"{ag}" # 
                            else: ag_disp = f"<span style='{u_black}'>{ag}</span>" # 
                            hthg_disp = f"{hthg}" # 
                            if htag == 0 and hthg > 0: htag_disp = f"{htag}" # 
                            else: htag_disp = f"<span style='{u_black_w}'>{htag}</span>" # 
                            ft_txt = f"{hg_disp}-{ag_disp}" # 
                            ht_inner = f"{hthg_disp}-{htag_disp}" # 
                        else:
                            ft_txt = f"{hg}-{ag}" # 
                            ht_inner = f"{hthg}-{htag}" # 
                        ht_str = f"[{ht_inner}]" # 
                        ht_html = f"<span style='color:#fff;font-weight:900;background:{col_ht};border-radius:3px;padding:0 4px 2px 4px;margin:0 3px'>{ht_str}</span>" # 
                        # [TAG-FIX3-J-COLOR-RESULT-V14-FIX3-ONLY]
                        # [TAG-FIX3-COMPAT-MINS_1T-FIX] - evita NameError linea 1787 - NO TOCAR VISUALIZACION
                        mins_1t = []  # compat
                        mins_2t = []  # compat
                        mins_1t_html = mins_html  # nuevo layout ya lleva todo
                        mins_2t_html = ""
                        try:
                            _fecha_dt_fix3 = pd.to_datetime(r.get('Date'), errors='coerce')
                            _fecha_str_fix3 = _fecha_dt_fix3.strftime("%d/%m/%Y") if pd.notna(_fecha_dt_fix3) else ""
                        except:
                            _fecha_str_fix3 = ""
                        # 1 SOLO CROMO G/E/P DERECHA - FIX DEFINITIVO SIN PARENTESIS
                        if hg > ag:
                            h_win = "font-weight:900;font-size:12.5px;color:#000"
                            a_win = "font-weight:400;opacity:0.85;font-size:11px;color:#000"
                            b_res = "G" if _is_home_fix3 else "P" if _is_away_fix3 else "G"
                            b_col = "#0f8105" if b_res == "G" else "#f31818"
                        elif ag > hg:
                            h_win = "font-weight:400;opacity:0.85;font-size:11px;color:#000"
                            a_win = "font-weight:900;font-size:12.5px;color:#000"
                            b_res = "P" if _is_home_fix3 else "G" if _is_away_fix3 else "P"
                            b_col = "#0f8105" if b_res == "G" else "#f31818"
                        else:
                            h_win = "font-weight:700;font-size:11px;color:#000"
                            a_win = "font-weight:700;font-size:11px;color:#000"
                            b_res = "E"
                            b_col = "#8B4513"
                        html_lineas_fix3 += f"<div style='border-left:3.5px solid {col_main};padding-left:6px;margin:2px 0 0 2px;max-width:320px;line-height:1.0'>"
                        html_lineas_fix3 += f"<div style='text-align:center;font-family:monospace;font-weight:900;font-size:11px;margin:0 0 2px 0'><span style='color:{col_main}'>{estado}</span> <span style='color:#000'>({_fecha_str_fix3})</span></div>"
                        html_lineas_fix3 += f"<div style='display:flex;justify-content:space-between;align-items:center'>"
                        html_lineas_fix3 += f"<div style='display:grid;grid-template-columns:38px 1fr 22px;align-items:center;font-family:monospace;font-size:11px;line-height:1.1;gap:4px;max-width:100%'>"
                        html_lineas_fix3 += f"<span style='color:#000;flex-shrink:0'>J{int(j_fix3)} |</span><span style='white-space:normal;word-break:break-word;overflow:hidden;{h_win}'>{h}</span><span style='padding-left:2px;flex-shrink:0;text-align:right;{h_win}'>{hg_disp}</span>"
                        html_lineas_fix3 += f"<span></span><span style='white-space:normal;word-break:break-word;overflow:hidden;{a_win}'>{a}</span><span style='padding-left:2px;flex-shrink:0;text-align:right;{a_win}'>{ag_disp}</span>"
                        html_lineas_fix3 += f"</div>"
                        html_lineas_fix3 += f"<div style='background:{b_col};color:#fff;font-weight:900;font-size:10px;text-align:center;border-radius:3px;padding:2px 0;width:18px;margin-left:8px'>{b_res}</div>"
                        html_lineas_fix3 += f"</div>"
                        html_lineas_fix3 += f"<div style='text-align:left;font-size:10px;line-height:1.2;margin:8px 0 0 0'><div style='margin:0 0 2px 0'>{mins_1t_html}</div><div>{mins_2t_html}</div></div>"
                        html_lineas_fix3 += f"</div>"
                        html_lineas_fix3 += f"<div style='height:1px;background:#e6e6e6;margin:6px 0 2px 12px;max-width:320px'></div> " # [TAG-FIX3-J-COLOR-RESULT-V14-FIX3-ONLY]
                        m1 = []; m2 = []
                        for evc in sorted(eventos_fix3.get(fid, []), key=lambda x: x['m']):
                            if MIN_DESDE_PRED_FIX3 is not None and evc.get('m',-1) < MIN_DESDE_PRED_FIX3: continue
                            if MIN_HASTA_PRED_FIX3 is not None and evc.get('m',-1) > MIN_HASTA_PRED_FIX3: continue
                            if 'Missed' in evc.get('tipo',''): continue
                            mm = evc.get('m',0)
                            if mm <= 45: m1.append(f"{mm}'")
                            else: m2.append(f"{mm}'")
                        if m1 and m2: mins_txt = " ".join(m1) + f" {ht_str} " + " ".join(m2)
                        elif m1: mins_txt = " ".join(m1) + f" {ht_str}"
                        elif m2: mins_txt = f"{ht_str} " + " ".join(m2)
                        else: mins_txt = f"{ht_str}"
                        partidos_pred_copy_fix3.append(f"J{int(j_fix3)}|{h} {hg}-{ag} {a} | {mins_txt}{estado}")
                    st.markdown(f"<div style='line-height:1.15;white-space:normal;word-break:break-word;margin:0 0 2px 0;padding:0'>{html_lineas_fix3}</div>", unsafe_allow_html=True)

    if partidos_pred_copy_fix3:
        import html as _html
        texto_final_fix3 = "\n".join(partidos_pred_copy_fix3[:200])
        safe_txt_fix3 = _html.escape(texto_final_fix3)
        import streamlit.components.v1 as components
        components.html(f"""
        <textarea id="txt_pred_fix3" style="position:absolute;left:-9999px;top:-9999px;">{safe_txt_fix3}</textarea>
        <button onclick="navigator.clipboard.writeText(document.getElementById('txt_pred_fix3').value).then(()=>{{let b=document.getElementById('btn_pred_copy_fix3'); b.innerText='✓ COPIADO'; b.style.background='#0f8105'; setTimeout(()=>{{b.innerText=' COPIAR PREDICCION FIX3'; b.style.background='#0A2342'}},1200)}})"
        id="btn_pred_copy_fix3"
        style="width:100%;background:#0A2342;color:white;border:none;border-radius:6px;padding:12px;font-weight:900;cursor:pointer;">
         COPIAR PREDICCION FIX3 ({len(partidos_sel_fix3)} partidos futuros)
        </button>
        """, height=55, scrolling=False)

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
################################################################### CLONADO
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
        p = pathlib.Path("/mnt/data/Calendario-Futuro-Ligas-Tu-Csv-LIMPIO.csv")
        if not p.exists():
            for q in [pathlib.Path(__file__).parent.resolve(), pathlib.Path(".").resolve()]:
                if (q / "Calendario-Futuro-Ligas-Tu-Csv-LIMPIO.csv").exists():
                    p = q / "Calendario-Futuro-Ligas-Tu-Csv-LIMPIO.csv"
                    break
        if not p.exists():
            return pd.DataFrame()
        df_fut = pd.read_csv(p, on_bad_lines='skip')
        df_fut['Date'] = pd.to_datetime(df_fut['Date'], errors='coerce')
        return df_fut

    df_futuro_fix2 = cargar_futuro_fix2()
    if df_futuro_fix2.empty:
        st.warning("No encuentro Calendario-Futuro-Ligas-Tu-Csv-LIMPIO.csv en /mnt/data")
        st.stop()

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
                "cond_manual_1_fix2": st.session_state.get("cond_manual_1_fix2", "TODOS"),
                "cond_manual_2_fix2": st.session_state.get("cond_manual_2_fix2", "TODOS"),
                "cond_loc_pred_fix2": st.session_state.get("cond_loc_pred_fix2", "Local en casa / Visitante fuera"),
                "filtro_ht_ft_unico_2026_v9_fix2": st.session_state.get("filtro_ht_ft_unico_2026_v9_fix2", []),
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
    if "cond_manual_1_fix2" not in st.session_state:
        st.session_state.cond_manual_1_fix2 = _persist_fix2.get("cond_manual_1_fix2") or st.query_params.get("cond_manual_1_fix2", "TODOS")
    if "cond_manual_2_fix2" not in st.session_state:
        st.session_state.cond_manual_2_fix2 = _persist_fix2.get("cond_manual_2_fix2") or st.query_params.get("cond_manual_2_fix2", "TODOS")
    if "cond_loc_pred_fix2" not in st.session_state:
        st.session_state.cond_loc_pred_fix2 = _persist_fix2.get("cond_loc_pred_fix2") or st.query_params.get("cond_loc_pred_fix2", "Local en casa / Visitante fuera")
    if "filtro_ht_ft_unico_2026_v9_fix2" not in st.session_state:
        st.session_state.filtro_ht_ft_unico_2026_v9_fix2 = _persist_fix2.get("filtro_ht_ft_unico_2026_v9_fix2") or st.query_params.get_all("filtro_ht_ft_unico_2026_v9_fix2")

    if st.button(" LIMPIAR TODO EL BLOQUE PREDICCION FIX2", key="btn_limpiar_pred_fix2", use_container_width=True):
        for k in ["ligas_pred_fix2","fecha_pred_fix2","min_desde_pred_fix2","min_hasta_pred_fix2","partidos_pred_sel_fix2","eq_manual_1_fix2","eq_manual_2_fix2","cond_manual_1_fix2","cond_manual_2_fix2","filtro_ht_ft_unico_2026_v9_fix2","cond_loc_pred_fix2"]:
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
    def cargar_base_europa_fix2():
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
                            dfs.append(pd.read_parquet(base))
                        except:
                            pass
                        break
            if not dfs:
                return pd.DataFrame()
            df_all = pd.concat(dfs, ignore_index=True)
            # drop duplicados por fixture_id si existe
            if 'fixture_id' in df_all.columns:
                df_all = df_all.drop_duplicates(subset=['fixture_id'], keep='last')
            return df_all

        def _load_concat_goles(file_list):
            dfs=[]
            for name in file_list:
                for base in [pathlib.Path(name), pathlib.Path(__file__).parent.resolve()/name, pathlib.Path("/mnt/data")/name]:
                    if base.exists():
                        try:
                            dfs.append(pd.read_parquet(base))
                        except:
                            pass
                        break
            if not dfs:
                return pd.DataFrame()
            return pd.concat(dfs, ignore_index=True)

        # PARTIDOS: europa + resto
        df_e = _load_concat_partidos(["base_partidos_europa.parquet", "base_partidos_resto.parquet"])
        if not df_e.empty:
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
            df_e['Jornada'] = 0
            for (l_name, s_name), g_s in df_e.groupby(['League','Season'], sort=False):
                g_s = g_s.sort_values('Date')
                idxs = g_s.index.to_numpy()
                n_teams = len(pd.unique(pd.concat([g_s['HomeTeam'], g_s['AwayTeam']]).dropna()))
                ppj = max(n_teams // 2, 1)
                df_e.loc[idxs, 'Jornada'] = (np.arange(len(idxs)) // ppj) + 1

        # GOLES: europa + resto
        df_g = _load_concat_goles(["base_goles_europa.parquet", "base_goles_resto.parquet"])
        ev = {}
        if not df_g.empty:
            df_g['fid_str'] = df_g['fixture_id'].astype(str).str.split('.').str[0]
            df_g['m'] = pd.to_numeric(df_g.get('minuto', 0), errors='coerce').fillna(0).astype(int)
            for fid, sub in df_g.groupby('fid_str'):
                ev[fid] = [{'m': int(r.get('m', 0)), 'team': normaliza(r.get('equipo','')), 'tipo': str(r.get('tipo',''))} for _, r in sub.iterrows()]
        return df_e, ev

    df_europa_fix2, eventos_europa_fix2 = cargar_base_europa_fix2()
    df_fix2 = df_europa_fix2
    eventos_fix2 = eventos_europa_fix2

    ligas_fut_all_fix2 = sorted(df_futuro_fix2['League_CSV'].dropna().unique().tolist())
    if not df_europa_fix2.empty and 'League' in df_europa_fix2.columns:
        ligas_europa_set_fix2 = set(df_europa_fix2['League'].dropna().astype(str).tolist())
        ligas_fut_fix2 = [l for l in ligas_fut_all_fix2 if any(normaliza(l) == normaliza(le) or normaliza(l) in normaliza(le) or normaliza(le) in normaliza(l) for le in ligas_europa_set_fix2)]
        if not ligas_fut_fix2:
            keywords_eu = ["Eliteserien","Eredivisie","Bundesliga","LaLiga","Premier","Serie A","Ligue","Pro League","First League Bulgaria","Super Lig","Ekstraklasa","Primeira Liga"]
            ligas_fut_fix2 = [l for l in ligas_fut_all_fix2 if any(k.lower() in l.lower() for k in keywords_eu)]
    else:
        ligas_fut_fix2 = ligas_fut_all_fix2

    c_lp1_fix2, c_lp2_fix2, c_lp3_fix2, c_lp4_fix2 = st.columns([2,1,1,1])
    with c_lp4_fix2:
        goles_parte_fix2 = st.selectbox("GOLES PARTE", ["Todo","1ªParte","2ªParte"], index=0, key="goles_parte_fix2")
        cond_loc_pred_fix2 = st.selectbox("Filtro", ["TODOS","equipo local solamente partidos de local","equipo visitante solamente sus partidos de visitante","Local en casa / Visitante fuera"], index=3, key="cond_loc_pred_fix2")
        res_1p_tipo_fix2 = st.selectbox("Resultado 1ªP", ["TODOS","EMPATE","GANA","PIERDE","EMPATEGANA","EMPATEPIERDE","GANAPIERDE"], index=0, key="res_1p_tipo_pred_fix2")
        opciones_res_fix2 = [f"{a}-{b}_1ªP" for a in range(5) for b in range(5)] + [f"{a}-{b}_2ªP" for a in range(5) for b in range(5)]
        resultados_pred_sel_fix2 = st.multiselect("Resultado 1ªP / 2ªP", opciones_res_fix2, default=[], key="filtro_ht_ft_unico_2026_v9_fix2", placeholder="Ej: 0-0_1ªP")
        overs_sel_fix2 = st.multiselect("Overs / Unders por parte", ["1P >0.5","1P >1.5","1P >2.5","2P >0.5","2P >1.5","2P >2.5"], default=[], key="overs_unders_pred_fix2", placeholder="Ej: 1P >0.5")
        res_live_tipo_fix2 = st.selectbox("Resultado LIVE", ["TODOS","EMPATE","GANA","PIERDE","EMPATEGANA","EMPATEPIERDE","GANAPIERDE"], index=0, key="res_live_tipo_fix2")
        min_live_raw_fix2 = st.text_input("MIN LIVE", key="min_live_fix2", placeholder="Ej: 76")

    lista_hist_equipos_fix2 = sorted(pd.concat([df_fix2['HomeTeam'], df_fix2['AwayTeam']]).dropna().astype(str).unique().tolist())

    c_man1_fix2, c_man2_fix2 = st.columns(2)
    with c_man1_fix2:
        equipos_manuales_1_fix2 = st.multiselect("Equipos manuales 1 FIX2", lista_hist_equipos_fix2, default=[], key="eq_manual_1_fix2", placeholder="Ej: Cartagena, Burgos...")
        cond_manual_1_fix2 = st.selectbox("Cond manual 1 FIX2", ["TODOS","solo local","solo visitante"], key="cond_manual_1_fix2")
    with c_man2_fix2:
        equipos_manuales_2_fix2 = st.multiselect("Equipos manuales 2 FIX2", lista_hist_equipos_fix2, default=[], key="eq_manual_2_fix2", placeholder="Ej: Antequera, Marbella...")
        cond_manual_2_fix2 = st.selectbox("Cond manual 2 FIX2", ["TODOS","solo local","solo visitante"], key="cond_manual_2_fix2")

    with c_lp1_fix2:
        ligas_pred_sel_fix2 = st.multiselect("Ligas futuras FIX2", ligas_fut_fix2, default=st.session_state.ligas_pred_fix2, key="ligas_pred_fix2", placeholder="Todas las ligas")
    with c_lp2_fix2:
        df_base_pred_fix2 = df_futuro_fix2 if not ligas_pred_sel_fix2 else df_futuro_fix2[df_futuro_fix2['League_CSV'].isin(ligas_pred_sel_fix2)]
        fechas_pred_fix2 = sorted(df_base_pred_fix2['Date'].dropna().dt.date.unique())
        fechas_pred_str_fix2 = ["Todas"] + [d.strftime("%d/%m/%Y") for d in fechas_pred_fix2]
        fecha_pred_sel_fix2 = st.selectbox("Fecha desde FIX2", fechas_pred_str_fix2, index=fechas_pred_str_fix2.index(st.session_state.fecha_pred_fix2) if st.session_state.fecha_pred_fix2 in fechas_pred_str_fix2 else 0, key="fecha_pred_fix2")
    with c_lp3_fix2:
        c_m1_fix2, c_m2_fix2 = st.columns(2)
        with c_m1_fix2:
            min_desde_pred_raw_fix2 = st.text_input("MIN DESDE FIX2", key="min_desde_pred_fix2", placeholder="-")
        with c_m2_fix2:
            min_hasta_pred_raw_fix2 = st.text_input("MIN HASTA FIX2", key="min_hasta_pred_fix2", placeholder="-")

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
    if not opciones_partidos_fix2:
        st.info("No hay partidos futuros con ese filtro FIX2")
    else:
        partidos_sel_fix2 = st.multiselect("Elige partido futuro FIX2 (auto-carga equipos)", opciones_partidos_fix2, key="partidos_pred_sel_fix2", placeholder="Ej: Magdeburg vs Hannover")

    partidos_pred_copy_fix2 = []
    tiene_manuales_fix2 = (len(equipos_manuales_1_fix2) > 0 or len(equipos_manuales_2_fix2) > 0)

    if not partidos_sel_fix2 and not tiene_manuales_fix2:
        st.caption("Selecciona partido futuro o equipo manual FIX2")
    else:
        partidos_pred_copy_fix2 = []
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
                _norm = normaliza(nom); _up = nom.upper().strip()
                _df = df_fix2[(df_fix2['HomeTeam'].astype(str).str.upper().str.strip() == _up) | (df_fix2['AwayTeam'].astype(str).str.upper().str.strip() == _up)]
                if _df.empty:
                    _df = df_fix2[(df_fix2['HomeTeam'].apply(lambda x: normaliza(x)==_norm)) | (df_fix2['AwayTeam'].apply(lambda x: normaliza(x)==_norm))]
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
                        for ev in eventos_fix2.get(fid, []):
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
            st.markdown(f"<div style='font-family:monospace;font-weight:900;background:#0A2342;color:#fff;padding:6px 8px;margin:12px 0 4px 0;font-size:12px'>🔮 FUTURO FIX2: {h_fut_fix2} {f_h_filt}/{f_h_tot} vs {a_fut_fix2} {f_a_filt}/{f_a_tot} | {partes_fix2[0].strip()}</div>", unsafe_allow_html=True)

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
                df_team_fix2 = df_fix2[(df_fix2['HomeTeam'].astype(str).str.upper().str.strip() == eq_up_fix2) | (df_fix2['AwayTeam'].astype(str).str.upper().str.strip() == eq_up_fix2)]
                if df_team_fix2.empty:
                    df_team_fix2 = df_fix2[(df_fix2['HomeTeam'].apply(lambda x: normaliza(x)==norm_eq_fix2)) | (df_fix2['AwayTeam'].apply(lambda x: normaliza(x)==norm_eq_fix2))]

                if cond_loc_pred_fix2 == "equipo local solamente partidos de local" and nombre_eq_fix2 == h_fut_fix2:
                    df_team_fix2 = df_team_fix2[df_team_fix2['HomeTeam'].astype(str).str.upper().str.strip() == eq_up_fix2]
                elif cond_loc_pred_fix2 == "equipo visitante solamente sus partidos de visitante" and nombre_eq_fix2 == a_fut_fix2:
                    df_team_fix2 = df_team_fix2[df_team_fix2['AwayTeam'].astype(str).str.upper().str.strip() == eq_up_fix2]
                elif cond_loc_pred_fix2 == "Local en casa / Visitante fuera":
                    if nombre_eq_fix2 == h_fut_fix2:
                        df_team_fix2 = df_team_fix2[df_team_fix2['HomeTeam'].astype(str).str.upper().str.strip() == eq_up_fix2]
                    elif nombre_eq_fix2 == a_fut_fix2:
                        df_team_fix2 = df_team_fix2[df_team_fix2['AwayTeam'].astype(str).str.upper().str.strip() == eq_up_fix2]

                # BASE TOTAL SIN FILTROS - Para testigo JX ante cualquier filtro
                df_team_base_total_fix2 = df_team_fix2.copy()

                if nombre_eq_fix2 in equipos_manuales_1_fix2:
                    if cond_manual_1_fix2 == "solo local":
                        df_team_fix2 = df_team_fix2[df_team_fix2['HomeTeam'].astype(str).str.upper().str.strip() == eq_up_fix2]
                    elif cond_manual_1_fix2 == "solo visitante":
                        df_team_fix2 = df_team_fix2[df_team_fix2['AwayTeam'].astype(str).str.upper().str.strip() == eq_up_fix2]
                if nombre_eq_fix2 in equipos_manuales_2_fix2:
                    if cond_manual_2_fix2 == "solo local":
                        df_team_fix2 = df_team_fix2[df_team_fix2['HomeTeam'].astype(str).str.upper().str.strip() == eq_up_fix2]
                    elif cond_manual_2_fix2 == "solo visitante":
                        df_team_fix2 = df_team_fix2[df_team_fix2['AwayTeam'].astype(str).str.upper().str.strip() == eq_up_fix2]

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
                            if _df_try.empty:
                                _df_try = _df_csv[(_df_csv['HomeTeam'].apply(lambda x: normaliza(str(x))==_norm)) | (_df_csv['AwayTeam'].apply(lambda x: normaliza(str(x))==_norm))]
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
                                                eventos_fix2[fid] = [{'m': int(r.get('m', 0)), 'team': normaliza(r.get('equipo','')), 'tipo': str(r.get('tipo',''))} for _, r in sub.iterrows()]
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
                        for ev in eventos_fix2.get(fid, []):
                            if 'Missed' in ev.get('tipo',''): continue
                            mm = ev.get('m',-1)
                            if MIN_DESDE_PRED_FIX2 is not None and mm < MIN_DESDE_PRED_FIX2: continue
                            if MIN_HASTA_PRED_FIX2 is not None and mm > MIN_HASTA_PRED_FIX2: continue
                            return True
                        return False
                    filt_fix2 = len(df_team_fix2[df_team_fix2.apply(_tiene_min_eq, axis=1)])
                else:
                    filt_fix2 = len(df_team_fix2)
                st.markdown(f"<div style='font-family:monospace;font-weight:900;background:#000;color:#fff;padding:2px 6px;margin:6px 0 2px 0;font-size:10px'>{nombre_eq_fix2.upper()} {filt_fix2}/{total_fix2} FIX2</div>", unsafe_allow_html=True)
                # FIX2 ORDEN J10 arriba = ultimo partido
                def _parse_fecha_fix2_robusto(s):
                    try:
                        if pd.isna(s):
                            return pd.NaT
                        d = pd.to_datetime(s, dayfirst=True, errors='coerce')
                        if pd.isna(d):
                            d = pd.to_datetime(s, errors='coerce')
                        return d
                    except:
                        return pd.NaT
                df_team_base_pred_fix2['Date_parsed'] = df_team_base_pred_fix2['Date'].apply(_parse_fecha_fix2_robusto)
                df_team_base_pred_fix2 = df_team_base_pred_fix2[df_team_base_pred_fix2['Date_parsed'] <= pd.to_datetime("2026-10-20")]
                df_team_base_pred_fix2['fid_num'] = pd.to_numeric(df_team_base_pred_fix2['fixture_id'], errors='coerce')
                df_team_base_pred_fix2 = df_team_base_pred_fix2.sort_values(['Date_parsed','fid_num'], ascending=[True, True])
                df_team_fix2['Date_parsed'] = df_team_fix2['Date'].apply(_parse_fecha_fix2_robusto) if not df_team_fix2.empty else df_team_fix2.get('Date')
                df_team_fix2 = df_team_fix2[df_team_fix2['Date_parsed'] <= pd.to_datetime("2026-10-20")]
                df_team_fix2['fid_num'] = pd.to_numeric(df_team_fix2['fixture_id'], errors='coerce') if not df_team_fix2.empty else 0
                df_team_fix2 = df_team_fix2.sort_values(['Date_parsed','fid_num'], ascending=[True, True]) if not df_team_fix2.empty else df_team_fix2
                # FIX DEFINITIVO - Jornadas continuas 15 últimas para testigo J|— aunque no haya partido en esa J
                if not df_team_base_pred_fix2.empty and 'Jornada' in df_team_base_pred_fix2.columns:
                    try:
                        max_j = int(pd.to_numeric(df_team_base_pred_fix2['Jornada'], errors='coerce').max())
                    except:
                        max_j = 0
                    jornadas_fix2 = list(range(max_j, max(0, max_j-15), -1))
                else:
                    jornadas_fix2 = sorted(df_team_base_pred_fix2['Jornada'].dropna().unique(), reverse=True)[:15] if 'Jornada' in df_team_base_pred_fix2.columns else []
                for j_fix2 in jornadas_fix2:
                    d_j_ok_fix2 = df_team_fix2[df_team_fix2['Jornada']==j_fix2].sort_values('Date', ascending=False) if not df_team_fix2.empty and 'Jornada' in df_team_fix2.columns else pd.DataFrame()
                    es_hueco_fix2 = d_j_ok_fix2.empty
                    # Para MIN DESDE/HASTA: si la jornada existe pero ningún partido tiene eventos en ese rango, también es hueco
                    if not es_hueco_fix2 and (MIN_DESDE_PRED_FIX2 is not None or MIN_HASTA_PRED_FIX2 is not None):
                        _tiene_algun_evento_jornada = False
                        for _, _rr_tmp in d_j_ok_fix2.iterrows():
                            _fid_tmp = str(_rr_tmp.get('fixture_id','')).split('.')[0]
                            for _ev_tmp in eventos_fix2.get(_fid_tmp, []):
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
                                _es_local_hueco = (normaliza(nombre_eq_fix2) == normaliza(_h0))
                                _loc_txt = "CASA" if _es_local_hueco else "VISITANTE"
                                _bg_hueco = "#111111" if _es_local_hueco else "#1a1a1a"
                            else:
                                _loc_txt = ""
                                _bg_hueco = "#0a0a0a"
                        except:
                            _loc_txt = ""
                            _bg_hueco = "#f5f5f5"
                        st.markdown(f"<div style='font-family:monospace; text-align:center; padding:4px; max-width:480px; margin:2px auto; background:{_bg_hueco}; border-radius:6px; border:1px solid #444;'><div style='color:#fff; font-weight:900; font-size:10px;'>J{int(j_fix2)} | — {_loc_txt}</div></div><div style='height:2.5px;background:#444;margin:4px auto 10px auto; max-width:480px;'></div>", unsafe_allow_html=True)
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
                        if norm_eq_fix2 == h_norm_r: col_main = "#0f8105" if hg>ag else "#f31818" if hg<ag else "#8B4513"
                        elif norm_eq_fix2 == a_norm_r: col_main = "#0f8105" if ag>hg else "#f31818" if ag<hg else "#8B4513"
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
                            else: col_ht = "#8B4513"
                        elif _is_away_fix2:
                            if htag > hthg: col_ht = "#0f8105"
                            elif htag < hthg: col_ht = "#f31818"
                            else: col_ht = "#8B4513"
                        else:
                            col_ht = "#0A2342"

                        # --- G/E/P ---
                        def res_eq_pred_fix2(gf, gc): return "G" if gf>gc else "E" if gf==gc else "P"
                        if norm_eq_fix2 == hn: r1 = res_eq_pred_fix2(hthg, htag); rF = res_eq_pred_fix2(hg, ag)
                        elif norm_eq_fix2 == an: r1 = res_eq_pred_fix2(htag, hthg); rF = res_eq_pred_fix2(ag, hg)
                        else: r1="E"; rF="E"
                        estado = f"{r1}/{rF}"

                        # --- NOMBRES con subrayado + EMOJI FUERA COMO QUIERES ---
                        EMOJI_SEL = "🔵"
                        EMOJI_RIVAL = "⚪"
                        if norm_eq_fix2 == h_norm_r:
                            h_txt = f"<span style='color:{col_main};text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:3px;font-weight:900'>{h}</span>"
                            a_txt = f"<span style='color:#ffffff'>{a}</span>"
                            emoji_home = EMOJI_SEL
                            emoji_away = EMOJI_RIVAL
                        elif norm_eq_fix2 == a_norm_r:
                            h_txt = f"<span style='color:#ffffff'>{h}</span>"
                            a_txt = f"<span style='color:{col_main};text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:3px;font-weight:900'>{a}</span>"
                            emoji_home = EMOJI_RIVAL
                            emoji_away = EMOJI_SEL
                        else:
                            h_txt = f"<span style='color:#ffffff'>{h}</span>"
                            a_txt = f"<span style='color:#ffffff'>{a}</span>"
                            emoji_home = EMOJI_RIVAL
                            emoji_away = EMOJI_SEL

                        # --- FT / HT con tu lógica de subrayado negro ---
                        u_black = "border-bottom:3.5px solid #000;padding-bottom:0px;"
                        u_black_w = "border-bottom:3.5px solid #000;padding-bottom:0px;color:#fff;"
                        if norm_eq_fix2 == hn:
                            if hg == 0 and ag > 0: hg_disp = f"{hg}"
                            else: hg_disp = f"<span style='{u_black}'>{hg}</span>"
                            ag_disp = f"{ag}"
                            if hthg == 0 and htag > 0: hthg_disp = f"{hthg}"
                            else: hthg_disp = f"<span style='{u_black_w}'>{hthg}</span>"
                            htag_disp = f"{htag}"
                            ft_txt = f"[{hg_disp}-{ag_disp}]"
                            ht_inner = f"{hthg_disp}-{htag_disp}"
                        elif norm_eq_fix2 == an:
                            hg_disp = f"{hg}"
                            if ag == 0 and hg > 0: ag_disp = f"{ag}"
                            else: ag_disp = f"<span style='{u_black}'>{ag}</span>"
                            hthg_disp = f"{hthg}"
                            if htag == 0 and hthg > 0: htag_disp = f"{htag}"
                            else: htag_disp = f"<span style='{u_black_w}'>{htag}</span>"
                            ft_txt = f"[{hg_disp}-{ag_disp}]"
                            ht_inner = f"{hthg_disp}-{htag_disp}"
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
                            grupos=[]; last=None; cur=[]; h=sh; a=sa; lh=sh; la=sa; last_is_home=None
                            for ev in evs:
                                m=ev.get('m',-1); team_ev=str(ev.get('team','')).strip(); tipo=str(ev.get('tipo',''))
                                es_local_raw = _equipo_es_local(team_ev, hn, an)
                                is_home_scoring = es_local_raw
                                if 'Missed Penalty' in tipo:
                                    if cur: grupos.append((cur, lh, la, last_is_home)); cur=[]; last=None
                                    grupos.append(([(m, tipo)], lh, la, is_home_scoring)); continue
                                if is_home_scoring: h+=1
                                else: a+=1
                                if last is not None and is_home_scoring != last and cur:
                                    grupos.append((cur, lh, la, last_is_home)); cur=[]
                                cur.append((m, tipo)); last=is_home_scoring; last_is_home=is_home_scoring; lh=h; la=a
                            if cur: grupos.append((cur, lh, la, last_is_home))
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
                        if g1_data and not any('Missed' in tp for _, tp in g1_data[-1][0]): 
                            g1_data[-1] = (g1_data[-1][0], hthg, htag, g1_data[-1][3])
                        g2_data = _agrupa_fix2_con_score_sub(evs_2p_fix2, hthg, htag)
                        if g2_data and not any('Missed' in tp for _, tp in g2_data[-1][0]):
                            g2_data[-1] = (g2_data[-1][0], hg, ag, g2_data[-1][3])

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
                        bg_j = "#111111" if es_local_j else "#1a1a1a"
                        html = f"<div style='font-family:monospace; text-align:center; padding:6px 4px 4px 4px; max-width:480px; margin:0 auto; line-height:1.2; background:{bg_j}; border-radius:6px; border:1px solid #444;'>"
                        html += f"<div style='font-weight:900; color:{col_main}; font-size:15px; line-height:1.2; margin:0;'>J{int(j_fix2)} | <span style='background:{col_main};color:#fff;padding:2px 6px;border-radius:4px; margin-right:6px;'>{estado}</span> {emoji_home} {h_txt}  {ft_txt}  {a_txt}{emoji_away}  <span style='color:#fff;'>({_fecha_str_fix2})</span></div>"
                        html += f"<div style='margin-top:2px; font-size:13px; color:#fff; line-height:1.2;'>(1ª parte {hthg}-{htag})</div>"
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
                                        txt_min = f"{base}{emoji_gol}"
                                        en_rango = (MIN_DESDE_PRED_FIX2 is None or mm >= MIN_DESDE_PRED_FIX2) and (MIN_HASTA_PRED_FIX2 is None or mm <= MIN_HASTA_PRED_FIX2)
                                        if filtro_act_fix2 and en_rango:
                                            txt_min = f"<span style='background:#444;color:#fff;border-radius:3px;padding:1px 4px;'>{txt_min}</span>"
                                        es_mio = (is_home and norm_eq_fix2 == hn) or (not is_home and norm_eq_fix2 == an)
                                        if es_mio and '(x)' not in txt_min:
                                            txt_min = f"<span style='font-weight:900; color:{col_main};'>{txt_min}</span>"
                                        is_missed = 'Missed' in tp
                                        if is_missed: continue
                                        score_txt = f"<span style='color:#ffffff'>{sh}-{sa}</span>"
                                        # HUECO 3 CHARS - 50px
                                        if is_home:
                                            html += f"<div style='text-align:center; line-height:1.9;'><span style='display:inline-block; width:160px; text-align:left; font-size:14px; color:#fff; font-weight:700; transform:translateX(-50px);'>{txt_min} {score_txt}</span></div>"
                                        else:
                                            html += f"<div style='text-align:center; line-height:1.9;'><span style='display:inline-block; width:160px; text-align:right; font-size:14px; color:#fff; font-weight:700; transform:translateX(50px);'>{score_txt} {txt_min}</span></div>"
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
                                        txt_min = f"{base}{emoji_gol}"
                                        if filtro_act_fix2 and (MIN_DESDE_PRED_FIX2 is None or mm >= MIN_DESDE_PRED_FIX2) and (MIN_HASTA_PRED_FIX2 is None or mm <= MIN_HASTA_PRED_FIX2):
                                            txt_min = f"<span style='background:#444;color:#fff;border-radius:3px;padding:1px 4px;'>{txt_min}</span>"
                                        es_mio = (is_home and norm_eq_fix2 == hn) or (not is_home and norm_eq_fix2 == an)
                                        if es_mio:
                                            txt_min = f"<span style='font-weight:900; color:{col_main};'>{txt_min}</span>"
                                        if is_home:
                                            html += f"<div style='text-align:center; line-height:1.9;'><span style='display:inline-block; width:160px; text-align:left; font-size:14px; color:#fff; font-weight:700; transform:translateX(-85px);'>{txt_min} <span style='color:#fff;'>{sh}-{sa}</span></span></div>"
                                        else:
                                            html += f"<div style='text-align:center; line-height:1.9;'><span style='display:inline-block; width:160px; text-align:right; font-size:14px; color:#fff; font-weight:700; transform:translateX(85px);'><span style='color:#fff;'>{sh}-{sa}</span> {txt_min}</span></div>"
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
                        # visual con HTML (sigue igual)
                        if m1 and m2: mins_txt = " ".join(m1) + f"{ht_str} " + " ".join(m2)
                        elif m1: mins_txt = " ".join(m1) + f"{ht_str}"
                        elif m2: mins_txt = f"{ht_str} " + " ".join(m2)
                        else: mins_txt = f"{ht_str}"
                        # limpio para copiar - sin <span>
                        ht_clean = f"[{hthg}-{htag}]"
                        ft_clean = f"{hg}-{ag}"
                        if m1 and m2: mins_txt_clean = " ".join(m1) + f"{ht_clean} " + " ".join(m2)
                        elif m1: mins_txt_clean = " ".join(m1) + f"{ht_clean}"
                        elif m2: mins_txt_clean = f"{ht_clean} " + " ".join(m2)
                        else: mins_txt_clean = f"{ht_clean}"
                        partidos_pred_copy_fix2.append(f"J{int(j_fix2)}|{h} {ft_clean} {a} {mins_txt_clean} {estado}")

                    st.markdown(f"<div style='line-height:1.15;white-space:normal;word-break:break-word;margin:0 0 2px 0;padding:0'>{html_lineas_fix2}</div>", unsafe_allow_html=True)

    if partidos_pred_copy_fix2:
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
            _eq_man1_txt = f"{equipos_manuales_1_fix2} [{cond_manual_1_fix2}]" if equipos_manuales_1_fix2 else "-"
            _eq_man2_txt = f"{equipos_manuales_2_fix2} [{cond_manual_2_fix2}]" if equipos_manuales_2_fix2 else "-"
            _partidos_fut_txt = f"{len(partidos_sel_fix2)}: {partidos_sel_fix2[:2]}" if partidos_sel_fix2 else "MANUAL"
            filtros_txt_fix2 = (
                f"FILTROS FIX2 | PARTIDOS FUT={_partidos_fut_txt} | Ligas=[{_ligas_txt}] | Fecha={_fecha_txt} | "
                f"GOLES_PARTE={_goles_parte_txt} | Filtro={_cond_loc_txt} | "
                f"1P_TIPO={_res_1p_tipo_txt} | 1P/2P_RES=[{_res_ht_ft_txt}] | Overs=[{_overs_txt}] | "
                f"LIVE={_live_txt} | MIN_DESDE={_min_desde_txt} HASTA={_min_hasta_txt} | "
                f"MANUAL1={_eq_man1_txt} | MANUAL2={_eq_man2_txt} | EQUIPOS_MOSTRADOS={equipos_a_mostrar_fix2}"
            )
        except Exception as e:
            filtros_txt_fix2 = f"FILTROS FIX2: {ligas_pred_sel_fix2} {fecha_pred_sel_fix2} {cond_loc_pred_fix2} | ERR:{e}"
        # TEXTO VISIBLE EN PANTALLA PARA VER FILTROS PUESTOS
        st.markdown(f"<div style='font-family:monospace; font-size:9px; background:#f0f0f0; border:1px solid #0A2342; border-radius:6px; padding:6px 8px; margin:8px 0; white-space:pre-wrap; word-break:break-word;'>{filtros_txt_fix2}</div>", unsafe_allow_html=True)
        texto_final_fix2 = filtros_txt_fix2 + "\n" + "\n".join(partidos_pred_copy_fix2[:200])
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
##################
################################################################### CLONADO


with st.expander(" PREDICCION RESTO - SUDAMERICA + ASIA + MLS", expanded=False):
    @st.cache_data(show_spinner=False)
    def cargar_base_resto():
        p_par = pathlib.Path("base_partidos_resto.parquet")
        if not p_par.exists():
            p_par = pathlib.Path(__file__).parent.resolve() / "base_partidos_resto.parquet"
        g_par = pathlib.Path("base_goles_resto.parquet")
        if not g_par.exists():
            g_par = pathlib.Path(__file__).parent.resolve() / "base_goles_resto.parquet"
        df_e = pd.read_parquet(p_par) if p_par.exists() else pd.DataFrame()
        if not df_e.empty:
            def _parse_fecha_base_resto(s):
                try:
                    d = pd.to_datetime(s, dayfirst=True, errors='coerce')
                    if pd.isna(d):
                        d = pd.to_datetime(s, errors='coerce')
                    return d
                except:
                    return pd.NaT
            df_e['Date'] = df_e['Date'].apply(_parse_fecha_base_resto)
            df_e = df_e.sort_values(['League','Season','Date']).copy()
            df_e['Jornada'] = 0
            for (l_name, s_name), g_s in df_e.groupby(['League','Season'], sort=False):
                g_s = g_s.sort_values('Date')
                idxs = g_s.index.to_numpy()
                n_teams = len(pd.unique(pd.concat([g_s['HomeTeam'], g_s['AwayTeam']]).dropna()))
                ppj = max(n_teams // 2, 1)
                df_e.loc[idxs, 'Jornada'] = (np.arange(len(idxs)) // ppj) + 1
        df_g = pd.read_parquet(g_par) if g_par.exists() else pd.DataFrame()
        ev = {}
        if not df_g.empty:
            df_g['fid_str'] = df_g['fixture_id'].astype(str).str.split('.').str[0]
            df_g['m'] = pd.to_numeric(df_g.get('minuto', 0), errors='coerce').fillna(0).astype(int)
            for fid, sub in df_g.groupby('fid_str'):
                ev[fid] = [{'m': int(r.get('m', 0)), 'team': normaliza(r.get('equipo','')), 'tipo': str(r.get('tipo',''))} for _, r in sub.iterrows()]
        return df_e, ev

    df_resto, eventos_resto = cargar_base_resto()
    df_r = df_resto
    eventos_r = eventos_resto

    if df_r.empty:
        st.warning("No encuentro base_partidos_resto.parquet")
        st.stop()

    # --- FILTROS SOLO RESTO - FIX df_futuro NO DEFINIDO ---
    @st.cache_data(show_spinner=False)
    def cargar_futuro_resto():
        p = pathlib.Path("/mnt/data/Calendario-Futuro-Ligas-Tu-Csv-LIMPIO.csv")
        if not p.exists():
            for q in [pathlib.Path(__file__).parent.resolve(), pathlib.Path(".").resolve()]:
                if (q / "Calendario-Futuro-Ligas-Tu-Csv-LIMPIO.csv").exists():
                    p = q / "Calendario-Futuro-Ligas-Tu-Csv-LIMPIO.csv"
                    break
        if not p.exists():
            return pd.DataFrame()
        df_fut = pd.read_csv(p, on_bad_lines='skip')
        df_fut['Date'] = pd.to_datetime(df_fut['Date'], errors='coerce')
        return df_fut
    df_futuro_r = cargar_futuro_resto()

    ligas_fut_all_r = sorted(df_futuro_r['League_CSV'].dropna().unique().tolist())
    if not df_r.empty and 'League' in df_r.columns:
        ligas_resto_set = set(df_r['League'].dropna().astype(str).tolist())
        ligas_fut_r = [l for l in ligas_fut_all_r if any(normaliza(l) == normaliza(le) or normaliza(l) in normaliza(le) or normaliza(le) in normaliza(l) for le in ligas_resto_set)]
        if not ligas_fut_r:
            keywords_resto = ["J1 League","J2 League","K League","CSL","A-League","Liga MX","MLS","Brasileirao","Primera Division Argentina","Primera A Colombia","Primera Division Chile","Liga 1 Peru","Serie A Ecuador","Liga Pro"]
            ligas_fut_r = [l for l in ligas_fut_all_r if any(k.lower() in l.lower() for k in keywords_resto)]
    else:
        ligas_fut_r = ligas_fut_all_r

    c1r,c2r,c3r,c4r = st.columns([2,1,1,1])
    with c1r:
        ligas_pred_sel_r = st.multiselect("Ligas futuras RESTO", ligas_fut_r, default=[], key="ligas_pred_resto", placeholder="J1, K1, CSL, MLS, Brasil...")
    with c2r:
        df_base_pred_r = df_futuro_r[df_futuro_r['League_CSV'].isin(ligas_fut_r)] if not ligas_pred_sel_r else df_futuro_r[df_futuro_r['League_CSV'].isin(ligas_pred_sel_r)]
        fechas_pred_r = sorted(df_base_pred_r['Date'].dropna().dt.date.unique())
        fechas_pred_str_r = ["Todas"] + [d.strftime("%d/%m/%Y") for d in fechas_pred_r]
        fecha_pred_sel_r = st.selectbox("Fecha desde RESTO", fechas_pred_str_r, key="fecha_pred_resto")
    with c3r:
        c_m1r, c_m2r = st.columns(2)
        with c_m1r:
            min_desde_pred_raw_r = st.text_input("MIN DESDE R", key="min_desde_pred_resto", placeholder="-")
        with c_m2r:
            min_hasta_pred_raw_r = st.text_input("MIN HASTA R", key="min_hasta_pred_resto", placeholder="-")
    with c4r:
        goles_parte_r = st.selectbox("GOLES PARTE R", ["Todo","1ªParte","2ªParte"], index=0, key="goles_parte_resto")
        cond_loc_pred_r = st.selectbox("Filtro R", ["TODOS","equipo local solamente partidos de local","equipo visitante solamente sus partidos de visitante","Local en casa / Visitante fuera"], index=3, key="cond_loc_pred_resto")
        res_1p_tipo_r = st.selectbox("Resultado 1ªP R", ["TODOS","EMPATE","GANA","PIERDE","EMPATEGANA","EMPATEPIERDE","GANAPIERDE"], index=0, key="res_1p_tipo_pred_resto")
        opciones_res_r = [f"{a}-{b}_1ªP" for a in range(5) for b in range(5)] + [f"{a}-{b}_2ªP" for a in range(5) for b in range(5)]
        resultados_pred_sel_r = st.multiselect("Resultado 1ªP / 2ªP R", opciones_res_r, default=[], key="filtro_ht_ft_resto", placeholder="Ej: 0-0_1ªP")
        overs_sel_r = st.multiselect("Overs / Unders R", ["1P >0.5","1P >1.5","1P >2.5","2P >0.5","2P >1.5","2P >2.5"], default=[], key="overs_unders_pred_resto", placeholder="Ej: 1P >0.5")
        res_live_tipo_r = st.selectbox("Resultado LIVE R", ["TODOS","EMPATE","GANA","PIERDE","EMPATEGANA","EMPATEPIERDE","GANAPIERDE"], index=0, key="res_live_tipo_resto")
        min_live_raw_r = st.text_input("MIN LIVE R", key="min_live_resto", placeholder="Ej: 76")

    # --- EQUIPOS MANUALES RESTO - AÑADIDO (igual que EUROPA) ---
    lista_hist_equipos_resto = sorted(pd.concat([df_r['HomeTeam'], df_r['AwayTeam']]).dropna().astype(str).unique().tolist())
    c_man1_r, c_man2_r = st.columns(2)
    with c_man1_r:
        equipos_manuales_1_r = st.multiselect("Equipos manuales 1", lista_hist_equipos_resto, default=[], key="eq_manual_1_resto", placeholder="Ej: Bahia, Flamengo...")
        cond_manual_1_r = st.selectbox("Cond manual 1", ["TODOS","solo local","solo visitante"], key="cond_manual_1_resto")
    with c_man2_r:
        equipos_manuales_2_r = st.multiselect("Equipos manuales 2", lista_hist_equipos_resto, default=[], key="eq_manual_2_resto", placeholder="Ej: Mirassol, Palmeiras...")
        cond_manual_2_r = st.selectbox("Cond manual 2", ["TODOS","solo local","solo visitante"], key="cond_manual_2_resto")

    def _parse_min_pred_r(v):
        try:
            if v is None or str(v).strip() in ["", "-", "–", "—"]: return None
            return int(str(v).strip().replace("'", ""))
        except: return None
    MIN_DESDE_PRED_R = _parse_min_pred_r(min_desde_pred_raw_r)
    MIN_HASTA_PRED_R = _parse_min_pred_r(min_hasta_pred_raw_r)
    MIN_LIVE_R = _parse_min_pred_r(min_live_raw_r)
    MIN_LIVE_R = _parse_min_pred_r(min_live_raw_r)

    if fecha_pred_sel_r!= "Todas":
        try:
            f_date_r = pd.to_datetime(fecha_pred_sel_r, dayfirst=True).date()
            df_base_pred_r = df_base_pred_r[df_base_pred_r['Date'].dt.date >= f_date_r]
        except: pass

    df_base_pred_r = df_base_pred_r.sort_values('Date').head(1000)

    opciones_partidos_r = []
    for _, r in df_base_pred_r.iterrows():
        try:
            fecha_s = r['Date'].strftime("%d/%m")
            liga_s = str(r['League_CSV'])[:15]
            h = str(r['HomeTeam']).strip()
            a = str(r['AwayTeam']).strip()
            fid = str(r.get('fixture_id',''))
            opciones_partidos_r.append(f"{fecha_s} | {liga_s} | {h} vs {a} | {fid}")
        except: continue

    partidos_sel_r = []
    if not opciones_partidos_r:
        st.info("No hay partidos futuros RESTO con ese filtro")
    else:
        partidos_sel_r = st.multiselect("Elige partido futuro RESTO", opciones_partidos_r, key="partidos_pred_sel_resto", placeholder="Ej: Kashima vs Urawa - J1")

    partidos_pred_copy_r = []
    # FIX MANUALES AUNQUE NO HAYA FUTURO SELECCIONADO
    manuales_extra_r = []
    if 'equipos_manuales_1_r' in locals() and equipos_manuales_1_r: manuales_extra_r.extend(equipos_manuales_1_r)
    if 'equipos_manuales_2_r' in locals() and equipos_manuales_2_r: manuales_extra_r.extend(equipos_manuales_2_r)

    if not partidos_sel_r and not manuales_extra_r:
        st.caption("Selecciona partido futuro RESTO")
    else:
        partidos_pred_copy_r = []
        partidos_a_iterar_r = partidos_sel_r if partidos_sel_r else (["MANUAL_ONLY"] if manuales_extra_r else [])

        for partido_str_r in partidos_a_iterar_r:
            if "MANUAL_ONLY" in partido_str_r:
                st.markdown(f"<div style='font-family:monospace;font-weight:900;background:#0A2342;color:#fff;padding:6px 8px;margin:12px 0 4px 0;font-size:12px'>🔮 MANUAL RESTO: {', '.join(manuales_extra_r)}</div>", unsafe_allow_html=True)
                equipos_a_mostrar_r = manuales_extra_r
                h_fut_r = ""
                a_fut_r = ""
            else:
                try:
                    partes_r = partido_str_r.split("|")
                    teams_part_r = partes_r[2].strip() if len(partes_r)>=3 else ""
                    if " vs " in teams_part_r:
                        h_fut_r, a_fut_r = [x.strip() for x in teams_part_r.split(" vs ")]
                    else:
                        continue
                except:
                    continue
                # conteo futuro resto CON MIN
                def _cnt_fut_r(nom):
                    _norm = normaliza(nom); _up = nom.upper().strip()
                    _df = df_r[(df_r['HomeTeam'].astype(str).str.upper().str.strip() == _up) | (df_r['AwayTeam'].astype(str).str.upper().str.strip() == _up)]
                    if _df.empty:
                        _df = df_r[(df_r['HomeTeam'].apply(lambda x: normaliza(x)==_norm)) | (df_r['AwayTeam'].apply(lambda x: normaliza(x)==_norm))]
                    _tot = len(_df)
                    _df_f = _df.copy()
                    if resultados_pred_sel_r:
                        set_1p_r = set(); set_2p_r = set()
                        for s in resultados_pred_sel_r:
                            if "_1ªP" in s:
                                try: a,b = s.replace("_1ªP","").split("-"); set_1p_r.add((int(a),int(b)))
                                except: pass
                            if "_2ªP" in s:
                                try: a,b = s.replace("_2ªP","").split("-"); set_2p_r.add((int(a),int(b)))
                                except: pass
                        if set_1p_r or set_2p_r:
                            def _cumple_r(rr):
                                try:
                                    hg_ = int(float(rr.get('FTHG',0) or 0)); ag_ = int(float(rr.get('FTAG',0) or 0))
                                    hthg_ = int(float(rr.get('HTHG',0) or 0)); htag_ = int(float(rr.get('HTAG',0) or 0))
                                except: return False
                                if set_1p_r and (hthg_, htag_) in set_1p_r: return True
                                if set_2p_r and (hg_, ag_) in set_2p_r: return True
                                return False
                            _df_f = _df_f[_df_f.apply(_cumple_r, axis=1)]
                    if MIN_DESDE_PRED_R is not None or MIN_HASTA_PRED_R is not None:
                        def _tiene_min_fr(rr):
                            fid = str(rr.get('fixture_id','')).split('.')[0]
                            for ev in eventos_r.get(fid, []):
                                if 'Missed' in ev.get('tipo',''): continue
                                mm = ev.get('m',-1)
                                if MIN_DESDE_PRED_R is not None and mm < MIN_DESDE_PRED_R: continue
                                if MIN_HASTA_PRED_R is not None and mm > MIN_HASTA_PRED_R: continue
                                return True
                            return False
                        _df_f = _df_f[_df_f.apply(_tiene_min_fr, axis=1)]
                    return len(_df_f), _tot
                f_h_filt_r, f_h_tot_r = _cnt_fut_r(h_fut_r)
                f_a_filt_r, f_a_tot_r = _cnt_fut_r(a_fut_r)
                st.markdown(f"<div style='font-family:monospace;font-weight:900;background:#0A2342;color:#fff;padding:6px 8px;margin:12px 0 4px 0;font-size:12px'>🔮 FUTURO RESTO: {h_fut_r} {f_h_filt_r}/{f_h_tot_r} vs {a_fut_r} {f_a_filt_r}/{f_a_tot_r} | {partes_r[0].strip()}</div>", unsafe_allow_html=True)
                equipos_a_mostrar_r = [h_fut_r, a_fut_r]
                if 'equipos_manuales_1_r' in locals() and equipos_manuales_1_r:
                    equipos_a_mostrar_r.extend(equipos_manuales_1_r)
                if 'equipos_manuales_2_r' in locals() and equipos_manuales_2_r:
                    equipos_a_mostrar_r.extend(equipos_manuales_2_r)

            for nombre_eq_r in equipos_a_mostrar_r:
                norm_eq_r = normaliza(nombre_eq_r)
                eq_up_r = nombre_eq_r.upper().strip()
                df_team_r = df_r[(df_r['HomeTeam'].astype(str).str.upper().str.strip() == eq_up_r) | (df_r['AwayTeam'].astype(str).str.upper().str.strip() == eq_up_r)]
                if df_team_r.empty:
                    df_team_r = df_r[(df_r['HomeTeam'].apply(lambda x: normaliza(x)==norm_eq_r)) | (df_r['AwayTeam'].apply(lambda x: normaliza(x)==norm_eq_r))]

                df_team_base_total_r = df_team_r.copy()
                # --- FIX FILTRO LOCAL/VISITANTE RESPETA COND MANUAL 1/2 ---
                es_manual_1 = 'equipos_manuales_1_r' in locals() and nombre_eq_r in equipos_manuales_1_r
                es_manual_2 = 'equipos_manuales_2_r' in locals() and nombre_eq_r in equipos_manuales_2_r

                if es_manual_1:
                    if cond_manual_1_r == "solo local":
                        df_team_r = df_team_r[df_team_r['HomeTeam'].astype(str).str.upper().str.strip() == eq_up_r]
                    elif cond_manual_1_r == "solo visitante":
                        df_team_r = df_team_r[df_team_r['AwayTeam'].astype(str).str.upper().str.strip() == eq_up_r]
                elif es_manual_2:
                    if cond_manual_2_r == "solo local":
                        df_team_r = df_team_r[df_team_r['HomeTeam'].astype(str).str.upper().str.strip() == eq_up_r]
                    elif cond_manual_2_r == "solo visitante":
                        df_team_r = df_team_r[df_team_r['AwayTeam'].astype(str).str.upper().str.strip() == eq_up_r]
                else:
                    # equipos de futuro - respeta Filtro R
                    if cond_loc_pred_r == "equipo local solamente partidos de local":
                        df_team_r = df_team_r[df_team_r['HomeTeam'].astype(str).str.upper().str.strip() == eq_up_r]
                    elif cond_loc_pred_r == "equipo visitante solamente sus partidos de visitante":
                        df_team_r = df_team_r[df_team_r['AwayTeam'].astype(str).str.upper().str.strip() == eq_up_r]
                    elif cond_loc_pred_r == "Local en casa / Visitante fuera":
                        if 'h_fut_r' in locals() and nombre_eq_r == h_fut_r:
                            df_team_r = df_team_r[df_team_r['HomeTeam'].astype(str).str.upper().str.strip() == eq_up_r]
                        elif 'a_fut_r' in locals() and nombre_eq_r == a_fut_r:
                            df_team_r = df_team_r[df_team_r['AwayTeam'].astype(str).str.upper().str.strip() == eq_up_r]

                df_team_base_pred_r = df_team_r.copy()
                if resultados_pred_sel_r:
                    set_1p_r = set(); set_2p_r = set()
                    for s in resultados_pred_sel_r:
                        if "_1ªP" in s:
                            try: a,b = s.replace("_1ªP","").split("-"); set_1p_r.add((int(a),int(b)))
                            except: pass
                        if "_2ªP" in s:
                            try: a,b = s.replace("_2ªP","").split("-"); set_2p_r.add((int(a),int(b)))
                            except: pass
                    if set_1p_r or set_2p_r:
                        def _cumple_res_pred_r(rr):
                            try:
                                hg_ = int(float(rr.get('FTHG',0) or 0)); ag_ = int(float(rr.get('FTAG',0) or 0))
                                hthg_ = int(float(rr.get('HTHG',0) or 0)); htag_ = int(float(rr.get('HTAG',0) or 0))
                            except: return False
                            if set_1p_r and (hthg_, htag_) in set_1p_r: return True
                            if set_2p_r and (hg_, ag_) in set_2p_r: return True
                            return False
                        df_team_r = df_team_r[df_team_r.apply(_cumple_res_pred_r, axis=1)]

                if overs_sel_r:
                    def _cumple_overs_pred_r(rr):
                        try:
                            hg_ = int(float(rr.get('FTHG',0) or 0)); ag_ = int(float(rr.get('FTAG',0) or 0))
                            hthg_ = int(float(rr.get('HTHG',0) or 0)); htag_ = int(float(rr.get('HTAG',0) or 0))
                        except: return False
                        g1 = hthg_ + htag_
                        g2 = (hg_ + ag_) - g1
                        if g2 < 0: g2 = 0
                        for o in overs_sel_r:
                            if o == "1P >0.5" and not (g1 > 0.5): return False
                            if o == "1P >1.5" and not (g1 > 1.5): return False
                            if o == "1P >2.5" and not (g1 > 2.5): return False
                            if o == "2P >0.5" and not (g2 > 0.5): return False
                            if o == "2P >1.5" and not (g2 > 1.5): return False
                            if o == "2P >2.5" and not (g2 > 2.5): return False
                        return True
                    df_team_r = df_team_r[df_team_r.apply(_cumple_overs_pred_r, axis=1)]

                if res_1p_tipo_r!= "TODOS":
                    def _cumple_1p_tipo_r(rr):
                        try:
                            hthg_ = int(float(rr.get('HTHG',0) or 0)); htag_ = int(float(rr.get('HTAG',0) or 0))
                        except: return False
                        hn_ = normaliza(rr.get('HomeTeam','')); an_ = normaliza(rr.get('AwayTeam',''))
                        if norm_eq_r == hn_:
                            r_ = "GANA" if hthg_ > htag_ else "EMPATE" if hthg_ == htag_ else "PIERDE"
                        elif norm_eq_r == an_:
                            r_ = "GANA" if htag_ > hthg_ else "EMPATE" if htag_ == hthg_ else "PIERDE"
                        else:
                            return False
                        if res_1p_tipo_r == "EMPATE": return r_ == "EMPATE"
                        if res_1p_tipo_r == "GANA": return r_ == "GANA"
                        if res_1p_tipo_r == "PIERDE": return r_ == "PIERDE"
                        if res_1p_tipo_r == "EMPATEGANA": return r_ in ("EMPATE","GANA")
                        if res_1p_tipo_r == "EMPATEPIERDE": return r_ in ("EMPATE","PIERDE")
                        if res_1p_tipo_r == "GANAPIERDE": return r_ in ("GANA","PIERDE")
                        return True
                    df_team_r = df_team_r[df_team_r.apply(_cumple_1p_tipo_r, axis=1)]

                # --- LIVE R: RESULTADO EN MINUTO X ---
                if res_live_tipo_r != "TODOS" and MIN_LIVE_R is not None:
                    def _strip_acc_r(s):
                        try:
                            return ''.join(c for c in unicodedata.normalize('NFKD', str(s)) if not unicodedata.combining(c))
                        except:
                            return str(s)
                    def _equipo_es_local_r(team_str, home_norm, away_norm):
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
                    def _cumple_live_r(rr):
                        fid = str(rr.get('fixture_id','')).split('.')[0]
                        hn_ = normaliza(rr.get('HomeTeam','')); an_ = normaliza(rr.get('AwayTeam',''))
                        hn_c = _strip_acc_r(hn_); an_c = _strip_acc_r(an_)
                        norm_eq_c = _strip_acc_r(norm_eq_r)
                        try:
                            hg_ft = int(float(rr.get('FTHG',0) or 0)); ag_ft = int(float(rr.get('FTAG',0) or 0))
                            hthg = int(float(rr.get('HTHG',0) or 0)); htag = int(float(rr.get('HTAG',0) or 0))
                        except:
                            hg_ft=0; ag_ft=0; hthg=0; htag=0
                        evs = eventos_r.get(fid, [])
                        sh_total = (hg_ft - hthg) + (ag_ft - htag)
                        if sh_total <0: sh_total=0
                        sh_up_to = 0
                        hg_live = 0; ag_live = 0; cnt_match=0
                        for ev in evs:
                            m = ev.get('m',0)
                            if m <= 45 or m > MIN_LIVE_R:
                                if m <= MIN_LIVE_R:
                                    team_ev = _strip_acc_r(ev.get('team',''))
                                    tipo = ev.get('tipo','')
                                    if 'Missed' in tipo: continue
                                    if 'Own Goal' in tipo:
                                        if team_ev == hn_c: ag_live+=1; cnt_match+=1
                                        elif team_ev == an_c: hg_live+=1; cnt_match+=1
                                    else:
                                        if team_ev == hn_c: hg_live+=1; cnt_match+=1
                                        elif team_ev == an_c: ag_live+=1; cnt_match+=1
                                continue
                            sh_up_to += 1
                            team_ev = _strip_acc_r(ev.get('team',''))
                            tipo = ev.get('tipo','')
                            if 'Missed' in tipo: continue
                            es_local_raw_live = _equipo_es_local_r(team_ev, hn_, an_)
                            is_home_live = (not es_local_raw_live) if 'Own Goal' in tipo else es_local_raw_live
                            if is_home_live: hg_live+=1; cnt_match+=1
                            else: ag_live+=1; cnt_match+=1
                        if MIN_LIVE_R <= 45:
                            if cnt_match==0:
                                hg_live = hthg if hthg+htag>0 else 0
                                ag_live = htag if hthg+htag>0 else 0
                        else:
                            if sh_up_to == 0:
                                hg_live = hthg; ag_live = htag
                            elif sh_up_to == sh_total and sh_total>0:
                                hg_live = hg_ft; ag_live = ag_ft
                            else:
                                if cnt_match==0 and sh_up_to>0:
                                    hg_live = hg_ft if sh_up_to==sh_total else hthg
                                    ag_live = ag_ft if sh_up_to==sh_total else htag
                        if norm_eq_c == hn_c:
                            r_ = "GANA" if hg_live > ag_live else "EMPATE" if hg_live == ag_live else "PIERDE"
                        elif norm_eq_c == an_c:
                            r_ = "GANA" if ag_live > hg_live else "EMPATE" if ag_live == hg_live else "PIERDE"
                        else:
                            return False
                        if res_live_tipo_r == "EMPATE": return r_ == "EMPATE"
                        if res_live_tipo_r == "GANA": return r_ == "GANA"
                        if res_live_tipo_r == "PIERDE": return r_ == "PIERDE"
                        if res_live_tipo_r == "EMPATEGANA": return r_ in ("EMPATE","GANA")
                        if res_live_tipo_r == "EMPATEPIERDE": return r_ in ("EMPATE","PIERDE")
                        if res_live_tipo_r == "GANAPIERDE": return r_ in ("GANA","PIERDE")
                        return True
                    df_team_r = df_team_r[df_team_r.apply(_cumple_live_r, axis=1)]

                if df_team_r.empty:
                    st.caption(f"{nombre_eq_r} - sin historial en base RESTO")
                    continue

                total_r = len(df_team_base_total_r) if 'df_team_base_total_r' in locals() else len(df_team_r)
                if MIN_DESDE_PRED_R is not None or MIN_HASTA_PRED_R is not None:
                    def _tiene_min_eq_r(rr):
                        fid = str(rr.get('fixture_id','')).split('.')[0]
                        for ev in eventos_r.get(fid, []):
                            if 'Missed' in ev.get('tipo',''): continue
                            mm = ev.get('m',-1)
                            if MIN_DESDE_PRED_R is not None and mm < MIN_DESDE_PRED_R: continue
                            if MIN_HASTA_PRED_R is not None and mm > MIN_HASTA_PRED_R: continue
                            return True
                        return False
                    filt_r = len(df_team_r[df_team_r.apply(_tiene_min_eq_r, axis=1)])
                else:
                    filt_r = len(df_team_r)
                st.markdown(f"<div style='font-family:monospace;font-weight:900;background:#000;color:#fff;padding:2px 6px;margin:6px 0 2px 0;font-size:10px'>{nombre_eq_r.upper()} {filt_r}/{total_r} RESTO</div>", unsafe_allow_html=True)
                # FIX RESTO ORDEN J10 arriba = ultimo - FIX ISO 03/12 -> 12/03 - FIX REMO ULTIMO BRAGANTINO 18/10 ARRIBA
                def _parse_fecha_resto_robusto(s):
                    try:
                        if pd.isna(s):
                            return pd.NaT
                        d = pd.to_datetime(s, format='%Y-%m-%d', errors='coerce')
                        if pd.isna(d):
                            d = pd.to_datetime(s, dayfirst=True, errors='coerce')
                        if pd.isna(d):
                            d = pd.to_datetime(s, errors='coerce')
                        return d
                    except:
                        return pd.NaT
                df_team_base_pred_r = df_team_base_total_r.copy()
                df_team_base_pred_r['Date_parsed'] = df_team_base_pred_r['Date'].apply(_parse_fecha_resto_robusto)
                df_team_base_pred_r['fid_num'] = pd.to_numeric(df_team_base_pred_r['fixture_id'], errors='coerce')
                df_team_base_pred_r = df_team_base_pred_r.sort_values(['Date_parsed','fid_num'], ascending=[True, True])
                df_team_r['Date_parsed'] = df_team_r['Date'].apply(_parse_fecha_resto_robusto) if not df_team_r.empty else df_team_r.get('Date')
                df_team_r['fid_num'] = pd.to_numeric(df_team_r['fixture_id'], errors='coerce') if not df_team_r.empty else 0
                df_team_r = df_team_r.sort_values(['Date_parsed','fid_num'], ascending=[True, True]) if not df_team_r.empty else df_team_r
                df_team_r = df_team_r.sort_values('Date_parsed', ascending=False)
                df_team_base_pred_r = df_team_base_pred_r.sort_values('Date_parsed', ascending=False)
                if not df_team_base_pred_r.empty and 'Jornada' in df_team_base_pred_r.columns:
                    fecha_por_j = df_team_base_pred_r.groupby('Jornada')['Date_parsed'].max()
                    jornadas_r = fecha_por_j.sort_values(ascending=False).head(15).index.tolist()
                else:
                    jornadas_r = sorted(df_team_base_pred_r['Jornada'].dropna().unique(), reverse=True)[:15]
                for j in jornadas_r:
                    d_j_ok_r = df_team_r[df_team_r['Jornada']==j].sort_values('Date_parsed', ascending=False) if not df_team_r.empty and 'Jornada' in df_team_r.columns else pd.DataFrame()
                    if d_j_ok_r.empty:
                        try:
                            _base_j_r = df_team_base_pred_r[df_team_base_pred_r['Jornada']==j] if 'df_team_base_pred_r' in locals() else df_team_base_total_r[df_team_base_total_r['Jornada']==j]
                            if not _base_j_r.empty:
                                _r0_r = _base_j_r.iloc[0]
                                _h0_r = str(_r0_r.get('HomeTeam','')).strip()
                                _es_local_hueco_r = (normaliza(nombre_eq_r) == normaliza(_h0_r))
                                _loc_txt_r = "CASA" if _es_local_hueco_r else "VISITANTE"
                                _bg_hueco_r = "#ffffff" if _es_local_hueco_r else "#fffde7"
                            else:
                                _loc_txt_r = ""
                                _bg_hueco_r = "#f5f5f5"
                        except:
                            _loc_txt_r = ""
                            _bg_hueco_r = "#f5f5f5"
                        st.markdown(f"<div style='font-family:monospace; text-align:center; padding:4px; max-width:480px; margin:2px auto; background:{_bg_hueco_r}; border-radius:6px; border:1px solid #ececec;'><div style='color:#000; font-weight:900; font-size:10px;'>J{int(j)} | — {_loc_txt_r}</div></div><div style='height:2.5px;background:#0A2342;margin:4px auto 10px auto; max-width:480px;'></div>", unsafe_allow_html=True)
                        continue
                    d_j_r = d_j_ok_r
                    html_lineas_r = ""
                    for _, r in d_j_r.iterrows():
                        fid = str(r.get('fixture_id','')).split('.')[0]
                        if MIN_DESDE_PRED_R is not None or MIN_HASTA_PRED_R is not None:
                            _tiene = False
                            for _ev in eventos_r.get(fid, []):
                                if 'Missed' in _ev.get('tipo',''): continue
                                _mm = _ev.get('m', -1)
                                if MIN_DESDE_PRED_R is not None and _mm < MIN_DESDE_PRED_R: continue
                                if MIN_HASTA_PRED_R is not None and _mm > MIN_HASTA_PRED_R: continue
                                _tiene = True
                                break
                            if not _tiene:
                                continue
                        h = str(r.get('HomeTeam','')).strip(); a = str(r.get('AwayTeam','')).strip()
                        try: hg = int(float(r.get('FTHG',0))); ag = int(float(r.get('FTAG',0)))
                        except: hg=0; ag=0
                        h_norm_r = normaliza(h); a_norm_r = normaliza(a)
                        if norm_eq_r == h_norm_r: col_main = "#0f8105" if hg>ag else "#f31818" if hg<ag else "#8B4513"
                        elif norm_eq_r == a_norm_r: col_main = "#0f8105" if ag>hg else "#f31818" if ag<hg else "#8B4513"
                        else: col_main = "#000"
                        try: hthg = int(float(r.get('HTHG',0) or 0)); htag = int(float(r.get('HTAG',0) or 0))
                        except: hthg=0; htag=0
                        ht_str = f"[{hthg}-{htag}]"
                        # [RESTO-FIX2-VISUAL] - MISMA LOGICA QUE FIX2
                        try:
                            _nf_clean = str(norm_eq_r).upper().strip()
                            _h_clean = str(h_norm_r).upper().strip()
                            _a_clean = str(a_norm_r).upper().strip()
                            _is_home = _nf_clean == _h_clean
                            _is_away = _nf_clean == _a_clean
                        except:
                            _is_home = (norm_eq_r == h_norm_r)
                            _is_away = (norm_eq_r == a_norm_r)
                        if _is_home:
                            if hthg > htag: col_ht = "#000"
                            elif hthg < htag: col_ht = "#000"
                            else: col_ht = "#000"
                        elif _is_away:
                            if htag > hthg: col_ht = "#000"
                            elif htag < hthg: col_ht = "#000"
                            else: col_ht = "#000"
                        else:
                            col_ht = "#000"
                        # 0-0 lo ponemos
                        if hthg == 0 and htag == 0:
                            estado_1p_r = "0-0 EMPATE"
                        elif _is_home:
                            if hthg > htag: estado_1p_r = "GANA"
                            elif hthg < htag: estado_1p_r = "PIERDE"
                            else: estado_1p_r = "EMPATE"
                        elif _is_away:
                            if htag > hthg: estado_1p_r = "GANA"
                            elif htag < hthg: estado_1p_r = "PIERDE"
                            else: estado_1p_r = "EMPATE"
                        else:
                            estado_1p_r = "EMPATE"
                        if "GANA" in estado_1p_r: col_estado_r = "#0f8105"
                        elif "PIERDE" in estado_1p_r: col_estado_r = "#f31818"
                        else: col_estado_r = "#8B4513"
                        ht_html = f"<span style='color:{col_estado_r};font-weight:900;font-size:10px;margin-left:6px'>{estado_1p_r}</span>"

                        filtro_act = (MIN_DESDE_PRED_R is not None or MIN_HASTA_PRED_R is not None)
                        # [RESTO-FIX2-AGRUPADO] - GOLES DIVIDIDOS IZQ/DER IGUAL QUE FIX2
                        import re
                        def _es_home_r(team_str):
                            def _clean(s):
                                s = str(s).upper().strip()
                                s = re.sub(r'^(VFL|1 FC|1\. FC|FC|CF|SC|SV|TSG|BORUSSIA|BAYER|SPVGG|SG|VfB|FSV|BSC)\s+', '', s)
                                return s.strip()
                            t = _clean(team_str)
                            hn_c = _clean(h_norm_r)
                            an_c = _clean(a_norm_r)
                            if t == hn_c: return True
                            if t == an_c: return False
                            if hn_c in t or t in hn_c: return True
                            if an_c in t or t in an_c: return False
                            if t.split()[-1] == hn_c.split()[-1]: return True
                            if t.split()[-1] == an_c.split()[-1]: return False
                            return False
                        def _agrupa_r_con_score(evs, sh=0, sa=0):
                            grupos=[]; last=None; cur=[]; h=sh; a=sa; lh=sh; la=sa
                            for ev in evs:
                                if 'Missed' in ev.get('tipo',''): continue
                                m=ev.get('m',-1); team_ev=str(ev.get('team','')).strip()
                                is_home = not _es_home_r(team_ev) if 'Own Goal' in ev.get('tipo','') else _es_home_r(team_ev)
                                if is_home: h+=1
                                else: a+=1
                                benef = h_norm_r if is_home else a_norm_r
                                es_mio = norm_eq_r in benef
                                col_min = col_main if es_mio else "#000"
                                peso = "font-weight:900;" if es_mio else "font-weight:700;"
                                sub_min_r = ""
                                en_rango = (MIN_DESDE_PRED_R is None or m >= MIN_DESDE_PRED_R) and (MIN_HASTA_PRED_R is None or m <= MIN_HASTA_PRED_R)
                                if filtro_act and en_rango:
                                    span = f"<span style='color:{col_min};{peso};{sub_min_r}background:#D3D3D3;border-radius:3px;padding:1px 4px;margin-right:1px;font-size:10px'>{m}'</span>"
                                else:
                                    span = f"<span style='color:{col_min};{peso};{sub_min_r}margin-right:1px;font-size:10px'>{m}'</span>"
                                if last is not None and is_home != last and cur:
                                    grupos.append(("".join(cur), lh, la, last)); cur=[]
                                cur.append(span); last=is_home; lh=h; la=a
                            if cur: grupos.append(("".join(cur), lh, la, last))
                            return grupos, h, a
                        # --- FIX2 STYLE PARA RESTO ---
                        hn = h_norm_r; an = a_norm_r
                        def res_eq_pred_r(gf, gc): return "G" if gf>gc else "E" if gf==gc else "P"
                        if norm_eq_r == hn: r1 = res_eq_pred_r(hthg, htag); rF = res_eq_pred_r(hg, ag)
                        elif norm_eq_r == an: r1 = res_eq_pred_r(htag, hthg); rF = res_eq_pred_r(ag, hg)
                        else: r1="E"; rF="E"
                        estado = f"{r1}/{rF}"
                        EMOJI_SEL_R = "⚪"
                        EMOJI_RIVAL_R = "⚫"
                        if norm_eq_r == hn:
                            h_txt = f"<span style='color:{col_main};text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:3px;font-weight:900'>{h}</span>"
                            a_txt = f"<span style='color:#000'>{a}</span>"
                            emoji_home_r = EMOJI_SEL_R; emoji_away_r = EMOJI_RIVAL_R
                        elif norm_eq_r == an:
                            h_txt = f"<span style='color:#000'>{h}</span>"
                            a_txt = f"<span style='color:{col_main};text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:3px;font-weight:900'>{a}</span>"
                            emoji_home_r = EMOJI_RIVAL_R; emoji_away_r = EMOJI_SEL_R
                        else:
                            h_txt = f"<span style='color:#000'>{h}</span>"; a_txt = f"<span style='color:#000'>{a}</span>"
                            emoji_home_r = EMOJI_RIVAL_R; emoji_away_r = EMOJI_SEL_R
                        u_black_r = "border-bottom:3.5px solid #000;padding-bottom:0px;"
                        u_black_w_r = "border-bottom:3.5px solid #000;padding-bottom:0px;color:#fff;"
                        if norm_eq_r == hn:
                            hg_disp = f"{hg}" if hg==0 and ag>0 else f"<span style='{u_black_r}'>{hg}</span>"
                            ag_disp = f"{ag}"
                            hthg_disp = f"{hthg}" if hthg==0 and htag>0 else f"<span style='{u_black_w_r}'>{hthg}</span>"
                            htag_disp = f"{htag}"
                            ft_txt = f"[{hg_disp}-{ag_disp}]"
                            ht_inner = f"{hthg_disp}-{htag_disp}"
                        elif norm_eq_r == an:
                            hg_disp = f"{hg}"
                            ag_disp = f"{ag}" if ag==0 and hg>0 else f"<span style='{u_black_r}'>{ag}</span>"
                            hthg_disp = f"{hthg}"
                            htag_disp = f"{htag}" if htag==0 and hthg>0 else f"<span style='{u_black_w_r}'>{htag}</span>"
                            ft_txt = f"[{hg_disp}-{ag_disp}]"
                            ht_inner = f"{hthg_disp}-{htag_disp}"
                        else:
                            ft_txt = f"[{hg}-{ag}]"; ht_inner = f"{hthg}-{htag}"
                        ht_str = f"[{ht_inner}]"
                        try:
                            _fecha_dt_r = pd.to_datetime(r.get('Date'), dayfirst=True, errors='coerce')
                            _fecha_str_r = _fecha_dt_r.strftime("%d/%m/%Y") if pd.notna(_fecha_dt_r) else ""
                        except:
                            _fecha_str_r = ""
                        def _es_home_r2(team_str):
                            t = str(team_str).upper().strip(); hn_u = str(hn).upper().strip(); an_u = str(an).upper().strip()
                            if t == hn_u or hn_u in t or t in hn_u: return True
                            if t == an_u or an_u in t or t in an_u: return False
                            return False
                        def _agrupa_r_con_score_sub(evs, sh=0, sa=0):
                            grupos=[]; last=None; cur=[]; h=sh; a=sa; lh=sh; la=sa; last_is_home=None
                            for ev in evs:
                                m=ev.get('m',-1); team_ev=str(ev.get('team','')).strip(); tipo=str(ev.get('tipo',''))
                                is_home_raw = _es_home_r2(team_ev)
                                is_own = 'Own Goal' in tipo
                                is_home_scoring = (not is_home_raw) if is_own else is_home_raw
                                if 'Missed Penalty' in tipo:
                                    if cur: grupos.append((cur, lh, la, last_is_home)); cur=[]; last=None
                                    grupos.append(([(m, tipo)], lh, la, is_home_scoring)); continue
                                if is_home_scoring: h+=1
                                else: a+=1
                                if last is not None and is_home_scoring != last and cur:
                                    grupos.append((cur, lh, la, last_is_home)); cur=[]
                                cur.append((m, tipo)); last=is_home_scoring; last_is_home=is_home_scoring; lh=h; la=a
                            if cur: grupos.append((cur, lh, la, last_is_home))
                            return grupos
                        evs_sorted_r = sorted(eventos_r.get(fid, []), key=lambda x: x['m'])
                        evs_1p_r = [e for e in evs_sorted_r if e.get('m',0) <= 45]
                        evs_2p_r = [e for e in evs_sorted_r if e.get('m',0) > 45]
                        def _fmt_mins_r(min_tipo_list):
                            out=[]
                            for mm, tp in min_tipo_list:
                                if 'Own Goal' in tp: out.append(f"(pp) {mm}'")
                                elif 'Missed Penalty' in tp: out.append(f"(x) {mm}'")
                                elif 'Penalty' in tp: out.append(f"(p) {mm}'")
                                else: out.append(f"{mm}'")
                            return "  ".join(out)
                        g1_data = _agrupa_r_con_score_sub(evs_1p_r, 0, 0)
                        if g1_data and not any('Missed' in tp for _, tp in g1_data[-1][0]): g1_data[-1] = (g1_data[-1][0], hthg, htag, g1_data[-1][3])
                        g2_data = _agrupa_r_con_score_sub(evs_2p_r, hthg, htag)
                        if g2_data and not any('Missed' in tp for _, tp in g2_data[-1][0]): g2_data[-1] = (g2_data[-1][0], hg, ag, g2_data[-1][3])
                        goles_parte_r = st.session_state.get("goles_parte_resto", "Todo")
                        mostrar_1p_r = goles_parte_r in ("Todo","1ªParte")
                        mostrar_2p_r = goles_parte_r in ("Todo","2ªParte")
                        filtro_act_r = (MIN_DESDE_PRED_R is not None or MIN_HASTA_PRED_R is not None)
                        es_local_j_r = (norm_eq_r == h_norm_r)
                        bg_j_r = "#ffffff" if es_local_j_r else "#fffde7"
                        html = f"<div style='font-family:monospace; text-align:center; padding:4px 4px 3px 4px; max-width:480px; margin:0 auto; line-height:1.1; background:{bg_j_r}; border-radius:6px; border:1px solid #ececec;'>"
                        html += f"<div style='font-weight:900; color:{col_main}; font-size:11px;'>J{int(j)} | {emoji_home_r} {h_txt}  {ft_txt}  {a_txt}{emoji_away_r}  <span style='background:{col_main};color:#fff;padding:1px 5px;border-radius:3px;'>{estado}</span> <span style='color:#000;'>({_fecha_str_r})</span></div>"
                        html += f"<div style='margin-top:6px; font-size:10px; color:#000;'>(1ª parte {hthg}-{htag})</div>"
                        if mostrar_1p_r:
                            if not g1_data:
                                html += f"<div style='font-size:10px; color:#888;'>—</div>"
                            else:
                                for mins_tipo, sh, sa, is_home in g1_data:
                                    emoji_gol = EMOJI_SEL_R if (is_home and hn==norm_eq_r) or (not is_home and an==norm_eq_r) else EMOJI_RIVAL_R
                                    parts = []
                                    for mm, tp in mins_tipo:
                                        if 'Own Goal' in tp: base = f"(pp) {mm}'"
                                        elif 'Missed Penalty' in tp: base = f"(x) {mm}'"
                                        elif 'Penalty' in tp: base = f"(p) {mm}'"
                                        else: base = f"{mm}'"
                                        txt = f"{base}{emoji_gol}"
                                        en_rango = (MIN_DESDE_PRED_R is None or mm >= MIN_DESDE_PRED_R) and (MIN_HASTA_PRED_R is None or mm <= MIN_HASTA_PRED_R)
                                        if filtro_act_r and en_rango:
                                            txt = f"<span style='background:#D3D3D3;border-radius:3px;padding:1px 4px;'>{txt}</span>"
                                        parts.append(txt)
                                    mins_txt = "  ".join(parts)
                                    is_missed = any('Missed' in tp for _, tp in mins_tipo)
                                    score_txt = "" if is_missed else f"{sh}-{sa}"
                                    if is_missed:
                                        html += f"<div style='display:grid; grid-template-columns: 1fr 50px 1fr; gap:8px; font-size:10px;'><div style='text-align:right;'>{mins_txt if is_home else ''}</div><div style='text-align:center;'></div><div style='text-align:left;'>{'' if is_home else mins_txt}</div></div>"
                                    else:
                                        if is_home:
                                            html += f"<div style='display:grid; grid-template-columns: 1fr 50px 1fr; gap:2px; font-size:10px; line-height:1.1; margin:0; padding:0;'><div style='text-align:right;'>{mins_txt}</div><div style='text-align:center; font-weight:700;'>{score_txt}</div><div></div></div>"
                                        else:
                                            html += f"<div style='display:grid; grid-template-columns: 1fr 50px 1fr; gap:8px; font-size:10px;'><div></div><div style='text-align:center; font-weight:700;'>{score_txt}</div><div style='text-align:left;'>{mins_txt}</div></div>"
                        if mostrar_2p_r:
                            html += f"<div style='margin:8px auto; font-size:9px; letter-spacing:2px; color:#000;'>___________________2ª________________</div>"
                            if not g2_data:
                                html += f"<div style='font-size:10px; color:#888;'>—</div>"
                            else:
                                for mins_tipo, sh, sa, is_home in g2_data:
                                    emoji_gol = EMOJI_SEL_R if (is_home and hn==norm_eq_r) or (not is_home and an==norm_eq_r) else EMOJI_RIVAL_R
                                    parts = []
                                    for mm, tp in mins_tipo:
                                        if 'Own Goal' in tp: base = f"(pp) {mm}'"
                                        elif 'Missed Penalty' in tp: base = f"(x) {mm}'"
                                        elif 'Penalty' in tp: base = f"(p) {mm}'"
                                        else: base = f"{mm}'"
                                        txt = f"{base}{emoji_gol}"
                                        en_rango = (MIN_DESDE_PRED_R is None or mm >= MIN_DESDE_PRED_R) and (MIN_HASTA_PRED_R is None or mm <= MIN_HASTA_PRED_R)
                                        if filtro_act_r and en_rango:
                                            txt = f"<span style='background:#D3D3D3;border-radius:3px;padding:1px 4px;'>{txt}</span>"
                                        parts.append(txt)
                                    mins_txt = "  ".join(parts)
                                    is_missed = any('Missed' in tp for _, tp in mins_tipo)
                                    score_txt = "" if is_missed else f"{sh}-{sa}"
                                    if is_missed:
                                        html += f"<div style='display:grid; grid-template-columns: 1fr 50px 1fr; gap:8px; font-size:10px;'><div style='text-align:right;'>{mins_txt if is_home else ''}</div><div style='text-align:center;'></div><div style='text-align:left;'>{'' if is_home else mins_txt}</div></div>"
                                    else:
                                        if is_home:
                                            html += f"<div style='display:grid; grid-template-columns: 1fr 50px 1fr; gap:2px; font-size:10px; line-height:1.1; margin:0; padding:0;'><div style='text-align:right;'>{mins_txt}</div><div style='text-align:center; font-weight:700;'>{score_txt}</div><div></div></div>"
                                        else:
                                            html += f"<div style='display:grid; grid-template-columns: 1fr 50px 1fr; gap:8px; font-size:10px;'><div></div><div style='text-align:center; font-weight:700;'>{score_txt}</div><div style='text-align:left;'>{mins_txt}</div></div>"
                        html += f"</div><div style='height:2.5px;background:#0A2342;margin:4px auto 10px auto; max-width:480px;'></div>"
                        html_lineas_r += html
                        m1 = []; m2 = []
                        for evc in sorted(eventos_r.get(fid, []), key=lambda x: x['m']):
                            if MIN_DESDE_PRED_R is not None and evc.get('m',-1) < MIN_DESDE_PRED_R: continue
                            if MIN_HASTA_PRED_R is not None and evc.get('m',-1) > MIN_HASTA_PRED_R: continue
                            if 'Missed' in evc.get('tipo',''): continue
                            mm = evc.get('m',0)
                            if mm <= 45: m1.append(f"{mm}'")
                            else: m2.append(f"{mm}'")
                        if m1 and m2: mins_txt = " ".join(m1) + f"{ht_str} " + " ".join(m2)
                        elif m1: mins_txt = " ".join(m1) + f"{ht_str}"
                        elif m2: mins_txt = f"{ht_str} " + " ".join(m2)
                        else: mins_txt = f"{ht_str}"
                        partidos_pred_copy_r.append(f"J{int(j)}|{h} {hg}-{ag} {a} | {mins_txt}{estado}")
                    st.markdown(f"<div style='line-height:1.15;white-space:normal;word-break:break-word;margin:0 0 2px 0;padding:0'>{html_lineas_r}</div>", unsafe_allow_html=True)

    if partidos_pred_copy_r:
        import html as _html
        texto_final_r = "\n".join(partidos_pred_copy_r[:200])
        safe_txt_r = _html.escape(texto_final_r)
        import streamlit.components.v1 as components
        components.html(f"""
        <textarea id="txt_pred_r" style="position:absolute;left:-9999px;top:-9999px;">{safe_txt_r}</textarea>
        <button onclick="navigator.clipboard.writeText(document.getElementById('txt_pred_r').value).then(()=>{{let b=document.getElementById('btn_pred_copy_r'); b.innerText='✓ COPIADO'; b.style.background='#0f8105'; setTimeout(()=>{{b.innerText=' COPIAR PREDICCION RESTO'; b.style.background='#0A2342'}},1200)}})"
        id="btn_pred_copy_r"
        style="width:100%;background:#0A2342;color:white;border:none;border-radius:6px;padding:12px;font-weight:900;cursor:pointer;">
         COPIAR PREDICCION RESTO ({len(partidos_sel_r)} partidos)
        </button>
        """, height=55, scrolling=False)

##############################clonado


############################################################
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
###############


with st.expander("GOLES HT / GOLES 75-90", expanded=False):
    st.caption("Precalculado - 8 partidos TODOS 6 cumplen / 5 LOCAL-VISITANTE 3 cumplen + 2 seguidos")

    @st.cache_data(show_spinner=False)
    def cargar_precalc_goles():
        import pathlib
        p1 = pathlib.Path("basepartidosprecalculado.parquet")
        p2 = pathlib.Path("basegolesprecalculado.parquet")
        if not p1.exists():
            p1 = pathlib.Path(__file__).parent.resolve() / "basepartidosprecalculado.parquet"
        if not p2.exists():
            p2 = pathlib.Path(__file__).parent.resolve() / "basegolesprecalculado.parquet"
        if not p1.exists() or not p2.exists():
            return pd.DataFrame(), pd.DataFrame(), {}, {}
        df_pp = pd.read_parquet(p1)
        df_gp = pd.read_parquet(p2)
        if 'last_date' in df_pp.columns:
            df_pp['last_date'] = pd.to_datetime(df_pp['last_date'], errors='coerce')
        # lookup rápido fid -> fila goles
        goles_by_fid = {str(r['fixture_id']): r for _, r in df_gp.iterrows()}
        # jornada por equipo una sola vez
        team_jornada = {}
        for team, g in df_gp.groupby(df_gp['HomeTeam'].astype(str).str.upper().str.strip()):
            # lo haremos luego por team normalizado, pero precalculamos lista ordenada por fecha
            pass
        # precalc simple para no recalcular en bucle - FIX JORNADA REAL DMY
        df_gp['fid_str'] = df_gp['fixture_id'].astype(str)
        if 'jornada_num' in df_gp.columns:
            jornada_by_fid = df_gp.set_index('fid_str')['jornada_num'].astype(str).to_dict()
        else:
            jornada_by_fid = {}
        team_fids = {}
        for _, r in df_gp.sort_values('Date').iterrows():
            for t in [str(r['HomeTeam']).upper().strip(), str(r['AwayTeam']).upper().strip()]:
                team_fids.setdefault(t, []).append(str(r['fixture_id']))
        team_fid_to_j = {t: {fid:i+1 for i,fid in enumerate(fids)} for t,fids in team_fids.items()}
        return df_pp, df_gp, goles_by_fid, team_fid_to_j, jornada_by_fid

    df_pre_partidos, df_pre_goles, goles_by_fid, team_fid_to_j, jornada_by_fid = cargar_precalc_goles()
    if not jornada_by_fid:
        jornada_by_fid = {}
    if df_pre_partidos.empty:
        st.warning("No encuentro basepartidosprecalculado.parquet / basegolesprecalculado.parquet")
        st.stop()

    ligas_g = sorted(df_pre_partidos['League'].dropna().unique().tolist())
    c_liga_g, c_eq_g, c_cond_g, c_ht, c_7590, c_8090 = st.columns([1,2,1,1,1,1]) # [TAG-GOLES-80-90-ADD-V15]
    with c_liga_g:
        ligas_sel_g = st.multiselect("Ligas", ligas_g, default=[], key="ligas_g_ht", placeholder="Todas")
    df_base_g = df_pre_partidos if not ligas_sel_g else df_pre_partidos[df_pre_partidos['League'].isin(ligas_sel_g)]

    # equipos ya vienen en precalc -> Team
    equipos_g = sorted(df_base_g['Team'].dropna().unique().tolist()) if not df_base_g.empty else []

    with c_eq_g:
        equipos_sel_g = st.multiselect("Equipos", equipos_g, default=[], key="eq_g_ht", placeholder="Todos")
    with c_cond_g:
        cond_g_sel = st.selectbox("Condición", ["TODOS","LOCAL","VISITANTE"], index=0, key="cond_g_ht")
    with c_ht:
        goles_ht_sel = st.selectbox("GOLES HT 30-45", ["NO","SI","Si va ganando","Si va empate","Si va perdiendo"], index=0, key="goles_ht_25_45")
    with c_7590:
        goles_7590_sel = st.selectbox("GOLES 75-90", ["NO","SI","Si va ganando","Si va empate","Si va perdiendo"], index=0, key="goles_75_90")
    with c_8090:
        goles_8090_sel = st.selectbox("GOLES 80-90", ["NO","SI","Si va ganando","Si va empate","Si va perdiendo"], index=0, key="goles_80_90") # [TAG-GOLES-80-90-ADD-V15]

    check_ht = (goles_ht_sel == "SI")
    check_75_raw = goles_7590_sel
    check_75 = (check_75_raw != "NO")
    check_80_raw = goles_8090_sel
    check_80 = (check_80_raw != "NO")
    es_modo_no_80 = (check_80_raw == "NO") # [TAG-NO80-TEMP-V19]

    if not check_ht and not check_75 and not check_80 and not es_modo_no_80:
        st.info("Activa SI en GOLES HT o en GOLES 75-90 o en GOLES 80-90")
    else:
        import json
        # --- FILTRO KEY con 80-90 + NO TEMPORADA --- [TAG-NO80-TEMP-V19]
        if es_modo_no_80 and not check_ht and not check_75:
            filtro_key = "NO_80"
        elif check_80 and not check_75 and not check_ht:
            if check_80_raw == "Si va ganando": filtro_key = "80_GANANDO"
            elif check_80_raw == "Si va empate": filtro_key = "80_EMPATE"
            elif check_80_raw == "Si va perdiendo": filtro_key = "80_PERDIENDO"
            else: filtro_key = "80"
        elif check_75_raw == "Si va ganando":
            filtro_key = "75_GANANDO"
        elif check_75_raw == "Si va empate":
            filtro_key = "75_EMPATE"
        elif check_75_raw == "Si va perdiendo":
            filtro_key = "75_PERDIENDO"
        elif check_ht and check_75_raw == "SI":
            filtro_key = "AMBOS"
        elif check_ht:
            filtro_key = "HT"
        else:
            filtro_key = "75"

        if cond_g_sel == "TODOS":
            n_margen = 7
            n_need = 5
        else:
            n_margen = 4
            n_need = 2

        if filtro_key in ["80","80_GANANDO","80_EMPATE","80_PERDIENDO","NO_80"]:
            df_f = df_base_g[(df_base_g['Condicion']==cond_g_sel)].copy()
            df_f = df_f.drop_duplicates(subset=['Team','League','Condicion'], keep='last')
        else:
            df_f = df_base_g[(df_base_g['Condicion']==cond_g_sel) & (df_base_g['Filtro']==filtro_key)].copy()
        # SIN FILTRO 5/7 ni 2 seguidos - muestra todos

        if equipos_sel_g:
            df_f = df_f[df_f['Team'].isin(equipos_sel_g)]

        # HELPERS 30-45 REAL - fuera de bucle
        def _parse_min_30_45_app(gd):
            try:
                mn = gd.get('min_num', None)
                if mn not in (None, '', 0, '0'):
                    return int(str(mn).split('+')[0].split('.')[0].strip() or 0)
                import re
                mtxt = str(gd.get('min','')).replace("'",'')
                mm = re.findall(r'\d+', mtxt)
                return int(mm[0]) if mm else 0
            except:
                return 0

        def _ok_filtro_det(det_list, fk, estado_75=""):
            if fk == "NO_80":
                for _gd in det_list:
                    _mn = _parse_min_30_45_app(_gd)
                    if 80 <= _mn <= 90:
                        return False
                return True
            for _gd in det_list:
                _mn = _parse_min_30_45_app(_gd)
                if _mn == 0:
                    continue
                if fk == "HT" and 30 <= _mn <= 45:
                    return True
                if fk == "75" and 75 <= _mn <= 90:
                    return True
                if fk == "75_GANANDO" and 75 <= _mn <= 90 and estado_75 == "GANANDO":
                    return True
                if fk == "75_EMPATE" and 75 <= _mn <= 90 and estado_75 == "EMPATE":
                    return True
                if fk == "75_PERDIENDO" and 75 <= _mn <= 90 and estado_75 == "PERDIENDO":
                    return True
                if fk == "80" and 80 <= _mn <= 90:
                    return True
                if fk == "80_GANANDO" and 80 <= _mn <= 90 and estado_75 == "GANANDO":
                    return True
                if fk == "80_EMPATE" and 80 <= _mn <= 90 and estado_75 == "EMPATE":
                    return True
                if fk == "80_PERDIENDO" and 80 <= _mn <= 90 and estado_75 == "PERDIENDO":
                    return True
                if fk == "AMBOS" and (30 <= _mn <= 45 or 75 <= _mn <= 90):
                    return True
            return False

        html_g = ""
        calificados_g = 0
        resumen_ligas_g = {}

        for _, row in df_f.sort_values(['League','cnt_7'], ascending=[True, False]).iterrows():
            team_g = row['Team']
            liga_team_g = row['League']
            try:
                _detalle_cnt = json.loads(row['partidos_json'])
            except:
                _detalle_cnt = []
            _checks_real = []
            for _p in _detalle_cnt:
                _raw = _p.get('minutos_todos_det','[]')
                try:
                    _dl = json.loads(_raw) if isinstance(_raw, str) else (_raw or [])
                except:
                    _dl = []
                _est_cnt = _p.get('estado_75','') or _p.get('estado','')
                _checks_real.append(_ok_filtro_det(_dl, filtro_key, _est_cnt))
            cnt_real_7 = sum(_checks_real)
            cnt_real_4 = sum(_checks_real[:4])
            cnt = cnt_real_7 if cond_g_sel=="TODOS" else cnt_real_4

            # FIX TOTAL: HT 30-45, 75-90 y 80-90 sin 5/7 ni 2 seguidos
            need_real = 1
            if cnt < need_real:
                continue
            calificados_g += 1

            if liga_team_g not in resumen_ligas_g:
                resumen_ligas_g[liga_team_g] = []
            # JORNADAS para resumen: J7=reciente -> J1=antigua - FIX DEFINITIVO SIN DESCOLGARSE
            def _key_dmy_cnt_fix(p):
                s = p.get('date','')
                try:
                    if '/' in s:
                        d,m,y = s.split('/')
                        return f"{y}{m.zfill(2)}{d.zfill(2)}"
                    return s
                except:
                    return ""
            checks_by_fid = {p.get('fid',''): ok for p, ok in zip(_detalle_cnt, _checks_real)}
            _detalle_cnt_ord = sorted(_detalle_cnt, key=_key_dmy_cnt_fix, reverse=True)
            _checks_real_ord = [checks_by_fid.get(p.get('fid',''), False) for p in _detalle_cnt_ord]
            _j_list = []
            for _idx, _p in enumerate(_detalle_cnt_ord[:n_margen]):
                _is_ok = _checks_real_ord[_idx] if _idx < len(_checks_real_ord) else False
                _rj = n_margen - _idx
                _is_home_loc = normaliza(_p.get('home','')) == normaliza(team_g)
                _loc = "C" if _is_home_loc else "F"
                _j_list.append(f"J{_rj}{_loc}" if _is_ok else "_")
            _j_str = ", ".join(_j_list) if _j_list else "-"
            resumen_ligas_g[liga_team_g].append((team_g, cnt, _j_str))

            html_g += f"<div style='font-family:monospace;font-weight:900;background:#0A2342;color:#fff;padding:4px 6px;margin:10px 0 2px 0'>{team_g} | {cnt}/{n_margen} cumplen 30-45:{goles_ht_sel} 75-90:{goles_7590_sel} 80-90:{goles_8090_sel} | 2 seguidos: SI</div>"

            try:
                detalle = json.loads(row['partidos_json'])
            except:
                detalle = []

            # FIX RAPIDO - mas reciente primero sin pd.to_datetime lento
            def _key_dmy_fast(p):
                s = p.get('date','')
                try:
                    if '/' in s:
                        d,m,y = s.split('/')
                        return f"{y}{m.zfill(2)}{d.zfill(2)}"
                    return s
                except:
                    return ""
            detalle = sorted(detalle, key=_key_dmy_fast, reverse=True)

            # jornada precalculada - 0 coste
            fid_to_jornada = team_fid_to_j.get(team_g.upper().strip(), {})
            if not fid_to_jornada:
                # fallback normalizado
                fid_to_jornada = team_fid_to_j.get(normaliza(team_g), {})

            for p in detalle[:n_margen]:
                    # FIX 30-45 REAL: recalcula ok con minutos_todos_det (30-45) - ignora CSV 25-45
                def _parse_min_30_45(gd):
                    try:
                        mn = gd.get('min_num', None)
                        if mn not in (None, '', 0, '0'):
                            return int(str(mn).split('+')[0].split('.')[0].strip() or 0)
                        mtxt = str(gd.get('min','')).replace("'",'')
                        import re
                        mm = re.findall(r'\d+', mtxt)
                        return int(mm[0]) if mm else 0
                    except:
                        return 0

                _det_raw_fix = p.get('minutos_todos_det','[]')
                try:
                    _det_list_fix = json.loads(_det_raw_fix) if isinstance(_det_raw_fix, str) else (_det_raw_fix or [])
                except:
                    _det_list_fix = []

                _ok_real = False
                _estado_p2 = p.get('estado_75','') or p.get('estado','')
                for _gd in _det_list_fix:
                    _mn = _parse_min_30_45(_gd)
                    if _mn == 0:
                        continue
                    if filtro_key == "HT" and 30 <= _mn <= 45:
                        _ok_real = True
                        break
                    if filtro_key == "75" and 75 <= _mn <= 90:
                        _ok_real = True
                        break
                    if filtro_key == "75_GANANDO" and 75 <= _mn <= 90 and _estado_p2 == "GANANDO":
                        _ok_real = True
                        break
                    if filtro_key == "75_EMPATE" and 75 <= _mn <= 90 and _estado_p2 == "EMPATE":
                        _ok_real = True
                        break
                    if filtro_key == "75_PERDIENDO" and 75 <= _mn <= 90 and _estado_p2 == "PERDIENDO":
                        _ok_real = True
                        break
                    if filtro_key == "80" and 80 <= _mn <= 90:
                        _ok_real = True
                        break
                    if filtro_key == "80_GANANDO" and 80 <= _mn <= 90 and _estado_p2 == "GANANDO":
                        _ok_real = True
                        break
                    if filtro_key == "80_EMPATE" and 80 <= _mn <= 90 and _estado_p2 == "EMPATE":
                        _ok_real = True
                        break
                    if filtro_key == "80_PERDIENDO" and 80 <= _mn <= 90 and _estado_p2 == "PERDIENDO":
                        _ok_real = True
                        break
                    if filtro_key == "NO_80" and not any(80 <= _parse_min_30_45(_x) <= 90 for _x in _det_list_fix):
                        _ok_real = True
                        break
                    if filtro_key == "AMBOS" and (30 <= _mn <= 45 or 75 <= _mn <= 90):
                        _ok_real = True
                        break
                ok = _ok_real

                label = "OK" if ok else "NO"
                h = p.get('home',''); a = p.get('away','')
                ft = p.get('ft','0-0')
                ht = p.get('ht','[0-0]')
                mins = p.get('mins','-')
                date = p.get('date','')
                estado = p.get('estado_75','')

                if not ok:
                    jornada_txt = ""
                    row_color = "#000000"
                else:
                    raw_j = fid_to_jornada.get(str(p.get('fid','')), '-')
                    jornada_txt = f"J{raw_j}"
                    try:
                        fh, fa = ft.split("-")
                        fh = int(fh.strip()); fa = int(fa.strip())
                    except:
                        fh = fa = 0
                    if normaliza(h) == normaliza(team_g):
                        if fh > fa: row_color = "#0f8105"
                        elif fh == fa: row_color = "#8B4513"
                        else: row_color = "#CC0000"
                    elif normaliza(a) == normaliza(team_g):
                        if fa > fh: row_color = "#0f8105"
                        elif fa == fh: row_color = "#8B4513"
                        else: row_color = "#CC0000"
                    else:
                        row_color = "#000000"

                if normaliza(h) == normaliza(team_g):
                    h_show = f"<span style='text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:3px'>{h}</span>"
                    a_show = a
                elif normaliza(a) == normaliza(team_g):
                    h_show = h
                    a_show = f"<span style='text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:3px'>{a}</span>"
                else:
                    h_show = h; a_show = a

                ht_html = f"<span style='background:#E8E8E8;color:#0A2342;font-weight:900;border-radius:3px;padding:0 4px;margin:0 3px'>{ht}</span>"

                def minuto_en_filtro(m_str, fk):
                    try:
                        num = int(''.join(filter(str.isdigit, m_str.split("'")[0])))
                    except:
                        return False
                    if fk == "HT":
                        return 30 <= num <= 45
                    elif fk in ["75","75_GANANDO","75_EMPATE","75_PERDIENDO"]:
                        return 75 <= num <= 90
                    elif fk in ["80","80_GANANDO","80_EMPATE","80_PERDIENDO"]:
                        return 80 <= num <= 90
                    elif fk == "NO_80":
                        return False
                    elif fk == "AMBOS":
                        return (30 <= num <= 45) or (75 <= num <= 90)
                    return False

                # --- TODOS los goles del partido ---
                all_goals = []
                try:
                    r = goles_by_fid.get(str(p.get('fid','')))
                    if r is not None:
                        # intenta sacar listas de minutos
                        # FIX: usa detalle real con equipo
                        det_raw = p.get('minutos_todos_det')
                        if det_raw:
                            import json as _js
                            det_list = _js.loads(det_raw) if isinstance(det_raw, str) else det_raw
                            hg = ""
                            ag = ""
                            all_goals = []
                            for gd in det_list:
                                ms = gd.get('min','')
                                eq = gd.get('equipo','')
                                is_f = eq == normaliza(team_g) or normaliza(team_g) in eq or eq in normaliza(team_g)
                                all_goals.append((ms, is_f, gd.get('min_num',0)))
                        else:
                            # sin detalle con equipo -> fallback con minutos_todos
                            hg = r.get('minutos_todos','') or p.get('minutos_todos','') or ""
                            def parse_mins(v):
                                if isinstance(v, list):
                                    return [str(x).strip() for x in v]
                                if isinstance(v, str):
                                    return [x.strip() for x in v.replace("'", "").split(",") if x.strip()]
                                return []
                            for mm in parse_mins(hg):
                                m_str = mm if "'" in mm else f"{mm}'"
                                # sin equipo no podemos diferenciar, se deja como True para no romper
                                all_goals.append((m_str, True, 0))
                            all_goals.sort(key=lambda x: x[2] or int(''.join(filter(str.isdigit, x[0])) or 0))
                except:
                    all_goals = []

                # fallback si no hay datos completos -> usa minutos_todos
                if not all_goals:
                    src = p.get('minutos_todos') or mins or ""
                    for m in str(src).split(","):
                        m=m.strip()
                        if m and m!= "-" and "HT" not in m and "2T" not in m:
                            all_goals.append((m, True, 0))

                if all_goals:
                    mins_1p_parts = []
                    mins_2p_parts = []
                    for m_str, is_filt_team, *_ in all_goals:
                        en_filtro = minuto_en_filtro(m_str, filtro_key)
                        bg = "background:#D3D3D3;border-radius:3px;" if en_filtro else ""
                        col = f"color:{row_color};font-weight:900;" if is_filt_team and 'row_color' in locals() else "color:#000;"
                        if not ok:
                            col = "color:#000;"
                        span = f"<span style='{bg}{col}padding:1px 4px;margin-right:2px'>{m_str}</span>"
                        try:
                            num_m = int(''.join(filter(str.isdigit, m_str.split("'")[0])) or 0)
                        except:
                            num_m = 0
                        if num_m <= 45:
                            mins_1p_parts.append(span)
                        else:
                            mins_2p_parts.append(span)
                    mins_1p_txt = "".join(mins_1p_parts)
                    mins_2p_txt = "".join(mins_2p_parts)
                else:
                    mins_1p_txt = "-"
                    mins_2p_txt = "-"

                raw_j = fid_to_jornada.get(str(p.get('fid','')), '-')
                if raw_j == '-':
                    # fallback si no hay mapeo fid->j, usa el orden del detalle para que no salga J-
                    try:
                        raw_j = str(n_margen - detalle[:n_margen].index(p))
                    except:
                        raw_j = '-'
                
                if not ok:
                    continue
                else:
                    jornada_txt = f"J{raw_j}"
                    if estado == "GANANDO":
                        row_color = "#0f8105"
                    elif estado == "EMPATE":
                        row_color = "#8B4513"
                    elif estado == "PERDIENDO":
                        row_color = "#CC0000"
                    else:
                        row_color = "#000000"

                    try:
                        fh, fa = ft.split("-")
                        fh = int(fh.strip()); fa = int(fa.strip())
                    except:
                        fh = fa = 0
                    if normaliza(h) == normaliza(team_g):
                        if fh > fa: row_color = "#0f8105"
                        elif fh == fa: row_color = "#8B4513"
                        else: row_color = "#CC0000"
                    elif normaliza(a) == normaliza(team_g):
                        if fa > fh: row_color = "#0f8105"
                        elif fa == fh: row_color = "#8B4513"
                        else: row_color = "#CC0000"
                    else:
                        row_color = "#000000"
                    html_g += f"<div style='font-family:monospace;font-size:11px;padding:3px 4px;border-bottom:1px solid #ddd;'><span style='color:{row_color};font-weight:700'>{jornada_txt} {h_show} {ft} {a_show} |</span> {ht_html} {mins_1p_txt} | {mins_2p_txt}<span style='color:#000'> | {date}</span></div>"

        # --- LISTADO RESUMEN ORDENADO POR LIGAS + FILTROS + COPIAR - RESTAURADO ---
        html_listado_g = "<div style='font-family:monospace;background:#fff;color:#000;padding:8px;border-radius:6px;margin:6px 0;font-size:11px;border:1px solid #000'>"
        for liga_name in sorted(resumen_ligas_g.keys()):
            html_listado_g += f"<div style='font-weight:900;margin-top:12px;color:#fff;background:#000;padding:4px 6px;border-radius:3px'>{liga_name.upper()}</div>"
            for team_r, cnt_r, j_str_r in sorted(resumen_ligas_g[liga_name], key=lambda x: x[1], reverse=True):
                html_listado_g += f"<div style='margin-left:12px;color:#000;padding:2px 0;border-bottom:1px dotted #ccc'>• {team_r} ({cnt_r}/{n_margen}) {j_str_r}</div>"
        html_listado_g += "</div>"

        if not ligas_sel_g:
            ligas_txt = "TODAS"
        elif len(ligas_sel_g) > 4:
            ligas_txt = f"{len(ligas_sel_g)} LIGAS"
        else:
            ligas_txt = ", ".join(ligas_sel_g)

        if not equipos_sel_g:
            equipos_txt = "TODOS"
        elif len(equipos_sel_g) > 8:
            equipos_txt = f"{len(equipos_sel_g)} EQUIPOS"
        else:
            equipos_txt = ", ".join(equipos_sel_g)

        filtros_txt = f"FILTROS: Ligas={ligas_txt} | Equipos={equipos_txt} | Cond={cond_g_sel} | HT={goles_ht_sel} | 75-90={goles_7590_sel} | 80-90={goles_8090_sel} | Key={filtro_key} | Vent={n_margen} | Cumplen={calificados_g}"

        if calificados_g == 0:
            st.info(f"Ningún equipo cumple 3/5 con 2 seguidos (25-45={check_ht} 75-90={check_75}) | {filtros_txt}")
            st.code(filtros_txt, language="text")
        else:
            import streamlit.components.v1 as components
            bloque = f"""
            <div style="width:100%; font-family:monospace;">
                <div style='font-family:monospace;background:#FFF9C4;color:#000;padding:8px;border:1px solid #000;border-radius:6px;margin:8px 0;font-size:11px;font-weight:700'>{filtros_txt}</div>
                <button onclick="navigator.clipboard.writeText(document.getElementById('copySourceG').innerText).then(()=>{{let b=document.getElementById('btnG_top'); b.innerText='COPIADO'; b.style.background='#0f8105'; setTimeout(()=>{{b.innerText='COPIAR FILTROS + RESUMEN ({calificados_g})'; b.style.background='#0A2342'}},1200)}})" id='btnG_top' style='width:100%;background:#0A2342;color:white;border:none;border-radius:6px;padding:12px;font-weight:900;cursor:pointer;margin-bottom:8px'>COPIAR FILTROS + RESUMEN ({calificados_g})</button>
                <div style='font-weight:900;background:#000;color:#fff;padding:6px;margin-bottom:6px'>EQUIPOS QUE CUMPLEN: {calificados_g}</div>
                <div id='copySourceG' style="max-height:none; overflow:visible;">
                    <div style='white-space:pre-wrap;margin-bottom:10px'>{filtros_txt}</div>
                    <div>{html_listado_g}</div>
                    <div>{html_g}</div>
                </div>
                <button onclick="navigator.clipboard.writeText(document.getElementById('copySourceG').innerText).then(()=>{{let b=document.getElementById('btnG'); b.innerText='COPIADO'; b.style.background='#0f8105'; setTimeout(()=>{{b.innerText='COPIAR FILTROS + RESUMEN ({calificados_g})'; b.style.background='#0A2342'}},1200)}})" id='btnG' style='width:100%;background:#0A2342;color:white;border:none;border-radius:6px;padding:12px;font-weight:900;cursor:pointer;margin-top:12px; margin-bottom:20px'>COPIAR FILTROS + RESUMEN ({calificados_g})</button>
                <div style="height:30px"></div>
            </div>
            """
            h_g = min(8000, max(1200, (len(html_g)+len(html_listado_g)+len(filtros_txt))//6 + 500))
            components.html(bloque, height=h_g, scrolling=True)
            
 # ================= BLOQUE PRE V2 - FIX PATH CLOUD - 100% INDEPENDIENTE - [TAG-PRE-V2-FIX-PATH-NO-TOCAR-FIX2-FIX3-RESTO] =================

